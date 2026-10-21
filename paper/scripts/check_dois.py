#!/usr/bin/env python3
"""Verify every DOI in references.bib against the registry and against the citation as written.

For each DOI: it must resolve (Crossref, or DataCite for 10.5281 Zenodo DOIs), the registry title must be >= 0.90
similar, the first author's family name must appear among the registry authors, and where the manuscript gives a
volume or starting page they must agree. Exits non-zero on any failure; writes out/doi_check.tsv.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "smash-bio-manuscript/1.0 (mailto:mhalma@opensourcemed.info)"}


def bib_entries() -> list[dict]:
    out = []
    for block in re.split(r"\n(?=@)", (PAPER / "references.bib").read_text(encoding="utf-8")):
        m = re.match(r"@(\w+)\{(\w+),", block.strip())
        if not m:
            continue
        fields = dict(re.findall(r"^\s*(\w+) = \{(.*)\},?$", block, re.M))
        out.append({"key": m.group(2), "type": m.group(1), **fields})
    return out


def fetch(url: str) -> dict:
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))


def norm(s: str) -> str:
    return re.sub(r"\W+", "", s.lower())


def registry(doi: str) -> dict:
    d = urllib.parse.quote(doi, safe="/()")
    if doi.startswith("10.5281/"):  # Zenodo is registered with DataCite
        a = fetch(f"https://api.datacite.org/dois/{d}")["data"]["attributes"]
        return {"title": a["titles"][0]["title"], "authors": [c.get("familyName") or c.get("name", "") for c in a["creators"]],
                "volume": None, "page": None}
    m = fetch(f"https://api.crossref.org/works/{d}")["message"]
    return {"title": (m.get("title") or [""])[0], "authors": [a.get("family", "") for a in m.get("author", [])],
            "volume": m.get("volume"), "page": m.get("page") or m.get("article-number")}


def main() -> int:
    rows, bad = [], 0
    for e in bib_entries():
        doi = e.get("doi")
        if not doi:
            rows.append((e["key"], "-", "no DOI (" + e["type"] + ")", ""))
            continue
        problems = []
        try:
            r = registry(doi)
            sim = difflib.SequenceMatcher(None, norm(r["title"]), norm(e["title"].strip("{}"))).ratio()
            if sim < 0.90:
                problems.append(f"title similarity {sim:.2f}: registry says '{r['title'][:60]}'")
            first = norm(e["author"].split(" and ")[0].split(",")[0])
            if not any(first and first in norm(a) for a in r["authors"]):
                problems.append(f"first author '{first}' not among registry authors")
            if e.get("volume") and r["volume"] and e["volume"] != r["volume"]:
                problems.append(f"volume {e['volume']} vs registry {r['volume']}")
            if e.get("pages") and r["page"]:
                if e["pages"].split("--")[0] != str(r["page"]).split("-")[0]:
                    problems.append(f"start page {e['pages']} vs registry {r['page']}")
        except Exception as exc:
            problems.append(f"does not resolve: {exc}")
        bad += bool(problems)
        rows.append((e["key"], doi, "FAIL" if problems else "ok", "; ".join(problems)))
    out = PAPER / "out" / "doi_check.tsv"
    out.write_text("key\tdoi\tstatus\tdetail\n" + "\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8")
    for r in rows:
        if r[2] not in ("ok",):
            print("  ", *r)
    print(f"check_dois: {sum(r[2] == 'ok' for r in rows)} ok, {bad} failed, "
          f"{sum(r[2].startswith('no DOI') for r in rows)} without DOI (see out/doi_check.tsv)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
