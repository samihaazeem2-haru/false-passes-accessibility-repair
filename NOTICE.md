# Third-party notices

This repository builds on the work and software below. Only the items marked "included" are redistributed here.

## AccessGuru (dataset and code)

- **Authors:** Nadeen Fathallah, Daniel Hernández and Steffen Staab.
- **Paper:** "AccessGuru: Leveraging LLMs to Detect and Correct Web Accessibility Violations in HTML Code",
  Proc. 27th Int. ACM SIGACCESS Conference on Computers and Accessibility (ASSETS), 2025,
  https://doi.org/10.1145/3663547.3746360
- **Repository:** https://github.com/NadeenAhmad/AccessGuruLLM, pinned at commit
  `bf45666aa281af7cca23aaabd9bfe3bd802b9036`.
- **Dataset licence:** Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/ . The repository README states this licence for the dataset.
- **Code licence:** MIT ("MIT License, Copyright (c) 2025 Nadeen Fathallah", from the repository's `LICENSE.txt`).
  The repository README's file tree labels `LICENSE.txt` as CC BY 4.0, but the file itself is the MIT licence.
- **What is included here:**
  - case references (dataset row, web-page id, rule id, category);
  - SHA-256 hashes of the published repair texts, but not the texts themselves;
  - trimmed excerpts of five original fragments and repairs in `examples/examples_false_pass.md`, with attribution;
  - replies from five local models in `data/local_model_repairs/*.jsonl`, which often quote the AccessGuru fragments
    that were given to them.

  The AccessGuru repository itself is **not included**; clone it at the commit above.
- **Prompts:** the first-round AccessGuru prompt was reused verbatim from the AccessGuru code (MIT) to generate the
  local-model repairs; see `plans/PLAN_extra_models.md`.

If you use anything derived from the AccessGuru dataset, please cite Fathallah et al. (2025) as above.

## axe-core 4.4.1

- **Author:** Deque Systems, Inc. ("Copyright (c) 2022 Deque Systems, Inc.", from the file header).
- **Licence:** Mozilla Public License 2.0 (MPL-2.0), http://mozilla.org/MPL/2.0/
- **Not included.** Download it yourself:
  `https://cdn.jsdelivr.net/npm/axe-core@4.4.1/axe.min.js`, saved as `axe-core-4.4.1.min.js`.
  SHA-256 of the file used in this study:
  `8466af7fff96c20227760135ab82e3c2d4a5c8726311d910ab58a295451a7c2f`.

## Playwright and Chromium

The checker runs axe-core in Chromium 129.0.6668.29 through Playwright 1.47.0 for Python. Neither is included;
`pip` and `playwright install` fetch them.

## The five local models

The models ran locally in Ollama 0.40.13, quantised to Q4_K_M and used for text only. **No model weights are
included.** Only their replies are included, in `data/local_model_repairs/`. The tags and digests come from
`docs/hardware_and_models.md`. The licences come from the licence layer of each Ollama model or from the
`general.license` field in its GGUF metadata, both read from the downloaded model files.

| Model | Ollama tag | Digest (sha256) | Licence |
|---|---|---|---|
| MiniCPM-V 4.5 | `openbmb/minicpm-v4.5:8b` | `2acb76d2089b7ff1d3a4c306fbe028438ff68e853a6cff786456046b94375334` | Not recorded in the downloaded Ollama files (no licence layer, no `general.license` field). See the model card at https://huggingface.co/openbmb/MiniCPM-V-4_5 before reuse. |
| Qwen3.5 4B | `qwen3.5:4b` | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` | Apache License 2.0 (Ollama licence layer; GGUF `general.license` = `apache-2.0`, link https://huggingface.co/Qwen/Qwen3.5-4B/blob/main/LICENSE) |
| InternVL3.5 2B | `hf.co/bartowski/OpenGVLab_InternVL3_5-2B-GGUF:Q4_K_M` | `5f190201c5de77b1980eb1f03d2e144ebd9b8380a70b5c45d8ed0db1eef78f75` | Apache License 2.0 (GGUF `general.license` = `apache-2.0`) |
| SmolVLM2 2.2B | `hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M` | `19c7714a4edfdd47694dfdbfa38dd56026b95452423b5900b483ac84c355183a` | Apache License 2.0 (GGUF `general.license` = `apache-2.0`) |
| Llama 3.2 3B | `llama3.2:3b` | `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | Llama 3.2 Community License Agreement and the Llama 3.2 Acceptable Use Policy (both shipped as Ollama licence layers) |

Llama 3.2 Vision 11B (`llama3.2-vision:11b`, digest
`6f2f9757ae97e8a3f8ea33d6adb2b11d93d9a35bef277cd2c0b1b5af8e8d0b1e`) was tried in the pilot but failed to load
in Ollama 0.40.13 and produced no repairs. The 3B text model was used instead.

## LLM judges

Two free-tier models on Groq, `openai/gpt-oss-120b` and `qwen/qwen3.8-27b`, were run as judges.
`data/judges/judge_verdicts.csv` keeps only their one-word verdicts; their rationale texts are not included.
