"""AlphaFold DB: predicted structures. Predictions, not measurements; labelled as such everywhere.

fetch: AlphaFold DB prediction API by UniProt accession. Raw file: data/raw/alphafold/<accession>.json
parse: one evidence item per predicted model, technique `af_prediction`, observable mean pLDDT.
"""

from __future__ import annotations

import json
import urllib.error

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, load_raw as _load, save_raw

KEY = "alphafold"
NAME = "AlphaFold DB"
LICENCE = "CC BY 4.0"
IMPLEMENTED = True
API_URL = "https://alphafold.ebi.ac.uk/api/prediction/{}"
ENTRY_URL = "https://alphafold.ebi.ac.uk/entry/{}"


def fetch(paths, accession: str, retrieved: str) -> dict:
    url = API_URL.format(accession)
    try:
        models = json.loads(fetch_url(url, cache_dir=paths.raw / "_cache"))
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        models = []  # no prediction for this accession (for example, sequences too long for the pipeline)
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "url": url,
                                            "models": models}, [url])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for m in raw["models"]:
        if m.get("uniprotAccession", accession) != accession:
            continue
        model_id = m.get("modelEntityId") or m.get("entryId")
        start, end = m.get("uniprotStart"), m.get("uniprotEnd")
        span = f", residues {start}-{end}" if start and end else ""
        records.append(evidence(
            evidence_id=f"EV-AFDB-{model_id}",
            accession=accession,
            technique="af_prediction",
            source_kind="computed",
            title=f"AlphaFold DB prediction {model_id}",
            construct=f"{m.get('toolUsed') or 'AlphaFold'}{span}",
            conds=conditions("in_silico", notes="Computed prediction; no experimental conditions."),
            obs_type="plddt",
            value=m.get("globalMetricValue"),
            unit="pLDDT",
            data_link=ENTRY_URL.format(accession), data_level="processed", data_format="mmCIF, PAE JSON",
            source=NAME, doi=None, deposit_id=model_id, retrieved=retrieved,
            url=ENTRY_URL.format(accession), licence=LICENCE,
        ))
    return records
