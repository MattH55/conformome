# Conformome: Zenodo archives for the paper release. Build brief for a coding agent

You are working in the `matth55/conformome` repository. Your job is to prepare the two Zenodo records the ORE article cites:
- the **software** record, which Zenodo creates automatically from a published GitHub release;
- the **data** record, which is uploaded as a dataset.

You prepare everything so that the author only has to check and click *Publish*.

The human-readable version of this procedure, with the reasons behind each step, is `zenodo/ZENODO_INSTRUCTIONS.md`. The templates are in `zenodo/`:
- `repo-root/.zenodo.json`
- `repo-root/CITATION.cff`
- `data-release/zenodo_data_metadata.json`
- `data-release/README_dataset.md`
- `data-release/zenodo_upload_data.py`

Work on a branch (`release/zenodo`) and open a PR when §7 passes.

## 0. Preconditions: stop if any fails

- `NUCLEIC_ACIDS_BRIEF.md` is merged and its tests pass.
- The paper release is frozen as described in `paper/BRIEF.md` §1, and `paper/out/stats.json` records its tag and commit.
- `make ingest map models site` on that commit reproduces `stats.json` exactly.

If any of these fails, report it and stop. The archives must match the numbers in the article.

## 1. Rules

1. **Do not publish anything.** Publishing on Zenodo mints a permanent DOI. The author does it.
   - Create the GitHub release as a **draft** only. Zenodo archives only when a release is *published*, so a draft is safe.
   - Run the data upload script without `--publish`. If you have no token, don't upload at all and leave the folder ready.
2. **Never invent metadata.** Leave ORCID, licences and DOIs as placeholders until the author supplies them, and list them in the PR. In particular:
   - no fake ORCID;
   - no guessed licence for BMRB, SASBDB, RMDB or SMASH-BIO.
3. **Redistribute only what the licence allows** (§3).
4. **Keep versions consistent.** The same version string must appear in the git tag, `.zenodo.json`, `CITATION.cff`, the data metadata, the dataset README and `stats.json`.

## 2. Software record files

1. **Copy the templates to the repo root.** Copy `zenodo/repo-root/.zenodo.json` and `zenodo/repo-root/CITATION.cff`, then set:
   - `version` to the paper release version (e.g. `0.1.0`, without the `v`);
   - `date-released` in `CITATION.cff` to the planned release date, as a placeholder the author confirms;
   - creators and ORCID as in the template. If the author has given an ORCID in the PR conversation or in `paper/ore_submission.md`, use it. Otherwise leave `0000-0000-0000-0000` and fail the check in §5 with a clear message.
2. **Add an MIT `LICENSE`** at the repo root if one is missing: "Copyright (c) 2026 Matthew T. J. Halma". If a different licence file already exists, do not replace it. Report the mismatch with `.zenodo.json` instead.
3. **Add `.zenodo.json` keys if relevant.** Use `"related_identifiers"` to point to the data DOI once it exists. Until then, leave the template as it is.
4. **README badge:** add a placeholder line `<!-- zenodo badge: added after first release -->`.

## 3. Data release: `scripts/make_data_release.py`

Write a script that assembles `release/` from the frozen build outputs:

```
release/
  all-records.jsonl        filtered (see below)
  molecules.zip            molecules/<molecule_id>.json, filtered
  profiles.zip             profiles/<evidence_id>.json, filtered
  schemas.zip              schemas/*.json
  techniques.yaml
  curation.zip             curation/*.yaml (draft files included; status field kept)
  manifest.json            raw-input manifest
  CHANGELOG.md             schema changelog
  README.md                rendered from zenodo/data-release/README_dataset.md
  LICENSE                  CC BY 4.0 legal code (see below)
  SHA256SUMS               checksums of every file above
```

**Licence filter.**
- Keep an evidence record, and any profile it references, only if its `provenance.licence` is on an allow-list in `zenodo/redistribution.yaml`. Start the allow-list with exactly: `CC0-1.0`, `CC-BY-4.0`.
- Every other value counts as **not redistributable**. That includes null, "unknown", "varies by project" and "[to be confirmed]".
- Molecule, state, transition and model records are Conformome's own and are always kept. Mapping records referring to excluded evidence keep the evidence ID, so the site link still works.
- Write `release/EXCLUDED.tsv` with three columns: source, licence value, number of records excluded. Print the same table. When the author confirms a source licence, they add it to `redistribution.yaml` and re-run.

**README rendering.**
- Fill the totals in the template from `stats.json`, using the keys of `NUCLEIC_ACIDS_BRIEF.md` §8 and `paper/BRIEF.md` §2.
- Fill the source-terms table from the licences actually recorded in the release.
- Leave the DOIs and `[confirm]` cells for the author. List them at the end of the script's output.

**LICENSE.** If CC BY 4.0 is chosen, the legal code must be included in full. If the build has no network access, don't download it: leave `LICENSE` with a one-line pointer to https://creativecommons.org/licenses/by/4.0/legalcode.txt and flag it in the PR.

**Determinism.** Zips are written with sorted entries and fixed timestamps, so that two runs produce byte-identical archives. Add a test that checks this.

## 4. Data metadata

- Copy `zenodo/data-release/zenodo_data_metadata.json` to `release_meta/zenodo_data_metadata.json`, then set the version.
- Fill the description's numbers from `stats.json`. The template wording names 81 proteins and six nucleic acids; check this against the release.
- Keep `SOFTWARE_VERSION_DOI` and the ORCID placeholders. The upload script refuses to run while they remain, which is intended.

## 5. Checks: `scripts/check_release_metadata.py`

Fail with a clear list of problems if any of the following is not true:
- `.zenodo.json` and `release_meta/zenodo_data_metadata.json` parse as JSON;
- `CITATION.cff` parses as YAML and has `cff-version`, `title`, `authors`, `version` and `license`;
- the version is identical in all the places listed in §1.4;
- the licence in `.zenodo.json` matches the `LICENSE` file, and the data licence matches `release/LICENSE`;
- the release totals in the README and the metadata description equal `stats.json`;
- no file in `release/` contains evidence whose licence is outside the allow-list (re-scan, don't trust the filter);
- `SHA256SUMS` verifies.

ORCID and DOI placeholders produce **warnings**, not failures, so the PR can be reviewed before the author fills them in.

Add a `make zenodo-prep` target that runs `make_data_release.py` and then `check_release_metadata.py`.

## 6. GitHub draft release

With `gh`, create a **draft** release for the paper tag:

```bash
gh release create v0.1.0 --draft --target <paper commit> \
  --title "Conformome v0.1.0: pilot release described in the ORE article" \
  --notes-file release_meta/release_notes.md
```

Generate `release_notes.md` from `stats.json`:
- the totals (proteins and nucleic acids separately);
- the schema 2.0.0 change from protein to molecule records;
- the new sources;
- a line saying the data are archived separately on Zenodo, with the DOI to follow.

If `gh` is not authenticated, write the command and notes into the PR instead.

**Do not publish the release.** Publishing is what makes Zenodo mint the software DOI, and the author does it after checking `.zenodo.json` on GitHub.

## 7. Done when

- [ ] `make zenodo-prep` runs on the frozen commit. `release/` is complete and identical on a second run, and the checks pass with warnings only for ORCID and DOIs.
- [ ] `EXCLUDED.tsv` lists every source left out and why.
- [ ] A draft GitHub release exists, or the command for it is in the PR.
- [ ] The PR description gives the author's remaining steps, in order:
  1. Confirm the ORCID and the source licences, and update `redistribution.yaml`. Re-run `make zenodo-prep`.
  2. Turn the repo on at zenodo.org → Account → GitHub.
  3. Publish the draft GitHub release. Copy the software **version DOI**.
  4. Put that DOI into `release_meta/zenodo_data_metadata.json`. Run `ZENODO_TOKEN=… python3 zenodo/data-release/zenodo_upload_data.py release/`, review the draft on Zenodo, and publish it. Copy the data **version DOI**.
  5. Put both DOIs into the manuscript (Data availability and Software availability) and into the dataset README on Zenodo (*Edit*, which does not create a new version).
  6. After the article is published, add its DOI to both records under *Related works*.
