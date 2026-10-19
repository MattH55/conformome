"""NAKB (Nucleic Acid Knowledgebase): 3D structures of RNA and DNA, indexed from the PDB.

fetch: NAKB's Solr index (the endpoint its download page links to). Two queries, merged by PDB ID:
         - entries with a nucleic-acid chain of exactly the molecule's sequence (field naseq);
         - for RNA, entries with a chain that Rfam assigns to the molecule's family, from the
           molecule's organism (fields rfamids and polymer.taxid): other constructs of the same RNA.
       The molecule's sequence, Rfam family and taxon are stored in the raw file, so parse needs no network.
       Raw file: data/raw/nakb/<molecule_id>.json
parse: one evidence item per matching nucleic-acid entity, like the PDB source. The construct says
       whether the chain has the same sequence or is another construct of the same family and organism.
       Only fields NAKB takes from the PDB are used (title, method, resolution, chains, ligands, DOI);
       NAKB's own curated annotations are not copied.
"""

from __future__ import annotations

import json
import urllib.parse

from conformome.common import fetch_url
from conformome.molecule import nucleic_acid_info
from conformome.sources.base import conditions, evidence, load_raw as _load, save_raw
from conformome.sources.pdb import DATA_FORMAT, METHOD_TECHNIQUE

KEY = "nakb"
NAME = "NAKB"
LICENCE = "PDB-derived fields: CC0 1.0 (wwPDB archive); NAKB annotations not used"
IMPLEMENTED = True
MOLECULE_TYPES = {"rna", "dna"}
SOLR_URL = "https://www.nakb.org/node/solr/nakb/select"
ATLAS_URL = "https://www.nakb.org/atlas={}"
FIELDS = ("pdbid,ndbid,title,exptlmethod,resolution,DOI,polymer.entity_id,polymer.authorchains,polymer.description,"
          "polymer.type,polymer.taxid,polymer.sequence_canonical,rfamentity,rfamids,nonpolymers,released")
ROWS = 2000

# Chemical component IDs of ions, written as conditions.ions names. Concentrations are not in the PDB entry.
IONS = {"MG": "Mg2+", "K": "K+", "NA": "Na+", "CA": "Ca2+", "MN": "Mn2+", "SR": "Sr2+", "BA": "Ba2+",
        "ZN": "Zn2+", "CO": "Co2+", "NI": "Ni2+", "CD": "Cd2+", "TL": "Tl+", "RB": "Rb+", "CS": "Cs+",
        "LI": "Li+", "NH4": "NH4+", "NCO": "Co(NH3)6 3+", "CL": "Cl-", "IOD": "I-", "BR": "Br-"}


def query_url(q: str) -> str:
    return SOLR_URL + "?" + urllib.parse.urlencode({"q": q, "fl": FIELDS, "wt": "json", "rows": ROWS})


def query(paths, q: str) -> tuple[list[dict], str]:
    url = query_url(q)
    data = json.loads(fetch_url(url, cache_dir=paths.raw / "_cache"))
    return data["response"]["docs"], url


def fetch(paths, molecule_id: str, retrieved: str) -> dict:
    mol = nucleic_acid_info(paths, molecule_id)
    docs, url = query(paths, f'naseq:"{mol["sequence"]}"')
    urls = [url]
    for rfam in mol["rfam"]:
        more, url = query(paths, f"rfamids:{rfam} AND polymer.taxid:{mol['taxid']}")
        docs += more
        urls.append(url)
    entries = {d["pdbid"]: d for d in docs}
    raw = {"accession": molecule_id, "retrieved": retrieved, "url": urls[0], "molecule": mol,
           "entries": [entries[k] for k in sorted(entries)]}
    return save_raw(paths, KEY, molecule_id, raw, urls)


def load_raw(paths, molecule_id: str) -> dict | None:
    return _load(paths, KEY, molecule_id)


def _entities(doc: dict) -> list[dict]:
    """Per-entity view of NAKB's parallel per-polymer lists, with the Rfam families of each entity."""
    ids = doc.get("polymer.entity_id") or []
    rfam = {}
    for ent, fam in zip(doc.get("rfamentity") or [], doc.get("rfamids") or []):
        rfam.setdefault(str(ent), set()).add(fam)
    out = []
    for i, ent in enumerate(ids):
        def col(name, default=None):
            values = doc.get(name) or []
            return values[i] if i < len(values) else default
        out.append({"entity": str(ent), "type": col("polymer.type"), "chains": col("polymer.authorchains", ""),
                    "description": col("polymer.description") or "nucleic-acid entity", "taxid": col("polymer.taxid"),
                    "sequence": (col("polymer.sequence_canonical") or "").upper(), "rfam": rfam.get(str(ent), set())})
    return out


def _match(entity: dict, mol: dict) -> str | None:
    """Why this entity belongs on the page, or None."""
    if entity["type"] not in {"RNA", "DNA", "DNA/RNA"}:
        return None
    if entity["sequence"] == mol["sequence"]:
        return "same sequence"
    if mol["taxid"] and entity["taxid"] == mol["taxid"] and entity["rfam"] & set(mol["rfam"]):
        fams = ", ".join(sorted(entity["rfam"] & set(mol["rfam"])))
        return f"other construct of the same Rfam family ({fams}) and organism, {len(entity['sequence'])} nt"
    return None


def _method(doc: dict) -> str | None:
    methods = doc.get("exptlmethod") or []
    return methods[0].upper() if methods else None


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for doc in raw["entries"]:
        if METHOD_TECHNIQUE.get(_method(doc)) is None:
            out.append({"id": doc["pdbid"], "reason": f"experimental method has no technique mapping ({_method(doc)})"})
        elif not any(_match(e, raw["molecule"]) for e in _entities(doc)):
            out.append({"id": doc["pdbid"], "reason": "no nucleic-acid entity with the same sequence, or the same family and organism"})
    return out


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    mol = raw["molecule"]
    for doc in raw["entries"]:
        technique = METHOD_TECHNIQUE.get(_method(doc))
        if technique is None:
            continue
        pdb_id = doc["pdbid"]
        resolution = (doc.get("resolution") or [None])[0]
        comps = doc.get("nonpolymers") or []
        ions = [{"ion": IONS[c], "concentration_mM": None} for c in comps if c in IONS]
        ligands = sorted(c for c in comps if c not in IONS)
        for ent in _entities(doc):
            why = _match(ent, mol)
            if why is None:
                continue
            records.append(evidence(
                evidence_id=f"EV-NAKB-{pdb_id}-{ent['entity']}",
                accession=accession,
                technique=technique,
                source_kind="deposit",
                title=doc.get("title"),
                construct=f"{ent['description']} (chains {ent['chains']}); {why}",
                conds=conditions("in_vitro", ions=ions, ligands=ligands,
                                 notes="Ligands and ions are those modelled in the entry; concentrations, pH and "
                                       "temperature are not in NAKB's index."),
                obs_type="resolution" if resolution is not None else "structure",
                value=resolution, unit="Å",
                data_link=ATLAS_URL.format(pdb_id), data_level="processed",
                data_format=DATA_FORMAT.get(technique, "mmCIF"),
                source=NAME, doi=doc.get("DOI"), deposit_id=pdb_id, retrieved=retrieved,
                url=ATLAS_URL.format(pdb_id), licence=LICENCE,
            ))
    return records
