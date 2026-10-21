# Conformome pipeline: code review

Repository reviewed: `/home/claude/matth55/conformome`. Nothing in it was modified. Running the test command creates `__pycache__/` directories, which are git-ignored; I removed them afterwards and `git status` is clean.
Scratch copy and probe scripts: `/tmp/claude-0/-home-claude/1e29f653-5f52-532e-91a7-fc92a0defd88/scratchpad/review-copy`, `/tmp/claude-0/-home-claude/1e29f653-5f52-532e-91a7-fc92a0defd88/scratchpad/scripts/probe.py`, `/tmp/claude-0/-home-claude/1e29f653-5f52-532e-91a7-fc92a0defd88/scratchpad/scripts/probe2.py`.

Test suite: **81 passed** (HANDOFF says 51, PILOT_REPORT says 49).

Every behaviour marked "probe" below was confirmed by running the code in the scratch copy. Issues are ranked by how much they would matter to a scientific reader or reviewer of the paper.

---

## S1. Conflict test is a 1-sigma test: about a third of agreeing pairs are flagged
`conformome/mapping/conflicts.py:56-57`

```python
combined = math.sqrt(ua ** 2 + ub ** 2)
if abs(va - vb) > combined:
```

- Combined uncertainty is computed **in quadrature**, which is correct for independent errors. The threshold, though, is **k = 1**. For two measurements of the same true value with Gaussian errors, P(|Δ| > σ_comb) ≈ 0.317. Probe: 31.6 % of 100,000 simulated agreeing pairs were flagged.
- All n(n-1)/2 pairs in a group are tested with no multiplicity control. A state with 10 consistent SASBDB entries is expected to show about 14 "conflicts".
- METHODS.md says only "differ by more than the combined uncertainty"; neither k nor quadrature is stated.
- PILOT_REPORT.md:99 calls the 18 hen-lysozyme flags "real flags". At k = 1 that cannot be told apart from chance. They also come from the same sample over different q-ranges, so the errors are not independent, and some may compare Guinier with P(r) Rg (S6).
- **Fix:** use k = 2 (≈95 %) or k = 3, make k a named constant, and record it in each conflict record and in METHODS. Report a z-score (`|Δ|/σ_comb`) per conflict. Consider a per-state chi-square or Birge-ratio consistency test instead of all pairs. Re-run the pilot numbers.

## S2. The comparability test does not do what METHODS says
`conformome/mapping/conflicts.py:20-35`

METHODS says "temperature within 5 °C, pH within 0.5". The code instead **rounds each value into a bin** (`round(temp/5)*5`, `round(ph*2)/2`):

- Probe: 22 °C and 23 °C (1 °C apart) are *not* compared, while 17.6 °C and 22.4 °C (4.8 °C apart) are.
- pH 7.24 and 7.26 fall into different bins (7.0 and 7.5). Python's banker's rounding makes edge cases uneven: 12.5 °C goes to 10, 17.5 °C to 20, pH 7.25 to 7.0, pH 7.75 to 8.0.
- **Null equals null:** `None == None`, so two items with no temperature and no pH are treated as having comparable conditions (probe: conflict flagged). Most SASBDB items have no pH or temperature, and PDB-derived items lack them often. METHODS never says that unknown matches unknown.
- **Ions and salt are not used.** `salt_mM` and `ions` (`ions` is now required in the conditions schema) are not in the signature. Only the free-text `buffer` string is (line 32). Probe: 10 mM vs 150 mM NaCl, and 0 vs 10 mM Mg²⁺, are compared and flagged.
  - Consequence: the fix proposed in HANDOFF ("Recover salt and mutations from SASBDB entry descriptions") **would not remove** the alpha-synuclein false conflicts unless `salt_mM` is also added to the signature.
  - For RNA, Mg²⁺ is the variable that matters most for state.
- **Constructs:** only `construct.description` is used (line 46), not `construct.labels`. Two smFRET or DEER items with different label positions but the same description are compared (probe: flagged).
  - SASBDB descriptions are the molecule `long_name` and carry no mutations. This produces the known alpha-synuclein K→R artefact.
  - Oligomeric state is not captured either (S6).
- Ligand tuples are compared case-sensitively here (`'ade' != 'ADE'`), while rules upper-case ligand IDs (`rules.py:105`).
- The code adds two criteria METHODS does not list: `buffer` and construct (they are mentioned only in the module docstring).
- **Fix:** compare pairwise with `|ΔT| ≤ 5` and `|ΔpH| ≤ 0.5` instead of binning. Treat null as "not comparable" (or make it an explicit, documented option and count those pairs). Add `salt_mM` (with a tolerance), the ion set and concentrations, `labels` and an oligomeric-state field. Normalise ligand case. Update METHODS to list exactly the criteria used.

## S3. Predictions count as independent techniques, so the "one method" flag is suppressed
`conformome/pipeline.py:174-194` (line 191); curation rules such as `curation/P00648.yaml` `barnase-md-native` and `barnase-af-native` (the same pattern is in P00974, P01053, P42212, Q13526 and others)

- The rules map AlphaFold DB (`af_prediction`) and MDDB (`md`) items onto native states. `coverage_grid` counts every technique with a non-zero cell, prediction or not. Probe: a state with xray + af_prediction + md is not in `single_method_states`.
  - The grid's purpose, per METHODS, is to show "a state that rests on a single technique". An X-ray-only native state plus its AlphaFold model now looks like three methods.
- `nmr_shifts` and `nmr_dynamics` are separate techniques, so two BMRB deposits from the same lab count as two methods (probe). The same applies to `xray`/`xray_time_resolved` and `cryoem`/`cryoem_heterogeneity`.
- A state with **zero** mapped evidence is not flagged at all (`sum(...) == 1`). HANDOFF lists five such inferred states, and their rows look healthier than a one-method row.
- Predictions also enter conflict detection: `find_conflicts` has no prediction filter. Probe: MD `population` vs smFRET `population` was flagged as a conflict.
- **Fix:** exclude `prediction: true` techniques (`taxonomy/techniques.yaml`) from the method count, and show them in a separate column group. Count methods by technique family (for example nmr_* = NMR, xray* = X-ray), or document the choice. Flag zero-evidence states as "no evidence". Exclude predictions from conflicts, or label prediction-vs-experiment conflicts separately.

## S4. Observed/inferred rules are only half enforced
- Enforced:
  - "Inferred must list assumptions" is enforced through the schema `if/then` (`schema/state.schema.json`, end of file), which `pipeline.map_protein` checks (`pipeline.py:246-248`) and `validate.py:139` re-checks. Covered by `tests/test_schema.py:72`.
  - The models step requires that only observed states export a representative, and that the representative is mapped to its state (`pipeline.py:284-290`).
- Not enforced anywhere (`curation.py`, `pipeline.py`, `validate.py`, schema):
  - An **observed state must cite a representative PDB.** `representative_pdb: null` on an observed state passes. Today's curation files happen to comply; I checked all 31.
  - The representative entry's technique must have `basis: observed`. A PDB-IHM (`integrative`) or PDB SAXS (`saxs_sans`) entry could be the representative and would be exported with the header "assumptions: none (observed)" (`pipeline.py:330-339`).
  - An observed state may rest only on inferred-technique evidence.
  - Assumptions that are only whitespace pass (`minLength: 1`).
- DisProt maps ECO "electron microscopy" (including negative stain) to `cryoem`, which has `basis: observed` (see S7).
- **Fix:** in `validate.build_errors` (and ideally in `load_curation`):
  - basis observed → `representative_pdb` required;
  - the representative's evidence technique must have `taxonomy[t].basis == "observed"`;
  - at least one mapped evidence item with an observed technique;
  - strip and check assumptions.
  Add tests for each.

## S5. Mapping: one item can map to two states, and text matching has real false positives
- **Two states from curators:** `pipeline.py:207-217` appends every curator assignment. Assigning one item to two states, for example by `evidence_id` and by `pdb:`, keeps both mappings. Probe: mappings `['S1','S2']`, no error. `validate.py:150` rejects only duplicates of the *same* state.
  - PILOT_REPORT §7 says fractional or multi-state mapping is not represented, yet the code allows it silently. The item is counted in both coverage cells and in both conflict groups.
  - Rules cannot do this: ambiguity there is handled correctly (`rules.py:149-160`). Curator precedence is also correct (`rules.py:150`, tested in `tests/test_rules.py:161`).
- **Substring matching** (`rules.py:125-131`) uses `w in text`. Real instances in the curation:
  - `curation/P37840.yaml` rule `as-nmr-monomer`: `title_none: ["bound", ...]` rejects every title containing "unbound". The free-monomer NMR entries most likely to say "unbound" are excluded (probe confirmed).
  - `curation/P0A334.yaml` rule `kcsa-open-title`: `title_any: ["open"]` has **no technique restriction**. It matches "reopening" and titles like "closed and open states", and it applies to BMRB, SASBDB, MDDB and SMASH-BIO items. A simulation titled "open" would be mapped to the *observed* state KcsA-open-inactivated.
  - `curation/Q8WZ42.yaml`: `"I27"` matches "I275T" (probe).
  - "apo" matches "apolipoprotein" and "active" matches "inactive" (probe). `P07550.yaml` guards against the latter by hand with `title_none: ["inactive"]`.
- **Criteria match more than their names say:** `title_*` criteria match title **plus construct text** (`rules.py:108-109`), but METHODS says "words in the title". `Q9Y490.yaml` `talin` rule `title_any: ["unfolding_protein"]` actually matches SMASH-BIO construct metadata ("experiment class: …"). This is documented only in curation/README.md.
- **Ligands are entry-level** (`pdb.py:188-192`), so a ligand bound to a partner entity counts. For example, `P01112.yaml` GDP rule `ligands_any: [GDP], ligands_none: [GNP,GCP,GSP,GTP]` will map Ras·GDP·AlF₃–RasGAP transition-state complexes to the GDP state.
- **Confidence depends on rule order:** when several rules for the same state match, the mapping takes `hits[0]` (`rules.py:158`). The confidence and justification shown are the first rule's, not the highest-confidence one's.
- **Fix:**
  - Reject (or require explicit acceptance of) any item mapped to more than one state.
  - Match on word boundaries (`re.search(rf"\b{re.escape(w)}\b", text, re.I)`), with an explicit `*_substring` option.
  - Rename or split the criteria into `title_*` and `text_*`.
  - Require `techniques`/`sources` on title rules for observed states.
  - Record every matching rule, and use the maximum confidence or state the policy.

## S6. SASBDB parsing feeds every conflict currently flagged
`conformome/sources/sasbdb.py`

The only conflicts the pipeline can produce today are SASBDB Rg pairs: no other source emits a type in `COMPARABLE_TYPES` (S9). So these parser limits directly drive the paper's conflict numbers:

- `_rg_nm` (lines 184-190) falls back from Guinier Rg to P(r) Rg under the same observable type. Different estimators, which can differ systematically, are compared as if they were the same quantity.
- Units:
  - Rg is assumed to be in nm "whatever the angular unit". This was checked on calmodulin only, and there is no plausibility guard (for example, Rg > 30 is probably Å).
  - `cell_temperature` is assumed to be °C with no check.
- Construct and sample:
  - Oligomeric state and copy number are not parsed. `mine` is a de-duplicated set of names (line 204), so a homodimer sample looks the same as a monomer, and "Rg is of the whole sample".
  - Mutations and salt are not parsed: this is the documented alpha-synuclein artefact.
- Search and filtering:
  - Codes are scraped by regex from the first search-results page only (line 165). Paginated or truncated results are lost silently.
  - Matching requires `uniprot_code == accession` exactly. Isoform-coded samples land in `not_ingested` with a misleading reason ("no molecule with this UniProt code").
- **Fix:**
  - Record the estimator (`guinier` vs `pddf`) in the observable or the signature.
  - Parse the oligomeric state, the number of molecules and the buffer salt.
  - Add a unit sanity range.
  - Follow pagination.
  - Compare only Guinier with Guinier.

## S7. Temperatures and technique assignment can be wrong by hundreds of degrees or by basis
- `pdb.py:137-147`:
  - The X-ray "temperature" is `diffrn.ambient_temp`, the **data-collection** temperature (100 K → −173.15 °C, probe). pH comes from `exptl_crystal_grow` (crystallisation). The two describe different stages.
  - `exptl_crystal_grow.temp` is queried (line 61) but never used.
  - NMR `pdbx_nmr_exptl_sample_conditions.temperature` is assumed to be in K with no unit or range check. Legacy entries that give °C ("25") become −248.15 °C (probe). `temperature_units` is not queried.
- `bmrb.py:69-71`: when `Val_units` is missing or unrecognised, the value is taken as °C, so 298 with no unit gives **298 °C** (probe). The fixture test (`tests/test_sources.py`, the range assertion −20 < T < 100) would catch this only on its fixture.
- `disprot.py:251-279`, ECO mapping by first substring:
  - "single-molecule **force** spectroscopy" → `smfret`;
  - "NMR … relaxation" → `nmr_shifts`;
  - CW EPR → `epr_deer`;
  - negative-stain EM → `cryoem`, an **observed** technique;
  - FCS → `fluorescence`.
  (all probed)
- **Fix:**
  - Use the crystal-grow temperature for the sample condition, or store both with labels.
  - Query `temperature_units`.
  - Reject temperatures outside a plausible range, for example −50 to 150 °C, and treat values below 0 as Kelvin errors for NMR.
  - Map ECO by ID, not by name substring, and add tests for each.

## S8. Isoforms: wrong pages and residue numbering
- `disprot.py:286`: `split("-")[0] == accession`. For an isoform page (`P10636-8`, which the schema allows), the filter never matches, so the page gets **zero** DisProt entries (probe: 0 of 2).
- On the canonical P10636 page, regions from P10636-2 *and* P10636-8 (fixture `tests/fixtures/sources/disprot_P10636.json`) sit next to the canonical 758-aa UniProt sequence, each in its own numbering. The construct text names the isoform, but nothing else signals the difference.
- PDB, BMRB, SASBDB and AlphaFold all match the exact accession, so an isoform page has no structures, and since PDB is PRIMARY the page cannot be built usefully.
- Docs contradict each other: METHODS.md:92 says "Only the canonical isoform of each protein is recorded"; HANDOFF and SOURCES say isoform-annotated DisProt entries are kept.
- **Fix:** compare the full `acc` for isoform pages and the base accession for canonical pages, and keep only exact-isoform entries unless numbering is mapped. Add a residue-numbering offset or an isoform field to the evidence. Make the docs agree.

## S9. Not-compared count and observable coverage are misleading
- `conflicts.py:71-76` `not_compared`:
  - It counts all evidence, including unmapped items (which can never be compared).
  - It **excludes** comparable items with no partner in their condition group, which were never compared either. Probe: an unmapped item with an uncertainty counted as "compared". The comment in `tests/test_mapping.py:76` describes exactly this gap.
  - The page shows the count **only when there are zero conflicts** (`site/build.py:441-450`), so pages with conflicts never say how much was left uncompared.
- `COMPARABLE_TYPES` (`conflicts.py:16-17`):
  - It contains `rate`, which is not an observable of any technique in `taxonomy/techniques.yaml`.
  - It omits `transition_rate`, `folding_rate`, `free_energy_difference`, `melting_temperature` and `hydrodynamic_radius`.
  - In practice only SASBDB `radius_of_gyration` is ever compared. The paper should say so.
- Uncertainty:
  - An uncertainty of 0 or a negative value is accepted (probe: 2.0 vs 2.0001 with σ = 0 is a conflict).
  - A NaN uncertainty silently yields "no conflict" and counts as compared.
  - `base.number("NaN")` returns `nan`, and `write_json` emits the invalid JSON token `NaN`.
- An item mapped twice to the same state produces duplicate conflict IDs. `validate.py:150` catches the double mapping, so this is minor.
- **Fix:** count per state: mapped items not compared, with the reason (no uncertainty, no value, type not comparable, no partner under comparable conditions). Always show the count. Treat uncertainty ≤ 0 or non-finite as missing. Reject NaN and inf in `number()`. Align `COMPARABLE_TYPES` with the taxonomy and add a test that every listed type exists.

## S10. Licence enforcement fails open and misses files
- `site/build.py:721` `redistributable.get(source, True)`: any provenance `source` string that is not exactly a module `NAME` is **redistributed**. `validate.py:186-187` builds `forbidden` the same way, so the validator cannot catch it.
- `validate.downloads_redistribution_errors` (`validate.py:183-199`) checks only `evidence` records in `downloads/proteins/*.json` and `all-records.jsonl`. It does not check:
  - bundle `conflicts` (`build.py:728`), which carry `values`, `uncertainties` and `evidence_ids` of any source. This is a latent leak: no SMASH-BIO type is comparable today, but adding e.g. `folding_rate` would leak values;
  - `coverage` counts, or `states.population.evidence_ids`;
  - `search/evidence.json` (`build.py:713-718`, `905-911`), a bulk, machine-readable JSON with every SMASH-BIO record ID, publication title, construct text and mapped state. It is effectively a download.
- MDDB keeps per-project licences in provenance (`mddb.py:61`), but `redistribute` is decided per source ("yes"), so a project with a restrictive licence is redistributed.
- No test exercises `downloads_redistribution_errors` or the SMASH-BIO exclusion. The fixture has no non-redistributable source.
- **Fix:**
  - Fail closed: an unknown source means not redistributable, and the validator errors on any provenance source not in REGISTRY.
  - Filter conflicts, population evidence IDs and the search index, or decide explicitly that the search index is page content and say so in SOURCES.md.
  - Check per-record licence strings against an allow-list.
  - Add a fixture with a SMASH-BIO item and assert it is absent from every file under `downloads/`.

## S11. Reproducibility: the manifest does not capture what it claims
- Dates:
  - `common.fetch_url` returns cached bytes forever (`common.py:76-79`), but `save_raw` and `record_download` stamp `retrieved = today()` (`common.py:111`, `base.py:37-41`). A re-download weeks later from a warm `_cache` records today's date for old data, both in the manifest and in every evidence provenance record.
  - The SHA-256 is computed over the re-serialised raw JSON, which contains `retrieved`. Hashes change daily even when upstream content is unchanged, so they cannot show that two builds used the same data.
- Missing from the manifest:
  - real request URLs: placeholders `"<code>"` and `"<id>"` (`sasbdb.py:168`, `bmrb.py:35`);
  - the PDB GraphQL request bodies (`pdb.py:117`: only the endpoint);
  - per-entry SASBDB and BMRB responses;
  - the code commit, hashes of `curation/`, `taxonomy/` and `targets.yaml`, and Python and package versions. Dependencies are unpinned in `pyproject.toml`;
  - a fixed version of the SMASH-BIO release: it is fetched from the moving `main` branch (`smashbio.py:148`). The SHA is recorded, but the file cannot be re-fetched.
- The committed `data/MANIFEST.json` has 757 entries, all dated 2026-10-19. It has **no entries for NAKB, RNAcentral, Rfam or DNA**, so the two nucleic-acid pages are not covered. It is also never pruned. CI regenerates its own manifest, so the committed file is not the one behind the live site.
- Ordering: output order follows API order for DisProt, MDDB, AlphaFold DB and SMASH-BIO (not sorted). `mapped.json`, `all-records.jsonl` and the ambiguous list can reorder between runs. Keys are sorted (`write_json` uses `sort_keys`) and conflicts are sorted, which is good.
- **Fix:**
  - Store the fetch time with each cache entry and propagate it.
  - Hash the raw response bytes, not the re-serialised JSON.
  - Record the real URLs and request bodies.
  - Write a build record (git SHA, input-file hashes, `pip freeze`) into the manifest.
  - Pin the SMASH-BIO release to a tag or commit.
  - Sort evidence by `evidence_id` after ingest.

## S12. Identity edge cases (lower severity)
- `molecule.py:156-164` `molecule_type` returns "protein" for any unrecognised string, including lowercase `urs…`. Validate the ID against the schema patterns first.
- The schema allows `URS…` without a taxon (`common.schema.json`, `molecule_id`), but `rnacentral.split` raises on it (`rnacentral.py:24-25`). Tighten the schema for RNA pages.
- DNA IDs:
  - `dna.py:27-30` hashes only the *first* DNA entity in NAKB's order. Two duplexes that share strand 1 collide, and a change in entity order changes the ID.
  - `sequence_canonical` drops base modifications.
  - Consider hashing the sorted set of strands plus modifications.
- The RNAcentral keys `URS[0-9A-F]{10}_<taxid>` and the Rfam/NAKB taxon comparison (int to int) are correct.

---

## Documentation mismatches
| Claim | Where | Code / fact |
|---|---|---|
| "temperature within 5 °C, pH within 0.5" | METHODS "Conflicts" | 5 °C and 0.5-pH bins; nulls match each other; buffer and construct also required; salt and ions not used (S2) |
| "combined uncertainty" | METHODS | quadrature at k = 1 is not stated (S1) |
| "words in the title" | METHODS "Mapping" | title *plus construct text* (`rules.py:108`) |
| "Only the canonical isoform … is recorded" | METHODS:92 | DisProt keeps isoform entries (HANDOFF, SOURCES, `disprot.py:285`) |
| "Ions: conditions list ions … next to the total salt" | METHODS | populated only by NAKB (without concentrations); not used in comparisons |
| "The page says how many items could not be compared" | METHODS | shown only when there are 0 conflicts; the count excludes no-partner items (S9) |
| "51 passing" / "49 tests" | HANDOFF:19 / PILOT_REPORT:3 | 81 pass |
| "17,522 from 7 sources" | HANDOFF:18, README:7 | 9 implemented evidence sources (NAKB and Rfam added); `targets.yaml` has 83 molecules, 31 curation files |
| "33 of the 52 flagged conflicts … K-to-R mutants" | HANDOFF:88 | PILOT_REPORT:100 says 33 alpha-syn **+ 1 tau** are artefacts |
| Lysozyme flags are "real flags" | PILOT_REPORT:99 | not distinguishable from chance at k = 1 (S1) |
| "Recover salt … from SASBDB" as the fix for false conflicts | HANDOFF "next steps" | `salt_mM` is not in `condition_signature`, so this would not help (S2) |
| `data/MANIFEST.json` "records every raw file" | HANDOFF, METHODS | no NAKB, RNAcentral, Rfam or DNA entries; dates and hashes are not reliable (S11) |
| `COMPARABLE_TYPES` includes `rate` | `conflicts.py:16` | not an observable of any technique |

## Test coverage gaps
1. Conflict thresholds:
   - boundary tests for |ΔT| = 4.9 vs 5.1 and ΔpH = 0.49 vs 0.51 (would expose the binning);
   - null vs null and null vs value;
   - salt and ions;
   - labels;
   - k and quadrature (`tests/test_mapping.py` checks only one clear-cut pair);
   - zero, negative and NaN uncertainty;
   - predictions excluded.
2. `not_compared` semantics. The existing test comment at `tests/test_mapping.py:76` describes the gap and asserts it as correct.
3. Curator assigning one item to two states; rule-order confidence; word-boundary matching (unbound/bound, apo/apolipoprotein, active/inactive).
4. Coverage grid: predictions, technique families, zero-evidence states.
5. Observed state without a representative; representative with an inferred technique; observed state with only inferred evidence.
6. Licence: no test for `downloads_redistribution_errors`, the fail-open default, conflicts in bundles, or `search/evidence.json`.
7. Units: PDB NMR temperature given in °C; BMRB missing units; SASBDB Guinier vs P(r) fallback; Rg plausibility.
8. DisProt isoform page (`P10636-8`); ECO mapping for force spectroscopy, relaxation and negative stain.
9. Determinism: run ingest and map twice with shuffled source order and assert byte-identical `mapped.json`. Manifest: dates and hashes for cache hits.
10. `molecule_type` on invalid IDs; DNA ID with duplex strand order.
