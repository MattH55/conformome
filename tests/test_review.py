"""Checks named in the code review that the older tests did not cover."""
import dataclasses
import json
import math
from pathlib import Path

import pytest

from conformome.common import read_json, sha256_bytes
from conformome.mapping.conflicts import comparable, find_conflicts, not_compared
from conformome.pipeline import coverage_grid
from conformome.sources.base import save_raw
from conformome.sources.pdb import _celsius
from conformome.sources.sasbdb import _rg_nm, _salt_mM
from conformome.validate import downloads_redistribution_errors, licence_redistributable
from tests.test_mapping import ev

FIXTURE = Path(__file__).parent / "fixtures" / "Q00000"


def test_temperature_and_ph_boundaries():
    base = ev("EV-A", 0.1, 0.01)
    near = ev("EV-B", 0.9, 0.01, temp=29.9)
    far = ev("EV-C", 0.9, 0.01, temp=30.1)
    assert comparable(base, near)
    assert not comparable(base, far)
    assert comparable(base, ev("EV-D", 0.9, 0.01, ph=7.49))
    assert not comparable(base, ev("EV-E", 0.9, 0.01, ph=7.51))


def test_missing_conditions_are_not_comparable_to_each_other():
    a, b = ev("EV-A", 0.1, 0.01), ev("EV-B", 0.9, 0.01)
    a["conditions"]["temperature_c"] = None
    b["conditions"]["temperature_c"] = None
    assert not comparable(a, b)
    a["conditions"]["temperature_c"] = 25.0
    a["conditions"]["buffer"] = None
    b["conditions"]["buffer"] = None
    assert not comparable(a, b)
    a["conditions"]["ions"] = []
    b["conditions"]["ions"] = []
    assert not comparable(a, b)


def test_salt_ions_and_labels():
    a, b = ev("EV-A", 0.1, 0.01, salt=100), ev("EV-B", 0.9, 0.01, salt=200)
    assert comparable(a, b)
    b["conditions"]["salt_mM"] = 201
    assert not comparable(a, b)
    b["conditions"]["salt_mM"] = 200
    b["conditions"]["ions"] = [{"ion": "K+", "concentration_mM": 150.0}]
    assert not comparable(a, b)
    b["conditions"]["ions"] = [{"ion": "Na+", "concentration_mM": 150.0}]
    a["construct"]["labels"] = ["donor"]
    assert not comparable(a, b)
    b["construct"]["labels"] = ["donor"]
    assert comparable(a, b)


def test_three_sigma_boundary_and_bad_uncertainties():
    # combined uncertainty of 1 and 1 is sqrt(2); z == 3 is not a conflict.
    span = 3 * math.sqrt(2)
    assert find_conflicts([ev("EV-A", 0.0, 1.0), ev("EV-B", span, 1.0)]) == []
    assert len(find_conflicts([ev("EV-A", 0.0, 1.0), ev("EV-B", span + 0.01, 1.0)])) == 1
    for bad in (0, -1, float("nan")):
        assert find_conflicts([ev("EV-A", 0.1, bad), ev("EV-B", 0.9, 0.01)]) == []


def test_predictions_are_excluded_from_conflicts_and_from_the_one_method_count():
    items = [ev("EV-A", 0.1, 0.01, technique="af_prediction"), ev("EV-B", 0.9, 0.01, technique="af_prediction")]
    assert find_conflicts(items, {"af_prediction"}) == []
    assert not_compared(items, {"af_prediction"}) == 2
    states = [{"state_id": "S"}, {"state_id": "T"}]
    grid = coverage_grid(states, [
        {**ev("EV-1", 1, 0.1, technique="af_prediction", state="S"), "data_level": "processed"},
        {**ev("EV-2", 1, 0.1, technique="xray", state="T"), "data_level": "processed"},
        {**ev("EV-3", 1, 0.1, technique="md", state="T"), "data_level": "processed"},
    ], ["af_prediction", "xray", "md"], {"af_prediction", "md"})
    assert grid["single_method_states"] == ["T"]
    assert grid["no_evidence_states"] == ["S"]


def test_ligands_are_compared_case_insensitively():
    a, b = ev("EV-A", 0.1, 0.01, ligands=["gdp"]), ev("EV-B", 0.9, 0.01, ligands=["GDP"])
    assert comparable(a, b)


def test_pdb_temperature_units_and_range():
    assert _celsius(100) == 100
    assert _celsius(298) == pytest.approx(24.85)
    assert _celsius(100, nmr=True) == 100
    assert _celsius(25, nmr=True) == 25
    assert _celsius(-173) is None
    assert _celsius(500) is None  # 500 K is above 150 °C and is dropped


def test_sasbdb_uses_guinier_only_and_reads_salt():
    assert _rg_nm({"guinier_rg": 2.0, "guinier_rg_error": 0.15, "pddf_rg": 9}) == (2.0, 0.15)
    assert _rg_nm({"guinier_rg": None, "pddf_rg": 2.1}) == (None, None)
    assert _rg_nm({"guinier_rg": 40, "guinier_rg_error": 1}) == (4.0, 0.1)
    assert _rg_nm({"guinier_rg": 400}) == (None, None)
    assert _salt_mM({"name": "50 mM NaCl"}) == 50
    assert _salt_mM({"name": "Tris"}) is None


def test_manifest_hash_ignores_the_retrieval_date(tmp_path, repo_paths):
    paths = dataclasses.replace(repo_paths, raw=tmp_path / "raw", manifest=tmp_path / "MANIFEST.json")
    save_raw(paths, "pdb", "P0", {"accession": "P0", "retrieved": "2020-01-01", "entries": [1]},
             ["https://example.test/a"])
    first = read_json(paths.manifest)["raw/pdb/P0.json"]
    save_raw(paths, "pdb", "P0", {"accession": "P0", "retrieved": "2026-10-19", "entries": [1]},
             ["https://example.test/a"])
    second = read_json(paths.manifest)["raw/pdb/P0.json"]
    assert first["sha256"] == second["sha256"]
    assert second["retrieved"] == "2026-10-19"
    key = sha256_bytes(b"https://example.test/a\n")
    meta = paths.raw / "_cache" / f"{key}.retrieved"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text("2019-05-01\n", encoding="utf-8")
    save_raw(paths, "pdb", "P0", {"accession": "P0", "retrieved": "2026-10-19", "entries": [1]},
             ["https://example.test/a"])
    assert read_json(paths.manifest)["raw/pdb/P0.json"]["retrieved"] == "2019-05-01"


def test_downloads_fail_closed(tmp_path, repo_paths):
    site = tmp_path / "site"
    (site / "downloads").mkdir(parents=True)
    (site / "search").mkdir()
    ok = {"evidence_id": "EV-OK", "provenance": {"source": "RCSB PDB", "licence": "CC0 1.0 (wwPDB archive data)"}}
    smash = {"evidence_id": "EV-SMASH-1", "provenance": {"source": "SMASH-BIO", "licence": "not stated by the source"}}
    unknown = {"evidence_id": "EV-X", "provenance": {"source": "Mystery", "licence": "CC BY 4.0"}}
    bundle = {
        "evidence": [ok, unknown],
        "conflicts": [{"conflict_id": "CF-1", "evidence_ids": ["EV-OK", "EV-SMASH-1"]}],
        "states": [{"state_id": "S", "population": {"value": 0.5, "uncertainty": None, "method": "fit",
                                                    "evidence_ids": ["EV-SMASH-1"]}}],
        "transitions": [],
    }
    (site / "downloads" / "proteins").mkdir()
    (site / "downloads" / "proteins" / "P0.json").write_text(json.dumps(bundle), encoding="utf-8")
    (site / "downloads" / "all-records.jsonl").write_text(
        json.dumps({"record_type": "evidence", **smash}) + "\n", encoding="utf-8")
    (site / "search" / "evidence.json").write_text(json.dumps([["EV-SMASH-1", "P0", "force_spectroscopy", "SMASH-BIO"]]),
                                                   encoding="utf-8")
    paths = dataclasses.replace(repo_paths, site=site)
    text = "\n".join(downloads_redistribution_errors(paths))
    assert "SMASH-BIO" in text and "Mystery" in text and "CF-1" in text and "population" in text
    assert "search/evidence.json" in text
    policy_allow = {"CC0 1.0 (wwPDB archive data)"}
    assert licence_redistributable("CC0 1.0 (wwPDB archive data)", policy_allow, ("not stated",))
    assert not licence_redistributable("CC0-1.0", policy_allow, ("not stated",))
    assert not licence_redistributable("", policy_allow, ("not stated",))


def test_two_curator_states_are_rejected(fixture_paths, tmp_path):
    from conformome import pipeline
    curation = tmp_path / "curation"
    curation.mkdir()
    text = (FIXTURE / "curation" / "Q00000.yaml").read_text(encoding="utf-8")
    text = text.replace(
        "rules:",
        "  - evidence_id: EV-PDB-9FX1-1\n    state: FX-closed\n    confidence: low\n"
        "    justification: second state\nrules:",
        1,
    )
    (curation / "Q00000.yaml").write_text(text, encoding="utf-8")
    paths = dataclasses.replace(fixture_paths, curation=curation)
    pipeline.ingest(paths, ["Q00000"])
    with pytest.raises(ValueError, match="assigned to"):
        pipeline.map_protein(paths, "Q00000")


def test_observed_state_without_a_representative_fails_validation(fixture_paths, tmp_path):
    from conformome import pipeline
    from conformome.site.build import build_site
    from conformome.validate import run
    curation = tmp_path / "curation"
    curation.mkdir()
    text = (FIXTURE / "curation" / "Q00000.yaml").read_text(encoding="utf-8")
    text = text.replace('representative_pdb: "9FX2"', "representative_pdb: null", 1)
    (curation / "Q00000.yaml").write_text(text, encoding="utf-8")
    paths = dataclasses.replace(fixture_paths, curation=curation)
    pipeline.ingest(paths, ["Q00000"])
    pipeline.map_protein(paths, "Q00000")
    pipeline.models(paths, "Q00000")
    build_site(paths, ["Q00000"])
    errors = run(paths, ["Q00000"])
    assert any("must cite representative_pdb" in e for e in errors)


def test_ingest_is_byte_stable(fixture_paths):
    from conformome import pipeline
    pipeline.ingest(fixture_paths, ["Q00000"])
    first = (fixture_paths.build / "Q00000" / "evidence.json").read_bytes()
    pipeline.ingest(fixture_paths, ["Q00000"])
    second = (fixture_paths.build / "Q00000" / "evidence.json").read_bytes()
    assert first == second
    ids = [row["evidence_id"] for row in json.loads(first)]
    assert ids == sorted(ids)
    assert (fixture_paths.build / "BUILD.json").exists()
