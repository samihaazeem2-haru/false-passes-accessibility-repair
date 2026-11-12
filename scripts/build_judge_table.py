"""Build data/judges/judge_verdicts.csv from the raw LLM-judge .jsonl files.

The raw files hold the judges' free-text rationales, which quote the AccessGuru repair texts, so they are not
released. This script keeps only four columns: item_id, judge, verdict, skipped.

If a judge has more than one record for the same item (a retry), the last record wins. step3_analyze.py reads the
files the same way.

Usage (standard library only):
    python -I scripts/build_judge_table.py OUT.csv ROUND1.jsonl ROUND2.jsonl
For example, from the working Data folder:
    python -I build_judge_table.py judge_verdicts.csv experiment/step2/human_sample_judgments.jsonl experiment/step2r2/human_sample_judgments_r2.jsonl
"""
import csv
import json
import sys


def main(out, paths):
    last = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                last[(r["item_id"], r["judge_model"])] = r["verdict"]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item_id", "judge", "verdict", "skipped"])
        for (item_id, judge), verdict in sorted(last.items()):
            w.writerow([item_id, judge, verdict, "yes" if verdict == "skipped_too_large" else "no"])
    print(f"wrote {len(last)} rows to {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
