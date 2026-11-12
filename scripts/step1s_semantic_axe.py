"""Step 1s-axe: what does the checker say about the 55 semantic cases, before and after repair? Free.

Same checker as the paper (set_content, axe-core 4.4.1, the paper's 93-tag runOnly list). Semantic faults
have no axe rule, so the question is whether axe can tell a good semantic repair from a bad one at all:
it reports violations before and after each repair, and which violations the repair introduced.

Usage (from the Data folder, .venv active):
    python -I experiment/scripts/step1s_semantic_axe.py experiment/artifact experiment/step1 experiment/vendor/axe-core-4.4.1.min.js
"""
import collections
import csv
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

ART, STEP1, AXE_JS = (os.path.abspath(a) for a in sys.argv[1:4])
src = open(os.path.join(ART, "code/Post-Processing_Evaluation/syntax_layout_evaluation.py"), encoding="utf-8").read()
TAGS = re.findall(r"'([^']+)'", re.search(r"type: 'tag',\s*values: \[(.*?)\]", src, re.S).group(1))
axe_src = open(AXE_JS, encoding="utf-8").read()
cases = [json.loads(l) for l in open(os.path.join(STEP1, "semantic_items.jsonl"), encoding="utf-8")]


def run(browser, fragment):
    page = browser.new_page()
    try:
        page.set_content(fragment)
        page.add_script_tag(content=axe_src)
        res = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
        return sorted({v["id"] for v in res["violations"]}), ""
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]
    finally:
        page.close()


out = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for c in cases:
        before, err_b = run(browser, c["html"])
        for model, m in c["models"].items():
            after, err_a = run(browser, m["repair"]) if m["repair"].strip() else (None, "empty repair")
            out.append({
                "case": c["case"], "type": c["type"], "model": model,
                "axe_before": "|".join(before or []), "axe_after": "|".join(after or []),
                "n_before": len(before) if before is not None else "", "n_after": len(after) if after is not None else "",
                "introduced": "|".join(sorted(set(after or []) - set(before or []))),
                "removed": "|".join(sorted(set(before or []) - set(after or []))),
                "error": err_b or err_a,
            })
        print(c["case"], flush=True)
    browser.close()

with open(os.path.join(STEP1, "semantic_axe.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

summary = {}
for model in ("GPT4", "Pixtral", "Qwen"):
    sub = [r for r in out if r["model"] == model and not r["error"]]
    summary[model] = {
        "cases_checked": len(sub),
        "errors": sum(1 for r in out if r["model"] == model and r["error"]),
        "axe_clean_before": sum(r["n_before"] == 0 for r in sub),
        "axe_clean_after": sum(r["n_after"] == 0 for r in sub),
        "same_violation_set_before_after": sum(r["axe_before"] == r["axe_after"] for r in sub),
        "repair_introduced_violations": sum(bool(r["introduced"]) for r in sub),
        "introduced_rules": dict(collections.Counter(x for r in sub for x in r["introduced"].split("|") if x).most_common()),
    }
with open(os.path.join(STEP1, "semantic_axe_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
