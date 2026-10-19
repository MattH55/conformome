"""One module per source. Import the module you need; see base.py for the contract."""

from conformome.sources import atlas, bmrb, literature, pdb, pdbihm, ped, sasbdb, smashbio

REGISTRY = {
    "pdb": pdb,
    "bmrb": bmrb,
    "sasbdb": sasbdb,
    "ped": ped,
    "pdbihm": pdbihm,
    "smashbio": smashbio,
    "atlas": atlas,
    "literature": literature,
}
