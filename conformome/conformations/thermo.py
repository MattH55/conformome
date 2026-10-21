"""Equilibrium force model: occupancies of secondary structures under tension, from sequence.

A molecule held at constant force F between its 5' and 3' ends. Each secondary structure s has a folding free
energy ΔG_s (ViennaRNA nearest-neighbour model, relative to the open chain) and an extension x_s(F) set by its
exterior loop: the unpaired exterior nucleotides behave as a single-stranded worm-like chain, and each exterior
helix contributes a rigid length d_helix along the force. The free energy at force F is

    G_s(F) = ΔG_s − ∫_0^F x_s(f) df

and the equilibrium occupancy is p_s(F) ∝ exp(−G_s(F)/kT). Summing p_s over the structures that belong to a
macrostate gives the macrostate's occupancy; ⟨x⟩(F) gives the equilibrium force–extension curve of the
molecule (without handles or trap compliance, which do not change the occupancies at constant force).

This follows the treatment of Gerland, Bundschuh and Hwa (Biophys. J. 2001) and Manosas and Ritort
(Biophys. J. 2005). It is a baseline: where measured occupancies differ from it, the difference is information
about kinetics or folding history, which `kinetics` models.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

KCAL_PER_MOL_TO_PN_NM = 6.9477  # 1 kcal/mol = 6.9477 pN·nm per molecule
BOLTZMANN_PN_NM_PER_K = 0.01380649

# Elastic parameters of the unfolded strand and helix, with the values used in the literature cited above.
DEFAULT_ELASTICITY = {
    "rna": {"persistence_nm": 1.0, "nm_per_nt": 0.59, "helix_nm": 2.0},
    "dna": {"persistence_nm": 1.35, "nm_per_nt": 0.59, "helix_nm": 2.0},
}


def kT(temperature_c: float) -> float:
    """Thermal energy in pN·nm."""
    return BOLTZMANN_PN_NM_PER_K * (temperature_c + 273.15)


def wlc_relative_extension(force_pn: float, persistence_nm: float, kt: float) -> float:
    """z = x/L of a worm-like chain at force F, inverting the Marko–Siggia interpolation by bisection."""
    if force_pn <= 0:
        return 0.0
    lo, hi = 0.0, 1.0 - 1e-12
    for _ in range(80):
        z = 0.5 * (lo + hi)
        f = kt / persistence_nm * (0.25 / (1 - z) ** 2 - 0.25 + z)
        lo, hi = (z, hi) if f < force_pn else (lo, z)
    return 0.5 * (lo + hi)


class StretchIntegral:
    """∫_0^F z(f) df for the worm-like chain, tabulated once per (persistence length, temperature)."""

    def __init__(self, persistence_nm: float, kt: float, f_max: float = 80.0, step: float = 0.05):
        self.step = step
        n = int(f_max / step) + 1
        z = [wlc_relative_extension(i * step, persistence_nm, kt) for i in range(n)]
        self.z = z
        self.cum = [0.0]
        for i in range(1, n):
            self.cum.append(self.cum[-1] + 0.5 * (z[i - 1] + z[i]) * step)

    def _interp(self, table, force):
        i = min(int(force / self.step), len(table) - 2)
        t = force / self.step - i
        return table[i] * (1 - t) + table[i + 1] * t

    def z_at(self, force: float) -> float:
        return self._interp(self.z, force)

    def work(self, force: float) -> float:
        return self._interp(self.cum, force)


def exterior_loop(structure: str) -> tuple[int, int]:
    """(unpaired exterior nucleotides, exterior helices) of a dot-bracket structure (nested pairs only)."""
    pt = _pair_table(structure)
    i, n_unpaired, n_helix = 0, 0, 0
    while i < len(structure):
        j = pt[i]
        if j < 0:
            n_unpaired += 1
            i += 1
        else:
            n_helix += 1
            i = j + 1
    return n_unpaired, n_helix


def _pair_table(structure: str) -> list[int]:
    pt, stack = [-1] * len(structure), []
    for i, ch in enumerate(structure):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            j = stack.pop()
            pt[i], pt[j] = j, i
    return pt


def _pairs(structure: str) -> frozenset:
    return frozenset((i, j) for i, j in enumerate(_pair_table(structure)) if j > i)


def nearest_reference(structures: list[str], references: dict[str, str]) -> list[str]:
    """Name of the nearest reference (base-pair distance, ties broken by name) for each structure."""
    refs = sorted((n, _pairs(s)) for n, s in references.items())
    out = []
    for st in structures:
        ps = _pairs(st)
        out.append(min(refs, key=lambda r: (len(ps ^ r[1]), r[0]))[0])
    return out


def bp_distance(a: str, b: str) -> int:
    pa, pb = _pair_table(a), _pair_table(b)
    sa = {(i, j) for i, j in enumerate(pa) if j > i}
    sb = {(i, j) for i, j in enumerate(pb) if j > i}
    return len(sa ^ sb)


@dataclass
class ForceModel:
    sequence: str
    molecule_type: str = "rna"  # "rna" or "dna"
    temperature_c: float = 25.0
    salt_m: float = 1.021  # monovalent salt, mol/L (ViennaRNA's reference is 1.021 M)
    elasticity: dict = field(default_factory=dict)

    def __post_init__(self):
        import RNA

        self.el = dict(DEFAULT_ELASTICITY[self.molecule_type], **self.elasticity)
        self.kt = kT(self.temperature_c)
        self.stretch = StretchIntegral(self.el["persistence_nm"], self.kt)
        if self.molecule_type == "dna":
            RNA.params_load_DNA_Mathews2004()
        else:
            RNA.params_load_RNA_Turner2004()
        md = RNA.md()
        md.temperature = self.temperature_c
        md.salt = self.salt_m
        md.uniq_ML = 1
        self.md = md
        self.fc = RNA.fold_compound(self.sequence, md)

    # --- single structures -------------------------------------------------------------------------------
    def energy_kcal(self, structure: str) -> float:
        return self.fc.eval_structure(structure)

    def extension_nm(self, structure: str, force: float) -> float:
        n_un, n_hel = exterior_loop(structure)
        return n_un * self.el["nm_per_nt"] * self.stretch.z_at(force) + n_hel * self.el["helix_nm"]

    def free_energy_kt(self, structure: str, force: float, energy_kcal: float | None = None) -> float:
        """G_s(F) / kT."""
        e = self.energy_kcal(structure) if energy_kcal is None else energy_kcal
        n_un, n_hel = exterior_loop(structure)
        work = n_un * self.el["nm_per_nt"] * self.stretch.work(force) + n_hel * self.el["helix_nm"] * force
        return (e * KCAL_PER_MOL_TO_PN_NM - work) / self.kt

    # --- ensembles -------------------------------------------------------------------------------------------
    def ensemble(self, delta_kcal: float | None = None, max_structures: int = 200_000,
                 unzipping_paths_from: list[str] | None = None) -> list[tuple[str, float]]:
        """Suboptimal structures within delta of the MFE, plus the open chain.

        The default delta reaches the open chain, which is complete but grows exponentially with length. For long
        sequences pass a smaller delta and the references whose unzipping paths should be added: the structures
        along the lowest-saddle path from each reference to the open chain are the partly unfolded intermediates
        that force populates, which a truncated window would otherwise miss.
        """
        mfe_s, mfe_e = self.fc.mfe()
        delta = abs(mfe_e) + 1.0 if delta_kcal is None else delta_kcal
        subs = self.fc.subopt(int(round(delta * 100)))
        if len(subs) > max_structures:
            raise ValueError(f"{len(subs)} suboptimal structures; lower delta_kcal or sample instead")
        out = {s.structure: s.energy for s in subs}
        open_chain = "." * len(self.sequence)
        out.setdefault(open_chain, 0.0)
        for ref in unzipping_paths_from or []:
            for step in self.fc.path_findpath(ref, open_chain, 20):
                out.setdefault(step.s, step.en)
        return sorted(out.items(), key=lambda t: t[1])

    def occupancies(self, structures: list[tuple[str, float]], force: float) -> list[float]:
        g = [self.free_energy_kt(s, force, e) for s, e in structures]
        g0 = min(g)
        w = [math.exp(-(x - g0)) for x in g]
        z = sum(w)
        return [x / z for x in w]

    def macrostate_curve(self, references: dict[str, str], forces: list[float],
                         delta_kcal: float | None = None, unzipping_paths: bool = False) -> dict:
        """Equilibrium occupancy of each macrostate (structures grouped by nearest reference, in base-pair
        distance) and the mean extension, at each force."""
        ens = self.ensemble(delta_kcal, unzipping_paths_from=list(references.values()) if unzipping_paths else None)
        names = list(references)
        member = nearest_reference([s for s, _ in ens], references)
        occ = {n: [] for n in names}
        mean_x = []
        for f in forces:
            p = self.occupancies(ens, f)
            for n in names:
                occ[n].append(sum(pi for pi, m in zip(p, member) if m == n))
            mean_x.append(sum(pi * self.extension_nm(s, f) for pi, (s, _) in zip(p, ens)))
        return {"forces_pn": forces, "occupancy": occ, "mean_extension_nm": mean_x, "n_structures": len(ens),
                "parameters": self.parameters()}

    def parameters(self) -> dict:
        return {"temperature_c": self.temperature_c, "salt_m": self.salt_m, "molecule_type": self.molecule_type,
                "energy_parameters": "DNA Mathews 2004" if self.molecule_type == "dna" else "RNA Turner 2004",
                **{f"elasticity_{k}": v for k, v in self.el.items()}}


def midpoint_force(forces: list[float], occupancy_folded: list[float]) -> float | None:
    """Force at which the folded occupancy crosses 0.5 (linear interpolation), or None."""
    for i in range(1, len(forces)):
        a, b = occupancy_folded[i - 1], occupancy_folded[i]
        if (a - 0.5) * (b - 0.5) <= 0 and a != b:
            return forces[i - 1] + (0.5 - a) / (b - a) * (forces[i] - forces[i - 1])
    return None
