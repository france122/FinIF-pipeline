#!/usr/bin/env python3
"""
清理低质量的移走约束：碎片(≤6字)、悬空格式前缀、列头定义。
删除后重新编号约束块，同步更新 prompt。

用法:
  python3 cleanup_moved_constraints.py [--dry-run]
"""
import json, os, re, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def is_junk(text):
    """判断移走的约束是否是低质量的垃圾约束。"""
    # 1. 碎片: ≤6字
    if len(text) <= 6:
        return True
    # 2. 悬空格式前缀: "以下列格式整理" 等，无具体格式说明
    if re.match(r'^(以|按照?|为)(下列|如下|以下)(格式|结构)', text) and len(text) <= 15:
        return True
    # 3. 列头定义: （项目/2024年/2023年/同比增减）
    if re.match(r'^（[^）]+/[^）]+）$', text):
        return True
    return False


def renumber_constraint_text(header, items):
    """重新编号约束块。"""
    lines = [header]
    for i, item in enumerate(items, start=1):
        lines.append(f"（{i}）{item}")
    return "\n".join(lines)


def main():
    dry_run = "--dry-run" in sys.argv

    samples_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_2134.jsonl")
    constraints_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "constraint_gen_output_v3.jsonl")

    with open(samples_path, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]
    samples_map = {s["sample_id"]: s for s in samples}

    with open(constraints_path, encoding="utf-8") as f:
        constraints = [json.loads(l) for l in f if l.strip()]

    total_removed = 0
    affected_samples = 0

    for c in constraints:
        ct = c["constraint_text"]
        n_sampled = len(c.get("sampled_constraints", []))

        lines = ct.split("\n")
        header = lines[0]  # "请在回答时严格遵守以下附加要求："
        items = []
        for line in lines[1:]:
            m = re.match(r'^（\d+）(.+)$', line.strip())
            if m:
                items.append(m.group(1))

        if len(items) <= n_sampled:
            continue

        sampled_items = items[:n_sampled]
        moved_items = items[n_sampled:]

        kept = [m for m in moved_items if not is_junk(m)]
        removed = [m for m in moved_items if is_junk(m)]

        if not removed:
            continue

        total_removed += len(removed)
        affected_samples += 1

        if dry_run and affected_samples <= 5:
            print(f"{c['sample_id']}: removing {len(removed)}")
            for r in removed:
                print(f"  - \"{r}\"")

        new_items = sampled_items + kept
        c["constraint_text"] = renumber_constraint_text(header, new_items)

        sample = samples_map.get(c["sample_id"])
        if sample:
            context = sample.get("context_text", "")
            query = sample.get("query_text", "")
            if context:
                sample["prompt"] = f"{context}\n\n{query}\n\n{c['constraint_text']}"
            else:
                sample["prompt"] = f"{query}\n\n{c['constraint_text']}"

    print(f"\n删除 {total_removed} 条低质量约束 (涉及 {affected_samples} 个 sample)")

    # 验证约束数分布
    from collections import Counter
    dist = Counter()
    for c in constraints:
        n = len(re.findall(r'（\d+）', c["constraint_text"]))
        dist[n] += 1
    print("\n约束数分布 (清理后):")
    for k in sorted(dist.keys()):
        print(f"  N={k}: {dist[k]} ({dist[k]/len(constraints)*100:.1f}%)")

    if dry_run:
        print("\n[DRY RUN] 未写入文件")
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
