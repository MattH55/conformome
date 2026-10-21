# Depositing Conformome v0.1.0 on Zenodo

Two records, in this order: **software** (GitHub release, archived by Zenodo automatically) and **data** (the deposit folder, uploaded as a dataset). The data record cites the software DOI, so the software goes first. Nothing here is published yet; every step that mints a DOI is yours to click.

## What is ready

| Item | Where | State |
| --- | --- | --- |
| Data deposit, unpacked | `release/` (12 files incl. `SHA256SUMS`) | built by `make zenodo-prep`; `make validate` 0 errors |
| Data deposit, zipped | `conformome-data-0.1.0.zip` (2.4 MB) | SHA-256 `740c8684699e41e445e9724fb177b25c9a4d7c5e1be841164e1b2ac929294aff` |
| Dataset README | `release/README.md` | counts filled from the build; DOIs still placeholders |
| Data metadata | `release_meta/zenodo_data_metadata.json` | description matches the build; ORCID and software DOI placeholders |
| GitHub release notes | `release_meta/release_notes.md` | counts from the build |
| Software metadata | `.zenodo.json`, `CITATION.cff` at repo root | version 0.1.0; ORCID placeholder; dates say 2026-10-19 |
| Paper numbers | `paper/out/stats.json` | same build; `release.tag` empty until v0.1.0 exists |

Counts in the deposit: 87 molecules (81 proteins, 5 RNA, 1 DNA); 17,677 evidence entries in the corpus, 15,089 archived, 64 RMDB reactivity profiles in `profiles.zip`; 36 curated molecules, 83 states. Excluded: 2,588 SMASH-BIO entries (`release/EXCLUDED.tsv`).

`make zenodo-prep` rebuilds `release/` and the zip from `build/` and then runs `scripts/check_release_metadata.py`. Two runs give byte-identical files. The checker fails on any mismatch between the build, the README, the metadata, the licences and the checksums; ORCID and DOI placeholders are warnings only.

## Before you start (10 min)

1. **ORCID.** Replace `0000-0000-0000-0000` in `.zenodo.json`, `CITATION.cff` and `release_meta/zenodo_data_metadata.json`. The upload script refuses to run while the placeholder remains.
2. **Dates.** Set `publication_date` in `.zenodo.json` and `date-released` in `CITATION.cff` to the day you publish the GitHub release.
3. **Licence strings marked "(verify)".** BMRB (786 records, stored as `CC0 1.0 (verify)`) and SASBDB (224 records, `CC BY 4.0 (verify)`) are *in* the archive because those strings are on the allow-list in `zenodo/redistribution.yaml`. Confirm each against the source's own terms. If one does not allow redistribution, remove its line from `redistribution.yaml`; the records then move to `EXCLUDED.tsv` on the next run.
4. **Tag and rebuild.** Commit the edits above, create the tag locally (do not push it; the GitHub release creates the public one):
   ```
   git tag v0.1.0
   .venv/Scripts/python -I paper/scripts/stats.py --check
   make zenodo-prep
   ```
   `stats.py --check` passes only when HEAD is tagged and the site pages agree; `release.tag` is then `v0.1.0`. If a later change moves any count, delete the local tag, rebuild, and tag again.

## 1. Software record (15 min)

1. Log in at https://zenodo.org with GitHub. Under *Account → GitHub* (https://zenodo.org/account/settings/github/), click *Sync now* if needed and switch **MattH55/conformome** to **On**.
2. Create the GitHub release as a draft on the tagged commit (the one in `paper/out/stats.json` → `release.commit`):
   ```
   gh release create v0.1.0 --draft --target <release.commit> \
     --title "Conformome v0.1.0: pilot release described in the ORE article" \
     --notes-file release_meta/release_notes.md
   ```
3. Open the draft on GitHub, check the notes, and click **Publish release**. Zenodo archives only published releases, not bare tags.
4. After a minute or two, the record appears under *Account → GitHub*. Check creator, ORCID, licence (MIT), version and the AntiHelix grant (859853). If the grant is missing, add it on the record with *Edit → Funding → European Commission → 859853*.
5. Copy the **version DOI** (not the concept DOI). Call it `SOFTWARE`.

If nothing appears after 10 minutes, the usual cause is invalid `.zenodo.json`: validate it, fix, delete the GitHub release (keep the tag), and publish again.

## 2. Data record (20 min)

1. Put `SOFTWARE` into `release_meta/zenodo_data_metadata.json` in place of `SOFTWARE_VERSION_DOI`. Leave `release/README.md` for now; it is edited once the data DOI is reserved (step 4).
2. Create a Zenodo token at *Account → Applications → Personal access tokens* with `deposit:write` and `deposit:actions`.
3. Create the draft deposit (no publishing):
   ```
   export ZENODO_TOKEN=...
   .venv/Scripts/python zenodo/data-release/zenodo_upload_data.py release/ --metadata release_meta/zenodo_data_metadata.json
   ```
   The script prints the draft's link and its reserved DOI. Call that `DATA`.
   - For a dry run first: make a separate account and token at https://sandbox.zenodo.org and add `--sandbox`.
   - Web form instead: https://zenodo.org/uploads/new, upload the 12 files from `release/`, click *Reserve DOI*, and fill the form from `release_meta/zenodo_data_metadata.json` (type Dataset, licence CC BY 4.0, funding European Commission 859853, related work "Is compiled by" → `SOFTWARE`).
4. Put `DATA` and `SOFTWARE` into `release/README.md` (the two `doi:10.5281/zenodo.*_DOI` lines) and re-upload that one file to the draft. Do not re-run `make zenodo-prep` after this, or the README reverts to placeholders.
5. In the draft, check title, creator, version `0.1.0`, licence, keywords and the related identifiers. *Preview*, then **Publish**.

## 3. Manuscript

- **Data availability:** `Zenodo: Conformome pilot release v0.1.0: conformational-state evidence records for proteins and nucleic acids. https://doi.org/10.5281/zenodo.DATA` under CC BY 4.0.
- **Software availability:** source code https://github.com/MattH55/conformome; archived code at time of publication https://doi.org/10.5281/zenodo.SOFTWARE; licence MIT.
- The manuscript's corpus numbers come from `paper/out/stats.json` through `paper/scripts/fill_numbers.py --write`; never type one by hand.

## 4. After the article is out

Edit both Zenodo records and add the article DOI under *Related works* ("Is described by" for software, "Is supplement to" for data). Editing metadata keeps the same DOI.

## Notes

- `release/`, the zip and `paper/out/` are git-ignored on purpose; `release_meta/` is committed.
- Optional download failures in this build: SASBDB returns 404 for 30 proteins (no SASBDB search page for them) and Q9BYF1; see `data/raw/download_failures.json`.
- On Windows with OneDrive, `make download` can hit a transient file lock on `data/MANIFEST.json`; `write_json` now writes atomically and retries, so a run no longer dies on it.
