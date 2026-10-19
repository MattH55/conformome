"""One module per source. Import the module you need; see base.py for the contract."""

from conformome.sources import (
    alphafold, atlas, bmrb, disprot, literature, mddb, nakb, pdb, pdbihm, ped, rfam, sasbdb, smashbio,
)

REGISTRY = {
    "pdb": pdb,
    "bmrb": bmrb,
    "sasbdb": sasbdb,
    "disprot": disprot,
    "alphafold": alphafold,
    "mddb": mddb,
    "smashbio": smashbio,
    "nakb": nakb,
    "rfam": rfam,
    "ped": ped,
    "pdbihm": pdbihm,
    "atlas": atlas,
    "literature": literature,
}

IMPLEMENTED = [m for m in REGISTRY.values() if m.IMPLEMENTED]


def molecule_types(module) -> set[str]:
    """Molecule types a source is queried for; sources keyed on UniProt default to proteins."""
    return getattr(module, "MOLECULE_TYPES", {"protein"})


def for_type(mtype: str) -> list:
    return [m for m in IMPLEMENTED if mtype in molecule_types(m)]


# The source a page cannot be built without (the structure archive for that molecule type).
PRIMARY = {"protein": pdb, "rna": nakb, "dna": nakb}
