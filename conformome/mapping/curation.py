"""Curation files: one YAML per molecule, owned by the curator.

Shape (see curation/README.md):
    uniprot (proteins) or molecule_id, name, curator, status (draft|reviewed), as_of, states, assignments, rules, transitions
Assignments are the curator's evidence-to-state decisions. Each one becomes a mapping record
with who = "curator:<curator>", the stated confidence and justification.
Rules are the curator's declarative criteria (technique, source, ligands, title words). Each match
becomes a mapping record with who = "rule:<rule id>" and the rule's confidence and justification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from conformome.common import load_yaml

CONFIDENCE = {"high", "medium", "low"}
STATE_KEYS = {"id", "name", "basis", "representative_pdb", "description", "assumptions", "parent",
              "secondary_structure", "family_label", "population"}
MATCH_KEYS = {"techniques", "sources", "observable_types", "environment", "ligands_any", "ligands_all",
              "ligands_none", "no_ligands", "ligand_text_any", "ligand_text_none", "title_any", "title_all",
              "title_none", "publication_title_any"}


@dataclass
class Curation:
    uniprot: str
    name: str
    curator: str
    status: str
    states: list[dict]
    transitions: list[dict]
    assignments: list[dict]
    rules: list[dict]
    as_of: str
    source_file: str
    errors: list[str] = field(default_factory=list)


def load_curation(path: Path, expected_uniprot: str | None = None) -> Curation:
    data = load_yaml(path)
    errors: list[str] = []
    uniprot = data.get("molecule_id") or data.get("uniprot")
    if not data.get("as_of"):
        errors.append(f"{path.name}: as_of date is required (the date the curation was last changed)")
    if expected_uniprot and uniprot != expected_uniprot:
        errors.append(f"{path.name}: molecule {uniprot} does not match file name {expected_uniprot}")
    states = data.get("states") or []
    state_ids = [s["id"] for s in states]
    if len(set(state_ids)) != len(state_ids):
        errors.append(f"{path.name}: duplicate state ids")
    for s in states:
        parent = s.get("parent")
        if parent and parent not in state_ids:
            errors.append(f"{path.name}: state {s['id']} has unknown parent {parent}")
        if s.get("basis") not in {"observed", "inferred"}:
            errors.append(f"{path.name}: state {s['id']} basis must be observed or inferred")
        unknown = set(s) - STATE_KEYS
        if unknown:
            errors.append(f"{path.name}: state {s['id']} has unknown keys {sorted(unknown)}")
    for a in data.get("assignments") or []:
        if bool(a.get("evidence_id")) == bool(a.get("pdb")):
            errors.append(f"{path.name}: assignment {a} needs exactly one of evidence_id or pdb")
        if a.get("state") not in state_ids:
            errors.append(f"{path.name}: assignment {a.get('evidence_id') or a.get('pdb')} names unknown state {a.get('state')}")
        if a.get("confidence") not in CONFIDENCE:
            errors.append(f"{path.name}: assignment {a.get('evidence_id') or a.get('pdb')} has invalid confidence")
        if not str(a.get("justification", "")).strip():
            errors.append(f"{path.name}: assignment {a.get('evidence_id') or a.get('pdb')} has no justification")
    rule_ids = [r.get("id") for r in data.get("rules") or []]
    if len(set(rule_ids)) != len(rule_ids):
        errors.append(f"{path.name}: duplicate rule ids")
    for r in data.get("rules") or []:
        rid = r.get("id")
        if not rid or not str(rid).replace("-", "").replace("_", "").isalnum():
            errors.append(f"{path.name}: rule id {rid!r} must be letters, digits, '-' or '_'")
        if r.get("state") not in state_ids:
            errors.append(f"{path.name}: rule {rid} names unknown state {r.get('state')}")
        if r.get("confidence") not in CONFIDENCE:
            errors.append(f"{path.name}: rule {rid} has invalid confidence")
        if not str(r.get("justification", "")).strip():
            errors.append(f"{path.name}: rule {rid} has no justification")
        match = r.get("match") or {}
        if not match:
            errors.append(f"{path.name}: rule {rid} has no match criteria")
        unknown = set(match) - MATCH_KEYS
        if unknown:
            errors.append(f"{path.name}: rule {rid} has unknown match keys {sorted(unknown)}")
    return Curation(
        uniprot=uniprot,
        name=data.get("name", uniprot),
        curator=data.get("curator", "unnamed"),
        status=data.get("status", "draft"),
        states=states,
        transitions=data.get("transitions") or [],
        assignments=data.get("assignments") or [],
        rules=data.get("rules") or [],
        as_of=str(data.get("as_of", "")),
        source_file=path.name,
        errors=errors,
    )


def curation_for(curation_dir: Path, accession: str) -> Curation:
    """The protein's curation file, or an empty 'uncurated' record when no curator has written one yet."""
    path = curation_dir / f"{accession}.yaml"
    if path.exists():
        return load_curation(path, accession)
    return Curation(uniprot=accession, name=accession, curator="none", status="uncurated", states=[],
                    transitions=[], assignments=[], rules=[], as_of="", source_file="")
