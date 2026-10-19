"""Literature: CD, HDX, smFRET, DEER and others without a deposit.

Status: stub. Planned: Europe PMC full text, LLM-assisted extraction that stores the exact sentence
or table cell used (evidence span), then human review. Nothing extracted goes live unreviewed
during the pilot: records are written with status "draft" and excluded from the site until a
curator marks them reviewed.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "Literature (Europe PMC)"
IMPLEMENTED = False
