"""SMASH-BIO: force spectroscopy records and results.

Status: stub, blocked on an input. The SMASH-BIO repository (matth55/smash-bio) builds its release
files with hub/s07_build_site.py, but no release JSONL is present in the checkout this pipeline
was given (its out/ directory is generated, not committed). Planned: read a pinned release file
(path or URL and SHA-256 supplied in curation config), one evidence item per force-spectroscopy
result, technique `force_spectroscopy` (inferred). SMASH-BIO code is never copied in.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "SMASH-BIO"
IMPLEMENTED = False
