from pathlib import Path

import pytest

from conformome.common import REPO_ROOT, Paths

FIXTURE = Path(__file__).parent / "fixtures" / "Q00000"


@pytest.fixture
def repo_paths(tmp_path) -> Paths:
    """The real schema, taxonomy and docs, with build and site written to a temporary directory."""
    return Paths(
        raw=tmp_path / "raw",
        curation=REPO_ROOT / "curation",
        build=tmp_path / "build",
        site=tmp_path / "site" / "dist",
        schema=REPO_ROOT / "schema",
        taxonomy=REPO_ROOT / "taxonomy",
        docs=REPO_ROOT / "docs",
        manifest=tmp_path / "MANIFEST.json",
    )


@pytest.fixture
def fixture_paths(tmp_path, repo_paths) -> Paths:
    """The synthetic fixture protein Q00000, with its own raw inputs and curation."""
    return Paths(
        raw=FIXTURE / "raw",
        curation=FIXTURE / "curation",
        build=tmp_path / "build",
        site=tmp_path / "site" / "dist",
        schema=repo_paths.schema,
        taxonomy=repo_paths.taxonomy,
        docs=repo_paths.docs,
        manifest=tmp_path / "MANIFEST.json",
    )
