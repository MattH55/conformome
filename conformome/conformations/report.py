"""Aggregate summary of build/<id>/conformations.json and predictions.json (numbers only, no source records).

    python -m conformome.conformations.report > conformations-summary.md
"""
from __future__ import annotations

import statistics

from conformome.common import default_paths, read_json
from conformome.pipeline import target_accessions


def main() -> None:
    paths = default_paths()
    rows, matches = [], []
    totals = {"conformations": 0, "segments": 0, "accepted": 0, "molecules_with_segments": 0}
    for acc in target_accessions(paths):
        f = paths.build / acc / "conformations.json"
        if not f.exists():
            continue
        data = read_json(f)
        confs, segs, asg = data["conformations"], data["segments"], data["assignments"]
        best = {a["segment_id"]: a for a in asg if a["rank"] == 1}
        accepted = [a for a in best.values() if a["accepted"]]
        totals["conformations"] += len(confs)
        totals["segments"] += len(segs)
        totals["accepted"] += len(accepted)
        totals["molecules_with_segments"] += bool(segs)
        released = {c["conformation_id"]: next((d["value"] for d in c["derived"]
                                                if d["quantity"] == "contour_length_released_nm"), None) for c in confs}
        kinds = {"ss": sum(c["conformation_id"].endswith("-ss") for c in confs),
                 "xyz": sum(c["conformation_id"].endswith("-xyz") for c in confs)}
        line = f"| {acc} | {kinds['ss']} | {kinds['xyz']} | {len(segs)} | {len(accepted)} |"
        pred = paths.build / acc / "predictions.json"
        if pred.exists():
            p = read_json(pred)
            f1 = max((e["value"] for e in p["evaluations"]), default=None)
            mids = p["equilibrium_curve"].get("unfold_midpoint_pn", {})
            line += f" {len(p['conformations'])} predicted; best bp-F1 {f1}; equilibrium midpoints " + \
                    ", ".join(f"{k} {v:.1f} pN" for k, v in sorted(mids.items())) + " |"
        else:
            line += " |"
        rows.append(line)
        for cid, val in released.items():
            if val is None:
                continue
            measured = [s["observables"][0]["measured"]["value"] for s in segs
                        if best.get(s["segment_id"], {}).get("target", {}).get("conformation_id") == cid
                        and best[s["segment_id"]]["accepted"]]
            if measured:
                matches.append((acc, cid, val, len(measured), statistics.median(measured)))
    print(f"## Conformations: {totals['conformations']} conformations, {totals['segments']} force segments on "
          f"{totals['molecules_with_segments']} molecules, {totals['accepted']} segments whose best match is accepted\n")
    print("| Molecule | from dot-bracket | from coordinates | force segments | accepted | predictions |")
    print("|---|---|---|---|---|---|")
    print("\n".join(rows))
    print("\n## Predicted contour length released on complete unfolding, per conformation\n")
    print("| Conformation | ΔLc (nm) | interval (nm) | structured residues | end-to-end (nm) |")
    print("|---|---|---|---|---|")
    for acc in target_accessions(paths):
        f = paths.build / acc / "conformations.json"
        if not f.exists():
            continue
        for c in read_json(f)["conformations"]:
            d = {x["quantity"]: x for x in c["derived"]}
            rel = d.get("contour_length_released_nm")
            if rel:
                lo, hi = rel["parameters"]["interval_nm"]
                e2e = d.get("end_to_end_distance_nm", {}).get("value")
                print(f"| {c['conformation_id']} | {rel['value']:.1f} | {lo:.1f}–{hi:.1f} | "
                      f"{rel['parameters']['n_structured']} | {e2e if e2e is not None else 'n/a'} |")
    print("\n## Predicted vs measured contour length released (accepted best matches)\n")
    print("| Molecule | Conformation | predicted ΔLc (nm) | n segments | median measured (nm) |")
    print("|---|---|---|---|---|")
    for acc, cid, val, n, med in sorted(matches, key=lambda t: -t[3]):
        print(f"| {acc} | {cid} | {val:.1f} | {n} | {med:.1f} |")


if __name__ == "__main__":
    main()
