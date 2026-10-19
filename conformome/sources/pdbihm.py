"""PDB-IHM: integrative models, including FRET-restrained ensembles.

Status: partly covered. Integrative entries distributed through the PDB are ingested by the `pdb`
source with technique `integrative`. Still to do: the restraint tables in the PDB-IHM mmCIF files,
so that an integrative model can list the evidence it was fitted to as constraints_used.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "PDB-IHM"
IMPLEMENTED = False
