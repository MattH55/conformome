"""Draw a blinded audit round from a frozen Conformome release.

The command-line entry point refuses to sample unless HEAD is exactly the
requested vX.Y.Z-paper tag. Tests call draw_round() with an explicit corpus
path and commit, so they do not need that tag.

Re-running with the same tag, seed and corpus rewrites byte-identical
sample.jsonl and sheet.html. key.jsonl is written beside them; the sheet
never reads it. Blinding is not enforced on disk.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_sheet  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+-paper$")

# Manuscript use-case lists, kept only where a curation file defines states.
# Filamin, von Willebrand factor, kinesin, dynein, myosins, amyloid precursor
# protein, prion, TDP-43 and huntingtin are named in the same sentences but
# have no state definitions, so a second curator cannot map them.
GROUPS = (
    ("folding", ("P0CG48", "P06654", "P00698", "P00648", "P01053", "P00974", "P00644")),
    ("large_change", ("P0AEX9", "P02925", "P02829", "P0DP23", "P0ABQ4", "P01112", "P00519", "P07550", "P0A334")),
    ("mechanical", ("Q8WZ42", "Q9Y490", "P07751")),
    ("disordered", ("P37840", "P10636")),
)
ALWAYS = "P37840"

FINDINGS = """# Findings

One issue per line. Start the line with the item id, then a short description.

Do not change files under curation/ in response to this round. Corrections belong in the next release.
"""


class AuditError(Exception):
    pass


@dataclass
class Protein:
    accession: str
    name: str
    as_of: str
    states: list[dict]
    evidence: list[dict]
    ambiguous_ids: set[str] = field(default_factory=set)
    conflicts: list[dict] = field(default_factory=list)


def jsonl_dumps(row: dict) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(jsonl_dumps(row) for row in rows), encoding="utf-8", newline="\n")


def _protein_id(acc: str) -> bool:
    return not (acc.startswith("URS") or acc.startswith("DNA-") or acc.startswith("CPX-"))


def _rule(ev: dict) -> tuple[str, str, str] | None:
    for mapping in ev.get("mappings") or []:
        who = mapping.get("who") or ""
        if who.startswith("rule:"):
            return who.split(":", 1)[1], mapping["state_id"], mapping.get("confidence") or ""
    return None


def _curator(ev: dict) -> tuple[str, str, str] | None:
    for mapping in ev.get("mappings") or []:
        who = mapping.get("who") or ""
        if who.startswith("curator:"):
            return who.split(":", 1)[1], mapping["state_id"], mapping.get("confidence") or ""
    return None


def load_release(build: Path, curation: Path) -> list[Protein]:
    proteins = []
    for path in sorted(curation.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        acc = str(data.get("molecule_id") or data.get("uniprot") or path.stem)
        if not _protein_id(acc):
            continue
        states = data.get("states") or []
        if not states:
            continue
        mapped_path = build / acc / "mapped.json"
        if not mapped_path.is_file():
            raise AuditError(f"no mapped.json for curated protein {acc} under {build}")
        mapped = json.loads(mapped_path.read_text(encoding="utf-8"))
        evidence = sorted(mapped.get("evidence") or [], key=lambda ev: ev["evidence_id"])
        ambiguous = {row["evidence_id"] for row in mapped.get("ambiguous") or []}
        conflicts = sorted(mapped.get("conflicts") or [], key=lambda row: row["conflict_id"])
        proteins.append(Protein(
            accession=acc,
            name=str(data.get("name") or acc),
            as_of=str(data.get("as_of") or ""),
            states=list(states),
            evidence=evidence,
            ambiguous_ids=ambiguous,
            conflicts=conflicts,
        ))
    if not proteins:
        raise AuditError(f"no curated proteins with mapped.json under {build}")
    return proteins


def definitions_for(states: list[dict]) -> list[dict]:
    by_id = {state["id"]: state for state in states}
    rows = []
    for state in states:
        parent = state.get("parent")
        parent_name = by_id[parent]["name"] if parent and parent in by_id else parent
        rows.append({
            "name": state.get("name") or state["id"],
            "basis": state.get("basis"),
            "description": state.get("description") or "",
            "representative_pdb": state.get("representative_pdb"),
            "assumptions": list(state.get("assumptions") or []),
            "parent": parent_name,
        })
    return rows


def public_evidence(ev: dict) -> dict:
    """Fields the reviewer is allowed to see. Mappings are omitted on purpose."""
    provenance = ev.get("provenance") or {}
    return {
        "technique": ev.get("technique"),
        "source": provenance.get("source"),
        "deposit_id": provenance.get("deposit_id"),
        "deposit_url": provenance.get("url"),
        "title": ev.get("title"),
        "construct": (ev.get("construct") or {}).get("description"),
        "labels": list((ev.get("construct") or {}).get("labels") or []),
        "conditions": ev.get("conditions") or {},
        "observable": ev.get("observable") or {},
        "doi": provenance.get("doi"),
    }


def _page(acc: str) -> str:
    return f"../../site/dist/protein/{acc}/index.html"


def _take(rng: random.Random, rows: list, k: int) -> list:
    rows = list(rows)
    if k >= len(rows):
        return rows
    return rng.sample(rows, k)


def largest_remainder(sizes: dict, target: int) -> dict:
    keys = sorted(k for k, n in sizes.items() if n > 0)
    total = sum(sizes[k] for k in keys)
    if total <= target:
        return {k: sizes[k] for k in keys}
    raw = {k: target * sizes[k] / total for k in keys}
    take = {k: min(sizes[k], int(raw[k])) for k in keys}
    left = target - sum(take.values())
    order = sorted(keys, key=lambda k: (-(raw[k] - int(raw[k])), -sizes[k], str(k)))
    while left > 0:
        grew = False
        for key in order:
            if left <= 0:
                break
            if take[key] < sizes[key]:
                take[key] += 1
                left -= 1
                grew = True
        if not grew:
            break
    return take


def allocate_a1(sizes: dict[str, int], target: int) -> dict[str, int]:
    """Per-rule sample sizes.

    A rule with fewer than 10 items is taken whole. Every larger rule gets at
    least 10, capped at its own size. The total then moves as close to
    `target` as those floors and caps allow.
    """
    if target < 1:
        raise AuditError("--n must be at least 1")
    present = {rule: n for rule, n in sizes.items() if n > 0}
    total_n = sum(present.values())
    if total_n == 0:
        return {}
    take = {rule: n for rule, n in present.items() if n < 10}
    large = sorted(rule for rule, n in present.items() if n >= 10)
    raw = {rule: target * present[rule] / total_n for rule in large}
    for rule in large:
        take[rule] = min(present[rule], max(10, int(round(raw[rule]))))
    def total() -> int:
        return sum(take.values())
    while total() > target:
        reducible = [rule for rule in large if take[rule] > 10]
        if not reducible:
            break
        rule = max(reducible, key=lambda r: (take[r] - raw[r], take[r], r))
        take[rule] -= 1
    while total() < target:
        growable = [rule for rule in large if take[rule] < present[rule]]
        if not growable:
            break
        rule = max(growable, key=lambda r: (raw[r] - take[r], present[r], r))
        take[rule] += 1
    return {rule: n for rule, n in take.items() if n}


def choose_proteins(curated: set[str], rng: random.Random, low: int = 8, high: int = 10, per_group: int = 2) -> list[str]:
    """8–10 curated accessions, about two from each pilot group, P37840 always included when it is curated."""
    pools = []
    for name, accs in GROUPS:
        pool = sorted(acc for acc in accs if acc in curated)
        rng.shuffle(pool)
        pools.append((name, pool))
    chosen: list[str] = []
    if ALWAYS in curated:
        chosen.append(ALWAYS)
    members = {name: set(accs) for name, accs in GROUPS}
    for name, pool in pools:
        need = per_group - sum(1 for acc in chosen if acc in members[name])
        for acc in pool:
            if need <= 0:
                break
            if acc in chosen:
                continue
            chosen.append(acc)
            need -= 1
    by_size = sorted(pools, key=lambda item: (-len(item[1]), item[0]))
    while len(chosen) < low:
        added = False
        for _, pool in by_size:
            for acc in pool:
                if acc not in chosen:
                    chosen.append(acc)
                    added = True
                    break
            if len(chosen) >= low:
                break
        if not added:
            break
    while len(chosen) > high:
        counts = {name: sum(1 for acc in chosen if acc in members[name]) for name, _ in GROUPS}
        name = max(counts, key=lambda n: (counts[n], n))
        drop = [acc for acc in reversed(chosen) if acc in members[name] and acc != ALWAYS]
        if not drop:
            break
        chosen.remove(drop[0])
    return chosen


def _bucket(protein: Protein) -> tuple[list, dict[str, list], list, list]:
    curator, by_rule, unmapped, ambiguous = [], {}, [], []
    for ev in protein.evidence:
        if _curator(ev):
            curator.append(ev)
            continue
        if ev["evidence_id"] in protein.ambiguous_ids:
            ambiguous.append(ev)
            continue
        rule = _rule(ev)
        if rule:
            by_rule.setdefault(rule[0], []).append(ev)
            continue
        if ev.get("mappings"):
            raise AuditError(f"{protein.accession} {ev['evidence_id']}: mapping is neither a curator nor a rule")
        unmapped.append(ev)
    return curator, by_rule, unmapped, ambiguous


def _sample_row(protein: Protein, *, item_id: str, kind: str, stratum: str, stratum_key: str,
                population: int, evidence: dict | None = None, evidence_b: dict | None = None) -> dict:
    return {
        "item_id": item_id,
        "kind": kind,
        "stratum": stratum,
        "stratum_key": stratum_key,
        "population": population,
        "protein": {"accession": protein.accession, "name": protein.name, "page": _page(protein.accession)},
        "definitions": definitions_for(protein.states),
        "choice_ids": [state["id"] for state in protein.states],
        "evidence": evidence,
        "evidence_b": evidence_b,
    }


def _key_row(**fields) -> dict:
    return fields


def sample_part_a(proteins: list[Protein], rng: random.Random, n: int, n_unmapped: int, n_ambiguous: int):
    by_rule: dict[str, list[tuple[Protein, dict]]] = {}
    unmapped: list[tuple[Protein, dict]] = []
    ambiguous: list[tuple[Protein, dict]] = []
    for protein in proteins:
        _, rules, plain, amb = _bucket(protein)
        for rule, rows in rules.items():
            by_rule.setdefault(rule, []).extend((protein, ev) for ev in rows)
        unmapped.extend((protein, ev) for ev in plain)
        ambiguous.extend((protein, ev) for ev in amb)
    for rule in by_rule:
        by_rule[rule].sort(key=lambda pair: (pair[0].accession, pair[1]["evidence_id"]))
    unmapped.sort(key=lambda pair: (pair[0].accession, pair[1]["evidence_id"]))
    ambiguous.sort(key=lambda pair: (pair[0].accession, pair[1]["evidence_id"]))
    alloc = allocate_a1({rule: len(rows) for rule, rows in by_rule.items()}, n)
    sample, key = [], []
    strata = {}
    for index, rule in enumerate(sorted(alloc)):
        picked = _take(rng, by_rule[rule], alloc[rule])
        population = len(by_rule[rule])
        stratum_key = f"A1-{index:03d}"
        strata[stratum_key] = {"population": population, "drawn": len(picked)}
        for protein, ev in picked:
            rule_id, state_id, _confidence = _rule(ev)
            sample.append(_sample_row(
                protein, item_id=ev["evidence_id"], kind="evidence", stratum="A1",
                stratum_key=stratum_key, population=population, evidence=public_evidence(ev),
            ))
            key.append(_key_row(
                item_id=ev["evidence_id"], part="A", stratum="A1", stratum_key=stratum_key,
                population=population, assigned_state=state_id, rule_id=rule_id,
                technique=ev.get("technique"), source=(ev.get("provenance") or {}).get("source"),
                accession=protein.accession, curator_confidence=None,
            ))
    unmapped_n = len(unmapped)
    unmapped_picked = _take(rng, unmapped, min(n_unmapped, unmapped_n))
    strata["A2"] = {"population": unmapped_n, "drawn": len(unmapped_picked)}
    for protein, ev in unmapped_picked:
        sample.append(_sample_row(
            protein, item_id=ev["evidence_id"], kind="evidence", stratum="A2",
            stratum_key="A2", population=unmapped_n, evidence=public_evidence(ev),
        ))
        key.append(_key_row(
            item_id=ev["evidence_id"], part="A", stratum="A2", stratum_key="A2",
            population=unmapped_n, assigned_state=None, rule_id=None,
            technique=ev.get("technique"), source=(ev.get("provenance") or {}).get("source"),
            accession=protein.accession, curator_confidence=None,
        ))
    ambiguous_n = len(ambiguous)
    ambiguous_picked = _take(rng, ambiguous, ambiguous_n if ambiguous_n <= n_ambiguous else n_ambiguous)
    strata["A3"] = {"population": ambiguous_n, "drawn": len(ambiguous_picked)}
    for protein, ev in ambiguous_picked:
        sample.append(_sample_row(
            protein, item_id=ev["evidence_id"], kind="evidence", stratum="A3",
            stratum_key="A3", population=ambiguous_n, evidence=public_evidence(ev),
        ))
        key.append(_key_row(
            item_id=ev["evidence_id"], part="A", stratum="A3", stratum_key="A3",
            population=ambiguous_n, assigned_state=None, rule_id=None,
            technique=ev.get("technique"), source=(ev.get("provenance") or {}).get("source"),
            accession=protein.accession, curator_confidence=None,
        ))
    rng.shuffle(sample)
    order = {row["item_id"]: i for i, row in enumerate(sample)}
    key.sort(key=lambda row: order[row["item_id"]])
    return sample, key, strata


def sample_part_b(proteins: list[Protein], rng: random.Random, n_mapped: int, n_unmapped: int):
    by_acc = {protein.accession: protein for protein in proteins}
    chosen = choose_proteins(set(by_acc), rng)
    if ALWAYS not in by_acc:
        raise AuditError("part B requires curated α-synuclein (P37840) in the release")
    sample, key = [], []
    per_protein = {}
    for acc in chosen:
        protein = by_acc[acc]
        curator, _, plain, _amb = _bucket(protein)
        mapped_n = len(curator)
        if mapped_n <= n_mapped:
            picked = list(curator)
        else:
            groups: dict[tuple, list] = {}
            for ev in curator:
                groups.setdefault((_curator(ev)[1], ev.get("technique")), []).append(ev)
            alloc = largest_remainder({k: len(v) for k, v in groups.items()}, n_mapped)
            picked = []
            for stratum in sorted(alloc, key=str):
                picked.extend(_take(rng, sorted(groups[stratum], key=lambda ev: ev["evidence_id"]), alloc[stratum]))
        plain_n = len(plain)
        plain_picked = _take(rng, plain, min(n_unmapped, plain_n))
        per_protein[acc] = {
            "mapped_population": mapped_n, "mapped_drawn": len(picked),
            "unmapped_population": plain_n, "unmapped_drawn": len(plain_picked),
        }
        for ev in picked:
            _who, state_id, confidence = _curator(ev)
            sample.append(_sample_row(
                protein, item_id=ev["evidence_id"], kind="evidence", stratum="B-mapped",
                stratum_key=f"B-mapped-{acc}", population=mapped_n, evidence=public_evidence(ev),
            ))
            key.append(_key_row(
                item_id=ev["evidence_id"], part="B", stratum="B-mapped", stratum_key=f"B-mapped-{acc}",
                population=mapped_n, assigned_state=state_id, rule_id=None,
                technique=ev.get("technique"), source=(ev.get("provenance") or {}).get("source"),
                accession=acc, curator_confidence=confidence,
            ))
        for ev in plain_picked:
            sample.append(_sample_row(
                protein, item_id=ev["evidence_id"], kind="evidence", stratum="B-unmapped",
                stratum_key=f"B-unmapped-{acc}", population=plain_n, evidence=public_evidence(ev),
            ))
            key.append(_key_row(
                item_id=ev["evidence_id"], part="B", stratum="B-unmapped", stratum_key=f"B-unmapped-{acc}",
                population=plain_n, assigned_state="none", rule_id=None,
                technique=ev.get("technique"), source=(ev.get("provenance") or {}).get("source"),
                accession=acc, curator_confidence=None,
            ))
        sample.append(_sample_row(
            protein, item_id=f"states:{acc}", kind="states", stratum="B-states",
            stratum_key=f"B-states-{acc}", population=1,
        ))
    rng.shuffle(sample)
    order = {row["item_id"]: i for i, row in enumerate(sample)}
    key.sort(key=lambda row: order[row["item_id"]])
    return sample, key, {"proteins": chosen, "per_protein": per_protein}


def _conflict_item_id(conflict: dict) -> str:
    first, second = conflict["evidence_ids"]
    return f"CF-{first}-{second}-{conflict['observable_type']}"


def sample_part_c(proteins: list[Protein], rng: random.Random, n_rest: int):
    by_acc = {protein.accession: protein for protein in proteins}
    owned = []
    for protein in proteins:
        for conflict in protein.conflicts:
            owned.append((protein, conflict))
    focus = [pair for pair in owned if pair[0].accession == ALWAYS]
    rest = [pair for pair in owned if pair[0].accession != ALWAYS]
    groups: dict[str, list] = {}
    for pair in rest:
        groups.setdefault(pair[1]["observable_type"], []).append(pair)
    for rows in groups.values():
        rows.sort(key=lambda pair: pair[1]["conflict_id"])
    alloc = largest_remainder({key: len(rows) for key, rows in groups.items()}, n_rest)
    picked = list(focus)
    strata = {"C-P37840": {"population": len(focus), "drawn": len(focus)}}
    for index, observable in enumerate(sorted(alloc)):
        rows = _take(rng, groups[observable], alloc[observable])
        stratum_key = f"C-{index:03d}"
        strata[stratum_key] = {"population": len(groups[observable]), "drawn": len(rows), "observable": observable}
        for protein, conflict in rows:
            conflict["_stratum_key"] = stratum_key
        picked.extend(rows)
    sample, key = [], []
    focus_n = len(focus)
    for protein, conflict in picked:
        evs = {ev["evidence_id"]: ev for ev in protein.evidence}
        try:
            left = evs[conflict["evidence_ids"][0]]
            right = evs[conflict["evidence_ids"][1]]
        except KeyError as exc:
            raise AuditError(f"{protein.accession}: conflict names unknown evidence {exc}") from exc
        on_focus = protein.accession == ALWAYS
        stratum_key = "C-P37840" if on_focus else conflict["_stratum_key"]
        population = focus_n if on_focus else strata[stratum_key]["population"]
        item_id = _conflict_item_id(conflict)
        sample.append(_sample_row(
            protein, item_id=item_id, kind="conflict",
            stratum="C-P37840" if on_focus else "C-rest",
            stratum_key=stratum_key, population=population,
            evidence=public_evidence(left), evidence_b=public_evidence(right),
        ))
        key.append(_key_row(
            item_id=item_id, part="C", stratum="C-P37840" if on_focus else "C-rest",
            stratum_key=stratum_key, population=population, assigned_state=None, rule_id=None,
            source_conflict_id=conflict["conflict_id"], state_id=conflict.get("state_id"),
            observable_type=conflict.get("observable_type"), accession=protein.accession,
            p37840=on_focus, evidence_ids=list(conflict["evidence_ids"]),
            values=list(conflict.get("values") or []),
            uncertainties=list(conflict.get("uncertainties") or []),
        ))
    rng.shuffle(sample)
    order = {row["item_id"]: i for i, row in enumerate(sample)}
    key.sort(key=lambda row: order[row["item_id"]])
    return sample, key, strata


def draw_round(*, part: str, round_id: str, tag: str, seed: int, reviewer: str, build: Path, curation: Path,
               dest: Path, commit: str, created: str | None = None, n: int | None = None,
               n_unmapped: int = 100, n_ambiguous: int = 50, n_rest: int = 50,
               n_mapped: int = 60, n_unmapped_protein: int = 15) -> dict:
    if part not in {"A", "B", "C"}:
        raise AuditError("part must be A, B or C")
    if not TAG_RE.match(tag):
        raise AuditError(f"tag {tag} is not a frozen paper release (expected vX.Y.Z-paper)")
    proteins = load_release(build, curation)
    rng = random.Random(seed)
    if part == "A":
        sample, key, strata = sample_part_a(proteins, rng, 200 if n is None else n, n_unmapped, n_ambiguous)
    elif part == "B":
        sample, key, strata = sample_part_b(proteins, rng, n_mapped, n_unmapped_protein)
    else:
        sample, key, strata = sample_part_c(proteins, rng, n_rest if n is None else n)
    dest.mkdir(parents=True, exist_ok=True)
    meta = {
        "part": part,
        "tag": tag,
        "commit": commit,
        "seed": int(seed),
        "reviewer": reviewer,
        "created": created or max((protein.as_of for protein in proteins), default=""),
        "round_id": round_id,
        "n_requested": n,
        "strata": strata,
    }
    (dest / "round.yaml").write_text(
        yaml.safe_dump(meta, sort_keys=True, allow_unicode=True), encoding="utf-8", newline="\n",
    )
    write_jsonl(dest / "sample.jsonl", sample)
    write_jsonl(dest / "key.jsonl", key)
    findings = dest / "findings.md"
    if not findings.exists():
        findings.write_text(FINDINGS, encoding="utf-8", newline="\n")
    audit_sheet.write_sheet(dest / "sample.jsonl", {"round_id": round_id, "part": part, "tag": tag, "seed": seed}, dest / "sheet.html")
    return meta


def head_exact_tag(repo: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "describe", "--exact-match", "--tags", "HEAD"],
            cwd=repo, stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out or None


def require_release_tag(repo: Path, tag: str) -> str:
    if not TAG_RE.match(tag):
        raise AuditError(f"tag {tag} is not a frozen paper release (expected vX.Y.Z-paper)")
    got = head_exact_tag(repo)
    if got != tag:
        raise AuditError(f"HEAD is {got or 'not tagged'}; draw this round with HEAD exactly at {tag}")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draw a blinded Conformome audit round")
    parser.add_argument("--part", required=True, choices=["A", "B", "C"])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--build", type=Path, default=REPO / "build")
    parser.add_argument("--curation", type=Path, default=REPO / "curation")
    parser.add_argument("--audit", type=Path, default=REPO / "audit")
    args = parser.parse_args(argv)
    try:
        commit = require_release_tag(REPO, args.tag)
        draw_round(
            part=args.part, round_id=args.round_id, tag=args.tag, seed=args.seed,
            reviewer=args.reviewer, build=args.build, curation=args.curation,
            dest=args.audit / args.round_id, commit=commit, n=args.n,
        )
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.audit / args.round_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
