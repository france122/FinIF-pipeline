#!/usr/bin/env python3
"""
训练数据约束采样 + 文本生成

prepare: 为 2134 条训练样本自由采样约束，用 text_hint 直接拼约束文本，输出 JSONL。
merge:   合并重跑结果。
"""
import json, os, random, re, argparse
from collections import Counter, defaultdict

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
TAXONOMY_PATH = os.path.join(PIPELINE_DIR, "..", "benchmark", "constraint_taxonomy.json")
SAMPLES_PATH = os.path.join(PIPELINE_DIR, "data", "samples_clean_2134.jsonl")
OUTPUT_PATH = os.path.join(PIPELINE_DIR, "data", "constraint_gen_output_v3.jsonl")

random.seed(42)


def load_jsonl(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── param sampling ──────────────────────────────────────────────


def sample_int_param(spec, task_tier, checker_cfg, param_name, sampled):
    td = checker_cfg.get("task_defaults", {}).get(task_tier, {})

    if "relative_to" in spec:
        base_val = sampled[spec["relative_to"]]
        lo, hi = spec["offset"]
        td_offset = td.get(f"{param_name}_offset", td.get(param_name))
        if td_offset:
            lo, hi = td_offset[0], td_offset[1]
        step = spec.get("step", 1)
        candidates = list(range(base_val + lo, base_val + hi + 1, step))
        return random.choice(candidates) if candidates else base_val + lo

    if "options" in spec:
        return random.choice(spec["options"])

    lo, hi = spec["range"]
    td_range = td.get(param_name)
    if td_range:
        lo, hi = td_range[0], td_range[1]
    step = spec.get("step", 1)
    candidates = list(range(lo, hi + 1, step))
    return random.choice(candidates) if candidates else lo


def sample_string_param(spec):
    if "pool" in spec:
        return random.choice(spec["pool"])
    if "options" in spec:
        return random.choice(spec["options"])
    if "default" in spec:
        return spec["default"]
    if "examples" in spec:
        return random.choice(spec["examples"])
    return ""


def sample_string_list_param(spec):
    if "pool" in spec:
        return random.choice(spec["pool"])
    if "default" in spec:
        return spec["default"]
    return []


def sample_params(checker_name, checker_cfg, task_tier):
    pspace = checker_cfg.get("param_space", {})
    if not pspace:
        return {}

    sampled = {}
    sorted_params = sorted(pspace.keys(), key=lambda k: 1 if "relative_to" in pspace[k] else 0)

    for pname in sorted_params:
        spec = pspace[pname]
        ptype = spec.get("type", "string")

        if spec.get("optional") and random.random() < 0.4:
            continue

        if ptype == "int":
            sampled[pname] = sample_int_param(spec, task_tier, checker_cfg, pname, sampled)
        elif ptype == "string":
            sampled[pname] = sample_string_param(spec)
        elif ptype == "string_list":
            sampled[pname] = sample_string_list_param(spec)
        elif ptype == "bool":
            sampled[pname] = spec.get("default", True)

    if checker_name == "check_conditional_trigger" and "trigger" in sampled:
        pool_by = pspace.get("followup", {}).get("pool_by_trigger", {})
        options = pool_by.get(sampled["trigger"], ["风险"])
        sampled["followup"] = random.choice(options)

    return sampled


# ── text rendering ─────────────────────────────────────────────


def format_hint(text_hint, params):
    result = text_hint
    for k, v in params.items():
        if isinstance(v, list):
            result = result.replace(f"{{{k}}}", "、".join(str(x) for x in v))
        else:
            result = result.replace(f"{{{k}}}", str(v))

    if "{forbidden_desc}" in result and "forbidden" in params:
        forbidden = params["forbidden"]
        if isinstance(forbidden, list):
            lq, rq = "“", "”"
            desc = "、".join(lq + w + rq for w in forbidden)
            result = result.replace("{forbidden_desc}", desc)
    if "{kw1}" in result and "required_keywords" in params:
        kws = params["required_keywords"]
        if len(kws) >= 2:
            result = result.replace("{kw1}", kws[0]).replace("{kw2}", kws[1])
        elif len(kws) == 1:
            result = result.replace("{kw1}", kws[0]).replace("{kw2}", kws[0])

    result = re.sub(r'[，,]\s*[^\s]*"\{[a-z_]+\}"', '', result)
    result = re.sub(r'\{[a-z_]+\}', '', result)
    result = result.strip().rstrip("，,")

    return result


def render_constraint_text(sampled_constraints):
    lines = ["请在回答时严格遵守以下附加要求："]
    for i, c in enumerate(sampled_constraints, 1):
        if c["type"] == "soft":
            lines.append(f"（{i}）{c['description']}")
        else:
            hint = format_hint(c.get("text_hint", ""), c.get("params", {}))
            lines.append(f"（{i}）{hint}")
    return "\n".join(lines)


# ── constraint pool & sampling ─────────────────────────────────


CONFLICT_MAP = {
    "check_no_table": ["表格", "制表", "表格形式", "表格呈现", "列表形式呈现"],
    "check_no_list": ["列表", "清单形式", "用列表", "以列表"],
}

EXCLUSION_PAIRS = [
    ("check_markdown_table", "check_no_table"),
    ("check_ordered_list_count", "check_no_list"),
]

JSON_EXCLUDES = {
    "check_markdown_table", "check_ordered_list_count", "check_section_count",
    "check_heading_level", "check_heading_depth", "check_blockquote_count",
    "check_no_table", "check_no_list",
}

N_CONSTRAINT_WEIGHTS = {1: 10, 2: 20, 3: 30, 4: 25, 5: 15}

TAG_BOOST = {"N3": 3.0, "S3": 3.0, "F4": 3.0}


def build_constraint_pool(hard_checkers, soft_templates):
    pool = []
    for name, cfg in hard_checkers.items():
        if name.startswith("_"):
            continue
        pool.append({
            "id": name,
            "checker": name,
            "type": "hard",
            "tag": cfg.get("tag", ""),
            "text_hint": cfg.get("text_hint", ""),
            "inv": cfg.get("inv", False),
            "max_uses_per_100": cfg.get("max_uses_per_100", 100),
            "applicable_tasks": cfg.get("applicable_tasks"),
            "param_space": cfg.get("param_space", {}),
            "task_defaults": cfg.get("task_defaults", {}),
            "_cfg": cfg,
        })

    for t in soft_templates:
        pool.append({
            "id": t["id"],
            "type": "soft",
            "tag": t.get("tag", ""),
            "description": t["description"],
            "rubric": t.get("rubric", ""),
            "applicable_tasks": t.get("applicable_tasks"),
            "excludes": set(t.get("excludes", [])),
            "max_uses": t.get("max_uses", 9999),
        })

    return pool


def detect_query_conflicts(query_text):
    blocked = set()
    for checker, keywords in CONFLICT_MAP.items():
        if any(kw in query_text for kw in keywords):
            blocked.add(checker)
    return blocked


def check_exclusions(selected_ids, candidate_id):
    for a, b in EXCLUSION_PAIRS:
        if candidate_id == a and b in selected_ids:
            return False
        if candidate_id == b and a in selected_ids:
            return False
    if candidate_id == "check_json_format":
        if selected_ids & JSON_EXCLUDES:
            return False
    if "check_json_format" in selected_ids:
        if candidate_id in JSON_EXCLUDES:
            return False
    return True


def check_soft_exclusions(selected_ids, candidate):
    excludes = candidate.get("excludes", set())
    return not (excludes & selected_ids)


def free_sample_constraints(pool, n, task_tier, query_text, inv_used, total_samples):
    blocked = detect_query_conflicts(query_text)

    candidates = []
    for c in pool:
        cid = c["id"]
        if cid in blocked:
            continue
        applicable = c.get("applicable_tasks")
        if applicable and task_tier not in applicable:
            continue
        if c["type"] == "hard" and c.get("inv", False):
            cap = c.get("max_uses_per_100", 100)
            scaled = max(1, int(cap * total_samples / 100))
            if inv_used.get(cid, 0) >= scaled:
                continue
        if c["type"] == "soft":
            cap = c.get("max_uses", 9999)
            scaled = max(1, int(cap * total_samples / 100))
            if inv_used.get(cid, 0) >= scaled:
                continue
        candidates.append(c)

    selected = []
    selected_ids = set()

    for _ in range(n):
        valid = [c for c in candidates
                 if c["id"] not in selected_ids
                 and check_exclusions(selected_ids, c["id"])
                 and (c["type"] != "soft" or check_soft_exclusions(selected_ids, c))]
        if not valid:
            break

        weights = [(1.0 / (inv_used.get(c["id"], 0) + 1)) * TAG_BOOST.get(c["tag"], 1.0) for c in valid]
        total_w = sum(weights)
        probs = [w / total_w for w in weights]

        r = random.random()
        cumulative = 0
        chosen = valid[-1]
        for c, p in zip(valid, probs):
            cumulative += p
            if r <= cumulative:
                chosen = c
                break

        selected_ids.add(chosen["id"])
        inv_used[chosen["id"]] = inv_used.get(chosen["id"], 0) + 1

        if chosen["type"] == "hard":
            params = sample_params(chosen["checker"], chosen["_cfg"], task_tier)
            selected.append({
                "type": "hard",
                "checker": chosen["checker"],
                "params": params,
                "tag": chosen["tag"],
                "text_hint": chosen["text_hint"],
                "inv": chosen.get("inv", False),
            })
        else:
            selected.append({
                "type": "soft",
                "id": chosen["id"],
                "description": chosen["description"],
                "rubric": chosen["rubric"],
                "tag": chosen["tag"],
            })

    return selected


# ── main ────────────────────────────────────────────────────────


def prepare():
    taxonomy = load_json(TAXONOMY_PATH)
    pool_cfg = taxonomy["constraint_pool"]
    hard_checkers = pool_cfg["hard_checkers"]
    soft_templates = pool_cfg["soft_templates"]["templates"]
    samples = load_jsonl(SAMPLES_PATH)

    pool = build_constraint_pool(hard_checkers, soft_templates)

    print(f"Loaded {len(samples)} training samples")
    print(f"Constraint pool: {sum(1 for c in pool if c['type']=='hard')} hard + "
          f"{sum(1 for c in pool if c['type']=='soft')} soft = {len(pool)} total")

    inv_used = {}
    outputs = []
    checker_counter = Counter()
    tag_counter = Counter()

    for sample in samples:
        n = random.choices(
            list(N_CONSTRAINT_WEIGHTS.keys()),
            weights=list(N_CONSTRAINT_WEIGHTS.values())
        )[0]

        sampled = free_sample_constraints(
            pool, n, sample["L1"], sample.get("query_text", ""),
            inv_used, len(samples)
        )

        for c in sampled:
            if c["type"] == "hard":
                checker_counter[c["checker"]] += 1
            else:
                checker_counter[c["id"]] += 1
            tag_counter[c["tag"]] += 1

        constraint_text = render_constraint_text(sampled)

        output = {
            "sample_id": sample["sample_id"],
            "L1": sample["L1"],
            "L2": sample["L2"],
            "constraint_text": constraint_text,
            "sampled_constraints": sampled,
            "hidden_checkers": sample.get("hidden_checkers", []),
        }
        outputs.append(output)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for o in outputs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    print(f"\nGenerated {len(outputs)} items → {OUTPUT_PATH}")

    print(f"\n── Checker/Template 使用分布 ──")
    for name, cnt in checker_counter.most_common():
        pct = cnt / len(outputs) * 100
        inv_mark = ""
        if name in hard_checkers and hard_checkers[name].get("inv"):
            inv_mark = " [INV]"
        print(f"  {name:<35s} {cnt:>5d} ({pct:>5.1f}%){inv_mark}")

    print(f"\n── Tag 分布 ──")
    for tag, cnt in sorted(tag_counter.items()):
        print(f"  {tag:<6s} {cnt:>5d} ({100*cnt/sum(tag_counter.values()):>5.1f}%)")

    n_dist = Counter(len(o["sampled_constraints"]) for o in outputs)
    print(f"\n── 约束数量分布 ──")
    for n in sorted(n_dist):
        print(f"  {n}条: {n_dist[n]} ({100*n_dist[n]/len(outputs):.1f}%)")

    unique_checkers = set()
    unique_soft = set()
    for o in outputs:
        for c in o["sampled_constraints"]:
            if c["type"] == "hard":
                unique_checkers.add(c["checker"])
            else:
                unique_soft.add(c.get("id", ""))
    hard_total = sum(1 for c in pool if c["type"] == "hard")
    soft_total = sum(1 for c in pool if c["type"] == "soft")
    print(f"\n── 多样性 ──")
    print(f"  Hard checkers used: {len(unique_checkers)}/{hard_total}")
    print(f"  Soft templates used: {len(unique_soft)}/{soft_total}")

    conflict_count = 0
    for o in outputs:
        query = next((s.get("query_text", "") for s in samples if s["sample_id"] == o["sample_id"]), "")
        blocked = detect_query_conflicts(query)
        if any(c.get("checker", "") in blocked for c in o["sampled_constraints"]):
            conflict_count += 1
    print(f"  Query-约束冲突: {conflict_count}")


def merge():
    output_path = os.path.join(PIPELINE_DIR, "data", "constraint_gen_output.jsonl")
    rerun_output_path = os.path.join(PIPELINE_DIR, "data", "constraint_gen_rerun_output.jsonl")
    merged_path = os.path.join(PIPELINE_DIR, "data", "constraint_gen_output_merged.jsonl")

    old = {item["sample_id"]: item for item in load_jsonl(output_path)}
    new = {item["sample_id"]: item for item in load_jsonl(rerun_output_path)}

    replaced = 0
    with open(merged_path, "w", encoding="utf-8") as f:
        for sid in sorted(old.keys()):
            if sid in new:
                f.write(json.dumps(new[sid], ensure_ascii=False) + "\n")
                replaced += 1
            else:
                f.write(json.dumps(old[sid], ensure_ascii=False) + "\n")

    print(f"Merged: {len(old)} total, {replaced} replaced from rerun")
    print(f"  → {merged_path}")


def main():
    parser = argparse.ArgumentParser(description="训练数据约束采样")
    parser.add_argument("command", choices=["prepare", "merge"],
                        help="prepare: 自由采样约束+直接拼文本; merge: 合并重跑结果")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "merge":
        merge()


if __name__ == "__main__":
    main()
