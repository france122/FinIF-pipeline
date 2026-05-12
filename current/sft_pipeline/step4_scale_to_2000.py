#!/usr/bin/env python3
"""
Step 4: 扩容到 2000+ 样本（严格 context 分区版）

Context 分区规则：
  A组 = benchmark-only（benchmark_all.json 中的 context）→ 不进训练集
  B组 = training-only（synthetic contexts_T*_new.jsonl）→ 本脚本使用

本脚本只加载 B组 context，确保训练集与 benchmark 无 context 重叠。
"""
import json, os, random, copy, hashlib
from collections import Counter

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PIPELINE_DIR, "data")
CONFIG_DIR = os.path.join(PIPELINE_DIR, "config")


def load_jsonl(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 1. 加载全部 context
# ============================================================
def load_all_contexts():
    """加载 B组 context：synthetic + external（benchmark已不再引用这些external contexts）"""
    ctx_map = {}

    # B组-1: synthetic contexts
    for t in ["T1", "T2", "T3"]:
        for r in load_jsonl(os.path.join(DATA_DIR, f"contexts_{t}_new.jsonl")):
            ctx_map[r["case_id"]] = r

    # B组-2: external contexts（已从 benchmark 移出，可安全用于训练）
    for r in load_jsonl(os.path.join(DATA_DIR, "context_pool_external.jsonl")):
        ctx_map[r["case_id"]] = r

    return ctx_map


# ============================================================
# 2. 为 benchmark / external context 生成 query
# ============================================================
QUERY_TEMPLATES_BY_L2 = {
    "T1.1": [
        "请从以上材料中提取关键数值数据，整理为表格并计算相关指标的变动幅度",
        "请基于以上数据，提取核心数据指标并进行基础运算分析",
        "请从材料中找出主要数值，计算同比/环比变化率",
    ],
    "T1.2": [
        "请分析以上公告中涉及的持股/减持数据，计算关键比例指标",
        "请从以上材料提取财务指标数据，分析其变化趋势",
        "请整理以上材料中的关键财务数据，计算相关增减比例",
    ],
    "T1.3": [
        "请将以上文件的关键信息以JSON格式结构化提取",
        "请以Markdown表格整理以上材料中的核心信息要素",
        "请以Q/A问答格式提取以上材料的关键事实和数据",
    ],
    "T2.1": [
        "请对以上材料进行综合分析，评估其中反映的财务状况和经营趋势",
        "请从盈利能力、偿债能力、运营效率三个维度分析以上数据",
        "请综合以上材料，给出核心指标的分析判断和投资建议",
    ],
    "T2.2": [
        "请对比以上材料中不同板块/产品的数据，分析结构变化",
        "请从多个维度评估以上数据所反映的业务状况",
        "请分析以上材料中各分项指标的占比和变动情况",
    ],
    "T3.1": [
        "请审查以上材料中的数据逻辑一致性，识别可能的异常或矛盾",
        "请基于以上材料推导关键指标间的数量关系，验证其合理性",
        "请从以上材料出发，逆推核心财务指标并与披露值交叉核验",
    ],
    "T3.2": [
        "请对以上材料进行合规审查分析，指出违规要点并量化影响",
        "请撰写以上材料的结构化分析报告，包含事实认定和定量分析",
        "请分析以上案例中的违法行为，评估处罚依据和影响程度",
    ],
    "T3.3": [
        "请交叉核验以上材料中多个数据源的一致性，找出差异并分析原因",
        "请对以上材料中的多步推导链进行验证，指出可能的错误环节",
    ],
}


def generate_queries_for_context(ctx):
    """为单个 context 生成多条 query"""
    l2 = ctx.get("L2", "T1.1")
    case_id = ctx["case_id"]
    templates = QUERY_TEMPLATES_BY_L2.get(l2, QUERY_TEMPLATES_BY_L2["T1.1"])

    # 如果 benchmark context 已有 query，优先用它
    existing_query = ctx.get("query", "")

    queries = []
    if existing_query and len(existing_query) > 10:
        queries.append({
            "query_id": f"Q-{case_id}-V0",
            "case_id": case_id,
            "L1": ctx.get("L1", l2.split(".")[0]),
            "L2": l2,
            "variant_type": "原始",
            "query_text": existing_query,
        })

    for i, tmpl in enumerate(templates):
        queries.append({
            "query_id": f"Q-{case_id}-V{i+1}",
            "case_id": case_id,
            "L1": ctx.get("L1", l2.split(".")[0]),
            "L2": l2,
            "variant_type": "模板生成",
            "query_text": tmpl,
        })

    return queries


# ============================================================
# 3. 约束组装（复用 step3 逻辑）
# ============================================================
GENERAL_IDS = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
FINANCIAL_SOFT_IDS = ["F6", "F7", "F8", "F9", "F10", "F11", "F12"]

EXCLUSIVE_PAIRS = [
    {"G1", "G8"}, {"G1", "G4"}, {"G1", "G6"}, {"G1", "G7"},
    {"G2", "G3"},
]

FINANCIAL_SOFT_TEMPLATES = {
    "F6": "判断关键指标的趋势方向（上升/下降/持平），需用数据支撑",
    "F7": "评估相关风险水平，需给出定性判断和定量依据",
    "F8": "检查是否符合相关法规或监管要求，指出合规或违规点",
    "F9": "对比关键数据的差异，用具体数值说明",
    "F10": "核验计算结果或提取数据是否与原文一致",
    "F11": "给出投资评级或类型判断，理由需引用具体数据",
    "F12": "识别并分析异常指标或数据背离现象，引用数据解释原因",
}


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


def render_financial_hard(cid, context_data, pool):
    relations = context_data.get("computable_relations", [])
    extracted = context_data.get("extracted_values", {})
    cfg = pool["financial"][cid]

    if cid == "F2" and len(relations) >= 2:
        rels = random.sample(relations, 2)
        text = f"依次计算{rels[0]['label']}和{rels[1]['label']}"
        params = {"results": [{"label": r["label"], "expected": r["expected"],
                               "tolerance": r.get("tolerance", 0.5)} for r in rels]}
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
        params = {"checks": [{"label": rel["label"], "expected": rel["expected"],
                               "tolerance": rel.get("tolerance", 0.5),
                               "formula": rel.get("formula", "")}]}
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


def sample_financial_hard(n, context_data, pool):
    relations = context_data.get("computable_relations", [])
    extracted = context_data.get("extracted_values", {})
    candidates = []
    if len(relations) >= 2:
        candidates.append("F2")
    if any(not k.startswith("_") for k in extracted):
        candidates.append("F3")
    if relations:
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


def build_hidden_checkers(context_data):
    checkers = []
    for rel in context_data.get("computable_relations", []):
        checkers.append({
            "id": "F1", "checker": "check_computation_result",
            "params": {"results": [{"label": rel["label"], "expected": rel["expected"],
                                     "tolerance": rel.get("tolerance", 0.5)}]},
        })
    return checkers


def assemble_prompt(context_text, query_text, constraints):
    if not constraints:
        return f"{context_text}\n\n{query_text}"
    lines = [f"（{i}）{c['rendered_text']}" for i, c in enumerate(constraints, 1)]
    return f"{context_text}\n\n{query_text}\n\n请在回答时严格遵守以下附加要求：\n" + "\n".join(lines)


def assemble_one_sample(query, ctx, pool, seed_suffix=""):
    n_total = random.randint(2, 4)
    n_general = random.randint(1, min(2, n_total))
    n_fin_soft = max(1, n_total - n_general - 1)
    n_fin_hard = n_total - n_general - n_fin_soft

    general_cs = sample_general(n_general, pool)
    fin_soft_cs = sample_financial_soft(n_fin_soft, pool)
    fin_hard_cs = sample_financial_hard(n_fin_hard, ctx, pool)
    visible_cs = general_cs + fin_soft_cs + fin_hard_cs
    random.shuffle(visible_cs)

    hidden_checkers = build_hidden_checkers(ctx)
    prompt = assemble_prompt(ctx["text"], query["query_text"], visible_cs)

    sid = f"S-{query['query_id']}{seed_suffix}"
    return {
        "sample_id": sid,
        "query_id": query["query_id"],
        "case_id": query["case_id"],
        "L1": query["L1"],
        "L2": query["L2"],
        "variant_type": query.get("variant_type", ""),
        "context_source": ctx.get("source", "unknown"),
        "context_text": ctx["text"],
        "query_text": query["query_text"],
        "constraints": visible_cs,
        "hidden_checkers": hidden_checkers,
        "n_constraints": len(visible_cs),
        "n_general": sum(1 for c in visible_cs if c["id"].startswith("G")),
        "n_financial_soft": sum(1 for c in visible_cs if c["id"].startswith("F") and c["type"] == "soft"),
        "n_financial_hard": sum(1 for c in visible_cs if c["id"].startswith("F") and c["type"] == "hard"),
        "n_hidden_checkers": len(hidden_checkers),
        "prompt": prompt,
    }


def prompt_hash(prompt):
    """对 prompt 取 hash 做去重"""
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


# ============================================================
# 4. 主流程
# ============================================================
def main():
    pool = load_json(os.path.join(CONFIG_DIR, "constraint_pool.json"))
    ctx_map = load_all_contexts()
    print(f"Loaded {len(ctx_map)} contexts")

    # 统计来源
    src_counter = Counter(c.get("source", "?") for c in ctx_map.values())
    print(f"  Sources: {dict(src_counter)}")

    # --- 加载已有 query ---
    existing_queries = load_jsonl(os.path.join(DATA_DIR, "query_pool.jsonl"))
    print(f"Loaded {len(existing_queries)} existing queries (SYN)")

    # --- B组 context 已通过 query_pool.jsonl 有对应 query ---
    # --- 为 external contexts 生成 query（它们没有现成的 query_pool 条目）---
    ext_queries = []
    for cid, ctx in ctx_map.items():
        if cid.startswith("EXT-"):
            l2 = ctx.get("L2", "")
            l1 = l2.split(".")[0] if "." in l2 else l2
            templates = QUERY_TEMPLATES_BY_L2.get(l2, QUERY_TEMPLATES_BY_L2.get(l1, []))
            for i, tmpl in enumerate(templates):
                ext_queries.append({
                    "query_id": f"{cid}-Q{i+1}",
                    "case_id": cid,
                    "L1": l1,
                    "L2": l2,
                    "query_text": tmpl,
                    "variant_type": "external",
                })
    all_queries = existing_queries + ext_queries
    print(f"Using {len(existing_queries)} synthetic + {len(ext_queries)} external = {len(all_queries)} queries")

    # --- 加载已有 540 条样本 ---
    existing_samples = []
    for t in ["T1", "T2", "T3"]:
        existing_samples.extend(load_jsonl(os.path.join(DATA_DIR, f"samples_{t}_param.jsonl")))
        existing_samples.extend(load_jsonl(os.path.join(DATA_DIR, f"samples_{t}_parameterized.jsonl")))
    print(f"Loaded {len(existing_samples)} existing samples")

    existing_hashes = set(prompt_hash(s["prompt"]) for s in existing_samples)
    all_samples = list(existing_samples)

    # --- 多 seed 约束重采样 ---
    TARGET = 2200
    seeds = [100, 200, 300, 400, 500, 600, 700]
    seen_hashes = set(existing_hashes)

    for seed in seeds:
        if len(all_samples) >= TARGET:
            break
        random.seed(seed)
        batch = []
        for q in all_queries:
            ctx = ctx_map.get(q["case_id"])
            if not ctx:
                continue
            s = assemble_one_sample(q, ctx, pool, seed_suffix=f"-R{seed}")
            h = prompt_hash(s["prompt"])
            if h not in seen_hashes:
                seen_hashes.add(h)
                batch.append(s)
        all_samples.extend(batch)
        print(f"  Seed {seed}: +{len(batch)} samples (total {len(all_samples)})")

    # --- 截断到目标数量（如果超了） ---
    if len(all_samples) > TARGET + 200:
        random.seed(42)
        random.shuffle(all_samples)
        all_samples = all_samples[:TARGET]

    # --- 输出 ---
    output_path = os.path.join(DATA_DIR, "samples_all_2000.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # --- 统计 ---
    print(f"\n=== Final: {len(all_samples)} samples → {output_path} ===")

    l1_counter = Counter(s["L1"] for s in all_samples)
    l2_counter = Counter(s["L2"] for s in all_samples)
    src_counter = Counter(s.get("context_source", "?") for s in all_samples)

    print(f"\nL1 分布:")
    for k, v in sorted(l1_counter.items()):
        print(f"  {k}: {v} ({v/len(all_samples)*100:.1f}%)")

    print(f"\nL2 分布:")
    for k, v in sorted(l2_counter.items()):
        print(f"  {k}: {v}")

    print(f"\nContext source:")
    for k, v in sorted(src_counter.items()):
        print(f"  {k}: {v}")

    cid_counter = Counter()
    for s in all_samples:
        for c in s.get("constraints", []):
            cid_counter[c["id"]] += 1
    print(f"\n约束使用频次:")
    for k, v in sorted(cid_counter.items()):
        print(f"  {k}: {v}")

    avg_c = sum(s.get("n_constraints", 0) for s in all_samples) / len(all_samples)
    print(f"\n平均可见约束数: {avg_c:.2f}")


if __name__ == "__main__":
    main()
