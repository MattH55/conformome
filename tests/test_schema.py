import copy

from conformome.common import check, load_taxonomy, load_validators
from conformome.validate import schema_errors, taxonomy_errors


def valid_evidence():
    return {
        "evidence_id": "EV-TEST-1",
        "molecule_id": "P69441",
        "technique": "xray",
        "source_kind": "deposit",
        "title": None,
        "construct": {"description": "test", "labels": []},
        "conditions": {"environment": "in_vitro", "temperature_c": None, "ph": None, "buffer": None,
                       "salt_mM": None, "ions": [], "ligands": [], "applied_force_pn": None, "notes": None},
        "observable": {"type": "resolution", "value": 2.0, "unit": "Å", "uncertainty": None},
        "mappings": [],
        "data_link": None,
        "data_level": "reported",
        "data_format": None,
        "reader": None,
        "provenance": {"source": "test", "doi": None, "deposit_id": None, "retrieved": "2026-01-01",
                       "url": "https://example.org", "licence": "CC0 1.0"},
    }


def valid_state():
    return {
        "state_id": "S-open", "molecule_id": "P69441", "name": "open", "parent_state": None, "basis": "observed",
        "representative_model": None, "description": "", "assumptions": [], "status": "draft",
        "provenance": {"source": "test", "doi": None, "deposit_id": None, "retrieved": "2026-01-01",
                       "url": "https://example.org", "licence": "CC0 1.0"},
    }


def test_schemas_are_valid_json_schema(repo_paths):
    assert schema_errors(repo_paths) == []


def test_taxonomy_is_consistent(repo_paths):
    assert taxonomy_errors(repo_paths) == []


def test_every_observed_and_inferred_technique_is_labelled(repo_paths):
    techniques = load_taxonomy(repo_paths.taxonomy / "techniques.yaml")
    assert {t["basis"] for t in techniques.values()} == {"observed", "inferred"}
    assert techniques["xray"]["basis"] == "observed"
    assert techniques["smfret"]["basis"] == "inferred"
    assert techniques["md"]["prediction"] is True


def test_valid_evidence_passes(repo_paths):
    validators = load_validators(repo_paths.schema)
    assert check(validators["evidence"], valid_evidence()) == []


def test_evidence_without_conditions_fails(repo_paths):
    validators = load_validators(repo_paths.schema)
    bad = valid_evidence()
    del bad["conditions"]
    assert check(validators["evidence"], bad)


def test_evidence_without_provenance_fails(repo_paths):
    validators = load_validators(repo_paths.schema)
    bad = valid_evidence()
    del bad["provenance"]["licence"]
    assert check(validators["evidence"], bad)


def test_inferred_state_requires_assumptions(repo_paths):
    validators = load_validators(repo_paths.schema)
    state = valid_state()
    state["basis"] = "inferred"
    assert check(validators["state"], state), "inferred state with no assumptions must fail"
    state["assumptions"] = ["Fitted to smFRET histograms under the stated buffer."]
    assert check(validators["state"], state) == []


def test_inferred_model_requires_assumptions(repo_paths):
    validators = load_validators(repo_paths.schema)
    model = {
        "model_id": "M-1", "molecule_id": "P69441", "state_id": "S-open", "format": "mmCIF", "file": "models/x.cif",
        "basis": "inferred", "constraints_used": [], "assumptions": None,
        "provenance": {"source": "test", "doi": None, "deposit_id": None, "retrieved": "2026-01-01",
                       "url": "https://example.org", "licence": "CC0 1.0"},
    }
    assert check(validators["model"], model)
    model["assumptions"] = "Ensemble member selected to satisfy restraints."
    assert check(validators["model"], model) == []


def test_mapping_needs_who_confidence_and_justification(repo_paths):
    validators = load_validators(repo_paths.schema)
    ev = valid_evidence()
    ev["mappings"] = [{"state_id": "S-open", "who": "curator:someone", "confidence": "high",
                       "justification": "Matches the anchor."}]
    assert check(validators["evidence"], ev) == []
    for field, value in [("who", "anonymous"), ("confidence", "certain"), ("justification", "")]:
        bad = copy.deepcopy(ev)
        bad["mappings"][0][field] = value
        assert check(validators["evidence"], bad), field


def test_uniprot_accession_pattern(repo_paths):
    validators = load_validators(repo_paths.schema)
    ev = valid_evidence()
    ev["molecule_id"] = "not-an-accession"
    assert check(validators["evidence"], ev)


def test_one_validator_per_record_type(repo_paths):
    assert {"molecule", "state", "evidence", "transition", "model", "mutational_effect", "state_vocabulary"} <= set(load_validators(repo_paths.schema))


def test_data_level_is_required_and_constrained(repo_paths):
    validators = load_validators(repo_paths.schema)
    ev = valid_evidence()
    del ev["data_level"]
    assert check(validators["evidence"], ev)
    ev["data_level"] = "partial"
    assert check(validators["evidence"], ev)
