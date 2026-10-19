# Conformome mapping audit — build brief for a coding agent

You are working in the `matth55/conformome` repository. This brief adds an **audit** of the frozen pilot release. Its results are reported in the ORE paper (see `paper/BRIEF.md`), and it answers the question reviewers will ask first: *how do you know the mappings are right?*

The audit has three parts:

| Part | Question | Who does the judging |
| --- | --- | --- |
| A. Rule audit | How often does a curated rule map an item to the right state, and how often does it miss one? | 1 reviewer (the author or a second curator), blind to the rule's answer |
| B. Second curator | Does an independent curator, given the same state definitions, map items the same way? | a second curator, blind to curator 1 |
| C. Conflict audit | Are flagged conflicts real disagreements or artefacts? | 1 reviewer |

Your job is the tooling: sampling, blind review sheets, ingesting the answers, the statistics, and the paper outputs. **You do not do the judging.** Never fill in a review answer, not even as a test fixture committed to `audit/`. Use `tests/fixtures/` with obviously synthetic data.

Work on a branch (`audit/pilot`) and open a PR when §8 passes.

## 1. Invariants

1. **Audit the frozen tag.** Every sample is drawn from the release that `paper/BRIEF.md` §1 tags (`v0.x.0-paper`). Record the tag and commit in each round's `round.yaml`. If the release is re-tagged, existing rounds stay valid only for their own tag. `audit_stats.py` refuses to mix tags.
2. **Blind.** A reviewer must never see the answer under test:
   - not the state the rule assigned (part A);
   - not curator 1's mapping (part B);
   - not the rule that produced the item's mapping (both).
   The sheets show the evidence item and the protein's state definitions only. Item order is shuffled with the round's seed.
3. **Seeded and reproducible.** Every sample is drawn with a seed stored in `round.yaml`. Re-running `audit_sample.py` with the same tag and seed must produce byte-identical sheets.
4. **Don't fix during the audit.** Errors found are logged as issues (`audit/<round>/findings.md`), not corrected in `curation/`. Corrections go into the next release, so the paper reports the error rate of the release it describes.
5. **No new dependencies** beyond those in `paper/requirements.txt`, plus `scipy` if you need it for intervals (or implement Wilson and bootstrap intervals in numpy).

## 2. Layout

```
audit/
  README.md                 how to run a round, for reviewers (plain language)
  <round_id>/               e.g. 2026-11-rules-r1
    round.yaml              part, tag, commit, seed, reviewer id, sample spec, created
    sample.jsonl            the items drawn (ids + everything the sheet shows), no answers
    key.jsonl               the answers under test (rule state, curator-1 state) — never shown in sheets
    sheet.html              the review sheet (§4)
    responses.csv           exported from sheet.html by the reviewer, then committed
    findings.md             free-text issues, one per line, item id first
scripts/audit_sample.py     draw a round
scripts/audit_sheet.py      build sheet.html from sample.jsonl
scripts/audit_stats.py      responses + key -> paper/out/audit_stats.json, tables, figure
```

`key.jsonl` sits in the same folder, so the reviewer could open it. Blinding relies on the reviewer not doing so. Say this in `audit/README.md`. Do not pretend it is enforced.

## 3. Sampling (`audit_sample.py`)

`python -I scripts/audit_sample.py --part A|B|C --tag v0.x.0-paper --seed N --reviewer ID [--n ...]`

**Part A: rule audit.** The population is every evidence item on a curated protein. Draw three strata:

- **A1, rule-mapped items:** precision. Stratify by rule. Take `max(10, proportional share)` per rule, capped at the rule's size, for a total of about 200 (default `--n 200`). Rules matching fewer than 10 items are taken whole.
- **A2, unmapped items:** missed mappings. Take a simple random sample of 100 items that no rule or assignment mapped and that are not ambiguous.
- **A3, ambiguous items:** all of them if there are 50 or fewer, else 50 at random.

Curator assignments are excluded from part A, because they *are* the reference. Record the stratum and its population size on every sampled item, so that `audit_stats.py` can weight back to the population.

**Part B: second curator.** Pick 8–10 curated proteins, chosen by seed but stratified across the four pilot groups (folding models, large conformational changes, mechanical, disordered/aggregating), with α-synuclein always included. For each protein, take every mapped item when the total is 60 or fewer. Otherwise take 60, stratified by curator-1 state and by technique. Add 15 unmapped items per protein, so the curator has a real "none of these" choice.

**Part C: conflict audit.** Take every conflict on P37840, plus a random sample of 50 conflicts from the rest of the release (fewer if there are fewer). Stratify by observable.

## 4. Review sheet (`audit_sheet.py` → `sheet.html`)

A single self-contained HTML file that works offline. Keep markup, CSS and JS inline with no external requests. Open it from disk.

**What each item card shows:**
- the protein (name, accession, link to its Conformome page in the frozen build);
- the evidence item: technique, source, deposit ID with a link to the source page, entry title, construct (residue range, mutations, tags), conditions, observable with value ± σ and unit, and DOI;
- the protein's **state definitions**: name, basis, description, representative PDB or assumptions, and parent. These come from `curation/<acc>.yaml`, with the mapping and rule sections stripped out.

**What the reviewer answers:**
- **Parts A and B:**
  - state: one of the protein's states, `none` or `cannot tell`;
  - confidence: high, medium or low;
  - residue coverage: does the entry cover the region that defines the state? yes, partial, no or unknown;
  - a free-text note.
- **Part C** shows both entries side by side and asks for a verdict:
  - `real` (a genuine disagreement);
  - `construct` (different constructs);
  - `conditions` (conditions differ in a way the schema doesn't capture);
  - `method` (the same observable means different things by method, e.g. Rg from SAXS versus MD);
  - `data_error` (an error in the source or in ingestion);
  - `cannot tell`.

  It also asks for a note.

**Behaviour:**
- Progress is saved in `localStorage`, wrapped in try/catch, and keyed by round id. The sheet must still work if storage is unavailable.
- An "Export responses.csv" button downloads the answers. The columns are `round_id, item_id, answer, confidence, coverage, verdict, note, answered_at`.
- The sheet shows progress (answered / total) and lets the reviewer filter to unanswered items.
- Keyboard shortcuts 1–9 pick a state, and `n` moves to the next item. Several hundred items have to be practical to get through.

Check the sheet by opening it in Playwright, answering three items, exporting, and parsing the CSV in a test. Run this check on a synthetic fixture round, not a real one.

## 5. Statistics (`audit_stats.py`)

Read `round.yaml`, `key.jsonl` and `responses.csv` for every round on the paper tag. Write `paper/out/audit_stats.json`, `paper/out/audit_tables.md` and `paper/figures/figS1_audit.{pdf,png,tiff}`.

Report a 95% interval for every proportion: Wilson for simple proportions, a bootstrap over items (or over proteins for part B) otherwise. Exclude `cannot tell` from the denominators, and report its count alongside.

**Part A:**
- `audit.rules.precision`: the share of A1 items where the reviewer's state equals the rule's state. Report it overall (weighted by stratum population) and per rule, per technique and per source.
- `audit.rules.wrong_state` and `audit.rules.should_be_none`: how the errors split.
- `audit.unmapped.miss_rate`: the share of A2 items the reviewer placed in a state. Extrapolate to an estimated count of missed mappings in the release, with an interval.
- `audit.ambiguous.resolvable`: the share of A3 items the reviewer could place.
- `audit.coverage.partial_or_no`: the share of correctly mapped items whose construct does not cover the state-defining region. This feeds the residue-coverage point reviewers will raise.

**Part B:**
- **Item-level agreement between curator 1 and curator 2:** percentage agreement and Cohen's κ, overall and per protein. Include `none` as a category.
- **Confidence-stratified agreement:** does agreement rise with curator-1 confidence?
- **Confusion matrices** per protein, and a list of the disagreements for `findings.md`.
- **Whether curator 2 would define the states differently.** Ask this once per protein in the sheet, as a yes/no plus a note. Report the count.

**Part C:**
- Verdict shares for P37840 and for the rest of the release.
- `audit.conflicts.real_share` with its interval.

Rules and states whose precision interval falls below 0.8 are listed in `audit_tables.md` as candidates for revision in the next release.

**Figure S1:** (A) precision per rule with intervals, ordered by rule size; (B) agreement between the two curators per protein (κ with interval); (C) conflict verdicts as stacked bars, P37840 versus the rest. Use `figstyle.py`.

## 6. Paper integration

Do this after rounds have responses. Before then, ship the tooling only.

- Add `audit_stats.py` to `paper/scripts/build.sh`, after `stats.py`. It writes `audit_stats.json`. `fill_numbers.py` must read both stats files: merge them, with the `audit.` prefix.
- Add a subsection **"Validation of the mapping"** to *Results and use cases*, before the use cases, with tagged numbers only:
  - one paragraph per part saying what was sampled, how, by whom (by role, e.g. "a second curator"), and the headline estimate with its interval;
  - one sentence on what changed in the next release as a result.
- Replace the discussion sentence "The accuracy of rule-based mapping has not been measured…" and the second-curator placeholder with a reference to this subsection.
- Add **Table S1**, from `audit_tables.md`: per-rule precision and the confusion summary. Add **Fig. S1**. Both go into the extended data, built as `out/supplementary.pdf` and included in the Zenodo archive (the audit folder, with responses, is part of the archive).
- Add the reviewer identity to the CRediT notes in `ore_submission.md`: the second curator is either a co-author or acknowledged. The author decides which, so leave a placeholder.
- If a round has no responses yet, the subsection stays out of `manuscript.md`. Do not commit a subsection with placeholder numbers.

## 7. Tests (`tests/test_audit.py`)

- The same tag and seed give identical `sample.jsonl` and `sheet.html`; a different seed gives a different sample.
- No field from `key.jsonl` appears anywhere in `sheet.html`. Test this by searching for each answer state id *in the context of the item card*, plus the rule ids.
- Stratum sizes and population counts sum correctly, and weighted precision equals unweighted precision when every stratum is the same size.
- κ matches a hand-computed example. Wilson intervals match known values.
- `audit_stats.py` fails clearly on mixed tags, on missing responses for an item, and on response item ids that aren't in the sample.

## 8. Done when

- [ ] `audit/README.md` explains in plain language how to open a sheet, answer, export and commit. A reviewer who has never seen the repo can follow it.
- [ ] Rounds A, B and C can each be drawn for the paper tag. Their sheets open offline and export valid CSV. The fixture round passes the Playwright test.
- [ ] `audit_stats.py` runs on the fixture round and produces the JSON, the tables and Fig. S1. You have looked at the figure.
- [ ] Tests pass, and nothing in `audit/` contains fabricated responses.
- [ ] The PR description lists the rounds drawn (with seeds and sizes) and what the author has to do next: who reviews which round, and an estimated time at about 30–40 items per hour for part A.
