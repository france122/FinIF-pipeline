#!/usr/bin/env python3
"""
FinIF Benchmark — DeepSeek 多模型回复生成 + 评测
模型：deepseek-v4-flash / deepseek-v4-pro / deepseek-v4-pro-thinking
评测：hard checkers (code) + soft judge (deepseek-v4-flash)

用法:
  # 生成全部3个模型的responses
  python gen_responses_ds.py gen --workers 5

  # 只生成某个模型
  python gen_responses_ds.py gen --models ds-v4-flash

  # 评测（hard + soft judge）
  python gen_responses_ds.py eval

  # 只跑 hard checkers
  python gen_responses_ds.py eval --hard-only
"""
import json, os, sys, re, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import checkers

DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE_URL = "https://api.deepseek.com"

client = OpenAI(api_key=DS_API_KEY, base_url=DS_BASE_URL)

MODEL_CONFIG = {
    "ds-v4-flash": {
        "api_model": "deepseek-v4-flash",
        "thinking": False,
        "max_tokens": 8192,
    },
    "ds-v4-flash-thinking": {
        "api_model": "deepseek-v4-flash",
        "thinking": True,
        "reasoning_effort": "high",
        "max_tokens": 16384,
    },
    "ds-v4-pro": {
        "api_model": "deepseek-v4-pro",
        "thinking": False,
        "max_tokens": 8192,
    },
    "ds-v4-pro-thinking": {
        "api_model": "deepseek-v4-pro",
        "thinking": True,
        "reasoning_effort": "high",
        "max_tokens": 16384,
    },
}

SYSTEM_PROMPT = ""


# ============================================================
# 生成
# ============================================================

def gen_one(prompt, model_key):
    cfg = MODEL_CONFIG[model_key]
    messages = [
        {"role": "user", "content": prompt},
    ]
    kwargs = {
        "model": cfg["api_model"],
        "messages": messages,
        "max_tokens": cfg["max_tokens"],
        "stream": False,
    }
    if cfg.get("thinking"):
        kwargs["extra_body"] = {
            "thinking": {"type": "enabled"},
            "reasoning_effort": cfg.get("reasoning_effort", "high"),
        }
        kwargs.pop("max_tokens")
        kwargs["extra_body"]["max_completion_tokens"] = cfg["max_tokens"]
    else:
        kwargs["temperature"] = 0.7

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            if content:
                return content
        except Exception as e:
            if "rate" in str(e).lower() or "429" in str(e):
                time.sleep(2 ** attempt)
                continue
            if attempt < 2:
                time.sleep(1)
                continue
            raise
    return None


def load_benchmark():
    path = os.path.join(SCRIPT_DIR, "benchmark", "benchmark_all.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["cases"]


def run_gen(model_keys, workers):
    cases = load_benchmark()
    output_dir = os.path.join(SCRIPT_DIR, "benchmark", "responses")
    os.makedirs(output_dir, exist_ok=True)

    import threading
    lock = threading.Lock()
    file_locks = {mk: threading.Lock() for mk in model_keys}

    all_tasks = []
    for model_key in model_keys:
        out_path = os.path.join(output_dir, f"responses_{model_key}.jsonl")
        existing_ids = set()
        if os.path.isfile(out_path):
            with open(out_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        existing_ids.add(json.loads(line)["case_id"])
        todo = [c for c in cases if c["case_id"] not in existing_ids]
        print(f"  {model_key}: {len(existing_ids)} done, {len(todo)} todo")
        for c in todo:
            all_tasks.append((model_key, c, out_path))

    if not all_tasks:
        print("All done!")
        return

    print(f"\nTotal tasks: {len(all_tasks)} (across {len(model_keys)} models, {workers} workers)")

    counters = {mk: {"done": 0, "failed": 0, "total": sum(1 for t in all_tasks if t[0] == mk)} for mk in model_keys}

    def process(task):
        model_key, case, out_path = task
        try:
            resp = gen_one(case["prompt"], model_key)
            if resp is None:
                return model_key, case["case_id"], None, "API returned None"
            return model_key, case["case_id"], resp, None
        except Exception as e:
            return model_key, case["case_id"], None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process, t): t for t in all_tasks}
        for future in as_completed(futures):
            model_key, case_id, resp, err = future.result()
            task = futures[future]
            _, case, out_path = task

            if resp:
                record = {
                    "case_id": case_id,
                    "model": model_key,
                    "response": resp,
                    "context": case.get("context", ""),
                }
                with file_locks[model_key]:
                    with open(out_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                counters[model_key]["done"] += 1
                c = counters[model_key]
                print(f"  [{c['done']+c['failed']}/{c['total']}] {model_key} {case_id} OK ({len(resp)} chars)")
            else:
                counters[model_key]["failed"] += 1
                c = counters[model_key]
                print(f"  [{c['done']+c['failed']}/{c['total']}] {model_key} {case_id} FAILED: {err}")

    for mk in model_keys:
        c = counters[mk]
        print(f"  {mk}: {c['done']} OK, {c['failed']} failed")


# ============================================================
# 评测
# ============================================================

JUDGE_SYSTEM = """你是一个金融文档评测专家。你的任务是判断模型输出是否满足给定的约束条件。

## 判断流程（必须严格遵循）

第一步：从模型输出中逐字引用与约束相关的内容作为证据。如果输出中存在表格、公式、计算步骤等，必须原样引用。
第二步：基于引用的证据，逐条评估约束是否满足。
第三步：给出最终判断。

## 重要规则

- 判断必须基于输出中实际存在的内容，不能凭印象。
- 如果输出中包含了Markdown表格（含|和---分隔符），则"要求表格"的约束应判PASS。
- 如果输出中包含了计算公式或推导步骤（如 A × B = C、数值代入等），则"要求计算过程"的约束应判PASS。
- 约束要求"展示计算过程"时，只要输出中给出了数据和推导逻辑即可，不要求完美的教科书格式。
- 只有在输出中确实找不到相关内容时才判FAIL。

请以JSON格式输出：
{"pass": true/false, "reason": "基于证据的判断理由（一句话）", "evidence": "从输出中引用的关键证据（简短摘录，不超过100字）"}"""

JUDGE_USER = """## 约束描述
{description}

## 评判标准
{rubric}

## 模型输出（请仔细阅读全文再判断）
{output}

请严格按照系统提示的三步流程判断。以JSON格式输出：{{"pass": true/false, "reason": "...", "evidence": "..."}}"""


def parse_judge(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    try:
        obj = json.loads(text)
        return {"pass": bool(obj.get("pass", False)), "reason": obj.get("reason", ""), "evidence": obj.get("evidence", "")}
    except (json.JSONDecodeError, ValueError):
        m = re.search(r'"pass"\s*:\s*(true|false)', text, re.IGNORECASE)
        if m:
            return {"pass": m.group(1).lower() == "true", "reason": "parsed from malformed json"}
        return {"pass": None, "reason": f"parse failed: {text[:100]}"}


def judge_soft(config, output):
    prompt = JUDGE_USER.format(
        description=config.get("description", ""),
        rubric=config.get("rubric", ""),
        output=output[:6000],
    )
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=512,
            )
            text = resp.choices[0].message.content
            if not text:
                if attempt < 2:
                    time.sleep(1)
                    continue
                return {"pass": None, "type": "soft", "error": "empty response"}
            result = parse_judge(text)
            if result.get("pass") is not None and result.get("reason") != "parsed from malformed json":
                result["type"] = "soft"
                return result
            if attempt < 2:
                time.sleep(1)
                continue
            result["type"] = "soft"
            return result
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return {"pass": None, "type": "soft", "error": str(e)}


def run_hard_check(config, output):
    fn_name = config["checker"]
    params = config.get("params", None)
    fn = getattr(checkers, fn_name, None)
    if fn is None:
        return {"pass": False, "type": "hard", "error": f"checker '{fn_name}' not found"}
    try:
        passed = fn(output, params)
        return {"pass": bool(passed), "type": "hard", "checker": fn_name}
    except Exception as e:
        return {"pass": False, "type": "hard", "error": str(e)}


def run_eval(hard_only, judge_workers, model_filter=None):
    config_path = os.path.join(SCRIPT_DIR, "benchmark", "eval_config_all.json")
    with open(config_path, encoding="utf-8") as f:
        all_constraints = json.load(f)["constraints"]

    resp_dir = os.path.join(SCRIPT_DIR, "benchmark", "responses")
    score_dir = os.path.join(SCRIPT_DIR, "benchmark", "scores")
    os.makedirs(score_dir, exist_ok=True)
    response_files = sorted([
        f for f in os.listdir(resp_dir)
        if f.startswith("responses_") and f.endswith(".jsonl")
    ])
    if model_filter:
        response_files = [f for f in response_files if any(m in f for m in model_filter)]

    if not response_files:
        print("No ds-* response files found!")
        return

    hard_count = sum(1 for v in all_constraints.values() if v["type"] == "hard")
    soft_count = sum(1 for v in all_constraints.values() if v["type"] == "soft")
    print(f"Eval config: {len(all_constraints)} constraints ({hard_count} hard, {soft_count} soft)")
    if hard_only:
        print("Mode: hard-only")
    else:
        print(f"Judge: deepseek-v4-flash (workers={judge_workers})")
    print(f"Response files: {response_files}")

    summary = {}

    for resp_file in response_files:
        model_name = resp_file.replace("responses_", "").replace(".jsonl", "")
        responses = {}
        with open(os.path.join(resp_dir, resp_file), encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    responses[obj["case_id"]] = obj

        print(f"\n{'='*60}")
        print(f"Evaluating: {model_name} ({len(responses)} responses)")

        all_results = {}

        # Run hard checks first (instant, local)
        for case_id, item in sorted(responses.items()):
            output = item["response"]
            results = {}
            for key, config in all_constraints.items():
                if not key.startswith(case_id + "#"):
                    continue
                if config["type"] == "hard":
                    results[key] = run_hard_check(config, output)
            all_results[case_id] = results

        h_total_all = sum(len(v) for v in all_results.values())
        print(f"  Hard checks done: {h_total_all} constraints")

        # Collect all soft judge tasks
        if not hard_only:
            soft_tasks = []
            for case_id, item in sorted(responses.items()):
                output = item["response"]
                context = item.get("context", "")
                for key, config in all_constraints.items():
                    if not key.startswith(case_id + "#"):
                        continue
                    if config["type"] == "soft":
                        soft_tasks.append((case_id, key, config, output))

            print(f"  Soft judge: {len(soft_tasks)} calls, {judge_workers} workers")
            done_count = [0]

            def _judge(task):
                cid, key, config, output = task
                result = judge_soft(config, output)
                done_count[0] += 1
                if done_count[0] % 20 == 0 or done_count[0] == len(soft_tasks):
                    print(f"    [{done_count[0]}/{len(soft_tasks)}] judged", flush=True)
                return cid, key, result

            with ThreadPoolExecutor(max_workers=judge_workers) as pool:
                for cid, key, result in pool.map(_judge, soft_tasks):
                    all_results[cid][key] = result
        else:
            for case_id in all_results:
                for key, config in all_constraints.items():
                    if key.startswith(case_id + "#") and config["type"] == "soft":
                        all_results[case_id][key] = {"pass": None, "type": "soft", "reason": "skipped"}

        for i, (case_id, results) in enumerate(sorted(all_results.items())):
            h_pass = sum(1 for v in results.values() if v["type"] == "hard" and v.get("pass") is True)
            h_total = sum(1 for v in results.values() if v["type"] == "hard")
            s_pass = sum(1 for v in results.values() if v["type"] == "soft" and v.get("pass") is True)
            s_total = sum(1 for v in results.values() if v["type"] == "soft")
            print(f"  [{i+1}/{len(responses)}] {case_id}: hard={h_pass}/{h_total} soft={s_pass}/{s_total}")

        # Compute scores
        scores = {}
        for case_id, cons in all_results.items():
            total = len(cons)
            passed = sum(1 for v in cons.values() if v.get("pass") is True)
            hard_t = sum(1 for v in cons.values() if v["type"] == "hard")
            hard_p = sum(1 for v in cons.values() if v["type"] == "hard" and v.get("pass") is True)
            soft_t = sum(1 for v in cons.values() if v["type"] == "soft")
            soft_p = sum(1 for v in cons.values() if v["type"] == "soft" and v.get("pass") is True)
            scores[case_id] = {
                "total": total, "passed": passed,
                "score": passed / total if total > 0 else 0,
                "hard": {"total": hard_t, "passed": hard_p},
                "soft": {"total": soft_t, "passed": soft_p},
            }

        tiers = {"T1": [], "T2": [], "T3": []}
        for cid, s in scores.items():
            tier = cid.split(".")[0]
            if tier in tiers:
                tiers[tier].append(s["score"])
        tier_scores = {}
        for tier, vals in tiers.items():
            tier_scores[tier] = sum(vals) / len(vals) if vals else 0
        all_vals = [s["score"] for s in scores.values()]
        tier_scores["overall"] = sum(all_vals) / len(all_vals) if all_vals else 0

        score_file = os.path.join(score_dir, f"scores_{model_name}.json")
        with open(score_file, "w", encoding="utf-8") as f:
            json.dump({
                "model": model_name,
                "results": all_results,
                "scores": scores,
                "tier_scores": tier_scores,
            }, f, ensure_ascii=False, indent=2)

        summary[model_name] = tier_scores
        print(f"  → {score_file}")

    print(f"\n{'='*80}")
    print(f"{'Model':<25s} {'T1':>8s} {'T2':>8s} {'T3':>8s} {'Overall':>8s}")
    print("-" * 55)
    for model_name, ts in sorted(summary.items()):
        print(f"{model_name:<25s} {ts.get('T1',0):>7.1%} {ts.get('T2',0):>7.1%} {ts.get('T3',0):>7.1%} {ts.get('overall',0):>7.1%}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("gen", help="Generate responses")
    p_gen.add_argument("--models", nargs="*", default=None,
                       help="Model keys: ds-v4-flash, ds-v4-pro, ds-v4-pro-thinking")
    p_gen.add_argument("--workers", type=int, default=5)

    p_eval = sub.add_parser("eval", help="Evaluate responses")
    p_eval.add_argument("--hard-only", action="store_true")
    p_eval.add_argument("--judge-workers", type=int, default=5)
    p_eval.add_argument("--models", nargs="*", default=None, help="Only eval these models")

    args = parser.parse_args()

    if args.cmd == "gen":
        model_keys = args.models or list(MODEL_CONFIG.keys())
        run_gen(model_keys, args.workers)
    elif args.cmd == "eval":
        run_eval(args.hard_only, args.judge_workers, args.models)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
