"""DNA structure pages: molecule records keyed on sequence, anchored on a PDB entry indexed by NAKB.

A DNA target in targets.yaml names its anchor entry:
    - {molecule_id: DNA-xxxxxxxxxxxx, anchor_pdb: 143D, name: "...", organism: {name: Homo sapiens, taxon_id: 9606}}
The sequence is the anchor's DNA chain (one DNA entity; for duplexes, the first strand), and
molecule_id must equal dna_id(sequence). organism is optional: synthetic constructs are null.
Raw file: data/raw/dna/<molecule_id>.json
"""

from __future__ import annotations

from conformome.common import read_json
from conformome.sources.base import commit_json
from conformome.molecule import dna_id
from conformome.sources import nakb

NAME = "NAKB"
LICENCE = nakb.LICENCE


def fetch(paths, molecule_id: str, retrieved: str, target: dict) -> dict:
    anchor = str(target.get("anchor_pdb") or "")
    if not anchor:
        raise ValueError(f"{molecule_id}: a DNA target needs anchor_pdb in targets.yaml")
    docs, url = nakb.query(paths, f"pdbid:{anchor}")
    if not docs:
        raise ValueError(f"{molecule_id}: anchor {anchor} is not in NAKB")
    dna = [e for e in nakb._entities(docs[0]) if e["type"] == "DNA"]
    if not dna:
        raise ValueError(f"{molecule_id}: anchor {anchor} has no DNA entity")
    sequence = dna[0]["sequence"]
    if dna_id(sequence) != molecule_id:
        raise ValueError(f"{molecule_id}: anchor {anchor} DNA sequence {sequence} has ID {dna_id(sequence)}")
    raw = {"retrieved": retrieved, "url": url, "target": target, "anchor": docs[0], "sequence": sequence,
           "taxid": dna[0]["taxid"]}
    return commit_json(paths, f"dna/{molecule_id}.json", raw, [url])


def parse(raw: dict, molecule_id: str) -> dict:
    target, anchor = raw["target"], raw["anchor"]
    organism = target.get("organism")
    return {
        "molecule_id": molecule_id,
        "molecule_type": "dna",
        "identifiers": {"uniprot": None, "isoform": None, "rnacentral": None, "rfam": None, "genbank": None,
                        "nakb": anchor.get("ndbid") or anchor["pdbid"], "pdb": [anchor["pdbid"]]},
        "name": target.get("name") or anchor.get("title") or molecule_id,
        "gene": None,
        "organism": ({"name": organism["name"], "taxon_id": organism["taxon_id"]} if organism else None),
        "sequence_length": len(raw["sequence"]),
        "sequence": raw["sequence"],
        "modifications": [],
        "domains": [],
        "ligands": [],
        "components": [],
        "provenance": {
            "source": NAME,
            "doi": anchor.get("DOI"),
            "deposit_id": anchor["pdbid"],
            "retrieved": raw["retrieved"],
            "url": nakb.ATLAS_URL.format(anchor["pdbid"]),
            "licence": LICENCE,
        },
    }


def load_raw(paths, molecule_id: str) -> dict | None:
    path = paths.raw / f"dna/{molecule_id}.json"
    return read_json(path) if path.exists() else None
