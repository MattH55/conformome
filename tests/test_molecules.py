"""Non-protein molecules, nucleic-acid states, mutational effects, kinetics and state vocabularies."""
import copy

import pytest

from conformome.common import check, load_validators
from conformome.molecule import (base_pairs, dna_id, family_label_errors, load_vocabularies, molecule_type,
                                 secondary_structure_errors)
from conformome.validate import vocabulary_errors
from tests.test_schema import valid_evidence, valid_state

PROV = {"source": "test", "doi": None, "deposit_id": None, "retrieved": "2026-01-01",
        "url": "https://example.org", "licence": "CC0 1.0"}
COND = {"environment": "in_vitro", "temperature_c": 25, "ph": 7.5, "buffer": "HEPES", "salt_mM": 100,
        "ions": [{"ion": "Mg2+", "concentration_mM": 5}], "ligands": ["ADE"], "applied_force_pn": None, "notes": None}
NO_IDS = {"uniprot": None, "isoform": None, "rnacentral": None, "rfam": None, "genbank": None, "nakb": None, "pdb": []}
TELO = "AGGGTTAGGGTTAGGGTTAGGG"  # human telomeric repeat (22AG)


def molecule(**kw):
    rec = {"molecule_id": "URS000000AAAA_666", "molecule_type": "rna",
           "identifiers": dict(NO_IDS, rnacentral="URS000000AAAA_666", rfam="RF00167", pdb=["1Y26"]),
           "name": "add adenine riboswitch aptamer", "gene": "add", "organism": {"name": "Vibrio vulnificus", "taxon_id": 672},
           "sequence_length": 12, "sequence": "GGGAAACCCUUU", "modifications": [], "domains": [], "ligands": ["adenine"],
           "components": [], "provenance": PROV}
    rec.update(kw)
    return rec


@pytest.fixture
def v(repo_paths):
    return load_validators(repo_paths.schema)


def test_molecule_ids_and_types():
    assert molecule_type("P69441") == molecule_type("P10636-8") == "protein"
    assert molecule_type("URS000000AAAA_666") == "rna"
    assert molecule_type(dna_id(TELO)) == "dna"
    assert molecule_type("CPX-1234") == "complex"
    assert dna_id(TELO) == dna_id(TELO.lower()) and dna_id(TELO) != dna_id(TELO + "T")


def test_rna_dna_and_complex_records_validate(v):
    assert check(v["molecule"], molecule()) == []
    dna = molecule(molecule_id=dna_id(TELO), molecule_type="dna", identifiers=dict(NO_IDS, pdb=["143D"], nakb="143D"),
                   name="human telomeric G-quadruplex", gene=None, organism=None,
                   sequence=TELO, sequence_length=len(TELO), ligands=[])
    assert check(v["molecule"], dna) == []
    cpx = molecule(molecule_id="CPX-lacI-DNA", molecule_type="complex", identifiers=NO_IDS, name="lac repressor-operator",
                   gene=None, sequence="", sequence_length=0,
                   components=[{"molecule_id": "P03023", "copies": 4}, {"molecule_id": dna_id("AATTGTGAGCGCTCACAATT"), "copies": 1}])
    assert check(v["molecule"], cpx) == []


def test_molecule_type_constrains_sequence_and_components(v):
    assert check(v["molecule"], molecule(sequence="GGGAAAXCCUUU"))
    assert check(v["molecule"], molecule(components=[{"molecule_id": "P69441", "copies": 1}]))
    assert check(v["molecule"], molecule(molecule_type="complex", sequence="", sequence_length=0, components=[]))
    assert check(v["molecule"], molecule(identifiers=dict(NO_IDS)))  # an RNA needs its RNAcentral ID


def test_dot_bracket_with_pseudoknot_and_errors():
    assert base_pairs("((..[[..))..]]") == [(0, 9), (1, 8), (4, 13), (5, 12)]
    assert base_pairs("AA..aa") == [(0, 5), (1, 4)]
    with pytest.raises(ValueError):
        base_pairs("((.)")
    with pytest.raises(ValueError):
        base_pairs("(.]")
    assert secondary_structure_errors({"dot_bracket": "(((...)))", "source": "test"}, "GGGAAACCC") == []
    assert secondary_structure_errors({"dot_bracket": "(((...)))", "source": "test"}, "GGGAAAGCC")  # G-G pair
    assert secondary_structure_errors({"dot_bracket": "((((((((((", "source": "test"}, "GGG")
    assert secondary_structure_errors({"dot_bracket": "(((...)))", "start": 2, "source": "t"}, "AGGGAAACCC") == []


def test_g_quadruplex_tetrads():
    db = ".+++...+++...+++...+++"
    assert secondary_structure_errors({"dot_bracket": db, "source": "143D"}, TELO[:len(db)]) == []
    assert secondary_structure_errors({"dot_bracket": "+" + db[1:], "source": "143D"}, TELO[:len(db)])


def test_nucleic_acid_state_with_family_label_and_population(v, repo_paths):
    s = dict(valid_state(), molecule_id="URS000000AAAA_666", basis="inferred", assumptions=["Fold from SHAPE-guided prediction."],
             secondary_structure={"dot_bracket": "(((...)))", "source": "SHAPE-guided RNAstructure"},
             family_label={"vocabulary": "riboswitch", "terms": {"aptamer": "aptamer_bound", "expression_platform": "platform_on"}},
             population={"value": 0.7, "uncertainty": 0.05, "method": "DRACO clustering", "evidence_ids": ["EV-RMDB-1"]})
    assert check(v["state"], s) == []
    vocab = load_vocabularies(repo_paths.taxonomy / "state_vocabularies")
    assert family_label_errors(s["family_label"], vocab) == []
    assert family_label_errors({"vocabulary": "riboswitch", "terms": {"aptamer": "open"}}, vocab)
    assert family_label_errors({"vocabulary": "kinase", "terms": {"activation": "active"}}, vocab)
    assert family_label_errors({"vocabulary": "nope", "terms": {"x": "y"}}, vocab)
    bad = copy.deepcopy(s)
    bad["population"]["value"] = 1.5
    assert check(v["state"], bad)


def test_state_vocabularies_validate_and_cite_a_source(repo_paths):
    assert vocabulary_errors(repo_paths) == []
    vocab = load_vocabularies(repo_paths.taxonomy / "state_vocabularies")
    assert {"kinase", "gpcr", "transporter", "ion_channel", "riboswitch", "g_quadruplex"} <= set(vocab)
    assert all(src.get("doi") for voc in vocab.values() for src in voc["source"])


def test_evidence_profile_and_ions(v):
    ev = dict(valid_evidence(), molecule_id="URS000000AAAA_666", technique="shape", conditions=COND,
              profile={"kind": "shape_reactivity", "start": 1, "values": [0.1, None, 1.2], "unit": None,
                       "normalization": "2-8% normalisation", "data_link": None})
    ev["observable"] = {"type": "reactivity_profile", "value": 3, "unit": "nucleotides", "uncertainty": None}
    assert check(v["evidence"], ev) == []
    bad = copy.deepcopy(ev)
    bad["profile"]["values"] = ["high"]
    assert check(v["evidence"], bad)
    bad = copy.deepcopy(ev)
    del bad["conditions"]["ions"]
    assert check(v["evidence"], bad)


def test_mutational_effect_variant_and_residue_summary(v):
    eff = {"effect_id": "ME-P0CG48-L67S", "molecule_id": "P0CG48", "scope": "variant",
           "variant": {"hgvs": "p.Leu67Ser", "clinvar_id": None}, "position": 67,
           "quantity": {"type": "ddg_folding", "value": 2.1, "unit": "kcal/mol", "uncertainty": 0.2, "n_variants": 1},
           "state_pair": {"from_state": "UB-unfolded", "to_state": "UB-native"}, "method": "denaturation",
           "conditions": COND, "data_link": None, "data_level": "reported", "provenance": PROV}
    assert check(v["mutational_effect"], eff) == []
    summary = dict(eff, effect_id="ME-P0CG48-r67", scope="residue_summary", variant=None,
                   quantity={"type": "ddg_folding", "value": 1.4, "unit": "kcal/mol", "uncertainty": None,
                             "summary": "mean", "n_variants": 19},
                   data_link="https://doi.org/10.5281/zenodo.7992926", data_level="processed")
    assert check(v["mutational_effect"], summary) == []
    assert check(v["mutational_effect"], dict(summary, variant=eff["variant"]))  # a summary has no single variant
    assert check(v["mutational_effect"], dict(eff, variant={"hgvs": "L67S", "clinvar_id": None}))  # not HGVS


def test_transition_with_kinetics_and_phi_values(v):
    k = {"value": 1.2e3, "unit": "s-1", "uncertainty": 50}
    t = {"transition_id": "T-fold", "molecule_id": "P0CG48", "from_state": "UB-unfolded", "to_state": "UB-native",
         "quantity": {"type": "rate", "value": 1.2e3, "unit": "s-1", "uncertainty": 50},
         "conditions": COND, "evidence_ids": ["EV-LIT-1"], "provenance": PROV,
         "kinetics": {"method": "stopped_flow", "forward_rate": k, "reverse_rate": None,
                      "m_value_forward": {"value": -1.1, "unit": "kcal mol-1 M-1", "uncertainty": None},
                      "m_value_reverse": None, "distance_to_transition_state": None, "activation_energy": None,
                      "phi_values": {"kind": "phi_value", "start": 1, "values": [None, 0.8, None, 0.1], "unit": None,
                                     "normalization": None, "data_link": None}}}
    assert check(v["transition"], t) == []
    assert check(v["transition"], dict(t, kinetics=dict(t["kinetics"], method="guess")))


def test_dot_bracket_model(v):
    m = {"model_id": "S-on-db", "molecule_id": "URS000000AAAA_666", "state_id": "S-on", "format": "dot-bracket",
         "file": "models/URS000000AAAA_666/S-on.dbn", "basis": "inferred", "constraints_used": ["EV-RMDB-1"],
         "assumptions": "SHAPE-guided minimum free-energy fold.", "provenance": PROV}
    assert check(v["model"], m) == []
