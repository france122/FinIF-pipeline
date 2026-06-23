#!/usr/bin/env python3
"""
FinIF SFT Training Data — Stage 2: Response Generation (RFT)
用 DS-V4-Flash-Thinking 生成 K=4 候选回复
"""
import json, os, sys, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-reasoner"  # DS-V4-Flash-Thinking
K = 4
TEMPERATURE = 0.7

SYSTEM_PROMPT = """你是一个专业的金融分析助手。请严格按照用户的输出格式要求回答问题。
- 如果要求Markdown格式，使用标准Markdown语法
- 如果要求JSON格式，仅输出有效JSON
- 如果要求计算，展示完整计算过程
- 不编造原文中不存在的数据
- 语言专业规范"""


def generate_one(prompt, case_id, k_idx):
    """生成单个回复"""
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=4096,
            )
            content = r.choices[0].message.content or ""
            reasoning = getattr(r.choices[0].message, "reasoning_content", "") or ""
            return {
                "case_id": case_id,
                "k": k_idx,
                "response": content,
                "reasoning_content": reasoning,
                "model": MODEL,
            }
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                time.sleep(2 ** attempt * 2)
                continue
            if "402" in err or "quota" in err.lower():
                print(f"  QUOTA ERROR {case_id} k={k_idx}: {err[:80]}")
                return None
            print(f"  FAIL {case_id} k={k_idx}: {err[:80]}")
            if attempt == 2:
                return None
            time.sleep(2)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--k", type=int, default=K)
    parser.add_argument("--start", type=int, default=0, help="Start from prompt index")
    parser.add_argument("--limit", type=int, default=None, help="Max prompts to process")
    parser.add_argument("--dry-run", action="store_true", help="Just show stats")
    args = parser.parse_args()

    with open(os.path.join(SCRIPT_DIR, "training_prompts.json"), encoding="utf-8") as f:
        data = json.load(f)
    prompts = data["prompts"]

    # Load existing responses to skip
    out_path = os.path.join(SCRIPT_DIR, "output", "training_responses_raw.jsonl")
    existing = set()
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    existing.add(f"{obj['case_id']}_k{obj['k']}")

    # Build task list
    tasks = []
    for i, p in enumerate(prompts):
        if i < args.start:
            continue
        if args.limit and i >= args.start + args.limit:
            break
        for k_idx in range(args.k):
            key = f"{p['case_id']}_k{k_idx}"
            if key not in existing:
                tasks.append((p["prompt"], p["case_id"], k_idx))

    total = len(prompts[args.start:args.start + (args.limit or len(prompts))])
    total_gen = total * args.k
    print(f"Prompts: {total}, K={args.k}, Total generations: {total_gen}")
    print(f"Already done: {len(existing)}, Remaining: {len(tasks)}")

    if args.dry_run:
        return

    if not tasks:
        print("All done!")
        return

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    completed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(generate_one, *t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            else:
                failed += 1

            if completed % 20 == 0 or completed == len(tasks):
                print(f"  {completed}/{len(tasks)} (failed: {failed})")

    print(f"\nDone! {completed - failed} responses saved, {failed} failed")


if __name__ == "__main__":
    main()
