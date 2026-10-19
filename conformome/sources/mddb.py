"""MDDB: molecular dynamics trajectories (the MDDB federation, including MoDEL).

fetch: MDDB REST API, projects whose metadata references the UniProt accession.
       Raw file: data/raw/mddb/<accession>.json
parse: one evidence item per project, technique `md` (a computed prediction), observable the
       simulated trajectory length in ns. Temperature from the project metadata (kelvin).
"""

from __future__ import annotations

import json
import re
import urllib.parse

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, kelvin_to_c, load_raw as _load, number, save_raw

KEY = "mddb"
NAME = "MDDB"
LICENCE = "per project (CC BY 4.0 for most)"
IMPLEMENTED = True
API_URL = "https://mmb.mddbr.eu/api/rest/v1/projects?query={}&limit=500"
PAGE_URL = "https://mmb.mddbr.eu/#/id/{}/overview"


def fetch(paths, accession: str, retrieved: str) -> dict:
    url = API_URL.format(urllib.parse.quote(json.dumps({"metadata.REFERENCES": accession})))
    data = json.loads(fetch_url(url, cache_dir=paths.raw / "_cache"))
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "url": url,
                                            "projects": data.get("projects") or []}, [url])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for project in raw["projects"]:
        meta = project.get("metadata") or {}
        if accession not in (meta.get("REFERENCES") or []):
            continue
        acc_id = project["accession"]
        doi = re.search(r"10\.\d{4,9}/\S+", meta.get("CITATION") or "")
        pdbs = ", ".join(meta.get("PDBIDS") or []) or "no PDB start structure listed"
        ff = ", ".join(meta.get("FF") or []) or "force field not stated"
        records.append(evidence(
            evidence_id=f"EV-MDDB-{acc_id}",
            accession=accession,
            technique="md",
            source_kind="computed",
            title=meta.get("NAME"),
            construct=f"start {pdbs}; {ff}",
            conds=conditions("in_silico", temperature_c=kelvin_to_c(meta.get("TEMP")),
                             ligands=meta.get("LIGANDNAMES") if isinstance(meta.get("LIGANDNAMES"), list) else None,
                             notes="Simulation; temperature is the thermostat setting."),
            obs_type="trajectory",
            value=number(meta.get("LENGTH")), unit="ns",
            data_link=PAGE_URL.format(acc_id),
            source=NAME, doi=doi.group(0).rstrip(".") if doi else None, deposit_id=acc_id, retrieved=retrieved,
            url=PAGE_URL.format(acc_id), licence=meta.get("LICENSE") or LICENCE,
        ))
    return records
