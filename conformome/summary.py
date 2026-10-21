"""Markdown summary of a build: one row per molecule, from build/<id>/molecule.json, mapped.json and ingest.json.

    python -m conformome.summary            # every molecule in targets.yaml
"""

from __future__ import annotations

from conformome.common import Paths, default_paths, read_json
from conformome.pipeline import target_accessions


def rows(paths: Paths, accessions: list[str]) -> list[str]:
    out = ["| Molecule | Type | Name | Evidence | By source | States | Mapped | Ambiguous | Conflicts |",
           "|---|---|---|---|---|---|---|---|---|"]
    missing = []
    totals = {"evidence": 0, "mapped": 0}
    for acc in accessions:
        out_dir = paths.build / acc
        if not (out_dir / "mapped.json").exists():
            missing.append(acc)
            continue
        mol = read_json(out_dir / "molecule.json")
        mapped = read_json(out_dir / "mapped.json")
        ingest = read_json(out_dir / "ingest.json")
        n = len(mapped["evidence"])
        n_mapped = sum(1 for ev in mapped["evidence"] if ev["mappings"])
        totals["evidence"] += n
        totals["mapped"] += n_mapped
        by_source = ", ".join(f"{k} {v['evidence_items']}" for k, v in ingest["sources"].items() if v["evidence_items"])
        out.append(f"| {acc} | {mol['molecule_type']} | {mol['name']} | {n} | {by_source} | {len(mapped['states'])} "
                   f"| {n_mapped} | {len(mapped['ambiguous'])} | {len(mapped['conflicts'])} |")
    head = [f"## Build summary: {len(accessions) - len(missing)} molecules, {totals['evidence']} evidence items, "
            f"{totals['mapped']} mapped", ""]
    tail = ["", f"Not built: {', '.join(missing)}"] if missing else []
    return head + out + tail


def main() -> None:
    paths = default_paths()
    print("\n".join(rows(paths, target_accessions(paths))))


if __name__ == "__main__":
    main()
