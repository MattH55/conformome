#!/usr/bin/env python3
"""Keep every corpus number in manuscript.md equal to corpus_stats.py output.

Inline numbers carry a trailing HTML comment naming their source, e.g.

    7,694<!--n:smfs.n_records-->           integer, thousands separators
    3.5%<!--n:smfs.pct_with_dataset|pct1-->   value is already a percentage
    42.0%<!--n:smfs.fair_completeness.mean_fulltext|frac1-->   value is a fraction

Pandoc drops HTML comments in docx/PDF output, so they never reach readers.
Table 2 lives between `<!-- table2:start -->` and `<!-- table2:end -->` and is
regenerated whole.

    python -I paper/scripts/fill_numbers.py --check   # exit 1 on any drift
    python -I paper/scripts/fill_numbers.py --write   # rewrite the file in place
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from corpus_stats import TECH_LABELS  # noqa: E402

MANUSCRIPT = PAPER / "manuscript.md"
STATS = PAPER / "out" / "corpus_stats.json"
TAG = re.compile(r"(\d[\d,]*(?:\.\d+)?%?)<!--n:([\w.]+)(?:\|(\w+))?-->")


def lookup(stats: dict, path: str):
    node = stats
    for part in path.split("."):
        node = node[part]
    return node


def fmt(value, how: str | None) -> str:
    if how == "pct1":
        return f"{value:.1f}%"
    if how == "frac1":
        return f"{100 * value:.1f}%"
    if how == "frac0":
        return f"{100 * value:.0f}%"
    if how == "raw":  # years and other values that must not get thousands separators
        return str(int(value))
    if how == "f1":
        return f"{value:.1f}"
    if how in (None, "int"):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"non-integer {value} needs an explicit format")
        return f"{int(value):,}"
    raise ValueError(f"unknown format {how}")


def table2(stats: dict) -> str:
    rows = ["| Technique | Records | Checked | With linked dataset | % of records | % of checked | With raw traces |",
            "| " + "-" * 34 + " | " + " | ".join(["-" * 9 + ":"] * 6) + " |"]  # dash counts set the relative column widths in pandoc
    tot = {"records": 0, "checked": 0, "with_dataset": 0, "raw_traces": 0}
    for key, v in stats["smfs"]["by_technique"].items():
        rows.append(f"| {TECH_LABELS[key]} | {v['records']:,} | {v['checked']:,} | {v['with_dataset']:,} | "
                    f"{v['pct_with_dataset']:.1f} | {v['pct_with_dataset_of_checked']:.1f} | {v['raw_traces']:,} |")
        for k in tot:
            tot[k] += v[k]
    s = stats["smfs"]
    assert tot == {"records": s["n_records"], "checked": s["n_checked"], "with_dataset": s["n_with_dataset"],
                   "raw_traces": s["n_with_raw_traces"]}, "technique rows do not sum to the totals"
    rows.append(f"| **All records** | **{s['n_records']:,}** | **{s['n_checked']:,}** | **{s['n_with_dataset']:,}** | "
                f"**{s['pct_with_dataset']:.1f}** | **{s['pct_with_dataset_of_checked']:.1f}** | **{s['n_with_raw_traces']:,}** |")
    return "\n".join(rows)


def process(text: str, stats: dict) -> str:
    text = TAG.sub(lambda m: fmt(lookup(stats, m.group(2)), m.group(3)) + f"<!--n:{m.group(2)}" +
                   (f"|{m.group(3)}" if m.group(3) else "") + "-->", text)
    block = re.compile(r"(<!-- table2:start -->)\n*.*?\n*(<!-- table2:end -->)", re.S)
    if not block.search(text):
        raise SystemExit("table2 markers missing in manuscript.md")
    # blank lines around the table so pandoc parses it as a pipe table, not as part of the raw-HTML comment
    return block.sub(lambda m: m.group(1) + "\n\n" + table2(stats) + "\n\n" + m.group(2), text)


def main() -> int:
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    old = MANUSCRIPT.read_text(encoding="utf-8")
    n_tags = len(TAG.findall(old))
    n_marked = old.count("<!--n:")
    if n_marked != n_tags:  # a tag the regex cannot parse would silently keep its placeholder digits
        print(f"fill_numbers: {n_marked - n_tags} malformed <!--n:...--> tag(s); paths may only contain letters, digits, _ and .")
        return 1
    new = process(old, stats)
    if new == old:
        print(f"fill_numbers: OK ({n_tags} tagged numbers + Table 2 match corpus_stats)")
        return 0
    if "--write" in sys.argv:
        MANUSCRIPT.write_text(new, encoding="utf-8", newline="\n")
        print(f"fill_numbers: rewrote manuscript.md ({n_tags} tagged numbers)")
        return 0
    old_tags, new_tags = TAG.findall(old), TAG.findall(new)
    for (a, p, _), (b, _, _) in zip(old_tags, new_tags):
        if a != b:
            print(f"  DRIFT {p}: text has {a}, stats say {b}")
    print("fill_numbers: manuscript differs from corpus_stats (run with --write)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
