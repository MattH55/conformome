# Fixture protein Q00000 (synthetic)

Every value in this directory is invented for testing. Q00000 is a valid UniProt-format accession
chosen so that the schema pattern is exercised; it does not refer to a real protein. PDB IDs
9FX1, 9FX2 and 9FX3 are fixture labels, not deposits.

The pipeline is run on this directory by `tests/test_fixture.py`. The generated `mapped.json` and
`models.json` must match `expected/` exactly; regenerate `expected/` only after reviewing a
deliberate change in behaviour.
