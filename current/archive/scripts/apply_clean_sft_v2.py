#!/usr/bin/env python3
"""
应用 GPT-5 清洗结果 v2：
策略：
- 有"制作/编制"移走 → 保留原始 query + 仅加纯格式约束到约束块
- 无"制作/编制" → 用 GPT-5 cleaned query + 加格式约束到约束块
- "绘制XX图" → 丢弃（模型无法画图）
- 碎片/垃圾/重复 → 丢弃

用法: python3 apply_clean_sft_v2.py [--dry-run]
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


def is_junk(text):
    if len(text) <= 6:
        return True
    if re.match(r'^(以|按照?|为)(下列|如下|以下)(格式|结构)', text) and len(text) <= 15:
        return True
    if re.match(r'^（[^）]+/[^）]+）$', text):
        return True
    return False


def is_impossible(text):
    """模型无法执行的指令（如绘制图表）"""
    if re.search(r'(绘制|画出|绘出|作图)', text):
        return True
    return False


def has_task_verb(text):
    """包含"制作/编制"等任务动词——不应作为约束"""
    return bool(re.search(r'(制作|编制)', text))


def is_duplicate(text, existing_ct):
    for _group, kws in DEDUP_KEYWORDS.items():
        if any(kw in text for kw in kws):
            for line in existing_ct.split("\n"):
                if any(kw in line for kw in kws):
                    return True
    return False


def extract_cleaned_query(cleaned_body, context_text):
    body = cleaned_body
    if body.startswith(TEMPLATE_PREFIX):
        body = body[len(TEMPLATE_PREFIX):]
    if not context_text:
        return body.strip()
    if body.startswith(context_text):
        return body[len(context_text):].strip()
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

    clean_results = {}
    refusals = 0
    with open(clean_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            sid = obj["trace_id"]
            try:
                resp = json.loads(obj["vulcan_output"]["llm_response"])
                clean_results[sid] = resp
            except (json.JSONDecodeError, TypeError):
                refusals += 1

    with open(samples_path, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]
    samples_map = {s["sample_id"]: s for s in samples}

    with open(constraints_path, encoding="utf-8") as f:
        constraints = [json.loads(l) for l in f if l.strip()]
    constraints_map = {c["sample_id"]: c for c in constraints}

    stats = {"edited": 0, "skipped": 0, "failed": 0,
             "use_cleaned": 0, "use_original": 0,
             "format_added": 0, "task_discarded": 0,
             "junk": 0, "dedup": 0, "impossible": 0}

    for sid, resp in sorted(clean_results.items()):
        if not resp.get("needs_edit"):
            stats["skipped"] += 1
            continue

        sample = samples_map.get(sid)
        constraint = constraints_map.get(sid)
        if not sample or not constraint:
            stats["failed"] += 1
            continue

        moved = resp.get("moved_constraints", [])
        moved = [re.sub(r'^[（(]\s*\d*\s*[）)]\s*', '', m.strip()) for m in moved]
        moved = [m for m in moved if m]

        if not moved:
            stats["skipped"] += 1
            continue

        context = sample.get("context_text", "")

        # 分类 moved constraints
        junk_items = [m for m in moved if is_junk(m)]
        impossible_items = [m for m in moved if not is_junk(m) and is_impossible(m)]
        task_items = [m for m in moved if not is_junk(m) and not is_impossible(m) and has_task_verb(m)]
        remaining = [m for m in moved if not is_junk(m) and not is_impossible(m) and not has_task_verb(m)]

        ct = constraint["constraint_text"]
        format_items = [m for m in remaining if not is_duplicate(m, ct)]
        dedup_items = [m for m in remaining if is_duplicate(m, ct)]

        stats["junk"] += len(junk_items)
        stats["impossible"] += len(impossible_items)
        stats["task_discarded"] += len(task_items)

        # 决定使用哪个 query
        if task_items:
            # 有"制作/编制"被移走 → 用原始 query（保证任务描述完整）
            # 不加任何 moved constraints 到约束块——它们全部来自原始 query，已经在里面了
            stats["use_original"] += 1
            stats["dedup"] += len(dedup_items) + len(format_items)
        else:
            # 只有纯格式被移走 → 用 GPT-5 cleaned query
            cleaned_query = extract_cleaned_query(resp["cleaned_body"], context)
            if cleaned_query is None:
                stats["failed"] += 1
                continue
            sample["query_text"] = cleaned_query
            stats["use_cleaned"] += 1
            stats["dedup"] += len(dedup_items)
            stats["format_added"] += len(format_items)

            # 追加纯格式约束到约束块
            n_existing = len(re.findall(r'（\d+）', ct))
            for i, fc in enumerate(format_items, start=n_existing + 1):
                ct += f"\n（{i}）{fc}"
            constraint["constraint_text"] = ct

        # 重建 prompt
        query = sample["query_text"]
        if context:
            sample["prompt"] = f"{context}\n\n{query}\n\n{ct}"
        else:
            sample["prompt"] = f"{query}\n\n{ct}"

        stats["edited"] += 1

    print(f"清洗结果: {len(clean_results)} 解析成功, {refusals} 拒绝")
    print(f"编辑: {stats['edited']}, 跳过: {stats['skipped']}, 失败: {stats['failed']}")
    print(f"  用 cleaned query: {stats['use_cleaned']}")
    print(f"  用原始 query (有制作/编制): {stats['use_original']}")
    print(f"  格式约束 → 约束块: {stats['format_added']}")
    print(f"  制作/编制 → 丢弃(query已有): {stats['task_discarded']}")
    print(f"  绘制/画图 → 丢弃(不可能): {stats['impossible']}")
    print(f"  垃圾碎片: {stats['junk']}")
    print(f"  去重跳过: {stats['dedup']}")

    from collections import Counter
    dist = Counter()
    for c in constraints:
        n = len(re.findall(r'（\d+）', c["constraint_text"]))
        dist[n] += 1
    print(f"\n约束数分布:")
    for k in sorted(dist.keys()):
        print(f"  N={k}: {dist[k]} ({dist[k]/len(constraints)*100:.1f}%)")

    if dry_run:
        print("\n[DRY RUN] 未写入")
        return

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
