"""RCSB PDB: observed structures for a UniProt accession.

fetch: RCSB Search API (polymer entities carrying the accession) -> batched RCSB GraphQL
       for entry metadata. Raw file: data/raw/pdb/<accession>.json
parse: one evidence item per deposited polymer entity whose UniProt mapping includes the
       accession. Conditions come from entry metadata; pH and temperature are null when the
       entry does not carry them in the machine-readable fields.
"""

from __future__ import annotations

import json
import urllib.parse

from conformome.common import fetch_url, read_json, record_download, write_json

KEY = "pdb"
NAME = "RCSB PDB"
IMPLEMENTED = True
LICENCE = "CC0 1.0 (wwPDB archive data)"
SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
GRAPHQL_URL = "https://data.rcsb.org/graphql"
ENTRY_URL = "https://www.rcsb.org/structure/{}"
BATCH = 50

# PDB experimental method -> conformome technique id (see taxonomy/techniques.yaml).
METHOD_TECHNIQUE = {
    "X-RAY DIFFRACTION": "xray",
    "ELECTRON MICROSCOPY": "cryoem",
    "ELECTRON CRYSTALLOGRAPHY": "microed",
    "NEUTRON DIFFRACTION": "neutron",
    "SOLUTION NMR": "nmr_structure",
    "SOLID-STATE NMR": "nmr_structure",
    # Integrative models (PDB-IHM, now distributed through the PDB) carry no exptl block; RCSB labels
    # them experimental_method "Integrative". They are inferred structures and are labelled as such.
    "INTEGRATIVE": "integrative",
    "SOLUTION SCATTERING": "saxs_sans",
}

# Deposited format per technique (what the entry page links to).
DATA_FORMAT = {
    "xray": "mmCIF + structure factors",
    "cryoem": "mmCIF + EMDB map",
    "microed": "mmCIF",
    "neutron": "mmCIF + structure factors",
    "nmr_structure": "mmCIF + NMR restraints",
    "integrative": "mmCIF/IHM",
    "saxs_sans": "mmCIF",
}

GRAPHQL_QUERY = """
query($ids: [String!]!) {
  entries(entry_ids: $ids) {
    rcsb_id
    struct { title }
    exptl { method }
    rcsb_entry_info { resolution_combined experimental_method }
    rcsb_accession_info { initial_release_date }
    rcsb_primary_citation { pdbx_database_id_DOI }
    diffrn { ambient_temp }
    exptl_crystal_grow { pH temp }
    pdbx_nmr_exptl_sample_conditions { temperature pH }
    polymer_entities {
      rcsb_id
      rcsb_polymer_entity { pdbx_description }
      rcsb_polymer_entity_container_identifiers { entity_id auth_asym_ids uniprot_ids }
    }
    nonpolymer_entities { nonpolymer_comp { chem_comp { id name } } }
    branched_entities { rcsb_branched_entity { pdbx_description } }
  }
}
"""


def search_entry_ids(accession: str, cache_dir) -> tuple[list[str], str]:
    """Entry IDs with at least one polymer entity mapped to the accession (sorted)."""
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                "operator": "exact_match",
                "value": accession,
            },
        },
        "request_options": {"paginate": {"start": 0, "rows": 10000}},
        "return_type": "polymer_entity",
    }
    url = SEARCH_URL + "?json=" + urllib.parse.quote(json.dumps(query))
    hits = json.loads(fetch_url(url, cache_dir=cache_dir)).get("result_set") or []
    return sorted({hit["identifier"].split("_")[0] for hit in hits}), url


def fetch(paths, accession: str, retrieved: str) -> dict:
    cache = paths.raw / "_cache"
    ids, search_url = search_entry_ids(accession, cache)
    entries, gql_urls = [], []
    for start in range(0, len(ids), BATCH):
        chunk = ids[start:start + BATCH]
        body = json.dumps({"query": GRAPHQL_QUERY, "variables": {"ids": chunk}}).encode()
        payload = json.loads(fetch_url(GRAPHQL_URL, body=body, cache_dir=cache,
                                       headers={"Content-Type": "application/json"}))
        if payload.get("errors"):
            raise RuntimeError(f"RCSB GraphQL error for {accession}: {payload['errors'][0]['message']}")
        entries.extend(e for e in payload["data"]["entries"] if e)
        gql_urls.append(GRAPHQL_URL)
    raw = {
        "accession": accession,
        "retrieved": retrieved,
        "search_url": search_url,
        "entry_ids": ids,
        "entries": entries,
    }
    rel = f"pdb/{accession}.json"
    write_json(paths.raw / rel, raw)
    record_download(paths, f"raw/{rel}", [search_url, GRAPHQL_URL], (paths.raw / rel).read_bytes())
    return raw


def _method(entry: dict) -> str | None:
    methods = [m["method"] for m in entry.get("exptl") or []]
    if methods:
        return methods[0]
    fallback = (entry.get("rcsb_entry_info") or {}).get("experimental_method")
    return fallback.upper() if fallback else None


def _number(value) -> float | None:
    """mmCIF values can arrive as strings through GraphQL; non-numeric text means unknown."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _temperature_c(entry: dict) -> float | None:
    # mmCIF defines these temperatures in kelvin.
    for block in entry.get("diffrn") or []:
        kelvin = _number(block.get("ambient_temp"))
        if kelvin is not None:
            return round(kelvin - 273.15, 2)
    for block in entry.get("pdbx_nmr_exptl_sample_conditions") or []:
        kelvin = _number(block.get("temperature"))
        if kelvin is not None:
            return round(kelvin - 273.15, 2)
    return None


def _ph(entry: dict) -> float | None:
    for block in (entry.get("exptl_crystal_grow") or []) + (entry.get("pdbx_nmr_exptl_sample_conditions") or []):
        value = _number(block.get("pH"))
        if value is not None:
            return value
    return None


def unmapped_methods(raw: dict) -> dict[str, int]:
    """Count entries whose experimental method has no technique mapping (reported, not ingested)."""
    counts: dict[str, int] = {}
    for entry in raw["entries"]:
        method = _method(entry)
        if method not in METHOD_TECHNIQUE:
            counts[str(method)] = counts.get(str(method), 0) + 1
    return counts


def unmapped_entries(raw: dict) -> list[dict]:
    """Entries not ingested because their experimental method has no technique mapping."""
    return [{"pdb_id": e["rcsb_id"], "method": _method(e), "title": e["struct"]["title"]}
            for e in raw["entries"] if _method(e) not in METHOD_TECHNIQUE]


def not_ingested(raw: dict, accession: str) -> list[dict]:
    return [{"id": u["pdb_id"], "reason": f"method {u['method']} has no technique mapping"} for u in unmapped_entries(raw)]


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for entry in raw["entries"]:
        pdb_id = entry["rcsb_id"]
        technique = METHOD_TECHNIQUE.get(_method(entry))
        if technique is None:
            continue
        resolution = (entry.get("rcsb_entry_info") or {}).get("resolution_combined") or []
        resolution = resolution[0] if resolution else None
        doi = (entry.get("rcsb_primary_citation") or {}).get("pdbx_database_id_DOI")
        ligands = sorted({np["nonpolymer_comp"]["chem_comp"]["id"] for np in entry.get("nonpolymer_entities") or []
                          if np.get("nonpolymer_comp")})
        # Oligosaccharides are branched entities, not nonpolymer ligands (maltose in 1ANF, for example).
        ligands += sorted({f"branched: {b['rcsb_branched_entity']['pdbx_description']}"
                           for b in entry.get("branched_entities") or [] if (b.get("rcsb_branched_entity") or {}).get("pdbx_description")})
        for poly in entry["polymer_entities"]:
            ident = poly["rcsb_polymer_entity_container_identifiers"]
            if accession not in (ident.get("uniprot_ids") or []):
                continue
            entity = ident["entity_id"]
            description = poly["rcsb_polymer_entity"].get("pdbx_description") or "polymer entity"
            chains = ",".join(ident.get("auth_asym_ids") or [])
            records.append({
                "evidence_id": f"EV-PDB-{pdb_id}-{entity}",
                "uniprot": accession,
                "technique": technique,
                "source_kind": "deposit",
                "title": (entry.get("struct") or {}).get("title"),
                "construct": {"description": f"{description} (chains {chains})", "labels": []},
                "conditions": {
                    "environment": "in_vitro",
                    "temperature_c": _temperature_c(entry),
                    "ph": _ph(entry),
                    "buffer": None,
                    "salt_mM": None,
                    "ligands": ligands,
                    "applied_force_pn": None,
                    "notes": "Entry-level ligand list; oligosaccharides appear as branched entities. pH and temperature are null when not deposited in machine-readable fields.",
                },
                "observable": {
                    "type": "resolution" if resolution is not None else "structure",
                    "value": resolution,
                    "unit": "Å" if resolution is not None else None,
                    "uncertainty": None,
                },
                "mappings": [],
                "data_link": ENTRY_URL.format(pdb_id),
                # Coordinates, maps and restraints are deposited; raw images and FIDs are held elsewhere (EMPIAR, SBGrid, BMRbig).
                "data_level": "processed",
                "data_format": DATA_FORMAT.get(technique, "mmCIF"),
                "reader": None,
                "provenance": {
                    "source": NAME,
                    "doi": doi,
                    "deposit_id": pdb_id,
                    "retrieved": retrieved,
                    "url": ENTRY_URL.format(pdb_id),
                    "licence": LICENCE,
                },
            })
    return records


def load_raw(paths, accession: str) -> dict | None:
    path = paths.raw / f"pdb/{accession}.json"
    return read_json(path) if path.exists() else None
