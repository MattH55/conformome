#!/usr/bin/env python3
"""Every corpus number in the Conformome paper, read from one frozen release.

Inputs (fixed; do not search at runtime):

    build/<accession>/mapped.json     map output: evidence, states, conflicts
    build/<accession>/models.json     exported state models
    build/<accession>/molecule.json   name, gene, molecule type
    taxonomy/techniques.yaml          technique taxonomy, in file order
    curation/<accession>.yaml         state ids and representative PDB entries
    data/MANIFEST.json                raw-input retrieval dates
    site/dist/index.html              site totals, for --check
    site/dist/protein/P37840/index.html
    site/dist/downloads/all-records.jsonl   redistributable records only

SMASH-BIO is omitted from all-records.jsonl, so evidence totals and the coverage
matrix are taken from build/<accession>/mapped.json, which is what the site uses.

    python -I scripts/stats.py            # write paper/out/stats.json, print it
    python -I scripts/stats.py --check    # also require the site HTML to match
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build"
SITE = REPO / "site" / "dist"
ALL_RECORDS = SITE / "downloads" / "all-records.jsonl"
PROTEIN_BUNDLES = SITE / "downloads" / "proteins"
TECHNIQUES_YAML = REPO / "taxonomy" / "techniques.yaml"
MANIFEST = REPO / "data" / "MANIFEST.json"
CURATION = REPO / "curation"
SITE_HOME = SITE / "index.html"
SITE_P37840 = SITE / "protein" / "P37840" / "index.html"
OUT = Path(__file__).resolve().parents[1] / "out" / "stats.json"

# Provenance source name -> stats key. These are the seven ingested protein sources.
SOURCE_KEYS = {
    "RCSB PDB": "pdb",
    "BMRB": "bmrb",
    "AlphaFold DB": "afdb",
    "SMASH-BIO": "smash",
    "DisProt": "disprot",
    "MDDB": "mddb",
    "SASBDB": "sasbdb",
}
STUB_SOURCES = ("ped", "pdbihm", "atlas", "literature")

# α-synuclein slugs in the manuscript -> state ids in curation/P37840.yaml.
# If that file does not contain exactly these states, stop. Do not remap.
P37840 = "P37840"
P37840_STATES = {
    "disordered": "aS-disordered",
    "micelle": "aS-micelle-helix",
    "fibril": "aS-fibril",
}


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return out.stdout.strip()


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _proteins() -> list[str]:
    """Protein accessions that the release actually built."""
    accs = []
    if not BUILD.is_dir():
        raise SystemExit(f"stats: {BUILD} is missing; run make ingest map models site first")
    for mapped in sorted(BUILD.glob("*/mapped.json")):
        mol_path = mapped.parent / "molecule.json"
        if not mol_path.exists():
            raise SystemExit(f"stats: {mol_path} missing")
        mol = _read_json(mol_path)
        if mol.get("molecule_type") == "protein":
            accs.append(mapped.parent.name)
    if not accs:
        raise SystemExit("stats: no protein builds under build/")
    return accs


def _technique_ids() -> list[str]:
    doc = yaml.safe_load(TECHNIQUES_YAML.read_text(encoding="utf-8"))
    ids = [t["id"] for t in doc["techniques"]]
    if len(ids) != len(set(ids)):
        raise SystemExit("stats: duplicate technique ids in techniques.yaml")
    return ids


def _curation_ids() -> set[str]:
    return {p.stem for p in CURATION.glob("*.yaml")}


def _load_p37840_curation() -> dict:
    path = CURATION / "P37840.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    got = [s["id"] for s in doc["states"]]
    want = list(P37840_STATES.values())
    if got != want:
        raise SystemExit(
            "stats: curation/P37840.yaml states are "
            + ", ".join(got)
            + "; the manuscript slugs map to "
            + ", ".join(want)
            + ". Refusing to force the mapping."
        )
    return doc


def _build_date() -> str:
    if not MANIFEST.exists():
        raise SystemExit(f"stats: {MANIFEST} missing")
    manifest = _read_json(MANIFEST)
    dates = [row.get("retrieved", "") for row in manifest.values() if isinstance(row, dict)]
    dates = [d for d in dates if d]
    if not dates:
        raise SystemExit("stats: manifest has no retrieval dates")
    return max(dates)


def compute() -> dict:
    accessions = _proteins()
    technique_ids = _technique_ids()
    curated_files = _curation_ids()
    p37840_cur = _load_p37840_curation()
    by_state_id = {s["id"]: s for s in p37840_cur["states"]}

    n_evidence = 0
    tech_evidence: Counter[str] = Counter()
    tech_proteins: Counter[str] = Counter()
    source_evidence: Counter[str] = Counter()
    source_proteins: Counter[str] = Counter()
    n_states = n_obs = n_inf = 0
    n_mapped = n_unmapped = n_ambiguous = 0
    n_by_assignment = n_by_rule = 0
    n_conflicts = n_uncompared = n_single = 0
    n_transitions = n_models = 0
    proteins_with_evidence = 0
    curated_with_evidence = 0

    p37840: dict = {}

    for acc in accessions:
        mapped = _read_json(BUILD / acc / "mapped.json")
        evidence = mapped["evidence"]
        if not evidence:
            continue
        proteins_with_evidence += 1
        is_curated = acc in curated_files
        if is_curated:
            curated_with_evidence += 1
        n_evidence += len(evidence)
        techs = {ev["technique"] for ev in evidence}
        sources = {ev["provenance"]["source"] for ev in evidence}
        for t in techs:
            tech_proteins[t] += 1
        for ev in evidence:
            tech_evidence[ev["technique"]] += 1
            source_evidence[ev["provenance"]["source"]] += 1
        for s in sources:
            source_proteins[s] += 1

        if is_curated:
            n_states += len(mapped["states"])
            n_obs += sum(1 for s in mapped["states"] if s["basis"] == "observed")
            n_inf += sum(1 for s in mapped["states"] if s["basis"] == "inferred")
            n_transitions += len(mapped["transitions"])
            n_conflicts += len(mapped["conflicts"])
            n_uncompared += int(mapped["not_compared"])
            n_ambiguous += len(mapped.get("ambiguous") or [])
            n_single += len(mapped["coverage"]["single_method_states"])
            for ev in evidence:
                if ev["mappings"]:
                    n_mapped += 1
                    whos = [m["who"] for m in ev["mappings"]]
                    if any(w.startswith("curator:") for w in whos):
                        n_by_assignment += 1
                    elif any(w.startswith("rule:") for w in whos):
                        n_by_rule += 1
                    else:
                        raise SystemExit(f"stats: {acc} {ev['evidence_id']} mapping who is neither curator nor rule")
                else:
                    n_unmapped += 1
        models_path = BUILD / acc / "models.json"
        if models_path.exists():
            n_models += len(_read_json(models_path))

        if acc == P37840:
            p37840 = _p37840(mapped, by_state_id)

    if not p37840:
        raise SystemExit("stats: P37840 has no evidence in the release")

    unknown_tech = sorted(set(tech_evidence) - set(technique_ids))
    if unknown_tech:
        raise SystemExit(f"stats: evidence uses techniques missing from techniques.yaml: {unknown_tech}")

    for name in source_evidence:
        if name not in SOURCE_KEYS:
            raise SystemExit(f"stats: unexpected evidence source {name!r}")

    n_curated = curated_with_evidence
    n_uncurated = proteins_with_evidence - n_curated
    if n_uncurated < 0:
        raise SystemExit("stats: more curated proteins than proteins with evidence")

    present_techs = [t for t in technique_ids if tech_evidence[t]]
    stats: dict = {
        "release": {
            "tag": _git("describe", "--tags", "--exact-match"),
            "commit": _git("rev-parse", "HEAD"),
            "build_date": _build_date(),
            "n_proteins": proteins_with_evidence,
            "n_evidence": n_evidence,
            "n_techniques": len(present_techs),
            "n_techniques_taxonomy": len(technique_ids),
            "n_sources": len(source_evidence),
            "n_stub_sources": sum(1 for _ in STUB_SOURCES),
            "n_curated": n_curated,
            "n_uncurated": n_uncurated,
            "n_states": n_states,
            "n_states_observed": n_obs,
            "n_states_inferred": n_inf,
            "n_mapped": n_mapped,
            "n_unmapped": n_unmapped,
            "n_ambiguous": n_ambiguous,
            "n_mapped_by_assignment": n_by_assignment,
            "n_mapped_by_rule": n_by_rule,
            "n_conflicts": n_conflicts,
            "n_uncompared": n_uncompared,
            "n_single_method_states": n_single,
            "n_transitions": n_transitions,
            "n_models": n_models,
        },
        "sources": {},
        "techniques": {},
        "p37840": p37840,
    }
    for name, key in SOURCE_KEYS.items():
        stats["sources"][key] = {"n_proteins": source_proteins[name], "n_evidence": source_evidence[name]}
    for tid in technique_ids:
        stats["techniques"][tid] = {"n_evidence": tech_evidence[tid], "n_proteins": tech_proteins[tid]}

    # Redistributable download must not silently disagree with the map for sources it includes.
    if ALL_RECORDS.exists():
        _check_all_records(stats, accessions)
    return stats


def _p37840(mapped: dict, by_state_id: dict) -> dict:
    evidence = mapped["evidence"]
    out = {
        "n_evidence": len(evidence),
        "n_sources": len({ev["provenance"]["source"] for ev in evidence}),
        "n_techniques": len({ev["technique"] for ev in evidence}),
        "n_mapped": sum(1 for ev in evidence if ev["mappings"]),
        "n_unmapped": sum(1 for ev in evidence if not ev["mappings"]),
        "n_states": len(mapped["states"]),
        "n_conflicts": len(mapped["conflicts"]),
        "n_smash_unmapped": sum(
            1 for ev in evidence if ev["provenance"]["source"] == "SMASH-BIO" and not ev["mappings"]
        ),
        "states": {},
    }
    cells = mapped["coverage"]["cells"]
    for slug, sid in P37840_STATES.items():
        row = cells.get(sid) or {}
        out["states"][slug] = {
            "n_evidence": sum(row.values()),
            "n_techniques": sum(1 for n in row.values() if n),
            "basis": by_state_id[sid]["basis"],
            "representative_pdb": by_state_id[sid].get("representative_pdb"),
        }
    return out


def _check_all_records(stats: dict, accessions: list[str]) -> None:
    """all-records.jsonl drops non-redistributable sources. Compare the rest."""
    n = 0
    proteins = set()
    for line in ALL_RECORDS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("record_type") != "evidence":
            continue
        if rec.get("molecule_id") not in accessions:
            continue
        if rec["provenance"]["source"] == "SMASH-BIO":
            raise SystemExit("stats: all-records.jsonl contains SMASH-BIO, which must not be redistributed")
        n += 1
        proteins.add(rec["molecule_id"])
    expected = stats["release"]["n_evidence"] - stats["sources"]["smash"]["n_evidence"]
    if n != expected:
        raise SystemExit(
            f"stats: all-records.jsonl has {n} redistributable protein evidence items; "
            f"mapped.json implies {expected}"
        )


def _ints(html: str) -> list[tuple[int, str]]:
    return [(int(n.replace(",", "")), label.strip()) for n, label in re.findall(r"<b>([\d,]+)</b>\s*([^<]+)", html)]


def _site_totals() -> dict:
    """The same sums the home page prints, over every molecule the site build included."""
    summaries = []
    for mapped_path in sorted(BUILD.glob("*/mapped.json")):
        mol = _read_json(mapped_path.parent / "molecule.json")
        mapped = _read_json(mapped_path)
        evidence = mapped["evidence"]
        summaries.append({
            "evidence": len(evidence),
            "states": len(mapped["states"]),
            "techs": {ev["technique"] for ev in evidence},
            "sources": {ev["provenance"]["source"] for ev in evidence},
        })
    return {
        "proteins": len(summaries),  # the home tile is labelled "proteins" and counts every page
        "evidence entries": sum(s["evidence"] for s in summaries),
        "techniques": len({t for s in summaries for t in s["techs"]}),
        "sources": len({src for s in summaries for src in s["sources"]}),
        "curated states": sum(s["states"] for s in summaries),
    }


def check_site(stats: dict) -> list[str]:
    """Fail if the frozen site HTML disagrees with the release files it was built from."""
    errors = []
    if not SITE_HOME.exists() or not SITE_P37840.exists():
        return ["site HTML missing; run make site"]
    home = {label: n for n, label in _ints(SITE_HOME.read_text(encoding="utf-8"))}
    page = {label: n for n, label in _ints(SITE_P37840.read_text(encoding="utf-8"))}
    expect_home = _site_totals()
    for label, want in expect_home.items():
        got = home.get(label)
        if got != want:
            errors.append(f"site home {label}: page has {got}, build files have {want}")
    rel = stats["release"]
    # The home tile is labelled "proteins" but counts every molecule page. Protein-only keys stay protein-only.
    # When the two differ, the manuscript has to say so; the check records the gap instead of moving a number.
    if home.get("proteins") != rel["n_proteins"] or home.get("evidence entries") != rel["n_evidence"]:
        print(
            "stats --check: home page counts every molecule "
            f"({home.get('proteins')} pages, {home.get('evidence entries')} evidence); "
            f"protein release is {rel['n_proteins']} proteins, {rel['n_evidence']} evidence",
            file=sys.stderr,
        )
        if home.get("proteins") != expect_home["proteins"]:
            errors.append("home page does not match the build")
    p = stats["p37840"]
    expect_page = {
        "evidence items": p["n_evidence"],
        "mapped to a state": p["n_mapped"],
        "states": p["n_states"],
        "techniques": p["n_techniques"],
        "sources": p["n_sources"],
        "conflicts": p["n_conflicts"],
    }
    for label, want in expect_page.items():
        got = page.get(label)
        if got != want:
            errors.append(f"site P37840 {label}: page has {got}, stats have {want}")
    return errors


def main() -> int:
    stats = compute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(stats, indent=2, ensure_ascii=False) + "\n"
    # stdout is what build.sh redirects. Keep diagnostics on stderr.
    sys.stdout.write(text)
    if "--check" in sys.argv:
        errors = check_site(stats)
        tag = stats["release"]["tag"]
        if not tag or not re.fullmatch(r"v\d+\.\d+\.\d+-paper", tag):
            errors.append(f"HEAD is not tagged vX.Y.Z-paper (git describe says {tag!r})")
        if not stats["release"]["commit"]:
            errors.append("could not read the release commit")
        for err in errors:
            print(f"stats --check: {err}", file=sys.stderr)
        if errors:
            return 1
        print(f"stats --check: site agrees ({stats['release']['n_proteins']} proteins, "
              f"{stats['release']['n_evidence']} evidence)", file=sys.stderr)
    else:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
