"""Conformation records, geometry, and the equilibrium and kinetic force models.

The sequences here are synthetic test hairpins, not published constructs: they check the physics and the
records, not agreement with experiment.
"""
import math
from pathlib import Path

import pytest

from conformome.common import check, load_validators
from conformome.conformations import build, geometry

SCHEMA = Path(__file__).resolve().parents[1] / "schema"
GC_HAIRPIN = "GGGCGCGGCCTTTTGGCCGCGCCC"
AT_HAIRPIN = "GATATTAATCTTTTGATTAATATC"


@pytest.fixture(scope="module")
def validators():
    return load_validators(SCHEMA)


def test_contour_length_released_interval_and_upper_bound():
    rel = geometry.contour_length_released(89, 4.0, "protein")
    assert rel.low < rel.value < rel.high
    assert rel.value == pytest.approx(89 * 0.365 - 4.0, abs=0.01)
    assert not rel.assumptions
    ub = geometry.contour_length_released(10, None, "rna")
    assert ub.value == pytest.approx(5.9) and "upper bound" in ub.assumptions[0]


def test_dot_bracket_segments_pairs_and_pseudoknots():
    db = "((..[[..))..]]"
    assert geometry.base_pairs(db) == [(0, 9), (1, 8), (4, 13), (5, 12)]
    segs = geometry.segments_from_dot_bracket(db, start=11)
    assert segs[0] == {"start": 11, "end": 12, "status": "paired", "label": None}
    assert geometry.structured_span(segs, ("paired",)) == (11, 24)
    with pytest.raises(ValueError):
        geometry.base_pairs("((.)")


def test_conformation_from_secondary_structure_is_valid(validators):
    state = {"state_id": "X-bound", "basis": "observed",
             "secondary_structure": {"dot_bracket": "(((....)))", "start": 1, "source": "test"}}
    rec = build.from_secondary_structure("URS0000000001_9606", "rna", state)
    assert check(validators["conformation"], rec) == []
    derived = {d["quantity"]: d for d in rec["derived"]}
    assert derived["n_base_pairs"]["value"] == 3
    assert derived["contour_length_released_nm"]["value"] == pytest.approx(10 * 0.59)


def test_assignment_keeps_every_candidate_and_ranks_by_residual(validators):
    def conf(cid, lo, hi):
        return {"conformation_id": cid, "state_id": None, "derived": [
            {"quantity": "contour_length_released_nm", "value": (lo + hi) / 2, "parameters": {"interval_nm": [lo, hi]}}]}
    seg = {"segment_id": "SG-T-1", "observables": [{"measured": {"value": 28.5, "unit": "nm", "uncertainty": 0.5}}]}
    out = build.assign("P69441", [seg], [conf("CF-a", 27.0, 30.0), conf("CF-b", 10.0, 12.0)])
    assert [a["target"]["conformation_id"] for a in out] == ["CF-a", "CF-b"]
    assert out[0]["accepted"] and out[0]["score"]["value"] == 0.0
    assert not out[1]["accepted"] and out[1]["score"]["value"] == pytest.approx(16.5)
    for a in out:
        assert check(validators["assignment"], dict(a, provenance=build._prov("P69441"))) == []


def test_trace_from_structure_reads_chain_geometry(tmp_path):
    gemmi = pytest.importorskip("gemmi")
    st = gemmi.Structure()
    model = gemmi.Model("1")
    chain = gemmi.Chain("A")
    for i in range(5):
        res = gemmi.Residue()
        res.name, res.seqid, res.entity_type = "ALA", gemmi.SeqId(str(i + 10)), gemmi.EntityType.Polymer
        atom = gemmi.Atom()
        atom.name, atom.element, atom.pos = "CA", gemmi.Element("C"), gemmi.Position(3.8 * i, 0, 0)
        res.add_atom(atom)
        chain.add_residue(res)
    model.add_chain(chain)
    st.add_model(model)
    st.setup_entities()
    path = tmp_path / "t.cif"
    st.make_mmcif_document().write_file(str(path))
    trace = geometry.trace_from_structure(str(path), None, "protein")
    assert trace.numbers == [10, 11, 12, 13, 14]
    assert geometry.distance(trace.points[0], trace.points[-1]) == pytest.approx(15.2)
    assert trace.segments() == [{"start": 10, "end": 14, "status": "folded", "label": None}]


# --- force models ------------------------------------------------------------------------------------------
RNA = pytest.importorskip("RNA", reason="ViennaRNA not installed")


def _folded_midpoint(seq):
    from conformome.conformations.thermo import ForceModel, midpoint_force
    m = ForceModel(seq, "dna", 25.0, 0.15)
    s, _ = m.fc.mfe()
    forces = [0.25 * i for i in range(121)]
    curve = m.macrostate_curve({"folded": s, "unfolded": "." * len(seq)}, forces)
    return m, s, midpoint_force(forces, curve["occupancy"]["folded"])


def test_wlc_inversion_matches_marko_siggia():
    from conformome.conformations.thermo import kT, wlc_relative_extension
    kt = kT(25.0)
    z = wlc_relative_extension(10.0, 1.0, kt)
    assert kt / 1.0 * (0.25 / (1 - z) ** 2 - 0.25 + z) == pytest.approx(10.0, rel=1e-6)


def test_stronger_stem_unfolds_at_higher_force():
    _, _, f_gc = _folded_midpoint(GC_HAIRPIN)
    _, _, f_at = _folded_midpoint(AT_HAIRPIN)
    assert f_gc > f_at > 0


def test_kinetics_obey_detailed_balance_and_converge_to_equilibrium():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from conformome.conformations.kinetics import KineticModel
    m, s, f_eq = _folded_midpoint(GC_HAIRPIN)
    km = KineticModel(m, {"folded": s, "unfolded": "." * len(GC_HAIRPIN)})
    k = km.rate_matrix(f_eq)
    w, v = np.linalg.eig(k)
    stationary = np.real(v[:, np.argmin(np.abs(w))])
    stationary /= stationary.sum()
    assert stationary == pytest.approx(km.equilibrium(f_eq), abs=1e-9)
    slow = km.ramp(5, 30, 1e-3)
    assert max(slow.divergence()) < 1e-4
    assert slow.midpoint("folded") == pytest.approx(f_eq, abs=0.1)


def test_hysteresis_grows_with_loading_rate():
    pytest.importorskip("scipy")
    from conformome.conformations.kinetics import KineticModel
    m, s, _ = _folded_midpoint(GC_HAIRPIN)
    km = KineticModel(m, {"folded": s, "unfolded": "." * len(GC_HAIRPIN)}, k0_per_s=1e3)
    gaps = []
    for rate in (1.0, 10.0, 100.0):
        up, down = km.ramp(5, 35, rate), km.ramp(35, 5, rate)
        gaps.append(up.midpoint("folded") - down.midpoint("folded"))
    assert gaps[0] < gaps[1] < gaps[2]
    assert all(math.isfinite(g) for g in gaps)


def test_folding_history_overrides_equilibrium_for_a_bistable_rna():
    """Synthetic 40-nt RNA with two near-isoenergetic folds and a high barrier (docs/CONFORMATIONS.md §4)."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from scipy.linalg import expm
    from conformome.conformations.kinetics import KineticModel, cotranscriptional_start
    from conformome.conformations.thermo import ForceModel
    seq = "UAGCGGUCUCUCAGGCUGCUUGCCGUCCGGCCCGGCCGCG"
    refs = {"one_hairpin": "..((((((.((..(((.....)))....))...)))))).",
            "two_hairpins": ".((((((((...)))))))).((((.......))))....", "open": "." * len(seq)}
    m = ForceModel(seq, "rna", 25.0, 0.15)
    km = KineticModel(m, refs, k0_per_s=1e3, max_structures=400_000)
    eq = dict(zip(km.names, km.equilibrium(0.0)))
    assert 0.25 < eq["one_hairpin"] < 0.5 and 0.5 < eq["two_hairpins"] < 0.75
    start = cotranscriptional_start(m, refs)
    assert start == "two_hairpins"
    p = expm(km.rate_matrix(0.0) * 3600) @ np.array([1.0 if n == start else 0.0 for n in km.names])
    assert dict(zip(km.names, p))["two_hairpins"] > 0.99  # still far from equilibrium after an hour
