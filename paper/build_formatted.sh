#!/usr/bin/env bash
# Formatted build (citations from references.csl.json via citeproc; no make_bib step needed).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out build
python3 -I scripts/make_reference_docx.py style/ref_default.docx style/reference.docx
COMMON=(out/manuscript.filled.md --citeproc --bibliography references.csl.json --csl open-research-europe.csl)
python3 -I scripts/fill_numbers.py --render out/manuscript.filled.md 2>/dev/null || cp manuscript.md out/manuscript.filled.md
pandoc "${COMMON[@]}" --reference-doc style/reference.docx -o out/Conformome_ORE_manuscript.docx
python3 -I scripts/polish_docx.py out/Conformome_ORE_manuscript.docx
pandoc "${COMMON[@]}" --pdf-engine=xelatex -V papersize=a4 -V geometry:margin=27mm -V fontsize=11pt -V fontfamily=helvet \
  -V mainfont="TeX Gyre Pagella" -V sansfont="TeX Gyre Heros" -V monofont="DejaVu Sans Mono" -H style/preamble.tex \
  -o out/Conformome_ORE_manuscript.pdf 2> build/xelatex.log
! grep -i "missing character" build/xelatex.log
echo "build OK"
