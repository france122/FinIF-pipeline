#!/usr/bin/env python3
"""
FinIF SFT Training Data — Stage 3: Score & Select
对 K=4 候选回复打分，选出每个 prompt 的最佳回复
"""
import json, os, sys, re, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import checkers

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com",
)

JUDGE_SYSTEM = """你是一个金融文档评测专家。判断模型输出是否满足给定的约束条件。
流程：1.引用证据 2.评估 3.判断。
规则：基于实际内容判断；有Markdown表格则表格约束PASS；有计算步骤则计算过程约束PASS；找不到才判FAIL。
输出JSON：{"pass": true/false, "reason": "一句话", "evidence": "摘录≤100字"}"""


def parse_judge(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    try:
        return {"pass": bool(json.loads(text).get("pass", False))}
    except:
        m = re.search(r'"pass"\s*:\s*(true|false)', text, re.I)
        if m:
            return {"pass": m.group(1).lower() == "true"}
        return {"pass": None}


def run_hard(config, output):
    fn = getattr(checkers, config["checker"], None)
    if fn is None:
        return {"pass": False, "type": "hard"}
    try:
        return {"pass": bool(fn(output, config.get("params"))), "type": "hard"}
    except:
        return {"pass": False, "type": "hard"}


def judge_soft(config, output, context):
    prompt = f"""## 约束描述
{config.get('description', '')}

## 评判标准
{config.get('rubric', '')}

## 原始上下文
{context[:3000] if context else '(无)'}

## 模型输出
{output[:4000]}

JSON输出：{{"pass": true/false, "reason": "...", "evidence": "..."}}"""
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=256,
            )
            text = r.choices[0].message.content
            if not text:
                continue
            res = parse_judge(text)
            res["type"] = "soft"
            return res
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            return {"pass": None, "type": "soft", "error": str(e)}
    return {"pass": None, "type": "soft", "error": "max retries"}


def score_response(response, constraints, context, judge_workers=5):
    """Score a single response against all its constraints. Returns pass_rate."""
    output = response["response"]
    output = re.sub(r"<think>.*?</think>\s*", "", output, flags=re.DOTALL)

    hard_results = {}
    soft_tasks = []

    for key, config in constraints.items():
        if config["type"] == "hard":
            hard_results[key] = run_hard(config, output)
        else:
            soft_tasks.append((key, config))

    soft_results = {}
    for key, config in soft_tasks:
        result = judge_soft(config, output, context)
        soft_results[key] = result

    all_results = {**hard_results, **soft_results}
    total = len(all_results)
    passed = sum(1 for v in all_results.values() if v.get("pass") is True)
    hard_total = len(hard_results)
    hard_passed = sum(1 for v in hard_results.values() if v.get("pass") is True)
    soft_total = len(soft_results)
    soft_passed = sum(1 for v in soft_results.values() if v.get("pass") is True)

    return {
        "pass_rate": passed / total if total else 0,
        "passed": passed,
        "total": total,
        "hard_pass_rate": hard_passed / hard_total if hard_total else 1.0,
        "hard_passed": hard_passed,
        "hard_total": hard_total,
        "soft_pass_rate": soft_passed / soft_total if soft_total else 1.0,
        "soft_passed": soft_passed,
        "soft_total": soft_total,
        "details": all_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.7, help="Min pass rate to select")
    parser.add_argument("--workers", type=int, default=10, help="Judge workers")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load prompts and constraints
    with open(os.path.join(SCRIPT_DIR, "training_prompts.json"), encoding="utf-8") as f:
        prompt_data = json.load(f)
    prompts_by_id = {p["case_id"]: p for p in prompt_data["prompts"]}

    with open(os.path.join(SCRIPT_DIR, "training_constraints.json"), encoding="utf-8") as f:
        all_constraints = json.load(f)["constraints"]

    # Load raw responses
    raw_path = os.path.join(SCRIPT_DIR, "output", "training_responses_raw.jsonl")
    if not os.path.isfile(raw_path):
        print(f"No responses found at {raw_path}")
        return

    responses = {}  # case_id -> [response1, response2, ...]
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                cid = obj["case_id"]
                if cid not in responses:
                    responses[cid] = []
                responses[cid].append(obj)

    print(f"Loaded {sum(len(v) for v in responses.values())} responses for {len(responses)} prompts")

    if args.dry_run:
        for cid, resps in sorted(responses.items()):
            print(f"  {cid}: {len(resps)} candidates")
        return

    # Score and select
    selected = []
    rejected = 0

    for cid in sorted(responses.keys()):
        resps = responses[cid]
        prompt_info = prompts_by_id.get(cid)
        if not prompt_info:
            print(f"  SKIP {cid}: no prompt found")
            continue

        # Get constraints for this case
        case_constraints = {k: v for k, v in all_constraints.items() if k.startswith(cid + "#")}
        context = prompt_info.get("context", "")

        best_score = -1
        best_resp = None
        best_scores = None

        for resp in resps:
            scores = score_response(resp, case_constraints, context)
            print(f"  {cid} k={resp['k']}: pass_rate={scores['pass_rate']:.1%} "
                  f"(hard={scores['hard_passed']}/{scores['hard_total']}, "
                  f"soft={scores['soft_passed']}/{scores['soft_total']})")

            if scores["pass_rate"] > best_score:
                best_score = scores["pass_rate"]
                best_resp = resp
                best_scores = scores

        if best_score >= args.threshold:
            selected.append({
                "case_id": cid,
                "prompt": prompt_info["prompt"],
                "response": best_resp["response"],
                "pass_rate": best_score,
                "scores": best_scores,
                "template": prompt_info.get("template", ""),
                "company": prompt_info.get("company", ""),
            })
            print(f"  -> SELECTED {cid}: {best_score:.1%}")
        else:
            rejected += 1
            print(f"  -> REJECTED {cid}: best={best_score:.1%} < threshold={args.threshold:.1%}")

    # Save selected responses
    out_path = os.path.join(SCRIPT_DIR, "output", "training_selected.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for item in selected:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"Selected: {len(selected)}/{len(responses)} (rejected: {rejected})")
    print(f"Average pass rate: {sum(s['pass_rate'] for s in selected)/len(selected):.1%}" if selected else "")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
