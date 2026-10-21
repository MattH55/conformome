# Agent task: make studies, states and transitions part of Conformome

Repository: `https://github.com/MattH55/conformome`. Start from branch `claude/conformation-schema`, which already
contains the record types and code described below. Work on `claude/integrate-studies`; open the pull request into
the default branch `ccr-ebb336f7-3qzi9h` and do not merge it. Do not touch `paper/`, `zenodo/` or `release/`, and do
not tag or publish anything.

Read first, in this order:

1. `docs/STUDIES.md`: construct, protocol, state network and occupancy records, with the rules.
2. `docs/CONFORMATIONS.md`: conformation, segment, assignment, prediction run and evaluation records, and the
   equilibrium and kinetic force models.
3. `docs/HANDOFF.md` and `curation/README.md`: how curated states, assignments, rules and transitions work today.
4. `schema/*.schema.json`, `conformome/conformations/`, and `studies/wnv-ns1prime-frameshift/`.

## What exists, and what is missing

| Exists on `claude/conformation-schema` | Missing |
| --- | --- |
| Schemas: `construct`, `protocol`, `state_network`, `occupancy`, `conformation`, `segment`, `assignment`, `prediction_run`, `evaluation` | Studies are not linked to molecule pages; their states are not curated states |
| `conformome/conformations/studies.py`: load, schema and cross-reference checks, Wilson intervals, Jensen–Shannon divergence, equilibrium comparison | The pipeline does not read studies; nothing about them reaches `build/`, the site or the downloads |
| `validate.study_errors` checks every `studies/<name>/` | Study transitions are not `transition` records; `transition.schema.json` cannot hold force-spectroscopy quantities |
| One study, WNV NS1' frameshift (Halma et al., PNAS 2019), with every unread value null | The WNV numbers; every other study |
| `make conformations`: conformations from dot-brackets and coordinates, ΔLc, force segments, baseline assignment, RNA predictions | Occupancies are not compared with predictions in the build; preparation history is not modelled |
| Site: molecule pages with a states-and-transitions diagram (`conformome/site/build.py: _diagram`) that is empty because no transitions are curated | Study panels, network graphs, occupancy bars, model comparison, a studies index |

## Outcome

After this task, a molecule page shows, for every study of that molecule, the construct and protocols, the state
network (states as nodes, transitions as edges, pathways), what each perturbation did, the measured occupancies
with intervals, and how far they are from the equilibrium and kinetic predictions. Study states are curated states
of the molecule (draft). Study transitions are ordinary `transition` records in `mapped.json`, so the existing
diagram, downloads and validation pick them up. Every number on these pages comes from a study file or from a
model run recorded as a `prediction_run`.

## Work packages (one commit each; one PR at the end)

### WP1. Extend `transition` for force spectroscopy and kinetics (schema minor bump)

`schema/transition.schema.json` today allows `quantity.type` ∈ {rate, delta_g} and an optional `kinetics` block.
Extend it, keeping every existing field and record valid:

- `quantity.type` gains `delta_lc`, `unfolding_force`, `refolding_force`, `hopping_force`, `barrier_height`,
  `distance_to_transition_state`.
- New optional fields: `direction` (unfold | refold | hop), `study` (`{network_id, protocol_id, transition_index}`
  or null), `n_events` (integer or null), `force_distribution` (the `dist` object from `state_network.schema.json`,
  moved to `common.schema.json#/$defs/distribution` and referenced from both).
- `conditions` gains `loading_rate_pn_s` and `pulling_speed_nm_s` (nullable, required with null default in
  `conformome/sources/base.py: conditions()`, like every other condition). Update every source module's call sites
  and the test fixture; the validator must stay green.

Add tests: an old transition validates unchanged; a force transition with a distribution validates; a transition
with an unknown quantity type fails.

### WP2. Molecule identity for study constructs

A study's construct must belong to a molecule page:

- Proteins: `construct.molecule_id` is the UniProt accession.
- Natural RNA: RNAcentral `URS…_<taxid>` when the construct is, or lies within, an RNAcentral sequence. Use
  `conformome/rnacentral.py`. When the construct is a region of a longer RNA, keep the region in
  `molecule_reference.start/end`.
- RNA with no RNAcentral entry (designed or viral sub-regions that RNAcentral lacks): add an `RNA-<12 hex>` id,
  the first 12 hex digits of the SHA-256 of the upper-case sequence, exactly as `conformome/molecule.py: dna_id`
  does for DNA. Add the pattern to `common.schema.json#/$defs/molecule_id`, a builder like `dna.py` that reads the
  sequence from the construct file (no network), and a collision test.
- A study whose construct sequence is still null cannot have a page. It stays in `studies/` and is reported as
  "pending sequence" by `make studies`, not as an error.

Add each linked molecule to `targets.yaml` with `batch: studies` and a `study:` key naming the study directory.

### WP3. Study states become curated states

For each molecule with a study, the curation file (`curation/<molecule_id>.yaml`) gains a `studies` block:

```yaml
studies:
  - network: SN-WNV-NS1prime
    states:            # study key -> curated state id; a missing curated state is created from the study (draft)
      PKS: WNV-PKS
      PKL: WNV-PKL
```

- `conformome/mapping/curation.py` reads the block. A study state with no curated counterpart becomes a draft
  curated state: id from the mapping, name from `label`, basis `observed` if the study state's `status` is
  `observed` and a structure resolves it, otherwise `inferred` with the assumption "assigned from force
  spectroscopy; no structure resolves it". The study's `structure.description` becomes the description, and
  `structure.dot_bracket` the secondary structure.
- The reverse link is written back into the built network: `state_id` on each study state, set at build time (do not
  edit study files from code).
- A curated state may be shared by several studies; the validator checks that a study key maps to exactly one state
  and that the mapping covers every non-U key used in transitions, pathways or occupancies.

### WP4. `make studies` pipeline step

Add a step between `map` and `models` (Makefile, `conformome/__main__.py`, `pipeline.py`):

1. Load every `studies/<name>/` (`studies.load`), validate it (`studies.schema_errors`, `studies.integrity_errors`);
   any error stops the build.
2. For each study linked to a built molecule, write `build/<molecule_id>/studies.json` with the construct,
   protocols, network (with `state_id` filled) and occupancies, with fractions and 95% intervals filled from
   counts (`studies.fill_intervals`).
3. Emit evidence records into the molecule's `evidence.json`, one per study transition with a measured ΔLc or force
   and one per occupancy: `technique: force_spectroscopy` (or the protocol's technique), `source_kind: literature`,
   `data_level: reported`, provenance from the study file, with `deposit_id` set to the network or occupancy id.
   Map each to its state with a curator assignment (`confidence: high`, justification "state assigned in the
   source study").
4. Emit `transition` records (WP1 schema) into `mapped.json["transitions"]`, one per study transition whose
   `from` and `to` map to curated states (U maps to the molecule's unfolded state, created as an inferred state if
   absent). Carry `n_events`, `delta_lc`, `force_distribution`, `rate_s`, `distance_to_ts_nm` and `barrier_kt` as
   quantities or kinetics fields. Values that are null in the study are omitted, never filled.

Tests: a synthetic study on the fixture molecule `Q00000` produces evidence, mappings and transitions; a study with an
unmapped key fails; a study with a null sequence is reported as pending.

### WP5. Models against occupancies

In the `conformations` step, for each occupancy of each linked study:

- Equilibrium: `studies.equilibrium_comparison`. Record the run as a `prediction_run` (method ViennaRNA, version,
  parameters) and the comparison in the occupancy's `comparisons` (in the build output, not the study file).
- Kinetic: `kinetics.KineticModel` with the protocol's loading rate and the macrostates of the network's states
  that have nested dot-brackets. The start distribution follows `protocol.preparation`: `annealed` →
  equilibrium at zero force; `held_at_low_force` → the master equation at `low_force_pn` for `wait_s` from the
  previous cycle's end; `cotranscriptional` → `kinetics.cotranscriptional_start`; `unknown` → do not run, say why.
  k0 is calibrated only from a measured rate in the same study; otherwise record `k0_per_s` as an uncalibrated
  default and say so in the comparison note.
- States that are pseudoknots or need tertiary contacts cannot be represented by the nested model. Report them as
  "not modelled" and compare on the remaining states only, renormalised, saying so.

Store the divergence (bits) for each comparison. Add a build-wide table of divergences to
`conformome/conformations/report.py`.

### WP6. Site

On each molecule page, after "States and transitions":

- **Studies**: one panel per study with the citation, construct (sequence, region, handles), protocols (mode,
  loading, preparation, perturbations, conditions), and the curation status with the list of missing values when
  incomplete.
- **Network graph**: extend `_diagram` (inline SVG, no external libraries): states as nodes (observed solid,
  proposed dashed), transitions as directed edges labelled with ΔLc and median force, pathways as coloured paths.
- **Perturbations**: a table of abolishes, creates, stabilizes and retains for each perturbation.
- **Occupancies**: horizontal bars with 95% intervals; equilibrium and kinetic predictions as markers on the same
  bars; divergence in bits.
- **Studies index**: a `studies/` page listing every study, its molecule, status, number of states, transitions
  and occupancies.

Downloads: `downloads/studies/<name>.json` (the built study bundle) and study records in `all-records.jsonl` with
`record_type` construct, protocol, state_network, occupancy. Numbers cited from papers are facts with a citation;
include them. Do not include text copied from papers.

Extend `validate.site_errors` so every study has a page section and every download parses against its schema.

### WP7. Curate studies

Rules for every study:

- Values only from the source text, tables, figures with numbers or supplementary files. Add a
  `curation.locators` object (schema change on all four record types) mapping each filled field path to where it
  was read: `{"network.transitions[0].delta_lc": "Table 2", …}`. A filled value without a locator fails validation.
- Never digitise a plot unless the author asks; if a value exists only in a plot, leave it null and list it as
  missing with the figure number.
- Sequences come from the paper or its supplement, or from the cited accession and coordinates; record which.
- Every study ends with status `incomplete` or `draft`. Only the author sets `reviewed`.

Order:

1. **WNV NS1' frameshift (Halma et al., PNAS 2019, doi:10.1073/pnas.1905258116).** Fill every item in the checklist in
   `docs/STUDIES.md`. The author will provide the text: either the PDF in `paper/sources/` (git-ignored) or the
   Europe PMC full-text URL `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6765238/fullTextXML` given in the
   task message. The thesis (University of Alberta ERA) has the background but its tables were not readable. The
   construct lies in RefSeq NC_009942; an independent study placed the frameshift element at nt 3420–3678 of that
   accession (Kelly et al., NAR 2025), which can be used to check the sequence.
2. **DNA hairpins under constant force (Woodside et al., PNAS 2006, doi:10.1073/pnas.0511048103).** Many sequences
   with occupancy versus force: the cleanest equilibrium test.
3. **Adenine riboswitch aptamers (Greenleaf et al., Science 2008; Neupane et al., NAR 2011).** Ligand-dependent
   states; links to the curated add aptamer `URS000080DF85_672`.
4. **Co-transcriptional folding of the pbuE riboswitch (Frieda & Block, Science 2012).** Preparation
   `cotranscriptional`: the contingency test.
5. **SARS-CoV-2 frameshift pseudoknot conformers (Neupane et al., Nat. Commun. 2021,
   doi:10.1038/s41467-021-25085-6)** and **HIV-1 frameshift signal (Ritchie et al., RNA 2017, doi:10.1261/rna.061655.117).**
6. **Titin I27 (Carrion-Vazquez et al., PNAS 1999).** A protein study, to test the protein path (ΔLc 28.4 ± 0.3 nm is
   already used as a check in `docs/CONFORMATIONS.md`).

Check every DOI against Crossref before writing it. Do not guess DOIs listed here without "doi:"; look them up.

### WP8. Documentation, tests, report

- Update `docs/STUDIES.md` (linking, pipeline step, site), `docs/CONFORMATIONS.md` (model comparisons in the build),
  `curation/README.md` (the `studies` block) and `docs/METHODS.md` (one paragraph).
- `make validate` passes with 0 errors; all tests pass except the two known audit tests that need matplotlib and a
  browser.
- Push to `claude/integrate-studies`. The Build-all workflow runs on `claude/**` branches and pushes its report to
  `reports/claude/integrate-studies`; read `build-summary.md` and `conformations-summary.md` there and quote the
  study counts in the PR.

## Hard rules

- No invented values, sequences, structures, DOIs or locators. Null and listed as missing is always acceptable.
- Values computed by Conformome are never written into measured fields; they carry method and assumptions.
- Study files are curated input; code never edits them.
- Curation stays `draft` / `incomplete`; the author reviews.
- Do not change the conflict rule, the mapping rules or the licence allow-list from `paper/ore`.
- Do not publish, tag, or open a Zenodo deposit.

## Pull request description

1. What changed per work package, with the schema version bumps.
2. Studies added, their status, and the count of filled vs missing values for each.
3. Molecules that gained pages from studies, and their ids.
4. Transitions now in `mapped.json` (count by molecule) and occupancies with model comparisons (divergence table).
5. Everything left as missing, by study, so the author can fill or confirm it.

## Done when

- `make site` builds study panels, network graphs and occupancy bars for every linked study, and a studies index.
- Study transitions appear as `transition` records and in the existing diagram.
- Each occupancy with usable structures has an equilibrium comparison; kinetic comparisons run where the
  preparation is known, and say why when they do not.
- The WNV study is filled from the paper as far as the text allows, with a locator for every value.
- `make validate` is green, the PR is open, nothing is published.
