#!/usr/bin/env python3
"""Coverage figure (legend "Figure 3"). Molecule x technique matrix from the map output of the frozen release.

Rows are grouped by molecule type (proteins, then RNA, then DNA) and, within proteins, by curation
status; each group is ordered by total evidence. site/dist/downloads/all-records.jsonl omits sources
that are not redistributed (SMASH-BIO). The site's own matrix is built from build/<acc>/mapped.json,
and so is this figure. The output file is still figures/fig2_coverage.*; the submission package
copies it to Figure3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import COL2, INK, BLUE_DARK, save  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build"
TECHNIQUES_YAML = REPO / "taxonomy" / "techniques.yaml"
CURATION = REPO / "curation"
MM = 1 / 25.4


# Nucleic acids have no gene symbol. Short labels for the six pilot molecules; anything else
# falls back to the first words of the molecule name.
NA_LABELS = {
    "URS000080DF85_672": "add riboswitch",
    "URS000080E020_32630": "preQ1 riboswitch",
    "URS000080E14B_11676": "HIV-1 TAR",
    "URS000080E052_32630": "P4-P6 domain",
    "URS00021ED9B3_2697049": "SARS-CoV-2 FSE",
    "DNA-6f16b68e4fba": "telomeric G4",
}


def _short_name(acc: str, name: str) -> str:
    if acc in NA_LABELS:
        return NA_LABELS[acc]
    short = name.split(",")[0].split("(")[0].strip()
    return short if len(short) <= 16 else short[:15].rstrip() + "…"


def main() -> None:
    order = [t["id"] for t in yaml.safe_load(TECHNIQUES_YAML.read_text(encoding="utf-8"))["techniques"]]
    curated = {p.stem for p in CURATION.glob("*.yaml")}
    rows = []
    for mapped_path in sorted(BUILD.glob("*/mapped.json")):
        acc = mapped_path.parent.name
        mol = json.loads((mapped_path.parent / "molecule.json").read_text(encoding="utf-8"))
        mtype = mol.get("molecule_type") or "protein"
        evidence = json.loads(mapped_path.read_text(encoding="utf-8"))["evidence"]
        if not evidence:
            continue
        counts = {t: 0 for t in order}
        for ev in evidence:
            counts[ev["technique"]] += 1
        if mtype == "protein":
            label = str(mol.get("gene") or acc)
        else:
            # Nucleic acids have no gene symbol; use a short form of the molecule name.
            label = _short_name(acc, mol.get("name") or acc)
        rows.append({"acc": acc, "label": label, "type": mtype, "curated": acc in curated,
                     "counts": counts, "total": len(evidence)})
    if not rows:
        raise SystemExit("fig2: no evidence under build/")
    present = [t for t in order if any(r["counts"][t] for r in rows)]
    by_total = lambda r: -r["total"]  # noqa: E731
    curated_rows = sorted((r for r in rows if r["type"] == "protein" and r["curated"]), key=by_total)
    rest_rows = sorted((r for r in rows if r["type"] == "protein" and not r["curated"]), key=by_total)
    rna_rows = sorted((r for r in rows if r["type"] == "rna"), key=by_total)
    dna_rows = sorted((r for r in rows if r["type"] == "dna"), key=by_total)
    groups = [g for g in (curated_rows, rest_rows, rna_rows, dna_rows) if g]
    ordered = [r for g in groups for r in g]

    matrix = np.array([[r["counts"][t] for t in present] for r in ordered], dtype=float)
    vmax = matrix.max()
    shade = np.zeros_like(matrix)
    positive = matrix > 0
    shade[positive] = np.log10(matrix[positive]) / np.log10(vmax)
    cmap = LinearSegmentedColormap.from_list("cov", ["#f7fbff", "#6eaed6", BLUE_DARK])
    cmap.set_bad("white")
    display = np.ma.masked_where(~positive, shade)

    n_rows, n_cols = matrix.shape
    # 7 pt row labels need about 2.6 mm of height so they do not collide.
    # Room below for the rotated technique ids and on the left for the longest row label.
    height_mm = 28 + n_rows * 2.7 + 22
    fig = plt.figure(figsize=(COL2, height_mm * MM))
    # Left labels, matrix, right bar. Top bar sits above the matrix.
    gs = fig.add_gridspec(2, 3, height_ratios=[0.9, n_rows * 0.18], width_ratios=[2.6, n_cols, 1.3],
                          hspace=0.05, wspace=0.04, left=0.01, right=0.98, top=0.98, bottom=0.085)
    ax_bar = fig.add_subplot(gs[0, 1])
    ax = fig.add_subplot(gs[1, 1])
    ax_right = fig.add_subplot(gs[1, 2], sharey=ax)
    fig.add_subplot(gs[0, 0]).axis("off")
    fig.add_subplot(gs[0, 2]).axis("off")
    fig.add_subplot(gs[1, 0]).axis("off")

    ax.imshow(display, cmap=cmap, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(present, rotation=90, ha="center", va="top", fontsize=7)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([r["label"] for r in ordered], fontsize=7)
    ax.tick_params(length=0, pad=1)
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color(INK)
        sp.set_linewidth(0.4)
    # A rule between each group: curated proteins | other proteins | RNA | DNA.
    boundary = -0.5
    for group in groups[:-1]:
        boundary += len(group)
        ax.axhline(boundary, color=INK, lw=0.6)
    # Nucleic-acid labels in italics so the type groups read at a glance.
    for tick, row in zip(ax.get_yticklabels(), ordered):
        if row["type"] != "protein":
            tick.set_fontstyle("italic")

    molecules_per_tech = (matrix > 0).sum(axis=0)
    ax_bar.bar(range(n_cols), molecules_per_tech, color="#2f6fa8", width=0.8)
    ax_bar.set_xlim(-0.5, n_cols - 0.5)
    ax_bar.set_ylabel("Molecules", fontsize=7)
    ax_bar.tick_params(labelbottom=False, length=0)
    ax_bar.set_xticks([])
    ax_bar.spines["bottom"].set_visible(False)

    totals = [r["total"] for r in ordered]
    ax_right.barh(range(n_rows), totals, color="#2f6fa8", height=0.8)
    ax_right.set_ylim(n_rows - 0.5, -0.5)
    ax_right.set_xlabel("Evidence", fontsize=7)
    ax_right.tick_params(labelleft=False, labelsize=7, length=2)
    ax_right.spines["left"].set_visible(False)

    save(fig, "fig2_coverage")


if __name__ == "__main__":
    main()
