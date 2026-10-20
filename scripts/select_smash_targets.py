#!/usr/bin/env python3
"""Select the next protein batch from the SMASH-BIO release, by a stated rule.

Rule (batch multi-source-2): UniProt accessions that SMASH-BIO marks as *verified* on an entity in at least
MIN_RECORDS records, and that targets.yaml does not already list. Unverified identifiers are ignored: in the
release they include gazetteer misassignments (plant and non-human orthologs named after human proteins).

Usage:
    python -I scripts/select_smash_targets.py RELEASE.jsonl.gz            # print the candidates
    python -I scripts/select_smash_targets.py RELEASE.jsonl.gz --append   # append them to targets.yaml

The names written are SMASH-BIO entity labels; page titles come from UniProt, not from these labels.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TARGETS = REPO / "targets.yaml"
BATCH = "multi-source-2"
MIN_RECORDS = 8


def main() -> int:
    release = Path(sys.argv[1])
    data = release.read_bytes()
    records = [json.loads(line) for line in gzip.decompress(data).decode("utf-8").split("\n") if line.strip()]
    listed = {t.get("uniprot") for t in yaml.safe_load(TARGETS.read_text(encoding="utf-8"))["targets"]}

    counts: collections.Counter[str] = collections.Counter()
    label: dict[str, str] = {}
    for rec in records:
        seen = set()
        for ent in (rec.get("biological_system") or {}).get("entities") or []:
            for ident in ent.get("identifiers") or []:
                acc = ident.get("id")
                if ident.get("scheme") == "uniprot" and ident.get("verified") and acc not in seen:
                    seen.add(acc)
                    counts[acc] += 1
                    label.setdefault(acc, ent.get("name") or acc)
    picked = [(acc, n) for acc, n in counts.most_common() if n >= MIN_RECORDS and acc not in listed]
    print(f"release sha256 {hashlib.sha256(data).hexdigest()}, {len(records)} records; {len(picked)} new accessions")
    for acc, n in picked:
        print(f"{acc}\t{n}\t{label[acc]}")
    if "--append" in sys.argv:
        lines = [f'  - {{uniprot: {acc}, batch: {BATCH}, name: {json.dumps(label[acc], ensure_ascii=False)}}}' for acc, _ in picked]
        text = TARGETS.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(lines) + "\n"
        TARGETS.write_text(text, encoding="utf-8")
        print(f"appended {len(lines)} entries to targets.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
