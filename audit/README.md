# Conformome mapping audit

This folder holds blinded review rounds for one frozen pilot release. A round asks whether the mappings in that release are right. It does not change them.

There are three kinds of round:

- **Part A.** Did the rules send each entry to the right state, and did they miss entries they should have mapped?
- **Part B.** Given the same state definitions, does a second curator map entries the same way as the first?
- **Part C.** Is a flagged conflict a real disagreement, or an artefact of construct, conditions, method or a data error?

You do the judging. The scripts only draw the sample, show the sheet and add up the answers afterwards.

## Before you open a sheet

Work on the release named in `round.yaml` (`tag` and `commit`). Do not edit anything under `curation/` while a round is open. If an entry looks wrong, record it in that round's `findings.md`. Corrections wait for the next release, so the paper can report the error rate of the release it describes.

Each round folder contains:

| File | What it is |
| --- | --- |
| `round.yaml` | part, release tag, commit, seed, reviewer id |
| `sample.jsonl` | the entries in the sheet |
| `key.jsonl` | the mapping under test |
| `sheet.html` | the review sheet |
| `responses.csv` | your answers, after you export them |
| `findings.md` | one issue per line, item id first |

## Blinding is your responsibility

The sheet does not show the state a rule assigned, the state curator 1 assigned, or the rule id. Those answers are in `key.jsonl`, in the same folder.

Nothing stops you from opening `key.jsonl`. If you open it, the round is no longer blind. Leave `key.jsonl` and the mapping sections of the curation files unread until you have exported `responses.csv`.

Item order was shuffled with the seed in `round.yaml`. Drawing the same release with the same seed again reproduces the same sheet.

## Answer a round

1. Open `sheet.html` in a browser. Double-click it, or drag it into Chrome or Edge. It loads nothing from the network. It still works if the browser will not store data locally.
2. Read the state definitions at the top. Each card links back to them. The protein name links to that protein's page in the frozen site (`site/dist`). Build the site for this release first if the link does not open.
3. Answer every card.
   - Parts A and B: pick a state, **none of these states**, or **cannot tell**. Then pick a confidence and say whether the construct covers the region that defines the state.
   - Part B also asks, once per protein, whether you would define the states differently.
   - Part C shows two entries side by side. Pick one verdict: real, construct, conditions, method, data error, or cannot tell.
4. A note is optional. Use it when the choice needs a reason.
5. Keys **1–9** select a choice on the current card. **n** moves to the next card. Click a card to make it current.
6. The header shows how many cards are answered. **Show unanswered** hides the rest.
7. Click **Export responses.csv** and save the file into this round's folder, replacing nothing else. The columns are `round_id, item_id, answer, confidence, coverage, verdict, note, answered_at`.
8. Add any problems to `findings.md`, one per line, starting with the item id.
9. Commit `responses.csv` and `findings.md`. Do not commit edits under `curation/`.

Part A is about 30–40 items an hour once the definitions are familiar. A round of about 200 rule-mapped items, plus the unmapped and ambiguous samples, is roughly a day of careful reading, not an afternoon.

## Who reviews which round

The author reviews part A and part C, or asks one other person who did not write the rule that is under test. Part B needs a second curator who did not write the state definitions. The author decides whether that person is a co-author or is acknowledged. Leave that decision as a placeholder in `paper/ore_submission.md` until it is made.

Put the reviewer's id in `round.yaml` when you know it. Rounds drawn before anyone is assigned use `to-be-assigned`. Do not invent a name.

## Drawing a round

This is for the person running the audit, not for the reviewer.

The sample is taken from the tagged release, with the repository checked out at that tag:

```text
git checkout vX.Y.Z-paper
python -I scripts/audit_sample.py --part A --tag vX.Y.Z-paper --seed 1 --reviewer to-be-assigned --round-id 2026-10-rules-r1
python -I scripts/audit_sample.py --part B --tag vX.Y.Z-paper --seed 2 --reviewer to-be-assigned --round-id 2026-10-curator-r1
python -I scripts/audit_sample.py --part C --tag vX.Y.Z-paper --seed 3 --reviewer to-be-assigned --round-id 2026-10-conflicts-r1
```

`--n` sets the part A rule sample (default 200) or the part C sample from proteins other than P37840 (default 50). Part A also takes 100 unmapped items and up to 50 ambiguous items. Part B takes 8–10 curated proteins across the four pilot groups, always including P37840.

The command refuses to draw unless `HEAD` is exactly that tag. A round stays tied to the tag in its `round.yaml`. If the release is tagged again, draw a new round. Do not pool rounds from different tags.

After `responses.csv` exists for the rounds you want to report:

```text
python -I scripts/audit_stats.py
```

That writes `paper/out/audit_stats.json`, `paper/out/audit_tables.md` and `paper/figures/figS1_audit.pdf` (plus png and tiff). Rounds that have no `responses.csv` are skipped. A file that misses an item, or names an item that was not in the sample, stops the script. The paper text is updated only after real answers exist. Do not type audit numbers by hand.
