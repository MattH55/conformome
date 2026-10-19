"""PDB-IHM: integrative models, including FRET-restrained ensembles, as mmCIF downloads.

Status: stub. Planned: index of PDB-IHM entries by UniProt, mmCIF parse of restraint tables.
Integrative models here are `inferred` and carry their restraints as constraints_used.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "PDB-IHM"
IMPLEMENTED = False
