"""The pipeline steps behind make download | ingest | map | models.

Each step is idempotent: it reads its inputs and rewrites its outputs under build/ (or data/raw/).
Nothing here edits a curated file.
"""

from __future__ import annotations

import collections
import urllib.error

from conformome import protein as protein_source
from conformome.common import (
    Paths, check, fetch_url, load_taxonomy, load_validators, load_yaml, read_json, record_download, today, write_json,
)
from conformome.mapping.conflicts import find_conflicts, not_compared
from conformome.mapping.curation import curation_for
from conformome.mapping.rules import apply_rules, curator_assignment
from conformome.molecule import molecule_type
from conformome import dna as dna_source
from conformome import rnacentral as rna_source
from conformome.sources import PRIMARY, for_type as sources_for
from conformome.sources import nakb as nakb_source
from conformome.sources import pdb as pdb_source

CURATION_URL = "https://github.com/matth55/conformome/blob/HEAD/curation/{}"
MODEL_URL = "https://files.rcsb.org/download/{}.{}"


def target_id(target: dict) -> str:
    """A targets.yaml entry names its molecule by molecule_id, or by uniprot for proteins."""
    return str(target.get("molecule_id") or target.get("uniprot"))


def target_accessions(paths: Paths) -> list[str]:
    """Molecules to build: targets.yaml (next to curation/) plus every curated molecule."""
    accs = {p.stem for p in paths.curation.glob("*.yaml")}
    targets = paths.curation.parent / "targets.yaml"
    if targets.exists():
        accs |= {target_id(t) for t in load_yaml(targets)["targets"]}
    return sorted(accs)


curated_accessions = target_accessions  # older name


IDENTITY_NAME = {"protein": "UniProt", "rna": "RNAcentral", "dna": "NAKB anchor", "complex": "complex"}


def target_entry(paths: Paths, acc: str) -> dict:
    targets = paths.curation.parent / "targets.yaml"
    entries = load_yaml(targets)["targets"] if targets.exists() else []
    return next((t for t in entries if target_id(t) == acc), {})


def fetch_identity(paths: Paths, acc: str, retrieved: str) -> None:
    """The molecule's own record: UniProt for proteins, RNAcentral for RNA, the NAKB anchor entry for DNA."""
    mtype = molecule_type(acc)
    if mtype == "protein":
        protein_source.fetch(paths, acc, retrieved)
    elif mtype == "rna":
        rna_source.fetch(paths, acc, retrieved)
    elif mtype == "dna":
        dna_source.fetch(paths, acc, retrieved, target_entry(paths, acc))
    else:
        raise NotImplementedError(f"{acc}: no download yet for complexes")


def molecule_record(paths: Paths, acc: str) -> dict:
    mtype = molecule_type(acc)
    module = {"protein": protein_source, "rna": rna_source, "dna": dna_source}.get(mtype)
    if module is None:
        raise NotImplementedError(f"{acc}: no ingest yet for complexes")
    raw = module.load_raw(paths, acc)
    if raw is None:
        raise FileNotFoundError(f"{acc}: no {IDENTITY_NAME[mtype]} download; run make download")
    return module.parse(raw, acc)


def _representatives(paths: Paths, accessions: list[str]) -> list[str]:
    reps = []
    for acc in accessions:
        for state in curation_for(paths.curation, acc).states:
            if state.get("representative_pdb"):
                reps.append(state["representative_pdb"])
    return sorted(set(reps))


def download(paths: Paths, accessions: list[str]) -> None:
    """Fetch UniProt and every implemented source. A failing optional source is logged, not fatal."""
    retrieved = today()
    failures = []
    for acc in accessions:
        mtype = molecule_type(acc)
        print(f"download {acc}: {IDENTITY_NAME[mtype]} entry")
        fetch_identity(paths, acc, retrieved)
        for module in sources_for(mtype):
            try:
                module.fetch(paths, acc, retrieved)
            except Exception as err:  # network or API failure: record it and carry on
                if module is PRIMARY[mtype]:
                    raise
                failures.append({"molecule_id": acc, "source": module.NAME, "error": f"{type(err).__name__}: {err}"})
                print(f"download {acc}: {module.NAME} FAILED ({err})")
                continue
            print(f"download {acc}: {module.NAME} ok")
    for pdb_id in _representatives(paths, accessions):
        for ext in ("cif", "pdb"):
            url = MODEL_URL.format(pdb_id, ext)
            try:
                data = fetch_url(url, cache_dir=paths.raw / "_cache")
            except urllib.error.HTTPError as err:
                print(f"download {pdb_id}.{ext}: not available ({err.code}); skipped")
                continue
            rel = f"pdb-files/{pdb_id}.{ext}"
            (paths.raw / rel).parent.mkdir(parents=True, exist_ok=True)
            (paths.raw / rel).write_bytes(data)
            record_download(paths, f"raw/{rel}", [url], data)
    write_json(paths.raw / "download_failures.json", failures)
    if failures:
        print(f"download: {len(failures)} optional source fetches failed; see data/raw/download_failures.json")


def ingest(paths: Paths, accessions: list[str]) -> None:
    validators = load_validators(paths.schema)
    taxonomy = load_taxonomy(paths.taxonomy / "techniques.yaml")
    for acc in accessions:
        out = paths.build / acc
        mtype = molecule_type(acc)
        protein = molecule_record(paths, acc)
        errors = check(validators["molecule"], protein)
        if errors:
            raise ValueError(f"{acc} molecule record invalid: {errors}")
        write_json(out / "molecule.json", protein)

        evidence, report = [], {"molecule_id": acc, "sources": {}}
        for module in sources_for(mtype):
            raw = module.load_raw(paths, acc)
            if raw is None:
                if module is PRIMARY[mtype]:
                    raise FileNotFoundError(f"{acc}: no {module.NAME} download; run make download")
                report["sources"][module.NAME] = {"status": "not downloaded", "evidence_items": 0, "not_ingested": []}
                continue
            records = module.parse(raw, acc, raw["retrieved"])
            for ev in records:
                errors = evidence_errors(validators, taxonomy, ev)
                if errors:
                    raise ValueError(f"{ev['evidence_id']} invalid: {errors}")
            skipped = module.not_ingested(raw, acc) if hasattr(module, "not_ingested") else []
            report["sources"][module.NAME] = {"status": "ingested", "evidence_items": len(records),
                                              "retrieved": raw["retrieved"], "not_ingested": skipped}
            evidence += records
        ids = [ev["evidence_id"] for ev in evidence]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"{acc}: duplicate evidence ids {dupes[:5]}")
        report["evidence_items"] = len(evidence)
        write_json(out / "evidence.json", evidence)
        write_json(out / "ingest.json", report)
        summary = ", ".join(f"{name} {s['evidence_items']}" for name, s in report["sources"].items())
        print(f"ingest {acc}: {len(evidence)} evidence items ({summary})")


def evidence_errors(validators: dict, taxonomy: dict, ev: dict) -> list[str]:
    errors = check(validators["evidence"], ev)
    tech = taxonomy.get(ev.get("technique"))
    if tech is None:
        errors.append(f"technique {ev.get('technique')} is not in taxonomy/techniques.yaml")
    elif ev["observable"]["type"] not in tech["observables"]:
        errors.append(f"observable {ev['observable']['type']} is not listed for technique {ev['technique']}")
    return errors


def coverage_grid(states: list[dict], evidence: list[dict], technique_order: list[str]) -> dict:
    present = {ev["technique"] for ev in evidence}
    techniques = [t for t in technique_order if t in present]
    cells = {s["state_id"]: {t: 0 for t in techniques} for s in states}
    for ev in evidence:
        for m in ev["mappings"]:
            if m["state_id"] in cells:
                cells[m["state_id"]][ev["technique"]] += 1
    # Best data level per cell (raw > processed > reported): which results can be re-analysed.
    rank = {"raw": 0, "processed": 1, "reported": 2}
    levels = {s["state_id"]: {} for s in states}
    for ev in evidence:
        for m in ev["mappings"]:
            if m["state_id"] in levels:
                cur = levels[m["state_id"]].get(ev["technique"])
                if cur is None or rank[ev["data_level"]] < rank[cur]:
                    levels[m["state_id"]][ev["technique"]] = ev["data_level"]
    single = [sid for sid, row in cells.items() if sum(1 for n in row.values() if n) == 1]
    unmapped = sum(1 for ev in evidence if not ev["mappings"])
    return {"techniques": techniques, "states": [s["state_id"] for s in states], "cells": cells, "data_levels": levels,
            "single_method_states": single, "unmapped_evidence": unmapped}


def map_protein(paths: Paths, acc: str) -> None:
    validators = load_validators(paths.schema)
    taxonomy_list = load_yaml(paths.taxonomy / "techniques.yaml")["techniques"]
    technique_order = [t["id"] for t in taxonomy_list]
    cur = curation_for(paths.curation, acc)
    if cur.errors:
        raise ValueError("; ".join(cur.errors))
    out = paths.build / acc
    evidence = read_json(out / "evidence.json")
    by_id = {ev["evidence_id"]: ev for ev in evidence}
    for a in cur.assignments:
        if a.get("pdb"):
            # A PDB ID stands for every entity of this protein in that entry.
            targets = [ev for ev in evidence if ev["provenance"]["source"] in (pdb_source.NAME, nakb_source.NAME)
                       and ev["provenance"]["deposit_id"] == str(a["pdb"])]
        else:
            targets = [by_id[a["evidence_id"]]] if a["evidence_id"] in by_id else []
        if not targets:
            raise ValueError(f"{acc}: assignment names unknown evidence {a.get('evidence_id') or a.get('pdb')}")
        for ev in targets:
            ev["mappings"].append(curator_assignment(cur.curator, a["state"], a["confidence"], a["justification"]))
    ambiguous = apply_rules(evidence, cur.rules)

    states = []
    for s in cur.states:
        states.append({
            "state_id": s["id"],
            "molecule_id": acc,
            "name": s["name"],
            "parent_state": s.get("parent"),
            "basis": s["basis"],
            "representative_model": None,
            "description": s.get("description", ""),
            "assumptions": s.get("assumptions") or [],
            "status": cur.status,
            "secondary_structure": s.get("secondary_structure"),
            "family_label": s.get("family_label"),
            "population": s.get("population"),
            "provenance": {
                "source": f"Conformome curation ({cur.source_file})",
                "doi": None,
                "deposit_id": None,
                "retrieved": cur.as_of,
                "url": CURATION_URL.format(cur.source_file),
                "licence": "Project licence (pending decision)",
            },
        })
    transitions = [dict(t, molecule_id=acc) for t in cur.transitions]

    for rec in states:
        for err in check(validators["state"], rec):
            raise ValueError(f"{rec['state_id']} invalid: {err}")
    for rec in transitions:
        for err in check(validators["transition"], rec):
            raise ValueError(f"{rec.get('transition_id')} invalid: {err}")

    mapped = {
        "molecule_id": acc,
        "curation": {"file": cur.source_file, "status": cur.status, "curator": cur.curator, "as_of": cur.as_of},
        "states": states,
        "transitions": transitions,
        "evidence": evidence,
        "ambiguous": ambiguous,
        "conflicts": find_conflicts(evidence),
        "not_compared": not_compared(evidence),
        "coverage": coverage_grid(states, evidence, technique_order),
    }
    # evidence.json stays as ingest wrote it; mapping reads it again on every run, so it must not change here.
    write_json(out / "mapped.json", mapped)
    mapped_states = sum(1 for ev in evidence if ev["mappings"])
    by_rule = sum(1 for ev in evidence for m in ev["mappings"] if m["who"].startswith("rule:"))
    print(f"map {acc}: {len(states)} states, {len(evidence)} evidence ({mapped_states} mapped, {by_rule} by rule, "
          f"{len(ambiguous)} ambiguous), {len(mapped['conflicts'])} conflicts, {len(transitions)} transitions")


def models(paths: Paths, acc: str) -> None:
    """Export observed state models: the representative PDB entry's own coordinates, as PDB and mmCIF."""
    validators = load_validators(paths.schema)
    out = paths.build / acc
    mapped = read_json(out / "mapped.json")
    evidence = mapped["evidence"]
    curated = {s["id"]: s for s in curation_for(paths.curation, acc).states}
    records = []
    for state in mapped["states"]:
        rep = curated[state["state_id"]].get("representative_pdb")
        if not rep:
            continue
        if state["basis"] != "observed":
            raise ValueError(f"{state['state_id']}: only observed states can export a representative in this version")
        ev = next((e for e in sorted(evidence, key=lambda e: e["evidence_id"])
                   if e["provenance"]["deposit_id"] == rep
                   and any(m["state_id"] == state["state_id"] for m in e["mappings"])), None)
        if ev is None:
            raise ValueError(f"{state['state_id']}: representative {rep} is not mapped to this state")
        for ext, fmt, header in (("cif", "mmCIF", _cif_header), ("pdb", "PDB", _pdb_header)):
            src = paths.raw / f"pdb-files/{rep}.{ext}"
            if not src.exists():
                print(f"models {state['state_id']}: {src.name} not downloaded; skipped")
                continue
            rel = f"{state['state_id']}.{ext}"
            dest = out / "models" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            body = src.read_text(encoding="utf-8", errors="replace")
            dest.write_text(header(state, rep) + body, encoding="utf-8")
            record = {
                "model_id": f"{state['state_id']}-{ext}",
                "molecule_id": acc,
                "state_id": state["state_id"],
                "format": fmt,
                "file": f"models/{acc}/{rel}",
                "basis": "observed",
                "constraints_used": [ev["evidence_id"]],
                "assumptions": None,
                "provenance": {
                    "source": "RCSB PDB",
                    "doi": ev["provenance"]["doi"],
                    "deposit_id": rep,
                    "retrieved": ev["provenance"]["retrieved"],
                    "url": f"https://files.rcsb.org/download/{rep}.{ext}",
                    "licence": ev["provenance"]["licence"],
                },
            }
            for err in check(validators["model"], record):
                raise ValueError(f"{record['model_id']} invalid: {err}")
            records.append(record)
        for s in mapped["states"]:
            if s["state_id"] == state["state_id"]:
                s["representative_model"] = f"{state['state_id']}-cif"
    write_json(out / "models.json", records)
    write_json(out / "mapped.json", mapped)
    print(f"models {acc}: {len(records)} model files")


def _cif_header(state: dict, rep: str) -> str:
    return (f"# conformome state: {state['state_id']} ({state['basis']})\n"
            f"# representative PDB entry: {rep}; coordinates unchanged from RCSB\n"
            "# assumptions: none (observed)\n")


def _pdb_header(state: dict, rep: str) -> str:
    return (f"REMARK 999 CONFORMOME state {state['state_id']} basis {state['basis']}\n"
            f"REMARK 999 representative PDB entry {rep}; coordinates unchanged from RCSB\n"
            "REMARK 999 assumptions: none (observed)\n")
