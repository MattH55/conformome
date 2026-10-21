from conformome.mapping.agreement import reactivity_auc, score_mappings


def test_auc_is_one_when_every_unpaired_position_is_more_reactive():
    ss = {"dot_bracket": "((((((......))))))", "source": "test"}
    values = [0.1] * 6 + [1.0] * 6 + [0.1] * 6
    assert reactivity_auc({"start": 1, "values": values}, ss) == 1.0


def test_auc_is_one_half_for_a_flat_profile_and_none_when_too_few_positions():
    ss = {"dot_bracket": "((((((......))))))", "source": "test"}
    assert reactivity_auc({"start": 1, "values": [0.5] * 18}, ss) == 0.5
    sparse = [None] * 18
    sparse[0], sparse[8] = 0.1, 1.0
    assert reactivity_auc({"start": 1, "values": sparse}, ss) is None


def test_profile_and_structure_offsets_are_respected():
    ss = {"dot_bracket": "((((((......))))))", "source": "test", "start": 3}
    values = [None, None] + [0.0] * 6 + [2.0] * 6 + [0.0] * 6
    assert reactivity_auc({"start": 1, "values": values}, ss) == 1.0


def test_score_is_added_to_the_mapping_only_when_the_state_has_pairing():
    ss = {"dot_bracket": "((((((......))))))", "source": "test"}
    evs = [{"profile": {"start": 1, "values": [0.1] * 6 + [1.0] * 6 + [0.1] * 6},
            "mappings": [{"state_id": "A"}, {"state_id": "B"}]}]
    assert score_mappings(evs, [{"state_id": "A", "secondary_structure": ss}, {"state_id": "B"}]) == 1
    assert evs[0]["mappings"][0]["agreement"]["score"] == 1.0
    assert "agreement" not in evs[0]["mappings"][1]
