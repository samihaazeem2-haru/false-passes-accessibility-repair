"""Step 2s: blinded judge for the 55 checker-blind semantic cases (AccessGuru repairs by GPT4, Pixtral, Qwen).

Same judge model, provider, cap logic and retries as step2_judge.py. Differences:
  - the page screenshot is sent with the prompt (semantic faults such as wrong alt text need it);
  - up to three developer corrections from the paper's human study are given as reference fixes
    (references, not the only acceptable answer);
  - the judge is blind to which model wrote the repair and to the paper's own verdict.
Results are cached in step2/semantic_judgments.jsonl; re-running resumes.

Usage (from the Data folder):
  python -I experiment/scripts/step2s_judge_semantic.py --dry-run
  python -I experiment/scripts/step2s_judge_semantic.py --cap-usd 3
"""
import argparse
import base64
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step2_judge as j  # noqa: E402

RUBRIC = """You are an expert web accessibility auditor. An HTML fragment from a web page has a SEMANTIC
accessibility violation: the markup is valid, but its meaning is wrong for users of assistive technology
(for example, alt text that does not describe the image, a link text that does not match its target, a
wrong lang attribute, or an ambiguous heading). A screenshot of the page is attached. A repair was proposed.
Decide whether the repair TRULY fixes the violation.

A repair is "fixed" only if ALL of these hold:
1. It is concrete code that could replace the original fragment (not advice or a placeholder).
2. It keeps the original element(s), their content and their purpose. Deleting, emptying or hiding the
   element, or replacing it with unrelated markup, does NOT fix it.
3. The new text/attributes are accurate and meaningful for THIS content: check them against the
   screenshot and the page content. Generic, invented or inaccurate text is not a fix.
4. It does not introduce a new accessibility barrier of similar or greater severity.

Reference corrections written by human developers are given. They show acceptable fixes, but a
different repair can also be correct if it meets the criteria above.
Use "unclear" only if the information given genuinely cannot decide.

Answer with JSON only:
{"verdict": "fixed" | "not_fixed" | "unclear",
 "failure_mode": "none" | "no_code" | "placeholder" | "element_removed_or_hidden" | "content_changed"
                 | "inaccurate_text" | "violation_remains" | "partial" | "new_barrier" | "other",
 "rationale": "<= 2 sentences"}
Use failure_mode "none" exactly when verdict is "fixed"."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["openrouter", "gemini"], default="openrouter")
    ap.add_argument("--model", default="google/gemini-3.8-flash")
    ap.add_argument("--cap-usd", type=float, default=3.0)
    ap.add_argument("--price-in", type=float, default=0.825)
    ap.add_argument("--price-out", type=float, default=4.125)
    ap.add_argument("--max-out-tokens", type=int, default=4096)
    ap.add_argument("--image-tokens", type=int, default=1500, help="allowance per screenshot in the cost estimate")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(j.OUT, exist_ok=True)

    cases = [json.loads(l) for l in open(os.path.join(j.STEP1, "semantic_items.jsonl"), encoding="utf-8")]
    todo_all = []
    for c in cases:
        refs = "\n".join(f"Developer {i + 1}:\n<<<\n{f.strip()}\n>>>" for i, f in enumerate(c["developer_fixes"]) if f.strip())
        for model, m in c["models"].items():
            if not m["repair"].strip():
                continue
            key = hashlib.sha256(f'sem\x00{c["case"]}\x00{m["repair"]}'.encode("utf-8")).hexdigest()[:20]
            prompt = (f"{RUBRIC}\n\nVIOLATION TYPE: {c['type']}\nDESCRIPTION: {c['description']}\n\n"
                      f"ORIGINAL FRAGMENT:\n<<<\n{c['html']}\n>>>\n\n"
                      f"REFERENCE CORRECTIONS:\n{refs or '(none)'}\n\n"
                      f"PROPOSED REPAIR:\n<<<\n{m['repair']}\n>>>")
            todo_all.append({"judge_key": key, "case": c["case"], "model": model, "prompt": prompt,
                             "screenshot": c["screenshot"]})
    # identical repairs for a case are judged once; the model name never enters the prompt
    unique = list({u["judge_key"]: u for u in todo_all}.values())
    random.Random(20261023).shuffle(unique)
    with open(os.path.join(j.OUT, "semantic_items.jsonl"), "w", encoding="utf-8") as fh:
        for u in todo_all:
            fh.write(json.dumps({k: u[k] for k in ("case", "model", "judge_key")}) + "\n")

    cache_path = os.path.join(j.OUT, "semantic_judgments.jsonl")
    done = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            r = json.loads(line)
            done[r["judge_key"]] = r
    todo = [u for u in unique if u["judge_key"] not in done]
    spent = sum(r.get("cost_usd", 0) for r in done.values())

    def worst_cost(u):
        tokens_in = len(u["prompt"]) / j.CHARS_PER_TOKEN + (a.image_tokens if u["screenshot"] else 0)
        return tokens_in * a.price_in / 1e6 + a.max_out_tokens * a.price_out / 1e6

    print(f"semantic repairs: {len(todo_all)}, unique: {len(unique)}, done: {len(done)}, to do: {len(todo)}")
    print(f"spent so far ${spent:.2f}; worst case for the rest ${sum(worst_cost(u) for u in todo):.2f} (cap ${a.cap_usd:.2f})")
    if a.dry_run:
        return

    headers = j.auth_headers(a.provider, j.load_key(a.provider))
    with open(cache_path, "a", encoding="utf-8") as fh:
        for n, u in enumerate(todo):
            if spent + worst_cost(u) > a.cap_usd:
                print(f"STOP: next call could exceed the ${a.cap_usd:.2f} cap (spent ${spent:.2f}). {len(todo) - n} left.")
                break
            img = None
            if u["screenshot"]:
                with open(os.path.join(j.ART, u["screenshot"]), "rb") as imf:
                    img = base64.b64encode(imf.read()).decode("ascii")
            text, tin, tout, actual = j.call_with_retry(a.provider, a.model, u["prompt"], a.max_out_tokens, headers, img)
            cost = actual if actual is not None else tin * a.price_in / 1e6 + tout * a.price_out / 1e6
            spent += cost
            try:
                verdict = j.parse_verdict(text)
            except (json.JSONDecodeError, AttributeError):
                verdict = {"verdict": "judge_error", "rationale": (text or "")[:300]}
            rec = {"judge_key": u["judge_key"], "provider": a.provider, "model_used": a.model.removeprefix("google/"),
                   "verdict": verdict.get("verdict"), "failure_mode": verdict.get("failure_mode"),
                   "rationale": verdict.get("rationale"), "tokens_in": tin, "tokens_out": tout,
                   "cost_usd": round(cost, 6), "cost_source": "provider" if actual is not None else "list_price"}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"{n + 1}/{len(todo)} {rec['verdict']:10s} ${spent:.2f}", flush=True)
    print(f"total spent: ${spent:.2f}")


if __name__ == "__main__":
    sys.exit(main())
