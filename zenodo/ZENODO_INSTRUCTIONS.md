# Zenodo records for the Conformome ORE article

The article needs two DOIs:

| Record | Where the DOI goes in the manuscript | Licence |
| --- | --- | --- |
| **Software**: the tagged GitHub release, archived automatically by Zenodo | Software availability: "Archived source code at time of publication" | MIT (OSI-approved, as ORE requires) |
| **Data**: the release files, uploaded as a dataset | Data availability: "Underlying data" | CC BY 4.0 (ORE asks for CC0 or CC BY) |

Do the software record first. The data record points to it.

**Timing.** The nucleic-acid work (`NUCLEIC_ACIDS_BRIEF.md`) must be merged and the release rebuilt **before** either record is made, because both archives must match the numbers in the paper. Make the Zenodo records last, after the paper release is frozen.

Always cite the **version DOI** (the one specific to v0.1.0), not the "concept" DOI that Zenodo also shows, which always resolves to the latest version. ORE wants the exact version the article describes.

---

## 0. Before you start (5 min)

1. Get your ORCID iD: https://orcid.org (free). Put it in place of `0000-0000-0000-0000` in `.zenodo.json`, `CITATION.cff` and `zenodo_data_metadata.json`.
2. Make sure the repo has a `LICENSE` file at its root, containing MIT text with "Copyright (c) 2026 Matthew T. J. Halma". On GitHub, use *Add file → Create new file*, type `LICENSE`, then *Choose a license template → MIT*.
3. Decide the data licence. CC BY 4.0 is the default here. Don't include SMASH-BIO, BMRB, SASBDB or RMDB records in the data archive until you have confirmed their terms; see `README_dataset.md`. RNAcentral supplies identifiers only, so no RNAcentral data are redistributed.

## 1. Software record (GitHub → Zenodo, about 15 min)

1. **Add the metadata files to the repo.** Commit `repo-root/.zenodo.json` and `repo-root/CITATION.cff` to the root of `matth55/conformome`. Zenodo reads `.zenodo.json`, so your name, ORCID, licence and grant appear correctly. Without it, the record is credited to "matth55", as happened with SMASH-BIO.
   - In `CITATION.cff`, set `date-released` to the day you will make the release.
   - Optional check: the CITATION.cff validator at https://citation-file-format.github.io.
2. **Connect GitHub to Zenodo.**
   - Log in at https://zenodo.org with **"Log in with GitHub"**. If you already have a Zenodo account from SMASH-BIO, use it and link GitHub under *Account → Linked accounts*.
   - Go to *Account → GitHub* (https://zenodo.org/account/settings/github/). Click *Sync now* if the repo isn't listed, then switch **matth55/conformome** to **On**.
3. **Make the release on GitHub.**
   - Make sure the commit you release is the one that built the numbers in the paper (the frozen release in `paper/BRIEF.md`).
   - Go to *Releases → Draft a new release*.
     - Tag: `v0.1.0`, created on publish, target `main` or the paper commit.
     - Title: `Conformome v0.1.0: pilot release described in the ORE article`.
     - Notes: one paragraph with the totals from the rebuilt release's `stats.json`: molecules (81 proteins plus the six nucleic acids), evidence entries, curated molecules and states. Mention the schema 2.0.0 change from protein to molecule records.
   - Click **Publish release**. Zenodo only archives *published releases*, not bare tags pushed from the command line.
4. **Collect the DOI.**
   - After a minute or two the record appears under *Account → GitHub* next to the repo. Open it.
   - Check the creator name, ORCID, licence (MIT), version (`v0.1.0`) and grant (AntiHelix 859853).
   - Copy the **version DOI**, e.g. `10.5281/zenodo.1234567`.
   - If something is wrong, click *Edit* on the record, fix it and *Publish* again. Metadata can be edited after publishing; the files cannot.
5. **Add the DOI badge** to the repo README (optional). The record page gives the Markdown for it.

If nothing appears after 10 minutes, check *Account → GitHub* for an error on the release. The usual cause is invalid JSON in `.zenodo.json`; paste it into a JSON validator. Fix the file, delete the GitHub release (keep the tag) and publish the release again.

## 2. Data record (upload, about 20 min)

1. **Put the files to deposit in one folder** (`release/`), taken from the same build as the software release:
   - `all-records.jsonl`
   - `molecules.zip`: zip the `molecules/` folder of per-molecule bundles. The `proteins/` copies kept for back-compatibility don't need to go in.
   - `profiles.zip`: zip the `profiles/` folder of reactivity profiles, leaving out any whose RMDB licence is unconfirmed
   - `schemas.zip`
   - `techniques.yaml`
   - `curation.zip`: zip `curation/*.yaml`. Nucleic-acid files still marked `status: draft` are fine to include, because the README says draft curation is labelled.
   - `manifest.json`
   - `CHANGELOG.md`: the schema changelog from the repo
   - `README.md`: from `README_dataset.md`, with the totals, [confirm] items and DOIs filled in
   - `LICENSE`: the CC BY 4.0 text, from https://creativecommons.org/licenses/by/4.0/legalcode.txt
2. In `zenodo_data_metadata.json`, replace `SOFTWARE_VERSION_DOI` with the DOI from step 1.4 and fill in your ORCID.
3. Choose one way to upload:
   - **Web form, simplest.**
     - Go to https://zenodo.org/uploads/new and upload the files.
     - Click *Reserve DOI*, then put that DOI into README.md and re-upload it.
     - Fill in the form from `zenodo_data_metadata.json`:
       - resource type *Dataset*
       - title, creators with ORCID and affiliation, description, version `0.1.0`
       - licence *Creative Commons Attribution 4.0 International*
       - keywords
       - funding: *European Commission → 859853*
       - related works: "Is compiled by" → the software DOI
     - *Preview*, then *Publish*.
   - **Script.**
     - Create a token at *Account → Applications → Personal access tokens* with the `deposit:write` and `deposit:actions` scopes.
     - Run `export ZENODO_TOKEN=...` and then `python3 zenodo_upload_data.py release/`.
     - The script creates a **draft** and prints its link and reserved DOI. Review the draft in the browser and click *Publish* there.
     - For a trial run, use a separate token from https://sandbox.zenodo.org and add `--sandbox`.
4. Copy the data **version DOI**.

## 3. Put the DOIs in the manuscript

In `manuscript_v3.md` (the version with nucleic acids, or your Word file):

- **Data availability:** `Zenodo: Conformome pilot release v0.1.0: conformational-state evidence records for proteins and nucleic acids. https://doi.org/10.5281/zenodo.<DATA>`, and "Data are available under the terms of the Creative Commons Attribution 4.0 International license (CC-BY 4.0)."
- **Software availability:**
  - Archived source code at time of publication: `https://doi.org/10.5281/zenodo.<SOFTWARE>`
  - License: `MIT License`
- **Software DOI in the reference list (optional):** add the record as a reference too, as was done for SMASH-BIO.

## 4. After the article is published

Edit both Zenodo records and add the article DOI under *Related works*, with the relation "Is described by" (software) or "Is supplement to" (data). Editing metadata does not create a new version.

## Also: fix the SMASH-BIO record

Open https://doi.org/10.5281/zenodo.23455641, click *Edit*, change the creator from "MattH55" to "Halma, Matthew T. J." with your ORCID and affiliation, and change the title to "SMASH-BIO release v1.0.0-paper". Then click *Publish*; this keeps the same DOI. Add the same `.zenodo.json` pattern to the smash-bio repo, so that future releases come out right.

## Notes

- **Funding:** if the `grants` entry in the JSON doesn't attach the AntiHelix grant, add it in the web form: *Funding → European Commission → search "859853"*.
- **Size:** Zenodo allows up to 50 GB per record, so the pilot release is far below the limit.
- **Licence check:** your MIT licence must also appear in the repo's `LICENSE` file, not only in `.zenodo.json`. Reviewers check the repository.
