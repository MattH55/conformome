"""UniProt: molecule records for proteins (name, organism, sequence, domains, ligands).

Raw file: data/raw/uniprot/<accession>.json (the UniProtKB entry, JSON).
Only the canonical isoform is recorded in this version; the schema allows an isoform field.
"""

from __future__ import annotations

import json

from conformome.common import fetch_url, read_json, record_download, write_json

NAME = "UniProtKB"
LICENCE = "CC BY 4.0 (UniProt)"
ENTRY_URL = "https://rest.uniprot.org/uniprotkb/{}.json"
PAGE_URL = "https://www.uniprot.org/uniprotkb/{}/entry"


def fetch(paths, accession: str, retrieved: str) -> dict:
    url = ENTRY_URL.format(accession)
    data = fetch_url(url, cache_dir=paths.raw / "_cache")
    raw = {"retrieved": retrieved, "url": url, "entry": json.loads(data)}
    rel = f"uniprot/{accession}.json"
    write_json(paths.raw / rel, raw)
    record_download(paths, f"raw/{rel}", [url], (paths.raw / rel).read_bytes())
    return raw


def parse(raw: dict, accession: str) -> dict:
    entry = raw["entry"]
    name = (entry.get("proteinDescription") or {}).get("recommendedName", {}).get("fullName", {}).get("value")
    genes = entry.get("genes") or []
    gene = genes[0]["geneName"]["value"] if genes and "geneName" in genes[0] else None
    organism = entry["organism"]
    sequence = entry["sequence"]["value"]
    domains, ligands, modifications = [], set(), []
    for feature in entry.get("features") or []:
        if feature.get("type") == "Domain":
            loc = feature["location"]
            domains.append({"name": feature.get("description", "domain"),
                            "start": loc["start"]["value"], "end": loc["end"]["value"]})
        if feature.get("type") == "Modified residue" and feature["location"]["start"].get("value"):
            modifications.append({"position": feature["location"]["start"]["value"], "kind": "ptm",
                                  "name": feature.get("description") or "modified residue", "source": NAME})
        if "ligand" in feature:
            ligands.add(feature["ligand"]["name"])
    return {
        "molecule_id": accession,
        "molecule_type": "protein",
        "identifiers": {"uniprot": accession.split("-")[0], "isoform": accession if "-" in accession else None,
                        "rnacentral": None, "rfam": None, "genbank": None, "nakb": None, "pdb": []},
        "name": name or accession,
        "gene": gene,
        "organism": {"name": organism["scientificName"], "taxon_id": organism["taxonId"]},
        "sequence_length": len(sequence),
        "sequence": sequence,
        "modifications": modifications,
        "domains": domains,
        "ligands": sorted(ligands),
        "components": [],
        "provenance": {
            "source": NAME,
            "doi": None,
            "deposit_id": accession,
            "retrieved": raw["retrieved"],
            "url": PAGE_URL.format(accession),
            "licence": LICENCE,
        },
    }


def load_raw(paths, accession: str) -> dict:
    return read_json(paths.raw / f"uniprot/{accession}.json")


def write_molecule(paths, accession: str, record: dict) -> None:
    write_json(paths.build / accession / "molecule.json", record)
