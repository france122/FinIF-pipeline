#!/usr/bin/env python3
"""评测修复后的 SFT 回复：对 flash_repair_v2.json 跑所有约束（hard + soft）"""
import json, asyncio, re, sys, os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checkers
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-07ddf2d18dbd4cd4a98640d03c4b3643",
    base_url="https://api.deepseek.com",
)

BASE = os.path.dirname(os.path.abspath(__file__))
REPAIR_FILE = os.path.join(BASE, "flash_repair_v2.json")
CONSTRAINT_FILE = os.path.join(BASE, "constraint_gen_output_v3.jsonl")
OUTPUT_FILE = os.path.join(BASE, "repair_scores.json")

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


def run_hard_check(config, output):
    fn_name = config["checker"]
    params = config.get("params", None)
    fn = getattr(checkers, fn_name, None)
    if fn is None:
        return {"pass": False, "type": "hard", "tag": config.get("tag", ""), "error": f"checker '{fn_name}' not found"}
    try:
        passed = fn(output, params)
        return {"pass": bool(passed), "type": "hard", "tag": config.get("tag", ""), "checker": fn_name}
    except Exception as e:
        return {"pass": False, "type": "hard", "tag": config.get("tag", ""), "error": str(e)}


async def judge_soft(sem, config, output):
    prompt = JUDGE_USER.format(
        description=config.get("description", ""),
        rubric=config.get("rubric", ""),
        output=output[:6000],
    )
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
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
                        await asyncio.sleep(1)
                        continue
                    return {"pass": None, "type": "soft", "tag": config.get("tag", ""), "error": "empty response"}
                result = parse_judge(text)
                if result.get("pass") is not None:
                    result["type"] = "soft"
                    result["tag"] = config.get("tag", "")
                    return result
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                result["type"] = "soft"
                result["tag"] = config.get("tag", "")
                return result
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"pass": None, "type": "soft", "tag": config.get("tag", ""), "error": str(e)}


async def main():
    with open(REPAIR_FILE, encoding="utf-8") as f:
        repairs = json.load(f)
    with open(CONSTRAINT_FILE, encoding="utf-8") as f:
        constraints = {json.loads(l)["sample_id"]: json.loads(l) for l in f}

    print(f"Repairs: {len(repairs)}, Constraints: {len(constraints)}")

    # 1) Hard checks (local, instant)
    hard_results = {}  # sid -> [(idx, result)]
    soft_tasks = []    # [(sid, idx, config, output)]
    hard_total, hard_pass = 0, 0

    for sid, fixed_text in repairs.items():
        cons = constraints[sid]["sampled_constraints"]
        hard_results[sid] = {}
        for i, c in enumerate(cons):
            if c["type"] == "hard":
                r = run_hard_check(c, fixed_text)
                hard_results[sid][i] = r
                hard_total += 1
                if r["pass"]:
                    hard_pass += 1
            else:
                soft_tasks.append((sid, i, c, fixed_text))

    print(f"Hard: {hard_pass}/{hard_total} passed ({hard_pass/max(hard_total,1)*100:.1f}%)")
    print(f"Soft tasks: {len(soft_tasks)}")

    # 2) Soft judge (async, 30 concurrency)
    sem = asyncio.Semaphore(30)
    soft_results = {}  # sid -> {idx: result}
    soft_pass = 0
    done = 0

    async def _run(sid, idx, config, output):
        return sid, idx, await judge_soft(sem, config, output)

    coros = [_run(sid, idx, c, out) for sid, idx, c, out in soft_tasks]
    for coro in asyncio.as_completed(coros):
        sid, idx, result = await coro
        if sid not in soft_results:
            soft_results[sid] = {}
        soft_results[sid][idx] = result
        if result.get("pass"):
            soft_pass += 1
        done += 1
        if done % 50 == 0 or done == len(soft_tasks):
            print(f"  [{done}/{len(soft_tasks)}] judged", flush=True)

    print(f"Soft: {soft_pass}/{len(soft_tasks)} passed ({soft_pass/max(len(soft_tasks),1)*100:.1f}%)")

    # 3) Merge and output
    records = []
    for sid in sorted(repairs.keys()):
        cons = constraints[sid]["sampled_constraints"]
        checks = {}
        for i in range(len(cons)):
            if i in hard_results.get(sid, {}):
                checks[f"c{i}"] = hard_results[sid][i]
            elif i in soft_results.get(sid, {}):
                checks[f"c{i}"] = soft_results[sid][i]

        n_total = len(cons)
        n_pass = sum(1 for v in checks.values() if v.get("pass"))
        records.append({
            "sample_id": sid,
            "n_constraints": n_total,
            "n_pass": n_pass,
            "pass_rate": round(n_pass / n_total, 4) if n_total > 0 else 1.0,
            "all_pass": n_pass == n_total,
            "checks": checks,
        })

    all_pass_count = sum(1 for r in records if r["all_pass"])
    total = len(records)

    print(f"\n{'='*60}")
    print(f"Prompt-level all-pass: {all_pass_count}/{total} ({all_pass_count/total*100:.1f}%)")
    print(f"Instruction-level: {hard_pass+soft_pass}/{hard_total+len(soft_tasks)} "
          f"({(hard_pass+soft_pass)/max(hard_total+len(soft_tasks),1)*100:.1f}%)")

    # Per-tag stats
    tag_stats = defaultdict(lambda: {"pass": 0, "total": 0})
    for r in records:
        for v in r["checks"].values():
            tag = v.get("tag", "?")
            tag_stats[tag]["total"] += 1
            if v.get("pass"):
                tag_stats[tag]["pass"] += 1

    print("\nPer-tag pass rates:")
    for tag in sorted(tag_stats, key=lambda t: tag_stats[t]["pass"]/max(tag_stats[t]["total"],1)):
        s = tag_stats[tag]
        rate = s["pass"] / s["total"] * 100
        print(f"  {tag:4s}: {s['pass']:3d}/{s['total']:3d} ({rate:5.1f}%)")

    # Failed samples detail
    failed = [r for r in records if not r["all_pass"]]
    if failed:
        print(f"\nFailed samples ({len(failed)}):")
        for r in failed:
            fail_tags = [v.get("tag","?") for v in r["checks"].values() if not v.get("pass")]
            print(f"  {r['sample_id']}: {r['n_pass']}/{r['n_constraints']} fail={fail_tags}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"total": total, "all_pass": all_pass_count,
                    "hard_total": hard_total, "hard_pass": hard_pass,
                    "soft_total": len(soft_tasks), "soft_pass": soft_pass,
                    "results": records}, f, ensure_ascii=False, indent=2)
    print(f"\n→ {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
