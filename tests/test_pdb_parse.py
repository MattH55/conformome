import json
from pathlib import Path

from conformome.common import check, load_validators
from conformome.sources import pdb

SAMPLE = Path(__file__).parent / "fixtures" / "pdb" / "graphql_sample.json"


def load_sample():
    entries = json.loads(SAMPLE.read_text())["data"]["entries"]
    return {"accession": "P69441", "retrieved": "2026-10-19", "entries": entries}


def test_only_entities_mapped_to_the_accession_are_ingested(repo_paths):
    records = pdb.parse(load_sample(), "P69441", "2026-10-19")
    ids = sorted(r["provenance"]["deposit_id"] for r in records)
    assert ids == ["1AKE", "4AKE"], "2CCM is calexcitin, a different UniProt accession"


def test_records_validate_and_carry_conditions_and_provenance(repo_paths):
    validators = load_validators(repo_paths.schema)
    records = {r["provenance"]["deposit_id"]: r for r in pdb.parse(load_sample(), "P69441", "2026-10-19")}
    for rec in records.values():
        assert check(validators["evidence"], rec) == []
        assert rec["provenance"]["licence"].startswith("CC0")
        assert rec["provenance"]["doi"]
    ake4 = records["4AKE"]
    assert ake4["technique"] == "xray"
    assert ake4["observable"] == {"type": "resolution", "value": 2.2, "unit": "Å", "uncertainty": None}
    assert ake4["conditions"]["temperature_c"] is None
    assert records["1AKE"]["conditions"]["ligands"] == ["AP5"]


def test_temperature_from_kelvin_and_string_values():
    entry = {"diffrn": [{"ambient_temp": 100.0}], "exptl_crystal_grow": None, "pdbx_nmr_exptl_sample_conditions": None}
    assert pdb._temperature_c(entry) == -173.15
    nmr = {"diffrn": None, "pdbx_nmr_exptl_sample_conditions": [{"temperature": "298.0", "pH": "6.5"}],
           "exptl_crystal_grow": None}
    assert pdb._temperature_c(nmr) == 24.85
    assert pdb._ph(nmr) == 6.5
    assert pdb._temperature_c({"diffrn": None, "pdbx_nmr_exptl_sample_conditions": [{"temperature": "n/a"}]}) is None


def test_unmapped_methods_are_counted_not_ingested():
    raw = {"entries": [{"rcsb_id": "9ZZZ", "exptl": [{"method": "FIBER DIFFRACTION"}], "struct": {"title": "x"}}]}
    assert pdb.unmapped_methods(raw) == {"FIBER DIFFRACTION": 1}
    assert pdb.not_ingested(raw, "P69441") == [{"id": "9ZZZ", "reason": "method FIBER DIFFRACTION has no technique mapping"}]
    assert pdb.parse(raw, "P69441", "2026-10-19") == []


def test_integrative_entries_are_ingested_and_labelled(repo_paths):
    entry = {
        "rcsb_id": "9A08", "exptl": None, "struct": {"title": "Structures of multiple states resolved by FRET"},
        "rcsb_entry_info": {"resolution_combined": None, "experimental_method": "Integrative"},
        "rcsb_primary_citation": None, "diffrn": None, "exptl_crystal_grow": None,
        "pdbx_nmr_exptl_sample_conditions": None, "nonpolymer_entities": None,
        "polymer_entities": [{"rcsb_polymer_entity": {"pdbx_description": "Endolysin"},
                              "rcsb_polymer_entity_container_identifiers": {"entity_id": "1", "auth_asym_ids": ["A"],
                                                                            "uniprot_ids": ["P00720"]}}],
    }
    [rec] = pdb.parse({"entries": [entry]}, "P00720", "2026-10-19")
    assert rec["technique"] == "integrative"
    assert rec["observable"] == {"type": "structure", "value": None, "unit": None, "uncertainty": None}
    assert rec["title"].startswith("Structures of multiple states")
    assert check(load_validators(repo_paths.schema)["evidence"], rec) == []
