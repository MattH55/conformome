# Sources and licences

Each source module in `conformome/sources/` has a row here. `make validate` checks that every module has a row, that the licence is recorded (not `TBD`), that `status` matches the module's `IMPLEMENTED` flag, and that sources marked `redistribute: no` do not appear in any downloadable file. Where a licence is marked **verify**, the licence was not checked against the source's own terms in this version and must be confirmed before a public release.

| Source | Module | Status | Licence | Redistribute | Notes |
|---|---|---|---|---|---|
| RCSB PDB (PDB archive, RCSB Search and GraphQL APIs) | `pdb` | implemented | CC0 1.0 (wwPDB archive) | yes | Observed structures (X-ray, cryo-EM, microED, neutron, NMR), plus integrative models (technique `integrative`) and SAXS models (`saxs_sans`) distributed through the PDB. Representative coordinates are exported as state models. |
| UniProtKB (REST API) | `protein` | implemented | CC BY 4.0 | yes | Protein records: name, organism, sequence, domains, ligands. Attribution required. |
| BMRB (API v2) | `bmrb` | implemented | CC0 1.0 (verify) | yes | One item per entry mapped to the accession by BMRB's UniProt mapping. Relaxation and exchange data become `nmr_dynamics`; shift-only entries become `nmr_shifts`. |
| SASBDB (search page and REST summaries) | `sasbdb` | implemented | CC BY 4.0 (verify) | yes | Radius of gyration with its error. The REST API has no UniProt filter, so codes are read from the search page and each summary is checked for the UniProt code. |
| DisProt (API) | `disprot` | implemented | CC BY 4.0 | yes | Curated disordered regions. The ECO evidence code is mapped to a technique; unmapped methods and non-structural terms are listed in `build/<acc>/ingest.json`. |
| AlphaFold DB (API) | `alphafold` | implemented | CC BY 4.0 | yes | Predicted structures with mean pLDDT. Labelled as predictions. |
| MDDB (REST API) | `mddb` | implemented | per project (CC BY 4.0 for most) | yes | MD projects whose metadata references the accession. The project's own licence string is kept in each record's provenance. Labelled as predictions. |
| SMASH-BIO release file | `smashbio` | implemented | not stated by the source (verify) | no | `website/downloads/smash-smfs-records.jsonl.gz` from matth55/smash-bio. SMASH-BIO software is MIT; the data licence is not stated, so records are shown on pages with links and left out of downloads. Most records are extracted automatically; the extraction level is kept on each item. |
| PED (Protein Ensemble Database) | `ped` | stub | verify on PED website | yes | API paths returned 404 on 2026-10-19. Ensembles that are also PDB integrative entries come through `pdb`. |
| PDB-IHM | `pdbihm` | stub | CC0 1.0 (wwPDB archive, verify) | yes | Integrative entries come through `pdb`; restraint tables are not yet parsed. |
| ATLAS | `atlas` | stub | CC BY 4.0 (verify) | yes | Indexed by ECOD chain, not UniProt; MD comes from `mddb` for now. |
| Literature (Europe PMC) | `literature` | stub | publisher-dependent | no | Full text is never redistributed. Extracted values are stored with the exact span used and reviewed before going live. |

Conformome's own curation files (`curation/`) and generated pages are licensed under the project licence, which is still to be decided (see `docs/PILOT_REPORT.md`).
