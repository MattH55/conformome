# Methods

## What a page is

One page per protein, keyed on its UniProt accession. A page lists the **states** a protein is curated to have, the **evidence** from each technique that has probed it, how each evidence item maps to a state, the **conflicts** between comparable measurements, and the **models** exported for observed states.


The proteins built are listed in `targets.yaml`. A protein with no curation file still gets a page with all its evidence, labelled "states not yet curated"; nothing on it is mapped until a curator defines states.
## Observed and inferred

Every state and every model carries one of two labels.

- **Observed**: the state is directly resolved by a structure determination. X-ray crystallography, cryo-EM, microED, neutron diffraction and NMR structure determination are observed methods.
- **Inferred**: the state or model is fitted to indirect constraints. Smoothed or averaged measurements (smFRET, force spectroscopy, HDX-MS, SAXS, CD, relaxation dispersion and the rest of the taxonomy) are inferred.
- Integrative models (PDB-IHM entries distributed through the PDB) are inferred: they are fitted to several kinds of restraints.
- Computational predictions (AlphaFold DB models, molecular dynamics, Markov state models, AlphaFold-based ensembles) are inferred and also flagged as predictions.

An inferred state or model must list its assumptions. The pipeline refuses to build one without them, and the page shows them one click away.

## Evidence

One evidence item per experiment or deposit:

- RCSB PDB: one item per polymer entity whose UniProt mapping includes the accession.
- BMRB: one item per entry in BMRB's UniProt mapping.
- SASBDB: one item per entry whose sample lists a molecule with this UniProt code (radius of gyration with its error).
- DisProt: one item per curated region with a structural-state or structural-transition term; the ECO evidence code names the technique.
- AlphaFold DB: one item per predicted model (mean pLDDT).
- MDDB: one item per simulation project that references the accession (trajectory length).
- SMASH-BIO: one item per extracted force-spectroscopy result, or one study-level item when a record has no extracted value. The extraction level (automatic or curated) is kept on the item.

Items a source returns but that cannot become evidence (an unmapped method, a non-structural term, a sample without the protein) are listed with the reason in `build/<UniProt>/ingest.json`. Each item records the technique, the construct, the conditions (environment, temperature, pH, ligands, applied force), the observable with its value, uncertainty and unit, the provenance (source, DOI, deposit ID, retrieval date, licence) and a link to the data.

Conditions are always present. An unknown value is recorded as null, not omitted. Temperatures from mmCIF fields (defined in kelvin) are converted to degrees Celsius. pH and temperature are null when an entry does not carry them in its machine-readable fields.

## Mapping

Each link from an evidence item to a state is a **mapping record**: who made it, a confidence (high, medium or low), and a one-line justification. The mapping is always shown on the page next to the evidence.

- **Curator assignment** (`who: curator:<name>`): the curator names the evidence and the state in `curation/<UniProt>.yaml`.
- **Curated rule** (`who: rule:<rule id>`): the curator writes criteria in the same file: techniques, sources, observable types, environment, ligands present or absent, and words in the title. Every criterion given must hold. Each rule carries its own confidence and justification, which every mapping it makes repeats.
- A curator assignment always wins: rules are not applied to evidence the curator has assigned.
- When rules for two different states match the same item, the item stays unmapped and is listed as ambiguous on the page.
- **Anchor RMSD** (`who: rule:anchor_rmsd`): a structure clusters with an anchor when its C-alpha RMSD, after superposition on shared residues, is within a cut-off. The superposition is implemented and tested. It is not yet run on the pilot, because it needs coordinates for every candidate entry.

Ambiguous evidence stays unmapped. Unmapped evidence is listed on the page and counted, and is never assigned to a state silently.

## Conflicts

Two evidence items conflict when they are mapped to the same state, report the same observable type and unit, have comparable conditions (environment, temperature within 5 °C, pH within 0.5, the same ligands), both carry an uncertainty, and their values differ by more than the combined uncertainty. Conflicts are shown on the page. Values are never averaged across a conflict.

Force observables (unfolding, rupture and similar forces) are not compared: they depend on loading rate, which the conditions schema does not record, so values from different pulling protocols are not comparable.

Evidence without an uncertainty is not compared. The page says how many items could not be compared, and that absence of a conflict is not agreement.

## Coverage grid

For each protein, the grid counts mapped evidence per state and technique. A state whose mapped evidence comes from exactly one technique is shaded and labelled "one method", so a state that rests on a single technique is visible at a glance.

## Models

Observed states export the representative PDB entry's coordinates, unchanged, as PDB and mmCIF files. The file header records the state, its basis and the source entry. Inferred states will get fitted models in a later stage; the pilot exports none.

## Transitions

A transition is directional and carries a rate or a free-energy difference, the conditions it was measured under, and the evidence IDs behind it. No transitions are curated in the pilot.

## Reproducibility

Every number on the site is produced by `make site` from `build/`, which is produced by `make ingest`, `make map` and `make models` from the raw downloads in `data/raw/`. The download manifest, `data/MANIFEST.json`, records the URLs, retrieval dates and SHA-256 hashes of each raw input. Raw downloads are not committed.

## Known limits of the pilot

- Only the canonical isoform of each protein is recorded.
- Literature extraction, PED and PDB-IHM restraint tables are not yet ingested. ATLAS is not ingested; MD comes from MDDB.
- Entries annotated to a sibling accession with an identical sequence (for example CALM2 and CALM3 for calmodulin) are not grouped with the pilot accession. See the pilot report.
- Curation is a draft and is labelled as such on every page until a curator reviews it.
