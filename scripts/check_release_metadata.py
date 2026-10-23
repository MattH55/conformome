#!/usr/bin/env python3
"""Check that the Zenodo deposit and its metadata agree with each other and with the build.

Run after scripts/make_data_release.py (make zenodo-prep does both). Exits 1 on any error.
ORCID and DOI placeholders are warnings, so the deposit can be reviewed before the author
fills them in; the upload script refuses to run while they remain.

Checked:
  .zenodo.json, CITATION.cff and release_meta/zenodo_data_metadata.json parse;
  one version string across those files, release/README.md and paper/out/stats.json;
  the software licence matches LICENSE, the data licence matches release/LICENSE;
  the counts in release/README.md and in the metadata description equal a fresh count of build/;
  paper/out/stats.json and build/BUILD.json name the same commit;
  no file in release/ holds evidence outside the licence allow-list (re-scanned, not trusted);
  SHA256SUMS verifies and names every other file in release/.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import yaml

from conformome.common import default_paths, read_json
from conformome.validate import _forbidden_source, _redistribution, allowed_source_names

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
META = ROOT / "release_meta" / "zenodo_data_metadata.json"
STATS = ROOT / "paper" / "out" / "stats.json"
PLACEHOLDERS = ("0000-0000-0000-0000", "SOFTWARE_VERSION_DOI", "DATA_VERSION_DOI")


def _build_counts(paths) -> dict:
    """The same totals make_data_release.py prints, recounted from build/."""
    policy = _redistribution(paths)
    allowed = allowed_source_names(paths)
    allowed_licences = set(policy["allow"])
    deny_phrases = policy["deny_if_contains"]
    deny_sources = set(policy["deny_sources"])
    counts = {"molecules": 0, "proteins": 0, "rna": 0, "dna": 0, "corpus": 0, "archived": 0,
              "curated": 0, "states": 0}
    for folder in sorted(paths.build.iterdir()):
        if not (folder / "molecule.json").exists() or not (folder / "mapped.json").exists():
            continue
        molecule = read_json(folder / "molecule.json")
        mapped = read_json(folder / "mapped.json")
        counts["molecules"] += 1
        counts[{"protein": "proteins", "rna": "rna", "dna": "dna"}.get(molecule.get("molecule_type") or "protein", "proteins")] += 1
        counts["states"] += len(mapped.get("states") or [])
        if (mapped.get("curation") or {}).get("status") not in {None, "uncurated"}:
            counts["curated"] += 1
        for ev in mapped.get("evidence") or []:
            counts["corpus"] += 1
            if _forbidden_source(ev, allowed, allowed_licences, deny_phrases, deny_sources) is None:
                counts["archived"] += 1
    return counts


def _readme_counts(text: str) -> dict:
    def grab(pattern: str) -> int | None:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None
    return {
        "molecules": grab(r"- molecules: (\d+)"),
        "proteins": grab(r"\((\d+) proteins"),
        "rna": grab(r"(\d+) RNA,"),
        "dna": grab(r"(\d+) DNA\)"),
        "corpus": grab(r"evidence entries, corpus: (\d+)"),
        "archived": grab(r"evidence entries, archived: (\d+)"),
        "curated": grab(r"curated molecules: (\d+)"),
        "states": grab(r"; states: (\d+)"),
    }


def _numbers(text: str) -> set[int]:
    return {int(n.replace(",", "")) for n in re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+\b", text)}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    paths = default_paths()

    # Parse the three metadata files.
    try:
        zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f".zenodo.json: {exc}")
        zenodo = {}
    try:
        cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8")) or {}
        for key in ("cff-version", "title", "authors", "version", "license"):
            if key not in cff:
                errors.append(f"CITATION.cff: missing {key}")
    except Exception as exc:
        errors.append(f"CITATION.cff: {exc}")
        cff = {}
    try:
        meta = json.loads(META.read_text(encoding="utf-8"))["metadata"]
    except Exception as exc:
        errors.append(f"{META.relative_to(ROOT)}: {exc}")
        meta = {}

    readme_path = RELEASE / "README.md"
    if not readme_path.exists():
        errors.append("release/README.md is missing; run scripts/make_data_release.py first")
        print("\n".join(f"ERROR {e}" for e in errors))
        return 1
    readme = readme_path.read_text(encoding="utf-8")

    # One version everywhere.
    versions = {
        ".zenodo.json": zenodo.get("version"),
        "CITATION.cff": str(cff.get("version") or ""),
        "release_meta/zenodo_data_metadata.json": meta.get("version"),
    }
    match = re.search(r"^# Conformome pilot release v(\S+):", readme, flags=re.M)
    versions["release/README.md"] = match.group(1) if match else None
    stats = read_json(STATS) if STATS.exists() else None
    if stats is None:
        warnings.append("paper/out/stats.json is missing; run paper/scripts/stats.py")
    else:
        tag = (stats.get("release") or {}).get("tag") or ""
        if tag:
            versions["paper/out/stats.json release.tag"] = tag.lstrip("v")
        else:
            warnings.append("paper/out/stats.json release.tag is empty: the release is not tagged yet")
    distinct = {v for v in versions.values()}
    if len(distinct) != 1 or None in distinct:
        errors.append("version strings differ: " + ", ".join(f"{k}={v!r}" for k, v in versions.items()))

    # Licences.
    software_licence = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").exists() else ""
    if zenodo.get("license") != "MIT" or "MIT License" not in software_licence:
        errors.append(f".zenodo.json license {zenodo.get('license')!r} does not match LICENSE")
    if cff.get("license") != zenodo.get("license"):
        errors.append(f"CITATION.cff license {cff.get('license')!r} differs from .zenodo.json")
    data_licence = (RELEASE / "LICENSE").read_text(encoding="utf-8") if (RELEASE / "LICENSE").exists() else ""
    if meta.get("license") != "cc-by-4.0" or "Attribution 4.0" not in data_licence:
        errors.append(f"data licence {meta.get('license')!r} does not match release/LICENSE")
    if "legal code was not downloaded" in data_licence:
        warnings.append("release/LICENSE is a pointer, not the CC BY 4.0 legal code")

    # Counts: README and metadata description against a recount of build/.
    build = _build_counts(paths)
    shown = _readme_counts(readme)
    for key, value in build.items():
        if shown.get(key) != value:
            errors.append(f"release/README.md {key}: shows {shown.get(key)}, build/ has {value}")
    description = re.sub(r"<[^>]+>", " ", meta.get("description") or "")
    in_description = _numbers(description)
    for key in ("molecules", "proteins", "corpus", "archived", "curated", "states"):
        if build[key] not in in_description:
            errors.append(f"metadata description does not state {key} = {build[key]}")

    # The build behind the numbers.
    build_json = paths.build / "BUILD.json"
    if stats is not None and build_json.exists():
        built = read_json(build_json).get("git_commit")
        recorded = (stats.get("release") or {}).get("commit")
        if built != recorded:
            errors.append(f"build/BUILD.json commit {built} differs from stats.json release.commit {recorded}")

    # Re-scan every evidence record in the deposit.
    policy = _redistribution(paths)
    allowed = allowed_source_names(paths)
    allowed_licences = set(policy["allow"])
    deny_phrases = policy["deny_if_contains"]
    deny_sources = set(policy["deny_sources"])

    def scan(where: str, record: dict) -> None:
        source = _forbidden_source(record, allowed, allowed_licences, deny_phrases, deny_sources)
        if source:
            errors.append(f"{where}: evidence from {source} is not redistributable")

    jsonl = RELEASE / "all-records.jsonl"
    if jsonl.exists():
        for n, line in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), 1):
            record = json.loads(line)
            if record.get("record_type") == "evidence":
                scan(f"all-records.jsonl line {n}", record)
    for name in ("molecules.zip", "profiles.zip"):
        path = RELEASE / name
        if not path.exists():
            errors.append(f"release/{name} is missing")
            continue
        with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as zf:
            for member in zf.namelist():
                payload = json.loads(zf.read(member))
                if name == "molecules.zip":
                    for ev in payload.get("evidence") or []:
                        scan(f"{name}:{member} {ev.get('evidence_id')}", ev)
                else:
                    scan(f"{name}:{member}", payload)

    # Checksums.
    sums_path = RELEASE / "SHA256SUMS"
    if not sums_path.exists():
        errors.append("release/SHA256SUMS is missing")
    else:
        listed: dict[str, str] = {}
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            digest, _, name = line.partition("  ")
            listed[name.strip()] = digest
        present = {p.name for p in RELEASE.iterdir() if p.is_file() and p.name != "SHA256SUMS"}
        for name in sorted(present - set(listed)):
            errors.append(f"SHA256SUMS does not list release/{name}")
        for name, digest in listed.items():
            path = RELEASE / name
            if not path.exists():
                errors.append(f"SHA256SUMS lists a missing file: {name}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append(f"SHA256SUMS mismatch for {name}")

    # Placeholders the author fills in.
    for label, text in (("release/README.md", readme),
                        ("release_meta/zenodo_data_metadata.json", json.dumps(meta)),
                        (".zenodo.json", json.dumps(zenodo)),
                        ("CITATION.cff", json.dumps(cff))):
        for token in PLACEHOLDERS:
            if token in text:
                warnings.append(f"{label} still holds the placeholder {token}")

    for line in warnings:
        print(f"WARNING {line}")
    for line in errors:
        print(f"ERROR {line}")
    print(f"check_release_metadata: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
