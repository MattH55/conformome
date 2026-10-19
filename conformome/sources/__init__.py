"""One module per source. Import the module you need; see base.py for the contract."""

from conformome.sources import (
    alphafold, atlas, bmrb, disprot, literature, mddb, pdb, pdbihm, ped, sasbdb, smashbio,
)

REGISTRY = {
    "pdb": pdb,
    "bmrb": bmrb,
    "sasbdb": sasbdb,
    "disprot": disprot,
    "alphafold": alphafold,
    "mddb": mddb,
    "smashbio": smashbio,
    "ped": ped,
    "pdbihm": pdbihm,
    "atlas": atlas,
    "literature": literature,
}

IMPLEMENTED = [m for m in REGISTRY.values() if m.IMPLEMENTED]
