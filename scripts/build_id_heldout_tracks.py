import json
import math
import random
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIEWER_DIR = BASE_DIR / "viewer"
QUERY_POOL_PATH = DATA_DIR / "query_pool" / "query_pool_v2_final.json"

TRAIN_QUERY_PATH = DATA_DIR / "splits" / "id_heldout_train_queries.json"
TEST_QUERY_PATH = DATA_DIR / "splits" / "id_heldout_test_queries.json"
V_TRACK_PATH = DATA_DIR / "tracks" / "id_heldout_v_track.json"
NV_TRACK_PATH = DATA_DIR / "tracks" / "id_heldout_nv_track.json"
MIXED_TRACK_PATH = DATA_DIR / "tracks" / "id_heldout_mixed_track.json"
ALL_TRACKS_PATH = DATA_DIR / "tracks" / "id_heldout_all_tracks.json"
VIEWER_PATH = VIEWER_DIR / "id_heldout_tracks_viewer.html"

RNG = random.Random(20260328)
TEST_RATIO = 0.2


V_CONSTRAINTS = {
    "GV-1": "回答不超过{n}个字",
    "GV-2": "至少包含{n}个句子",
    "GV-3": "回答分为{n}个段落",
    "GV-4a": "使用 Markdown 格式输出",
    "GV-4b": "包含至少{n}级标题层级",
    "GV-5": "使用编号列表组织回答",
    "GV-6": "使用 Markdown 表格呈现关键信息",
    "GV-7": "以 JSON 格式输出",
    "GV-8": "必须包含关键词：{kw1}、{kw2}",
    "GV-9": "不得出现“{word}”",
    "GV-10": "开头第一个词必须是“{word}”",
    "GV-11": "使用 Checkbox 格式 `[ ]` / `[x]`",
    "GV-12": "输出必须包含至少一个代码块或公式块",
    "GV-13": "第一行必须为“{first_line}”，最后一行为“{last_line}”",
    "GV-14": "每个 bullet 必须以“{prefix}”开头",
    "FV-1": "末尾必须包含风险提示声明：{risk_line}",
    "FV-2": "必须声明“{disclaimer}”",
    "FV-3": "若提到“{trigger}”，必须同时补充“{followup}”",
    "FV-4": "按{order_field}从高到低排序输出",
    "FV-5": "若出现货币金额，统一使用 {currency_rule} 表示",
    "FV-6": "必须给出风险等级（R1-R5）",
    "FV-7": "必须包含一个投资评级词（买入/增持/中性/减持/卖出）",
}

NV_CONSTRAINTS = {
    "GN-1": "先给出结论，再给出分析过程",
    "GN-2": "回答末尾必须包含一段总结",
    "GN-3": "使用正式书面语，不得口语化",
    "GN-4": "使用客观中立的语气，不带主观倾向",
    "GN-5": "段落之间必须逻辑连贯，有明确过渡",
    "GN-6": "避免重复内容，每段应提供新信息",
    "GN-7": "使用类比或举例来辅助解释",
    "FN-1": "从风险管理的角度分析",
    "FN-2": "站在监管机构的立场回答",
    "FN-3": "从零售投资者的视角分析",
    "FN-4": "从 ESG 角度评价",
    "FN-5": "从宏观经济的角度分析",
    "FN-6": "注明所引用信息的来源",
    "FN-7": "专业术语缩写需给出全称",
    "FN-8": "使用通俗语言，尽量避免专业术语",
    "FN-9": "仅基于提供的材料作答",
    "FN-10": "必须引用具体财务指标数据",
    "FN-11": "必须包含定量分析",
    "FN-12": "非金融领域术语不得使用英文",
    "FN-13": "至少包含{n}个专业金融术语",
    "FN-14": "假设当前处于{market_env}下进行分析",
    "FN-15": "以{goal}为首要考量",
    "FN-16": "以{doc_style}的风格撰写",
    "FN-17": "在假设{condition}的前提下进行分析",
}

CONFLICTS = {frozenset({"FN-7", "FN-8"})}


KEYWORDS_BY_FAMILY = {
    "suggestion": ["风险", "收益", "配置", "流动性", "期限", "波动", "组合"],
    "diagnosis": ["风险点", "异常", "原因", "建议", "待核实", "证据", "影响"],
    "api": ["步骤", "代码", "数据", "接口", "字段", "结果", "流程"],
    "sales": ["产品特点", "适合人群", "风险提示", "常见误区", "注意事项", "收益来源"],
}

FORBIDDEN_BY_FAMILY = {
    "suggestion": ["稳赚不赔", "闭眼买", "绝对安全"],
    "diagnosis": ["肯定没问题", "完全无风险", "无需核实"],
    "api": ["随便写", "一键搞定", "无需检查"],
    "sales": ["稳赚", "零风险", "保证赚钱"],
}

FIRST_WORD_BY_FAMILY = {
    "suggestion": ["结论", "建议"],
    "diagnosis": ["结论", "问题"],
    "api": ["步骤", "方案"],
    "sales": ["说明", "建议"],
}

PREFIX_BY_FAMILY = {
    "suggestion": ["要点：", "建议："],
    "diagnosis": ["风险点：", "建议："],
    "api": ["步骤：", "说明："],
    "sales": ["要点：", "提示："],
}

MARKET_ENVS = ["熊市", "牛市", "加息周期", "流动性紧缩", "震荡市", "经济修复阶段"]
PRIMARY_GOALS = ["资本保全", "收益最大化", "风险最小化", "合规优先", "流动性优先"]
DOC_STYLES = ["券商研报", "财经新闻", "投资备忘录", "监管公告", "客户说明书"]
CONDITIONS = ["利率上升50bp", "人民币贬值5%", "GDP增速降至3%", "市场波动率显著上升", "监管要求收紧"]


def load_queries():
    return json.loads(QUERY_POOL_PATH.read_text(encoding="utf-8"))


def family_of(item):
    tmpl = item.get("template_id")
    origin = item.get("origin_task")
    if tmpl in {"T1", "T2"} or origin == "finsuggestion":
        return "suggestion"
    if tmpl in {"T4", "T5"} or origin == "findiag":
        return "diagnosis"
    if tmpl in {"T7", "T9"} or origin == "apiutil":
        return "api"
    if tmpl in {"T10", "T11"} or origin == "finsales":
        return "sales"
    return "suggestion"


def group_key(item):
    return (
        item["source_type"],
        item["role_mode"],
        item.get("template_id") or "NO_TEMPLATE",
        item.get("origin_task") or "NO_ORIGIN",
    )


def stratified_split(records):
    groups = defaultdict(list)
    for item in records:
        groups[group_key(item)].append(item)

    group_specs = []
    for key, items in sorted(groups.items()):
        shuffled = list(items)
        RNG.shuffle(shuffled)
        exact = len(shuffled) * TEST_RATIO
        base = math.floor(exact)
        frac = exact - base
        group_specs.append({"key": key, "items": shuffled, "base": base, "frac": frac})

    target_test = int(round(len(records) * TEST_RATIO))
    assigned = sum(spec["base"] for spec in group_specs)
    remainder = target_test - assigned
    order = sorted(
        range(len(group_specs)),
        key=lambda i: (group_specs[i]["frac"], len(group_specs[i]["items"])),
        reverse=True,
    )
    for i in order[:remainder]:
        group_specs[i]["base"] += 1

    train, test = [], []
    for spec in group_specs:
        cutoff = spec["base"]
        test.extend(spec["items"][:cutoff])
        train.extend(spec["items"][cutoff:])

    train = sorted(train, key=lambda x: x["id"])
    test = sorted(test, key=lambda x: x["id"])
    return train, test


def sample_count(dist_name, rng):
    p = rng.random()
    if dist_name == "v":
        return 1 if p < 0.50 else 2 if p < 0.85 else 3
    if dist_name == "nv":
        return 1 if p < 0.60 else 2 if p < 0.90 else 3
    return 2 if p < 0.70 else 3


def v_candidates(item):
    tmpl = item.get("template_id")
    fam = family_of(item)
    base = {
        "suggestion": ["GV-1", "GV-2", "GV-3", "GV-4a", "GV-4b", "GV-5", "GV-6", "GV-8", "GV-9", "GV-10", "GV-13", "GV-14", "FV-1", "FV-2", "FV-4", "FV-5", "FV-6", "FV-7"],
        "diagnosis": ["GV-1", "GV-2", "GV-3", "GV-4a", "GV-4b", "GV-5", "GV-6", "GV-8", "GV-9", "GV-10", "GV-13", "GV-14", "FV-4", "FV-5", "FV-6"],
        "api": ["GV-2", "GV-3", "GV-4a", "GV-4b", "GV-5", "GV-7", "GV-8", "GV-9", "GV-10", "GV-11", "GV-12", "GV-13", "GV-14", "FV-3", "FV-4", "FV-5"],
        "sales": ["GV-1", "GV-2", "GV-3", "GV-4a", "GV-4b", "GV-5", "GV-6", "GV-8", "GV-9", "GV-10", "GV-13", "GV-14", "FV-1", "FV-2", "FV-4", "FV-5", "FV-6"],
    }[fam]
    if tmpl == "T9":
        return ["GV-3", "GV-4a", "GV-5", "GV-10", "GV-11", "GV-13", "GV-14", "FV-4", "FV-5"]
    if tmpl == "T7":
        return ["GV-4a", "GV-5", "GV-7", "GV-10", "GV-12", "GV-13", "GV-14", "FV-3", "FV-4", "FV-5"]
    return base


def nv_candidates(item):
    fam = family_of(item)
    base = {
        "suggestion": ["GN-1", "GN-2", "GN-3", "GN-4", "GN-5", "GN-6", "GN-7", "FN-1", "FN-3", "FN-5", "FN-6", "FN-7", "FN-8", "FN-9", "FN-10", "FN-11", "FN-12", "FN-13", "FN-14", "FN-15", "FN-16", "FN-17"],
        "diagnosis": ["GN-1", "GN-2", "GN-3", "GN-4", "GN-5", "GN-6", "FN-1", "FN-2", "FN-5", "FN-6", "FN-7", "FN-8", "FN-9", "FN-10", "FN-11", "FN-12", "FN-13", "FN-14", "FN-15", "FN-16", "FN-17"],
        "api": ["GN-1", "GN-2", "GN-3", "GN-5", "GN-6", "FN-6", "FN-8", "FN-9", "FN-12", "FN-13", "FN-14", "FN-15", "FN-16", "FN-17"],
        "sales": ["GN-1", "GN-2", "GN-3", "GN-4", "GN-5", "GN-6", "GN-7", "FN-3", "FN-6", "FN-7", "FN-8", "FN-9", "FN-12", "FN-13", "FN-14", "FN-15", "FN-16"],
    }[fam]
    return base


def choice(seed_text, seq):
    rng = random.Random(seed_text)
    return seq[rng.randrange(len(seq))]


def instantiate_v(cid, item):
    fam = family_of(item)
    title_seed = f"{item['id']}-{cid}"
    kw = KEYWORDS_BY_FAMILY[fam]
    forbidden = FORBIDDEN_BY_FAMILY[fam]
    first_words = FIRST_WORD_BY_FAMILY[fam]
    prefixes = PREFIX_BY_FAMILY[fam]
    if cid == "GV-1":
        n = choice(title_seed, [120, 150, 180, 220])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(n=n)}
    if cid == "GV-2":
        n = choice(title_seed, [3, 4, 5])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(n=n)}
    if cid == "GV-3":
        n = choice(title_seed, [2, 3, 4])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(n=n)}
    if cid == "GV-4b":
        n = choice(title_seed, [2, 3])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(n=n)}
    if cid == "GV-8":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(kw1=kw[0], kw2=kw[1])}
    if cid == "GV-9":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(word=choice(title_seed, forbidden))}
    if cid == "GV-10":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(word=choice(title_seed, first_words))}
    if cid == "GV-13":
        first_line = choice(title_seed, ["## 核心结论", "## 结论", "## 执行摘要"])
        last_line = choice(title_seed + "-last", ["仅供参考", "以上为本次输出", "请结合实际情况判断"])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(first_line=first_line, last_line=last_line)}
    if cid == "GV-14":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(prefix=choice(title_seed, prefixes))}
    if cid == "FV-1":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(risk_line="风险提示：以上内容仅供参考，投资有风险。")}
    if cid == "FV-2":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(disclaimer="以上内容不构成投资建议")}
    if cid == "FV-3":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(trigger="高收益", followup="高收益通常伴随高风险")}
    if cid == "FV-4":
        order_field = choice(title_seed, ["风险高低", "优先级", "重要性"])
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(order_field=order_field)}
    if cid == "FV-5":
        return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid].format(currency_rule="CNY / USD 代码")}
    return {"id": cid, "type": "V", "text": V_CONSTRAINTS[cid]}


def instantiate_nv(cid, item):
    title_seed = f"{item['id']}-{cid}"
    if cid == "FN-13":
        n = choice(title_seed, [3, 4, 5])
        return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid].format(n=n)}
    if cid == "FN-14":
        return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid].format(market_env=choice(title_seed, MARKET_ENVS))}
    if cid == "FN-15":
        return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid].format(goal=choice(title_seed, PRIMARY_GOALS))}
    if cid == "FN-16":
        return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid].format(doc_style=choice(title_seed, DOC_STYLES))}
    if cid == "FN-17":
        return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid].format(condition=choice(title_seed, CONDITIONS))}
    return {"id": cid, "type": "NV", "text": NV_CONSTRAINTS[cid]}


def sample_unique(ids, count, item_seed):
    rng = random.Random(item_seed)
    pool = list(ids)
    rng.shuffle(pool)
    selected = []
    for cid in pool:
        if any(frozenset({cid, existing}) in CONFLICTS for existing in selected):
            continue
        selected.append(cid)
        if len(selected) == count:
            break
    return selected


def build_constraints(item, track):
    seed = f"{item['id']}-{track}"
    if track == "V-track":
        count = sample_count("v", random.Random(seed))
        ids = sample_unique(v_candidates(item), count, seed)
        return [instantiate_v(cid, item) for cid in ids]
    if track == "NV-track":
        count = sample_count("nv", random.Random(seed))
        ids = sample_unique(nv_candidates(item), count, seed)
        return [instantiate_nv(cid, item) for cid in ids]
    rng = random.Random(seed)
    if sample_count("mixed", rng) == 2:
        v_count, nv_count = 1, 1
    else:
        v_count, nv_count = 2, 1
    v_ids = sample_unique(v_candidates(item), v_count, seed + "-v")
    nv_ids = sample_unique(nv_candidates(item), nv_count, seed + "-nv")
    return [instantiate_v(cid, item) for cid in v_ids] + [instantiate_nv(cid, item) for cid in nv_ids]


def final_prompt(item, constraints):
    lines = [f"{idx}. {c['text']}" for idx, c in enumerate(constraints, start=1)]
    return item["input"].rstrip() + "\n\n附加要求：\n" + "\n".join(lines)


def build_track_samples(records, split_name, track_name):
    samples = []
    for idx, item in enumerate(records, start=1):
        constraints = build_constraints(item, track_name)
        samples.append(
            {
                "sample_id": f"{split_name.lower()}-{track_name.lower().replace('-', '_')}-{idx:04d}",
                "split": split_name,
                "track": track_name,
                "query_id": item["id"],
                "source_type": item["source_type"],
                "origin_task": item.get("origin_task"),
                "template_id": item.get("template_id"),
                "template_name": item["template_name"],
                "role_mode": item["role_mode"],
                "role": item.get("role"),
                "title": item["title"],
                "material_type": item["material_type"],
                "query_input": item["input"],
                "base_query_input": item.get("base_input", item["input"]),
                "constraints": constraints,
                "constraint_ids": [c["id"] for c in constraints],
                "prompt": final_prompt(item, constraints),
            }
        )
    return samples


def build_viewer(all_samples):
    data_json = json.dumps(all_samples, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ID Held-out Tracks Viewer</title>
  <style>
    :root {{
      --bg:#0b1020; --panel:#121a2b; --panel2:#18233a; --line:#283554;
      --text:#ebf1ff; --muted:#9fb0d3; --chip:#243452;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .wrap {{ max-width:1400px; margin:0 auto; padding:24px; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    .sub {{ color:var(--muted); line-height:1.7; margin-bottom:20px; }}
    .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:18px; }}
    .stat {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }}
    .k {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
    .v {{ font-size:24px; font-weight:700; }}
    .toolbar {{ display:grid; grid-template-columns:1.2fr 1fr 1fr 1fr 1fr 1fr 1fr; gap:12px; margin-bottom:18px; }}
    input, select {{ width:100%; border:1px solid var(--line); border-radius:12px; padding:12px 14px; background:var(--panel); color:var(--text); font-size:14px; }}
    .hint {{ color:var(--muted); margin-bottom:18px; font-size:13px; }}
    .list {{ display:grid; gap:14px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; overflow:hidden; }}
    .card-head {{ padding:16px 18px 10px; border-bottom:1px solid rgba(255,255,255,0.05); }}
    .title {{ font-size:18px; font-weight:700; margin-bottom:10px; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .chip {{ background:var(--chip); border-radius:999px; padding:5px 10px; font-size:12px; }}
    .body {{ padding:16px 18px 18px; display:grid; gap:14px; }}
    .section {{ font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; }}
    pre {{ margin:0; white-space:pre-wrap; word-break:break-word; background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:14px; line-height:1.6; font-size:13px; }}
    .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    .empty {{ padding:32px 18px; color:var(--muted); text-align:center; background:var(--panel); border:1px solid var(--line); border-radius:16px; }}
    .small {{ color:#95e0c3; font-size:13px; line-height:1.7; }}
    @media (max-width: 1180px) {{ .toolbar,.grid2 {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>ID Held-out Tracks Viewer</h1>
    <div class="sub">当前展示的是 query 级别 80/20 划分后的 track 数据。`train-query` 与 `test-query` 已先切分，再分别构造 `V-track`、`NV-track` 与 `Mixed-track`，用于后续训练与主测试集评测。</div>
    <div class="stats" id="stats"></div>
    <div class="toolbar">
      <input id="search" type="text" placeholder="搜索标题、query、constraint 文本" />
      <select id="split"></select>
      <select id="track"></select>
      <select id="sourceType"></select>
      <select id="originTask"></select>
      <select id="templateId"></select>
      <select id="roleMode"></select>
    </div>
    <div class="hint" id="hint"></div>
    <div class="list" id="list"></div>
  </div>
  <script>
    const DATA = {data_json};
    const $ = (id) => document.getElementById(id);
    const ids = ["search","split","track","sourceType","originTask","templateId","roleMode"];
    function uniq(arr) {{
      return [...new Set(arr)].sort((a,b) => String(a).localeCompare(String(b), "zh-CN"));
    }}
    function esc(str) {{
      return String(str).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
    }}
    function fill(sel, vals, label) {{
      sel.innerHTML = `<option value="">全部${{label}}</option>` + vals.map(v => `<option value="${{esc(v)}}">${{esc(v)}}</option>`).join("");
    }}
    function renderStats() {{
      const stats = {{
        total: DATA.length,
        train: DATA.filter(x => x.split === "train").length,
        test: DATA.filter(x => x.split === "test").length,
        v: DATA.filter(x => x.track === "V-track").length,
        nv: DATA.filter(x => x.track === "NV-track").length,
        mixed: DATA.filter(x => x.track === "Mixed-track").length,
      }};
      $("stats").innerHTML = `
        <div class="stat"><div class="k">总样本数</div><div class="v">${{stats.total}}</div></div>
        <div class="stat"><div class="k">Train 样本</div><div class="v">${{stats.train}}</div></div>
        <div class="stat"><div class="k">Test 样本</div><div class="v">${{stats.test}}</div></div>
        <div class="stat"><div class="k">V-track</div><div class="v">${{stats.v}}</div></div>
        <div class="stat"><div class="k">NV-track</div><div class="v">${{stats.nv}}</div></div>
        <div class="stat"><div class="k">Mixed-track</div><div class="v">${{stats.mixed}}</div></div>
      `;
    }}
    function render() {{
      const q = $("search").value.trim().toLowerCase();
      const split = $("split").value;
      const track = $("track").value;
      const sourceType = $("sourceType").value;
      const originTask = $("originTask").value;
      const templateId = $("templateId").value;
      const roleMode = $("roleMode").value;
      const rows = DATA.filter(item => {{
        const hay = [
          item.sample_id, item.title, item.query_input, item.prompt,
          item.track, item.split, item.source_type, item.origin_task || "",
          item.template_id || "", item.role_mode, ...(item.constraint_ids || [])
        ].join("\\n").toLowerCase();
        return (!q || hay.includes(q))
          && (!split || item.split === split)
          && (!track || item.track === track)
          && (!sourceType || item.source_type === sourceType)
          && (!originTask || item.origin_task === originTask)
          && (!templateId || item.template_id === templateId)
          && (!roleMode || item.role_mode === roleMode);
      }});
      $("hint").textContent = `显示 ${{rows.length}} / ${{DATA.length}} 条`;
      if (!rows.length) {{
        $("list").innerHTML = `<div class="empty">没有匹配结果，换个关键词或清空筛选试试。</div>`;
        return;
      }}
      $("list").innerHTML = rows.map(item => `
        <div class="card">
          <div class="card-head">
            <div class="title">${{esc(item.title)}}</div>
            <div class="meta">
              <span class="chip">${{esc(item.sample_id)}}</span>
              <span class="chip">${{esc(item.split)}}</span>
              <span class="chip">${{esc(item.track)}}</span>
              <span class="chip">${{esc(item.source_type)}}</span>
              ${{item.origin_task ? `<span class="chip">${{esc(item.origin_task)}}</span>` : ""}}
              ${{item.template_id ? `<span class="chip">${{esc(item.template_id)}}</span>` : ""}}
              <span class="chip">${{esc(item.role_mode)}}</span>
              <span class="chip">${{esc(item.role || "无角色")}}</span>
            </div>
          </div>
          <div class="body">
            <div class="grid2">
              <div>
                <div class="section">Constraint IDs</div>
                <div class="small">${{esc((item.constraint_ids || []).join(", "))}}</div>
              </div>
              <div>
                <div class="section">Constraint Text</div>
                <div class="small">${{esc((item.constraints || []).map(x => x.text).join(" | "))}}</div>
              </div>
            </div>
            <div>
              <div class="section">Query Input</div>
              <pre>${{esc(item.query_input)}}</pre>
            </div>
            <div>
              <div class="section">Final Prompt</div>
              <pre>${{esc(item.prompt)}}</pre>
            </div>
          </div>
        </div>
      `).join("");
    }}
    fill($("split"), uniq(DATA.map(x => x.split)), "split");
    fill($("track"), uniq(DATA.map(x => x.track)), "track");
    fill($("sourceType"), uniq(DATA.map(x => x.source_type)), "来源类型");
    fill($("originTask"), uniq(DATA.map(x => x.origin_task).filter(Boolean)), "FinEval来源任务");
    fill($("templateId"), uniq(DATA.map(x => x.template_id).filter(Boolean)), "模板");
    fill($("roleMode"), uniq(DATA.map(x => x.role_mode)), "角色模式");
    renderStats();
    render();
    ids.forEach(id => {{
      $(id).addEventListener("input", render);
      $(id).addEventListener("change", render);
    }});
  </script>
</body>
</html>
"""
    return html


def main():
    TRAIN_QUERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    V_TRACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    VIEWER_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = load_queries()
    train, test = stratified_split(records)

    train_v = build_track_samples(train, "train", "V-track")
    test_v = build_track_samples(test, "test", "V-track")
    train_nv = build_track_samples(train, "train", "NV-track")
    test_nv = build_track_samples(test, "test", "NV-track")
    train_m = build_track_samples(train, "train", "Mixed-track")
    test_m = build_track_samples(test, "test", "Mixed-track")

    v_all = train_v + test_v
    nv_all = train_nv + test_nv
    mixed_all = train_m + test_m
    all_samples = v_all + nv_all + mixed_all

    TRAIN_QUERY_PATH.write_text(json.dumps(train, ensure_ascii=False, indent=2), encoding="utf-8")
    TEST_QUERY_PATH.write_text(json.dumps(test, ensure_ascii=False, indent=2), encoding="utf-8")
    V_TRACK_PATH.write_text(json.dumps(v_all, ensure_ascii=False, indent=2), encoding="utf-8")
    NV_TRACK_PATH.write_text(json.dumps(nv_all, ensure_ascii=False, indent=2), encoding="utf-8")
    MIXED_TRACK_PATH.write_text(json.dumps(mixed_all, ensure_ascii=False, indent=2), encoding="utf-8")
    ALL_TRACKS_PATH.write_text(json.dumps(all_samples, ensure_ascii=False, indent=2), encoding="utf-8")
    VIEWER_PATH.write_text(build_viewer(all_samples), encoding="utf-8")

    print("train queries", len(train))
    print("test queries", len(test))
    print("v track", len(v_all))
    print("nv track", len(nv_all))
    print("mixed track", len(mixed_all))
    print("all samples", len(all_samples))


if __name__ == "__main__":
    main()
