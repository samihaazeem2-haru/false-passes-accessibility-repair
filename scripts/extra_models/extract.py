"""Free, deterministic replacement for the paper's LLM-based HTML extractor (filter_extract_llm_responses.py asked
open-mistral-7b to "Extract the last HTML code snippet"). Applied identically to the new models and, for
re-extraction, to the published GPT-4 / Mistral / Qwen raw replies.

Order (first rule that yields markup wins):
  1. the last ###albidaya### ... ###alnihaya### block that contains an HTML tag
  2. text after the last ###albidaya### when no closing marker follows (cut-off reply)
  3. the last fenced ``` block that contains an HTML tag
  4. from the first "<tag" to the last ">" in the reply
  5. otherwise the text of the last marker block, or the whole reply (no markup: flagged no-HTML, as in the
     published files); "" only when the reply itself is empty
Code fences inside the result are removed.
"""
import re

TAG = re.compile(r"<[a-zA-Z!/]")
FENCE_LINE = re.compile(r"^\s*```[\w-]*\s*$", re.M)


def _clean(t):
    return FENCE_LINE.sub("", t).strip()


def extract(reply):
    # deviation 3 (PLAN): reasoning in <think> blocks is not part of the reply; an unclosed <think> runs to the end
    reply = re.sub(r"<think>.*?(</think>|$)", "", reply or "", flags=re.S)
    blocks = [b for b in re.findall(r"###albidaya###(.*?)###alnihaya###", reply, re.S) if TAG.search(b)]
    if blocks:
        return _clean(blocks[-1])
    k = reply.rfind("###albidaya###")
    if k >= 0 and "###alnihaya###" not in reply[k:] and TAG.search(reply[k:]):
        tail = reply[k + len("###albidaya###"):]
        return _clean(tail.split("```")[0] if tail.count("```") % 2 else tail)
    fenced = [b for b in re.findall(r"```[\w-]*\n(.*?)```", reply, re.S) if TAG.search(b)]
    if fenced:
        return _clean(fenced[-1])
    m = TAG.search(reply)
    if m:
        end = reply.rfind(">")
        if end > m.start():
            return reply[m.start():end + 1].strip()
    marked = re.findall(r"###albidaya###(.*?)###alnihaya###", reply, re.S)
    return _clean(marked[-1] if marked else reply)
