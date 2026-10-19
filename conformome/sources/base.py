"""The contract every source module follows.

A source module exposes:
    NAME          human-readable source name, as it appears in docs/SOURCES.md
    IMPLEMENTED   False until fetch and parse work end to end
    fetch(paths, accession, retrieved) -> raw   downloads and caches; writes to paths.raw
    parse(raw, accession, retrieved) -> [evidence dict]  pure function, no network

Parsed evidence is a dict that validates against schema/evidence.schema.json, with
an empty "mappings" list. Mapping to states happens later, in conformome.mapping.
"""

from __future__ import annotations


class NotImplementedSource(NotImplementedError):
    """Raised by stub sources. The message says what is missing."""


IMPLEMENTED = False


def fetch(paths, accession: str, retrieved: str):  # pragma: no cover - stub
    raise NotImplementedSource(f"{__name__}.fetch is not implemented yet")


def parse(raw, accession: str, retrieved: str):  # pragma: no cover - stub
    raise NotImplementedSource(f"{__name__}.parse is not implemented yet")
