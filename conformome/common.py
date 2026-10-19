"""Shared paths, cached HTTP, download manifest and schema helpers."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

REPO_ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "conformome/0.1 (https://conformome.org)"
_last_request = [0.0]


@dataclass(frozen=True)
class Paths:
    """Every directory the pipeline reads or writes. Tests point these at fixtures."""

    raw: Path  # downloaded inputs (git-ignored)
    curation: Path  # hand-written, reviewed YAML
    build: Path  # generated records (git-ignored)
    site: Path  # generated static site (git-ignored)
    schema: Path
    taxonomy: Path
    docs: Path
    manifest: Path  # committed download manifest


def default_paths() -> Paths:
    root = REPO_ROOT
    return Paths(
        raw=root / "data" / "raw",
        curation=root / "curation",
        build=root / "build",
        site=root / "site" / "dist",
        schema=root / "schema",
        taxonomy=root / "taxonomy",
        docs=root / "docs",
        manifest=root / "data" / "MANIFEST.json",
    )


def today() -> str:
    return dt.date.today().isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fetch_url(url: str, *, body: bytes | None = None, headers: dict | None = None,
              cache_dir: Path | None = None, throttle: float = 0.15, retries: int = 4) -> bytes:
    """GET (or POST when body is given) with on-disk caching, throttling and backoff."""
    key = sha256_bytes((url + "\n").encode() + (body or b""))
    cached = cache_dir / f"{key}.bin" if cache_dir else None
    if cached and cached.exists():
        return cached.read_bytes()

    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    req_headers.update(headers or {})
    delay = 2.0
    for attempt in range(retries + 1):
        wait = throttle - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.monotonic()
        try:
            req = urllib.request.Request(url, data=body, headers=req_headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            break
        except urllib.error.HTTPError as err:
            if err.code < 500 and err.code != 429 or attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(delay)
        delay *= 2
    if cached:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


def record_download(paths: Paths, rel: str, urls: list[str], data: bytes) -> None:
    """Write-through manifest: every raw file is listed with its URLs, date and SHA-256."""
    manifest = read_json(paths.manifest) if paths.manifest.exists() else {}
    manifest[rel] = {"urls": urls, "retrieved": today(), "sha256": sha256_bytes(data), "bytes": len(data)}
    write_json(paths.manifest, manifest)


def load_validators(schema_dir: Path) -> dict[str, Draft202012Validator]:
    """One validator per record type, with the shared common.schema.json resolvable by $ref."""
    schemas = {p.stem.replace(".schema", ""): read_json(p) for p in sorted(schema_dir.glob("*.schema.json"))}
    registry = Registry().with_resources(
        (s["$id"], Resource.from_contents(s, default_specification=DRAFT202012)) for s in schemas.values()
    )
    return {name: Draft202012Validator(s, registry=registry) for name, s in schemas.items() if name != "common"}


def load_taxonomy(path: Path) -> dict[str, dict]:
    data = load_yaml(path)
    return {t["id"]: t for t in data["techniques"]}


def check(validator: Draft202012Validator, record: dict) -> list[str]:
    """Return human-readable schema errors (empty when the record is valid)."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in validator.iter_errors(record)]
