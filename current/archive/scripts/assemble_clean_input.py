#!/usr/bin/env python3
"""
组装 query 清洗的 LLM 输入数据。
输出 JSONL，每行包含 id、system、user，拿去批量调模型即可。

用法:
  python3 assemble_clean_input.py
  # 输出:
  #   clean_input_bench.jsonl   (100 条)
  #   clean_input_sft.jsonl     (2134 条)
"""
import json, os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """你是金融NLP数据清洗员。

## 任务
我会给你一段完整的prompt。prompt的末尾可能有一个"约束块"，以"请在回答时严格遵守以下附加要求"开头。

你的任务：检查约束块**之前**的正文部分，找出其中的格式/排版/结构类指令，从正文中删除它们，并列出被删除的内容（以便后续追加到约束块中）。

## 什么算格式/排版/结构类指令（需要移走）
- 输出格式要求："以表格形式""制作表格""用JSON格式输出""用列表列出"
- 字数/排版要求："控制在500字""不超过300字""分3个段落""使用二级标题"
- 格式动词短语："以下列格式输出""按照以下结构""以Markdown格式"
- 视觉排版指令："编号列表""加粗关键词""使用引用块"

## 什么不算（需要保留在正文中）
- 核心信息需求（要什么数据、做什么分析、比较什么）
- 具体数据字段（如"包含收益率、风险指标、持仓占比"）
- 计算/推理任务（如"计算超额收益率""展示计算过程"）
- 结构性信息组织（如"分4个方面分析""从以下角度""分别计算"）
- 上下文数据（金融数据表格、公告原文等）——这些绝对不能动

## 判断标准
去掉这句话后，信息需求本身会缺失 → 保留
去掉这句话后，只是换了个呈现方式 → 移走

## 改写原则
- 最小改动，只删格式指令，其余文字保持原样
- 如果子项同时含格式和信息需求（如"制作对比表格，包含收益率和风险指标"），只删格式部分（"制作表格"），保留信息需求（"对比收益率和风险指标"）
- 不要改变金融含义，不要添加原文没有的内容
- 约束块本身（"请在回答时严格遵守以下附加要求"及其后面的内容）不要修改，也不要出现在你的输出中"""

USER_TEMPLATE = """以下是完整prompt：

{full_prompt}

---
请输出JSON（不要包裹在markdown代码块中）：
{{"needs_edit": true/false, "cleaned_body": "约束块之前的正文（删除格式指令后）", "moved_constraints": ["被移走的格式指令1", "被移走的格式指令2"]}}

如果正文中没有任何格式/排版类指令，needs_edit设为false，cleaned_body原样返回正文部分，moved_constraints为空数组。
注意：cleaned_body只包含约束块之前的正文，不要包含约束块。"""


def extract_constraint_block(prompt):
    m = re.search(r'(\n*请在回答时严格遵守以下附加要求[：:].*$)', prompt, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def assemble_bench():
    bench_path = os.path.join(SCRIPT_DIR, "benchmark_all.json")
    output_path = os.path.join(SCRIPT_DIR, "clean_input_bench.jsonl")

    with open(bench_path, encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    items = []
    for case in cases:
        cid = case["case_id"]
        user_prompt = USER_TEMPLATE.format(full_prompt=case["prompt"])

        items.append({
            "id": cid,
            "system": SYSTEM_PROMPT,
            "user": user_prompt,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Bench: {len(items)} items → {output_path}")


def assemble_sft():
    samples_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_2134.jsonl")
    constraints_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "constraint_gen_output_v3.jsonl")
    output_path = os.path.join(SCRIPT_DIR, "clean_input_sft.jsonl")

    with open(samples_path, encoding="utf-8") as f:
        samples = {s["sample_id"]: s for l in f if l.strip() for s in [json.loads(l)]}

    constraints = {}
    with open(constraints_path, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                c = json.loads(l)
                constraints[c["sample_id"]] = c

    items = []
    for sid in sorted(samples.keys()):
        sample = samples[sid]
        context = sample.get("context_text", "")
        query = sample.get("query_text", "")
        constraint_text = constraints[sid]["constraint_text"]

        full_prompt = f"{context}\n\n{query}\n\n{constraint_text}"
        user_prompt = USER_TEMPLATE.format(full_prompt=full_prompt)

        items.append({
            "id": sid,
            "system": SYSTEM_PROMPT,
            "user": user_prompt,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"SFT: {len(items)} items → {output_path}")


if __name__ == "__main__":
    assemble_bench()
    assemble_sft()
