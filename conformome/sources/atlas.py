"""ATLAS: molecular dynamics of representative PDB chains.

Status: stub. MD is ingested from MDDB (`mddb`); ATLAS indexes trajectories by ECOD chain, not by
UniProt, so a chain-to-accession lookup (SIFTS) is needed first.
"""

from conformome.sources.base import fetch, parse  # noqa: F401  (stubs raise NotImplementedSource)

NAME = "ATLAS"
IMPLEMENTED = False
