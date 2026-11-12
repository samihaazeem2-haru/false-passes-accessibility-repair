# False Passes in LLM-Based Web Accessibility Repair: A Human-Validated Audit

Data, code and results for the paper by **Samiha Azeem and Toshiba Nayyab**, Department of Computer Science,
Forman Christian College (A Chartered University), Lahore, Pakistan.

## Abstract

LLM tools that repair web accessibility problems are usually scored by running an automated checker again and
counting the violations that disappear. We asked how often a repair that passes this check is still not a real
fix. We took the repairs that the AccessGuru study published for GPT-4, Mistral and Qwen on the 186 syntax and
layout violations that axe-core 4.4.1 detects before repair. Two labellers then judged checker-passing repairs
without seeing the model, the checker result or any tool output. A pilot round with a first rubric gave poor
agreement. After the rubric was clarified, a fresh sample of 120 checker-passing final repairs gave high agreement,
and the labellers judged a large share of those passes as not fixed, with clear differences between models. Simple
signals that need no judge (placeholder text, no HTML, a new violation, lost content) catch part of the problem.
Two free LLM judges did not agree with the labellers well enough to replace them. A smaller third round on
first-round repairs by five local models found false passes there too. We suggest that repair studies report a
false-pass rate next to the checker pass rate.

## What we found

All numbers in this section are read by script from `results/results.json` (rounds 1 and 2) and
`results/results_round3.json` (round 3). `scripts/verify_release.py` recomputes the main ones from the CSV files.

**Round 2 (main result).** AccessGuru-final repairs that pass the checker, 40 sampled per model. The false-pass rate
is the share of checker passes that the labellers' consensus calls `not_fixed`. The true-fix estimate is the
checker pass rate times one minus the false-pass rate. The 95% confidence intervals come from a cluster bootstrap
that resamples cases (4,000 replicates, seed 20261024).

| Model | Checker pass, AccessGuru final (of 186) | Consensus not fixed / checker passes labelled | False-pass rate (95% CI) | Estimated true fix over 186 (95% CI) |
|---|---|---|---|---|
| GPT-4 | 182 (97.8%) | 9 / 40 | 22.5% (10.4 to 36.2) | 75.8% (62.5 to 87.7) |
| Mistral | 169 (90.9%) | 22 / 40 | 55.0% (39.5 to 70.3) | 40.9% (27.0 to 54.9) |
| Qwen | 168 (90.3%) | 13 / 40 | 32.5% (18.9 to 47.5) | 61.0% (47.4 to 73.2) |
| Pooled | | 44 / 120 | 36.7% (27.1 to 47.1) | |

- **Agreement before adjudication:** Cohen's kappa 0.928 in round 2 (116 of 120 items agreed), against 0.105 in the round-1 pilot (n = 70 items where both labellers chose fixed or not fixed).
- **Model differences (round 2):** Mistral minus GPT-4 +32.5 points (CI +13.5 to +51.8); Mistral minus Qwen +22.5 (CI +4.4 to +41.2); GPT-4 minus Qwen -10.0 (CI -27.1 to +7.4), which includes zero.
- **Pilot and combined:** the round-1 pilot consensus gave a pooled false-pass rate of 34.2% (CI 26.0 to 42.2); both rounds together give 35.4% (CI 29.2 to 42.1). The combined figure is secondary because the rubric changed.
- **Content-shrink flag (no judge needed):** it fired on 50 of 120 round-2 items; the labellers called 30 of those not fixed, and 14 unflagged items not fixed (kappa 0.407).
- **LLM judges vs the human consensus (round 2):** `openai/gpt-oss-120b` kappa 0.385 (n = 106; 14 items skipped as too large for the free tier); `qwen/qwen3.8-27b` kappa 0.16 (n = 104; 15 items skipped as too large for the free tier). The plan required kappa of at least 0.7 before a judge could stand in for people; neither came close.

**Round 3 (five local models, secondary).** First-round repairs that pass the checker, 12 sampled per model,
60 items on 52 cases. This is a small check, not a model ranking, and it is not tested against round 2: the models
are different and the repairs are first-round rather than final.

| Model | Items | Consensus fixed | Consensus not fixed | Truncated in any turn |
|---|---|---|---|---|
| MiniCPM-V-4.5 | 12 | 9 | 3 | 0 |
| Qwen3.5-4B | 12 | 11 | 1 | 1 |
| InternVL3.5-2B | 12 | 9 | 3 | 3 |
| SmolVLM2-2.2B | 12 | 5 | 7 | 9 |
| Llama-3.2-3B | 12 | 11 | 1 | 0 |
| Pooled | 60 | 45 | 15 | 13 |

- **Pooled false-pass rate:** 15 / 60 = 25.0% (95% CI 14.3 to 36.1; cluster bootstrap over 52 cases).
- **Agreement before adjudication:** Cohen's kappa 0.822 (56 of 60 items agreed).
- **Truncated replies excluded:** 8 / 47 = 17.0% (CI 7.0 to 28.3) without items truncated in any turn; 9 / 51 = 17.6% (CI 7.8 to 28.0) without items whose turn-4 reply was truncated.
- Per-model counts are descriptive only; 12 items per model are too few for per-model rates.

**Extraction check.** The published AccessGuru pipeline used an extra LLM call to cut the HTML out of each reply.
For 16 of the 120 round-2 items, a deterministic extractor gives a different text, and the labellers called all 16
`not_fixed`. On the other 104 items the false-pass rate is 26.9% (28/104). So part of the round-2 rate comes from the
published extraction step, not from the repair model. Details: `data/extraction_check/extraction_vs_human.md`.

## Folder map

```
README.md              this file
LICENSE                MIT licence for the code
DATA_LICENSE.md        CC BY 4.0 for our labels, annotations and derived tables
NOTICE.md              third-party attribution (AccessGuru, axe-core, the five local models)
CITATION.cff           how to cite
CHANGES.md             where every file came from, and the files changed for privacy
SHA256SUMS             SHA-256 of every file in the repository
.gitignore             keeps keys, environments, model files and caches out of git
.gitattributes         stops git from changing line endings, so the checksums still match after a clone
paper/                 paper.tex and references.bib (draft of 27 October 2026; see the note below)
data/
  round1_pilot/        round 1: hidden key, both labels and consensus, adjudicated disagreements
  round2_main/         round 2: frozen sample, hidden key, each labeller's own file, adjudication, merged consensus
  round3_local_models/ round 3: the same files for the five local models
  local_model_repairs/ the five local models' repairs with all five raw replies (.jsonl), and checker_results.csv
  extraction_check/    published vs deterministic extraction, and its comparison with the round-2 labels
  judges/              the two LLM judges' verdicts (one word per item; no rationale text)
rubric/                rubric v1 and the v2 addendum, each with its worked examples
plans/                 the frozen plans: PLAN_round2.md, PLAN_round3.md, PLAN_extra_models.md
scripts/               all analysis scripts; scripts/extra_models/ holds the local-model and round-3 scripts
results/               results.json, results_round2.md, results_round3.{json,md}, summaries, false_pass_by_category.csv
examples/              examples_false_pass.md: five round-2 false passes, trimmed, with attribution
docs/                  HANDOFF.md (the working notes up to the end of round 2) and hardware_and_models.md
```

`paper/paper.tex` is the draft of 27 October 2026, copied as it was except for one line (see `CHANGES.md`). It
still uses an earlier working title, does not yet describe round 3 or the extraction check, and contains red
`\fillin{...}` reminders that the authors still have to resolve. No compiled `paper.pdf` was found, so none is
included.

## Data dictionary

Terms used throughout:
- A **case** is one row of the AccessGuru syntax/layout sample file
  (`data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv` in the AccessGuru repository, Syntax and
  Layout rows only, counted from 0). One case is one violation. The bootstrap resamples cases.
- An **item** is one repair of one case by one model, shown to the labellers under a neutral code.
- Labels are `fixed`, `not_fixed` or `unclear`. True/False columns hold the text `True` or `False`.

### `data/round1_pilot/labeling_key.csv`

The hidden key of round 1 (never shown to the labellers). 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `pool_size` | Number of checker-passing AccessGuru-final repairs of this model (182, 169 or 168), the pool the item was drawn from. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |

### `data/round1_pilot/human_labels.csv`

Round 1 merged labels, one row per item. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `label_A` | Labeller A's verdict before adjudication: `fixed`, `not_fixed` or `unclear`. |
| `label_B` | Labeller B's verdict before adjudication: `fixed`, `not_fixed` or `unclear`. |
| `note_A` | Labeller A's optional note; empty for most items. |
| `note_B` | Labeller B's optional note; empty for every item. |
| `adjudicated` | The verdict both labellers agreed on together for a disputed item; empty when they agreed from the start. |
| `consensus` | The final label used in the analysis: the shared label when both labellers agreed, otherwise the adjudicated verdict. |

### `data/round1_pilot/adjudication.csv`

The 84 round-1 items where the labellers differed (including any `unclear`), with the verdict they settled on together. 84 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `label_A` | Labeller A's original verdict. |
| `note_A` | Labeller A's original note. |
| `label_B` | Labeller B's original verdict. |
| `note_B` | Labeller B's original note. |
| `final_verdict` | The verdict both labellers agreed on together. |

### `data/round2_main/sample_round2.csv`

The frozen round-2 sample; its SHA-256 is in `plans/PLAN_round2.md`. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `full_pool_size` | All checker-passing AccessGuru-final repairs of this model (182, 169 or 168). |
| `eligible_pool_size` | The same pool after removing every round-1 case (86, 79 or 76); the item was drawn from it. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `response_sha256` | SHA-256 of the exact published repair text shown to the labellers (UTF-8); the text itself is not released. |

### `data/round2_main/labeling_key_r2.csv`

The hidden key of round 2 (never shown to the labellers); its SHA-256 is in `plans/PLAN_round2.md`. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `pool_size` | The eligible pool the item was drawn from (86, 79 or 76). |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |

### `data/round2_main/human_labels_A2.csv`

Labeller A2's labels exactly as downloaded from their page, in their page's order. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `labeller` | The labeller code, always `A2`. |
| `human_verdict` | The labeller's own verdict before any discussion: `fixed` or `not_fixed`. |
| `note` | The labeller's optional note; empty for every item. |

### `data/round2_main/human_labels_B2.csv`

Labeller B2's labels exactly as downloaded from their page, in their page's order. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `labeller` | The labeller code, always `B2`. |
| `human_verdict` | The labeller's own verdict before any discussion: `fixed` or `not_fixed`. |
| `note` | The labeller's optional note; empty for every item. |

### `data/round2_main/adjudication_r2.csv`

The 4 round-2 disagreements and the verdict the labellers settled on together. 4 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `final_verdict` | The verdict both labellers agreed on together. |
| `notes` | Notes written during adjudication; empty for every item. |

### `data/round2_main/human_labels_r2.csv`

Round 2 merged labels, one row per item; the `consensus` column gives the main result. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `label_A` | Labeller A2's verdict before adjudication. |
| `label_B` | Labeller B2's verdict before adjudication. |
| `note_A` | Labeller A2's note; empty for every item. |
| `note_B` | Labeller B2's note; empty for every item. |
| `adjudicated` | The verdict both labellers agreed on together for a disputed item; empty when they agreed from the start. |
| `consensus` | The final label used in the analysis: the shared label when both labellers agreed, otherwise the adjudicated verdict. |

### `data/round3_local_models/sample_round3.csv`

The frozen round-3 sample; its SHA-256 is in `plans/PLAN_round3.md`. 60 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The local model that wrote the repair (MiniCPM-V-4.5, Qwen3.5-4B, InternVL3.5-2B, SmolVLM2-2.2B or Llama-3.2-3B). |
| `pool_size` | Number of checker-passing first-round repairs of this model, the pool the item was drawn from (155, 160, 145, 101 or 145). |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `truncated_any_turn` | `True` if the model's output hit the 4,096-token limit in any of the five chat turns. |
| `truncated_turn4` | `True` if the turn-4 reply, from which the repair is extracted, was cut off. |
| `context_full_any_turn` | `True` if prompt plus output reached the 32,768-token context in any turn (never the case). |
| `response_sha256` | SHA-256 of the exact repair text shown to the labellers (UTF-8): `extract.py` applied to the stored turn-4 reply. |

### `data/round3_local_models/labeling_key_r3.csv`

The hidden key of round 3 (never shown to the labellers); its SHA-256 is in `plans/PLAN_round3.md`. 60 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The local model that wrote the repair (MiniCPM-V-4.5, Qwen3.5-4B, InternVL3.5-2B, SmolVLM2-2.2B or Llama-3.2-3B). |
| `pool_size` | Number of checker-passing first-round repairs of this model, the pool the item was drawn from. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `truncated_any_turn` | `True` if the model's output hit the 4,096-token limit in any of the five chat turns. |
| `truncated_turn4` | `True` if the turn-4 reply, from which the repair is extracted, was cut off. |
| `context_full_any_turn` | `True` if prompt plus output reached the 32,768-token context in any turn (never the case). |

### `data/round3_local_models/human_labels_A3.csv`

Labeller A3's labels exactly as downloaded from their page. 60 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `labeller` | The labeller code, always `A3`. |
| `human_verdict` | The labeller's own verdict before any discussion: `fixed` or `not_fixed`. |
| `note` | The labeller's optional note; empty for every item. |

### `data/round3_local_models/human_labels_B3.csv`

Labeller B3's labels exactly as downloaded from their page. 60 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `labeller` | The labeller code, always `B3`. |
| `human_verdict` | The labeller's own verdict before any discussion: `fixed` or `not_fixed`. |
| `note` | The labeller's optional note; empty for every item. |

### `data/round3_local_models/adjudication_r3.csv`

The 4 round-3 disagreements and the verdict the labellers settled on together. 4 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `final_verdict` | The verdict both labellers agreed on together. |
| `notes` | Notes written during adjudication; empty for every item. |

### `data/round3_local_models/human_labels_r3.csv`

Round 3 merged labels, one row per item. 60 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The local model that wrote the repair (MiniCPM-V-4.5, Qwen3.5-4B, InternVL3.5-2B, SmolVLM2-2.2B or Llama-3.2-3B). |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `truncated_any_turn` | `True` if the model's output hit the 4,096-token limit in any of the five chat turns. |
| `truncated_turn4` | `True` if the turn-4 reply, from which the repair is extracted, was cut off. |
| `label_A` | Labeller A3's verdict before adjudication. |
| `label_B` | Labeller B3's verdict before adjudication. |
| `note_A` | Labeller A3's note; empty for every item. |
| `note_B` | Labeller B3's note; empty for every item. |
| `adjudicated` | The verdict both labellers agreed on together for a disputed item; empty when they agreed from the start. |
| `consensus` | The final label used in the analysis: the shared label when both labellers agreed, otherwise the adjudicated verdict. |

### `data/local_model_repairs/checker_results.csv`

Checker results for first-round repairs on the 186 cases: the five local models (one extraction) and the three published models (both extractions). 2,046 rows. 2046 data rows.

| Column | Meaning |
|---|---|
| `model` | The repairing model: `GPT4`, `Mistral`, `Qwen` or one of the five local models. |
| `source` | `published` for a reply published by AccessGuru; `new` for a reply generated in this study. |
| `extraction` | `published` for the text AccessGuru extracted (its `filtered_response`); `deterministic` for `extract.py` applied to the raw turn-4 reply. |
| `method` | Always `accessguru_first`: the first-round AccessGuru prompt, without re-prompting. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `empty_response` | `True` if the repair text is empty. |
| `flag_placeholder` | `True` if the repair contains placeholder text (for example "would go here" or `INCOMPLETE_RESPONSE`). |
| `flag_no_html_tag` | `True` if the repair contains no HTML tag at all. |
| `len_ratio` | Length of the repair divided by the length of the original fragment, in characters. |
| `target_fires` | `True` if the target rule or an accepted alias still fires on the repair; empty when the repair is empty or the axe run failed. |
| `checker_pass` | `True` if the repair is not empty and the target rule (or an accepted alias) no longer fires in axe-core 4.4.1; empty when the axe run failed. |
| `introduced` | axe rule ids that fire on the repair but did not fire on the original, joined by a vertical bar; empty if none. |
| `error` | The axe/Playwright error message (first 200 characters) if the run failed; otherwise empty. |
| `elements_orig` | Number of HTML elements in the original fragment. |
| `elements_kept` | Number of those elements still present in the repair (same tag, or same id or class for a re-tagged element). |
| `elements_kept_ratio` | `elements_kept` divided by `elements_orig`. |
| `content_shrink` | `True` if the length ratio is below 0.5 or fewer than 80% of the original's elements are kept; empty for an empty repair. |

### `data/extraction_check/final_extraction_rows.csv`

The published AccessGuru-final repairs of GPT-4, Mistral and Qwen on the 186 cases, scored twice: with the published extraction (`pub_`) and with the deterministic extractor applied to the raw reply (`det_`). 558 data rows.

| Column | Meaning |
|---|---|
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `row` | The case: the row of the AccessGuru syntax/layout sample file (Syntax and Layout rows only, counted from 0). |
| `id` | The AccessGuru dataset's web-page id; several cases can come from the same web page. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `reprompted` | `True` if AccessGuru re-prompted this case, so the final repair comes from the re-prompt reply. |
| `raw_reply_available` | `True` if the raw reply behind the final repair is stored in the AccessGuru workbooks. |
| `text_identical` | `True` if the two extracted texts are byte-identical. |
| `text_identical_ignoring_whitespace` | `True` if the two texts are identical once whitespace is ignored. |
| `text_identical_ignoring_fences_and_whitespace` | `True` if the two texts are identical once Markdown code fences and whitespace are ignored. |
| `pub_empty_response` | Published extraction. `True` if the repair text is empty. |
| `pub_flag_placeholder` | Published extraction. `True` if the repair contains placeholder text (for example "would go here" or `INCOMPLETE_RESPONSE`). |
| `pub_flag_no_html_tag` | Published extraction. `True` if the repair contains no HTML tag at all. |
| `pub_len_ratio` | Published extraction. Length of the repair divided by the length of the original fragment, in characters. |
| `pub_checker_pass` | Published extraction. `True` if the repair is not empty and the target rule (or an accepted alias) no longer fires in axe-core 4.4.1; empty when the axe run failed. |
| `pub_introduced` | Published extraction. axe rule ids that fire on the repair but did not fire on the original, joined by a vertical bar; empty if none. |
| `pub_error` | Published extraction. The axe/Playwright error message (first 200 characters) if the run failed; otherwise empty. |
| `pub_content_shrink` | Published extraction. `True` if the length ratio is below 0.5 or fewer than 80% of the original's elements are kept; empty for an empty repair. |
| `det_empty_response` | Deterministic extraction. `True` if the repair text is empty. |
| `det_flag_placeholder` | Deterministic extraction. `True` if the repair contains placeholder text (for example "would go here" or `INCOMPLETE_RESPONSE`). |
| `det_flag_no_html_tag` | Deterministic extraction. `True` if the repair contains no HTML tag at all. |
| `det_len_ratio` | Deterministic extraction. Length of the repair divided by the length of the original fragment, in characters. |
| `det_checker_pass` | Deterministic extraction. `True` if the repair is not empty and the target rule (or an accepted alias) no longer fires in axe-core 4.4.1; empty when the axe run failed. |
| `det_introduced` | Deterministic extraction. axe rule ids that fire on the repair but did not fire on the original, joined by a vertical bar; empty if none. |
| `det_error` | Deterministic extraction. The axe/Playwright error message (first 200 characters) if the run failed; otherwise empty. |
| `det_content_shrink` | Deterministic extraction. `True` if the length ratio is below 0.5 or fewer than 80% of the original's elements are kept; empty for an empty repair. |

### `data/extraction_check/extraction_vs_human.csv`

The 120 round-2 items joined with the extraction check. 120 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `model` | The model that wrote the published repair: `GPT4`, `Mistral` or `Qwen`. |
| `category` | The AccessGuru violation category, `Syntax` or `Layout`. |
| `rule` | The axe-core rule id of the target violation (for example `image-alt`). |
| `extraction_text` | `same` if the published and deterministic texts are identical once code fences and whitespace are ignored; otherwise `differs`. |
| `consensus` | The round-2 consensus label (from `data/round2_main/human_labels_r2.csv`). |
| `det_checker_pass` | `True` if the deterministic text would also pass the checker. |

### `data/judges/judge_verdicts.csv`

Verdicts of the two free LLM judges on the round-1 (H...) and round-2 (R2-...) items, with the last record kept when a judge was retried. Built by `scripts/build_judge_table.py`; the rationales are not released. 480 data rows.

| Column | Meaning |
|---|---|
| `item_id` | Neutral item code shown to the labellers: H001 to H120 in round 1, R2-001 to R2-120 in round 2, R3-001 to R3-060 in round 3. |
| `judge` | The judge model: `openai/gpt-oss-120b` or `qwen/qwen3.8-27b` (Groq free tier). |
| `verdict` | `fixed`, `not_fixed`, `skipped_too_large` (not sent: too large for the free tier) or `judge_error` (the answer was cut off even after a retry). |
| `skipped` | `yes` if the item was skipped as too large for the free tier; otherwise `no`. |

### `data/local_model_repairs/*.jsonl` (not CSV)

One file per local model, one JSON record per case (186 each). Fields: `model`, the Ollama tag of the model; `slug`, the short model name used in file names; `row`, the case (row of the sample file); `id`, the web-page id; `rule`, the axe rule id; `category`, `Syntax` or `Layout`; `decision_confirmation`, the raw turn-4 reply, from which the repair is extracted; `filtered_response`, the repair: `extract.py` applied to the turn-4 reply at generation time (scoring re-extracts it from `decision_confirmation`); `error`, the call error, if any; otherwise empty; `retried`, `true` if the case was rerun once after a runtime error (missing in the 19 pilot records written before this rule existed); `first_error`, the error that caused the retry (also missing in those 19 records); `truncated_output_any_turn`, `true` if any turn hit the output limit; `context_full_any_turn`, `true` if any turn filled the context; `seconds_total`, generation time for the case; `turns`, the five chat turns, each with `turn`, `prompt_tokens`, `output_tokens`, `seconds`, `done_reason` (`length` means the output was cut off) and `content` (the model's reply).

## How the labels were made

**The labellers.** Every round had two labellers, and they were the same two people in every round. They were
two colleagues of the authors, both lab instructors with a computer science degree and working knowledge of HTML,
CSS and JavaScript; neither is an author; neither is an accessibility specialist; no users with disabilities took
part. In the files they appear only as codes: A and B in round 1, A2 and B2 in round 2, A3 and B3 in round 3.

**What the labellers saw.** Each labeller got their own offline HTML page. For each item it showed the rule id,
the rule's description, axe's failure summary, the original fragment and the proposed repair. It never showed the
model name, the method, the checker result, any judge verdict or any flag. Each page had its own random item order.
The labellers worked alone and blind, and did not discuss items until both had returned their files. A repair
counts as `fixed` only if four conditions hold: it is concrete code, not advice or a placeholder; it keeps the
original content and purpose; it resolves the named violation; and it creates no new barrier.

**Round 1 (pilot, rubric v1).** 120 checker-passing AccessGuru-final repairs, 40 per model (GPT-4, Mistral, Qwen),
seed 20261023, drawn from checker output only before any LLM judge ran. Agreement was poor (binary kappa 0.105).
The disagreements were settled by discussion between the two labellers. Round 1 is reported as a pilot.

**Writing rubric v2.** The authors asked the labellers about the disputed pilot items, wrote clarifications to the
rubric and gave them worked examples showing which label fits which kind of case. The result is the v2 addendum
(`rubric/rubric_v2_addendum.md`), which keeps the four v1 conditions and makes them precise, plus three new worked
examples. Rubric v1 itself was not changed.

**Round 2 (main, rubric v2, fresh sample).** 120 new checker-passing AccessGuru-final repairs, 40 per model,
seed 20261026. Every case used in round 1 was excluded for every model. The pages showed the v2 addendum first,
then rubric v1 unchanged, then all 8 worked examples. The 4 disagreements were settled by discussion between the
two labellers.

**Round 3 (five local models).** 60 checker-passing first-round repairs by five local models, 12 per model,
seed 20261102, with exactly the round-2 rubric and page design. The 4 disagreements were settled by discussion.

**Freezing.** For rounds 2 and 3 the sample was drawn first, its SHA-256 and the SHA-256 of the hidden key were
written into a plan, and the plan was frozen before any labelling page existed (`plans/PLAN_round2.md`,
24 October 2026 16:50 PKT; `plans/PLAN_round3.md`, 1 November 2026 17:45 PKT). The page builders refuse to run,
and the analysis scripts refuse to report, if the sample hash does not match its plan. The sample files store a
SHA-256 of every repair text, so each hash pins the exact items. The plan for the local-model generation
(`plans/PLAN_extra_models.md`) was frozen on 31 October 2026 before any repair was generated; its deviations are
listed at its end. The plans in `plans/` are byte-identical to the frozen files.

## How to rerun everything

Everything below is free. Only the optional LLM-judge step needs a (free) API key, and the repository never
contains one. Commands are for a terminal opened in a new, empty working folder, called `<Data>` here. On Windows,
use `python` from a virtual environment and the same commands work in PowerShell, except where noted.

**1. Recreate the working layout from this repository.**
```
python <repo>/scripts/setup_layout.py <Data>
cd <Data>
```
This copies the scripts, plans and data into `<Data>/experiment/` where the scripts expect them, and writes
minimal judge files (item id, judge, verdict) so that the judge tables can be rebuilt.

**2. Get AccessGuru, the checker and the browser.**
```
git clone https://github.com/NadeenAhmad/AccessGuruLLM.git experiment/artifact
git -C experiment/artifact checkout bf45666aa281af7cca23aaabd9bfe3bd802b9036
python -m venv .venv
```
Activate the environment (`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` in PowerShell), then:
```
python -m pip install playwright==1.47.0
python -m playwright install chromium
curl -L -o experiment/vendor/axe-core-4.4.1.min.js https://cdn.jsdelivr.net/npm/axe-core@4.4.1/axe.min.js
```
Check the download: its SHA-256 must be `8466af7fff96c20227760135ab82e3c2d4a5c8726311d910ab58a295451a7c2f`
(`sha256sum experiment/vendor/axe-core-4.4.1.min.js`, or in PowerShell
`Get-FileHash experiment/vendor/axe-core-4.4.1.min.js`). The original runs used axe-core 4.4.1,
Chromium 129.0.6668.29 and Playwright 1.47.0.

**3. Rebuild the checker results** (no LLM). Run in this order:
```
python -I experiment/scripts/step0_inspect.py experiment/artifact experiment/step0
python -I experiment/scripts/step0b_baseline_axe.py experiment/artifact experiment/step0 experiment/vendor/axe-core-4.4.1.min.js
python -I experiment/scripts/step0c_undetected_reasons.py experiment/step0 experiment/vendor/axe-core-4.4.1.min.js
python -I experiment/scripts/step1_checker_on_paper_outputs.py experiment/artifact experiment/step0 experiment/step1 experiment/vendor/axe-core-4.4.1.min.js
python -I experiment/scripts/step1s_semantic_items.py experiment/artifact experiment/step1
python -I experiment/scripts/step1s_semantic_axe.py experiment/artifact experiment/step1 experiment/vendor/axe-core-4.4.1.min.js
```
Step 0b should report 186 baseline-detected cases (133 Syntax and 53 Layout) and 93 tags. Step 1 should give
AccessGuru-final checker passes of 182 (GPT-4), 169 (Mistral) and 168 (Qwen).

**4. Check the round-2 sample (optional).** In a scratch copy of `<Data>`, because this command overwrites
`step2r2/sample_round2.csv` and `step2r2/labeling_key_r2.csv`:
```
python -I experiment/scripts/step2h_labeling_r2.py sample experiment --force
```
The SHA-256 of the redrawn `sample_round2.csv` must equal the hash in `PLAN_round2.md`.

**5. Rounds 1 and 2: the analysis.**
```
python -I experiment/scripts/step3_analyze.py experiment
```
This writes `experiment/step3/results.json` and `results_round2.md`, after checking that the sample hash matches
the plan. The judge tables are rebuilt from the minimal judge files. We tested this from a clean layout: every
human-label, judge and round-comparison section of `results.json`, and the whole of `results_round2.md`, came out
identical to the released files. The only differences are the judge fields of `main_by_model_method` and
`accessguru_final_false_pass_by_rule`, which come from an early 24-item judge pilot whose outputs are not released;
on a rerun those fields come out empty. No number in the paper uses them.

**6. Local models and round 3.**
```
python -I experiment/extra_models/scripts/score.py experiment
python -I experiment/extra_models/scripts/final_extraction_check.py experiment
python -I experiment/extra_models/scripts/round3_labeling.py analyze experiment
python -I experiment/extra_models/scripts/extraction_vs_human.py
```
`score.py` re-scores the stored repairs. `final_extraction_check.py` reruns the extraction check.
`round3_labeling.py analyze` recomputes the round-3 results from the merged labels, after checking the sample hash
against `PLAN_round3.md`. `extraction_vs_human.py` rebuilds the comparison of extraction and human labels.
Regenerating the repairs themselves (`gen_repairs.py`, `run_all.py`) needs Ollama 0.40.13 and the model digests in
`docs/hardware_and_models.md`; at temperature 0 and a fixed seed the replies should be close, but GPU and driver
differences can change them.

**7. Rebuild the labelling pages (optional).** The pages are not in this repository because they contain the full
AccessGuru fragments and repairs. They are rebuilt from the AccessGuru clone:
```
python -I experiment/scripts/step2h_labeling_r2.py pages experiment
python -I experiment/scripts/step2h_labeling_r2.py verify experiment
python -I experiment/extra_models/scripts/round3_labeling.py pages experiment
python -I experiment/extra_models/scripts/round3_labeling.py verify experiment
```
The adjudication pages are built from the list of disagreements, which the `merge` step writes. Merging the
released labeller files again reproduces the released merged files:
```
python -I experiment/scripts/step2h_labeling_r2.py merge experiment experiment/step2r2/human_labels_A2.csv experiment/step2r2/human_labels_B2.csv
python -I experiment/scripts/step2h_labeling_r2.py adjpage experiment
python -I experiment/extra_models/scripts/round3_labeling.py merge experiment experiment/extra_models/round3/human_labels_A3.csv experiment/extra_models/round3/human_labels_B3.csv
python -I experiment/extra_models/scripts/round3_labeling.py adjpage experiment
```
The round-1 pages are built by `python -I experiment/scripts/step2h_labeling.py make experiment`. That command
also redraws the round-1 sample and rewrites `step2/labeling_key.csv`, so run it only in a scratch copy and compare
the new key with `data/round1_pilot/labeling_key.csv`.

**8. LLM judges (optional, free tier).** Put a `.env` file next to `experiment/` holding `GROQ_API_KEY=...`, then:
```
python -I experiment/scripts/step2_judge.py --provider groq --human-sample --round 2 --model openai/gpt-oss-120b
python -I experiment/scripts/step2_judge.py --provider groq --human-sample --round 2 --model qwen/qwen3.8-27b
```
The script reads the key in-process and never prints or stores it. Never commit the `.env` file. Free-tier models
change without notice, so a rerun may not reproduce the released verdicts.

**Quick check without any of the above.** From the repository root:
```
python scripts/verify_release.py
```
It recomputes the round-2 and round-3 false-pass counts and rates and both kappas from the CSV files, compares them
with `results/`, and checks the frozen sample hashes. It needs only the Python standard library.

## How to verify the checksums

`SHA256SUMS` lists the SHA-256 of every file in the repository except itself. From the repository root:
```
sha256sum -c SHA256SUMS
```
In PowerShell (no `sha256sum`):
```
Get-Content SHA256SUMS | ForEach-Object {
  $h, $f = $_ -split '  ', 2
  if ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -eq $h) { "OK   $f" } else { "FAIL $f" }
}
```
`CHANGES.md` gives, for every copied file, its source in the study's working folder and whether it is
byte-identical to it. The `.gitattributes` file tells git not to convert line endings, so a clone on Windows keeps
the same bytes and the same checksums.

## Not included, and why

- **API keys, `.env` files and tokens.** Never shared. Only the optional judge step needs a key.
- **`.venv`, Python caches and logs.** They are machine-specific and can hold local paths.
- **The local model weights (`ollama_models`, about 21 GB).** Too large, and each has its own licence. Tags and
  digests are in `docs/hardware_and_models.md` and `NOTICE.md`.
- **The AccessGuru repository.** It belongs to its authors. Clone it at commit
  `bf45666aa281af7cca23aaabd9bfe3bd802b9036` (step 2 above).
- **axe-core 4.4.1 (`axe-core-4.4.1.min.js`).** MPL-2.0 and not ours to bundle here. Download it from
  `https://cdn.jsdelivr.net/npm/axe-core@4.4.1/axe.min.js`; SHA-256
  `8466af7fff96c20227760135ab82e3c2d4a5c8726311d910ab58a295451a7c2f`.
- **The labelling and adjudication HTML pages.** They contain the full AccessGuru fragments and repairs. Step 7
  rebuilds them.
- **The raw LLM-judge `.jsonl` files.** Their rationales quote the repair texts. `data/judges/judge_verdicts.csv`
  keeps only item id, judge, verdict and whether the item was skipped.
- **The published AccessGuru repair texts.** Only their SHA-256 hashes (`response_sha256` in the sample files), and
  the trimmed excerpts in `examples/examples_false_pass.md`, are included.
- **The step-0, step-1 and step-3 working outputs.** Steps 3 to 5 regenerate them.
- **The 24 judgments of an early paid judge pilot,** which was dropped when the study moved to a $0 plan. No result
  in the paper depends on them.
- **The intermediate `adjudication_todo` files** written by the merge step. The merge step rewrites them.
- **A compiled `paper.pdf`.** None was found.

## Known inconsistency

PLAN_round2.md, results_round2.md and some analysis text call labeller A 'the author'. That wording is wrong and
the frozen plan was not edited; both labellers were colleagues of the authors, not authors.

(The same wrong caveat line is written by `scripts/step3_analyze.py` into `results_round2.md`, and
`PLAN_round2.md` also calls labeller B "a classmate". Both files are kept byte-identical, because the plan's hash
is part of the record.)

## Limitations

- **First-round prompt only for the local models.** AccessGuru's re-prompting loop was not run for the five local
  models, so their numbers compare with the published first-round results, not with the final ones.
- **4-bit quantisation.** All five local models ran at Q4_K_M, text only, at temperature 0 with a fixed seed. Full
  precision or vendor-hosted versions may behave differently.
- **Llama 3.2 3B instead of 11B.** The planned Llama 3.2 Vision 11B model failed to load in Ollama 0.40.13
  ("unknown model architecture: 'mllama'"), so the Llama 3.2 3B text model was used instead. It is smaller than
  planned and, unlike the other four, a text-only model.
- **SmolVLM2 truncation.** SmolVLM2 2.2B has a native context of 8,192 tokens. Its output was cut off in 92 of
  186 cases, 7 cases failed outright, and 9 of the 13 truncated round-3 items are SmolVLM2's. Its round-3 counts
  partly reflect truncation, which is why round 3 also reports rates with truncated replies excluded.
- **The published pipeline's extraction step.** The round-2 repairs are the texts AccessGuru published, which an
  extra LLM call cut out of each reply. For 16 of 120 round-2 items that step broke the repair, and all 16 were
  judged `not_fixed` (see "What we found").
- **Small samples.** 120 items per main round, 40 per model, and 12 per model in round 3. Per-model intervals are
  wide, and round 3 gives counts only per model.
- **Fragments, not pages.** The checker and the labellers saw HTML fragments, as in AccessGuru. Several cases can
  come from the same web page, and the case bootstrap does not model that.
- **The labellers are not accessibility specialists,** and no users with disabilities took part.
- **Overlap in round 3.** 50 of the 52 round-3 cases also appeared in rounds 1 or 2 with another model's repair,
  so the labellers may have seen those fragments before.
- **Free LLM judges** change without notice, and each shares a developer with one repairer (gpt-oss-120b with
  GPT-4, qwen3.8-27b with Qwen).

## Use of AI tools

AI coding assistants (Claude and Codex) were used as supporting tools to assist with writing and executing analysis scripts, developing the labelling interfaces. The study design, research decisions, interpretation of results, and human-generated labels were the responsibility of the authors and their colleagues.

## Licences

- **Code** (`scripts/`): MIT, see `LICENSE`.
- **Our labels, annotations, rubric texts, plans and derived tables**: CC BY 4.0, see `DATA_LICENSE.md`.
- **Third-party material**: the AccessGuru dataset (CC BY 4.0) and code (MIT) by Fathallah et al., axe-core 4.4.1
  (MPL-2.0, not included) and the five local models (licences listed in `NOTICE.md`).

## How to cite

Please cite the paper and this repository using the details in [`CITATION.cff`](CITATION.cff). On GitHub, the
"Cite this repository" button in the sidebar formats them for you. If you use the AccessGuru data, please also cite
Fathallah et al. (2025), as listed in `NOTICE.md`.
