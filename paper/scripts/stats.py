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

Every molecule the release built is counted: proteins, RNA and DNA. release.n_evidence,
n_states, n_curated and the mapping counts are over all molecules; the _protein and _na keys
split them. release.n_proteins counts proteins with evidence, as before.

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
MOLECULE_BUNDLES = SITE / "downloads" / "molecules"
TECHNIQUES_YAML = REPO / "taxonomy" / "techniques.yaml"
MANIFEST = REPO / "data" / "MANIFEST.json"
CURATION = REPO / "curation"
SITE_HOME = SITE / "index.html"
SITE_P37840 = SITE / "protein" / "P37840" / "index.html"
OUT = Path(__file__).resolve().parents[1] / "out" / "stats.json"

VERSION = "0.1.0"

# Provenance source name -> stats key: the seven protein sources, then the nucleic-acid sources.
SOURCE_KEYS = {
    "RCSB PDB": "pdb",
    "BMRB": "bmrb",
    "AlphaFold DB": "afdb",
    "SMASH-BIO": "smash",
    "DisProt": "disprot",
    "MDDB": "mddb",
    "SASBDB": "sasbdb",
    "NAKB": "nakb",
    "Rfam": "rfam",
    "RMDB": "rmdb",
}
# Sources reported only when a module for them ran in this release (a missing module is not zero evidence).
OPTIONAL_SOURCE_KEYS = {"rmdb"}

# Pilot nucleic acids: manuscript slug -> molecule id. The G-quadruplex states are reported by topology.
NA_SLUGS = {
    "add": "URS000080DF85_672",
    "preq1": "URS000080E020_32630",
    "tar": "URS000080E14B_11676",
    "p4p6": "URS000080E052_32630",
    "fse": "URS00021ED9B3_2697049",
    "g4": "DNA-6f16b68e4fba",
}
G4_STATES = {"parallel": "G4-parallel", "antiparallel": "G4-antiparallel", "hybrid": "G4-hybrid"}
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


def _molecules() -> dict[str, str]:
    """Every molecule the release built, id -> molecule type."""
    out = {}
    if not BUILD.is_dir():
        raise SystemExit(f"stats: {BUILD} is missing; run make ingest map models site first")
    for mapped in sorted(BUILD.glob("*/mapped.json")):
        mol_path = mapped.parent / "molecule.json"
        if not mol_path.exists():
            raise SystemExit(f"stats: {mol_path} missing")
        out[mapped.parent.name] = _read_json(mol_path).get("molecule_type", "protein")
    if not any(t == "protein" for t in out.values()):
        raise SystemExit("stats: no protein builds under build/")
    return out


def _ion_blind_conflicts(evidence: list[dict]) -> int:
    """Conflicts the 3-sigma rule would report if ion species and concentrations were ignored."""
    sys.path.insert(0, str(REPO))
    from conformome.mapping.conflicts import find_conflicts
    doc = yaml.safe_load(TECHNIQUES_YAML.read_text(encoding="utf-8"))
    predictions = {t["id"] for t in doc["techniques"] if t.get("prediction")}
    blind = []
    for ev in evidence:
        ev = json.loads(json.dumps(ev))
        ev["conditions"]["ions"] = [{"ion": "any", "concentration_mM": 1.0}]
        blind.append(ev)
    return len(find_conflicts(blind, predictions))


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
    molecules = _molecules()
    technique_ids = _technique_ids()
    curated_files = _curation_ids()
    p37840_cur = _load_p37840_curation()
    by_state_id = {s["id"]: s for s in p37840_cur["states"]}

    tech_evidence: Counter[str] = Counter()
    tech_molecules: Counter[str] = Counter()
    tech_proteins: Counter[str] = Counter()
    tech_evidence_protein: Counter[str] = Counter()
    single_method: list[dict] = []
    source_evidence: Counter[str] = Counter()
    source_molecules: Counter[str] = Counter()
    source_proteins: Counter[str] = Counter()
    n: Counter[str] = Counter()  # release counters; keys ending _na are the nucleic-acid share
    with_evidence: Counter[str] = Counter()  # molecule type -> molecules with at least one evidence item
    removed_by_ion_rule: Counter[str] = Counter()
    na: dict = {}
    g4: dict = {}
    p37840: dict = {}

    for acc, mtype in molecules.items():
        mapped = _read_json(BUILD / acc / "mapped.json")
        evidence = mapped["evidence"]
        if not evidence:
            continue
        kind = "protein" if mtype == "protein" else "na"
        with_evidence[mtype] += 1
        is_curated = acc in curated_files
        n["evidence"] += len(evidence)
        n[f"evidence_{kind}"] += len(evidence)
        techs = {ev["technique"] for ev in evidence}
        sources = {ev["provenance"]["source"] for ev in evidence}
        for t in techs:
            tech_molecules[t] += 1
            tech_proteins[t] += kind == "protein"
        for ev in evidence:
            tech_evidence[ev["technique"]] += 1
            tech_evidence_protein[ev["technique"]] += kind == "protein"
            source_evidence[ev["provenance"]["source"]] += 1
        for src in sources:
            source_molecules[src] += 1
            source_proteins[src] += kind == "protein"

        if is_curated:
            n["curated"] += 1
            n[f"curated_{kind}"] += 1
            n["states"] += len(mapped["states"])
            n[f"states_{kind}"] += len(mapped["states"])
            n["states_observed"] += sum(1 for s in mapped["states"] if s["basis"] == "observed")
            n["states_inferred"] += sum(1 for s in mapped["states"] if s["basis"] == "inferred")
            n["transitions"] += len(mapped["transitions"])
            n["conflicts"] += len(mapped["conflicts"])
            n[f"conflicts_{kind}"] += len(mapped["conflicts"])
            n["uncompared"] += int(mapped["not_compared"])
            n["ambiguous"] += len(mapped.get("ambiguous") or [])
            n["single_method_states"] += len(mapped["coverage"]["single_method_states"])
            mol_name = _read_json(BUILD / acc / "molecule.json")["name"]
            for sid in mapped["coverage"]["single_method_states"]:
                row = mapped["coverage"]["cells"][sid]
                used = [t for t, c in row.items() if c]
                state = next(st for st in mapped["states"] if st["state_id"] == sid)
                single_method.append({"molecule_id": acc, "molecule": mol_name, "type": mtype, "state_id": sid,
                                      "state": state["name"], "techniques": used, "n_evidence": sum(row.values())})
            removed_by_ion_rule[kind] += _ion_blind_conflicts(evidence) - len(mapped["conflicts"])
            for ev in evidence:
                if ev["mappings"]:
                    n["mapped"] += 1
                    n[f"mapped_{kind}"] += 1
                    whos = [m["who"] for m in ev["mappings"]]
                    if any(w.startswith("curator:") for w in whos):
                        n["mapped_by_assignment"] += 1
                    elif any(w.startswith("rule:") for w in whos):
                        n["mapped_by_rule"] += 1
                    else:
                        raise SystemExit(f"stats: {acc} {ev['evidence_id']} mapping who is neither curator nor rule")
                else:
                    n["unmapped"] += 1
        models_path = BUILD / acc / "models.json"
        if models_path.exists():
            n["models"] += len(_read_json(models_path))

        if acc == P37840:
            p37840 = _p37840(mapped, by_state_id)
        for slug, mol_id in NA_SLUGS.items():
            if acc == mol_id:
                na[slug] = {
                    "n_evidence": len(evidence),
                    "n_techniques": len(techs),
                    "n_sources": len(sources),
                    "n_states": len(mapped["states"]),
                    "n_mapped": sum(1 for ev in evidence if ev["mappings"]),
                    "n_unmapped": sum(1 for ev in evidence if not ev["mappings"]),
                    "n_ambiguous": len(mapped.get("ambiguous") or []),
                    "n_rmdb": sum(1 for ev in evidence if ev["provenance"]["source"] == "RMDB"),
                    "n_conflicts": len(mapped["conflicts"]),
                    "length": _read_json(BUILD / acc / "molecule.json")["sequence_length"],
                }
        if acc == NA_SLUGS["g4"]:
            g4 = _g4(mapped)

    if not p37840:
        raise SystemExit("stats: P37840 has no evidence in the release")
    missing = sorted(set(NA_SLUGS) - set(na))
    if missing:
        raise SystemExit(f"stats: pilot nucleic acids missing from the build: {missing}")

    unknown_tech = sorted(set(tech_evidence) - set(technique_ids))
    if unknown_tech:
        raise SystemExit(f"stats: evidence uses techniques missing from techniques.yaml: {unknown_tech}")

    for name in source_evidence:
        if name not in SOURCE_KEYS:
            raise SystemExit(f"stats: unexpected evidence source {name!r}")

    n_with_evidence = sum(with_evidence.values())
    n_uncurated = n_with_evidence - n["curated"]
    if n_uncurated < 0:
        raise SystemExit("stats: more curated molecules than molecules with evidence")

    present_techs = [t for t in technique_ids if tech_evidence[t]]
    tag = _git("describe", "--tags", "--exact-match")
    release = {
        "version": VERSION,
        "tag": tag,
        "commit": _git("rev-parse", "HEAD"),
        "build_date": _build_date(),
        "n_molecules": n_with_evidence,
        "n_proteins": with_evidence["protein"],
        "n_rna": with_evidence["rna"],
        "n_dna": with_evidence["dna"],
        "n_na": with_evidence["rna"] + with_evidence["dna"],
        "n_evidence": n["evidence"],
        "n_evidence_protein": n["evidence_protein"],
        "n_evidence_na": n["evidence_na"],
        "n_techniques": len(present_techs),
        "n_techniques_protein": sum(1 for t in present_techs if tech_proteins[t]),
        "n_techniques_na": sum(1 for t in present_techs if tech_molecules[t] > tech_proteins[t]),
        "n_techniques_taxonomy": len(technique_ids),
        "n_sources": len(source_evidence),
        "n_sources_protein": sum(1 for s in source_evidence if source_proteins[s]),
        "n_stub_sources": len(STUB_SOURCES),
        "n_curated": n["curated"],
        "n_curated_protein": n["curated_protein"],
        "n_curated_na": n["curated_na"],
        "n_uncurated": n_uncurated,
        "n_states": n["states"],
        "n_states_protein": n["states_protein"],
        "n_states_na": n["states_na"],
        "n_states_observed": n["states_observed"],
        "n_states_inferred": n["states_inferred"],
        "n_mapped": n["mapped"],
        "n_mapped_protein": n["mapped_protein"],
        "n_mapped_na": n["mapped_na"],
        "n_unmapped": n["unmapped"],
        "n_ambiguous": n["ambiguous"],
        "n_mapped_by_assignment": n["mapped_by_assignment"],
        "n_mapped_by_rule": n["mapped_by_rule"],
        "n_conflicts": n["conflicts"],
        "n_conflicts_protein": n["conflicts_protein"],
        "n_conflicts_na": n["conflicts_na"],
        "n_uncompared": n["uncompared"],
        "n_single_method_states": n["single_method_states"],
        "n_transitions": n["transitions"],
        "n_models": n["models"],
    }
    stats: dict = {
        "release": release,
        "sources": {},
        "techniques": {},
        "conflicts": {"removed_by_ion_rule": {"protein": removed_by_ion_rule["protein"],
                                              "na": removed_by_ion_rule["na"]}},
        "p37840": p37840,
        "na": na,
        "g4": g4,
        "single_method": single_method,
    }
    for name, key in SOURCE_KEYS.items():
        if key in OPTIONAL_SOURCE_KEYS and not source_evidence[name] and not _module_ran(key):
            continue
        stats["sources"][key] = {"n_molecules": source_molecules[name], "n_proteins": source_proteins[name],
                                 "n_evidence": source_evidence[name]}
    for tid in technique_ids:
        stats["techniques"][tid] = {"n_evidence": tech_evidence[tid], "n_molecules": tech_molecules[tid],
                                    "n_proteins": tech_proteins[tid], "n_evidence_protein": tech_evidence_protein[tid]}

    # Redistributable download must not silently disagree with the map for sources it includes.
    if ALL_RECORDS.exists():
        _check_all_records(stats, list(molecules))
    return stats


def _module_ran(key: str) -> bool:
    """A source module ran in this release when it left raw files."""
    return any((REPO / "data" / "raw" / key).glob("*.json"))


def _g4(mapped: dict) -> dict:
    """G-quadruplex states by topology: evidence count, the ions on that evidence, representative entry."""
    cur = yaml.safe_load((CURATION / f"{NA_SLUGS['g4']}.yaml").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in cur["states"]}
    if set(G4_STATES.values()) - set(by_id):
        raise SystemExit(f"stats: G-quadruplex curation lacks states {sorted(set(G4_STATES.values()) - set(by_id))}")
    states = {}
    for slug, sid in G4_STATES.items():
        evs = [ev for ev in mapped["evidence"] if any(m["state_id"] == sid for m in ev["mappings"])]
        ions = Counter(i["ion"] for ev in evs for i in ev["conditions"].get("ions") or [])
        states[slug] = {
            "n_evidence": len(evs),
            "n_techniques": len({ev["technique"] for ev in evs}),
            "techniques": ", ".join(sorted({ev["technique"] for ev in evs})),
            "ions": ", ".join(sorted(ions)) or "none stated",
            "n_with_k": sum(1 for ev in evs if any(i["ion"] == "K+" for i in ev["conditions"].get("ions") or [])),
            "n_with_na": sum(1 for ev in evs if any(i["ion"] == "Na+" for i in ev["conditions"].get("ions") or [])),
            "basis": by_id[sid]["basis"],
            "representative_pdb": by_id[sid].get("representative_pdb"),
        }
    return {"states": states}


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
            f"stats: all-records.jsonl has {n} redistributable evidence items; "
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
            "type": mol.get("molecule_type", "protein"),
            "evidence": len(evidence),
            "states": len(mapped["states"]),
            "techs": {ev["technique"] for ev in evidence},
            "sources": {ev["provenance"]["source"] for ev in evidence},
        })
    return {
        "molecules": len(summaries),
        "proteins": sum(1 for s in summaries if s["type"] == "protein"),
        "RNAs": sum(1 for s in summaries if s["type"] == "rna"),
        "DNAs": sum(1 for s in summaries if s["type"] == "dna"),
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
    for label, key in (("molecules", "n_molecules"), ("proteins", "n_proteins"), ("RNAs", "n_rna"), ("DNAs", "n_dna"),
                       ("evidence entries", "n_evidence"), ("techniques", "n_techniques"), ("sources", "n_sources"),
                       ("curated states", "n_states")):
        if home.get(label) != rel[key]:
            errors.append(f"site home {label}: page has {home.get(label)}, stats release.{key} is {rel[key]}")
    for mol_id in NA_SLUGS.values():
        if not (SITE / "protein" / mol_id / "index.html").exists():
            errors.append(f"site page for {mol_id} missing")
    if not (SITE / "molecules" / "index.html").exists():
        errors.append("site Molecules page missing")
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
        if tag != f"v{VERSION}":
            errors.append(f"HEAD is not tagged v{VERSION} (git describe says {tag!r})")
        if not stats["release"]["commit"]:
            errors.append("could not read the release commit")
        for err in errors:
            print(f"stats --check: {err}", file=sys.stderr)
        if errors:
            return 1
        rel = stats["release"]
        print(f"stats --check: site agrees ({rel['n_molecules']} molecules: {rel['n_proteins']} proteins, "
              f"{rel['n_rna']} RNA, {rel['n_dna']} DNA; {rel['n_evidence']} evidence)", file=sys.stderr)
    else:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
