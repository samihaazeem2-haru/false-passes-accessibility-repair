"""Step 0c: label every baseline-undetected syntax/layout case with a reason.

Usage (from the Data folder):
    python -I experiment/scripts/step0c_undetected_reasons.py experiment/step0 experiment/vendor/axe-core-4.4.1.min.js

Reasons, checked in this order:
  checker_error      axe.run threw (no result for the case)
  rule_absent_in_axe the target rule ID (and any alias) does not occur as id:"<rule>" in the axe 4.4.1 bundle
  axe_incomplete     axe returned the target rule as "incomplete" (needs review), not as a violation
  not_fired          the rule exists and axe ran, but it did not flag the fragment
"""
import collections
import csv
import json
import os
import sys

OUT, AXE_JS = (os.path.abspath(a) for a in sys.argv[1:3])
axe_src = open(AXE_JS, encoding="utf-8").read()
rows = list(csv.DictReader(open(os.path.join(OUT, "syntax_layout_baseline_axe.csv"), encoding="utf-8")))

out = []
for r in rows:
    if r["baseline_detected"] == "True":
        group, reason = "baseline_detected", ""
    else:
        group = "baseline_undetected"
        ids = r["accepted_axe_ids"].split("|")
        if r["error"]:
            reason = "checker_error"
        elif not any(f'id:"{i}"' in axe_src for i in ids):
            reason = "rule_absent_in_axe"
        elif r["target_incomplete"] == "True":
            reason = "axe_incomplete"
        else:
            reason = "not_fired"
    out.append({"row": r["row"], "id": r["id"], "category": r["category"], "rule": r["rule"],
                "group": group, "reason": reason})

with open(os.path.join(OUT, "syntax_layout_groups.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

summary = {}
for cat in ("Syntax", "Layout"):
    sub = [o for o in out if o["category"] == cat]
    und = [o for o in sub if o["group"] == "baseline_undetected"]
    summary[cat] = {
        "n": len(sub),
        "baseline_detected": len(sub) - len(und),
        "baseline_undetected": len(und),
        "undetected_by_reason": dict(collections.Counter(o["reason"] for o in und).most_common()),
        "undetected_by_reason_and_rule": {
            reason: dict(collections.Counter(o["rule"] for o in und if o["reason"] == reason).most_common())
            for reason in sorted({o["reason"] for o in und})},
    }
with open(os.path.join(OUT, "syntax_layout_groups_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
