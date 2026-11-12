# Analysis plan, round 3: five local models (frozen before labelling)

- **Frozen:** 2026-11-01 17:45 Pakistan Standard Time (UTC+05:00). Written after the sample was drawn and before any labelling page existed.
- **Sample file:** `experiment/extra_models/round3/sample_round3.csv`, SHA-256 `ab9ebc0cf12a361fb1f36b13dcc33d7a679d1b88bba6c03b8557a1d4a44af450`. The file holds a SHA-256 of each repair text, so this hash pins the exact 60 items.
- **Hidden key:** `experiment/extra_models/round3/labeling_key_r3.csv`, SHA-256 `285af2feee18d37b5d5ff12c12de13c16dbeaa8e4bcb72d295cea19d6b04bb10`. It holds the model and the truncation flags. The labellers never see it.
- **Lock:** `extra_models/scripts/round3_labeling.py pages` refuses to build the pages unless this file contains the sample hash above, and `analyze` checks it again.
- This plan and the rubric do not change after labelling starts. Any analysis not listed here is reported as exploratory. Nothing from rounds 1 and 2 is changed.

## 1. Why there is a round 3

The extra-model run (`PLAN_extra_models.md`) scored five local models with the checker only. Round 3 asks the same question as round 2 for them: how often is a checker pass not a true fix? It is a small, secondary check (60 items). It is not a model ranking.

## 2. Sample

- **Population:** first-round AccessGuru repairs from the five new models (MiniCPM-V-4.5, Qwen3.5-4B, InternVL3.5-2B, SmolVLM2-2.2B, Llama-3.2-3B) that pass the checker (axe-core 4.4.1) on the 186 baseline-detected syntax/layout cases, using the **deterministic extraction** (`extra_models/checker_results.csv`, `source = new`). The repair text shown is `extract.py` applied to the stored turn-4 reply: the same text the checker scored.
- **Eligible pools:** MiniCPM-V-4.5 155, Qwen3.5-4B 160, InternVL3.5-2B 145, SmolVLM2-2.2B 101, Llama-3.2-3B 145.
- **Draw:** a simple random sample of 12 per model, seed 20261102, in the model order above, then shuffled. Only checker output is read; no judge output exists for these items. The draw gives 60 items on 52 distinct cases (45 Syntax, 15 Layout). Ids are R3-001 to R3-060.
- **No exclusions.** 50 of the 52 cases were also used in round 1 or round 2, with a different model's repair; 58 of the 60 items come from such a case. The labellers may therefore recognise an original fragment. This is reported as a caveat.
- **Truncated replies stay in the sample.** The hidden key flags them: `truncated_any_turn` (any of the five turns hit the output limit; 13 items: SmolVLM2 9, InternVL3.5 3, Qwen3.5 1) and `truncated_turn4` (the turn-4 reply the repair comes from was cut off; 9 items). No context was full. 7 sampled repairs carry the no-HTML or placeholder flag; they stay too.
- **Labellers:** labeller A3 and labeller B3 (codes only; no names are stored). Each works alone on their own page (`labeling_A3.html`, `labeling_B3.html`), in their own random order (seeds 20261103 and 20261104). They do not discuss items until both CSVs are in.
- **Blinding:** the pages show the rule, its description, axe's failure summary, the original fragment and the repair. They show no model name, checker result, flag (truncation, no-HTML, shrink, new violation) or judge output.
- **Rubric:** exactly as in round 2. The v2 addendum is shown first, then rubric v1 unchanged, then all 8 worked examples. The page is built by the round-2 code (`step2h_labeling_r2.py`, imported, not edited). Only the round label, the browser storage key and the file names change.

## 3. Outcomes

**Primary outcome: the pooled false-pass rate.** It is the share of the 60 checker-passing repairs whose consensus is `not_fixed`. The denominator is the items whose consensus is `fixed` or `not_fixed`.
- 95% CI: a cluster bootstrap that resamples cases (dataset rows), 4000 replicates, seed 20261024 (the same as rounds 1 and 2).

**Per model:** counts only (fixed / not_fixed / unclear out of 12), descriptive. With 12 items per model, no per-model rate, CI or test is reported.

**Primary reliability:** binary Cohen's kappa between A3 and B3 **before adjudication**. It uses the items where both said `fixed` or `not_fixed`. Also reported: the 3-label kappa and the A3×B3 confusion table.

**Pre-specified secondary analyses:**
1. **Truncated replies excluded:** the pooled false-pass rate and CI without the `truncated_any_turn` items. The same is also given without the `truncated_turn4` items.
2. A consensus of `unclear` counted as `not_fixed` (sensitivity).

## 4. Exclusion and missing-data rules

These are the same as round 2.
- An item with a missing label has no consensus until it is labelled or adjudicated. It is excluded, and the number excluded is reported.
- Every disagreement goes to adjudication, including one or both labellers saying `unclear`. Both labellers decide together on `adjudication_r3.html`, which saves `adjudication_r3.csv`.
- A consensus of `unclear` is excluded from the primary outcome.
- No item is dropped or replaced after labelling starts, and the sample is not redrawn.

## 5. Interpretation rules, set in advance

- If the binary kappa before adjudication is below 0.6, the false-pass rate is reported with that caveat. The rubric is not changed.
- Round 3 uses first-round repairs from small local models (Q4_K_M, text-only). It is not compared with round 2 as a test, because round 2 used the published AccessGuru-final repairs of other models.

## 6. Steps

```
python -I experiment/extra_models/scripts/round3_labeling.py pages   experiment
python -I experiment/extra_models/scripts/round3_labeling.py verify  experiment
# labellers return human_labels_A3.csv, human_labels_B3.csv -> copy unchanged into experiment/extra_models/round3/
python -I experiment/extra_models/scripts/round3_labeling.py merge   experiment experiment/extra_models/round3/human_labels_A3.csv experiment/extra_models/round3/human_labels_B3.csv
python -I experiment/extra_models/scripts/round3_labeling.py adjpage experiment
# both labellers decide together -> adjudication_r3.csv into experiment/extra_models/round3/, then run merge again
python -I experiment/extra_models/scripts/round3_labeling.py analyze experiment
```
