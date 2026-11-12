# Round 3 results: five local models, first-round repairs

Sample SHA-256 `ab9ebc0cf12a361fb1f36b13dcc33d7a679d1b88bba6c03b8557a1d4a44af450` (matches PLAN_round3.md). 60 items; consensus missing for 0.

## Reliability (before adjudication)

- Binary kappa A3-B3: **0.822** (n = 60, agreement 0.933).
- 3-label kappa: 0.822 (n = 60).
- Confusion (A3 | B3: count): {'fixed|fixed': 43, 'fixed|not_fixed': 1, 'not_fixed|fixed': 3, 'not_fixed|not_fixed': 13}.
- Labeller counts: {'A3': {'fixed': 44, 'not_fixed': 16}, 'B3': {'fixed': 46, 'not_fixed': 14}}.

## Primary: pooled false-pass rate

- 15/60 = 25.0% (95% CI 14.3 to 36.1; 52 cases)

## Truncated replies excluded

- Truncated in any turn excluded (13 items): 8/47 = 17.0% (95% CI 7.0 to 28.3; 43 cases)
- Turn-4 reply truncated excluded (9 items): 9/51 = 17.6% (95% CI 7.8 to 28.0; 47 cases)

## Sensitivity: consensus unclear counted as not fixed

- 15/60 = 25.0% (95% CI 14.3 to 36.1; 52 cases)

## Per model (counts only, descriptive; 12 items per model is too few for per-model rates)

| Model | Items | Consensus fixed | Not fixed | Unclear | No consensus | Truncated (any turn) |
|---|---|---|---|---|---|---|
| MiniCPM-V-4.5 | 12 | 9 | 3 | 0 | 0 | 0 |
| Qwen3.5-4B | 12 | 11 | 1 | 0 | 0 | 1 |
| InternVL3.5-2B | 12 | 9 | 3 | 0 | 0 | 3 |
| SmolVLM2-2.2B | 12 | 5 | 7 | 0 | 0 | 9 |
| Llama-3.2-3B | 12 | 11 | 1 | 0 | 0 | 0 |

Bootstrap: cluster bootstrap over cases (dataset rows), 4000 reps, seed 20261024.
