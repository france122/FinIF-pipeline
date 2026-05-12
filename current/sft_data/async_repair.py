#!/usr/bin/env python3
"""用 ds-v4-flash 异步并行修复 SFT 回复，基于 judge reason 精准修改"""
import json, asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checkers
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-07ddf2d18dbd4cd4a98640d03c4b3643",
    base_url="https://api.deepseek.com",
)

SYSTEM = (
    "你是金融文档修复专家。用户会给你一段金融回复和它未通过的约束条件及评审意见。"
    "你需要对回复做最小化修改使其满足所有约束。"
    "注意：只修改不合格的部分，保留原文的事实内容、数据和分析逻辑。"
    "直接输出修改后的完整回复，不要加任何解释。"
)


def build_prompt(task):
    lines = ["## 未通过的约束及评审意见\n"]
    for fc in task["failed_constraints"]:
        lines.append(f"### 约束 [{fc['tag']}]")
        lines.append(f"- 描述: {fc['description']}")
        if fc["type"] == "hard":
            lines.append(f"- 类型: 硬约束 (程序化校验)")
            lines.append(f"- Checker: {fc['checker']}")
            lines.append(f"- 参数: {json.dumps(fc['params'], ensure_ascii=False)}")
        else:
            lines.append(f"- 类型: 软约束 (LLM评审)")
            lines.append(f"- 评判标准: {fc['rubric']}")
        if fc["judge_reason"]:
            lines.append(f"- **评审不通过原因: {fc['judge_reason']}**")
        lines.append("")

    lines.append("## 所有约束（修改时不要破坏已通过的约束）\n")
    for i, c in enumerate(task["all_constraints"]):
        lines.append(f"{i+1}. [{c['tag']}] {c['description']}")
    lines.append("")

    lines.append("## 原始回复\n")
    lines.append(task["response"])

    return "\n".join(lines)


async def fix_one(sem, task, idx, total):
    async with sem:
        prompt = build_prompt(task)
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    max_tokens=8192,
                )
                text = resp.choices[0].message.content
                if text and len(text) > 50:
                    return task["sample_id"], text
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"  FAILED {task['sample_id']}: {e}", flush=True)
                    return task["sample_id"], None
        return task["sample_id"], None


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只修前 N 条（0=全部）")
    parser.add_argument("--skip-existing", action="store_true", help="跳过已有修复的样本")
    args = parser.parse_args()

    with open("/Users/minimax/Desktop/FinIF/current/sft_data/repair_v2.json") as f:
        tasks = json.load(f)

    if args.skip_existing:
        existing = {}
        repair_file = "/Users/minimax/Desktop/FinIF/current/sft_data/flash_repair_v2.json"
        if os.path.exists(repair_file):
            with open(repair_file) as f:
                existing = json.load(f)
        before = len(tasks)
        tasks = [t for t in tasks if t["sample_id"] not in existing]
        print(f"Skip existing: {before} → {len(tasks)} (skipped {before - len(tasks)})", flush=True)

    if args.limit > 0:
        tasks = tasks[:args.limit]
    print(f"Tasks: {len(tasks)}", flush=True)

    sem = asyncio.Semaphore(30)
    coros = [fix_one(sem, t, i, len(tasks)) for i, t in enumerate(tasks)]

    fixes = {}
    done = 0
    for coro in asyncio.as_completed(coros):
        sid, result = await coro
        done += 1
        if result:
            fixes[sid] = result
        if done % 20 == 0 or done == len(tasks):
            print(f"  [{done}/{len(tasks)}] done, {len(fixes)} fixed", flush=True)

    # Verify hard constraints
    with open("/Users/minimax/Desktop/FinIF/current/sft_data/constraint_gen_output_v3.jsonl") as f:
        constraints = {json.loads(l)["sample_id"]: json.loads(l) for l in f}

    pass_count = 0
    fail_details = []
    for sid, fixed_text in fixes.items():
        cons = constraints[sid]["sampled_constraints"]
        all_pass = True
        fails = []
        for i, c in enumerate(cons):
            if c["type"] == "hard":
                fn = getattr(checkers, c["checker"], None)
                if fn:
                    ok = fn(fixed_text, c.get("params"))
                    if not ok:
                        all_pass = False
                        fails.append(c.get("tag", c["checker"]))
        if all_pass:
            pass_count += 1
        else:
            fail_details.append({"sid": sid, "still_fail": fails})

    print(f"\nHard check verification: {pass_count}/{len(fixes)} all-pass", flush=True)
    if fail_details:
        print(f"Still failing hard: {len(fail_details)}", flush=True)
        for fd in fail_details[:10]:
            print(f"  {fd['sid']}: {fd['still_fail']}", flush=True)

    out = "/Users/minimax/Desktop/FinIF/current/sft_data/flash_repair_v2.json"
    if args.skip_existing and existing:
        existing.update(fixes)
        fixes = existing
    with open(out, "w") as f:
        json.dump(fixes, f, ensure_ascii=False, indent=2)
    print(f"\n→ {out} ({len(fixes)} entries)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
