# Sources and licences

Each source module in `conformome/sources/` has a row here. `make validate` checks that every module has a row, that the licence is recorded (not `TBD`), that `status` matches the module's `IMPLEMENTED` flag, and that sources marked `redistribute: no` do not appear in any downloadable file. Where a licence is marked **verify**, the licence was not checked against the source's own terms in this version and must be confirmed before a public release.

| Source | Module | Status | Licence | Redistribute | Notes |
|---|---|---|---|---|---|
| RCSB PDB (PDB archive, RCSB Search and GraphQL APIs) | `pdb` | implemented (pilot) | CC0 1.0 (wwPDB archive) | yes | Observed structures and entry metadata. Coordinates of representative entries are exported as state models. |
| UniProtKB (REST API) | `protein` | implemented (pilot) | CC BY 4.0 | yes | Protein records: name, organism, sequence, domains, ligands. Attribution required. |
| BMRB | `bmrb` | stub | CC0 1.0 (verify) | yes | NMR shifts, relaxation and dispersion. Not yet ingested. |
| SASBDB | `sasbdb` | stub | CC BY 4.0 (verify) | yes | SAXS profiles and models. Not yet ingested. |
| PED (Protein Ensemble Database) | `ped` | stub | verify on PED website | yes | Disordered-protein ensembles. Not yet ingested. |
| PDB-IHM | `pdbihm` | stub | CC0 1.0 (wwPDB archive, verify) | yes | Integrative models. Not yet ingested. |
| SMASH-BIO release files | `smashbio` | stub | not stated by the source (verify) | no | SMASH-BIO software is MIT; its metadata README states only "research and educational purposes". Data are linked, not redistributed, until the licence is clarified. |
| ATLAS / MDDB | `atlas` | stub | CC BY 4.0 (verify) | yes | MD summaries. Not yet ingested. |
| Literature (Europe PMC) | `literature` | stub | publisher-dependent | no | Full text is never redistributed. Extracted values are stored with the exact span used and reviewed before going live. |

Conformome's own curation files (`curation/`) and generated pages are licensed under the project licence, which is still to be decided (see `docs/PILOT_REPORT.md`).
