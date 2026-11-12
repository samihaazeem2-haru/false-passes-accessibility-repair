# Hardware and models

Recorded 2026-10-31.

## Hardware

- RAM: 64 GB (65,310 MB)
- GPU: NVIDIA GeForce RTX 4070, 12 GB VRAM (driver 617.42, CUDA backend in Ollama), plus Intel UHD 770 (unused)
- Free disk on C: about 644 GB before the downloads
- OS: Windows 11 Pro

## Runtime

- Ollama **0.40.13**, installed with winget (`Ollama.Ollama`). Free, no account, no API key.
- Models are stored in `experiment/extra_models/ollama_models` (user environment variable `OLLAMA_MODELS`).
- Hosted options were checked first and rejected for $0: on Hugging Face only Qwen3.5-4B had an inference provider,
  and that one is billed per call. Meta's Llama repos are gated and the supplied account had no access. No key was
  used for any download or generation, and none is stored.

## Models (all Q4_K_M, text-only use)

| Model | Ollama tag | Digest (sha256) | Params (GGUF) | Native context | Size |
|---|---|---|---|---|---|
| MiniCPM-V 4.5 | `openbmb/minicpm-v4.5:8b` | `2acb76d2089b7ff1d3a4c306fbe028438ff68e853a6cff786456046b94375334` | 8.19 B (language model) | 40,960 | 6.12 GB |
| Qwen3.5 4B | `qwen3.5:4b` | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` | 4.21 B | 262,144 | 3.32 GB |
| InternVL3.5 2B | `hf.co/bartowski/OpenGVLab_InternVL3_5-2B-GGUF:Q4_K_M` | `5f190201c5de77b1980eb1f03d2e144ebd9b8380a70b5c45d8ed0db1eef78f75` | 2.03 B (language model) | 40,960 | 1.92 GB |
| SmolVLM2 2.2B | `hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M` | `19c7714a4edfdd47694dfdbfa38dd56026b95452423b5900b483ac84c355183a` | 1.81 B (language model) | **8,192** | 1.71 GB |
| Llama 3.2 3B (used) | `llama3.2:3b` | `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | 3.21 B | 131,072 | 2.02 GB |
| Llama 3.2 Vision 11B (pilot only, failed to load) | `llama3.2-vision:11b` | `6f2f9757ae97e8a3f8ea33d6adb2b11d93d9a35bef277cd2c0b1b5af8e8d0b1e` | 10.67 B | 131,072 | 7.82 GB |

Llama 3.2 Vision 11B fits the hardware, but Ollama 0.40.13 cannot load its `mllama` architecture, so the 3B text model
was used instead (PLAN deviation 1). Llama 3.2 3B is a text-only model, unlike the other four.

The full-model parameter counts on the Hugging Face pages, including the vision parts, are: MiniCPM-V-4_5 8.70 B,
Qwen3.5-4B 4.66 B, InternVL3_5-2B 2.35 B, SmolVLM2-2.2B-Instruct 2.25 B, Llama-3.2-11B-Vision-Instruct 10.67 B.
The vision projector is loaded but never used, because no image is sent.

**Settings (all models):** temperature 0, seed 20261031, `num_ctx` 32768, `num_predict` 4096 per turn, `think: false`
(MiniCPM-V 4.5 and Qwen3.5 have a thinking mode).

**SmolVLM2's native context is 8,192 tokens**, below the shared `num_ctx`. Cases whose chat goes past 8k tokens are
outside what that model was trained on, and they are counted in the results.

## Uninstall afterwards

1. Delete the models: remove the folder `experiment\extra_models\ollama_models` (about 21 GB).
2. Remove the variable: in PowerShell run
   `[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $null, "User")`.
3. Uninstall Ollama: run `winget uninstall --id Ollama.Ollama`, or use Settings > Apps > Installed apps > Ollama >
   Uninstall.
4. Optional: delete `%USERPROFILE%\.ollama` (the server key and history) and `%LOCALAPPDATA%\Ollama` (logs).
