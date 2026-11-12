"""Step 1: run the paper's checker on the repairs the paper already published. No LLM or paid API is called.

For the 186 baseline-detected syntax/layout cases, each repaired fragment (`filtered_response`, used
as stored, exactly as syntax_layout_evaluation.py does) is loaded with set_content and checked with
axe-core 4.4.1 and the paper's 93-tag runOnly list. "checker_pass" means the target rule (or its alias)
no longer fires and the response is not empty.

Methods per model (GPT4, Mistral, Qwen):
  baseline_one / baseline_two / baseline_three   the paper's baseline prompts
  accessguru_first                               AccessGuru without corrective re-prompting (ablation file)
  accessguru_final                               re-prompted answer where re-prompting ran, else first-round answer

Each row also gets heuristic flags (not a verdict on "truly fixed"): placeholder text, no HTML tag,
and the response length relative to the original fragment.

Usage (from the Data folder, with the .venv active):
    python -I experiment/scripts/step1_checker_on_paper_outputs.py experiment/artifact experiment/step0 experiment/step1 experiment/vendor/axe-core-4.4.1.min.js
"""
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_read import read_first_sheet  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

csv.field_size_limit(10**9)

ART, STEP0, OUT, AXE_JS = (os.path.abspath(a) for a in sys.argv[1:5])
os.makedirs(OUT, exist_ok=True)
RES = os.path.join(ART, "results/accessguru_dataset/syntax_layout")
EVAL_PY = os.path.join(ART, "code/Post-Processing_Evaluation/syntax_layout_evaluation.py")

FILES = {
    "GPT4": {
        "baseline_one": "GPT4/results_baseline_one_our_dataset_gpt_4.xlsx",
        "baseline_two": "GPT4/results_baseline_two_our_dataset_gpt_4.xlsx",
        "baseline_three": "GPT4/results_baseline_three_our_dataset_gpt_4.xlsx",
        "first": "GPT4/results_accessguru_ablation_our_dataset_gpt_4.xlsx",
        "reprompt": "GPT4/GPT4rePrompt_results_accessguru_after_corrective_our_dataset_gpt_4_filtered.xlsx",
    },
    "Mistral": {
        "baseline_one": "Mistral/results_baseline_one_our_dataset_mistral.xlsx",
        "baseline_two": "Mistral/results_baseline_two_our_dataset_mistral.xlsx",
        "baseline_three": "Mistral/results_baseline_three_our_dataset_mistral.xlsx",
        "first": "Mistral/results_accessguru_ablation_our_dataset_mistral.xlsx",
        "reprompt": "Mistral/rePrompt_results_accessguru_ablation_our_dataset_mistral_filtered.xlsx",
    },
    "Qwen": {
        "baseline_one": "Qwen/results_baseline_one_our_dataset_qwen.xlsx",
        "baseline_two": "Qwen/results_baseline_two_our_dataset_qwen.xlsx",
        "baseline_three": "Qwen/results_baseline_three_our_dataset_qwen.xlsx",
        "first": "Qwen/results_accessguru_ablation_our_dataset_qwen.xlsx",
        "reprompt": "Qwen/rePrompt_results_accessguru_corrective_our_dataset_qwen.xlsx",
    },
}
PLACEHOLDER = re.compile(r"would go here|placeholder(?![\w-]*\s*=)|INCOMPLETE_RESPONSE|no html modifications", re.I)  # not the placeholder= attribute

src = open(EVAL_PY, encoding="utf-8").read()
TAGS = re.findall(r"'([^']+)'", re.search(r"type: 'tag',\s*values: \[(.*?)\]", src, re.S).group(1))
axe_src = open(AXE_JS, encoding="utf-8").read()

sample = [r for r in csv.DictReader(open(os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                         encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]
base = list(csv.DictReader(open(os.path.join(STEP0, "syntax_layout_baseline_axe.csv"), encoding="utf-8")))
detected = [int(b["row"]) for b in base if b["baseline_detected"] == "True"]


def squash(h):
    return re.sub(r"\s+", "", h or "")


sample_index = collections.defaultdict(list)
for i, s in enumerate(sample):
    sample_index[(s["id"], s["violationnumberID"].strip())].append(i)


def load(rel):
    """Return workbook rows indexed by sample row. Rows are matched on (id, rule), not position:
    some workbooks are shifted or reordered. Ids are stored as floats (e.g. 2.30914312E8).
    Repeated (id, rule) pairs are told apart by the stored input fragment."""
    rows = read_first_sheet(os.path.join(RES, rel))
    by_sample = {}
    for r in rows:
        key = (str(int(float(r["id"]))), r["violationnumberID"].strip())
        free = [i for i in sample_index.get(key, []) if i not in by_sample]
        if not free:
            raise SystemExit(f"unmatched row {key} in {rel}")
        same = [i for i in free if squash(sample[i]["affectedHTMLElement(s)"]) == squash(r["affectedHTMLElement(s)"])]
        i = (same or free)[0]
        r["_input_differs"] = not same
        by_sample[i] = r
    if len(by_sample) != len(sample):
        raise SystemExit(f"{len(by_sample)} of {len(sample)} sample rows matched in {rel}")
    return by_sample


# (model, method, row, response, paper_case, input_differs)
jobs = []
for model, files in FILES.items():
    wb = {k: load(v) for k, v in files.items()}
    for i in detected:
        for m in ("baseline_one", "baseline_two", "baseline_three"):
            r = wb[m][i]
            jobs.append((model, m, i, r["filtered_response"], r.get("Case", ""), r["_input_differs"]))
        first = wb["first"][i]
        rp = wb["reprompt"][i]
        jobs.append((model, "accessguru_first", i, first["filtered_response"], first.get("Case", ""), first["_input_differs"]))
        if rp["re-prompt_s5_orgPrompt"].strip():
            jobs.append((model, "accessguru_final", i, rp["filtered_response"], "reprompted", rp["_input_differs"]))
        else:
            jobs.append((model, "accessguru_final", i, first["filtered_response"], "not_reprompted", first["_input_differs"]))

# Repair texts for the Step 2 judge, keyed the same way as the checker CSV.
with open(os.path.join(OUT, "responses.jsonl"), "w", encoding="utf-8") as fh:
    for model, method, i, resp, _, _ in jobs:
        fh.write(json.dumps({"model": model, "method": method, "row": i, "response": resp or ""}, ensure_ascii=False) + "\n")

aliases = {int(b["row"]): b["accepted_axe_ids"].split("|") for b in base}
base_fired = {int(b["row"]): set(filter(None, b["all_violations"].split("|"))) for b in base}

out = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for n, (model, method, i, resp, paper_case, input_differs) in enumerate(jobs):
        s = sample[i]
        resp = resp or ""
        rec = {"model": model, "method": method, "row": i, "id": s["id"], "category": s["category"].strip(),
               "rule": s["violationnumberID"].strip(), "paper_case": paper_case[:80], "input_differs": input_differs,
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
        out.append(rec)
        if n % 100 == 0:
            print(f"{n}/{len(jobs)}", flush=True)
    browser.close()

with open(os.path.join(OUT, "checker_on_paper_outputs.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

summary = collections.defaultdict(dict)
for model in FILES:
    for method in ("baseline_one", "baseline_two", "baseline_three", "accessguru_first", "accessguru_final"):
        sub = [r for r in out if r["model"] == model and r["method"] == method]
        passed = [r for r in sub if r["checker_pass"] is True]
        summary[model][method] = {
            "n": len(sub),
            "checker_pass": len(passed),
            "checker_pass_and_new_violation": sum(bool(r["introduced"]) for r in passed),
            "checker_pass_but_placeholder_or_no_html": sum(r["flag_placeholder"] or r["flag_no_html_tag"] for r in passed),
            "empty_response": sum(r["empty_response"] for r in sub),
            "input_differs": sum(r["input_differs"] for r in sub),
            "errors": sum(bool(r["error"]) for r in sub),
        }
with open(os.path.join(OUT, "checker_on_paper_outputs_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
