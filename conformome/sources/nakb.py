"""NAKB (Nucleic Acid Knowledgebase): 3D structures of RNA and DNA, indexed from the PDB.

fetch: NAKB's Solr index (the endpoint its download page links to), with candidates from three queries,
       merged by PDB ID:
         - entries with a nucleic-acid chain of exactly the molecule's sequence (field naseq);
         - entities RCSB's sequence search finds at 90% identity or more (RCSB Search API, mmseqs2);
         - for RNA, entries with a chain that Rfam assigns to the molecule's family, from the
           molecule's organism (fields rfamids and polymer.taxid).
       The organism is the molecule's own taxon, or, when RNAcentral files it as a synthetic construct
       (taxon 32630), the taxa NAKB gives its exact-sequence chains. The molecule's sequence, families,
       taxa and sequence-search hits are stored in the raw file, so parse needs no network.
       Raw file: data/raw/nakb/<molecule_id>.json
parse: one evidence item per matching nucleic-acid entity, like the PDB source: the same sequence; a
       similar sequence (90% identity over 90% of the molecule); or the same Rfam family and organism.
       The last two must be 0.8-1.25 times the molecule's length, so a larger RNA that contains this
       one (a whole intron around a domain, an mRNA in a ribosome) is not taken for another construct.
       The construct line says which rule matched.
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
RCSB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
SYNTHETIC_TAXON = 32630
MIN_IDENTITY = 0.9
MIN_COVERAGE = 0.9
LENGTH_RATIO = (0.8, 1.25)

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


def sequence_search(paths, sequence: str, kind: str) -> dict[str, dict]:
    """RCSB sequence search: {"<PDB>_<entity>": {identity, coverage, length}} at MIN_IDENTITY or more."""
    body = {"query": {"type": "terminal", "service": "sequence",
                      "parameters": {"evalue_cutoff": 1, "identity_cutoff": MIN_IDENTITY, "sequence_type": kind,
                                     "value": sequence}},
            "return_type": "polymer_entity",
            "request_options": {"return_all_hits": True, "results_verbosity": "verbose"}}
    data = fetch_url(RCSB_SEARCH_URL, body=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
                     cache_dir=paths.raw / "_cache")
    if not data.strip():  # RCSB answers 204 with an empty body when nothing matches
        return {}
    hits = {}
    for r in json.loads(data).get("result_set") or []:
        m = r["services"][0]["nodes"][0]["match_context"][0]
        hits[r["identifier"]] = {"identity": m["sequence_identity"], "length": m["subject_length"],
                                 "coverage": round((m["query_end"] - m["query_beg"] + 1) / len(sequence), 3)}
    return hits


def fetch(paths, molecule_id: str, retrieved: str) -> dict:
    mol = nucleic_acid_info(paths, molecule_id)
    docs, url = query(paths, f'naseq:"{mol["sequence"]}"')
    urls = [url, RCSB_SEARCH_URL]
    taxa = {mol["taxid"]} - {None, SYNTHETIC_TAXON}
    if not taxa:
        taxa = {e["taxid"] for d in docs for e in _entities(d) if e["sequence"] == mol["sequence"]} - {None, -1, SYNTHETIC_TAXON}
    similar = sequence_search(paths, mol["sequence"], mol["type"])
    pdb_ids = sorted({k.split("_")[0] for k in similar} - {d["pdbid"] for d in docs})
    for i in range(0, len(pdb_ids), 100):
        more, url = query(paths, "pdbid:(" + " OR ".join(pdb_ids[i:i + 100]) + ")")
        docs += more
    for rfam in mol["rfam"]:
        for taxid in sorted(taxa):
            more, url = query(paths, f"rfamids:{rfam} AND polymer.taxid:{taxid}")
            docs += more
            urls.append(url)
    mol = dict(mol, taxa=sorted(taxa), similar=similar)
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


def _match(entity: dict, mol: dict, pdb_id: str = "") -> str | None:
    """Why this entity belongs on the page, or None."""
    if entity["type"] not in {"RNA", "DNA", "DNA/RNA"}:
        return None
    if entity["sequence"] == mol["sequence"]:
        return "same sequence"
    n = len(entity["sequence"])
    if not LENGTH_RATIO[0] <= n / len(mol["sequence"]) <= LENGTH_RATIO[1]:
        return None
    hit = (mol.get("similar") or {}).get(f"{pdb_id}_{entity['entity']}")
    if hit and hit["identity"] >= MIN_IDENTITY and hit["coverage"] >= MIN_COVERAGE:
        return f"other construct, similar sequence ({hit['identity']:.0%} identity over {hit['coverage']:.0%}), {n} nt"
    taxa = set(mol.get("taxa", [mol.get("taxid")])) - {None}
    if entity["taxid"] in taxa and entity["rfam"] & set(mol["rfam"]):
        fams = ", ".join(sorted(entity["rfam"] & set(mol["rfam"])))
        return f"other construct of the same Rfam family ({fams}) and organism, {n} nt"
    return None


def _method(doc: dict) -> str | None:
    methods = doc.get("exptlmethod") or []
    return methods[0].upper() if methods else None


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for doc in raw["entries"]:
        if METHOD_TECHNIQUE.get(_method(doc)) is None:
            out.append({"id": doc["pdbid"], "reason": f"experimental method has no technique mapping ({_method(doc)})"})
        elif not any(_match(e, raw["molecule"], doc["pdbid"]) for e in _entities(doc)):
            out.append({"id": doc["pdbid"], "reason": "no nucleic-acid entity with the same or a similar sequence of similar "
                                                      "length, or of the same family and organism (larger RNAs containing "
                                                      "this one are left out)"})
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
            why = _match(ent, mol, pdb_id)
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
