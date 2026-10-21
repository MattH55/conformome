"""Turn completed audit rounds into paper/out/audit_stats.json, tables and Fig. S1.

Rounds with no responses.csv are skipped. A responses file that misses a sampled
item, or that names an item that was not sampled, is an error. Rounds that have
responses must all carry the same release tag.

`cannot tell` is left out of every denominator and reported as a count.
Proportions use a Wilson interval. Weighted precision and Cohen's kappa use a
bootstrap over items, except part B's overall kappa, which is a bootstrap over
proteins. No response under audit/ is invented here.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
Z = 1.959963984540054
N_BOOT = 2000
VERDICTS = ("real", "construct", "conditions", "method", "data_error", "cannot tell")
RESPONSE_COLUMNS = ("round_id", "item_id", "answer", "confidence", "coverage", "verdict", "note", "answered_at")


class AuditError(Exception):
    pass


def wilson(k: int, n: int, z: float = Z) -> tuple[float | None, float | None]:
    """95% Wilson score interval. Returns (None, None) when n is 0."""
    if n <= 0:
        return None, None
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa. `none` is an ordinary category. Undefined for an empty list."""
    if not pairs:
        return None
    labels = sorted({label for pair in pairs for label in pair})
    index = {label: i for i, label in enumerate(labels)}
    matrix = np.zeros((len(labels), len(labels)), dtype=float)
    for left, right in pairs:
        matrix[index[left], index[right]] += 1
    n = matrix.sum()
    po = np.trace(matrix) / n
    pe = float((matrix.sum(axis=1) * matrix.sum(axis=0)).sum() / (n * n))
    if math.isclose(pe, 1.0):
        return 1.0 if math.isclose(po, 1.0) else 0.0
    return float((po - pe) / (1 - pe))


def confusion(pairs: list[tuple[str, str]]) -> tuple[list[str], list[list[int]]]:
    labels = sorted({label for pair in pairs for label in pair})
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for left, right in pairs:
        matrix[index[left]][index[right]] += 1
    return labels, matrix


def _proportion(k: int, n: int, method: str = "wilson") -> dict:
    low, high = wilson(k, n) if method == "wilson" else (None, None)
    return {
        "estimate": None if n == 0 else k / n,
        "low": low,
        "high": high,
        "k": k,
        "n": n,
        "method": method,
    }


def _boot_interval(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    low, high = np.quantile(np.asarray(values, dtype=float), [0.025, 0.975])
    return float(low), float(high)


def _cannot(value: str) -> bool:
    return (value or "").strip().lower() in {"cannot tell", "cannot_tell", "cannot-tell"}


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_responses(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        names = [name.strip() for name in (reader.fieldnames or [])]
        missing = [column for column in RESPONSE_COLUMNS if column not in names]
        if missing:
            raise AuditError(f"{path}: responses.csv is missing columns {', '.join(missing)}")
        rows = []
        for row in reader:
            rows.append({column: (row.get(column) or "").strip() for column in RESPONSE_COLUMNS})
    return rows


def _check_responses(sample: list[dict], responses: list[dict], round_id: str) -> None:
    sample_ids = [row["item_id"] for row in sample]
    seen = []
    for row in responses:
        if row["item_id"] not in sample_ids:
            raise AuditError(f"{round_id}: response item id not in the sample: {row['item_id']}")
        seen.append(row["item_id"])
    if len(seen) != len(set(seen)):
        raise AuditError(f"{round_id}: duplicate item id in responses.csv")
    missing = [item_id for item_id in sample_ids if item_id not in set(seen)]
    if missing:
        raise AuditError(f"{round_id}: missing responses for {len(missing)} items, first {missing[0]}")


def load_completed(audit_dir: Path) -> list[dict]:
    """Load every round that has a responses.csv. Skip rounds that have none."""
    if not audit_dir.is_dir():
        raise AuditError(f"no audit directory at {audit_dir}")
    rounds = []
    for path in sorted(p for p in audit_dir.iterdir() if p.is_dir()):
        if not (path / "round.yaml").is_file() or not (path / "responses.csv").is_file():
            continue
        meta = yaml.safe_load((path / "round.yaml").read_text(encoding="utf-8")) or {}
        meta["round_id"] = meta.get("round_id") or path.name
        sample = _read_jsonl(path / "sample.jsonl")
        key = _read_jsonl(path / "key.jsonl")
        responses = _read_responses(path / "responses.csv")
        _check_responses(sample, responses, meta["round_id"])
        rounds.append({"meta": meta, "sample": sample, "key": key, "responses": responses})
    if not rounds:
        raise AuditError(f"no completed rounds (responses.csv) under {audit_dir}")
    tags = {row["meta"].get("tag") for row in rounds}
    if len(tags) != 1:
        raise AuditError("refuses to mix tags: " + ", ".join(sorted(str(tag) for tag in tags)))
    return rounds


def _join(rnd: dict) -> list[dict]:
    keys = {row["item_id"]: row for row in rnd["key"]}
    responses = {row["item_id"]: row for row in rnd["responses"]}
    joined = []
    for item in rnd["sample"]:
        item_id = item["item_id"]
        response = responses[item_id]
        if item.get("kind") == "evidence" and not response["answer"]:
            raise AuditError(f"{rnd['meta']['round_id']}: blank answer for {item_id}")
        if item.get("kind") == "conflict" and not response["verdict"]:
            raise AuditError(f"{rnd['meta']['round_id']}: blank verdict for {item_id}")
        joined.append({
            "item": item,
            "key": keys.get(item_id),
            "response": response,
            "part": rnd["meta"]["part"],
            "round_id": rnd["meta"]["round_id"],
        })
    return joined


def _weighted_precision(rows: list[dict]) -> float | None:
    """sum over rules of (N_rule / N) * (correct_rule / n_rule), N and n taken once per rule."""
    by_rule: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_rule[row["rule_id"]].append(row)
    if not by_rule:
        return None
    populations = {rule: rows_[0]["population"] for rule, rows_ in by_rule.items()}
    total = sum(populations.values())
    if total <= 0:
        return None
    score = 0.0
    for rule, rows_ in by_rule.items():
        score += (populations[rule] / total) * (sum(row["correct"] for row in rows_) / len(rows_))
    return score


def _bootstrap_values(stat, rows: list, rng: np.random.Generator) -> list[float]:
    if not rows:
        return []
    out = []
    n = len(rows)
    for _ in range(N_BOOT):
        pick = rng.integers(0, n, size=n)
        value = stat([rows[int(i)] for i in pick])
        if value is not None:
            out.append(value)
    return out


def _part_a(rows: list[dict], rng: np.random.Generator) -> dict:
    a1 = [row for row in rows if row["key"] and row["key"].get("stratum") == "A1"]
    decisive = []
    cannot = 0
    for row in a1:
        answer = row["response"]["answer"]
        if _cannot(answer):
            cannot += 1
            continue
        assigned = row["key"]["assigned_state"]
        decisive.append({
            "rule_id": row["key"]["rule_id"],
            "assigned_state": assigned,
            "technique": row["key"].get("technique"),
            "source": row["key"].get("source"),
            "population": row["key"]["population"],
            "correct": answer == assigned,
            "wrong_state": answer not in {assigned, "none"},
            "should_be_none": answer == "none",
            "coverage": row["response"]["coverage"],
        })
    estimate = _weighted_precision(decisive)
    low, high = _boot_interval(_bootstrap_values(_weighted_precision, decisive, rng))
    precision = {
        "estimate": estimate, "low": low, "high": high,
        "k": sum(row["correct"] for row in decisive), "n": len(decisive),
        "method": "bootstrap", "weighted": True,
    }
    by_rule = {}
    for rule in sorted({row["rule_id"] for row in decisive}):
        group = [row for row in decisive if row["rule_id"] == rule]
        k = sum(row["correct"] for row in group)
        by_rule[rule] = _proportion(k, len(group))
        by_rule[rule]["population"] = group[0]["population"]
    by_state = {}
    for state in sorted({row["assigned_state"] for row in decisive}):
        group = [row for row in decisive if row["assigned_state"] == state]
        by_state[state] = _proportion(sum(row["correct"] for row in group), len(group))
    def grouped(field: str) -> dict:
        out = {}
        for name in sorted({row[field] for row in decisive if row[field]}):
            group = [row for row in decisive if row[field] == name]
            out[name] = _proportion(sum(row["correct"] for row in group), len(group))
        return out
    correct = [row for row in decisive if row["correct"]]
    covered = [row for row in correct if row["coverage"] in {"yes", "partial", "no", "unknown"}]
    partial = sum(row["coverage"] in {"partial", "no"} for row in covered)
    a2 = [row for row in rows if row["key"] and row["key"].get("stratum") == "A2"]
    a2_cannot = sum(_cannot(row["response"]["answer"]) for row in a2)
    a2_decisive = [row for row in a2 if not _cannot(row["response"]["answer"])]
    misses = sum(row["response"]["answer"] != "none" for row in a2_decisive)
    a3 = [row for row in rows if row["key"] and row["key"].get("stratum") == "A3"]
    a3_cannot = sum(_cannot(row["response"]["answer"]) for row in a3)
    a3_decisive = [row for row in a3 if not _cannot(row["response"]["answer"])]
    resolved = sum(row["response"]["answer"] not in {"none", ""} for row in a3_decisive)
    population = a2[0]["key"]["population"] if a2 else 0
    miss = _proportion(misses, len(a2_decisive))
    missed = {
        "estimate": None if miss["estimate"] is None else miss["estimate"] * population,
        "low": None if miss["low"] is None else miss["low"] * population,
        "high": None if miss["high"] is None else miss["high"] * population,
        "population": population,
    }
    candidates = []
    for rule, stats in by_rule.items():
        if stats["high"] is not None and stats["high"] < 0.8:
            candidates.append({"kind": "rule", "id": rule, **{k: stats[k] for k in ("estimate", "low", "high", "k", "n")}})
    for state, stats in by_state.items():
        if stats["high"] is not None and stats["high"] < 0.8:
            candidates.append({"kind": "state", "id": state, **{k: stats[k] for k in ("estimate", "low", "high", "k", "n")}})
    return {
        "rules": {
            "precision": precision,
            "by_rule": by_rule,
            "by_state": by_state,
            "by_technique": grouped("technique"),
            "by_source": grouped("source"),
            "wrong_state": _proportion(sum(row["wrong_state"] for row in decisive), len(decisive)),
            "should_be_none": _proportion(sum(row["should_be_none"] for row in decisive), len(decisive)),
            "cannot_tell": cannot,
        },
        "unmapped": {"miss_rate": miss, "missed_mappings": missed, "cannot_tell": a2_cannot},
        "ambiguous": {"resolvable": _proportion(resolved, len(a3_decisive)), "cannot_tell": a3_cannot},
        "coverage": {"partial_or_no": _proportion(partial, len(covered))},
        "revision_candidates": candidates,
    }


def _pairs_for(rows: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for row in rows:
        if row["key"] is None or row["key"].get("assigned_state") is None and row["key"].get("stratum") != "B-unmapped":
            continue
        answer = row["response"]["answer"]
        if _cannot(answer):
            continue
        reference = row["key"]["assigned_state"]
        pairs.append((reference, answer))
    return pairs


def _part_b(rounds: list[dict], rng: np.random.Generator) -> dict:
    rows = [row for rnd in rounds for row in _join(rnd) if rnd["meta"]["part"] == "B"]
    evidence = [row for row in rows if row["item"].get("kind") == "evidence"]
    cannot = sum(_cannot(row["response"]["answer"]) for row in evidence)
    by_protein: dict[str, list] = defaultdict(list)
    for row in evidence:
        if row["key"] is None:
            continue
        by_protein[row["key"]["accession"]].append(row)
    per_protein = {}
    disagreements = []
    for acc in sorted(by_protein):
        decisive_rows = [row for row in by_protein[acc] if not _cannot(row["response"]["answer"])]
        pairs = _pairs_for(decisive_rows)
        labels, matrix = confusion(pairs)
        kappa = cohens_kappa(pairs)
        kappas = []
        if pairs:
            n = len(pairs)
            for _ in range(N_BOOT):
                pick = rng.integers(0, n, size=n)
                value = cohens_kappa([pairs[int(i)] for i in pick])
                if value is not None:
                    kappas.append(value)
        low, high = _boot_interval(kappas)
        agreed = sum(left == right for left, right in pairs)
        per_protein[acc] = {
            "agreement": _proportion(agreed, len(pairs)),
            "kappa": {"estimate": kappa, "low": low, "high": high, "n": len(pairs), "method": "bootstrap"},
            "labels": labels,
            "confusion": matrix,
        }
        for row in decisive_rows:
            reference = row["key"]["assigned_state"]
            answer = row["response"]["answer"]
            if reference != answer:
                disagreements.append({
                    "item_id": row["item"]["item_id"],
                    "accession": acc,
                    "curator_1": reference,
                    "curator_2": answer,
                    "note": row["response"]["note"],
                })
    protein_pairs = [_pairs_for([row for row in by_protein[acc] if not _cannot(row["response"]["answer"])]) for acc in sorted(by_protein)]
    protein_pairs = [pairs for pairs in protein_pairs if pairs]
    overall_pairs = [pair for pairs in protein_pairs for pair in pairs]
    overall_kappa = cohens_kappa(overall_pairs)
    boot = []
    if protein_pairs:
        n = len(protein_pairs)
        for _ in range(N_BOOT):
            pick = rng.integers(0, n, size=n)
            pooled = [pair for i in pick for pair in protein_pairs[int(i)]]
            value = cohens_kappa(pooled)
            if value is not None:
                boot.append(value)
    low, high = _boot_interval(boot)
    agreed = sum(left == right for left, right in overall_pairs)
    by_confidence = {}
    for level in ("high", "medium", "low"):
        group = [
            row for row in evidence
            if row["key"] and row["key"].get("curator_confidence") == level and not _cannot(row["response"]["answer"])
        ]
        pairs = _pairs_for(group)
        by_confidence[level] = _proportion(sum(left == right for left, right in pairs), len(pairs))
    differently = []
    asked = 0
    for row in rows:
        if row["item"].get("kind") != "states":
            continue
        asked += 1
        if row["response"]["answer"] == "yes":
            differently.append(row["item"]["item_id"].split(":", 1)[1])
    return {
        "agreement": {
            "overall": {
                "percent": _proportion(agreed, len(overall_pairs)),
                "kappa": {"estimate": overall_kappa, "low": low, "high": high, "n": len(overall_pairs), "method": "bootstrap-proteins"},
                "cannot_tell": cannot,
            },
            "by_protein": per_protein,
            "by_confidence": by_confidence,
        },
        "states_defined_differently": {"n_yes": len(differently), "n_asked": asked, "accessions": differently},
        "disagreements": disagreements,
    }


def _verdict_table(rows: list[dict]) -> dict:
    decisive = [row for row in rows if not _cannot(row["response"]["verdict"])]
    counts = {verdict: 0 for verdict in VERDICTS}
    for row in rows:
        verdict = row["response"]["verdict"]
        if verdict in counts:
            counts[verdict] += 1
        elif _cannot(verdict):
            counts["cannot tell"] += 1
    shares = {verdict: _proportion(counts[verdict], len(rows)) for verdict in VERDICTS}
    real = _proportion(sum(row["response"]["verdict"] == "real" for row in decisive), len(decisive))
    return {"n": len(rows), "cannot_tell": counts["cannot tell"], "shares": shares, "real_share": real}


def _part_c(rows: list[dict]) -> dict:
    conflicts = [row for row in rows if row["item"].get("kind") == "conflict"]
    focus = [row for row in conflicts if row["key"] and row["key"].get("p37840")]
    rest = [row for row in conflicts if row not in focus]
    pooled = _verdict_table(conflicts)
    return {
        "real_share": pooled["real_share"],
        "p37840": _verdict_table(focus),
        "rest": _verdict_table(rest),
        "cannot_tell": pooled["cannot_tell"],
    }


def evaluate(rounds: list[dict]) -> dict:
    tags = {row["meta"].get("tag") for row in rounds}
    if len(tags) != 1:
        raise AuditError("refuses to mix tags: " + ", ".join(sorted(str(tag) for tag in tags)))
    for rnd in rounds:
        _check_responses(rnd["sample"], rnd["responses"], rnd["meta"].get("round_id", ""))
    rng = np.random.Generator(np.random.PCG64(min(int(row["meta"]["seed"]) for row in rounds)))
    joined = [row for rnd in rounds for row in _join(rnd)]
    part_a = _part_a([row for row in joined if row["part"] == "A"], rng) if any(row["meta"]["part"] == "A" for row in rounds) else None
    part_b = _part_b([row for row in rounds if row["meta"]["part"] == "B"], rng) if any(row["meta"]["part"] == "B" for row in rounds) else None
    part_c = _part_c([row for row in joined if row["part"] == "C"]) if any(row["meta"]["part"] == "C" for row in rounds) else None
    audit = {
        "rules": None if part_a is None else part_a["rules"],
        "unmapped": None if part_a is None else part_a["unmapped"],
        "ambiguous": None if part_a is None else part_a["ambiguous"],
        "coverage": None if part_a is None else part_a["coverage"],
        "revision_candidates": [] if part_a is None else part_a["revision_candidates"],
        "agreement": None if part_b is None else part_b["agreement"],
        "states_defined_differently": None if part_b is None else part_b["states_defined_differently"],
        "disagreements": [] if part_b is None else part_b["disagreements"],
        "conflicts": part_c,
    }
    return {
        "tag": next(iter(tags)),
        "rounds": [
            {
                "round_id": row["meta"].get("round_id"),
                "part": row["meta"].get("part"),
                "tag": row["meta"].get("tag"),
                "commit": row["meta"].get("commit"),
                "seed": row["meta"].get("seed"),
                "n_items": len(row["sample"]),
                "n_responses": len(row["responses"]),
            }
            for row in rounds
        ],
        "audit": audit,
    }


def _fmt(stats: dict | None) -> str:
    if not stats or stats.get("estimate") is None:
        return "n=0"
    low = stats.get("low")
    high = stats.get("high")
    interval = " " if low is None else f" ({low:.3f}, {high:.3f})"
    return f"{stats['estimate']:.3f}{interval}  k={stats.get('k')} n={stats.get('n')}"


def render_tables(stats: dict) -> str:
    audit = stats["audit"]
    lines = [
        f"# Audit tables for {stats['tag']}",
        "",
        "Intervals are 95%. Wilson intervals are used for simple proportions. Weighted precision and kappa use a bootstrap (2,000 resamples): over items, and over proteins for the overall part-B kappa. `cannot tell` is excluded from denominators.",
        "",
        "A rule or a state is a revision candidate when its 95% interval lies entirely below 0.8.",
        "",
    ]
    rules = audit.get("rules") or {}
    if rules:
        lines += ["## Part A. Rule precision", "", f"Overall, weighted by rule population: {_fmt(rules['precision'])}.", "",
                  f"Wrong state: {_fmt(rules['wrong_state'])}. Should be none: {_fmt(rules['should_be_none'])}. Cannot tell: {rules['cannot_tell']}.", "",
                  "| Rule | Population | Precision |", "| --- | --- | --- |"]
        for rule, row in sorted(rules["by_rule"].items(), key=lambda item: (-item[1]["population"], item[0])):
            lines.append(f"| {rule} | {row['population']} | {_fmt(row)} |")
        lines += ["", "| Technique | Precision |", "| --- | --- |"]
        for name, row in rules["by_technique"].items():
            lines.append(f"| {name} | {_fmt(row)} |")
        lines += ["", "| Source | Precision |", "| --- | --- |"]
        for name, row in rules["by_source"].items():
            lines.append(f"| {name} | {_fmt(row)} |")
        unmapped = audit["unmapped"]
        missed = unmapped["missed_mappings"]
        lines += ["", "## Part A. Unmapped and ambiguous items", "",
                  f"Miss rate among unmapped items: {_fmt(unmapped['miss_rate'])}.",
                  f"Extrapolated missed mappings in the release: {missed['estimate']} ({missed['low']}, {missed['high']}) of {missed['population']}.",
                  f"Ambiguous items the reviewer could place: {_fmt(audit['ambiguous']['resolvable'])}.",
                  f"Correctly mapped items whose construct coverage was partial or no: {_fmt(audit['coverage']['partial_or_no'])}.",
                  ""]
    candidates = audit.get("revision_candidates") or []
    lines += ["## Revision candidates", ""]
    if candidates:
        lines += ["| Kind | Id | Precision |", "| --- | --- | --- |"]
        for row in candidates:
            lines.append(f"| {row['kind']} | {row['id']} | {_fmt(row)} |")
    else:
        lines.append("None. No rule or state has its 95% interval entirely below 0.8.")
    lines.append("")
    agreement = audit.get("agreement")
    if agreement:
        lines += ["## Part B. Second curator", "",
                  f"Overall agreement: {_fmt(agreement['overall']['percent'])}.",
                  f"Overall kappa (bootstrap over proteins): {_fmt(agreement['overall']['kappa'])}.",
                  f"Cannot tell: {agreement['overall']['cannot_tell']}.", "",
                  "| Protein | Agreement | Kappa |", "| --- | --- | --- |"]
        for acc, row in agreement["by_protein"].items():
            lines.append(f"| {acc} | {_fmt(row['agreement'])} | {_fmt(row['kappa'])} |")
        lines += ["", "### Agreement by curator-1 confidence", ""]
        for level, row in agreement["by_confidence"].items():
            lines.append(f"- {level}: {_fmt(row)}")
        differently = audit["states_defined_differently"]
        lines += ["", f"Proteins where curator 2 would define the states differently: {differently['n_yes']} of {differently['n_asked']} ({', '.join(differently['accessions']) or 'none'}).",
                  "", "### Confusion matrices", "", "Rows are curator 1. Columns are curator 2, in the label order shown.", ""]
        for acc, row in agreement["by_protein"].items():
            lines.append(f"{acc}: labels {', '.join(row['labels']) or 'none'}")
            for matrix_row in row["confusion"]:
                lines.append("  " + " ".join(str(value) for value in matrix_row))
            lines.append("")
        lines += ["### Disagreements", "", "These rows are for findings.md. The note is the reviewer's own note.", "",
                  "| Item | Protein | Curator 1 | Curator 2 | Note |", "| --- | --- | --- | --- | --- |"]
        for row in audit["disagreements"]:
            lines.append(f"| {row['item_id']} | {row['accession']} | {row['curator_1']} | {row['curator_2']} | {row['note']} |")
        lines.append("")
    conflicts = audit.get("conflicts")
    if conflicts:
        lines += ["## Part C. Conflicts", "", f"Share judged real (cannot tell excluded): {_fmt(conflicts['real_share'])}.", ""]
        for label, key in (("P37840", "p37840"), ("Rest of the release", "rest")):
            block = conflicts[key]
            lines += [f"### {label} (n={block['n']})", "", "| Verdict | Share of all answers |", "| --- | --- |"]
            for verdict in VERDICTS:
                lines.append(f"| {verdict} | {_fmt(block['shares'][verdict])} |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _import_figstyle():
    scripts = REPO / "paper" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import figstyle
    return figstyle


def write_figure(stats: dict, dest_dir: Path) -> None:
    figstyle = _import_figstyle()
    import matplotlib.pyplot as plt
    audit = stats["audit"]
    rules = (audit.get("rules") or {}).get("by_rule") or {}
    ordered = sorted(rules, key=lambda rule: (-rules[rule]["population"], rule))
    proteins = (audit.get("agreement") or {}).get("by_protein") or {}
    conflicts = audit.get("conflicts") or {}
    height = (40 + max(len(ordered), 1) * 5 + max(len(proteins), 1) * 5 + 40) * figstyle.MM
    fig, axes = plt.subplots(3, 1, figsize=(figstyle.COL2, max(height, 120 * figstyle.MM)), constrained_layout=True)

    ax = axes[0]
    if ordered:
        y = np.arange(len(ordered))
        est = [rules[rule]["estimate"] or 0 for rule in ordered]
        low = [0 if rules[rule]["low"] is None else max(0.0, rules[rule]["estimate"] - rules[rule]["low"]) for rule in ordered]
        high = [0 if rules[rule]["high"] is None else max(0.0, rules[rule]["high"] - rules[rule]["estimate"]) for rule in ordered]
        ax.barh(y, est, color=figstyle.BLUE, xerr=[low, high], ecolor=figstyle.INK, capsize=2, height=0.7)
        ax.set_yticks(y, ordered)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.axvline(0.8, color=figstyle.GREY, lw=0.6)
    else:
        ax.text(0.5, 0.5, "No part A responses", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Precision")
    figstyle.panel_letter(ax, "A")

    ax = axes[1]
    names = list(proteins)
    if names:
        y = np.arange(len(names))
        est = [proteins[name]["kappa"]["estimate"] or 0 for name in names]
        low = [0 if proteins[name]["kappa"]["low"] is None else max(0.0, (proteins[name]["kappa"]["estimate"] or 0) - proteins[name]["kappa"]["low"]) for name in names]
        high = [0 if proteins[name]["kappa"]["high"] is None else max(0.0, proteins[name]["kappa"]["high"] - (proteins[name]["kappa"]["estimate"] or 0)) for name in names]
        ax.barh(y, est, color=figstyle.BLUE_DARK, xerr=[low, high], ecolor=figstyle.INK, capsize=2, height=0.7)
        ax.set_yticks(y, names)
        ax.invert_yaxis()
    else:
        ax.text(0.5, 0.5, "No part B responses", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Cohen's kappa")
    figstyle.panel_letter(ax, "B")

    ax = axes[2]
    colours = [figstyle.BLUE_DARK, figstyle.BLUE, figstyle.BLUE_LIGHT, figstyle.BLUE_PALE, "#d98b3a", figstyle.GREY]
    series = []
    for key, label in (("p37840", "P37840"), ("rest", "Rest")):
        block = conflicts.get(key)
        if block and block["n"]:
            series.append((label, [block["shares"][verdict]["estimate"] or 0 for verdict in VERDICTS]))
    if series:
        x = np.arange(len(series))
        bottom = np.zeros(len(series))
        for verdict, colour in zip(VERDICTS, colours):
            heights = [row[1][VERDICTS.index(verdict)] for row in series]
            ax.bar(x, heights, bottom=bottom, color=colour, width=0.55, label=verdict)
            bottom += heights
        ax.set_xticks(x, [row[0] for row in series])
        ax.set_ylim(0, 1)
        ax.legend(frameon=False, fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    else:
        ax.text(0.5, 0.5, "No part C responses", ha="center", va="center", transform=ax.transAxes)
    ax.set_ylabel("Share of verdicts")
    figstyle.panel_letter(ax, "C")
    dest_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest_dir / "figS1_audit.pdf", facecolor="white")
    rgb = figstyle._flatten(fig)
    rgb.save(dest_dir / "figS1_audit.png", dpi=(300, 300))
    rgb.save(dest_dir / "figS1_audit.tiff", compression="tiff_lzw", dpi=(300, 300))
    plt.close(fig)


def write_outputs(stats: dict, out_dir: Path, figure_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n",
    )
    (out_dir / "audit_tables.md").write_text(render_tables(stats), encoding="utf-8", newline="\n")
    write_figure(stats, figure_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarise completed Conformome audit rounds")
    parser.add_argument("--audit", type=Path, default=REPO / "audit")
    parser.add_argument("--out", type=Path, default=REPO / "paper" / "out")
    parser.add_argument("--figures", type=Path, default=REPO / "paper" / "figures")
    args = parser.parse_args(argv)
    try:
        stats = evaluate(load_completed(args.audit))
        write_outputs(stats, args.out, args.figures)
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out / 'audit_stats.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
