"""Score AccessGuru first-round repairs from the new models and the published ones with the paper's checker.

Copied and adapted from experiment/scripts/step1_checker_on_paper_outputs.py (checker, flags) and
experiment/scripts/step3_analyze.py (content-shrink flag, Wilson CI). The originals are not edited.

Checker: axe-core 4.4.1, the 93-tag runOnly list parsed from the paper's syntax_layout_evaluation.py, fragment loaded
with set_content. checker_pass = response not empty and the target rule (or an accepted alias) no longer fires.
Flags: placeholder text, no HTML tag, new violation (a rule that did not fire on the original page), content shrink
(len_ratio < 0.5 or < 80% of the original's elements kept).

Rows scored (all on the same 186 cases, method accessguru_first):
  new models          extraction "deterministic" (scripts/extract.py on turn 4)
  GPT4/Mistral/Qwen   extraction "published"     (the workbooks' filtered_response, as in step1)
                      extraction "deterministic" (scripts/extract.py on the stored raw turn-4 reply)
The published/published rows are compared cell by cell with step1 and step3 as a replication check.

Usage (from the Data folder, .venv active):
    python -I experiment/extra_models/scripts/score.py experiment
"""
import collections
import csv
import html.parser
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
EXP = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.join(EXP, "scripts"))
from xlsx_read import read_first_sheet  # noqa: E402
from extract import extract  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

csv.field_size_limit(10**9)
ART = os.path.join(EXP, "artifact")
XM = os.path.join(EXP, "extra_models")
RES = os.path.join(ART, "results/accessguru_dataset/syntax_layout")
EVAL_PY = os.path.join(ART, "code/Post-Processing_Evaluation/syntax_layout_evaluation.py")
AXE_JS = os.path.join(EXP, "vendor/axe-core-4.4.1.min.js")

PUBLISHED = {  # first-round (ablation) workbooks, as in step1; raw turn-4 column per model
    "GPT4": ("GPT4/results_accessguru_ablation_our_dataset_gpt_4.xlsx", "Decision_Confirmation"),
    "Mistral": ("Mistral/results_accessguru_ablation_our_dataset_mistral.xlsx", "MetaCognitive_Response"),
    "Qwen": ("Qwen/results_accessguru_ablation_our_dataset_qwen.xlsx", "Decision_Confirmation"),
}
NEW_ORDER = ["MiniCPM-V-4.5", "Qwen3.5-4B", "InternVL3.5-2B", "SmolVLM2-2.2B", "Llama-3.2-3B"]

# ---- from step1 ----
PLACEHOLDER = re.compile(r"would go here|placeholder(?![\w-]*\s*=)|INCOMPLETE_RESPONSE|no html modifications", re.I)
src = open(EVAL_PY, encoding="utf-8").read()
TAGS = re.findall(r"'([^']+)'", re.search(r"type: 'tag',\s*values: \[(.*?)\]", src, re.S).group(1))
axe_src = open(AXE_JS, encoding="utf-8").read()
sample = [r for r in csv.DictReader(open(os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                         encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]
base = list(csv.DictReader(open(os.path.join(EXP, "step0/syntax_layout_baseline_axe.csv"), encoding="utf-8")))
detected = [int(b["row"]) for b in base if b["baseline_detected"] == "True"]
aliases = {int(b["row"]): b["accepted_axe_ids"].split("|") for b in base}
base_fired = {int(b["row"]): set(filter(None, b["all_violations"].split("|"))) for b in base}


def squash(h):
    return re.sub(r"\s+", "", h or "")


sample_index = collections.defaultdict(list)
for i, s in enumerate(sample):
    sample_index[(s["id"], s["violationnumberID"].strip())].append(i)


def load(rel):
    """Same row matching as step1: on (id, rule), repeated pairs told apart by the stored input fragment."""
    rows = read_first_sheet(os.path.join(RES, rel))
    by_sample = {}
    for r in rows:
        key = (str(int(float(r["id"]))), r["violationnumberID"].strip())
        free = [i for i in sample_index.get(key, []) if i not in by_sample]
        same = [i for i in free if squash(sample[i]["affectedHTMLElement(s)"]) == squash(r["affectedHTMLElement(s)"])]
        by_sample[(same or free)[0]] = r
    return by_sample


# ---- from step3 ----
SHRINK_LEN_RATIO = 0.5
SHRINK_KEPT_RATIO = 0.8


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(k / n, 3), round(c - h, 3), round(c + h, 3)]


class _Elements(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []  # (tag, id, class)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elements.append((tag, (a.get("id") or "").strip(), " ".join(sorted((a.get("class") or "").split()))))


def elements(text):
    p = _Elements()
    try:
        p.feed(text or "")
        p.close()
    except Exception:  # noqa: BLE001
        pass
    return p.elements


def shrink(original, response, len_ratio):
    orig, rep = elements(original), elements(response)
    pools = [collections.Counter(e[i] for e in rep if e[i]) for i in range(3)]
    kept = 0
    for e in orig:
        for i in range(3):
            if e[i] and pools[i][e[i]] > 0:
                pools[i][e[i]] -= 1
                kept += 1
                break
    n = len(orig)
    ratio = round(kept / n, 3) if n else None
    flag = float(len_ratio) < SHRINK_LEN_RATIO or (ratio is not None and ratio < SHRINK_KEPT_RATIO)
    return {"elements_orig": n, "elements_kept": kept, "elements_kept_ratio": ratio, "content_shrink": flag}


# ---- jobs: (model, source, extraction, row, response) ----
jobs = []
for model, (rel, raw_col) in PUBLISHED.items():
    wb = load(rel)
    for i in detected:
        jobs.append((model, "published", "published", i, wb[i]["filtered_response"] or ""))
        jobs.append((model, "published", "deterministic", i, extract(wb[i][raw_col])))
new_models = []
for slug in NEW_ORDER:
    path = os.path.join(XM, "repairs", f"{slug}.jsonl")
    if not os.path.exists(path):
        continue
    recs = {r["row"]: r for r in map(json.loads, filter(str.strip, open(path, encoding="utf-8")))}
    new_models.append(slug)
    for i in detected:
        if i in recs:
            jobs.append((slug, "new", "deterministic", i, extract(recs[i]["decision_confirmation"])))  # re-extract (PLAN deviation 3)

out = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for n, (model, source, extraction, i, resp) in enumerate(jobs):
        s = sample[i]
        rec = {"model": model, "source": source, "extraction": extraction, "method": "accessguru_first", "row": i, "id": s["id"],
               "category": s["category"].strip(), "rule": s["violationnumberID"].strip(),
               "empty_response": not resp.strip(),
               "flag_placeholder": bool(PLACEHOLDER.search(resp)),
               "flag_no_html_tag": not re.search(r"<[a-zA-Z!]", resp),
               "len_ratio": round(len(resp) / max(1, len(s["affectedHTMLElement(s)"])), 3)}
        if rec["empty_response"]:
            rec.update({"target_fires": "", "checker_pass": False, "introduced": "", "error": ""})
        else:
            page = browser.new_page()
            try:
                page.set_content(resp)
                page.add_script_tag(content=axe_src)
                res = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
                fired = {v["id"] for v in res["violations"]}
                fires = any(t in fired for t in aliases[i])
                rec.update({"target_fires": fires, "checker_pass": not fires,
                            "introduced": "|".join(sorted(fired - base_fired[i])), "error": ""})
            except Exception as e:  # noqa: BLE001
                rec.update({"target_fires": "", "checker_pass": "", "introduced": "", "error": str(e)[:200]})
            page.close()
        rec.update(shrink(s["affectedHTMLElement(s)"], resp, rec["len_ratio"]) if not rec["empty_response"]
                   else {"elements_orig": "", "elements_kept": "", "elements_kept_ratio": "", "content_shrink": ""})
        out.append(rec)
        if n % 200 == 0:
            print(f"{n}/{len(jobs)}", flush=True)
    browser.close()

with open(os.path.join(XM, "checker_results.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

# ---- replication check against the original step1 / step3 outputs ----
s1 = {(r["model"], int(r["row"])): r for r in csv.DictReader(open(os.path.join(EXP, "step1/checker_on_paper_outputs.csv"), encoding="utf-8"))
      if r["method"] == "accessguru_first"}
s3 = {(r["model"], int(r["row"])): r for r in csv.DictReader(open(os.path.join(EXP, "step3/main_joined.csv"), encoding="utf-8"))
      if r["method"] == "accessguru_first"}
mism = collections.Counter()
for r in out:
    if r["source"] == "published" and r["extraction"] == "published":
        k = (r["model"], r["row"])
        for f in ("checker_pass", "empty_response", "flag_placeholder", "flag_no_html_tag", "introduced"):
            mism[f] += str(r[f]) != s1[k][f]
        mism["content_shrink"] += str(r["content_shrink"]) != s3[k]["content_shrink"]
replication = {"compared_rows": sum(1 for r in out if r["extraction"] == "published"), "mismatches": dict(mism)}


def stats(sub):
    n = len(sub)
    passed = [r for r in sub if r["checker_pass"] is True]
    nonempty = [r for r in sub if not r["empty_response"]]
    c = lambda rows, f: sum(bool(f(r)) for r in rows)  # noqa: E731
    noh = lambda r: r["flag_placeholder"] or r["flag_no_html_tag"]  # noqa: E731
    return {
        "n": n,
        "checker_pass": wilson(len(passed), n), "checker_pass_count": len(passed),
        "empty": wilson(c(sub, lambda r: r["empty_response"]), n), "empty_count": c(sub, lambda r: r["empty_response"]),
        "no_html_or_placeholder": wilson(c(nonempty, noh), n), "no_html_or_placeholder_count": c(nonempty, noh),
        "new_violation": wilson(c(nonempty, lambda r: r["introduced"]), n), "new_violation_count": c(nonempty, lambda r: r["introduced"]),
        "content_shrink": wilson(c(nonempty, lambda r: r["content_shrink"] is True), n),
        "content_shrink_count": c(nonempty, lambda r: r["content_shrink"] is True),
        "among_checker_passes": {
            "no_html_or_placeholder": c(passed, noh), "new_violation": c(passed, lambda r: r["introduced"]),
            "content_shrink": c(passed, lambda r: r["content_shrink"] is True)},
        "errors": c(sub, lambda r: r["error"]),
    }


summary = {"method": "accessguru_first", "cases": len(detected), "primary_extraction": "deterministic",
           "replication_check_vs_step1_step3": replication, "models": {}}
for model in list(PUBLISHED) + new_models:
    for ex in (["published", "deterministic"] if model in PUBLISHED else ["deterministic"]):
        sub = [r for r in out if r["model"] == model and r["extraction"] == ex]
        summary["models"].setdefault(model, {})[ex] = stats(sub)

# generation metadata for new models
calls = [json.loads(l) for l in open(os.path.join(XM, "logs/calls.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(XM, "logs/calls.jsonl")) else []
for slug in new_models:
    cl = [c for c in calls if c["slug"] == slug]
    recs = [json.loads(l) for l in open(os.path.join(XM, "repairs", f"{slug}.jsonl"), encoding="utf-8") if l.strip()]
    summary["models"][slug]["generation"] = {
        "cases_generated": len(recs), "calls": len(cl), "hours": round(sum(c["seconds"] for c in cl) / 3600, 2),
        "output_tokens": sum(c["output_tokens"] for c in cl),
        "cases_output_truncated": sum(r["truncated_output_any_turn"] for r in recs),
        "cases_context_full": sum(r["context_full_any_turn"] for r in recs),
        "cases_with_call_error": sum(bool(r["error"]) for r in recs),
        "cases_retried": sum(r.get("retried", False) for r in recs)}

with open(os.path.join(XM, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)


def pct(v, k):
    return f"{k} ({v[0] * 100:.1f}%, {v[1] * 100:.1f}-{v[2] * 100:.1f})" if v else "-"


L = ["# Extra models: AccessGuru first-round repairs, checker results", "",
     f"Same {len(detected)} syntax/layout cases (axe 4.4.1 detects the target rule before repair), same first-round AccessGuru prompt, "
     "same checker (axe-core 4.4.1, 93 tags) and judge-free flags as the published GPT-4 / Mistral / Qwen results. "
     "No human labels. Each cell: count (percent, 95% Wilson CI). All percentages are out of all cases.", "",
     "**Primary comparison:** every model's repair cut out of its turn-4 reply with the same free deterministic extractor "
     "(`scripts/extract.py`). The published models' own extraction (a paid Mistral call in the paper) is shown for reference.", "",
     "| Model | Extraction | Checker pass | Empty | No HTML or placeholder | New violation | Content shrink |",
     "|---|---|---|---|---|---|---|"]
for model, by_ex in summary["models"].items():
    for ex, st in by_ex.items():
        if ex == "generation":
            continue
        L.append(f"| {model} | {ex} | {pct(st['checker_pass'], st['checker_pass_count'])} | {pct(st['empty'], st['empty_count'])} | "
                 f"{pct(st['no_html_or_placeholder'], st['no_html_or_placeholder_count'])} | {pct(st['new_violation'], st['new_violation_count'])} | "
                 f"{pct(st['content_shrink'], st['content_shrink_count'])} |")
L += ["", "## Among checker passes (the paper's convention)", "",
      "How many checker passes are still suspicious by a judge-free signal.", "",
      "| Model | Extraction | Checker passes | ...no HTML or placeholder | ...new violation | ...content shrink |", "|---|---|---|---|---|---|"]
for model, by_ex in summary["models"].items():
    for ex, st in by_ex.items():
        if ex == "generation":
            continue
        a = st["among_checker_passes"]
        L.append(f"| {model} | {ex} | {st['checker_pass_count']} | {a['no_html_or_placeholder']} | {a['new_violation']} | {a['content_shrink']} |")
if new_models:
    L += ["", "## Generation (local Ollama, $0)", "", "| Model | Cases | Calls | Hours | Output tokens | Cases truncated (output) | Cases context full | Call errors |",
          "|---|---|---|---|---|---|---|---|"]
    for slug in new_models:
        g = summary["models"][slug]["generation"]
        L.append(f"| {slug} | {g['cases_generated']} | {g['calls']} | {g['hours']} | {g['output_tokens']} | {g['cases_output_truncated']} | "
                 f"{g['cases_context_full']} | {g['cases_with_call_error']} |")
L += ["", "## Replication check", "",
      f"The published texts re-scored with these copied scripts versus the original step1/step3 outputs: "
      f"{replication['compared_rows']} rows, mismatches per field {replication['mismatches']}.", "",
      "## Caveats", "",
      "- First-round prompt only. The paper's re-prompting loop ('final') is not run for the new models, so compare with the published *first-round* numbers, not 'final'.",
      "- Checker pass is not 'truly fixed'; in round 2 humans found many checker passes not fixed. The flags are signals, not verdicts.",
      "- New models run locally at Q4_K_M quantization, text-only, temperature 0, fixed seed; the published models ran on vendor APIs at default settings."]
open(os.path.join(XM, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print(json.dumps({m: {e: (v.get("checker_pass") if isinstance(v, dict) else None) for e, v in d.items()} for m, d in summary["models"].items()}, indent=1))
print("replication:", replication)
