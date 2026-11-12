"""Step 0: read-only inspection of the AccessGuru artifact.

Usage (from the Data folder):
    python -I experiment/scripts/step0_inspect.py experiment/artifact experiment/step0

Opens every artifact file read-only. Writes only into the output directory.
Standard library only.
"""
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile

csv.field_size_limit(10**9)

ART = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)

SEM_CSV = "data/accessguru_dataset/accessguru_sampled_semantic_violations.csv"
SL_CSV = "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"
FULL_OLD = "data/accessguru_dataset/Original_full_data.csv"
FULL_NEW = "data/accessguru_dataset/Original_full_data_new.csv"
BASELINE2 = "data/baseline_two_dataset.csv"
TAXONOMY = "data/prompts_support/violation_taxonomy.csv"

# Taken verbatim from code/Post-Processing_Evaluation/syntax_layout_evaluation.py
EVAL_ALIASES = {
    "area-alt": "img-alt",
    "aria-roles": "aria-deprecated-role",
    "aria-prohibited-attr": ["aria-valid-attr-value", "aria-allowed-attr"],
    "aria-hidden-body": "aria-hidden-focus",
}


def p(rel):
    return os.path.join(ART, rel)


def read_csv(rel):
    with open(p(rel), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", ART, *args],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


# ---------------------------------------------------------------- 1. hashes
manifest = []
for root, dirs, files in os.walk(ART):
    dirs[:] = sorted(d for d in dirs if d != ".git")
    for f in sorted(files):
        full = os.path.join(root, f)
        rel = os.path.relpath(full, ART).replace(os.sep, "/")
        manifest.append((rel, os.path.getsize(full), sha256_file(full)))
manifest.sort()
manifest_text = "".join(f"{h}  {s}  {r}\n" for r, s, h in manifest)
with open(os.path.join(OUT, "artifact_manifest.sha256"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(manifest_text)
provenance = {
    "artifact_path": ART,
    "git_head": git("rev-parse", "HEAD"),
    "git_tree": git("rev-parse", "HEAD^{tree}"),
    "git_commit_date": git("log", "-1", "--format=%cI"),
    "git_shallow": git("rev-parse", "--is-shallow-repository"),
    "git_remote": git("remote", "get-url", "origin"),
    "git_status_porcelain": git("status", "--porcelain"),
    "file_count_excl_git": len(manifest),
    "total_bytes_excl_git": sum(s for _, s, _ in manifest),
    "folder_sha256": hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
    "folder_sha256_definition": "sha256 of artifact_manifest.sha256 (lines '<sha256>  <bytes>  <relpath>', sorted by relpath, LF, .git excluded)",
}

# ---------------------------------------------------------------- 2. license
with open(p("LICENSE.txt"), encoding="utf-8") as fh:
    lic_first = fh.readline().strip()
with open(p("README.md"), encoding="utf-8") as fh:
    readme = fh.read()
license_info = {
    "LICENSE.txt_first_line": lic_first,
    "README_license_lines": [l.strip() for l in readme.splitlines()
                             if re.search(r"licen[cs]e", l, re.I)],
}

# ---------------------------------------------------------------- 3. taxonomy
tax = {}
for r in read_csv(TAXONOMY):
    tax[r["violationnumberID"].strip()] = r["Category"].strip()

# Rule names that the dataset itself pairs with a Deque axe documentation URL.
full_new = read_csv(FULL_NEW)
axe_named = collections.defaultdict(set)
for r in full_new:
    m = re.search(r"dequeuniversity\.com/rules/axe/([\d.]+)/([a-z0-9-]+)", r["violation_description_url"])
    if m:
        axe_named[m.group(2)].add(m.group(1))

# ---------------------------------------------------------------- 4. sampled syntax/layout file
sl = read_csv(SL_CSV)
REL_RES = re.compile(r"""(?:src|href|srcset|poster|data)\s*=\s*["'](?!https?:|data:|#|mailto:|tel:|javascript:|//)([^"']+)""", re.I)


def html_profile(h):
    h = h or ""
    return {
        "empty": not h.strip(),
        "has_html_tag": bool(re.search(r"<html\b", h, re.I)),
        "has_doctype": bool(re.search(r"<!doctype", h, re.I)),
        "has_body": bool(re.search(r"<body\b", h, re.I)),
        "has_relative_resource": bool(REL_RES.search(h)),
        "has_style_or_class": bool(re.search(r"\b(style|class)\s*=", h, re.I)),
        "length": len(h),
    }


def summarize(rows, html_key):
    profs = [html_profile(r[html_key]) for r in rows]
    lengths = sorted(x["length"] for x in profs)
    n = len(lengths)
    return {
        "n": n,
        "empty_html": sum(x["empty"] for x in profs),
        "with_<html>": sum(x["has_html_tag"] for x in profs),
        "with_doctype": sum(x["has_doctype"] for x in profs),
        "with_<body>": sum(x["has_body"] for x in profs),
        "with_relative_resource_ref": sum(x["has_relative_resource"] for x in profs),
        "with_class_or_style_attr": sum(x["has_style_or_class"] for x in profs),
        "html_len_min_median_max": [lengths[0], lengths[n // 2], lengths[-1]] if n else None,
    }


sl_by_cat = collections.defaultdict(list)
for r in sl:
    sl_by_cat[r["category"].strip()].append(r)

sl_report = {
    "rows": len(sl),
    "category_counts": {k: len(v) for k, v in sorted(sl_by_cat.items())},
    "unique_page_ids": len({r["id"] for r in sl}),
    "unique_urls": len({r["webURL"] for r in sl}),
    "duplicate_(id,rule)_rows": len(sl) - len({(r["id"], r["violationnumberID"]) for r in sl}),
    "columns": list(sl[0].keys()),
    "per_category": {},
}

eligibility_rows = []
for cat, rows in sorted(sl_by_cat.items()):
    rules = collections.Counter(r["violationnumberID"].strip() for r in rows)
    tax_mismatch = {k: tax.get(k, "NOT IN TAXONOMY") for k in rules if tax.get(k) != cat}
    not_axe_named = sorted(k for k in rules if k not in axe_named)
    info = summarize(rows, "affectedHTMLElement(s)")
    info.update({
        "distinct_rules": len(rules),
        "rule_counts": dict(rules.most_common()),
        "rules_whose_taxonomy_category_differs": tax_mismatch,
        "rules_without_deque_axe_url_in_full_dataset": not_axe_named,
        "impact_counts": dict(collections.Counter(r["impact"].strip() for r in rows)),
        "rows_with_failureSummary": sum(bool(r["failureSummary"].strip()) for r in rows),
        "rows_with_additional_info": sum(bool(r["additional_info"].strip()) for r in rows),
        "rows_with_Additional_Context_Needed": sum(bool(r["Additional Context Needed"].strip()) for r in rows),
    })
    sl_report["per_category"][cat] = info

    for r in rows:
        rule = r["violationnumberID"].strip()
        prof = html_profile(r["affectedHTMLElement(s)"])
        is_axe = rule in axe_named
        offline_ok = cat in ("Syntax", "Layout") and is_axe and not prof["empty"]
        eligibility_rows.append({
            "id": r["id"], "category": cat, "rule": rule,
            "taxonomy_category": tax.get(rule, ""),
            "axe_rule_named_in_dataset": is_axe,
            "eval_alias": json.dumps(EVAL_ALIASES.get(rule, "")),
            "html_empty": prof["empty"],
            "has_relative_resource": prof["has_relative_resource"],
            "offline_candidate": offline_ok,
        })

with open(os.path.join(OUT, "syntax_layout_offline_eligibility.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(eligibility_rows[0].keys()))
    w.writeheader()
    w.writerows(eligibility_rows)

eligible_counts = collections.Counter(
    (e["category"], e["offline_candidate"]) for e in eligibility_rows)
sl_report["offline_candidate_counts"] = {f"{c}|{ok}": n for (c, ok), n in sorted(eligible_counts.items())}

# ---------------------------------------------------------------- 5. semantic file
sem = read_csv(SEM_CSV)
sem_types = collections.Counter(r["Violation Type"].strip() for r in sem)
supp_dir = p("data/accessguru_dataset/accessguru_semantic_violations_sampled_dataset_supp_material")
assets_dir = p("semantic_sampled_dataset_assets")
supp_files = set(os.listdir(supp_dir))
asset_files = set(os.listdir(assets_dir))
sem_md = open(p("accessguru_sampled_semantic_violations_dataset.md"), encoding="utf-8").read()
md_refs = re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']|\]\(([^)]+)\)", sem_md)
md_refs = [a or b for a, b in md_refs]
md_local = [r for r in md_refs if not r.startswith("http")]
md_missing = sorted({r for r in md_local if not os.path.exists(p(r))})

sl_sem = sl_by_cat.get("Semantic", [])
sem_keys = collections.Counter((r["webURL"].strip(), r["Violation Type"].strip()) for r in sem)
slsem_keys = collections.Counter((r["webURL"].strip(), r["violationnumberID"].strip()) for r in sl_sem)

sem_report = {
    "rows": len(sem),
    "columns": list(sem[0].keys()),
    "violation_type_counts": dict(sem_types.most_common()),
    "types_not_semantic_in_taxonomy": {k: tax.get(k, "NOT IN TAXONOMY") for k in sem_types if tax.get(k) != "Semantic"},
    "types_with_deque_axe_url_in_full_dataset": sorted(k for k in sem_types if k in axe_named),
    "impact_counts": dict(collections.Counter(r["Impact"].strip() for r in sem)),
    "html": summarize(sem, "Affected HTML"),
    "unique_urls": len({r["webURL"] for r in sem}),
    "w3c_act_testcase_urls": sum("wcag-act-rules/testcases" in r["webURL"] for r in sem),
    "supp_material_numbered_pngs_1_to_55_present": sum(f"{i}.png" in supp_files for i in range(1, 56)),
    "semantic_sampled_dataset_assets": sorted(asset_files),
    "semantic_md_local_refs": len(md_local),
    "semantic_md_local_refs_missing": md_missing,
    "match_with_Semantic_rows_in_syntax_layout_file_(url,type)_multiset_equal": sem_keys == slsem_keys,
    "semantic_rows_only_in_semantic_csv": sum((sem_keys - slsem_keys).values()),
    "semantic_rows_only_in_syntax_layout_csv": sum((slsem_keys - sem_keys).values()),
}

# ---------------------------------------------------------------- 6. full datasets and joins
full_old = read_csv(FULL_OLD)
fn_cat = collections.Counter(r["violation_category"].strip() for r in full_new)
fo_cat = collections.Counter(r["category"].strip() for r in full_old)
fo_ids = {r["id"] for r in full_old}
fn_pageids = {r["web_URL_id"] for r in full_new}
fn_urls = {r["web_URL"].strip() for r in full_new}
fo_urls = {r["webURL"].strip() for r in full_old}
sl_ids = {r["id"] for r in sl}
sl_urls = {r["webURL"].strip() for r in sl}
html_paths = [r["html_file_path"] for r in full_new] + [r["html_filepath"] for r in full_old]
full_report = {
    "Original_full_data_new.csv": {
        "rows": len(full_new),
        "category_counts": dict(fn_cat),
        "distinct_violation_names": len({r["violation_name"] for r in full_new}),
        "unique_pages": len(fn_pageids),
        "scrape_status": dict(collections.Counter(r["scrape_status"] for r in full_new)),
        "axe_doc_versions_in_urls": dict(collections.Counter(
            m.group(1) for r in full_new
            for m in [re.search(r"rules/axe/([\d.]+)/", r["violation_description_url"])] if m)),
        "rows_with_wcag_reference": sum(bool(r["wcag_reference"].strip()) and r["wcag_reference"].strip() != "[]" for r in full_new),
        "rows_with_supplementary_information": sum(bool(r["supplementary_information"].strip()) for r in full_new),
    },
    "Original_full_data.csv": {
        "rows": len(full_old),
        "category_counts": dict(fo_cat),
        "unique_pages": len(fo_ids),
    },
    "raw_html_files_referenced": len(set(html_paths)),
    "raw_html_files_present_in_artifact": sum(
        os.path.exists(p(os.path.join("data", os.path.basename(x)))) for x in set(html_paths)),
    "any_raw_html_dir_in_artifact": any(re.search(r"raw_html|html_pages", r) for r, _, _ in manifest),
    "sampled_syntax_layout_ids_found_in_Original_full_data.csv": len(sl_ids & fo_ids),
    "sampled_syntax_layout_urls_found_in_Original_full_data.csv": len(sl_urls & fo_urls),
    "sampled_syntax_layout_urls_found_in_Original_full_data_new.csv": len(sl_urls & fn_urls),
    "baseline_two_dataset.csv_rows": len(read_csv(BASELINE2)),
}

# ---------------------------------------------------------------- 7. results and human study
def xlsx_rows(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        wb = z.read("xl/workbook.xml").decode("utf-8")
        names = re.findall(r'<sheet [^>]*name="([^"]+)"', wb)
        sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        for name, sheet in zip(names, sorted(sheets, key=lambda s: int(re.search(r"\d+", s.split("/")[-1]).group()))):
            rows = re.findall(rb"<row[ >].*?</row>", z.read(sheet), re.S)
            out[name] = sum(bool(re.search(rb"<v>|<t[ >]", r)) for r in rows) - 1  # non-blank rows minus header
    return out


results = {}
for rel, _, _ in manifest:
    if rel.startswith("results/") and rel.endswith(".xlsx"):
        try:
            results[rel] = xlsx_rows(p(rel))
        except Exception as e:  # noqa: BLE001
            results[rel] = f"ERROR: {e}"

human = {}
for rel, _, _ in manifest:
    if rel.startswith("human_developer_correction_study/") and rel.endswith(".csv"):
        rows = read_csv(rel)
        human[rel] = {"rows": len(rows), "columns": list(rows[0].keys()) if rows else []}
survey = json.load(open(p("human_developer_correction_study/Our_dataset_Survey.json"), encoding="utf-8"))
human["Our_dataset_Survey.json_top_level_type"] = type(survey).__name__
human["Our_dataset_Survey.json_top_level_len"] = len(survey) if hasattr(survey, "__len__") else None

report = {
    "provenance": provenance,
    "license": license_info,
    "taxonomy_rows": len(tax),
    "taxonomy_category_counts": dict(collections.Counter(tax.values())),
    "sampled_syntax_layout_file": sl_report,
    "sampled_semantic_file": sem_report,
    "full_datasets": full_report,
    "results_xlsx_data_rows_per_sheet": results,
    "human_study": human,
}
with open(os.path.join(OUT, "step0_counts.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)
print(json.dumps(report, indent=1))
