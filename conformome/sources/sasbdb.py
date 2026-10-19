"""SASBDB: small-angle scattering profiles, with radius of gyration and maximum dimension.

fetch: SASBDB search page for the accession (the REST API has no UniProt filter), then the REST
       summary of each code found. Raw file: data/raw/sasbdb/<accession>.json
parse: one evidence item per entry whose sample contains a molecule with this UniProt code.
       Observable: Guinier radius of gyration with its error, in nm (P(r) Rg when Guinier is absent).
"""

from __future__ import annotations

import json
import re

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, load_raw as _load, number, save_raw

KEY = "sasbdb"
NAME = "SASBDB"
LICENCE = "CC BY 4.0 (verify)"
IMPLEMENTED = True
SEARCH_URL = "https://www.sasbdb.org/search/?q={}"
SUMMARY_URL = "https://www.sasbdb.org/rest-api/entry/summary/{}/"
PAGE_URL = "https://www.sasbdb.org/data/{}/"


def fetch(paths, accession: str, retrieved: str) -> dict:
    search = SEARCH_URL.format(accession)
    html = fetch_url(search, cache_dir=paths.raw / "_cache", headers={"Accept": "text/html"}).decode("utf-8", "replace")
    codes = sorted(set(re.findall(r"SASD[A-Z0-9]{3}", html)))
    summaries = [json.loads(fetch_url(SUMMARY_URL.format(c), cache_dir=paths.raw / "_cache")) for c in codes]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "search_url": search,
                                            "summaries": summaries}, [search, SUMMARY_URL.format("<code>")])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _molecules(summary: dict) -> list[dict]:
    return ((summary.get("experiment") or {}).get("sample") or {}).get("molecule") or []


def not_ingested(raw: dict, accession: str) -> list[dict]:
    return [{"id": s["code"], "reason": "no molecule with this UniProt code in the sample"}
            for s in raw["summaries"] if not any(m.get("uniprot_code") == accession for m in _molecules(s))]


def _rg_nm(summary: dict) -> tuple[float | None, float | None]:
    # SASBDB reports Rg and Dmax in nm whatever the angular unit of the curve (checked on 2026-10-19:
    # calmodulin entries in 1/A give Rg 2.0-2.2 nm).
    value, err = number(summary.get("guinier_rg")), number(summary.get("guinier_rg_error"))
    if value is None:
        value, err = number(summary.get("pddf_rg")), number(summary.get("pddf_rg_error"))
    return value, err


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for s in raw["summaries"]:
        molecules = _molecules(s)
        if not any(m.get("uniprot_code") == accession for m in molecules):
            continue
        experiment = s.get("experiment") or {}
        buffer = (experiment.get("sample") or {}).get("buffer") or {}
        rg, err = _rg_nm(s)
        dmax = number(s.get("pddf_dmax"))
        others = [m.get("long_name") or m.get("short_name") for m in molecules if m.get("uniprot_code") != accession]
        mine = sorted({m.get("long_name") or m.get("short_name") or accession for m in molecules
                       if m.get("uniprot_code") == accession})
        project = s.get("project") or {}
        pub = project.get("publication") or {}
        records.append(evidence(
            evidence_id=f"EV-SASBDB-{s['code']}",
            accession=accession,
            technique="saxs_sans",
            source_kind="deposit",
            title=project.get("title") or s.get("description"),
            construct=f"{'; '.join(mine)}" + (f" with {', '.join(o for o in others if o)}" if others else ""),
            conds=conditions("in_vitro", temperature_c=number(experiment.get("cell_temperature")),
                             ph=number(buffer.get("ph") or buffer.get("pH")), buffer=buffer.get("name"),
                             ligands=[f"partner: {o}" for o in others if o],
                             notes="Other molecules in the sample are listed as partners; Rg is of the whole sample."
                                   + (f" Dmax {dmax:g} nm." if dmax is not None else "")),
            obs_type="radius_of_gyration",
            value=rg, unit="nm", uncertainty=err,
            data_link=PAGE_URL.format(s["code"]),
            source=NAME, doi=pub.get("doi"), deposit_id=s["code"], retrieved=retrieved,
            url=PAGE_URL.format(s["code"]), licence=LICENCE,
        ))
    return records
