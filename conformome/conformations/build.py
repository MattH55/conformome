"""Build conformation, segment and assignment records for one molecule from its mapped build.

Inputs (all produced by earlier pipeline steps): build/<id>/molecule.json, mapped.json, models.json and the
exported model files in build/<id>/models/. Output: build/<id>/conformations.json with three lists,
`conformations`, `segments` and `assignments`, each validated against its JSON Schema.

What is built, and from what:
  * one conformation per curated secondary structure (nucleic acids: dot-bracket, base pairs, paired and
    unpaired segments, contour length released on unfolding);
  * one conformation per exported representative structure (coordinates, observed segments, end-to-end
    distance and radius of gyration of the traced chain, contour length released on unfolding);
  * one segment per force-spectroscopy evidence record that reports a contour-length increment;
  * one assignment per (segment, conformation) pair, scored by how far the measured increment lies from the
    conformation's predicted interval. This is the classical way force data are assigned to structures, and it
    is the baseline any learned assignment method has to beat.
"""
from __future__ import annotations

from pathlib import Path

from conformome.common import check, load_validators, read_json, today, write_json
from conformome.conformations import geometry

METHOD_VERSION = "conformome.conformations " + geometry.GEOMETRY_VERSION
LICENCE = "CC BY 4.0"
URL = "https://conformome.org"
ACCEPT_MIN_NM = 2.0  # assignment threshold: residual ≤ max(2 × measured uncertainty, ACCEPT_MIN_NM)
LENGTH_UNITS_TO_NM = {"nm": 1.0, "Å": 0.1, "A": 0.1, "angstrom": 0.1, "pm": 0.001, "um": 1000.0, "µm": 1000.0}


def _prov(acc: str) -> dict:
    return {"source": "Conformome (computed)", "doi": None, "deposit_id": acc, "retrieved": today(),
            "url": URL, "licence": LICENCE}


def _derived(quantity, value, unit, method, parameters=None, assumptions=None) -> dict:
    return {"quantity": quantity, "value": value, "unit": unit, "method": method,
            "parameters": parameters or {}, "assumptions": assumptions or []}


def _released_entry(rel: geometry.Released, method: str) -> dict:
    params = dict(rel.parameters, interval_nm=[rel.low, rel.high])
    return _derived("contour_length_released_nm", rel.value, "nm", method, params, rel.assumptions)


def from_secondary_structure(acc: str, mtype: str, state: dict) -> dict | None:
    ss = state.get("secondary_structure")
    if not ss:
        return None
    db, start = ss["dot_bracket"], ss.get("start", 1)
    segs = geometry.segments_from_dot_bracket(db, start)
    pairs = [[start + i, start + j] for i, j in geometry.base_pairs(db)]
    span = geometry.structured_span(segs, ("paired",))
    derived = [_derived("n_base_pairs", len(pairs), "count", "geometry.base_pairs")]
    if span:
        n = span[1] - span[0] + 1
        derived.append(_derived("n_structured_residues", n, "count", "geometry.structured_span",
                                {"first": span[0], "last": span[1]}))
        derived.append(_released_entry(geometry.contour_length_released(n, None, mtype), "geometry.contour_length_released"))
    return {
        "conformation_id": f"CF-{state['state_id']}-ss",
        "molecule_id": acc, "state_id": state["state_id"], "basis": state["basis"], "prediction": False,
        "method": {"name": "curated secondary structure", "version": METHOD_VERSION,
                   "parameters": {"source": ss.get("source")}, "training_data_cutoff": None},
        "coverage": {"start": start, "end": start + len(db) - 1, "numbering": "molecule"},
        "representations": {
            "secondary_structure": {"scheme": "dot_bracket", "string": db, "start": start},
            "segments": segs,
            "contacts": {"kind": "base_pairs", "cutoff_nm": None, "pairs": pairs},
        },
        "derived": derived,
        "assumptions": ["The structured region is taken to span from the first to the last paired position."],
        "status": "computed", "provenance": _prov(acc),
    }


def from_model(acc: str, mtype: str, state: dict, model: dict, build_dir: Path) -> dict | None:
    path = build_dir / "models" / Path(model["file"]).name
    if not path.exists():
        return None
    entity = None
    for ev_id in model.get("constraints_used") or []:
        if ev_id.startswith("EV-PDB-"):
            entity = ev_id.rsplit("-", 1)[-1]
    try:
        trace = geometry.trace_from_structure(str(path), entity, mtype)
    except ImportError:
        return None
    if trace is None or len(trace.points) < 2:
        return None
    segs = trace.segments()
    d_ends = geometry.distance(trace.points[0], trace.points[-1]) / 10.0
    n = trace.numbers[-1] - trace.numbers[0] + 1
    rg = geometry.radius_of_gyration(trace.points) / 10.0
    atom = "Cα" if mtype == "protein" else "P or C4'"
    method = "geometry.trace_from_structure"
    rel = geometry.contour_length_released(n, d_ends, mtype)
    pdb_id = model["provenance"]["deposit_id"]
    return {
        "conformation_id": f"CF-{state['state_id']}-xyz",
        "molecule_id": acc, "state_id": state["state_id"], "basis": state["basis"], "prediction": False,
        "method": {"name": "representative structure", "version": METHOD_VERSION,
                   "parameters": {"pdb_id": pdb_id, "entity": entity, "chain": trace.chain, "atom": atom},
                   "training_data_cutoff": None},
        "coverage": {"start": trace.numbers[0], "end": trace.numbers[-1], "numbering": "author"},
        "representations": {
            "segments": segs,
            "coordinates": {"format": "mmCIF", "file": model["file"], "pdb_id": pdb_id, "model_number": 1,
                            "chains": [trace.chain], "numbering": "author"},
        },
        "derived": [
            _derived("n_residues", len(trace.numbers), "count", method),
            _derived("n_structured_residues", n, "count", method, {"first": trace.numbers[0], "last": trace.numbers[-1]}),
            _derived("end_to_end_distance_nm", round(d_ends, 2), "nm", method, {"atom": atom}),
            _derived("radius_of_gyration_nm", round(rg, 2), "nm", method, {"atom": atom}),
            _released_entry(rel, "geometry.contour_length_released"),
        ],
        "assumptions": [
            f"Every residue between the first and last traced {atom} is structured, and the force is applied "
            "at those two residues; linkers and handles outside the traced chain are not modelled.",
            "Residue numbers are the deposited author numbers, not the page's reference numbering.",
        ],
        "status": "computed", "provenance": _prov(acc),
    }


def segments_from_evidence(acc: str, evidence: list[dict]) -> list[dict]:
    out = []
    for ev in evidence:
        obs = ev["observable"]
        if ev["technique"] != "force_spectroscopy" or obs["type"] != "contour_length_increment" or obs["value"] is None:
            continue
        scale = LENGTH_UNITS_TO_NM.get((obs["unit"] or "").strip())
        if scale is None:
            continue
        unc = obs["uncertainty"] * scale if obs["uncertainty"] is not None else None
        out.append({
            "segment_id": "SG-" + ev["evidence_id"].removeprefix("EV-"),
            "molecule_id": acc, "evidence_id": ev["evidence_id"], "kind": "force_transition",
            "aggregation": "ensemble_summary", "trajectory_id": None, "index": None,
            "previous_segment": None, "next_segment": None,
            "observables": [{"quantity": "contour_length_increment",
                             "measured": {"value": round(obs["value"] * scale, 3), "unit": "nm",
                                          "uncertainty": unc}, "statistic": None}],
            "force_range_pn": None, "conditions": ev["conditions"], "provenance": ev["provenance"],
        })
    return out


def assign(acc: str, segments: list[dict], conformations: list[dict]) -> list[dict]:
    """Score every segment against every conformation's predicted ΔLc interval; keep all candidates."""
    candidates = []
    for c in conformations:
        rel = next((d for d in c["derived"] if d["quantity"] == "contour_length_released_nm"), None)
        if rel:
            lo, hi = rel["parameters"]["interval_nm"]
            candidates.append((c, lo, hi))
    out = []
    for seg in segments:
        m = seg["observables"][0]["measured"]
        threshold = max(2 * (m["uncertainty"] or 0.0), ACCEPT_MIN_NM)
        scored = []
        for c, lo, hi in candidates:
            resid = 0.0 if lo <= m["value"] <= hi else min(abs(m["value"] - lo), abs(m["value"] - hi))
            scored.append((resid, c))
        scored.sort(key=lambda t: (t[0], t[1]["conformation_id"]))
        for rank, (resid, c) in enumerate(scored, 1):
            out.append({
                "assignment_id": f"AS-{seg['segment_id'].removeprefix('SG-')}-{c['conformation_id'].removeprefix('CF-')}",
                "molecule_id": acc, "segment_id": seg["segment_id"],
                "target": {"conformation_id": c["conformation_id"], "state_id": c["state_id"], "transition": None},
                "score": {"kind": "residual_nm", "value": round(resid, 3), "n_candidates": len(scored)},
                "rank": rank, "accepted": resid <= threshold,
                "method": {"name": "contour-length interval match", "version": METHOD_VERSION,
                           "parameters": {"threshold_nm": threshold, "rule": "residual ≤ max(2σ, 2 nm)"},
                           "training_data_cutoff": None},
                "status": "computed", "provenance": _prov(acc),
            })
    return out


def build(paths, acc: str) -> dict:
    out_dir = paths.build / acc
    molecule = read_json(out_dir / "molecule.json")
    mapped = read_json(out_dir / "mapped.json")
    models = read_json(out_dir / "models.json") if (out_dir / "models.json").exists() else []
    mtype = molecule["molecule_type"]
    conformations = []
    for state in mapped["states"]:
        if mtype in ("rna", "dna"):
            c = from_secondary_structure(acc, mtype, state)
            if c:
                conformations.append(c)
        for model in models:
            if model["state_id"] == state["state_id"] and model["format"] == "mmCIF":
                c = from_model(acc, mtype, state, model, out_dir)
                if c:
                    conformations.append(c)
    segments = segments_from_evidence(acc, mapped["evidence"])
    assignments = assign(acc, segments, conformations)
    result = {"conformations": conformations, "segments": segments, "assignments": assignments}
    validators = load_validators(paths.schema)
    for kind, name in (("conformations", "conformation"), ("segments", "segment"), ("assignments", "assignment")):
        for rec in result[kind]:
            errs = check(validators[name], rec)
            if errs:
                raise ValueError(f"{acc}: invalid {name} record: {errs[0]}")
    write_json(out_dir / "conformations.json", result)
    accepted = sum(1 for a in assignments if a["accepted"] and a["rank"] == 1)
    print(f"conformations {acc}: {len(conformations)} conformations, {len(segments)} force segments, "
          f"{accepted} segments with an accepted best match")
    return result
