"""Step 2: blinded LLM judge — is each published repair truly fixed? (syntax/layout, 186 baseline-detected cases)

The judge (Gemini, a different model family from the repairers GPT-4 / Mistral / Qwen) sees only the
rule, axe's description of the failure, the original fragment and the repaired output. It never sees
the model, the method or the checker result. Items are judged in a fixed shuffled order, in priority
order (AccessGuru final, AccessGuru first round, then baselines), so a cap stop leaves the primary
data complete. Identical (case, response) pairs are judged once. Empty responses are not sent: they
are "not_fixed / no_code" by definition.

Spending is capped: before every call the worst-case cost of that call is added to the running
total, and the run stops if it would exceed --cap-usd. Actual token usage is recorded per call.
Results are cached in judgments.jsonl, so re-running resumes and never pays twice.

Provider "openrouter" (default) reads OPENROUTER_API_KEY and records OpenRouter's actual charge per call;
provider "gemini" reads GEMINI_API_KEY (the free tier hit its daily quota on 2026-10-23); provider "groq"
reads GROQ_API_KEY (free tier, $0; OpenAI-compatible endpoint). Keys are never printed or stored.
Standard library only.

$0 plan (--human-sample): judge only the 120 human-labelled items of step2/labeling_key.csv, which was drawn
from checker output before any judge ran. Results go to step2/human_sample_judgments.jsonl, one record per
(item, judge model). Calls are paced to the free per-minute token limit (--tpm). An item whose prompt plus
--max-out-tokens cannot fit in one minute's budget is recorded as "skipped_too_large" and not sent (Groq's
HTTP 413 is recorded the same way); --retry-skipped retries them. A daily-quota 429 stops the run;
re-running resumes. --round 2 judges the round-2 sample instead (step2r2/labeling_key_r2.csv ->
step2r2/human_sample_judgments_r2.jsonl, same prompt as round 1); round-1 files are not touched. Groq no longer serves the Llama 3.x models to this key (HTTP 404 on 2026-10-23), so the
defaults are the two remaining general models, each from the same family as one repairer (gpt-oss: OpenAI
like GPT-4; qwen: like Qwen); step3 reports agreement on out-of-family items separately.

Usage (from the Data folder):
  python -I experiment/scripts/step2_judge.py --key-info
  python -I experiment/scripts/step2_judge.py --dry-run
  python -I experiment/scripts/step2_judge.py --cap-usd 10
  python -I experiment/scripts/step2_judge.py --provider groq --human-sample --dry-run
  python -I experiment/scripts/step2_judge.py --provider groq --human-sample --model openai/gpt-oss-120b
  python -I experiment/scripts/step2_judge.py --provider groq --human-sample --model qwen/qwen3.8-27b
  python -I experiment/scripts/step2_judge.py --provider groq --human-sample --round 2 --model openai/gpt-oss-120b
  python -I experiment/scripts/step2_judge.py --provider groq --human-sample --round 2 --model qwen/qwen3.8-27b
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

csv.field_size_limit(10**9)

DATA = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ART = os.path.join(DATA, "experiment", "artifact")
STEP1 = os.path.join(DATA, "experiment", "step1")
OUT = os.path.join(DATA, "experiment", "step2")
API = "https://generativelanguage.googleapis.com/v1beta"
OPENROUTER = "https://openrouter.ai/api/v1"
GROQ = "https://api.groq.com/openai/v1"
KEY_NAMES = {"gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "groq": "GROQ_API_KEY"}
# Groq per-model request extras: keep reasoning short and out of the answer text
GROQ_EXTRA = {"openai/gpt-oss": {"reasoning_effort": "low", "include_reasoning": False},
              "qwen/": {"reasoning_effort": "none"}}
HUMAN_KEY = os.path.join(OUT, "labeling_key.csv")
HUMAN_JUDGMENTS = os.path.join(OUT, "human_sample_judgments.jsonl")
ROUND2 = {"key": os.path.join(DATA, "experiment", "step2r2", "labeling_key_r2.csv"),
          "judgments": os.path.join(DATA, "experiment", "step2r2", "human_sample_judgments_r2.jsonl")}
METHOD_PRIORITY = ["accessguru_final", "accessguru_first", "baseline_one", "baseline_two", "baseline_three"]
CHARS_PER_TOKEN = 3.0  # deliberately low, so token estimates run high
MAX_CHARS_PER_TOKEN = 4.5  # deliberately high: a prompt over the budget even at this ratio is certainly too large

RUBRIC = """You are an expert web accessibility auditor. A developer tool flagged an accessibility
violation in an HTML fragment taken from a real web page, and a repair was proposed. Decide whether
the repair TRULY fixes the violation.

A repair is "fixed" only if ALL of these hold:
1. It is concrete code that could replace the original fragment (not advice, a placeholder, or a
   description of what should be done).
2. It keeps the original element(s), their content and their purpose. Deleting, emptying, hiding
   (display:none, aria-hidden, etc.) or replacing the element with unrelated markup does NOT fix it.
3. It resolves the specific violation named below, as WCAG and the axe rule intend. For colour
   contrast, the new colours must plausibly meet the required ratio; if colours are given, check them.
4. It does not introduce a new accessibility barrier of similar or greater severity.

If the repair applies to only some of several affected elements, it is "not_fixed".
Use "unclear" only if the fragment genuinely lacks the information needed to decide.

Answer with JSON only:
{"verdict": "fixed" | "not_fixed" | "unclear",
 "failure_mode": "none" | "no_code" | "placeholder" | "element_removed_or_hidden" | "content_changed"
                 | "violation_remains" | "partial" | "new_barrier" | "other",
 "rationale": "<= 2 sentences"}
Use failure_mode "none" exactly when verdict is "fixed"."""


def load_key(provider):
    wanted = KEY_NAMES[provider]
    with open(os.path.join(DATA, ".env"), encoding="utf-8") as fh:
        for line in fh:
            name, _, value = line.strip().partition("=")
            if name.strip().removeprefix("export ").strip() == wanted:
                return value.strip().strip('"').strip("'")
    raise SystemExit(f"{wanted} not found in .env")


def auth_headers(provider, key):
    if provider == "gemini":
        return {"x-goog-api-key": key, "Content-Type": "application/json"}
    # Groq sits behind Cloudflare, which rejects urllib's default User-Agent
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "accessguru-study/1.0"}


def request(url, headers, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def judge_call(provider, model, prompt, max_out, headers, image_png_b64=None):
    """Returns (text, tokens_in, tokens_out, actual_cost_or_None). Optionally sends one PNG image after the text."""
    if provider == "gemini":
        parts = [{"text": prompt}]
        if image_png_b64:
            parts.append({"inlineData": {"mimeType": "image/png", "data": image_png_b64}})
        body = {"contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "maxOutputTokens": max_out}}
        res = request(f"{API}/models/{model}:generateContent", headers, body)
        usage = res.get("usageMetadata", {})
        try:
            text = res["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = None
        return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0), None
    content = prompt
    if image_png_b64:
        content = [{"type": "text", "text": prompt},
                   {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_png_b64}"}}]
    body = {"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0,
            "max_tokens": max_out, "response_format": {"type": "json_object"}}
    if provider == "groq":
        body.update(next((v for k, v in GROQ_EXTRA.items() if model.startswith(k)), {}))
        res = request(f"{GROQ}/chat/completions", headers, body)
        usage = res.get("usage", {})
        try:
            text = res["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            text = None
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), 0.0
    body["usage"] = {"include": True}
    res = request(f"{OPENROUTER}/chat/completions", headers, body)
    usage = res.get("usage", {})
    try:
        text = res["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        text = None
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("cost")


class TooLarge(Exception):
    """HTTP 413: the request is larger than the per-minute token limit."""


class JsonFailed(Exception):
    """Groq HTTP 400 json_validate_failed: the answer hit max_tokens before the JSON was complete."""


def call_with_retry(provider, model, prompt, max_out, headers, image_png_b64=None):
    """judge_call with backoff for demand spikes (429/500/503) and network blips; other errors stop the run."""
    for attempt in range(8):
        try:
            return judge_call(provider, model, prompt, max_out, headers, image_png_b64)
        except urllib.error.HTTPError as e:
            err = e.read()[:300].decode("utf-8", "replace")
            if e.code == 413 or "request too large" in err.lower():
                raise TooLarge(err)
            if e.code == 400 and "json_validate_failed" in err:
                raise JsonFailed(err)
            retry_after = e.headers.get("retry-after")
            if e.code == 429 and retry_after and float(retry_after) > 600:
                raise SystemExit(f"HTTP 429: quota used up, the provider asks to wait {float(retry_after) / 3600:.1f} h. "
                                 "Re-run later; finished judgments are kept.")
            if e.code in (429, 500, 503) and attempt < 7:
                wait = float(retry_after) + 1 if retry_after else min(300, 15 * 2 ** attempt)
                print(f"HTTP {e.code}, retrying in {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise SystemExit(f"HTTP {e.code}: {err!r}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 7:
                wait = min(300, 15 * 2 ** attempt)
                print(f"network error ({e}), retrying in {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise SystemExit(f"network error: {e}")


def parse_verdict(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`").removeprefix("json").strip()
    return json.loads(t)


def load_sample():
    return [r for r in csv.DictReader(open(os.path.join(ART, "data/accessguru_dataset/accessguru_sampled_syntax_layout_dataset.csv"),
                                           encoding="utf-8-sig", newline="")) if r["category"].strip() in ("Syntax", "Layout")]


def make_prompt(s, resp):
    return (f"{RUBRIC}\n\nAXE RULE: {s['violationnumberID'].strip()}\n"
            f"RULE DESCRIPTION: {s['description'].strip()}\n"
            f"AXE FAILURE SUMMARY: {s['failureSummary'].strip() or '(none)'}\n\n"
            f"ORIGINAL FRAGMENT:\n<<<\n{s['affectedHTMLElement(s)']}\n>>>\n\n"
            f"PROPOSED REPAIR:\n<<<\n{resp}\n>>>")


def build_items(step1):
    sample = load_sample()
    seen, items = {}, []
    for line in open(os.path.join(step1, "responses.jsonl"), encoding="utf-8"):
        j = json.loads(line)
        s = sample[j["row"]]
        resp = j["response"]
        key = hashlib.sha256(f'{j["row"]}\x00{resp}'.encode("utf-8")).hexdigest()[:20]
        j["judge_key"] = key
        if key not in seen and resp.strip():
            seen[key] = {
                "judge_key": key, "row": j["row"], "method": j["method"],
                "prompt": make_prompt(s, resp),
            }
        items.append(j)
    unique = list(seen.values())
    random.Random(20261022).shuffle(unique)
    best = {}
    for j in items:
        if j["judge_key"] in seen:
            p = METHOD_PRIORITY.index(j["method"])
            best[j["judge_key"]] = min(p, best.get(j["judge_key"], p))
    for u in unique:
        u["method"] = METHOD_PRIORITY[best[u["judge_key"]]]  # highest-priority method that uses this response
    unique.sort(key=lambda u: best[u["judge_key"]])
    return items, unique


def run_human_sample(a):
    """Judge the 120 human-sample items with one model, paced to the free per-minute token limit. $0 on Groq."""
    if not os.path.exists(HUMAN_KEY):
        raise SystemExit(f"{HUMAN_KEY} missing: build the human sample first (step2h_labeling.py make / step2h_labeling_r2.py sample).")
    sample = load_sample()
    responses = {(r["model"], r["row"]): r["response"] for r in map(json.loads, open(os.path.join(a.step1_dir, "responses.jsonl"), encoding="utf-8"))
                 if r["method"] == "accessguru_final"}
    todo_all = []
    for k in csv.DictReader(open(HUMAN_KEY, encoding="utf-8")):
        prompt = make_prompt(sample[int(k["row"])], responses[(k["model"], int(k["row"]))])
        todo_all.append({"item_id": k["item_id"], "prompt": prompt, "est_tokens": int(len(prompt) / a.chars_per_token),
                         "min_tokens": int(len(prompt) / MAX_CHARS_PER_TOKEN)})

    done = {}
    if os.path.exists(HUMAN_JUDGMENTS):
        for line in open(HUMAN_JUDGMENTS, encoding="utf-8"):
            r = json.loads(line)
            if r["judge_model"] == a.model:
                done[r["item_id"]] = r  # later records override earlier ones
    retry = {"skipped_too_large", "judge_error"} if a.retry_skipped else {"judge_error"}
    todo = [u for u in todo_all if u["item_id"] not in done or done[u["item_id"]]["verdict"] in retry]
    budget = a.tpm - a.max_out_tokens
    too_big = [u for u in todo if u["min_tokens"] > budget]
    maybe = [u for u in todo if u["est_tokens"] > budget and u not in too_big]
    print(f"judge {a.provider}:{a.model}; human sample {len(todo_all)} items, done {len(done)}, to do {len(todo)}")
    print(f"per-minute budget for the prompt: {budget} tokens (tpm {a.tpm} - max out {a.max_out_tokens})")
    print(f"  certainly too large (skipped, not sent): {len(too_big)} {[u['item_id'] for u in too_big]}")
    print(f"  borderline (sent; the provider's 413 decides): {len(maybe)} {[u['item_id'] for u in maybe]}")
    if a.dry_run:
        return
    if a.limit:
        todo = todo[: a.limit]

    headers = auth_headers(a.provider, load_key(a.provider))
    window = collections.deque()  # (time, tokens) of calls in the last 60 s
    with open(HUMAN_JUDGMENTS, "a", encoding="utf-8") as fh:
        def write(rec):
            fh.write(json.dumps({"item_id": u["item_id"], "provider": a.provider, "judge_model": a.model, **rec}, ensure_ascii=False) + "\n")
            fh.flush()

        for n, u in enumerate(todo):
            if u["min_tokens"] > budget:
                write({"verdict": "skipped_too_large", "est_tokens": u["est_tokens"],
                       "rationale": f"prompt >= ~{u['min_tokens']} tokens > {budget}"})
                print(f"{n + 1}/{len(todo)} {u['item_id']} skipped_too_large (>= ~{u['min_tokens']} tokens)", flush=True)
                continue
            need = min(a.tpm, u["est_tokens"] + a.max_out_tokens)
            while True:
                now = time.time()
                while window and now - window[0][0] > 60:
                    window.popleft()
                if sum(t for _, t in window) + need <= a.tpm:
                    break
                time.sleep(max(1.0, 61 - (now - window[0][0])))
            try:
                try:
                    text, tin, tout, _ = call_with_retry(a.provider, a.model, u["prompt"], a.max_out_tokens, headers)
                except JsonFailed:  # one retry with more room, if the per-minute budget allows it
                    window.append((time.time(), need))
                    more = min(3 * a.max_out_tokens, a.tpm - u["est_tokens"])
                    if more <= a.max_out_tokens:
                        raise
                    print(f"{u['item_id']} answer cut off; retrying with max {more} output tokens", flush=True)
                    time.sleep(61)
                    text, tin, tout, _ = call_with_retry(a.provider, a.model, u["prompt"], more, headers)
            except TooLarge as e:
                window.append((time.time(), 0))
                write({"verdict": "skipped_too_large", "est_tokens": u["est_tokens"], "rationale": f"HTTP 413: {e}"[:300]})
                print(f"{n + 1}/{len(todo)} {u['item_id']} skipped_too_large (HTTP 413)", flush=True)
                continue
            except JsonFailed as e:
                write({"verdict": "judge_error", "rationale": f"answer cut off before valid JSON: {e}"[:300]})
                print(f"{n + 1}/{len(todo)} {u['item_id']} judge_error (answer cut off)", flush=True)
                continue
            window.append((time.time(), max(tin + tout, need)))
            try:
                verdict = parse_verdict(text)
            except (json.JSONDecodeError, AttributeError):
                verdict = {"verdict": "judge_error", "rationale": (text or "")[:300]}
            if verdict.get("verdict") not in ("fixed", "not_fixed", "unclear"):
                verdict = {"verdict": "judge_error", "rationale": json.dumps(verdict)[:300]}
            write({"verdict": verdict.get("verdict"), "failure_mode": verdict.get("failure_mode"),
                   "rationale": verdict.get("rationale"), "tokens_in": tin, "tokens_out": tout, "cost_usd": 0.0})
            print(f"{n + 1}/{len(todo)} {u['item_id']} {verdict.get('verdict')}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["openrouter", "gemini", "groq"], default="openrouter")
    ap.add_argument("--model", default=None, help="default: google/gemini-3.8-flash; with --provider groq: openai/gpt-oss-120b")
    ap.add_argument("--human-sample", action="store_true", help="$0 plan: judge only the 120 items in step2/labeling_key.csv")
    ap.add_argument("--round", type=int, choices=[1, 2], default=1, help="--human-sample: 2 = round-2 sample in step2r2/")
    ap.add_argument("--tpm", type=int, default=8000, help="free-tier tokens per minute (Groq: 8000 on 2026-10-23)")
    ap.add_argument("--chars-per-token", type=float, default=3.2, help="prompt size estimate for pacing and skipping")
    ap.add_argument("--limit", type=int, default=0, help="judge at most this many items (0 = all)")
    ap.add_argument("--retry-skipped", action="store_true", help="retry items recorded as skipped_too_large")
    ap.add_argument("--cap-usd", type=float, default=10.0)
    ap.add_argument("--price-in", type=float, default=0.825, help="USD per 1M input tokens (OpenRouter list price, 2026-10-23)")
    ap.add_argument("--price-out", type=float, default=4.125, help="USD per 1M output tokens, thinking included")
    ap.add_argument("--max-out-tokens", type=int, default=4096)
    ap.add_argument("--step1-dir", default=STEP1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--key-info", action="store_true", help="OpenRouter credit limit and usage (no key printed)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.model is None:
        a.model = "openai/gpt-oss-120b" if a.provider == "groq" else "google/gemini-3.8-flash"
    if a.human_sample:
        if a.round == 2:
            global HUMAN_KEY, HUMAN_JUDGMENTS
            HUMAN_KEY, HUMAN_JUDGMENTS = ROUND2["key"], ROUND2["judgments"]
        if a.max_out_tokens == 4096:  # the paid-run default; free per-minute limits need a smaller reservation
            a.max_out_tokens = 600  # verdicts used ~120 output tokens in the 2026-10-23 test
        return run_human_sample(a)
    if a.provider == "groq":
        raise SystemExit("--provider groq is for the $0 plan: add --human-sample")

    if a.key_info:
        d = request(f"{OPENROUTER}/key", auth_headers("openrouter", load_key("openrouter"))).get("data", {})
        print({k: d.get(k) for k in ("limit", "limit_remaining", "usage", "is_free_tier")})
        return
    if a.list_models:
        res = request(f"{API}/models?pageSize=200", auth_headers("gemini", load_key("gemini")))
        for m in res.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print(m["name"].removeprefix("models/"))
        return

    items, unique = build_items(a.step1_dir)
    with open(os.path.join(OUT, "items.jsonl"), "w", encoding="utf-8") as fh:
        for j in items:
            fh.write(json.dumps({k: j[k] for k in ("model", "method", "row", "judge_key")}) + "\n")

    cache_path = os.path.join(OUT, "judgments.jsonl")
    done = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            r = json.loads(line)
            done[r["judge_key"]] = r
    todo = [u for u in unique if u["judge_key"] not in done]
    spent = sum(r.get("cost_usd", 0) for r in done.values())

    def worst_cost(u):
        return len(u["prompt"]) / CHARS_PER_TOKEN * a.price_in / 1e6 + a.max_out_tokens * a.price_out / 1e6

    def typical_cost(u):  # assumes ~1,500 output tokens including thinking
        return len(u["prompt"]) / CHARS_PER_TOKEN * a.price_in / 1e6 + 1500 * a.price_out / 1e6

    est_all = sum(worst_cost(u) for u in todo)
    print(f"items: {len(items)} (empty responses skipped: {sum(not j['response'].strip() for j in items)})")
    print(f"unique judgments: {len(unique)}, already done: {len(done)}, to do: {len(todo)}")
    print(f"spent so far: ${spent:.2f}; worst-case cost of the rest: ${est_all:.2f} (cap ${a.cap_usd:.2f})")
    for m in METHOD_PRIORITY:
        sub = [u for u in todo if u["method"] == m]
        print(f"  {m:17s} {len(sub):4d} judgments, typical ${sum(typical_cost(u) for u in sub):6.2f}, worst case ${sum(worst_cost(u) for u in sub):6.2f}")
    if a.dry_run:
        return

    headers = auth_headers(a.provider, load_key(a.provider))
    with open(cache_path, "a", encoding="utf-8") as fh:
        for n, u in enumerate(todo):
            if spent + worst_cost(u) > a.cap_usd:
                print(f"STOP: next call could exceed the ${a.cap_usd:.2f} cap (spent ${spent:.2f}). {len(todo) - n} left.")
                break
            text, tin, tout, actual = call_with_retry(a.provider, a.model, u["prompt"], a.max_out_tokens, headers)
            cost = actual if actual is not None else tin * a.price_in / 1e6 + tout * a.price_out / 1e6
            spent += cost
            try:
                verdict = parse_verdict(text)
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
