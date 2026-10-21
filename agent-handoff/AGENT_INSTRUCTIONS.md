# Agent task: update the Conformome manuscript, then build the archive

Work in the clone of `https://github.com/MattH55/conformome` on branch `paper/ore` (pushed). Continue on that branch.

The code review in `CODE_REVIEW_DETAIL.md` and `REPO_REVIEW.md` (fixes 1–16, except the default-branch rename and Enforce HTTPS) is already applied on this branch. Do not revert the 3σ conflict rule, the word-boundary mapper, the licence allow-list, or the parser fixes. Corpus counts in the manuscript that say "to be filled" are waiting on a full `make map`; do not type them. Do not rename the default branch. Do not publish.

The default branch on GitHub is `ccr-ebb336f7-3qzi9h`, at the same commit as local `main` (`863b5ef`). There is no `origin/main`. Open the pull request into `ccr-ebb336f7-3qzi9h`. Do not merge it. `paper/ore` is already two commits ahead of that default: audit tooling (`a888021`) and this handoff. PR #2 is the open audit pull request; leave it alone.

Local path on the author's machine: `C:\Users\matth\OneDrive\Documents\PhD\Conformome`. A fresh clone of `paper/ore` is fine.

Read these files before editing, in this order:

1. This file. Where it disagrees with `ZENODO_BRIEF.md` or `paper/BRIEF.md`, this file wins.
2. `NUCLEIC_ACIDS_BRIEF.md` §2.2, §5, §6, §7 and §8.
3. `docs/SOURCES.md` (the live redistribution rule).
4. `paper/manuscript.md`.
5. `ZENODO_BRIEF.md` and `zenodo/ZENODO_INSTRUCTIONS.md` for the archive layout only.

`docs/HANDOFF.md` and `docs/PILOT_REPORT.md` describe the protein-only pilot and were not updated when the molecule schema landed. Do not treat them as the list of what is left to build. `paper/BRIEF.md` is the older protein paper kit: its figure table numbers Fig. 3 as screenshots and Fig. 4 as the pipeline. The manuscript is the authority. It numbers Fig. 2 pipeline, Fig. 3 coverage matrix, Fig. 4 α-synuclein screenshots. Do not renumber the manuscript to match the brief.

## Outcome

One frozen commit, then two products that describe it:

1. `paper/manuscript.md`, with every corpus number coming from `paper/out/stats.json`, and a formatted Word file and PDF.
2. A local data archive in `release/`, plus software metadata at the repo root, ready for the author to publish. You do not publish.

Do not tag, and do not write `release/`, until the scope gate below has been resolved in the files you are about to commit.

## Scope gate

The manuscript is written as a six-nucleic-acid paper with RMDB, reactivity profiles, a Molecules page, and a conflict rule that refuses to compare different cations. The tree does not build that paper. Checked on 2026-10-19, from `build/*/evidence.json` and `build/*/mapped.json`:

| What the manuscript says | What this tree has |
| --- | --- |
| Eight sources, including RMDB | No RMDB module. Protein sources are PDB, BMRB, SASBDB, DisProt, AlphaFold DB, MDDB, SMASH-BIO. RNA/DNA sources are NAKB and Rfam only. PDB, BMRB, SASBDB, SMASH-BIO and MDDB are not queried for nucleic acids (`MOLECULE_TYPES` is unset, so they default to protein). |
| Six nucleic acids, each with draft curation | `targets.yaml` has two: `URS000080DF85_672` (add adenine riboswitch, 13 records: 12 NAKB X-ray, 1 Rfam) and `DNA-6f16b68e4fba` (telomeric G-quadruplex `AGGGTTAGGGTTAGGGTTAGGG`, anchor PDB `143D`, 14 NAKB records: 10 X-ray, 4 NMR structures). Draft curation exists only for the riboswitch (3 observed states, 10 mapped, 3 unmapped, 0 conflicts). The G-quadruplex has no curation file, no states and no mappings. Missing from `targets.yaml`: preQ1, HIV-1 TAR, *Tetrahymena* P4–P6, SARS-CoV-2 frameshifting element. |
| Cations are part of the conflict rule | `comparable()` requires the same ion species, each concentration within a factor of two. A missing ion list is not comparable. NAKB is still the only source that fills `conditions.ions`. |
| Reactivity profiles in the downloads | No `profiles/` directory and no source writes them. |
| A Molecules page and per-molecule bundles | The nav still says Proteins. Nucleic-acid pages are served at `/protein/<id>/`. Bundles go to `downloads/proteins/`. |
| 17,522 evidence records, 7 sources | Those are the protein rows. The same build has 27 further nucleic-acid records (17,549 evidence records in total). `paper/scripts/stats.py` skips any `molecule.json` whose type is not `protein`, which is why a stats file would hide them. |

Pick one path and say which in the pull request. Do not mix them.

**Finish.** Complete `NUCLEIC_ACIDS_BRIEF.md` §5–§7 before freezing: the six molecules, RMDB or an explicit recorded decision that RMDB returned no records, draft curation with `status: draft`, ion-aware conflict comparison, profile sidecars for probing records that exist, and site labels that match the manuscript (Molecules, type split, ion column). Representative PDB IDs go into a curation file only after they have been checked on the PDB. If an identifier cannot be checked, leave that state out and name it in the PR. Do not invent deposits, sequences, licences, or mappings.

**Cut.** If a molecule or source cannot be built from real records, delete the claims that depend on it. A cut is an edit to the false sentences, not a swap of the number 6 for 2 while RMDB, the cation rule, the profiles, and the Molecules page remain in the text. On this path, do not add the key `conflicts.removed_by_ion_rule.protein` as if the rule existed. Remove the sentence that says different cations are never compared, unless you have implemented that comparison.

Do not fetch records merely to make a draft sentence true, and do not invent a fourth nucleic acid to keep the word "six". A molecule that has no raw input and no checked structures is a cut, listed in the PR.

## Hard rules

- Do not publish a GitHub release, do not pass `--publish` to the Zenodo upload script, and do not mint a DOI.
- Do not invent curation, licences, ORCIDs, references, audit answers, or conflict examples.
- Do not type a corpus number by hand. A number enters the manuscript only as a tag that `fill_numbers.py` fills from `stats.json`.
- `paper/out/stats.json` is not on the branch. Any copy on a local disk from before this handoff is the protein-only count. Regenerate it after the scope gate.
- Leave ORCID as `0000-0000-0000-0000`. No ORCID is recorded in `paper/ore_submission.md`.
- Do not rewrite `provenance.licence` on evidence records so that it matches an SPDX token.
- The audit subsection stays out of the manuscript. No `responses.csv` is committed. `scripts/audit_sample.py` refuses an untagged HEAD; draw audit rounds only after the paper tag exists, and do not put placeholder audit numbers into the manuscript.
- Opening the pull request starts `.github/workflows/ci.yml`: `make download` then `make validate` for every target. That job uses the network and the weekly raw-data cache. Open the PR when the branch is ready, not at the start.

## Licence rule for the archive

The site includes a source in the downloads when `docs/SOURCES.md` says `redistribute: yes`, and drops it when that column says `no`. SMASH-BIO and literature are `no`. BMRB, SASBDB, NAKB and RNAcentral are `yes` with a verify note. The validator enforces the source name, not an SPDX id.

The strings stored on the records, counted from the current `build/*/evidence.json`, are:

| Records | Source | `provenance.licence` |
| --- | --- | --- |
| 13,434 | RCSB PDB | `CC0 1.0 (wwPDB archive data)` |
| 2,588 | SMASH-BIO | `not stated by the source` |
| 746 | BMRB | `CC0 1.0 (verify)` |
| 264 | MDDB | `This trajectory dataset is released under a Creative Commons Attribution 4.0 International Public License` |
| 224 | SASBDB | `CC BY 4.0 (verify)` |
| 190 | DisProt | `CC BY 4.0` |
| 76 | AlphaFold DB | `CC BY 4.0` |
| 26 | NAKB | `PDB-derived fields: CC0 1.0 (wwPDB archive); NAKB annotations not used` |
| 1 | Rfam | `CC0 1.0` |

None of those equal `CC0-1.0` or `CC-BY-4.0`. Filtering on those two tokens drops every evidence record. Do not do that.

`zenodo/redistribution.yaml` now lists those stored strings, plus `deny_sources` for SMASH-BIO and literature. The site and the validator use that file. Keep a record when its stored licence is on that list. MDDB is per record: the exact sentence above is allowed, and a record whose licence is missing, `not stated`, or any other sentence is excluded. A new string encountered on a `redistribute: yes` source is excluded. It is not relabelled. Do not put the SPDX tokens `CC0-1.0` and `CC-BY-4.0` back.

`EXCLUDED.tsv` has three columns: source, licence value, number of records excluded. SMASH-BIO must appear there. PDB, DisProt and AlphaFold must not, unless a record's own string is absent from the list.

The checker fails if `release/` contains evidence from a denied source. It also fails if the archive contains zero evidence records while the build has records from a source marked `redistribute: yes`. Comparing the README's headline totals to `stats.json` is not enough.

The dataset README states two counts: the corpus totals from `stats.json`, and the number of evidence records actually present in `all-records.jsonl`. The manuscript already says that evidence which may not be redistributed is left out of the downloads. Keep that distinction. Do not make the README claim that the zip contains the SMASH-BIO rows.

Manuscript licence cells for BMRB, SASBDB, RMDB, SMASH-BIO and MDDB stay `[to be confirmed]`. DisProt and AlphaFold may say `CC BY 4.0`. PDB may say `CC0 1.0 (wwPDB archive data)`. NAKB and Rfam keep the verify note in the PR even though their records are included.

## 1. Freeze one release

Do this only after the scope gate is resolved in code and in `paper/manuscript.md`.

```
make ingest
make map
make models
make site
```

Reuse `data/raw/` when the pipeline allows it. On Windows, `python3` may be missing; `PYTHON=python make site` or `py -3` is acceptable. Prefer Git Bash for `paper/build_formatted.sh`.

Then use one version everywhere:

| Place | Value |
| --- | --- |
| Git tag, created locally, not pushed | `v0.1.0` |
| `.zenodo.json`, `CITATION.cff`, data metadata, dataset README, `stats.json` `release.version` | `0.1.0` |
| `stats.json` `release.tag` | `v0.1.0` |
| `stats.json` `release.commit` | the tagged commit, full SHA |

`paper/BRIEF.md` also mentions `v0.1.0-paper`. Use `v0.1.0` so the tag and the Zenodo version are the same release. Record that choice in the PR. If a later edit changes a count, delete the local tag, rebuild, and tag the new commit.

## 2. Regenerate `paper/out/stats.json`

`paper/scripts/stats.py` currently ignores non-protein builds. Count every `build/<id>/mapped.json`.

Keep the protein keys in `paper/BRIEF.md` §2. Add the keys from `NUCLEIC_ACIDS_BRIEF.md` §8 that the chosen scope can support. `release.n_rna` and `release.n_dna` are counts of molecules in the frozen build, not the number 6. `sources.rmdb.*` is present only when an RMDB module ran; a missing module is not reported as zero evidence from RMDB.

`stats.py --check` must match the rebuilt `site/dist/` pages. If the cut path leaves the nav saying Proteins, check those pages, and do not require a molecule-type split the site does not render.

Also record `release.version`, `release.tag`, `release.commit`, and `release.build_date`.

## 3. Update the manuscript

Work in `paper/manuscript.md`. Pandoc drops HTML comments.

```
17522<!--n:release.n_evidence-->
Eight<!-- = release.n_sources -->
```

Replace `paper/scripts/fill_numbers.py`. It is still the SMASH-BIO script (`corpus_stats`, table 2). The replacement must:

- Read `paper/out/stats.json`.
- Support `--check` (exit 1 on drift), `--write` (rewrite tags in place), and `--render PATH` (write `out/manuscript.filled.md`, leaving `manuscript.md` unchanged). `paper/build_formatted.sh` already calls `--render`.
- Regenerate Table 1 between `<!-- table1:start -->` and `<!-- table1:end -->`. Rows are sources with at least one evidence record, ordered by molecules descending. Licence text follows the licence rule above.
- Convert spelled-out numbers 1–99, with a capital at the start of a sentence.

Replace every corpus count, including the bare numbers in the pilot-results paragraph (17,522, 19 techniques, 30 and 51 proteins, 8,679, 4,110, and the α-synuclein 346 / 262 / 211 / 33 / 19 split). The α-synuclein paragraph matches `docs/PILOT_REPORT.md` and can be tagged if `stats.py --check` agrees with `site/dist/protein/P37840/`. The phrase "81 proteins and six nucleic acids" survives only when both numbers come from `stats.json`.

Leave these as placeholders, and copy each one into the PR:

- ORCID.
- Zenodo DOIs. Write `\[to be filled: Zenodo DOI\]`.
- The Conformome data licence. `docs/PILOT_REPORT.md` has not chosen one. The archive may carry a CC BY 4.0 pointer; the manuscript keeps the placeholder until the author confirms.
- The code licence, until a root `LICENSE` exists. Adding MIT `Copyright (c) 2026 Matthew T. J. Halma` is allowed when the root has no licence file. If a different licence file is already there, keep it and report the mismatch with `.zenodo.json`.
- One α-synuclein conflict sentence, until both values are checked against their source pages. `docs/HANDOFF.md` says 33 of 52 conflicts are SASBDB K-to-R mutants at different salt. Do not turn that note into a worked example unless you have checked the two entries.
- Named single-method states. The count is a tag. Name two or three only when `stats.json` gives the molecule and the technique.
- The AI model version in the Acknowledgements.

On the finish path, tag the G-quadruplex counts from `g4.states.*`. On the cut path, the use-case section does not claim curated cation states.

Do not add a "Validation of the mapping" subsection.

Citations stay as pandoc `[@key]` and resolve from `paper/references.csl.json`. Do not run `make_bib.py`. A new reference is a CSL-JSON entry with a DOI, checked against Crossref. If Crossref is unreachable, use `paper/data/crossref_cache.json` and say that the check was skipped.

From `paper/`, in Git Bash:

```
bash build_formatted.sh
```

That writes `out/manuscript.filled.md`, `out/Conformome_ORE_manuscript.docx`, and `out/Conformome_ORE_manuscript.pdf`. If pandoc or xelatex is missing, write the filled markdown, name the missing tool, and do not claim the Word or PDF file exists.

`paper/scripts/lint_manuscript.py` should report 0 errors. Author decisions are warnings. Abstract: 300 words or fewer. Keywords: 8 or fewer.

## 4. Build the data archive

Follow `ZENODO_BRIEF.md` §2–§5 for the file layout, with the licence rule in this file instead of the SPDX allow-list. Implement:

- `scripts/make_data_release.py`
- `scripts/check_release_metadata.py`
- a `zenodo-prep` target in the `Makefile`

`make zenodo-prep` writes `release/` and then runs the checker.

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

`profiles.zip` may contain no entries. Say so in the README when it is empty. Do not invent profiles.

Molecule, state, transition, and model records stay. A mapping that points at excluded evidence keeps the evidence id.

`README.md` is rendered from `zenodo/data-release/README_dataset.md`. Fill corpus totals from `stats.json`. Fill the archived evidence count from `all-records.jsonl`. Leave DOI and `[confirm]` cells. If the frozen release is not 81 proteins and six nucleic acids, change that sentence to the real counts. The script prints every remaining placeholder.

`release/LICENSE` is the CC BY 4.0 legal text. If you cannot download it, write one line pointing at `https://creativecommons.org/licenses/by/4.0/legalcode.txt` and flag that in the PR. That pointer does not decide the manuscript's data-licence placeholder.

Zips use sorted names and a fixed timestamp so a second run is byte-identical. Add a test for that.

Copy `zenodo/data-release/zenodo_data_metadata.json` to `release_meta/zenodo_data_metadata.json` and set the version. The description's counts must match the README, including the archived-versus-corpus distinction. Keep `SOFTWARE_VERSION_DOI` and the ORCID placeholder. The upload script must refuse to run while those remain.

Copy `zenodo/repo-root/.zenodo.json` and `zenodo/repo-root/CITATION.cff` to the repo root and set the version. In `CITATION.cff`, set `date-released` to `2026-10-19` and mark it in the PR as a date the author confirms. Add this line to the repo `README.md`:

```
<!-- zenodo badge: added after first release -->
```

`scripts/check_release_metadata.py` fails, with a list, when any of these is false:

- `.zenodo.json` and `release_meta/zenodo_data_metadata.json` parse as JSON.
- `CITATION.cff` parses as YAML and has `cff-version`, `title`, `authors`, `version`, and `license`.
- The version `0.1.0` is the same in the tag (without `v`), `.zenodo.json`, `CITATION.cff`, the data metadata, the dataset README, and `stats.json`.
- The software licence matches the root `LICENSE`, and the data licence file matches `release/LICENSE`.
- Corpus totals in the README match `stats.json`, and the archived evidence count in the README matches a rescan of `all-records.jsonl`.
- No evidence from a `deny_sources` entry is in `release/`.
- The archive is not empty of evidence while the build contains redistributable records.
- `SHA256SUMS` verifies.

ORCID and DOI placeholders are warnings.

Run `make zenodo-prep` twice. The second `release/` must match the first byte for byte.

## 5. Draft GitHub release, or the command for it

Write `release_meta/release_notes.md` from `stats.json`: protein and nucleic-acid totals separately, which scope you took, the schema 2.0.0 change from protein records to molecule records, the sources that contributed records, the sources left out of the data archive, and one line that the data archive is a separate Zenodo record whose DOI will follow.

Create a draft only, after the tag exists:

```
gh release create v0.1.0 --draft --target <tagged commit> \
  --title "Conformome v0.1.0: pilot release described in the ORE article" \
  --notes-file release_meta/release_notes.md
```

If `gh` cannot create the draft, put that command and the notes in the PR. Do not publish the release. Publishing is what makes Zenodo mint the software DOI.

Do not run `zenodo/data-release/zenodo_upload_data.py`.

## 6. Pull request

Base: `ccr-ebb336f7-3qzi9h`. Head: `paper/ore`.

```
gh pr create --base ccr-ebb336f7-3qzi9h --head paper/ore
```

The description lists, in this order:

1. Which scope you took, finish or cut, and the tag and commit.
2. The corpus counts, and how they differ from the protein-only 81 / 17,522 / 7 sources.
3. On a cut: each manuscript claim you removed, including any of the four missing nucleic acids, RMDB, profiles, the Molecules page, and the cation rule.
4. On a finish: the representative PDB IDs you checked, and any state you left out because the identifier could not be checked.
5. `EXCLUDED.tsv`, and the confirmation that PDB, DisProt and AlphaFold records are in the archive.
6. Open placeholders: ORCID, licences still marked verify, the Conformome data licence, both DOIs, the conflict example, single-method examples, the AI model version, `date-released`.
7. The author's remaining steps:
   1. Confirm the ORCID and the unverified source licences. Change `zenodo/redistribution.yaml` only after that confirmation. Re-run `make zenodo-prep`.
   2. Turn the repo on at zenodo.org → Account → GitHub.
   3. Publish the draft GitHub release. Copy the software version DOI.
   4. Put that DOI into `release_meta/zenodo_data_metadata.json`. Run `ZENODO_TOKEN=… python zenodo/data-release/zenodo_upload_data.py release/`, review the draft on Zenodo, and publish it. Copy the data version DOI.
   5. Put both DOIs into the manuscript and into the dataset README on Zenodo (Edit, which does not create a new version).
   6. After the article is published, add its DOI to both Zenodo records under Related works.

## Done when

- The scope gate is resolved in the manuscript, not only in the PR text.
- `v0.1.0` points at the commit recorded in `paper/out/stats.json`.
- `stats.py --check` and `fill_numbers.py --check` pass against the rebuilt site.
- `out/manuscript.filled.md` has no `\[to be filled: n\]` and no bare corpus count. The author decisions listed above may remain.
- `make zenodo-prep` passes twice with identical `release/` bytes. SMASH-BIO is excluded. PDB evidence is present. Checker warnings are limited to the ORCID and the DOIs.
- The pull request targets `ccr-ebb336f7-3qzi9h`.
- A draft GitHub release exists, or the exact command is in the PR.
- Nothing has been published.
