# Submission checklist: Conformome, Open Research Europe

Prepared 2026-10-23 from the `paper/ore` branch. **Not ready to submit** while any item under "What only the author can do" is open.

## What only the author can do (in this order)

1. ~~Supply the ORCID iD~~ Done 2026-10-24 (0000-0003-2487-0636, in all four places). Still open: confirm the source licences marked "to be confirmed" in Table 1 and "verify" in `zenodo/redistribution.yaml` (BMRB, SASBDB, RMDB, MDDB, SMASH-BIO, NAKB, Rfam, RNAcentral). Re-run `make zenodo-prep` after any change to `redistribution.yaml`.
2. ~~Choose the Conformome data licence~~ Done: CC BY 4.0, as published on the Zenodo data record.
3. Supply the AI model version for the Acknowledgements (`manuscript.md` line 171) and the matching line in `form_answers.md` and `cover_letter.md`.
4. Decide the second-curator note at the end of the Discussion: report agreement, or delete the note.
5. Turn on the GitHub–Zenodo integration, tag `v0.1.0` on the frozen commit, publish the draft GitHub release (`release_meta/DEPOSIT.md` §1). That mints the software DOI.
6. ~~Upload and publish the data archive~~ Done 2026-10-23: https://doi.org/10.5281/zenodo.23536810. Still open: once the software DOI exists, add it to the data record as a related work ("Is compiled by"; *Edit*, no new version).
7. ~~Data DOI in `manuscript.md`~~ Done. Still open: the software DOI (`manuscript.md` Software availability), then rebuild: `bash paper/build_formatted.sh`, and refresh `paper/submission/` (copy the new `.docx`/`.pdf`, update `form_answers.md` and `cover_letter.md`).
8. Check `CITATION.cff` `date-released`.
9. Log in at https://open-research-europe.ec.europa.eu, start a Software Tool Article submission, enter the answers from `form_answers.md`, upload the files in `paper/submission/`, accept the declarations, and submit.

## Agent checks (brief §7)

- [ ] `v0.1.0` (local) points at the commit in `paper/out/stats.json`. **Open:** no tag yet; `release.tag` is empty. The tag is step 5 above, after the author's edits, because they change the commit.
- [x] `fill_numbers.py --check`: "87 tags and Table 1 agree with stats.json".
- [x] `lint_manuscript.py`: 0 errors, 14 warnings (all author placeholders, and "abstract 300/300 words").
- [x] `conformome validate`: 0 errors. `pytest`: 135 passed.
- [ ] `stats.py --check`: **not run**; it requires HEAD to be tagged `v0.1.0` (step 5).
- [x] `paper/out/manuscript.filled.md` has no `[n]` tags and no bare corpus count. It still has 6 `[to be filled]` and 7 `[to be confirmed]` placeholders, all listed above as the author's.
- [x] Abstract 300/300 words (the ORE limit is "up to 300"); 8 keywords (limit 8).
- [x] Every `[@key]` resolves (40 distinct keys, 49 CSL entries); the Word reference list has no "???".
- [x] Figures 1–4 match their legends and the frozen build: Figure1 data model, Figure2 pipeline (counts from `stats.json`), Figure3 molecule × technique coverage (87 rows, nucleic acids grouped, bar "Molecules"), Figure4 α-synuclein page screenshots from the rebuilt `site/dist`. TIFF and PNG at 300 dpi, RGB, white background, 170 mm wide (see `form_answers.md` on the 150 mm guidance).
- [x] `make zenodo-prep` passes twice with identical bytes; SMASH-BIO is in `EXCLUDED.tsv` (2,588 records); PDB evidence is present (13,434 records).
- [x] Table 1 licence cells: PDB, DisProt and AlphaFold DB state a licence; the other seven stay `[to be confirmed]`.
- [ ] `paper/submission/` committed and the PR from `paper/ore` into `ccr-ebb336f7-3qzi9h` open and not merged. **Done when this commit is pushed** (PR #4).

## Files in this folder

| File | Source |
| --- | --- |
| `Conformome_ORE_manuscript.docx` | `bash paper/build_formatted.sh` (pandoc 3.12.1, python-docx polish) |
| `Conformome_ORE_manuscript.pdf` | same filled Markdown through xelatex with Cambria/Arial/Consolas, because MiKTeX on this machine lacks the TeX Gyre fonts the repo preamble names. Reading copy only; ORE takes the Word file. |
| `figures/Figure1–4.tiff`, `.png` | `paper/figures/fig1_model`, `fig4_pipeline`, `fig2_coverage`, `fig3_screens`, renamed to the legend numbers |
| `cover_letter.md` | draft; signature and three placeholders left to the author |
| `form_answers.md` | field-by-field answers for the submission form, with the ORE requirements read on 2026-10-23 |
