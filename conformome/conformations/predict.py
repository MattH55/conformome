"""Forward predictions from sequence: equilibrium structures under force, as prediction_run, conformation and
evaluation records, plus the predicted equilibrium pulling curve.

For each RNA molecule (DNA is supported by thermo/kinetics but not run here by default, because the pilot DNA is
a G-quadruplex, which the secondary-structure model used here does not represent):

  * a prediction_run records ViennaRNA's version, the parameters and the sequence hash;
  * predicted conformations: the MFE, any alternative local minimum within 3 kcal/mol, and the open chain, each
    with its folding free energy and the contour length it releases on unfolding (from its exterior loop);
  * the equilibrium occupancy of each predicted conformation and of each curated secondary structure from 0 to
    40 pN, and the mean extension: what an infinitely slow pulling experiment would show;
  * evaluations: base-pair F1 of each predicted conformation against each curated observed secondary structure.

All records are predictions (prediction: true, basis: inferred) and list the model's assumptions.
"""
from __future__ import annotations

import hashlib

from conformome.common import check, load_validators, read_json, today, write_json
from conformome.conformations import geometry
from conformome.conformations.thermo import ForceModel, bp_distance, exterior_loop, midpoint_force, _pair_table

FORCES = [round(0.25 * i, 2) for i in range(0, 161)]
FULL_ENSEMBLE_MAX_NT = 36  # longer sequences use a truncated window plus unzipping paths
WINDOW_KCAL = 5.0
ALT_WINDOW_KCAL = 3.0
ASSUMPTIONS = [
    "Nearest-neighbour secondary-structure energies only; tertiary contacts, pseudoknots and ligand binding are not modelled.",
    "Force acts on the 5' and 3' ends; unpaired exterior nucleotides stretch as a worm-like chain and each exterior helix as a rigid 2 nm rod.",
    "Occupancies are equilibrium values; real pulling at finite loading rate departs from them (see kinetics).",
    "Curated references are compared on their nested base pairs only; pseudoknot and kissing-loop pairs are dropped.",
    "For sequences longer than 36 nt the ensemble is truncated to 5 kcal/mol above the MFE plus the unzipping paths of the reference structures, which under-counts partly folded alternatives.",
]


def _prov(acc: str) -> dict:
    return {"source": "Conformome (computed)", "doi": None, "deposit_id": acc, "retrieved": today(),
            "url": "https://conformome.org", "licence": "CC BY 4.0"}


def base_pair_f1(pred: str, ref: str) -> float:
    pp = {(i, j) for i, j in enumerate(_pair_table(pred)) if j > i}
    pr = {(i, j) for i, j in enumerate(_pair_table(ref)) if j > i}
    if not pp and not pr:
        return 1.0
    tp = len(pp & pr)
    return 0.0 if tp == 0 else 2 * tp / (len(pp) + len(pr))


def local_minima(model: ForceModel, window_kcal: float) -> list[tuple[str, float]]:
    """Structures within window of the MFE that no single base-pair move can lower (at zero force)."""
    import RNA

    out = []
    for s, e in model.ensemble(delta_kcal=window_kcal):
        pt = RNA.ptable(s)
        if all(model.fc.eval_move_pt(pt, m.pos_5, m.pos_3) >= 0 for m in model.fc.neighbors(pt)):
            out.append((s, e))
    return out


def predict(paths, acc: str) -> dict | None:
    import RNA

    out_dir = paths.build / acc
    molecule = read_json(out_dir / "molecule.json")
    if molecule["molecule_type"] != "rna" or not molecule.get("sequence"):
        return None
    full_seq = molecule["sequence"].upper().replace("T", "U")
    mapped = read_json(out_dir / "mapped.json")
    # Curated secondary structures may cover only the construct studied (e.g. an aptamer within a longer RNA).
    # Predict on the region the curated structures cover, so that predictions and references are comparable.
    # Pseudoknot and kissing-loop brackets ([] {} <> Aa) are not in the nested model; references keep nested pairs.
    curated, region = {}, (1, len(full_seq))
    for st in mapped["states"]:
        ss = st.get("secondary_structure")
        if not ss:
            continue
        start, db = ss.get("start", 1), ss["dot_bracket"]
        nested = "".join(ch if ch in "()." else "." for ch in db)
        curated[st["state_id"]] = (start, nested)
    windows = {(start, start + len(db) - 1) for start, db in curated.values()}
    if len(windows) == 1:  # every curated structure covers the same window: predict on it
        region = windows.pop()
    seq = full_seq[region[0] - 1:region[1]]
    curated = {k: db for k, (start, db) in curated.items() if start == region[0] and len(db) == len(seq)}
    model = ForceModel(seq, "rna", temperature_c=25.0, salt_m=0.15)
    version = RNA.__version__
    run_id = f"PR-{acc}-vienna{version.replace('.', '')}-eq"
    method = {"name": "ViennaRNA equilibrium force model", "version": version,
              "parameters": model.parameters(), "training_data_cutoff": None}

    minima = local_minima(model, ALT_WINDOW_KCAL)[:6]
    open_chain = "." * len(seq)
    predicted = {f"min{i + 1}": s for i, (s, _) in enumerate(minima)}
    predicted["open"] = open_chain
    refs = {**{f"pred:{k}": v for k, v in predicted.items()}, **{f"curated:{k}": v for k, v in curated.items()}}
    full = len(seq) <= FULL_ENSEMBLE_MAX_NT
    curve = model.macrostate_curve(refs, FORCES, delta_kcal=None if full else WINDOW_KCAL, unzipping_paths=not full)
    if not full:
        curve["parameters"]["ensemble"] = (f"suboptimal structures within {WINDOW_KCAL} kcal/mol of the MFE, the open "
                                           "chain, and every structure on the unzipping path of each reference")

    conformations = []
    for name, s in predicted.items():
        energy = model.energy_kcal(s)
        n_un, n_hel = exterior_loop(s)
        pairs = [[i + 1, j + 1] for i, j in enumerate(_pair_table(s)) if j > i]  # region-relative
        span = geometry.structured_span(geometry.segments_from_dot_bracket(s), ("paired",)) if pairs else None
        derived = [{"quantity": "n_base_pairs", "value": len(pairs), "unit": "count", "method": "dot-bracket",
                    "parameters": {}, "assumptions": []}]
        if span:
            rel = geometry.contour_length_released(span[1] - span[0] + 1, None, "rna")
            derived.append({"quantity": "contour_length_released_nm", "value": rel.value, "unit": "nm",
                            "method": "geometry.contour_length_released",
                            "parameters": dict(rel.parameters, interval_nm=[rel.low, rel.high]),
                            "assumptions": rel.assumptions})
        conformations.append({
            "conformation_id": f"CF-{acc}-vienna-{name}", "molecule_id": acc, "state_id": None,
            "basis": "inferred", "prediction": True,
            "method": dict(method, parameters=dict(method["parameters"], folding_free_energy_kcal=round(energy, 2),
                                                    exterior_unpaired=n_un, exterior_helices=n_hel)),
            "coverage": {"start": region[0], "end": region[1], "numbering": "molecule"},
            "representations": {"secondary_structure": {"scheme": "dot_bracket", "string": s, "start": region[0]},
                                "segments": geometry.segments_from_dot_bracket(s, region[0]),
                                "contacts": {"kind": "base_pairs", "cutoff_nm": None,
                                             "pairs": [[i + region[0] - 1, j + region[0] - 1] for i, j in pairs]}},
            "derived": derived, "assumptions": ASSUMPTIONS, "status": "computed", "provenance": _prov(acc),
        })
    run = {"run_id": run_id, "molecule_id": acc, "method": method,
           "inputs": {"sequence_sha256": hashlib.sha256(seq.encode()).hexdigest(), "msa": None, "templates": False,
                      "seeds": []},
           "conformation_ids": [c["conformation_id"] for c in conformations], "provenance": _prov(acc)}
    evaluations = []
    for state_id, ref in curated.items():
        for c in conformations:
            pred_db = c["representations"]["secondary_structure"]["string"]
            evaluations.append({
                "evaluation_id": f"EVL-{c['conformation_id'].removeprefix('CF-')}-{state_id}", "run_id": run_id,
                "molecule_id": acc, "reference": {"state_id": state_id, "conformation_id": f"CF-{state_id}-ss",
                                                  "deposited": None},
                "metric": "base_pair_f1", "value": round(base_pair_f1(pred_db, ref), 3), "best_of_n": None,
                "held_out": None, "provenance": _prov(acc)})
    midpoints = {name: midpoint_force(FORCES, [1 - x for x in occ]) for name, occ in curve["occupancy"].items()
                 if name != "pred:open"}
    result = {"prediction_runs": [run], "conformations": conformations, "evaluations": evaluations,
              "equilibrium_curve": {**curve, "references": refs,
                                    "unfold_midpoint_pn": {k: v for k, v in midpoints.items() if v is not None}}}
    validators = load_validators(paths.schema)
    for kind, name in (("prediction_runs", "prediction_run"), ("conformations", "conformation"), ("evaluations", "evaluation")):
        for rec in result[kind]:
            errs = check(validators[name], rec)
            if errs:
                raise ValueError(f"{acc}: invalid {name}: {errs[0]}")
    write_json(out_dir / "predictions.json", result)
    best = max((e["value"] for e in evaluations), default=None)
    print(f"predict {acc}: {len(conformations)} predicted conformations, {curve['n_structures']} structures; "
          f"best base-pair F1 vs curated {best}")
    return result
