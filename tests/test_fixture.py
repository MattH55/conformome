"""The fixture protein must reproduce its expected states, mappings, coverage and models exactly."""
import json

from conformome import pipeline
from conformome.common import read_json
from pathlib import Path

from conformome.validate import run

FIXTURE = Path(__file__).parent / "fixtures" / "Q00000"


def generate(paths):
    pipeline.ingest(paths, ["Q00000"])
    pipeline.map_protein(paths, "Q00000")
    pipeline.models(paths, "Q00000")


def test_fixture_reproduces_expected_outputs(fixture_paths):
    generate(fixture_paths)
    out = fixture_paths.build / "Q00000"
    mapped = read_json(out / "mapped.json")
    expected = read_json(FIXTURE / "expected" / "mapped.json")
    assert mapped == expected
    assert read_json(out / "models.json") == read_json(FIXTURE / "expected" / "models.json")


def test_fixture_passes_validation(fixture_paths):
    generate(fixture_paths)
    from conformome.site.build import build_site
    build_site(fixture_paths, ["Q00000"])
    assert run(fixture_paths, ["Q00000"]) == []


def test_fixture_coverage_grid_and_single_method_states(fixture_paths):
    generate(fixture_paths)
    coverage = read_json(fixture_paths.build / "Q00000" / "mapped.json")["coverage"]
    assert coverage["techniques"] == ["xray", "cryoem", "nmr_structure"]
    assert coverage["cells"]["FX-open"] == {"xray": 1, "cryoem": 0, "nmr_structure": 0}
    assert coverage["cells"]["FX-closed"] == {"xray": 0, "cryoem": 2, "nmr_structure": 0}
    assert coverage["single_method_states"] == ["FX-open", "FX-closed", "FX-intermediate"]
    assert coverage["unmapped_evidence"] == 1


def test_fixture_rules_map_and_flag_ambiguity(fixture_paths):
    generate(fixture_paths)
    mapped = read_json(fixture_paths.build / "Q00000" / "mapped.json")
    by_id = {e["evidence_id"]: e for e in mapped["evidence"]}
    assert [m["who"] for m in by_id["EV-PDB-9FX5-1"]["mappings"]] == ["rule:fx-substrate-closed"]
    assert by_id["EV-PDB-9FX4-1"]["mappings"] == []
    assert mapped["ambiguous"] == [{"evidence_id": "EV-PDB-9FX4-1", "states": ["FX-closed", "FX-open"],
                                    "rules": ["fx-substrate-closed", "fx-open-title"]}]
    # 9FX1 says "open" and is X-ray, but the curator's assignment stands alone.
    assert [m["who"] for m in by_id["EV-PDB-9FX1-1"]["mappings"]] == ["curator:fixture-author"]
