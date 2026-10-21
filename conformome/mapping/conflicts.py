"""Conflict detection. Disagreements are flagged on the page, never averaged away.

Two mapped evidence items conflict when they report the same observable type and unit, their
conditions are comparable, both carry a positive finite uncertainty, neither is a prediction,
and |Δ| > CONFLICT_SIGMA times the combined uncertainty (quadrature). CONFLICT_SIGMA is 3.

Comparable means: the same environment, buffer, construct description, label set and ligand set
(case-insensitive); temperature within 5 °C; pH within 0.5; salt_mM within a factor of two;
the same ion species, each concentration within a factor of two. A missing temperature, pH,
salt, buffer or ion list is not comparable. Unknown does not match unknown.

Force observables are left out: they depend on loading rate, which is not in the conditions.
"""

from __future__ import annotations

import math
from itertools import combinations

# Scalar observables that exist on at least one technique. `rate` is not in the taxonomy.
# Force observables are omitted on purpose (see the module docstring).
COMPARABLE_TYPES = {
    "population", "distance", "delta_g", "exchange_rate", "fret_efficiency",
    "radius_of_gyration", "lifetime", "transition_rate", "folding_rate",
    "free_energy_difference", "melting_temperature", "hydrodynamic_radius",
}

CONFLICT_SIGMA = 3
TEMPERATURE_TOLERANCE_C = 5.0
PH_TOLERANCE = 0.5


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive(value) -> bool:
    return _finite(value) and value > 0


def _ions(items: list) -> dict[str, float] | None:
    """Species to concentration. None when the list is empty or a concentration is missing."""
    if not items:
        return None
    out = {}
    for item in items:
        ion = str(item.get("ion") or "").replace(" ", "")
        conc = item.get("concentration_mM")
        if not ion or not _finite(conc) or conc < 0:
            return None
        out[ion] = float(conc)
    return out or None


def _factor_of_two(a: float, b: float) -> bool:
    if a == 0 and b == 0:
        return True
    if a <= 0 or b <= 0:
        return False
    return max(a, b) <= 2 * min(a, b)


def comparable(a: dict, b: dict) -> bool:
    """True when the two items were measured under conditions this release treats as the same."""
    ca, cb = a["conditions"], b["conditions"]
    if ca.get("environment") != cb.get("environment"):
        return False
    ba = (ca.get("buffer") or "").strip().lower()
    bb = (cb.get("buffer") or "").strip().lower()
    if not ba or not bb or ba != bb:
        return False
    ta, tb = ca.get("temperature_c"), cb.get("temperature_c")
    if not _finite(ta) or not _finite(tb) or abs(ta - tb) > TEMPERATURE_TOLERANCE_C:
        return False
    pa, pb = ca.get("ph"), cb.get("ph")
    if not _finite(pa) or not _finite(pb) or abs(pa - pb) > PH_TOLERANCE:
        return False
    sa, sb = ca.get("salt_mM"), cb.get("salt_mM")
    if not _finite(sa) or not _finite(sb) or not _factor_of_two(sa, sb):
        return False
    ia, ib = _ions(ca.get("ions") or []), _ions(cb.get("ions") or [])
    if ia is None or ib is None or set(ia) != set(ib):
        return False
    if any(not _factor_of_two(ia[ion], ib[ion]) for ion in ia):
        return False
    if {x.upper() for x in ca.get("ligands") or []} != {x.upper() for x in cb.get("ligands") or []}:
        return False
    da = ((a.get("construct") or {}).get("description") or "").strip().lower()
    db = ((b.get("construct") or {}).get("description") or "").strip().lower()
    if da != db:
        return False
    la = tuple(sorted((a.get("construct") or {}).get("labels") or []))
    lb = tuple(sorted((b.get("construct") or {}).get("labels") or []))
    return la == lb


def _usable(ev: dict, predictions: set[str]) -> bool:
    obs = ev["observable"]
    return (ev.get("technique") not in predictions
            and obs["type"] in COMPARABLE_TYPES
            and _finite(obs.get("value"))
            and _positive(obs.get("uncertainty"))
            and ev.get("mappings"))


def find_conflicts(evidence: list[dict], prediction_techniques: set[str] | None = None) -> list[dict]:
    predictions = prediction_techniques or set()
    groups: dict[tuple, list[dict]] = {}
    for ev in evidence:
        if not _usable(ev, predictions):
            continue
        for mapping in ev["mappings"]:
            key = (mapping["state_id"], ev["observable"]["type"], ev["observable"]["unit"])
            groups.setdefault(key, []).append(ev)

    conflicts = []
    for (state_id, obs_type, unit), items in sorted(groups.items(), key=lambda kv: str(kv[0])):
        unique = {ev["evidence_id"]: ev for ev in items}
        for a, b in combinations(sorted(unique.values(), key=lambda e: e["evidence_id"]), 2):
            if not comparable(a, b):
                continue
            ua, ub = a["observable"]["uncertainty"], b["observable"]["uncertainty"]
            va, vb = a["observable"]["value"], b["observable"]["value"]
            combined = math.sqrt(ua ** 2 + ub ** 2)
            delta = abs(va - vb)
            z = delta / combined
            if z > CONFLICT_SIGMA:
                conflicts.append({
                    "conflict_id": f"CF-{state_id}-{obs_type}-{a['evidence_id']}-{b['evidence_id']}",
                    "state_id": state_id,
                    "observable_type": obs_type,
                    "unit": unit,
                    "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                    "values": [va, vb],
                    "uncertainties": [ua, ub],
                    "z": round(z, 3),
                    "threshold_sigma": CONFLICT_SIGMA,
                    "reason": (f"differ by {delta:.3g} {unit or ''} "
                               f"({z:.2f}σ, threshold {CONFLICT_SIGMA}σ, combined uncertainty {combined:.3g})"),
                })
    return conflicts


def not_compared(evidence: list[dict], prediction_techniques: set[str] | None = None) -> int:
    """Mapped items that never entered a pairwise comparison, counted once per evidence id."""
    predictions = prediction_techniques or set()
    compared: set[str] = set()
    groups: dict[tuple, list[dict]] = {}
    for ev in evidence:
        if not ev.get("mappings") or not _usable(ev, predictions):
            continue
        for mapping in ev["mappings"]:
            key = (mapping["state_id"], ev["observable"]["type"], ev["observable"]["unit"])
            groups.setdefault(key, []).append(ev)
    for items in groups.values():
        unique = {ev["evidence_id"]: ev for ev in items}
        ordered = sorted(unique.values(), key=lambda e: e["evidence_id"])
        for a, b in combinations(ordered, 2):
            if comparable(a, b):
                compared.add(a["evidence_id"])
                compared.add(b["evidence_id"])
    mapped = {ev["evidence_id"] for ev in evidence if ev.get("mappings")}
    return len(mapped - compared)
