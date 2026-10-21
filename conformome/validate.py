"""make validate: every check the CI gate runs. Returns a list of errors; empty means pass."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

from conformome.common import Paths, check, load_taxonomy, load_validators, load_yaml, read_json
from conformome.mapping.curation import curation_for
from conformome.molecule import (family_label_errors, load_vocabularies, molecule_type,
                                 secondary_structure_errors)
from conformome.pipeline import evidence_errors, target_accessions, target_id
from conformome.sources import REGISTRY

RESOLUTION_CLASSES = {"atomic", "residue", "domain", "global", "single_molecule"}


def schema_errors(paths: Paths) -> list[str]:
    errors = []
    for p in sorted(paths.schema.glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(read_json(p))
        except Exception as err:  # jsonschema raises SchemaError with a message
            errors.append(f"{p.name}: not a valid JSON Schema: {err.message if hasattr(err, 'message') else err}")
    return errors


def taxonomy_errors(paths: Paths) -> list[str]:
    errors = []
    for tid, t in load_taxonomy(paths.taxonomy / "techniques.yaml").items():
        if t.get("basis") not in {"observed", "inferred"}:
            errors.append(f"taxonomy {tid}: basis must be observed or inferred")
        if t.get("resolution_class") not in RESOLUTION_CLASSES:
            errors.append(f"taxonomy {tid}: unknown resolution_class {t.get('resolution_class')}")
        if not t.get("observables"):
            errors.append(f"taxonomy {tid}: no observables listed")
        if t.get("tier") not in {1, 2, 3, None} or ("tier" not in t):
            errors.append(f"taxonomy {tid}: tier must be 1, 2, 3 or null (predictions)")
        if t.get("tier") is None and not t.get("prediction"):
            errors.append(f"taxonomy {tid}: only predictions may have a null tier")
        for k in ("raw_location", "raw_format"):
            if not t.get(k):
                errors.append(f"taxonomy {tid}: {k} is required")
        if not isinstance(t.get("prediction"), bool):
            errors.append(f"taxonomy {tid}: prediction must be true or false")
    return errors


def sources_table(paths: Paths) -> dict[str, dict]:
    """Rows of docs/SOURCES.md, keyed by module name (the `Module` column)."""
    rows = {}
    lines = (paths.docs / "SOURCES.md").read_text(encoding="utf-8").splitlines()
    header = None
    for line in lines:
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if "module" in row:
            rows[row["module"].strip("`")] = row
    return rows


def sources_errors(paths: Paths) -> list[str]:
    errors = []
    table = sources_table(paths)
    for key, module in REGISTRY.items():
        row = table.get(key)
        if row is None:
            errors.append(f"docs/SOURCES.md has no row for source module {key}")
            continue
        if not row.get("licence") or "TBD" in row["licence"]:
            errors.append(f"docs/SOURCES.md: licence for {key} is missing or TBD")
        if row.get("redistribute", "").lower() not in {"yes", "no"}:
            errors.append(f"docs/SOURCES.md: redistribute for {key} must be yes or no")
        if row.get("status", "").lower().startswith("implemented") != module.IMPLEMENTED:
            errors.append(f"docs/SOURCES.md: status for {key} does not match IMPLEMENTED={module.IMPLEMENTED}")
    return errors


def state_content_errors(state: dict, molecule: dict, vocabularies: dict) -> list[str]:
    """Checks the schema cannot express: dot-bracket balance and pairing, vocabulary terms."""
    errors = []
    if state.get("secondary_structure"):
        if molecule.get("molecule_type") not in {"rna", "dna"}:
            errors.append("secondary_structure is only for RNA and DNA molecules")
        errors += secondary_structure_errors(state["secondary_structure"], molecule.get("sequence"))
    if state.get("family_label"):
        errors += family_label_errors(state["family_label"], vocabularies)
    return errors


def vocabulary_errors(paths: Paths) -> list[str]:
    validators = load_validators(paths.schema)
    errors = []
    for p in sorted((paths.taxonomy / "state_vocabularies").glob("*.yaml")):
        vocab = load_yaml(p)
        errors += [f"state_vocabularies/{p.name}: {e}" for e in check(validators["state_vocabulary"], vocab)]
        if vocab.get("id") != p.stem:
            errors.append(f"state_vocabularies/{p.name}: id {vocab.get('id')} does not match the file name")
    return errors


def build_errors(paths: Paths, accessions: list[str]) -> list[str]:
    errors: list[str] = []
    validators = load_validators(paths.schema)
    taxonomy = load_taxonomy(paths.taxonomy / "techniques.yaml")
    table = sources_table(paths)
    vocabularies = load_vocabularies(paths.taxonomy / "state_vocabularies")
    for acc in accessions:
        out = paths.build / acc
        if not (out / "mapped.json").exists():
            errors.append(f"{acc}: build/{acc}/mapped.json missing; run make map")
            continue
        cur_path = paths.curation / f"{acc}.yaml"
        cur = curation_for(paths.curation, acc)
        errors += [f"{acc}: {e}" for e in cur.errors]
        rule_ids = {r["id"] for r in cur.rules}

        molecule = read_json(out / "molecule.json")
        errors += [f"{acc} molecule: {e}" for e in check(validators["molecule"], molecule)]
        if molecule.get("molecule_type") != molecule_type(acc):
            errors.append(f"{acc} molecule: molecule_type {molecule.get('molecule_type')} does not match the ID scheme ({molecule_type(acc)})")

        mapped = read_json(out / "mapped.json")
        states = {s["state_id"]: s for s in mapped["states"]}
        evidence_ids = {ev["evidence_id"] for ev in mapped["evidence"]}
        curated_states = {s["id"]: s for s in cur.states}
        evidence_by_deposit: dict[str, list[dict]] = {}
        for ev in mapped["evidence"]:
            evidence_by_deposit.setdefault(str(ev["provenance"].get("deposit_id") or ""), []).append(ev)
        for s in mapped["states"]:
            errors += [f"{acc} state {s['state_id']}: {e}" for e in check(validators["state"], s)]
            raw_state = curated_states.get(s["state_id"], {})
            for assumption in raw_state.get("assumptions") or []:
                if not str(assumption).strip():
                    errors.append(f"{acc} state {s['state_id']}: assumption is empty")
            if s["basis"] == "observed":
                rep = str(raw_state.get("representative_pdb") or "")
                if not rep:
                    errors.append(f"{acc} state {s['state_id']}: an observed state must cite representative_pdb")
                else:
                    reps = evidence_by_deposit.get(rep, [])
                    if not reps:
                        errors.append(f"{acc} state {s['state_id']}: representative {rep} has no evidence in this build")
                    for ev in reps:
                        basis = (taxonomy.get(ev["technique"]) or {}).get("basis")
                        if basis != "observed":
                            errors.append(f"{acc} state {s['state_id']}: representative {rep} is {ev['technique']}, basis {basis}")
                observed_support = [ev for ev in mapped["evidence"]
                                    if any(m["state_id"] == s["state_id"] for m in ev["mappings"])
                                    and (taxonomy.get(ev["technique"]) or {}).get("basis") == "observed"]
                if not observed_support:
                    errors.append(f"{acc} state {s['state_id']}: observed state has no evidence from an observed technique")
            if s["parent_state"] and s["parent_state"] not in states:
                errors.append(f"{acc} state {s['state_id']}: unknown parent {s['parent_state']}")
            errors += [f"{acc} state {s['state_id']}: {e}" for e in state_content_errors(s, molecule, vocabularies)]
        for ev in mapped["evidence"]:
            errors += [f"{acc} {ev['evidence_id']}: {e}" for e in evidence_errors(validators, taxonomy, ev)]
            for m in ev["mappings"]:
                if m["state_id"] not in states:
                    errors.append(f"{acc} {ev['evidence_id']}: mapping names unknown state {m['state_id']}")
                if m["who"].startswith("rule:") and m["who"][5:] not in rule_ids:
                    errors.append(f"{acc} {ev['evidence_id']}: mapping cites rule {m['who'][5:]}, not in {cur_path.name}")
            states_for_item = {m["state_id"] for m in ev["mappings"]}
            if len(states_for_item) != len(ev["mappings"]):
                errors.append(f"{acc} {ev['evidence_id']}: mapped twice to the same state")
            if len(states_for_item) > 1:
                errors.append(f"{acc} {ev['evidence_id']}: mapped to more than one state ({', '.join(sorted(states_for_item))})")
        for amb in mapped.get("ambiguous", []):
            if amb["evidence_id"] not in evidence_ids:
                errors.append(f"{acc} ambiguous item {amb['evidence_id']}: unknown evidence")
        for t in mapped["transitions"]:
            errors += [f"{acc} transition {t.get('transition_id')}: {e}" for e in check(validators["transition"], t)]
            for side in ("from_state", "to_state"):
                if t.get(side) not in states:
                    errors.append(f"{acc} transition {t.get('transition_id')}: unknown {side} {t.get(side)}")
            for eid in t.get("evidence_ids", []):
                if eid not in evidence_ids:
                    errors.append(f"{acc} transition {t.get('transition_id')}: unknown evidence {eid}")

        models = read_json(out / "models.json") if (out / "models.json").exists() else []
        for m in models:
            errors += [f"{acc} model {m['model_id']}: {e}" for e in check(validators["model"], m)]
            if m["state_id"] not in states:
                errors.append(f"{acc} model {m['model_id']}: unknown state {m['state_id']}")
            if not (out / "models" / Path(m["file"]).name).exists():
                errors.append(f"{acc} model {m['model_id']}: file {m['file']} missing from build")
        for s in mapped["states"]:
            if s["representative_model"] and s["representative_model"] not in {m["model_id"] for m in models}:
                errors.append(f"{acc} state {s['state_id']}: representative_model has no model record")
        if mapped["curation"]["status"] == "reviewed" and any(s["status"] != "reviewed" for s in mapped["states"]):
            errors.append(f"{acc}: curation is reviewed but a state is still draft")
        for c in mapped["conflicts"]:
            for eid in c["evidence_ids"]:
                if eid not in evidence_ids:
                    errors.append(f"{acc} conflict {c['conflict_id']}: unknown evidence {eid}")
    return errors


def _redistribution(paths: Paths) -> dict:
    path = paths.docs.parent / "zenodo" / "redistribution.yaml"
    if not path.exists():
        return {"allow": [], "deny_if_contains": [], "deny_sources": []}
    data = load_yaml(path) or {}
    return {
        "allow": list(data.get("allow") or []),
        "deny_if_contains": [str(p).lower() for p in (data.get("deny_if_contains") or [])],
        "deny_sources": set(data.get("deny_sources") or []),
    }


def licence_redistributable(licence: str | None, allowed: set[str], deny_phrases: tuple[str, ...] | list[str]) -> bool:
    """Keep a record only when its stored licence string is on the allow-list and not restrictive."""
    text = (licence or "").strip()
    if not text or text not in allowed:
        return False
    low = text.lower()
    return not any(phrase in low for phrase in deny_phrases)


def allowed_source_names(paths: Paths) -> set[str]:
    """Fail closed: only a SOURCES.md row with redistribute yes, plus Conformome's own curation."""
    table = sources_table(paths)
    names = {REGISTRY[key].NAME for key, row in table.items()
             if key in REGISTRY and row.get("redistribute", "").lower() == "yes"}
    names.add("Conformome curation")
    return names


def _forbidden_source(record: dict, allowed_sources: set[str], allowed_licences: set[str],
                      deny_phrases: list[str], deny_sources: set[str]) -> str | None:
    prov = record.get("provenance") or {}
    source = prov.get("source")
    if not source:
        return None
    if (source not in allowed_sources or source in deny_sources
            or not licence_redistributable(prov.get("licence"), allowed_licences, deny_phrases)):
        return source
    return None


def downloads_redistribution_errors(paths: Paths) -> list[str]:
    """No non-redistributable evidence may appear under downloads/ or in search/evidence.json."""
    allowed = allowed_source_names(paths)
    policy = _redistribution(paths)
    allowed_licences = set(policy["allow"])
    deny_phrases = policy["deny_if_contains"]
    deny_sources = policy["deny_sources"]
    errors = []

    def reject(where: str, record: dict) -> None:
        source = _forbidden_source(record, allowed, allowed_licences, deny_phrases, deny_sources)
        if source:
            errors.append(f"{where}: evidence {record.get('evidence_id', '')} from {source} is not redistributable")

    downloads = paths.site / "downloads"
    if downloads.exists():
        jsonl = downloads / "all-records.jsonl"
        if jsonl.exists():
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("record_type") == "evidence":
                    reject("all-records.jsonl", record)
        for bundle_file in sorted(downloads.rglob("*.json")):
            bundle = read_json(bundle_file)
            if not isinstance(bundle, dict) or "evidence" not in bundle:
                continue
            for ev in bundle["evidence"]:
                reject(bundle_file.name, ev)
            kept = {ev["evidence_id"] for ev in bundle["evidence"]}
            for conflict in bundle.get("conflicts") or []:
                leaked = [eid for eid in conflict.get("evidence_ids") or [] if eid not in kept]
                if leaked:
                    errors.append(f"{bundle_file.name}: conflict {conflict.get('conflict_id')} cites excluded evidence {leaked[0]}")
            for state in bundle.get("states") or []:
                pop = state.get("population") if isinstance(state.get("population"), dict) else None
                leaked = [eid for eid in (pop or {}).get("evidence_ids") or [] if eid not in kept]
                if leaked:
                    errors.append(f"{bundle_file.name}: state {state.get('state_id')} population cites excluded evidence {leaked[0]}")
            for transition in bundle.get("transitions") or []:
                leaked = [eid for eid in transition.get("evidence_ids") or [] if eid not in kept]
                if leaked:
                    errors.append(f"{bundle_file.name}: transition {transition.get('transition_id')} cites excluded evidence {leaked[0]}")
    search = paths.site / "search" / "evidence.json"
    if search.exists():
        for row in read_json(search):
            source = row[3] if isinstance(row, list) and len(row) > 3 else None
            if source and (source not in allowed):
                errors.append(f"search/evidence.json: {row[0]} from {source} is not redistributable")
    return errors


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[tuple[str, str]] = []  # (attr, value)
        self.ids: set[str] = set()
        self.has_viewer = False
        self.has_grid = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src"):
            if d.get(attr):
                self.refs.append((attr, d[attr]))
        if d.get("id"):
            self.ids.add(d["id"])
        self.has_viewer = self.has_viewer or d.get("id") == "viewer"
        self.has_grid = self.has_grid or d.get("id") == "coverage-grid"


def site_errors(paths: Paths, accessions: list[str]) -> list[str]:
    site = paths.site
    if not (site / "index.html").exists():
        return [f"site not built at {site}; run make site"]
    errors = []
    pages = list(site.rglob("*.html"))
    for page in pages:
        parser = _Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for attr, ref in parser.refs:
            if re.match(r"^(https?:|mailto:|data:)", ref) or ref.startswith("#"):
                continue
            target = (page.parent / ref.split("#")[0].split("?")[0]).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append(f"{page.relative_to(site)}: broken {attr} {ref}")
    for acc in accessions:
        page = site / "protein" / acc / "index.html"
        if not page.exists():
            errors.append(f"protein page for {acc} missing")
            continue
        parser = _Links()
        parser.feed(page.read_text(encoding="utf-8"))
        if not parser.has_grid:
            errors.append(f"{acc}: protein page has no coverage grid")
        models_file = paths.build / acc / "models.json"
        if models_file.exists() and read_json(models_file) and not parser.has_viewer:
            errors.append(f"{acc}: protein page has models but no viewer")
    search = site / "search"
    if not (search / "index.html").exists() or not (search / "proteins.json").exists():
        errors.append("search page or its protein index is missing")
    else:
        listed = {p["acc"] for p in read_json(search / "proteins.json")}
        if listed != set(accessions):
            errors.append(f"search index lists {len(listed)} proteins, expected {len(set(accessions))}")
        if not (search / "evidence.json").exists():
            errors.append("search evidence index is missing")
    if (site / "CNAME").read_text().strip() != "conformome.org":
        errors.append("site/dist/CNAME must contain conformome.org")
    return errors


def targets_errors(paths: Paths) -> list[str]:
    """Every curated protein must be listed in targets.yaml, once, with a reason for inclusion."""
    path = paths.curation.parent / "targets.yaml"
    if not path.exists():
        return []
    targets = load_yaml(path)["targets"]
    accs = [target_id(t) for t in targets]
    errors = [f"targets.yaml: {a} listed more than once" for a in sorted({a for a in accs if accs.count(a) > 1})]
    errors += [f"targets.yaml: {target_id(t)} has no batch" for t in targets if not t.get("batch")]
    errors += [f"curation/{p.name} has no entry in targets.yaml" for p in sorted(paths.curation.glob("*.yaml"))
               if p.stem not in accs]
    return errors


def study_errors(paths: Paths) -> list[str]:
    """Every studies/<name>/ directory: schemas, and the cross-references the schemas cannot check."""
    from conformome.conformations import studies

    root = paths.curation.parent / "studies"
    errors = []
    for d in sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []:
        study = studies.load(d)
        errors += [f"studies/{d.name}: {e}" for e in studies.schema_errors(study, paths.schema)]
        errors += [f"studies/{d.name}: {e}" for e in studies.integrity_errors(study)]
    return errors


def run(paths: Paths, accessions: list[str] | None = None, site: bool = True) -> list[str]:
    accessions = accessions or target_accessions(paths)
    errors = schema_errors(paths) + taxonomy_errors(paths) + vocabulary_errors(paths) + sources_errors(paths) + targets_errors(paths)
    errors += study_errors(paths)
    errors += build_errors(paths, accessions)
    if site:
        errors += site_errors(paths, accessions)
        errors += downloads_redistribution_errors(paths)
    return errors
