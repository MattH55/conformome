"""Agreement between a reactivity profile and a state's pairing.

The score is the area under the ROC curve for telling unpaired from paired nucleotides by reactivity:
the probability that a randomly chosen unpaired position is more reactive than a randomly chosen paired
one (ties count one half). 1 means every unpaired position is more reactive, 0.5 means no separation.
It is stored on the mapping record and shown on the page. It never makes or removes a mapping.
"""

from __future__ import annotations

METHOD = "ROC AUC of reactivity, unpaired versus paired positions of the state's dot-bracket"
MIN_EACH = 5  # positions needed in each class before a score is given


def paired_mask(dot_bracket: str) -> list[bool]:
    """True where the dot-bracket pairs the position (brackets, pseudoknot letters, '+' tetrad guanines)."""
    return [c != "." for c in dot_bracket]


def reactivity_auc(profile: dict, secondary_structure: dict) -> float | None:
    """The AUC over positions measured in the profile and covered by the dot-bracket, or None when too few."""
    pairs = paired_mask(secondary_structure["dot_bracket"])
    ss_start = secondary_structure.get("start", 1)
    unpaired, paired = [], []
    for i, value in enumerate(profile["values"]):
        if value is None:
            continue
        j = profile["start"] + i - ss_start
        if 0 <= j < len(pairs):
            (paired if pairs[j] else unpaired).append(value)
    if len(unpaired) < MIN_EACH or len(paired) < MIN_EACH:
        return None
    wins = sum(1.0 if u > p else 0.5 if u == p else 0.0 for u in unpaired for p in paired)
    return round(wins / (len(unpaired) * len(paired)), 3)


def score_mappings(evidence: list[dict], states: list[dict]) -> int:
    """Add an agreement score to each mapping of a profile to a state with a dot-bracket. Returns how many."""
    by_id = {s["state_id"]: s for s in states}
    n = 0
    for ev in evidence:
        if not ev.get("profile"):
            continue
        for m in ev["mappings"]:
            ss = (by_id.get(m["state_id"]) or {}).get("secondary_structure")
            if not ss:
                continue
            score = reactivity_auc(ev["profile"], ss)
            if score is not None:
                m["agreement"] = {"score": score, "method": METHOD}
                n += 1
    return n
