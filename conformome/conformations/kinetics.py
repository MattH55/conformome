"""Kinetic force model: macrostate occupancies under a force ramp, and how far they depart from equilibrium.

Coarse-grained, so that experimental loading rates (pN/s) are reachable:

  * Macrostates are named reference structures (local minima: a curated state's dot-bracket, the MFE, the open
    chain, an alternative fold). Every suboptimal structure belongs to the macrostate nearest to it in
    base-pair distance, and a macrostate's free energy at force F is the basin sum
        G_m(F) = −kT ln Σ_{s∈m} exp(−G_s(F)/kT).
  * The barrier between macrostates i and j is the highest free energy, at force F, along the lowest-saddle
    direct path between their references (ViennaRNA findpath, computed once at zero force; the force term of each
    structure on the path is added at every F). This gives each barrier its own distance to the transition
    state, set by how the exterior loop changes along the path, instead of a fitted Bell parameter.
  * The barrier height out of macrostate i is read from that landscape: the highest point on the path minus the
    lowest point on i's side of it. Rates are k_ij = k0 · exp(−(B_ij − G_i)/kT) with B_ij = max(G_i + height_i, G_j),
    and k_ji follows from the same B_ij, so k_ij/k_ji = exp((G_i − G_j)/kT): detailed balance holds and a slow
    enough ramp reproduces the equilibrium occupancies of `thermo` (same macrostate grouping) exactly.
  * The master equation dp/dt = K(F(t)) p is integrated over the ramp with matrix exponentials.

What departs from equilibrium is then attributable: to the loading rate (hysteresis, ramp-dependent unfolding
force), to the starting distribution (folding history, e.g. a structure formed co-transcriptionally from the 5'
end), or to a pathway the equilibrium model cannot see. k0 sets the absolute time scale; it is a parameter, not
a prediction, and must be calibrated against one measured rate before absolute forces are compared.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm

from conformome.conformations.thermo import ForceModel, bp_distance, midpoint_force, nearest_reference


@dataclass
class RampResult:
    forces_pn: list[float]
    occupancy: dict[str, list[float]]
    equilibrium: dict[str, list[float]]
    direction: str  # "unfold" (increasing force) or "refold"
    loading_rate_pn_s: float

    def divergence(self) -> list[float]:
        """Jensen–Shannon divergence (bits) between kinetic and equilibrium occupancies at each force."""
        names = list(self.occupancy)
        out = []
        for i in range(len(self.forces_pn)):
            p = np.array([self.occupancy[n][i] for n in names]) + 1e-300
            q = np.array([self.equilibrium[n][i] for n in names]) + 1e-300
            m = 0.5 * (p + q)
            out.append(float(0.5 * np.sum(p * np.log2(p / m)) + 0.5 * np.sum(q * np.log2(q / m))))
        return out

    def midpoint(self, folded: str) -> float | None:
        return midpoint_force(self.forces_pn, self.occupancy[folded])


class KineticModel:
    def __init__(self, model: ForceModel, references: dict[str, str], k0_per_s: float = 1e6,
                 delta_kcal: float | None = None, path_width: int = 20,
                 max_structures: int = 200_000):
        self.model = model
        self.names = list(references)
        self.refs = references
        self.k0 = k0_per_s
        self.ensemble = model.ensemble(delta_kcal, max_structures)
        self.member = nearest_reference([s for s, _ in self.ensemble], references)
        self._ens = self._arrays(self.ensemble)
        self._member_idx = np.array([self.names.index(m) for m in self.member])
        self.paths = {}
        for a in range(len(self.names)):
            for b in range(a + 1, len(self.names)):
                ra, rb = references[self.names[a]], references[self.names[b]]
                path = model.fc.path_findpath(ra, rb, path_width)
                self.paths[(a, b)] = self._arrays([(st.s, st.en) for st in path])

    def _arrays(self, structures):
        """Energy (pN·nm), unpaired exterior length (nm) and exterior helix length (nm) per structure."""
        from conformome.conformations.thermo import KCAL_PER_MOL_TO_PN_NM, exterior_loop
        el = self.model.el
        e = np.array([en for _, en in structures]) * KCAL_PER_MOL_TO_PN_NM
        ext = [exterior_loop(st) for st, _ in structures]
        return e, np.array([u for u, _ in ext]) * el["nm_per_nt"], np.array([h for _, h in ext]) * el["helix_nm"]

    def _g(self, arrays, force: float) -> np.ndarray:
        """G_s(F)/kT for an array of structures (vectorised thermo.ForceModel.free_energy_kt)."""
        e, l_ss, l_hel = arrays
        return (e - l_ss * self.model.stretch.work(force) - l_hel * force) / self.model.kt

    def basin_free_energies(self, force: float) -> np.ndarray:
        g_s = self._g(self._ens, force)
        g = np.full(len(self.names), np.inf)
        for i in range(len(self.names)):
            x = g_s[self._member_idx == i]
            if x.size:
                g[i] = x.min() - math.log(np.exp(-(x - x.min())).sum())
        return g

    def rate_matrix(self, force: float) -> np.ndarray:
        g = self.basin_free_energies(force)
        n = len(self.names)
        k = np.zeros((n, n))
        for (a, b), path in self.paths.items():
            if not (np.isfinite(g[a]) and np.isfinite(g[b])):
                continue
            # Barrier height from the local landscape along the path (relative to the lowest point on a's side
            # of the saddle), anchored on a's basin free energy; the reverse rate then follows from detailed
            # balance. Comparing the saddle with the basin sums directly would count the compact reference
            # structure, not the basin's actual population, and invent barriers that grow with force.
            landscape = self._g(path, force)
            k_star = int(np.argmax(landscape))
            height_a = float(landscape[k_star] - landscape[:k_star + 1].min())
            barrier = max(g[a] + height_a, g[b])
            k[b, a] = self.k0 * math.exp(-(barrier - g[a]))  # a -> b
            k[a, b] = self.k0 * math.exp(-(barrier - g[b]))  # b -> a
        k[np.diag_indices(n)] = -k.sum(axis=0)
        return k

    def equilibrium(self, force: float) -> np.ndarray:
        g = self.basin_free_energies(force)
        w = np.exp(-(g - np.min(g[np.isfinite(g)])))
        w[~np.isfinite(g)] = 0
        return w / w.sum()

    def ramp(self, f_start: float, f_end: float, loading_rate_pn_s: float, step_pn: float = 0.1,
             start: dict[str, float] | None = None) -> RampResult:
        """Integrate the master equation while the force changes linearly from f_start to f_end."""
        n_steps = max(1, int(round(abs(f_end - f_start) / step_pn)))
        df = (f_end - f_start) / n_steps
        dt = abs(df) / loading_rate_pn_s
        p = (np.array([start.get(nm, 0.0) for nm in self.names]) if start else self.equilibrium(f_start))
        p = p / p.sum()
        forces, occ, eq = [f_start], [p.copy()], [self.equilibrium(f_start)]
        for i in range(n_steps):
            f = f_start + (i + 1) * df
            p = expm(self.rate_matrix(f) * dt) @ p
            p = np.clip(p, 0, None)
            p /= p.sum()
            forces.append(round(f, 6))
            occ.append(p.copy())
            eq.append(self.equilibrium(f))
        return RampResult(
            forces_pn=forces,
            occupancy={nm: [float(o[i]) for o in occ] for i, nm in enumerate(self.names)},
            equilibrium={nm: [float(e[i]) for e in eq] for i, nm in enumerate(self.names)},
            direction="unfold" if f_end > f_start else "refold",
            loading_rate_pn_s=loading_rate_pn_s,
        )


def cotranscriptional_start(model: ForceModel, references: dict[str, str], step: int = 1) -> str:
    """Name of the macrostate reached by folding the chain 5'→3', keeping each prefix's MFE as it grows.

    A crude proxy for co-transcriptional folding: the structure of every prefix is the MFE of that prefix
    constrained to keep the pairs already formed, unless refolding lowers the energy by more than the
    prefix-local barrier allows (not modelled here: pairs, once formed, are kept). The full-length structure is
    assigned to the nearest reference.
    """
    import RNA

    seq = model.sequence
    kept = ""
    for end in range(step, len(seq) + 1, step):
        fc = RNA.fold_compound(seq[:end], model.md)
        constraint = kept + "." * (end - len(kept))
        fc.hc_add_from_db(constraint, RNA.CONSTRAINT_DB_ENFORCE_BP | RNA.CONSTRAINT_DB_DEFAULT)
        kept, _ = fc.mfe()
    full = kept + "." * (len(seq) - len(kept))
    return min(references, key=lambda n: (bp_distance(full, references[n]), n))
