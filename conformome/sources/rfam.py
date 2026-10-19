"""Rfam: RNA families, their covariance models and consensus secondary structures.

fetch: for each Rfam family RNAcentral assigns to the molecule, the family record (JSON) and the
       consensus structure and reference lines (SS_cons, RF) of the seed alignment. The rest of the
       alignment is not kept. Raw file: data/raw/rfam/<molecule_id>.json
parse: one evidence item per family hit, technique `rfam_covariation` (comparative sequence analysis,
       flagged as a prediction). The observable is the fraction of the molecule the hit covers.
       The consensus structure is per alignment column; projecting it onto this sequence needs
       cmalign (Infernal) and is not done here.
"""

from __future__ import annotations

import json

from conformome import rnacentral
from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, load_raw as _load, save_raw

KEY = "rfam"
NAME = "Rfam"
LICENCE = "CC0 1.0"
IMPLEMENTED = True
MOLECULE_TYPES = {"rna"}
FAMILY_URL = "https://rfam.org/family/{}?content-type=application/json"
SEED_URL = "https://rfam.org/family/{}/alignment/stockholm?gzip=0"
PAGE_URL = "https://rfam.org/family/{}"
RFAM_URL = "https://rfam.org"


def consensus(stockholm: str) -> dict:
    """SS_cons and RF of a Stockholm alignment, joined across blocks."""
    lines = {"SS_cons": [], "RF": []}
    for line in stockholm.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "#=GC" and parts[1] in lines:
            lines[parts[1]].append(parts[2])
    return {k: "".join(v) for k, v in lines.items()}


def fetch(paths, molecule_id: str, retrieved: str) -> dict:
    ident = rnacentral.load_raw(paths, molecule_id)
    if ident is None:
        raise FileNotFoundError(f"{molecule_id}: download the RNAcentral entry first")
    families, urls = {}, []
    for hit in rnacentral.rfam_hits(ident):
        acc = hit["rfam"]
        if acc in families:
            continue
        fam_url, seed_url = FAMILY_URL.format(acc), SEED_URL.format(acc)
        family = json.loads(fetch_url(fam_url, cache_dir=paths.raw / "_cache"))["rfam"]
        seed = fetch_url(seed_url, headers={"Accept": "*/*"}, cache_dir=paths.raw / "_cache").decode("utf-8", "replace")
        families[acc] = {"family": family, "consensus": consensus(seed)}
        urls += [fam_url, seed_url]
    raw = {"accession": molecule_id, "retrieved": retrieved, "url": RFAM_URL, "hits": rnacentral.rfam_hits(ident),
           "length": len(ident["entry"]["sequence"]), "families": families}
    return save_raw(paths, KEY, molecule_id, raw, urls)


def load_raw(paths, molecule_id: str) -> dict | None:
    return _load(paths, KEY, molecule_id)


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for hit in raw["hits"]:
        acc = hit["rfam"]
        fam = raw["families"][acc]["family"]
        cur = fam.get("curation") or {}
        records.append(evidence(
            evidence_id=f"EV-RFAM-{acc}-{hit['start']}-{hit['end']}",
            accession=accession,
            technique="rfam_covariation",
            source_kind="computed",
            title=f"Rfam {acc} ({fam.get('id')}): {fam.get('description')}",
            construct=(f"positions {hit['start']}-{hit['end']} of {raw['length']} match the family covariance model; "
                       f"type {cur.get('type') or 'not stated'}; consensus structure source: {cur.get('structure_source') or 'not stated'}"),
            conds=conditions("in_silico", notes=f"Rfam release {(fam.get('release') or {}).get('number', 'not stated')}."),
            obs_type="family_coverage",
            value=round(hit["completeness"], 3) if hit.get("completeness") is not None else None, unit="fraction",
            data_link=PAGE_URL.format(acc), data_level="processed", data_format="Stockholm (SS_cons), covariance model",
            source=NAME, doi=None, deposit_id=acc, retrieved=retrieved, url=PAGE_URL.format(acc), licence=LICENCE,
        ))
    return records
