# Submission form answers: Open Research Europe

Field-by-field answers for https://open-research-europe.ec.europa.eu → Submit → Software Tool Article. Items marked **[author]** need the author's input before the form is filled. The ORE requirements quoted below were read on 2026-10-23 from the article guidelines, the data/software guidelines, the pre-submission checklist and the eligibility page (the dedicated Software Tool Article page returned 404 that day; its requirements come from the article-type table in the general guidelines).

## Article

| Field | Answer |
| --- | --- |
| Article type | Software Tool Article |
| Subject area | Biological sciences › Structural biology / Biophysics |
| Title | Conformome: an index of experimental evidence on the conformational states of proteins and nucleic acids, mapped across techniques |
| Keywords (max 8) | protein conformation; conformational ensembles; structural biology; FAIR data; database; integrative structural biology; single-molecule biophysics; RNA structure |

## Abstract (≤ 300 words; paste from the filled manuscript)

**Background.** The function of a protein or nucleic acid depends on the conformations it adopts, but the evidence on those conformations is divided by technique. Structures are deposited in the PDB, NMR data in the BMRB, scattering profiles in SASBDB and RNA chemical-probing data in the RNA Mapping Database, while simulations sit in molecular dynamics archives and force-spectroscopy results mostly in the literature. No existing resource brings this evidence together for one molecule and relates it to the states the molecule is thought to adopt.

**Methods.** Conformome (https://conformome.org) collects experimental and computational entries for each protein, RNA or DNA molecule from ten sources: the RCSB PDB, BMRB, SASBDB, the RNA Mapping Database, DisProt, MDDB, AlphaFold DB, SMASH-BIO, NAKB and Rfam. Each entry keeps its technique, construct, conditions (including ions), observable with uncertainty, and provenance. Curators define the states of each molecule and map entries to them individually or through explicit rules, and each mapping records who made it, with what confidence and why. States resolved directly by a structure are labelled observed; states fitted to indirect measurements are labelled inferred and must list their assumptions. Disagreements between comparable measurements are flagged rather than averaged.

**Results.** The pilot release covers 81 proteins and six nucleic acids, with 17,677 evidence entries from 22 techniques; 36 molecules have draft curation, with 83 states. Each molecule page shows a state-by-technique coverage grid that identifies states supported by a single method, together with the evidence, conflicts and structural models of observed states. All records, schemas and curation files can be downloaded.

**Conclusions.** Conformome makes the multi-technique evidence on the conformational states of proteins and nucleic acids findable and comparable, and shows where that evidence is sparse or inconsistent.

(The abstract contains no citations or cross-references, as ORE requires. If the manuscript is rebuilt after the DOIs are filled, re-paste from `paper/out/manuscript.filled.md`.)

## Author

| Field | Answer |
| --- | --- |
| Name | Matthew T. J. Halma |
| Affiliation | Open Source Medicine, Pärnu mnt. 139c, 11317 Tallinn, Estonia |
| Email | mhalma@opensourcemed.info |
| ORCID | **[author]** (optional on ORE, but used in `.zenodo.json`, `CITATION.cff` and the manuscript byline; fill all four places with the same iD) |
| CRediT roles | Conceptualization; Data curation; Methodology; Software; Validation; Visualization; Writing – original draft; Writing – review & editing (single author) |
| Corresponding author | yes |

## Eligibility and funding

| Field | Answer |
| --- | --- |
| Eligibility route | EU-funded project: Horizon 2020 Marie Skłodowska-Curie ITN **AntiHelix**, grant agreement **859853** (project completed) |
| Funder | European Commission, Horizon 2020 |
| Grant statement (as in the manuscript) | This project has received funding from the European Union's Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No 859853 (AntiHelix). |
| Note | ORE validates authors through an institutional email, department website or letter of reference. The corresponding email is an Open Source Medicine address; have a second validation route ready if asked. **[author]** confirms eligibility with ORE if in doubt. |

## Competing interests (as in the manuscript)

M.T.J.H. is a former employee of LUMICKS B.V., a manufacturer of optical tweezers instruments, and develops SMASH-BIO, one of the sources ingested by Conformome. No other competing interests were disclosed.

## AI-use declaration (must match the Acknowledgements word for word)

The author used Claude (Anthropic; **[author: model version]**) to help draft and edit the manuscript text and to write parts of the pipeline, website and figure code, in order to speed up writing and software development. The author checked all content, numbers and interpretations and takes full responsibility for them. No generative AI was used to create or alter figures.

ORE asks for "the tool, version where known, purpose, and the human checks applied"; the statement covers all four once the version is filled.

## Data availability statement (as in the manuscript, with the DOI filled)

Zenodo: Conformome pilot release 0.1.0. https://doi.org/10.5281/zenodo.**[author: data DOI]**

This project contains the following underlying data: `all-records.jsonl` (every molecule, state, transition, evidence and model record); one JSON bundle per molecule; per-nucleotide reactivity profiles for chemical-probing entries; the JSON Schemas for all record types; `techniques.yaml` (technique taxonomy); the per-molecule curation files; the manifest of raw inputs (URL, retrieval date and SHA-256 checksum).

The same files can be downloaded from https://conformome.org/downloads/. Evidence from sources whose licence does not allow redistribution is not included in the archive and is linked at source.

Data are available under the terms of the **[author: licence; the archive carries CC BY 4.0]** (ORE accepts CC0 or CC BY 4.0; CC0 preferred).

ORE requires the repository name, a description of each dataset and the licence statement; all three are present once the DOI and licence are filled. Zenodo is on ORE's trusted-repository list.

## Software availability statement (as in the manuscript, with the DOI filled)

- Software available from: https://conformome.org
- Source code available from: https://github.com/matth55/conformome
- Archived source code at time of publication: https://doi.org/10.5281/zenodo.**[author: software DOI]** (version v0.1.0)
- License: MIT License

ORE asks for these four lines, an open (preferably OSI-approved) licence and the DOI of the version underlying the article. MIT is OSI-approved.

## Files to upload

| File | Notes |
| --- | --- |
| `Conformome_ORE_manuscript.docx` | ORE accepts DOC/DOCX, RTF or LaTeX. Sections present in the required order: Abstract, Keywords, Introduction, Methods (Implementation, Operation), Results and use cases, Discussion and conclusions, Data availability, Software availability, Competing interests, Grant information, Acknowledgements, References, Figure legends. Tables are Word tables. |
| `figures/Figure1.tiff` … `Figure4.tiff` | TIFF, 300 dpi, RGB, white background, LZW-compressed. PNG copies alongside. Legends are in the manuscript and each figure is cited in the text. |
| `Conformome_ORE_manuscript.pdf` | Reading copy only. ORE does not list PDF as an accepted manuscript format; do not upload it as the manuscript. |

## Requirements the package does not meet, or that were not checked

- **Figure width.** ORE guidance for line art is 75–150 mm. The figures are 170 mm wide at 300 dpi (full text width of the repo's figure style). Either accept as is (the dpi is above the stated minimum, and the figures scale) or rebuild with `COL2` set to 150 mm in `paper/scripts/figstyle.py`.
- **TIFF compression.** ORE's fallback wording is "uncompressed TIFFs"; these use lossless LZW. Resave without compression if the system rejects them.
- **Graphs as EPS.** ORE prefers EPS or the original editable file for graphs; `paper/figures/*.pdf` are the vector originals and can be uploaded instead if asked.
- **Main-text word limit:** not found on the pages read; not checked.
- **File-size limits:** not found; not checked.
- **Reporting guidelines:** not applicable to a Software Tool Article as far as the pages read state.
- **Plain-language summary:** optional on ORE; none written. Add one if wanted.

## Suggested and excluded reviewers

Exactly as the author wrote them in `paper/ore_submission.md` (affiliations marked *confirm*, no email addresses). Prune before entering.

**Suggested:** Kresten Lindorff-Larsen (University of Copenhagen); Benjamin Schuler (University of Zurich); Andrej Šali (UCSF); Mihaly Varadi (EMBL-EBI); Michael Woodside (University of Alberta); Lewis Kay (University of Toronto); Silvio Tosatto (University of Padua).

**Excluded:** VU Amsterdam (Wuite, Peterman and Heller groups); co-authors of Halma et al. 2025 (Kumar, van Eck, Abeln, Gates); current or former LUMICKS staff.
