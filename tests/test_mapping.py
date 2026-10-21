import numpy as np
import pytest

from conformome.mapping.conflicts import CONFLICT_SIGMA, comparable, find_conflicts, not_compared
from conformome.mapping.curation import load_curation
from conformome.mapping.rules import anchor_rmsd, curator_assignment, rmsd_ca


def test_rmsd_of_identical_coordinates_is_zero():
    coords = np.random.default_rng(0).normal(size=(20, 3))
    assert rmsd_ca(coords, coords) == pytest.approx(0.0, abs=1e-9)


def test_rmsd_is_invariant_to_rigid_motion():
    rng = np.random.default_rng(1)
    coords = rng.normal(size=(30, 3))
    theta = 0.7
    rot = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    moved = coords @ rot.T + np.array([5.0, -3.0, 2.0])
    assert rmsd_ca(coords, moved) == pytest.approx(0.0, abs=1e-9)


def test_rmsd_reports_a_known_displacement():
    coords = np.zeros((4, 3))
    coords[:, 0] = [0, 1, 2, 3]
    coords[:, 1] = [0, 1, 0, 1]
    shifted = coords.copy()
    shifted[:, 2] += 1.0  # uniform offset is removed by superposition
    assert rmsd_ca(coords, shifted) == pytest.approx(0.0, abs=1e-9)
    noisy = coords.copy()
    noisy[0, 2] += 2.0
    assert rmsd_ca(coords, noisy) > 0.0


def test_anchor_rmsd_cutoff():
    coords = np.random.default_rng(2).normal(size=(10, 3))
    within, value = anchor_rmsd(coords, coords + 0.0, cutoff=2.0)
    assert within and value == pytest.approx(0.0, abs=1e-9)


def test_rmsd_rejects_too_few_atoms():
    with pytest.raises(ValueError):
        rmsd_ca(np.zeros((2, 3)), np.zeros((2, 3)))


def ev(eid, value, unc, temp=25.0, ph=7.0, ligands=(), state="S", unit="fraction",
       buffer="HEPES", salt=150.0, ions=None, technique="smfret"):
    return {
        "evidence_id": eid,
        "technique": technique,
        "observable": {"type": "population", "value": value, "unit": unit, "uncertainty": unc},
        "conditions": {
            "environment": "in_vitro", "temperature_c": temp, "ph": ph, "buffer": buffer,
            "salt_mM": salt, "ions": [{"ion": "Na+", "concentration_mM": 150.0}] if ions is None else ions,
            "ligands": list(ligands),
        },
        "construct": {"description": "", "labels": []},
        "mappings": [{"state_id": state}],
    }


def test_disagreeing_populations_are_flagged_not_averaged():
    conflicts = find_conflicts([ev("EV-A", 0.30, 0.02), ev("EV-B", 0.50, 0.03)])
    assert len(conflicts) == 1
    assert conflicts[0]["evidence_ids"] == ["EV-A", "EV-B"]
    assert conflicts[0]["state_id"] == "S"
    assert conflicts[0]["threshold_sigma"] == CONFLICT_SIGMA
    assert conflicts[0]["z"] > CONFLICT_SIGMA


def test_agreeing_values_within_combined_uncertainty_are_not_flagged():
    assert find_conflicts([ev("EV-A", 0.30, 0.05), ev("EV-B", 0.34, 0.05)]) == []


def test_items_under_different_conditions_are_not_compared():
    items = [ev("EV-A", 0.30, 0.01, temp=25.0), ev("EV-B", 0.60, 0.01, temp=37.0)]
    assert find_conflicts(items) == []
    assert not comparable(items[0], items[1])


def test_items_without_uncertainty_are_not_compared_and_are_counted():
    items = [ev("EV-A", 0.30, None), ev("EV-B", 0.50, 0.02)]
    assert find_conflicts(items) == []
    # Both items are mapped and neither entered a comparable pair.
    assert not_compared(items) == 2


def test_curation_loader_rejects_unknown_state(tmp_path):
    path = tmp_path / "P69441.yaml"
    path.write_text(
        "uniprot: P69441\nname: x\ncurator: c\nstatus: draft\nas_of: 2026-01-01\n"
        "states:\n  - {id: A, name: a, basis: observed, parent: nope}\n"
        "assignments:\n  - {evidence_id: EV-1, state: MISSING, confidence: high, justification: j}\n")
    cur = load_curation(path, "P69441")
    assert any("unknown parent" in e for e in cur.errors)
    assert any("unknown state" in e for e in cur.errors)


def test_curator_assignment_record_shape():
    rec = curator_assignment("A. Curator", "S-open", "high", "Anchor match.")
    assert rec == {"state_id": "S-open", "who": "curator:A. Curator", "confidence": "high",
                   "justification": "Anchor match.", "rule": "curator_assignment"}


def test_different_constructs_are_not_compared():
    a, b = ev("EV-A", 0.30, 0.01), ev("EV-B", 0.60, 0.01)
    a["construct"] = {"description": "wild type"}
    b["construct"] = {"description": "L99A mutant"}
    assert find_conflicts([a, b]) == []
    b["construct"] = {"description": "wild type"}
    assert len(find_conflicts([a, b])) == 1


def test_k_and_na_items_are_never_compared():
    k = ev("EV-K", 0.30, 0.01, ions=[{"ion": "K+", "concentration_mM": 100.0}])
    na = ev("EV-NA", 0.90, 0.01, ions=[{"ion": "Na+", "concentration_mM": 100.0}])
    assert not comparable(k, na)
    assert find_conflicts([k, na]) == []


def test_mg_more_than_a_factor_of_two_apart_is_not_compared():
    low = ev("EV-LO", 0.30, 0.01, ions=[{"ion": "Mg2+", "concentration_mM": 1.0}])
    high = ev("EV-HI", 0.90, 0.01, ions=[{"ion": "Mg2+", "concentration_mM": 10.0}])
    near = ev("EV-NEAR", 0.90, 0.01, ions=[{"ion": "Mg2+", "concentration_mM": 1.5}])
    assert not comparable(low, high)
    assert comparable(low, near)
    assert len(find_conflicts([low, high, near])) == 1
