#!/usr/bin/env python3
"""Figure 4. The build, with the release counts from paper/out/stats.json."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import COL2, INK, BLUE, BLUE_DARK, BLUE_LIGHT, BLUE_PALE, save, stats  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402


def box(ax, x, y, w, h, face, title, body):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015",
        facecolor=face, edgecolor=INK, linewidth=0.7,
    ))
    ax.text(x + w / 2, y + h - 0.06, title, ha="center", va="top", fontsize=8, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h / 2 - 0.04, body, ha="center", va="center", fontsize=7, color=INK, linespacing=1.3)


def arrow(ax, x1, x2, y):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=BLUE_DARK, lw=0.9))


def main() -> None:
    s = stats()["release"]
    src = stats()["sources"]
    fig, ax = plt.subplots(figsize=(COL2, 78 * (1 / 25.4)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.05)

    box(ax, 0.02, 0.52, 0.16, 0.40, BLUE_PALE, "Sources",
        f"{s['n_sources']} ingested\n"
        f"PDB {src['pdb']['n_evidence']:,}\n"
        f"BMRB {src['bmrb']['n_evidence']:,}\n"
        f"SMASH {src['smash']['n_evidence']:,}\n"
        f"+ {s['n_sources'] - 3} more")
    box(ax, 0.24, 0.52, 0.16, 0.40, "white", "make ingest",
        f"{s['n_evidence']:,}\nevidence\nrecords")
    box(ax, 0.46, 0.52, 0.22, 0.40, "white", "make map",
        f"{s['n_mapped']:,} mapped\n"
        f"{s['n_unmapped']:,} unmapped\n"
        f"{s['n_ambiguous']} ambiguous\n"
        f"{s['n_conflicts']} conflicts\n"
        f"{s['n_states']} states")
    box(ax, 0.74, 0.72, 0.22, 0.20, BLUE_LIGHT, "make models",
        f"{s['n_models']} model files")
    box(ax, 0.74, 0.52, 0.22, 0.16, BLUE, "make site",
        "pages + downloads")
    arrow(ax, 0.18, 0.24, 0.72)
    arrow(ax, 0.40, 0.46, 0.72)
    arrow(ax, 0.68, 0.74, 0.82)
    arrow(ax, 0.68, 0.74, 0.60)
    ax.text(0.50, 0.18,
            f"{s['n_proteins']} proteins  ·  {s['n_curated']} with draft curation  ·  "
            f"{s['n_techniques']} techniques with evidence  ·  "
            f"manifest dated {s['build_date']}",
            ha="center", va="center", fontsize=7, color=INK)
    ax.text(0.50, 0.08, "Counts are read from the frozen release (paper/out/stats.json).",
            ha="center", va="center", fontsize=7, color="#52606d")
    save(fig, "fig4_pipeline")


if __name__ == "__main__":
    main()
