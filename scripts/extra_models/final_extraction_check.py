"""Extraction check on the published AccessGuru-final (re-prompting) repairs of GPT-4, Mistral and Qwen. Free, no LLM.

The paper cut each repair out of the model's reply with a paid open-mistral-7b call (`filtered_response`). Here the
free deterministic extractor (`extract.py`, unchanged) is applied to the stored raw replies of the 'final' repairs,
and both versions are scored with the same checker and flags. Nothing published or earlier is changed: this script
only reads the workbooks, step1/ and step3/, and writes extra_models/final_extraction_check/.

Which raw reply belongs to 'final' (same rule as step1_checker_on_paper_outputs.py):
  re-prompted case (re-prompt_s5_orgPrompt not empty)  -> re-prompt workbook, column re-prompt_Decision_Confirmation
  otherwise                                             -> first-round workbook, Decision_Confirmation
                                                           (Mistral: MetaCognitive_Response), as in score.py
A re-prompted case whose raw reply cell is empty has no raw reply: it is reported, and scored as an empty repair.

Checker and flags are copied from score.py (itself copied from step1/step3): axe-core 4.4.1, 93 tags, set_content,
same aliases; placeholder / no-HTML / new violation / content shrink with unchanged thresholds. As a replication
check, the published final texts are re-scored here and compared with step1 and step3 cell by cell.

Usage (from the Data folder, .venv active):
    python -I experiment/extra_models/scripts/final_extraction_check.py experiment
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
OUT = os.path.join(EXP, "extra_models", "final_extraction_check")
RES = os.path.join(ART, "results/accessguru_dataset/syntax_layout")
EVAL_PY = os.path.join(ART, "code/Post-Processing_Evaluation/syntax_layout_evaluation.py")
AXE_JS = os.path.join(EXP, "vendor/axe-core-4.4.1.min.js")

FILES = {  # (first-round workbook, its raw turn-4 column, re-prompt workbook)
    "GPT4": ("GPT4/results_accessguru_ablation_our_dataset_gpt_4.xlsx", "Decision_Confirmation",
             "GPT4/GPT4rePrompt_results_accessguru_after_corrective_our_dataset_gpt_4_filtered.xlsx"),
    "Mistral": ("Mistral/results_accessguru_ablation_our_dataset_mistral.xlsx", "MetaCognitive_Response",
                "Mistral/rePrompt_results_accessguru_ablation_our_dataset_mistral_filtered.xlsx"),
    "Qwen": ("Qwen/results_accessguru_ablation_our_dataset_qwen.xlsx", "Decision_Confirmation",
             "Qwen/rePrompt_results_accessguru_corrective_our_dataset_qwen.xlsx"),
}
RAW_REPROMPT = "re-prompt_Decision_Confirmation"

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


def defence(h):
    """Whitespace and code fences (```html ... ```) removed: the published texts often keep the fences."""
    return squash(re.sub(r"```[\w-]*", "", h or ""))


sample_index = collections.defaultdict(list)
for i, s in enumerate(sample):
    sample_index[(s["id"], s["violationnumberID"].strip())].append(i)


def load(rel):
    rows = read_first_sheet(os.path.join(RES, rel))
    by_sample = {}
    for r in rows:
        key = (str(int(float(r["id"]))), r["violationnumberID"].strip())
        free = [i for i in sample_index.get(key, []) if i not in by_sample]
        same = [i for i in free if squash(sample[i]["affectedHTMLElement(s)"]) == squash(r["affectedHTMLElement(s)"])]
        by_sample[(same or free)[0]] = r
    return by_sample


SHRINK_LEN_RATIO, SHRINK_KEPT_RATIO = 0.5, 0.8


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(c - h, 3), round(c + h, 3)]


class _Elements(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []

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
    return float(len_ratio) < SHRINK_LEN_RATIO or (ratio is not None and ratio < SHRINK_KEPT_RATIO)


# ---- texts ----
items = []  # (model, row, reprompted, raw_available, published_text, deterministic_text)
for model, (first_rel, raw_col, rp_rel) in FILES.items():
    first, rp = load(first_rel), load(rp_rel)
    for i in detected:
        if rp[i]["re-prompt_s5_orgPrompt"].strip():
            raw = rp[i].get(RAW_REPROMPT) or ""
            items.append((model, i, True, bool(raw.strip()), rp[i]["filtered_response"] or "", extract(raw)))
        else:
            raw = first[i][raw_col] or ""
            items.append((model, i, False, bool(raw.strip()), first[i]["filtered_response"] or "", extract(raw)))


def score(page_factory, i, resp):
    s = sample[i]
    rec = {"empty_response": not resp.strip(), "flag_placeholder": bool(PLACEHOLDER.search(resp)),
           "flag_no_html_tag": not re.search(r"<[a-zA-Z!]", resp),
           "len_ratio": round(len(resp) / max(1, len(s["affectedHTMLElement(s)"])), 3)}
    if rec["empty_response"]:
        rec.update({"checker_pass": False, "introduced": "", "content_shrink": "", "error": ""})
        return rec
    page = page_factory()
    try:
        page.set_content(resp)
        page.add_script_tag(content=axe_src)
        res = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
        fired = {v["id"] for v in res["violations"]}
        rec.update({"checker_pass": not any(t in fired for t in aliases[i]),
                    "introduced": "|".join(sorted(fired - base_fired[i])), "error": ""})
    except Exception as e:  # noqa: BLE001
        rec.update({"checker_pass": "", "introduced": "", "error": str(e)[:200]})
    page.close()
    rec["content_shrink"] = shrink(s["affectedHTMLElement(s)"], resp, rec["len_ratio"])
    return rec


out = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for n, (model, i, reprompted, raw_ok, pub, det) in enumerate(items):
        s = sample[i]
        row = {"model": model, "row": i, "id": s["id"], "category": s["category"].strip(), "rule": s["violationnumberID"].strip(),
               "reprompted": reprompted, "raw_reply_available": raw_ok,
               "text_identical": pub == det, "text_identical_ignoring_whitespace": squash(pub) == squash(det),
               "text_identical_ignoring_fences_and_whitespace": defence(pub) == defence(det)}
        for tag, text in (("pub", pub), ("det", det)):
            for k, v in score(browser.new_page, i, text).items():
                row[f"{tag}_{k}"] = v
        out.append(row)
        if n % 100 == 0:
            print(f"{n}/{len(items)}", flush=True)
    browser.close()

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "final_extraction_rows.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

# ---- replication: published final texts re-scored here vs step1 / step3 ----
s1 = {(r["model"], int(r["row"])): r for r in csv.DictReader(open(os.path.join(EXP, "step1/checker_on_paper_outputs.csv"), encoding="utf-8"))
      if r["method"] == "accessguru_final"}
s3 = {(r["model"], int(r["row"])): r for r in csv.DictReader(open(os.path.join(EXP, "step3/main_joined.csv"), encoding="utf-8"))
      if r["method"] == "accessguru_final"}
mism = collections.Counter()
for r in out:
    k = (r["model"], r["row"])
    for f in ("checker_pass", "empty_response", "flag_placeholder", "flag_no_html_tag", "introduced"):
        mism[f] += str(r[f"pub_{f}"]) != s1[k][f]
    mism["content_shrink"] += str(r["pub_content_shrink"]) != s3[k]["content_shrink"]
    mism["paper_case_reprompted"] += (s1[k]["paper_case"] == "reprompted") != r["reprompted"]


def stats(rows, tag):
    n = len(rows)
    nonempty = [r for r in rows if not r[f"{tag}_empty_response"]]
    passed = [r for r in rows if r[f"{tag}_checker_pass"] is True]
    noh = lambda r: r[f"{tag}_flag_placeholder"] or r[f"{tag}_flag_no_html_tag"]  # noqa: E731
    newv = lambda r: bool(r[f"{tag}_introduced"])  # noqa: E731
    shr = lambda r: r[f"{tag}_content_shrink"] is True  # noqa: E731
    c = lambda rs, f: sum(bool(f(r)) for r in rs)  # noqa: E731
    return {"n": n, "checker_pass": len(passed), "empty": n - len(nonempty),
            "no_html_or_placeholder": c(nonempty, noh), "new_violation": c(nonempty, newv), "content_shrink": c(nonempty, shr),
            "among_passes": {"no_html_or_placeholder": c(passed, noh), "new_violation": c(passed, newv), "content_shrink": c(passed, shr)},
            "checker_pass_wilson": wilson(len(passed), n), "errors": c(rows, lambda r: r[f"{tag}_error"])}


summary = {"cases": len(detected), "replication_vs_step1_step3": {"rows": len(out), "mismatches": dict(mism)}, "models": {}}
for model in FILES:
    rows = [r for r in out if r["model"] == model]
    rp = [r for r in rows if r["reprompted"]]
    summary["models"][model] = {
        "reprompted_cases": len(rp), "reprompted_raw_missing": sum(not r["raw_reply_available"] for r in rp),
        "not_reprompted_raw_missing": sum(not r["raw_reply_available"] for r in rows if not r["reprompted"]),
        "texts_differ": sum(not r["text_identical"] for r in rows),
        "texts_differ_ignoring_whitespace": sum(not r["text_identical_ignoring_whitespace"] for r in rows),
        "texts_differ_ignoring_fences_and_whitespace": sum(not r["text_identical_ignoring_fences_and_whitespace"] for r in rows),
        "texts_differ_ignoring_fences_and_whitespace_reprompted": sum(not r["text_identical_ignoring_fences_and_whitespace"] for r in rp),
        "texts_differ_reprompted": sum(not r["text_identical"] for r in rp),
        "texts_differ_ignoring_whitespace_reprompted": sum(not r["text_identical_ignoring_whitespace"] for r in rp),
        "checker_pass_changed": sum(r["pub_checker_pass"] != r["det_checker_pass"] for r in rows),
        "pass_to_fail": sum(r["pub_checker_pass"] is True and r["det_checker_pass"] is not True for r in rows),
        "fail_to_pass": sum(r["pub_checker_pass"] is not True and r["det_checker_pass"] is True for r in rows),
        "published": stats(rows, "pub"), "deterministic": stats(rows, "det"),
        "reprompted_only": {"published": stats(rp, "pub"), "deterministic": stats(rp, "det")}}
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), indent=2)

L = ["# Extraction check on the published AccessGuru-final repairs", "",
     f"The {len(detected)} baseline-detected syntax/layout cases. 'Published' = the paper's own extraction (`filtered_response`, "
     "a paid open-mistral-7b call), exactly the texts scored in step1/step3. 'Deterministic' = `scripts/extract.py` applied to the raw "
     "reply that produced the final repair: the re-prompt reply (`re-prompt_Decision_Confirmation`) for re-prompted cases, else the "
     "first-round turn-4 reply. Same checker and flags. No earlier result is changed; this is a sensitivity check only.", "",
     "## Raw replies available", "",
     "| Model | Re-prompted cases (of 186) | Re-prompted, raw reply missing | Not re-prompted, raw reply missing |", "|---|---|---|---|"]
for m, d in summary["models"].items():
    L.append(f"| {m} | {d['reprompted_cases']} | {d['reprompted_raw_missing']} | {d['not_reprompted_raw_missing']} |")
L += ["", "## All 186 cases (counts out of 186)", "",
      "| Model | Extraction | Checker pass (95% Wilson CI) | Empty | No HTML or placeholder | New violation | Content shrink |", "|---|---|---|---|---|---|---|"]
for m, d in summary["models"].items():
    for ex in ("published", "deterministic"):
        st = d[ex]
        w = st["checker_pass_wilson"]
        L.append(f"| {m} | {ex} | {st['checker_pass']} ({w[0]*100:.1f}%, {w[1]*100:.1f}-{w[2]*100:.1f}) | {st['empty']} | "
                 f"{st['no_html_or_placeholder']} | {st['new_violation']} | {st['content_shrink']} |")
L += ["", "## Among checker passes", "", "| Model | Extraction | Checker passes | ...no HTML or placeholder | ...new violation | ...content shrink |",
      "|---|---|---|---|---|---|"]
for m, d in summary["models"].items():
    for ex in ("published", "deterministic"):
        st = d[ex]
        a = st["among_passes"]
        L.append(f"| {m} | {ex} | {st['checker_pass']} | {a['no_html_or_placeholder']} | {a['new_violation']} | {a['content_shrink']} |")
L += ["", "## Re-prompted cases only", "", "| Model | n | Extraction | Checker pass | No HTML or placeholder | New violation | Content shrink |",
      "|---|---|---|---|---|---|---|"]
for m, d in summary["models"].items():
    for ex in ("published", "deterministic"):
        st = d["reprompted_only"][ex]
        L.append(f"| {m} | {st['n']} | {ex} | {st['checker_pass']} | {st['no_html_or_placeholder']} | {st['new_violation']} | {st['content_shrink']} |")
L += ["", "## How many repair texts differ", "",
      "| Model | Differ (of 186) | Differ ignoring whitespace | Differ ignoring code fences and whitespace | Re-prompted cases: differ / differ ignoring fences and whitespace | Checker result changed | pass -> not pass | not pass -> pass |",
      "|---|---|---|---|---|---|---|---|"]
for m, d in summary["models"].items():
    L.append(f"| {m} | {d['texts_differ']} | {d['texts_differ_ignoring_whitespace']} | {d['texts_differ_ignoring_fences_and_whitespace']} | "
             f"{d['texts_differ_reprompted']} / "
             f"{d['texts_differ_ignoring_fences_and_whitespace_reprompted']} | {d['checker_pass_changed']} | {d['pass_to_fail']} | {d['fail_to_pass']} |")
L += ["", "## Replication check", "",
      f"Published final texts re-scored here vs step1 (`checker_on_paper_outputs.csv`) and step3 (`main_joined.csv`, content shrink): "
      f"{len(out)} rows, mismatches per field {dict(mism)}.", "",
      "## Notes", "",
      "- The paper's numbers (step1/step3, round 1 and round 2) are unchanged and remain the published-extraction results. "
      "The human samples were drawn from the published extraction; this check does not touch them.",
      "- 'Empty' with deterministic extraction can only come from an empty raw reply; such cases count as not passing."]
open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
