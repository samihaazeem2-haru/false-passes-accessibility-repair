"""Round 3: blind human labels on 60 checker-passing FIRST-ROUND repairs from the five new local models. Free.

Rubric v1 plus the v2 addendum and all 8 worked examples, exactly as in round 2: the page is built by
experiment/scripts/step2h_labeling_r2.py page() (imported, never edited), then only the round label, the browser
storage key and the file names are changed. Nothing from rounds 1 and 2 is read except that module's code.

sample:  12 per model (MiniCPM-V-4.5, Qwen3.5-4B, InternVL3.5-2B, SmolVLM2-2.2B, Llama-3.2-3B), simple random
         sample (seed 20261102) of the repairs that pass the checker with the deterministic extraction
         (extra_models/checker_results.csv, source=new). The repair text is extract.py on the stored turn-4 reply,
         the same text the checker scored. Truncated replies stay in; the hidden key flags them.
         Writes round3/sample_round3.csv (SHA-256 of each repair text) and round3/labeling_key_r3.csv (hidden key,
         ids R3-001..R3-060, with model and truncation flags). Never redraws unless --force.
pages:   requires extra_models/PLAN_round3.md to contain the SHA-256 of sample_round3.csv. Writes
         round3/labeling_A3.html and round3/labeling_B3.html: a different random order each (seeds 20261103,
         20261104), no model name, checker result, flag or judge output. Downloads human_labels_A3.csv / _B3.csv.
verify:  the round-2 checks plus the new model names and truncation words.
merge:   <human_labels_A3.csv> <human_labels_B3.csv> -> round3/human_labels_r3.csv, round3/adjudication_todo_r3.csv.
adjpage: round3/adjudication_r3.html from the todo file; downloads adjudication_r3.csv (item_id, final_verdict, notes).
         Put it in round3/ and run merge again.
analyze: round3/results_round3.json and round3/results_round3.md (as frozen in PLAN_round3.md).

Usage (from the Data folder):
    python -I experiment/extra_models/scripts/round3_labeling.py sample  experiment
    python -I experiment/extra_models/scripts/round3_labeling.py pages   experiment
    python -I experiment/extra_models/scripts/round3_labeling.py verify  experiment
    python -I experiment/extra_models/scripts/round3_labeling.py merge   experiment <human_labels_A3.csv> <human_labels_B3.csv>
    python -I experiment/extra_models/scripts/round3_labeling.py adjpage experiment
    python -I experiment/extra_models/scripts/round3_labeling.py analyze experiment
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract import extract  # noqa: E402

csv.field_size_limit(10**9)
MODELS = ["MiniCPM-V-4.5", "Qwen3.5-4B", "InternVL3.5-2B", "SmolVLM2-2.2B", "Llama-3.2-3B"]
SEED = 20261102
PER_MODEL = 12
N = PER_MODEL * len(MODELS)
LABELLERS = ["A3", "B3"]
PREFIX = "R3-"
BOOT_REPS = 4000
BOOT_SEED = 20261024  # same bootstrap seed as rounds 1 and 2


def r2mod(exp):
    sys.path.insert(0, os.path.join(exp, "scripts"))
    import step2h_labeling_r2 as r2  # noqa: E402  (rubric text, cards, page template; not edited)
    return r2


def paths(exp):
    xm = os.path.join(exp, "extra_models")
    out = os.path.join(xm, "round3")
    return {"xm": xm, "out": out, "plan": os.path.join(xm, "PLAN_round3.md"),
            "sample": os.path.join(out, "sample_round3.csv"), "key": os.path.join(out, "labeling_key_r3.csv"),
            "labels": os.path.join(out, "human_labels_r3.csv"), "todo": os.path.join(out, "adjudication_todo_r3.csv"),
            "adj": os.path.join(out, "adjudication_r3.csv")}


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def records(exp):
    out = {}
    for m in MODELS:
        for r in map(json.loads, filter(str.strip, open(os.path.join(exp, "extra_models/repairs", f"{m}.jsonl"), encoding="utf-8"))):
            out[(m, int(r["row"]))] = r
    return out


def repair_text(rec):
    return extract(rec["decision_confirmation"])  # exactly what score.py checked


def truncation(rec):
    t4 = [t for t in rec.get("turns", []) if t.get("turn") == 4]
    return {"truncated_any_turn": bool(rec["truncated_output_any_turn"]),
            "truncated_turn4": bool(t4 and t4[-1].get("done_reason") == "length"),
            "context_full_any_turn": bool(rec["context_full_any_turn"])}


def sample(exp, force):
    p = paths(exp)
    os.makedirs(p["out"], exist_ok=True)
    if os.path.exists(p["key"]) and not force:
        sys.exit(f"{p['key']} exists: the round-3 sample is fixed.")
    rows = list(csv.DictReader(open(os.path.join(p["xm"], "checker_results.csv"), encoding="utf-8")))
    recs = records(exp)
    rng = random.Random(SEED)
    picked = []
    for m in MODELS:
        pool = sorted((r for r in rows if r["model"] == m and r["source"] == "new" and r["extraction"] == "deterministic"
                       and r["checker_pass"] == "True"), key=lambda r: int(r["row"]))
        print(f"{m}: checker-passing first-round repairs (deterministic extraction) {len(pool)}")
        if len(pool) < PER_MODEL:
            sys.exit(f"STOP: {m} has only {len(pool)} eligible. Nothing written.")
        for r in rng.sample(pool, PER_MODEL):
            rec = recs[(m, int(r["row"]))]
            text = repair_text(rec)
            assert text.strip()
            picked.append({"model": m, "pool_size": len(pool), **{k: r[k] for k in ("row", "id", "category", "rule")},
                           **truncation(rec), "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    rng.shuffle(picked)
    picked = [{"item_id": f"{PREFIX}{i:03d}", **x} for i, x in enumerate(picked, 1)]
    with open(p["sample"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(picked[0].keys()))
        w.writeheader()
        w.writerows(picked)
    with open(p["key"], "w", encoding="utf-8", newline="") as fh:  # round-2 key columns + truncation flags
        cols = ["item_id", "model", "pool_size", "row", "id", "category", "rule", "truncated_any_turn", "truncated_turn4", "context_full_any_turn"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(picked)
    print(f"sample: {len(picked)} items, seed {SEED}; per model {dict(collections.Counter(x['model'] for x in picked))}")
    print(f"distinct cases: {len({x['row'] for x in picked})}; categories {dict(collections.Counter(x['category'] for x in picked))}")
    print(f"truncated (any turn): {sum(x['truncated_any_turn'] for x in picked)}; turn 4: {sum(x['truncated_turn4'] for x in picked)}; "
          f"context full: {sum(x['context_full_any_turn'] for x in picked)}")
    print(f"sample_round3.csv sha256 {sha256_file(p['sample'])}")
    print(f"labeling_key_r3.csv sha256 {sha256_file(p['key'])}")


def page(r2, labeller, cards):
    doc = r2.page(labeller, cards, N)  # round-2 page: addendum, v1 rubric unchanged, 8 worked examples
    for a, b in ((f'const KEY = "repair-labels-round2-{labeller}";', f'const KEY = "repair-labels-round3-{labeller}";'),
                 ("<title>Repair Labeling Round 2", "<title>Repair Labeling Round 3"),
                 ("<b>Repair labeling round 2 &middot;", "<b>Repair labeling round 3 &middot;")):
        assert doc.count(a) == 1, a
        doc = doc.replace(a, b)
    return doc


def load_items(exp):
    p = paths(exp)
    recs = records(exp)
    key = list(csv.DictReader(open(p["key"], encoding="utf-8")))
    texts = {k["item_id"]: repair_text(recs[(k["model"], int(k["row"]))]) for k in key}
    for x in csv.DictReader(open(p["sample"], encoding="utf-8")):  # the repair text must be the one the plan froze
        assert hashlib.sha256(texts[x["item_id"]].encode("utf-8")).hexdigest() == x["response_sha256"], x["item_id"]
    return key, texts


def pages(exp):
    p = paths(exp)
    r2 = r2mod(exp)
    if not os.path.exists(p["plan"]):
        sys.exit("extra_models/PLAN_round3.md missing: freeze the plan before building the pages.")
    h = sha256_file(p["sample"])
    if h not in open(p["plan"], encoding="utf-8").read():
        sys.exit(f"PLAN_round3.md does not contain the sample hash {h}.")
    data = r2.r1.load_sample(os.path.join(exp, "artifact"))
    key, texts = load_items(exp)
    for n, labeller in enumerate(LABELLERS):
        order = list(key)
        random.Random(SEED + 1 + n).shuffle(order)
        cards = [r2.r1.card(k["item_id"], data[int(k["row"])], texts[k["item_id"]]) for k in order]
        # newline="": no CRLF translation, so a CR-LF inside a repair is not doubled (browsers show the text exactly)
        with open(os.path.join(p["out"], f"labeling_{labeller}.html"), "w", encoding="utf-8", newline="") as fh:
            fh.write(page(r2, labeller, cards))
        print(f"wrote extra_models/round3/labeling_{labeller}.html ({len(cards)} items, first three {[k['item_id'] for k in order[:3]]})")


EXTRA_LEAKS = [r"minicpm", r"internvl", r"smolvlm", r"ollama", r"openbmb", r"bartowski", r"ggml", r"hf\.co"]
EXTRA_CHROME = [r"truncat", r"\bflag", r"pool_size", r"context_full", r"done_reason"]


def leak_hits(r2, doc):
    chrome, _ = r2.chrome_and_data(doc)
    hits = collections.Counter()
    for pat in r2.LEAKS + EXTRA_LEAKS:
        hits[pat] += len(re.findall(pat, doc, flags=re.I))
    for pat in [c.replace("R2-", "R3-") for c in r2.CHROME_ONLY] + EXTRA_CHROME:  # aria-label "Verdict for R3-..." allowed
        hits[pat] += len(re.findall(pat, chrome, flags=re.I))
    return +hits, chrome, doc


def env_values(exp):
    env = os.path.join(os.path.dirname(exp), ".env")
    if not os.path.exists(env):
        return []
    vals = [l.partition("=")[2].strip().strip('"').strip("'") for l in open(env, encoding="utf-8") if "=" in l]
    return [v for v in vals if len(v) >= 12]


def verify(exp):
    p = paths(exp)
    r2 = r2mod(exp)
    key, texts = load_items(exp)
    data = r2.r1.load_sample(os.path.join(exp, "artifact"))
    ids_key = {k["item_id"] for k in key}
    envv = env_values(exp)
    orders, ok = {}, True
    for labeller in LABELLERS:
        doc = open(os.path.join(p["out"], f"labeling_{labeller}.html"), encoding="utf-8", newline="").read()
        ids = re.findall(r'<section class="card" data-id="([^"]+)"', doc)
        orders[labeller] = ids
        hits, chrome, _ = leak_hits(r2, doc)
        others = [o for o in LABELLERS + ["A", "B", "A2", "B2"] if o != labeller]
        shown = re.findall(r"<h3>Proposed repair</h3><pre>(.*?)</pre>", doc, flags=re.S)
        n_ex = len(r2.r1.EXAMPLES) + len(r2.EXTRA_EXAMPLES)
        nl = lambda t: t.replace("\r\n", "\n").replace("\r", "\n")  # noqa: E731  browsers treat all line endings alike
        checks = {f"{N} cards": len(ids) == N, "ids = key": set(ids) == ids_key and len(set(ids)) == len(ids),
                  "repair text = sampled text (line endings normalised)": [nl(html.unescape(s)) for s in shown[n_ex:]] == [nl(texts[i]) for i in ids]
                  if len(shown) == N + n_ex else False,
                  "original = dataset fragment (line endings normalised)": all(nl(f"<pre>{html.escape(data[int(k['row'])]['affectedHTMLElement(s)'])}</pre>") in nl(doc) for k in key),
                  "addendum shown verbatim": all(html.escape(t) in doc for t in r2.ADDENDUM),
                  "v1 rubric unchanged": r2.r1.RUBRIC_HTML in doc,
                  "8 worked examples": doc.count('<div class="ex">') == n_ex == 8,
                  "same rubric block as round 2 page builder": r2.addendum_html() in doc and r2.extra_examples_html(len(r2.r1.EXAMPLES) + 1) in doc,
                  "download name": f'a.download = "human_labels_{labeller}.csv"' in doc,
                  "own storage key": f'"repair-labels-round3-{labeller}"' in doc and "round2" not in chrome,
                  "no other labeller in page code": not any(re.search(rf"labell?er {o}\b|human_labels_{o}\.csv|-{o}\"|\"{o}\"", chrome) for o in others),
                  "single inline script, no external resources": chrome.count("<script") == 1 and "<script>" in chrome,
                  "no .env value": not any(v in doc for v in envv),
                  "no model/checker/judge/flag/truncation/key text": not hits}
        for name, good in checks.items():
            print(f"  {labeller}: {'OK  ' if good else 'FAIL'} {name}")
            ok &= bool(good)
        for pat, c in hits.items():
            print(f"      {pat!r} x{c}")
    diff = sum(a != b for a, b in zip(orders["A3"], orders["B3"]))
    print(f"  orders differ at {diff}/{N} positions")
    ok &= diff > N * 0.8
    print("VERIFY", "PASSED" if ok else "FAILED")
    if not ok:
        sys.exit(1)


def merge(exp, path_a, path_b):
    """Same logic as round 2: agreed fixed/not_fixed -> consensus; otherwise the round-3 adjudicated label."""
    p = paths(exp)
    r2 = r2mod(exp)
    key = list(csv.DictReader(open(p["key"], encoding="utf-8")))
    ids = {k["item_id"] for k in key}
    la, lb = r2.r1.read_labels(path_a), r2.r1.read_labels(path_b)
    for name, lab in (("A3", la), ("B3", lb)):
        extra = set(lab) - ids
        if extra:
            sys.exit(f"labeller {name} CSV has item ids not in round 3 (wrong file?): {sorted(extra)[:5]}")
    adj = {}
    if os.path.exists(p["adj"]):
        for r in csv.DictReader(open(p["adj"], encoding="utf-8-sig")):
            v = (r.get("final_verdict") or "").strip()
            if v:
                if v not in r2.VERDICTS:
                    sys.exit(f"adjudication_r3.csv: unknown verdict {v!r} for {r['item_id']}")
                adj[r["item_id"]] = v
    rows, todo = [], []
    for k in key:
        a, b = la.get(k["item_id"], {}), lb.get(k["item_id"], {})
        va, vb = a.get("verdict", ""), b.get("verdict", "")
        agreed = va == vb and va in ("fixed", "not_fixed")
        if va and vb and not agreed:
            todo.append({"item_id": k["item_id"], "label_A": va, "note_A": a.get("note", ""),
                         "label_B": vb, "note_B": b.get("note", ""), "final_verdict": adj.get(k["item_id"], "")})
        rows.append({**{f: k[f] for f in ("item_id", "model", "row", "id", "category", "rule", "truncated_any_turn", "truncated_turn4")},
                     "label_A": va, "label_B": vb, "note_A": a.get("note", ""), "note_B": b.get("note", ""),
                     "adjudicated": adj.get(k["item_id"], ""), "consensus": va if agreed else adj.get(k["item_id"], "")})
    with open(p["labels"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(p["todo"], "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "label_A", "note_A", "label_B", "note_B", "final_verdict"])
        w.writeheader()
        w.writerows(todo)
    print(f"labelled: A3 {sum(bool(r['label_A']) for r in rows)}, B3 {sum(bool(r['label_B']) for r in rows)} of {len(rows)}")
    print(f"agreed: {len(rows) - len(todo) - sum(not (r['label_A'] and r['label_B']) for r in rows)}; need adjudication: {len(todo)} "
          f"(adjudicated: {sum(bool(t['final_verdict']) for t in todo)}) -> extra_models/round3/adjudication_todo_r3.csv")
    print(f"consensus available: {sum(bool(r['consensus']) for r in rows)} -> extra_models/round3/human_labels_r3.csv")


def adjpage(exp):
    p = paths(exp)
    r2 = r2mod(exp)
    todo = list(csv.DictReader(open(p["todo"], encoding="utf-8")))
    if not todo:
        sys.exit("adjudication_todo_r3.csv is empty: nothing to adjudicate.")
    key = {k["item_id"]: k for k in csv.DictReader(open(p["key"], encoding="utf-8"))}
    _, texts = load_items(exp)
    data = r2.r1.load_sample(os.path.join(exp, "artifact"))
    cards = []
    for t in todo:  # round-2 adjudication card, labeller codes A3/B3
        c = r2.adj_card(t, data[int(key[t["item_id"]]["row"])], texts[t["item_id"]])
        c = c.replace("<b>Labeller A2:</b>", "<b>Labeller A3:</b>").replace("<b>Labeller B2:</b>", "<b>Labeller B3:</b>")
        cards.append(c)
    doc = r2.adj_page(cards, len(cards))
    for a, b in (("<title>Round 2 Adjudication</title>", "<title>Round 3 Adjudication</title>"),
                 ("<b>Round 2 adjudication</b>", "<b>Round 3 adjudication</b>"),
                 ("labeller A2 and labeller B2", "labeller A3 and labeller B3"),
                 ("<code>adjudication_r2.csv</code> in the <code>experiment\\step2r2</code> folder",
                  "<code>adjudication_r3.csv</code> in the <code>experiment\\extra_models\\round3</code> folder"),
                 ('const KEY = "repair-adjudication-round2";', 'const KEY = "repair-adjudication-round3";'),
                 ('a.download = "adjudication_r2.csv"', 'a.download = "adjudication_r3.csv"')):
        assert doc.count(a) == 1, a
        doc = doc.replace(a, b)
    out = os.path.join(p["out"], "adjudication_r3.html")
    open(out, "w", encoding="utf-8", newline="").write(doc)
    hits, chrome, _ = leak_hits(r2, doc)
    checks = {"cards = todo items": re.findall(r'<section class="card" data-id="([^"]+)"', doc) == [t["item_id"] for t in todo],
              "addendum shown verbatim": all(html.escape(t) in doc for t in r2.ADDENDUM),
              "v1 rubric unchanged": r2.r1.RUBRIC_HTML in doc,
              "download name": 'a.download = "adjudication_r3.csv"' in doc,
              "own storage key": '"repair-adjudication-round3"' in doc and "round2" not in chrome,
              "no round-2 labeller codes": not re.search(r"\b[AB]2\b", chrome),
              "single inline script": chrome.count("<script") == 1,
              "no .env value": not any(v in doc for v in env_values(exp)),
              "no model/checker/judge/flag/truncation/key text": not hits}
    for name, good in checks.items():
        print(f"  {'OK  ' if good else 'FAIL'} {name}")
    for pat, c in hits.items():
        print(f"      {pat!r} x{c}")
    print(f"wrote extra_models/round3/adjudication_r3.html ({len(cards)} items)")
    print("ADJPAGE VERIFY", "PASSED" if all(checks.values()) else "FAILED")
    if not all(checks.values()):
        sys.exit(1)


# ---------------------------------------------------------------- analysis (frozen in PLAN_round3.md)
def kappa(pairs):  # copied from step3_analyze.py
    n = len(pairs)
    if not n:
        return None
    labels = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def boot_ci(values):  # copied from step3_analyze.py
    v = sorted(x for x in values if x is not None)
    if len(v) < 20:
        return None
    return [round(v[int(0.025 * len(v))], 3), round(v[int(0.975 * len(v)) - 1], 3)]


def fpr(items, unclear_nf=False):
    bad = ("not_fixed", "unclear") if unclear_nf else ("not_fixed",)
    d = [r for r in items if r["consensus"] in ("fixed", "not_fixed") or (unclear_nf and r["consensus"] == "unclear")]
    return (sum(r["consensus"] in bad for r in d) / len(d) if d else None), len(d), sum(r["consensus"] in bad for r in d)


def pooled_boot(items, unclear_nf=False):
    est, n, k = fpr(items, unclear_nf)
    clusters = collections.defaultdict(list)
    for r in items:
        clusters[r["row"]].append(r)
    cl = list(clusters.values())
    rng = random.Random(BOOT_SEED)
    reps = [fpr([r for _ in cl for r in rng.choice(cl)], unclear_nf)[0] for _ in range(BOOT_REPS)]
    return {"not_fixed": k, "decided": n, "estimate": None if est is None else round(est, 3),
            "ci95_cluster_bootstrap": boot_ci(reps), "cases": len(cl)}


def analyze(exp):
    p = paths(exp)
    plan = open(p["plan"], encoding="utf-8").read()
    h = sha256_file(p["sample"])
    if h not in plan:
        sys.exit(f"PLAN_round3.md does not contain the sample hash {h}.")
    rows = list(csv.DictReader(open(p["labels"], encoding="utf-8")))
    missing = [r["item_id"] for r in rows if not r["consensus"]]
    both = [r for r in rows if r["label_A"] and r["label_B"]]
    binary = [(r["label_A"], r["label_B"]) for r in both if r["label_A"] in ("fixed", "not_fixed") and r["label_B"] in ("fixed", "not_fixed")]
    conf = collections.Counter((r["label_A"], r["label_B"]) for r in both)
    res = {"sample_sha256": h, "items": len(rows), "no_consensus_yet": missing,
           "kappa_before_adjudication": {"binary": kappa(binary), "binary_n": len(binary),
                                          "binary_agreement": round(sum(a == b for a, b in binary) / len(binary), 3) if binary else None,
                                          "three_label": kappa([(r["label_A"], r["label_B"]) for r in both]), "three_label_n": len(both),
                                          "confusion_A_rows_B_cols": {f"{a}|{b}": c for (a, b), c in sorted(conf.items())}},
           "labeller_counts": {L: dict(collections.Counter(r[f"label_{c}"] for r in rows if r[f"label_{c}"])) for L, c in (("A3", "A"), ("B3", "B"))},
           "primary_pooled_false_pass": pooled_boot(rows),
           "sensitivity_unclear_as_not_fixed": pooled_boot(rows, unclear_nf=True),
           "truncated_excluded": {"any_turn": pooled_boot([r for r in rows if r["truncated_any_turn"] != "True"]),
                                  "turn4_only": pooled_boot([r for r in rows if r["truncated_turn4"] != "True"])},
           "truncated_items": {"any_turn": sum(r["truncated_any_turn"] == "True" for r in rows),
                               "turn4": sum(r["truncated_turn4"] == "True" for r in rows),
                               "not_fixed_among_truncated_any_turn": fpr([r for r in rows if r["truncated_any_turn"] == "True"])[2]},
           "per_model_counts_descriptive": {m: {"items": sum(r["model"] == m for r in rows),
                                                **{v: sum(r["model"] == m and r["consensus"] == v for r in rows) for v in ("fixed", "not_fixed", "unclear")},
                                                "no_consensus": sum(r["model"] == m and not r["consensus"] for r in rows),
                                                "truncated_any_turn": sum(r["model"] == m and r["truncated_any_turn"] == "True" for r in rows)}
                                            for m in MODELS},
           "bootstrap": f"cluster bootstrap over cases (dataset rows), {BOOT_REPS} reps, seed {BOOT_SEED}"}
    json.dump(res, open(os.path.join(p["out"], "results_round3.json"), "w", encoding="utf-8"), indent=2)

    def ci(d):
        c = d["ci95_cluster_bootstrap"]
        return (f"{d['not_fixed']}/{d['decided']} = {d['estimate']*100:.1f}% (95% CI {c[0]*100:.1f} to {c[1]*100:.1f}; {d['cases']} cases)"
                if d["estimate"] is not None and c else f"{d['not_fixed']}/{d['decided']}")
    k = res["kappa_before_adjudication"]
    L = ["# Round 3 results: five local models, first-round repairs", "",
         f"Sample SHA-256 `{h}` (matches PLAN_round3.md). {len(rows)} items; consensus missing for {len(missing)}"
         + (f": {', '.join(missing)}" if missing else "") + ".", "",
         "## Reliability (before adjudication)", "",
         f"- Binary kappa A3-B3: **{k['binary']}** (n = {k['binary_n']}, agreement {k['binary_agreement']}).",
         f"- 3-label kappa: {k['three_label']} (n = {k['three_label_n']}).",
         f"- Confusion (A3 | B3: count): {k['confusion_A_rows_B_cols']}.",
         f"- Labeller counts: {res['labeller_counts']}."]
    if k["binary"] is not None and k["binary"] < 0.6:
        L.append("- **Binary kappa is below 0.6: the consensus false-pass rate is reported with that caveat (plan section 5).**")
    L += ["", "## Primary: pooled false-pass rate", "", f"- {ci(res['primary_pooled_false_pass'])}", "",
          "## Truncated replies excluded", "",
          f"- Truncated in any turn excluded ({res['truncated_items']['any_turn']} items): {ci(res['truncated_excluded']['any_turn'])}",
          f"- Turn-4 reply truncated excluded ({res['truncated_items']['turn4']} items): {ci(res['truncated_excluded']['turn4_only'])}", "",
          "## Sensitivity: consensus unclear counted as not fixed", "", f"- {ci(res['sensitivity_unclear_as_not_fixed'])}", "",
          "## Per model (counts only, descriptive; 12 items per model is too few for per-model rates)", "",
          "| Model | Items | Consensus fixed | Not fixed | Unclear | No consensus | Truncated (any turn) |", "|---|---|---|---|---|---|---|"]
    for m, d in res["per_model_counts_descriptive"].items():
        L.append(f"| {m} | {d['items']} | {d['fixed']} | {d['not_fixed']} | {d['unclear']} | {d['no_consensus']} | {d['truncated_any_turn']} |")
    L += ["", f"Bootstrap: {res['bootstrap']}."]
    open(os.path.join(p["out"], "results_round3.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["sample", "pages", "verify", "merge", "adjpage", "analyze"])
    ap.add_argument("exp")
    ap.add_argument("labels", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    exp = os.path.abspath(a.exp)
    if a.action == "merge":
        if len(a.labels) != 2:
            sys.exit("merge needs two CSVs: labeller A3 and labeller B3")
        merge(exp, *a.labels)
    else:
        {"sample": lambda: sample(exp, a.force), "pages": lambda: pages(exp), "verify": lambda: verify(exp),
         "adjpage": lambda: adjpage(exp), "analyze": lambda: analyze(exp)}[a.action]()
