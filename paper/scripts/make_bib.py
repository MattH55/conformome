#!/usr/bin/env python3
"""Reference tooling for manuscript.md (BRIEF.md section 5, step 1).

manuscript.md keeps its human-readable numbered citations `(n)`, `(n,m)`, `(n–m)` and numbered reference list.

    --renumber   renumber citations and the list in order of first appearance (rewrites manuscript.md)
    (default)    write references.bib (DOIs looked up on Crossref and cached) and out/manuscript.pandoc.md,
                 where citations are `[@refNN]` and the numbered list is replaced by pandoc's bibliography,
                 so the Cell Press CSL renumbers automatically.

A DOI is accepted from Crossref only if the title is >= 0.90 similar and the year matches; anything else is left
without a DOI and reported, never guessed.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
MANUSCRIPT = PAPER / "manuscript.md"
CACHE = PAPER / "data" / "crossref_cache.json"
UA = {"User-Agent": "smash-bio-manuscript/1.0 (mailto:mhalma@opensourcemed.info)"}
CITE = re.compile(r"\((\d{1,2}(?:\s*[,–-]\s*\d{1,2})*)\)")
REF_HEAD = "## References"


def split_manuscript(text: str) -> tuple[str, list[str]]:
    body, _, refs = text.partition("\n" + REF_HEAD + "\n")
    if not refs:
        raise SystemExit("no '## References' section")
    lines = [ln for ln in refs.splitlines() if ln.strip()]
    return body, lines


def expand(group: str) -> list[int]:
    out: list[int] = []
    for part in re.split(r"\s*,\s*", group):
        if re.search(r"[–-]", part):
            a, b = re.split(r"\s*[–-]\s*", part)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def compress(nums: list[int]) -> str:
    nums = sorted(set(nums))
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append(f"{nums[i]}–{nums[j]}")
        else:
            parts.extend(str(x) for x in nums[i:j + 1])
        i = j + 1
    return ",".join(parts)


PROTECT_TITLE = ["von Willebrand", "DNA", "RNA", "B-DNA", "AFM", "FAIR", "SMASH-BIO", "MechanoProDB", "PseudoBase", "FSDB",
                 "STRENDA DB", "POTATO", "Pylake", "Europe PMC", "GroEL", "Bell", "ISRIB", "T7"]
PARTICLES = ("del ", "van ", "von ", "de ", "da ")


def protect(title: str) -> str:
    for w in PROTECT_TITLE:
        title = re.sub(r"(?<![{\w])" + re.escape(w) + r"(?![}\w])", "{" + w + "}", title)
    return title


def brace_particle(author: str) -> str:
    fam, _, given = author.partition(",")
    fam = fam.strip()
    return ("{" + fam + "}," + given) if fam.lower().startswith(PARTICLES) else author


def renumber(text: str) -> str:
    body, ref_lines = split_manuscript(text)
    refs = {int(m.group(1)): ln for ln in ref_lines if (m := re.match(r"(\d+)\. ", ln))}
    first: list[int] = []
    for m in CITE.finditer(body):
        for n in expand(m.group(1)):
            if n in refs and n not in first:
                first.append(n)
    unused = sorted(set(refs) - set(first))
    if unused:
        print(f"warning: references never cited: {unused}", file=sys.stderr)
    order = first + unused
    mapping = {old: new for new, old in enumerate(order, 1)}
    body = CITE.sub(lambda m: "(" + compress([mapping[n] for n in expand(m.group(1)) if n in mapping]) + ")", body)
    new_refs = [re.sub(r"^\d+\. ", f"{mapping[old]}. ", refs[old]) for old in order]
    return body + "\n" + REF_HEAD + "\n\n" + "\n".join(new_refs) + "\n"


# ---- bibliography ------------------------------------------------------------------------------------
INITIALS = re.compile(r"^[A-Z]\.(?:-[A-Z]\.)?$")


def parse_authors(s: str) -> list[str]:
    s = s.strip()
    others = s.endswith("et al")
    s = re.sub(r",?\s*et al\.?$", "", s)
    m = re.match(r"^([^,]+), ((?:[A-Z]\.(?:-[A-Z]\.)?\s?)+)(.*)$", s)
    if not m:
        return [s]
    names = [f"{m.group(1)}, {m.group(2).strip()}"]
    rest = m.group(3).strip(" ,")
    for part in filter(None, (p.strip() for p in re.split(r",\s+(?:and\s+)?|\s+and\s+", rest))):
        toks = part.split()
        k = 0
        while k < len(toks) and INITIALS.match(toks[k]):
            k += 1
        names.append(f"{' '.join(toks[k:])}, {' '.join(toks[:k])}" if 0 < k < len(toks) else part)
    if others:
        names.append("others")
    return names


def parse_ref(line: str) -> dict:
    m = re.match(r"^(\d+)\. (.+?)\.? (\d{4})\. (.+)$", line)
    if not m:  # no year: unpublished manuscript
        m2 = re.match(r"^(\d+)\. ([^,]+, (?:[A-Z]\. ?)+)(.+?)\.? (Manuscript in preparation)\.$", line)
        num, au, title, note = m2.groups()
        return {"n": int(num), "type": "unpublished", "author": parse_authors(au), "title": title.strip(" ."),
                "note": note}
    num, au, year, rest = m.groups()
    ref = {"n": int(num), "type": "article", "author": parse_authors(au), "year": year}
    j = re.match(r"^(.+?)\. \*(.+?)\*(?: \((Oxford)\))?\s*(?:(\S+?)\.?)?$", rest)
    if j:
        title, journal, oxford, volpages = j.groups()
        ref.update(title=title, journal=journal + (" (Oxford)" if oxford else ""))
        if volpages and re.match(r"^[\w.]+:[\w–-]+$", volpages):
            vol, pages = volpages.split(":", 1)
            ref.update(volume=vol, pages=pages)
        elif volpages:
            ref["note"] = volpages
    else:  # software/dataset record, e.g. Zenodo
        title, _, tail = rest.partition(". ")
        ref.update(type="misc", title=title, note=tail.rstrip("."))
        doi = re.search(r"https://doi\.org/(\S+?)\.?$", tail)
        if doi:
            ref["doi"] = doi.group(1)
    return ref


def crossref_doi(ref: dict, cache: dict) -> str | None:
    if ref.get("doi") or ref["type"] == "unpublished":
        return ref.get("doi")
    key = str(ref["n"]) + "|" + ref["title"]
    if key not in cache:
        q = urllib.parse.urlencode({"query.bibliographic": f"{ref['title']} {ref['author'][0].split(',')[0]} {ref['year']}",
                                    "rows": 3, "select": "DOI,title,issued,published-print,published-online,volume"})
        try:
            items = json.load(urllib.request.urlopen(urllib.request.Request(
                "https://api.crossref.org/works?" + q, headers=UA), timeout=30))["message"]["items"]
        except Exception as exc:  # network or API failure: leave undecided, do not cache
            print(f"  crossref lookup failed for ref {ref['n']}: {exc}", file=sys.stderr)
            return None
        best = None
        for it in items:
            title = (it.get("title") or [""])[0]
            sim = difflib.SequenceMatcher(None, re.sub(r"\W+", "", title.lower()),
                                          re.sub(r"\W+", "", ref["title"].lower())).ratio()
            years = {str((it.get(k, {}).get("date-parts") or [[None]])[0][0])
                     for k in ("issued", "published-print", "published-online")}
            vol_ok = not ref.get("volume") or it.get("volume") == ref["volume"]  # rejects same-titled conference abstracts
            if sim >= 0.90 and ref["year"] in years and vol_ok and (best is None or sim > best[0]):
                best = (sim, it["DOI"])
        cache[key] = best[1] if best else None
        time.sleep(0.2)
    return cache[key]


STOP = set("a an the of and or for in on at to by with from into its is are as vs via under between".split())


def bbt_key(ref: dict) -> str:
    """Better BibTeX default pattern: auth.lower + shorttitle(3,3) + year (ASCII-folded, no particles)."""
    import unicodedata
    fam = ref["author"][0].split(",")[0].strip("{} ")
    fam = fam.split()[-1] if fam.lower().startswith(("del ", "van ", "von ", "de ", "da ")) else fam.replace(" ", "")
    fold = lambda x: "".join(c for c in unicodedata.normalize("NFKD", x) if c.isascii() and c.isalnum())
    words = [w for w in re.sub(r"[^\w\s-]", " ", ref["title"]).split() if w.lower() not in STOP]
    short = "".join(w[:1].upper() + w[1:] for w in words[:3])
    return fold(fam.lower()) + fold(short) + str(ref.get("year", ""))


KEYS: dict[int, str] = {}


def to_bibtex(ref: dict) -> str:
    key = KEYS[ref["n"]]
    fields = {"author": " and ".join(brace_particle(a) for a in ref["author"]), "title": "{" + protect(ref["title"]) + "}"}
    for f in ("year", "journal", "volume", "pages", "doi", "note"):
        if ref.get(f):
            fields[f] = ref[f].replace("–", "--") if f == "pages" else ref[f]
    body = ",\n".join(f"  {k} = {{{v}}}" if k != "title" else f"  title = {v}" for k, v in fields.items())
    return f"@{ref['type']}{{{key},\n{body}\n}}\n"


def pandoc_version(text: str) -> str:
    body, _ = split_manuscript(text)

    def repl(m: re.Match) -> str:
        return "[" + "; ".join("@" + KEYS[n] for n in expand(m.group(1))) + "]"

    body = CITE.sub(repl, body)
    body = re.sub(r" (\[@)", r"\1", body)  # superscript citations abut the preceding word (Vancouver)
    title, _, body = body.partition("\n")  # first line is "# Title": move it to pandoc metadata
    title = title.lstrip("# ").strip().replace('"', '\\"')
    body = f'---\ntitle: "{title}"\n---\n' + body
    return body + "\n" + REF_HEAD + "\n\n::: {#refs}\n:::\n"


def main() -> int:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    if "--check" in sys.argv:  # every [@key] cited in out/manuscript.pandoc.md must exist in references.bib
        bib = set(re.findall(r"^@\w+\{([^,]+),", (PAPER / "references.bib").read_text(encoding="utf-8"), re.M))
        md = (PAPER / "out" / "manuscript.pandoc.md").read_text(encoding="utf-8")
        cited = {k for grp in re.findall(r"\[@([A-Za-z0-9_:-]+)|; @([A-Za-z0-9_:-]+)", md) for k in grp if k}
        missing = sorted(cited - bib)
        print(f"make_bib --check: {len(cited)} keys cited, {len(bib)} in references.bib, missing {missing or 'none'}")
        return 1 if missing else 0
    if "--renumber" in sys.argv:
        new = renumber(text)
        if new != text:
            MANUSCRIPT.write_text(new, encoding="utf-8", newline="\n")
        print("make_bib: citations renumbered in order of first appearance" if new != text else "make_bib: numbering already in order")
        return 0
    _, ref_lines = split_manuscript(text)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    refs = [parse_ref(ln) for ln in ref_lines]
    missing = []
    for r in refs:
        if not r.get("doi"):
            r["doi"] = crossref_doi(r, cache)
        if not r.get("doi") and r["type"] != "unpublished":
            missing.append(r["n"])
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    seen: dict[str, int] = {}
    for r in refs:  # unique keys: BBT appends a, b, ... on collision
        k = bbt_key(r)
        if k in seen:
            seen[k] += 1
            k += "abcdefgh"[seen[k] - 1]
        else:
            seen[k] = 1
        KEYS[r["n"]] = k
    (PAPER / "references.bib").write_text("\n".join(to_bibtex(r) for r in refs), encoding="utf-8")
    (PAPER / "out").mkdir(exist_ok=True)
    (PAPER / "out" / "manuscript.pandoc.md").write_text(pandoc_version(text), encoding="utf-8")
    print(f"make_bib: {len(refs)} references -> references.bib; DOI missing for refs {missing or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
