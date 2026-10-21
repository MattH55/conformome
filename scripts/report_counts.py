"""Print corpus counts from build/*/mapped.json. Run after make map. Does not invent numbers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"


def main() -> int:
    files = sorted(BUILD.glob("*/mapped.json"))
    if not files:
        print("report: build/*/mapped.json is missing; run make map", file=sys.stderr)
        return 1
    molecules = evidence = mapped = conflicts = 0
    single = no_evidence = 0
    by_type: dict[str, int] = {}
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        molecules += 1
        evidence += len(data.get("evidence") or [])
        mapped += sum(1 for ev in data["evidence"] if ev.get("mappings"))
        conflicts += len(data.get("conflicts") or [])
        coverage = data.get("coverage") or {}
        single += len(coverage.get("single_method_states") or [])
        no_evidence += len(coverage.get("no_evidence_states") or [])
        mol = BUILD / path.parent.name / "molecule.json"
        kind = "unknown"
        if mol.exists():
            kind = json.loads(mol.read_text(encoding="utf-8")).get("molecule_type") or "unknown"
        by_type[kind] = by_type.get(kind, 0) + 1
    print(f"molecules {molecules} " + " ".join(f"{k} {v}" for k, v in sorted(by_type.items())))
    print(f"evidence {evidence}")
    print(f"mapped {mapped}")
    print(f"conflicts {conflicts}")
    print(f"single_method_states {single}")
    print(f"no_evidence_states {no_evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
