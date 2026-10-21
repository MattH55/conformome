# Agent task: populate the Conformome resource

Repository: `https://github.com/MattH55/conformome`. Put this file in `agent-handoff/POPULATE_RESOURCE.md`.

The pilot release covers 81 proteins (30 with draft curation) and 2 nucleic acids (1 curated), from 9 sources and 20 of the 51 techniques in `taxonomy/techniques.yaml`. Most of the schema and taxonomy is still unused: transitions, mutational effects, profiles, family vocabularies, raw-data pointers, complexes, and 31 techniques with no records. This task fills them from real deposited data, in order, one work package (WP) per pull request.

Read first, in this order: `docs/HANDOFF.md`, `docs/METHODS.md`, `docs/SOURCES.md`, `curation/README.md`, `conformome/sources/base.py` (the source contract), and `NUCLEIC_ACIDS_BRIEF.md` §1–§7.

## Branching: keep the paper release frozen

The ORE paper describes tag `v0.1.0`, which is cut from `paper/ore` by `agent-handoff/AGENT_INSTRUCTIONS.md`.

- Start from the `v0.1.0` tag once it exists. Until then, start from the tip of `paper/ore` and rebase onto the tag when it appears.
- Work on `resource/<wp-id>` branches, one per WP. Open each PR into the default branch `ccr-ebb336f7-3qzi9h`. Do not merge, and do not touch `paper/`, `zenodo/` or `release/`.
- The next public release is `v0.2.0`. Do not tag it; the author does.

## Rules for every WP

1. **No invented data.** Every evidence record, state, representative structure, transition and mutational effect comes from a deposited record you have fetched, or from a curated rule applied to such records. If an identifier cannot be checked against its source, leave the item out and list it in the PR.
2. **Licence before ingestion.** A new source gets a `docs/SOURCES.md` row (licence, `redistribute`, notes) **before** its module is merged. Read the source's own terms page and quote the clause in the PR. If the terms are unclear, mark the licence `(verify)` and set `redistribute: no`. Only the author changes that later.
3. **Follow the source contract** in `conformome/sources/base.py`: `KEY`, `NAME`, `LICENCE`, `IMPLEMENTED`, `MOLECULE_TYPES`, `fetch` (network, cached, writes a manifest row through `save_raw`) and `parse` (pure, no network). Also add `not_ingested` with a reason for each skipped item. Store unknown conditions as `null`, never omit them. Set `data_level` truthfully.
4. **Curation is a draft.** Every new or changed curation file is `status: draft`, `curator: draft (unreviewed)`. Each mapping carries a confidence and a one-line justification. Check every representative PDB ID against RCSB (title, chain, UniProt or sequence mapping) before writing it. Use family-vocabulary labels only from `taxonomy/state_vocabularies/`.
5. **Be polite to servers.** Honour each source's rate limits and robots rules, use the HTTP cache in `data/raw/_cache`, and back off on 429/5xx. Never bypass a refused or paywalled page.
6. **Green builds.** `make validate` passes with 0 errors and new tests pass. Each new source has a parse test against a committed, trimmed real response (as `tests/` already does for PDB GraphQL) and a fixture molecule case.
7. **Count before and after.** Every PR includes the output of `scripts/report_counts.py` before and after the change: molecules, evidence by source and technique, states (observed/inferred), single-method states, states with no evidence, conflicts, transitions, mutational effects. Explain every change in a count larger than 5%.
8. **Do not decide for the owner.** The items in "Owner decisions" at the end are implemented behind a configuration switch that is **off by default**, and reported in the PR.

## WP1: clean the existing evidence (small, do first)

| Item | Change | Done when |
| --- | --- | --- |
| SASBDB salt and mutations | Parse salt concentration and mutations from SASBDB entry descriptions and sample fields into `conditions.salt_mM`, `conditions.buffer` and the construct's variant list. Keep the raw string. | The α-synuclein K→R / NaCl pairs are no longer comparable. List the conflicts removed, with their SASBDB codes. |
| Isoform numbering | Map DisProt regions annotated on isoforms (e.g. tau P10636-8) onto canonical numbering by aligning the isoform sequence from UniProt. Keep the original range. | Tau regions show both ranges; a test covers the alignment. |
| Domain scope | Add an optional `residue_range` to states (schema minor version bump), so that a domain-level state (Hsp90 NTD, spectrin SH3) says which residues it covers. Rules may then match only evidence whose construct overlaps the range. | Hsp90 and spectrin curation use it; the validator checks ranges against the sequence length. |
| DisProt methods | Map the two unmapped ECO methods only if a technique id fits exactly; otherwise leave them in `not_ingested` with the reason. | `ingest.json` reasons are specific. |
| Raw-data pointers | Fill `data_level: raw` links where the deposit points to raw data: EMPIAR for cryo-EM entries (via the EMDB → EMPIAR cross-reference), BMRbig for NMR, SBGrid/proteindiffraction.org for X-ray where listed, SMASH-BIO trace links. | Coverage-grid data levels change only where a link exists. |

## WP2: query existing sources for nucleic acids

`MOLECULE_TYPES` defaults to proteins, so the riboswitch has no NMR, SAXS, MD or force data on its page. For each of PDB, BMRB, SASBDB, MDDB and SMASH-BIO:

- Find how the source identifies nucleic acids: RCSB sequence search and entity polymer type; BMRB by molecular system and sequence; SASBDB by sample sequence; MDDB by metadata; SMASH-BIO entity annotations.
- Match by exact sequence, or by RNAcentral id where the source carries one. A construct that differs from the reference is kept only with its alignment in `construct.aligned_to_reference`.
- Set `MOLECULE_TYPES` and add tests.
- Avoid duplicating NAKB: a PDB entry already ingested through NAKB is not ingested twice. Pick one source per PDB id and record which.

Done when the adenine riboswitch and the G-quadruplex pages show every deposited technique the sources hold for them, and the PR lists what was found per source.

## WP3: implement the stub sources

| Stub | Task | If blocked |
| --- | --- | --- |
| PED (`ped.py`) | Find PED's current documented API (the 2026-10-19 paths returned 404). Ingest ensembles as `ped_ensemble` evidence (inferred, with the ensemble's own experimental restraints listed), mapped to proteins by UniProt. Ensembles that are also PDB integrative entries are not duplicated. | Record the URLs tried and the responses in `docs/SOURCES.md`, and leave the stub. |
| PDB-IHM restraints (`pdbihm.py`) | Parse the restraint tables of integrative entries from their mmCIF (crosslinks, derived distances such as FRET, SAS datasets) into evidence with observables `distance` / `fret_efficiency` / `radius_of_gyration`, linked to the parent integrative entry. | Parse the subset with a clear observable; list the rest. |
| ATLAS (`atlas.py`) | Map ATLAS ECOD-chain entries → PDB chain → UniProt (via SIFTS), and ingest each simulation as `md` (prediction), with the PDB chain as the construct. | Same. |
| PDB technique refinements | Emit `xray_time_resolved` (serial or time-resolved crystallography, from the experiment and diffraction metadata) and `cryoem_heterogeneity` (entries from one EMDB map set with several deposited conformations), using rules documented in `docs/METHODS.md`. | Keep `xray` / `cryoem`. |

## WP4: new sources

Implement in this order. Each one is a module, a `SOURCES.md` row, and tests. Find each source's current download or API from its own documentation, and record the URL and access date in the module docstring.

1. **RMDB** (RNA chemical probing). Ingest SHAPE, DMS and other probing datasets as `shape` / `dms_mapseq` / `na_footprinting` evidence. Each record carries a per-nucleotide profile sidecar (`profiles/<evidence_id>.json`, per `NUCLEIC_ACIDS_BRIEF.md` §7) and its conditions, including ions. Compute the profile-versus-dot-bracket agreement score as `mapping.agreement` (method named), and show it on the page. It does **not** create mappings.
2. **Folding thermodynamics and kinetics.** Use the Protein Folding Database (PFDB), ProThermDB and ThermoMutDB, and the mega-scale stability dataset (Tsuboyama et al. 2023; its deposited data release).
   - Wild-type ΔG of unfolding and folding/unfolding rates become `transition` records between the curated native and unfolded states, with `conditions` (temperature, pH, denaturant) and `evidence_ids`.
   - Point-mutant ΔΔG values become `mutational_effect` records (`schema/mutational_effect.schema.json`), with `state_pair` set to the same two states.
   - Only for molecules that have both states curated.
   - Normalise sign conventions and record them in the provenance.
3. **Deep mutational scans** from MaveDB, as `mutational_effect` records. Use only score sets whose assay reports stability, folding or conformational equilibrium (state the assay in `method`); skip pure fitness or activity scans. MaveDB licences are per dataset: carry each one through.
4. **Force-spectroscopy transitions from SMASH-BIO.** Where a SMASH-BIO record reports ΔG, a rate at zero force, or Bell–Evans parameters for a curated state pair, emit a `transition` with `applied_force_pn` and the loading rate if the record has it. Add a `loading_rate_pN_s` field to conditions (schema bump). This also lets force observables enter conflict detection, but only when both items record a loading rate.

## WP5: expand the molecule set

1. **The four remaining pilot nucleic acids** from `NUCLEIC_ACIDS_BRIEF.md` §5: class-I preQ1 riboswitch, HIV-1 TAR, *Tetrahymena* P4–P6 and the SARS-CoV-2 frameshifting element. Add them to `targets.yaml` (batch `nucleic-acid-2`) with checked RNAcentral ids. Each needs evidence from at least two techniques, or it is left out and named in the PR.
2. **A selection script, `scripts/select_targets.py`, for the next protein batch** (`multi-source-2`, at most 60 proteins). It ranks UniProt accessions by the number of distinct techniques with deposited data across the implemented sources. It favours proteins with a family vocabulary (kinases, GPCRs, ion channels, transporters, riboswitch-binding proteins) and proteins with WP4 thermodynamic or DMS data. It writes its criteria and the selection date into `targets.yaml` comments. Commit the script output, not a hand-picked list.
3. **Complexes** (`CPX-…` ids; `ingest` currently raises `NotImplementedError`). Implement the minimal case: a complex defined by its component molecule ids, evidence from PDB entries that contain all components, and states curated like any other molecule. Pilot it on two complexes that have several states deposited, chosen from the existing molecules (for example a riboswitch with a protein partner, or MBP with a partner). Record the choice and the reason.

## WP6: draft curation

Work in this order:

1. **The 51 evidence-only proteins**, starting with those with the most techniques (spike, p53, APP, Hsp90-α, histone H3.1, then the rest). For each:
   - Define states from the protein's family vocabulary where one exists, otherwise from the conformations its deposits actually show.
   - Write curator assignments for anchor structures and rules for the rest.
   - Target: at least 50% of evidence mapped, 0 ambiguous items without a note.
2. **The telomeric G-quadruplex**, with states split by topology and cation (K⁺ hybrid forms, Na⁺ antiparallel basket, crystal parallel form). Recover cations from the primary publication of each deposit where NAKB lacks them, citing the DOI in the justification.
3. **The five inferred states with no evidence** (unfolded BPTI, CI2, spectrin SH3, Pin1; minor state of cyclophilin A). Fill them from WP2–WP4 data (relaxation dispersion in BMRB, folding data, SMASH-BIO unfolding). If nothing qualifies, leave them empty and say so.
4. **Family labels**: apply vocabulary labels to every new kinase, GPCR, ion-channel and transporter state.

Write `curation/REVIEW_QUEUE.md`, one row per molecule: rules with low confidence, items mapped only by rule, representative structures, open questions. Curators work from this file.

## WP7: literature extraction, behind review

Implement `literature.py` for the techniques no archive covers: smFRET, HDX-MS, denaturation midpoints, relaxation-dispersion populations and rates, and DEER distances. Search Europe PMC open-access full text for the curated molecules.

- Extract values with the exact text span, units, uncertainty and conditions.
- Write them to `literature/queue/<molecule_id>.jsonl` with `status: pending`. **Nothing pending is ingested.** The build reads only items a human has marked `status: accepted` (with reviewer and date).
- Never store more than the extracted span. Full text is never redistributed (`SOURCES.md` already says so).

Done when the queue exists for the curated molecules and a review sheet generator (`scripts/literature_sheet.py`) produces a CSV for the author.

## WP8: site and downloads

- Rename the Proteins page and nav to **Molecules**, with a molecule-type filter. Keep the existing URLs and add a `molecule/<id>/` alias.
- Write one download bundle per molecule (`downloads/molecules/<id>.json`); keep `proteins/` as a compatibility copy for one release.
- Add a **Gaps** page generated from the build: states supported by a single technique, states with no evidence, molecules with no curation, and techniques with no records. It is the public to-do list and is what makes the resource useful to experimentalists.
- Add transition and mutational-effect tables to molecule pages, and a `profiles.zip` download.

## Owner decisions (implement behind a switch that is off by default; report in the PR)

1. Calmodulin paralog grouping (CALM1/2/3 share a sequence). Implement `group_identical_sequences: false` in configuration.
2. Powder-diffraction lysozyme entries as `xray`. Implement `count_powder_as_xray: false`.
3. Running the RMSD mapping rule. Implement a coordinate cache with a size budget and a dry-run mode that reports, without mapping, how many items it would map and how many current mappings it would contradict, on the curated molecules only.
4. The SMASH-BIO data licence (a one-cell change in `SOURCES.md`, the author's call).
5. The project licence for code and curation.

## Order and pull requests

| PR | WP | Depends on |
| --- | --- | --- |
| 1 | WP1 data clean-up | `v0.1.0` tag |
| 2 | WP2 nucleic acids in existing sources | 1 |
| 3 | WP3 stubs (PED, PDB-IHM, ATLAS, technique refinements) | 1 |
| 4 | WP4.1 RMDB and profiles | 2 |
| 5 | WP4.2–4.4 thermodynamics, kinetics, DMS, force transitions | 1 |
| 6 | WP5 molecule expansion | 2, 3 |
| 7 | WP6 curation | 4, 5, 6 |
| 8 | WP7 literature queue | 1 |
| 9 | WP8 site and downloads | 6 |

Each PR description lists: what was added, the counts before and after (rule 7), the sources and licences touched, the items left out and why, and the curation changes awaiting review.

## Done when

- Every stub source is either implemented or has a recorded reason it cannot be.
- RMDB, the folding and stability sources, and MaveDB are ingested with licences recorded.
- All six pilot nucleic acids and the next protein batch are built.
- Every built molecule has draft curation or is named in `REVIEW_QUEUE.md` with the reason it has none.
- Transitions and mutational effects appear on molecule pages for every molecule with qualifying data.
- The Gaps page and the Molecules page are live in the build.
- `make validate` is green, nothing has been published or tagged, and every curation change is marked as a draft.
