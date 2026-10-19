"""RNAcentral, Rfam and NAKB, run on trimmed real responses saved in tests/fixtures/sources/."""
import json
from pathlib import Path

import pytest

from conformome import dna, rnacentral
from conformome.common import check, load_taxonomy, load_validators
from conformome.molecule import dna_id
from conformome.pipeline import evidence_errors
from conformome.sources import PRIMARY, for_type, nakb, rfam

FIX = Path(__file__).parent / "fixtures" / "sources"
RNA = "URS000080DF85_672"
DNA = "DNA-6f16b68e4fba"


def raw(name):
    return json.loads((FIX / name).read_text())


@pytest.fixture
def checker(repo_paths):
    validators = load_validators(repo_paths.schema)
    taxonomy = load_taxonomy(repo_paths.taxonomy / "techniques.yaml")
    return lambda ev: evidence_errors(validators, taxonomy, ev)


def test_sources_are_chosen_by_molecule_type():
    assert nakb in for_type("rna") and rfam in for_type("rna") and nakb in for_type("dna")
    assert rfam not in for_type("dna") and nakb not in for_type("protein") and rfam not in for_type("protein")
    assert PRIMARY["rna"] is nakb and PRIMARY["dna"] is nakb


def test_rnacentral_molecule_record(repo_paths):
    rec = rnacentral.parse(raw(f"rnacentral_{RNA}.json"), RNA)
    assert check(load_validators(repo_paths.schema)["molecule"], rec) == []
    assert rec["molecule_type"] == "rna" and rec["identifiers"]["rfam"] == "RF00167"
    assert rec["organism"] == {"name": "Vibrio vulnificus", "taxon_id": 672}
    assert rec["sequence_length"] == 71 and set(rec["sequence"]) <= set("ACGU")
    assert rec["domains"] == [{"name": "Purine riboswitch aptamer (Rfam RF00167)", "start": 2, "end": 69}]


def test_rna_pages_must_be_species_specific():
    with pytest.raises(ValueError):
        rnacentral.split("URS000080DF85")


def test_dna_molecule_record_is_keyed_on_its_sequence(repo_paths):
    r = raw(f"dna_{DNA}.json")
    rec = dna.parse(r, DNA)
    assert check(load_validators(repo_paths.schema)["molecule"], rec) == []
    assert dna_id(rec["sequence"]) == DNA and rec["identifiers"]["pdb"] == ["143D"]
    assert rec["organism"]["taxon_id"] == 9606


@pytest.mark.parametrize("module,name,acc", [
    (nakb, f"nakb_{RNA}.json", RNA), (nakb, f"nakb_{DNA}.json", DNA), (rfam, f"rfam_{RNA}.json", RNA),
])
def test_every_record_validates(module, name, acc, checker):
    records = module.parse(raw(name), acc, "2026-10-19")
    assert records
    for ev in records:
        assert checker(ev) == [], ev["evidence_id"]
        assert ev["provenance"]["source"] == module.NAME and ev["molecule_id"] == acc


def test_nakb_matches_same_sequence_and_same_family_constructs():
    records = {ev["evidence_id"]: ev for ev in nakb.parse(raw(f"nakb_{RNA}.json"), RNA, "2026-10-19")}
    assert set(records) == {"EV-NAKB-1Y26-1", "EV-NAKB-4LX5-1", "EV-NAKB-6VWT-1"}
    assert records["EV-NAKB-1Y26-1"]["construct"]["description"].endswith("same sequence")
    assert "same Rfam family (RF00167) and organism" in records["EV-NAKB-4LX5-1"]["construct"]["description"]
    one = records["EV-NAKB-1Y26-1"]
    assert one["technique"] == "xray" and one["observable"] == {"type": "resolution", "value": 2.1, "unit": "Å", "uncertainty": None}
    assert one["conditions"]["ions"] == [{"ion": "Mg2+", "concentration_mM": None}]
    assert one["conditions"]["ligands"] == ["ADE"]  # ions are not ligands


def test_nakb_entity_of_another_family_or_organism_is_not_matched():
    mol = {"sequence": "GGGAAACCC", "rfam": ["RF00167"], "taxid": 672}
    base = {"entity": "1", "type": "RNA", "chains": "A", "description": "x", "sequence": "GGGAAAUCCC"}
    assert nakb._match(dict(base, taxid=672, rfam={"RF00167"}), mol)
    assert nakb._match(dict(base, taxid=1423, rfam={"RF00167"}), mol) is None
    assert nakb._match(dict(base, taxid=672, rfam={"RF00050"}), mol) is None
    assert nakb._match(dict(base, type="Protein", taxid=672, rfam={"RF00167"}, sequence="GGGAAACCC"), mol) is None


def test_nakb_dna_structures_by_method():
    records = nakb.parse(raw(f"nakb_{DNA}.json"), DNA, "2026-10-19")
    by_id = {ev["provenance"]["deposit_id"]: ev for ev in records}
    assert by_id["143D"]["technique"] == "nmr_structure" and by_id["143D"]["observable"]["type"] == "structure"
    assert by_id["1KF1"]["conditions"]["ions"] == [{"ion": "K+", "concentration_mM": None}]
    assert by_id["2MCO"]["conditions"]["ions"] == [{"ion": "Na+", "concentration_mM": None}]


def test_rfam_hit_is_a_prediction_with_coverage(repo_paths):
    [ev] = rfam.parse(raw(f"rfam_{RNA}.json"), RNA, "2026-10-19")
    tax = load_taxonomy(repo_paths.taxonomy / "techniques.yaml")
    assert ev["technique"] == "rfam_covariation" and tax["rfam_covariation"]["prediction"] is True
    assert ev["source_kind"] == "computed" and ev["conditions"]["environment"] == "in_silico"
    assert ev["observable"]["type"] == "family_coverage" and 0.9 < ev["observable"]["value"] <= 1
    cons = raw(f"rfam_{RNA}.json")["families"]["RF00167"]["consensus"]
    assert len(cons["SS_cons"]) == len(cons["RF"]) > 0


def test_stockholm_consensus_joins_blocks():
    sto = "# STOCKHOLM 1.0\nseq1 ACGU\n#=GC SS_cons <<..\n#=GC RF ACGU\n\nseq1 AAAA\n#=GC SS_cons ..>>\n#=GC RF aaaa\n//\n"
    assert rfam.consensus(sto) == {"SS_cons": "<<....>>", "RF": "ACGUaaaa"}


def test_bmrb_sequence_hits_keep_full_length_high_identity_matches():
    from conformome.sources import bmrb
    hits = [
        {"entry_id": "1", "entity_id": "1", "percent_id": 100.0, "q.start": 1, "q.end": 22},
        {"entry_id": "2", "entity_id": "1", "percent_id": 95.0, "q.start": 2, "q.end": 22},
        {"entry_id": "3", "entity_id": "1", "percent_id": 76.0, "q.start": 1, "q.end": 21},   # low identity
        {"entry_id": "4", "entity_id": "1", "percent_id": 100.0, "q.start": 1, "q.end": 11},  # half the sequence
        {"entry_id": "2", "entity_id": "2", "percent_id": 90.0, "q.start": 1, "q.end": 22},   # worse hit, same entry
    ]
    best = bmrb.sequence_hits(hits, 22)
    assert set(best) == {"1", "2"}
    assert best["1"] == {"percent_id": 100.0, "coverage": 1.0, "entity_id": "1"}
    assert best["2"]["entity_id"] == "1" and best["2"]["coverage"] == 0.955


def test_bmrb_nucleic_acid_entries_say_how_they_match(checker):
    from conformome.sources import bmrb
    records = {ev["evidence_id"]: ev for ev in bmrb.parse(raw(f"bmrb_{DNA}.json"), DNA, "2026-10-19")}
    assert set(records) == {"EV-BMRB-17655", "EV-BMRB-19381", "EV-BMRB-31254"}
    for ev in records.values():
        assert checker(ev) == [] and ev["technique"] == "nmr_shifts"
    assert records["EV-BMRB-17655"]["construct"]["description"].endswith("contains this sequence")
    assert "(another construct)" in records["EV-BMRB-19381"]["construct"]["description"]
    assert bmrb in for_type("rna") and bmrb in for_type("dna") and bmrb in for_type("protein")
