"""RNAcentral: molecule records for RNAs (name, organism, sequence, Rfam family and region).

RNA pages are keyed on the species-specific RNAcentral identifier (URS..._<taxid>), the RNA
counterpart of a UniProt accession: one sequence in one organism.
Raw file: data/raw/rnacentral/<id>.json (the species-specific RNA entry and its Rfam hits).
"""

from __future__ import annotations

import json

from conformome.common import fetch_url, read_json
from conformome.sources.base import commit_json

NAME = "RNAcentral"
LICENCE = "CC0 1.0 (verify)"
ENTRY_URL = "https://rnacentral.org/api/v1/rna/{}/?format=json"
RFAM_HITS_URL = "https://rnacentral.org/api/v1/rna/{}/rfam-hits/{}?format=json"
PAGE_URL = "https://rnacentral.org/rna/{}/{}"


def split(molecule_id: str) -> tuple[str, int]:
    """URS000080DF85_672 -> ("URS000080DF85", 672). RNA pages must name their organism."""
    urs, _, taxid = molecule_id.partition("_")
    if not taxid:
        raise ValueError(f"{molecule_id}: RNA pages are keyed on the species-specific ID (URS..._<taxid>)")
    return urs, int(taxid)


def fetch(paths, molecule_id: str, retrieved: str) -> dict:
    urs, taxid = split(molecule_id)
    entry_url = ENTRY_URL.format(molecule_id)
    hits_url = RFAM_HITS_URL.format(urs, taxid)
    entry = json.loads(fetch_url(entry_url, cache_dir=paths.raw / "_cache"))
    hits = json.loads(fetch_url(hits_url, cache_dir=paths.raw / "_cache")).get("results") or []
    raw = {"retrieved": retrieved, "url": entry_url, "entry": entry, "rfam_hits": hits}
    return commit_json(paths, f"rnacentral/{molecule_id}.json", raw, [entry_url, hits_url])


def rfam_hits(raw: dict) -> list[dict]:
    """Rfam families that cover the sequence: accession, names and the region (1-based, inclusive)."""
    out = []
    for h in raw["rfam_hits"]:
        model = h["rfam_model"]
        out.append({"rfam": model["rfam_model_id"], "short_name": model.get("short_name"),
                    "long_name": model.get("long_name") or model["rfam_model_id"],
                    "start": h["sequence_start"], "end": h["sequence_stop"],
                    "completeness": h.get("sequence_completeness")})
    return out


def parse(raw: dict, molecule_id: str) -> dict:
    entry = raw["entry"]
    urs, taxid = split(molecule_id)
    hits = rfam_hits(raw)
    sequence = entry["sequence"].upper()
    return {
        "molecule_id": molecule_id,
        "molecule_type": "rna",
        "identifiers": {"uniprot": None, "isoform": None, "rnacentral": molecule_id,
                        "rfam": hits[0]["rfam"] if hits else None, "genbank": None, "nakb": None, "pdb": []},
        "name": entry.get("short_description") or entry.get("description") or molecule_id,
        "gene": (entry.get("genes") or [None])[0],
        "organism": {"name": entry.get("species") or f"taxon {taxid}", "taxon_id": entry.get("taxid") or taxid},
        "sequence_length": len(sequence),
        "sequence": sequence,
        "modifications": [],
        "domains": [{"name": f"{h['long_name']} (Rfam {h['rfam']})", "start": h["start"], "end": h["end"]} for h in hits],
        "ligands": [],
        "components": [],
        "provenance": {
            "source": NAME,
            "doi": None,
            "deposit_id": molecule_id,
            "retrieved": raw["retrieved"],
            "url": PAGE_URL.format(urs, taxid),
            "licence": LICENCE,
        },
    }


def load_raw(paths, molecule_id: str) -> dict | None:
    path = paths.raw / f"rnacentral/{molecule_id}.json"
    return read_json(path) if path.exists() else None
