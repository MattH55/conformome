#!/usr/bin/env python3
"""Assemble the Conformome data deposit and zip it for Zenodo.

Writes release/ and conformome-data-0.1.0.zip. Does not upload and does not publish.
Evidence is kept only when docs/SOURCES.md says redistribute: yes and the stored
provenance.licence is listed in zenodo/redistribution.yaml. SMASH-BIO is denied.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

from conformome.common import default_paths, read_json
from conformome.validate import allowed_source_names, licence_redistributable, _redistribution

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
ZIP_PATH = ROOT / "conformome-data-0.1.0.zip"
VERSION = "0.1.0"
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/legalcode.txt"
RECORD_ORDER = ("molecule", "state", "transition", "evidence", "model")


def _zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Sorted names and a fixed timestamp, so two runs match byte for byte."""
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in sorted(members, key=lambda item: item[0]):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.flag_bits |= 0x800
            zf.writestr(info, data)
    return buf.getvalue()


def _public_records(records: list[dict], kept_ids: set[str]) -> list[dict]:
    out = []
    for record in records:
        record = json.loads(json.dumps(record))
        pop = record.get("population")
        if isinstance(pop, dict) and "evidence_ids" in pop:
            ids = [eid for eid in pop["evidence_ids"] if eid in kept_ids]
            if ids:
                pop["evidence_ids"] = ids
            else:
                record["population"] = None
        if isinstance(record.get("evidence_ids"), list):
            record["evidence_ids"] = [eid for eid in record["evidence_ids"] if eid in kept_ids]
        out.append(record)
    return out


def _keep(ev: dict, allowed_sources: set[str], allowed_licences: set[str],
          deny_phrases: list[str], deny_sources: set[str]) -> bool:
    prov = ev.get("provenance") or {}
    source = prov.get("source")
    return (source in allowed_sources and source not in deny_sources
            and licence_redistributable(prov.get("licence"), allowed_licences, deny_phrases))


def _line(record_type: str, record: dict) -> bytes:
    body = {"record_type": record_type, **record}
    return (json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _cc_by_text() -> tuple[str, bool]:
    try:
        req = urllib.request.Request(CC_BY_URL, headers={"User-Agent": "conformome-release"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        if "Attribution 4.0" not in text:
            raise ValueError("downloaded text is not the CC BY 4.0 legal code")
        return text if text.endswith("\n") else text + "\n", True
    except Exception as exc:
        return (f"Creative Commons Attribution 4.0 International: {CC_BY_URL}\n"
                f"(The legal code was not downloaded: {exc})\n", False)


def _readme(counts: dict, sources: list[tuple[str, str, int]], nucleic: list[str],
            licence_full: bool) -> str:
    source_rows = "\n".join(
        f"| {name} | {n} archived evidence records | {licence} |" for name, licence, n in sources)
    nucleic_lines = "\n".join(f"- {line}" for line in nucleic) or "- none in this build"
    licence_note = "" if licence_full else (
        "\nThe LICENSE file is a pointer to the CC BY 4.0 legal code because the legal text "
        "could not be downloaded during this build.\n")
    if counts["profiles"]:
        profiles_row = (f"| `profiles.zip` | {counts['profiles']} per-nucleotide reactivity profiles, one file per "
                        "chemical-probing evidence item (`profiles/<evidence_id>.json`), in the shape the website "
                        "serves under `downloads/profiles/`. |")
        profiles_note = f"`profiles.zip` holds {counts['profiles']} reactivity profiles (RMDB)."
    else:
        profiles_row = "| `profiles.zip` | Empty. This build has no per-nucleotide reactivity profiles. |"
        profiles_note = "`profiles.zip` has no entries."
    return f"""# Conformome pilot release v{VERSION}: data

An index of experimental and computational evidence on biomolecular conformation: proteins, RNA and DNA.
- Website: https://conformome.org
- Source code: https://github.com/MattH55/conformome, archived at doi:10.5281/zenodo.SOFTWARE_VERSION_DOI

Cite as: Halma MTJ. Conformome pilot release v{VERSION}: conformational-state evidence records for proteins and nucleic acids. Zenodo; 2026. doi:10.5281/zenodo.DATA_VERSION_DOI

## Contents

This deposit was assembled from the pipeline's `build/` directory; `manifest.json` records every raw input behind it.

Nucleic acids included:

{nucleic_lines}

Counts below are two different totals. **Corpus** is every evidence record in `build/`. **Archived** is the evidence written into `all-records.jsonl` after the licence filter. Evidence that may not be redistributed is left out of this deposit; the website still links it at the source.

- molecules: {counts['molecules']} ({counts['proteins']} proteins, {counts['rna']} RNA, {counts['dna']} DNA)
- evidence entries, corpus: {counts['corpus_evidence']}
- evidence entries, archived: {counts['archived_evidence']} (proteins {counts['evidence_protein']}, nucleic acids {counts['evidence_na']})
- techniques with archived entries: {counts['techniques']}
- curated molecules: {counts['curated']}; states: {counts['states']} (nucleic-acid states: {counts['states_na']})

## Files

| File | Contents |
| --- | --- |
| `all-records.jsonl` | Every archived record, one JSON object per line. `record_type` is `molecule`, `state`, `transition`, `evidence` or `model`. |
| `molecules.zip` | One JSON bundle per molecule (`molecules/<molecule_id>.json`). Evidence that failed the licence filter is omitted. |
{profiles_row}
| `schemas.zip` | JSON Schemas for every record type and their shared definitions. |
| `techniques.yaml` | Technique taxonomy. |
| `curation.zip` | Per-molecule curation files. Draft files are included with their status field unchanged. |
| `manifest.json` | Raw inputs: URL, retrieval date, SHA-256. |
| `CHANGELOG.md` | Schema notes for molecule records, ion conditions and nucleic-acid state fields. |
| `README.md` | This file. |
| `LICENSE` | CC BY 4.0. |
| `EXCLUDED.tsv` | Evidence left out, by source and stored licence string. |
| `SHA256SUMS` | SHA-256 of the other files in this deposit. |

## Licence and source attribution

Conformome's own records, curation files, schemas and taxonomy in this deposit are released under CC BY 4.0. The author still confirms that choice for the manuscript. Evidence records keep the source licence stored on each record.
{licence_note}
| Source | Archived evidence | Stored licence |
| --- | --- | --- |
{source_rows}

SMASH-BIO and literature are not redistributed. Any other evidence whose stored licence is absent from `zenodo/redistribution.yaml` is listed in `EXCLUDED.tsv` and is not in `all-records.jsonl`. BMRB, SASBDB and NAKB strings that contain "verify" are included because that is the string stored on the records; those terms still need the author's confirmation before a public Zenodo publish. MDDB is included only when the record carries the allowed project sentence.

{profiles_note}

## Placeholders for the author

- ORCID is not in this README.
- `SOFTWARE_VERSION_DOI` and `DATA_VERSION_DOI` are not assigned. This zip was not uploaded.

## Funding

This project has received funding from the European Union's Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No 859853 (AntiHelix).
"""


def _changelog() -> str:
    return """# Schema changelog

## Molecule records

A molecule record describes one protein, RNA, DNA or complex. Protein pages use the UniProt accession. Natural RNA uses an RNAcentral identifier. DNA oligonucleotides use `DNA-` plus a hash of the reference sequence.

## Conditions

Evidence conditions include temperature, pH, environment, ligands, applied force and an ion list. Unreported values stay null.

## Nucleic-acid states

A state may carry a dot-bracket secondary structure. G-quadruplex guanines in that string use `+`.
"""


def main() -> None:
    paths = default_paths()
    policy = _redistribution(paths)
    allowed_sources = allowed_source_names(paths)
    allowed_licences = set(policy["allow"])
    deny_phrases = policy["deny_if_contains"]
    deny_sources = set(policy["deny_sources"])

    build_dirs = sorted(p for p in paths.build.iterdir() if (p / "molecule.json").exists() and (p / "mapped.json").exists())
    if not build_dirs:
        raise SystemExit(f"no molecule builds in {paths.build}")

    jsonl = bytearray()
    molecule_members: list[tuple[str, bytes]] = []
    profile_members: list[tuple[str, bytes]] = []
    excluded: Counter[tuple[str, str]] = Counter()
    source_licences: dict[str, Counter[str]] = {}
    counts = {k: 0 for k in (
        "molecules", "proteins", "rna", "dna", "corpus_evidence", "archived_evidence",
        "evidence_protein", "evidence_na", "techniques", "curated", "states", "states_na")}
    techniques: set[str] = set()
    nucleic: list[str] = []

    for folder in build_dirs:
        molecule = read_json(folder / "molecule.json")
        mapped = read_json(folder / "mapped.json")
        models = read_json(folder / "models.json") if (folder / "models.json").exists() else []
        mtype = molecule.get("molecule_type") or "protein"
        acc = molecule.get("molecule_id") or folder.name
        counts["molecules"] += 1
        if mtype == "protein":
            counts["proteins"] += 1
        elif mtype == "rna":
            counts["rna"] += 1
            nucleic.append(f"{molecule.get('name') or acc} (RNA, `{acc}`)")
        elif mtype == "dna":
            counts["dna"] += 1
            nucleic.append(f"{molecule.get('name') or acc} (DNA, `{acc}`)")
        else:
            nucleic.append(f"{molecule.get('name') or acc} ({mtype}, `{acc}`)")

        states = list(mapped.get("states") or [])
        transitions = list(mapped.get("transitions") or [])
        evidence = list(mapped.get("evidence") or [])
        counts["states"] += len(states)
        if mtype in {"rna", "dna"}:
            counts["states_na"] += len(states)
        if (mapped.get("curation") or {}).get("status") not in {None, "uncurated"}:
            counts["curated"] += 1

        kept = []
        for ev in evidence:
            counts["corpus_evidence"] += 1
            prov = ev.get("provenance") or {}
            if _keep(ev, allowed_sources, allowed_licences, deny_phrases, deny_sources):
                kept.append(ev)
                source_licences.setdefault(prov.get("source") or "", Counter())[prov.get("licence") or ""] += 1
                techniques.add(ev.get("technique") or "")
                if mtype == "protein":
                    counts["evidence_protein"] += 1
                elif mtype in {"rna", "dna"}:
                    counts["evidence_na"] += 1
            else:
                excluded[(prov.get("source") or "(no source)", prov.get("licence") or "(none)")] += 1
        counts["archived_evidence"] += len(kept)
        kept_ids = {ev["evidence_id"] for ev in kept}
        # Reactivity profiles travel as one sidecar per evidence item, the same shape the site
        # serves under downloads/profiles/, so a record's data_ref resolves inside the deposit.
        for ev in kept:
            if ev.get("profile"):
                sidecar = {"evidence_id": ev["evidence_id"], "molecule_id": acc, "technique": ev["technique"],
                           "profile": ev["profile"], "conditions": ev["conditions"], "provenance": ev["provenance"]}
                profile_members.append((
                    f"profiles/{ev['evidence_id']}.json",
                    (json.dumps(sidecar, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
                ))
        conflicts = [c for c in (mapped.get("conflicts") or []) if all(eid in kept_ids for eid in c.get("evidence_ids") or [])]
        bundle = {
            "molecule_id": acc,
            "molecule": molecule,
            "curation": mapped.get("curation"),
            "states": _public_records(states, kept_ids),
            "transitions": _public_records(transitions, kept_ids),
            "evidence": kept,
            "conflicts": conflicts,
            "coverage": mapped.get("coverage"),
            "models": models,
        }
        molecule_members.append((
            f"molecules/{acc}.json",
            (json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
        ))
        jsonl += _line("molecule", molecule)
        for state in sorted(states, key=lambda s: s.get("state_id") or ""):
            jsonl += _line("state", state)
        for transition in sorted(transitions, key=lambda t: t.get("transition_id") or t.get("id") or ""):
            jsonl += _line("transition", transition)
        for ev in sorted(kept, key=lambda e: e.get("evidence_id") or ""):
            jsonl += _line("evidence", ev)
        for model in sorted(models, key=lambda m: m.get("model_id") or ""):
            jsonl += _line("model", model)

    counts["techniques"] = len(techniques)
    counts["profiles"] = len(profile_members)

    schema_members = [(f"schemas/{p.name}", p.read_bytes()) for p in sorted(paths.schema.glob("*.json"))]
    curation_members = [(f"curation/{p.name}", p.read_bytes()) for p in sorted(paths.curation.glob("*.yaml"))]
    techniques_bytes = (paths.taxonomy / "techniques.yaml").read_bytes()
    manifest_bytes = paths.manifest.read_bytes() if paths.manifest.exists() else b"{}\n"
    licence_text, licence_full = _cc_by_text()

    source_rows = []
    for name, licences in sorted(source_licences.items(), key=lambda kv: -sum(kv[1].values())):
        shown = "; ".join(f"{lic} ({n})" if len(licences) > 1 else lic for lic, n in licences.most_common())
        source_rows.append((name, shown, sum(licences.values())))

    readme = _readme(counts, source_rows, nucleic, licence_full)
    excluded_lines = ["source\tlicence\tn"]
    for (source, licence), n in sorted(excluded.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])):
        excluded_lines.append(f"{source}\t{licence}\t{n}")
    excluded_text = "\n".join(excluded_lines) + "\n"

    files = {
        "all-records.jsonl": bytes(jsonl),
        "molecules.zip": _zip_bytes(molecule_members),
        "profiles.zip": _zip_bytes(profile_members),
        "schemas.zip": _zip_bytes(schema_members),
        "techniques.yaml": techniques_bytes,
        "curation.zip": _zip_bytes(curation_members),
        "manifest.json": manifest_bytes,
        "CHANGELOG.md": _changelog().encode("utf-8"),
        "README.md": readme.encode("utf-8"),
        "LICENSE": licence_text.encode("utf-8"),
        "EXCLUDED.tsv": excluded_text.encode("utf-8"),
    }
    for raw in files["all-records.jsonl"].splitlines():
        record = json.loads(raw)
        if record.get("record_type") != "evidence":
            continue
        source = (record.get("provenance") or {}).get("source")
        if source in deny_sources:
            raise SystemExit(f"{source} evidence leaked into all-records.jsonl")
    sums = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items()))
    files["SHA256SUMS"] = sums.encode("utf-8")

    if RELEASE.exists():
        for child in RELEASE.iterdir():
            if child.is_file():
                child.unlink()
    RELEASE.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (RELEASE / name).write_bytes(data)
    ZIP_PATH.write_bytes(_zip_bytes([(name, data) for name, data in files.items()]))

    print(f"wrote {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes)")
    print(f"unpacked copy: {RELEASE}")
    print(f"molecules {counts['molecules']} (protein {counts['proteins']}, rna {counts['rna']}, dna {counts['dna']})")
    print(f"evidence corpus {counts['corpus_evidence']}; archived {counts['archived_evidence']}; "
          f"reactivity profiles {counts['profiles']}")
    print("excluded:")
    print(excluded_text, end="")
    if not licence_full:
        print("LICENSE is a pointer; the CC BY 4.0 legal code was not downloaded")
    print("not uploaded")


if __name__ == "__main__":
    main()
