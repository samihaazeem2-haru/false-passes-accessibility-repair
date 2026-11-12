# Extra models: AccessGuru first-round repairs, checker results

Same 186 syntax/layout cases (axe 4.4.1 detects the target rule before repair), same first-round AccessGuru prompt, same checker (axe-core 4.4.1, 93 tags) and judge-free flags as the published GPT-4 / Mistral / Qwen results. No human labels. Each cell: count (percent, 95% Wilson CI). All percentages are out of all cases.

**Primary comparison:** every model's repair cut out of its turn-4 reply with the same free deterministic extractor (`scripts/extract.py`). The published models' own extraction (a paid Mistral call in the paper) is shown for reference.

| Model | Extraction | Checker pass | Empty | No HTML or placeholder | New violation | Content shrink |
|---|---|---|---|---|---|---|
| GPT4 | published | 174 (93.5%, 89.1-96.3) | 0 (0.0%, 0.0-2.0) | 18 (9.7%, 6.2-14.8) | 29 (15.6%, 11.1-21.5) | 67 (36.0%, 29.5-43.1) |
| GPT4 | deterministic | 175 (94.1%, 89.7-96.7) | 0 (0.0%, 0.0-2.0) | 14 (7.5%, 4.5-12.2) | 30 (16.1%, 11.5-22.1) | 66 (35.5%, 29.0-42.6) |
| Mistral | published | 157 (84.4%, 78.5-88.9) | 0 (0.0%, 0.0-2.0) | 39 (21.0%, 15.7-27.4) | 45 (24.2%, 18.6-30.8) | 125 (67.2%, 60.2-73.5) |
| Mistral | deterministic | 163 (87.6%, 82.1-91.6) | 0 (0.0%, 0.0-2.0) | 2 (1.1%, 0.3-3.8) | 45 (24.2%, 18.6-30.8) | 109 (58.6%, 51.4-65.4) |
| Qwen | published | 155 (83.3%, 77.3-88.0) | 0 (0.0%, 0.0-2.0) | 41 (22.0%, 16.7-28.5) | 46 (24.7%, 19.1-31.4) | 68 (36.6%, 30.0-43.7) |
| Qwen | deterministic | 151 (81.2%, 75.0-86.1) | 2 (1.1%, 0.3-3.8) | 20 (10.8%, 7.1-16.0) | 48 (25.8%, 20.1-32.5) | 54 (29.0%, 23.0-35.9) |
| MiniCPM-V-4.5 | deterministic | 155 (83.3%, 77.3-88.0) | 1 (0.5%, 0.1-3.0) | 16 (8.6%, 5.4-13.5) | 54 (29.0%, 23.0-35.9) | 71 (38.2%, 31.5-45.3) |
| Qwen3.5-4B | deterministic | 160 (86.0%, 80.3-90.3) | 4 (2.2%, 0.8-5.4) | 18 (9.7%, 6.2-14.8) | 60 (32.3%, 26.0-39.3) | 28 (15.1%, 10.6-20.9) |
| InternVL3.5-2B | deterministic | 145 (78.0%, 71.5-83.3) | 2 (1.1%, 0.3-3.8) | 5 (2.7%, 1.2-6.1) | 51 (27.4%, 21.5-34.2) | 52 (28.0%, 22.0-34.8) |
| SmolVLM2-2.2B | deterministic | 101 (54.3%, 47.1-61.3) | 7 (3.8%, 1.8-7.6) | 28 (15.1%, 10.6-20.9) | 38 (20.4%, 15.3-26.8) | 85 (45.7%, 38.7-52.9) |
| Llama-3.2-3B | deterministic | 145 (78.0%, 71.5-83.3) | 0 (0.0%, 0.0-2.0) | 1 (0.5%, 0.1-3.0) | 61 (32.8%, 26.5-39.8) | 45 (24.2%, 18.6-30.8) |

## Among checker passes (the paper's convention)

How many checker passes are still suspicious by a judge-free signal.

| Model | Extraction | Checker passes | ...no HTML or placeholder | ...new violation | ...content shrink |
|---|---|---|---|---|---|
| GPT4 | published | 174 | 17 | 28 | 62 |
| GPT4 | deterministic | 175 | 14 | 29 | 62 |
| Mistral | published | 157 | 31 | 32 | 103 |
| Mistral | deterministic | 163 | 2 | 37 | 94 |
| Qwen | published | 155 | 37 | 37 | 60 |
| Qwen | deterministic | 151 | 19 | 41 | 48 |
| MiniCPM-V-4.5 | deterministic | 155 | 16 | 48 | 64 |
| Qwen3.5-4B | deterministic | 160 | 17 | 56 | 24 |
| InternVL3.5-2B | deterministic | 145 | 5 | 41 | 46 |
| SmolVLM2-2.2B | deterministic | 101 | 22 | 21 | 68 |
| Llama-3.2-3B | deterministic | 145 | 1 | 47 | 37 |

## Generation (local Ollama, $0)

| Model | Cases | Calls | Hours | Output tokens | Cases truncated (output) | Cases context full | Call errors |
|---|---|---|---|---|---|---|---|
| MiniCPM-V-4.5 | 186 | 933 | 3.76 | 771970 | 20 | 0 | 0 |
| Qwen3.5-4B | 186 | 930 | 4.0 | 1428735 | 26 | 0 | 0 |
| InternVL3.5-2B | 186 | 930 | 1.19 | 806702 | 20 | 0 | 0 |
| SmolVLM2-2.2B | 186 | 895 | 1.46 | 886849 | 92 | 0 | 7 |
| Llama-3.2-3B | 186 | 930 | 1.37 | 622962 | 7 | 0 | 0 |

## Replication check

The published texts re-scored with these copied scripts versus the original step1/step3 outputs: 558 rows, mismatches per field {'checker_pass': 0, 'empty_response': 0, 'flag_placeholder': 0, 'flag_no_html_tag': 0, 'introduced': 0, 'content_shrink': 0}.

## Caveats

- First-round prompt only. The paper's re-prompting loop ('final') is not run for the new models, so compare with the published *first-round* numbers, not 'final'.
- Checker pass is not 'truly fixed'; in round 2 humans found many checker passes not fixed. The flags are signals, not verdicts.
- New models run locally at Q4_K_M quantization, text-only, temperature 0, fixed seed; the published models ran on vendor APIs at default settings.
