#!/usr/bin/env python3
"""
SFT 训练数据质量评测 + LLaMA-Factory 格式转换

用法:
  # Step 1: 评测 GPT-5.4 回复质量（hard checker + soft judge）
  python3 score_sft_responses.py score --judge-workers 20

  # Step 2: 筛选 + 导出 LLaMA-Factory 格式
  python3 score_sft_responses.py export --threshold 0.9
"""
import json, os, sys, re, time, argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import checkers

DS_API_KEY = "sk-07ddf2d18dbd4cd4a98640d03c4b3643"
DS_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DS_API_KEY, base_url=DS_BASE_URL)

SFT_DATA_DIR = os.path.join(SCRIPT_DIR, "sft_data")
RESPONSE_FILE = os.path.join(SFT_DATA_DIR, "sft_data.jsonl")
CONSTRAINT_FILE = os.path.join(SFT_DATA_DIR, "constraint_gen_output_v3.jsonl")
SCORES_FILE = os.path.join(SFT_DATA_DIR, "sft_scores.json")

SYSTEM_PROMPT = (
    "你是一位金融领域专家。请基于提供的检索内容回答用户问题。"
    "你必须严格遵循用户在 prompt 中给出的所有约束条件，包括但不限于："
    "输出格式（JSON/Markdown/表格等）、数值精度（小数位数）、段落数量、"
    "字数限制、语气风格等。如果有多条约束，每一条都必须满足，不可遗漏。"
)

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
        return {"pass": bool(obj.get("pass", False)), "reason": obj.get("reason", "")}
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
            if result.get("pass") is not None:
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


def cmd_score(args):
    with open(RESPONSE_FILE, encoding="utf-8") as f:
        responses = {json.loads(l)["trace_id"]: json.loads(l) for l in f}
    with open(CONSTRAINT_FILE, encoding="utf-8") as f:
        constraints = {json.loads(l)["sample_id"]: json.loads(l) for l in f}

    matched = set(responses.keys()) & set(constraints.keys())
    print(f"Responses: {len(responses)}, Constraints: {len(constraints)}, Matched: {len(matched)}")

    hard_tasks = []
    soft_tasks = []
    for sid in sorted(matched):
        resp = responses[sid]["vulcan_output"]["llm_response"]
        for i, sc in enumerate(constraints[sid]["sampled_constraints"]):
            if sc["type"] == "hard":
                hard_tasks.append((sid, i, sc, resp))
            else:
                soft_tasks.append((sid, i, sc, resp))

    print(f"Hard checks: {len(hard_tasks)}, Soft judges: {len(soft_tasks)}")

    results = defaultdict(dict)

    print("Running hard checks...")
    for sid, idx, config, output in hard_tasks:
        r = run_hard_check(config, output)
        r["tag"] = config.get("tag", "")
        results[sid][f"c{idx}"] = r

    hard_pass = sum(1 for sid in results for k, v in results[sid].items() if v.get("pass"))
    hard_total = len(hard_tasks)
    print(f"  Hard: {hard_pass}/{hard_total} passed ({hard_pass/hard_total*100:.1f}%)")

    print(f"Soft judging: {len(soft_tasks)} calls, {args.judge_workers} workers")
    done = 0
    def _judge(task):
        sid, idx, config, output = task
        r = judge_soft(config, output)
        r["tag"] = config.get("tag", "")
        return sid, idx, r

    with ThreadPoolExecutor(max_workers=args.judge_workers) as pool:
        futs = [pool.submit(_judge, t) for t in soft_tasks]
        for fut in as_completed(futs):
            sid, idx, r = fut.result()
            results[sid][f"c{idx}"] = r
            done += 1
            if done % 100 == 0 or done == len(soft_tasks):
                print(f"  [{done}/{len(soft_tasks)}] judged")

    soft_pass = sum(1 for sid in results for k, v in results[sid].items()
                    if v.get("type") == "soft" and v.get("pass"))
    print(f"  Soft: {soft_pass}/{len(soft_tasks)} passed ({soft_pass/len(soft_tasks)*100:.1f}%)")

    records = []
    for sid in sorted(matched):
        checks = results.get(sid, {})
        n_total = len(constraints[sid]["sampled_constraints"])
        n_pass = sum(1 for v in checks.values() if v.get("pass"))
        pass_rate = n_pass / n_total if n_total > 0 else 1.0
        records.append({
            "sample_id": sid,
            "n_constraints": n_total,
            "n_pass": n_pass,
            "pass_rate": round(pass_rate, 4),
            "all_pass": n_pass == n_total,
            "checks": {k: {kk: vv for kk, vv in v.items() if kk != "type"} for k, v in checks.items()},
        })

    output_data = {
        "total": len(records),
        "hard_total": hard_total,
        "hard_pass": hard_pass,
        "soft_total": len(soft_tasks),
        "soft_pass": soft_pass,
        "results": records,
    }
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n→ {SCORES_FILE}")

    all_pass_count = sum(1 for r in records if r["all_pass"])
    print(f"\nPrompt-level all-pass: {all_pass_count}/{len(records)} ({all_pass_count/len(records)*100:.1f}%)")
    print(f"Instruction-level: {hard_pass + soft_pass}/{hard_total + len(soft_tasks)} "
          f"({(hard_pass + soft_pass)/(hard_total + len(soft_tasks))*100:.1f}%)")

    tag_stats = defaultdict(lambda: {"pass": 0, "total": 0})
    for r in records:
        for k, v in r["checks"].items():
            tag = v.get("tag", "?")
            tag_stats[tag]["total"] += 1
            if v.get("pass"):
                tag_stats[tag]["pass"] += 1
    print("\nPer-tag pass rates:")
    for tag in sorted(tag_stats, key=lambda t: tag_stats[t]["pass"]/max(tag_stats[t]["total"],1)):
        s = tag_stats[tag]
        print(f"  {tag:4s}: {s['pass']:4d}/{s['total']:4d} ({s['pass']/s['total']*100:5.1f}%)")

    thresholds = [1.0, 0.95, 0.9, 0.85, 0.8]
    print("\nSurvival by threshold:")
    for t in thresholds:
        kept = sum(1 for r in records if r["pass_rate"] >= t)
        print(f"  ≥{t:.0%}: {kept}/{len(records)} ({kept/len(records)*100:.1f}%)")


def cmd_export(args):
    if not os.path.exists(SCORES_FILE):
        print(f"Error: {SCORES_FILE} not found. Run 'score' first.")
        sys.exit(1)

    with open(SCORES_FILE, encoding="utf-8") as f:
        scores = json.load(f)
    with open(RESPONSE_FILE, encoding="utf-8") as f:
        responses = {json.loads(l)["trace_id"]: json.loads(l) for l in f}

    kept = [r for r in scores["results"] if r["pass_rate"] >= args.threshold]
    dropped = len(scores["results"]) - len(kept)
    print(f"Threshold: {args.threshold:.0%}")
    print(f"Kept: {len(kept)}, Dropped: {dropped}")

    if dropped > 0:
        failed = [r for r in scores["results"] if r["pass_rate"] < args.threshold]
        print(f"\nDropped samples (first 20):")
        for r in sorted(failed, key=lambda x: x["pass_rate"])[:20]:
            failed_tags = [v.get("tag", "?") for v in r["checks"].values() if not v.get("pass")]
            print(f"  {r['sample_id']}: {r['n_pass']}/{r['n_constraints']} "
                  f"({r['pass_rate']:.0%}) failed=[{','.join(failed_tags)}]")

    conversations = []
    for r in kept:
        sid = r["sample_id"]
        resp_data = responses[sid]
        user_msg = resp_data["messages"][1]["content"]
        response = resp_data["vulcan_output"]["llm_response"]
        conversations.append({
            "conversations": [
                {"from": "system", "value": SYSTEM_PROMPT},
                {"from": "human", "value": user_msg},
                {"from": "gpt", "value": f"<think>\n\n</think>\n\n{response}"},
            ]
        })

    train_file = os.path.join(SFT_DATA_DIR, "finif_sft_train.json")
    with open(train_file, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    print(f"\n→ {train_file} ({len(conversations)} samples)")

    dataset_info = {
        "finif_sft": {
            "file_name": "finif_sft_train.json",
            "formatting": "sharegpt",
            "columns": {
                "messages": "conversations"
            },
            "tags": {
                "role_tag": "from",
                "content_tag": "value",
                "user_tag": "human",
                "assistant_tag": "gpt",
                "system_tag": "system"
            }
        }
    }
    info_file = os.path.join(SFT_DATA_DIR, "dataset_info.json")
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, ensure_ascii=False, indent=2)
    print(f"→ {info_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SFT response scoring & export")
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score", help="Score GPT-5.4 responses")
    p_score.add_argument("--judge-workers", type=int, default=20)

    p_export = sub.add_parser("export", help="Export to LLaMA-Factory format")
    p_export.add_argument("--threshold", type=float, default=0.9)

    args = parser.parse_args()
    if args.cmd == "score":
        cmd_score(args)
    elif args.cmd == "export":
        cmd_export(args)
    else:
        parser.print_help()
