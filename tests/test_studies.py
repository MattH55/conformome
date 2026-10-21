"""Study records (construct, protocol, state network, occupancy): the WNV frameshift study, cross-reference
checks, intervals, divergence, and comparison with the equilibrium model on a synthetic study."""
import copy
from pathlib import Path

import pytest

from conformome.conformations import studies

ROOT = Path(__file__).resolve().parents[1]
WNV = ROOT / "studies" / "wnv-ns1prime-frameshift"


def test_wnv_study_is_valid_and_marked_incomplete():
    s = studies.load(WNV)
    assert studies.schema_errors(s, ROOT / "schema") == []
    assert studies.integrity_errors(s) == []
    assert s["network"]["curation"]["status"] == "incomplete" and s["network"]["curation"]["missing"]
    keys = {st["key"] for st in s["network"]["states"]}
    assert {"PKS", "PKL", "HP38", "HP71"} <= keys
    assert all(st["delta_lc_from_unfolded"] is None for st in s["network"]["states"])  # nothing estimated


def test_integrity_catches_undefined_keys_and_bad_counts():
    s = copy.deepcopy(studies.load(WNV))
    s["network"]["pathways"][0]["states"].append("XX")
    s["network"]["perturbation_effects"][0]["abolishes"].append("YY")
    occ = s["occupancies"][0]
    occ["total"], occ["entries"][0]["count"], occ["entries"][0]["fraction"] = 10, 12, 1.2
    occ["entries"][1]["fraction"] = 0.5
    errs = studies.integrity_errors(s)
    assert any("state XX not defined" in e for e in errs)
    assert any("abolishes YY not defined" in e for e in errs)
    assert any("count for path-PKS exceeds total" in e for e in errs)
    assert any("fractions sum" in e for e in errs)


def test_missing_values_cannot_be_marked_complete():
    s = copy.deepcopy(studies.load(WNV))
    s["network"]["curation"]["status"] = "complete"
    assert any("lists missing values but has status complete" in e for e in studies.integrity_errors(s))


def test_wilson_interval_and_divergence():
    lo, hi = studies.wilson_ci(30, 100)
    assert lo == pytest.approx(0.2189, abs=1e-3) and hi == pytest.approx(0.3958, abs=1e-3)
    assert studies.js_divergence_bits({"a": 1.0}, {"a": 1.0}) == 0
    assert studies.js_divergence_bits({"a": 1.0}, {"b": 1.0}) == pytest.approx(1.0)


def test_equilibrium_comparison_on_a_synthetic_study():
    pytest.importorskip("RNA")
    seq = "UAGCGGUCUCUCAGGCUGCUUGCCGUCCGGCCCGGCCGCG"  # synthetic bistable RNA (docs/CONFORMATIONS.md)
    s = copy.deepcopy(studies.load(WNV))
    s["construct"]["sequence"] = seq
    s["network"]["states"] = [
        dict(s["network"]["states"][0], key="one", structure={"conformation_id": None, "description": None,
             "dot_bracket": "..((((((.((..(((.....)))....))...)))))).", }),
        dict(s["network"]["states"][0], key="two", structure={"conformation_id": None, "description": None,
             "dot_bracket": ".((((((((...)))))))).((((.......))))...."}),
    ]
    occ = {"occupancy_id": "OC-T", "network_id": s["network"]["network_id"], "protocol_id": "PT-WNV-ramp",
           "basis": "state_at_force", "direction": "equilibrium", "force_window_pn": {"min": 0, "max": 0},
           "entries": [{"key": "one", "count": 0, "fraction": None, "ci95": None},
                       {"key": "two", "count": 50, "fraction": None, "ci95": None}],
           "total": 50, "comparisons": []}
    studies.fill_intervals(occ)
    cmp = studies.equilibrium_comparison(s, occ, temperature_c=25.0)
    pred = {p["key"]: p["fraction"] for p in cmp["predicted"]}
    assert 0.25 < pred["one"] < 0.5  # equilibrium puts a third in the long hairpin
    assert cmp["divergence_bits"] > 0.1  # a history-prepared sample (all 'two') departs from it
