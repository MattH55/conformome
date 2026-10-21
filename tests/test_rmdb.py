from conformome.sources import rmdb

# A trimmed RDAT in the layout RMDB serves: a 5-nt flank, the 8-nt molecule, a 2-nt tail.
RDAT = "\n".join([
    "RDAT_VERSION\t0.34",
    "NAME\ttest hairpin",
    "SEQUENCE\tGGAAAGCGCUUCGCGAA",
    "OFFSET\t-5",
    "SEQPOS\t" + "\t".join(str(i) for i in range(-4, 13)),
    "ANNOTATION\tchemical:MgCl2:10mM\tchemical:HEPES:50mM(pH8.0)\ttemperature:24C",
    "ANNOTATION_DATA:1\tmodifier:1M7",
    "ANNOTATION_DATA:2\tmodifier:nomod",
    "ANNOTATION_DATA:3\tmodifier:DMS\tmutation:G6A",
    "REACTIVITY:1\t" + "\t".join(f"{i / 10:.1f}" for i in range(17)),
    "REACTIVITY_ERROR:1\t" + "\t".join("0.05" for _ in range(17)),
    "REACTIVITY:2\t" + "\t".join("0.0" for _ in range(17)),
    "REACTIVITY:3\t" + "\t".join("0.1" for _ in range(17)),
])
MOLECULE = "GCGCTTCG"  # T is read as U


def raw():
    return {"accession": "URS0000000001_1", "retrieved": "2026-10-20", "sequence": MOLECULE, "scanned": 1,
            "not_scanned": [{"rmdb_id": "BIG_LIB_0001", "construct_count": 5000}],
            "entries": {"TEST_1M7_0001": {"manifest": {"rmdb_id": "TEST_1M7_0001", "pub_title": "Test", "doi": None},
                                          "rdat_url": "https://example.org/TEST_1M7_0001.rdat", "rdat": RDAT}}}


def test_rdat_parse_and_sequence_match():
    rdat = rmdb.parse_rdat(RDAT)
    assert rdat["offset"] == -5 and rdat["seqpos"][0] == -4
    assert rmdb.matches(rdat, MOLECULE) == ["1", "2", "3"]
    assert rmdb.matches(rdat, "AAAAAAAAAAAA") == []


def test_profile_is_projected_onto_the_molecule_numbering():
    rec, = rmdb.parse(raw(), "URS0000000001_1", "2026-10-20")
    prof = rec["profile"]
    assert rec["technique"] == "shape" and prof["kind"] == "shape_reactivity"
    # Construct index 5 (seqpos 1) is molecule position 1.
    assert prof["start"] == 1 and len(prof["values"]) == 8
    assert prof["values"][0] == 0.5 and prof["values"][-1] == 1.2
    assert prof["uncertainties"][0] == 0.05
    assert rec["conditions"]["ions"] == [{"ion": "Mg2+", "concentration_mM": 10.0}]
    assert rec["conditions"]["temperature_c"] == 24
    assert "partial construct" in rec["construct"]["description"]


def test_controls_mutants_and_large_libraries_are_listed_not_ingested():
    reasons = {n["id"]: n["reason"] for n in rmdb.not_ingested(raw(), "URS0000000001_1")}
    assert reasons["TEST_1M7_0001:2"] == "no-modifier control"
    assert reasons["TEST_1M7_0001:3"].startswith("mutant construct")
    assert "not scanned" in reasons["BIG_LIB_0001"]
