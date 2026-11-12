# Analysis plan, round 2 (frozen before labelling)

- **Frozen:** 2026-10-24 16:50 Pakistan Standard Time (UTC+05:00). Written after the sample was drawn and before any labelling page existed.
- **Sample file:** `experiment/step2r2/sample_round2.csv`, SHA-256 `350169aa3c4e9817bb7645233c1d19ea578de8a1591a451b5ffe88cc6857d162`. The file holds a SHA-256 of each repair text, so this hash pins the exact 120 items.
- **Hidden key:** `experiment/step2r2/labeling_key_r2.csv`, SHA-256 `c1a5a712b26dd085fafe395efa977ea02d092220add3eef01bb885060ebd97ce`.
- **Lock:** `step2h_labeling_r2.py pages` refuses to build the pages unless this file contains the sample hash above.
- This plan and the rubric (v1 text plus the v2 addendum) **do not change after labelling starts.** Any later analysis not listed here is reported as exploratory.

## 1. Why there is a round 2

Round 1 used rubric v1 on 120 items with labellers A and B. Binary Cohen's kappa between A and B was 0.105 (70 items where both decided). That is too low to trust a consensus. Round 2 uses the same four conditions, made precise by a written v2 addendum and three extra worked examples, on 120 new items. **Round 1 is reported in the paper as a pilot.** Its files are not changed. Its results are kept in `step3/results_round1.json`.

## 2. Sample

- **Population:** AccessGuru-final repairs that pass the paper's checker (axe-core 4.4.1) on the 186 baseline-detected syntax/layout cases.
- **Exclusions:** every case (dataset row) used in round 1 for any model is excluded, and so is every round-1 item. Eligible pool sizes: GPT-4 86 of 182, Mistral 79 of 169, Qwen 76 of 168.
- **Draw:** a simple random sample of 40 per model, seed 20261026. The draw uses only step-1 checker output and no judge output. It gives 120 items on 75 distinct cases (85 Syntax, 35 Layout). Ids are R2-001 to R2-120.
- **Labellers:** labeller A (the author) and labeller B (a classmate). Each works alone, on their own page (`labeling_A2.html`, `labeling_B2.html`), in their own random order (seeds 20261027 and 20261028).
- **Blinding:** the pages show the rule, its description, axe's failure summary, the original fragment and the repair. They show no model name, method, checker result, judge verdict or content-shrink flag. Labellers do not talk about items until both CSVs are in.

## 3. Outcomes

**Primary outcome: the false-pass rate**, per model (GPT-4, Mistral, Qwen) and pooled. It is the share of checker-passing AccessGuru-final repairs whose round-2 consensus is `not_fixed`. The denominator is the items whose consensus is `fixed` or `not_fixed`.
- 95% CI: a cluster bootstrap that resamples cases (dataset rows), 4000 replicates, seed 20261024 (the same as round 1).

**Primary reliability:** binary Cohen's kappa between A and B **before adjudication**. It uses the items where both said `fixed` or `not_fixed`; `unclear` is excluded.

**Secondary outcomes (all pre-specified):**
1. The 3-label kappa between A and B before adjudication, and the A×B confusion table.
2. Each labeller's own false-pass rate, per model and pooled, computed two ways: `unclear` excluded, and `unclear` counted as `not_fixed`.
3. The sensitivity of the primary outcome when a consensus of `unclear` counts as `not_fixed`.
4. Pairwise model differences in the false-pass rate (GPT-4−Mistral, GPT-4−Qwen, Mistral−Qwen), with cluster-bootstrap CIs.
5. **True-fix estimate over the 186 cases:** checker pass rate × (1 − false-pass rate), per model, with a bootstrap CI. The pass rate is treated as fixed: 182, 169 and 168 out of 186.
6. **Content-shrink flag vs the human consensus:** precision, how many unflagged items humans call not fixed, and kappa. The thresholds were fixed before round 1 (0.5 length, 0.8 elements kept) and are not changed.
7. **Free Groq judges** (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) on the 120 round-2 items:
   - each judge vs the consensus (agreement, kappa), overall and on out-of-family items only;
   - judge vs judge.

   The judges use the same prompt as in round 1, so round 1 and round 2 can be compared. Judge output is never shown on a labelling page. The judges are run after the sample is frozen and before any human labels are merged.
8. **Round 1 vs round 2 table:** kappa, consensus false-pass rate, per-labeller false-pass rates, and judge-vs-human kappa.
9. **Combined round 1 + round 2 estimate** (240 items, 173 cases, cluster bootstrap by case). It is labelled **secondary** because the rubric differed between rounds.

## 4. Exclusion and missing-data rules

- An item missing a label from either labeller has no consensus until it is labelled or adjudicated. It is excluded from the false-pass rate and from kappa, and the number excluded is reported.
- Items where A and B disagree go to adjudication. Disagreement includes one labeller saying `unclear`, or both saying `unclear`. Both labellers discuss each one and fill `final_verdict` (`fixed`, `not_fixed` or `unclear`) in `step2r2/adjudication_r2.csv`. Round-1 adjudication is never reused.
- A consensus of `unclear` is excluded from the primary outcome (sensitivity analysis 3 counts it as `not_fixed`).
- Items a judge could not process (`skipped_too_large`, `judge_error`) are excluded from that judge's agreement only. They are listed by id. Humans label all 120.
- No item is dropped or replaced after labelling starts. The sample is not redrawn.

## 5. Interpretation rules, set in advance

- If the binary kappa before adjudication is below 0.6, the consensus false-pass rate is reported with that caveat. The rubric is still not changed after the fact.
- A free judge is called a possible substitute for humans only if its kappa vs the consensus is at least 0.7.
- The round-2 estimate is the primary estimate. Round 1 is the pilot. The combined estimate is secondary.
