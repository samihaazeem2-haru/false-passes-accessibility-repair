# Extraction check on the published AccessGuru-final repairs

The 186 baseline-detected syntax/layout cases. 'Published' = the paper's own extraction (`filtered_response`, a paid open-mistral-7b call), exactly the texts scored in step1/step3. 'Deterministic' = `scripts/extract.py` applied to the raw reply that produced the final repair: the re-prompt reply (`re-prompt_Decision_Confirmation`) for re-prompted cases, else the first-round turn-4 reply. Same checker and flags. No earlier result is changed; this is a sensitivity check only.

## Raw replies available

| Model | Re-prompted cases (of 186) | Re-prompted, raw reply missing | Not re-prompted, raw reply missing |
|---|---|---|---|
| GPT4 | 40 | 0 | 0 |
| Mistral | 61 | 1 | 0 |
| Qwen | 68 | 0 | 0 |

## All 186 cases (counts out of 186)

| Model | Extraction | Checker pass (95% Wilson CI) | Empty | No HTML or placeholder | New violation | Content shrink |
|---|---|---|---|---|---|---|
| GPT4 | published | 182 (97.8%, 94.6-99.2) | 0 | 26 | 24 | 69 |
| GPT4 | deterministic | 184 (98.9%, 96.2-99.7) | 0 | 22 | 25 | 69 |
| Mistral | published | 169 (90.9%, 85.9-94.2) | 0 | 46 | 28 | 119 |
| Mistral | deterministic | 170 (91.4%, 86.5-94.6) | 1 | 3 | 30 | 99 |
| Qwen | published | 168 (90.3%, 85.2-93.8) | 0 | 38 | 26 | 54 |
| Qwen | deterministic | 162 (87.1%, 81.5-91.2) | 2 | 21 | 30 | 44 |

## Among checker passes

| Model | Extraction | Checker passes | ...no HTML or placeholder | ...new violation | ...content shrink |
|---|---|---|---|---|---|
| GPT4 | published | 182 | 24 | 22 | 67 |
| GPT4 | deterministic | 184 | 22 | 25 | 69 |
| Mistral | published | 169 | 38 | 18 | 108 |
| Mistral | deterministic | 170 | 1 | 25 | 92 |
| Qwen | published | 168 | 38 | 25 | 54 |
| Qwen | deterministic | 162 | 21 | 28 | 43 |

## Re-prompted cases only

| Model | n | Extraction | Checker pass | No HTML or placeholder | New violation | Content shrink |
|---|---|---|---|---|---|---|
| GPT4 | 40 | published | 36 | 11 | 24 | 15 |
| GPT4 | 40 | deterministic | 38 | 9 | 24 | 15 |
| Mistral | 61 | published | 44 | 17 | 28 | 34 |
| Mistral | 61 | deterministic | 48 | 2 | 28 | 23 |
| Qwen | 68 | published | 50 | 4 | 26 | 7 |
| Qwen | 68 | deterministic | 50 | 4 | 26 | 7 |

## How many repair texts differ

| Model | Differ (of 186) | Differ ignoring whitespace | Differ ignoring code fences and whitespace | Re-prompted cases: differ / differ ignoring fences and whitespace | Checker result changed | pass -> not pass | not pass -> pass |
|---|---|---|---|---|---|---|---|
| GPT4 | 172 | 172 | 13 | 37 / 6 | 2 | 0 | 2 |
| Mistral | 52 | 52 | 46 | 16 / 16 | 11 | 5 | 6 |
| Qwen | 129 | 129 | 26 | 53 / 0 | 6 | 6 | 0 |

## Replication check

Published final texts re-scored here vs step1 (`checker_on_paper_outputs.csv`) and step3 (`main_joined.csv`, content shrink): 558 rows, mismatches per field {'checker_pass': 0, 'empty_response': 0, 'flag_placeholder': 0, 'flag_no_html_tag': 0, 'introduced': 0, 'content_shrink': 0, 'paper_case_reprompted': 0}.

## Notes

- The paper's numbers (step1/step3, round 1 and round 2) are unchanged and remain the published-extraction results. The human samples were drawn from the published extraction; this check does not touch them.
- 'Empty' with deterministic extraction can only come from an empty raw reply; such cases count as not passing.
