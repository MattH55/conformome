"""SMASH-BIO: single-molecule force spectroscopy records and their extracted results.

Consumes the SMASH-BIO release file (website/downloads/smash-smfs-records.jsonl.gz in
matth55/smash-bio); no SMASH-BIO code is used. Set CONFORMOME_SMASHBIO_RELEASE to a local path or
CONFORMOME_SMASHBIO_URL to another release URL. The file's SHA-256 is recorded in data/MANIFEST.json.

fetch: the release file (once), then the records whose entities carry the UniProt accession.
       Raw file: data/raw/smashbio/<accession>.json
parse: one evidence item per extracted result whose quantity is a force-spectroscopy observable;
       records without such a result give one `study_record` item. Most SMASH-BIO records are
       extracted automatically; the extraction level is kept in the conditions notes.
The licence of SMASH-BIO data is not stated, so docs/SOURCES.md marks it not redistributable:
these records appear on pages with links, and are left out of downloads.
"""

from __future__ import annotations

import gzip
import io
import json
import os
from pathlib import Path

from conformome.common import fetch_url, record_download, sha256_bytes
from conformome.sources.base import conditions, evidence, load_raw as _load, number, save_raw

KEY = "smashbio"
NAME = "SMASH-BIO"
LICENCE = "not stated by the source"
IMPLEMENTED = True
RELEASE_URL = "https://raw.githubusercontent.com/MattH55/smash-bio/main/website/downloads/smash-smfs-records.jsonl.gz"
IN_CELL = {"tension_sensors"}
_release_cache: dict[str, tuple[list[dict], str, str]] = {}


def _release(paths) -> tuple[list[dict], str, str]:
    local = os.environ.get("CONFORMOME_SMASHBIO_RELEASE")
    url = os.environ.get("CONFORMOME_SMASHBIO_URL", RELEASE_URL)
    key = local or url
    if key not in _release_cache:
        data = Path(local).read_bytes() if local else fetch_url(url, cache_dir=paths.raw / "_cache")
        rel = "smashbio/release.jsonl.gz"
        (paths.raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (paths.raw / rel).write_bytes(data)
        record_download(paths, f"raw/{rel}", [f"file://{local}" if local else url], data)
        records = [json.loads(line) for line in gzip.open(io.BytesIO(data), "rt", encoding="utf-8") if line.strip()]
        _release_cache[key] = (records, f"file://{local}" if local else url, sha256_bytes(data))
    return _release_cache[key]


def _uniprots(record: dict) -> set[str]:
    ents = (record.get("biological_system") or {}).get("entities") or []
    return {i["id"] for e in ents for i in (e.get("identifiers") or []) if i.get("scheme") == "uniprot"}


def fetch(paths, accession: str, retrieved: str) -> dict:
    records, url, sha = _release(paths)
    mine = [r for r in records if accession in _uniprots(r)]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "release_url": url,
                                            "release_sha256": sha, "records": mine}, [url])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


# SMASH-BIO observable -> taxonomy observable for force_spectroscopy. Unlisted quantities are skipped.
QUANTITIES = {
    "unfolding_force", "refolding_force", "rupture_force", "unbinding_force", "adhesion_force",
    "contour_length", "contour_length_increment", "persistence_length", "folding_free_energy",
    "distance_to_transition_state", "unfolding_rate", "folding_rate", "rate_constant_zero_force",
    "step_size", "stall_force", "velocity", "dwell_time", "bond_lifetime", "loading_rate",
    "elastic_modulus", "molecular_stiffness", "equilibrium_force", "overstretching_force", "torque",
}


def _value(result: dict) -> float | None:
    for key in ("value", "mean", "median"):
        if number(result.get(key)) is not None:
            return number(result[key])
    return None


def _entity_names(record: dict, accession: str) -> str:
    names = []
    for e in (record.get("biological_system") or {}).get("entities") or []:
        if any(i.get("scheme") == "uniprot" and i.get("id") == accession for i in e.get("identifiers") or []):
            names.append(e.get("name", "") + (f" ({e['region']})" if e.get("region") else ""))
    return "; ".join(n for n in names if n) or "entity carrying this accession"


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    out = []
    for rec in raw["records"]:
        rid = rec["record_id"]
        pub = rec.get("publication") or {}
        doi = pub.get("doi")
        primary = (rec.get("technique") or {}).get("primary") or "force_spectroscopy_unspecified"
        solution = rec.get("solution") or {}
        level = (rec.get("curation") or {}).get("level", "unknown")
        classes = ", ".join((rec.get("assay") or {}).get("experiment_class") or []) or "not stated"
        construct = f"{_entity_names(rec, accession)}; {primary.replace('_', ' ')}; experiment class: {classes}"
        common = dict(accession=accession, technique="force_spectroscopy", source_kind="literature",
                      data_level="reported", data_format=None,
                      title=pub.get("title"), data_link=f"https://doi.org/{doi}" if doi else raw["release_url"],
                      source=NAME, doi=doi, deposit_id=rid, retrieved=retrieved, url=raw["release_url"], licence=LICENCE)
        env = "in_cell" if primary in IN_CELL else "in_vitro"
        notes = f"SMASH-BIO extraction level: {level}."
        results = [(i, r) for i, r in enumerate(rec.get("results") or [])
                   if r.get("quantity") in QUANTITIES and _value(r) is not None]
        if not results:
            out.append(evidence(evidence_id=f"EV-SMASH-{rid}", construct=construct,
                                conds=conditions(env, ph=number(solution.get("pH")), buffer=solution.get("buffer"), notes=notes),
                                obs_type="study_record", **common))
            continue
        for i, r in results:
            force = number((r.get("conditions") or {}).get("force_pN"))
            applies = (r.get("applies_to") or {}).get("entity")
            out.append(evidence(
                evidence_id=f"EV-SMASH-{rid}-r{i}",
                construct=construct + (f"; result applies to {applies}" if applies else ""),
                conds=conditions(env, ph=number(solution.get("pH")), buffer=solution.get("buffer"),
                                 applied_force_pn=force, notes=notes + f" Statistic: {r.get('statistic', 'not stated')}."),
                obs_type=r["quantity"], value=_value(r), unit=r.get("unit"), uncertainty=number(r.get("uncertainty")),
                **common))
    return out
