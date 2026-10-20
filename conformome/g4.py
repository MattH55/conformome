"""G-quadruplex strand topology from coordinates: a curator's aid, not a mapping rule.

Each G-tract's 5'->3' direction (first to last guanine C1') is projected on the stacking axis, the
direction of least spread of the tract guanines (tetrads are ~20 Å wide and ~7 Å tall). Four tracts
in one direction is parallel, 2+2 antiparallel, 3+1 hybrid. The pattern also gives the loop types
between successive tracts: same direction needs a propeller loop; opposite, a lateral or diagonal one.

    python -m conformome.g4 2,3,4 8,9,10 14,15,16 20,21,22 -- 1KF1.cif 143D.cif
"""

from __future__ import annotations

import sys

import numpy as np

TELOMERIC_22 = [(2, 3, 4), (8, 9, 10), (14, 15, 16), (20, 21, 22)]


def c1_positions(cif_text: str) -> dict[int, np.ndarray]:
    """C1' coordinates of the first model and first chain, keyed on label_seq_id (altloc A or none)."""
    cols, pos = [], {}
    model = chain = None
    for line in cif_text.splitlines():
        if line.startswith("_atom_site."):
            cols.append(line.strip().split(".", 1)[1])
            continue
        if not cols or not line.startswith(("ATOM", "HETATM")):
            if cols and pos and line.startswith("#"):
                break
            continue
        row = dict(zip(cols, line.split()))
        model = model or row["pdbx_PDB_model_num"]
        chain = chain or row["label_asym_id"]
        if row["pdbx_PDB_model_num"] != model or row["label_asym_id"] != chain:
            continue
        if row["label_atom_id"].strip('"') == "C1'" and row.get("label_alt_id", ".") in (".", "A"):
            pos[int(row["label_seq_id"])] = np.array([float(row[k]) for k in ("Cartn_x", "Cartn_y", "Cartn_z")])
    return pos


def topology(pos: dict[int, np.ndarray], tracts=TELOMERIC_22) -> dict:
    pts = np.array([pos[i] for t in tracts for i in t])
    axis = np.linalg.svd(pts - pts.mean(0))[2][2]
    proj = [float((pos[t[-1]] - pos[t[0]]) @ axis) for t in tracts]
    pattern = "".join("+" if (p > 0) == (proj[0] > 0) else "-" for p in proj)
    same = pattern.count("+")
    kind = {4: "parallel", 2: "antiparallel"}.get(max(same, len(tracts) - same), "hybrid")
    loops = ["propeller" if a == b else "lateral or diagonal" for a, b in zip(pattern, pattern[1:])]
    return {"pattern": pattern, "topology": kind, "loops": loops, "projections_A": [round(p, 1) for p in proj]}


def main(argv: list[str]) -> None:
    split = argv.index("--") if "--" in argv else 0
    tracts = [tuple(int(x) for x in t.split(",")) for t in argv[:split]] or TELOMERIC_22
    for path in argv[split + 1 if split else 0:]:
        with open(path, encoding="utf-8") as f:
            print(path, topology(c1_positions(f.read()), tracts))


if __name__ == "__main__":
    main(sys.argv[1:])
