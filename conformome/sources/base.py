"""The contract every source module follows, and helpers they share.

A source module exposes:
    KEY           short name; raw files live in data/raw/<KEY>/<accession>.json
    NAME          human-readable source name, as it appears in docs/SOURCES.md and in provenance
    LICENCE       licence of the source data, as recorded in docs/SOURCES.md
    IMPLEMENTED   False until fetch and parse work end to end
    MOLECULE_TYPES  optional; the molecule types the source is queried for (default {"protein"})
    fetch(paths, accession, retrieved) -> raw   downloads and caches; writes data/raw/<KEY>/<accession>.json
    parse(raw, accession, retrieved) -> [evidence dict]  pure function, no network
    not_ingested(raw, accession) -> [{"id", "reason"}]   optional; items seen but not turned into evidence

Parsed evidence validates against schema/evidence.schema.json, with an empty "mappings" list.
Mapping to states happens later, in conformome.mapping.
"""

from __future__ import annotations

import json

from conformome.common import cache_retrieved, read_json, record_download, sha256_bytes, write_json


class NotImplementedSource(NotImplementedError):
    """Raised by stub sources. The message says what is missing."""


IMPLEMENTED = False


def fetch(paths, accession: str, retrieved: str):  # pragma: no cover - stub
    raise NotImplementedSource("this source is not implemented yet")


def parse(raw, accession: str, retrieved: str):  # pragma: no cover - stub
    raise NotImplementedSource("this source is not implemented yet")


def commit_json(paths, rel: str, raw: dict, urls: list[str],
                bodies: list[bytes | None] | None = None) -> dict:
    """Write a raw JSON file and its manifest row.

    The retrieval date is the earliest cache sidecar for these requests, so a later run
    does not stamp today's date on data fetched earlier. The manifest hash covers the JSON
    with the retrieved field removed.
    """
    cache = paths.raw / "_cache"
    dates = []
    body_hashes = []
    for i, url in enumerate(urls):
        body = bodies[i] if bodies and i < len(bodies) else None
        if body:
            body_hashes.append(sha256_bytes(body))
        found = cache_retrieved(cache, url, body)
        if found:
            dates.append(found)
    if dates:
        raw = {**raw, "retrieved": min(dates)}
    write_json(paths.raw / rel, raw)
    payload = {k: v for k, v in raw.items() if k != "retrieved"}
    content = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    record_download(paths, f"raw/{rel}", urls, (paths.raw / rel).read_bytes(),
                    retrieved=raw.get("retrieved"), content_sha=sha256_bytes(content),
                    request_body_sha256=body_hashes or None)
    return raw


def save_raw(paths, key: str, accession: str, raw: dict, urls: list[str],
             bodies: list[bytes | None] | None = None) -> dict:
    return commit_json(paths, f"{key}/{accession}.json", raw, urls, bodies)


def load_raw(paths, key: str, accession: str) -> dict | None:
    path = paths.raw / f"{key}/{accession}.json"
    return read_json(path) if path.exists() else None


def conditions(environment: str = "in_vitro", *, temperature_c=None, ph=None, buffer=None, salt_mM=None,
               ions=None, ligands=None, applied_force_pn=None, notes=None) -> dict:
    """A complete conditions object: unknown values are null, never omitted."""
    return {
        "environment": environment,
        "temperature_c": temperature_c,
        "ph": ph,
        "buffer": buffer,
        "salt_mM": salt_mM,
        "ions": list(ions or []),
        "ligands": sorted(ligands or []),
        "applied_force_pn": applied_force_pn,
        "notes": notes,
    }


def number(value) -> float | None:
    """Numbers can arrive as strings. Non-numeric text, NaN and infinity mean unknown."""
    import math
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def kelvin_to_c(value) -> float | None:
    kelvin = number(value)
    return None if kelvin is None else round(kelvin - 273.15, 2)


def evidence(*, evidence_id: str, accession: str, technique: str, source_kind: str, title: str | None,
             construct: str, labels=None, conds: dict, obs_type: str, value=None, unit=None, uncertainty=None,
             data_link: str | None, data_level: str, data_format: str | None = None, reader: str | None = None,
             source: str, doi: str | None, deposit_id: str | None, retrieved: str,
             url: str, licence: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "molecule_id": accession,
        "technique": technique,
        "source_kind": source_kind,
        "title": title,
        "construct": {"description": construct, "labels": list(labels or [])},
        "conditions": conds,
        "observable": {"type": obs_type, "value": value, "unit": unit if value is not None else None,
                       "uncertainty": uncertainty if value is not None else None},
        "mappings": [],
        "data_link": data_link,
        "data_level": data_level,
        "data_format": data_format,
        "reader": reader,
        "provenance": {"source": source, "doi": doi, "deposit_id": deposit_id, "retrieved": retrieved,
                       "url": url, "licence": licence},
    }
