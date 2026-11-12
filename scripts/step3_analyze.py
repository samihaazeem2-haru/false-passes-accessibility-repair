"""Step 3: checker pass vs truly fixed. Free; works on whatever judgments exist so far.

Main analysis (186 baseline-detected syntax/layout cases), per model x method:
  checker_pass         axe 4.4.1 no longer flags the target rule (Step 1)
  judged               judge verdict available (empty responses count as judged not_fixed / no_code)
  judge_fixed          verdict "fixed"
  false_pass           checker pass but judge says not_fixed      -> share of checker passes (Wilson 95% CI)
  false_fail           checker fail but judge says fixed           -> share of checker fails
  content_shrink       judge-free flag: the repair is much shorter than the original (len_ratio < 0.5) or keeps
                       fewer than 80% of the original's elements (matched by tag name, else by id or class
                       list for re-tagged elements; a full-page wrapper adds elements but never hides a dropped
                       one). Raw values are in main_joined.csv; its precision is checked on the human sample.
Checker-blind semantic (55 cases), per model: judge fixed rate, agreement with the paper's own manual
verdict (new score == 0), the paper's axe score change, and our axe run (step1/semantic_axe.csv) against the
paper's manual verdict -- does an axe "pass" say anything about a semantic fix?

$0 plan, human sample (step2/human_labels.csv from step2h_labeling.py merge; 120 checker-passing AccessGuru-final
repairs, 40 per model, drawn at random before any judge ran):
  false-pass rate per model = consensus "not_fixed" / consensus fixed-or-not_fixed, with a 95% cluster
  bootstrap CI that resamples cases (the same case can be sampled for several models), plus pooled and
  pairwise model differences, and the implied true-fix rate on all 186 (checker pass rate x (1 - false pass)).
  Cohen's kappa between labellers A and B (3 labels, and binary where both decided).
  Each judge in step2/human_sample_judgments.jsonl vs the human consensus (agreement, kappa), also on the
  items where judge and repairer are from different families; skipped items are listed.
  content_shrink flag vs the human consensus.
  Round 1 is the pilot (rubric v1); its output keys are unchanged (copy: step3/results_round1.json).

Round 2 (primary; plan frozen in PLAN_round2.md; step2r2/ from step2h_labeling_r2.py and step2_judge.py --round 2):
  the same human-sample analysis on 120 new items (rubric v2), plus each labeller's own false-pass rate
  (unclear excluded / unclear counted as not_fixed), the consensus with unclear counted as not_fixed, a check
  that the sample file still matches the hash in the plan, a round1-vs-round2 table and a combined
  round1+round2 estimate (secondary: the rubric differed). Writes step3/results_round2.md in plain language.

Usage (from the Data folder):
    python -I experiment/scripts/step3_analyze.py experiment
"""
import collections
import csv
import hashlib
import html.parser
import json
import math
import os
import random
import sys

csv.field_size_limit(10**9)
EXP = os.path.abspath(sys.argv[1])
OUT = os.path.join(EXP, "step3")
os.makedirs(OUT, exist_ok=True)
METHODS = ["baseline_one", "baseline_two", "baseline_three", "accessguru_first", "accessguru_final"]
SHRINK_LEN_RATIO = 0.5
SHRINK_KEPT_RATIO = 0.8
BOOT_REPS = 4000
BOOT_SEED = 20261024
# judge family -> repairer model of the same family (in-family judging risks self-preference)
JUDGE_FAMILY = {"openai/": "GPT4", "qwen/": "Qwen", "mistral": "Mistral", "google/": None, "gemini": None, "meta-llama/": None, "llama": None}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(k / n, 3), round(c - h, 3), round(c + h, 3)]


def jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")] if os.path.exists(path) else []


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    labels = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


class _Elements(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []  # (tag, id, class)

    def handle_starttag(self, tag, attrs):  # also called for <x/> via handle_startendtag
        a = dict(attrs)
        self.elements.append((tag, (a.get("id") or "").strip(), " ".join(sorted((a.get("class") or "").split()))))


def elements(text):
    p = _Elements()
    try:
        p.feed(text or "")
        p.close()
    except Exception:  # noqa: BLE001 -- malformed markup: count what was parsed
        pass
    return p.elements


def shrink(original, response, len_ratio):
    """An original element counts as kept if the repair still has an unused element with the same tag, or,
    for a re-tagged element (e.g. div -> header for landmark rules), the same id or the same class list."""
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


def boot_ci(values):
    v = sorted(x for x in values if x is not None)
    if len(v) < 20:
        return None
    return [round(v[int(0.025 * len(v))], 3), round(v[int(0.975 * len(v)) - 1], 3)]


# ---------------------------------------------------------------- main analysis
sample = [r for r in csv.DictReader(open(os.path.join(EXP, "artifact/data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                         encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]
responses = {(r["model"], r["method"], r["row"]): r["response"] for r in jsonl(os.path.join(EXP, "step1/responses.jsonl"))}
checker = {(r["model"], r["method"], int(r["row"])): r
           for r in csv.DictReader(open(os.path.join(EXP, "step1/checker_on_paper_outputs.csv"), encoding="utf-8"))}
judg = {r["judge_key"]: r for r in jsonl(os.path.join(EXP, "step2/judgments.jsonl"))}
keys = {(r["model"], r["method"], r["row"]): r["judge_key"] for r in jsonl(os.path.join(EXP, "step2/items.jsonl"))}

joined = []
for k, c in checker.items():
    if c["empty_response"] == "True":
        verdict, mode = "not_fixed", "no_code"
    else:
        jr = judg.get(keys.get(k))
        verdict, mode = (jr["verdict"], jr["failure_mode"]) if jr else (None, None)
    sh = (shrink(sample[k[2]]["affectedHTMLElement(s)"], responses[k], c["len_ratio"]) if c["empty_response"] != "True"
          else {"elements_orig": "", "elements_kept": "", "elements_kept_ratio": "", "content_shrink": ""})
    joined.append({**c, **sh, "judge_verdict": verdict, "judge_failure_mode": mode})

with open(os.path.join(OUT, "main_joined.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(joined[0].keys()))
    w.writeheader()
    w.writerows(joined)

main = {}
for model in sorted({r["model"] for r in joined}):
    for method in METHODS:
        sub = [r for r in joined if r["model"] == model and r["method"] == method]
        jd = [r for r in sub if r["judge_verdict"] in ("fixed", "not_fixed", "unclear")]
        cp = [r for r in jd if r["checker_pass"] == "True"]
        cf = [r for r in jd if r["checker_pass"] == "False"]
        fp = [r for r in cp if r["judge_verdict"] == "not_fixed"]
        main[f"{model}|{method}"] = {
            "n": len(sub),
            "checker_pass": sum(r["checker_pass"] == "True" for r in sub),
            "checker_pass_content_shrink": sum(r["checker_pass"] == "True" and r["content_shrink"] is True for r in sub),
            "judged": len(jd),
            "judge_fixed": sum(r["judge_verdict"] == "fixed" for r in jd),
            "judge_unclear": sum(r["judge_verdict"] == "unclear" for r in jd),
            "checker_pass_judged": len(cp),
            "false_pass": len(fp),
            "false_pass_rate_ci": wilson(len(fp), len(cp)),
            "false_fail": sum(r["judge_verdict"] == "fixed" for r in cf),
            "false_fail_rate_ci": wilson(sum(r["judge_verdict"] == "fixed" for r in cf), len(cf)),
            "false_pass_modes": dict(collections.Counter(r["judge_failure_mode"] for r in fp).most_common()),
        }

by_rule = collections.defaultdict(lambda: collections.Counter())
for r in joined:
    if r["method"] == "accessguru_final" and r["checker_pass"] == "True" and r["judge_verdict"]:
        by_rule[(r["category"], r["rule"])]["checker_pass_judged"] += 1
        by_rule[(r["category"], r["rule"])]["false_pass"] += r["judge_verdict"] == "not_fixed"
rules = sorted(({"category": c, "rule": rl, **v} for (c, rl), v in by_rule.items()),
               key=lambda x: -x["checker_pass_judged"])

# ---------------------------------------------------------------- semantic
sem_cases = jsonl(os.path.join(EXP, "step1/semantic_items.jsonl"))
sem_j = {r["judge_key"]: r for r in jsonl(os.path.join(EXP, "step2/semantic_judgments.jsonl"))}
sem_keys = {(r["case"], r["model"]): r["judge_key"] for r in jsonl(os.path.join(EXP, "step2/semantic_items.jsonl"))}
semantic = {}
for model in ("GPT4", "Pixtral", "Qwen"):
    rows = []
    for c in sem_cases:
        m = c["models"][model]
        jr = sem_j.get(sem_keys.get((c["case"], model)))
        rows.append((m, jr["verdict"] if jr else None))
    jd = [(m, v) for m, v in rows if v in ("fixed", "not_fixed", "unclear")]
    paper_pairs = [("fixed" if m["paper_new_score"] == 0 else "not_fixed", v) for m, v in jd
                   if v in ("fixed", "not_fixed") and m["paper_new_score"] is not None]
    semantic[model] = {
        "n": len(rows), "judged": len(jd),
        "judge_fixed_rate_ci": wilson(sum(v == "fixed" for _, v in jd), len(jd)),
        "paper_fixed_rate (first round)": wilson(sum(m["paper_new_score"] == 0 for m, _ in rows), len(rows)),
        "judge_vs_paper_agreement": round(sum(a == b for a, b in paper_pairs) / len(paper_pairs), 3) if paper_pairs else None,
        "judge_vs_paper_kappa": kappa(paper_pairs),
        "paper_says_fixed_judge_says_not": sum(a == "fixed" and b == "not_fixed" for a, b in paper_pairs),
        "axe_score_unchanged_after_repair": sum(m["paper_axe_score_before"] == m["paper_axe_score_after"] for m, _ in rows),
        "axe_score_increased_after_repair": sum((m["paper_axe_score_after"] or 0) > (m["paper_axe_score_before"] or 0) for m, _ in rows),
    }

# our axe 4.4.1 run on the semantic repairs vs the paper's own manual verdict. Axe cannot see these faults,
# so an informative checker would at least track the manual verdict; kappa near 0 says it does not.
sem_axe = {(r["case"], r["model"]): r for r in csv.DictReader(open(os.path.join(EXP, "step1/semantic_axe.csv"), encoding="utf-8"))}
semantic_axe_vs_paper = {}
for model in ("GPT4", "Pixtral", "Qwen"):
    rows = []
    for c in sem_cases:
        m, ax = c["models"][model], sem_axe.get((c["case"], model))
        if ax is None or ax["error"] or m["paper_new_score"] is None:
            continue
        rows.append({"paper": "fixed" if m["paper_new_score"] == 0 else "not_fixed",
                     "no_new_violation": "fixed" if not ax["introduced"] else "not_fixed",
                     "clean_after": "fixed" if int(ax["n_after"] or 0) == 0 else "not_fixed"})
    out = {"n": len(rows), "paper_fixed": sum(r["paper"] == "fixed" for r in rows)}
    for axe_def in ("no_new_violation", "clean_after"):
        pairs = [(r["paper"], r[axe_def]) for r in rows]
        out[f"axe_{axe_def}"] = {
            "axe_pass": sum(b == "fixed" for _, b in pairs),
            "agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None,
            "kappa": kappa(pairs),
            "paper_not_fixed_but_axe_pass": sum(a == "not_fixed" and b == "fixed" for a, b in pairs),
            "paper_fixed_but_axe_fail": sum(a == "fixed" and b == "not_fixed" for a, b in pairs)}
    semantic_axe_vs_paper[model] = out

# ---------------------------------------------------------------- $0 plan: human sample
jrow = {(r["model"], r["method"], int(r["row"])): r for r in joined}
PASS_RATE = {m: sum(r["checker_pass"] == "True" for r in joined if r["model"] == m and r["method"] == "accessguru_final") /
             sum(1 for r in joined if r["model"] == m and r["method"] == "accessguru_final") for m in {r["model"] for r in joined}}


def read_judgments(path):
    out = {}
    for r in jsonl(path):
        out[(r["judge_model"], r["item_id"])] = r  # later records override earlier ones
    return out


def judges_alone_section(hkey, judgments_path):
    """Judges on a human sample, before any human labels: per-model "false pass" as each judge sees it,
    judge-vs-judge agreement and judge vs the judge-free content_shrink flag. None of this replaces the humans."""
    flag = {k["item_id"]: jrow[(k["model"], "accessguru_final", int(k["row"]))]["content_shrink"] is True for k in hkey}
    hjv = {k: r["verdict"] for k, r in read_judgments(judgments_path).items()}
    jms = sorted({m for m, _ in hjv})
    sample_models = sorted({k["model"] for k in hkey})
    out = {"per_judge": {}, "judge_vs_judge": {}}
    for jm in jms:
        per_model = {}
        for model in sample_models:
            vs = [hjv.get((jm, k["item_id"])) for k in hkey if k["model"] == model]
            dec_v = [v for v in vs if v in ("fixed", "not_fixed")]
            per_model[model] = {"judged": sum(v in ("fixed", "not_fixed", "unclear") for v in vs),
                                "not_fixed": sum(v == "not_fixed" for v in vs), "fixed": sum(v == "fixed" for v in vs),
                                "unclear": sum(v == "unclear" for v in vs),
                                "judge_false_pass_rate_ci": wilson(sum(v == "not_fixed" for v in dec_v), len(dec_v))}
        pairs = [("not_fixed" if flag[k["item_id"]] else "fixed", hjv.get((jm, k["item_id"]))) for k in hkey
                 if hjv.get((jm, k["item_id"])) in ("fixed", "not_fixed")]
        out["per_judge"][jm] = {
            "by_repairer_model": per_model,
            "skipped_too_large": sorted(k["item_id"] for k in hkey if hjv.get((jm, k["item_id"])) == "skipped_too_large"),
            "judge_error": sorted(k["item_id"] for k in hkey if hjv.get((jm, k["item_id"])) == "judge_error"),
            "not_judged_yet": sum((jm, k["item_id"]) not in hjv for k in hkey),
            "content_shrink_flagged_judge_not_fixed": f"{sum(a == b == 'not_fixed' for a, b in pairs)}/{sum(a == 'not_fixed' for a, _ in pairs)}",
            "content_shrink_unflagged_judge_not_fixed": f"{sum(a == 'fixed' and b == 'not_fixed' for a, b in pairs)}/{sum(a == 'fixed' for a, _ in pairs)}",
            "kappa_shrink_flag_vs_judge": kappa(pairs)}
    for i, a in enumerate(jms):
        for b in jms[i + 1:]:
            pairs = [(hjv.get((a, k["item_id"])), hjv.get((b, k["item_id"]))) for k in hkey]
            pairs = [p for p in pairs if p[0] in ("fixed", "not_fixed") and p[1] in ("fixed", "not_fixed")]
            out["judge_vs_judge"][f"{a} vs {b}"] = {
                "both_decided": len(pairs),
                "agreement": round(sum(x == y for x, y in pairs) / len(pairs), 3) if pairs else None,
                "kappa": kappa(pairs)}
    return out


def load_human_rows(path):
    hrows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in hrows:
        r["content_shrink"] = jrow[(r["model"], "accessguru_final", int(r["row"]))]["content_shrink"] is True
    return hrows


def fpr(items, col="consensus", unclear_nf=False):
    """Share not_fixed among decided items; with unclear_nf, "unclear" counts as not_fixed instead of being excluded."""
    bad = ("not_fixed", "unclear") if unclear_nf else ("not_fixed",)
    d = [r for r in items if r[col] in ("fixed", "not_fixed") or (unclear_nf and r[col] == "unclear")]
    return sum(r[col] in bad for r in d) / len(d) if d else None


def fp_stats(items, models, col="consensus", unclear_nf=False):
    s = {m: fpr([r for r in items if r["model"] == m], col, unclear_nf) for m in models}
    s["pooled"] = fpr(items, col, unclear_nf)
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            s[f"{a}-{b}"] = None if s[a] is None or s[b] is None else s[a] - s[b]
    for m in models:
        s[f"true_fix_186_{m}"] = None if s[m] is None else PASS_RATE[m] * (1 - s[m])
    return s


def boot_table(items, models, col="consensus", unclear_nf=False):
    """Point estimates and 95% cluster-bootstrap CIs (cases = dataset rows resampled with replacement)."""
    point = fp_stats(items, models, col, unclear_nf)
    clusters = collections.defaultdict(list)
    for r in items:
        clusters[r["row"]].append(r)
    cl = list(clusters.values())
    rng = random.Random(BOOT_SEED)
    reps = [fp_stats([r for _ in cl for r in rng.choice(cl)], models, col, unclear_nf) for _ in range(BOOT_REPS)]
    return {k: {"estimate": None if v is None else round(v, 3), "ci95_cluster_bootstrap": boot_ci([x[k] for x in reps])}
            for k, v in point.items()}, len(cl)


def human_section(hrows, judgments_path, sample_desc):
    models = sorted({r["model"] for r in hrows})
    fp_table, n_clusters = boot_table(hrows, models)
    for m in models:
        sub = [r for r in hrows if r["model"] == m]
        fp_table[m].update({"n": len(sub), "consensus_not_fixed": sum(r["consensus"] == "not_fixed" for r in sub),
                            "consensus_fixed": sum(r["consensus"] == "fixed" for r in sub),
                            "consensus_unclear": sum(r["consensus"] == "unclear" for r in sub),
                            "no_consensus_yet": sum(not r["consensus"] for r in sub),
                            "wilson_ci95_ignoring_clusters": wilson(sum(r["consensus"] == "not_fixed" for r in sub),
                                                                    sum(r["consensus"] in ("fixed", "not_fixed") for r in sub))})

    both = [(r["label_A"], r["label_B"]) for r in hrows if r["label_A"] and r["label_B"]]
    both_bin = [p for p in both if p[0] in ("fixed", "not_fixed") and p[1] in ("fixed", "not_fixed")]
    inter_rater = {"both_labelled": len(both),
                   "agreement_3_labels": round(sum(a == b for a, b in both) / len(both), 3) if both else None,
                   "kappa_3_labels": kappa(both),
                   "both_decided": len(both_bin),
                   "agreement_binary": round(sum(a == b for a, b in both_bin) / len(both_bin), 3) if both_bin else None,
                   "kappa_binary": kappa(both_bin),
                   "confusion_A_x_B": dict(collections.Counter(f"{a}|{b}" for a, b in both))}

    hj = read_judgments(judgments_path)
    judges = {}
    for jm in sorted({k[0] for k in hj}):
        fam = next((v for k, v in JUDGE_FAMILY.items() if jm.lower().startswith(k)), None)
        recs = {iid: r for (m, iid), r in hj.items() if m == jm}
        pairs, pairs_out = [], []
        for r in hrows:
            v = recs.get(r["item_id"], {}).get("verdict")
            if r["consensus"] in ("fixed", "not_fixed") and v in ("fixed", "not_fixed"):
                pairs.append((r["consensus"], v))
                if r["model"] != fam:
                    pairs_out.append((r["consensus"], v))
        judged = [r for r in recs.values() if r["verdict"] in ("fixed", "not_fixed", "unclear")]
        judges[jm] = {
            "same_family_repairer": fam,
            "judged": len(judged),
            "skipped_too_large": sorted(i for i, r in recs.items() if r["verdict"] == "skipped_too_large"),
            "judge_error": sorted(i for i, r in recs.items() if r["verdict"] == "judge_error"),
            "not_judged_yet": sum(r["item_id"] not in recs for r in hrows),
            "judge_false_pass_rate": round(sum(r["verdict"] == "not_fixed" for r in judged) /
                                           max(1, sum(r["verdict"] in ("fixed", "not_fixed") for r in judged)), 3) if judged else None,
            "vs_human_n": len(pairs),
            "vs_human_agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None,
            "vs_human_kappa": kappa(pairs),
            "human_fixed_judge_not": sum(a == "fixed" and b == "not_fixed" for a, b in pairs),
            "human_not_judge_fixed": sum(a == "not_fixed" and b == "fixed" for a, b in pairs),
            "out_of_family_n": len(pairs_out),
            "out_of_family_agreement": round(sum(a == b for a, b in pairs_out) / len(pairs_out), 3) if pairs_out else None,
            "out_of_family_kappa": kappa(pairs_out),
        }

    dec = [r for r in hrows if r["consensus"] in ("fixed", "not_fixed")]
    flagged = [r for r in dec if r["content_shrink"]]
    shrink_vs_human = {"decided": len(dec), "flagged": len(flagged),
                       "flagged_and_human_not_fixed": sum(r["consensus"] == "not_fixed" for r in flagged),
                       "unflagged_and_human_not_fixed": sum(r["consensus"] == "not_fixed" and not r["content_shrink"] for r in dec),
                       "kappa_flag_vs_human": kappa([(r["consensus"], "not_fixed" if r["content_shrink"] else "fixed") for r in dec])}
    return {"design": f"{len(hrows)} checker-passing AccessGuru-final repairs, {sample_desc}, "
                      f"{n_clusters} distinct cases; cluster bootstrap over cases, {BOOT_REPS} reps, seed {BOOT_SEED}",
            "false_pass_rate_human_consensus": fp_table, "inter_rater": inter_rater,
            "judges_vs_human": judges, "content_shrink_vs_human": shrink_vs_human}


def per_labeller_section(hrows):
    """Each labeller's own false-pass rate before adjudication, unclear excluded and unclear counted as not_fixed."""
    models = sorted({r["model"] for r in hrows})
    out = {}
    for lab in ("A", "B"):
        col = f"label_{lab}"
        out[f"labeller_{lab}"] = {"labelled": sum(bool(r[col]) for r in hrows),
                                  "counts": {m: dict(collections.Counter(r[col] or "missing" for r in hrows if r["model"] == m)) for m in models}}
        for mode, nf in (("unclear_excluded", False), ("unclear_as_not_fixed", True)):
            t, _ = boot_table(hrows, models, col, nf)
            out[f"labeller_{lab}"][mode] = {k: t[k] for k in models + ["pooled"]}
    return out


# ---- round 1 (pilot, rubric v1): unchanged output under the same keys as before
judges_alone = None
key_path = os.path.join(EXP, "step2/labeling_key.csv")
if os.path.exists(key_path):
    judges_alone = judges_alone_section(list(csv.DictReader(open(key_path, encoding="utf-8"))),
                                        os.path.join(EXP, "step2/human_sample_judgments.jsonl"))
human, hrows1 = None, None
hl = os.path.join(EXP, "step2/human_labels.csv")
if os.path.exists(hl):
    hrows1 = load_human_rows(hl)
    human = human_section(hrows1, os.path.join(EXP, "step2/human_sample_judgments.jsonl"), "random per model (seed 20261023)")

# ---- round 2 (rubric v2, 120 new items on cases not used in round 1): primary per PLAN_round2.md
R2 = os.path.join(EXP, "step2r2")
r2_alone, r2_human, hrows2, r2_plan = None, None, None, None
key2 = os.path.join(R2, "labeling_key_r2.csv")
if os.path.exists(key2):
    hkey2 = list(csv.DictReader(open(key2, encoding="utf-8")))
    sample_hash = hashlib.sha256(open(os.path.join(R2, "sample_round2.csv"), "rb").read()).hexdigest()
    plan_path = os.path.join(EXP, "PLAN_round2.md")
    r2_plan = {"plan_file": "PLAN_round2.md", "sample_round2_sha256": sample_hash,
               "sample_hash_matches_plan": os.path.exists(plan_path) and sample_hash in open(plan_path, encoding="utf-8").read(),
               "overlap_with_round1_cases": len({k["row"] for k in hkey2} & {k["row"] for k in csv.DictReader(open(key_path, encoding="utf-8"))})
               if os.path.exists(key_path) else None,
               # a case is one dataset row (one violation); several rows can come from the same web page (dataset "id")
               "items_from_a_web_page_also_used_in_round1": sum(k["id"] in {r["id"] for r in csv.DictReader(open(key_path, encoding="utf-8"))}
                                                                for k in hkey2) if os.path.exists(key_path) else None}
    r2_alone = judges_alone_section(hkey2, os.path.join(R2, "human_sample_judgments_r2.jsonl"))
    hl2 = os.path.join(R2, "human_labels_r2.csv")
    if os.path.exists(hl2):
        hrows2 = load_human_rows(hl2)
        r2_human = human_section(hrows2, os.path.join(R2, "human_sample_judgments_r2.jsonl"),
                                 "random per model (seed 20261026) excluding every round-1 case, rubric v2")
        r2_human["labels_complete"] = {"A": sum(bool(r["label_A"]) for r in hrows2), "B": sum(bool(r["label_B"]) for r in hrows2),
                                       "consensus": sum(bool(r["consensus"]) for r in hrows2), "n": len(hrows2)}
        r2_human["consensus_sensitivity_unclear_as_not_fixed"] = boot_table(hrows2, sorted({r["model"] for r in hrows2}), unclear_nf=True)[0]
        r2_human["per_labeller_false_pass"] = per_labeller_section(hrows2)


def round_summary(hrows, sec):
    if not sec:
        return None
    fp = sec["false_pass_rate_human_consensus"]
    pl = per_labeller_section(hrows)
    ir = sec["inter_rater"]
    return {"kappa_binary_before_adjudication": ir["kappa_binary"], "kappa_3_labels_before_adjudication": ir["kappa_3_labels"],
            "agreement_binary": ir["agreement_binary"], "both_decided": ir["both_decided"],
            "unclear_by_A": sum(r["label_A"] == "unclear" for r in hrows), "unclear_by_B": sum(r["label_B"] == "unclear" for r in hrows),
            "consensus_false_pass": {k: fp[k] for k in fp if not k.startswith("true_fix") and "-" not in k},
            "true_fix_186": {k: fp[k] for k in fp if k.startswith("true_fix")},
            "labeller_false_pass_pooled": {f"{lab}_{mode}": pl[f"labeller_{lab}"][mode]["pooled"]
                                           for lab in ("A", "B") for mode in ("unclear_excluded", "unclear_as_not_fixed")},
            "judge_vs_human_kappa": {jm: v["vs_human_kappa"] for jm, v in sec["judges_vs_human"].items()},
            "content_shrink_flagged_not_fixed": f"{sec['content_shrink_vs_human']['flagged_and_human_not_fixed']}/{sec['content_shrink_vs_human']['flagged']}"}


round_cmp = {"note": "round 1 = pilot, rubric v1; round 2 = primary, rubric v1 + v2 addendum; different items and cases",
             "round1": round_summary(hrows1, human), "round2": round_summary(hrows2, r2_human)}

combined = None
if hrows1 and hrows2:
    both_rounds = [{**r, "round": 1} for r in hrows1] + [{**r, "round": 2} for r in hrows2]
    cmodels = sorted({r["model"] for r in both_rounds})
    ctab, ncl = boot_table(both_rounds, cmodels)
    combined = {"label": "SECONDARY: the rubric differed between rounds (v1 vs v1 + v2 addendum); round 2 alone is primary",
                "design": f"{len(both_rounds)} items, {ncl} distinct cases (round-2 cases exclude round-1 cases), "
                          f"cluster bootstrap over cases, {BOOT_REPS} reps, seed {BOOT_SEED}",
                "n_decided": {m: sum(r["model"] == m and r["consensus"] in ("fixed", "not_fixed") for r in both_rounds) for m in cmodels},
                "false_pass_rate_human_consensus": ctab}

result = {"main_by_model_method": main, "accessguru_final_false_pass_by_rule": rules,
          "semantic_checker_blind": semantic, "semantic_axe_vs_paper_manual": semantic_axe_vs_paper,
          "human_sample_judges_alone_0usd": judges_alone, "human_sample_0usd": human,
          "human_sample_round2_plan": r2_plan, "human_sample_round2_judges_alone": r2_alone,
          "human_sample_round2": r2_human, "round1_vs_round2": round_cmp,
          "combined_round1_round2_secondary": combined}
with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)


# ---------------------------------------------------------------- results_round2.md (plain language, numbers from above only)
def pct(e):
    """{"estimate", "ci95_cluster_bootstrap"} -> '34.2% (95% CI 25.0% to 44.1%)'."""
    if not e or e.get("estimate") is None:
        return "not available"
    ci = e.get("ci95_cluster_bootstrap")
    s = f"{100 * e['estimate']:.1f}%"
    return s + (f" (95% CI {100 * ci[0]:.1f}% to {100 * ci[1]:.1f}%)" if ci else " (CI not available)")


def diff(e):
    if not e or e.get("estimate") is None:
        return "not available"
    ci = e.get("ci95_cluster_bootstrap")
    return f"{100 * e['estimate']:+.1f} points" + (f" (95% CI {100 * ci[0]:+.1f} to {100 * ci[1]:+.1f})" if ci else "")


def na(v):
    return "not available" if v is None else v


def kword(k):
    if k is None:
        return "not available"
    band = ("poor (below chance)" if k < 0 else "slight" if k <= 0.2 else "fair" if k <= 0.4 else "moderate" if k <= 0.6
            else "substantial" if k <= 0.8 else "almost perfect")
    return f"{k} ({band} agreement on the Landis-Koch scale)"


def write_md():
    L = ["# Round 2 results: checker pass vs truly fixed", "",
         "Generated by `step3_analyze.py` from `step3/results.json`. Every number below is computed by the script; nothing is typed in by hand.",
         "Plan: `PLAN_round2.md` (frozen before labelling). Round 1 is the pilot (`step3/results_round1.json`).", ""]
    if r2_plan:
        L += [f"- Sample file hash `{r2_plan['sample_round2_sha256']}`; matches the frozen plan: **{'yes' if r2_plan['sample_hash_matches_plan'] else 'NO'}**.",
              f"- Round-2 cases that were also used in round 1: {r2_plan['overlap_with_round1_cases']}. "
              f"Items whose web page (dataset `id`) also gave a different violation to round 1: {r2_plan['items_from_a_web_page_also_used_in_round1']}.", ""]
    L += ["## 1. Human labels", ""]
    if not r2_human:
        L += ["Not merged yet (`step2r2/human_labels_r2.csv` missing). Sections 1 to 4 fill in after the merge.", ""]
    else:
        lc, ir = r2_human["labels_complete"], r2_human["inter_rater"]
        fp = r2_human["false_pass_rate_human_consensus"]
        models = [m for m in ("GPT4", "Mistral", "Qwen") if m in fp]
        L += [f"Labelled: A {lc['A']}/{lc['n']}, B {lc['B']}/{lc['n']}; consensus available for {lc['consensus']}/{lc['n']}.", ""]
        if lc["consensus"] < lc["n"]:
            L += [f"**{lc['n'] - lc['consensus']} items have no consensus yet** (missing labels or not yet adjudicated). "
                  "The numbers below use only the items that do; finish the adjudication before reporting them.", ""]
        L += ["### Reliability before adjudication (primary reliability measure)", "",
              f"- Binary Cohen's kappa (both said fixed or not_fixed, n = {ir['both_decided']}): **{kword(ir['kappa_binary'])}**; "
              f"raw agreement {ir['agreement_binary']}.",
              f"- 3-label kappa (fixed / not_fixed / unclear, n = {ir['both_labelled']}): {kword(ir['kappa_3_labels'])}; raw agreement {ir['agreement_3_labels']}.",
              f"- A × B counts: {', '.join(f'{k} {v}' for k, v in sorted(ir['confusion_A_x_B'].items()))}.",
              ("- The plan set 0.6 as the bar for trusting the consensus. Binary kappa is "
               + ("**at or above** 0.6." if (ir["kappa_binary"] or 0) >= 0.6 else "**below** 0.6, so the consensus numbers carry that caveat.")),
              ""]
        L += ["### False-pass rate (primary outcome)", "",
              "Share of checker-passing AccessGuru-final repairs that the two labellers' consensus calls **not fixed** "
              "(consensus `unclear` excluded). CIs: cluster bootstrap by case.", "",
              "| Repairer | Not fixed / decided | False-pass rate |", "|---|---|---|"]
        for m in models:
            L.append(f"| {m} | {fp[m]['consensus_not_fixed']} / {fp[m]['consensus_not_fixed'] + fp[m]['consensus_fixed']} | {pct(fp[m])} |")
        L += [f"| Pooled | | {pct(fp['pooled'])} |", "",
              "Model differences (first minus second): " + "; ".join(f"{k} {diff(fp[k])}" for k in fp if "-" in k and not k.startswith("true")) + ".", "",
              "**True-fix estimate over all 186 cases** = checker pass rate × (1 − false-pass rate): "
              + "; ".join(f"{m} {pct(fp[f'true_fix_186_{m}'])}" for m in models) + ".", ""]
        sens = r2_human["consensus_sensitivity_unclear_as_not_fixed"]
        L += ["Sensitivity (consensus `unclear` counted as not fixed): " + "; ".join(f"{m} {pct(sens[m])}" for m in models)
              + f"; pooled {pct(sens['pooled'])}.", ""]
        pl = r2_human["per_labeller_false_pass"]
        L += ["### Each labeller alone (before adjudication)", "",
              "| Labeller | Unclear | " + " | ".join(models) + " | Pooled |", "|---|---|" + "---|" * (len(models) + 1)]
        for lab in ("A", "B"):
            for mode, name in (("unclear_excluded", "excluded"), ("unclear_as_not_fixed", "counted as not fixed")):
                t = pl[f"labeller_{lab}"][mode]
                L.append(f"| {lab} | {name} | " + " | ".join(pct(t[m]) for m in models) + f" | {pct(t['pooled'])} |")
        L.append("")
        sh = r2_human["content_shrink_vs_human"]
        L += ["### Content-shrink flag vs humans", "",
              f"Of {sh['decided']} decided items, the judge-free flag fired on {sh['flagged']}; humans called {sh['flagged_and_human_not_fixed']} of those not fixed. "
              f"Among unflagged items, humans called {sh['unflagged_and_human_not_fixed']} not fixed. Kappa flag vs humans: {kword(sh['kappa_flag_vs_human'])}.", ""]
    L += ["## 2. Free Groq judges on the 120 round-2 items", ""]
    if not r2_alone or not r2_alone["per_judge"]:
        L += ["Not run yet.", ""]
    else:
        for jm, v in r2_alone["per_judge"].items():
            per = v["by_repairer_model"]
            L += [f"- **{jm}** calls not fixed: " + "; ".join(f"{x['not_fixed']}/{x['not_fixed'] + x['fixed']} of {m}'s repairs" for m, x in per.items())
                  + f". Skipped as too large ({len(v['skipped_too_large'])}): {', '.join(v['skipped_too_large']) or 'none'}. "
                  f"Errors: {', '.join(v['judge_error']) or 'none'}. Not judged yet: {v['not_judged_yet']}."]
        for k, v in r2_alone["judge_vs_judge"].items():
            L.append(f"- Judge vs judge ({k}): both decided {v['both_decided']}, agreement {v['agreement']}, kappa {kword(v['kappa'])}.")
        L.append("")
        if r2_human:
            L += ["Judges vs the human consensus (a judge could stand in for humans only if kappa ≥ 0.7, per the plan):", "",
                  "| Judge | n | Agreement | Kappa | Out-of-family n | Out-of-family kappa |", "|---|---|---|---|---|---|"]
            for jm, v in r2_human["judges_vs_human"].items():
                L.append(f"| {jm} | {v['vs_human_n']} | {na(v['vs_human_agreement'])} | {na(v['vs_human_kappa'])} | {v['out_of_family_n']} | {na(v['out_of_family_kappa'])} |")
            L.append("")
        else:
            L += ["These are judge opinions only, not results: no human labels are merged yet.", ""]
    L += ["## 3. Round 1 (pilot) vs round 2", ""]
    r1s, r2s = round_cmp["round1"], round_cmp["round2"]
    if r1s and r2s:
        def row(name, f):
            return f"| {name} | {na(f(r1s))} | {na(f(r2s))} |"
        L += ["| | Round 1 (rubric v1, pilot) | Round 2 (rubric v2, primary) |", "|---|---|---|",
              row("Binary kappa A-B, before adjudication", lambda s: f"{s['kappa_binary_before_adjudication']} (n = {s['both_decided']})"),
              row("3-label kappa A-B", lambda s: s["kappa_3_labels_before_adjudication"]),
              row("Unclear labels, A / B", lambda s: f"{s['unclear_by_A']} / {s['unclear_by_B']}")]
        for m in ("GPT4", "Mistral", "Qwen", "pooled"):
            L.append(row(f"Consensus false-pass, {m}", lambda s, m=m: pct(s["consensus_false_pass"].get(m))))
        for m in ("GPT4", "Mistral", "Qwen"):
            L.append(row(f"True fix over 186, {m}", lambda s, m=m: pct(s["true_fix_186"].get(f"true_fix_186_{m}"))))
        for k in r2s["labeller_false_pass_pooled"]:
            L.append(row(f"Labeller {k.replace('_', ' ', 1).replace('_', ' ')} (pooled)", lambda s, k=k: pct(s["labeller_false_pass_pooled"][k])))
        for jm in sorted(set(r1s["judge_vs_human_kappa"]) | set(r2s["judge_vs_human_kappa"])):
            L.append(row(f"Kappa {jm} vs humans", lambda s, jm=jm: s["judge_vs_human_kappa"].get(jm)))
        L += [row("Content-shrink flagged and not fixed", lambda s: s["content_shrink_flagged_not_fixed"]), ""]
    else:
        L += ["Available once round-2 labels are merged.", ""]
    L += ["## 4. Combined round 1 + round 2 (secondary)", ""]
    if combined:
        c = combined["false_pass_rate_human_consensus"]
        L += [f"**{combined['label']}.** {combined['design']}.", "",
              "False-pass rate: " + "; ".join(f"{m} {pct(c[m])} (decided n = {combined['n_decided'][m]})" for m in combined["n_decided"])
              + f"; pooled {pct(c['pooled'])}.",
              "True fix over 186: " + "; ".join(f"{m} {pct(c[f'true_fix_186_{m}'])}" for m in combined["n_decided"]) + ".", ""]
    else:
        L += ["Available once round-2 labels are merged.", ""]
    L += ["## Caveats", "",
          "- The sample covers only checker-passing AccessGuru-final repairs, so the false-pass rate is P(not truly fixed | checker pass) for that method.",
          "- Round-2 cases exclude every round-1 case. Because round 1's cases were themselves random, round 2 is still a random sample of cases, "
          "but the two rounds together are not one simple random sample. That is one more reason the combined estimate is secondary.",
          "- A case is one dataset row (one violation). Several cases can come from the same web page, so some round-2 items share a page "
          "with round-1 items (count above), and the bootstrap, which resamples cases, does not model page-level correlation.",
          "- The labellers are the author (A) and a classmate (B), not independent experts.",
          "- The judges are free-tier models, each from the same family as one repairer; judge prompts are unchanged from round 1 (rubric v1 wording).", ""]
    with open(os.path.join(OUT, "results_round2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


write_md()

print(f"{'model|method':30s} {'n':>4s} {'pass':>5s} {'judged':>6s} {'fixed':>6s} {'false pass (rate, 95% CI)':>34s}")
for k, v in main.items():
    print(f"{k:30s} {v['n']:4d} {v['checker_pass']:5d} {v['judged']:6d} {v['judge_fixed']:6d} "
          f"{v['false_pass']:4d}/{v['checker_pass_judged']:<4d} {str(v['false_pass_rate_ci']):>24s}")
print("\ncontent shrink among checker passes:", {k: f"{v['checker_pass_content_shrink']}/{v['checker_pass']}" for k, v in main.items()
                                                 if k.endswith("accessguru_final")})
print("\nsemantic:", json.dumps(semantic, indent=1))
print("\nsemantic, our axe vs the paper's manual verdict:", json.dumps(semantic_axe_vs_paper, indent=1))
print("\nhuman sample, judges alone ($0 plan):", json.dumps(judges_alone, indent=1))
print("\nhuman sample ($0 plan):", json.dumps(human, indent=1) if human else "no step2/human_labels.csv yet")
print("\nROUND 2 plan check:", json.dumps(r2_plan))
print("\nROUND 2 judges alone:", json.dumps(r2_alone, indent=1) if r2_alone else "no round-2 sample yet")
print("\nROUND 2 human sample:", json.dumps(r2_human, indent=1) if r2_human else "no step2r2/human_labels_r2.csv yet")
print("\nround 1 vs round 2:", json.dumps(round_cmp, indent=1))
print("\ncombined round 1 + round 2 (SECONDARY):", json.dumps(combined, indent=1) if combined else "not yet")
print("\nwrote step3/results.json, step3/main_joined.csv, step3/results_round2.md")
