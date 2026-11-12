# Changes and provenance

This repository was assembled on 12 November 2026 from the study's working folder. Every file below was copied, not moved; the working files were not changed. Source paths are relative to the working folder that holds `experiment/`.

## Files changed for privacy (the copy only)

| File | What was replaced | SHA-256 of the source | SHA-256 of the copy |
|---|---|---|---|
| `paper/paper.tex` (from `paper.tex`) | the labellers' names (and the reminder to confirm them) replaced by a neutral sentence | `32ef599bfcaca5bc51bfd985c00bae3ca7069079623212fa6392408a916ecdeb` | `61ff3494790a9936cf6bfc63f0a42c51ba21e8d11e6bc1aec15509130adafabb` |
| `docs/HANDOFF.md` (from `experiment/HANDOFF.md`) | two absolute paths containing the username replaced by `<path-to-Data-folder>`; two paths into a personal download folder replaced by `<folder-with-returned-labels>`; two mentions of that download folder reworded | `7c614c8bae45196db84b6d3a2ee508592537f724d1707ebe49dd671da8f8029d` | `1a421707872284e0afb2fbc62fd4d2295bb5d3798cb59c3709e870076eb81868` |

No script, CSV or JSON file contained a username, an absolute path, a key or a labeller's name, so none of them was changed. The word "downloads" still appears in three scripts, where it describes a browser download ("the CSV downloads as ..."), and in one model reply ("downloads an app"); neither is a folder.

## Files skipped because they are larger than 20 MB

None. The largest file is `data/local_model_repairs/Qwen3.5-4B.jsonl` (7,734,278 bytes).

## Copied files

| File in this repository | Source in the working folder | Byte-identical |
|---|---|---|
| `paper/paper.tex` | `paper.tex` | **no** (see above) |
| `paper/references.bib` | `references.bib` | yes |
| `data/round1_pilot/labeling_key.csv` | `experiment/release/data/labeling_key.csv` | yes |
| `data/round1_pilot/human_labels.csv` | `experiment/release/data/human_labels.csv` | yes |
| `data/round1_pilot/adjudication.csv` | `experiment/release/data/adjudication.csv` | yes |
| `data/round2_main/sample_round2.csv` | `experiment/release/data/sample_round2.csv` | yes |
| `data/round2_main/labeling_key_r2.csv` | `experiment/release/data/labeling_key_r2.csv` | yes |
| `data/round2_main/human_labels_A2.csv` | `experiment/release/data/human_labels_A2.csv` | yes |
| `data/round2_main/human_labels_B2.csv` | `experiment/release/data/human_labels_B2.csv` | yes |
| `data/round2_main/adjudication_r2.csv` | `experiment/release/data/adjudication_r2.csv` | yes |
| `data/round2_main/human_labels_r2.csv` | `experiment/release/data/human_labels_r2.csv` | yes |
| `data/round3_local_models/sample_round3.csv` | `experiment/extra_models/round3/sample_round3.csv` | yes |
| `data/round3_local_models/labeling_key_r3.csv` | `experiment/extra_models/round3/labeling_key_r3.csv` | yes |
| `data/round3_local_models/human_labels_A3.csv` | `experiment/extra_models/round3/human_labels_A3.csv` | yes |
| `data/round3_local_models/human_labels_B3.csv` | `experiment/extra_models/round3/human_labels_B3.csv` | yes |
| `data/round3_local_models/adjudication_r3.csv` | `experiment/extra_models/round3/adjudication_r3.csv` | yes |
| `data/round3_local_models/human_labels_r3.csv` | `experiment/extra_models/round3/human_labels_r3.csv` | yes |
| `data/local_model_repairs/MiniCPM-V-4.5.jsonl` | `experiment/extra_models/repairs/MiniCPM-V-4.5.jsonl` | yes |
| `data/local_model_repairs/Qwen3.5-4B.jsonl` | `experiment/extra_models/repairs/Qwen3.5-4B.jsonl` | yes |
| `data/local_model_repairs/InternVL3.5-2B.jsonl` | `experiment/extra_models/repairs/InternVL3.5-2B.jsonl` | yes |
| `data/local_model_repairs/SmolVLM2-2.2B.jsonl` | `experiment/extra_models/repairs/SmolVLM2-2.2B.jsonl` | yes |
| `data/local_model_repairs/Llama-3.2-3B.jsonl` | `experiment/extra_models/repairs/Llama-3.2-3B.jsonl` | yes |
| `data/local_model_repairs/checker_results.csv` | `experiment/extra_models/checker_results.csv` | yes |
| `data/extraction_check/final_extraction_rows.csv` | `experiment/extra_models/final_extraction_check/final_extraction_rows.csv` | yes |
| `data/extraction_check/extraction_vs_human.csv` | `experiment/extra_models/extraction_vs_human.csv` | yes |
| `data/extraction_check/extraction_vs_human.json` | `experiment/extra_models/extraction_vs_human.json` | yes |
| `data/extraction_check/extraction_vs_human.md` | `experiment/extra_models/extraction_vs_human.md` | yes |
| `rubric/rubric_v1.md` | `experiment/release/rubric/rubric_v1.md` | yes |
| `rubric/rubric_v2_addendum.md` | `experiment/release/rubric/rubric_v2_addendum.md` | yes |
| `plans/PLAN_round2.md` | `experiment/PLAN_round2.md` | yes |
| `plans/PLAN_round3.md` | `experiment/extra_models/PLAN_round3.md` | yes |
| `plans/PLAN_extra_models.md` | `experiment/extra_models/PLAN_extra_models.md` | yes |
| `scripts/step0_inspect.py` | `experiment/scripts/step0_inspect.py` | yes |
| `scripts/step0b_baseline_axe.py` | `experiment/scripts/step0b_baseline_axe.py` | yes |
| `scripts/step0c_undetected_reasons.py` | `experiment/scripts/step0c_undetected_reasons.py` | yes |
| `scripts/step1_checker_on_paper_outputs.py` | `experiment/scripts/step1_checker_on_paper_outputs.py` | yes |
| `scripts/step1s_semantic_axe.py` | `experiment/scripts/step1s_semantic_axe.py` | yes |
| `scripts/step1s_semantic_items.py` | `experiment/scripts/step1s_semantic_items.py` | yes |
| `scripts/step2_judge.py` | `experiment/scripts/step2_judge.py` | yes |
| `scripts/step2h_labeling.py` | `experiment/scripts/step2h_labeling.py` | yes |
| `scripts/step2h_labeling_r2.py` | `experiment/scripts/step2h_labeling_r2.py` | yes |
| `scripts/step2s_judge_semantic.py` | `experiment/scripts/step2s_judge_semantic.py` | yes |
| `scripts/step3_analyze.py` | `experiment/scripts/step3_analyze.py` | yes |
| `scripts/xlsx_read.py` | `experiment/scripts/xlsx_read.py` | yes |
| `scripts/extra_models/extract.py` | `experiment/extra_models/scripts/extract.py` | yes |
| `scripts/extra_models/extraction_vs_human.py` | `experiment/extra_models/scripts/extraction_vs_human.py` | yes |
| `scripts/extra_models/final_extraction_check.py` | `experiment/extra_models/scripts/final_extraction_check.py` | yes |
| `scripts/extra_models/gen_repairs.py` | `experiment/extra_models/scripts/gen_repairs.py` | yes |
| `scripts/extra_models/round3_labeling.py` | `experiment/extra_models/scripts/round3_labeling.py` | yes |
| `scripts/extra_models/run_all.py` | `experiment/extra_models/scripts/run_all.py` | yes |
| `scripts/extra_models/score.py` | `experiment/extra_models/scripts/score.py` | yes |
| `results/results.json` | `experiment/step3/results.json` | yes |
| `results/results_round2.md` | `experiment/step3/results_round2.md` | yes |
| `results/results_round3.json` | `experiment/extra_models/round3/results_round3.json` | yes |
| `results/results_round3.md` | `experiment/extra_models/round3/results_round3.md` | yes |
| `results/extra_models_summary.md` | `experiment/extra_models/summary.md` | yes |
| `results/extra_models_summary.json` | `experiment/extra_models/summary.json` | yes |
| `results/final_extraction_check_summary.md` | `experiment/extra_models/final_extraction_check/summary.md` | yes |
| `results/final_extraction_check_summary.json` | `experiment/extra_models/final_extraction_check/summary.json` | yes |
| `results/false_pass_by_category.csv` | `experiment/release/false_pass_by_category.csv` | yes |
| `examples/examples_false_pass.md` | `experiment/release/examples_false_pass.md` | yes |
| `docs/HANDOFF.md` | `experiment/HANDOFF.md` | **no** (see above) |
| `docs/hardware_and_models.md` | `experiment/extra_models/hardware_and_models.md` | yes |

## Files written for this repository

These are new. `data/judges/judge_verdicts.csv` was built by `scripts/build_judge_table.py` from the raw judge files `experiment/step2/human_sample_judgments.jsonl` and `experiment/step2r2/human_sample_judgments_r2.jsonl`, which are not released. The README's results tables and data dictionary were generated from `results/results.json`, `results/results_round3.json` and the CSV headers.

- `.gitattributes`
- `.gitignore`
- `CHANGES.md`
- `CITATION.cff`
- `DATA_LICENSE.md`
- `LICENSE`
- `NOTICE.md`
- `README.md`
- `SHA256SUMS`
- `data/judges/judge_verdicts.csv`
- `scripts/build_judge_table.py`
- `scripts/setup_layout.py`
- `scripts/verify_release.py`

## Relation to the earlier release package

The earlier package `experiment/release/` (1 November 2026) holds the same data. This repository adds `scripts/extra_models/extraction_vs_human.py` and its outputs in `data/extraction_check/`, the round-2 report `results/results_round2.md`, the paper source, the working notes `docs/HANDOFF.md` and the judge verdict table, and it arranges the files by round.
