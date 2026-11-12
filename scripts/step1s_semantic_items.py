"""Step 1s: assemble the 55 checker-blind semantic cases with each model's AccessGuru repair. Free, read-only.

Per case: type, impact, description, original fragment, screenshot path (supp_material/<#>.png), the three
developers' corrections (human study) as references, and per model (GPT4, Pixtral, Qwen):
  repair      Extracted_LLM_responseHTML (the only code column; re-prompted code is not stored in the workbooks)
  paper_*     the paper's own manual verdict columns and axe (Playwright) scores before and after repair

Workbook rows are matched to cases by (# , type, whitespace-free fragment); blank and summary rows are dropped.

Usage (from the Data folder):
    python -I experiment/scripts/step1s_semantic_items.py experiment/artifact experiment/step1
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_read import read_first_sheet  # noqa: E402

csv.field_size_limit(10**9)
ART, OUT = (os.path.abspath(a) for a in sys.argv[1:3])
os.makedirs(OUT, exist_ok=True)
RES = os.path.join(ART, "results/accessguru_dataset/semantic")
SUPP = "data/accessguru_dataset/accessguru_semantic_violations_sampled_dataset_supp_material"
FILES = {
    "GPT4": ("GPT4/Re-Prompting_metacognitivePrompting_results_accessguru_semantic_dataset_gpt_4.xlsx",
             "Violation Score After Corrective Reprompting"),
    "Pixtral": ("Pixtral/Re-Prompting_metacognitivePrompting_results_accessguru_ablation_semantic_dataset_pixtral (1).xlsx",
                "Score_After_Corrective_Reprompting"),
    "Qwen": ("Qwen/Re-Prompting_metacognitivePrompting_results_accessguru_ablation_semantic_dataset_qwen-vl-plus (1).xlsx",
             "After Correction"),
}


def squash(h):
    return re.sub(r"\s+", "", h or "")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


sem = list(csv.DictReader(open(os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_semantic_violations.csv"),
                               encoding="utf-8-sig", newline="")))
devs = []
for i in (1, 2, 3):
    rows = list(csv.DictReader(open(os.path.join(ART, f"human_developer_correction_study/humanCorrection_developer{i}.csv"),
                                    encoding="utf-8-sig", newline="")))
    qcol, acol = list(rows[0].keys())[:2]
    devs.append({str(r[qcol]).strip(): r[acol] for r in rows})

cases = []
for s in sem:
    n = s["#"].strip()
    cases.append({
        "case": n, "type": s["Violation Type"].strip(), "impact": s["Impact"].strip(),
        "description": s["Description"].strip(), "url": s["webURL"].strip(), "html": s["Affected HTML"],
        "screenshot": f"{SUPP}/{n}.png" if os.path.exists(os.path.join(ART, SUPP, f"{n}.png")) else None,
        "developer_fixes": [d.get(n, "") for d in devs], "models": {},
    })

for model, (rel, after_col) in FILES.items():
    rows = [r for r in read_first_sheet(os.path.join(RES, rel)) if r["Violation Type"].strip()]
    if len(rows) != len(cases):
        raise SystemExit(f"{model}: {len(rows)} case rows, expected {len(cases)}")
    for c, r in zip(cases, rows):
        if (str(r["#"]).split(".")[0], r["Violation Type"].strip(), squash(r["Affected HTML"])) != (c["case"], c["type"], squash(c["html"])):
            raise SystemExit(f"{model}: row for case {c['case']} does not match")
        c["models"][model] = {
            "repair": r["Extracted_LLM_responseHTML"],
            "paper_old_score": num(r["Old Violation Score"]),
            "paper_new_score": num(r["New Violation Score"]),
            "paper_score_after_reprompt": num(r[after_col]),
            "paper_remarks": r["Remarks"].strip(),
            "paper_axe_score_before": num(r["InitialPlaywrightScore"]),
            "paper_axe_score_after": num(r["NewPlaywrightScore"]),
        }

with open(os.path.join(OUT, "semantic_items.jsonl"), "w", encoding="utf-8") as fh:
    for c in cases:
        fh.write(json.dumps(c, ensure_ascii=False) + "\n")

summary = {"cases": len(cases), "with_screenshot": sum(bool(c["screenshot"]) for c in cases),
           "with_3_developer_fixes": sum(all(f.strip() for f in c["developer_fixes"]) for c in cases)}
for model in FILES:
    ms = [c["models"][model] for c in cases]
    summary[model] = {
        "repairs_nonempty": sum(bool(m["repair"].strip()) for m in ms),
        "paper_fixed_first_round (new_score==0)": sum(m["paper_new_score"] == 0 for m in ms),
        "paper_fixed_after_reprompt (score==0)": sum(m["paper_score_after_reprompt"] == 0 for m in ms),
        "paper_axe_score_unchanged": sum(m["paper_axe_score_before"] == m["paper_axe_score_after"] for m in ms),
        "paper_axe_score_increased": sum((m["paper_axe_score_after"] or 0) > (m["paper_axe_score_before"] or 0) for m in ms),
        "paper_remarks_nonempty": sum(bool(m["paper_remarks"]) for m in ms),
    }
with open(os.path.join(OUT, "semantic_items_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
