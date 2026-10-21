# Conformome ORE paper — build brief for a coding agent

You are working in the `matth55/conformome` repository. Your job is to turn the draft in `paper/manuscript.md` into a submission-ready Open Research Europe (ORE) **Software Tool Article**. Every number in the paper must come from the release files, every figure from a script, and the build must be one command.

Read this whole file before you start. Work on a branch (`paper/ore`), commit in small steps, and open a PR when §9 passes. Do not change the pipeline's behaviour to make the paper look better. If the data disagree with the text, change the text, and list the change in the PR description.

## 0. What is already here

```
paper/
  BRIEF.md                  this file
  manuscript.md             full draft (ORE section order, numbered citations, number tags)
  open-research-europe.csl  citation style (Vancouver, superscript); do not edit
  reference.docx            Word style reference for pandoc
  scripts/
    make_bib.py             reference list -> references.bib (Better BibTeX keys) + pandoc citations; --renumber, --check
    check_dois.py           resolves every DOI in references.bib, checks title/year
    lint_manuscript.py      ORE limits, figure/table/citation cross-checks, placeholder report
    fill_numbers.py         keeps tagged numbers equal to stats output (needs adapting, §3)
    figstyle.py             shared matplotlib style (Arial/Liberation Sans, sizes, palette)
    lineno.tex              line numbers for the review PDF
```

These come from the SMASH-BIO paper kit (`MattH55/smash-bio`, `paper/`), which was built and submitted the same way. When something here is unclear, that kit is the reference implementation.

## 1. Invariants

1. **Freeze first.** The paper describes one tagged release. Before computing anything, build the release from a clean checkout (`make ingest map models site`, or reuse `build/` if `build/manifest.json` matches the commit), and tag it `v0.1.0-paper` (or the next free `v0.x.0-paper`). All numbers, figures and screenshots come from that tag. If you rebuild later and the numbers change, re-tag. Do not edit the paper by hand to match a moving target.
2. **No hand-typed numbers.** Every corpus number in the text has a tag like `81<!--n:release.n_proteins-->`. Pandoc drops HTML comments, so readers never see them. Spelled-out numbers at the start of a sentence carry `<!-- = key -->` and are checked too (§3).
3. **Never fabricate.** Do not invent references, DOIs, licences, conflict examples or reviewer details. Unresolved items stay as `\[to be filled: …\]` or `\[to be confirmed\]` placeholders. The linter reports them, and they go in the PR description as the author's to-do list.
4. **Do not touch** `curation/*.yaml` or the source modules as part of this task. The paper reports the pilot as it is.
5. Use Python 3.11 or later. Run scripts with `python -I`. Keep new dependencies to matplotlib, numpy, pyyaml, jsonschema and playwright, and add them to `paper/requirements.txt`.

## 2. `paper/scripts/stats.py`: every number from the release

Inputs: `build/` (or the downloads directory the site build writes): `all-records.jsonl`, `proteins/<acc>.json`, `techniques.yaml`, `manifest.json`, and the conflict and mapping outputs of `make map`. First find where each of these lives in the repo (`grep -rn "all-records" Makefile src/ scripts/`). Write the paths in a constant at the top of the script, with no guessing at runtime.

Output: `paper/out/stats.json`, with exactly these keys (add more if you need them; never rename these):

```
release.tag, release.commit, release.build_date
release.n_proteins            proteins with >=1 evidence record                     (draft: 81)
release.n_evidence            evidence records                                      (17,522)
release.n_techniques          distinct technique ids with >=1 evidence record       (19)
release.n_techniques_taxonomy entries in techniques.yaml                            (19)
release.n_sources             sources with >=1 evidence record                      (7)
release.n_stub_sources        sources implemented but with 0 records (ped, pdbihm, atlas, literature)
release.n_curated             proteins with a curation file                         (30)
release.n_uncurated           n_proteins - n_curated                                (51)
release.n_states              state records                                         (67)
release.n_states_observed / release.n_states_inferred
release.n_mapped / release.n_unmapped / release.n_ambiguous   evidence on curated proteins
release.n_mapped_by_assignment / release.n_mapped_by_rule
release.n_conflicts           total flagged conflicts
release.n_uncompared          items skipped for lack of uncertainty
release.n_single_method_states  states whose mapped evidence comes from exactly 1 technique
release.n_transitions, release.n_models
sources.<id>.n_proteins, sources.<id>.n_evidence     for pdb, bmrb, afdb, smash, disprot, mddb, sasbdb
techniques.<id>.n_evidence, techniques.<id>.n_proteins   for all 19 ids
p37840.n_evidence, .n_sources, .n_techniques, .n_mapped, .n_unmapped, .n_states, .n_conflicts
p37840.n_smash_unmapped       SMASH-BIO evidence on P37840 not mapped to any state  (19)
p37840.states.<slug>.n_evidence, .n_techniques, .basis, .representative_pdb
```

Map the α-synuclein state slugs `disordered`, `micelle` and `fibril` to the state ids in `curation/P37840.yaml` with a small dict at the top of the script. If the curation file has a different number of states, stop and report it. Do not force the mapping.

Also check that `stats.py --check` agrees with the site's own totals: parse the counts on `site/index.html` and `site/protein/P37840/index.html` (or wherever `make site` writes) and fail on any difference. A paper and a site that disagree is the worst possible outcome.

The draft values are given above in brackets. If the frozen release differs, that is expected. Let `fill_numbers.py --write` update the text, then reread every sentence that contains a changed number. In particular, check "almost all of them cryo-EM", "lopsided" and "single technique" in the α-synuclein use case, and rewrite them if they are no longer true.

## 3. Adapt `fill_numbers.py`

- Point `STATS` at `paper/out/stats.json`. Remove the `corpus_stats` / `TECH_LABELS` import and the `table2` generator.
- Add a `table1` generator for the block between `<!-- table1:start -->` and `<!-- table1:end -->`. The rows are the 7 ingested sources in descending `n_proteins` order. Keep the "Unit of evidence" and "Licence" columns from a small dict in the script. The licence strings come from §5 and stay `\[to be confirmed\]` until resolved. Keep the tagged count cells.
- Add support for spelled-out numbers: `Seven<!-- = release.n_sources -->`. The check converts the word with a dict for 1–99 (capitalised at the start of a sentence) and compares. `--write` replaces the word.
- `--check` exits 1 on any drift; `--write` rewrites in place.

## 4. Figures (`paper/scripts/fig*.py` → `paper/figures/`)

Each script writes `.pdf` (vector), `.png` (300 dpi) and `.tiff` (300 dpi, LZW, RGB, white background, with no transparency; flatten alpha onto white). Width is 170 mm for full-width and 85 mm for single-column. Use `figstyle.py`. Body text must be at least 7 pt at final size, with no clipped or overlapping labels. Render each PNG and look at it with your image viewer before you move on.

| Fig | Script | Content | Data |
| --- | --- | --- | --- |
| 1 | `fig1_model.py` | Data model. Boxes for protein, state (observed / inferred badge, nesting arrow), evidence (technique, construct, conditions, value ± σ + unit, provenance), mapping (who, confidence, reason) placed **between** evidence and state, transition (state ↔ state), model (per observed state), and a conflict marker between two evidence items on one state. Draw it with matplotlib patches; no hand-drawn assets. | Field names read from `schemas/*.json` so that the figure cannot drift from the schema. |
| 2 | `fig2_coverage.py` | Protein × technique matrix: 81 rows × 19 columns, log-shaded by evidence count (0 = white), rows grouped curated / not yet curated and ordered by total within each group, columns in `techniques.yaml` order. Label rows with protein short names (UniProt gene names) in small type. Above the matrix, a bar per column with the number of proteins; on the right, a bar per row with total evidence. | `all-records.jsonl` |
| 3 | `fig3_screens.py` | Playwright screenshots of `protein/P37840/` from the **local build of the frozen tag** (serve `site/` with `python -m http.server`), not the live site. (A) the states panel, (B) the coverage grid, (C) the Mol* viewer on the fibril model. Wait for the viewer canvas to render, and use a 1400 px viewport at device scale factor 2. Compose the panels into one figure with A/B/C labels. Use `--compose` to recompose from cached screenshots without a browser. | site build |
| 4 | `fig4_pipeline.py` | Pipeline: sources → `make ingest` → `make map` (assignments, rules, conflicts) → `make models` → `make site` + downloads, with the record counts at each stage from `stats.json` (evidence, mapped/unmapped/ambiguous, states, models, files). | `stats.json` |

Chromium is usually preinstalled. If `playwright` cannot find it, set `executablePath` rather than downloading a new copy. Legends are already in the manuscript. If a figure ends up showing something the legend does not say, fix the legend.

Also write `figures_preview.py`, which produces `out/figures_preview.md`: each figure followed by its legend, built into a PDF for proofreading.

## 5. Placeholders to resolve

Resolve what you can from the repo and public sources; leave the rest, and list it.

| Item | Where | How |
| --- | --- | --- |
| Data licence for records and curation files | Data availability | Read `docs/PILOT_REPORT.md` and `LICENSE*`. If the author has decided, fill it in. If not, leave the placeholder and say so in the PR. Do not choose one. |
| Code licence | Software availability | From `LICENSE` in the repo root. If there is none, leave the placeholder and flag it. ORE requires an OSI-approved licence. |
| Source licences: BMRB, SMASH-BIO, SASBDB | Table 1 | From each source's own terms page and from what the source module records in `provenance.licence`. Quote the exact licence name and add the terms URL to the PR. If the module stores a different value from the terms page, flag it. |
| Release version and Zenodo DOIs | Data and Software availability | After the tag is pushed and the GitHub–Zenodo integration archives it. If the integration is not enabled, write the steps in the PR for the author. Do not mint a DOI any other way. |
| Per-technique sentence | Results › pilot release | Write 1–2 sentences from `stats.json`. Every number gets a tag. |
| One conflict example | α-synuclein use case | Pick one conflict on P37840 from the map output. Describe it factually: the two entries, observable, values ± σ and conditions. **Leave the placeholder** unless both entries' values can be checked against their source pages. The author will review. |
| Single-method states | "finding where the evidence is thin" | Filled by `fill_numbers --write` (the draft has 0 as a dummy). Name 2–3 examples in the text. |
| Second-curator note | Discussion | Leave it for the author. |

## 6. References

The reference list is in the SMASH-BIO style, and `make_bib.py` parses it as is (tested on all 21 entries). Run `make_bib.py --renumber` after any text change. It renumbers citations by first appearance.

Check these against the publisher's page before submission. Correct the entry in the list, not in the `.bib`:

- **8 (MDDB):** Amaro et al. 2025 *Nat. Methods* is the community FAIR-simulations paper. Confirm the volume and pages, and check whether a dedicated MDDB database paper exists by now. If one does, cite it instead.
- **9 (SMASH-BIO):** submitted to ORE. If it has been published, give the ORE citation with its DOI. Otherwise cite the Zenodo record `https://doi.org/10.5281/zenodo.23455641` as a misc entry (`Halma, M. T. J. 2026. SMASH-BIO release v1.0.0-paper. Zenodo. https://doi.org/…`), which `parse_ref` handles.
- **11 (CoDNaS 2.0), 13 (PDB-IHM, Vallat et al. 2021), 15 (UniProt 2025):** confirm the author lists, volume and pages.
- Everything else: `check_dois.py` must pass. If Crossref is unreachable, `make_bib.py` uses `data/crossref_cache.json`. Commit the cache.

Do not add references to fill gaps. If a sentence needs a citation you cannot find, leave a `\[to be filled: citation\]` placeholder.

## 7. Build: `paper/scripts/build.sh`

Copy the structure of the SMASH-BIO `build.sh` (gates first, outputs after):

```bash
set -euo pipefail; cd "$(dirname "$0")/.."; PY="python -X utf8"; mkdir -p out figures
$PY -I scripts/stats.py --check > out/stats.json
$PY -I scripts/fill_numbers.py --check
$PY -I scripts/lint_manuscript.py
$PY -I scripts/make_bib.py --renumber
$PY -I scripts/make_bib.py            # writes references.bib + out/manuscript.pandoc.md
$PY -I scripts/make_bib.py --check
[[ "${1:-}" == "--skip-network" ]] || $PY -I scripts/check_dois.py
for f in fig1_model fig2_coverage fig4_pipeline; do $PY scripts/$f.py; done
[[ -f figures/_screens/states.png ]] || $PY scripts/fig3_screens.py
$PY scripts/fig3_screens.py --compose
COMMON=(out/manuscript.pandoc.md --citeproc --bibliography references.bib --csl open-research-europe.csl)
pandoc "${COMMON[@]}" --reference-doc reference.docx -o out/manuscript.docx
pandoc "${COMMON[@]}" --pdf-engine=xelatex -V geometry:margin=25mm -V fontsize=12pt -V linestretch=2 \
  -V mainfont="Liberation Sans" -V fontfamily=helvet -H scripts/lineno.tex -o out/manuscript.pdf
$PY scripts/figures_preview.py
pandoc out/figures_preview.md --pdf-engine=xelatex -V geometry:margin=20mm -V mainfont="Liberation Sans" -V fontfamily=helvet -o out/figures_preview.pdf
```

Known gotchas from the SMASH-BIO build:

- `lmodern.sty` is often missing. Use `-V fontfamily=helvet` with Liberation Sans, and add a fontconfig alias Arial → Liberation Sans if matplotlib asks for Arial.
- Liberation Sans lacks some glyphs, such as ∇. Write those as TeX math.
- Keep name particles braced in the `.bib` (`{de Graaf}`, `{van Eck}`). `make_bib.py` already does this.

Add a `paper` target to the repo `Makefile` that runs `bash paper/scripts/build.sh`. Add `paper/out/` and `paper/figures/_screens/` to `.gitignore`. Commit the figures.

## 8. Submission notes: `paper/ore_submission.md`

Write this file with:

- **Article type:** Software Tool Article. Subject: Biological sciences › Structural biology / Biophysics. Title, author and the 8 keywords taken from the manuscript.
- **Eligibility:** Horizon 2020 MSCA ITN AntiHelix, grant agreement 859853 (project ended; ORE accepts results of completed H2020 projects). Conformome extends the conformational-ensemble and FAIR-data work of that fellowship; it ingests SMASH-BIO and builds on the Table 3 standard, both outputs of the same project. Note: *confirm with ore@f1000.com if in doubt.*
- **Competing interests:** former LUMICKS B.V. employee, and developer of SMASH-BIO, a source that Conformome ingests. Copy these from the manuscript.
- **AI-use disclosure:** the Acknowledgements text, verbatim, for the submission form.
- **Upload set:** `out/manuscript.docx`; `figures/fig1_model.tiff` … `fig4_pipeline.tiff`; the Data and Software availability DOIs.
- **Suggested reviewers.** Table with name, affiliation, expertise and why. Every affiliation is marked *confirm*. Use public pages only, and do not include email addresses. Starting list for the author to prune:
  - Kresten Lindorff-Larsen (Copenhagen): ensembles, MD and integrative modelling.
  - Benjamin Schuler (Zurich): smFRET of disordered proteins.
  - Andrej Šali (UCSF): integrative structures, PDB-IHM.
  - Mihaly Varadi (EMBL-EBI): PDBe-KB, AlphaFold DB, data integration.
  - Michael Woodside (Alberta): force spectroscopy of folding.
  - Lewis Kay (Toronto): NMR of excited states.
  - Silvio Tosatto (Padua): DisProt and PED. This is the closest resource. Note in the table that Conformome links to these rather than duplicating them.
- **Exclude:** VU Amsterdam (Wuite, Peterman, Heller groups), co-authors of Halma et al. 2025 (Kumar, van Eck, Abeln, Gates), and current or former LUMICKS staff.

## 9. Done when

- [ ] Tag `v0.x.0-paper` exists and `stats.json` records it with its commit.
- [ ] `bash paper/scripts/build.sh` exits 0 from a clean clone, given `build/` for that tag.
- [ ] `stats.py --check` agrees with the site build; `fill_numbers.py --check` reports no drift.
- [ ] `lint_manuscript.py` reports 0 errors, the abstract has 300 words or fewer, and there are 8 keywords or fewer. Only the §5 items the author must decide remain as warnings.
- [ ] `make_bib.py --check` passes, and `check_dois.py` passes or lists only the §6 items.
- [ ] All 4 figures exist as pdf/png/tiff, you have looked at each one, and each legend matches its figure.
- [ ] `out/manuscript.docx` opens. `out/manuscript.pdf` has line numbers, superscript citations, all figures referenced in order (Fig. 1 → 4) and Table 1 rendered.
- [ ] `ore_submission.md` is written.
- [ ] The PR description lists: the numbers that changed from the draft, sentences rewritten because of them, the open placeholders with the facts needed for each, and any reference corrections.
