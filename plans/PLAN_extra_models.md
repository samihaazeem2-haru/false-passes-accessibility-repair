# Plan: extra models on the AccessGuru syntax/layout cases

Frozen 2026-10-31, before any repair was generated. Not changed after generation starts. Any later deviation is
added at the end under "Deviations", with a date, and never edits the text above it.

## Goal

A comparative extension, no human labels. Five more models repair the same 186 syntax/layout cases with the same
input that the published GPT-4 / Mistral / Qwen got in AccessGuru. Then they are scored with the same checker and
the same judge-free signals.

## Cases

- The 186 rows of `artifact/data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv` (Syntax/Layout)
  where `step0/syntax_layout_baseline_axe.csv` has `baseline_detected == True`, as in step1.
- **Case-list SHA-256: `a9262805332d649162c462ebec0a0b7c77807319af8d12c94b1faad58591afa9`**
  (over `row \t id \t rule \t affectedHTMLElement(s) \n` for each case in row order; `case_list_hash()` in
  `scripts/gen_repairs.py`).

## Method reused

- **Published:** all three published models used the same AccessGuru metacognitive prompt: one system message and
  five user turns in one chat (comprehension, preliminary correction with the WCAG guidelines, critical evaluation,
  decision confirmation with `###albidaya###`/`###alnihaya###` markers, confidence). The repair is the turn-4 reply.
  The system message and the five prompts hash identically in `syntax_metacognitive_implementation_{GPT4,Qwen,mistral}.py`.
  The only difference is that Mistral's file also holds an unused variant of turn 5, which does not touch the repair.
  The paper then ran a re-prompting loop ("final") on cases whose `newImpactScore != 0`.
- **Reused here: the first-round prompt only**, copied verbatim from `syntax_metacognitive_implementation_Qwen.py`.
  The guidelines come from the same `mapping_dict_file.json` and `WCAGGuidelines.csv`.
- **The re-prompting loop is not run.** It uses a different, longer prompt and is triggered by the paper's
  `newImpactScore`, which comes from the paper's own evaluation, and it would roughly double the run time. So it is
  not "cheap". The new models are compared with the published **first-round** (`accessguru_first`) results.

## Models (local Ollama 0.40.13, $0, no API key, text-only)

| Model | Ollama tag | Quant |
|---|---|---|
| MiniCPM-V 4.5 (8B) | `openbmb/minicpm-v4.5:8b` | Q4_K_M |
| Qwen3.5 4B | `qwen3.5:4b` | Q4_K_M |
| InternVL3.5 2B | `hf.co/bartowski/OpenGVLab_InternVL3_5-2B-GGUF:Q4_K_M` | Q4_K_M |
| SmolVLM2 2.2B | `hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M` | Q4_K_M |
| Llama 3.2 Vision 11B | `llama3.2-vision:11b` | Q4_K_M |

Digests and parameter counts are in `hardware_and_models.md`.

## Fixed generation settings (all models)

- temperature 0, seed 20261031, `num_ctx` 32768, `num_predict` (max output tokens per turn) 4096.
- Thinking disabled (`think: false`) where a model has a thinking mode (Qwen3.5), because the published models
  answered directly.
- Text-only: no image is sent. The chat template is each model's own Ollama template.
- `num_ctx` choice: the largest case's prompt is about 16k tokens, and the replies are added to the chat on later
  turns. Every call logs `done_reason` (`length` = output truncated) and whether prompt+output reached `num_ctx`
  (context full: Ollama may then drop the oldest tokens). Both are reported per model, never silently fixed.
- The published models ran on vendor APIs at their default settings (no temperature or max tokens were set), so
  "same settings" means the same values for all five new models, not the same values as the paper.
- One attempt per case. A call error leaves an empty repair, which counts as a failure (`empty`).

## Extraction

- The paper extracted the HTML from the turn-4 reply with a paid `open-mistral-7b` call. Here a free,
  deterministic extractor (`scripts/extract.py`) is used: the last marker block containing HTML, else the last
  fenced code block with HTML, else the markup span, else the reply text (flagged as no-HTML).
- The same extractor is also applied to the published GPT-4 / Mistral / Qwen raw turn-4 replies, which are stored in
  the workbooks (`Decision_Confirmation`, or `MetaCognitive_Response` for Mistral).
- **Primary: the deterministic re-extraction for all eight models**, because then only the model differs.
  The published extraction is reported next to it as a secondary column.

## Scoring (same rules as the published models)

Copied into `scripts/score.py` from `step1_checker_on_paper_outputs.py` and `step3_analyze.py`. The originals are
not edited. axe-core 4.4.1 (`vendor/axe-core-4.4.1.min.js`), the 93-tag runOnly list parsed from the paper's
`syntax_layout_evaluation.py`, the fragment loaded with `set_content`, and the same alias list.

- **Primary outcomes**, per model, each a count out of 186 with a 95% Wilson CI:
  1. checker pass (the reply is not empty and the target rule or an accepted alias no longer fires)
  2. empty reply
  3. no HTML tag or placeholder text
  4. new violation (a rule fires that did not fire on the original page)
  5. content shrink (`len_ratio < 0.5` or < 80% of the original's elements kept; thresholds unchanged)
- Also reported: outcomes 3-5 among checker passes (the paper's convention).
- Replication check: the published texts re-scored with the copied script must match step1/step3 exactly.

## Exclusion rules

- No case is excluded. A case with a call error, an empty reply, a truncated output or a full context stays in the
  denominator (186) and is reported in the generation table.
- If a model cannot load or run at all on this PC, it is reported as failed with the reason. It is not swapped for
  another size without asking.

## Run order

1. Pilot: the first 5 cases for each model. Show the outputs and a time estimate, then wait for "go".
2. Full run of all 186 cases per model (resumable; the pilot cases are reused because the settings are unchanged).
3. Score, summarise, zip, and scan the zip for key-like strings.

## Deviations

### 2026-10-31, after the pilot (5 cases per model), before the full run. Approved by the user ("go").

1. **Llama 3.2 Vision 11B replaced by `llama3.2:3b` (text, Q4_K_M).** Ollama 0.40.13 cannot load the
   `mllama` architecture ("unknown model architecture: 'mllama'"), so all 5 pilot calls failed. This is the
   fallback named in the task ("else 3B text"). The failed pilot record is kept in
   `logs/pilot_llama32_vision_11b_failed.jsonl`.
2. **One retry for runtime errors.** A case whose call fails with a runtime error (HTTP 5xx, CUDA error, server crash,
   connection error) is rerun once from turn 1, and the retry is logged (`retried`, `first_error`). Errors that come
   from the request itself, such as HTTP 400 "exceeds the available context size", are not retried and count as
   failures. The pilot case MiniCPM-V row 1 (CUDA error at turn 4) is rerun under this rule.
3. **`<think>` blocks are removed before extraction.** InternVL3.5 sometimes writes its reasoning in
   `<think>...</think>` (an unclosed `<think>` is removed to the end of the reply). The rule applies to every model
   and changes nothing for the published replies. Scoring re-extracts from the stored raw turn-4 reply, so pilot
   records are treated the same way.
4. **SmolVLM2 context limit (no change of rule, only noted).** Ollama caps SmolVLM2 at its native 8,192 tokens.
   Requests above that are rejected (HTTP 400) and count as failed (empty) repairs, which are reported.
