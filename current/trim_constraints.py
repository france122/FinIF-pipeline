#!/usr/bin/env python3
"""
缩减 benchmark 约束数量：从 3-6 → 1-5
目标分布: 1(10), 2(20), 3(30), 4(25), 5(15)
"""
import json, os, re, random
from collections import defaultdict, Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 42

def load_data():
    with open(os.path.join(SCRIPT_DIR, "benchmark", "eval_config_all.json"), encoding="utf-8") as f:
        eval_cfg = json.load(f)
    with open(os.path.join(SCRIPT_DIR, "benchmark", "benchmark_all.json"), encoding="utf-8") as f:
        bench = json.load(f)
    return eval_cfg, bench

def c_num(key):
    return int(key.split("#C")[1])

def group_by_case(constraints):
    groups = defaultdict(list)
    for key, cfg in constraints.items():
        cid = key.split("#")[0]
        groups[cid].append((key, cfg))
    for cid in groups:
        groups[cid].sort(key=lambda x: c_num(x[0]))
    return dict(groups)

def assign_targets(case_groups, rng):
    """Assign target constraint count to each case."""
    target_dist = {1: 15, 2: 20, 3: 30, 4: 20, 5: 15}

    current_sizes = {}
    for cid, cons in case_groups.items():
        current_sizes[cid] = len(cons)

    by_size = defaultdict(list)
    for cid, sz in current_sizes.items():
        by_size[sz].append(cid)
    for sz in by_size:
        rng.shuffle(by_size[sz])

    targets = {}
    remaining = dict(target_dist)

    # 原3条(16) → 保持3条×16
    for cid in by_size[3]:
        targets[cid] = 3

    # 原4条(32) → 1条×15, 2条×7, 3条×10
    for cid in by_size[4][:15]:
        targets[cid] = 1
    for cid in by_size[4][15:22]:
        targets[cid] = 2
    for cid in by_size[4][22:]:
        targets[cid] = 3

    # 原5条(24) → 2条×13, 3条×4, 4条×7
    for cid in by_size[5][:13]:
        targets[cid] = 2
    for cid in by_size[5][13:17]:
        targets[cid] = 3
    for cid in by_size[5][17:]:
        targets[cid] = 4

    # 原6条(28) → 4条×13, 5条×15
    for cid in by_size[6][:13]:
        targets[cid] = 4
    for cid in by_size[6][13:]:
        targets[cid] = 5

    # Verify
    result_dist = Counter(targets.values())
    print(f"目标分布: {dict(sorted(result_dist.items()))}")
    assert result_dist == target_dist, f"分布不匹配: {result_dist} vs {target_dist}"

    return targets

def choose_to_keep(constraints_list, keep_n, global_remaining, rng):
    """Choose which constraints to keep, maintaining tag diversity."""
    if keep_n >= len(constraints_list):
        return [k for k, _ in constraints_list]

    n_drop = len(constraints_list) - keep_n

    tag_in_case = defaultdict(list)
    for key, cfg in constraints_list:
        tag_in_case[cfg["tag"]].append((key, cfg))

    drop_keys = set()

    # Pass 1: drop duplicates within same tag first
    for tag, items in tag_in_case.items():
        if len(items) > 1 and len(drop_keys) < n_drop:
            drop_keys.add(items[0][0])
            if len(drop_keys) >= n_drop:
                break

    # Pass 2: prefer dropping constraints from globally over-represented tags
    if len(drop_keys) < n_drop:
        remaining = [(k, c) for k, c in constraints_list if k not in drop_keys]
        remaining.sort(key=lambda x: (-global_remaining[x[1]["tag"]], rng.random()))
        for key, cfg in remaining:
            if len(drop_keys) >= n_drop:
                break
            drop_keys.add(key)

    for key, cfg in constraints_list:
        if key in drop_keys:
            global_remaining[cfg["tag"]] -= 1

    return [k for k, _ in constraints_list if k not in drop_keys]

def update_prompt(prompt, original_count, keep_indices):
    """Remove dropped constraint lines from prompt and renumber."""
    # Find 附加要求 section
    pattern = r'（(\d+)）([^\n]+)'

    lines = prompt.split('\n')
    req_start = None
    for i, line in enumerate(lines):
        if '附加要求' in line:
            req_start = i
            break

    if req_start is None:
        return prompt

    # Collect requirement lines (they follow the 附加要求 line)
    req_lines = []
    req_line_indices = []
    for i in range(req_start + 1, len(lines)):
        m = re.match(r'^（(\d+)）(.+)$', lines[i].strip())
        if m:
            req_lines.append((int(m.group(1)), m.group(2), i))
            req_line_indices.append(i)
        elif lines[i].strip() and req_lines:
            break

    # keep_indices is 0-based list of which to keep
    new_lines = list(lines)

    # Mark lines for removal
    remove_set = set()
    for idx, (num, text, line_i) in enumerate(req_lines):
        if idx not in keep_indices:
            remove_set.add(line_i)

    # Build new prompt
    result = []
    new_num = 1
    for i, line in enumerate(new_lines):
        if i in remove_set:
            continue
        if i in req_line_indices:
            m = re.match(r'^(\s*)（\d+）(.+)$', line)
            if m:
                line = f"{m.group(1)}（{new_num}）{m.group(2)}"
                new_num += 1
        result.append(line)

    return '\n'.join(result)

def main():
    rng = random.Random(SEED)
    eval_cfg, bench = load_data()
    constraints = eval_cfg["constraints"]
    cases = bench["cases"]

    case_groups = group_by_case(constraints)

    print(f"原始: {len(constraints)} 约束, {len(case_groups)} cases")
    print(f"原始分布: {dict(sorted(Counter(len(v) for v in case_groups.values()).items()))}")

    targets = assign_targets(case_groups, rng)

    # Initialize global_remaining with current tag counts
    global_remaining = Counter(cfg["tag"] for _, cfg in sum(case_groups.values(), []))

    # Decide which constraints to keep for each case
    keep_map = {}
    for cid in sorted(case_groups.keys()):
        cons = case_groups[cid]
        target = targets[cid]
        kept_keys = choose_to_keep(cons, target, global_remaining, rng)
        keep_map[cid] = kept_keys

    # Build new eval_config
    new_constraints = {}
    for cid, kept_keys in keep_map.items():
        for key in kept_keys:
            new_constraints[key] = constraints[key]

    # Update prompts in benchmark_all.json
    case_lookup = {c["case_id"]: c for c in cases}
    for cid, cons in case_groups.items():
        kept_keys = set(keep_map[cid])
        keep_indices = [i for i, (k, _) in enumerate(cons) if k in kept_keys]

        case = case_lookup[cid]
        case["prompt"] = update_prompt(case["prompt"], len(cons), keep_indices)

    # Stats
    new_dist = Counter()
    for cid, keys in keep_map.items():
        new_dist[len(keys)] += 1

    print(f"\n新分布: {dict(sorted(new_dist.items()))}")
    print(f"新约束总数: {len(new_constraints)} (砍了 {len(constraints) - len(new_constraints)})")

    # Tag coverage
    old_tags = Counter(v["tag"] for v in constraints.values())
    new_tags = Counter(v["tag"] for v in new_constraints.values())
    print(f"\nTag 覆盖:")
    for tag in sorted(old_tags.keys()):
        old_n = old_tags[tag]
        new_n = new_tags.get(tag, 0)
        pct = new_n / old_n * 100
        marker = " ⚠️" if pct < 40 else ""
        print(f"  {tag}: {old_n} → {new_n} ({pct:.0f}%){marker}")

    # Hard/soft ratio
    old_hard = sum(1 for v in constraints.values() if v["type"] == "hard")
    old_soft = sum(1 for v in constraints.values() if v["type"] == "soft")
    new_hard = sum(1 for v in new_constraints.values() if v["type"] == "hard")
    new_soft = sum(1 for v in new_constraints.values() if v["type"] == "soft")
    print(f"\nHard/Soft: {old_hard}/{old_soft} → {new_hard}/{new_soft}")

    # Write outputs
    eval_cfg["constraints"] = new_constraints
    with open(os.path.join(SCRIPT_DIR, "benchmark", "eval_config_all.json"), "w", encoding="utf-8") as f:
        json.dump(eval_cfg, f, ensure_ascii=False, indent=2)

    bench["cases"] = cases
    with open(os.path.join(SCRIPT_DIR, "benchmark", "benchmark_all.json"), "w", encoding="utf-8") as f:
        json.dump(bench, f, ensure_ascii=False, indent=2)

    print(f"\n已更新 eval_config_all.json 和 benchmark_all.json")

if __name__ == "__main__":
    main()
