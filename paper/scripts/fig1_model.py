#!/usr/bin/env python3
"""Figure 1. Data model, drawn from the JSON Schema field names."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import COL2, INK, BLUE, BLUE_DARK, BLUE_LIGHT, BLUE_PALE, GREY, save  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[2] / "schema"


def schema(name: str) -> dict:
    return json.loads((SCHEMA / name).read_text(encoding="utf-8"))


def fields(doc: dict, *names: str) -> list[str]:
    """Field names must exist on the schema. A rename breaks the figure instead of drifting."""
    props = doc.get("properties") or {}
    missing = [n for n in names if n not in props]
    if missing:
        raise SystemExit(f"fig1: {doc.get('title')} has no fields {missing}")
    return list(names)


def box(ax, x, y, w, h, face, title, lines, title_color=INK):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
        facecolor=face, edgecolor=INK, linewidth=0.7, mutation_aspect=0.5,
    ))
    ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=8,
            fontweight="bold", color=title_color)
    line_h = 0.022
    for i, line in enumerate(lines):
        ax.text(x + 0.012, y + h - 0.042 - i * line_h, line, ha="left", va="top", fontsize=7, color=INK)


def main() -> None:
    molecule = schema("molecule.schema.json")
    state = schema("state.schema.json")
    evidence = schema("evidence.schema.json")
    transition = schema("transition.schema.json")
    model = schema("model.schema.json")
    mol_f = fields(molecule, "molecule_id", "name", "gene")
    st_f = fields(state, "state_id", "basis", "parent_state", "assumptions", "representative_model")
    ev_f = fields(evidence, "technique", "construct", "conditions", "observable", "provenance")
    obs = evidence["properties"]["observable"]
    for name in ("value", "uncertainty", "unit"):
        if name not in obs["properties"]:
            raise SystemExit(f"fig1: observable schema has no {name}")
    tr_f = fields(transition, "from_state", "to_state", "quantity")
    mo_f = fields(model, "state_id", "format", "basis")
    # The mapping lives on the evidence record, between evidence and state. Its fields are a shared definition.
    ref = evidence["properties"]["mappings"]["items"].get("$ref", "")
    if not ref.endswith("/mapping"):
        raise SystemExit(f"fig1: evidence.mappings items are not the mapping definition ({ref})")
    common = schema("common.schema.json")
    map_f = fields(common["$defs"]["mapping"], "who", "confidence", "justification")

    fig, ax = plt.subplots(figsize=(COL2, 150 * (1 / 25.4)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

    # Two columns. Arrows stay in the gaps, so no label crosses a box.
    left, right, col_w = 0.02, 0.58, 0.40
    box(ax, 0.28, 0.875, 0.44, 0.105, BLUE_PALE, "Protein", mol_f)
    box(ax, left, 0.68, col_w, 0.15, "#e7f2e7", "State · observed",
        [st_f[0], f"{st_f[1]} = observed", st_f[4]])
    box(ax, right, 0.68, col_w, 0.15, "#f8ecd4", "State · inferred",
        [st_f[0], f"{st_f[1]} = inferred", st_f[3]])
    ax.annotate("", xy=(right, 0.76), xytext=(left + col_w, 0.76),
                arrowprops=dict(arrowstyle="-|>", color=BLUE_DARK, lw=0.8))
    ax.text((left + col_w + right) / 2, 0.845, st_f[2], ha="center", va="bottom", fontsize=7, color=BLUE_DARK)

    box(ax, left, 0.50, col_w, 0.13, BLUE_LIGHT, "Model", [mo_f[0], mo_f[1], mo_f[2]])
    box(ax, right, 0.50, col_w, 0.13, "white", "Transition", tr_f)
    ax.annotate("", xy=(left + col_w / 2, 0.68), xytext=(left + col_w / 2, 0.63),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))
    ax.annotate("", xy=(right + col_w / 2, 0.68), xytext=(right + col_w / 2, 0.63),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=0.7))
    ax.annotate("", xy=(right, 0.56), xytext=(left + col_w, 0.56),
                arrowprops=dict(arrowstyle="<->", color=BLUE, lw=0.7))

    box(ax, left, 0.32, col_w, 0.13, "white", "Mapping", map_f)
    box(ax, right, 0.32, col_w, 0.13, "white", "Mapping", map_f)
    ax.annotate("", xy=(left + col_w / 2, 0.50), xytext=(left + col_w / 2, 0.45),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))
    ax.annotate("", xy=(right + col_w / 2, 0.50), xytext=(right + col_w / 2, 0.45),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))

    ev_lines = [ev_f[0], ev_f[1], ev_f[2], "value, uncertainty, unit", ev_f[4]]
    box(ax, left, 0.09, col_w, 0.17, BLUE_PALE, "Evidence", ev_lines)
    box(ax, right, 0.09, col_w, 0.17, BLUE_PALE, "Evidence", ev_lines)
    ax.annotate("", xy=(left + col_w / 2, 0.32), xytext=(left + col_w / 2, 0.26),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))
    ax.annotate("", xy=(right + col_w / 2, 0.32), xytext=(right + col_w / 2, 0.26),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7))

    # Conflict sits under the two evidence boxes, with a tick up into each.
    x1, x2 = left + col_w * 0.35, right + col_w * 0.65
    ax.plot([x1, x1, x2, x2], [0.09, 0.045, 0.045, 0.09], color="#8c2f2f", lw=0.8)
    ax.text((x1 + x2) / 2, 0.028, "Conflict", ha="center", va="top", fontsize=8,
            fontweight="bold", color="#8c2f2f")
    save(fig, "fig1_model")


if __name__ == "__main__":
    main()
