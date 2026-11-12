"""Recompute the headline numbers from the released CSV files and compare them with the released results.

Standard library only. Run it from the repository root:
    python scripts/verify_release.py

What it checks
- Round 2 (main): the pooled false-pass rate (44/120) and the rate for each model, from
  data/round2_main/human_labels_r2.csv, against results/results.json (key human_sample_round2).
- Round 2: the consensus column is rebuilt from the two labellers' own files and the adjudication file.
- Round 2: binary Cohen's kappa between A2 and B2 before adjudication (0.928), from the labellers' own files.
- Round 3 (local models): the pooled false-pass rate (15/60), the per-model counts and kappa A3-B3 (0.822),
  against results/results_round3.json. Round 3 is not in results.json; it has its own results file.
- Round 1 (pilot): kappa A-B (0.105) and the pooled consensus rate (41/120), against results/results.json.
- The SHA-256 of each frozen sample file appears in its frozen plan.

It prints PASS or FAIL for every number and exits with status 1 if anything fails.
"""
import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def path(*parts):
    return os.path.join(ROOT, *parts)


def rows(*parts):
    with open(path(*parts), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(*parts):
    with open(path(*parts), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def kappa(pairs):
    """Cohen's kappa, written the same way as kappa() in scripts/step3_analyze.py."""
    n = len(pairs)
    if not n:
        return None
    labels = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def check(name, computed, *expected):
    ok = all(computed == e for e in expected)
    shown = " = ".join(repr(e) for e in expected)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: computed {computed!r}; expected {shown}")
    if not ok:
        FAILS.append(name)


def binary_pairs(a_rows, b_rows):
    a = {r["item_id"]: r["human_verdict"] for r in a_rows}
    b = {r["item_id"]: r["human_verdict"] for r in b_rows}
    if set(a) != set(b):
        FAILS.append("labeller files cover different items")
    ok = ("fixed", "not_fixed")
    return [(a[i], b[i]) for i in sorted(a) if a[i] in ok and b.get(i) in ok], a, b


def rebuilt_consensus(merged, a, b, adj_rows):
    adj = {r["item_id"]: r["final_verdict"] for r in adj_rows}
    bad = 0
    for r in merged:
        i = r["item_id"]
        expect = a[i] if a[i] == b[i] else adj.get(i, "")
        bad += (r["consensus"] != expect) + (r["label_A"] != a[i]) + (r["label_B"] != b[i])
    return bad


def rate(items):
    dec = [r for r in items if r["consensus"] in ("fixed", "not_fixed")]
    nf = sum(r["consensus"] == "not_fixed" for r in dec)
    return nf, len(dec), round(nf / len(dec), 3) if dec else None


def main():
    res = json.load(open(path("results", "results.json"), encoding="utf-8"))
    res3 = json.load(open(path("results", "results_round3.json"), encoding="utf-8"))

    print("== Round 2 (main), data/round2_main/ vs results/results.json")
    r2 = res["human_sample_round2"]
    fp = r2["false_pass_rate_human_consensus"]
    merged = rows("data", "round2_main", "human_labels_r2.csv")
    nf, n, est = rate(merged)
    check("round 2 pooled not_fixed / decided", f"{nf}/{n}", "44/120",
          f"{sum(fp[m]['consensus_not_fixed'] for m in ('GPT4', 'Mistral', 'Qwen'))}/"
          f"{sum(fp[m]['consensus_not_fixed'] + fp[m]['consensus_fixed'] for m in ('GPT4', 'Mistral', 'Qwen'))}")
    check("round 2 pooled false-pass rate", est, fp["pooled"]["estimate"])
    for m in ("GPT4", "Mistral", "Qwen"):
        nf, n, est = rate([r for r in merged if r["model"] == m])
        check(f"round 2 {m} not_fixed / decided", f"{nf}/{n}",
              f"{fp[m]['consensus_not_fixed']}/{fp[m]['consensus_not_fixed'] + fp[m]['consensus_fixed']}")
        check(f"round 2 {m} false-pass rate", est, fp[m]["estimate"])
    pairs, a, b = binary_pairs(rows("data", "round2_main", "human_labels_A2.csv"),
                               rows("data", "round2_main", "human_labels_B2.csv"))
    check("round 2 kappa A2-B2 (binary, before adjudication)", kappa(pairs), 0.928, r2["inter_rater"]["kappa_binary"])
    check("round 2 items both decided", len(pairs), r2["inter_rater"]["both_decided"])
    check("round 2 merged file matches labeller files + adjudication (mismatches)",
          rebuilt_consensus(merged, a, b, rows("data", "round2_main", "adjudication_r2.csv")), 0)

    print("\n== Round 3 (local models), data/round3_local_models/ vs results/results_round3.json")
    merged3 = rows("data", "round3_local_models", "human_labels_r3.csv")
    p3 = res3["primary_pooled_false_pass"]
    nf, n, est = rate(merged3)
    check("round 3 pooled not_fixed / decided", f"{nf}/{n}", "15/60", f"{p3['not_fixed']}/{p3['decided']}")
    check("round 3 pooled false-pass rate", est, p3["estimate"])
    for m, c in res3["per_model_counts_descriptive"].items():
        got = sum(r["model"] == m and r["consensus"] == "not_fixed" for r in merged3)
        items = sum(r["model"] == m for r in merged3)
        check(f"round 3 {m} not_fixed / items", f"{got}/{items}", f"{c['not_fixed']}/{c['items']}")
    pairs3, a3, b3 = binary_pairs(rows("data", "round3_local_models", "human_labels_A3.csv"),
                                  rows("data", "round3_local_models", "human_labels_B3.csv"))
    check("round 3 kappa A3-B3 (binary, before adjudication)", kappa(pairs3), 0.822,
          res3["kappa_before_adjudication"]["binary"])
    check("round 3 merged file matches labeller files + adjudication (mismatches)",
          rebuilt_consensus(merged3, a3, b3, rows("data", "round3_local_models", "adjudication_r3.csv")), 0)

    print("\n== Round 1 (pilot), data/round1_pilot/ vs results/results.json")
    r1 = res["human_sample_0usd"]
    merged1 = rows("data", "round1_pilot", "human_labels.csv")
    ok = ("fixed", "not_fixed")
    pairs1 = [(r["label_A"], r["label_B"]) for r in merged1 if r["label_A"] in ok and r["label_B"] in ok]
    check("round 1 kappa A-B (binary, unclear excluded)", kappa(pairs1), 0.105, r1["inter_rater"]["kappa_binary"])
    nf, n, est = rate(merged1)
    check("round 1 pooled not_fixed / decided", f"{nf}/{n}", "41/120")
    check("round 1 pooled false-pass rate", est, r1["false_pass_rate_human_consensus"]["pooled"]["estimate"])

    print("\n== Frozen sample hashes")
    plan2 = open(path("plans", "PLAN_round2.md"), encoding="utf-8").read()
    plan3 = open(path("plans", "PLAN_round3.md"), encoding="utf-8").read()
    for name, h, plan in (
            ("data/round2_main/sample_round2.csv", sha256("data", "round2_main", "sample_round2.csv"), plan2),
            ("data/round2_main/labeling_key_r2.csv", sha256("data", "round2_main", "labeling_key_r2.csv"), plan2),
            ("data/round3_local_models/sample_round3.csv", sha256("data", "round3_local_models", "sample_round3.csv"), plan3),
            ("data/round3_local_models/labeling_key_r3.csv", sha256("data", "round3_local_models", "labeling_key_r3.csv"), plan3)):
        check(f"{name} hash is in its frozen plan", h in plan, True)

    print(f"\n{'ALL CHECKS PASSED' if not FAILS else f'{len(FAILS)} CHECK(S) FAILED: ' + '; '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
