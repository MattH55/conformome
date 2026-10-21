"""Pure geometry for conformation records: no network, no files beyond the coordinate file passed in.

The central quantity is the contour length a conformation releases when it unfolds completely,

    ΔLc = n_structured × l_residue − d_ends

where n_structured is the number of residues (or nucleotides) between the first and last structured position,
l_residue is the contour length per residue of the unfolded chain, and d_ends is the distance between the two
positions at which the structured region meets the rest of the chain (the attachment points). This is the
quantity a force-extension curve measures as a step in contour length. Values of l_residue vary between
studies (0.36–0.40 nm per amino acid; about 0.59 nm per nucleotide for single-stranded RNA), so the value used
is always stored with the result, and the range is used to give the prediction an interval, not a point.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Contour length per residue of the unfolded chain, nm. (low, central, high).
RESIDUE_LENGTH_NM = {
    "protein": (0.36, 0.365, 0.40),
    "rna": (0.55, 0.59, 0.63),
    "dna": (0.55, 0.59, 0.63),
}
GEOMETRY_VERSION = "1"


@dataclass(frozen=True)
class Released:
    value: float  # central estimate, nm
    low: float
    high: float
    parameters: dict
    assumptions: list[str]


def contour_length_released(n_structured: int, end_to_end_nm: float | None, molecule_type: str) -> Released:
    """ΔLc for complete unfolding of a structured region of n_structured residues."""
    lo, mid, hi = RESIDUE_LENGTH_NM[molecule_type]
    assumptions = []
    d = end_to_end_nm
    if d is None:
        d = 0.0
        assumptions.append("End-to-end distance of the structured region unknown; taken as 0, so the value is an upper bound.")
    return Released(
        value=round(n_structured * mid - d, 2),
        low=round(n_structured * lo - d, 2),
        high=round(n_structured * hi - d, 2),
        parameters={"n_structured": n_structured, "end_to_end_nm": end_to_end_nm,
                    "residue_length_nm": {"low": lo, "central": mid, "high": hi}},
        assumptions=assumptions,
    )


def base_pairs(dot_bracket: str) -> list[tuple[int, int]]:
    """0-based (i, j) pairs from dot-bracket, including pseudoknot brackets and Aa..Zz pairs."""
    openers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    closers = {v: k for k, v in openers.items()}
    stacks: dict[str, list[int]] = {}
    pairs = []
    for i, ch in enumerate(dot_bracket):
        if ch in openers or (ch.isalpha() and ch.isupper()):
            stacks.setdefault(ch, []).append(i)
        elif ch in closers or (ch.isalpha() and ch.islower()):
            key = closers.get(ch, ch.upper())
            if not stacks.get(key):
                raise ValueError(f"unbalanced dot-bracket at position {i + 1}")
            pairs.append((stacks[key].pop(), i))
    if any(stacks.values()):
        raise ValueError("unbalanced dot-bracket: unclosed brackets")
    return sorted(pairs)


def segments_from_dot_bracket(dot_bracket: str, start: int = 1) -> list[dict]:
    """Runs of paired and unpaired positions, in the numbering that starts at `start`.

    '+' (G-quadruplex tetrad guanines) counts as paired.
    """
    paired = set()
    for i, j in base_pairs(dot_bracket):
        paired.update((i, j))
    paired.update(i for i, ch in enumerate(dot_bracket) if ch == "+")
    out = []
    for i in range(len(dot_bracket)):
        status = "paired" if i in paired else "unpaired"
        if out and out[-1]["status"] == status:
            out[-1]["end"] = start + i
        else:
            out.append({"start": start + i, "end": start + i, "status": status, "label": None})
    return out


def structured_span(segments: list[dict], structured: tuple[str, ...]) -> tuple[int, int] | None:
    """First and last position of any segment whose status counts as structured."""
    inside = [s for s in segments if s["status"] in structured]
    if not inside:
        return None
    return min(s["start"] for s in inside), max(s["end"] for s in inside)


def radius_of_gyration(points: list[tuple[float, float, float]]) -> float:
    n = len(points)
    cx, cy, cz = (sum(p[k] for p in points) / n for k in range(3))
    return math.sqrt(sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2 for p in points) / n)


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.dist(a, b)


@dataclass(frozen=True)
class ChainTrace:
    """One representative atom per residue (Cα for proteins, P or C4' for nucleic acids), in chain order."""
    chain: str
    numbers: list[int]  # author residue numbers
    points: list[tuple[float, float, float]]  # Å

    def segments(self) -> list[dict]:
        """Observed stretches (consecutive author numbers) and the gaps between them."""
        out: list[dict] = []
        for num in self.numbers:
            if out and num == out[-1]["end"] + 1:
                out[-1]["end"] = num
                continue
            if out and num > out[-1]["end"] + 1:
                out.append({"start": out[-1]["end"] + 1, "end": num - 1, "status": "unobserved", "label": None})
            out.append({"start": num, "end": num, "status": "folded", "label": None})
        return out


def trace_from_structure(path: str, entity_id: str | None, molecule_type: str, model_number: int = 1) -> ChainTrace | None:
    """Read one chain of the given PDB entity from an mmCIF or PDB file (requires gemmi)."""
    import gemmi

    st = gemmi.read_structure(path)
    st.setup_entities()
    model = st[model_number - 1]
    subchains = None
    if entity_id is not None:
        ent = next((e for e in st.entities if e.name == str(entity_id)), None)
        subchains = set(ent.subchains) if ent else None
    atom_names = ("CA",) if molecule_type == "protein" else ("P", "C4'")
    for chain in model:
        poly = chain.get_polymer()
        if not len(poly):
            continue
        if subchains is not None and poly.subchain_id() not in subchains:
            continue
        numbers, points = [], []
        for res in poly:
            atom = next((res.find_atom(n, "*") for n in atom_names if res.find_atom(n, "*")), None)
            if atom is None:
                continue
            numbers.append(res.seqid.num)
            points.append((atom.pos.x, atom.pos.y, atom.pos.z))
        if numbers:
            return ChainTrace(chain=chain.name, numbers=numbers, points=points)
    return None
