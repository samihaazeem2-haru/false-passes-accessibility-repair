"""Step 2h, round 2: blind human labels with rubric v2 on 120 NEW checker-passing AccessGuru-final repairs. Free.

Round 1 (step2/, rubric v1, binary kappa 0.105) is kept unchanged as a pilot. This script never reads or
writes a round-1 output except step2/labeling_key.csv, which it only reads to exclude round-1 items and cases.
The rubric v1 text, card layout and worked examples are imported from step2h_labeling.py unchanged; the
v2 addendum and three extra worked examples are added here.

sample: draw 40 per model (GPT4, Mistral, Qwen), simple random sample (seed 20261026) of the AccessGuru-final
        repairs that pass the paper's checker on the 186 baseline-detected cases, EXCLUDING every case (dataset
        row) used in round 1 for any model, and therefore every round-1 item. Judge-free: only step1 checker
        output is read. Writes step2r2/sample_round2.csv (with a SHA-256 of each repair text, so the file hash
        pins the exact items) and step2r2/labeling_key_r2.csv (hidden key; ids R2-001..R2-120). Stops if a model
        has fewer than 40 eligible. Never redraws an existing sample unless --force.
pages:  requires experiment/PLAN_round2.md to contain the SHA-256 of sample_round2.csv (the analysis plan is
        frozen before the pages exist). Writes step2r2/labeling_A2.html and step2r2/labeling_B2.html: same 120
        items, a different random order each, blind (rule, description, axe failure summary, original, repair
        only). Labels are kept in the browser; the CSV downloads as human_labels_A2.csv / human_labels_B2.csv
        with the round-1 columns (item_id, labeller, human_verdict, note).
verify: re-reads both pages and checks: 120 cards each, same item set, different order, no model / method /
        checker / judge / shrink text, no API-key-like strings, no other labeller's name in the download code.
merge:  join the two CSVs with the key -> step2r2/human_labels_r2.csv; disagreements -> step2r2/adjudication_todo_r2.csv.
        To adjudicate, both labellers fill final_verdict (fixed / not_fixed / unclear) and save the file as
        step2r2/adjudication_r2.csv, then run merge again. Round-1 adjudication is never read.
adjpage: step2r2/adjudication_r2.html from adjudication_todo_r2.csv: each disputed item with both labels, a shared
        Fixed / Not fixed / Unclear choice and notes; blind like the labelling pages (same leak checks, run on build).
        Downloads adjudication_r2.csv (item_id, final_verdict, notes), which merge reads.

Usage (from the Data folder):
    python -I experiment/scripts/step2h_labeling_r2.py sample experiment
    python -I experiment/scripts/step2h_labeling_r2.py pages  experiment
    python -I experiment/scripts/step2h_labeling_r2.py verify experiment
    python -I experiment/scripts/step2h_labeling_r2.py merge  experiment <human_labels_A2.csv> <human_labels_B2.csv>
    python -I experiment/scripts/step2h_labeling_r2.py adjpage experiment
"""
import argparse
import collections
import csv
import hashlib
import html
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script folder from sys.path
import step2h_labeling as r1  # noqa: E402  (rubric v1 text, card layout, worked examples, page template)

csv.field_size_limit(10**9)
MODELS = r1.MODELS
SEED = 20261026
PER_MODEL = 40
LABELLERS = ["A2", "B2"]
VERDICTS = r1.VERDICTS
PREFIX = "R2-"

ADDENDUM = [
    "Concrete code: a full page or a fragment is fine if it could replace the original. Advice, comments, or "
    "placeholders (\"code would go here\") are not a fix.",
    "Keeps the content: compare original and repair element by element. NOT fixed if any original element, text, "
    "link, image or form control is removed, emptied, hidden (display:none, aria-hidden, hidden), or replaced by "
    "unrelated markup, or if the visible meaning changes (e.g. \"Sale\" becomes \"Buy now\"). Fine: whitespace, "
    "attribute order, wrapping in a full page, doctype/head/lang added, extra wrapper or extra elements added, as "
    "long as nothing original is lost.",
    "Resolves this violation: use the axe failure summary as the target. Names, labels and alt text must be "
    "non-empty and meaningful in context (not \"image\", \"link\", \"button\", \"click here\", a file name). For "
    "contrast, compute the ratio with a contrast checker using the final colours (do not eyeball). Structural rules "
    "(region, heading, landmark): the requested structure must exist in the repair.",
    "No new barrier: check for removed lang, broken label/for/id links, positive tabindex, hidden focusable "
    "elements, duplicate ids, conflicting roles.",
    "If several elements are affected, ALL must be fixed.",
    "Unclear is NOT a middle option. Use it only when information is missing from the item (e.g. contrast depends "
    "on CSS that is not shown). Never use it because the item is hard.",
    "Spend at most 4 minutes per item.",
]

EXTRA_EXAMPLES = [
    ("color-contrast", "Elements must have sufficient color contrast",
     '<a href="/sale" style="color:#999999;background:#ffffff">Sale</a>',
     '<a href="/sale" style="color:#777777;background:#ffffff">Sale</a>',
     "Not fixed", "It looks darker, but a contrast checker gives #777777 on #ffffff = 4.48:1, below the required "
     "4.5:1 (addendum 3: compute, do not eyeball)."),
    ("region", "All page content should be contained by landmarks",
     '<div class="promo"><h2>Offers</h2><a href="/deals">See deals</a></div>',
     '<!DOCTYPE html>\n<html lang="en">\n<head><title>Offers</title></head>\n<body>\n<main>\n'
     '  <div class="promo"><h2>Offers</h2><a href="/deals">See deals</a></div>\n</main>\n</body>\n</html>',
     "Fixed", "Wrapping in a full page with doctype, head and lang is fine; every original element, text and link "
     "is still there; the requested landmark (main) exists (addendum 2 and 3)."),
    ("color-contrast", "Elements must have sufficient color contrast",
     '<span class="hint">Optional</span>',
     '<span class="hint-dark">Optional</span>',
     "Unclear", "Only the class name changed and the colours of .hint-dark are not shown anywhere in the item, so "
     "the ratio cannot be computed: information is missing (addendum 6). If the colours were shown, you would "
     "compute the ratio and answer Fixed or Not fixed."),
]


def paths(exp):
    out = os.path.join(exp, "step2r2")
    return {"out": out, "sample": os.path.join(out, "sample_round2.csv"), "key": os.path.join(out, "labeling_key_r2.csv"),
            "plan": os.path.join(exp, "PLAN_round2.md"), "r1_key": os.path.join(exp, "step2", "labeling_key.csv"),
            "labels": os.path.join(out, "human_labels_r2.csv"), "todo": os.path.join(out, "adjudication_todo_r2.csv"),
            "adj": os.path.join(out, "adjudication_r2.csv")}


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def final_responses(exp):
    return {(r["model"], int(r["row"])): r["response"] for r in r1.jsonl(os.path.join(exp, "step1/responses.jsonl"))
            if r["method"] == "accessguru_final"}


def sample(exp, force):
    p = paths(exp)
    os.makedirs(p["out"], exist_ok=True)
    if os.path.exists(p["key"]) and not force:
        sys.exit(f"{p['key']} exists: the round-2 sample is fixed. Use --force only if no one has started labelling.")
    r1_key = list(csv.DictReader(open(p["r1_key"], encoding="utf-8")))
    r1_rows = {k["row"] for k in r1_key}
    r1_items = {(k["model"], k["row"]) for k in r1_key}
    rows = list(csv.DictReader(open(os.path.join(exp, "step1/checker_on_paper_outputs.csv"), encoding="utf-8")))
    resp = final_responses(exp)
    rng = random.Random(SEED)
    picked, short = [], {}
    for model in MODELS:
        full = [r for r in rows if r["model"] == model and r["method"] == "accessguru_final" and r["checker_pass"] == "True"]
        pool = sorted((r for r in full if r["row"] not in r1_rows and (model, r["row"]) not in r1_items), key=lambda r: int(r["row"]))
        print(f"{model}: checker-passing AccessGuru final {len(full)}; eligible after excluding round-1 cases {len(pool)}")
        if len(pool) < PER_MODEL:
            short[model] = len(pool)
            continue
        picked += [{"model": model, "full_pool_size": len(full), "eligible_pool_size": len(pool),
                    **{k: r[k] for k in ("row", "id", "category", "rule")},
                    "response_sha256": hashlib.sha256(resp[(model, int(r["row"]))].encode("utf-8")).hexdigest()}
                   for r in rng.sample(pool, PER_MODEL)]
    if short:
        sys.exit(f"STOP: fewer than {PER_MODEL} eligible for {short}. Nothing written.")
    rng.shuffle(picked)
    picked = [{"item_id": f"{PREFIX}{i:03d}", **x} for i, x in enumerate(picked, 1)]
    assert not ({x["row"] for x in picked} & r1_rows)
    with open(p["sample"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(picked[0].keys()))
        w.writeheader()
        w.writerows(picked)
    with open(p["key"], "w", encoding="utf-8", newline="") as fh:  # same columns as round 1's labeling_key.csv
        w = csv.DictWriter(fh, fieldnames=["item_id", "model", "pool_size", "row", "id", "category", "rule"])
        w.writeheader()
        w.writerows({**{k: x[k] for k in ("item_id", "model", "row", "id", "category", "rule")}, "pool_size": x["eligible_pool_size"]}
                    for x in picked)
    print(f"sample: {len(picked)} items, seed {SEED}; per model {dict(collections.Counter(x['model'] for x in picked))}")
    print(f"distinct cases: {len({x['row'] for x in picked})}; overlap with round-1 cases: 0; "
          f"categories {dict(collections.Counter(x['category'] for x in picked))}")
    print(f"sample_round2.csv sha256 {sha256_file(p['sample'])}")


def addendum_html():
    items = "".join(f"<li>{html.escape(t)}</li>" for t in ADDENDUM)
    return (f'<div class="addendum" role="note" aria-labelledby="add-h"><h2 id="add-h">Rubric v2 addendum: read this first '
            f'(same four conditions as v1, made precise)</h2><ol>{items}</ol></div>')


def extra_examples_html(start):
    out = []
    for i, (rule, desc, orig, rep, verdict, why) in enumerate(EXTRA_EXAMPLES, start):
        out.append(f"""<div class="ex"><b>Example {i} (v2 addendum)</b> &middot; rule <code>{rule}</code> &mdash; {html.escape(desc)}
<div class="cols"><div><h3>Original fragment</h3><pre>{html.escape(orig)}</pre></div>
<div><h3>Proposed repair</h3><pre>{html.escape(rep)}</pre></div></div>
<p class="answer">Answer: <b>{verdict}</b>. {html.escape(why)}</p></div>""")
    return "\n".join(out)


def page(labeller, cards, n):
    """The round-1 page with: the v2 addendum shown above the v1 rubric, three extra worked examples, a round-2
    storage key (file:// pages share one localStorage, so it must differ from round 1) and the round-2 file name."""
    doc = r1.page(labeller, cards, n)
    v1_open = '<details open><summary><b>Rubric: "Fixed" only if all four hold</b></summary>'
    assert doc.count(v1_open) == 1 and doc.count(f'const KEY = "repair-labels-v2-{labeller}";') == 1
    doc = doc.replace(v1_open, addendum_html() + '\n<details open><summary><b>Rubric v1 (unchanged): "Fixed" only if all four hold</b></summary>')
    ex_close = f"{r1.example_html()}</details>"
    assert doc.count(ex_close) == 1
    doc = doc.replace(f'<details><summary><b>Worked examples (not part of the {n} items)</b></summary>',
                      f'<details open><summary><b>Worked examples (not part of the {n} items)</b></summary>')
    doc = doc.replace(ex_close, f"{r1.example_html()}\n{extra_examples_html(len(r1.EXAMPLES) + 1)}</details>")
    doc = doc.replace(f'const KEY = "repair-labels-v2-{labeller}";', f'const KEY = "repair-labels-round2-{labeller}";')
    doc = doc.replace("<title>Repair Labeling", "<title>Repair Labeling Round 2")
    doc = doc.replace("<b>Repair labeling &middot;", "<b>Repair labeling round 2 &middot;")
    doc = doc.replace(".ex {", ".addendum { background:var(--ex); border:2px solid var(--accent); border-radius:8px; padding:8px 16px; margin:12px 0; }\n"
                               ".addendum h2 { margin-top:4px; }\n.ex {")
    return doc


def pages(exp):
    p = paths(exp)
    if not os.path.exists(p["plan"]):
        sys.exit("experiment/PLAN_round2.md missing: freeze the analysis plan before building the pages.")
    h = sha256_file(p["sample"])
    if h not in open(p["plan"], encoding="utf-8").read():
        sys.exit(f"PLAN_round2.md does not contain the sample hash {h}: the sample changed after the plan was frozen.")
    data = r1.load_sample(os.path.join(exp, "artifact"))
    resp = final_responses(exp)
    key = list(csv.DictReader(open(p["key"], encoding="utf-8")))
    for x in csv.DictReader(open(p["sample"], encoding="utf-8")):  # the repair text must be the one the plan froze
        assert hashlib.sha256(resp[(x["model"], int(x["row"]))].encode("utf-8")).hexdigest() == x["response_sha256"], x["item_id"]
    for n, labeller in enumerate(LABELLERS):
        order = list(key)
        random.Random(SEED + 1 + n).shuffle(order)  # each labeller sees the items in a different order
        cards = [r1.card(k["item_id"], data[int(k["row"])], resp[(k["model"], int(k["row"]))]) for k in order]
        with open(os.path.join(p["out"], f"labeling_{labeller}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(labeller, cards, len(order)))
        print(f"wrote step2r2/labeling_{labeller}.html ({len(cards)} items, first three {[k['item_id'] for k in order[:3]]})")


# Anywhere on the page, item data included: names of repairers, methods, judges, judge/checker fields, API keys.
LEAKS = [r"\bGPT-?4", r"\bgpt-", r"mistral", r"qwen", r"pixtral", r"openai", r"groq", r"gemini", r"llama",
         r"accessguru", r"checker_pass", r"judge_model", r"failure_mode", r"rationale", r"content_shrink", r"len_ratio",
         r"skipped_too_large", r"api[_-]?key", r"\bsk-[A-Za-z0-9_-]{16,}", r"\bgsk_[A-Za-z0-9]{16,}",
         r"AIza[0-9A-Za-z_-]{20,}", r"Bearer [A-Za-z0-9]"]
# In the page's own text (instructions, rubric, examples, code; item data removed) additionally: generic study words.
# Allowed rubric phrases are removed first: "contrast checker" (v2 addendum 3), "The checker no longer complains"
# (v1 worked example 3) and "Judge each item on its own" (v1 rubric), all of which are about how to label.
CHROME_ONLY = [r"checker", r"judge", r"shrink", r"\bmodel", r"baseline", r"re-?prompt", r"\bverdict\b(?! for R2-)",
               r"https?://", r"<(script|link|img|iframe)[^>]+(src|href)="]
ALLOWED = ["contrast checker", "The checker no longer complains", "Judge each item on its own"]


def chrome_and_data(doc):
    data = re.findall(r"<pre>(.*?)</pre>", doc, flags=re.S)
    chrome = re.sub(r"<pre>.*?</pre>", "<pre></pre>", doc, flags=re.S)
    for a in ALLOWED:
        chrome = chrome.replace(a, "")
    return chrome, "\n".join(data)


def verify(exp):
    p = paths(exp)
    key = {k["item_id"]: k for k in csv.DictReader(open(p["key"], encoding="utf-8"))}
    env_vals = []
    env = os.path.join(os.path.dirname(exp), ".env")
    if os.path.exists(env):  # check that no key VALUE leaked into a page, without ever printing it
        env_vals = [l.partition("=")[2].strip().strip('"').strip("'") for l in open(env, encoding="utf-8") if "=" in l]
        env_vals = [v for v in env_vals if len(v) >= 12]
    orders, ok = {}, True
    for labeller in LABELLERS:
        path = os.path.join(p["out"], f"labeling_{labeller}.html")
        doc = open(path, encoding="utf-8").read()
        chrome, data = chrome_and_data(doc)
        ids = re.findall(r'<section class="card" data-id="([^"]+)"', doc)
        orders[labeller] = ids
        others = [o for o in LABELLERS + ["A", "B"] if o != labeller]
        checks = {"120 cards": len(ids) == 120, "ids = key": set(ids) == set(key) and len(set(ids)) == len(ids),
                  "120 repairs shown": doc.count("<h3>Proposed repair</h3>") == 120 + len(r1.EXAMPLES) + len(EXTRA_EXAMPLES),
                  "addendum shown verbatim": all(html.escape(t) in doc for t in ADDENDUM),
                  "v1 rubric unchanged": r1.RUBRIC_HTML in doc,
                  "8 worked examples": doc.count('<div class="ex">') == len(r1.EXAMPLES) + len(EXTRA_EXAMPLES),
                  "download name": f'a.download = "human_labels_{labeller}.csv"' in doc,
                  "own storage key": f'"repair-labels-round2-{labeller}"' in doc,
                  "no other labeller in page code": not any(re.search(rf"labell?er {o}\b|human_labels_{o}\.csv|-{o}\"|\"{o}\"", chrome) for o in others),
                  "single inline script, no external resources": chrome.count("<script") == 1 and "<script>" in chrome,
                  "no .env value": not any(v in doc for v in env_vals)}
        hits = collections.Counter()
        for pat in LEAKS:
            hits.update({pat: len(re.findall(pat, doc, flags=re.I))})
        for pat in CHROME_ONLY:
            hits.update({pat: len(re.findall(pat, chrome, flags=re.I))})
        hits = +hits
        checks["no model/method/checker/judge/shrink/key text"] = not hits
        for name, good in checks.items():
            print(f"  {labeller}: {'OK  ' if good else 'FAIL'} {name}")
            ok &= good
        for pat, c in hits.items():
            src = doc if pat in LEAKS else chrome
            ctx = [src[max(0, m.start() - 60): m.end() + 60].replace("\n", " ") for m in re.finditer(pat, src, flags=re.I)][:3]
            print(f"      {pat!r} x{c}: {ctx}")
    diff = sum(a != b for a, b in zip(orders["A2"], orders["B2"]))
    print(f"  orders differ at {diff}/120 positions")
    ok &= diff > 100
    print("VERIFY", "PASSED" if ok else "FAILED")
    if not ok:
        sys.exit(1)


def merge(exp, path_a, path_b):
    """Same logic as round 1: agreed fixed/not_fixed -> consensus; otherwise the round-2 adjudicated label."""
    p = paths(exp)
    key = list(csv.DictReader(open(p["key"], encoding="utf-8")))
    ids = {k["item_id"] for k in key}
    la, lb = r1.read_labels(path_a), r1.read_labels(path_b)
    for name, lab in (("A2", la), ("B2", lb)):
        extra = set(lab) - ids
        if extra:
            sys.exit(f"labeller {name} CSV has item ids not in round 2 (wrong file?): {sorted(extra)[:5]}")
    adj = {}
    if os.path.exists(p["adj"]):
        for r in csv.DictReader(open(p["adj"], encoding="utf-8-sig")):
            v = (r.get("final_verdict") or "").strip()
            if v:
                if v not in VERDICTS:
                    sys.exit(f"adjudication_r2.csv: unknown verdict {v!r} for {r['item_id']} (use fixed, not_fixed or unclear)")
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
    with open(p["labels"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(p["todo"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "label_A", "note_A", "label_B", "note_B", "final_verdict"])
        w.writeheader()
        w.writerows(todo)
    print(f"labelled: A2 {sum(bool(r['label_A']) for r in rows)}, B2 {sum(bool(r['label_B']) for r in rows)} of {len(rows)}")
    print(f"agreed fixed/not_fixed: {sum(r['label_A'] == r['label_B'] and r['label_A'] in ('fixed', 'not_fixed') for r in rows)}; "
          f"need adjudication: {len(todo)} (adjudicated: {sum(bool(t['final_verdict']) for t in todo)}) -> step2r2/adjudication_todo_r2.csv")
    print(f"consensus available: {sum(bool(r['consensus']) for r in rows)} -> step2r2/human_labels_r2.csv")


def adj_card(t, s, resp):
    """One disputed item: the labelling card's content plus both labels and a shared decision."""
    iid = t["item_id"]
    lab = {"fixed": "Fixed", "not_fixed": "Not fixed", "unclear": "Unclear"}
    labels = "".join(f'<p><b>Labeller {n}:</b> {lab.get(t[f"label_{c}"], html.escape(t[f"label_{c}"]))}'
                     f' &middot; note: {html.escape(t[f"note_{c}"].strip()) or "<i>(none)</i>"}</p>' for n, c in (("A2", "A"), ("B2", "B")))
    return f"""
<section class="card" data-id="{iid}" id="{iid}">
  <h2>{iid} &middot; rule <code>{html.escape(s['violationnumberID'].strip())}</code></h2>
  <p class="desc">{html.escape(s['description'].strip())}</p>
  <p class="desc"><b>axe failure summary (original):</b> {html.escape(s['failureSummary'].strip() or '(none)')}</p>
  <div class="cols">
    <div><h3>Original fragment</h3><pre>{html.escape(s['affectedHTMLElement(s)'])}</pre></div>
    <div><h3>Proposed repair</h3><pre>{html.escape(resp)}</pre></div>
  </div>
  <div class="labels">{labels}</div>
  <div class="choice" role="radiogroup" aria-label="Final decision for {iid}">
    <b>Final decision:</b>
    <label><input type="radio" name="{iid}" value="fixed"> Fixed</label>
    <label><input type="radio" name="{iid}" value="not_fixed"> Not fixed</label>
    <label><input type="radio" name="{iid}" value="unclear"> Unclear</label>
    <textarea class="note" rows="2" placeholder="notes: why you decided this" aria-label="Notes for {iid}" data-note="{iid}"></textarea>
  </div>
</section>"""


def adj_page(cards, n):
    """Built from the round-1 page template so the look, storage and download code are the same."""
    doc = r1.page("A2", cards, n)
    start, end = doc.index('<header>'), doc.index('<script>')
    head, script = doc[:start], doc[end:]
    head = head.replace("<title>Repair Labeling A2</title>", "<title>Round 2 Adjudication</title>")
    head = head.replace(".ex {", ".addendum { background:var(--ex); border:2px solid var(--accent); border-radius:8px; padding:8px 16px; margin:12px 0; }\n"
                                 ".labels { background:var(--ex); border-radius:6px; padding:4px 12px; margin:8px 0; }\n"
                                 ".labels p { margin:4px 0; }\n.ex {")
    head = head.replace(".note {", "textarea.note { display:block; width:100%; box-sizing:border-box; font:inherit; }\n.note {")
    body = f"""<header><b>Round 2 adjudication</b> &middot; <span id="count">0</span> / {n} decided
 <button id="dl">Download CSV</button> <span id="todo"></span></header>
<section class="intro">
<h2>What to do</h2>
<p>These are the {n} items where labeller A2 and labeller B2 gave different labels. Decide each one <b>together</b>,
using the same rubric as before (below). Pick Fixed, Not fixed or Unclear and write a short note on why. Decisions are
saved in this browser as you go. When all {n} are decided, click <b>Download CSV</b> and put
<code>adjudication_r2.csv</code> in the <code>experiment\\step2r2</code> folder.</p>
{addendum_html()}
<details><summary><b>Rubric v1 (unchanged): "Fixed" only if all four hold</b></summary>{r1.RUBRIC_HTML}</details>
<details><summary><b>Worked examples (not part of the {n} items)</b></summary>{r1.example_html()}
{extra_examples_html(len(r1.EXAMPLES) + 1)}</details>
</section>
{''.join(cards)}
"""
    script = script.replace('const KEY = "repair-labels-v2-A2";', 'const KEY = "repair-adjudication-round2";')
    old_rows = ('const rows = ["item_id,labeller,human_verdict,note"].concat(\n'
                '    [...document.querySelectorAll(".card")].map(c => { const id=c.dataset.id, v=st[id]||{}; return [id, "A2", v.v||"", q(v.n)].join(","); }));')
    assert script.count(old_rows) == 1 and script.count('a.download = "human_labels_A2.csv"') == 1
    script = script.replace(old_rows, 'const rows = ["item_id,final_verdict,notes"].concat(\n'
                            '    [...document.querySelectorAll(".card")].map(c => { const id=c.dataset.id, v=st[id]||{}; return [id, v.v||"", q(v.n)].join(","); }));')
    script = script.replace('a.download = "human_labels_A2.csv"', 'a.download = "adjudication_r2.csv"')
    assert script.count('document.querySelectorAll("input.note")') == 1
    script = script.replace('document.querySelectorAll("input.note")', 'document.querySelectorAll("textarea.note")')
    script = script.replace('"next unlabelled: "', '"next undecided: "').replace('"all labelled"', '"all decided"')
    return head + body + script


def adjpage(exp):
    """step2r2/adjudication_r2.html from adjudication_todo_r2.csv: blind, like the labelling pages."""
    p = paths(exp)
    todo = list(csv.DictReader(open(p["todo"], encoding="utf-8")))
    if not todo:
        sys.exit("adjudication_todo_r2.csv is empty: nothing to adjudicate.")
    key = {k["item_id"]: k for k in csv.DictReader(open(p["key"], encoding="utf-8"))}
    data = r1.load_sample(os.path.join(exp, "artifact"))
    resp = final_responses(exp)
    cards = [adj_card(t, data[int(key[t["item_id"]]["row"])], resp[(key[t["item_id"]]["model"], int(key[t["item_id"]]["row"]))]) for t in todo]
    out = os.path.join(p["out"], "adjudication_r2.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(adj_page(cards, len(cards)))
    print(f"wrote step2r2/adjudication_r2.html ({len(cards)} items: {', '.join(t['item_id'] for t in todo)})")
    # same blinding checks as the labelling pages
    doc = open(out, encoding="utf-8").read()
    chrome, _ = chrome_and_data(doc)
    hits = {pat: len(re.findall(pat, doc, flags=re.I)) for pat in LEAKS}
    hits.update({pat: len(re.findall(pat, chrome, flags=re.I)) for pat in CHROME_ONLY})
    hits = {k: v for k, v in hits.items() if v}
    env = os.path.join(os.path.dirname(exp), ".env")
    env_vals = [l.partition("=")[2].strip().strip('"').strip("'") for l in open(env, encoding="utf-8") if "=" in l] if os.path.exists(env) else []
    checks = {"cards = todo items": re.findall(r'<section class="card" data-id="([^"]+)"', doc) == [t["item_id"] for t in todo],
              "repairs shown": doc.count("<h3>Proposed repair</h3>") == len(todo) + len(r1.EXAMPLES) + len(EXTRA_EXAMPLES),
              "addendum shown verbatim": all(html.escape(t) in doc for t in ADDENDUM),
              "v1 rubric unchanged": r1.RUBRIC_HTML in doc,
              "download name": 'a.download = "adjudication_r2.csv"' in doc,
              "csv header": '"item_id,final_verdict,notes"' in doc,
              "own storage key": '"repair-adjudication-round2"' in doc,
              "single inline script, no external resources": chrome.count("<script") == 1 and "<script>" in chrome,
              "no .env value": not any(v in doc for v in env_vals if len(v) >= 12),
              "no model/method/checker/judge/shrink/key text": not hits}
    for name, good in checks.items():
        print(f"  {'OK  ' if good else 'FAIL'} {name}")
    for pat, c in hits.items():
        print(f"      {pat!r} x{c}")
    print("ADJPAGE VERIFY", "PASSED" if all(checks.values()) else "FAILED")
    if not all(checks.values()):
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["sample", "pages", "verify", "merge", "adjpage"])
    ap.add_argument("exp")
    ap.add_argument("labels", nargs="*", help="merge: human_labels_A2.csv human_labels_B2.csv")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    exp = os.path.abspath(a.exp)
    if a.action == "sample":
        sample(exp, a.force)
    elif a.action == "pages":
        pages(exp)
    elif a.action == "verify":
        verify(exp)
    elif a.action == "adjpage":
        adjpage(exp)
    else:
        if len(a.labels) != 2:
            sys.exit("merge needs two CSVs: labeller A2 and labeller B2")
        merge(exp, *a.labels)
