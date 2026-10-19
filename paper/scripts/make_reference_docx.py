#!/usr/bin/env python3
"""Build style2/reference.docx: a plain, journal-style Word template for pandoc.

Times New Roman 12 pt, 1.5 line spacing, black bold headings (no Word theme colours),
left-aligned title, small table text, numbered reference list at 11 pt.
"""
import sys
from pathlib import Path

import docx
import docx.enum.style
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

src, out = Path(sys.argv[1]), Path(sys.argv[2])
d = docx.Document(src)
BLACK = RGBColor(0, 0, 0)
FONT = "Times New Roman"


def font(style, size=None, bold=None, italic=None, color=BLACK, name=FONT):
    f = style.font
    f.name = name
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color is not None: f.color.rgb = color


def para(style, before=0, after=6, line=1.5, align=None, indent_first=None, keep_next=None):
    pf = style.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line
    if align is not None: pf.alignment = align
    if indent_first is not None: pf.first_line_indent = indent_first
    if keep_next is not None: pf.keep_with_next = keep_next


S = {s.name: s for s in d.styles}
for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text"):
    font(S[name], 12)
    para(S[name], after=8)
para(S["Compact"], after=2)

font(S["Title"], 17, bold=True)
para(S["Title"], before=0, after=18, line=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
font(S["Author"], 12)
para(S["Author"], after=4, line=1.3, align=WD_ALIGN_PARAGRAPH.LEFT)

for name, size, b, i, before in (("Heading 1", 14, True, False, 20), ("Heading 2", 12, True, False, 14),
                                 ("Heading 3", 12, False, True, 10), ("Heading 4", 12, False, True, 8)):
    font(S[name], size, bold=b, italic=i)
    para(S[name], before=before, after=6, line=1.15, keep_next=True)

font(S["Bibliography"], 11)
para(S["Bibliography"], after=4, line=1.15)
for name in ("Caption", "Table Caption", "Image Caption"):
    font(S[name], 11, italic=False)
    para(S[name], before=6, after=6, line=1.15)

note = S["Table Note"] if "Table Note" in S else d.styles.add_style("Table Note", docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
note.base_style = S["Normal"]
font(note, 10)
para(note, before=4, after=12, line=1.15)

# hyperlinks: dark blue, no underline
if "Hyperlink" in S:
    h = S["Hyperlink"]
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x68)
    h.font.underline = False

# page: A4, 2.5 cm margins
for sec in d.sections:
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(2.5))

d.save(out)
print("wrote", out)
