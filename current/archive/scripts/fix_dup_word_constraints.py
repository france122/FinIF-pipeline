#!/usr/bin/env python3
"""
修复字数约束重复：同一 sample 中同时出现 "控制在X到Y字" 和 "不超过Z字"。
策略：保留范围约束（控制在X到Y字），删除不超过约束。
同步更新 constraint_text、sampled_constraints、prompt。

用法: python3 fix_dup_word_constraints.py [--dry-run]
"""
import json, os, re, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_word_count_items(items):
    range_idx = []
    max_idx = []
    for i, text in enumerate(items):
        if re.search(r'控制在\d+到\d+字', text):
            range_idx.append(i)
        elif re.search(r'不超过\d+字', text):
            max_idx.append(i)
    return range_idx, max_idx


def main():
    dry_run = "--dry-run" in sys.argv

    samples_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_2134.jsonl")
    constraints_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "constraint_gen_output_v3.jsonl")

    with open(samples_path, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]
    samples_map = {s["sample_id"]: s for s in samples}

    with open(constraints_path, encoding="utf-8") as f:
        constraints = [json.loads(l) for l in f if l.strip()]

    fixed = 0
    removed_total = 0

    for c in constraints:
        ct = c["constraint_text"]
        lines = ct.split("\n")
        header = lines[0]

        items = []
        for line in lines[1:]:
            m = re.match(r'^（\d+）(.+)$', line.strip())
            if m:
                items.append(m.group(1))

        range_idx, max_idx = find_word_count_items(items)

        if not (range_idx and max_idx):
            continue

        if len(items) - len(max_idx) < 3:
            print(f"  SKIP {c['sample_id']}: N={len(items)} → {len(items)-len(max_idx)} (< 3)")
            continue

        to_remove = set(max_idx)
        new_items = [item for i, item in enumerate(items) if i not in to_remove]
        n_removed = len(to_remove)

        new_sc = [sc for sc in c["sampled_constraints"]
                  if sc.get("checker") != "check_word_limit"]

        new_lines = [header]
        for i, item in enumerate(new_items, start=1):
            new_lines.append(f"（{i}）{item}")
        c["constraint_text"] = "\n".join(new_lines)
        c["sampled_constraints"] = new_sc

        sample = samples_map.get(c["sample_id"])
        if sample:
            context = sample.get("context_text", "")
            query = sample.get("query_text", "")
            if context:
                sample["prompt"] = f"{context}\n\n{query}\n\n{c['constraint_text']}"
            else:
                sample["prompt"] = f"{query}\n\n{c['constraint_text']}"

        fixed += 1
        removed_total += n_removed

        if dry_run or fixed <= 5:
            kept_text = items[range_idx[0]]
            removed_texts = [items[i] for i in max_idx]
            print(f"  {c['sample_id']}: 保留「{kept_text}」, 删除 {removed_texts}")

    print(f"\n修复 {fixed} 个 sample, 删除 {removed_total} 条重复字数约束")

    from collections import Counter
    dist = Counter()
    for c in constraints:
        n = len(re.findall(r'（\d+）', c["constraint_text"]))
        dist[n] += 1
    print("\n约束数分布:")
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
