#!/usr/bin/env python3
"""
FinIF SFT Training Data — Stage 4: Format for Training
将选出的 (prompt, response) 对格式化为 Qwen3 SFT 训练格式
"""
import json, os, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """你是一个专业的金融分析助手。请严格按照用户的输出格式要求回答问题。
- 如果要求Markdown格式，使用标准Markdown语法
- 如果要求JSON格式，仅输出有效JSON
- 如果要求计算，展示完整计算过程
- 不编造原文中不存在的数据
- 语言专业规范"""


def format_qwen3_sft(prompt, response, enable_thinking=False):
    """格式化为 Qwen3 ChatML 格式

    Non-thinking mode (default):
    response 前加 <think>\n</think>\n 空标签
    """
    if enable_thinking:
        content = response
    else:
        content = f"<think>\n</think>\n{response}"

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": content},
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--thinking", action="store_true", help="Enable thinking tags (default: non-thinking)")
    parser.add_argument("--min-pass-rate", type=float, default=0.7, help="Filter by min pass rate")
    args = parser.parse_args()

    input_path = os.path.join(SCRIPT_DIR, "output", "training_selected.jsonl")
    if not os.path.isfile(input_path):
        print(f"No selected data found at {input_path}")
        print("Run score_training_data.py first.")
        return

    items = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                if obj.get("pass_rate", 0) >= args.min_pass_rate:
                    items.append(obj)

    print(f"Loaded {len(items)} selected responses (pass_rate >= {args.min_pass_rate:.1%})")

    sft_data = []
    for item in items:
        sft_item = format_qwen3_sft(item["prompt"], item["response"], args.thinking)
        sft_item["metadata"] = {
            "case_id": item["case_id"],
            "pass_rate": item["pass_rate"],
            "template": item.get("template", ""),
            "company": item.get("company", ""),
        }
        sft_data.append(sft_item)

    # Save
    mode = "thinking" if args.thinking else "non-thinking"
    out_path = os.path.join(SCRIPT_DIR, "output", f"sft_data_{mode}.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for item in sft_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Saved {len(sft_data)} SFT samples to {out_path}")
    print(f"Mode: {mode}")

    # Stats
    from collections import Counter
    templates = Counter(item["metadata"]["template"] for item in sft_data)
    print(f"\nPer template:")
    for t, c in sorted(templates.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
