# Conformome: add nucleic acids (RNA and DNA). Build brief for a coding agent

You are working in the `matth55/conformome` repository. Extend Conformome from proteins to **molecules**, so that RNA and DNA get the same treatment as proteins:
- evidence from many techniques;
- curated states marked observed or inferred;
- mapping records;
- conflicts;
- a coverage grid.

The nucleic acids will be part of the release described in the ORE article. Finish this brief **before** freezing the paper release in `paper/BRIEF.md` §1. The paper's numbers are then regenerated from the rebuilt release.

Work on a branch (`feature/nucleic-acids`) and open a PR when §10 passes. Read the whole brief first.

## 1. Invariants

1. **Proteins must not change.** After the change, every existing protein page, download and number must be identical except for the fields this brief renames. Add a regression test (§9) that rebuilds the protein part of the release and diffs it against the current release.
2. **URLs must not break.** `/protein/<UniProt>/` keeps working. It becomes the canonical URL for proteins, or a redirect to the new canonical URL; either is acceptable, but no existing link may 404.
3. **Same rules for nucleic acids.**
   - Observed states cite a representative PDB entry.
   - Inferred states list their assumptions.
   - Conflicts are flagged, never averaged.
   - Every mapping records who made it, the rule used, the confidence and the reason.
4. **No fabricated curation.** You write the code, the schemas and **draft** curation files that a curator will review. Draft curation files must carry `status: draft` and `curator: null`, and the site must show "draft, not yet reviewed" for them. The author fills in the curator field after review.
5. **Licences.** Record each new source's licence in `provenance.licence`. If a licence does not permit redistribution, or you cannot determine it, the evidence is shown and linked but kept out of the downloads, as for SMASH-BIO.

## 2. Data model changes (schema 2.0.0)

### 2.1 `protein` becomes `molecule`

```json
{
  "record_type": "molecule",
  "molecule_id": "uniprot:P37840 | rnacentral:URS0000... | seq:dna:3f9a1c2e",
  "molecule_type": "protein | rna | dna | complex",
  "name": "Adenine riboswitch aptamer (Vibrio vulnificus add)",
  "organism": {"taxon_id": 672, "name": "Vibrio vulnificus"},
  "reference_sequence": "...",
  "reference_sequence_source": "UniProt | RNAcentral | curated",
  "xrefs": {"uniprot": null, "rnacentral": "URS...", "rfam": "RF00167", "pdb_entities": ["4TZX_1"]},
  "aliases": ["add riboswitch"]
}
```

**Identifier rules, in order:**
1. Proteins: `uniprot:<accession>`, unchanged in substance.
2. Natural RNAs with an RNAcentral entry: `rnacentral:<URS id>`. Use the species-specific ID (`URS..._<taxid>`) where one exists.
3. Everything else, including synthetic DNA oligonucleotides such as the telomeric G-quadruplex sequence and engineered constructs: `seq:<rna|dna>:<first 8 hex characters of SHA-256 of the uppercase reference sequence>`. Store the full sequence. Add a collision test.

`complex` is reserved and not used in this release. Do not build it.

**Back-compatibility:**
- `record_type: "protein"` stays readable.
- The build writes `molecule` records, plus a `protein` alias field in the JSON Lines output for one release, documented as deprecated.
- Bump all schema versions and write a `CHANGELOG.md` entry.

### 2.2 Conditions: add ions

Nucleic-acid conformations depend strongly on cation identity and concentration. The clearest case is the telomeric G-quadruplex, whose fold topology differs between K⁺ and Na⁺. Add to `conditions`:

```json
"ions": {"Mg2+": {"value": 10, "unit": "mM"}, "K+": {"value": 100, "unit": "mM"}, "Na+": null, "Li+": null},
"ionic_strength": {"value": null, "unit": "mM"},
"denaturant": {"name": null, "value": null, "unit": null}
```

Unknown values stay `null`, as elsewhere. Convert all concentrations to mM.

**Conflict comparability** (`map/conflicts.py`) gains three requirements. Two items are comparable only if:
- they have the same set of non-null monovalent cation species;
- their [Mg²⁺] values are both null, or both within a factor of 2;
- their denaturant is the same.

Apply these to proteins as well. Report how many protein conflicts this removes; the number should be small or zero, and the PR description must give it.

### 2.3 State: secondary structure

Nucleic-acid states are often defined by base pairing rather than by coordinates. Add these optional fields to `state`:

```json
"secondary_structure": {"dot_bracket": "((((....))))..", "numbering": "reference_sequence", "source": "curated | PDB-derived | probing-derived"},
"topology": "parallel | antiparallel | hybrid-1 | hybrid-2 | basket | null"
```

`topology` is a controlled vocabulary for G-quadruplexes only. Validate it in the schema with `if molecule_type in [rna, dna]`.

**Observed and inferred:**
- A nucleic-acid state is **observed** only if a PDB structure (X-ray, cryo-EM or NMR) resolves it.
- Secondary structure derived from chemical probing (SHAPE or DMS), with or without folding software, is **inferred**. Its assumptions must name the folding model and the restraints used.
- CD topology signatures and force-spectroscopy states are **inferred**.

### 2.4 Construct and residue coverage

Nucleic-acid constructs often add flanking sequences, handles (for force spectroscopy), linkers or fluorophores. Add to each evidence item:

```json
"construct": {"sequence": "...", "aligned_to_reference": {"start": 13, "end": 83, "identity": 1.0},
              "modifications": ["Cy3-5'", "biotin-3'"], "handles": "dsDNA 1.5 kb"}
```

Compute `aligned_to_reference` with a global–local alignment against `reference_sequence` (Biopython `PairwiseAligner`, `mode="local"`).

Mapping rules can then require `min_coverage` of a state's defining region; add that criterion to the rule engine. Evidence covering less than the state-defining region is shown on the page, marked "partial construct".

## 3. Techniques (`techniques.yaml`)

Add these entries, or enable them if the taxonomy already has them, with the existing `resolves_directly` flag:

| id | label | resolves directly | typical observable |
| --- | --- | --- | --- |
| `shape` | SHAPE chemical probing (incl. SHAPE-MaP) | no | per-nucleotide reactivity profile |
| `dms` | DMS probing (incl. DMS-MaPseq) | no | per-nucleotide reactivity profile |
| `chem_probing_other` | other chemical / enzymatic probing (hydroxyl radical, in-line, nuclease) | no | reactivity profile |
| `crosslink_seq` | crosslinking–ligation sequencing (PARIS, SPLASH, COMRADES) | no | base-pair contacts |
| `smfret` | single-molecule FRET | no | FRET efficiency populations, rates |
| `uv_melting` | UV / thermal melting | no | Tm, ΔH, ΔG |
| `cd` | circular dichroism (exists) | no | G4 topology signature (264 / 295 nm) |

Force spectroscopy, NMR, X-ray, cryo-EM, SAXS, MD and integrative models already exist. They apply unchanged.

**Coverage-grid rule.** Reactivity profiles are per-nucleotide vectors, not scalars. Store them in a sidecar file referenced from the evidence record (`data_ref`). Do not compare them in the scalar conflict detector. Instead, compute an optional agreement score between a profile and a state's dot-bracket: the AUC of reactivity for unpaired versus paired nucleotides. Store the score on the mapping record as `support_metric`. It is shown on the page and **not** used to make mappings automatically in this release.

## 4. Sources

Write new source modules following the existing pattern: query by `molecule_id` or its xrefs, keep source identifiers and licences, write evidence. For each source, find and record the licence on its own terms page, and add the terms URL to the PR description.

| Source | What to ingest | Key |
| --- | --- | --- |
| **RCSB PDB** (extend) | Nucleic-acid polymer entities; protein–NA complexes add evidence to both molecules | sequence match to `reference_sequence`; RNAcentral xref where available |
| **BMRB** (extend) | NA chemical shifts and relaxation | entity sequence match |
| **SASBDB** (extend) | NA Rg | entity sequence match |
| **RMDB**, the RNA Mapping Database (new) | SHAPE, DMS and other probing datasets, with conditions | sequence match; keep the RMDB entry ID |
| **RNAcentral** (new, identity only) | molecule records, Rfam family, PDB xrefs; no evidence | URS ID |
| **SMASH-BIO** (extend) | force-spectroscopy studies of NA hairpins, riboswitches, G-quadruplexes, pseudoknots | SMASH-BIO entity annotations → `molecule_id` |
| **MDDB** (extend) | NA simulations | sequence / PDB match |

Write stubs, without ingesting, for NAKB/NDB, the RNA 3D Hub representative sets and RASP. Document what each would add.

## 5. Pilot nucleic acids

Add these six molecules, with **draft** curation files (`curation/<molecule_id>.yaml`, `status: draft`). States are given as starting points for the curator; check every representative PDB ID against the PDB before writing it into the file.

| Molecule | Type | Draft states (curator to confirm) | Why it is in the pilot |
| --- | --- | --- | --- |
| Adenine riboswitch aptamer (*V. vulnificus add*) | RNA | ligand-free; adenine-bound; partially folded intermediates seen by force spectroscopy | Classic multi-technique system: X-ray, NMR, smFRET, optical tweezers |
| preQ1 class-I riboswitch (*B. subtilis*) | RNA | unfolded/hairpin; preQ1-bound H-type pseudoknot | Small, well characterised by NMR, X-ray and force spectroscopy |
| HIV-1 TAR | RNA | ground state; excited states from NMR relaxation dispersion | The standard example of NMR-detected excited states in RNA |
| *Tetrahymena* group I intron P4–P6 domain | RNA | Mg²⁺-folded tertiary structure; unfolded/secondary-only | Mg²⁺-dependent folding; X-ray, SAXS, SHAPE, smFRET |
| SARS-CoV-2 frameshifting element (FSE) | RNA | three-stem pseudoknot; alternative conformations from probing and cryo-EM | Recent, contested multi-state system; good conflict test |
| Human telomeric G-quadruplex (d[AG₃(T₂AG₃)₃] and variants) | DNA | K⁺ hybrid forms; Na⁺ antiparallel basket; crystal parallel form | Topology depends on cation and method: tests the ions conditions and observed/inferred rules |

Draft rules may use technique, source, ions, ligand presence and title keywords, as for proteins. The G-quadruplex curation must separate states by cation. Add a test confirming that K⁺ and Na⁺ items are never compared for conflicts.

## 6. Site

- Rename "Proteins" to **"Molecules"** in the navigation. Add a type filter (protein / RNA / DNA) and a type badge to each row of the coverage matrix.
- On a molecule page:
  - show the type, identifiers (RNAcentral, Rfam, PDB entities) and reference sequence;
  - for nucleic-acid states, render the dot-bracket aligned to the sequence. Plain monospace text is enough; do not add a heavy dependency.
  - show the G-quadruplex topology badge;
  - show ion conditions in the evidence table;
  - mark "partial construct" items.
- Mol* already renders nucleic acids. Make sure the cartoon representation is chosen for NA entities.
- Home page totals are split by molecule type.

## 7. Downloads

- `all-records.jsonl` includes molecule records of every type.
- Per-molecule bundles are written to `molecules/<molecule_id>.json`, with `proteins/<acc>.json` kept as a copy for one release.
- Reactivity-profile sidecars are written to `profiles/<evidence_id>.json`.
- The schemas are updated, and the manifest lists the new sources.

## 8. Statistics for the paper

Extend `paper/scripts/stats.py` (see `paper/BRIEF.md` §2) with:

```
release.n_molecules, release.n_proteins, release.n_rna, release.n_dna
release.n_evidence_protein, release.n_evidence_na
release.n_curated_na, release.n_states_na
sources.rmdb.n_molecules, sources.rmdb.n_evidence
na.<slug>.n_evidence, .n_techniques, .n_states, .n_conflicts     # one per pilot nucleic acid
g4.states.<slug>.n_evidence, .ions                               # for the use case
conflicts.removed_by_ion_rule.protein                            # §2.2
```

Keep the existing protein keys unchanged, so that the current manuscript tags still resolve.

## 9. Tests

- **Protein regression.** Rebuild the protein subset and diff it against the pre-change release (records, bundles, counts). The only differences allowed are the renamed fields and the ion-rule conflict changes, and each conflict change must be listed.
- **Identifiers.** Each of the three molecule-ID schemes round-trips, the sequence-hash IDs have no collisions across the release, and the RNAcentral IDs resolve in the cached identity data.
- **Schema rules.** An NA state with a dot-bracket of the wrong length fails validation. An NA inferred state without assumptions fails the build. `topology` is rejected on RNA molecules unless it is a G-quadruplex.
- **Conflicts.** Items differing in cation species, or in [Mg²⁺] by more than a factor of 2, are never compared.
- **Alignment.** A construct with handles and a fluorophore aligns to the right reference interval.
- **Reactivity AUC.** The score is computed correctly on a synthetic profile with known pairing.

## 10. Done when

- [ ] Schema 2.0.0 is in place with a changelog, and old `protein` records are still readable.
- [ ] RMDB and RNAcentral modules are ingesting; the PDB, BMRB, SASBDB, SMASH-BIO and MDDB modules are extended to nucleic acids; licences are recorded.
- [ ] All six pilot nucleic acids have evidence, draft curation and pages that build; the G-quadruplex states are separated by cation.
- [ ] The protein regression test passes, with every difference listed in the PR.
- [ ] Old `/protein/<acc>/` URLs all resolve.
- [ ] `stats.py` emits the §8 keys.
- [ ] The PR description lists:
  - the per-source counts;
  - the representative PDB IDs used, each checked;
  - the source licences with their terms URLs;
  - the conflict changes caused by the ion rule;
  - what the curator must review (every draft NA curation file).
