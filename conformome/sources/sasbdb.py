"""SASBDB: small-angle scattering profiles, with radius of gyration and maximum dimension.

fetch: SASBDB search page for the accession (the REST API has no UniProt filter), then the REST
       summary of each code found. Raw file: data/raw/sasbdb/<accession>.json
parse: one evidence item per entry whose sample contains a molecule with this UniProt code.
       Observable: Guinier radius of gyration with its error, in nm. P(r) Rg is not used.
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
    codes: set[str] = set()
    search_urls = []
    for page in range(1, 11):
        search = SEARCH_URL.format(accession) if page == 1 else SEARCH_URL.format(accession) + f"&page={page}"
        html = fetch_url(search, cache_dir=paths.raw / "_cache", headers={"Accept": "text/html"}).decode("utf-8", "replace")
        found = set(re.findall(r"SASD[A-Z0-9]{3}", html))
        search_urls.append(search)
        if not found or found <= codes:
            break
        codes |= found
    summaries = [json.loads(fetch_url(SUMMARY_URL.format(c), cache_dir=paths.raw / "_cache")) for c in sorted(codes)]
    urls = search_urls + [SUMMARY_URL.format(c) for c in sorted(codes)]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "search_url": search_urls[0],
                                            "summaries": summaries}, urls)


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _molecules(summary: dict) -> list[dict]:
    return ((summary.get("experiment") or {}).get("sample") or {}).get("molecule") or []


_SALT = re.compile(r"(\d+(?:\.\d+)?)\s*mM", re.IGNORECASE)


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for summary in raw["summaries"]:
        if not any(m.get("uniprot_code") == accession for m in _molecules(summary)):
            out.append({"id": summary["code"], "reason": "no molecule with this UniProt code in the sample"})
        elif _rg_nm(summary)[0] is None:
            out.append({"id": summary["code"], "reason": "no Guinier Rg (P(r) Rg is not compared with Guinier)"})
    return out


def _rg_nm(summary: dict) -> tuple[float | None, float | None]:
    """Guinier Rg only, in nm. A value above 30 nm is treated as ångström and divided by 10."""
    value, err = number(summary.get("guinier_rg")), number(summary.get("guinier_rg_error"))
    if value is None:
        return None, None
    if value > 30:
        if value <= 300:
            value = value / 10
            err = None if err is None else err / 10
        else:
            return None, None
    return value, err


def _salt_mM(buffer: dict) -> float | None:
    match = _SALT.search(buffer.get("name") or "")
    return number(match.group(1)) if match else None


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for s in raw["summaries"]:
        molecules = _molecules(s)
        if not any(m.get("uniprot_code") == accession for m in molecules):
            continue
        experiment = s.get("experiment") or {}
        buffer = (experiment.get("sample") or {}).get("buffer") or {}
        rg, err = _rg_nm(s)
        if rg is None:
            continue
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
                             salt_mM=_salt_mM(buffer),
                             ligands=[f"partner: {o}" for o in others if o],
                             notes="Other molecules in the sample are listed as partners; Rg is of the whole sample."
                                   + (f" Dmax {dmax:g} nm." if dmax is not None else "")),
            obs_type="radius_of_gyration",
            value=rg, unit="nm", uncertainty=err,
            data_link=PAGE_URL.format(s["code"]), data_level="processed", data_format="scattering curve",
            source=NAME, doi=pub.get("doi"), deposit_id=s["code"], retrieved=retrieved,
            url=PAGE_URL.format(s["code"]), licence=LICENCE,
        ))
    return records
