Pilot release of Conformome, the version described in the Open Research Europe article.

**Corpus** (`make validate`: 0 errors; the exact commit is recorded in `paper/out/stats.json`)

- 87 molecules: 81 proteins, 5 RNAs (the *V. vulnificus* adenine riboswitch aptamer, the preQ1-I riboswitch aptamer, HIV-1 TAR, the *Tetrahymena* P4–P6 domain and the SARS-CoV-2 frameshift stimulation element) and 1 DNA (the human telomeric G-quadruplex)
- 17,677 evidence entries from ten ingested sources: RCSB PDB, BMRB, SASBDB, DisProt, AlphaFold DB, MDDB, SMASH-BIO, NAKB, Rfam and RMDB (RNAcentral supplies RNA identifiers); 21 techniques with entries out of 51 in the taxonomy
- 36 molecules with draft curation, 83 conformational states (15 for nucleic acids); 5,239 evidence entries mapped to a state
- 1 conflict flagged at the 3σ threshold; 35 single-method states; 11 states with no evidence

**Changes in this release**

- Schema 2.0.0: records are per molecule (`molecule_id`, `molecule_type`) rather than per protein, with ion conditions and nucleic-acid state fields (dot-bracket secondary structure, G-quadruplex topology).
- New sources: NAKB, Rfam and RMDB (chemical-probing reactivity profiles) for nucleic acids; RNAcentral for RNA identity; BMRB queried by sequence for RNA and DNA.
- Conflict detection uses a 3σ pairwise test on quadrature-combined uncertainties, with `z` stored on each conflict; conditions are compared pairwise (temperature within 5 °C, pH within 0.5, salt and ions within a factor of two) and unknown never matches unknown.
- Mapping rules match on word boundaries and keep title and construct criteria apart; an evidence item mapped to two states is a validation error.
- Licence checks fail closed: downloads and the data archive hold only sources and licence strings listed in `docs/SOURCES.md` and `zenodo/redistribution.yaml`.
- SASBDB salts, ions and construct variants are read from the deposit text, which removed the 32 false α-synuclein conflicts of the previous build.

The data files are archived separately on Zenodo under CC BY 4.0; the data DOI is added to this release once it is minted.
