#!/usr/bin/env python3
"""
将 LLM 清洗结果应用回 SFT 训练数据。

读取:
  sft_data/sft_clean_data.jsonl           (GPT-5 清洗结果)
  sft_pipeline/data/samples_clean_2134.jsonl
  sft_pipeline/data/constraint_gen_output_v3.jsonl

写入:
  sft_pipeline/data/samples_clean_2134.jsonl   (覆盖)
  sft_pipeline/data/constraint_gen_output_v3.jsonl (覆盖)

用法:
  python3 apply_clean_sft.py [--dry-run]
"""
import json, os, re, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_PREFIX = "以下是完整prompt：\n\n"

DEDUP_KEYWORDS = {
    "table": ["表格", "Markdown表格", "markdown表格"],
    "json":  ["JSON格式", "json格式", "JSON输出"],
    "list":  ["列表", "编号列表", "列出"],
    "word":  ["不超过", "控制在", "字以内", "字左右"],
    "heading": ["标题", "二级标题", "三级标题"],
    "bold":  ["加粗"],
    "quote": ["引用块"],
    "code":  ["代码块"],
}


def is_duplicate(moved_text, existing_constraint_text):
    """检查 moved_text 是否与 existing_constraint_text 中的约束重复。"""
    for _group, keywords in DEDUP_KEYWORDS.items():
        moved_hits = any(kw in moved_text for kw in keywords)
        if not moved_hits:
            continue
        for line in existing_constraint_text.split("\n"):
            if any(kw in line for kw in keywords):
                return True
    return False


def count_existing_constraints(constraint_text):
    return len(re.findall(r'（\d+）', constraint_text))


def extract_cleaned_query(cleaned_body, context_text):
    """从 cleaned_body 中提取清洗后的 query（去掉 context 前缀）。"""
    body = cleaned_body

    if body.startswith(TEMPLATE_PREFIX):
        body = body[len(TEMPLATE_PREFIX):]

    if not context_text:
        return body.strip()

    if body.startswith(context_text):
        return body[len(context_text):].strip()

    # 模糊匹配: GPT 可能微改了 context 中的空格/标点
    # 尝试逐字符找最长公共前缀
    min_len = min(len(body), len(context_text))
    match_end = 0
    for i in range(min_len):
        if body[i] == context_text[i]:
            match_end = i + 1
        else:
            break

    if match_end > len(context_text) * 0.8:
        return body[len(context_text):].strip()

    return None


def main():
    dry_run = "--dry-run" in sys.argv

    clean_path = os.path.join(SCRIPT_DIR, "sft_data", "sft_clean_data.jsonl")
    samples_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_2134.jsonl")
    constraints_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "constraint_gen_output_v3.jsonl")

    # --- 1. 读取 GPT 清洗结果 ---
    clean_results = {}
    refusals = 0
    parse_errors = 0

    with open(clean_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            sid = obj["trace_id"]
            llm_resp_str = obj["vulcan_output"]["llm_response"]
            try:
                llm_resp = json.loads(llm_resp_str)
                clean_results[sid] = llm_resp
            except (json.JSONDecodeError, TypeError):
                refusals += 1

    print(f"清洗结果: {len(clean_results)} 条解析成功, {refusals} 条拒绝/解析失败")

    # --- 2. 读取原始数据 ---
    with open(samples_path, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]
    samples_map = {s["sample_id"]: s for s in samples}

    with open(constraints_path, encoding="utf-8") as f:
        constraints = [json.loads(l) for l in f if l.strip()]
    constraints_map = {c["sample_id"]: c for c in constraints}

    # --- 3. 应用清洗 ---
    edited = 0
    skipped = 0
    failed = 0
    total_moved = 0
    total_deduped = 0

    for sid, resp in sorted(clean_results.items()):
        if not resp.get("needs_edit"):
            skipped += 1
            continue

        sample = samples_map.get(sid)
        constraint = constraints_map.get(sid)
        if not sample or not constraint:
            print(f"  WARN {sid}: sample or constraint not found")
            failed += 1
            continue

        cleaned_body = resp["cleaned_body"]
        moved = resp.get("moved_constraints", [])
        moved = [re.sub(r'^[（(]\s*\d*\s*[）)]\s*', '', m.strip()) for m in moved]
        moved = [m for m in moved if m]

        if not moved:
            skipped += 1
            continue

        # 去重: 跳过与已有约束重复的移走指令
        ct = constraint["constraint_text"]
        deduped = [m for m in moved if not is_duplicate(m, ct)]
        n_deduped = len(moved) - len(deduped)
        moved = deduped
        total_deduped += n_deduped

        if not moved:
            skipped += 1
            continue

        context = sample.get("context_text", "")
        cleaned_query = extract_cleaned_query(cleaned_body, context)

        if cleaned_query is None:
            print(f"  WARN {sid}: cannot extract cleaned query (context mismatch)")
            failed += 1
            continue

        # 更新 constraint_text: 追加移走的约束
        ct = constraint["constraint_text"]
        n = count_existing_constraints(ct)
        for i, mc in enumerate(moved, start=n + 1):
            ct += f"\n（{i}）{mc}"
        constraint["constraint_text"] = ct

        # 更新 query_text
        old_query = sample["query_text"]
        sample["query_text"] = cleaned_query

        # 重建 prompt
        if context:
            sample["prompt"] = f"{context}\n\n{cleaned_query}\n\n{ct}"
        else:
            sample["prompt"] = f"{cleaned_query}\n\n{ct}"

        edited += 1
        total_moved += len(moved)

        if edited <= 10 or dry_run:
            print(f"  {sid}: moved {len(moved)} constraints")
            for m in moved:
                print(f"    + {m}")

    print(f"\n汇总: {edited} edited, {skipped} unchanged, {failed} failed, {refusals} refused")
    print(f"  共移动 {total_moved} 条格式指令到约束块")
    print(f"  去重跳过 {total_deduped} 条重复约束")

    if dry_run:
        print("\n[DRY RUN] 未写入文件")
        return

    # --- 4. 写回文件 ---
    # 按原始顺序写回
    with open(samples_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"  → {samples_path}")

    with open(constraints_path, "w", encoding="utf-8") as f:
        for c in constraints:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"  → {constraints_path}")


if __name__ == "__main__":
    main()
