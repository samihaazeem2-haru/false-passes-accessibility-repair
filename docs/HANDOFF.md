# Handoff: AccessGuru, checker pass vs truly fixed

Status as of 2026-10-24 22:15 PKT: **ROUND 2 is complete (labelled, adjudicated, judged, analysed). Read section 0 first; the results are in `step3/results_round2.md`.** Sections 1-7 describe round 1 (now the pilot) and the shared pipeline; they were written 2026-10-23.

## 0. Round 2 (primary), started 2026-10-24

**Why.** Round 1 (rubric v1, 120 items, labellers A and B) finished with binary kappa A-B **0.105** (70 items both decided; 3-label kappa 0.026). Labeller B used `unclear` 39 times. Consensus false-pass rates were GPT-4 0.175, Mistral 0.45, Qwen 0.40, pooled 0.342, but with kappa this low they cannot be trusted. Round 1 stays in the paper as a **pilot**. None of its files were changed, and its results are copied to `step3/results_round1.json`. `step3_analyze.py` still writes the same round-1 keys, checked identical to that copy.

**Design (frozen in `PLAN_round2.md` before any page existed).**
- 120 NEW checker-passing AccessGuru-final repairs, 40 per model, seed 20261026. Every round-1 case (dataset row) is excluded, for every model.
- Eligible pools: GPT-4 86, Mistral 79, Qwen 76. The sample covers 75 distinct cases (85 Syntax, 35 Layout), none overlapping round 1.
- **"Case" = one dataset row (one violation)**, as everywhere in this project and in the bootstrap. The dataset's `id` column is the *web page* (122 pages hold the 250 rows). 66 of the 120 round-2 items (from 34 of their 60 web pages) come from a web page that also gave a *different* violation to round 1. Excluding whole round-1 web pages would leave only 42 / 37 / 37 eligible (GPT-4 / Mistral / Qwen), below 40, so that stricter reading was not used. The count is reported in `results.json` → `human_sample_round2_plan` and in the caveats of `results_round2.md`.
- The plan file holds the SHA-256 of `step2r2/sample_round2.csv`. The page builder refuses to run if the hash does not match, and `step3` re-checks it.
- The rubric is v1 unchanged, plus a v2 addendum shown prominently, plus 3 extra worked examples:
  - contrast computed at 4.48:1, so not fixed;
  - a full-page wrap with a `main` landmark, so fixed;
  - a class-only contrast change with the CSS not shown, so unclear.
- **Primary outcome:** consensus false-pass rate per model and pooled, with a cluster bootstrap by case (4000 reps).
- **Primary reliability:** binary kappa A-B before adjudication.

| Step | Script | Output | Status |
|---|---|---|---|
| sample | `step2h_labeling_r2.py sample` | `step2r2/sample_round2.csv`, `step2r2/labeling_key_r2.csv` (hidden key, ids R2-001..R2-120) | done |
| plan | by hand | `PLAN_round2.md` | frozen 2026-10-24 16:50 PKT |
| pages | `step2h_labeling_r2.py pages` | `step2r2/labeling_A2.html` (labeller A), `step2r2/labeling_B2.html` (labeller B) | done |
| verify | `step2h_labeling_r2.py verify` | console | PASSED (details below) |
| free judges | `step2_judge.py --provider groq --human-sample --round 2` | `step2r2/human_sample_judgments_r2.jsonl`, `logs/groq_round2_judge.log` | **done** (see "Round-2 judges" below) |
| label | two people | `step2r2/human_labels_A2.csv`, `step2r2/human_labels_B2.csv` (unchanged copies of the files the labellers returned) | **done**, validated (below) |
| merge | `step2h_labeling_r2.py merge` | `step2r2/human_labels_r2.csv`, `step2r2/adjudication_todo_r2.csv` | **done**: 116 agreed, 4 to adjudicate |
| adjudication page | `step2h_labeling_r2.py adjpage` | `step2r2/adjudication_r2.html` | **done**, verified (below) |
| adjudicate | both labellers together, on the page | `step2r2/adjudication_r2.csv` (item_id, final_verdict, notes) | **done** 2026-10-24 22:13 PKT; validated; merge re-run: consensus 120/120 |
| judges re-run | `step2_judge.py ... --round 2` (resume) | same files | **done** 22:14 PKT, $0: nothing left for gpt-oss; qwen R2-050 retried, cut off again (stays `judge_error`) |
| analysis | `step3_analyze.py` (unchanged since 18:47 PKT, SHA-256 `b1c3c6f1…d355`) | `step3/results.json`, `step3/results_round2.md`, `step3/main_joined.csv` | **done** 22:15 PKT (results below) |

**The pages were checked by script and in a headless browser.**
- Each page has 120 cards with the same item set, and the two orders differ at 119 of 120 positions.
- The addendum is shown verbatim, the v1 rubric is unchanged, and there are 8 worked examples.
- No model, method, checker, judge or shrink text appears, and no API key or `.env` value.
- The download names are `human_labels_A2.csv` / `human_labels_B2.csv`, with the round-1 columns.
- Each page has its own browser-storage key, separate from round 1's, because pages opened from disk share storage.
- Labels survive a reload, and the pages make no network requests.
- **Re-checked 2026-10-24 18:45 PKT**, independently of the script's own `verify`:
  - the sample was recomputed from step-1 output; the repair text on every card is byte-identical to step 1;
  - headless Chromium, offline: a label and a note survive a reload, the download is `human_labels_A2.csv` / `human_labels_B2.csv` with 120 rows and the round-1 header, there are 0 network requests and 0 script errors.
- **Dry run of the whole pipeline**, on made-up labels in a scratch copy (no real file touched): merge → `adjudication_todo_r2.csv` → filled `adjudication_r2.csv` → merge → `step3_analyze.py`. Every round-2 table filled in without error.

**Round-2 judges: done 2026-10-24 19:20 PKT, $0** (Groq free tier).
- Neither judge's output appears on any labelling page.
- **Not human-validated:** these are judge opinions until the labels are merged.

The table gives the share of checker passes each judge calls not fixed.

| Repairer | gpt-oss-120b | qwen3.8-27b |
|---|---|---|
| GPT-4 | 16/35 | 25/33 |
| Mistral | 22/36 | 30/36 |
| Qwen | 7/35 | 20/35 |

- Judge vs judge: 104 items both decided, agreement 0.683, kappa 0.406. Qwen is again the harsher judge.
- **Skipped as too large** (free limit of 8,000 tokens per minute):
  - gpt-oss-120b, 14 items: R2-014, R2-016, R2-020, R2-021, R2-022, R2-025, R2-048, R2-054, R2-055, R2-070, R2-072, R2-084, R2-104, R2-111;
  - qwen3.8-27b: the same 14 plus R2-053.
- **Judge error:** qwen on R2-050 (its answer was cut off even after the retry with 3× the output room). Under the plan it is excluded from that judge's agreement only.
- Humans label all 120.

**Round-2 labels: received and merged 2026-10-24 (before adjudication).**
- Files: `human_labels_A2.csv` (SHA-256 `b8ae796c…bebab9`) and `human_labels_B2.csv` (SHA-256 `d6af93eb…b04f73a`), copied byte-identical from the files the labellers returned into `step2r2/`. The copies are never edited.
- Validation (both files): header `item_id,labeller,human_verdict,note`; 120 data rows; ids are exactly the 120 ids of `sample_round2.csv`, no duplicates, none missing, none extra; verdicts only `fixed` / `not_fixed`; labeller column `A2` / `B2` throughout; no blank rows, no stray spaces; no notes written by either labeller; each file's row order equals its own page's card order. No problems.
- Pre-adjudication reliability (computed with step3's `kappa()`; round-1 figures re-derived from `step2/human_labels.csv` and identical to `step3/results_round1.json`):

| | Round 1 (rubric v1) | Round 2 (rubric v2) |
|---|---|---|
| Items agreed (both fixed or both not_fixed) / to adjudicate | 36 / 84 | 116 / 4 |
| Binary kappa A-B (unclear excluded) | 0.105 (n = 70, agreement 0.514) | **0.928** (n = 120, agreement 0.967) |
| 3-label kappa A-B | 0.026 (agreement 0.308) | 0.928 (agreement 0.967) |
| Labeller A: fixed / not_fixed / unclear | 43 / 65 / 12 | 75 / 45 / 0 |
| Labeller B: fixed / not_fixed / unclear | 71 / 10 / 39 | 79 / 41 / 0 |
| A false-pass rate, unclear excluded / as not_fixed | 0.602 (65/108) / 0.642 (77/120) | 0.375 (45/120) / 0.375 |
| B false-pass rate, unclear excluded / as not_fixed | 0.123 (10/81) / 0.408 (49/120) | 0.342 (41/120) / 0.342 |

- Round-2 confusion (rows A2, columns B2): fixed/fixed 75, not_fixed/not_fixed 41, not_fixed/fixed 4, fixed/not_fixed 0. No `unclear` from either labeller.
- Disputed items: R2-006, R2-072, R2-085, R2-109 (all A2 not_fixed, B2 fixed).
- Kappa 0.928 is above the plan's 0.6 bar, so the consensus needs no low-kappa caveat. The jump from 0.105 is large; the write-up should say the rubric v2 addendum is the main change between rounds and that round-2 items are new.
- Per-model labeller rates are held back until after adjudication (they come out of `step3_analyze.py`).

**Adjudication page** (`step2r2/adjudication_r2.html`, built by `step2h_labeling_r2.py adjpage`).
- One card per disputed item: id, rule, description, axe failure summary, original fragment, proposed repair, both labels and notes, a Fixed / Not fixed / Unclear choice and a notes box. Same rubric text (v2 addendum + v1 + 8 worked examples).
- Blind: the builder runs the same leak checks as the labelling pages' `verify` (no model, method, checker, judge, shrink or key text) and PASSED.
- Headless Chromium, offline: 4 cards, a choice and a multi-line note with a comma and quotes survive a reload, the download is `adjudication_r2.csv` with header `item_id,final_verdict,notes` and 4 rows, 0 network requests, 0 script errors, no horizontal scroll at 390 px. Own storage key `repair-adjudication-round2`. The downloaded test file was fed to `merge` in a scratch copy and read correctly; no real `adjudication_r2.csv` was written.

**Adjudication: done 2026-10-24 22:13 PKT.** `step2r2/adjudication_r2.csv` holds exactly the 4 disputed items, with valid verdicts and no notes: R2-006 not_fixed, R2-072 fixed, R2-085 not_fixed, R2-109 not_fixed. After the re-run merge, the consensus is 76 fixed / 44 not_fixed / 0 unclear, with no item missing. The labellers' CSVs and `PLAN_round2.md` are unchanged; their hashes were checked before the merge. A byte-identical copy was also saved by hand as `step2/adjudication_r2.csv` (the round-1 folder, 22:12). No script reads it, the round-1 results are unaffected, and it can be deleted.

**Round-2 results (2026-10-24 22:15 PKT; full text in `step3/results_round2.md`, numbers in `step3/results.json`).**
- The analysis ran exactly as planned, with no change to `step3_analyze.py` after the labels arrived. The sample hash matches the plan. The round-1 keys in `results.json` are identical to `results_round1.json`.
- The headline counts were checked independently from `human_labels_r2.csv` and the judge file, and they match.
- **Reliability before adjudication:** binary kappa 0.928 (n = 120), above the plan's 0.6 bar.

| Repairer | Consensus not fixed | False-pass rate (95% cluster-bootstrap CI) | True fix over 186 (95% CI) |
|---|---|---|---|
| GPT-4 | 9/40 | 22.5% (10.4 to 36.2) | 75.8% (62.5 to 87.7) |
| Mistral | 22/40 | 55.0% (39.5 to 70.3) | 40.9% (27.0 to 54.9) |
| Qwen | 13/40 | 32.5% (18.9 to 47.5) | 61.0% (47.4 to 73.2) |
| Pooled | 44/120 | 36.7% (27.1 to 47.1) | |

- **Model differences:** Mistral has a higher false-pass rate than GPT-4 (+32.5 points, CI 13.5 to 51.8) and than Qwen (+22.5, CI 4.4 to 41.2). GPT-4 vs Qwen: -10.0 points, CI -27.1 to +7.4, which includes 0.
- **Sensitivity:** with `unclear` counted as not fixed, nothing changes (there is no `unclear` consensus).
- **Judges vs the human consensus:** gpt-oss-120b kappa 0.385 (n = 106, out-of-family 0.443); qwen3.8-27b kappa 0.16 (n = 104, out-of-family 0.166). Both are below the plan's 0.7 bar, so **neither free judge can stand in for the humans**.
  - Skipped as too large: gpt-oss 14 items, qwen 15 items (listed in `results_round2.md`). Qwen also has 1 error: R2-050.
- **Content-shrink flag:** fired on 50 items, and humans called 30 of those not fixed. Humans also called 14 unflagged items not fixed. Kappa 0.407.
- **Combined round 1 + 2 (secondary):** pooled false-pass 35.4% (CI 29.2 to 42.1); GPT-4 20.0%, Mistral 50.0%, Qwen 36.2%.

**Commands (PowerShell, from the Data folder).**
```powershell
cd "<path-to-Data-folder>"
$env:PYTHONIOENCODING = "utf-8"
$py = ".\.venv\Scripts\python.exe"

# judges: ALREADY DONE (free; re-running only fills gaps)
& $py -I experiment\scripts\step2_judge.py --provider groq --human-sample --round 2 --model openai/gpt-oss-120b
& $py -I experiment\scripts\step2_judge.py --provider groq --human-sample --round 2 --model qwen/qwen3.8-27b

# labels: DONE (copies in experiment\step2r2\, merged, page built)
& $py -I experiment\scripts\step2h_labeling_r2.py merge experiment experiment\step2r2\human_labels_A2.csv experiment\step2r2\human_labels_B2.csv
& $py -I experiment\scripts\step2h_labeling_r2.py adjpage experiment
# adjudication: DONE (experiment\step2r2\adjudication_r2.csv); the merge line above was re-run afterwards

# results
& $py -I experiment\scripts\step3_analyze.py experiment
```
**Rules:** send each person only their own page. Never send the key, the judge files or the results. Nobody discusses items until both CSVs are in. The rubric and the plan do not change from here on.

---

## Round 1 (pilot) and shared pipeline

Original status, as of 2026-10-23. **The plan is now $0: no paid API calls. Do not run `run_paid_steps.ps1`** (it is kept only as a record of the old paid plan). "Truly fixed" is now measured by **two human labellers** on a fixed random sample of 120 checker-passing AccessGuru-final repairs, and two free Groq judges are scored against those humans. What is done and the exact commands are in section 4.

The full log of decisions and findings is `00_inspection.md`. This file covers what is done, what is not, and exactly how to finish.

---

## 1. The study in one paragraph

AccessGuru (Fathallah et al.) repairs web-accessibility violations with LLMs and scores success with an automated checker: axe-core 4.4.1, run on the HTML fragment. We ask how often a **checker pass** is a **true fix**.
- **Main analysis:** the 186 syntax/layout cases where axe actually flags the target rule before repair. The repairs are the paper's own published outputs (GPT-4, Mistral, Qwen × 3 baselines + AccessGuru first round + AccessGuru final), so no new repairs are generated.
- **Checker-blind analysis:** the 55 semantic cases, which axe cannot detect at all, are reported separately.
- **Measuring "truly fixed" ($0 plan):** two people label, blind and independently, 120 checker-passing AccessGuru-final repairs (40 per model, random, seed 20261023). Their consensus gives the **false-pass rate** per model (checker pass but not truly fixed), with a cluster bootstrap CI by case. A judge-free **content-shrink** flag covers all repairs. Two free Groq LLM judges are run on the same 120 items only, to see whether a free judge could stand in for humans. (Old paid plan: Gemini 3.8 Flash judge on all 1,649 repairs. Dropped, $0 budget.)

## 2. Provenance

| | |
|---|---|
| Artifact | `experiment/artifact/` = github.com/NadeenAhmad/AccessGuruLLM, commit `bf45666aa281af7cca23aaabd9bfe3bd802b9036`, unmodified (`git status` clean) |
| Folder hash | `41d3c888b8e339aec2807c56da27a7e04c237ad9f77279934a29e8c35548b50d` (definition and per-file hashes: `step0/artifact_manifest.sha256`) |
| License | Code MIT (`LICENSE.txt`); dataset CC BY 4.0 (README). Cite the paper. |
| Checker | axe-core 4.4.1 (SHA-256 `8466af7f…a7c2f`), Chromium 129.0.6668.29, Playwright 1.47.0, the paper's 93-tag list, read from its code |

## 3. Done (free) and what it shows

| Step | Script | Output | Result |
|---|---|---|---|
| 0 inspection | `step0_inspect.py` | `step0/step0_counts.json` | 250 = 195 Syntax + 55 Layout; 55 Semantic; full data 3,524 rows; only fragments, no page HTML |
| 0b baseline axe | `step0b_baseline_axe.py` | `step0/syntax_layout_baseline_axe*.{csv,json}` | **186** flagged before repair (133 Syntax + 53 Layout) = main set |
| 0c undetected reasons | `step0c_undetected_reasons.py` | `step0/syntax_layout_groups*.{csv,json}` | **64** baseline-undetected: 52 rule did not fire (missing page context, e.g. `duplicate-id` 19, `landmark-unique` 14), 5 rule absent from axe 4.4.1, 4 axe "incomplete", 3 axe errors |
| 1 checker on paper repairs | `step1_checker_on_paper_outputs.py` | `step1/checker_on_paper_outputs*.{csv,json}`, `step1/responses.jsonl` | 2,790 axe runs, 2 errors; table below |
| 1s semantic set | `step1s_semantic_items.py` | `step1/semantic_items*.json*` | 55 cases × 3 models, screenshots and developer references attached |
| 1s semantic axe | `step1s_semantic_axe.py` | `step1/semantic_axe*.{csv,json}` | axe cannot see the semantic faults; repairs add new axe violations (below) |
| 2h human sample | `step2h_labeling.py make` | `step2/labeling_A.html`, `step2/labeling_B.html`, `step2/labeling_key.csv` | **120 items** (40 per model, 98 distinct cases, 87 Syntax + 33 Layout), drawn from step1 checker output only, before any Groq judge ran. Pages are blind (checked: no model, method, checker or AI verdict text). |
| 2 free Groq judges | `step2_judge.py --provider groq --human-sample` | `step2/human_sample_judgments.jsonl`, `logs/groq_human_sample_judge.log` | **done, $0.** gpt-oss-120b judged 112/120, Qwen 3.8 27B 109/120; the rest were too large for the free per-minute limit (below) |
| 3 analysis | `step3_analyze.py` | `step3/results.json`, `step3/main_joined.csv` | runs now; human-sample section fills in once labels are merged |

**Checker results on the 186 main cases** (counts out of 186):

| Model | Method | Checker pass | Empty repair | Pass + new axe violation | Pass but no HTML / placeholder text |
|---|---|---|---|---|---|
| GPT-4 | AccessGuru final | 182 | 0 | 22 | 24 |
| GPT-4 | AccessGuru first | 174 | 0 | 28 | 17 |
| GPT-4 | baseline 1 / 2 / 3 | 127 / 145 / 33 | 47 / 24 / 126 | 35 / 38 / 5 | 2 / 4 / 0 |
| Mistral | AccessGuru final | 169 | 0 | 18 | 38 |
| Mistral | AccessGuru first | 157 | 0 | 32 | 31 |
| Mistral | baseline 1 / 2 / 3 | 45 / 45 / 9 | 117 / 128 / 177 | 22 / 18 / 1 | 1 / 5 / 0 |
| Qwen | AccessGuru final | 168 | 0 | 25 | 38 |
| Qwen | AccessGuru first | 155 | 0 | 37 | 37 |
| Qwen | baseline 1 / 2 / 3 | 128 / 129 / 51 | 27 / 13 / 77 | 36 / 34 / 7 | 6 / 2 / 0 |

The last column is a text heuristic (no `<tag>`, or phrases like "would go here" / `INCOMPLETE_RESPONSE`), not a verdict. It already shows that the checker passes non-repairs. Example: a GPT-4 "repair" that is only the comment "Corrected HTML and CSS code would go here…" was scored fixed by the paper's checker.

**Semantic (checker-blind), our axe run:**
- Axe reports the same violation set before and after for 24 (GPT-4), 27 (Pixtral) and 10 (Qwen) of 55 repairs.
- Repairs introduced new axe violations in 4 / 3 / **23** cases. Qwen dropped `lang` in 12.
- The paper's own manual verdicts call 51 / 46 / 36 of the first-round repairs fixed.

**Content shrink (judge-free, all repairs; `content_shrink` in `step3/main_joined.csv`).** The flag fires when the repair is under half the original's length (`len_ratio < 0.5`) or keeps under 80% of the original's elements. An element counts as kept if the repair has an element with the same tag, or, for a re-tagged element such as `div`→`header`, the same id or class. Flagged checker passes, AccessGuru final: **GPT-4 67/182, Mistral 108/169, Qwen 54/168.** Typical flagged cases: CSS-only "fixes" that drop the content, and sections emptied into comments. It is a flag, not a verdict; its precision against the humans is reported in `content_shrink_vs_human`.

**Semantic: our axe vs the paper's own manual verdicts** (`semantic_axe_vs_paper_manual`). Treating "repair added no new axe violation" as an axe pass, agreement with the paper's manual fixed/not-fixed is kappa **0.19 / 0.09 / −0.05** (GPT-4 / Pixtral / Qwen). With "axe clean after" instead, kappa is 0.03 / −0.02 / 0.06. Axe tells you essentially nothing about semantic fixes. For Qwen, axe passes 11 repairs that the paper calls not fixed.

**Free judges on the 120-item sample: NOT human-validated yet** (`human_sample_judges_alone_0usd`). The table gives the share of checker passes each judge calls *not* fixed, with Wilson 95% CIs.

| Repairer | gpt-oss-120b | qwen3.8-27b |
|---|---|---|
| GPT-4 | 16/36 = 0.44 (0.30–0.60) | 28/35 = 0.80 (0.64–0.90) |
| Mistral | 28/38 = 0.74 (0.58–0.85) | 34/37 = 0.92 (0.79–0.97) |
| Qwen | 18/38 = 0.47 (0.33–0.63) | 27/37 = 0.73 (0.57–0.85) |

- **Both judges say a large share of checker passes are not truly fixed, and both rank Mistral worst.** They disagree on how large: judge-vs-judge agreement is 0.73, kappa 0.42, and Qwen is much harsher. Only the human labels can say which judge, if either, to trust. Until then, report these as *judge estimates*, not results.
- **Content-shrink flag vs judges:** when the flag fires, gpt-oss says not fixed 45/48 times and Qwen 45/45. Unflagged items are judged not fixed 17/64 times (gpt-oss) and 44/64 times (Qwen). The flag has high precision but misses many failures. Expected, since it cannot see partial fixes or wrong colours.
- **Skipped as too large** for the free 8,000 tokens-per-minute limit (humans still label them): gpt-oss H011, H017, H041, H065, H073, H077, H091, H094; Qwen the same plus H005, H007, H054.
- **Rationales:** 8 random gpt-oss rationales were read; all were grounded in the code. One pattern is strict: a contrast repair that turned a `<span>` into an `<h1>` was called not fixed (structure changed). The humans decide such cases.
- **Run notes:** Qwen sometimes ran out of output room before finishing its JSON (Groq HTTP 400 `json_validate_failed`). The judge now retries once with 3× the room, and if that fails it records `judge_error` instead of stopping; 2 items needed the retry, 0 errors remain.

**Judge pilot (24 judgments, $0.07 actual, old paid plan):** of 21 checker-passing repairs, 12 were judged *not* fixed. Reasons: placeholders, content deleted or replaced, partial fixes, contrast still failing, new barriers. All 24 rationales were read by hand and look grounded in the code.

## 4. The $0 plan: what is left and how to finish

Nothing below costs money. **Do not run `run_paid_steps.ps1`.** The Groq key works: free tier, 8,000 tokens per minute, 1,000 requests per day per model.

| Task | Who | Time | Command |
|---|---|---|---|
| Label 120 items, alone, blind | **two people** (ideally not the author) | 2–4 h each | open `step2/labeling_A.html` (person A) and `step2/labeling_B.html` (person B) |
| Merge the two CSVs | you | 1 min | `step2h_labeling.py merge` |
| Adjudicate the disagreements | both labellers together | ~30 min | fill `final_verdict` in `step2/adjudication_todo.csv`, save as `step2/adjudication.csv`, merge again |
| ~~Free Groq judges on the same 120~~ | computer | **done 2026-10-23** | `step2_judge.py --provider groq --human-sample` |
| Final tables | computer | seconds | `step3_analyze.py` |

**Judge models.** Groq no longer serves `llama-3.3-70b-versatile` or `llama-3.1-8b-instant` to this key (HTTP 404, `model_not_found`, 2026-10-23). The judges are therefore:
- `openai/gpt-oss-120b`, the same family as the GPT-4 repairer
- `qwen/qwen3.8-27b`, the same family as the Qwen repairer

Each judge is in-family for one repairer, so `step3` also reports judge-human agreement on out-of-family items only. Both use the same rubric and prompt as the old Gemini judge. If Groq brings Llama back, pass `--model <id>`.

**Skipped items** (too big for the 8,000 tokens-per-minute limit): 7 are certainly too large and are never sent: H011, H017, H041, H065, H073, H077, H091. Four are borderline (H005, H007, H054, H094); they are sent, and Groq decides. Both kinds are listed under `skipped_too_large` in `step3/results.json`. Humans label all 120 regardless.

### Blockers (things only a person can do), status 2026-10-23
| Blocker | Why it blocks | What unblocks it |
|---|---|---|
| **Human labels (A and B)** | the headline false-pass rate, labeller kappa, judge-vs-human and shrink-vs-human all need them | two people label `labeling_A.html` / `labeling_B.html` and return the CSVs |
| **Adjudication** | items the two labellers disagree on have no consensus | both labellers fill `final_verdict` in `adjudication_todo.csv` |
| ~~Groq daily limit~~ | not hit; both judges finished on 2026-10-23 | — |
| 8–11 items too large for free judges | Groq free tier caps one request at 8,000 tokens per minute | none possible at $0. They are listed; humans label them; agreement is computed on the rest |
| Llama judges | Groq returns 404 for both requested Llama models | none needed: gpt-oss-120b and qwen3.8-27b are used instead |

Everything not on this list is done or runs by itself. Until labels exist, `step3/results.json` → `human_sample_judges_alone_0usd` shows what the free judges say on the 120 items. It gives each judge's view of the false-pass rate, judge-vs-judge kappa and judge vs content-shrink flag. **It is not a human-validated result.**

### Exact commands (PowerShell, from the Data folder)

```powershell
cd "<path-to-Data-folder>"
$env:PYTHONIOENCODING = "utf-8"
$py = ".\.venv\Scripts\python.exe"

# 1. free judges on the 120 items: ALREADY DONE (re-running is harmless; it only fills gaps)
& $py -I experiment\scripts\step2_judge.py --provider groq --human-sample --model openai/gpt-oss-120b
& $py -I experiment\scripts\step2_judge.py --provider groq --human-sample --model qwen/qwen3.8-27b

# 2. after both people send their CSVs
& $py -I experiment\scripts\step2h_labeling.py merge experiment "<folder-with-returned-labels>\human_labels_A.csv" "<folder-with-returned-labels>\human_labels_B.csv"
#    -> both labellers discuss experiment\step2\adjudication_todo.csv, fill final_verdict,
#       save it as experiment\step2\adjudication.csv, then run the merge line again

# 3. results
& $py -I experiment\scripts\step3_analyze.py experiment
```

**Rules for labellers:** send each person only their own HTML file. Never send `labeling_key.csv`, the judge files or `results.json`. People do not talk about items until both CSVs are in. Labels are saved in the browser as they go, so they can stop and come back in the same browser.

### What to read in `step3/results.json` → `human_sample_0usd`
- `false_pass_rate_human_consensus`: **the headline.** For each model, the share of checker passes that humans judge not truly fixed, with a 95% cluster-bootstrap CI (cases resampled). Also pooled, model differences, and `true_fix_186_<model>` (checker pass rate × (1 − false-pass rate)).
- `inter_rater`: Cohen's kappa between A and B. **Below about 0.6, tighten the rubric before trusting the consensus.**
- `judges_vs_human`: agreement and kappa per Groq judge, overall and out-of-family. Only if kappa is high (≥ about 0.7) can a free judge be argued to scale to all 1,649 repairs. That would still be a separate free run, at a few hundred calls per day.
- `content_shrink_vs_human`: how often a flagged repair is truly not fixed.

The old pilot judgments (`step2/judgments.jsonl`, 24 items, Gemini) are kept but are not used by the $0 plan, and the human sample was not drawn from them.

## 5. Setting up on another machine

```powershell
git clone https://github.com/NadeenAhmad/AccessGuruLLM.git experiment\artifact
git -C experiment\artifact checkout bf45666aa281af7cca23aaabd9bfe3bd802b9036
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install playwright==1.47.0   # use "python -m pip": pip.exe was blocked by Windows Application Control here
python -m playwright install chromium
New-Item -ItemType Directory -Force experiment\vendor | Out-Null
Invoke-WebRequest https://cdn.jsdelivr.net/npm/axe-core@4.4.1/axe.min.js -OutFile experiment\vendor\axe-core-4.4.1.min.js
```
Then re-run the free steps in order (commands are in each script's docstring): step0 → 0b → 0c → 1 → 1s items → 1s axe. Put a `.env` next to `experiment\` containing `GROQ_API_KEY=` (the $0 plan; free key from console.groq.com). **Never commit, print or share `.env`.** The scripts read the key in-process and never print or store it.

## 6. Caveats to carry into the paper

- **Fragment-level checking** follows the paper. Page-context rules (`duplicate-id`, `landmark-*`, `region`) are fragile on fragments, which explains most of the 64 baseline-undetected cases. Those are reported as their own group, never as fixes.
- **Five sampled rule IDs postdate axe 4.4.1** (`summary-name`, `aria-conditional-attr`, `aria-deprecated-role`, `aria-braille-equivalent`, `target-size`). The paper's alias `aria-roles→aria-deprecated-role` points to one of them.
- **AccessGuru final** = the re-prompted answer where re-prompting ran (GPT-4 40, Mistral 61, Qwen 68 of 186), else the first-round answer. In the re-prompt workbooks, non-re-prompted rows hold `INCOMPLETE_RESPONSE`.
- **Workbook rows are matched by (id, rule),** not position: the Qwen files are shifted, and ids are stored as floats. Three Mistral baseline rows among the 186 were generated from a different input (`input_differs`).
- **Baseline methods often have empty repairs** in the published workbooks (up to 177/186). They count as not fixed, which reflects the published data, not necessarily the prompt.
- **Semantic repairs:** the workbooks store only first-round code. 48 of the 55 semantic cases are W3C ACT test pages, not real-world sites.
- **Old pilot judge model:** `gemini-2.5-flash` was unavailable to new accounts (HTTP 404), so the judge is `gemini-3.8-flash`. The pilot used it both via Google (7 calls) and OpenRouter (17 calls); the model is the same.
- **Human sample scope:** the 120 items are *checker passes* of *AccessGuru final* only. So the false-pass rate is P(not truly fixed | checker pass) for that method. It says nothing direct about baselines, first-round repairs or false fails. Each model's sample is a simple random sample from its pool (182 / 169 / 168).
- **Free judges are in-family for one repairer each** (gpt-oss ↔ GPT-4, qwen ↔ Qwen), so report out-of-family agreement too. They are free-tier models and change without notice, so record the model IDs and dates.
- **The content-shrink thresholds** (0.5 length, 0.8 elements kept) were set by reading examples, before any human labels, and they are not tuned on the labels.
- **Spending to date:** about $0.07 on OpenRouter. The account shows that as usage against $0 credit, so it may need settling. Gemini calls so far were free tier.

## 7. Files

```
experiment/
  HANDOFF.md              this file
  00_inspection.md        full log: inspection, decisions, findings
  run_paid_steps.ps1      OLD paid plan; do not run ($0 plan: section 4)
  scripts/                all code (standard library + Playwright; no pandas)
    xlsx_read.py              read-only .xlsx reader
    step0_inspect.py          counts, hashes, licence
    step0b_baseline_axe.py    axe on the 250 originals
    step0c_undetected_reasons.py
    step1_checker_on_paper_outputs.py
    step1s_semantic_items.py
    step1s_semantic_axe.py
    step2_judge.py            judge; --provider groq --human-sample = free judge on the 120 items
    step2s_judge_semantic.py  semantic judge with screenshots (paid; not in the $0 plan)
    step2h_labeling.py        make: 120-item blind sample + one page per labeller; merge: A + B + adjudication
    step2h_labeling_r2.py     round 2: sample / pages / verify / merge / adjpage (imports the v1 rubric from step2h_labeling.py)
    step3_analyze.py          final tables (content shrink, human false-pass, kappa, judge vs human, semantic axe)
  step2/
    labeling_A.html, labeling_B.html   send one to each labeller
    labeling_key.csv                   hidden key (model, case): never show to labellers
    human_sample_judgments.jsonl       Groq judge verdicts on the 120
    human_labels.csv, adjudication_todo.csv   written by merge
    judgments.jsonl                    24 old pilot judgments (not used by the $0 plan)
  PLAN_round2.md          round-2 analysis plan, frozen before labelling (holds the sample hash)
  step2r2/                round 2
    labeling_A2.html, labeling_B2.html   send one to each labeller
    sample_round2.csv, labeling_key_r2.csv   frozen sample / hidden key: never show to labellers
    human_sample_judgments_r2.jsonl      Groq judge verdicts on the round-2 120
    human_labels_r2.csv, adjudication_todo_r2.csv, adjudication_r2.csv   merge outputs / labellers' adjudication
    human_labels_A2.csv, human_labels_B2.csv   the labellers' CSVs, byte-identical copies (never edit)
    adjudication_r2.html                 blind adjudication page for the disputed items
  step3/results_round1.json   frozen copy of round-1 results; step3/results_round2.md  plain-language round-2 report
  step0/  step1/  step3/  other outputs
  logs/                   run logs
  artifact/               the paper's repository (not in the zip; re-clone at the commit above)
  vendor/                 axe-core 4.4.1 (not in the zip; download command above)
```
