"""Full run: all 186 cases for each model (resumable), then scoring. Log: logs/run_all.log.

Usage (from the Data folder): .venv/Scripts/python.exe -I experiment/extra_models/scripts/run_all.py
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
XM = os.path.dirname(HERE)
EXP = os.path.dirname(XM)
ORDER = ["hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M", "hf.co/bartowski/OpenGVLab_InternVL3_5-2B-GGUF:Q4_K_M",
         "llama3.2:3b", "qwen3.5:4b", "openbmb/minicpm-v4.5:8b"]  # fastest first, so partial results come early

with open(os.path.join(XM, "logs", "run_all.log"), "a", encoding="utf-8", buffering=1) as log:
    def say(msg):
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

    say("start")
    for m in ORDER:
        say(f"model {m}")
        rc = subprocess.call([sys.executable, "-I", os.path.join(HERE, "gen_repairs.py"), m], stdout=log, stderr=subprocess.STDOUT)
        say(f"model {m} exit {rc}")
    say("scoring")
    rc = subprocess.call([sys.executable, "-I", os.path.join(HERE, "score.py"), EXP], stdout=log, stderr=subprocess.STDOUT)
    say(f"scoring exit {rc}")
    say("ALL DONE")
