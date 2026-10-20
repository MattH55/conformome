"""Mapping rules. Each returns mapping records; nothing here decides silently.

curator_assignment  the curator named the evidence and the state (who = curator:<name>)
curated rule        the curator wrote criteria in curation/<acc>.yaml (who = rule:<rule id>).
                    Evidence matched by rules for two different states stays unmapped and is
                    listed as ambiguous; a curator assignment always wins over rules.
anchor_rmsd         a structure clusters with an anchor when its C-alpha RMSD, after
                    superposition on shared residues, is within a cut-off (who = rule:anchor_rmsd).
                    rmsd_ca() is implemented and tested; it is not yet wired to coordinate
                    downloads for the pilot (see docs/PILOT_REPORT.md).
"""

from __future__ import annotations

import re

import numpy as np

_CONFIDENCE = {"high": 3, "medium": 2, "low": 1}


def curator_assignment(curator: str, state_id: str, confidence: str, justification: str) -> dict:
    return {
        "state_id": state_id,
        "who": f"curator:{curator}",
        "confidence": confidence,
        "justification": justification,
        "rule": "curator_assignment",
    }


def _ligands(ev: dict) -> set[str]:
    return {l.upper() for l in ev["conditions"].get("ligands") or []}


def _has_word(word: str, text: str) -> bool:
    """Whole word, case-insensitive. 'bound' does not match 'unbound', and 'I27' does not match 'I275'."""
    return re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE) is not None


def _words(words, text: str, *, how: str) -> bool:
    found = [_has_word(w, text) for w in words]
    if how == "any":
        return any(found)
    if how == "all":
        return all(found)
    return not any(found)


def rule_matches(match: dict, ev: dict) -> bool:
    """True when the evidence meets every criterion given. Absent criteria are not checked.

    title_* reads the deposit title only. construct_* reads the construct description only.
    """
    ligands = _ligands(ev)
    title = ev.get("title") or ""
    construct = (ev.get("construct") or {}).get("description") or ""
    ligand_text = " | ".join(ev["conditions"].get("ligands") or []).lower()
    checks = {
        "techniques": lambda v: ev["technique"] in v,
        "sources": lambda v: ev["provenance"]["source"] in v,
        "observable_types": lambda v: ev["observable"]["type"] in v,
        "environment": lambda v: ev["conditions"]["environment"] in ([v] if isinstance(v, str) else v),
        "ligands_any": lambda v: bool(ligands & {x.upper() for x in v}),
        "ligands_all": lambda v: {x.upper() for x in v} <= ligands,
        "ligands_none": lambda v: not (ligands & {x.upper() for x in v}),
        "no_ligands": lambda v: (not ligands) == bool(v),
        "ligand_text_any": lambda v: any(w.lower() in ligand_text for w in v),
        "ligand_text_none": lambda v: not any(w.lower() in ligand_text for w in v),
        "title_any": lambda v: _words(v, title, how="any"),
        "title_all": lambda v: _words(v, title, how="all"),
        "title_none": lambda v: _words(v, title, how="none"),
        "construct_any": lambda v: _words(v, construct, how="any"),
        "construct_all": lambda v: _words(v, construct, how="all"),
        "construct_none": lambda v: _words(v, construct, how="none"),
        "publication_title_any": lambda v: _words(v, title, how="any"),
    }
    return all(checks[key](value) for key, value in match.items())


def rule_mapping(rule: dict) -> dict:
    return {
        "state_id": rule["state"],
        "who": f"rule:{rule['id']}",
        "confidence": rule["confidence"],
        "justification": rule["justification"],
        "rule": rule["id"],
    }


def apply_rules(evidence: list[dict], rules: list[dict]) -> list[dict]:
    """Add rule mappings in place. Returns the ambiguous items (rules point to different states)."""
    ambiguous = []
    for ev in evidence:
        if any(m["who"].startswith("curator:") for m in ev["mappings"]):
            continue
        hits = [r for r in rules if rule_matches(r["match"], ev)]
        states = []
        for r in hits:
            if r["state"] not in states:
                states.append(r["state"])
        if len(states) == 1:
            same = [r for r in hits if r["state"] == states[0]]
            best = max(same, key=lambda r: _CONFIDENCE.get(r["confidence"], 0))
            ev["mappings"].append(rule_mapping(best))
        elif len(states) > 1:
            ambiguous.append({"evidence_id": ev["evidence_id"], "states": states, "rules": [r["id"] for r in hits]})
    return ambiguous


def rmsd_ca(coords_a: np.ndarray, coords_b: np.ndarray) -> float:
    """C-alpha RMSD after optimal superposition (Kabsch). Inputs are (N, 3) arrays of matched atoms."""
    a = np.asarray(coords_a, dtype=float)
    b = np.asarray(coords_b, dtype=float)
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"need matched (N, 3) arrays, got {a.shape} and {b.shape}")
    if len(a) < 3:
        raise ValueError("at least three matched atoms are needed to superpose")
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    d = np.sign(np.linalg.det(u @ vt))
    correction = np.diag([1.0, 1.0, d])
    rotation = u @ correction @ vt
    diff = a @ rotation - b
    return float(np.sqrt((diff ** 2).sum() / len(a)))


def anchor_rmsd(coords: np.ndarray, anchor: np.ndarray, cutoff: float) -> tuple[bool, float]:
    value = rmsd_ca(coords, anchor)
    return value <= cutoff, value
