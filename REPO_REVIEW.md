# Conformome repository review: suggested changes

Repository `matth55/conformome`, commit `863b5ef` (19 Oct 2026), branch `ccr-ebb336f7-3qzi9h`. All 81 tests pass. The full code review, with a failure scenario and a fix for each issue, is in `CODE_REVIEW_DETAIL.md` (S1–S12).

**Summary.** The pipeline is well structured. It has provenance, a validator, licence rules and honest "draft" labelling. But several defects change numbers or claims that the ORE manuscript states, and some of them are exactly what reviewers would test first. The repo is also further along than the manuscript and my briefs assumed: RNA, DNA, the molecule schema, ions and nucleic-acid techniques already exist. So the nucleic-acid brief and the manuscript need correcting (§6).

---

## 1. Fix before freezing the paper release (these change the paper's numbers or claims)

| # | Problem | Where | Effect on the paper | Change |
|---|---|---|---|---|
| 1 | **Conflict test is 1σ.** Values are flagged when they differ by more than the combined (quadrature) uncertainty. About 32% of truly consistent pairs get flagged, with no correction for multiple comparisons. | `mapping/conflicts.py:56-57` | All 52 conflicts, including the α-synuclein "33", mean little | Use a 2σ, preferably 3σ, threshold set in one constant; store z = Δ/σ on each conflict; report the threshold in METHODS and the paper |
| 2 | **The 33 α-synuclein conflicts are known artefacts.** PILOT_REPORT and HANDOFF both say they compare K→R mutants at different NaCl concentrations. | SASBDB data, `sources/sasbdb.py` | The manuscript presents them as real conflicts in the use case | Parse mutations, salt and oligomeric state from SASBDB descriptions, or dismiss these conflicts by curation. In either case, rewrite the α-synuclein paragraph |
| 3 | **Comparability doesn't match METHODS.** Temperature and pH are rounded into bins: 22 °C vs 23 °C is not compared, but 17.6 °C vs 22.4 °C is. A missing temperature or pH counts as equal to another missing value. Ions and salt are ignored; only the free-text buffer is used. Ligand names are compared case-sensitively. | `conflicts.py:20-35` | The stated "within 5 °C, pH within 0.5" rule is not what runs | Compare pairwise against tolerances. Treat missing values as not comparable. Use `conditions.ions`, which is already required. Normalise ligands. Add boundary tests |
| 4 | **Temperatures are wrong.** For X-ray, the data-collection temperature is used (100 K becomes −173 °C) alongside the crystallisation pH. NMR temperatures are always treated as kelvin, so 25 becomes −248 °C. A BMRB value with no unit is taken as °C, so 298 becomes 298 °C. | `sources/pdb.py:61,137-147`, `sources/bmrb.py:71` | Displayed conditions are wrong, and conflict comparability is distorted | Use the crystal-growth temperature for crystals and record the collection temperature separately. Sanity-check unit ranges (a value above 200 is kelvin) |
| 5 | **Predictions count as techniques in the coverage grid.** AlphaFold and MD hide the "one method" flag. NMR shifts and NMR dynamics count as two methods. Empty states are never flagged. | `pipeline.py:191` | The "30 of 68 single-method states" figure is undercounted | Leave predictions out of the method count (show them separately). Group by method family (NMR, X-ray and so on) for the flag. Mark empty states "no evidence" |
| 6 | **Observed states aren't checked.** An observed state needn't cite a representative PDB, and nothing checks that the representative was solved by an observed technique. An integrative or SAXS entry would be exported as "observed, no assumptions". | `pipeline.py:246, 330-339`, schema | The paper claims "an observed state must cite a representative PDB entry" | Enforce both rules in the state schema and the validator |
| 7 | **Rule text matching uses substrings.** In P37840, `title_none: ["bound"]` also rejects "unbound". The KcsA `title_any: ["open"]` rule has no technique filter, so it maps BMRB, MDDB and SMASH-BIO items. "I27" matches "I275". "Title" criteria also search the construct text. | `mapping/rules.py`; `curation/P37840.yaml:62`, `P0A334.yaml`, `Q8WZ42.yaml` | Mapping counts in the α-synuclein use case and Table 1 shift | Match on word boundaries (regex `\b`), split `title_*` from `construct_*`, and fix the three curation files |
| 8 | **One item can be assigned to two states** with no error. | `pipeline.py:207-217`, `validate.py:150` | Contradicts "never assigned silently" | Raise an error in the validator |
| 9 | **The DisProt method mapping uses name substrings.** Force spectroscopy becomes smFRET, NMR relaxation becomes `nmr_shifts`, and negative-stain EM becomes `cryoem`, an *observed* technique. | `sources/disprot.py:251-279` | Wrong technique counts, and a wrong observed basis | Map by ECO code with an explicit table, and fail on anything unmapped |

## 2. Data licensing: leaks that matter before a Zenodo release

| # | Problem | Where | Change |
|---|---|---|---|
| 10 | Licence checks *fail open*: an unknown source counts as redistributable, both in the build and in the validator | `site/build.py:721`, `validate.py:183-199` | Fail closed: only sources listed in `docs/SOURCES.md` with `redistribute: yes` are allowed |
| 11 | `search/evidence.json` publishes every SMASH-BIO record ID, title and construct; conflicts in the per-protein bundles carry values from any source | site build | Filter both, and add a test that scans *every* file in `site/dist/downloads` and `search/` |
| 12 | MDDB per-project licences are kept on each record but never enforced | `site/build.py` | Apply the record-level `provenance.licence` against an allow-list; this is the same rule the Zenodo brief uses |

## 3. Reproducibility: needed for "every number is regenerated"

| # | Problem | Change |
|---|---|---|
| 13 | Cached responses are stamped with *today's* date, in the manifest and in every evidence record, so hashes change daily although the data don't (`common.py:76-79,111`) | Store the original fetch date with the cache entry, and hash the payload without the date |
| 14 | The manifest has placeholder URLs (`<code>`, `<id>`), no query bodies, no code commit and no package versions; NAKB, RNAcentral, Rfam and DNA inputs are missing from the committed `MANIFEST.json` | Record full URLs and query bodies, the git commit and `pip freeze`, and regenerate the manifest |
| 15 | SMASH-BIO is fetched from the moving `main` branch | Pin it to the release tag or the Zenodo DOI (v1.0.0-paper) |
| 16 | Dependencies are unpinned, and evidence order follows API order | Add a lock file (`requirements.lock`); sort evidence by `evidence_id` before writing; add a test that builds twice and compares |

## 4. Smaller correctness items

- **Isoforms:** an isoform page (P10636-8) gets no DisProt entries, and the canonical tau page mixes residue numbering (S8). Either map ranges to canonical numbering or keep isoform evidence on isoform pages only. METHODS ("only the canonical isoform") contradicts HANDOFF; make them agree.
- **"Not compared" count:** it includes unmapped items and is shown only when there are zero conflicts. Zero, negative or NaN uncertainties are accepted. `rate` is in `COMPARABLE_TYPES` but not in the taxonomy (S9).
- **Rule confidence:** when several rules for one state match, the first rule's confidence wins (`rules.py:158`). Use the highest, or keep all of them.
- **Ligands are per entry, not per chain:** HRas·GDP·AlF₃ maps to the GDP state. At least add an `AlF` / `BeF` exclusion to the HRas rules.
- **IDs:** an unrecognised ID defaults to protein; the RNAcentral pattern in the schema and in the code disagree; the DNA ID hashes only the first strand, in whatever order NAKB lists them (S12).

## 5. Repository hygiene

| Item | Now | Suggest |
|---|---|---|
| Licence | No `LICENSE` file; "none chosen" in docs | Add MIT for code and CC BY 4.0 for curation and data; state both in README and `pyproject.toml` (`license = "MIT"`) |
| Default branch | `ccr-ebb336f7-3qzi9h` (no `main`) | Rename to `main` before tagging the paper release. GitHub redirects old links, and the workflows use `default_branch`, so they keep working |
| README | "per-protein", "7 sources", 81 proteins | "proteins and nucleic acids", 9 implemented sources, 83 molecules; regenerate the numbers from the build |
| HANDOFF / PILOT_REPORT | Tests 51 / 49, 7 sources, artefact conflicts 33 vs 33+1 | Generate the status tables from `build/` (a `make report` target) so they can't go stale |
| `pyproject.toml` | "Per-protein index" | "Per-molecule index of conformational-state evidence" |
| Citation | No `CITATION.cff` or `.zenodo.json` | Add them from `zenodo/repo-root/` in the kit |
| HTTPS | Not enforced | Tick *Enforce HTTPS* now; reviewers will open the site |
| Nucleic-acid pages | Live under `/protein/<id>/` | Add `/molecule/<id>/` with redirects, or rename the section "Molecules" |
| CI | Every PR downloads all sources (about 45 min with a cold cache) | Run a fast job on PRs (tests plus fixture build); keep the full download for the default branch and a weekly run |
| METHODS | Misdescribes the conflict criteria, title matching, isoforms and ions | Rewrite after fixes 1–9 so the text matches the code exactly; the paper's Methods should quote it |

## 6. Corrections to the kit I gave you

The repo already has much of the nucleic-acid work, and some conventions differ from my brief. The agent must follow the repo, not the brief.

| Topic | Repo (keep) | My brief / manuscript said (wrong) |
|---|---|---|
| DNA ID | `DNA-<12 hex of SHA-256>` | `seq:dna:<8 hex>` |
| Record type | `molecule` with `molecule_id`; schema already changed | "Introduce schema 2.0.0" |
| Ions | `conditions.ions` already **required** | "Add ions" (the remaining job is to *use* them in conflicts) |
| Technique IDs | `shape`, `dms_mapseq`, `duplex_crosslinking`, `mutate_and_map`, `na_footprinting`, `uv_melting`, `native_gel_mobility`, `smfret` (51 in total) | `dms`, `crosslink_seq`, `chem_probing_other` |
| NA structures | Come from **NAKB** (sequence + Rfam family match), not a PDB extension | "Extend PDB" |
| Sources | 9 implemented: PDB, BMRB, SASBDB, DisProt, AlphaFold DB, MDDB, SMASH-BIO, **NAKB**, **Rfam** (plus RNAcentral for identity) | Manuscript v3: "eight sources … including the RNA Mapping Database". **RMDB is not implemented** |
| Pilot NAs | 2 present: add riboswitch (curated draft, 3 states, X-ray only) and telomeric G4 (evidence only) | 6 listed as if planned from scratch |
| Profile agreement | `mapping.agreement` exists in the schema; the scoring isn't written yet | Described as new |

**What the nucleic-acid brief should be reduced to:**
1. Add the RMDB source (or drop RMDB from the manuscript).
2. Turn on BMRB, SASBDB, SMASH-BIO and MDDB for RNA and DNA (`MOLECULE_TYPES`).
3. Add the four missing pilot molecules: preQ1, TAR, P4–P6 and FSE.
4. Draft G4 curation that separates the cation forms.
5. Use ions in conflicts.
6. Profile-vs-dot-bracket agreement scoring.
7. Molecule pages and URLs.

**Manuscript v3 changes:**
- the source list and count (9, with NAKB and Rfam; RNAcentral for identifiers);
- RMDB only if it is implemented;
- the conflict criteria as actually implemented (after fix 1, give the σ threshold);
- the α-synuclein conflict paragraph (fix 2);
- single-method counting (fix 5).

## 7. Suggested order

1. **Fixes 1–9 and 10–12**, each with the missing tests listed in `CODE_REVIEW_DETAIL.md`. Rebuild and record how the numbers move (conflicts, mappings, single-method states) in the PR.
2. **Fixes 13–16 and §5 hygiene**: licence, branch rename, README/METHODS, HTTPS.
3. **The reduced nucleic-acid work** (§6).
4. **The audit, then freezing the paper release, then the Zenodo archives**, as in `START_HERE.md`.
