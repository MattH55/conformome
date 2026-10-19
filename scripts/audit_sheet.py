"""Build a self-contained offline review sheet from a round's sample.jsonl.

The sheet shows the evidence and the protein's state definitions. It does not
show rule ids or the state under test. Choice buttons are numbered; the mapping
from a number to a state id lives in the page script, outside the item cards.
"""
from __future__ import annotations

import html
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _fmt_conditions(cond: dict | None) -> str:
    if not cond:
        return "not reported"
    parts = []
    if cond.get("environment"):
        parts.append(str(cond["environment"]))
    if cond.get("ph") is not None:
        parts.append(f"pH {cond['ph']}")
    if cond.get("temperature_c") is not None:
        parts.append(f"{cond['temperature_c']} °C")
    if cond.get("buffer"):
        parts.append(f"buffer {cond['buffer']}")
    if cond.get("salt_mM") is not None:
        parts.append(f"salt {cond['salt_mM']} mM")
    if cond.get("ions"):
        parts.append("ions " + ", ".join(str(x) for x in cond["ions"]))
    if cond.get("ligands"):
        parts.append("ligands " + ", ".join(str(x) for x in cond["ligands"]))
    if cond.get("applied_force_pn") is not None:
        parts.append(f"force {cond['applied_force_pn']} pN")
    if cond.get("notes"):
        parts.append(str(cond["notes"]))
    return "; ".join(parts) if parts else "not reported"


def _fmt_observable(obs: dict | None) -> str:
    if not obs:
        return "not reported"
    if obs.get("value") is None:
        return f"{obs.get('type') or 'observable'} not reported"
    unit = obs.get("unit") or ""
    if obs.get("uncertainty") is None:
        return f"{obs.get('type')} {obs['value']} {unit}".strip()
    return f"{obs.get('type')} {obs['value']} ± {obs['uncertainty']} {unit}".strip()


def _evidence_html(ev: dict) -> str:
    labels = ", ".join(ev.get("labels") or []) or "none recorded"
    doi = ev.get("doi")
    doi_html = f'<a href="https://doi.org/{_esc(doi)}">{_esc(doi)}</a>' if doi else "none recorded"
    deposit = ev.get("deposit_id") or "none recorded"
    url = ev.get("deposit_url")
    deposit_html = f'<a href="{_esc(url)}">{_esc(deposit)}</a>' if url else _esc(deposit)
    return f"""
      <dl class="evidence">
        <dt>Technique</dt><dd>{_esc(ev.get("technique"))}</dd>
        <dt>Source</dt><dd>{_esc(ev.get("source"))}</dd>
        <dt>Deposit</dt><dd>{deposit_html}</dd>
        <dt>Title</dt><dd>{_esc(ev.get("title"))}</dd>
        <dt>Construct</dt><dd>{_esc(ev.get("construct"))}</dd>
        <dt>Tags</dt><dd>{_esc(labels)}</dd>
        <dt>Conditions</dt><dd>{_esc(_fmt_conditions(ev.get("conditions")))}</dd>
        <dt>Observable</dt><dd>{_esc(_fmt_observable(ev.get("observable")))}</dd>
        <dt>DOI</dt><dd>{doi_html}</dd>
      </dl>"""


def _definitions_html(acc: str, name: str, definitions: list[dict]) -> str:
    blocks = []
    for i, state in enumerate(definitions, start=1):
        assumptions = state.get("assumptions") or []
        assumption_html = "".join(f"<li>{_esc(a)}</li>" for a in assumptions) or "<li>none recorded</li>"
        parent = state.get("parent") or "none"
        pdb = state.get("representative_pdb") or "none"
        blocks.append(f"""
        <div class="state">
          <h3>{i}. {_esc(state.get("name"))}</h3>
          <p><b>Basis.</b> {_esc(state.get("basis"))}. <b>Parent.</b> {_esc(parent)}.
             <b>Representative PDB.</b> {_esc(pdb)}.</p>
          <p>{_esc(state.get("description"))}</p>
          <ul>{assumption_html}</ul>
        </div>""")
    body = "".join(blocks) if blocks else "<p>No state definitions recorded.</p>"
    return f'<section class="definitions" id="defs-{_esc(acc)}"><h2>{_esc(name)} ({_esc(acc)})</h2>{body}</section>'


def _choices_html(index: int, kind: str, definitions: list[dict]) -> str:
    name = f"answer-{index}"
    rows = []
    if kind == "conflict":
        options = [
            ("real", "real — a genuine disagreement"),
            ("construct", "construct — the constructs differ"),
            ("conditions", "conditions — conditions differ in a way the record does not capture"),
            ("method", "method — the observable means different things by method"),
            ("data_error", "data error — an error in the source or in ingestion"),
            ("cannot-tell", "cannot tell"),
        ]
        legend = "Verdict"
    elif kind == "states":
        options = [("yes", "yes"), ("no", "no")]
        legend = "Would you define these states differently?"
    else:
        options = [(str(i), f"{i + 1}. {state.get('name')}") for i, state in enumerate(definitions)]
        options.append(("none", "none of these states"))
        options.append(("cannot-tell", "cannot tell"))
        legend = "Which state does this entry support?"
    for value, label in options:
        rows.append(
            f'<label><input type="radio" name="{name}" value="{_esc(value)}"> {_esc(label)}</label>'
        )
    extra = ""
    if kind == "evidence":
        extra = f"""
        <fieldset>
          <legend>Confidence</legend>
          <label><input type="radio" name="confidence-{index}" value="high"> high</label>
          <label><input type="radio" name="confidence-{index}" value="medium"> medium</label>
          <label><input type="radio" name="confidence-{index}" value="low"> low</label>
        </fieldset>
        <fieldset>
          <legend>Does the construct cover the region that defines the state?</legend>
          <label><input type="radio" name="coverage-{index}" value="yes"> yes</label>
          <label><input type="radio" name="coverage-{index}" value="partial"> partial</label>
          <label><input type="radio" name="coverage-{index}" value="no"> no</label>
          <label><input type="radio" name="coverage-{index}" value="unknown"> unknown</label>
        </fieldset>"""
    return f"""
      <fieldset>
        <legend>{legend}</legend>
        {''.join(rows)}
      </fieldset>
      {extra}
      <label class="note">Note <textarea rows="2"></textarea></label>"""


def _card_html(index: int, item: dict) -> str:
    kind = item["kind"]
    protein = item["protein"]
    acc = protein["accession"]
    link = protein["page"]
    head = (
        f'<p class="protein"><a href="{_esc(link)}">{_esc(protein["name"])}</a> '
        f'({_esc(acc)}). <a href="#defs-{_esc(acc)}">State definitions</a>.</p>'
    )
    if kind == "conflict":
        body = (
            '<div class="pair"><div><h3>Entry A</h3>'
            + _evidence_html(item["evidence"])
            + '</div><div><h3>Entry B</h3>'
            + _evidence_html(item["evidence_b"])
            + "</div></div>"
        )
    elif kind == "states":
        body = "<p>Answer once for this protein, after you have seen its items.</p>"
    else:
        body = _evidence_html(item["evidence"])
    return f"""
    <article class="card" id="card-{index}" data-index="{index}" data-item="{_esc(item["item_id"])}" data-kind="{_esc(kind)}">
      <h2>Item {index + 1}</h2>
      {head}
      {body}
      {_choices_html(index, kind, item.get("definitions") or [])}
    </article>"""


_STYLE = """
body { margin: 0; font: 16px/1.4 Georgia, "Times New Roman", serif; color: #1b2733; background: #fff; }
header { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #d9d9d9; padding: 12px 16px; z-index: 2; }
h1 { font-size: 20px; margin: 0 0 8px; }
header p, header button { margin: 0 12px 0 0; }
button { font: 16px Georgia, serif; padding: 4px 10px; }
main { padding: 16px; max-width: 920px; }
.definitions, .card { border: 1px solid #d9d9d9; padding: 12px 16px; margin: 0 0 16px; }
.card.current { outline: 3px solid #2f6fa8; }
.protein { margin-top: 0; }
dl.evidence { display: grid; grid-template-columns: 9em 1fr; gap: 2px 8px; margin: 0; }
dt { font-weight: bold; }
dd { margin: 0; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
fieldset { border: 0; padding: 8px 0; margin: 0; }
legend { font-weight: bold; padding: 0; }
label { display: block; margin: 2px 0; }
.note textarea { width: 100%; box-sizing: border-box; font: 16px Georgia, serif; }
#progress { font-weight: bold; }
body.only-unanswered article.card.answered { display: none; }
@media (max-width: 700px) { .pair { grid-template-columns: 1fr; } }
"""

_SCRIPT = r"""
const ROUND = __ROUND__;
const CHOICE_IDS = __CHOICES__;
const mem = {};
function storageKey() { return "conformome-audit:" + ROUND; }
function readStore() {
  try {
    const raw = localStorage.getItem(storageKey());
    if (raw) Object.assign(mem, JSON.parse(raw));
  } catch (e) {}
  return mem;
}
function writeStore() {
  try { localStorage.setItem(storageKey(), JSON.stringify(mem)); }
  catch (e) {}
}
function cards() { return Array.from(document.querySelectorAll("article.card")); }
function named(card, prefix) {
  return Array.from(card.querySelectorAll("input")).filter(el => el.name === prefix + "-" + card.dataset.index);
}
function checked(card, prefix) {
  const el = named(card, prefix).find(el => el.checked);
  return el ? el.value : "";
}
function isAnswered(card) { return checked(card, "answer") !== ""; }
function exportAnswer(card) {
  const raw = checked(card, "answer");
  if (card.dataset.kind === "conflict") return "";
  if (raw === "cannot-tell") return "cannot tell";
  if (raw === "none" || raw === "yes" || raw === "no" || raw === "") return raw;
  const ids = CHOICE_IDS[card.dataset.item] || [];
  const id = ids[Number(raw)];
  return id == null ? "" : id;
}
function exportVerdict(card) {
  if (card.dataset.kind !== "conflict") return "";
  const raw = checked(card, "answer");
  return raw === "cannot-tell" ? "cannot tell" : raw;
}
function progress() {
  const all = cards();
  const n = all.filter(isAnswered).length;
  document.getElementById("progress").textContent = n + " / " + all.length + " answered";
}
function stamp(card) {
  if (!card || !card.dataset || !card.dataset.item) return;
  const id = card.dataset.item;
  const prev = mem[id] || {};
  const row = {
    answer: checked(card, "answer"),
    confidence: checked(card, "confidence"),
    coverage: checked(card, "coverage"),
    note: card.querySelector("textarea").value
  };
  const changed = ["answer", "confidence", "coverage", "note"].some(k => row[k] !== (prev[k] || ""));
  if (!changed && prev.answered_at) row.answered_at = prev.answered_at;
  else if (changed) row.answered_at = new Date().toISOString();
  else return;
  mem[id] = row;
  writeStore();
  card.classList.toggle("answered", isAnswered(card));
  progress();
}
let current = 0;
let unansweredOnly = false;
function visible(card) { return !unansweredOnly || !card.classList.contains("answered"); }
function focusCard(i) {
  const all = cards();
  if (!all.length) return;
  current = (i + all.length) % all.length;
  all.forEach(c => c.classList.remove("current"));
  all[current].classList.add("current");
  all[current].scrollIntoView({block: "nearest"});
}
function restore() {
  readStore();
  cards().forEach(card => {
    const row = mem[card.dataset.item];
    if (!row) return;
    ["answer", "confidence", "coverage"].forEach(prefix => {
      const value = row[prefix];
      if (!value) return;
      const el = named(card, prefix).find(input => input.value === value);
      if (el) el.checked = true;
    });
    if (row.note) card.querySelector("textarea").value = row.note;
    card.classList.toggle("answered", isAnswered(card));
  });
  progress();
}
function csvEscape(value) {
  const s = value == null ? "" : String(value);
  if (/[",\r\n]/.test(s)) return '"' + s.replaceAll('"', '""') + '"';
  return s;
}
document.getElementById("export").addEventListener("click", () => {
  const header = ["round_id", "item_id", "answer", "confidence", "coverage", "verdict", "note", "answered_at"];
  const lines = [header.join(",")];
  cards().forEach(card => {
    const saved = mem[card.dataset.item] || {};
    const cols = [
      ROUND, card.dataset.item, exportAnswer(card), checked(card, "confidence"),
      checked(card, "coverage"), exportVerdict(card), card.querySelector("textarea").value,
      saved.answered_at || ""
    ];
    lines.push(cols.map(csvEscape).join(","));
  });
  const blob = new Blob([lines.join("\n") + "\n"], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "responses.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
});
document.getElementById("filter").addEventListener("click", () => {
  unansweredOnly = !unansweredOnly;
  document.body.classList.toggle("only-unanswered", unansweredOnly);
  document.getElementById("filter").textContent = unansweredOnly ? "Show all items" : "Show unanswered";
});
document.addEventListener("keydown", (ev) => {
  if (ev.target.matches("textarea")) return;
  if (ev.key === "n" || ev.key === "N") {
    ev.preventDefault();
    const all = cards();
    for (let step = 1; step <= all.length; step++) {
      const i = (current + step) % all.length;
      if (visible(all[i])) { focusCard(i); break; }
    }
  }
  if (ev.key >= "1" && ev.key <= "9") {
    const card = cards()[current];
    if (!card) return;
    const inputs = named(card, "answer");
    const input = inputs[Number(ev.key) - 1];
    if (!input) return;
    input.checked = true;
    stamp(card);
  }
});
cards().forEach(card => {
  card.addEventListener("change", () => stamp(card));
  card.querySelector("textarea").addEventListener("input", () => stamp(card));
  card.addEventListener("click", () => focusCard(Number(card.dataset.index)));
});
restore();
focusCard(0);
"""


def render_html(items: list[dict], meta: dict) -> str:
    """Return the sheet. `meta` supplies round_id, part, tag and seed. No answer fields are read."""
    definitions = []
    seen = set()
    choice_ids = {}
    cards = []
    for index, item in enumerate(items):
        acc = item["protein"]["accession"]
        if acc not in seen:
            seen.add(acc)
            definitions.append(_definitions_html(acc, item["protein"]["name"], item.get("definitions") or []))
        if item.get("kind") == "evidence":
            choice_ids[item["item_id"]] = list(item.get("choice_ids") or [])
        cards.append(_card_html(index, item))
    part = meta.get("part", "")
    intro = {
        "A": "For each entry, choose the state it supports, or none of these states, or cannot tell. Keys 1–9 pick a choice. n moves to the next item.",
        "B": "Map each entry using the state definitions on this page. You are not shown anyone else's mapping. Keys 1–9 pick a choice. n moves to the next item. Once per protein, say whether you would define the states differently.",
        "C": "Each card shows two entries that were flagged as a possible conflict. Choose why, or cannot tell. Keys 1–6 pick a verdict. n moves to the next item.",
    }.get(part, "Answer every card, then export the CSV.")
    script = _SCRIPT.replace("__ROUND__", json.dumps(meta["round_id"])).replace(
        "__CHOICES__", json.dumps(choice_ids, ensure_ascii=True)
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Conformome audit { _esc(meta["round_id"]) }</title>
<style>{_STYLE}</style>
</head>
<body>
<header>
  <h1>Conformome audit, part {_esc(part)} — {_esc(meta["round_id"])}</h1>
  <p>{_esc(intro)}</p>
  <p>Release {_esc(meta.get("tag"))}, seed {_esc(meta.get("seed"))}. This file works from disk and does not load anything else.</p>
  <p id="progress">0 / {len(items)} answered</p>
  <button type="button" id="filter">Show unanswered</button>
  <button type="button" id="export">Export responses.csv</button>
</header>
<main>
{''.join(definitions)}
{''.join(cards)}
</main>
<script>{script}</script>
</body>
</html>
"""


def write_sheet(sample_path: Path, meta: dict, dest: Path) -> str:
    html_text = render_html(read_jsonl(sample_path), meta)
    dest.write_text(html_text, encoding="utf-8", newline="\n")
    return html_text
