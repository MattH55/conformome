"""Molecule identity and nucleic-acid secondary structure.

Pages are keyed on a molecule ID (see schema/common.schema.json#/$defs/molecule_id):
UniProt for proteins, RNAcentral URS for RNA, DNA-<hash> for DNA structures without a
sequence database entry, CPX-<id> for complexes.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from conformome.common import load_yaml

UNIPROT = re.compile(r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})(-[0-9]+)?$")
RNACENTRAL = re.compile(r"^URS[0-9A-F]{10}(_[0-9]+)?$")

# Bracket pairs of extended dot-bracket notation; letters pair upper (open) with lower (close).
BRACKETS = {"(": ")", "[": "]", "{": "}", "<": ">"}
BRACKETS.update({c: c.lower() for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"})
CLOSERS = {v: k for k, v in BRACKETS.items()}


def molecule_type(molecule_id: str) -> str:
    """The molecule type implied by an ID's scheme. An unrecognised ID is not a protein."""
    if UNIPROT.fullmatch(molecule_id):
        return "protein"
    if re.fullmatch(r"URS[0-9A-F]{10}_[0-9]+", molecule_id):
        return "rna"
    if re.fullmatch(r"DNA-[0-9a-f]{12}", molecule_id):
        return "dna"
    if molecule_id.startswith("CPX-") and len(molecule_id) > 4:
        return "complex"
    raise ValueError(f"unrecognised molecule id {molecule_id!r}")


def dna_id(sequence: str) -> str:
    """Stable ID for a DNA structure keyed on its sequence: DNA- plus 12 hex digits of SHA-256."""
    seq = re.sub(r"\s+", "", sequence).upper()
    return "DNA-" + hashlib.sha256(seq.encode("ascii")).hexdigest()[:12]


def base_pairs(dot_bracket: str) -> list[tuple[int, int]]:
    """0-based (i, j) pairs. Raises ValueError on an unbalanced structure."""
    stacks: dict[str, list[int]] = {k: [] for k in BRACKETS}
    pairs = []
    for i, ch in enumerate(dot_bracket):
        if ch in BRACKETS:
            stacks[ch].append(i)
        elif ch in CLOSERS:
            opener = CLOSERS[ch]
            if not stacks[opener]:
                raise ValueError(f"unmatched '{ch}' at position {i + 1}")
            pairs.append((stacks[opener].pop(), i))
        elif ch not in ".+":
            raise ValueError(f"unknown character '{ch}' at position {i + 1}")
    for opener, stack in stacks.items():
        if stack:
            raise ValueError(f"unmatched '{opener}' at position {stack[0] + 1}")
    return sorted(pairs)


def secondary_structure_errors(ss: dict, sequence: str | None) -> list[str]:
    """Balance, length and (when the sequence is known) pairing checks for a state's dot-bracket."""
    db = ss["dot_bracket"]
    try:
        pairs = base_pairs(db)
    except ValueError as err:
        return [f"dot-bracket: {err}"]
    if not sequence:
        return []
    start = ss.get("start", 1)
    if start - 1 + len(db) > len(sequence):
        return [f"dot-bracket runs past the sequence end ({start - 1 + len(db)} > {len(sequence)})"]
    errors = []
    seq = sequence[start - 1:start - 1 + len(db)].upper().replace("T", "U")
    allowed = {"AU", "UA", "GC", "CG", "GU", "UG"}
    for i, j in pairs:
        if seq[i] + seq[j] not in allowed and "N" not in (seq[i], seq[j]):
            errors.append(f"dot-bracket pairs {seq[i]}{start + i} with {seq[j]}{start + j}, not a Watson-Crick or wobble pair")
    for i, ch in enumerate(db):
        if ch == "+" and seq[i] != "G":
            errors.append(f"dot-bracket marks {seq[i]}{start + i} as a tetrad guanine")
    return errors


def nucleic_acid_info(paths, molecule_id: str) -> dict:
    """Sequence, Rfam families and taxon of an RNA or DNA page, from the identity file download wrote."""
    from conformome import dna, rnacentral  # identity modules import sources, which import this module
    if molecule_type(molecule_id) == "rna":
        raw = rnacentral.load_raw(paths, molecule_id)
        if raw is None:
            raise FileNotFoundError(f"{molecule_id}: download the RNAcentral entry first")
        return {"type": "rna", "sequence": raw["entry"]["sequence"].upper(),
                "rfam": sorted({h["rfam"] for h in rnacentral.rfam_hits(raw)}), "taxid": rnacentral.split(molecule_id)[1]}
    raw = dna.load_raw(paths, molecule_id)
    if raw is None:
        raise FileNotFoundError(f"{molecule_id}: download the DNA anchor entry first")
    return {"type": "dna", "sequence": raw["sequence"], "rfam": [], "taxid": None}


def load_vocabularies(directory: Path) -> dict[str, dict]:
    """taxonomy/state_vocabularies/<id>.yaml, keyed on id."""
    return {(v := load_yaml(p))["id"]: v for p in sorted(directory.glob("*.yaml"))}


def family_label_errors(label: dict, vocabularies: dict[str, dict]) -> list[str]:
    vocab = vocabularies.get(label["vocabulary"])
    if vocab is None:
        return [f"family_label names unknown vocabulary {label['vocabulary']}"]
    axes = {a["id"]: {t["id"] for t in a["terms"]} for a in vocab["axes"]}
    errors = []
    for axis, term in label["terms"].items():
        if axis not in axes:
            errors.append(f"family_label: vocabulary {vocab['id']} has no axis {axis}")
        elif term not in axes[axis]:
            errors.append(f"family_label: {term} is not a term of {vocab['id']}/{axis}")
    return errors
