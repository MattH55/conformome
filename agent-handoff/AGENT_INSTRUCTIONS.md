# Agent task: update the Conformome manuscript, then build the archive

Work in the clone of `https://github.com/MattH55/conformome` on branch `paper/ore`. That branch is already pushed. It starts from `audit/pilot` (`a888021`) and adds this handoff: the briefs, the nucleic-acid manuscript, the Zenodo templates, and these instructions. Continue on `paper/ore`. Open a pull request into `main` when the checks below pass. Do not merge it.

Local path on the author's machine: `C:\Users\matth\OneDrive\Documents\PhD\Conformome`. A fresh clone is fine.

Read these files before editing, in this order:

1. `START_HERE.md`
2. `NUCLEIC_ACIDS_BRIEF.md` §5 and §8
3. `paper/BRIEF.md` §1–§5 (figures and the `make_bib.py` steps are out of scope here)
4. `ZENODO_BRIEF.md` and `zenodo/ZENODO_INSTRUCTIONS.md`
5. `docs/SOURCES.md`
6. `paper/manuscript.md`

## Outcome

Two products, both describing the same frozen commit:

1. `paper/manuscript.md`, with every corpus number coming from `paper/out/stats.json`, and a formatted Word file and PDF.
2. A local data archive in `release/`, plus software metadata at the repo root, ready for the author to publish. You do not publish.

## Hard rules

- Do not publish a GitHub release, do not pass `--publish` to the Zenodo upload script, and do not mint a DOI.
- Do not invent curation, licences, ORCIDs, references, audit answers, or conflict examples.
- Do not type a corpus number by hand. A number enters the manuscript only as a tag that `fill_numbers.py` fills from `stats.json`.
- Do not use the numbers already in `paper/out/stats.json`. That file is the protein-only pilot: `"tag": ""`, commit `a888021`, 81 proteins, 17,522 evidence records, 7 sources, no RMDB block. Treat it as stale and regenerate it.
- Do not edit `curation/*.yaml` except to add a draft file that `NUCLEIC_ACIDS_BRIEF.md` §5 already names, and only after each representative PDB ID has been checked on the PDB. Set `status: draft`. If a PDB ID cannot be checked, leave that state out and say so in the PR.
- Leave ORCID as `0000-0000-0000-0000`. No ORCID is recorded in `paper/ore_submission.md`.
- Leave BMRB, SASBDB, RMDB, SMASH-BIO, and MDDB licence cells as `[to be confirmed]` unless `docs/SOURCES.md` and the source module's `LICENCE` agree and are not marked `verify`. They do not agree with the Zenodo allow-list today. The allow-list in `zenodo/redistribution.yaml` stays exactly `CC0-1.0` and `CC-BY-4.0` until the author adds a value.
- The audit subsection stays out of the manuscript. `responses.csv` has not been committed.

## What the tree contains (checked 2026-10-19)

- Branch `audit/pilot` at `a888021`. PR #2 is open for the audit tooling. `main` is `863b5ef` (nucleic-acid schema work, PR #1).
- No git tags. No root `LICENSE`. No root `.zenodo.json`.
- `pytest`: 93 passed.
- `targets.yaml` lists 81 proteins and two nucleic acids: `URS000080DF85_672` (add adenine riboswitch) and `DNA-6f16b68e4fba` (human telomeric G-quadruplex, anchor PDB `143D`).
- Draft curation exists for the riboswitch only (`curation/URS000080DF85_672.yaml`). The G-quadruplex has a target and a `build/` directory, and no curation file.
- These four molecules from `NUCLEIC_ACIDS_BRIEF.md` §5 are absent from `targets.yaml` and from `curation/`: preQ1 class-I riboswitch, HIV-1 TAR, *Tetrahymena* P4–P6, SARS-CoV-2 frameshifting element.
- There is no `conformome/sources/` module for RMDB. Source modules present: PDB, BMRB, SASBDB, DisProt, MDDB, AlphaFold, SMASH-BIO, NAKB, Rfam, plus stubs `ped`, `pdbihm`, `atlas`, `literature`.
- `paper/scripts/fill_numbers.py` is still the SMASH-BIO script (`corpus_stats`, table 2). Replace that behaviour. `paper/build_formatted.sh` already calls `python3 -I scripts/fill_numbers.py --render`.
- `paper/manuscript.md` is the nucleic-acid draft. Many counts are still prose or `\[to be filled\]`. Line 94 still says 17,522 evidence entries, 19 techniques, 30 curated proteins, 68 states, and 51 uncurated proteins. Those become tags after the rebuild. If the rebuild differs, the sentence changes with the tag.
- `build/<id>/` exists for the current targets. There is no `build/manifest.json`. `site/dist/` exists and may not match a clean rebuild.
- GitHub `gh` is authenticated as `MattH55`. A draft release is allowed. Publishing is not.
- Tests were run with `python -m pytest`. The Makefile variable `PYTHON` defaults to `python3`, which may be missing on Windows. Use `python` or `py -3` when `python3` is absent, including inside `paper/build_formatted.sh` if you have to invoke it from PowerShell. Prefer Git Bash for `build_formatted.sh`.

## 1. Freeze one release

From a clean view of your branch:

```
make ingest
make map
make models
make site
```

Reuse cached files under `data/raw/` when the pipeline allows it. If a molecule has no raw download, report it and leave it out of the release. Do not fetch new source records in order to make the manuscript's draft sentences true.

Then set one version and use it everywhere:

| Place | Value |
| --- | --- |
| Git tag | `v0.1.0` |
| `.zenodo.json`, `CITATION.cff`, data metadata, dataset README, `stats.json` `release.version` | `0.1.0` |
| `stats.json` `release.tag` | `v0.1.0` |
| `stats.json` `release.commit` | the tagged commit, full SHA |

`paper/BRIEF.md` also mentions `v0.1.0-paper`. Use `v0.1.0` so the tag, the Zenodo version, and `stats.json` are the same release. Record that choice in the PR. Create the tag locally. Do not push it.

If a later edit changes any count, delete the tag, rebuild, and tag the new commit.

## 2. Regenerate `paper/out/stats.json`

Extend `paper/scripts/stats.py`. Keep the protein keys already listed in `paper/BRIEF.md` §2. Add the keys from `NUCLEIC_ACIDS_BRIEF.md` §8:

```
release.n_molecules, release.n_proteins, release.n_rna, release.n_dna
release.n_evidence_protein, release.n_evidence_na
release.n_curated_na, release.n_states_na
sources.rmdb.n_molecules, sources.rmdb.n_evidence
na.<slug>.n_evidence, .n_techniques, .n_states, .n_conflicts
g4.states.<slug>.n_evidence, .ions
conflicts.removed_by_ion_rule.protein
```

Also record `release.version`, `release.tag`, `release.commit`, and `release.build_date`.

Count a molecule only if `build/<id>/` has evidence from this run. `n_rna` and `n_dna` are counts of those molecules, not the number 6 from the draft. If RMDB contributed no records, `sources.rmdb.n_evidence` is 0 and the manuscript says so.

`stats.py --check` must match the totals on the rebuilt `site/dist/` pages, including the split by molecule type on the home page.

The manuscript claims six nucleic acids and an RMDB row. After the rebuild, if `n_rna + n_dna` is not 6, rewrite those sentences to the molecules that were built and list the missing four in the PR. Keep their names out of counted claims. Do not add them to `targets.yaml` unless you also have raw inputs and a draft curation file with checked PDB IDs.

## 3. Update the manuscript

Work in `paper/manuscript.md`. Pandoc drops HTML comments, so readers do not see the tags.

Inline number:

```
17522<!--n:release.n_evidence-->
```

Spelled-out number at the start of a sentence:

```
Eight<!-- = release.n_sources -->
```

`fill_numbers.py` must:

- Read `paper/out/stats.json`.
- Support `--check` (exit 1 on drift), `--write` (rewrite tags in place), and `--render PATH` (write `out/manuscript.filled.md` with tags resolved, leaving `manuscript.md` unchanged).
- Regenerate Table 1 between `<!-- table1:start -->` and `<!-- table1:end -->`. Rows are ingested sources with at least one evidence record, ordered by molecules descending. Columns stay Source, Unit of evidence, Proteins / nucleic acids, Licence. Protein and nucleic-acid counts are tags. Licence text comes from a dict in the script: use the strings in `docs/SOURCES.md`. Any row whose `docs/SOURCES.md` licence contains `verify`, `not stated`, `per project`, or `TBD` is rendered as `[to be confirmed]`.
- Convert spelled-out numbers 1–99, including a capital at the start of a sentence.

Replace every corpus count, including the bare numbers in the pilot-results paragraph and the table note that says "81" and "six". The words "81 proteins and six nucleic acids" stay only when `release.n_proteins` is 81 and `release.n_rna + release.n_dna` is 6. Otherwise change the sentence.

Leave these as placeholders, and copy each one into the PR:

- ORCID.
- Zenodo DOIs and the version DOI. Write `\[to be filled: Zenodo DOI\]`.
- Data licence for Conformome records. `docs/PILOT_REPORT.md` has not chosen one. The archive may still carry CC BY 4.0 as the intended data licence; the manuscript keeps the placeholder until the author confirms.
- Code licence, until a root `LICENSE` file exists. Adding MIT `Copyright (c) 2026 Matthew T. J. Halma` is allowed when the root has no `LICENSE`. If a different licence file is already there, keep it and report the mismatch with `.zenodo.json`.
- One α-synuclein conflict sentence, until both values are checked against their source pages.
- Named single-method states, until you can name two or three from `stats.json` with molecule and technique. The count itself is a tag (`release.n_single_method_states`).
- The G-quadruplex use-case sentence, until `g4.states.*` exists. If the G-quadruplex has no curation file, leave the descriptive placeholder and tag only the counts you can compute.
- The technique-list check. Compare the techniques named in the Methods paragraph with technique ids that have `n_evidence > 0`. Delete names that have zero entries. Add names that have entries and are missing from the sentence. The two counts are tags (`release.n_techniques_taxonomy`, `release.n_techniques`).
- AI model version in the Acknowledgements.

Do not add a "Validation of the mapping" subsection.

Citations stay as pandoc `[@key]` and resolve from `paper/references.csl.json`. Do not run `make_bib.py`. When you add a reference, add a CSL-JSON entry with a DOI and check it against Crossref. If Crossref is unreachable, use `paper/data/crossref_cache.json` and say that the check was skipped.

Build from `paper/` with Git Bash:

```
bash build_formatted.sh
```

That script renders `out/manuscript.filled.md`, then `out/Conformome_ORE_manuscript.docx` and `out/Conformome_ORE_manuscript.pdf`. If pandoc or xelatex is missing, write the filled markdown, say which tool is missing, and do not claim the Word or PDF file exists.

`paper/scripts/lint_manuscript.py` should report 0 errors. Remaining author decisions are warnings. Abstract: 300 words or fewer. Keywords: 8 or fewer.

## 4. Build the data archive

Follow `ZENODO_BRIEF.md` §2–§5. Implement:

- `scripts/make_data_release.py`
- `scripts/check_release_metadata.py`
- a `zenodo-prep` target in the `Makefile`

`make zenodo-prep` writes `release/` and then runs the checker.

`release/` contains exactly:

```
all-records.jsonl
molecules.zip
profiles.zip
schemas.zip
techniques.yaml
curation.zip
manifest.json
CHANGELOG.md
README.md
LICENSE
SHA256SUMS
EXCLUDED.tsv
```

Licence filter: keep an evidence record, and any reactivity profile it references, only when `provenance.licence` is exactly `CC0-1.0` or `CC-BY-4.0`. The strings in the current modules are longer (`CC0 1.0 (wwPDB archive data)`, `CC BY 4.0`, `CC0 1.0 (verify)`, `not stated by the source`, `per project (CC BY 4.0 for most)`). Do not silently rewrite them to the allow-list spelling. Records that do not match are excluded. `EXCLUDED.tsv` has three columns: source, licence value, number of records excluded. Print that table. Molecule, state, transition, and model records are Conformome's own and stay in the archive. A mapping that points at excluded evidence keeps the evidence id.

`README.md` is `zenodo/data-release/README_dataset.md` with the totals filled from `stats.json`. Leave DOI and `[confirm]` cells for the author. The script prints those cells at the end.

`LICENSE` in `release/` is the CC BY 4.0 legal text. If you cannot download it, write one line pointing at `https://creativecommons.org/licenses/by/4.0/legalcode.txt` and flag that in the PR.

Zips use sorted names and a fixed timestamp so a second run is byte-identical. Add a test for that.

Copy `zenodo/data-release/zenodo_data_metadata.json` to `release_meta/zenodo_data_metadata.json` and set the version. Fill description counts from `stats.json`. If the release is not 81 proteins and six nucleic acids, change that sentence in the metadata to the real counts. Keep `SOFTWARE_VERSION_DOI` and the ORCID placeholder. The upload script must refuse to run while those remain.

Copy `zenodo/repo-root/.zenodo.json` and `zenodo/repo-root/CITATION.cff` to the repo root and set the version. In `CITATION.cff`, set `date-released` to `2026-10-19` and mark it in the PR as a date the author confirms. Add this line to `README.md`:

```
<!-- zenodo badge: added after first release -->
```

`scripts/check_release_metadata.py` fails with a list of problems when any of these is false:

- `.zenodo.json` and `release_meta/zenodo_data_metadata.json` parse as JSON.
- `CITATION.cff` parses as YAML and has `cff-version`, `title`, `authors`, `version`, and `license`.
- The version `0.1.0` is the same in the tag (without `v`), `.zenodo.json`, `CITATION.cff`, the data metadata, the dataset README, and `stats.json`.
- The software licence matches the root `LICENSE`, and the data licence matches `release/LICENSE`.
- Totals in the dataset README and the metadata description equal `stats.json`.
- A rescan of `release/` finds no evidence whose licence is outside the allow-list.
- `SHA256SUMS` verifies.

ORCID and DOI placeholders are warnings, so the PR can be reviewed before the author fills them in.

Run `make zenodo-prep` twice. The second `release/` must match the first byte for byte.

## 5. Draft GitHub release, or the command for it

Write `release_meta/release_notes.md` from `stats.json`: protein and nucleic-acid totals separately, the schema 2.0.0 change from protein records to molecule records, the sources that actually contributed records, and one line that the data archive is a separate Zenodo record whose DOI will follow.

Create a draft only:

```
gh release create v0.1.0 --draft --target <tagged commit> \
  --title "Conformome v0.1.0: pilot release described in the ORE article" \
  --notes-file release_meta/release_notes.md
```

If `gh` cannot create the draft, put that command and the notes in the PR. Do not publish the release. Publishing is what makes Zenodo mint the software DOI.

Do not run `zenodo/data-release/zenodo_upload_data.py`. Leave `release/` on disk so the author can upload it.

## 6. Pull request

The PR description lists, in this order:

1. The tag, commit, and the counts that changed relative to the stale `stats.json` (81 / 17,522 / 7 sources).
2. Sentences rewritten because the rebuilt release does not match the draft, including how many nucleic acids were actually built.
3. Molecules from `NUCLEIC_ACIDS_BRIEF.md` §5 that are still absent.
4. `EXCLUDED.tsv`.
5. Open placeholders: ORCID, source licences still marked verify, data licence, both DOIs, conflict example, single-method examples, G-quadruplex prose, AI model version, `date-released`.
6. The author's remaining steps:
   1. Confirm the ORCID and the source licences. Edit `zenodo/redistribution.yaml` only with a confirmed SPDX-style value. Re-run `make zenodo-prep`.
   2. Turn the repo on at zenodo.org → Account → GitHub.
   3. Publish the draft GitHub release. Copy the software version DOI.
   4. Put that DOI into `release_meta/zenodo_data_metadata.json`. Run `ZENODO_TOKEN=… python zenodo/data-release/zenodo_upload_data.py release/`, review the draft on Zenodo, and publish it. Copy the data version DOI.
   5. Put both DOIs into the manuscript (Data availability and Software availability) and into the dataset README on Zenodo (Edit, which does not create a new version).
   6. After the article is published, add its DOI to both Zenodo records under Related works.

## Done when

- `v0.1.0` points at the commit recorded in `paper/out/stats.json`.
- `stats.py --check` and `fill_numbers.py --check` pass.
- `out/manuscript.filled.md` has no `\[to be filled: n\]` and no bare corpus count. Author decisions listed above may remain.
- `make zenodo-prep` passes twice with identical `release/` bytes. Checker output is warnings only for the ORCID and the DOIs.
- `release/EXCLUDED.tsv` lists every excluded source and the licence string stored on the records.
- A draft GitHub release exists, or the exact command is in the PR.
- Nothing has been published.
