"""PED: Protein Ensemble Database for disordered proteins.

Status: stub, blocked. The PED API paths tried (deposition.proteinensemble.org/api/v1/entries/...)
returned 404 or redirected to a broken path on 2026-10-19. PED ensembles that are also PDB
integrative entries are ingested through the `pdb` source.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "PED"
IMPLEMENTED = False
