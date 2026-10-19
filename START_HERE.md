# Conformome ORE submission: order of work for a coding agent

Unzip this kit at the root of `matth55/conformome`. Do the briefs **in this order**. Each depends on the one before it, and each ends with a PR for the author to review before you start the next.

| # | Brief | What it produces | Author action before the next step |
| --- | --- | --- | --- |
| 1 | `NUCLEIC_ACIDS_BRIEF.md` | RNA/DNA support (schema 2.0.0, RMDB, ions, six pilot nucleic acids with **draft** curation) | Review and approve the nucleic-acid curation files |
| 2 | `paper/AUDIT_BRIEF.md` | Audit tooling and review sheets for the frozen release | Do the audit rounds; commit `responses.csv` |
| 3 | `paper/BRIEF.md` | Frozen paper release, `stats.json`, figures 1–4, manuscript build | Check figures and numbers; resolve the remaining placeholders |
| 4 | `ZENODO_BRIEF.md` | Archive files, metadata, checks, draft GitHub release | Publish the GitHub release and the Zenodo data record; supply both DOIs |
| 5 | `paper/BRIEF.md` §5 again | DOIs and licences filled; final `docx` and `pdf` | Submit to ORE |

**Manuscript source.** Use the nucleic-acid version of the manuscript, `paper/manuscript.md`, which replaces the protein-only draft. Its "[to be filled]" placeholders are filled from `stats.json` (`paper/BRIEF.md` §3) as number tags. Convert each placeholder to a tag of the form `123<!--n:key-->`, with the keys from `NUCLEIC_ACIDS_BRIEF.md` §8. Never type numbers by hand.

**Citations and build.** The manuscript uses pandoc citations (`[@key]`) resolved from `paper/references.csl.json`, an export of the author's Zotero library with verified fixes applied. Ignore the `make_bib.py` steps in `paper/BRIEF.md` §6–7. Build with `paper/build_formatted.sh`, which produces the formatted Word file and PDF. Extend `fill_numbers.py` with a `--render` mode that writes `out/manuscript.filled.md` with every tag resolved; until then the script copies the manuscript unchanged. Keep the formatting files in `paper/style/` as they are. When adding references, add CSL-JSON entries with DOIs and verify them against Crossref.

**Rules that apply throughout:**
- Never publish a DOI, push a release or upload a published record. The author does each of these.
- Never invent curation, licences, ORCIDs, references or audit answers.
- Every number in the paper comes from the frozen release.
