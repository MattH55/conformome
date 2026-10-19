# Pilot report

Status: the pipeline runs end to end on the ten pilot proteins, and `make validate` passes. The curation is a **draft written by an assistant, not reviewed by a curator**. Every page says so. This report stops the pilot here, as the brief asks, and waits for review.

All numbers below come from `build/<UniProt>/` and `build/<UniProt>/ingest.json`, produced by `make site` on 2026-10-19 from the RCSB PDB archive (search and GraphQL APIs). Raw inputs and their SHA-256 hashes are in `data/MANIFEST.json`.

## Accessions confirmed before ingestion

Each accession and organism was checked against UniProtKB. Two first guesses were wrong and were replaced.

| Protein | UniProt | Organism | Note |
|---|---|---|---|
| Adenylate kinase | P69441 | *E. coli* K12 | P0A6D7 is shikimate kinase, so not used |
| Calmodulin | P0DP23 | *H. sapiens* | CALM1; CALM2 and CALM3 share the sequence (see below) |
| T4 lysozyme | P00720 | Enterobacteria phage T4 | |
| Maltose-binding protein | P0AEX9 | *E. coli* K12 | |
| Ubiquitin | P0CG48 | *H. sapiens* | polyubiquitin-C; P62987 is UBA52, so not used |
| Protein G B1 domain | P06654 | *Streptococcus* sp. group G | full-length protein; the GB1 domain is the target |
| Hsp90 | P02829 | *S. cerevisiae* S288c | HSP82 |
| Lac repressor | P03023 | *E. coli* K12 | |
| Alpha-synuclein | P37840 | *H. sapiens* | |
| Titin (Ig repeat I27) | Q8WZ42 | *H. sapiens* | curator's choice, from SMASH-BIO force records; see below |

## Evidence counts by technique

Evidence is one item per PDB entity mapped to the accession. `Mapped` counts items with a curator mapping.

| Protein | PDB entries | Evidence | Mapped | States (observed / inferred) | Evidence by technique | Conflicts |
|---|---:|---:|---:|---|---|---:|
| Adenylate kinase | 29 | 29 | 2 | 2 (2 / 0) | xray 29 | 0 |
| Calmodulin-1 | 341 | 344 | 2 | 2 (2 / 0) | xray 164, cryoem 134, nmr_structure 46 | 0 |
| T4 lysozyme | 780 | 780 | 3 | 3 (3 / 0) | xray 765, cryoem 12, nmr_structure 2, neutron 1 | 0 |
| Maltose-binding protein | 532 | 538 | 2 | 2 (2 / 0) | xray 380, cryoem 147, nmr_structure 11 | 0 |
| Ubiquitin | 349 | 378 | 1 | 1 (1 / 0) | xray 232, cryoem 93, nmr_structure 53 | 0 |
| Protein G (GB1) | 54 | 51 | 1 | 1 (1 / 0) | nmr_structure 23, xray 17, cryoem 11 | 0 |
| Hsp90 (HSP82) | 50 | 49 | 2 | 2 (2 / 0) | xray 48, nmr_structure 1 | 0 |
| Lac repressor | 25 | 25 | 2 | 2 (2 / 0) | xray 15, nmr_structure 10 | 0 |
| Alpha-synuclein | 253 | 250 | 2 | 3 (2 / 1) | cryoem 216, xray 18, nmr_structure 14, microed 2 | 0 |
| Titin (I27) | 64 | 66 | 1 | 2 (1 / 1) | xray 54, nmr_structure 10, cryoem 2 | 0 |
| **Total** | **2,477** | **2,510** | **18** | **20 (18 / 2)** | xray 1,722, cryoem 615, nmr_structure 170, microed 2, neutron 1 | **0** |

Mapping rules used: `curator` only, 18 of 18 mappings. `rule` mappings: 0. The RMSD rule is implemented and tested but not run (see gaps).

## Entries not ingested, and why

Every skipped entry is listed with its ID and method in `build/<UniProt>/ingest.json`.

- **No experimental method (computed or integrative models).** 9 entries: 9A08 (T4 lysozyme, FRET-restrained ensemble), 9AAO (Hsp90), 9A1C and 9A1D (protein G, CS-Rosetta models), 9A1L and 8ZZ4 (ubiquitin, including a CUE domain complex), and 9A1A, 9A1H and 9A1Q (alpha-synuclein ensembles). They are not silently dropped, but they have no technique and no label yet. See gap 2 below.
- **Solution scattering** (SAXS): 2KLK (protein G) and 2LV6 (calmodulin). These belong to the SASBDB source, which is not implemented.

## States defined

| Protein | States (basis) | Representative entry |
|---|---|---|
| Adenylate kinase | open, apo (observed); closed, Ap5A-bound (observed) | 4AKE; 1AKE |
| Calmodulin-1 | Ca2+-saturated extended (observed); Ca2+-saturated collapsed, trifluoperazine-bound (observed) | 1CLL; 1CTR |
| T4 lysozyme | wild type (observed); L99A cavity, apo (observed); L99A cavity, benzene-bound (observed) | 2LZM; 3DMV; 1L83 |
| Maltose-binding protein | open, apo (observed); closed, maltose-bound (observed) | 1JW4; 1ANF |
| Ubiquitin | folded (observed) | 1UBQ |
| Protein G (GB1) | native (observed) | 1PGA |
| Hsp90 | closed, nucleotide-bound complex (observed); N-terminal domain, apo (observed) | 2CG9; 1AH6 |
| Lac repressor | inducer-bound (observed); operator-bound (observed) | 2P9H; 1EFA |
| Alpha-synuclein | disordered monomer (inferred, 3 assumptions); helical on micelle (observed); fibril (observed) | 1XQ8; 6A6B |
| Titin I27 | folded (observed); unfolded under force (inferred, 3 assumptions) | 1TIT |

Models: 18 observed states exported, each as PDB and mmCIF (36 files), with a header naming the state and the source entry. No inferred model has been fitted.

## Conflicts found

None, and this is less informative than it sounds. Only evidence with a value, a comparable observable type and an uncertainty can conflict. PDB records give a resolution with no uncertainty, so every pilot item is in the "not compared" group. Structural evidence needs a different comparable quantity before conflicts can be detected for it (see gaps).

## Coverage: what the grid shows

Every state in the pilot rests on a single technique. That is the honest state of the pilot, not a finding about the proteins. Only representative entries are mapped; the rest of the evidence is ingested and listed but unmapped. The main next step is turning the grid from one cell per state into the real picture, which needs the mapping rule below.

## What the schema could not represent

These are the questions the review should answer. Each one changes the schema or the rules, so I have not decided them alone.

1. **Paralogs with identical sequence.** CALM1, CALM2 and CALM3 share one sequence, but each has its own UniProt accession. RCSB annotates about 70 entity hits (46 under P0DP29, 24 under P0DP33) to the siblings, which the accession-keyed query does not return. The apo calmodulin structures I looked for are among them. Options: an accession group per sequence identity, or one page for the group with the accession as a field.
2. **Computed and integrative entries.** 9 PDB entries have no method, so there is no technique for them. Options: map them to `pdbihm` or a new `computational` technique, or hold them for their own source. Either way they must be labelled as predictions or integrative models.
3. **Structural conflicts.** Resolution has no uncertainty, so structures never conflict. A comparable structural observable is needed, such as an inter-domain distance with its error, or a per-state RMSD between representatives.
4. **Scope of a state.** Hsp90 `N-terminal domain, apo` is a domain, not a full-length conformation. The state schema has no field for a residue range or domain scope. I wrote it into the description, which is not enough for comparison.
5. **Ligands are entry-level.** The ligand list belongs to the whole entry, not to the entity that carries the evidence. In 1EFA, the operator DNA and the anti-inducer share an entry with the repressor.
6. **Populations of ensembles.** An NMR ensemble has members with weights, and the state schema does not hold weights. An evidence item may also map to several states with fractional occupancy, which the mapping record does not express.
7. **Missing conditions.** Temperature and pH are null for many entries. Buffer and salt are never recorded for PDB evidence. The schema accepts null, but the coverage grid cannot tell "not measured" from "not deposited".

## Gaps: what is not done

- **Sources.** Only RCSB PDB is ingested. BMRB, SASBDB, PED, PDB-IHM, ATLAS/MDDB and literature are stubs, and each stub says what it needs. SMASH-BIO is blocked: its release files are not in the checkout, and its data licence is not stated (only "research and educational purposes"), so its evidence is set to not redistributable.
- **Titin evidence.** The curator's protein has no SMASH-BIO evidence yet. Its unfolded state is defined but has nothing behind it.
- **RMSD mapping.** `rmsd_ca` (Kabsch superposition) is implemented and tested. It is not wired to coordinate downloads for the pilot, because that would mean downloading coordinates for about 2,500 entries. The decision on how to cache them belongs to the review.
- **Transitions.** None are curated; no rate or free-energy evidence is ingested.
- **Isoforms.** Only the canonical isoform is recorded.
- **Literature.** None extracted. The brief's rule (nothing extracted goes live unreviewed) is enforced by the stub, not by a working pipeline yet.
- **Viewer.** Verified in headless Chromium with software WebGL: the page loads with no console errors, and the structure draws. Not checked on real GPUs or across browsers.
- **Deployment.** Not configured. Pages needs its source set to GitHub Actions; the custom domain needs DNS at Namecheap; Zenodo archiving happens at the first tagged release. None of these has been done.
- **Licence.** No project licence has been chosen for code or curation. The validator rejects `TBD` licences in `docs/SOURCES.md`, but it does not check the project licence.

## Decisions needed from the review

1. Who is the curator for each pilot protein? Every curation file says `draft (unreviewed)` and the states, representatives and assumptions need expert review.
2. Where is the SMASH-BIO release file, and what is its data licence? Without it the titin evidence and the curator's protein choice stay unfilled.
3. How should paralogs be grouped (gap 1)?
4. How should integrative and computed PDB entries be labelled (gap 2)?
5. Should the RMSD rule run on the pilot, and with what coordinate cache (gap RMSD)?
6. Project licence for code and for curation.
7. Confirm the Pages approach (GitHub Pages or Cloudflare Pages) and the DNS records for conformome.org.
