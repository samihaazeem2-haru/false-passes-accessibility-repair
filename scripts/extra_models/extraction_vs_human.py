"""Do the round-2 human verdicts depend on the extraction step of the published AccessGuru pipeline?

Read-only on all inputs. Writes only:
  extra_models/extraction_vs_human.{json,csv}
(the .md is written by hand from the json). No API calls, no labelling, no labeller names in outputs.
"""
import collections
import csv
import json
import math
import os
import random
import sys

EXP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(EXP, "extra_models")
BOOT_SEED, BOOT_REPS = 20261024, 4000
MODELS = ["GPT4", "Mistral", "Qwen"]
EXAMPLES = ["R2-083", "R2-056", "R2-117", "R2-107", "R2-063"]
COL = "text_identical_ignoring_fences_and_whitespace"

P = {
    "sample_round2": os.path.join(EXP, "release/data/sample_round2.csv"),
    "labeling_key_r2": os.path.join(EXP, "release/data/labeling_key_r2.csv"),
    "human_labels_r2": os.path.join(EXP, "release/data/human_labels_r2.csv"),
    "final_extraction_rows": os.path.join(EXP, "extra_models/final_extraction_check/final_extraction_rows.csv"),
}


def read(p):
    return list(csv.DictReader(open(p, encoding="utf-8", newline="")))


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(c - h, 3), round(c + h, 3)]


def fpr(items):
    dec = [r for r in items if r["consensus"] in ("fixed", "not_fixed")]
    return None if not dec else sum(r["consensus"] == "not_fixed" for r in dec) / len(dec)


def boot(items, stat):
    clusters = collections.defaultdict(list)
    for r in items:
        clusters[r["row"]].append(r)
    cl = list(clusters.values())
    rng = random.Random(BOOT_SEED)
    reps = sorted(x for x in (stat([r for _ in cl for r in rng.choice(cl)]) for _ in range(BOOT_REPS)) if x is not None)
    ci = None if len(reps) < 20 else [round(reps[int(0.025 * len(reps))], 3), round(reps[int(0.975 * len(reps)) - 1], 3)]
    return ci, len(cl)


sample, key, human, ext = (read(P[k]) for k in ("sample_round2", "labeling_key_r2", "human_labels_r2", "final_extraction_rows"))
ext_by = {(r["model"], r["row"]): r for r in ext}
assert len(ext_by) == len(ext), "duplicate (model,row) in final_extraction_rows"
key_by = {r["item_id"]: r for r in key}
samp_by = {r["item_id"]: r for r in sample}

# ---- join + consistency checks
problems, items = [], []
for h in human:
    iid = h["item_id"]
    for src, d in (("labeling_key_r2", key_by), ("sample_round2", samp_by)):
        s = d.get(iid)
        if s is None or any(s[c] != h[c] for c in ("model", "row", "id", "category", "rule")):
            problems.append(f"{iid}: mismatch vs {src}")
    e = ext_by.get((h["model"], h["row"]))
    if e is None:
        problems.append(f"{iid}: no row in final_extraction_rows for ({h['model']},{h['row']})")
        continue
    if any(e[c] != h[c] for c in ("id", "category", "rule")):
        problems.append(f"{iid}: id/category/rule differ from final_extraction_rows")
    pub_flag = e["pub_flag_placeholder"] == "True" or e["pub_flag_no_html_tag"] == "True"
    det_flag = e["det_flag_placeholder"] == "True" or e["det_flag_no_html_tag"] == "True"
    items.append({
        "item_id": iid, "model": h["model"], "row": h["row"], "category": h["category"], "rule": h["rule"],
        "extraction_text": "same" if e[COL] == "True" else "differs",
        "consensus": h["consensus"],
        "pub_checker_pass": e["pub_checker_pass"], "det_checker_pass": e["det_checker_pass"],
        "pub_flag_no_html_or_placeholder": pub_flag, "det_flag_no_html_or_placeholder": det_flag,
        "reprompted": e["reprompted"], "raw_reply_available": e["raw_reply_available"],
    })
if len(sample) != 120 or len(key) != 120 or len(human) != 120:
    problems.append(f"unexpected sizes sample={len(sample)} key={len(key)} human={len(human)}")
if problems:
    print("STOP: join problems\n" + "\n".join(problems))
    sys.exit(1)

# ---- tables
def block(sub):
    nf = sum(r["consensus"] == "not_fixed" for r in sub)
    dec = sum(r["consensus"] in ("fixed", "not_fixed") for r in sub)
    return {"n": len(sub), "decided": dec, "consensus_not_fixed": nf, "consensus_fixed": dec - nf,
            "false_pass_rate_wilson95": wilson(nf, dec)}


groups = {}
for g in ("same", "differs", "all"):
    gi = items if g == "all" else [r for r in items if r["extraction_text"] == g]
    t = {m: block([r for r in gi if r["model"] == m]) for m in MODELS}
    t["pooled"] = block(gi)
    ci, ncl = boot(gi, fpr)
    t["pooled"]["false_pass_rate_cluster_bootstrap95"] = ci
    t["pooled"]["n_clusters"] = ncl
    groups[g] = t

# difference (differs minus same), bootstrapped jointly over all 120 items' row clusters
def diff(sub):
    a, b = fpr([r for r in sub if r["extraction_text"] == "differs"]), fpr([r for r in sub if r["extraction_text"] == "same"])
    return None if a is None or b is None else a - b

dci, _ = boot(items, diff)
difference = {"pooled_differs_minus_same": round(diff(items), 3), "cluster_bootstrap95": dci}

differs = [r for r in items if r["extraction_text"] == "differs"]
det = {}
for m in MODELS + ["pooled"]:
    sub = differs if m == "pooled" else [r for r in differs if r["model"] == m]
    det[m] = {
        "n_differs": len(sub),
        "pub_checker_pass": sum(r["pub_checker_pass"] == "True" for r in sub),
        "det_checker_pass": sum(r["det_checker_pass"] == "True" for r in sub),
        "det_checker_fail": sum(r["det_checker_pass"] == "False" for r in sub),
        "det_checker_pass_missing": sum(r["det_checker_pass"] not in ("True", "False") for r in sub),
        "flag_changed": sum(r["pub_flag_no_html_or_placeholder"] != r["det_flag_no_html_or_placeholder"] for r in sub),
        "flag_pub_only": sum(r["pub_flag_no_html_or_placeholder"] and not r["det_flag_no_html_or_placeholder"] for r in sub),
        "flag_det_only": sum(r["det_flag_no_html_or_placeholder"] and not r["pub_flag_no_html_or_placeholder"] for r in sub),
        # cross-tab of consensus x det_checker_pass
        "not_fixed_and_det_pass": sum(r["consensus"] == "not_fixed" and r["det_checker_pass"] == "True" for r in sub),
        "not_fixed_and_det_fail": sum(r["consensus"] == "not_fixed" and r["det_checker_pass"] == "False" for r in sub),
        "fixed_and_det_pass": sum(r["consensus"] == "fixed" and r["det_checker_pass"] == "True" for r in sub),
        "fixed_and_det_fail": sum(r["consensus"] == "fixed" and r["det_checker_pass"] == "False" for r in sub),
        "reprompted": sum(r["reprompted"] == "True" for r in sub),
    }

by_id = {r["item_id"]: r for r in items}
examples = [{k: by_id[i][k] for k in ("item_id", "model", "rule", "consensus", "extraction_text", "det_checker_pass",
                                      "pub_flag_no_html_or_placeholder", "det_flag_no_html_or_placeholder")} for i in EXAMPLES]

result = {
    "inputs": {k: os.path.relpath(v, EXP).replace("\\", "/") for k, v in P.items()},
    "join": {"items": len(items), "matched": len(items), "unmatched": 0, "join_key": ["model", "row"],
             "also_checked_equal": ["id", "category", "rule", "labeling_key_r2", "sample_round2"]},
    "all_pub_checker_pass": all(r["pub_checker_pass"] == "True" for r in items),
    "groups": groups, "difference": difference, "differs_detail": det, "examples": examples,
    "bootstrap": {"reps": BOOT_REPS, "seed": BOOT_SEED, "cluster": "dataset row", "ci": "2.5/97.5 percentiles"},
}
json.dump(result, open(os.path.join(OUT, "extraction_vs_human.json"), "w", encoding="utf-8"), indent=2)
with open(os.path.join(OUT, "extraction_vs_human.csv"), "w", encoding="utf-8", newline="") as f:
    cols = ["item_id", "model", "category", "rule", "extraction_text", "consensus", "det_checker_pass"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in items:
        w.writerow({c: r[c] for c in cols})
print(json.dumps(result, indent=1))
