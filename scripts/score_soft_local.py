#!/usr/bin/env python3
"""
Soft constraint scoring: 本地并发调 GPT-5 做 LLM judge
增量写入，支持断点续跑

用法:
  nohup python3 scripts/score_soft_local.py &
"""
import json, sys, re, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import importlib, verifier.registry, verifier.rubric_runner
importlib.reload(verifier.registry)
importlib.reload(verifier.rubric_runner)

from ref_local_gpt import get_gpt_response
from verifier.rubric_runner import build_judge_prompt

JUDGE_MODEL = "gpt-5-2025-08-07"
MAX_WORKERS = 3
RESPONSE_FILE = Path("/Users/minimax/Desktop/respose_by_gpt5_4.jsonl")
OUT_PATH = REPO / "data" / "scores" / "soft_scores.jsonl"

# Load responses
with open(RESPONSE_FILE) as f:
    data = [json.loads(line) for line in f]

# Collect soft tasks
tasks = []
for d in data:
    vo = d["vulcan_output"]
    response = vo.get("response", "")
    query = d["messages"][0]["content"] if d.get("messages") else ""
    for c in d.get("constraints", []):
        cid = c["constraint_id"]
        if cid.startswith(("GS", "FS")):
            tasks.append({
                "sample_id": d.get("sample_id", vo.get("sample_id")),
                "constraint_id": cid,
                "rendered_text": c.get("rendered_text", ""),
                "query": query,
                "response": response,
            })

# Resume: skip already done
done_keys = set()
if OUT_PATH.exists():
    with open(OUT_PATH) as f:
        for line in f:
            r = json.loads(line)
            done_keys.add(f"{r['sample_id']}_{r['constraint_id']}")

remaining = [t for t in tasks if f"{t['sample_id']}_{t['constraint_id']}" not in done_keys]
print(f"Total: {len(tasks)}, Done: {len(done_keys)}, Remaining: {len(remaining)}")

def score_one(task):
    try:
        prompt_data = build_judge_prompt(
            task["constraint_id"], task["query"], task["response"],
            rendered_constraint_text=task["rendered_text"])
        messages = [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": prompt_data["user"]},
        ]
        raw = get_gpt_response(messages, JUDGE_MODEL, temperature=0, max_tokens=512)
        score, passed, reason = None, None, ""
        if raw:
            # Try multiple extraction strategies
            text = raw.strip()
            # Strip markdown code block
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            # Try full parse first
            try:
                p = json.loads(text)
                score, passed, reason = p.get("score"), p.get("passed"), p.get("reason", "")
            except:
                # Fallback: find any JSON object (allow nested braces)
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if m:
                    try:
                        p = json.loads(m.group())
                        score, passed, reason = p.get("score"), p.get("passed"), p.get("reason", "")
                    except:
                        reason = f"JSON parse failed"
        return {"sample_id": task["sample_id"], "constraint_id": task["constraint_id"],
                "rendered_text": task["rendered_text"], "score": score, "passed": passed,
                "reason": reason, "raw_response": (raw or "")[:500],
                "status": "pass" if passed else ("fail" if passed is False else "error")}
    except Exception as e:
        return {"sample_id": task["sample_id"], "constraint_id": task["constraint_id"],
                "score": None, "passed": None, "reason": str(e), "raw_response": "",
                "status": "error"}

# Run
start = time.time()
with open(OUT_PATH, "a") as fout:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(score_one, t): t for t in remaining}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")
            fout.flush()
            if done % 10 == 0:
                elapsed = time.time() - start
                eta = elapsed / done * (len(remaining) - done)
                print(f"  {done}/{len(remaining)} ({elapsed:.0f}s elapsed, ETA {eta:.0f}s)", flush=True)

elapsed = time.time() - start
print(f"\nDone. {done} scored in {elapsed:.0f}s")
