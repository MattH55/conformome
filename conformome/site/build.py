"""Static site: index, protein, technique, about and downloads pages.

Every number and every table on the site is generated from build/ (mapped.json, models.json,
molecule.json), taxonomy/techniques.yaml, schema/ and docs/. Nothing here is hand-edited HTML.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from conformome.common import Paths, load_taxonomy, load_yaml, read_json, write_json
from conformome.sources import IMPLEMENTED, REGISTRY
from conformome.validate import sources_table

MOLSTAR_VERSION = "5.11.0"  # published 2026-07-19; at least two weeks old at the time of this build
MOLSTAR_BASE = f"https://cdn.jsdelivr.net/npm/molstar@{MOLSTAR_VERSION}/build/viewer/"
REPO_URL = "https://github.com/matth55/conformome"
MOLSTAR_FORMAT = {"PDB": "pdb", "mmCIF": "mmcif"}

CSS = """
:root{--bg:#fbfaf7;--surface:#ffffff;--fg:#1d1d1b;--muted:#5d5b55;--accent:#1f5a8a;--border:#d9d6cd;
--observed:#1e6b3a;--observed-bg:#e3f2e8;--inferred:#8a5a00;--inferred-bg:#fbefd6;--warn:#8a1f1f;--warn-bg:#f8e3e3;
--prediction:#4b3b8a;--prediction-bg:#ebe7f7;--code:#f1efe8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15161a;--surface:#1d1f25;--fg:#ececea;
--muted:#a7a59c;--accent:#8fbde6;--border:#34363e;--observed:#8fd3a6;--observed-bg:#1f3a2a;--inferred:#e8c173;
--inferred-bg:#3b3019;--warn:#f0a3a3;--warn-bg:#3d2222;--prediction:#c2b6f0;--prediction-bg:#2c2644;--code:#262830}}
:root[data-theme="dark"]{--bg:#15161a;--surface:#1d1f25;--fg:#ececea;--muted:#a7a59c;--accent:#8fbde6;--border:#34363e;
--observed:#8fd3a6;--observed-bg:#1f3a2a;--inferred:#e8c173;--inferred-bg:#3b3019;--warn:#f0a3a3;--warn-bg:#3d2222;
--prediction:#c2b6f0;--prediction-bg:#2c2644;--code:#262830}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header.site{border-bottom:1px solid var(--border);background:var(--surface)}
header.site nav,main,footer{max-width:1100px;margin:0 auto;padding:0 16px}
header.site nav{display:flex;flex-wrap:wrap;gap:16px;align-items:center;min-height:56px}
header.site .brand{font-weight:700;color:var(--fg);text-decoration:none;margin-right:auto}
a{color:var(--accent)}
main{padding-top:24px;padding-bottom:48px}
h1{font-size:1.7rem;margin:0 0 4px}h2{font-size:1.25rem;margin:32px 0 8px;border-bottom:1px solid var(--border);padding-bottom:4px}
h3{font-size:1.05rem;margin:20px 0 6px}
.sub{color:var(--muted);margin:0 0 12px}
.banner{border:1px solid var(--border);border-left:4px solid var(--warn);background:var(--warn-bg);padding:10px 14px;border-radius:6px;margin:12px 0}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px;min-width:120px}
.stat b{display:block;font-size:1.3rem}
.scroll{overflow-x:auto;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:0.92rem}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
th{background:var(--code);font-weight:600;position:sticky;top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.single td{background:var(--warn-bg)}
.lvl{font-size:.7rem;opacity:.7;border:1px solid currentColor;border-radius:3px;padding:0 .2em}
#coverage-grid td:first-child{min-width:11rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin:12px 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.card h3{margin:0 0 2px;font-size:1.02rem}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.chip{font-size:0.78rem;padding:1px 7px;border-radius:999px;background:var(--code);border:1px solid var(--border);white-space:nowrap}
.searchbar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.searchbar input[type=search]{flex:1 1 260px;font:inherit;padding:8px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--fg)}
.searchbar button{font:inherit;padding:8px 14px;border:1px solid var(--accent);border-radius:6px;background:var(--accent);color:var(--bg);cursor:pointer}
table.matrix{font-size:0.82rem}
table.matrix th.tech{writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;padding:6px 2px;vertical-align:bottom}
table.matrix td.m{text-align:center;padding:3px 4px;min-width:2.2em;font-variant-numeric:tabular-nums}
table.matrix td.m a{color:var(--fg);text-decoration:none;display:block}
mark{background:var(--inferred-bg);color:inherit;padding:0 1px;border-radius:2px}
td.hit{font-weight:600;color:var(--observed)}
.badge{display:inline-block;font-size:0.78rem;font-weight:600;padding:1px 8px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.badge-observed{color:var(--observed);background:var(--observed-bg)}
.badge-inferred{color:var(--inferred);background:var(--inferred-bg)}
.badge-prediction{color:var(--prediction);background:var(--prediction-bg)}
.badge-draft{color:var(--warn);background:var(--warn-bg)}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.controls input,.controls select,select#model-select{font:inherit;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--fg);max-width:100%}
#viewer{position:relative;width:100%;height:440px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
.muted{color:var(--muted)}
code{background:var(--code);padding:1px 4px;border-radius:4px;font-size:0.9em;word-break:break-word}
details{margin:6px 0}summary{cursor:pointer;color:var(--accent)}
svg text{fill:var(--fg)}
footer{color:var(--muted);font-size:0.88rem;border-top:1px solid var(--border);margin-top:32px;padding-top:12px;padding-bottom:24px}
"""

SCRIPT_FILTER = """
function conformomeFilter(tableId, controlIds, textId){
  var rows=[].slice.call(document.querySelectorAll('#'+tableId+' tbody tr'));
  var controls=controlIds.map(function(id){return document.getElementById(id)});
  var text=document.getElementById(textId);
  function apply(){
    var q=(text?text.value:'').toLowerCase();
    rows.forEach(function(r){
      var ok=q===''||r.getAttribute('data-text').indexOf(q)>=0;
      controls.forEach(function(c){
        if(!c)return;
        var attr=c.getAttribute('data-attr');
        var v=c.value;
        if(v!=='' && r.getAttribute(attr)!==v) ok=false;
      });
      r.style.display=ok?'':'none';
    });
    var shown=rows.filter(function(r){return r.style.display!=='none'}).length;
    var out=document.getElementById(tableId+'-count');
    if(out)out.textContent=shown+' of '+rows.length+' shown';
  }
  controls.forEach(function(c){if(c)c.addEventListener('change',apply)});
  if(text)text.addEventListener('input',apply);
  apply();
}
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def badge(basis: str) -> str:
    return f'<span class="badge badge-{esc(basis)}">{esc(basis)}</span>'


def fmt_obs(obs: dict) -> str:
    if obs["value"] is None:
        return esc(obs["type"])
    unc = f" ± {obs['uncertainty']:g}" if obs.get("uncertainty") is not None else ""
    unit = f" {obs['unit']}" if obs.get("unit") else ""
    return f"{esc(obs['type'])}: {obs['value']:g}{esc(unit)}{esc(unc)}"


def fmt_conditions(c: dict) -> str:
    parts = [c["environment"].replace("_", " ")]
    if c.get("temperature_c") is not None:
        parts.append(f"{c['temperature_c']:g} °C")
    if c.get("ph") is not None:
        parts.append(f"pH {c['ph']:g}")
    if c.get("ligands"):
        parts.append("ligands " + ", ".join(c["ligands"]))
    if c.get("applied_force_pn") is not None:
        parts.append(f"{c['applied_force_pn']:g} pN")
    return " · ".join(esc(p) for p in parts)


def page(title: str, body: str, root: str, scripts: str = "", head_extra: str = "", description: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Conformome</title>
<meta name="description" content="{esc(description or 'Conformome: conformational states and the techniques that probed them')}">
<link rel="icon" href="data:,">
<style>{CSS}</style>
{head_extra}
</head>
<body>
<header class="site"><nav>
<a class="brand" href="{root}index.html">Conformome</a>
<a href="{root}proteins/index.html">Proteins</a>
<a href="{root}search/index.html">Search</a>
<a href="{root}about/index.html">About and methods</a>
<a href="{root}downloads/index.html">Downloads</a>
<a href="{REPO_URL}">GitHub</a>
</nav></header>
<main>
{body}
</main>
<footer>Every number on this page is generated by <code>make site</code> from the pipeline outputs.
Corrections: see <a href="{REPO_URL}/blob/HEAD/CONTRIBUTING.md">CONTRIBUTING</a>.</footer>
{scripts}
</body>
</html>
"""


def md_to_html(text: str) -> str:
    """Minimal Markdown for docs/*.md: headings, paragraphs, lists, pipe tables, code, bold, links."""
    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    out, para, lines = [], [], text.splitlines()
    i = 0
    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
    while i < len(lines):
        line = lines[i]
        if line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            flush()
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="scroll"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in head)
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            flush()
            level = len(m.group(1)) + 1  # page h1 is the title; document # becomes h2
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
        elif line.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif line.strip() == "":
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def _load(paths: Paths, acc: str):
    out = paths.build / acc
    protein = read_json(out / "molecule.json")
    mapped = read_json(out / "mapped.json")
    models = read_json(out / "models.json") if (out / "models.json").exists() else []
    return protein, mapped, models


ID_LABEL = {"protein": "UniProt", "rna": "RNAcentral", "dna": "NAKB", "complex": "Complex"}


def organism_name(molecule: dict) -> str:
    return molecule["organism"]["name"] if molecule.get("organism") else "synthetic construct"


def _identity_line(acc: str, mol: dict) -> str:
    """Identifier, family, gene, organism and length, worded for the molecule type."""
    mtype = mol.get("molecule_type", "protein")
    shown = mol["identifiers"]["nakb"] if mtype == "dna" else acc
    parts = [f'{ID_LABEL[mtype]} <a href="{esc(mol["provenance"]["url"])}">{esc(shown)}</a>']
    if mol["identifiers"].get("rfam"):
        rf = mol["identifiers"]["rfam"]
        parts.append(f'Rfam <a href="https://rfam.org/family/{esc(rf)}">{esc(rf)}</a>')
    if mol.get("gene"):
        parts.append("gene " + esc(mol["gene"]))
    parts.append(esc(organism_name(mol)))
    parts.append(f'{mol["sequence_length"]} {"residues" if mtype == "protein" else "nt"}')
    return " · ".join(parts)


def _state_extras(s: dict) -> str:
    """Family label, population and secondary structure, when the state has them."""
    out = ""
    if s.get("family_label"):
        fl = s["family_label"]
        terms = ", ".join(f"{k}: {v}" for k, v in fl["terms"].items())
        out += (f'<p class="muted">Family vocabulary <a href="../../downloads/taxonomy/state_vocabularies/{esc(fl["vocabulary"])}.yaml">'
                f'{esc(fl["vocabulary"])}</a>: {esc(terms)}</p>')
    if s.get("population"):
        p = s["population"]
        unc = f" ± {p['uncertainty']:.2f}" if p["uncertainty"] is not None else ""
        out += f'<p class="muted">Population {p["value"]:.2f}{unc} ({esc(p["method"])})</p>'
    if s.get("secondary_structure"):
        ss = s["secondary_structure"]
        out += f'<pre class="dotbracket">{esc(ss["dot_bracket"])}</pre><p class="muted">Pairing from {esc(ss["source"])}</p>'
    return out


def _protein_page(paths: Paths, acc: str, protein: dict, mapped: dict, models: list[dict], taxonomy: dict) -> str:
    root = "../../"
    states = mapped["states"]
    evidence = mapped["evidence"]
    coverage = mapped["coverage"]
    draft = mapped["curation"]["status"] != "reviewed"
    techniques = coverage["techniques"]
    state_name = {s["state_id"]: s["name"] for s in states}

    banner = ""
    if mapped["curation"]["status"] == "uncurated":
        banner = ('<div class="banner"><b>States not yet curated.</b> Every evidence item for this protein is listed, '
                  'but no states are defined yet, so nothing is mapped. See CONTRIBUTING to curate it.</div>')
    elif draft:
        banner = ('<div class="banner"><b>Draft curation.</b> States and evidence-to-state mappings have not been '
                  'reviewed by a curator. Treat the grid and models as provisional.</div>')

    stats = (f'<div class="stats">'
             f'<div class="stat"><b>{len(evidence)}</b>evidence items</div>'
             f'<div class="stat"><b>{sum(1 for e in evidence if e["mappings"])}</b>mapped to a state</div>'
             f'<div class="stat"><b>{len(states)}</b>states</div>'
             f'<div class="stat"><b>{len(techniques)}</b>techniques</div>'
             f'<div class="stat"><b>{len({e["provenance"]["source"] for e in evidence})}</b>sources</div>'
             f'<div class="stat"><b>{len(mapped["conflicts"])}</b>conflicts</div></div>')

    # Coverage grid
    head = "".join(f'<th class="num" title="{esc(taxonomy[t]["name"])}"><a href="{root}technique/{esc(t)}/index.html">{esc(t)}</a></th>'
                   for t in techniques)
    rows = []
    for s in states:
        row = coverage["cells"][s["state_id"]]
        single = s["state_id"] in coverage["single_method_states"]
        lv = coverage["data_levels"][s["state_id"]]
        cells = "".join(f'<td class="num{" hit" if row[t] else ""}"'
                        + (f' title="best data level: {lv[t]}"><span class="lvl lvl-{lv[t]}">{DATA_LEVEL_LABEL[lv[t]]}</span> {row[t]}</td>' if row[t] else '>·</td>')
                        for t in techniques)
        note = " (one method)" if single else ""
        rows.append(f'<tr class="{"single" if single else ""}"><td>{esc(s["name"])}<br><span class="muted">'
                    f'{esc(s["state_id"])}</span></td><td>{badge(s["basis"])}{esc(note)}</td>{cells}'
                    f'<td class="num">{sum(row.values())}</td></tr>')
    empty_row = f'<tr><td colspan="{len(techniques) + 3}" class="muted">No states defined yet.</td></tr>'
    grid = ('<h2>Coverage grid</h2>'
            '<p class="sub">Mapped evidence per state and technique. Shaded rows rest on a single technique. Badge = best data level in the cell: raw (traces, images, FIDs: can be re-analysed), proc (maps, curves, tables, trajectories) or rep (values in the paper only).</p>'
            '<div class="scroll"><table id="coverage-grid"><thead><tr><th>State</th><th>Basis</th>'
            f'{head}<th class="num">Total</th></tr></thead><tbody>{"".join(rows) or empty_row}</tbody></table></div>'
            f'<p class="muted">Unmapped evidence: {coverage["unmapped_evidence"]} of {len(evidence)} items. '
            'Mappings come from curator assignments and curated rules; see About for how rules work.</p>')
    grid += _sources_panel(evidence, mapped.get("ambiguous", []), state_name)

    # Viewer
    model_data = []
    for m in models:
        if m["format"] != "mmCIF":
            continue
        state = next(s for s in states if s["state_id"] == m["state_id"])
        assumptions = ("; ".join(state["assumptions"]) if state["basis"] == "inferred" and state["assumptions"]
                       else (m.get("assumptions") or "Observed: directly resolved in PDB entry "
                             f"{m['provenance']['deposit_id']}. No modelling assumptions."))
        model_data.append({"state": state["name"], "state_id": m["state_id"], "basis": m["basis"],
                           "format": MOLSTAR_FORMAT[m["format"]], "url": root + "downloads/" + m["file"],
                           "assumptions": assumptions})
    if model_data:
        options = "".join(f'<option value="{i}">{esc(d["state"])} ({esc(d["state_id"])})</option>'
                          for i, d in enumerate(model_data))
        viewer = ('<h2>Structure</h2>'
                  '<p class="sub">Choose a state. Each model is badged observed or inferred; assumptions are one click away.</p>'
                  f'<div class="controls"><label for="model-select">State model</label>'
                  f'<select id="model-select">{options}</select></div>'
                  '<div id="viewer" role="img" aria-label="3D structure of the selected state"></div>'
                  '<div id="model-info"></div>'
                  '<noscript><p class="muted">The 3D viewer needs JavaScript. Models are in the downloads.</p></noscript>')
        model_json = json.dumps(model_data).replace("</", "<\\/")
        scripts = (f'<script type="application/json" id="model-data">{model_json}</script>'
                   f'<script src="{MOLSTAR_BASE}molstar.js"></script>'
                   '<script>'
                   '(function(){'
                   'var data=JSON.parse(document.getElementById("model-data").textContent);'
                   'var select=document.getElementById("model-select");var info=document.getElementById("model-info");'
                   'function show(i){var d=data[i];info.innerHTML="";'
                   'var b=document.createElement("span");b.className="badge badge-"+d.basis;b.textContent=d.basis;'
                   'info.appendChild(b);var det=document.createElement("details");det.open=d.basis==="inferred";'
                   'var s=document.createElement("summary");s.textContent=d.basis==="inferred"?"Assumptions":"Basis";'
                   'var p=document.createElement("p");p.textContent=d.assumptions;det.appendChild(s);det.appendChild(p);info.appendChild(det);}'
                   'if(!window.molstar){document.getElementById("viewer").textContent="The 3D viewer could not load. Models are in the downloads.";'
                   'show(0);return;}'
                   'molstar.Viewer.create("viewer",{layoutIsExpanded:false,layoutShowControls:false,'
                   'layoutShowSequence:false,layoutShowLog:false,layoutShowRemoteState:false,viewportShowExpand:false})'
                   '.then(function(viewer){'
                   'function load(i){var d=data[i];show(i);viewer.plugin.clear().then(function(){'
                   'return viewer.loadStructureFromUrl(d.url,d.format);});}'
                   'select.addEventListener("change",function(){load(+select.value);});'
                   'load(0);});'
                   'show(0);})();'
                   '</script>')
        head_extra = (f'<link rel="stylesheet" href="{MOLSTAR_BASE}molstar.css">')
    else:
        viewer = ('<h2>Structure</h2><p class="muted">No state models are exported for this protein yet. '
                  'Observed states export the representative PDB entry; inferred states need fitted models, not yet built.</p>')
        scripts = ""
        head_extra = ""

    # State and transition diagram
    diagram = _diagram(states, mapped["transitions"])
    state_rows = "".join(
        f'<tr><td>{esc(s["name"])}<br><span class="muted">{esc(s["state_id"])}</span></td><td>{badge(s["basis"])}</td>'
        f'<td>{esc(s["parent_state"] or "—")}</td><td>{esc(s["description"])}'
        + (f'<details><summary>Assumptions ({len(s["assumptions"])})</summary><ul>'
           + "".join(f"<li>{esc(a)}</li>" for a in s["assumptions"]) + "</ul></details>" if s["assumptions"] else "")
        + _state_extras(s) + "</td></tr>" for s in states)
    states_html = ('<h2>States and transitions</h2>' + diagram +
                   '<div class="scroll"><table><thead><tr><th>State</th><th>Basis</th><th>Parent</th>'
                   f'<th>Description</th></tr></thead><tbody>{state_rows}</tbody></table></div>')
    if mapped["transitions"]:
        trows = "".join(
            f'<tr><td>{esc(t["from_state"])} → {esc(t["to_state"])}</td>'
            f'<td>{esc(t["quantity"]["type"])}: {t["quantity"]["value"]:g} {esc(t["quantity"]["unit"])}</td>'
            f'<td>{fmt_conditions(t["conditions"])}</td><td>{", ".join(esc(e) for e in t["evidence_ids"])}</td></tr>'
            for t in mapped["transitions"])
        states_html += ('<h3>Transitions</h3><div class="scroll"><table><thead><tr><th>From → to</th><th>Quantity</th>'
                        f'<th>Conditions</th><th>Evidence</th></tr></thead><tbody>{trows}</tbody></table></div>')
    else:
        states_html += '<p class="muted">No transitions recorded in this version (no rate or free-energy evidence has been curated yet).</p>'

    # Evidence table
    tech_options = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in techniques)
    source_options = "".join(f'<option value="{esc(s)}">{esc(s)}</option>'
                             for s in sorted({ev["provenance"]["source"] for ev in evidence}))
    env_options = "".join(f'<option value="{esc(e)}">{esc(e.replace("_", " "))}</option>'
                          for e in sorted({ev["conditions"]["environment"] for ev in evidence}))
    erows = []
    for ev in evidence:
        mapped_flag = "yes" if ev["mappings"] else "no"
        mappings = "<br>".join(
            f'{esc(state_name.get(m["state_id"], m["state_id"]))} · {esc(m["who"])} · {esc(m["confidence"])}'
            f'<br><span class="muted">{esc(m["justification"])}</span>' for m in ev["mappings"]) or '<span class="muted">unmapped</span>'
        link = esc(ev["data_link"] or "#")
        text = " ".join([ev["evidence_id"], ev["technique"], ev["conditions"]["environment"], ev["construct"]["description"],
                         ev.get("title") or "",
                         ev["provenance"]["source"], ev["provenance"]["deposit_id"] or ""] +
                        [m["state_id"] for m in ev["mappings"]]).lower()
        erows.append(
            f'<tr id="{esc(ev["evidence_id"])}" data-technique="{esc(ev["technique"])}" data-environment="{esc(ev["conditions"]["environment"])}" '
            f'data-source="{esc(ev["provenance"]["source"])}" data-mapped="{mapped_flag}" data-text="{esc(text)}">'
            f'<td><a href="{link}">{esc(ev["evidence_id"])}</a><br><span class="muted">{esc(ev["provenance"]["source"])}</span></td>'
            f'<td><a href="{root}technique/{esc(ev["technique"])}/index.html">{esc(ev["technique"])}</a></td>'
            f'<td>{fmt_obs(ev["observable"])}</td><td>{fmt_conditions(ev["conditions"])}'
            f'<br><span class="muted">{esc(ev.get("title") or "")}{" · " if ev.get("title") else ""}'
            f'{esc(ev["construct"]["description"])}</span></td><td>{mappings}</td></tr>')
    evidence_html = (
        '<h2>Evidence</h2>'
        '<p class="sub">One row per deposit or experiment. Filter by technique, environment or text. Unmapped evidence is listed too.</p>'
        '<div class="controls">'
        '<input id="ev-text" type="search" placeholder="Search evidence, state, source" aria-label="Search evidence">'
        f'<select id="ev-technique" data-attr="data-technique" aria-label="Technique"><option value="">All techniques</option>{tech_options}</select>'
        f'<select id="ev-environment" data-attr="data-environment" aria-label="Environment"><option value="">All environments</option>{env_options}</select>'
        f'<select id="ev-source" data-attr="data-source" aria-label="Source"><option value="">All sources</option>{source_options}</select>'
        '<select id="ev-mapped" data-attr="data-mapped" aria-label="Mapping"><option value="">Mapped and unmapped</option>'
        '<option value="yes">Mapped only</option><option value="no">Unmapped only</option></select>'
        '</div><p class="muted" id="ev-table-count"></p>'
        '<div class="scroll" style="max-height:70vh"><table id="ev-table"><thead><tr><th>Evidence</th><th>Technique</th>'
        '<th>Observable</th><th>Conditions</th><th>Mapped to state</th></tr></thead>'
        f'<tbody>{"".join(erows)}</tbody></table></div>')
    evidence_scripts = (f'<script>{SCRIPT_FILTER}'
                        'conformomeFilter("ev-table",["ev-technique","ev-environment","ev-source","ev-mapped"],"ev-text");</script>')

    # Conflicts
    if mapped["conflicts"]:
        items = "".join(f'<li><b>{esc(c["state_id"])}</b> · {esc(c["observable_type"])}: '
                        f'{", ".join(f"{v:g}" for v in c["values"])} {esc(c["unit"] or "")} · '
                        f'{", ".join(esc(e) for e in c["evidence_ids"])}<br><span class="muted">{esc(c["reason"])}</span></li>'
                        for c in mapped["conflicts"])
        conflicts = f'<ul>{items}</ul>'
    else:
        conflicts = ('<p>No conflicts found among comparable evidence.</p>'
                     f'<p class="muted">{mapped["not_compared"]} evidence items could not be compared: they lack a comparable '
                     'observable type, a value, or an uncertainty. Absence of a conflict here is not agreement.</p>')
    conflicts_html = f'<h2>Conflicts</h2>{conflicts}'

    downloads = [f'<li><a href="{root}downloads/proteins/{esc(acc)}.json">Protein bundle (JSON)</a></li>']
    for m in models:
        downloads.append(f'<li><a href="{root}downloads/{esc(m["file"])}">{esc(m["model_id"])}</a> '
                         f'<span class="muted">({esc(m["format"])}, {esc(m["basis"])})</span></li>')
    if mapped["curation"]["file"]:
        downloads.append(f'<li><a href="{REPO_URL}/blob/HEAD/curation/{esc(acc)}.yaml">Curation file (YAML)</a></li>')
    downloads_html = f'<h2>Downloads</h2><ul>{"".join(downloads)}</ul>'

    body = (
        f'<h1>{esc(protein["name"])}</h1>'
        f'<p class="sub">{_identity_line(acc, protein)}</p>'
        f'{banner}{stats}{grid}{viewer}{states_html}{evidence_html}{conflicts_html}{downloads_html}')
    return page(protein["name"], body, root, scripts=scripts + evidence_scripts, head_extra=head_extra,
                description=f"Conformational states and techniques for {protein['name']} ({acc})")


def _sources_panel(evidence: list[dict], ambiguous: list[dict], state_name: dict) -> str:
    by_source: dict[str, list[int]] = {}
    by_rule: dict[str, int] = {}
    for ev in evidence:
        row = by_source.setdefault(ev["provenance"]["source"], [0, 0])
        row[0] += 1
        row[1] += bool(ev["mappings"])
        for m in ev["mappings"]:
            if m["who"].startswith("rule:"):
                by_rule[m["who"][5:]] = by_rule.get(m["who"][5:], 0) + 1
    rows = "".join(f'<tr><td>{esc(s)}</td><td class="num">{n}</td><td class="num">{k}</td></tr>'
                   for s, (n, k) in sorted(by_source.items()))
    html_out = ('<h3>Sources</h3><div class="scroll"><table><thead><tr><th>Source</th>'
                f'<th class="num">Evidence</th><th class="num">Mapped</th></tr></thead><tbody>{rows}</tbody></table></div>')
    if by_rule:
        html_out += ('<h3>Curated rules applied</h3><ul>'
                     + "".join(f'<li><code>{esc(r)}</code>: {n} items</li>' for r, n in sorted(by_rule.items())) + '</ul>')
    if ambiguous:
        items = "".join(f'<li>{esc(a["evidence_id"])}: rules {esc(", ".join(a["rules"]))} point to '
                        f'{esc(", ".join(state_name.get(s, s) for s in a["states"]))}</li>' for a in ambiguous[:50])
        more = f'<p class="muted">and {len(ambiguous) - 50} more.</p>' if len(ambiguous) > 50 else ""
        html_out += (f'<h3>Ambiguous evidence ({len(ambiguous)})</h3><p class="muted">Matched by rules for different '
                     f'states, so left unmapped for a curator to decide.</p><ul>{items}</ul>{more}')
    return html_out


def _diagram(states: list[dict], transitions: list[dict]) -> str:
    if not states:
        return '<p class="muted">No states defined.</p>'
    width, box_w, box_h, gap = max(680, len(states) * 180), 160, 56, 20
    pos = {s["state_id"]: 40 + i * (box_w + gap) for i, s in enumerate(states)}
    height = 150 if transitions else 90
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'aria-label="State and transition diagram" style="max-width:{width}px">'
             '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker></defs>']
    for t in transitions:
        x1, x2 = pos[t["from_state"]] + box_w / 2, pos[t["to_state"]] + box_w / 2
        mid = (x1 + x2) / 2
        q = t["quantity"]
        label = f'{q["value"]:g} {q["unit"]}' + (" (rate)" if q["type"] == "rate" else " (ΔG)")
        parts.append(f'<path d="M{x1},{box_h + 10} Q{mid},{height - 10} {x2},{box_h + 10}" fill="none" '
                     'stroke="currentColor" stroke-width="1.5" marker-end="url(#arrow)"/>'
                     f'<text x="{mid}" y="{height - 16}" text-anchor="middle" font-size="12">{esc(label)}</text>')
    for s in states:
        x = pos[s["state_id"]]
        fill = "var(--observed-bg)" if s["basis"] == "observed" else "var(--inferred-bg)"
        parts.append(f'<rect x="{x}" y="10" width="{box_w}" height="{box_h}" rx="10" fill="{fill}" stroke="var(--border)"/>'
                     f'<text x="{x + box_w / 2}" y="34" text-anchor="middle" font-size="13" font-weight="600">{esc(s["name"][:26])}</text>'
                     f'<text x="{x + box_w / 2}" y="54" text-anchor="middle" font-size="11">{esc(s["basis"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _matrix(rows: list[dict], techniques: list[str], taxonomy: dict, root: str = "") -> str:
    """Proteins x techniques, shaded by evidence count (log scale)."""
    import math
    top = max([n for r in rows for n in r["tech_counts"].values()] or [1])
    head = "".join(f'<th class="tech" title="{esc(taxonomy[tid]["name"])}"><a href="{root}technique/{esc(tid)}/index.html">{esc(tid)}</a></th>'
                   for tid in techniques)
    body = []
    for r in sorted(rows, key=lambda r: (-len(r["tech_counts"]), r["name"].lower())):
        cells = []
        for tid in techniques:
            n = r["tech_counts"].get(tid, 0)
            if not n:
                cells.append('<td class="m"></td>')
                continue
            pct = round(18 + 72 * math.log10(n + 1) / math.log10(top + 1))
            cells.append(f'<td class="m" style="background:color-mix(in srgb, var(--accent) {pct}%, transparent)" '
                         f'title="{esc(r["name"])}: {n} {esc(tid)}"><a href="{root}protein/{esc(r["acc"])}/index.html">{n}</a></td>')
        body.append(f'<tr><td><a href="{root}protein/{esc(r["acc"])}/index.html">{esc(r["name"])}</a></td>{"".join(cells)}</tr>')
    return ('<h2>Technique coverage</h2>'
            '<p class="sub">Evidence items per protein and technique. Darker cells hold more evidence (log scale); '
            'proteins probed by the most techniques come first. Click a cell to open the protein.</p>'
            f'<div class="scroll" style="max-height:80vh"><table class="matrix"><thead><tr><th>Protein</th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


SMASH_BIO_URL = "https://smash-bio.org/"


def _states_label(n: int) -> str:
    return "states not yet curated" if n == 0 else f"{n} state" + ("" if n == 1 else "s")


def _home_page(summaries: list[dict], techniques: list[str]) -> str:
    """The front door: what Conformome is, live counts, search, and the sister project SMASH-BIO."""
    n_ev = sum(s["evidence"] for s in summaries)
    n_states = sum(len(s["state_list"]) for s in summaries)
    n_curated = sum(1 for s in summaries if s["status"] != "uncurated")
    by_source: dict[str, int] = {}
    for s in summaries:
        for name in s["source_list"]:
            by_source[name] = by_source.get(name, 0) + 1
    sources = "".join(f'<li><b>{esc(name)}</b> <span class="muted">· {n} proteins</span></li>'
                      for name, n in sorted(by_source.items(), key=lambda kv: -kv[1]))
    tiles = "".join(f'<div class="stat"><b>{v:,}</b>{esc(k)}</div>' for k, v in (
        ("proteins", len(summaries)), ("evidence entries", n_ev), ("techniques", len(techniques)),
        ("sources", len(by_source)), ("curated states", n_states)))
    featured = sorted(summaries, key=lambda s: (-len(s["tech_counts"]), -s["evidence"]))[:6]
    cards = "".join(
        f'<div class="card"><h3><a href="protein/{esc(s["acc"])}/index.html">{esc(s["name"])}</a></h3>'
        f'<div class="muted">{esc(s["organism"])}</div>'
        f'<div class="muted" style="margin-top:6px">{s["evidence"]:,} entries · {len(s["tech_counts"])} techniques · '
        f'{_states_label(len(s["state_list"]))}</div></div>' for s in featured)
    body = f"""
<h1 style="font-size:2.1rem">Conformome</h1>
<p class="sub" style="font-size:1.15rem;max-width:46rem">A database of experimental entries that probe protein conformation, each in its own way.</p>
<p style="max-width:46rem">Every technique sees a protein's shape differently. Crystallography resolves atoms in a lattice. Cryo-EM sees
particles frozen in ice. NMR reports how each residue moves. Small-angle scattering measures overall size in solution. Force
spectroscopy pulls a single molecule apart and records how it gives way. Simulations and predictions say what a model expects.
Conformome gathers these entries for each protein, keeps them side by side with their conditions and provenance, and maps them
onto shared conformational states, so you can see which techniques support which state, and where they disagree.</p>
<form class="searchbar" action="search/index.html" method="get" role="search" style="max-width:46rem">
<input name="q" type="search" placeholder="Search proteins, states, PDB or BMRB IDs, ligands, titles" aria-label="Search Conformome">
<button type="submit">Search</button></form>
<div class="stats">{tiles}</div>
<p><a href="proteins/index.html">Browse all proteins and the technique coverage matrix</a> · <a href="search/index.html">Search</a> ·
<a href="about/index.html">How it works</a> · <a href="downloads/index.html">Downloads</a></p>

<h2>How to read an entry</h2>
<div class="cards">
<div class="card"><h3>Evidence entries</h3><p>One experiment or deposit: a crystal structure, an NMR data set, a SAXS curve,
a force-spectroscopy result. Each keeps its technique, construct, conditions (temperature, pH, ligands, force) and source.</p></div>
<div class="card"><h3>Conformational states</h3><p>Named shapes a protein adopts, such as open and closed, apo and bound, folded and
unfolded. Curators map each entry to a state and say who decided, how confident they are, and why.</p></div>
<div class="card"><h3>Observed or inferred</h3><p>A state is <span class="badge badge-observed">observed</span> when a structure
resolves it directly, and <span class="badge badge-inferred">inferred</span> when it is fitted to indirect measurements; inferred
states list their assumptions.</p></div>
<div class="card"><h3>Disagreement is shown</h3><p>When comparable measurements of the same state disagree beyond their errors, the
page flags the conflict instead of averaging it away.</p></div>
</div>

<h2>Most-probed proteins</h2>
<div class="cards">{cards}</div>

<h2>Where the entries come from</h2>
<ul>{sources}</ul>

<h2>Sister project: SMASH-BIO</h2>
<div class="card" style="max-width:46rem"><h3><a href="{SMASH_BIO_URL}">SMASH-BIO</a></h3>
<p class="muted">Single Molecule Analysis and Spectroscopy Hub</p>
<p>SMASH-BIO indexes single-molecule force spectroscopy studies (optical and magnetic tweezers, AFM and more) with their
instruments, conditions and results. Conformome takes its force-spectroscopy entries from the SMASH-BIO release, so the
mechanical view of a protein sits next to its structures, NMR and scattering data.
<a href="{SMASH_BIO_URL}">Visit smash-bio.org</a>.</p></div>

<div class="banner" style="margin-top:24px"><b>Pilot.</b> {len(summaries)} proteins; {n_curated} have draft curation that no curator
has reviewed yet, and the rest list their evidence without states. Corrections and curation are welcome: see
<a href="{REPO_URL}/blob/HEAD/docs/CONTRIBUTING.md">CONTRIBUTING</a>.</div>
"""
    return page("Home", body, "", description="Conformome: a database of experimental entries that probe "
                "protein conformation, each in its own way, mapped onto shared conformational states.")


def _proteins_page(rows: list[dict], source_names: list[str], techniques: list[str], taxonomy: dict) -> str:
    root = "../"
    def curation_cell(status: str) -> str:
        if status == "uncurated":
            return '<span class="muted">not yet curated</span>'
        return '<span class="badge badge-draft">draft</span>' if status == "draft" else "reviewed"

    body_lines = []
    for r in rows:
        search = esc((r["name"] + " " + r["acc"] + " " + r["organism"]).lower())
        body_lines.append(
            f'<tr data-text="{search}">'
            f'<td><a href="{root}protein/{esc(r["acc"])}/index.html">{esc(r["name"])}</a></td>'
            f'<td>{esc(r["acc"])}</td><td>{esc(r["organism"])}</td>'
            f'<td class="num">{r["techniques"]}</td><td class="num">{r["states"]}</td>'
            f'<td class="num">{r["sources"]}</td><td class="num">{r["evidence"]}</td><td class="num">{r["mapped"]}</td>'
            f'<td>{curation_cell(r["status"])}</td></tr>')
    rows_html = "".join(body_lines)
    body = ('<h1>Proteins</h1>'
            '<p class="sub">Every protein in Conformome, with the techniques that have probed it.</p>'
            f'<div class="banner"><b>Pilot.</b> {len(rows)} proteins. Evidence from {esc(", ".join(source_names))}. '
            'Curation is a draft that no curator has reviewed yet, and some proteins have no states yet; literature extraction, PED and PDB-IHM restraints are not yet included.</div>'
            '<form class="searchbar" action="../search/index.html" method="get" role="search">'
            '<input name="q" type="search" placeholder="Search proteins, states, PDB or BMRB IDs, ligands, titles" '
            'aria-label="Search everything"><button type="submit">Search</button></form>'
            f'{_matrix(rows, techniques, taxonomy, root)}'
            '<h2>All proteins</h2>'
            '<div class="controls"><input id="p-text" type="search" placeholder="Filter this table by name, UniProt or organism" '
            'aria-label="Filter proteins"></div><p class="muted" id="p-table-count"></p>'
            '<div class="scroll"><table id="p-table"><thead><tr><th>Protein</th><th>UniProt</th><th>Organism</th>'
            '<th class="num">Techniques</th><th class="num">States</th><th class="num">Sources</th><th class="num">Evidence</th>'
            '<th class="num">Mapped</th><th>Curation</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>')
    scripts = f'<script>{SCRIPT_FILTER}conformomeFilter("p-table",[],"p-text");</script>'
    return page("Proteins", body, root, scripts=scripts)


def _technique_page(tid: str, tech: dict, covered: list[dict]) -> str:
    root = "../../"
    prediction = '<span class="badge badge-prediction">computed prediction</span>' if tech["prediction"] else ""
    rows = "".join(f'<tr><td><a href="{root}protein/{esc(c["acc"])}/index.html">{esc(c["name"])}</a></td>'
                   f'<td class="num">{c["count"]}</td></tr>' for c in covered) or \
        '<tr><td colspan="2" class="muted">No evidence in the pilot yet.</td></tr>'
    body = (f'<h1>{esc(tech["name"])}</h1>'
            f'<p class="sub">{badge(tech["basis"])} {prediction} <span class="muted">category: {esc(tech["category"])} · '
            f'resolution class: {esc(tech["resolution_class"])}</span></p>'
            f'<p>{esc(tech["description"])}</p>'
            '<h2>Observables</h2><ul>' + "".join(f'<li><code>{esc(o)}</code></li>' for o in tech["observables"]) + '</ul>'
            '<h2>Proteins covered</h2><div class="scroll"><table><thead><tr><th>Protein</th>'
            f'<th class="num">Evidence items</th></tr></thead><tbody>{rows}</tbody></table></div>')
    return page(tech["name"], body, root, description=tech["description"])


DATA_LEVEL_LABEL = {"raw": "raw", "processed": "proc", "reported": "rep"}


def build_site(paths: Paths, accessions: list[str]) -> None:
    site = paths.site
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)
    taxonomy = load_taxonomy(paths.taxonomy / "techniques.yaml")
    sources = sources_table(paths)
    redistributable = {mod.NAME: sources.get(key, {}).get("redistribute", "no").lower() != "no"
                       for key, mod in REGISTRY.items()}
    redistributable.setdefault("Conformome curation", True)

    summaries, bundles, all_lines, search_rows = [], {}, [], []
    technique_acc: dict[str, list[dict]] = {}
    for acc in accessions:
        protein, mapped, models = _load(paths, acc)
        draft = mapped["curation"]["status"] != "reviewed"
        summaries.append({
            "acc": acc, "name": protein["name"], "organism": organism_name(protein),
            "techniques": len(mapped["coverage"]["techniques"]), "states": len(mapped["states"]),
            "evidence": len(mapped["evidence"]), "mapped": sum(1 for e in mapped["evidence"] if e["mappings"]),
            "sources": len({e["provenance"]["source"] for e in mapped["evidence"]}),
            "draft": draft,
            "status": mapped["curation"]["status"],
            "gene": protein.get("gene") or "",
            "length": protein["sequence_length"],
            "tech_counts": {tt: sum(1 for e in mapped["evidence"] if e["technique"] == tt)
                            for tt in mapped["coverage"]["techniques"]},
            "source_list": sorted({e["provenance"]["source"] for e in mapped["evidence"]}),
            "state_list": [{"id": s["state_id"], "name": s["name"], "basis": s["basis"]} for s in mapped["states"]],
        })
        state_names = {s["state_id"]: s["name"] for s in mapped["states"]}
        for e in mapped["evidence"]:
            search_rows.append([
                e["evidence_id"], acc, e["technique"], e["provenance"]["source"], e["provenance"]["deposit_id"] or "",
                (e.get("title") or "")[:200], e["construct"]["description"][:160], " ".join(e["conditions"]["ligands"])[:160],
                "; ".join(state_names.get(m["state_id"], m["state_id"]) for m in e["mappings"]),
            ])
        for t in mapped["coverage"]["techniques"]:
            count = sum(1 for e in mapped["evidence"] if e["technique"] == t)
            technique_acc.setdefault(t, []).append({"acc": acc, "name": protein["name"], "count": count})
        evidence_out = [e for e in mapped["evidence"] if redistributable.get(e["provenance"]["source"], True)]
        bundle = {
            "molecule_id": acc,
            "molecule": protein,
            "curation": mapped["curation"],
            "states": mapped["states"],
            "transitions": mapped["transitions"],
            "evidence": evidence_out,
            "conflicts": mapped["conflicts"],
            "coverage": mapped["coverage"],
            "models": models,
        }
        bundles[acc] = bundle
        write_json(site / "downloads" / "proteins" / f"{acc}.json", bundle)
        all_lines += [{"record_type": "molecule", **protein}]
        all_lines += [{"record_type": "state", **s} for s in mapped["states"]]
        all_lines += [{"record_type": "transition", **t} for t in mapped["transitions"]]
        all_lines += [{"record_type": "evidence", **e} for e in evidence_out]
        all_lines += [{"record_type": "model", **m} for m in models]
        models_src = paths.build / acc / "models"
        if models_src.exists():
            shutil.copytree(models_src, site / "downloads" / "models" / acc)

        out_dir = site / "protein" / acc
        out_dir.mkdir(parents=True)
        (out_dir / "index.html").write_text(_protein_page(paths, acc, protein, mapped, models, taxonomy), encoding="utf-8")

    with (site / "downloads" / "all-records.jsonl").open("w", encoding="utf-8") as fh:
        for line in all_lines:
            fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")

    for t_id, tech in taxonomy.items():
        covered = sorted(technique_acc.get(t_id, []), key=lambda c: c["acc"])
        page_dir = site / "technique" / t_id
        page_dir.mkdir(parents=True)
        (page_dir / "index.html").write_text(_technique_page(t_id, tech, covered), encoding="utf-8")

    technique_order = [tid for tid in taxonomy if any(tid in s["tech_counts"] for s in summaries)]
    (site / "proteins").mkdir(parents=True, exist_ok=True)
    (site / "proteins" / "index.html").write_text(
        _proteins_page(summaries, [m.NAME for m in IMPLEMENTED], technique_order, taxonomy), encoding="utf-8")
    (site / "index.html").write_text(_home_page(summaries, technique_order), encoding="utf-8")
    _write_search(site, summaries, search_rows, technique_order, taxonomy)
    _write_about(paths, site)
    _write_downloads(paths, site, accessions)
    (site / "CNAME").write_text("conformome.org\n", encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")


def _write_about(paths: Paths, site: Path) -> None:
    parts = []
    for name in ("METHODS.md", "CONTRIBUTING.md", "SOURCES.md"):
        parts.append(md_to_html((paths.docs / name).read_text(encoding="utf-8")))
    body = ('<h1>About and methods</h1>'
            '<p class="sub">The mapping rules, the observed and inferred rule, sources and licences, and how to contribute.</p>'
            + "\n".join(parts))
    (site / "about").mkdir(parents=True)
    (site / "about" / "index.html").write_text(page("About and methods", body, "../"), encoding="utf-8")


def _write_downloads(paths: Paths, site: Path, accessions: list[str]) -> None:
    dl = site / "downloads"
    (dl / "schema").mkdir(parents=True, exist_ok=True)
    for p in paths.schema.glob("*.schema.json"):
        shutil.copy(p, dl / "schema" / p.name)
    (dl / "taxonomy").mkdir(parents=True, exist_ok=True)
    shutil.copy(paths.taxonomy / "techniques.yaml", dl / "taxonomy" / "techniques.yaml")
    (dl / "taxonomy" / "state_vocabularies").mkdir(parents=True, exist_ok=True)
    for v in (paths.taxonomy / "state_vocabularies").glob("*.yaml"):
        shutil.copy(v, dl / "taxonomy" / "state_vocabularies" / v.name)
    if paths.manifest.exists():
        shutil.copy(paths.manifest, dl / "manifest.json")
    else:
        write_json(dl / "manifest.json", {})
    body = ('<h1>Downloads</h1>'
            '<p class="sub">Every file is generated from the pipeline. Records carry provenance and conditions.</p>'
            '<ul>'
            '<li><a href="all-records.jsonl">All records, one JSON object per line</a> (record_type: molecule, state, transition, evidence, model)</li>'
            + "".join(f'<li><a href="proteins/{esc(acc)}.json">{esc(acc)}: protein bundle (JSON)</a></li>' for acc in accessions)
            + '<li><a href="schema/molecule.schema.json">JSON Schemas</a> for molecule, state, evidence, transition, model, mutational effect and state vocabulary, '
            'plus <a href="schema/common.schema.json">shared definitions</a></li>'
            '<li><a href="taxonomy/techniques.yaml">Technique taxonomy</a> and '
            + ", ".join(f'<a href="taxonomy/state_vocabularies/{esc(v.name)}">{esc(v.stem)}</a>'
                        for v in sorted((paths.taxonomy / "state_vocabularies").glob("*.yaml")))
            + ' state vocabularies</li>'
            '<li><a href="manifest.json">Download manifest</a>: source URLs, retrieval dates and SHA-256 of every raw input</li>'
            '</ul>'
            '<p class="muted">State models are linked from each protein page. Evidence from sources whose licence forbids '
            'redistribution is left out of these files; the site links to the source instead.</p>')
    (dl / "index.html").write_text(page("Downloads", body, "../"), encoding="utf-8")


SEARCH_JS = r"""
(function(){
  var P=[], E=null, byAcc={};
  var $=function(id){return document.getElementById(id)};
  var q=$('s-q'), out=$('s-results'), evOut=$('s-evidence'), info=$('s-info');
  var facets=['technique','source','organism','curation','basis'];
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function tokens(){return q.value.toLowerCase().split(/\s+/).filter(Boolean)}
  function hit(text,toks){text=text.toLowerCase();for(var i=0;i<toks.length;i++){if(text.indexOf(toks[i])<0)return false}return true}
  function mark(s,toks){var h=esc(s);toks.forEach(function(t){if(t.length<2)return;var re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig');h=h.replace(re,'<mark>$1</mark>')});return h}
  function val(f){return $('f-'+f).value}
  function protOk(p){
    if(val('technique')&&!(val('technique') in p.tech_counts))return false;
    if(val('source')&&p.source_list.indexOf(val('source'))<0)return false;
    if(val('organism')&&p.organism!==val('organism'))return false;
    if(val('curation')&&p.status!==val('curation'))return false;
    if(val('basis')&&!p.state_list.some(function(s){return s.basis===val('basis')}))return false;
    return true;
  }
  function ptext(p){return [p.name,p.acc,p.gene,p.organism,Object.keys(p.tech_counts).join(' '),p.source_list.join(' '),
    p.state_list.map(function(s){return s.name+' '+s.id}).join(' ')].join(' ')}
  function sync(){
    var u=new URLSearchParams(); if(q.value)u.set('q',q.value);
    facets.forEach(function(f){if(val(f))u.set(f,val(f))});
    history.replaceState(null,'',u.toString()?'?'+u.toString():location.pathname);
  }
  function card(p,toks,n){
    var chips=Object.keys(p.tech_counts).map(function(t){return '<span class="chip">'+esc(t)+' '+p.tech_counts[t]+'</span>'}).join('');
    var states=p.state_list.map(function(s){return '<span class="badge badge-'+esc(s.basis)+'">'+mark(s.name,toks)+'</span>'}).join(' ');
    var cur=p.status==='uncurated'?'<span class="muted">states not yet curated</span>':(p.status==='draft'?'<span class="badge badge-draft">draft curation</span>':'reviewed');
    var hits=n?'<div style="margin-top:6px"><a href="#s-evidence" data-acc="'+esc(p.acc)+'" class="ev-jump">'+n+' matching evidence item'+(n===1?'':'s')+'</a></div>':'';
    return '<div class="card"><h3><a href="../protein/'+esc(p.acc)+'/index.html">'+mark(p.name,toks)+'</a></h3>'+
      '<div class="muted">'+mark(p.acc,toks)+(p.gene?' · '+mark(p.gene,toks):'')+' · '+mark(p.organism,toks)+'</div>'+
      '<div class="chips">'+chips+'</div><div>'+(states||'')+'</div>'+
      '<div class="muted" style="margin-top:6px">'+p.evidence+' evidence · '+p.mapped+' mapped · '+p.source_list.length+' sources · '+cur+'</div>'+hits+'</div>';
  }
  function evidenceHits(toks){
    // Returns {rows: first 200 matches, total, perAcc: counts}, or null when the evidence index is not needed or not loaded.
    if(!toks.length&&!val('technique')&&!val('source'))return null;
    if(!E)return 'loading';
    var rows=[],total=0,perAcc={};
    for(var i=0;i<E.length;i++){
      var e=E[i], p=byAcc[e[1]];
      if(!p||!protOk(p))continue;
      if(val('technique')&&e[2]!==val('technique'))continue;
      if(val('source')&&e[3]!==val('source'))continue;
      if(!hit(e.join(' ')+' '+p.name,toks))continue;
      total++; perAcc[e[1]]=(perAcc[e[1]]||0)+1; if(rows.length<200)rows.push([e,p]);
    }
    return {rows:rows,total:total,perAcc:perAcc};
  }
  function render(){
    sync();
    var toks=tokens(), ev=evidenceHits(toks);
    if(ev==='loading'){evOut.innerHTML='<p class="muted">Loading the evidence index...</p>';
      fetch('evidence.json').then(function(r){return r.json()}).then(function(d){E=d;render()})
        .catch(function(){evOut.innerHTML='<p class="muted">The evidence index could not be loaded.</p>'});ev=null}
    var per=(ev&&ev.perAcc)||{};
    // A protein is listed when its own text matches, or when any of its evidence matches.
    var ps=P.filter(function(p){return protOk(p)&&(hit(ptext(p),toks)||per[p.acc])});
    ps.sort(function(a,b){var ma=hit(ptext(a),toks)?1:0, mb=hit(ptext(b),toks)?1:0;
      return (mb-ma)||((per[b.acc]||0)-(per[a.acc]||0))||(b.evidence-a.evidence)});
    out.innerHTML=ps.length?ps.map(function(p){return card(p,toks,per[p.acc])}).join(''):'<p class="muted">No proteins match.</p>';
    info.textContent=ps.length+' of '+P.length+' proteins';
    if(!ev){
      if(!toks.length&&!val('technique')&&!val('source'))
        evOut.innerHTML='<p class="muted">Type a query to search individual evidence items (PDB, BMRB and SASBDB IDs, titles, ligands, mapped states).</p>';
      return;  // otherwise the evidence index is loading and render() runs again when it arrives
    }
    evOut.innerHTML='<p class="muted">'+ev.total+' evidence items'+(ev.total>200?'; first 200 shown':'')+'</p>'+
      (ev.rows.length?'<div class="scroll"><table><thead><tr><th>Evidence</th><th>Protein</th><th>Technique</th><th>Title and construct</th><th>Mapped to</th></tr></thead><tbody>'+
      ev.rows.map(function(r){var e=r[0],p=r[1];return '<tr><td><a href="../protein/'+esc(e[1])+'/index.html#'+esc(e[0])+'">'+mark(e[0],toks)+'</a><br><span class="muted">'+esc(e[3])+'</span></td>'+
        '<td>'+esc(p.name)+'</td><td>'+esc(e[2])+'</td><td>'+mark(e[5],toks)+'<br><span class="muted">'+mark(e[6],toks)+(e[7]?' · '+mark(e[7],toks):'')+'</span></td>'+
        '<td>'+(e[8]?mark(e[8],toks):'<span class="muted">unmapped</span>')+'</td></tr>'}).join('')+'</tbody></table></div>':'');
  }
  fetch('proteins.json').then(function(r){return r.json()}).then(function(d){
    P=d; P.forEach(function(p){byAcc[p.acc]=p});
    var opts={technique:{},source:{},organism:{},curation:{},basis:{observed:1,inferred:1}};
    P.forEach(function(p){Object.keys(p.tech_counts).forEach(function(t){opts.technique[t]=1});
      p.source_list.forEach(function(s){opts.source[s]=1});opts.organism[p.organism]=1;opts.curation[p.status]=1});
    facets.forEach(function(f){var sel=$('f-'+f);Object.keys(opts[f]).sort().forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o)})});
    var u=new URLSearchParams(location.search); q.value=u.get('q')||'';
    facets.forEach(function(f){if(u.get(f))$('f-'+f).value=u.get(f)});
    render();
  }).catch(function(){out.innerHTML='<p class="muted">The protein index could not be loaded.</p>'});
  var timer; q.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(render,150)});
  facets.forEach(function(f){$('f-'+f).addEventListener('change',render)});
  $('s-form').addEventListener('submit',function(ev){ev.preventDefault();render()});
})();
"""


def _write_search(site: Path, summaries: list[dict], search_rows: list[list], techniques: list[str], taxonomy: dict) -> None:
    out = site / "search"
    out.mkdir(parents=True, exist_ok=True)
    proteins = [{k: s[k] for k in ("acc", "name", "gene", "organism", "length", "status", "evidence", "mapped",
                                   "tech_counts", "source_list", "state_list")} for s in summaries]
    (out / "proteins.json").write_text(json.dumps(proteins, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "evidence.json").write_text(json.dumps(search_rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    selects = "".join(f'<select id="f-{f}" aria-label="{label}"><option value="">{label}: any</option></select>'
                      for f, label in (("technique", "Technique"), ("source", "Source"), ("organism", "Organism"),
                                       ("curation", "Curation"), ("basis", "State basis")))
    body = ('<h1>Search</h1>'
            '<p class="sub">Search proteins, states and individual evidence items. Every word must match. '
            'Filters narrow both proteins and evidence; the address bar keeps the search, so it can be shared.</p>'
            '<form id="s-form" class="searchbar" role="search"><input id="s-q" type="search" '
            'placeholder="for example: maltose closed, 1UBQ, fibril cryoem, unfolding_force" aria-label="Search" autofocus>'
            '<button type="submit">Search</button></form>'
            f'<div class="controls">{selects}</div>'
            '<p class="muted" id="s-info" aria-live="polite"></p>'
            '<h2>Proteins</h2><div id="s-results" class="cards"></div>'
            '<h2>Evidence</h2><div id="s-evidence"></div>'
            '<noscript><p>Search needs JavaScript. The <a href="../index.html">protein list</a> works without it.</p></noscript>')
    (out / "index.html").write_text(page("Search", body, "../", scripts=f"<script>{SEARCH_JS}</script>",
                                         description="Search Conformome proteins, states and evidence"), encoding="utf-8")
