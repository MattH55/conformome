"""G-quadruplex topology from coordinates, ions from BMRB samples, and ion rule criteria."""
import numpy as np

from conformome.g4 import TELOMERIC_22, topology
from conformome.mapping.rules import rule_matches
from conformome.sources import bmrb
from tests.test_schema import valid_evidence


def quadruplex(directions):
    """Synthetic C1' positions: four tracts at the corners of a square, three tetrads along z."""
    corners = [(5, 5), (-5, 5), (-5, -5), (5, -5)]
    pos = {}
    for (x, y), tract, d in zip(corners, TELOMERIC_22, directions):
        zs = [0.0, 3.4, 6.8] if d > 0 else [6.8, 3.4, 0.0]
        for i, z in zip(tract, zs):
            pos[i] = np.array([x, y, z])
    return pos


def test_topology_from_strand_directions():
    assert topology(quadruplex([1, 1, 1, 1]))["topology"] == "parallel"
    assert topology(quadruplex([1, -1, 1, -1]))["topology"] == "antiparallel"
    hybrid = topology(quadruplex([1, 1, -1, 1]))
    assert hybrid["topology"] == "hybrid" and hybrid["pattern"] == "++-+"
    assert hybrid["loops"] == ["propeller", "lateral or diagonal", "lateral or diagonal"]
    assert topology(quadruplex([-1, -1, -1, -1]))["pattern"] == "++++"  # overall orientation does not matter


def test_bmrb_ions_from_sample_components():
    def entry(components):
        return {"1": {"sample": [{"loops": [{"category": "_Sample_component",
                                               "tags": ["Mol_common_name", "Concentration_val", "Concentration_val_units"],
                                               "data": components}]}]}}
    assert bmrb.ions(entry([["DNA", "1", "mM"], ["KCl", "70", "mM"], ["KPi", "20", "mM"]]), "1") == \
        [{"ion": "K+", "concentration_mM": 70.0}]
    assert bmrb.ions(entry([["sodium chloride", "0.1", "M"], ["magnesium chloride", "500", "uM"]]), "1") == \
        [{"ion": "Mg2+", "concentration_mM": 0.5}, {"ion": "Na+", "concentration_mM": 100.0}]
    assert bmrb.ions(entry([["potassium phosphate", "25", "mM"]]), "1") == [{"ion": "K+", "concentration_mM": None}]
    assert bmrb.ions(entry([["H2O", "90", "%"], ["PEG 200", ".", "mM"]]), "1") == []
    assert bmrb.ions({"1": {}}, "1") == []


def test_ion_rule_criteria():
    ev = valid_evidence()
    ev["conditions"]["ions"] = [{"ion": "Na+", "concentration_mM": 50}]
    assert rule_matches({"ions_any": ["Na+"], "ions_none": ["K+"]}, ev)
    ev["conditions"]["ions"].append({"ion": "K+", "concentration_mM": None})
    assert not rule_matches({"ions_any": ["Na+"], "ions_none": ["K+"]}, ev)
    assert rule_matches({"ions_any": ["K+"]}, ev)
