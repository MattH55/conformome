# Depositing Conformome v0.1.0 on Zenodo

Two records, in this order: **software** (GitHub release, archived by Zenodo automatically) and **data** (the zip, uploaded as a dataset). The data record cites the software DOI, so the software goes first. Nothing here is published yet; every step that mints a DOI is yours to click.

## What is ready

| Item | Where | State |
| --- | --- | --- |
| Data deposit, unpacked | `release/` (11 files + `SHA256SUMS`) | built from commit `dcf432a`, `make validate` 0 errors |
| Data deposit, zipped | `conformome-data-0.1.0.zip` (2.2 MB) | SHA-256 `ecfff204ef22fa3910dc57436f479c76059cd64e6b816d0766741f4644c1649e` |
| Dataset README | `release/README.md` | counts filled from the build; DOIs and ORCID still placeholders |
| Data metadata | `release_meta/zenodo_data_metadata.json` | description matches the build; ORCID and software DOI placeholders |
| GitHub release notes | `release_meta/release_notes.md` | counts from the build |
| Software metadata | `.zenodo.json`, `CITATION.cff` at repo root | version 0.1.0; ORCID placeholder; dates say 2026-10-19 |

Counts in the deposit: 83 molecules (81 proteins, 1 RNA, 1 DNA); 17,541 evidence entries in the corpus, 14,953 archived; 31 curated molecules, 71 states. Excluded: 2,588 SMASH-BIO entries (`release/EXCLUDED.tsv`).

## Before you start (10 min)

1. **ORCID.** Replace `0000-0000-0000-0000` in `.zenodo.json`, `CITATION.cff` and `release_meta/zenodo_data_metadata.json`. The upload script refuses to run while the placeholder remains.
2. **Dates.** Set `publication_date` in `.zenodo.json` and `date-released` in `CITATION.cff` to the day you publish the GitHub release.
3. **Licence strings marked "(verify)".** BMRB (746 records, stored as `CC0 1.0 (verify)`) and SASBDB (224 records, `CC BY 4.0 (verify)`) are *in* the archive because those strings are on the allow-list in `zenodo/redistribution.yaml`. Confirm each against the source's own terms. If one does not allow redistribution, remove its line from `redistribution.yaml` and re-run step 4; the records then move to `EXCLUDED.tsv`.
4. **Re-run after any of the above** so the README, checksums and zip match:
   ```
   .venv/Scripts/python -I scripts/make_data_release.py
   ```
   Commit the metadata edits.

## 1. Software record (15 min)

1. Log in at https://zenodo.org with GitHub. Under *Account → GitHub* (https://zenodo.org/account/settings/github/), click *Sync now* if needed and switch **MattH55/conformome** to **On**.
2. Create the GitHub release as a draft, targeting the merge commit on the default branch:
   ```
   gh release create v0.1.0 --draft --target 254746b74e24b6a3365e7c4666499a5d75b1219b \
     --title "Conformome v0.1.0: pilot release described in the ORE article" \
     --notes-file release_meta/release_notes.md
   ```
   (`254746b` is the merge of PR #3; its tree is the build commit `dcf432a` plus the merge.)
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
4. Put `DATA` and `SOFTWARE` into `release/README.md` (the two `doi:10.5281/zenodo.*_DOI` lines) and re-upload that one file to the draft. Do not re-run the release script after this, or the README reverts to placeholders.
5. In the draft, check title, creator, version `0.1.0`, licence, keywords and the related identifiers. *Preview*, then **Publish**.

## 3. Manuscript

- **Data availability:** `Zenodo: Conformome pilot release v0.1.0: conformational-state evidence records for proteins and nucleic acids. https://doi.org/10.5281/zenodo.DATA` under CC BY 4.0.
- **Software availability:** source code https://github.com/MattH55/conformome; archived code at time of publication https://doi.org/10.5281/zenodo.SOFTWARE; licence MIT.
- The manuscript's corpus numbers must equal `paper/out/stats.json` from this build (protein scope: 81 proteins, 17,514 entries, 1 conflict, 30 single-method states). `paper/out/stats.json` was regenerated from the same build; `release.tag` is empty until v0.1.0 exists, so re-run `python -I paper/scripts/stats.py` after tagging.

## 4. After the article is out

Edit both Zenodo records and add the article DOI under *Related works* ("Is described by" for software, "Is supplement to" for data). Editing metadata keeps the same DOI.

## Notes

- `release/`, the zip and `paper/out/` are git-ignored on purpose; `release_meta/` is committed.
- The deposit is deterministic: the zips use sorted entries and a fixed timestamp, so a rebuild from the same `build/` gives the same checksums.
- `profiles.zip` is empty (no reactivity profiles in this release); the README says so.
