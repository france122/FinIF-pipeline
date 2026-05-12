#!/usr/bin/env python3
"""
批量运行 LLM Judge 评估 pending soft constraints。
用法: python run_judge.py
输入: pending_judge_tasks.jsonl (279条任务)
输出: judge_results.jsonl (279条结果)
"""
import json, os, re, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from openai import OpenAI
client = OpenAI(api_key="sk-504da47d1abd45aca3a64f2d4430d011", base_url="https://api.deepseek.com")
JUDGE_MODEL = "deepseek-v4-flash"

JUDGE_SYSTEM_PROMPT = """你是一个金融文档评测专家。你的任务是判断模型输出是否满足给定的约束条件。

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

JUDGE_USER_PROMPT = """## 约束描述
{description}

## 评判标准
{rubric}

## 原始上下文
{context}

## 模型输出（请仔细阅读全文再判断）
{output}

请严格按照系统提示的三步流程：先引用证据，再逐条评估，最后判断。以JSON格式输出（pass字段必须在最前）：{{"pass": true/false, "reason": "...", "evidence": "..."}}"""


def parse_judge_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    try:
        obj = json.loads(text)
        return {"pass": bool(obj.get("pass", False)), "reason": obj.get("reason", ""), "evidence": obj.get("evidence", "")}
    except (json.JSONDecodeError, ValueError):
        pass_match = re.search(r'"pass"\s*:\s*(true|false)', text, re.IGNORECASE)
        if pass_match:
            passed = pass_match.group(1).lower() == "true"
            reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
            reason = reason_match.group(1) if reason_match else ""
            return {"pass": passed, "reason": reason}
        if "pass" in text.lower():
            if re.search(r'pass.*?true', text, re.IGNORECASE | re.DOTALL):
                return {"pass": True, "reason": "extracted from malformed json"}
            elif re.search(r'pass.*?false', text, re.IGNORECASE | re.DOTALL):
                return {"pass": False, "reason": "extracted from malformed json"}
        return {"pass": None, "reason": f"parse failed: {text[:100]}"}


def judge_one(task):
    prompt = JUDGE_USER_PROMPT.format(
        description=task["description"],
        rubric=task["rubric"],
        context=task["context"] or "(无)",
        output=task["output"],
    )
    try:
        resp = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=512,
        )
        text = resp.choices[0].message.content
        if text is None:
            return {
                "task_id": task["task_id"],
                "constraint_id": task["constraint_id"],
                "model": task["model"],
                "type": "soft",
                "pass": None,
                "reason": "API returned None",
            }
        result = parse_judge_response(text)
        result["task_id"] = task["task_id"]
        result["constraint_id"] = task["constraint_id"]
        result["model"] = task["model"]
        result["type"] = "soft"
        return result
    except Exception as e:
        return {
            "task_id": task["task_id"],
            "constraint_id": task["constraint_id"],
            "model": task["model"],
            "type": "soft",
            "pass": None,
            "reason": f"API error: {e}",
        }


def main():
    input_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_judge_tasks.jsonl")
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "judge_results.jsonl")

    with open(input_file) as f:
        tasks = [json.loads(line) for line in f if line.strip()]
    print(f"Loaded {len(tasks)} tasks")

    # Skip already completed
    done_ids = set()
    if os.path.exists(output_file):
        with open(output_file) as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["task_id"])
        print(f"Already completed: {len(done_ids)}, remaining: {len(tasks) - len(done_ids)}")
    tasks = [t for t in tasks if t["task_id"] not in done_ids]

    if not tasks:
        print("All tasks done!")
        return

    completed = 0
    with open(output_file, "a") as out_f:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(judge_one, t): t for t in tasks}
            for future in as_completed(futures):
                result = future.result()
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()
                completed += 1
                status = "PASS" if result.get("pass") else "FAIL" if result.get("pass") is False else "ERR"
                print(f"[{completed}/{len(tasks)}] {result['task_id']} → {status}")

    print(f"\nDone! Results saved to {output_file}")


if __name__ == "__main__":
    main()
