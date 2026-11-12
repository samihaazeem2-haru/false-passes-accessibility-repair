"""Step 2h: blind human labels for a fixed random sample of checker-passing AccessGuru-final repairs. Free.

make:  draw 120 items = 40 per model (GPT4, Mistral, Qwen), simple random sample (seed 20261023) of the
       AccessGuru-final repairs that pass the paper's checker on the 186 baseline-detected cases. The draw
       uses ONLY step1 checker output -- never any judge output -- so labellers and judge are independent.
       It writes one self-contained page per labeller (labeling_A.html, labeling_B.html; same items, each in
       its own shuffled order) showing only the rule, its description, the original fragment and the repair:
       no model name, no method, no checker result, no AI verdict. Each page has the rubric and worked
       examples, keeps labels in the browser and downloads human_labels_<labeller>.csv.
       The hidden key (step2/labeling_key.csv) must not be shown to labellers. An existing sample is never
       redrawn unless --force is given.
merge: join the two labellers' CSVs with the key -> step2/human_labels.csv (read by step3_analyze.py), and
       list items that need adjudication in step2/adjudication_todo.csv. To adjudicate, both labellers
       discuss each listed item, fill final_verdict, save it as step2/adjudication.csv and run merge again.
       consensus = the shared label when both say fixed/not_fixed alike, else the adjudicated label.

Usage (from the Data folder):
    python -I experiment/scripts/step2h_labeling.py make  experiment
    python -I experiment/scripts/step2h_labeling.py merge experiment <human_labels_A.csv> <human_labels_B.csv>
"""
import argparse
import collections
import csv
import html
import json
import os
import random
import sys

csv.field_size_limit(10**9)
MODELS = ["GPT4", "Mistral", "Qwen"]
SEED = 20261023
LABELLERS = ["A", "B"]
VERDICTS = ("fixed", "not_fixed", "unclear")

RUBRIC_HTML = """<ol>
<li><b>Concrete code.</b> The repair is HTML/CSS that could replace the original fragment &mdash; not advice,
 a comment, a placeholder ("code would go here") or a description of what to do.</li>
<li><b>Keeps the content.</b> It keeps the original element(s), their text/content and their purpose.
 Deleting, emptying, hiding (<code>display:none</code>, <code>aria-hidden="true"</code>, &hellip;) or replacing
 the element with unrelated markup is <b>not</b> a fix. Wrapping the fragment in a full page is fine.</li>
<li><b>Resolves this violation</b> as WCAG and the named axe rule intend. For colour contrast the new colours
 must plausibly meet the ratio (4.5:1 normal text, 3:1 large text; 7:1 / 4.5:1 for <i>-enhanced</i>).
 A name/label/alt must be meaningful, not filler such as "image" or "link".</li>
<li><b>No new barrier</b> of similar or greater severity (e.g. removing <code>lang</code>, breaking a label,
 making something unfocusable).</li>
</ol>
<p>If several elements are affected and only some are repaired: <b>Not fixed</b>.
 Use <b>Unclear</b> only when the fragment genuinely lacks the information to decide (e.g. contrast depends on a
 CSS class whose colours are not shown). Judge each item on its own; do not discuss items with the other
 labeller until you have both downloaded your CSVs.</p>"""

EXAMPLES = [
    ("image-alt", "Images must have alternate text",
     '<img src="logo.png" class="brand">', '<img src="logo.png" class="brand" alt="Acme Corp logo">',
     "Fixed", "Concrete code, same element, meaningful alt text."),
    ("link-name", "Links must have discernible text",
     '<a href="/cart"><i class="icon-cart"></i></a>', "<!-- Corrected HTML with an aria-label would go here -->",
     "Not fixed", "A placeholder comment, not code (rule 1)."),
    ("image-alt", "Images must have alternate text",
     '<img src="sales-chart.png">', '<img src="sales-chart.png" aria-hidden="true">',
     "Not fixed", "The checker no longer complains, but a meaningful image was hidden (rule 2)."),
    ("button-name", "Buttons must have discernible text",
     '<div class="nav"><button class="menu"></button> <a href="/">Home</a></div>',
     '<button class="menu" aria-label="Open menu"></button>',
     "Not fixed", "The button is named, but the Home link and wrapper were dropped (rule 2)."),
    ("color-contrast", "Elements must have sufficient color contrast",
     '<p style="color:#999999;background:#ffffff">Sale ends today</p>',
     '<p style="color:#595959;background:#ffffff">Sale ends today</p>',
     "Fixed", "#595959 on white is about 7:1, above 4.5:1; text unchanged."),
]


def jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def load_sample(art):
    return [r for r in csv.DictReader(open(os.path.join(art, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                           encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]


def draw(exp, per_model):
    """Judge-free draw: only step1 checker output is read."""
    rng = random.Random(SEED)
    rows = list(csv.DictReader(open(os.path.join(exp, "step1/checker_on_paper_outputs.csv"), encoding="utf-8")))
    picked = []
    for model in MODELS:
        pool = sorted((r for r in rows if r["model"] == model and r["method"] == "accessguru_final" and r["checker_pass"] == "True"),
                      key=lambda r: int(r["row"]))
        picked += [{"model": model, "pool_size": len(pool), **{k: r[k] for k in ("row", "id", "category", "rule")}}
                   for r in rng.sample(pool, per_model)]
    rng.shuffle(picked)
    return [{"item_id": f"H{i:03d}", **p} for i, p in enumerate(picked, 1)]


def card(item_id, s, resp):
    return f"""
<section class="card" data-id="{item_id}" id="{item_id}">
  <h2>{item_id} &middot; rule <code>{html.escape(s['violationnumberID'].strip())}</code></h2>
  <p class="desc">{html.escape(s['description'].strip())}</p>
  <p class="desc"><b>axe failure summary (original):</b> {html.escape(s['failureSummary'].strip() or '(none)')}</p>
  <div class="cols">
    <div><h3>Original fragment</h3><pre>{html.escape(s['affectedHTMLElement(s)'])}</pre></div>
    <div><h3>Proposed repair</h3><pre>{html.escape(resp)}</pre></div>
  </div>
  <div class="choice" role="radiogroup" aria-label="Verdict for {item_id}">
    <label><input type="radio" name="{item_id}" value="fixed"> Fixed</label>
    <label><input type="radio" name="{item_id}" value="not_fixed"> Not fixed</label>
    <label><input type="radio" name="{item_id}" value="unclear"> Unclear</label>
    <input class="note" type="text" placeholder="optional note (why)" aria-label="Note for {item_id}" data-note="{item_id}">
  </div>
</section>"""


def example_html():
    out = []
    for i, (rule, desc, orig, rep, verdict, why) in enumerate(EXAMPLES, 1):
        out.append(f"""<div class="ex"><b>Example {i}</b> &middot; rule <code>{rule}</code> &mdash; {html.escape(desc)}
<div class="cols"><div><h3>Original fragment</h3><pre>{html.escape(orig)}</pre></div>
<div><h3>Proposed repair</h3><pre>{html.escape(rep)}</pre></div></div>
<p class="answer">Answer: <b>{verdict}</b>. {html.escape(why)}</p></div>""")
    return "\n".join(out)


def page(labeller, cards, n):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repair Labeling {labeller}</title>
<style>
:root {{ --bg:#fafafa; --fg:#1b1b1b; --card:#fff; --line:#d8d8d8; --muted:#555; --code:#f3f3f3; --accent:#1f5fbf; --ex:#eef4ff; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141414; --fg:#eee; --card:#1e1e1e; --line:#3a3a3a; --muted:#aaa; --code:#262626; --accent:#7fb0ff; --ex:#1b2333; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; margin:0; padding:16px; }}
header {{ position:sticky; top:0; background:var(--bg); padding:8px 0; border-bottom:1px solid var(--line); z-index:1; }}
.card, .intro {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 16px; margin:16px 0; }}
.ex {{ background:var(--ex); border-radius:6px; padding:8px 12px; margin:10px 0; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.cols > div {{ min-width:0; }}
@media (max-width:800px) {{ .cols {{ grid-template-columns:1fr; }} }}
pre {{ background:var(--code); padding:8px; max-height:420px; overflow:auto; white-space:pre-wrap; word-break:break-all; font-size:12.5px; }}
h2 {{ font-size:17px; margin:4px 0; }} h3 {{ font-size:13px; margin:6px 0 2px; color:var(--muted); }}
.desc {{ color:var(--muted); margin:4px 0; }}
.choice label {{ margin-right:16px; }}
.note {{ width:min(420px,100%); margin-top:6px; }}
button {{ background:var(--accent); color:#fff; border:0; border-radius:6px; padding:6px 12px; cursor:pointer; }}
#todo {{ color:var(--muted); font-size:13px; }}
</style></head><body>
<header><b>Repair labeling &middot; labeller {labeller}</b> &middot; <span id="count">0</span> / {n} labelled
 <button id="dl">Download CSV</button> <span id="todo"></span></header>
<section class="intro">
<h2>What to do</h2>
<p>Each item shows an accessibility violation found by an automated tool, the original HTML fragment, and a
proposed repair. Decide whether the repair <b>truly</b> fixes the violation. Labels are saved in this browser as you
go; when finished click <b>Download CSV</b> and send <code>human_labels_{labeller}.csv</code> back. Work alone.</p>
<details open><summary><b>Rubric: "Fixed" only if all four hold</b></summary>{RUBRIC_HTML}</details>
<details><summary><b>Worked examples (not part of the {n} items)</b></summary>{example_html()}</details>
</section>
{''.join(cards)}
<script>
const KEY = "repair-labels-v2-{labeller}";
let st = {{}};
try {{ st = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function save() {{ try {{ localStorage.setItem(KEY, JSON.stringify(st)); }} catch (e) {{}} count(); }}
function count() {{
  const ids = [...document.querySelectorAll(".card")].map(c => c.dataset.id);
  const left = ids.filter(id => !(st[id] && st[id].v));
  document.getElementById("count").textContent = ids.length - left.length;
  document.getElementById("todo").textContent = left.length ? "next unlabelled: " + left[0] : "all labelled";
}}
document.querySelectorAll("input[type=radio]").forEach(r => {{
  if (st[r.name] && st[r.name].v === r.value) r.checked = true;
  r.addEventListener("change", () => {{ st[r.name] = {{...(st[r.name]||{{}}), v:r.value}}; save(); }});
}});
document.querySelectorAll("input.note").forEach(n => {{
  const id = n.dataset.note; if (st[id] && st[id].n) n.value = st[id].n;
  n.addEventListener("input", () => {{ st[id] = {{...(st[id]||{{}}), n:n.value}}; save(); }});
}});
document.getElementById("dl").addEventListener("click", () => {{
  const q = s => '"' + String(s||"").replace(/"/g,'""') + '"';
  const rows = ["item_id,labeller,human_verdict,note"].concat(
    [...document.querySelectorAll(".card")].map(c => {{ const id=c.dataset.id, v=st[id]||{{}}; return [id, "{labeller}", v.v||"", q(v.n)].join(","); }}));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.join("\\n")], {{type:"text/csv"}}));
  a.download = "human_labels_{labeller}.csv"; a.click();
}});
count();
</script></body></html>"""


def make(exp, per_model, force):
    out = os.path.join(exp, "step2")
    key_path = os.path.join(out, "labeling_key.csv")
    if os.path.exists(key_path) and not force:
        sys.exit(f"{key_path} exists: the sample is fixed. Use --force only if no one has started labelling.")
    sample = load_sample(os.path.join(exp, "artifact"))
    responses = {(r["model"], r["method"], int(r["row"])): r["response"] for r in jsonl(os.path.join(exp, "step1/responses.jsonl"))}
    key_rows = draw(exp, per_model)

    for n, labeller in enumerate(LABELLERS):
        order = list(key_rows)
        random.Random(SEED + 1 + n).shuffle(order)  # each labeller sees the items in a different order
        cards = [card(k["item_id"], sample[int(k["row"])], responses[(k["model"], "accessguru_final", int(k["row"]))]) for k in order]
        with open(os.path.join(out, f"labeling_{labeller}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(labeller, cards, len(order)))
    with open(key_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(key_rows[0].keys()))
        w.writeheader()
        w.writerows(key_rows)
    print(f"sample: {len(key_rows)} items, seed {SEED}; per model {dict(collections.Counter(k['model'] for k in key_rows))}")
    pools = {k["model"]: k["pool_size"] for k in key_rows}
    print(f"pool sizes (checker-passing AccessGuru final): {pools}")
    print(f"distinct cases: {len({k['row'] for k in key_rows})}; categories {dict(collections.Counter(k['category'] for k in key_rows))}")
    print(f"wrote {', '.join(f'step2/labeling_{l}.html' for l in LABELLERS)} and step2/labeling_key.csv (hidden key)")


def read_labels(path):
    rows = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        v = (r.get("human_verdict") or "").strip()
        if v and v not in VERDICTS:
            sys.exit(f"{path}: unknown verdict {v!r} for {r['item_id']}")
        rows[r["item_id"].strip()] = {"verdict": v, "note": r.get("note", "")}
    return rows


def merge(exp, path_a, path_b):
    out = os.path.join(exp, "step2")
    key = list(csv.DictReader(open(os.path.join(out, "labeling_key.csv"), encoding="utf-8")))
    la, lb = read_labels(path_a), read_labels(path_b)
    adj_path = os.path.join(out, "adjudication.csv")
    adj = {}
    if os.path.exists(adj_path):
        for r in csv.DictReader(open(adj_path, encoding="utf-8-sig")):
            v = (r.get("final_verdict") or "").strip()
            if v:
                if v not in VERDICTS:
                    sys.exit(f"adjudication.csv: unknown verdict {v!r} for {r['item_id']}")
                adj[r["item_id"]] = v
    rows, todo = [], []
    for k in key:
        a, b = la.get(k["item_id"], {}), lb.get(k["item_id"], {})
        va, vb = a.get("verdict", ""), b.get("verdict", "")
        agreed = va == vb and va in ("fixed", "not_fixed")
        consensus = va if agreed else adj.get(k["item_id"], "")
        if va and vb and not agreed:
            todo.append({"item_id": k["item_id"], "label_A": va, "note_A": a.get("note", ""),
                         "label_B": vb, "note_B": b.get("note", ""), "final_verdict": adj.get(k["item_id"], "")})
        rows.append({**{f: k[f] for f in ("item_id", "model", "row", "id", "category", "rule")},
                     "label_A": va, "label_B": vb, "note_A": a.get("note", ""), "note_B": b.get("note", ""),
                     "adjudicated": adj.get(k["item_id"], ""), "consensus": consensus})
    with open(os.path.join(out, "human_labels.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "adjudication_todo.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "label_A", "note_A", "label_B", "note_B", "final_verdict"])
        w.writeheader()
        w.writerows(todo)
    print(f"labelled: A {sum(bool(r['label_A']) for r in rows)}, B {sum(bool(r['label_B']) for r in rows)} of {len(rows)}")
    print(f"agreed fixed/not_fixed: {sum(r['label_A'] == r['label_B'] and r['label_A'] in ('fixed', 'not_fixed') for r in rows)}; "
          f"need adjudication: {len(todo)} (adjudicated: {sum(bool(t['final_verdict']) for t in todo)}) -> step2/adjudication_todo.csv")
    print(f"consensus available: {sum(bool(r['consensus']) for r in rows)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["make", "merge"])
    ap.add_argument("exp")
    ap.add_argument("labels", nargs="*", help="merge: human_labels_A.csv human_labels_B.csv")
    ap.add_argument("--per-model", type=int, default=40)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    exp = os.path.abspath(a.exp)
    if a.action == "make":
        make(exp, a.per_model, a.force)
    else:
        if len(a.labels) != 2:
            sys.exit("merge needs two CSVs: labeller A and labeller B")
        merge(exp, *a.labels)
