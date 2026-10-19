"""Curation files: one YAML per protein, owned by the curator.

Shape (see curation/README.md):
    uniprot, name, curator, status (draft|reviewed), states, transitions, assignments
Assignments are the curator's evidence-to-state decisions. Each one becomes a mapping record
with who = "curator:<curator>", the stated confidence and justification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from conformome.common import load_yaml

CONFIDENCE = {"high", "medium", "low"}


@dataclass
class Curation:
    uniprot: str
    name: str
    curator: str
    status: str
    states: list[dict]
    transitions: list[dict]
    assignments: list[dict]
    as_of: str
    source_file: str
    errors: list[str] = field(default_factory=list)


def load_curation(path: Path, expected_uniprot: str | None = None) -> Curation:
    data = load_yaml(path)
    errors: list[str] = []
    uniprot = data.get("uniprot")
    if not data.get("as_of"):
        errors.append(f"{path.name}: as_of date is required (the date the curation was last changed)")
    if expected_uniprot and uniprot != expected_uniprot:
        errors.append(f"{path.name}: uniprot {uniprot} does not match file name {expected_uniprot}")
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
    for a in data.get("assignments") or []:
        if a.get("state") not in state_ids:
            errors.append(f"{path.name}: assignment {a.get('evidence_id')} names unknown state {a.get('state')}")
        if a.get("confidence") not in CONFIDENCE:
            errors.append(f"{path.name}: assignment {a.get('evidence_id')} has invalid confidence")
        if not str(a.get("justification", "")).strip():
            errors.append(f"{path.name}: assignment {a.get('evidence_id')} has no justification")
    return Curation(
        uniprot=uniprot,
        name=data.get("name", uniprot),
        curator=data.get("curator", "unnamed"),
        status=data.get("status", "draft"),
        states=states,
        transitions=data.get("transitions") or [],
        assignments=data.get("assignments") or [],
        as_of=str(data.get("as_of", "")),
        source_file=path.name,
        errors=errors,
    )
