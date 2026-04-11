"""
评分主脚本：读 Vulcan 回复 → hard 约束跑 rule checker → soft 约束调 LLM judge → 汇总输出

用法：
    python3 scripts/score_responses.py \
        --responses vulcan/eval_response_test/test_response.jsonl \
        --output data/scores/test_scores.json \
        --judge-model gpt-4o-2024-11-20 \
        --max-workers 8
"""

import argparse
import importlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from verifier.rubric_runner import JUDGE_SYSTEM_PROMPT, build_judge_prompt

# ---------------------------------------------------------------------------
# Minimax proxy config (from user's existing setup)
# ---------------------------------------------------------------------------

MINIMAX_PROXY_URL = "http://thirdpart-proxy-prod.xaminim.com/v1/proxy"

MODEL_MAP_TOKEN = {
    "gpt-4o-2024-11-20": (
        "Jctaakf7hHX9oml-pUYXcsYjUVgMceKZIP202DzBZ3FOCfl2nKNNu3v0V6M-wuKiQ-H5piAl1Ysti4Eql953Wn-dK3WGBHThqj8NkeBj_jV_7M4E9qhDAHkcavmJxMJmdXPiBRBeZYrEaatvHvsmOw==",
        "5e08875459232e487e6c55a177c6f7b0f68ecca4acc3dd1e827e2fb544fd1507",
    ),
    "chatgpt-4o-latest": (
        "Ai4p2ITp1bBbxozFec0Qg0z6o1HxP5Cl68X9htQVJwqQVHitMZp3D5vQBJbY2Qbgi1jR1pT8kkNxeDt5PUciQCF3R53daG4IJPJVZvUhudUrb0jdFGyIlqkKgQJvVIn2QaxQyU1RvvHLYUd_hgw2pA==",
        "610e4bc50a3c533b5401370fe126b36741872487460328603007d0c014158740",
    ),
    "claude-sonnet-4-20250514": (
        "7ENu46Lrftpy1s-mjdEJQvzc94KTrDEzVCBh2otsJg-MvF_4gBLCOV3SKS77rfrnkFnmQkDOsx5ueztCwMynRK4gzmY1T1crPtrW-v6VE58geYfYPWvaFaolRMYZ8RY6V3GjJgXRhG7QuBch-9MM7Q==",
        "610e4bc50a3c533b5401370fe126b36741872487460328603007d0c014158740",
    ),
}


def call_minimax_proxy(messages, model, temperature=0, max_tokens=512, max_retries=3, timeout_sec=120):
    """Call LLM via minimax proxy."""
    if model not in MODEL_MAP_TOKEN:
        raise ValueError(f"Model {model} not in MODEL_MAP_TOKEN")
    token, billing_token = MODEL_MAP_TOKEN[model]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Content-Type": "application/json;",
        "minimax_token": token,
        "billing_token": billing_token,
        "Accept-Encoding": "deflate",
    }

    import requests as req_lib

    for attempt in range(1, max_retries + 1):
        try:
            resp = req_lib.post(MINIMAX_PROXY_URL, headers=headers, json=payload, timeout=timeout_sec)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp_data = resp.json()
            if "error" in resp_data:
                raise ValueError(f"API error: {resp_data['error']}")
            return resp_data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)
    return None


# ---------------------------------------------------------------------------
# Hard constraint scoring (local rule checkers)
# ---------------------------------------------------------------------------

_rule_module_cache = {}


def load_rule_module(constraint_id):
    if constraint_id not in _rule_module_cache:
        module_name = f"verifier.rules.{constraint_id.replace('-', '_') if '-' in constraint_id else constraint_id}"
        # Use importlib to handle hyphenated module names
        spec_path = REPO_ROOT / "verifier" / "rules" / f"{constraint_id}.py"
        spec = importlib.util.spec_from_file_location(module_name, spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _rule_module_cache[constraint_id] = mod
    return _rule_module_cache[constraint_id]


def score_hard_constraint(constraint_id, response_text, constraint_info):
    """Score a hard constraint using rule checker. Returns dict with score details."""
    mod = load_rule_module(constraint_id)
    params = constraint_info.get("filled_params") or {}
    result = mod.check(response_text, params)
    return {
        "constraint_id": constraint_id,
        "type": "hard",
        "check_mode": "rule",
        "score": result.score,
        "passed": result.passed,
        "status": result.status,
        "message": result.message,
        "evidence": result.evidence,
    }


# ---------------------------------------------------------------------------
# Soft constraint scoring (LLM judge)
# ---------------------------------------------------------------------------

def score_soft_constraint(constraint_id, query_text, response_text, constraint_info, model, rendered_text=None):
    """Score a soft constraint using LLM judge. Returns dict with score details."""
    prompt_data = build_judge_prompt(
        constraint_id,
        query_text,
        response_text,
        rendered_constraint_text=rendered_text,
    )

    messages = [
        {"role": "system", "content": prompt_data["system"]},
        {"role": "user", "content": prompt_data["user"]},
    ]

    raw = call_minimax_proxy(messages, model=model, temperature=0, max_tokens=512)

    # Parse JSON from response
    score = None
    passed = None
    reason = ""
    evidence = []

    try:
        # Try to extract JSON from response
        json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            score = parsed.get("score")
            passed = parsed.get("passed")
            reason = parsed.get("reason", "")
            evidence = parsed.get("evidence", [])
    except (json.JSONDecodeError, AttributeError):
        reason = f"JSON parse failed: {raw[:200]}"

    return {
        "constraint_id": constraint_id,
        "type": "soft",
        "check_mode": "LLM-as-a-judge",
        "score": score,
        "passed": passed,
        "status": "pass" if passed else ("fail" if passed is False else "error"),
        "message": reason,
        "evidence": evidence,
        "raw_judge_response": raw,
    }


# ---------------------------------------------------------------------------
# Main scoring pipeline
# ---------------------------------------------------------------------------

def load_responses(path):
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            vo = record["vulcan_output"]
            samples.append({
                "sample_id": vo["sample_id"],
                "query_id": vo["query_id"],
                "split": vo["split"],
                "track": vo["track"],
                "query_input": vo["query_input"],
                "response_text": vo["response_text"],
                "constraints": vo["constraints"],
                "constraint_ids": vo["constraint_ids"],
                "source_type": vo.get("source_type"),
                "role_mode": vo.get("role_mode"),
            })
    return samples


def score_sample(sample, judge_model):
    """Score all constraints in a single sample."""
    results = []
    for c in sample["constraints"]:
        cid = c["id"]
        ctype = c["type"]
        if ctype == "hard":
            result = score_hard_constraint(cid, sample["response_text"], c)
        else:
            rendered = c.get("text", None)
            result = score_soft_constraint(
                cid, sample["query_input"], sample["response_text"], c,
                model=judge_model, rendered_text=rendered,
            )
        results.append(result)

    # Aggregate
    hard_scores = [r["score"] for r in results if r["type"] == "hard" and r["score"] is not None]
    soft_scores = [r["score"] for r in results if r["type"] == "soft" and r["score"] is not None]

    hard_mean = sum(hard_scores) / len(hard_scores) if hard_scores else None
    soft_mean = sum(soft_scores) / len(soft_scores) if soft_scores else None

    if hard_mean is not None and soft_mean is not None:
        sample_score = (hard_mean + soft_mean) / 2
    elif hard_mean is not None:
        sample_score = hard_mean
    elif soft_mean is not None:
        sample_score = soft_mean
    else:
        sample_score = None

    return {
        "sample_id": sample["sample_id"],
        "query_id": sample["query_id"],
        "split": sample["split"],
        "track": sample["track"],
        "source_type": sample.get("source_type"),
        "role_mode": sample.get("role_mode"),
        "n_constraints": len(sample["constraints"]),
        "n_hard": len(hard_scores),
        "n_soft": len(soft_scores),
        "hard_mean": round(hard_mean, 2) if hard_mean is not None else None,
        "soft_mean": round(soft_mean, 2) if soft_mean is not None else None,
        "sample_score": round(sample_score, 2) if sample_score is not None else None,
        "constraint_results": results,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Score model responses against constraints.")
    parser.add_argument("--responses", type=Path, required=True, help="Vulcan response JSONL")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "scores" / "test_scores.json")
    parser.add_argument("--judge-model", default="gpt-4o-2024-11-20")
    parser.add_argument("--max-workers", type=int, default=8, help="Parallel workers for soft judge calls")
    parser.add_argument("--limit", type=int, default=0, help="Limit samples for testing")
    return parser.parse_args()


def main():
    args = parse_args()
    samples = load_responses(args.responses)
    if args.limit:
        samples = samples[:args.limit]

    print(f"Loaded {len(samples)} samples")
    print(f"Judge model: {args.judge_model}")

    # Score hard constraints first (fast, local)
    hard_count = sum(1 for s in samples for c in s["constraints"] if c["type"] == "hard")
    soft_count = sum(1 for s in samples for c in s["constraints"] if c["type"] == "soft")
    print(f"Hard constraints to score: {hard_count} (local)")
    print(f"Soft constraints to score: {soft_count} (API)")

    # Score all samples with parallel soft constraint calls
    scored = []
    errors = []

    def process_sample(sample):
        try:
            return score_sample(sample, args.judge_model)
        except Exception as e:
            return {"sample_id": sample["sample_id"], "error": str(e)}

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {pool.submit(process_sample, s): s for s in samples}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if "error" in result:
                errors.append(result)
                print(f"ERROR {result['sample_id']}: {result['error']}")
            else:
                scored.append(result)
            if done % 20 == 0:
                print(f"progress {done}/{len(samples)}")

    # Sort by sample_id
    scored.sort(key=lambda x: x["sample_id"])

    # Aggregate stats
    track_stats = {}
    for s in scored:
        track = s["track"]
        if track not in track_stats:
            track_stats[track] = {"hard_scores": [], "soft_scores": [], "sample_scores": [], "count": 0}
        track_stats[track]["count"] += 1
        if s["hard_mean"] is not None:
            track_stats[track]["hard_scores"].append(s["hard_mean"])
        if s["soft_mean"] is not None:
            track_stats[track]["soft_scores"].append(s["soft_mean"])
        if s["sample_score"] is not None:
            track_stats[track]["sample_scores"].append(s["sample_score"])

    summary = {}
    for track, stats in sorted(track_stats.items()):
        summary[track] = {
            "count": stats["count"],
            "hard_mean": round(sum(stats["hard_scores"]) / len(stats["hard_scores"]), 2) if stats["hard_scores"] else None,
            "soft_mean": round(sum(stats["soft_scores"]) / len(stats["soft_scores"]), 2) if stats["soft_scores"] else None,
            "sample_mean": round(sum(stats["sample_scores"]) / len(stats["sample_scores"]), 2) if stats["sample_scores"] else None,
        }

    output = {
        "meta": {
            "judge_model": args.judge_model,
            "response_file": str(args.responses),
            "total_samples": len(scored),
            "total_errors": len(errors),
            "hard_constraints_scored": hard_count,
            "soft_constraints_scored": soft_count,
        },
        "summary": summary,
        "scores": scored,
        "errors": errors,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDone. {len(scored)} scored, {len(errors)} errors.")
    print(f"Output: {args.output}")
    print("\nSummary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
