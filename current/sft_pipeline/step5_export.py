#!/usr/bin/env python3
"""
Step 5: 导出 messages + metadata 训练格式
输入: samples_all_2000.jsonl
输出: sft_train_2000.jsonl (messages + metadata)
"""
import json, os
from collections import Counter

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PIPELINE_DIR, "data")

SYSTEM_PROMPT = """你是一位专业的金融分析助手。请严格按照用户的附加要求（格式、字数、内容约束等）完成分析任务。所有计算需展示过程，数据引用需准确标注来源。"""


def main():
    input_path = os.path.join(DATA_DIR, "samples_all_2000.jsonl")
    output_path = os.path.join(DATA_DIR, "sft_train_2000.jsonl")

    samples = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    records = []
    for s in samples:
        record = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": s["prompt"]},
            ],
            "metadata": {
                "sample_id": s["sample_id"],
                "case_id": s["case_id"],
                "query_id": s["query_id"],
                "L1": s["L1"],
                "L2": s["L2"],
                "variant_type": s.get("variant_type", ""),
                "context_source": s.get("context_source", ""),
                "n_constraints": s.get("n_constraints", 0),
                "n_general": s.get("n_general", 0),
                "n_financial_soft": s.get("n_financial_soft", 0),
                "n_financial_hard": s.get("n_financial_hard", 0),
                "n_hidden_checkers": s.get("n_hidden_checkers", 0),
                "constraints": s.get("constraints", []),
                "hidden_checkers": s.get("hidden_checkers", []),
            }
        }
        records.append(record)

    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- 统计 ---
    print(f"Exported {len(records)} records → {output_path}")

    l1 = Counter(r["metadata"]["L1"] for r in records)
    l2 = Counter(r["metadata"]["L2"] for r in records)
    src = Counter(r["metadata"]["context_source"] for r in records)

    print(f"\n=== 分布统计 ===")
    print(f"\nL1:")
    for k, v in sorted(l1.items()):
        print(f"  {k}: {v} ({v/len(records)*100:.1f}%)")

    print(f"\nL2:")
    for k, v in sorted(l2.items()):
        print(f"  {k}: {v} ({v/len(records)*100:.1f}%)")

    print(f"\nContext source:")
    for k, v in sorted(src.items()):
        print(f"  {k or '(legacy)'}: {v}")

    nc = [r["metadata"]["n_constraints"] for r in records]
    print(f"\n约束数: min={min(nc)}, max={max(nc)}, avg={sum(nc)/len(nc):.2f}")

    cid_counter = Counter()
    for r in records:
        for c in r["metadata"]["constraints"]:
            cid_counter[c["id"]] += 1
    print(f"\n约束 ID 频次:")
    for k, v in sorted(cid_counter.items()):
        print(f"  {k}: {v}")

    # 抽样 3 条
    import random
    random.seed(0)
    picks = random.sample(records, 3)
    print(f"\n=== 抽样 3 条 ===")
    for i, p in enumerate(picks):
        meta = p["metadata"]
        prompt_preview = p["messages"][1]["content"][:120].replace("\n", " ")
        constraint_ids = [c["id"] for c in meta["constraints"]]
        print(f"\n[{i+1}] {meta['sample_id']}  L2={meta['L2']}  src={meta.get('context_source','?')}")
        print(f"    约束: {constraint_ids}")
        print(f"    prompt: {prompt_preview}...")


if __name__ == "__main__":
    main()
