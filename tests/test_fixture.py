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


def test_uncurated_protein_gets_an_evidence_only_page(fixture_paths, tmp_path):
    import dataclasses
    from conformome.site.build import build_site
    empty = tmp_path / "no-curation" / "curation"
    empty.mkdir(parents=True)
    (empty.parent / "targets.yaml").write_text("targets:\n  - {uniprot: Q00000, batch: test}\n")
    paths = dataclasses.replace(fixture_paths, curation=empty)
    generate(paths)
    mapped = read_json(paths.build / "Q00000" / "mapped.json")
    assert mapped["curation"]["status"] == "uncurated"
    assert mapped["states"] == [] and all(not e["mappings"] for e in mapped["evidence"])
    assert read_json(paths.build / "Q00000" / "models.json") == []
    build_site(paths, ["Q00000"])
    page = (paths.site / "protein" / "Q00000" / "index.html").read_text()
    assert "States not yet curated" in page and 'id="coverage-grid"' in page
    assert run(paths) == []


def test_targets_file_must_cover_curation(fixture_paths, tmp_path):
    import dataclasses
    from conformome.validate import targets_errors
    root = tmp_path / "t"
    (root / "curation").mkdir(parents=True)
    (root / "curation" / "Q00000.yaml").write_text((FIXTURE / "curation" / "Q00000.yaml").read_text())
    (root / "targets.yaml").write_text("targets:\n  - {uniprot: P69441, batch: b}\n  - {uniprot: P69441}\n")
    errors = targets_errors(dataclasses.replace(fixture_paths, curation=root / "curation"))
    assert "targets.yaml: P69441 listed more than once" in errors
    assert "targets.yaml: P69441 has no batch" in errors
    assert "curation/Q00000.yaml has no entry in targets.yaml" in errors
