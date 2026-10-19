"""Mapping rules. Each returns mapping records; nothing here decides silently.

curator_assignment  the curator named the evidence and the state (who = curator:<name>)
anchor_rmsd         a structure clusters with an anchor when its C-alpha RMSD, after
                    superposition on shared residues, is within a cut-off (who = rule:anchor_rmsd).
                    rmsd_ca() is implemented and tested; it is not yet wired to coordinate
                    downloads for the pilot (see docs/PILOT_REPORT.md).
"""

from __future__ import annotations

import numpy as np


def curator_assignment(curator: str, state_id: str, confidence: str, justification: str) -> dict:
    return {
        "state_id": state_id,
        "who": f"curator:{curator}",
        "confidence": confidence,
        "justification": justification,
        "rule": "curator_assignment",
    }


def rmsd_ca(coords_a: np.ndarray, coords_b: np.ndarray) -> float:
    """C-alpha RMSD after optimal superposition (Kabsch). Inputs are (N, 3) arrays of matched atoms."""
    a = np.asarray(coords_a, dtype=float)
    b = np.asarray(coords_b, dtype=float)
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"need matched (N, 3) arrays, got {a.shape} and {b.shape}")
    if len(a) < 3:
        raise ValueError("at least three matched atoms are needed to superpose")
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    d = np.sign(np.linalg.det(u @ vt))
    correction = np.diag([1.0, 1.0, d])
    rotation = u @ correction @ vt
    diff = a @ rotation - b
    return float(np.sqrt((diff ** 2).sum() / len(a)))


def anchor_rmsd(coords: np.ndarray, anchor: np.ndarray, cutoff: float) -> tuple[bool, float]:
    value = rmsd_ca(coords, anchor)
    return value <= cutoff, value
