"""DisProt: manually curated disordered regions, each with the experimental method behind it.

fetch: DisProt search API by UniProt accession. Raw file: data/raw/disprot/<accession>.json
parse: one evidence item per region annotated with a structural state or transition (for example
       "disorder", "disorder to order"). The ECO evidence code names the method, which is mapped to a
       technique; regions whose method has no mapping, or whose term is not structural, are reported.
"""

from __future__ import annotations

import json

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, load_raw as _load, save_raw

KEY = "disprot"
NAME = "DisProt"
LICENCE = "CC BY 4.0"
IMPLEMENTED = True
SEARCH_URL = "https://disprot.org/api/search?acc={}&format=json"
PAGE_URL = "https://disprot.org/{}"
STRUCTURAL = {"structural state", "structural transition"}

# Most specific phrases first. Matched against the lower-cased ECO evidence name.
# None means the name is recognised and deliberately not ingested (it would get the wrong basis).
ECO_TECHNIQUE = [
    ("negative stain", None),
    ("negative-stain", None),
    ("force spectroscopy", "force_spectroscopy"),
    ("single-molecule fret", "smfret"),
    ("smfret", "smfret"),
    ("fluorescence resonance energy transfer", "ensemble_fret"),
    ("hydrogen deuterium exchange", "hdx_ms"),
    ("electron paramagnetic resonance", "epr_deer"),
    ("relaxation", "nmr_dynamics"),
    ("nuclear magnetic resonance", "nmr_shifts"),
    ("circular dichroism", "cd"),
    ("infrared", "ftir_raman"),
    ("raman", "ftir_raman"),
    ("small-angle", "saxs_sans"),
    ("x-ray scattering", "saxs_sans"),
    ("x-ray crystallography", "xray"),
    ("electron microscopy", "cryoem"),
    ("gel electrophoresis", "gel_electrophoresis"),
    ("size-exclusion", "sec"),
    ("gel filtration", "sec"),
    ("proteolysis", "limited_proteolysis"),
    ("protease", "limited_proteolysis"),
    ("dynamic light scattering", "dls"),
    ("ultracentrifugation", "auc"),
    ("ion mobility", "native_ms"),
    ("molecular dynamics", "md"),
    ("fluorescence", "fluorescence"),
]


def technique_for(eco_name: str) -> str | None:
    name = (eco_name or "").lower()
    for phrase, tech in ECO_TECHNIQUE:
        if phrase in name:
            return tech
    return None


def fetch(paths, accession: str, retrieved: str) -> dict:
    url = SEARCH_URL.format(accession)
    data = json.loads(fetch_url(url, cache_dir=paths.raw / "_cache"))
    # Exact accession only. An isoform page (P10636-8) does not inherit the canonical entry,
    # and the canonical page does not mix isoform residue numbers into the canonical sequence.
    entries = [e for e in data.get("data", []) if (e.get("acc") or "") == accession]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "url": url,
                                            "entries": entries}, [url])


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _regions(raw: dict, accession: str):
    """Regions of this accession only. An isoform (P10636-8) is a different page from P10636."""
    for entry in raw["entries"]:
        if (entry.get("acc") or "") != accession:
            continue
        for region in entry.get("regions") or []:
            yield entry, region


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for _, r in _regions(raw, accession):
        if (r.get("term_namespace") or "").lower() not in STRUCTURAL:
            out.append({"id": r.get("region_id"), "reason": f"term not structural ({r.get('term_name')})"})
        elif technique_for(r.get("ec_name")) is None:
            out.append({"id": r.get("region_id"), "reason": f"method has no technique mapping ({r.get('ec_name')})"})
    return out


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for entry, r in _regions(raw, accession):
        technique = technique_for(r.get("ec_name"))
        if (r.get("term_namespace") or "").lower() not in STRUCTURAL or technique is None:
            continue
        start, end = r.get("start"), r.get("end")
        pmid = r.get("reference_id") if r.get("reference_source") == "pmid" else None
        disprot_id = entry.get("disprot_id")
        records.append(evidence(
            evidence_id=f"EV-DISPROT-{r['region_id']}",
            accession=accession,
            technique=technique,
            source_kind="literature",
            title=f"DisProt {disprot_id}: {r.get('term_name')}, residues {start}-{end}",
            construct=(f"residues {start}-{end} of {entry.get('acc') or accession}; evidence: {r.get('ec_name')}"),
            conds=conditions("in_vitro", notes="DisProt annotations do not record sample conditions."),
            obs_type="disorder_region",
            value=(end - start + 1) if isinstance(start, int) and isinstance(end, int) else None,
            unit="residues",
            data_level="reported", data_format=None,
            data_link=f"https://europepmc.org/article/MED/{pmid}" if pmid else PAGE_URL.format(disprot_id),
            source=NAME, doi=None, deposit_id=r["region_id"], retrieved=retrieved,
            url=PAGE_URL.format(disprot_id), licence=LICENCE,
        ))
    return records
