"""Parsers for the non-PDB sources, run on trimmed real responses saved in tests/fixtures/sources/."""
import json
from pathlib import Path

import pytest

from conformome.common import load_taxonomy, load_validators
from conformome.pipeline import evidence_errors
from conformome.sources import alphafold, bmrb, disprot, mddb, sasbdb, smashbio

FIX = Path(__file__).parent / "fixtures" / "sources"


def run(module, name, acc):
    raw = json.loads((FIX / name).read_text())
    return module.parse(raw, acc, "2026-10-19"), raw


@pytest.fixture
def checker(repo_paths):
    validators = load_validators(repo_paths.schema)
    taxonomy = load_taxonomy(repo_paths.taxonomy / "techniques.yaml")
    return lambda ev: evidence_errors(validators, taxonomy, ev)


@pytest.mark.parametrize("module,name,acc", [
    (alphafold, "alphafold_P69441.json", "P69441"),
    (bmrb, "bmrb_P01053.json", "P01053"),
    (sasbdb, "sasbdb_P0CG48.json", "P0CG48"),
    (disprot, "disprot_P10636.json", "P10636-8"),
    (mddb, "mddb_P01053.json", "P01053"),
    (smashbio, "smashbio_Q8WZ42.json", "Q8WZ42"),
])
def test_every_record_validates_with_provenance_and_conditions(module, name, acc, checker):
    records, _ = run(module, name, acc)
    assert records
    for ev in records:
        assert checker(ev) == [], ev["evidence_id"]
        assert ev["provenance"]["source"] == module.NAME
        assert ev["provenance"]["licence"]


def test_alphafold_is_a_prediction_with_plddt(repo_paths):
    [ev], _ = run(alphafold, "alphafold_P69441.json", "P69441")
    tax = load_taxonomy(repo_paths.taxonomy / "techniques.yaml")
    assert ev["technique"] == "af_prediction" and tax["af_prediction"]["prediction"] is True
    assert ev["source_kind"] == "computed" and ev["conditions"]["environment"] == "in_silico"
    assert ev["observable"]["type"] == "plddt" and 0 < ev["observable"]["value"] <= 100


def test_bmrb_classifies_entries_and_converts_temperature():
    records, _ = run(bmrb, "bmrb_P01053.json", "P01053")
    assert {r["technique"] for r in records} <= {"nmr_shifts", "nmr_dynamics"}
    for r in records:
        assert r["provenance"]["doi"].startswith("10.13018/BMR")
        t = r["conditions"]["temperature_c"]
        assert t is None or -20 < t < 100, "temperature must be in degrees Celsius"
    assert bmrb.classify(["1H chemical shifts", "T1 relaxation values"]) == ("nmr_dynamics", "relaxation_rate")
    assert bmrb.classify(["H exchange rates"]) == ("nmr_dynamics", "exchange_rate")
    assert bmrb.classify(["coupling constants"]) is None


def test_sasbdb_rg_in_nm_and_partners_recorded():
    records, _ = run(sasbdb, "sasbdb_P0CG48.json", "P0CG48")
    by = {r["provenance"]["deposit_id"]: r for r in records}
    alone, partnered = by["SASDCG7"], by["SASDBR3"]
    assert alone["observable"] == {"type": "radius_of_gyration", "value": 2.0, "unit": "nm", "uncertainty": 0.15}
    assert alone["conditions"]["ligands"] == []
    assert any(l.startswith("partner: ") for l in partnered["conditions"]["ligands"])


def test_disprot_keeps_an_isoform_on_its_own_page_only():
    canonical, raw = run(disprot, "disprot_P10636.json", "P10636")
    isoform, _ = run(disprot, "disprot_P10636.json", "P10636-8")
    assert canonical == []
    assert isoform and all("P10636-8" in r["construct"]["description"] for r in isoform)
    assert all(r["observable"]["type"] == "disorder_region" for r in isoform)
    reasons = {x["reason"] for x in disprot.not_ingested(raw, "P10636-8")}
    assert any(reason.startswith("term not structural") for reason in reasons)
    assert disprot.technique_for("far-UV circular dichroism evidence used in manual assertion") == "cd"
    assert disprot.technique_for("single-molecule FRET evidence") == "smfret"
    assert disprot.technique_for("force spectroscopy evidence") == "force_spectroscopy"
    assert disprot.technique_for("NMR relaxation evidence") == "nmr_dynamics"
    assert disprot.technique_for("negative stain electron microscopy") is None
    assert disprot.technique_for("spectrometry evidence used in manual assertion") is None


def test_mddb_is_computed_md_with_trajectory_length():
    records, _ = run(mddb, "mddb_P01053.json", "P01053")
    for r in records:
        assert r["technique"] == "md" and r["source_kind"] == "computed"
        assert r["observable"]["type"] == "trajectory" and r["observable"]["unit"] == "ns"


def test_smashbio_results_and_study_records_carry_extraction_level():
    records, _ = run(smashbio, "smashbio_Q8WZ42.json", "Q8WZ42")
    by = {r["evidence_id"]: r for r in records}
    result = by["EV-SMASH-SMFS-000508-r0"]
    assert result["observable"]["type"] == "unfolding_force" and result["observable"]["unit"] == "pN"
    assert by["EV-SMASH-SMFS-000147"]["observable"]["type"] == "study_record"
    assert all("extraction level" in r["conditions"]["notes"] for r in records)
    assert all("experiment class:" in r["construct"]["description"] for r in records)


@pytest.mark.parametrize("module,name,acc,level", [
    (alphafold, "alphafold_P69441.json", "P69441", "processed"),
    (bmrb, "bmrb_P01053.json", "P01053", "processed"),
    (sasbdb, "sasbdb_P0CG48.json", "P0CG48", "processed"),
    (disprot, "disprot_P10636.json", "P10636-8", "reported"),
    (mddb, "mddb_P01053.json", "P01053", "processed"),
    (smashbio, "smashbio_Q8WZ42.json", "Q8WZ42", "reported"),
])
def test_each_source_sets_its_data_level(module, name, acc, level):
    records, _ = run(module, name, acc)
    assert {r["data_level"] for r in records} == {level}
