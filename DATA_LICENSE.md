# Data licence

## What this licence covers

The following are released under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**,
https://creativecommons.org/licenses/by/4.0/ :

- the human labels, the adjudication decisions and the consensus labels in `data/round1_pilot/`,
  `data/round2_main/` and `data/round3_local_models/`;
- the samples and hidden keys in those folders (item codes, case references and SHA-256 hashes of the repair texts);
- the derived tables in `data/local_model_repairs/checker_results.csv`, `data/extraction_check/`,
  `data/judges/` and `results/`;
- the rubric texts in `rubric/` and the plans in `plans/`.

Copyright (c) 2026 Samiha Azeem and Toshiba Nayyab.

You may share and adapt this material for any purpose, including commercially, as long as you give appropriate
credit, provide a link to the licence and say whether you made changes.

## Please cite

If you use these labels or tables, please cite the paper *False Passes in LLM-Based Web Accessibility Repair:
A Human-Validated Audit* by Samiha Azeem and Toshiba Nayyab. The citation details are in `CITATION.cff`.

## What this licence does not cover

- **Content from the AccessGuru dataset** (Fathallah et al., CC BY 4.0). The rule ids and the case references in
  our tables point into that dataset. `examples/examples_false_pass.md` quotes trimmed excerpts of five original
  fragments and their published repairs. The files in `data/local_model_repairs/*.jsonl` contain replies from five
  local models, and those replies often quote the AccessGuru fragments they were asked to repair. That material
  stays under the AccessGuru dataset's own CC BY 4.0 licence and must be credited to Fathallah et al.
  See `NOTICE.md`.
- **Model outputs** in `data/local_model_repairs/*.jsonl` were produced by the five local models listed in
  `NOTICE.md`. Each model has its own licence, listed there.
- **The analysis code** in `scripts/` is under the MIT licence in `LICENSE`.
