"""BMRB: NMR chemical shifts, relaxation and dispersion data.

Status: stub. Planned: BMRB REST API lookup by UniProt-linked entries, then parse shifts and
relaxation/dispersion tables into `nmr_dynamics` (inferred) and `nmr_structure` (observed) evidence.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "BMRB"
IMPLEMENTED = False
