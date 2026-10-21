Pilot release of Conformome, the version described in the Open Research Europe article.

**Corpus** (built from commit dcf432a; `make validate` reports 0 errors)

- 83 molecules: 81 proteins, 1 RNA (the *V. vulnificus* adenine riboswitch aptamer, `URS000080DF85_672`) and 1 DNA (the human telomeric G-quadruplex, `DNA-6f16b68e4fba`)
- 17,541 evidence entries from eight ingested sources: RCSB PDB, BMRB, SASBDB, DisProt, AlphaFold DB, MDDB, NAKB and Rfam (RNAcentral supplies RNA identifiers); 19 techniques with entries out of 51 in the taxonomy
- 31 molecules with draft curation, 71 conformational states (3 for nucleic acids); 5,134 evidence entries mapped to a state
- 1 conflict flagged at the 3σ threshold; 33 single-method states; 8 states with no evidence

**Changes in this release**

- Schema 2.0.0: records are per molecule (`molecule_id`, `molecule_type`) rather than per protein, with ion conditions and nucleic-acid state fields (dot-bracket secondary structure, G-quadruplex topology).
- New sources: NAKB and Rfam for nucleic acids; RNAcentral for RNA identity.
- Conflict detection uses a 3σ pairwise test on quadrature-combined uncertainties, with `z` stored on each conflict; conditions are compared pairwise (temperature within 5 °C, pH within 0.5, salt and ions within a factor of two) and unknown never matches unknown.
- Mapping rules match on word boundaries and keep title and construct criteria apart; an evidence item mapped to two states is a validation error.
- Licence checks fail closed: downloads and the data archive hold only sources and licence strings listed in `docs/SOURCES.md` and `zenodo/redistribution.yaml`.
- SASBDB salts, ions and construct variants are read from the deposit text, which removed the 32 false α-synuclein conflicts of the previous build.

The data files are archived separately on Zenodo under CC BY 4.0; the data DOI is added to this release once it is minted.
