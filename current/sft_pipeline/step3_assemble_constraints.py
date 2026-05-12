#!/usr/bin/env python3
"""
Step 3: 约束组装
对 query_pool 中每条 query，采样可见约束 + 附加隐性 checker，拼装 prompt。

约束 = 显性指令（模型看到的附加要求）：G1-G10, F6-F12（共17个）
Checker = 隐性验证（模型看不到，后台验证用）：F1-F5 的 params

输出: data/samples_raw.jsonl
"""
import json, os, random

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
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


GENERAL_IDS = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
FINANCIAL_SOFT_IDS = ["F6", "F7", "F8", "F9", "F10", "F11", "F12"]
FINANCIAL_VISIBLE_HARD_IDS = ["F2", "F3", "F4", "F5"]

EXCLUSIVE_PAIRS = [
    {"G1", "G8"}, {"G1", "G4"}, {"G1", "G6"}, {"G1", "G7"},
    {"G2", "G3"},
]


def check_exclusive(selected_ids):
    for pair in EXCLUSIVE_PAIRS:
        if pair.issubset(set(selected_ids)):
            return False
    return True


def render_general(cid, cfg):
    template = cfg["template"]
    params = {}
    if cid == "G2":
        n = random.choice(cfg["params_schema"]["N"])
        template = template.replace("{N}", str(n))
        params = {"max_words": n}
    elif cid == "G3":
        r = random.choice(cfg["params_schema"]["ranges"])
        template = template.replace("{min_words}", str(r[0])).replace("{max_words}", str(r[1]))
        params = {"min_words": r[0], "max_words": r[1]}
    elif cid == "G4":
        n = random.choice(cfg["params_schema"]["N"])
        template = template.replace("{N}", str(n))
        params = {"min_sections": n}
    elif cid == "G5":
        r = random.choice(cfg["params_schema"]["ranges"])
        template = template.replace("{min_count}", str(r[0])).replace("{max_count}", str(r[1]))
        params = {"min_count": r[0], "max_count": r[1]}
    elif cid == "G8":
        template = template.replace("{content_desc}", "相关数据")
    return {
        "id": cid, "name": cfg["name"], "type": cfg["type"],
        "checker": cfg.get("checker"), "rendered_text": template,
        "params": params if params else None,
    }


def sample_general(n, pool):
    candidates = list(GENERAL_IDS)
    random.shuffle(candidates)
    selected = []
    for cid in candidates:
        if len(selected) >= n:
            break
        test = [s["id"] for s in selected] + [cid]
        if check_exclusive(test):
            selected.append(render_general(cid, pool["general"][cid]))
    return selected


FINANCIAL_SOFT_TEMPLATES = {
    "F6": "判断关键指标的趋势方向（上升/下降/持平），需用数据支撑",
    "F7": "评估相关风险水平，需给出定性判断和定量依据",
    "F8": "检查是否符合相关法规或监管要求，指出合规或违规点",
    "F9": "对比关键数据的差异，用具体数值说明",
    "F10": "核验计算结果或提取数据是否与原文一致",
    "F11": "给出投资评级或类型判断，理由需引用具体数据",
    "F12": "识别并分析异常指标或数据背离现象，引用数据解释原因",
}


def sample_financial_visible_hard(n, context_data, pool):
    """采样 F2-F5 中可用的 hard 约束作为可见约束。"""
    relations = context_data.get("computable_relations", [])
    extracted = context_data.get("extracted_values", {})
    candidates = []

    if len(relations) >= 2:
        candidates.append("F2")
    if any(not k.startswith("_") for k in extracted):
        candidates.append("F3")
    if len(relations) >= 2:
        candidates.append("F4")
    if "_ranking" in extracted:
        candidates.append("F5")

    random.shuffle(candidates)
    selected = []
    for cid in candidates[:n]:
        rendered = render_financial_hard(cid, context_data, pool)
        if rendered:
            selected.append(rendered)
    return selected


def render_financial_hard(cid, context_data, pool):
    relations = context_data.get("computable_relations", [])
    extracted = context_data.get("extracted_values", {})
    cfg = pool["financial"][cid]

    if cid == "F2" and len(relations) >= 2:
        rels = random.sample(relations, 2)
        text = f"依次计算{rels[0]['label']}和{rels[1]['label']}"
        params = {"results": [{"label": r["label"], "expected": r["expected"], "tolerance": r.get("tolerance", 0.5)} for r in rels]}
    elif cid == "F3":
        keys = [k for k in extracted if not k.startswith("_")]
        if not keys:
            return None
        sample_keys = random.sample(keys, min(3, len(keys)))
        text = f"从原文准确提取以下数据：{', '.join(sample_keys)}"
        params = {"expected_values": {k: extracted[k] for k in sample_keys}}
    elif cid == "F4" and relations:
        rel = random.choice(relations)
        text = f"推导{rel['label']}的完整计算过程"
        params = {"checks": [{"label": rel["label"], "expected": rel["expected"], "tolerance": rel.get("tolerance", 0.5), "formula": rel.get("formula", "")}]}
    elif cid == "F5" and "_ranking" in extracted:
        text = "按正确顺序排列相关项目"
        params = {"ranking": json.loads(extracted["_ranking"])}
    else:
        return None

    return {
        "id": cid, "name": cfg["name"], "type": "hard",
        "checker": cfg.get("checker"), "rendered_text": text,
        "params": params,
    }


def sample_financial_soft(n, pool):
    candidates = list(FINANCIAL_SOFT_IDS)
    random.shuffle(candidates)
    selected = []
    for cid in candidates[:n]:
        cfg = pool["financial"][cid]
        selected.append({
            "id": cid, "name": cfg["name"], "type": "soft",
            "checker": None, "rendered_text": FINANCIAL_SOFT_TEMPLATES[cid],
            "params": None,
        })
    return selected


def build_hidden_checkers(context_data):
    """F1 只做隐性验证，不展示给模型。"""
    checkers = []
    relations = context_data.get("computable_relations", [])
    for rel in relations:
        checkers.append({
            "id": "F1", "checker": "check_computation_result",
            "params": {"results": [{"label": rel["label"], "expected": rel["expected"], "tolerance": rel.get("tolerance", 0.5)}]},
        })
    return checkers


def assemble_prompt(context_text, query_text, constraints):
    if not constraints:
        return f"{context_text}\n\n{query_text}"

    constraint_lines = []
    for i, c in enumerate(constraints, 1):
        constraint_lines.append(f"（{i}）{c['rendered_text']}")

    return f"""{context_text}

{query_text}

请在回答时严格遵守以下附加要求：
{chr(10).join(constraint_lines)}"""


def main():
    context_pool = {c["case_id"]: c for c in load_jsonl(os.path.join(PIPELINE_DIR, "data", "context_pool.jsonl"))}
    queries = load_jsonl(os.path.join(PIPELINE_DIR, "data", "query_pool.jsonl"))
    pool = load_json(os.path.join(PIPELINE_DIR, "config", "constraint_pool.json"))

    print(f"Loaded {len(context_pool)} contexts, {len(queries)} queries")

    samples = []
    for q in queries:
        case_id = q["case_id"]
        ctx = context_pool.get(case_id)
        if not ctx:
            continue

        n_total = random.randint(2, 4)
        n_general = random.randint(1, min(2, n_total))
        n_fin_soft = max(1, n_total - n_general - 1)
        n_fin_hard = n_total - n_general - n_fin_soft

        general_cs = sample_general(n_general, pool)
        fin_soft_cs = sample_financial_soft(n_fin_soft, pool)
        fin_hard_cs = sample_financial_visible_hard(n_fin_hard, ctx, pool)
        visible_cs = general_cs + fin_soft_cs + fin_hard_cs
        random.shuffle(visible_cs)

        hidden_checkers = build_hidden_checkers(ctx)

        prompt = assemble_prompt(ctx["text"], q["query_text"], visible_cs)

        sample = {
            "sample_id": f"S-{q['query_id']}",
            "query_id": q["query_id"],
            "case_id": case_id,
            "L1": q["L1"],
            "L2": q["L2"],
            "variant_type": q.get("variant_type", ""),
            "context_text": ctx["text"],
            "query_text": q["query_text"],
            "constraints": visible_cs,
            "hidden_checkers": hidden_checkers,
            "n_constraints": len(visible_cs),
            "n_general": sum(1 for c in visible_cs if c["id"].startswith("G")),
            "n_financial_soft": sum(1 for c in visible_cs if c["id"].startswith("F")),
            "n_hidden_checkers": len(hidden_checkers),
            "prompt": prompt,
        }
        samples.append(sample)

    output_file = os.path.join(PIPELINE_DIR, "data", "samples_raw.jsonl")
    with open(output_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    avg_cs = sum(s["n_constraints"] for s in samples) / len(samples)
    avg_g = sum(s["n_general"] for s in samples) / len(samples)
    avg_fs = sum(s["n_financial_soft"] for s in samples) / len(samples)
    avg_hc = sum(s["n_hidden_checkers"] for s in samples) / len(samples)
    print(f"\nGenerated {len(samples)} samples")
    print(f"Visible constraints: avg {avg_cs:.1f} (general {avg_g:.1f} + financial-soft {avg_fs:.1f})")
    print(f"Hidden checkers: avg {avg_hc:.1f}")

    from collections import Counter
    cid_counter = Counter()
    for s in samples:
        for c in s["constraints"]:
            cid_counter[c["id"]] += 1
    print("\nVisible constraint usage:")
    for cid, cnt in sorted(cid_counter.items()):
        print(f"  {cid}: {cnt}")

    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()
