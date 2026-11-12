"""Generate AccessGuru first-round repairs with local Ollama models. $0, no API key.

The conversation is the published AccessGuru first-round (ablation, no re-prompting) prompt, copied verbatim from
artifact/code/AccessGuru/AccessGuruCorrect/syntax_metacognitive_implementation_Qwen.py (identical to the GPT-4
version): one system message and five user turns in one chat. The repair is turn 4 (Decision_Confirmation).
Text-only input. Settings are fixed in PLAN_extra_models.md.

Resumable: a case already in repairs/<slug>.jsonl is skipped. Every call is logged to logs/calls.jsonl.

Usage (from the Data folder, .venv active):
    python -I experiment/extra_models/scripts/gen_repairs.py <model_tag> [--limit N]
"""
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # experiment/extra_models
EXP = os.path.dirname(HERE)
ART = os.path.join(EXP, "artifact")
OLLAMA = "http://127.0.0.1:11434/api/chat"

MODELS = {  # tag -> slug used in file names
    "openbmb/minicpm-v4.5:8b": "MiniCPM-V-4.5",
    "qwen3.5:4b": "Qwen3.5-4B",
    "hf.co/bartowski/OpenGVLab_InternVL3_5-2B-GGUF:Q4_K_M": "InternVL3.5-2B",
    "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M": "SmolVLM2-2.2B",
    "llama3.2:3b": "Llama-3.2-3B",  # deviation 1 (PLAN): llama3.2-vision:11b cannot load in Ollama 0.40.13
}
OPTIONS = {"temperature": 0, "seed": 20261031, "num_ctx": 32768, "num_predict": 4096}

# ---- verbatim from syntax_metacognitive_implementation_Qwen.py -------------------------------------------
SYSTEM = """You are a Web accessibility expert with a strong proficiency in HTML and a deep commitment to fixing Web accessibility violations.
                                        You are familiar with different types of disabilities and user needs.
                                        You are familiar with assistive technologies such as screen readers and understand how they interact with the Web.
                                        You specialize in analyzing Web pages, identifying issues, and providing immediate, corrected HTML code solutions that meet WCAG 2.1 standards.
                                        Your expertise includes resolving problems like missing or improper Alt text, insufficient heading structure, non-semantic elements, inaccessible forms, and color contrast issues.
                                        You are adept at transforming flawed code into compliant, clean HTML that works seamlessly with assistive technologies, ensuring that Websites are fully navigable by keyboard and readable by screen readers.
                                        You provide the corrected code necessary for immediate implementation, ensuring that Websites are not only compliant but truly inclusive for users with disabilities.
                                        Your mission is to ensure that every Website and Web application is accessible to all users by providing expertly corrected HTML, making the Web a more inclusive space.
                                        You reflect on your own answers, assess their accuracy, and provide corrections only when necessary."""


def get_category(c):
    categories = {
        "Syntax": """These occur when HTML code lacks essential structural elements or attributes required for accessibility,
        such as missing alt attributes or improper use of heading tags and table elements.
        To correct this type of web accessibility violation, expertise in HTML coding is required.""",
        "Layout": """These relate to design and visual organization issues, such as insufficient color contrast or poor font sizing,
        that reduce readability or usability for visually impaired users.
        Fixes must ensure accessibility without negatively affecting users without impairments or distort the page layout for users without impairments.
        To correct this type of web accessibility violation, knowledge of web design principles and front-end coding is required.""",
        "Semantic": """These involve the misuse or absence of meaningful content or attributes,
        such as vague alt text or improper use of semantic elements like <header> or <section>.
    To correct this type of web accessibility violation, expertise in HTML semantics and coding is required.""",
    }
    return categories.get(c, "No description available for this category.")


def prompts(category, category_description, violationType, violationDescription, impact, URL, HTMLElement, guideline):
    return [f"""
    Clarify your understanding of the following web accessibility violation:
    Violation Category: "{category}": {category_description},
    Violation type: "{violationType}",
    Violation description: "{violationDescription}",
    Impact: "{impact}" (Impact is a rating determined by the severity of the violation, indicating the extent to which it hinders user interaction with the Web content. The scale is [cosmetic, minor, moderate, serious, critical]).
    Web page URL: "{URL}"
    Affected HTML Element(s): "{HTMLElement}"
    """, f"""
    Based on your understanding, provide a preliminary correction for the web accessibility violation based on the following WCAG guideline(s): "{guideline}".
    Make sure your generated code corrects the web accessibility violation without introducing new violations.
    Ensure you generate the complete corrected code, not just a snippet.
    """, """
    Critically assess your preliminary correction, make sure to correct the initial web accessibility violation without introducing new web accessibility violations.
    Only make corrections if the previous answer is incorrect.
    Make sure your generated code corrects the web accessibility violation without introducing new violations.
    """, """
    Confirm your final decision on whether the correction is accurate or not and provide the reasoning for your decision.
    Only suggest further corrections if the initial response contains errors.
    Make sure your generated code corrects the web accessibility violation without introducing new violations.
    Enclose your corrected HTML code to replace the initial code with violations between these two marker strings: "###albidaya###" as first line and "###alnihaya###" as last line.
    """, """
    Evaluate your confidence (0-100%) in your correction, enclose your confidence score as "Score: <score>".
    Provide an explanation for this confidence level, enclose your explanation as "Explanation: <explanation>".
    """]
# ---- end verbatim ------------------------------------------------------------------------------------------

MAPPING = json.load(open(os.path.join(ART, "data/prompts_support/mapping_dict_file.json"), encoding="utf-8"))
WCAG = {r["guideId"]: r["description"] for r in csv.DictReader(open(os.path.join(ART, "data/prompts_support/WCAGGuidelines.csv"),
                                                                      encoding="utf-8-sig", newline=""))}


def get_guidelines(violationType):
    return [str(x + ":" + WCAG[x]) for x in MAPPING[violationType]]


def load_cases():
    """The 186 syntax/layout rows where axe 4.4.1 detects the target rule before repair (step0)."""
    csv.field_size_limit(10**9)
    sample = [r for r in csv.DictReader(open(os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                             encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]
    base = csv.DictReader(open(os.path.join(EXP, "step0/syntax_layout_baseline_axe.csv"), encoding="utf-8"))
    return [(int(b["row"]), sample[int(b["row"])]) for b in base if b["baseline_detected"] == "True"]


def case_list_hash(cases):
    h = hashlib.sha256()
    for i, s in cases:
        h.update(f"{i}\t{s['id']}\t{s['violationnumberID'].strip()}\t{s['affectedHTMLElement(s)']}\n".encode("utf-8"))
    return h.hexdigest()


def chat(model, messages):
    body = {"model": model, "messages": messages, "stream": False, "think": False, "options": OPTIONS}
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as f:
            r = json.load(f)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="ignore")
        if "does not support thinking" in msg:  # models without a thinking mode reject the flag
            body.pop("think")
            req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3600) as f:
                r = json.load(f)
        else:
            raise RuntimeError(f"HTTP {e.code}: {msg[:200]}")
    return r, round(time.time() - t0, 2)


def is_runtime_error(error):
    """Deviation 2 (PLAN): server-side failures are retried once; request errors (HTTP 4xx) are not."""
    return bool(error) and "HTTP 4" not in error


def run_case(model, slug, i, s):
    cat = s["category"].strip()
    ps = prompts(category=cat, category_description=get_category(cat), violationType=s["violationnumberID"].strip(),
                 guideline=get_guidelines(s["violationnumberID"].strip()), violationDescription=s["description"],
                 impact=s["impact"], URL=s["webURL"], HTMLElement=s["affectedHTMLElement(s)"])
    messages = [{"role": "system", "content": SYSTEM}]
    turns, error = [], ""
    for t, p in enumerate(ps, 1):
        messages.append({"role": "user", "content": p})
        try:
            r, secs = chat(model, messages)
        except Exception as e:  # noqa: BLE001 -- logged, case kept with an empty repair
            error = f"turn {t}: {str(e)[:200]}"
            break
        content = r["message"].get("content", "")
        messages.append({"role": "assistant", "content": content})
        pt, et = r.get("prompt_eval_count", 0), r.get("eval_count", 0)
        log = {"model": model, "slug": slug, "row": i, "id": s["id"], "turn": t, "prompt_tokens": pt, "output_tokens": et,
               "seconds": secs, "done_reason": r.get("done_reason"),
               "truncated_output": r.get("done_reason") == "length",
               "context_full": pt + et >= OPTIONS["num_ctx"]}
        turns.append(log | {"content": content})
        with open(os.path.join(HERE, "logs", "calls.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(log) + "\n")
    return turns, error


def run(model, limit=None):
    if os.name == "nt":  # keep the PC awake while generating (ES_CONTINUOUS | ES_SYSTEM_REQUIRED); no setting is changed
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    slug = MODELS[model]
    cases = load_cases()
    os.makedirs(os.path.join(HERE, "repairs"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    out_path = os.path.join(HERE, "repairs", f"{slug}.jsonl")
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)["row"] for l in open(out_path, encoding="utf-8") if l.strip()}
    todo = [(i, s) for i, s in cases[:limit] if i not in done]  # --limit N = the first N cases, so a resume stays inside them
    print(f"{slug}: {len(done)} cached, {len(todo)} to run", flush=True)
    for n, (i, s) in enumerate(todo):
        turns, error = run_case(model, slug, i, s)
        first_error = ""
        if is_runtime_error(error):
            first_error = error
            time.sleep(10)
            turns, error = run_case(model, slug, i, s)
        s4 = turns[3]["content"] if len(turns) >= 4 else ""
        rec = {"model": model, "slug": slug, "row": i, "id": s["id"], "rule": s["violationnumberID"].strip(),
               "category": s["category"].strip(), "decision_confirmation": s4, "filtered_response": extract(s4), "error": error,
               "retried": bool(first_error), "first_error": first_error,
               "truncated_output_any_turn": any(x["truncated_output"] for x in turns),
               "context_full_any_turn": any(x["context_full"] for x in turns),
               "seconds_total": round(sum(x["seconds"] for x in turns), 2),
               "turns": [{k: x[k] for k in ("turn", "prompt_tokens", "output_tokens", "seconds", "done_reason", "content")} for x in turns]}
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {n + 1}/{len(todo)} row {i} {rec['seconds_total']}s{' ERROR ' + error if error else ''}", flush=True)


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    run(sys.argv[1], lim)
