from conformome.mapping.rules import apply_rules, rule_matches


def ev(eid, technique="xray", ligands=(), title="", source="RCSB PDB", mappings=None):
    return {
        "evidence_id": eid, "technique": technique, "title": title,
        "construct": {"description": "", "labels": []},
        "conditions": {"environment": "in_vitro", "ligands": list(ligands)},
        "observable": {"type": "resolution"},
        "provenance": {"source": source},
        "mappings": list(mappings or []),
    }


RULES = [
    {"id": "closed-ligand", "state": "closed", "confidence": "medium", "justification": "ligand closes it",
     "match": {"ligands_any": ["AP5"]}},
    {"id": "open-title", "state": "open", "confidence": "low", "justification": "title says open",
     "match": {"techniques": ["xray"], "title_any": ["open"]}},
    {"id": "closed-cryo", "state": "closed", "confidence": "low", "justification": "second rule, same state",
     "match": {"techniques": ["cryoem"], "title_any": ["closed"]}},
]


def test_every_criterion_must_hold():
    assert rule_matches({"techniques": ["xray"], "ligands_any": ["ap5"]}, ev("a", ligands=["AP5"]))
    assert not rule_matches({"techniques": ["cryoem"], "ligands_any": ["AP5"]}, ev("a", ligands=["AP5"]))
    assert rule_matches({"no_ligands": True}, ev("a"))
    assert not rule_matches({"no_ligands": True}, ev("a", ligands=["HOH"]))
    assert rule_matches({"ligands_none": ["MAL"]}, ev("a", ligands=["GOL"]))
    assert rule_matches({"title_none": ["mutant"], "title_all": ["apo", "open"]}, ev("a", title="Apo open form"))
    assert rule_matches({"sources": ["DisProt"]}, ev("a", source="DisProt"))
    maltose = ev("a", ligands=["branched: alpha-D-glucopyranose-(1-4)-alpha-D-glucopyranose"])
    cyclodextrin = ev("b", ligands=["branched: Cycloheptakis-(1-4)-(alpha-D-glucopyranose)"])
    closed = {"ligand_text_any": ["glucopyranose-(1-4)"], "ligand_text_none": ["cyclo"]}
    assert rule_matches(closed, maltose) and not rule_matches(closed, cyclodextrin)


def test_single_state_match_maps_with_rule_provenance():
    items = [ev("a", ligands=["AP5"])]
    assert apply_rules(items, RULES) == []
    assert items[0]["mappings"] == [{"state_id": "closed", "who": "rule:closed-ligand", "confidence": "medium",
                                     "justification": "ligand closes it", "rule": "closed-ligand"}]


def test_conflicting_rules_leave_evidence_unmapped_and_listed():
    items = [ev("a", ligands=["AP5"], title="open form with AP5")]
    ambiguous = apply_rules(items, RULES)
    assert items[0]["mappings"] == []
    assert ambiguous == [{"evidence_id": "a", "states": ["closed", "open"], "rules": ["closed-ligand", "open-title"]}]


def test_two_rules_for_the_same_state_give_one_mapping():
    items = [ev("a", technique="cryoem", ligands=["AP5"], title="closed")]
    apply_rules(items, RULES)
    assert [m["who"] for m in items[0]["mappings"]] == ["rule:closed-ligand"]


def test_curator_assignment_wins_over_rules():
    curator = {"state_id": "open", "who": "curator:x", "confidence": "high", "justification": "j", "rule": None}
    items = [ev("a", ligands=["AP5"], mappings=[curator])]
    assert apply_rules(items, RULES) == []
    assert items[0]["mappings"] == [curator]
