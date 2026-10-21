"""SASBDB: small-angle scattering profiles, with radius of gyration and maximum dimension.

fetch: SASBDB search page for the accession (the REST API has no UniProt filter), then the REST
       summary of each code found. Raw file: data/raw/sasbdb/<accession>.json
parse: one evidence item per entry whose sample contains a molecule with this UniProt code.
       Observable: Guinier radius of gyration with its error, in nm. P(r) Rg is not used.
       Salt, ionic species and construct variants are read from the deposit's own free text
       (sample name, buffer name, additive, comment, molecule names), because SASBDB records
       no structured salt field. Subscripts, dashes and spacing are normalised before matching.
"""

from __future__ import annotations

import json
import re

from conformome.common import fetch_url
from conformome.sources.base import conditions, evidence, load_raw as _load, number, save_raw

KEY = "sasbdb"
NAME = "SASBDB"
LICENCE = "CC BY 4.0 (verify)"
IMPLEMENTED = True
SEARCH_URL = "https://www.sasbdb.org/search/?q={}"
SUMMARY_URL = "https://www.sasbdb.org/rest-api/entry/summary/{}/"
PAGE_URL = "https://www.sasbdb.org/data/{}/"

# --- text normalisation -------------------------------------------------------------
# SASBDB free text mixes Unicode subscripts (K₂HPO₄), thin and non-breaking spaces, en
# dashes, and both "mM" and "M". Every pattern below runs on the normalised form.
_TRANSLATE = {ord(c): str(i) for i, c in enumerate("₀₁₂₃₄₅₆₇₈₉")}
_TRANSLATE.update({ord(c): str(i) for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")})
_TRANSLATE[ord("⁺")] = "+"
_TRANSLATE[ord("⁻")] = "-"
_TRANSLATE[0xB5] = "u"  # micro sign
_TRANSLATE[0x3BC] = "u"  # greek small letter mu
for _cp in (0xA0, 0x2000, 0x2009, 0x202F, 0x205F, 0x3000):  # nbsp and the thin spaces
    _TRANSLATE[_cp] = " "
for _cp in (0x2013, 0x2014, 0x2212, 0xFF0D):  # en dash, em dash, minus, fullwidth hyphen
    _TRANSLATE[_cp] = "-"


def normalize_text(value) -> str:
    """Unicode subscripts, dashes and odd spaces folded into plain, singly-spaced text."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).translate(_TRANSLATE)).strip()


# --- salts and ions -----------------------------------------------------------------
# A recognised salt is a metal or ammonium cation paired with a halide or a sulfate. The
# buffering agents SASBDB deposits name instead (HEPES, Tris, MES, acetate, citrate,
# phosphate, glycine) are deliberately absent: their concentration is not a salt
# concentration, and reading it as one made every alpha-synuclein deposit look identical.
_SALT_NAMES = [
    (r"NaCl|sodium\s+chloride", "Na+"),
    (r"KCl|potassium\s+chloride", "K+"),
    (r"LiCl|lithium\s+chloride", "Li+"),
    (r"CsCl|cae?sium\s+chloride", "Cs+"),
    (r"NaBr|sodium\s+bromide", "Na+"),
    (r"KBr|potassium\s+bromide", "K+"),
    (r"KF|potassium\s+fluoride", "K+"),
    (r"NaF|sodium\s+fluoride", "Na+"),
    (r"MgCl2|magnesium\s+chloride", "Mg2+"),
    (r"CaCl2|calcium\s+chloride", "Ca2+"),
    (r"MnCl2|manganese\s+chloride", "Mn2+"),
    (r"ZnCl2|zinc\s+chloride", "Zn2+"),
    (r"NH4Cl|ammonium\s+chloride", "NH4+"),
    (r"(?:guanidinium|guanidinum)(?:\s|-)?(?:chloride|Cl)|GdmCl|GdnHCl|guanidine\s+hydrochloride",
     "Gdm+"),
    (r"Na2SO4|sodium\s+sul(?:fa|ph)ate", "Na+"),
    (r"Li2SO4|lithium\s+sul(?:fa|ph)ate", "Li+"),
    (r"K2SO4|potassium\s+sul(?:fa|ph)ate", "K+"),
    (r"MgSO4|magnesium\s+sul(?:fa|ph)ate", "Mg2+"),
    (r"ZnSO4|zinc\s+sul(?:fa|ph)ate", "Zn2+"),
    (r"CuSO4|copper\s+sul(?:fa|ph)ate", "Cu2+"),
    (r"\(NH4\)2SO4|ammonium\s+sul(?:fa|ph)ate", "NH4+"),
]
# A molarity, never a percentage or an osmolality: the unit must not be followed by a letter.
_CONC = r"(\d+(?:\.\d+)?)\s*(mM|M|uM|nM)(?![A-Za-z])"
_TO_MILLIMOLAR = {"mm": 1.0, "m": 1000.0, "um": 0.001, "nm": 1e-6}
# Salt names are matched only as whole tokens: KF must not match inside AKF, MgCl2 must not
# match inside a longer formula.
_CONNECTOR = r"\s*(?:(?:of|containing|in)\s+)?"


def _mM(value: str, unit: str) -> float | None:
    """A concentration in the deposit's unit, returned in millimolar."""
    conc = number(value)
    factor = _TO_MILLIMOLAR.get((unit or "").lower())
    return None if conc is None or factor is None else conc * factor


def _salt_names(names: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9])(?:{names})(?![A-Za-z0-9])", re.IGNORECASE)


def _salt_concentrations(segment: str, names: str) -> list[float]:
    """The concentration a salt name carries in one component of a buffer string.

    A figure written before the name is the deposit's own and wins: reading a name first would
    let the next component's number be taken as this one's ("100 mM NaCl, 50 mM Tris", or the
    "200 mM NaCl 0.01 mM ZnSO4" of a buffer typed without commas). Only when nothing precedes
    the name is the name-first spelling ("NaCl 150 mM") used.
    """
    out = []
    for match in _salt_names(names).finditer(segment):
        before = re.search(_CONC + _CONNECTOR + "$", segment[:match.start()], re.IGNORECASE)
        if before:
            value = _mM(*before.groups())
            if value is not None:
                out.append(value)
            continue
        after = re.match(r"\s*[,;]?\s*(?:(?:of|at|in)\s+)?" + _CONC, segment[match.end():],
                         re.IGNORECASE)
        if after:
            value = _mM(*after.groups())
            if value is not None:
                out.append(value)
    return out


def _ions_in_one_field(text: str) -> dict[str, float | None]:
    """Ion to concentration within a single field. Salts of one ion add up."""
    known: dict[str, float] = {}
    unnamed: set[str] = set()
    # Buffer strings are components joined by commas or semicolons; reading them apart stops
    # one component's number being taken as another's.
    segments = [s for s in re.split(r"[,;]", text) if s.strip()]
    for names, ion in _SALT_NAMES:
        amounts = [a for segment in segments for a in _salt_concentrations(segment, names)]
        if amounts:
            known[ion] = known.get(ion, 0.0) + sum(amounts)
        elif any(_salt_names(names).search(segment) for segment in segments):
            unnamed.add(ion)
    out: dict[str, float | None] = {ion: round(value, 6) for ion, value in known.items()}
    out.update({ion: None for ion in unnamed - set(known)})
    return out


def salt_ions(texts) -> list[dict]:
    """Ions named with a concentration, plus ions named without one at null.

    Takes every free-text field of the deposit, because SASBDB puts the salt in whichever the
    depositor reached for: often the buffer name, sometimes only the sample name. A species
    seen without a number comes back with concentration_mM None, so what the deposit does not
    say stays unknown instead of guessed. Fields quote each other, so each is read on its own
    and the highest figure for an ion wins; that stops a buffer string written twice in the
    record from counting its salt twice.
    """
    seen: dict[str, float | None] = {}
    for raw in texts:
        text = normalize_text(raw)
        if not text:
            continue
        for ion, conc in _ions_in_one_field(text).items():
            best = seen.get(ion)
            if ion not in seen or (conc is not None and (best is None or conc > best)):
                seen[ion] = conc
    return [{"ion": ion, "concentration_mM": seen[ion]} for ion in sorted(seen)]


def total_salt_mM(ions: list[dict]) -> float | None:
    """The sum of the salt concentrations the deposit states. None when any is unknown."""
    if not ions or any(item["concentration_mM"] is None for item in ions):
        return None
    return round(sum(item["concentration_mM"] for item in ions), 6)


# --- construct variants ---------------------------------------------------------------
# Only tokens the deposit itself writes down. Nothing is inferred from the sequence, so a
# construct this parser cannot see is a construct left unlabelled, not a construct guessed.
_AA = "ACDEFGHIKLMNPQRSTVWYU"
# A point mutation: wild-type residue, position, mutant residue. The lookarounds keep the
# chemical formulas in the buffer names out of it (K2HPO4, NaH2PO4, D2O, MgCl2).
_MUTATION = re.compile(rf"(?<![\w-])([{_AA}]\d{{1,4}}[{_AA}])(?![\w-])")
# "at tau residue C317": a named position without a mutant residue.
_RESIDUE = re.compile(rf"\bresidues?\s+([{_AA}]\d{{1,4}})(?![\w-])")
_RANGE = re.compile(r"\b(?:residues|amino acids|aa)\s+(\d{1,5})\s*-\s*(\d{1,5})\b")
_ISOFORM = re.compile(r"\b(?:[Ii]soform\s+[A-Za-z][A-Za-z0-9-]*|\d[NV]\d[RK](?:\s+isoform)?|"
                      r"full[- ]?length|truncated?|fragment)\b", re.IGNORECASE)
_TAGS = re.compile(r"\b(?:His[-\s]?tag(?:ged)?|poly[-\s]histidine[-\s]tagged|GST[-\s]?tag(?:ged)?|"
                   r"MBP[-\s]?tag(?:ged)?|SUMO[-\s]?tag(?:ged)?|FLAG[-\s]?tag(?:ged)?)\b",
                   re.IGNORECASE)
_WILD_TYPE = re.compile(r"\b(?:wild[-\s]?type|WT|wildtype)\b", re.IGNORECASE)


def construct_labels(texts: list) -> list[str]:
    """Variant labels read out of the deposit's own text: mutations, isoforms, tags, ranges.

    Conflict detection compares the label set, so these decide which items are the same
    construct. Order is stable and duplicates are folded case-insensitively.
    """
    found: list[str] = []
    for raw in texts:
        text = normalize_text(raw)
        if not text:
            continue
        for match in _RANGE.finditer(text):
            found.append(f"{match.group(1)}-{match.group(2)}")
        for match in _MUTATION.finditer(text):
            found.append(match.group(1))
        found += _RESIDUE.findall(text)
        for pattern in (_ISOFORM, _TAGS):
            found += [match.group(0) for match in pattern.finditer(text)]
        if _WILD_TYPE.search(text):
            found.append("wild type")
    out: list[str] = []
    seen: set[str] = set()
    for token in found:
        key = token.lower().replace(" ", "-")
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def fetch(paths, accession: str, retrieved: str) -> dict:
    codes: set[str] = set()
    search_urls = []
    for page in range(1, 11):
        search = SEARCH_URL.format(accession) if page == 1 else SEARCH_URL.format(accession) + f"&page={page}"
        html = fetch_url(search, cache_dir=paths.raw / "_cache", headers={"Accept": "text/html"}).decode("utf-8", "replace")
        found = set(re.findall(r"SASD[A-Z0-9]{3}", html))
        search_urls.append(search)
        if not found or found <= codes:
            break
        codes |= found
    summaries = [json.loads(fetch_url(SUMMARY_URL.format(c), cache_dir=paths.raw / "_cache")) for c in sorted(codes)]
    urls = search_urls + [SUMMARY_URL.format(c) for c in sorted(codes)]
    return save_raw(paths, KEY, accession, {"accession": accession, "retrieved": retrieved, "search_url": search_urls[0],
                                            "summaries": summaries}, urls)


def load_raw(paths, accession: str) -> dict | None:
    return _load(paths, KEY, accession)


def _molecules(summary: dict) -> list[dict]:
    return ((summary.get("experiment") or {}).get("sample") or {}).get("molecule") or []


def not_ingested(raw: dict, accession: str) -> list[dict]:
    out = []
    for summary in raw["summaries"]:
        if not any(m.get("uniprot_code") == accession for m in _molecules(summary)):
            out.append({"id": summary["code"], "reason": "no molecule with this UniProt code in the sample"})
        elif _rg_nm(summary)[0] is None:
            out.append({"id": summary["code"], "reason": "no Guinier Rg (P(r) Rg is not compared with Guinier)"})
    return out


def _rg_nm(summary: dict) -> tuple[float | None, float | None]:
    """Guinier Rg only, in nm. A value above 30 nm is treated as ångström and divided by 10."""
    value, err = number(summary.get("guinier_rg")), number(summary.get("guinier_rg_error"))
    if value is None:
        return None, None
    if value > 30:
        if value <= 300:
            value = value / 10
            err = None if err is None else err / 10
        else:
            return None, None
    return value, err


def _sample_fields(experiment: dict) -> dict:
    """The deposit's own free-text fields, in the order they are read."""
    sample = experiment.get("sample") or {}
    buffer = sample.get("buffer") or {}
    return {"sample_name": sample.get("name"), "buffer_name": buffer.get("name"),
            "additive": buffer.get("additive"), "comment": buffer.get("comment"),
            "ph": buffer.get("ph") or buffer.get("pH")}


def parse(raw: dict, accession: str, retrieved: str) -> list[dict]:
    records = []
    for s in raw["summaries"]:
        molecules = _molecules(s)
        if not any(m.get("uniprot_code") == accession for m in molecules):
            continue
        experiment = s.get("experiment") or {}
        fields = _sample_fields(experiment)
        rg, err = _rg_nm(s)
        if rg is None:
            continue
        dmax = number(s.get("pddf_dmax"))
        others = [m.get("long_name") or m.get("short_name") for m in molecules if m.get("uniprot_code") != accession]
        mine = sorted({m.get("long_name") or m.get("short_name") or accession for m in molecules
                       if m.get("uniprot_code") == accession})
        # Salt, ionic species and variants are read from every field of the deposit that can name
        # them; the sample name is not a rare case, it is where SASBDB puts the salt.
        texts = [fields["sample_name"], fields["buffer_name"], fields["additive"], fields["comment"],
                 *[m.get("long_name") for m in molecules], *[m.get("short_name") for m in molecules],
                 *[m.get("molecule_description") for m in molecules], s.get("description")]
        ions = salt_ions(texts)
        project = s.get("project") or {}
        pub = project.get("publication") or {}
        notes = ["Other molecules in the sample are listed as partners; Rg is of the whole sample."]
        if ions:
            notes.append("Salts as deposited: " + ", ".join(
                item["ion"] + ("" if item["concentration_mM"] is None
                               else f" {item['concentration_mM']:g} mM")
                for item in ions) + ".")
        else:
            notes.append("No salt or ionic strength is stated in the deposit.")
        written = [t for t in (fields["buffer_name"], fields["sample_name"]) if t]
        if written:
            notes.append("Buffer and sample as written: " + " | ".join(str(t) for t in written) + ".")
        if dmax is not None:
            notes.append(f"Dmax {dmax:g} nm.")
        records.append(evidence(
            evidence_id=f"EV-SASBDB-{s['code']}",
            accession=accession,
            technique="saxs_sans",
            source_kind="deposit",
            title=project.get("title") or s.get("description"),
            construct=f"{'; '.join(mine)}" + (f" with {', '.join(o for o in others if o)}" if others else ""),
            labels=construct_labels(texts),
            conds=conditions("in_vitro", temperature_c=number(experiment.get("cell_temperature")),
                             ph=number(fields["ph"]), buffer=fields["buffer_name"],
                             salt_mM=total_salt_mM(ions), ions=ions,
                             ligands=[f"partner: {o}" for o in others if o],
                             notes=" ".join(notes)),
            obs_type="radius_of_gyration",
            value=rg, unit="nm", uncertainty=err,
            data_link=PAGE_URL.format(s["code"]), data_level="processed", data_format="scattering curve",
            source=NAME, doi=pub.get("doi"), deposit_id=s["code"], retrieved=retrieved,
            url=PAGE_URL.format(s["code"]), licence=LICENCE,
        ))
    return records
