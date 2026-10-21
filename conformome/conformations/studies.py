"""Single-molecule studies as linked records: construct → protocol(s) → state network → occupancies.

A study lives in one directory (studies/<name>/) as construct.json, protocols.json (a list), network.json and
occupancies.json (a list). This module loads a study, checks what the JSON Schemas cannot (that every key a
transition, pathway, perturbation effect or occupancy uses is defined; that counts and fractions agree; that a
record with missing values says it is incomplete), adds confidence intervals, and compares measured occupancies
with the equilibrium force model.
"""
from __future__ import annotations

import math
from pathlib import Path

from conformome.common import check, load_validators, read_json

UNFOLDED = "U"


def load(study_dir: Path) -> dict:
    return {
        "construct": read_json(study_dir / "construct.json"),
        "protocols": read_json(study_dir / "protocols.json"),
        "network": read_json(study_dir / "network.json"),
        "occupancies": read_json(study_dir / "occupancies.json") if (study_dir / "occupancies.json").exists() else [],
    }


def schema_errors(study: dict, schema_dir: Path) -> list[str]:
    v = load_validators(schema_dir)
    errs = [f"construct: {e}" for e in check(v["construct"], study["construct"])]
    for p in study["protocols"]:
        errs += [f"{p.get('protocol_id')}: {e}" for e in check(v["protocol"], p)]
    errs += [f"network: {e}" for e in check(v["state_network"], study["network"])]
    for o in study["occupancies"]:
        errs += [f"{o.get('occupancy_id')}: {e}" for e in check(v["occupancy"], o)]
    return errs


def integrity_errors(study: dict) -> list[str]:
    c, protocols, net, occs = study["construct"], study["protocols"], study["network"], study["occupancies"]
    errs = []
    pids = {p["protocol_id"] for p in protocols}
    for p in protocols:
        if p["construct_id"] != c["construct_id"]:
            errs.append(f"{p['protocol_id']}: construct_id {p['construct_id']} is not {c['construct_id']}")
    if net["construct_id"] != c["construct_id"]:
        errs.append("network: construct_id does not match the construct")
    errs += [f"network: protocol {p} not defined" for p in net["protocol_ids"] if p not in pids]

    state_keys = [s["key"] for s in net["states"]]
    path_keys = [p["key"] for p in net["pathways"]]
    errs += [f"network: duplicate key {k}" for k in sorted({k for k in state_keys + path_keys if (state_keys + path_keys).count(k) > 1})]
    known = set(state_keys) | {UNFOLDED}
    for t in net["transitions"]:
        for end in ("from", "to"):
            if t[end] not in known:
                errs.append(f"transition {t['from']}→{t['to']}: state {t[end]} not defined")
        if t["protocol_id"] and t["protocol_id"] not in pids:
            errs.append(f"transition {t['from']}→{t['to']}: protocol {t['protocol_id']} not defined")
    for p in net["pathways"]:
        errs += [f"pathway {p['key']}: state {k} not defined" for k in p["states"] if k not in known]
    perturbations = {(p["protocol_id"], q["key"]) for p in protocols for q in p["perturbations"]}
    for e in net["perturbation_effects"]:
        if (e["protocol_id"], e["perturbation"]) not in perturbations:
            errs.append(f"perturbation effect: {e['perturbation']} is not a perturbation of {e['protocol_id']}")
        for field in ("abolishes", "creates", "stabilizes", "retains"):
            errs += [f"perturbation effect {e['perturbation']}: {field} {k} not defined" for k in e[field] if k not in known]

    for o in occs:
        oid = o["occupancy_id"]
        if o["network_id"] != net["network_id"]:
            errs.append(f"{oid}: network_id does not match")
        if o["protocol_id"] not in pids:
            errs.append(f"{oid}: protocol {o['protocol_id']} not defined")
        pool = set(path_keys) if o["basis"] == "pathway_per_trajectory" else known
        errs += [f"{oid}: key {e['key']} not defined for basis {o['basis']}" for e in o["entries"] if e["key"] not in pool]
        fractions = [e["fraction"] for e in o["entries"] if e["fraction"] is not None]
        if fractions and sum(fractions) > 1.0 + 1e-6:
            errs.append(f"{oid}: fractions sum to {sum(fractions):.3f} > 1")
        for e in o["entries"]:
            if e["count"] is not None and o["total"] is not None:
                if e["count"] > o["total"]:
                    errs.append(f"{oid}: count for {e['key']} exceeds total")
                elif e["fraction"] is not None and abs(e["fraction"] - e["count"] / o["total"]) > 0.005:
                    errs.append(f"{oid}: fraction for {e['key']} disagrees with count/total")
    for name, rec in [("construct", c), ("network", net)] + [(p["protocol_id"], p) for p in protocols] + [(o["occupancy_id"], o) for o in occs]:
        cur = rec["curation"]
        if cur["missing"] and cur["status"] in ("complete", "reviewed"):
            errs.append(f"{name}: lists missing values but has status {cur['status']}")
    return errs


def wilson_ci(count: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if total == 0:
        return (0.0, 1.0)
    p = count / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def fill_intervals(occupancy: dict) -> dict:
    """Fractions and 95% intervals from counts, where counts and a total are given."""
    total = occupancy["total"]
    for e in occupancy["entries"]:
        if e["count"] is not None and total:
            e["fraction"] = round(e["count"] / total, 4)
            e["ci95"] = list(wilson_ci(e["count"], total))
    return occupancy


def js_divergence_bits(measured: dict[str, float], predicted: dict[str, float]) -> float:
    keys = sorted(set(measured) | set(predicted))
    p = [measured.get(k, 0.0) for k in keys]
    q = [predicted.get(k, 0.0) for k in keys]
    sp, sq = sum(p), sum(q)
    p, q = [x / sp for x in p], [x / sq for x in q]
    m = [(a + b) / 2 for a, b in zip(p, q)]

    def kl(a, b):
        return sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0)
    return round(0.5 * kl(p, m) + 0.5 * kl(q, m), 4)


def equilibrium_comparison(study: dict, occupancy: dict, temperature_c: float | None = None) -> dict | None:
    """Predicted equilibrium occupancy of the network's states at the occupancy's force window, and the divergence.

    Uses the states that carry a nested dot-bracket. Returns None when the construct has no sequence, when
    fewer than two states have a usable structure, or when the occupancy has no measured fractions.
    """
    from conformome.conformations.thermo import ForceModel

    seq = study["construct"]["sequence"]
    measured = {e["key"]: e["fraction"] for e in occupancy["entries"] if e["fraction"] is not None}
    if not seq or not measured or occupancy["basis"] not in ("state_at_force", "dwell_time_fraction", "first_state_per_trajectory"):
        return None
    refs = {s["key"]: s["structure"]["dot_bracket"] for s in study["network"]["states"]
            if s["structure"]["dot_bracket"] and set(s["structure"]["dot_bracket"]) <= set("().")
            and len(s["structure"]["dot_bracket"]) == len(seq)}
    refs[UNFOLDED] = "." * len(seq)
    if len(refs) < 2:
        return None
    protocol = next(p for p in study["protocols"] if p["protocol_id"] == occupancy["protocol_id"])
    cond = protocol["conditions"]
    t = temperature_c if temperature_c is not None else (cond["temperature_c"] or 25.0)
    salt = (cond["salt_mM"] or 1021.0) / 1000.0
    window = occupancy["force_window_pn"]
    force = (window["min"] + window["max"]) / 2 if window else 0.0
    model = ForceModel(seq, study["construct"]["molecule_type"], t, salt)
    curve = model.macrostate_curve(refs, [force], unzipping_paths=len(seq) > 36,
                                   delta_kcal=None if len(seq) <= 36 else 5.0)
    predicted = {k: v[0] for k, v in curve["occupancy"].items()}
    return {"prediction_run_id": None, "model": "equilibrium",
            "predicted": [{"key": k, "fraction": round(v, 4)} for k, v in sorted(predicted.items())],
            "divergence_bits": js_divergence_bits(measured, predicted),
            "note": f"ViennaRNA equilibrium at {force:.1f} pN, {t} °C, {salt * 1000:.0f} mM monovalent salt; "
                    "pseudoknots and tertiary contacts are not modelled."}
