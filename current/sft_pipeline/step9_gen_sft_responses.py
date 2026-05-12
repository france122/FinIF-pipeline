#!/usr/bin/env python3
"""
Step 9: 1Q多A Teacher Response 生成 + 择优
为训练数据生成 teacher model 回复，每条 prompt 生成 N 个候选回复，
用 hidden_checkers 评分后选最优作为 SFT ground-truth。

用法:
  # 为 benchmark 生成 teacher responses（单条）
  python step9_gen_sft_responses.py --mode benchmark --model gpt-5-2025-08-07

  # 为训练数据生成 1Q多A responses
  python step9_gen_sft_responses.py --mode training --model gpt-5-2025-08-07 --n 3

  # 续跑（自动跳过已完成的 sample）
  python step9_gen_sft_responses.py --mode training --model gpt-5-2025-08-07 --n 3 --resume
"""
import json
import os
import sys
import argparse
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
sys.path.insert(0, CURRENT_DIR)

from gpt_call_all import get_gpt_response
import checkers

SYSTEM_PROMPT = "你是一位专业的金融分析助手。请严格按照用户的附加要求（格式、字数、内容约束等）完成分析任务。所有计算需展示过程，数据引用需准确标注来源。"

REASONING_MODELS = {"gpt-5-2025-08-07", "o3-2025-04-16", "o3-mini", "o1-2024-12-17"}


def gen_one_response(prompt, model, temperature, max_tokens):
    effective_max_tokens = 16384 if model in REASONING_MODELS else max_tokens
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    resp = get_gpt_response(
        messages=messages,
        model_version=model,
        temperature=temperature,
        max_tokens=effective_max_tokens,
        max_try=5,
    )
    return resp


def run_hidden_checkers(response, hidden_checkers_list):
    if not hidden_checkers_list or not response:
        return 0, 0, []
    results = []
    for hc in hidden_checkers_list:
        checker_name = hc.get("checker", "")
        params = hc.get("params", None)
        fn = getattr(checkers, checker_name, None)
        if fn is None:
            results.append({"checker": checker_name, "pass": False, "error": "not found"})
            continue
        try:
            passed = fn(response, params)
            results.append({"checker": checker_name, "pass": bool(passed)})
        except Exception as e:
            results.append({"checker": checker_name, "pass": False, "error": str(e)})
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    return passed, total, results


# ============================================================
# Mode 1: Benchmark responses
# ============================================================

def run_benchmark(model, temperature, max_tokens, workers):
    benchmark_path = os.path.join(CURRENT_DIR, "benchmark", "benchmark_all.json")
    output_dir = os.path.join(CURRENT_DIR, "benchmark", "scores")
    os.makedirs(output_dir, exist_ok=True)

    with open(benchmark_path, encoding="utf-8") as f:
        data = json.load(f)
    cases = data["cases"]
    print(f"Loaded {len(cases)} benchmark cases")

    short = model.replace("/", "_")
    out_path = os.path.join(output_dir, f"responses_{short}.jsonl")

    existing_ids = set()
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_ids.add(json.loads(line)["case_id"])

    todo = [c for c in cases if c["case_id"] not in existing_ids]
    print(f"Already done: {len(existing_ids)}, Todo: {len(todo)}")

    if not todo:
        print("All benchmark cases done!")
        return

    done = 0
    failed = 0

    def process(case):
        try:
            resp = gen_one_response(case["prompt"], model, temperature, max_tokens)
            if resp is None:
                return case["case_id"], None, "API returned None"
            return case["case_id"], resp, None
        except Exception as e:
            return case["case_id"], None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(process, c): c for c in todo}
        for future in as_completed(future_map):
            case = future_map[future]
            case_id, resp, err = future.result()
            if resp is not None:
                record = {
                    "case_id": case_id,
                    "model": model,
                    "response": resp,
                    "context": case.get("context", ""),
                }
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                done += 1
                print(f"  [{done+failed}/{len(todo)}] {case_id} OK ({len(resp)} chars)")
            else:
                failed += 1
                print(f"  [{done+failed}/{len(todo)}] {case_id} FAILED: {err}")

    print(f"\nBenchmark done: {done} OK, {failed} failed → {out_path}")
    print(f"Next: python eval_responses.py --models {short}")


# ============================================================
# Mode 2: Training 1Q多A
# ============================================================

def run_training(model, n_candidates, temperature, max_tokens, workers, resume):
    input_path = os.path.join(DATA_DIR, "sft_train_2000.jsonl")
    output_path = os.path.join(DATA_DIR, f"sft_train_responses_{model.replace('/', '_')}.jsonl")
    candidates_path = os.path.join(DATA_DIR, f"sft_candidates_{model.replace('/', '_')}.jsonl")

    samples = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    print(f"Loaded {len(samples)} training samples")

    done_ids = set()
    if resume and os.path.isfile(output_path):
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["sample_id"])
        print(f"Resuming: {len(done_ids)} already done")

    todo = [s for s in samples if s["metadata"]["sample_id"] not in done_ids]
    print(f"Todo: {len(todo)} samples, {n_candidates} candidates each")

    if not todo:
        print("All training samples done!")
        return

    stats = Counter()

    def process_one(sample):
        meta = sample["metadata"]
        prompt = sample["messages"][1]["content"]
        hidden = meta.get("hidden_checkers", [])
        sample_id = meta["sample_id"]

        candidates = []
        for i in range(n_candidates):
            resp = gen_one_response(prompt, model, temperature, max_tokens)
            if resp is None:
                continue
            passed, total, details = run_hidden_checkers(resp, hidden)
            candidates.append({
                "index": i,
                "response": resp,
                "passed": passed,
                "total": total,
                "score": passed / total if total > 0 else 1.0,
                "details": details,
                "char_len": len(resp),
            })

        if not candidates:
            return sample_id, None, "all candidates failed"

        best = max(candidates, key=lambda c: (c["score"], -c["char_len"]))
        return sample_id, best, candidates

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(process_one, s): s for s in todo}
        for future in as_completed(future_map):
            sample = future_map[future]
            meta = sample["metadata"]
            sample_id, best, all_cands = future.result()
            completed += 1

            if best is not None:
                record = {
                    "sample_id": sample_id,
                    "case_id": meta["case_id"],
                    "L2": meta["L2"],
                    "model": model,
                    "response": best["response"],
                    "score": best["score"],
                    "passed": best["passed"],
                    "total": best["total"],
                    "n_candidates": len(all_cands),
                }
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                if all_cands:
                    cand_record = {
                        "sample_id": sample_id,
                        "candidates": [
                            {"index": c["index"], "score": c["score"],
                             "passed": c["passed"], "total": c["total"],
                             "char_len": c["char_len"]}
                            for c in all_cands
                        ],
                    }
                    with open(candidates_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(cand_record, ensure_ascii=False) + "\n")

                status = f"score={best['score']:.0%} ({best['passed']}/{best['total']})"
                stats["ok"] += 1
            else:
                status = f"FAILED: {all_cands}"
                stats["fail"] += 1

            if completed % 10 == 0 or completed == len(todo):
                print(f"  [{completed}/{len(todo)}] {sample_id} {status}")

    print(f"\nTraining responses done: {stats['ok']} OK, {stats['fail']} failed")
    print(f"Best responses → {output_path}")
    print(f"Candidate details → {candidates_path}")

    if os.path.isfile(output_path):
        scores = []
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    scores.append(json.loads(line)["score"])
        if scores:
            print(f"\n=== Score Summary ===")
            print(f"Total: {len(scores)}")
            print(f"Avg score: {sum(scores)/len(scores):.1%}")
            print(f"Perfect (1.0): {sum(1 for s in scores if s >= 1.0)} ({sum(1 for s in scores if s >= 1.0)/len(scores):.1%})")
            print(f"Score >= 0.5: {sum(1 for s in scores if s >= 0.5)} ({sum(1 for s in scores if s >= 0.5)/len(scores):.1%})")


# ============================================================
# Mode 3: Assemble final SFT dataset
# ============================================================

def assemble_final(model):
    """Merge best teacher responses into sft_train_2000.jsonl → sft_train_final.jsonl"""
    train_path = os.path.join(DATA_DIR, "sft_train_2000.jsonl")
    resp_path = os.path.join(DATA_DIR, f"sft_train_responses_{model.replace('/', '_')}.jsonl")
    output_path = os.path.join(DATA_DIR, "sft_train_final.jsonl")

    samples = {}
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                samples[obj["metadata"]["sample_id"]] = obj

    responses = {}
    with open(resp_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                responses[obj["sample_id"]] = obj

    matched = 0
    missing = 0
    records = []
    for sid, sample in sorted(samples.items()):
        if sid in responses:
            sample["messages"].append({
                "role": "assistant",
                "content": responses[sid]["response"],
            })
            sample["metadata"]["teacher_model"] = model
            sample["metadata"]["teacher_score"] = responses[sid]["score"]
            matched += 1
        else:
            missing += 1
            continue
        records.append(sample)

    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Assembled {matched} samples with teacher responses → {output_path}")
    if missing:
        print(f"Skipped {missing} samples without teacher responses")

    scores = [r["metadata"]["teacher_score"] for r in records]
    print(f"Avg teacher score: {sum(scores)/len(scores):.1%}")


def main():
    parser = argparse.ArgumentParser(description="SFT Pipeline Step 9: Teacher Response Generation")
    parser.add_argument("--mode", choices=["benchmark", "training", "assemble"], required=True)
    parser.add_argument("--model", default="gpt-5-2025-08-07")
    parser.add_argument("--n", type=int, default=3, help="Number of candidates per sample (training mode)")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    print(f"Mode: {args.mode}")
    print(f"Model: {args.model}")

    if args.mode == "benchmark":
        run_benchmark(args.model, args.temperature, args.max_tokens, args.workers)
    elif args.mode == "training":
        run_training(args.model, args.n, args.temperature, args.max_tokens, args.workers, args.resume)
    elif args.mode == "assemble":
        assemble_final(args.model)


if __name__ == "__main__":
    main()
