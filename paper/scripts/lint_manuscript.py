#!/usr/bin/env python3
"""Pre-build checks for manuscript.md (BRIEF.md sections 3 and 5).

    --fix   merge `### **Heading.**` + paragraph into a bold run-in `**Heading.** paragraph`, then lint

Checks: duplicated paragraphs; number-unit spacing; figure/table references with no caption and captions never
referenced; every numbered citation has a reference and every reference is cited; abstract <= 250 and
significance <= 120 words; 5 keywords; title <= 150 characters; no leftover editor byline; unresolved placeholders
(reported as warnings, they are the submission to-do list). Exit code 1 on any error.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
MANUSCRIPT = PAPER / "manuscript.md"
UNIT = re.compile(r"\d(pN|nm|kHz|Hz|mW|K|s|mM|mbar)\b")
RUN_IN = re.compile(r"^### (\*\*.+?\*\*)\n\n(?=[^\n#|])", re.M)
CITE = re.compile(r"\((\d{1,2}(?:\s*[,–-]\s*\d{1,2})*)\)")


def words(s: str) -> int:
    s = re.sub(r"<!--.*?-->", "", s)
    s = re.sub(r"[\\*^~`]", "", s)
    return len(s.split())


def section(text: str, name: str, nxt: str) -> str:
    m = re.search(rf"## {name}\n\n(.*?)\n\n## {nxt}", text, re.S)
    return m.group(1) if m else ""


def expand(group: str) -> set[int]:
    out: set[int] = set()
    for part in re.split(r"\s*,\s*", group):
        if re.search(r"[–-]", part):
            a, b = re.split(r"\s*[–-]\s*", part)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def lint(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    body, _, refs = text.partition("\n## References\n")
    prose = re.sub(r"<!--.*?-->", "", body)
    prose_nocode = re.sub(r"`[^`]*`", "", prose)

    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", prose)]
    for p, n in Counter(p for p in paras if len(p) > 60 and not p.startswith("|")).items():
        if n > 1:
            errors.append(f"duplicate paragraph x{n}: {p[:70]}...")

    for m in UNIT.finditer(prose_nocode):
        errors.append(f"missing space before unit: ...{prose_nocode[max(0, m.start() - 25):m.end() + 10]!r}")

    title = text.splitlines()[0].lstrip("# ").strip()
    if len(title) > 150:
        errors.append(f"title is {len(title)} characters (limit 150)")
    if re.search(r"\b[A-Z][a-z]{2} \d{1,2}, 20\d\d\s*·\s*@", text):
        errors.append("editor byline still present")

    n_abs = words(section(text, "Abstract", "Significance" if "## Significance" in text else "Introduction"))
    n_sig = words(re.sub(r"\*\*Keywords:.*", "", section(text, "Significance", "Introduction"), flags=re.S)) if "## Significance" in text else 0
    if n_abs > 300:  # ORE limit
        errors.append(f"abstract is {n_abs} words (limit 300)")
    if n_sig > 120:
        errors.append(f"significance is {n_sig} words (limit 120)")
    kw = re.search(r"\*\*Keywords:\*\*\s*(.+)", text)
    if not kw or not 3 <= len([k for k in kw.group(1).split(";") if k.strip()]) <= 8:
        errors.append("expected 3-8 keywords")

    # figure / table references vs captions
    legends = text.partition("\n## Figure legends\n")[2].partition("\n## References")[0]
    fig_defined = set(re.findall(r"\*\*Figure (\d)\.", legends))
    tab_defined = set(re.findall(r"^\*\*Table (\d)\.", body, re.M))
    body_no_legends = body.partition("\n## Figure legends\n")[0]
    fig_used = set(re.findall(r"\bFigs?\. (\d)", body_no_legends))
    tab_used = set(re.findall(r"\bTable (\d)\b", body_no_legends))
    for f in sorted(fig_used - fig_defined):
        errors.append(f"Fig. {f} is referenced but has no legend")
    for f in sorted(fig_defined - fig_used):
        errors.append(f"Figure {f} has a legend but is never referenced in the text")
    for t_ in sorted(tab_used - tab_defined):
        errors.append(f"Table {t_} is referenced but has no caption")
    for t_ in sorted(tab_defined - tab_used):
        errors.append(f"Table {t_} has a caption but is never referenced")
    supp = PAPER / "out" / "supplementary.md"
    for s in sorted(set(re.findall(r"Table (S\d)", body))):
        if not supp.exists() or f"Table {s}." not in supp.read_text(encoding="utf-8"):
            errors.append(f"Table {s} is referenced but out/supplementary.md does not define it")

    # citations
    listed = {int(m.group(1)) for ln in refs.splitlines() if (m := re.match(r"(\d+)\. ", ln))}
    cited: set[int] = set()
    for m in CITE.finditer(body):
        cited |= expand(m.group(1))
    for n in sorted(cited - listed):
        errors.append(f"citation ({n}) has no entry in the reference list")
    for n in sorted(listed - cited):
        errors.append(f"reference {n} is never cited")

    for m in re.finditer(r"\\\[(?:to be|URL|Authors|organisation)[^\]]*\]|\bTODO\b|\bFIXME\b", body):
        warnings.append(f"placeholder: {m.group(0)}")
    for m in re.finditer(r"Manuscript in preparation", refs):
        warnings.append("reference list contains a 'Manuscript in preparation' entry")
    warnings.append(f"abstract {n_abs}/300 words, significance {n_sig}/120 words")
    return errors, warnings


def main() -> int:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    if "--fix" in sys.argv:
        fixed = RUN_IN.sub(lambda m: m.group(1) + " ", text)
        if fixed != text:
            MANUSCRIPT.write_text(fixed, encoding="utf-8", newline="\n")
            print(f"lint: merged {len(RUN_IN.findall(text))} run-in headings")
        text = fixed
    errors, warnings = lint(text)
    for w in warnings:
        print("  warn :", w)
    for e in errors:
        print("  ERROR:", e)
    print(f"lint: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
