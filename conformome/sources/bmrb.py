"""BMRB: NMR chemical shifts, relaxation and exchange data.

fetch: BMRB's UniProt-to-entry mapping (one shared file), then the entry_information and
       sample_conditions saveframes of each entry. Raw file: data/raw/bmrb/<accession>.json
parse: one evidence item per entry. Entries with relaxation data become `nmr_dynamics` /
       relaxation_rate, entries with exchange data `nmr_dynamics` / exchange_rate, and entries with
       only chemical shifts `nmr_shifts` / chemical_shift. Temperature and pH come from the first
       sample condition list.
"""

from __future__ import annotations

import json
import re

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, kelvin_to_c, load_raw as _load, number, save_raw

KEY = "bmrb"
NAME = "BMRB"
LICENCE = "CC0 1.0 (verify)"
IMPLEMENTED = True
MAP_URL = "https://api.bmrb.io/v2/mappings/uniprot/bmrb?format=json"
ENTRY_URL = "https://api.bmrb.io/v2/entry/{}?saveframe_category=entry_information&saveframe_category=sample_conditions"
PAGE_URL = "https://bmrb.io/data_library/summary/index.php?bmrbId={}"


def fetch(paths, accession: str, retrieved: str) -> dict:
    mapping = json.loads(fetch_url(MAP_URL, cache_dir=paths.raw / "_cache"))
    ids = sorted({i for row in mapping if row["uniprot_id"] == accession for i in row["bmrb_ids"]}, key=int)
    entries = {}
    for bmrb_id in ids:
        entries[bmrb_id] = json.loads(fetch_url(ENTRY_URL.format(bmrb_id), cache_dir=paths.raw / "_cache"))
    urls = [MAP_URL] + [ENTRY_URL.format(bmrb_id) for bmrb_id in ids]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "map_url": MAP_URL,
                                            "entries": entries}, urls)


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _frame(data: dict, bmrb_id: str, category: str) -> dict | None:
    frames = (data.get(bmrb_id) or {}).get(category) or []
    return frames[0] if frames else None


def _loop(frame: dict | None, category: str) -> list[dict]:
    for loop in (frame or {}).get("loops", []):
        if loop["category"] == category:
            return [dict(zip(loop["tags"], row)) for row in loop["data"]]
    return []


def classify(datum_types: list[str]) -> tuple[str, str] | None:
    types = [t.lower() for t in datum_types]
    if any(k in t for t in types for k in ("relaxation", "heteronuclear noe", "order parameter", "t1rho")):
        return "nmr_dynamics", "relaxation_rate"
    if any("exchange" in t or "protection" in t for t in types):
        return "nmr_dynamics", "exchange_rate"
    if any("chemical shift" in t for t in types):
        return "nmr_shifts", "chemical_shift"
    return None


def _sample(data: dict, bmrb_id: str) -> tuple[float | None, float | None]:
    temp = ph = None
    for row in _loop(_frame(data, bmrb_id, "sample_conditions"), "_Sample_condition_variable"):
        kind = (row.get("Type") or "").lower()
        if kind == "temperature" and temp is None:
            unit = (row.get("Val_units") or "").strip().lower()
            raw = number(row.get("Val"))
            if raw is None:
                temp = None
            elif unit in ("k", "kelvin") or (not unit and raw > 200):
                temp = kelvin_to_c(raw)
            elif not unit or unit in ("c", "celsius", "degc", "°c"):
                temp = raw
            else:
                temp = None
            if temp is not None and not -50 <= temp <= 150:
                temp = None
        elif kind == "ph" and ph is None:
            ph = number(row.get("Val"))
    return temp, ph


def _info(data: dict, bmrb_id: str) -> tuple[str | None, list[str]]:
    frame = _frame(data, bmrb_id, "entry_information")
    tags = dict((t[0], t[1]) for t in (frame or {}).get("tags", []))
    title = re.sub(r"\s+", " ", tags.get("Title") or "").strip() or None
    types = [row["Type"] for row in _loop(frame, "_Datum")]
    return title, types


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for bmrb_id, data in raw["entries"].items():
        _, types = _info(data, bmrb_id)
        if classify(types) is None:
            out.append({"id": f"bmr{bmrb_id}", "reason": f"no shift, relaxation or exchange data ({', '.join(types) or 'no data types'})"})
    return out


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for bmrb_id, data in raw["entries"].items():
        title, types = _info(data, bmrb_id)
        kind = classify(types)
        if kind is None:
            continue
        technique, obs = kind
        temp, ph = _sample(data, bmrb_id)
        records.append(evidence(
            evidence_id=f"EV-BMRB-{bmrb_id}",
            accession=accession,
            technique=technique,
            source_kind="deposit",
            title=title,
            construct="BMRB data: " + ", ".join(types[:6]),
            conds=conditions("in_vitro", temperature_c=temp, ph=ph,
                             notes="From the first sample condition list of the entry."),
            obs_type=obs,
            data_link=PAGE_URL.format(bmrb_id), data_level="processed", data_format="NMR-STAR",
            source=NAME, doi=f"10.13018/BMR{bmrb_id}", deposit_id=f"bmr{bmrb_id}", retrieved=retrieved,
            url=PAGE_URL.format(bmrb_id), licence=LICENCE,
        ))
    return records
