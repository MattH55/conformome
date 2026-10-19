"""BMRB: NMR chemical shifts, relaxation and exchange data.

fetch: proteins: BMRB's UniProt-to-entry mapping (one shared file). RNA and DNA: BMRB's BLAST
       search on the molecule's sequence; entries whose alignment covers at least 90% of the
       sequence at 90% identity or more are kept, with the identity and coverage recorded.
       Then the entry_information and sample_conditions saveframes of each entry.
       Raw file: data/raw/bmrb/<accession>.json
parse: one evidence item per entry. Entries with relaxation data become `nmr_dynamics` /
       relaxation_rate, entries with exchange data `nmr_dynamics` / exchange_rate, and entries with
       only chemical shifts `nmr_shifts` / chemical_shift. Temperature and pH come from the first
       sample condition list.
"""

from __future__ import annotations

import json
import re

from conformome.common import fetch_url
from conformome.molecule import molecule_type, nucleic_acid_info
from conformome.sources.base import conditions, evidence, kelvin_to_c, load_raw as _load, number, save_raw

KEY = "bmrb"
NAME = "BMRB"
LICENCE = "CC0 1.0 (verify)"
IMPLEMENTED = True
MOLECULE_TYPES = {"protein", "rna", "dna"}
FASTA_URL = "https://api.bmrb.io/v2/search/fasta/{}?type={}"
MIN_COVERAGE = 0.9
MIN_IDENTITY = 90.0
MAP_URL = "https://api.bmrb.io/v2/mappings/uniprot/bmrb?format=json"
ENTRY_URL = ("https://api.bmrb.io/v2/entry/{}?saveframe_category=entry_information&saveframe_category=sample_conditions"
             "&saveframe_category=sample")
# Sample components that supply an ion. Chlorides and acetates give the ion at the salt concentration;
# phosphates, cacodylates and other buffers name the ion without a concentration.
CATIONS = [("potassium", "K+"), ("sodium", "Na+"), ("magnesium", "Mg2+"), ("calcium", "Ca2+"), ("lithium", "Li+"),
           ("manganese", "Mn2+"), ("ammonium", "NH4+"), ("caesium", "Cs+"), ("cesium", "Cs+"), ("rubidium", "Rb+"),
           ("strontium", "Sr2+"), ("zinc", "Zn2+")]
FORMULA_CATIONS = {"KCL": "K+", "NACL": "Na+", "LICL": "Li+", "CSCL": "Cs+", "RBCL": "Rb+", "NH4CL": "NH4+",
                   "MGCL2": "Mg2+", "CACL2": "Ca2+", "MNCL2": "Mn2+", "ZNCL2": "Zn2+", "SRCL2": "Sr2+",
                   "KPI": "K+", "NAPI": "Na+", "KOAC": "K+", "NAOAC": "Na+", "MG(OAC)2": "Mg2+"}
UNIT_TO_MM = {"m": 1000.0, "mm": 1.0, "um": 0.001, "µm": 0.001, "nm": 1e-6}
PAGE_URL = "https://bmrb.io/data_library/summary/index.php?bmrbId={}"


def sequence_hits(hits: list[dict], length: int) -> dict[str, dict]:
    """Best BLAST hit per entry that covers most of the query at high identity."""
    best: dict[str, dict] = {}
    for h in hits:
        coverage = (abs(h["q.end"] - h["q.start"]) + 1) / length
        if coverage < MIN_COVERAGE or h["percent_id"] < MIN_IDENTITY:
            continue
        cur = best.get(h["entry_id"])
        if cur is None or (h["percent_id"], coverage) > (cur["percent_id"], cur["coverage"]):
            best[h["entry_id"]] = {"percent_id": h["percent_id"], "coverage": round(coverage, 3), "entity_id": h["entity_id"]}
    return best


def fetch(paths, accession: str, retrieved: str) -> dict:
    urls = [MAP_URL]
    matches = None
    if molecule_type(accession) == "protein":
        mapping = json.loads(fetch_url(MAP_URL, cache_dir=paths.raw / "_cache"))
        ids = sorted({i for row in mapping if row["uniprot_id"] == accession for i in row["bmrb_ids"]}, key=int)
    else:
        info = nucleic_acid_info(paths, accession)
        url = FASTA_URL.format(info["sequence"], info["type"])
        urls = [url]
        matches = sequence_hits(json.loads(fetch_url(url, cache_dir=paths.raw / "_cache")), len(info["sequence"]))
        ids = sorted(matches, key=int)
    entries = {}
    for bmrb_id in ids:
        entries[bmrb_id] = json.loads(fetch_url(ENTRY_URL.format(bmrb_id), cache_dir=paths.raw / "_cache"))
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "map_url": urls[0],
                                            "sequence_matches": matches, "entries": entries},
                    urls + [ENTRY_URL.format("<id>")])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _frame(data: dict, bmrb_id: str, category: str) -> dict | None:
    frames = (data.get(bmrb_id) or {}).get(category) or []
    return frames[0] if frames else None


def _loop(frame: dict | None, category: str) -> list[dict]:
    for loop in (frame or {}).get("loops", []):
        if loop["category"] == category:
            return [dict(zip(loop["tags"], row)) for row in loop["data"]]
    return []


def _cation(name: str) -> tuple[str | None, bool]:
    """(ion, whether one ion per formula unit at the salt concentration) for a sample component name."""
    compact = re.sub(r"[\s_-]+", "", name).upper()
    if compact in FORMULA_CATIONS:
        ion = FORMULA_CATIONS[compact]
        return ion, compact.endswith(("CL", "CL2", "OAC", "(OAC)2"))
    low = name.lower()
    for word, ion in CATIONS:
        if re.search(rf"\b{word}\b", low):
            return ion, any(low.endswith(s) for s in (" chloride", " acetate"))
    return None, False


def ions(data: dict, bmrb_id: str) -> list[dict]:
    """Ions in the entry's first sample, with concentrations in mM where the component gives one."""
    frame = _frame(data, bmrb_id, "sample")
    totals: dict[str, float | None] = {}
    for row in _loop(frame, "_Sample_component"):
        ion, exact = _cation(row.get("Mol_common_name") or "")
        if ion is None:
            continue
        conc = number(row.get("Concentration_val"))
        factor = UNIT_TO_MM.get((row.get("Concentration_val_units") or "").strip().lower())
        mm = conc * factor if exact and conc is not None and factor is not None else None
        if ion not in totals:
            totals[ion] = mm
        elif mm is not None:
            totals[ion] = (totals[ion] or 0) + mm
    return [{"ion": ion, "concentration_mM": None if v is None else round(v, 3)} for ion, v in sorted(totals.items())]


def classify(datum_types: list[str]) -> tuple[str, str] | None:
    types = [t.lower() for t in datum_types]
    if any(k in t for t in types for k in ("relaxation", "heteronuclear noe", "order parameter", "t1rho")):
        return "nmr_dynamics", "relaxation_rate"
    if any("exchange" in t or "protection" in t for t in types):
        return "nmr_dynamics", "exchange_rate"
    if any("chemical shift" in t for t in types):
        return "nmr_shifts", "chemical_shift"
    return None


def _sample(data: dict, bmrb_id: str) -> tuple[float | None, float | None]:
    temp = ph = None
    for row in _loop(_frame(data, bmrb_id, "sample_conditions"), "_Sample_condition_variable"):
        kind = (row.get("Type") or "").lower()
        if kind == "temperature" and temp is None:
            unit = (row.get("Val_units") or "").strip().lower()
            temp = kelvin_to_c(row.get("Val")) if unit in ("k", "kelvin") else number(row.get("Val"))
        elif kind == "ph" and ph is None:
            ph = number(row.get("Val"))
    return temp, ph


def _info(data: dict, bmrb_id: str) -> tuple[str | None, list[str]]:
    frame = _frame(data, bmrb_id, "entry_information")
    tags = dict((t[0], t[1]) for t in (frame or {}).get("tags", []))
    title = re.sub(r"\s+", " ", tags.get("Title") or "").strip() or None
    types = [row["Type"] for row in _loop(frame, "_Datum")]
    return title, types


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for bmrb_id, data in raw["entries"].items():
        _, types = _info(data, bmrb_id)
        if classify(types) is None:
            out.append({"id": f"bmr{bmrb_id}", "reason": f"no shift, relaxation or exchange data ({', '.join(types) or 'no data types'})"})
    return out


def _match_note(raw: dict, bmrb_id: str) -> str:
    m = (raw.get("sequence_matches") or {}).get(bmrb_id)
    if not m:
        return ""
    if m["percent_id"] == 100 and m["coverage"] == 1:
        return f"; entity {m['entity_id']} contains this sequence"
    return f"; entity {m['entity_id']} matches {m['percent_id']:.0f}% over {m['coverage']:.0%} of this sequence (another construct)"


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for bmrb_id, data in raw["entries"].items():
        title, types = _info(data, bmrb_id)
        kind = classify(types)
        if kind is None:
            continue
        technique, obs = kind
        temp, ph = _sample(data, bmrb_id)
        records.append(evidence(
            evidence_id=f"EV-BMRB-{bmrb_id}",
            accession=accession,
            technique=technique,
            source_kind="deposit",
            title=title,
            construct="BMRB data: " + ", ".join(types[:6]) + _match_note(raw, bmrb_id),
            conds=conditions("in_vitro", temperature_c=temp, ph=ph, ions=ions(data, bmrb_id),
                             notes="From the first sample and sample condition list of the entry. Ion "
                                   "concentrations are given only for chloride and acetate salts."),
            obs_type=obs,
            data_link=PAGE_URL.format(bmrb_id), data_level="processed", data_format="NMR-STAR",
            source=NAME, doi=f"10.13018/BMR{bmrb_id}", deposit_id=f"bmr{bmrb_id}", retrieved=retrieved,
            url=PAGE_URL.format(bmrb_id), licence=LICENCE,
        ))
    return records
