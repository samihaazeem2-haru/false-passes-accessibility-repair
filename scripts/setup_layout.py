"""Copy this repository's files into the working folder layout that the analysis scripts expect.

The study scripts were written for a folder called experiment/ with subfolders step2/, step2r2/, extra_models/ and
so on. This script recreates that layout from the repository, so the commands in README.md work unchanged.

Usage (standard library only), from the repository root:
    python scripts/setup_layout.py DATA_FOLDER

DATA_FOLDER is a new or empty folder; the layout is created under DATA_FOLDER/experiment/. The script never
overwrites an existing file; it stops instead. It does not download anything. You still need to clone AccessGuru
into DATA_FOLDER/experiment/artifact and download axe-core into DATA_FOLDER/experiment/vendor (see README.md).

It also writes minimal judge files (item_id, judge_model, verdict) from data/judges/judge_verdicts.csv, so that
step3_analyze.py can rebuild the judge tables. They hold no rationale text.
"""
import csv
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plan(exp):
    """(source in the repository, destination in the layout) for every file."""
    m = []

    def add(src_glob, dst_dir):
        found = sorted(glob.glob(os.path.join(ROOT, src_glob)))
        if not found:
            sys.exit(f"nothing matches {src_glob}")
        m.extend((s, os.path.join(exp, dst_dir, os.path.basename(s))) for s in found)

    add("scripts/step*.py", "scripts")
    add("scripts/xlsx_read.py", "scripts")
    add("plans/PLAN_round2.md", "")
    add("data/round1_pilot/*.csv", "step2")
    add("data/round2_main/*.csv", "step2r2")
    add("data/round2_main/*.csv", "release/data")  # extraction_vs_human.py reads the round-2 files from here
    add("plans/PLAN_extra_models.md", "extra_models")
    add("plans/PLAN_round3.md", "extra_models")
    add("docs/hardware_and_models.md", "extra_models")
    add("data/local_model_repairs/checker_results.csv", "extra_models")
    add("data/local_model_repairs/*.jsonl", "extra_models/repairs")
    add("data/round3_local_models/*.csv", "extra_models/round3")
    add("data/extraction_check/final_extraction_rows.csv", "extra_models/final_extraction_check")
    add("scripts/extra_models/*.py", "extra_models/scripts")
    return m


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    exp = os.path.join(os.path.abspath(sys.argv[1]), "experiment")
    moves = plan(exp)
    judge_files = {"H": os.path.join(exp, "step2", "human_sample_judgments.jsonl"),
                   "R2": os.path.join(exp, "step2r2", "human_sample_judgments_r2.jsonl")}
    clashes = [d for _, d in moves if os.path.exists(d)] + [d for d in judge_files.values() if os.path.exists(d)]
    if clashes:
        sys.exit("These files already exist; nothing was copied:\n  " + "\n  ".join(clashes))
    for src, dst in moves:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    for d in ("step0", "step1", "step3", "vendor"):
        os.makedirs(os.path.join(exp, d), exist_ok=True)
    with open(os.path.join(ROOT, "data", "judges", "judge_verdicts.csv"), encoding="utf-8", newline="") as fh:
        verdicts = list(csv.DictReader(fh))
    for prefix, dst in judge_files.items():
        with open(dst, "w", encoding="utf-8", newline="\n") as out:
            for r in verdicts:
                if r["item_id"].startswith(prefix):
                    out.write(json.dumps({"item_id": r["item_id"], "judge_model": r["judge"], "verdict": r["verdict"]}) + "\n")
    print(f"copied {len(moves)} files and wrote 2 judge files under {exp}")


if __name__ == "__main__":
    main()
