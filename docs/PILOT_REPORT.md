# Pilot report

Status: the pipeline runs end to end on **30 proteins** and **7 evidence sources**, and `make validate` passes (49 tests, 0 validation errors). The curation is a **draft written by an assistant, not reviewed by a curator**; every page says so. This report closes the expanded pilot and waits for review.

All numbers below come from `build/<UniProt>/mapped.json` and `build/<UniProt>/ingest.json`, produced by `make site` on 2026-10-19. Raw inputs and their SHA-256 hashes are in `data/MANIFEST.json`.

## Batch multi-source-1: 51 evidence-only proteins

`targets.yaml` now lists every protein the site builds. A third batch adds the 51 proteins with at least one PDB structure, one BMRB deposit and one SMASH-BIO record, and 8 or more BMRB deposits or SMASH-BIO records (selected on 2026-10-19 from the BMRB UniProt mapping and the SMASH-BIO release). They include SARS-CoV-2 spike, ACE2, p53, histone H3.1, Hsp90-alpha, the amyloid-beta precursor protein, prion protein, TDP-43, SOD1, bacteriorhodopsin, Cas9, kinesin-1, dynein, myosins, fibronectin, von Willebrand factor, integrin beta-1, collagen I and cytochrome c.

These proteins have **no curation yet**: their pages list all their evidence, say "states not yet curated", and map nothing. The numbers in the sections below cover the 30 curated proteins only.

| | |
|---|---|
| Proteins | 51 (81 in total) |
| Evidence items | 9,187 (17,522 in total) |
| By source | RCSB PDB 6,318; SMASH-BIO 2,025; BMRB 323; MDDB 218; DisProt 143; SASBDB 112; AlphaFold DB 48 |
| Proteins with evidence from 5 or more techniques | 45 |
| Proteins with evidence from 4 or more sources | 50 |
| Largest page | SARS-CoV-2 spike, 2,468 evidence items (2 MB) |

The site also has a search page and a proteins x techniques coverage matrix on the front page; see `docs/METHODS.md` and the README.

## What changed since the first pilot

| | First pilot | Now |
|---|---|---|
| Proteins | 10 | 30 |
| Sources ingested | RCSB PDB | RCSB PDB, BMRB, SASBDB, DisProt, AlphaFold DB, MDDB, SMASH-BIO |
| Techniques with evidence | 5 | 16 |
| Evidence items | 2,510 | 8,335 |
| Mapped to a state | 18 | 5,392 |
| States | 20 | 67 (54 observed, 13 inferred) |
| States supported by more than one technique | 0 | 32 |
| Conflicts flagged | 0 | 52 |

Other changes:

- **Curated rules.** Curation files can now hold rules (technique, source, ligands present or absent, ligand text, title words, publication title). Each mapping a rule makes says `rule:<id>`, with the rule's confidence and justification. A curator assignment always wins. Items matched by rules for two different states stay unmapped and are listed as ambiguous (1 item in the whole set).
- **Integrative and SAXS entries from the PDB** are ingested as `integrative` (inferred) and `saxs_sans`, not skipped. The 9 integrative entries the first pilot dropped (for example the FRET-restrained T4 lysozyme ensemble 9A08) are now on the pages.
- **Oligosaccharide ligands.** Maltose, maltodextrins and cyclodextrins are branched entities in the PDB, not nonpolymer ligands. They are now in the ligand list as `branched: <description>`, so that MBP rules can tell maltose (closes MBP) from beta-cyclodextrin (does not).
- **Comparability for conflicts** now also requires the same construct and buffer, and force observables are not compared at all, because loading rate is not recorded.
- Curator assignments can name a PDB ID (`pdb: 4AKE`) instead of an entity-level evidence ID.

## Proteins

Accessions and organisms were checked against UniProtKB before ingestion; all 20 new accessions are reviewed Swiss-Prot entries. Anchor entries were checked against RCSB for title and UniProt mapping. Three candidates were rejected because they are mouse, not human: 1IEP and 1OPK (Abl), 2L7A (talin R3).

Evidence per source, then mapping. `Mapped` gives items mapped (curator / rule mappings). `States` gives total (observed / inferred). `Multi` counts states with mapped evidence from more than one technique.

| Protein | UniProt | Evidence | PDB | BMRB | SASBDB | DisProt | AFDB | MDDB | SMASH-BIO | Mapped (curator / rule) | States (obs / inf) | Multi | Techniques | Ambiguous | Conflicts |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| Tyrosine-protein kinase ABL1 | P00519 | 127 | 85 | 35 | 0 | 5 | 1 | 1 | 0 | 12 (4 / 8) | 4 (4 / 0) | 0 | 5 | 1 | 0 |
| Thermonuclease | P00644 | 335 | 298 | 34 | 0 | 0 | 1 | 0 | 2 | 301 (2 / 299) | 3 (2 / 1) | 2 | 5 | 0 | 0 |
| Ribonuclease | P00648 | 71 | 53 | 10 | 0 | 0 | 1 | 2 | 5 | 69 (1 / 68) | 2 (1 / 1) | 1 | 7 | 0 | 0 |
| Lysozyme C | P00698 | 1484 | 1386 | 39 | 33 | 0 | 1 | 5 | 20 | 1460 (1 / 1459) | 2 (1 / 1) | 2 | 11 | 0 | 18 |
| Endolysin | P00720 | 793 | 781 | 3 | 0 | 0 | 0 | 1 | 8 | 9 (3 / 6) | 3 (3 / 0) | 0 | 8 | 0 | 0 |
| Pancreatic trypsin inhibitor | P00974 | 169 | 128 | 23 | 10 | 0 | 1 | 7 | 0 | 160 (1 / 159) | 2 (1 / 1) | 1 | 7 | 0 | 0 |
| Subtilisin-chymotrypsin inhibitor-2A | P01053 | 37 | 26 | 5 | 0 | 0 | 1 | 5 | 0 | 37 (1 / 36) | 2 (1 / 1) | 1 | 5 | 0 | 0 |
| GTPase HRas | P01112 | 295 | 285 | 7 | 0 | 1 | 1 | 1 | 0 | 254 (2 / 252) | 2 (2 / 0) | 2 | 7 | 0 | 0 |
| Myoglobin | P02185 | 397 | 356 | 40 | 0 | 0 | 1 | 0 | 0 | 117 (4 / 113) | 4 (4 / 0) | 2 | 6 | 0 | 0 |
| ATP-dependent molecular chaperone HSP82 | P02829 | 56 | 50 | 2 | 0 | 1 | 1 | 2 | 0 | 2 (2 / 0) | 2 (2 / 0) | 0 | 6 | 0 | 0 |
| Ribose import binding protein RbsB | P02925 | 18 | 7 | 0 | 9 | 0 | 1 | 1 | 0 | 6 (2 / 4) | 2 (2 / 0) | 0 | 4 | 0 | 0 |
| Lactose operon repressor | P03023 | 49 | 25 | 14 | 0 | 0 | 1 | 0 | 9 | 15 (2 / 13) | 2 (2 / 0) | 1 | 5 | 0 | 0 |
| Immunoglobulin G-binding protein G | P06654 | 86 | 54 | 6 | 0 | 0 | 1 | 5 | 20 | 30 (1 / 29) | 1 (1 / 0) | 1 | 9 | 0 | 0 |
| Beta-2 adrenergic receptor | P07550 | 157 | 149 | 1 | 0 | 3 | 1 | 0 | 3 | 18 (3 / 15) | 2 (2 / 0) | 2 | 8 | 0 | 0 |
| Spectrin alpha chain, non-erythrocytic 1 | P07751 | 77 | 64 | 7 | 1 | 0 | 1 | 4 | 0 | 49 (1 / 48) | 2 (1 / 1) | 1 | 9 | 0 | 0 |
| pH-gated potassium channel KcsA | P0A334 | 96 | 89 | 6 | 0 | 0 | 1 | 0 | 0 | 22 (3 / 19) | 3 (3 / 0) | 1 | 4 | 0 | 0 |
| Chaperone protein DnaK | P0A6Y8 | 93 | 68 | 2 | 1 | 1 | 1 | 1 | 19 | 2 (2 / 0) | 2 (2 / 0) | 0 | 8 | 0 | 0 |
| Dihydrofolate reductase | P0ABQ4 | 192 | 165 | 5 | 0 | 12 | 1 | 0 | 9 | 80 (2 / 78) | 2 (2 / 0) | 0 | 6 | 0 | 0 |
| Chemotaxis protein CheY | P0AE67 | 69 | 61 | 6 | 0 | 0 | 1 | 1 | 0 | 61 (2 / 59) | 2 (2 / 0) | 1 | 5 | 0 | 0 |
| Maltose/maltodextrin-binding periplasmic protein | P0AEX9 | 566 | 538 | 8 | 5 | 0 | 1 | 1 | 13 | 526 (2 / 524) | 2 (2 / 0) | 2 | 8 | 0 | 0 |
| Polyubiquitin-C | P0CG48 | 505 | 380 | 39 | 15 | 0 | 1 | 2 | 68 | 420 (1 / 419) | 1 (1 / 0) | 1 | 10 | 0 | 0 |
| Calmodulin-1 | P0DP23 | 400 | 345 | 21 | 8 | 2 | 1 | 3 | 20 | 2 (2 / 0) | 2 (2 / 0) | 0 | 9 | 0 | 0 |
| Microtubule-associated protein tau | P10636 | 374 | 315 | 10 | 8 | 5 | 1 | 0 | 35 | 299 (2 / 297) | 3 (2 / 1) | 3 | 11 | 0 | 1 |
| Alpha-synuclein | P37840 | 346 | 253 | 47 | 11 | 15 | 1 | 0 | 19 | 262 (2 / 260) | 3 (2 / 1) | 3 | 14 | 0 | 33 |
| Green fluorescent protein | P42212 | 722 | 657 | 2 | 0 | 0 | 1 | 0 | 62 | 682 (1 / 681) | 2 (1 / 1) | 1 | 5 | 0 | 0 |
| Peptidyl-prolyl cis-trans isomerase A | P62937 | 215 | 205 | 8 | 0 | 0 | 1 | 1 | 0 | 204 (1 / 203) | 2 (1 / 1) | 1 | 7 | 0 | 0 |
| Adenylate kinase | P69441 | 31 | 29 | 0 | 0 | 0 | 1 | 0 | 1 | 19 (2 / 17) | 2 (2 / 0) | 0 | 3 | 0 | 0 |
| Peptidyl-prolyl cis-trans isomerase NIMA-interacting 1 | Q13526 | 222 | 194 | 25 | 0 | 1 | 1 | 1 | 0 | 222 (1 / 221) | 2 (1 / 1) | 1 | 5 | 0 | 0 |
| Titin | Q8WZ42 | 279 | 66 | 2 | 8 | 1 | 0 | 2 | 200 | 19 (1 / 18) | 2 (1 / 1) | 1 | 8 | 0 | 0 |
| Talin-1 | Q9Y490 | 74 | 4 | 16 | 3 | 0 | 1 | 0 | 50 | 33 (1 / 32) | 2 (1 / 1) | 1 | 7 | 0 | 0 |

Totals by source: RCSB PDB 7,116; SMASH-BIO 563; BMRB 423; SASBDB 112; DisProt 47; MDDB 46; AlphaFold DB 28.

Totals by technique: xray 5,620; cryoem 1,152; force_spectroscopy 563; nmr_shifts 421; nmr_structure 300; saxs_sans 118; md 46; microed 30; af_prediction 28; nmr_dynamics 18; integrative 13; neutron 12; cd 9; ftir_raman 2; epr_deer 2; gel_electrophoresis 1.

## Items not ingested, and why

Every skipped item is listed with its ID and reason in `build/<UniProt>/ingest.json`.

- RCSB PDB: 14 powder-diffraction entries of hen lysozyme (no technique mapping yet; they could map to `xray`).
- BMRB: 10 entries with no shift, relaxation or exchange data.
- DisProt: 41 regions, most with non-structural terms (protein binding, lipid binding, flexible linker); 2 whose method has no mapping (atomic force microscopy, unspecified spectrometry).

## Conflicts found

52 conflicts, all on SASBDB radii of gyration. They split into two groups:

- **Hen lysozyme (18):** the same sample analysed over different q-ranges (SWAXS) gives Rg values that differ beyond their errors. These are real flags of the kind the brief asks for.
- **Alpha-synuclein (33) and tau (1):** K-to-R mutants measured at different NaCl concentrations. SASBDB summaries record neither the mutation nor the salt separately, so the entries look comparable when they are not. **These are artefacts of missing fields**, and a curator should dismiss them or the source parser should recover the salt and mutation from the entry description.

A first run also flagged ubiquitin and BPTI, but those compared free protein with complexes (MINDY2, PDI). Partners are now recorded as `partner: <name>` ligands, which removes those false comparisons.

## States without evidence

5 inferred states have nothing mapped yet: the unfolded states of BPTI, CI2, alpha-spectrin SH3 and Pin1, and the minor state of cyclophilin A. Their BMRB entries are shift-only and there are no SMASH-BIO unfolding records for them. Denaturation, relaxation dispersion and literature evidence would fill them.

## Low-confidence rules to review first

These rules map many items with a stated low confidence. Each is a curator judgement that should be confirmed or removed:

- AlphaFold predictions and MD simulations mapped to the native state of folded proteins.
- MBP structures with no maltodextrin mapped to the open state (many are MBP fusions).
- Apo E. coli ADK crystal structures mapped to open; unphosphorylated CheY mapped to inactive.
- SMASH-BIO force records classed as protein unfolding mapped to unfolded states. Most SMASH-BIO records are extracted automatically (from abstracts or full text); the extraction level is shown on each item.

## What the schema could not represent

1. **Paralogs with identical sequence.** CALM1, CALM2 and CALM3 share one sequence; about 70 PDB entity hits sit under the sibling accessions and are not on the calmodulin page.
2. **Loading rate.** Unfolding and rupture forces depend on it, and the conditions schema has no field for it, so force values are never compared.
3. **Salt and mutations.** The conditions schema has a salt field, but sources rarely fill it; mutations are free text in the construct. This is what produced the alpha-synuclein false conflicts.
4. **Isoform numbering.** DisProt annotates tau on isoform P10636-8 (2N4R). Residue ranges are kept with the isoform named, but are not mapped to canonical numbering.
5. **Scope of a state.** A domain-level state (Hsp90 N-terminal domain, the spectrin SH3 domain within the whole spectrin chain) has no residue-range field.
6. **Ligands are entry-level**, not entity-level.
7. **Population weights** for ensemble members, and fractional mapping of one item to several states.

## Not done

- **PED:** the API paths returned 404 on 2026-10-19. PED ensembles that are PDB integrative entries come through the PDB.
- **PDB-IHM restraints:** integrative entries are ingested, but their restraint tables are not parsed.
- **ATLAS:** indexed by ECOD chain, not UniProt; MD comes from MDDB instead.
- **Literature extraction:** none. The stub enforces the review-before-live rule.
- **RMSD mapping rule:** implemented and tested, still not run on the pilot.
- **Transitions:** none curated.
- **Inferred models:** none fitted.
- **Deployment:** Pages, DNS and Zenodo are not configured.
- **Licences:** BMRB, SASBDB and SMASH-BIO data licences are marked "verify". The project licence is not chosen.

## Decisions needed from the review

1. Curators for each protein, starting with the rules listed under "Low-confidence rules".
2. SMASH-BIO data licence. You maintain SMASH-BIO, so stating a licence there would let its records into the downloads; for now they appear on pages only.
3. Whether to recover salt and mutations from SASBDB descriptions, or to dismiss the alpha-synuclein conflicts by curation.
4. Paralog grouping for calmodulin.
5. Whether powder-diffraction entries should count as `xray`.
6. Whether to run the RMSD rule, and how to cache coordinates for about 8,000 PDB entities.
7. Project licence, and GitHub Pages or Cloudflare Pages.
