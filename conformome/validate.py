"""make validate: every check the CI gate runs. Returns a list of errors; empty means pass."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

from conformome.common import Paths, check, load_taxonomy, load_validators, load_yaml, read_json
from conformome.mapping.curation import curation_for
from conformome.pipeline import evidence_errors, target_accessions
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


def build_errors(paths: Paths, accessions: list[str]) -> list[str]:
    errors: list[str] = []
    validators = load_validators(paths.schema)
    taxonomy = load_taxonomy(paths.taxonomy / "techniques.yaml")
    table = sources_table(paths)
    for acc in accessions:
        out = paths.build / acc
        if not (out / "mapped.json").exists():
            errors.append(f"{acc}: build/{acc}/mapped.json missing; run make map")
            continue
        cur_path = paths.curation / f"{acc}.yaml"
        cur = curation_for(paths.curation, acc)
        errors += [f"{acc}: {e}" for e in cur.errors]
        rule_ids = {r["id"] for r in cur.rules}

        protein = read_json(out / "protein.json")
        errors += [f"{acc} protein: {e}" for e in check(validators["protein"], protein)]

        mapped = read_json(out / "mapped.json")
        states = {s["state_id"]: s for s in mapped["states"]}
        evidence_ids = {ev["evidence_id"] for ev in mapped["evidence"]}
        for s in mapped["states"]:
            errors += [f"{acc} state {s['state_id']}: {e}" for e in check(validators["state"], s)]
            if s["parent_state"] and s["parent_state"] not in states:
                errors.append(f"{acc} state {s['state_id']}: unknown parent {s['parent_state']}")
        for ev in mapped["evidence"]:
            errors += [f"{acc} {ev['evidence_id']}: {e}" for e in evidence_errors(validators, taxonomy, ev)]
            for m in ev["mappings"]:
                if m["state_id"] not in states:
                    errors.append(f"{acc} {ev['evidence_id']}: mapping names unknown state {m['state_id']}")
                if m["who"].startswith("rule:") and m["who"][5:] not in rule_ids:
                    errors.append(f"{acc} {ev['evidence_id']}: mapping cites rule {m['who'][5:]}, not in {cur_path.name}")
            if len({m["state_id"] for m in ev["mappings"]}) != len(ev["mappings"]):
                errors.append(f"{acc} {ev['evidence_id']}: mapped twice to the same state")
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


def downloads_redistribution_errors(paths: Paths) -> list[str]:
    """Evidence from a source whose licence forbids redistribution must not appear in any download."""
    table = sources_table(paths)
    forbidden = {REGISTRY[k].NAME for k, row in table.items()
                 if k in REGISTRY and row.get("redistribute", "").lower() == "no"}
    downloads = paths.site / "downloads"
    errors = []
    for bundle_file in sorted((downloads / "proteins").glob("*.json")) if downloads.exists() else []:
        for ev in read_json(bundle_file)["evidence"]:
            if ev["provenance"]["source"] in forbidden:
                errors.append(f"{bundle_file.name}: evidence {ev['evidence_id']} is from a source that may not be redistributed")
    lines = (downloads / "all-records.jsonl").read_text(encoding="utf-8").splitlines() if downloads.exists() and (downloads / "all-records.jsonl").exists() else []
    for line in lines:
        rec = json.loads(line)
        if rec.get("record_type") == "evidence" and rec["provenance"]["source"] in forbidden:
            errors.append(f"all-records.jsonl: evidence {rec['evidence_id']} is from a source that may not be redistributed")
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
    accs = [str(t.get("uniprot")) for t in targets]
    errors = [f"targets.yaml: {a} listed more than once" for a in sorted({a for a in accs if accs.count(a) > 1})]
    errors += [f"targets.yaml: {t.get('uniprot')} has no batch" for t in targets if not t.get("batch")]
    errors += [f"curation/{p.name} has no entry in targets.yaml" for p in sorted(paths.curation.glob("*.yaml"))
               if p.stem not in accs]
    return errors


def run(paths: Paths, accessions: list[str] | None = None, site: bool = True) -> list[str]:
    accessions = accessions or target_accessions(paths)
    errors = schema_errors(paths) + taxonomy_errors(paths) + sources_errors(paths) + targets_errors(paths)
    errors += build_errors(paths, accessions)
    if site:
        errors += site_errors(paths, accessions)
        errors += downloads_redistribution_errors(paths)
    return errors
