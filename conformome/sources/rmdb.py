"""RMDB, the RNA Mapping Database: chemical-probing reactivity profiles (SHAPE, DMS and others).

RMDB is a static site (rmdb.stanford.edu, built from DasLab/rmdb.github.io). Its manifest lists every
entry; each entry's RDAT file is a GitHub release asset whose address is on the entry's detail page.
Database content is CC0 1.0 (rmdb.stanford.edu/about/).

fetch: the manifest (once), then the RDAT of every entry with at most MAX_CONSTRUCTS constructs and a
       sequence at least as long as the molecule. An entry matches when one of its construct
       sequences contains the molecule's sequence exactly (T read as U), so flanking primers and
       hairpin cassettes are allowed. Larger libraries are listed as not scanned. The matching RDATs
       are kept in data/raw/rmdb/<molecule_id>.json.
parse: one evidence item per reactivity column of a matching construct that has a chemical modifier
       and no mutation annotation. The profile is projected onto the molecule's own numbering
       (positions outside the molecule are dropped) and stored on the evidence item; the site writes
       it out as a sidecar. Conditions come from the RDAT annotations (buffer, MgCl2, NaCl, KCl,
       temperature, pH).
"""

from __future__ import annotations

import json
import re

from conformome.common import fetch_url
from conformome.molecule import nucleic_acid_info
from conformome.sources.base import conditions, evidence, load_raw as _load, number, save_raw

KEY = "rmdb"
NAME = "RMDB"
LICENCE = "CC0 1.0"
IMPLEMENTED = True
MOLECULE_TYPES = {"rna"}
SITE = "https://rmdb.stanford.edu"
MANIFEST_URL = f"{SITE}/manifest.json"
DETAIL_URL = SITE + "/detail/{}/"
MAX_CONSTRUCTS = 300

# Modifier (as RDAT writes it, case-insensitive) -> (technique, profile kind).
MODIFIERS = {
    "1m7": ("shape", "shape_reactivity"), "nmia": ("shape", "shape_reactivity"),
    "1m6": ("shape", "shape_reactivity"), "2a3": ("shape", "shape_reactivity"),
    "nai": ("shape", "shape_reactivity"), "nai-n3": ("shape", "shape_reactivity"),
    "bzcn": ("shape", "shape_reactivity"), "fai": ("shape", "shape_reactivity"),
    "dms": ("dms_mapseq", "dms_reactivity"),
    "oh": ("na_footprinting", "hydroxyl_radical_reactivity"),
    "fe-edta": ("na_footprinting", "hydroxyl_radical_reactivity"),
}
NO_MODIFIER = {"nomod", "none", "no mod", "nomodification", ""}
ION_CHEMICALS = {"mgcl2": "Mg2+", "nacl": "Na+", "kcl": "K+", "cacl2": "Ca2+", "licl": "Li+", "mncl2": "Mn2+"}
MONOVALENT = {"Na+", "K+", "Li+"}


def _norm(seq: str) -> str:
    return re.sub(r"[^ACGU]", "", seq.upper().replace("T", "U"))


def parse_rdat(text: str) -> dict:
    """The parts of an RDAT file this module uses."""
    out = {"name": None, "sequence": "", "sequences": {}, "annotation": [], "data_annotation": {},
           "offset": 0, "seqpos": [], "reactivity": {}, "reactivity_error": {}, "comments": []}
    for line in text.splitlines():
        parts = line.rstrip("\n").split("\t")
        key = parts[0].strip()
        rest = [p.strip() for p in parts[1:] if p.strip() != ""]
        if not key:
            continue
        if key == "NAME":
            out["name"] = " ".join(rest)
        elif key == "SEQUENCE":
            out["sequence"] = "".join(rest)
        elif key.startswith("SEQUENCE:"):
            out["sequences"][key.split(":", 1)[1]] = "".join(rest)
        elif key == "ANNOTATION":
            out["annotation"] = rest
        elif key.startswith("ANNOTATION_DATA:"):
            out["data_annotation"][key.split(":", 1)[1]] = rest
        elif key == "OFFSET":
            out["offset"] = int(number(rest[0]) or 0) if rest else 0
        elif key == "SEQPOS":
            out["seqpos"] = [int(re.sub(r"[^0-9-]", "", p)) for p in rest if re.sub(r"[^0-9-]", "", p)]
        elif key.startswith("REACTIVITY_ERROR:"):
            out["reactivity_error"][key.split(":", 1)[1]] = [number(v) for v in rest]
        elif key.startswith("REACTIVITY:"):
            out["reactivity"][key.split(":", 1)[1]] = [number(v) for v in rest]
        elif key.startswith("COMMENT"):
            out["comments"].append(" ".join([key[7:].strip()] + rest).strip())
    return out


def _tags(items: list[str]) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for item in items:
        name, _, value = item.partition(":")
        tags.setdefault(name.strip().lower(), []).append(value.strip())
    return tags


def _conditions(tags: dict[str, list[str]], notes: str) -> dict:
    ions, buffer, ph, salt, temp = [], [], None, None, None
    for chem in tags.get("chemical", []):
        name, _, amount = chem.partition(":")
        conc = re.match(r"([0-9.]+)\s*(m|u|µ)?M", amount, re.I)
        conc_mm = None
        if conc:
            factor = {"m": 1.0, "u": 1e-3, "µ": 1e-3}.get((conc.group(2) or "").lower(), 1000.0)
            conc_mm = round(float(conc.group(1)) * factor, 6)
        ph_match = re.search(r"pH\s*([0-9.]+)", amount, re.I)
        if ph_match:
            ph = number(ph_match.group(1))
        ion = ION_CHEMICALS.get(name.strip().lower())
        if ion:
            ions.append({"ion": ion, "concentration_mM": conc_mm})
            if ion in MONOVALENT and conc_mm is not None:
                salt = (salt or 0) + conc_mm
        else:
            buffer.append(f"{name.strip()} {amount}".strip())
    for value in tags.get("temperature", []):
        temp = number(re.sub(r"[^0-9.-]", "", value))
    return conditions("in_vitro", temperature_c=temp, ph=ph, buffer="; ".join(buffer) or None,
                      salt_mM=salt, ions=ions, notes=notes)


def candidates(manifest: list[dict], length: int) -> tuple[list[dict], list[dict]]:
    """Entries to scan, and entries skipped because they are large libraries."""
    scan, skipped = [], []
    for entry in manifest:
        if (entry.get("sequence_len") or 0) < length:
            continue
        (scan if (entry.get("construct_count") or 0) <= MAX_CONSTRUCTS else skipped).append(entry)
    return scan, skipped


def _rdat_url(paths, rmdb_id: str) -> str | None:
    html = fetch_url(DETAIL_URL.format(rmdb_id), cache_dir=paths.raw / "_cache",
                     headers={"Accept": "text/html"}).decode("utf-8", "replace")
    found = re.search(r'https://github\.com/DasLab/rmdb\.github\.io/releases/download/[^"\']+\.rdat', html)
    return found.group(0) if found else None


def matches(rdat: dict, sequence: str) -> list[str]:
    """Data columns whose construct sequence contains the molecule's sequence."""
    target = _norm(sequence)
    cols = []
    for col in rdat["reactivity"]:
        seq = rdat["sequences"].get(col) or rdat["sequence"]
        if target and target in _norm(seq):
            cols.append(col)
    return cols


def fetch(paths, accession: str, retrieved: str) -> dict:
    info = nucleic_acid_info(paths, accession)
    manifest = json.loads(fetch_url(MANIFEST_URL, cache_dir=paths.raw / "_cache"))
    scan, skipped = candidates(manifest, len(info["sequence"]))
    entries, urls = {}, [MANIFEST_URL]
    for entry in scan:
        rdat_url = _rdat_url(paths, entry["rmdb_id"])
        if not rdat_url:
            continue
        text = fetch_url(rdat_url, cache_dir=paths.raw / "_cache", headers={"Accept": "text/plain"}).decode("utf-8", "replace")
        if matches(parse_rdat(text), info["sequence"]):
            entries[entry["rmdb_id"]] = {"manifest": entry, "rdat_url": rdat_url, "rdat": text}
            urls.append(rdat_url)
    raw = {"accession": accession, "retrieved": retrieved, "manifest_url": MANIFEST_URL,
           "sequence": info["sequence"], "scanned": len(scan),
           "not_scanned": [{"rmdb_id": e["rmdb_id"], "construct_count": e["construct_count"]} for e in skipped],
           "entries": entries}
    return save_raw(paths, KEY, accession, raw, urls)


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _columns(raw: dict):
    """(rmdb_id, entry, rdat, column, tags, technique/kind or reason)."""
    for rmdb_id, item in sorted(raw["entries"].items()):
        rdat = parse_rdat(item["rdat"])
        common = rdat["annotation"]
        for col in matches(rdat, raw["sequence"]):
            tags = _tags(common + rdat["data_annotation"].get(col, []))
            modifier = (tags.get("modifier") or [""])[0].strip()
            if tags.get("mutation") and any(m.strip().upper() not in ("WT", "") for m in tags["mutation"]):
                yield rmdb_id, item, rdat, col, tags, f"mutant construct ({', '.join(tags['mutation'])})"
            elif modifier.lower() in NO_MODIFIER:
                yield rmdb_id, item, rdat, col, tags, "no-modifier control"
            elif modifier.lower() not in MODIFIERS:
                yield rmdb_id, item, rdat, col, tags, f"modifier {modifier} has no technique mapping"
            else:
                yield rmdb_id, item, rdat, col, tags, MODIFIERS[modifier.lower()]


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = [{"id": e["rmdb_id"], "reason": f"library of {e['construct_count']} constructs, not scanned"}
           for e in raw["not_scanned"]]
    out += [{"id": f"{rid}:{col}", "reason": what} for rid, _, _, col, _, what in _columns(raw) if isinstance(what, str)]
    return out


def profile(rdat: dict, col: str, sequence: str, kind: str, data_link: str) -> dict:
    """Reactivities on the molecule's own numbering (1..len), null where not measured."""
    construct = _norm(rdat["sequences"].get(col) or rdat["sequence"])
    start = construct.find(_norm(sequence))
    n = len(_norm(sequence))
    values: list[float | None] = [None] * n
    errors: list[float | None] = [None] * n
    reactivity = rdat["reactivity"].get(col) or []
    error = rdat["reactivity_error"].get(col) or []
    # SEQPOS labels are positions in the RDAT numbering; construct index = seqpos - offset - 1.
    seqpos = rdat["seqpos"] or list(range(1 + rdat["offset"], len(reactivity) + 1 + rdat["offset"]))
    for i, pos in enumerate(seqpos):
        j = pos - rdat["offset"] - 1 - start
        if 0 <= j < n and i < len(reactivity):
            values[j] = reactivity[i]
            errors[j] = error[i] if i < len(error) else None
    out = {"kind": kind, "start": 1, "values": values, "unit": None,
           "normalization": "as deposited in RMDB (see the RDAT comments)", "data_link": data_link}
    if any(e is not None for e in errors):
        out["uncertainties"] = errors
    return out


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for rmdb_id, item, rdat, col, tags, what in _columns(raw):
        if isinstance(what, str):
            continue
        technique, kind = what
        entry = item["manifest"]
        construct_len = len(_norm(rdat["sequences"].get(col) or rdat["sequence"]))
        partial = construct_len != len(_norm(raw["sequence"]))
        prof = profile(rdat, col, raw["sequence"], kind, item["rdat_url"])
        measured = sum(1 for v in prof["values"] if v is not None)
        experiment = ", ".join(tags.get("experimenttype", [])) or "chemical mapping"
        notes = f"RMDB {rmdb_id}, column {col}; {experiment}; modifier {tags['modifier'][0]}."
        rec = evidence(
            evidence_id=f"EV-RMDB-{rmdb_id}-{col}",
            accession=accession,
            technique=technique,
            source_kind="deposit",
            title=entry.get("pub_title") or rdat["name"],
            construct=(f"{rdat['name'] or entry.get('name')}; construct {construct_len} nt"
                       + ("; partial construct: the molecule sits inside a longer construct" if partial else "")),
            labels=[],
            conds=_conditions(tags, notes),
            obs_type="reactivity_profile",
            value=measured, unit="positions measured",
            data_link=item["rdat_url"], data_level="processed", data_format="RDAT",
            source=NAME, doi=entry.get("doi"), deposit_id=rmdb_id, retrieved=retrieved,
            url=DETAIL_URL.format(rmdb_id), licence=LICENCE,
        )
        rec["profile"] = prof
        records.append(rec)
    return records
