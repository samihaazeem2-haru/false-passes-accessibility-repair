"""Step 0b: does axe flag the target rule on each sampled syntax/layout fragment before repair?

Mirrors AccessGuru's checker (code/Post-Processing_Evaluation/syntax_layout_evaluation.py):
page.set_content(fragment), inject axe-core 4.4.1, axe.run with the same runOnly tag list,
which is read from that file rather than retyped. The rule alias mapping is copied from the same file.
No LLM or paid API is called.

Usage (from the Data folder):
    python -I experiment/scripts/step0b_baseline_axe.py experiment/artifact experiment/step0 experiment/vendor/axe-core-4.4.1.min.js
"""
import csv
import hashlib
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

csv.field_size_limit(10**9)

ART, OUT, AXE_JS = (os.path.abspath(a) for a in sys.argv[1:4])
EVAL_PY = os.path.join(ART, "code/Post-Processing_Evaluation/syntax_layout_evaluation.py")
SL_CSV = os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv")

# Same mapping as syntax_layout_evaluation.py; aria-prohibited-attr accepts either listed rule.
EVAL_ALIASES = {
    "area-alt": ["img-alt"],
    "aria-roles": ["aria-deprecated-role"],
    "aria-prohibited-attr": ["aria-valid-attr-value", "aria-allowed-attr"],
    "aria-hidden-body": ["aria-hidden-focus"],
}

src = open(EVAL_PY, encoding="utf-8").read()
tags_block = re.search(r"type: 'tag',\s*values: \[(.*?)\]", src, re.S).group(1)
TAGS = re.findall(r"'([^']+)'", tags_block)

axe_src = open(AXE_JS, encoding="utf-8").read()
axe_sha = hashlib.sha256(axe_src.encode("utf-8")).hexdigest()

rows = [r for r in csv.DictReader(open(SL_CSV, encoding="utf-8-sig", newline=""))
        if r["category"].strip() in ("Syntax", "Layout")]

out_rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for i, r in enumerate(rows):
        rule = r["violationnumberID"].strip()
        targets = [rule] + EVAL_ALIASES.get(rule, [])
        page = browser.new_page()
        rec = {"row": i, "id": r["id"], "category": r["category"].strip(), "rule": rule,
               "accepted_axe_ids": "|".join(targets)}
        try:
            page.set_content(r["affectedHTMLElement(s)"])
            page.add_script_tag(content=axe_src)
            res = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
            fired = sorted({v["id"] for v in res["violations"]})
            rec.update({
                "axe_version": res.get("testEngine", {}).get("version", ""),
                "baseline_detected": any(t in fired for t in targets),
                "target_incomplete": any(t == v["id"] for v in res["incomplete"] for t in targets),
                "all_violations": "|".join(fired),
                "error": "",
            })
        except Exception as e:  # noqa: BLE001
            rec.update({"axe_version": "", "baseline_detected": "", "target_incomplete": "",
                        "all_violations": "", "error": str(e)[:300]})
        page.close()
        out_rows.append(rec)
        print(i, rule, rec["baseline_detected"], flush=True)
    version = browser.version
    browser.close()

with open(os.path.join(OUT, "syntax_layout_baseline_axe.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)

summary = {"axe_js_sha256": axe_sha, "chromium_version": version, "n_tags": len(TAGS), "rows": len(out_rows)}
for cat in ("Syntax", "Layout"):
    sub = [r for r in out_rows if r["category"] == cat]
    summary[cat] = {
        "n": len(sub),
        "baseline_detected": sum(r["baseline_detected"] is True for r in sub),
        "not_detected": sum(r["baseline_detected"] is False for r in sub),
        "errors": sum(bool(r["error"]) for r in sub),
        "not_detected_but_incomplete": sum(r["baseline_detected"] is False and r["target_incomplete"] for r in sub),
    }
with open(os.path.join(OUT, "syntax_layout_baseline_axe_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
