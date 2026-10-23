#!/usr/bin/env python3
"""Write out/figures_preview.md: each figure PNG followed by its legend, from manuscript.md."""
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
text = (PAPER / "manuscript.md").read_text(encoding="utf-8")
legends = text.partition("\n## Figure legends\n")[2].partition("\n## References")[0]
# Legend numbers (manuscript.md) -> script output names. The scripts predate the renumbering.
names = {1: "fig1_model", 2: "fig4_pipeline", 3: "fig2_coverage", 4: "fig3_screens"}
blocks = []
for m in re.finditer(r"\*\*Figure (\d)\. .*?(?=\n\n\*\*Figure|\Z)", legends.strip(), re.S):
    n = int(m.group(1))
    legend = re.sub(r"<!--.*?-->", "", m.group(0)).strip()
    blocks.append(f"![](../figures/{names[n]}.png){{width=100%}}\n\n{legend}\n\n\\newpage\n")
out = PAPER / "out" / "figures_preview.md"
out.parent.mkdir(exist_ok=True)
out.write_text("\n".join(blocks), encoding="utf-8", newline="\n")
print("figures_preview.md written")
