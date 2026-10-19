"""Audit sampling, blinding, intervals and the fixture review sheet.

Every protein, rule and response in this file is synthetic. Nothing here is written
under audit/, and no review answer is filled in for a real round.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.0.0-paper"
RULE_SECRET = "RULE-HIDDEN-zzz"
STATE_A = "ST-HIDDEN-aaa"
STATE_B = "ST-HIDDEN-bbb"


def _load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sample = _load("audit_sample")
stats = _load("audit_stats")
sheet = _load("audit_sheet")


def _evidence(eid: str, technique: str, source: str, mappings: list[dict], title: str = "Synthetic deposit"):
    return {
        "evidence_id": eid,
        "technique": technique,
        "title": title,
        "construct": {"description": "residues 1-40, synthetic", "labels": ["His-tag"]},
        "conditions": {
            "environment": "in_vitro", "temperature_c": 25, "ph": 7.0, "buffer": "HEPES",
            "salt_mM": 150, "ions": [], "ligands": [], "applied_force_pn": None, "notes": None,
        },
        "observable": {"type": "radius_of_gyration", "value": 2.0, "uncertainty": 0.2, "unit": "nm"},
        "mappings": mappings,
        "provenance": {
            "source": source, "deposit_id": eid, "url": f"https://example.test/{eid}",
            "doi": "10.9999/synthetic", "retrieved": "2026-01-15", "licence": "synthetic — not a real licence",
        },
    }


def _rule(rule: str, state: str) -> dict:
    return {"who": f"rule:{rule}", "state_id": state, "confidence": "high", "justification": "synthetic"}


def _curator(state: str, confidence: str = "high") -> dict:
    return {"who": "curator:synthetic-person", "state_id": state, "confidence": confidence, "justification": "synthetic"}


def _write_protein(root: Path, acc: str, name: str, evidence: list[dict], ambiguous: list[dict], conflicts: list[dict]):
    curation = root / "curation"
    build = root / "build" / acc
    curation.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    (curation / f"{acc}.yaml").write_text(
        f"""uniprot: {acc}
name: {name}
as_of: "2026-01-15"
states:
  - id: {STATE_A}
    name: Open conformation
    basis: observed
    representative_pdb: "9SYN"
    description: Synthetic open form used only in tests.
  - id: {STATE_B}
    name: Closed conformation
    basis: inferred
    description: Synthetic closed form used only in tests.
    assumptions: ["This state exists only inside the audit test fixture."]
    parent: {STATE_A}
""",
        encoding="utf-8",
    )
    mapped = {"evidence": evidence, "ambiguous": ambiguous, "conflicts": conflicts}
    (build / "mapped.json").write_text(json.dumps(mapped), encoding="utf-8")


def _corpus(root: Path) -> None:
    """A small synthetic release. Rule and state ids are deliberately distinctive."""
    proteins = {
        "P37840": "Synthetic synuclein",
        "P0CG48": "Synthetic ubiquitin",
        "P0AEX9": "Synthetic maltose-binding protein",
        "Q8WZ42": "Synthetic titin",
    }
    for acc, name in proteins.items():
        evidence = []
        for i in range(3):
            evidence.append(_evidence(f"EV-{acc}-S{i}", "xray", "RCSB PDB", [_rule("RULE-SMALL", STATE_A)]))
        for i in range(12):
            evidence.append(_evidence(f"EV-{acc}-A{i}", "xray", "RCSB PDB", [_rule(RULE_SECRET, STATE_A)]))
        for i in range(12):
            evidence.append(_evidence(f"EV-{acc}-B{i}", "cryoem", "RCSB PDB", [_rule("RULE-OTHER", STATE_B)]))
        for i in range(4):
            evidence.append(_evidence(f"EV-{acc}-U{i}", "nmr_shifts", "BMRB", []))
        for i in range(2):
            evidence.append(_evidence(f"EV-{acc}-C{i}", "xray", "RCSB PDB", [_curator(STATE_A if i == 0 else STATE_B)]))
        ambiguous = [{"evidence_id": f"EV-{acc}-M{i}", "states": [STATE_A, STATE_B], "rules": ["not-shown"]} for i in range(2)]
        for row in ambiguous:
            evidence.append(_evidence(row["evidence_id"], "saxs_sans", "SASBDB", []))
        conflicts = []
        if acc in {"P37840", "P0CG48"}:
            conflicts.append({
                "conflict_id": f"CF-{STATE_A}-radius_of_gyration-EV-{acc}-C0-EV-{acc}-C1",
                "state_id": STATE_A,
                "observable_type": "radius_of_gyration",
                "unit": "nm",
                "evidence_ids": [f"EV-{acc}-C0", f"EV-{acc}-C1"],
                "values": [1.5, 4.0],
                "uncertainties": [0.1, 0.1],
                "reason": "synthetic disagreement",
            })
        _write_protein(root, acc, name, evidence, ambiguous, conflicts)


def _draw(root: Path, part: str, seed: int, round_id: str, folder: str | None = None, **kwargs):
    return sample.draw_round(
        part=part, round_id=round_id, tag=TAG, seed=seed, reviewer="to-be-assigned",
        build=root / "build", curation=root / "curation",
        dest=root / "rounds" / (folder or round_id),
        commit="fixture-commit", created="2026-01-15", **kwargs,
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_same_seed_is_byte_identical_and_another_seed_differs(tmp_path: Path):
    _corpus(tmp_path)
    _draw(tmp_path, "A", 7, "a7", folder="one", n=20, n_unmapped=5, n_ambiguous=50)
    _draw(tmp_path, "A", 7, "a7", folder="two", n=20, n_unmapped=5, n_ambiguous=50)
    _draw(tmp_path, "A", 8, "a7", folder="three", n=20, n_unmapped=5, n_ambiguous=50)
    first = tmp_path / "rounds" / "one"
    again = tmp_path / "rounds" / "two"
    other = tmp_path / "rounds" / "three"
    assert _read(first / "sample.jsonl") == _read(again / "sample.jsonl")
    assert _read(first / "sheet.html") == _read(again / "sheet.html")
    assert _read(first / "sample.jsonl") != _read(other / "sample.jsonl")


def test_parts_b_and_c_are_reproducible(tmp_path: Path):
    _corpus(tmp_path)
    for part, kwargs in (("B", {}), ("C", {"n": 10})):
        _draw(tmp_path, part, 3, f"{part}-same", folder=f"{part}-1", **kwargs)
        _draw(tmp_path, part, 3, f"{part}-same", folder=f"{part}-2", **kwargs)
        one = tmp_path / "rounds" / f"{part}-1"
        two = tmp_path / "rounds" / f"{part}-2"
        assert _read(one / "sample.jsonl") == _read(two / "sample.jsonl")
        assert _read(one / "sheet.html") == _read(two / "sheet.html")


def test_sheet_hides_the_answer_under_test(tmp_path: Path):
    _corpus(tmp_path)
    _draw(tmp_path, "A", 1, "blind", n=20, n_unmapped=5)
    _draw(tmp_path, "C", 1, "blind-c", n=10)
    key = [json.loads(line) for line in _read(tmp_path / "rounds" / "blind" / "key.jsonl").splitlines()]
    html_text = _read(tmp_path / "rounds" / "blind" / "sheet.html")
    assert any(row["rule_id"] == RULE_SECRET for row in key)
    assert RULE_SECRET not in html_text
    assert "RULE-SMALL" not in html_text
    assert "RULE-OTHER" not in html_text
    assert "not-shown" not in html_text
    cards = re.findall(r"<article class=\"card\".*?</article>", html_text, flags=re.DOTALL)
    assert cards
    for card in cards:
        assert STATE_A not in card
        assert STATE_B not in card
        assert "rule:" not in card
    conflict_html = _read(tmp_path / "rounds" / "blind-c" / "sheet.html")
    conflict_cards = re.findall(r"<article class=\"card\".*?</article>", conflict_html, flags=re.DOTALL)
    for card in conflict_cards:
        assert STATE_A not in card
        assert "CF-" + STATE_A not in card
    assert STATE_A in html_text  # the export map, outside the cards


def test_stratum_counts_match_the_population(tmp_path: Path):
    _corpus(tmp_path)
    _draw(tmp_path, "A", 4, "counts", n=20, n_unmapped=5, n_ambiguous=50)
    rows = [json.loads(line) for line in _read(tmp_path / "rounds" / "counts" / "sample.jsonl").splitlines()]
    # Four proteins: each has 3 small-rule, 12 + 12 large-rule, 4 unmapped, 2 ambiguous. Curator items are excluded.
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row["stratum_key"], []).append(row)
    populations = {}
    for key, items in grouped.items():
        assert len({item["population"] for item in items}) == 1
        populations[key] = items[0]["population"]
        assert len(items) <= items[0]["population"]
    a1 = {key: value for key, value in populations.items() if key.startswith("A1-")}
    assert sum(a1.values()) == 4 * (3 + 12 + 12)
    assert sum(len(items) for key, items in grouped.items() if key.startswith("A1-")) <= sum(a1.values())
    assert populations["A2"] == 4 * 4
    assert len(grouped["A2"]) == 5
    assert populations["A3"] == 4 * 2
    assert len(grouped["A3"]) == populations["A3"]
    ids = {row["item_id"] for row in rows}
    assert not any("-C0" in item or "-C1" in item for item in ids)


def test_allocate_a1_respects_the_floor_and_the_target():
    take = sample.allocate_a1({"big": 1000, "mid": 20, "tiny": 3}, 200)
    assert take["tiny"] == 3
    assert 10 <= take["mid"] <= 20
    assert sum(take.values()) == 200


def test_choose_proteins_covers_the_four_groups():
    curated = {acc for _, accs in sample.GROUPS for acc in accs}
    for seed in (1, 2, 99):
        chosen = sample.choose_proteins(curated, __import__("random").Random(seed))
        assert 8 <= len(chosen) <= 10
        assert len(chosen) == len(set(chosen))
        assert "P37840" in chosen
        for _, accs in sample.GROUPS:
            assert set(chosen) & set(accs)


def test_weighted_precision_matches_unweighted_when_strata_match():
    rows = []
    for rule, flags in (("r1", [1, 0, 1, 1]), ("r2", [0, 1, 1, 1])):
        for flag in flags:
            rows.append({"rule_id": rule, "population": 40, "correct": flag})
    weighted = stats._weighted_precision(rows)
    unweighted = sum(row["correct"] for row in rows) / len(rows)
    assert weighted == pytest.approx(unweighted)
    uneven = [{"rule_id": "r1", "population": 100, "correct": 1} for _ in range(10)]
    uneven += [{"rule_id": "r2", "population": 100, "correct": flag} for flag in (1, 0)]
    assert stats._weighted_precision(uneven) == pytest.approx(0.75)
    assert sum(row["correct"] for row in uneven) / len(uneven) != pytest.approx(0.75)


def test_kappa_and_wilson_match_known_values():
    pairs = [("A", "A"), ("A", "A"), ("A", "B"), ("B", "B"), ("B", "B"), ("B", "A"), ("C", "C"), ("C", "C"), ("C", "A"), ("A", "C")]
    # po = 0.6, pe = 0.34, kappa = 0.26 / 0.66
    assert stats.cohens_kappa(pairs) == pytest.approx(0.26 / 0.66)
    low, high = stats.wilson(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-4)
    assert high == pytest.approx(0.7634, abs=1e-4)


def _round(part: str, items: list[dict], responses: list[dict], seed: int = 1, tag: str = TAG) -> dict:
    return {
        "meta": {"round_id": f"fixture-{part}", "part": part, "tag": tag, "commit": "fixture", "seed": seed},
        "sample": items,
        "key": [item["key"] for item in items if item.get("key")],
        "responses": responses,
    }


def _item(item_id: str, kind: str, key: dict | None, answer: str, *, verdict: str = "", note: str = "",
          confidence: str = "high", coverage: str = "yes") -> tuple[dict, dict]:
    item = {
        "item_id": item_id,
        "kind": kind,
        "stratum": (key or {}).get("stratum", ""),
        "response_answer": answer,
    }
    if key:
        key = dict(key, item_id=item_id)
        item["key"] = key
    response = {
        "round_id": "fixture", "item_id": item_id, "answer": answer, "confidence": confidence,
        "coverage": coverage, "verdict": verdict, "note": note, "answered_at": "2026-01-15T00:00:00Z",
    }
    return item, response


def test_stats_on_a_synthetic_fixture(tmp_path: Path):
    a_items, a_responses = [], []
    # Two equal strata, so weighted and unweighted precision match: 3/4 and 3/4.
    flags = {RULE_SECRET: [STATE_A, STATE_A, STATE_A, "none"], "RULE-BAD": ["none", "none", "none", "none"]}
    for rule, answers in flags.items():
        state = STATE_A if rule == RULE_SECRET else STATE_B
        for index, answer in enumerate(answers):
            item, response = _item(
                f"EV-{rule}-{index}", "evidence",
                {"part": "A", "stratum": "A1", "population": 20, "assigned_state": state, "rule_id": rule,
                 "technique": "xray", "source": "RCSB PDB", "accession": "P37840", "curator_confidence": None},
                answer, coverage="partial" if answer == state else "yes",
            )
            a_items.append(item)
            a_responses.append(response)
    item, response = _item(
        "EV-miss", "evidence",
        {"part": "A", "stratum": "A2", "population": 40, "assigned_state": None, "rule_id": None,
         "technique": "xray", "source": "RCSB PDB", "accession": "P37840"},
        STATE_A,
    )
    a_items.append(item)
    a_responses.append(response)
    item, response = _item(
        "EV-amb", "evidence",
        {"part": "A", "stratum": "A3", "population": 4, "assigned_state": None, "rule_id": None,
         "technique": "xray", "source": "RCSB PDB", "accession": "P37840"},
        "cannot tell",
    )
    a_items.append(item)
    a_responses.append(response)

    labels = [("A", "A"), ("A", "A"), ("A", "B"), ("B", "B"), ("B", "B"), ("B", "A"), ("C", "C"), ("C", "C"), ("C", "A"), ("A", "C")]
    b_items, b_responses = [], []
    for index, (reference, answer) in enumerate(labels):
        item, response = _item(
            f"EV-B-{index}", "evidence",
            {"part": "B", "stratum": "B-mapped", "population": 10, "assigned_state": reference, "rule_id": None,
             "technique": "xray", "source": "RCSB PDB", "accession": "P37840", "curator_confidence": "high"},
            answer, note="reviewer note" if reference != answer else "",
        )
        b_items.append(item)
        b_responses.append(response)
    item, response = _item("states:P37840", "states", None, "yes")
    b_items.append(item)
    b_responses.append(response)

    c_spec = [
        ("CF-1", True, "real"),
        ("CF-2", True, "cannot tell"),
        ("CF-3", False, "real"),
        ("CF-4", False, "construct"),
    ]
    c_items, c_responses = [], []
    for item_id, focus, verdict in c_spec:
        item, response = _item(
            item_id, "conflict",
            {"part": "C", "stratum": "C-P37840" if focus else "C-rest", "population": 2, "p37840": focus,
             "assigned_state": None, "rule_id": None, "accession": "P37840" if focus else "P0CG48"},
            "", verdict=verdict,
        )
        c_items.append(item)
        c_responses.append(response)

    rounds = [
        _round("A", a_items, a_responses, seed=11),
        _round("B", b_items, b_responses, seed=12),
        _round("C", c_items, c_responses, seed=13),
    ]
    result = stats.evaluate(rounds)
    precision = result["audit"]["rules"]["precision"]["estimate"]
    assert precision == pytest.approx(0.375)  # strata of equal size: 3/4 and 0/4
    assert result["audit"]["rules"]["cannot_tell"] == 0
    assert any(row["id"] == "RULE-BAD" for row in result["audit"]["revision_candidates"])
    assert result["audit"]["unmapped"]["miss_rate"]["k"] == 1
    assert result["audit"]["unmapped"]["missed_mappings"]["population"] == 40
    assert result["audit"]["agreement"]["overall"]["kappa"]["estimate"] == pytest.approx(0.26 / 0.66)
    assert result["audit"]["states_defined_differently"]["n_yes"] == 1
    assert result["audit"]["disagreements"]
    assert result["audit"]["conflicts"]["real_share"]["k"] == 2
    assert result["audit"]["conflicts"]["real_share"]["n"] == 3
    out = tmp_path / "out"
    figs = tmp_path / "figs"
    stats.write_outputs(result, out, figs)
    assert (out / "audit_stats.json").is_file()
    assert "Revision candidates" in _read(out / "audit_tables.md")
    assert (figs / "figS1_audit.png").stat().st_size > 1000
    fixed = Path.home() / "AppData" / "Local" / "Temp" / "figS1_audit.png"
    fixed.write_bytes((figs / "figS1_audit.png").read_bytes())


def test_stats_rejects_mixed_tags_missing_rows_and_unknown_ids(tmp_path: Path):
    item, response = _item(
        "EV-1", "evidence",
        {"part": "A", "stratum": "A2", "population": 1, "assigned_state": None, "rule_id": None, "accession": "P37840"},
        "none",
    )
    complete = _round("A", [item], [response], tag=TAG)
    other = _round("A", [item], [response], tag="v0.2.0-paper")
    with pytest.raises(stats.AuditError, match="mix tags"):
        stats.evaluate([complete, other])
    missing = _round("A", [item, {**item, "item_id": "EV-2", "key": {**item["key"], "item_id": "EV-2"}}], [response])
    with pytest.raises(stats.AuditError, match="missing responses"):
        stats.evaluate([missing])
    unknown = dict(response, item_id="EV-NO")
    bad = _round("A", [item], [response, unknown])
    with pytest.raises(stats.AuditError, match="not in the sample"):
        stats.evaluate([bad])

    audit = tmp_path / "audit"
    done = audit / "done"
    done.mkdir(parents=True)
    (done / "round.yaml").write_text("part: A\ntag: v0.0.0-paper\nseed: 1\nround_id: done\n", encoding="utf-8")
    (done / "sample.jsonl").write_text(json.dumps({"item_id": "EV-1", "kind": "evidence"}) + "\n", encoding="utf-8")
    (done / "key.jsonl").write_text(json.dumps(item["key"]) + "\n", encoding="utf-8")
    with (done / "responses.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stats.RESPONSE_COLUMNS))
        writer.writeheader()
        writer.writerow(response)
    skipped = audit / "skipped"
    skipped.mkdir()
    (skipped / "round.yaml").write_text("part: B\ntag: v9.9.9-paper\nseed: 2\nround_id: skipped\n", encoding="utf-8")
    (skipped / "sample.jsonl").write_text("{}\n", encoding="utf-8")
    loaded = stats.load_completed(audit)
    assert [row["meta"]["round_id"] for row in loaded] == ["done"]


def test_untagged_head_is_refused():
    proc = subprocess.run(
        [sys.executable, "-I", "scripts/audit_sample.py", "--part", "A", "--tag", TAG,
         "--seed", "1", "--reviewer", "to-be-assigned", "--round-id", "not-drawn"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "not tagged" in proc.stderr


def _browser() -> str | None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def test_playwright_answers_three_items_and_exports_csv(tmp_path: Path):
    browser_path = _browser()
    if browser_path is None:
        pytest.fail("Chrome or Edge is required to check the review sheet")
    playwright_sync = pytest.importorskip("playwright.sync_api")
    evidence = [
        _evidence("EV-SYN-1", "xray", "RCSB PDB", [_rule(RULE_SECRET, STATE_A)]),
        _evidence("EV-SYN-2", "xray", "RCSB PDB", [_rule(RULE_SECRET, STATE_A)]),
        _evidence("EV-SYN-3", "cryoem", "RCSB PDB", [_rule(RULE_SECRET, STATE_B)]),
    ]
    _write_protein(tmp_path, "P37840", "Synthetic synuclein", evidence, [], [])
    _draw(tmp_path, "A", 5, "sheet", n=10, n_unmapped=0, n_ambiguous=0)
    html_path = tmp_path / "rounds" / "sheet" / "sheet.html"
    sample_rows = [json.loads(line) for line in _read(tmp_path / "rounds" / "sheet" / "sample.jsonl").splitlines()]
    assert len(sample_rows) == 3
    requests = []
    with playwright_sync.sync_playwright() as play:
        browser = play.chromium.launch(executable_path=browser_path, headless=True)
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});")
        page.on("request", lambda request: requests.append(request.url))
        page.goto(html_path.as_uri())
        cards = page.locator("article.card")
        assert cards.count() == 3
        cards.nth(0).locator("input[value='0']").check()
        cards.nth(0).locator("input[value='high']").check()
        cards.nth(0).locator("input[value='yes']").check()
        cards.nth(0).locator("textarea").fill("hello, \"world\"")
        cards.nth(1).locator("input[value='none']").check()
        cards.nth(2).locator("input[value='cannot-tell']").check()
        with page.expect_download() as download_info:
            page.locator("#export").click()
        download = download_info.value
        target = tmp_path / "responses.csv"
        download.save_as(str(target))
        browser.close()
    assert all(url.startswith(("file:", "blob:", "data:")) for url in requests)
    with target.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == list(stats.RESPONSE_COLUMNS)
    assert len(rows) == 3
    by_id = {row["item_id"]: row for row in rows}
    first = sample_rows[0]
    assert by_id[first["item_id"]]["answer"] == first["choice_ids"][0]
    assert by_id[first["item_id"]]["note"] == 'hello, "world"'
    assert by_id[sample_rows[1]["item_id"]]["answer"] == "none"
    assert by_id[sample_rows[2]["item_id"]]["answer"] == "cannot tell"
    assert RULE_SECRET not in html_path.read_text(encoding="utf-8")
