#!/usr/bin/env bash
# Build the manuscript. Run from anywhere:  bash paper/scripts/build.sh [--skip-network]
# Gates first (numbers, lint, citations), then figures and pandoc outputs.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(cd .. && pwd)"
# Prefer the repo venv so `python -I` still sees matplotlib and the others.
if [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
  export PATH="$ROOT/.venv/Scripts:$PATH"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  export PATH="$ROOT/.venv/bin:$PATH"
fi
PY="python -X utf8"
mkdir -p out figures

$PY -I scripts/stats.py --check > out/stats.json
$PY -I scripts/fill_numbers.py --check
$PY -I scripts/lint_manuscript.py
$PY -I scripts/make_bib.py --renumber
$PY -I scripts/make_bib.py
$PY -I scripts/make_bib.py --check
[[ "${1:-}" == "--skip-network" ]] || $PY -I scripts/check_dois.py
for f in fig1_model fig2_coverage fig4_pipeline; do $PY scripts/$f.py; done
[[ -f figures/_screens/states.png ]] || $PY scripts/fig3_screens.py
$PY scripts/fig3_screens.py --compose
COMMON=(out/manuscript.pandoc.md --citeproc --bibliography references.bib --csl open-research-europe.csl)
pandoc "${COMMON[@]}" --reference-doc reference.docx -o out/manuscript.docx
pandoc "${COMMON[@]}" --pdf-engine=xelatex -V geometry:margin=25mm -V fontsize=12pt -V linestretch=2 \
  -V mainfont="Liberation Sans" -V fontfamily=helvet -H scripts/lineno.tex -o out/manuscript.pdf
$PY scripts/figures_preview.py
pandoc out/figures_preview.md --pdf-engine=xelatex -V geometry:margin=20mm -V mainfont="Liberation Sans" -V fontfamily=helvet -o out/figures_preview.pdf
echo "build OK: out/manuscript.docx out/manuscript.pdf out/figures_preview.pdf"
