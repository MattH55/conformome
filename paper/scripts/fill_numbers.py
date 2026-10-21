#!/usr/bin/env python3
"""Keep every corpus number in manuscript.md equal to paper/out/stats.json.

A number in the manuscript carries a trailing HTML comment that names its key in stats.json:

    17,549<!--n:release.n_evidence-->       digits, with thousands separators
    Nine<!--w:release.n_sources-->          spelled out for 1-99, digits above; the capital is kept
    Nine<!-- = release.n_sources -->        the same, in the handoff's older spelling
    1KF1<!--t:g4.states.parallel.representative_pdb-->   a text value without spaces

Pandoc drops HTML comments, so readers never see them. Table 1 lives between
`<!-- table1:start -->` and `<!-- table1:end -->` and is regenerated whole.

    python -I paper/scripts/fill_numbers.py --check          # exit 1 on drift or an open number placeholder
    python -I paper/scripts/fill_numbers.py --write          # rewrite manuscript.md in place
    python -I paper/scripts/fill_numbers.py --render PATH    # write a filled copy; manuscript.md is unchanged
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
MANUSCRIPT = PAPER / "manuscript.md"
STATS = PAPER / "out" / "stats.json"

NUMBER_TAG = re.compile(r"(\d[\d,]*)<!--n:([\w.]+)-->")
WORD_TAG = re.compile(r"\b([A-Za-z]+(?:-[a-z]+)?)(?:<!--w:([\w.]+)-->|<!-- = ([\w.]+) -->)")
TEXT_TAG = re.compile(r"([^\s<>(]+)<!--t:([\w.]+)-->")
TABLE = re.compile(r"(<!-- table1:start -->\n)(.*?)(\n<!-- table1:end -->)", re.S)
OPEN_NUMBER = re.compile(r"\\\[to be filled: n[^\]]*\\\]|\\\[n\\\]|\\\[to be filled: total\\\]")

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

# Table 1: stats key -> (display name, unit of evidence, licence cell). Licence text follows the
# handoff's licence rule: only PDB, DisProt and AlphaFold DB may state a licence; the rest wait for the author.
SOURCES = {
    "pdb": ("RCSB PDB", "One item per polymer entity mapped to the molecule, including integrative and SAXS models",
            "CC0 1.0 (wwPDB archive data)"),
    "bmrb": ("BMRB", "One item per mapped entry (proteins) or per entry matching the sequence (nucleic acids)",
             "\\[to be confirmed\\]"),
    "afdb": ("AlphaFold DB", "One item per model, with mean pLDDT", "CC BY 4.0"),
    "smash": ("SMASH-BIO", "One item per extracted force result, or one item per study",
              "\\[to be confirmed\\]; not redistributed"),
    "disprot": ("DisProt", "One item per curated region with a structural term", "CC BY 4.0"),
    "mddb": ("MDDB", "One item per simulation project", "\\[to be confirmed\\]; varies by project"),
    "sasbdb": ("SASBDB", "Guinier radius of gyration with uncertainty", "\\[to be confirmed\\]"),
    "nakb": ("NAKB", "One item per PDB entry with a matching nucleic-acid chain", "\\[to be confirmed\\]"),
    "rfam": ("Rfam", "One covariance item per family hit, flagged as a prediction", "\\[to be confirmed\\]"),
    "rmdb": ("RMDB", "One reactivity profile per chemical-probing column whose construct contains the sequence",
             "\\[to be confirmed\\]"),
}


def lookup(stats: dict, path: str):
    node = stats
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(path)
        node = node[part]
    return node


def digits(value) -> str:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{value!r} is not an integer")
    return f"{value:,}"


def spell(value: int) -> str:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{value!r} is not an integer")
    if 0 <= value < 20:
        return ONES[value]
    if 20 <= value < 100:
        tens, ones = divmod(value, 10)
        return TENS[tens] + (f"-{ONES[ones]}" if ones else "")
    return f"{value:,}"


def word(value: int, old: str) -> str:
    out = spell(value)
    return out[0].upper() + out[1:] if old[:1].isupper() else out


def table1(stats: dict) -> str:
    rows = []
    for key, (name, unit, licence) in SOURCES.items():
        src = stats["sources"].get(key)
        if not src or not src["n_evidence"]:
            continue
        n_prot = src["n_proteins"]
        n_na = src["n_molecules"] - n_prot
        rows.append((src["n_molecules"], name, unit, f"{n_prot or '--'} / {n_na or '--'}", licence))
    rows.sort(key=lambda r: (-r[0], r[1]))
    rel = stats["release"]
    lines = ["**Table 1.** Sources ingested in the pilot release, ordered by the number of molecules with entries.", "",
             "| Source | Unit of evidence | Proteins / nucleic acids | Licence |",
             "|:----------------|:-------------------------------------------------|-------------:|:--------------------|"]
    lines += [f"| {name} | {unit} | {count} | {licence} |" for _, name, unit, count, licence in rows]
    lines += ["", '::: {custom-style="Table Note"}',
              f"*Proteins / nucleic acids*, number of the {rel['n_proteins']:,} pilot proteins and "
              f"{spell(rel['n_na'])} pilot nucleic acids with at least one entry from the source; --, none.",
              ":::"]
    return "\n".join(lines)


def fill(text: str, stats: dict) -> tuple[str, list[str]]:
    """The filled text, and a list of (old -> new) drifts and unknown keys."""
    problems: list[str] = []

    def number(m: re.Match) -> str:
        try:
            new = digits(lookup(stats, m.group(2)))
        except (KeyError, TypeError) as err:
            problems.append(f"n:{m.group(2)}: {err}")
            return m.group(0)
        if new != m.group(1):
            problems.append(f"n:{m.group(2)}: {m.group(1)} -> {new}")
        return f"{new}<!--n:{m.group(2)}-->"

    def spelled(m: re.Match) -> str:
        key = m.group(2) or m.group(3)
        try:
            new = word(lookup(stats, key), m.group(1))
        except (KeyError, TypeError) as err:
            problems.append(f"w:{key}: {err}")
            return m.group(0)
        if new != m.group(1):
            problems.append(f"w:{key}: {m.group(1)} -> {new}")
        return f"{new}<!--w:{key}-->"

    def textual(m: re.Match) -> str:
        try:
            new = str(lookup(stats, m.group(2)))
        except KeyError as err:
            problems.append(f"t:{m.group(2)}: {err}")
            return m.group(0)
        if " " in new:
            problems.append(f"t:{m.group(2)}: value {new!r} has spaces; use a different tag")
            return m.group(0)
        if new != m.group(1):
            problems.append(f"t:{m.group(2)}: {m.group(1)} -> {new}")
        return f"{new}<!--t:{m.group(2)}-->"

    text = NUMBER_TAG.sub(number, text)
    text = WORD_TAG.sub(spelled, text)
    text = TEXT_TAG.sub(textual, text)
    found = TABLE.search(text)
    if not found:
        problems.append("table1 markers missing")
    else:
        new_table = table1(stats)
        if found.group(2) != new_table:
            problems.append("table1: regenerated")
        text = text[:found.start(2)] + new_table + text[found.end(2):]
    return text, problems


def main(argv: list[str]) -> int:
    if not STATS.exists():
        print(f"fill_numbers: {STATS} missing; run scripts/stats.py first", file=sys.stderr)
        return 2
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    text = MANUSCRIPT.read_text(encoding="utf-8")
    filled, problems = fill(text, stats)
    unknown = [p for p in problems if ": " in p and not " -> " in p and p != "table1: regenerated"]
    if "--write" in argv:
        MANUSCRIPT.write_text(filled, encoding="utf-8", newline="\n")
        for p in problems:
            print(f"fill_numbers: {p}", file=sys.stderr)
        return 1 if unknown else 0
    if "--render" in argv:
        out = Path(argv[argv.index("--render") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(filled, encoding="utf-8", newline="\n")
        for p in unknown:
            print(f"fill_numbers: {p}", file=sys.stderr)
        return 1 if unknown else 0
    # --check (default)
    errors = list(problems)
    errors += [f"open number placeholder: {m.group(0)}" for m in OPEN_NUMBER.finditer(text)]
    for e in errors:
        print(f"fill_numbers --check: {e}", file=sys.stderr)
    if errors:
        return 1
    n_tags = len(NUMBER_TAG.findall(text)) + len(WORD_TAG.findall(text)) + len(TEXT_TAG.findall(text))
    print(f"fill_numbers --check: {n_tags} tags and Table 1 agree with {STATS.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
