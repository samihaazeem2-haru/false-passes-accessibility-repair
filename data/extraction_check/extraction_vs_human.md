# Round-2 human verdicts vs. the extraction step

**Summary**
1. For 104 of the 120 round-2 items, the published extraction gives the same text as the deterministic one (ignoring code fences and whitespace). On these items the human false-pass rate is 26.9% (28/104; cluster bootstrap 17.7–37.0%).
2. The other 16 items have different text, and humans marked **all 16** not_fixed (100%; Wilson 80.6–100%). On 12 of them the published text trips the no-HTML/placeholder flag and the deterministic text does not. The published extraction broke these repairs.
3. So part of the 36.7% round-2 rate comes from the extraction step, not from the model. 14 of the 16 would still pass the checker under deterministic extraction, but no human has seen that text, so their verdict is unknown. All five false-pass examples in `release/examples_false_pass.md` have the same text under both extractions.

Script: `extra_models/scripts/extraction_vs_human.py` (read-only on inputs, $0, no API calls, no new labelling). Per-item rows: `extraction_vs_human.csv`. All numbers: `extraction_vs_human.json`.

## Inputs
| File | Path |
|---|---|
| sample_round2.csv | `release/data/sample_round2.csv` (byte-identical copy in `step2r2/`) |
| labeling_key_r2.csv | `release/data/labeling_key_r2.csv` (byte-identical copy in `step2r2/`) |
| human_labels_r2.csv | `release/data/human_labels_r2.csv` (byte-identical copy in `step2r2/`) |
| final_extraction_rows.csv | `extra_models/final_extraction_check/final_extraction_rows.csv` (byte-identical copy in `release/extra_models/final_extraction_check/`) |

## Join
I joined on (model, row) and **120 of 120 items matched**. None were unmatched. For every item, id, category and rule also agree with final_extraction_rows, labeling_key_r2 and sample_round2. All 120 have `pub_checker_pass = True`, as expected for the round-2 pool. Every item has a consensus (fixed or not_fixed), so decided = n throughout.

Cross-check: over all 120 items the script gives 44/120 = 36.7% with a cluster bootstrap of 27.1–47.1%, the same as `release/README.md`.

## False-pass rate by group
Grouping uses `text_identical_ignoring_fences_and_whitespace`. FPR = consensus not_fixed / decided. The Wilson interval treats items as independent. The cluster bootstrap uses 4000 reps, seed 20261024, and resamples dataset rows as clusters within each group.

| Group | Model | n | not_fixed | FPR | 95% Wilson | 95% cluster bootstrap |
|---|---|---|---|---|---|---|
| same text | GPT4 | 37 | 6 | 16.2% | 7.7–31.1 | |
| same text | Mistral | 31 | 13 | 41.9% | 26.4–59.2 | |
| same text | Qwen | 36 | 9 | 25.0% | 13.8–41.1 | |
| same text | **pooled** | 104 | 28 | 26.9% | 19.3–36.2 | 17.7–37.0 (69 clusters) |
| text differs | GPT4 | 3 | 3 | 100% | 43.8–100 | |
| text differs | Mistral | 9 | 9 | 100% | 70.1–100 | |
| text differs | Qwen | 4 | 4 | 100% | 51.0–100 | |
| text differs | **pooled** | 16 | 16 | 100% | 80.6–100 | 100–100 (13 clusters)* |
| all (reference) | pooled | 120 | 44 | 36.7% | 28.6–45.6 | 27.1–47.1 (75 clusters) |

\*Every item in the group is not_fixed, so every bootstrap replicate is also 100%. The interval is degenerate and says nothing beyond the 16/16 count. Use the Wilson interval here.

Extra: the pooled difference (differs − same) is 73.1 points, with a cluster bootstrap of 62.9–82.1 over all 120 items resampled jointly.

## The 16 "text differs" items
| | GPT4 | Mistral | Qwen | Pooled |
|---|---|---|---|---|
| Items | 3 | 9 | 4 | 16 |
| Still pass checker under deterministic extraction (`det_checker_pass`) | 3 | 8 | 3 | **14** |
| Fail checker under deterministic extraction | 0 | 1 | 1 | 2 (R2-074, R2-025) |
| No-HTML/placeholder flag differs between extractions | 1 | 8 | 3 | **12** |
| ...flagged under published only | 1 | 8 | 3 | 12 |
| ...flagged under deterministic only | 0 | 0 | 0 | 0 |
| Re-prompted cases | 1 | 4 | 0 | 5 |

The flag counts "placeholder OR no HTML tag" as one flag. 10 of the 16 are `color-contrast-enhanced`. In all 16 the published text is a tiny fraction of the original (length ratio 0.0–0.07), which points to the extraction having dropped the repair.

Limits:
- Humans judged the **published** text. Nobody has labelled the deterministic text, so this check cannot say whether those 14 checker passes would be real fixes. That would need new labelling, which is out of scope here.
- One bound follows from the data. Under deterministic extraction these 120 items would give 118 checker passes. 104 keep their human verdicts (28 not_fixed), and 14 have unknown verdicts. The false-pass rate on those 118 would therefore be between 28/118 = 23.7% (all 14 fixed) and 42/118 = 35.6% (all 14 not_fixed). This applies only to these sampled items. A full deterministic-extraction pool would contain other checker passes too.

## The five examples in `release/examples_false_pass.md`
| Item | Model | Rule | Published text = deterministic text? | det_checker_pass |
|---|---|---|---|---|
| R2-083 | Mistral | link-name | yes, same | True |
| R2-056 | Qwen | image-alt | yes, same | True |
| R2-117 | Mistral | image-alt | yes, same | True |
| R2-107 | Qwen | region | yes, same | True |
| R2-063 | GPT4 | aria-allowed-role | yes, same | True |

None of the five worked examples depends on the extraction step. (R2-107 has the no-HTML/placeholder flag under both extractions.)
