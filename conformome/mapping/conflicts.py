"""Conflict detection. Disagreements are flagged on the page, never averaged away.

Two evidence items conflict when they are mapped to the same state, report the same observable
type and unit, have comparable conditions (including the same construct and buffer), both carry an uncertainty, and their values differ by
more than the combined uncertainty. Items without uncertainties are not compared, and this is
recorded in the conflicts panel rather than assumed to agree.
"""

from __future__ import annotations

import math
from itertools import combinations

# Force observables are left out: unfolding and rupture forces depend on loading rate, which the
# conditions schema does not record, so values from different pulling protocols are not comparable.
COMPARABLE_TYPES = {"population", "distance", "rate", "delta_g", "exchange_rate", "fret_efficiency",
                    "radius_of_gyration", "lifetime"}


def condition_signature(conditions: dict, construct: str | None = None) -> tuple:
    """Comparable when environment, temperature, pH, buffer, ligands and construct match (rounded).

    The construct is part of the signature so that mutants, fragments and complexes are not compared
    with each other; the buffer string stands in for salt, which most sources do not record separately.
    """
    temp = conditions.get("temperature_c")
    ph = conditions.get("ph")
    return (
        conditions.get("environment"),
        None if temp is None else round(temp / 5) * 5,
        None if ph is None else round(ph * 2) / 2,
        (conditions.get("buffer") or "").strip().lower(),
        tuple(sorted(conditions.get("ligands") or [])),
        construct,
    )


def find_conflicts(evidence: list[dict]) -> list[dict]:
    by_state_type: dict[tuple, list[dict]] = {}
    for ev in evidence:
        obs = ev["observable"]
        if obs["type"] not in COMPARABLE_TYPES or obs["value"] is None:
            continue
        for m in ev["mappings"]:
            key = (m["state_id"], obs["type"], obs["unit"],
                   condition_signature(ev["conditions"], ev.get("construct", {}).get("description")))
            by_state_type.setdefault(key, []).append(ev)

    conflicts = []
    for (state_id, obs_type, unit, sig), items in sorted(by_state_type.items(), key=lambda kv: str(kv[0])):
        for a, b in combinations(sorted(items, key=lambda e: e["evidence_id"]), 2):
            ua, ub = a["observable"]["uncertainty"], b["observable"]["uncertainty"]
            if ua is None or ub is None:
                continue
            va, vb = a["observable"]["value"], b["observable"]["value"]
            combined = math.sqrt(ua ** 2 + ub ** 2)
            if abs(va - vb) > combined:
                conflicts.append({
                    "conflict_id": f"CF-{state_id}-{obs_type}-{a['evidence_id']}-{b['evidence_id']}",
                    "state_id": state_id,
                    "observable_type": obs_type,
                    "unit": unit,
                    "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                    "values": [va, vb],
                    "uncertainties": [ua, ub],
                    "reason": f"differ by {abs(va - vb):.3g} {unit or ''}, beyond combined uncertainty {combined:.3g}",
                })
    return conflicts


def not_compared(evidence: list[dict]) -> int:
    """Count evidence that could not enter the comparison (no comparable type, value or uncertainty)."""
    return sum(1 for ev in evidence
               if ev["observable"]["type"] not in COMPARABLE_TYPES
               or ev["observable"]["value"] is None
               or ev["observable"]["uncertainty"] is None)
