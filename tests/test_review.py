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
from conformome.sources.sasbdb import _rg_nm, construct_labels, normalize_text, salt_ions, total_salt_mM
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


def test_sasbdb_uses_guinier_only():
    assert _rg_nm({"guinier_rg": 2.0, "guinier_rg_error": 0.15, "pddf_rg": 9}) == (2.0, 0.15)
    assert _rg_nm({"guinier_rg": None, "pddf_rg": 2.1}) == (None, None)
    assert _rg_nm({"guinier_rg": 40, "guinier_rg_error": 1}) == (4.0, 0.1)
    assert _rg_nm({"guinier_rg": 400}) == (None, None)


def test_sasbdb_normalizes_deposited_text():
    assert normalize_text("K₂HPO₄/KH₂PO₄") == "K2HPO4/KH2PO4"
    assert normalize_text("50\u2009mM potassium phosphate") == "50 mM potassium phosphate"
    assert normalize_text("Fe(III)-TMPyP, pH ∼ 10.7") == "Fe(III)-TMPyP, pH ∼ 10.7"
    assert normalize_text("peptides – 1 mM") == "peptides - 1 mM"
    assert normalize_text(None) == ""


def test_sasbdb_reads_salt_from_the_field_that_names_it():
    # The alpha-synuclein series writes its salt only in the sample name.
    assert salt_ions(["α-Synuclein WT 1.16mg/ml 100 mM NaCl", "20mM HEPES"]) == [
        {"ion": "Na+", "concentration_mM": 100.0}]
    assert salt_ions(["20 mM HEPES, 150 mM NaCl"]) == [{"ion": "Na+", "concentration_mM": 150.0}]
    assert salt_ions(["NaCl 150 mM"]) == [{"ion": "Na+", "concentration_mM": 150.0}]
    assert salt_ions(["20 mM TRIS, 40 mM KCl, 20 mM CaCl2"]) == [
        {"ion": "Ca2+", "concentration_mM": 20.0}, {"ion": "K+", "concentration_mM": 40.0}]
    # Unicode subscripts and molar units.
    assert salt_ions(["50 mM sodium phosphate, 300 mM KCl"]) == [{"ion": "K+", "concentration_mM": 300.0}]
    assert salt_ions(["0.2 M glycine-HCl, 80 mM NaCl"]) == [{"ion": "Na+", "concentration_mM": 80.0}]
    assert salt_ions(["10 mM CaCl₂"]) == [{"ion": "Ca2+", "concentration_mM": 10.0}]
    assert salt_ions(["20 mM HEPES 200 mM NaCl 0.01 mM ZnSO4"]) == [
        {"ion": "Na+", "concentration_mM": 200.0}, {"ion": "Zn2+", "concentration_mM": 0.01}]


def test_buffers_are_not_salts():
    # Reading the buffering agent as the salt made every alpha-synuclein deposit look alike.
    for buffer in ("20mM HEPES", "40 mM Sodium Acetate", "20 mM Sodium Acetate/HEPES",
                   "phosphate buffered saline", "PBS", "20 mM MES pH 6.0", "10 mM citric acid",
                   "50 mM sodium phosphate", "20 mM K₂HPO₄/KH₂PO₄", "0.2 M glycine-HCl",
                   "50 mM Tris-HCl", "1 mol% ethylammonium nitrate"):
        assert salt_ions([buffer]) == [], buffer
    assert salt_ions(["50 mM Tris, 50 mM NaCl, 10% glycerol"]) == [
        {"ion": "Na+", "concentration_mM": 50.0}]
    # A percentage, a reducing agent or a mass ratio is not a salt concentration.
    assert salt_ions(["20 mM Tris, 10% (v/v) glycerol, 1 mM TCEP"]) == []
    assert salt_ions(["1 mM DTT, 2 mM β-mercaptoethanol"]) == []
    assert salt_ions(["5 mg/mL lysozyme in 150 mM NaCl"]) == [{"ion": "Na+", "concentration_mM": 150.0}]



def test_sasbdb_ions_without_a_number_stay_unknown():
    assert salt_ions(["PBS, 150 mM NaCl, 1 mM CaCl2"]) == [
        {"ion": "Ca2+", "concentration_mM": 1.0}, {"ion": "Na+", "concentration_mM": 150.0}]
    assert salt_ions(["guanidinium chloride"]) == [{"ion": "Gdm+", "concentration_mM": None}]
    assert total_salt_mM(salt_ions(["guanidinium chloride"])) is None
    assert total_salt_mM(salt_ions(["20 mM KCl, 100 mM NaCl"])) == 120.0
    assert total_salt_mM(salt_ions(["Tris"])) is None


def test_sasbdb_does_not_borrow_the_next_components_number():
    # "100 mM NaCl, 50 mM Tris": the 50 belongs to Tris, not to the salt.
    assert salt_ions(["100 mM NaCl, 50 mM Tris-HCl"]) == [{"ion": "Na+", "concentration_mM": 100.0}]
    # The fields quote each other; a salt named twice is one salt, not two.
    assert salt_ions(["40 mM NaOAc pH 3.8, 150 mM NaCl", "40 mM NaOAc pH 3.8, 150 mM NaCl"]) == [
        {"ion": "Na+", "concentration_mM": 150.0}]


def test_sasbdb_construct_labels_come_from_the_deposit_text():
    labels = construct_labels(["Isoform Tau-F of Microtubule-associated protein tau (C291A, K311C, K317C, C322A)"])
    assert labels == ["c291a", "k311c", "k317c", "c322a", "isoform-tau-f"]
    assert construct_labels(["α-Synuclein WT in 0 mM NaCl"]) == ["wild-type"]
    assert construct_labels(["SEC-SAXS of tau dGAE fragment (2N4R residues 297-391)"]) == [
        "297-391", "fragment", "2n4r"]
    assert construct_labels(["von Willebrand factor C6-CK G2705R"]) == ["g2705r"]
    assert construct_labels(["His-Tagged Monomeric RAD51 [F86E, A89E]"]) == ["f86e", "a89e", "his-tagged"]
    # Chemical formulas in a buffer are not mutations.
    assert construct_labels(["20 mM K₂HPO₄/KH₂PO₄, 100 mM NaCl"]) == []
    assert construct_labels([None, ""]) == []


def test_different_salt_is_no_longer_comparable():
    def item(salt, ions, labels=(), rg=3.4):
        return {
            "evidence_id": f"EV-{salt}",
            "technique": "saxs_sans",
            "observable": {"type": "radius_of_gyration", "value": rg, "unit": "nm", "uncertainty": 0.03},
            "conditions": {"environment": "in_vitro", "temperature_c": 20.0, "ph": 7.2,
                           "buffer": "20mM HEPES", "salt_mM": salt,
                           "ions": [{"ion": "Na+", "concentration_mM": v} for v in ions],
                           "ligands": []},
            "construct": {"description": "Alpha-synuclein", "labels": list(labels)},
            "mappings": [{"state_id": "S"}],
        }

    # The α-synuclein series: same buffer, same construct, different salt.
    assert comparable(item(100.0, [100.0]), item(150.0, [150.0]))
    assert not comparable(item(50.0, [50.0]), item(150.0, [150.0]))
    assert not comparable(item(0.0, [0.0]), item(100.0, [100.0]))
    assert not comparable(item(100.0, [100.0]), item(100.0, [100.0], labels=["wild-type"]))
    assert not comparable(item(100.0, [100.0]), item(100.0, [100.0, 20.0]))
    assert find_conflicts([item(50.0, [50.0]), item(150.0, [150.0])]) == []


def test_missing_ion_data_is_reported_not_guessed():
    assert salt_ions([]) == []
    assert salt_ions([None, None]) == []
    assert total_salt_mM([]) is None



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
