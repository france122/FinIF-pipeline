#!/usr/bin/env python3
"""
FinIF Dashboard — Benchmark + Training Data 可视化
用法: python3 dashboard.py
浏览器打开 http://localhost:18926
"""
import json, os, glob
from http.server import HTTPServer, SimpleHTTPRequestHandler
from collections import Counter

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = os.path.dirname(PIPELINE_DIR)


def load_benchmark():
    with open(os.path.join(CURRENT_DIR, "benchmark", "benchmark_all.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    with open(os.path.join(CURRENT_DIR, "benchmark", "eval_config_all.json"), encoding="utf-8") as f:
        constraints = json.load(f)["constraints"]
    case_constraints = {}
    for key, cfg in constraints.items():
        cid = key.split("#")[0]
        case_constraints.setdefault(cid, []).append({"key": key, **cfg})
    items = []
    for c in cases:
        cid = c["case_id"]
        l2 = cid.split("-")[0]
        l1 = l2.split(".")[0]
        cs = case_constraints.get(cid, [])
        items.append({
            "case_id": cid, "L1": l1, "L2": l2,
            "context": c.get("context", ""),
            "prompt": c.get("prompt", ""),
            "n_constraints": len(cs),
            "n_hard": sum(1 for x in cs if x.get("type") == "hard"),
            "n_soft": sum(1 for x in cs if x.get("type") == "soft"),
            "constraints": cs,
        })
    l1c = Counter(i["L1"] for i in items)
    l2c = Counter(i["L2"] for i in items)
    checkers = Counter()
    tag_counter = Counter()
    tag_cat_counter = Counter()
    comp_total = 0
    corr_total = 0
    for i in items:
        case_tags = set()
        for c in i["constraints"]:
            if c.get("checker"):
                checkers[c["checker"]] += 1
            t = c.get("tag", "")
            if t:
                tag_counter[t] += 1
                tag_cat_counter[t[0]] += 1
                case_tags.add(t)
            if c.get("is_if"):
                comp_total += 1
            else:
                corr_total += 1
        i["n_comp"] = sum(1 for c in i["constraints"] if c.get("is_if"))
        i["n_corr"] = sum(1 for c in i["constraints"] if not c.get("is_if", True))
        i["tag_cats"] = sorted(set(t[0] for t in case_tags if t))
    total_c = sum(i["n_constraints"] for i in items)
    stats = {
        "total": len(items),
        "total_constraints": total_c,
        "avg_constraints": round(total_c / max(len(items), 1), 2),
        "comp_total": comp_total,
        "corr_total": corr_total,
        "comp_ratio": round(comp_total / max(total_c, 1) * 100, 1),
        "by_l1": dict(sorted(l1c.items())),
        "by_l2": dict(sorted(l2c.items())),
        "by_checker": dict(sorted(checkers.items())),
        "by_tag": dict(sorted(tag_counter.items())),
        "by_tag_cat": dict(sorted(tag_cat_counter.items())),
    }
    TAG_CAT_NAMES = {"F": "Format", "N": "Number", "L": "Linguistic", "S": "Style", "C": "Content"}
    stats["tag_cat_names"] = TAG_CAT_NAMES
    return {"stats": stats, "cases": items}


def load_scores():
    """Load all scores_*.json from output directory, extract dual-axis metrics."""
    output_dir = os.path.join(CURRENT_DIR, "benchmark", "scores")
    models = []
    for path in sorted(glob.glob(os.path.join(output_dir, "scores_*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        model_name = d.get("model", os.path.basename(path).replace("scores_", "").replace(".json", ""))
        ts = d.get("tier_scores", {})
        scores = d.get("scores", {})

        # Overall / tier scores (legacy flat format)
        overall = ts.get("overall", 0)
        t1 = ts.get("T1", 0)
        t2 = ts.get("T2", 0)
        t3 = ts.get("T3", 0)

        # Dual-axis: compliance & correctness (new format, may not exist yet)
        comp = ts.get("compliance", {})
        corr = ts.get("correctness", {})
        compliance_overall = comp.get("overall", None)
        correctness_overall = corr.get("overall", None)
        compliance_tiers = {k: comp.get(k, None) for k in ["T1", "T2", "T3"]}
        correctness_tiers = {k: corr.get(k, None) for k in ["T1", "T2", "T3"]}

        # Per-case dual-axis (aggregate if present)
        case_compliance = []
        case_correctness = []
        for cid, cs in scores.items():
            if isinstance(cs, dict) and "compliance" in cs:
                c_score = cs["compliance"].get("score", None)
                if c_score is not None:
                    case_compliance.append(c_score)
            if isinstance(cs, dict) and "correctness" in cs:
                c_score = cs["correctness"].get("score", None)
                if c_score is not None:
                    case_correctness.append(c_score)

        # Fallback: if tier_scores has no compliance/correctness, use per-case aggregates
        if compliance_overall is None and case_compliance:
            compliance_overall = sum(case_compliance) / len(case_compliance)
        if correctness_overall is None and case_correctness:
            correctness_overall = sum(case_correctness) / len(case_correctness)

        models.append({
            "model": model_name,
            "overall": round(overall * 100, 1),
            "T1": round(t1 * 100, 1),
            "T2": round(t2 * 100, 1),
            "T3": round(t3 * 100, 1),
            "compliance": round(compliance_overall * 100, 1) if compliance_overall is not None else None,
            "correctness": round(correctness_overall * 100, 1) if correctness_overall is not None else None,
            "compliance_tiers": {k: round(v * 100, 1) if v is not None else None for k, v in compliance_tiers.items()},
            "correctness_tiers": {k: round(v * 100, 1) if v is not None else None for k, v in correctness_tiers.items()},
            "n_cases": len(scores),
        })
    return {"models": models}


def load_training():
    path = os.path.join(PIPELINE_DIR, "data", "sft_train_2000.jsonl")
    raw_samples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw_samples.append(json.loads(line))
    # 列表只保留摘要，详情通过 API 按需加载
    items = []
    full_map = {}  # sample_id → full data，供 API 用
    for s in raw_samples:
        m = s["metadata"]
        sid = m["sample_id"]
        prompt_full = s["messages"][1]["content"] if len(s["messages"]) > 1 else ""
        items.append({
            "sample_id": sid,
            "case_id": m["case_id"],
            "L1": m["L1"], "L2": m["L2"],
            "context_source": m.get("context_source", "") or "legacy",
            "n_constraints": m["n_constraints"],
            "n_hidden": m.get("n_hidden_checkers", 0),
            "preview": prompt_full[:100],
            "cids": [c["id"] for c in m.get("constraints", [])],
        })
        full_map[sid] = {
            "sample_id": sid,
            "case_id": m["case_id"],
            "query_id": m["query_id"],
            "L1": m["L1"], "L2": m["L2"],
            "variant_type": m.get("variant_type", ""),
            "context_source": m.get("context_source", "") or "legacy",
            "n_constraints": m["n_constraints"],
            "constraints": m.get("constraints", []),
            "hidden_checkers": m.get("hidden_checkers", []),
            "prompt": prompt_full,
        }
    l1c = Counter(i["L1"] for i in items)
    l2c = Counter(i["L2"] for i in items)
    src = Counter(i["context_source"] for i in items)
    cid_counter = Counter()
    for sid, full in full_map.items():
        for c in full["constraints"]:
            cid_counter[c["id"]] += 1
    nc = [i["n_constraints"] for i in items]
    hard_total = sum(1 for full in full_map.values() for c in full["constraints"] if c.get("type") == "hard")
    soft_total = sum(1 for full in full_map.values() for c in full["constraints"] if c.get("type") == "soft")
    stats = {
        "total": len(items),
        "avg_constraints": round(sum(nc) / max(len(nc), 1), 2),
        "hard_total": hard_total,
        "soft_total": soft_total,
        "hidden_total": sum(i["n_hidden"] for i in items),
        "by_l1": dict(sorted(l1c.items())),
        "by_l2": dict(sorted(l2c.items())),
        "by_source": dict(sorted(src.items())),
        "by_constraint": dict(sorted(cid_counter.items())),
    }
    return {"stats": stats, "samples": items}, full_map


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FinIF Dashboard</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;--purple:#a371f7;--text:#c9d1d9;--muted:#8b949e;--hover:#1c2128}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px}
a{color:var(--accent);text-decoration:none}

.topbar{background:#010409;border-bottom:1px solid var(--border);padding:12px 24px;display:flex;align-items:center;gap:20px;position:sticky;top:0;z-index:100}
.topbar h1{font-size:18px;color:#fff;font-weight:600}
.topbar .logo{font-size:20px;color:var(--accent)}
.mtab{padding:6px 16px;border-radius:20px;border:1px solid transparent;background:transparent;color:var(--muted);cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}
.mtab:hover{color:var(--text);background:var(--hover)}
.mtab.active{background:var(--accent);color:#fff;border-color:var(--accent)}

.wrap{max-width:1400px;margin:0 auto;padding:20px 24px}
.panel{display:none}.panel.active{display:block}

.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.sc{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;text-align:center}
.sc .n{font-size:28px;font-weight:700;color:var(--accent)}
.sc .l{font-size:11px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.5px}

.sec{margin-bottom:28px}
.sec h2{font-size:14px;font-weight:600;margin-bottom:10px;color:var(--text);border-left:3px solid var(--accent);padding-left:10px}

.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
@media(max-width:900px){.chart-row{grid-template-columns:1fr}}
.chart-box{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px}
.chart-box h3{font-size:12px;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}

.bars{display:flex;gap:4px;align-items:end;height:120px;padding:0 2px}
.bi{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px}
.b{background:linear-gradient(180deg,var(--accent),#1f6feb);border-radius:3px 3px 0 0;min-height:2px;width:100%;transition:height .3s}
.b:hover{opacity:.8}
.bl{font-size:9px;color:var(--muted);text-align:center;line-height:1.1;height:28px;display:flex;align-items:center;word-break:break-all}
.bv{font-size:10px;color:var(--text);font-weight:600}

.pie-wrap{display:flex;align-items:center;gap:24px}
.pie{width:120px;height:120px;border-radius:50%;flex-shrink:0}
.pie-legend{display:flex;flex-direction:column;gap:4px}
.pie-item{display:flex;align-items:center;gap:6px;font-size:12px}
.pie-dot{width:10px;height:10px;border-radius:2px;flex-shrink:0}

.filters{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;align-items:center}
.fb{padding:4px 14px;border-radius:16px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px;transition:all .12s}
.fb:hover{border-color:var(--accent);color:var(--accent)}
.fb.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.sb{padding:5px 12px;border-radius:16px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:12px;width:200px;outline:none}
.sb:focus{border-color:var(--accent)}
select.sf{padding:4px 10px;border-radius:16px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:12px;outline:none;cursor:pointer}

.list{display:flex;flex-direction:column;gap:4px;max-height:480px;overflow-y:auto}
.li{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:8px 14px;cursor:pointer;transition:all .12s;display:flex;align-items:center;gap:10px;font-size:12px}
.li:hover,.li.sel{border-color:var(--accent);background:var(--hover)}
.li .id{font-weight:700;color:var(--accent);min-width:140px;font-family:'SF Mono',Monaco,Consolas,monospace;font-size:11px}
.badge{font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600}
.bT1{background:#1e3a5f;color:#58a6ff}.bT2{background:#3b2f0a;color:#d29922}.bT3{background:#3b1c1c;color:#f85149}
.bsyn{background:#1b2e1b;color:#3fb950}.bbench{background:#1e3a5f;color:#58a6ff}.bext{background:#2d1b3d;color:#a371f7}.bleg{background:#2a2a2a;color:#8b949e}
.cb{font-size:10px;padding:2px 6px;border-radius:4px;background:#1b1b3a;color:var(--purple)}
.ldesc{flex:1;font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

.paging{display:flex;gap:8px;align-items:center;margin-top:10px;justify-content:center}
.paging button{padding:4px 12px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px}
.paging button:hover{border-color:var(--accent);color:var(--accent)}
.paging button:disabled{opacity:.3;cursor:default}
.paging span{font-size:12px;color:var(--muted)}

.dp{display:none;margin-top:20px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:20px}
.dp.vis{display:block}
.dp-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.dp-top h2{font-size:16px;color:#fff}
.dp-close{padding:4px 10px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px}
.dp-close:hover{border-color:var(--red);color:var(--red)}

.dp-nav{display:flex;gap:6px;margin-bottom:14px}
.dp-nav button{padding:4px 12px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:12px}
.dp-nav button:hover{border-color:var(--accent);color:var(--accent)}

.tabs{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:14px}
.tab{padding:8px 18px;cursor:pointer;color:var(--muted);font-size:13px;border-bottom:2px solid transparent;transition:all .12s}
.tab:hover{color:var(--text)}.tab.on{color:var(--accent);border-bottom-color:var(--accent)}
.tc{display:none}.tc.on{display:block}

.tblk{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:14px;font-size:12px;line-height:1.8;white-space:pre-wrap;word-break:break-all;max-height:500px;overflow-y:auto;font-family:'SF Mono',Monaco,Consolas,monospace}

.ctable{width:100%;border-collapse:collapse;font-size:12px}
.ctable th{background:var(--bg);padding:8px 10px;text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase;border-bottom:1px solid var(--border)}
.ctable td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}
.ctable tr:hover{background:var(--hover)}
.ctable .ck{font-family:monospace;color:var(--green);font-size:11px}
.ctable .tp{font-size:10px;padding:2px 6px;border-radius:3px}
.ctable thead th{position:sticky;top:0}
.ctable td[style*="font-weight:700"]{font-size:13px}
.tp-hard{background:#1e3a5f;color:#58a6ff}
.tp-soft{background:#3b2f0a;color:#d29922}

details{margin-bottom:10px}
details summary{cursor:pointer;color:var(--accent);font-size:13px;padding:6px 0}
details summary:hover{text-decoration:underline}

.empty{text-align:center;padding:40px;color:var(--muted);font-size:13px}
</style>
</head>
<body>

<div class="topbar">
<span class="logo">◆</span>
<h1>FinIF Dashboard</h1>
<button class="mtab active" onclick="switchPanel('benchmark')">Benchmark</button>
<button class="mtab" onclick="switchPanel('training')">Training Data</button>
<button class="mtab" onclick="switchPanel('evaluation')">Evaluation</button>
</div>

<!-- ==================== BENCHMARK PANEL ==================== -->
<div class="panel active" id="p-benchmark">
<div class="wrap">

<div class="sg" id="bm-stats"></div>

<div class="chart-row">
<div class="chart-box"><h3>L1 分布</h3><div class="bars" id="bm-l1-bars"></div></div>
<div class="chart-box"><h3>L2 分布</h3><div class="bars" id="bm-l2-bars"></div></div>
</div>

<div class="chart-row">
<div class="chart-box"><h3>Taxonomy 大类分布</h3><div class="bars" id="bm-tagcat-bars"></div></div>
<div class="chart-box"><h3>Compliance vs Correctness</h3><div class="pie-wrap" id="bm-if-pie"></div></div>
</div>

<div class="chart-row">
<div class="chart-box" style="grid-column:1/-1"><h3>Taxonomy 子类分布</h3><div class="bars" id="bm-tag-bars" style="height:140px"></div></div>
</div>

<div class="sec">
<h2>Cases</h2>
<div class="filters">
<button class="fb on" onclick="bmFilter('all',this)">All</button>
<button class="fb" onclick="bmFilter('T1',this)">T1</button>
<button class="fb" onclick="bmFilter('T2',this)">T2</button>
<button class="fb" onclick="bmFilter('T3',this)">T3</button>
<input class="sb" id="bm-search" placeholder="Search case_id..." oninput="bmSearch()">
</div>
<div class="list" id="bm-list"></div>
<div class="dp" id="bm-detail"></div>
</div>

</div>
</div>

<!-- ==================== TRAINING DATA PANEL ==================== -->
<div class="panel" id="p-training">
<div class="wrap">

<div class="sg" id="tr-stats"></div>

<div class="chart-row">
<div class="chart-box"><h3>L1 分布</h3><div class="bars" id="tr-l1-bars"></div></div>
<div class="chart-box"><h3>L2 分布</h3><div class="bars" id="tr-l2-bars"></div></div>
</div>

<div class="chart-row">
<div class="chart-box"><h3>约束使用频次</h3><div class="bars" id="tr-cid-bars"></div></div>
<div class="chart-box"><h3>Context 来源</h3><div class="pie-wrap" id="tr-src-pie"></div></div>
</div>

<div class="sec">
<h2>Samples</h2>
<div class="filters">
<button class="fb on" onclick="trFilter('all',this)">All</button>
<button class="fb" onclick="trFilter('T1',this)">T1</button>
<button class="fb" onclick="trFilter('T2',this)">T2</button>
<button class="fb" onclick="trFilter('T3',this)">T3</button>
<select class="sf" id="tr-l2-sel" onchange="trApply()"><option value="">All L2</option></select>
<select class="sf" id="tr-src-sel" onchange="trApply()"><option value="">All Sources</option></select>
<input class="sb" id="tr-search" placeholder="Search case_id / sample_id..." oninput="trApply()">
</div>
<div class="list" id="tr-list"></div>
<div class="paging" id="tr-paging"></div>
<div class="dp" id="tr-detail"></div>
</div>

</div>
</div>

<!-- ==================== EVALUATION PANEL ==================== -->
<div class="panel" id="p-evaluation">
<div class="wrap">

<div class="sg" id="ev-stats"></div>

<div class="sec">
<h2>Model Comparison — Compliance vs Correctness</h2>
<div class="chart-box" style="margin-bottom:24px">
<h3>Dual-Axis Scores (grouped bars)</h3>
<div id="ev-dual-bars" style="display:flex;gap:2px;align-items:end;height:200px;padding:0 2px"></div>
<div id="ev-dual-legend" style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:12px"></div>
</div>
</div>

<div class="chart-row">
<div class="chart-box">
<h3>Overall Score Ranking</h3>
<div class="bars" id="ev-overall-bars" style="height:160px"></div>
</div>
<div class="chart-box">
<h3>Compliance vs Correctness (Scatter)</h3>
<div id="ev-scatter" style="position:relative;width:100%;height:240px;background:var(--bg);border:1px solid var(--border);border-radius:4px"></div>
</div>
</div>

<div class="sec">
<h2>Score Table</h2>
<div style="overflow-x:auto">
<table class="ctable" id="ev-table">
<thead><tr>
<th>Model</th><th>Overall</th><th>Compliance</th><th>Correctness</th>
<th>T1</th><th>T2</th><th>T3</th><th>Cases</th>
</tr></thead>
<tbody id="ev-table-body"></tbody>
</table>
</div>
</div>

</div>
</div>

<script>
const BM = __BENCHMARK_DATA__;
const TR = __TRAINING_DATA__;
const SC = __SCORES_DATA__;
const PAGE_SIZE = 50;

// ---- Utils ----
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function renderBars(id,data,colors){
  const el=document.getElementById(id);
  const vals=Object.values(data);
  const mx=Math.max(...vals,1);
  let h='';
  const cs=colors||['var(--accent)'];
  Object.entries(data).forEach(([k,v],i)=>{
    const pct=Math.max(2,v/mx*100);
    const c=cs[i%cs.length];
    h+=`<div class="bi"><div class="bv">${v}</div><div class="b" style="height:${pct}%;background:${c}"></div><div class="bl">${k}</div></div>`;
  });
  el.innerHTML=h;
}
function renderStats(id,cards){
  document.getElementById(id).innerHTML=cards.map(c=>`<div class="sc"><div class="n">${c[0]}</div><div class="l">${c[1]}</div></div>`).join('');
}
function l1badge(l1){return `<span class="badge b${l1}">${l1}</span>`}
function srcBadge(s){const m={synthetic:'bsyn',benchmark:'bbench',external:'bext',legacy:'bleg'};return `<span class="badge ${m[s]||'bleg'}">${s}</span>`}

const TAG_COLORS={F1:'#58a6ff',F2:'#4a9af5',F3:'#3c8eeb',F4:'#2e82e0',F5:'#2076d6',F6:'#1a6dc0',F7:'#1464b0',F8:'#0e5ba0',
  N1:'#3fb950',N2:'#35a046',N3:'#2b873c',N4:'#216e32',
  L1:'#a371f7',L2:'#9560e8',L3:'#874fd9',L4:'#793eca',
  S1:'#d29922',S2:'#c08a1e',S3:'#ae7b1a',S4:'#9c6c16',
  C1:'#f0883e',C2:'#e07934',C3:'#d06a2a',C4:'#c05b20',C5:'#b04c16',C6:'#f85149'};
const TAG_CAT_COLORS={F:'#58a6ff',N:'#3fb950',L:'#a371f7',S:'#d29922',C:'#f85149'};

// ---- Benchmark ----
function initBenchmark(){
  const s=BM.stats;
  renderStats('bm-stats',[
    [s.total,'Cases'],[s.total_constraints,'Constraints'],
    [s.avg_constraints,'Avg/Case'],
    [s.comp_total,'Compliance'],['<span style="color:var(--green)">'+s.comp_ratio+'%</span>','Comp. Ratio'],
    [s.corr_total,'Correctness']
  ]);
  const l1c=['#58a6ff','#d29922','#f85149'];
  renderBars('bm-l1-bars',s.by_l1,l1c);
  const l2c=Object.keys(s.by_l2).map(k=>k.startsWith('T1')?'#58a6ff':k.startsWith('T2')?'#d29922':'#f85149');
  renderBars('bm-l2-bars',s.by_l2,l2c);

  // Tag category bars (F/N/L/S/C)
  if(s.by_tag_cat){
    const catLabels={F:'Format',N:'Number',L:'Linguistic',S:'Style',C:'Content'};
    const catData={};const catColors=[];
    Object.entries(s.by_tag_cat).forEach(([k,v])=>{catData[catLabels[k]||k]=v;catColors.push(TAG_CAT_COLORS[k]||'#8b949e')});
    renderBars('bm-tagcat-bars',catData,catColors);
  }

  // Compliance vs Correctness pie
  if(s.comp_total!==undefined){
    const ifn=s.comp_total,cn=s.corr_total;
    const t=ifn+cn;
    const ifp=ifn/t*360;
    const stops=`var(--green) 0deg ${ifp}deg, var(--red) ${ifp}deg 360deg`;
    document.getElementById('bm-if-pie').innerHTML=`
      <div class="pie" style="background:conic-gradient(${stops})"></div>
      <div class="pie-legend">
        <div class="pie-item"><div class="pie-dot" style="background:var(--green)"></div>Compliance: ${ifn} (${(ifn/t*100).toFixed(1)}%)</div>
        <div class="pie-item"><div class="pie-dot" style="background:var(--red)"></div>Correctness: ${cn} (${(cn/t*100).toFixed(1)}%)</div>
      </div>`;
  }

  // Per-tag bars
  if(s.by_tag){
    const tc=[];Object.keys(s.by_tag).forEach(k=>tc.push(TAG_COLORS[k]||'#8b949e'));
    renderBars('bm-tag-bars',s.by_tag,tc);
  }

  bmRender(BM.cases);
}
let bmFilterVal='all';
function bmFilter(v,btn){
  bmFilterVal=v;
  document.querySelectorAll('#p-benchmark .fb').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  bmApply();
}
function bmSearch(){bmApply()}
function bmApply(){
  const q=document.getElementById('bm-search').value.toLowerCase();
  let items=BM.cases.filter(c=>{
    if(bmFilterVal!=='all'&&c.L1!==bmFilterVal) return false;
    if(q&&!c.case_id.toLowerCase().includes(q)) return false;
    return true;
  });
  bmRender(items);
}
function bmRender(items){
  const el=document.getElementById('bm-list');
  if(!items.length){el.innerHTML='<div class="empty">No cases found</div>';return}
  el.innerHTML=items.map((c,i)=>{
    const tcats=(c.tag_cats||[]).map(t=>`<span class="badge" style="background:${TAG_CAT_COLORS[t]||'#333'}22;color:${TAG_CAT_COLORS[t]||'#8b949e'};font-size:9px;padding:1px 5px">${t}</span>`).join('');
    return `<div class="li" onclick="bmShow('${c.case_id}')">
    <span class="id">${c.case_id}</span>${l1badge(c.L1)}
    <span class="badge" style="background:#1b1b3a;color:var(--purple)">${c.L2}</span>
    <span class="cb">${c.n_constraints}c</span>
    <span style="font-size:10px;color:var(--green)">${c.n_comp||0} COMP</span>
    <span style="font-size:10px;color:var(--red)">${c.n_corr||0} CORR</span>
    ${tcats}
    <span class="ldesc">${esc(c.prompt.substring(c.context.length).trim().substring(0,60))}</span>
  </div>`}).join('');
}
function bmShow(cid){
  const c=BM.cases.find(x=>x.case_id===cid);if(!c)return;
  const dp=document.getElementById('bm-detail');
  dp.classList.add('vis');
  const query=c.prompt.substring(c.context.length).trim();
  let ctbl=`<table class="ctable"><tr><th>ID</th><th>Type</th><th>Tag</th><th>Checker</th><th>Description</th><th>Params</th></tr>`;
  c.constraints.forEach(x=>{
    const tp=x.type==='hard'?'<span class="tp tp-hard">hard</span>':'<span class="tp tp-soft">soft</span>';
    const tag=x.tag?`<span class="tp" style="background:${TAG_COLORS[x.tag]||'#333'}33;color:${TAG_COLORS[x.tag]||'#8b949e'}">${x.tag}</span>`:'—';
    const ifmark=x.is_if===false?'<span style="font-size:9px;color:var(--red);margin-left:3px">CORR</span>':'<span style="font-size:9px;color:var(--green);margin-left:3px">COMP</span>';
    const params=x.params?`<code style="font-size:10px;color:var(--muted)">${esc(JSON.stringify(x.params).substring(0,120))}</code>`:'—';
    ctbl+=`<tr><td>${x.key}</td><td>${tp}${ifmark}</td><td>${tag}</td><td class="ck">${x.checker||'—'}</td><td>${esc(x.description||'')}</td><td>${params}</td></tr>`;
  });
  ctbl+='</table>';
  dp.innerHTML=`
    <div class="dp-top"><h2>${cid} ${l1badge(c.L1)} <span class="badge" style="background:#1b1b3a;color:var(--purple)">${c.L2}</span></h2>
    <button class="dp-close" onclick="document.getElementById('bm-detail').classList.remove('vis')">✕ Close</button></div>
    <details><summary>Context (${c.context.length} chars)</summary><div class="tblk">${esc(c.context)}</div></details>
    <div class="sec"><h2>Query</h2><div class="tblk">${esc(query)}</div></div>
    <div class="sec"><h2>Constraints (${c.n_constraints})</h2>${ctbl}</div>`;
  dp.scrollIntoView({behavior:'smooth',block:'start'});
}

// ---- Training ----
let trFilterVal='all',trPage=0,trFiltered=[];
function initTraining(){
  const s=TR.stats;
  renderStats('tr-stats',[
    [s.total,'Samples'],[s.avg_constraints,'Avg Constraints'],
    [s.hard_total,'Hard'],[s.soft_total,'Soft'],[s.hidden_total,'Hidden Checkers']
  ]);
  const l1c=['#58a6ff','#d29922','#f85149'];
  renderBars('tr-l1-bars',s.by_l1,l1c);
  const l2c=Object.keys(s.by_l2).map(k=>k.startsWith('T1')?'#58a6ff':k.startsWith('T2')?'#d29922':'#f85149');
  renderBars('tr-l2-bars',s.by_l2,l2c);
  const cidColors=Object.keys(s.by_constraint).map(k=>k.startsWith('G')?'#3fb950':'#58a6ff');
  renderBars('tr-cid-bars',s.by_constraint,cidColors);

  // Pie
  const srcData=s.by_source;
  const pieColors=['#58a6ff','#3fb950','#d29922','#a371f7','#f85149'];
  const total=Object.values(srcData).reduce((a,b)=>a+b,0);
  let angle=0;const stops=[];
  const legendItems=[];
  Object.entries(srcData).forEach(([k,v],i)=>{
    const deg=v/total*360;const c=pieColors[i%pieColors.length];
    stops.push(`${c} ${angle}deg ${angle+deg}deg`);
    legendItems.push(`<div class="pie-item"><div class="pie-dot" style="background:${c}"></div>${k}: ${v} (${(v/total*100).toFixed(1)}%)</div>`);
    angle+=deg;
  });
  document.getElementById('tr-src-pie').innerHTML=`<div class="pie" style="background:conic-gradient(${stops.join(',')})"></div><div class="pie-legend">${legendItems.join('')}</div>`;

  // L2 dropdown
  const l2sel=document.getElementById('tr-l2-sel');
  Object.keys(s.by_l2).sort().forEach(k=>{l2sel.innerHTML+=`<option value="${k}">${k}</option>`});
  // Source dropdown
  const srcsel=document.getElementById('tr-src-sel');
  Object.keys(s.by_source).sort().forEach(k=>{srcsel.innerHTML+=`<option value="${k}">${k}</option>`});

  trApply();
}
function trFilter(v,btn){
  trFilterVal=v;
  document.querySelectorAll('#p-training .fb').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  trPage=0;trApply();
}
function trApply(){
  const q=document.getElementById('tr-search').value.toLowerCase();
  const l2=document.getElementById('tr-l2-sel').value;
  const src=document.getElementById('tr-src-sel').value;
  trFiltered=TR.samples.filter(s=>{
    if(trFilterVal!=='all'&&s.L1!==trFilterVal) return false;
    if(l2&&s.L2!==l2) return false;
    if(src&&s.context_source!==src) return false;
    if(q&&!s.case_id.toLowerCase().includes(q)&&!s.sample_id.toLowerCase().includes(q)) return false;
    return true;
  });
  trRenderPage();
}
function trRenderPage(){
  const start=trPage*PAGE_SIZE;
  const page=trFiltered.slice(start,start+PAGE_SIZE);
  const el=document.getElementById('tr-list');
  if(!page.length){el.innerHTML='<div class="empty">No samples found</div>';document.getElementById('tr-paging').innerHTML='';return}
  el.innerHTML=page.map(s=>`<div class="li" onclick="trShow('${s.sample_id}')">
    <span class="id">${s.sample_id}</span>${l1badge(s.L1)}
    <span class="badge" style="background:#1b1b3a;color:var(--purple)">${s.L2}</span>
    ${srcBadge(s.context_source)}
    <span class="cb">${s.n_constraints}c</span>
    <span class="ldesc">${esc(s.preview)}</span>
  </div>`).join('');
  const totalPages=Math.ceil(trFiltered.length/PAGE_SIZE);
  document.getElementById('tr-paging').innerHTML=`
    <button onclick="trPage=Math.max(0,trPage-1);trRenderPage()" ${trPage===0?'disabled':''}>← Prev</button>
    <span>${trPage+1} / ${totalPages} (${trFiltered.length} items)</span>
    <button onclick="trPage=Math.min(${totalPages-1},trPage+1);trRenderPage()" ${trPage>=totalPages-1?'disabled':''}>Next →</button>`;
}
function trShow(sid){
  const s=TR.samples.find(x=>x.sample_id===sid);if(!s)return;
  const dp=document.getElementById('tr-detail');
  dp.classList.add('vis');
  dp.innerHTML=`<div class="dp-top"><h2>${sid} ${l1badge(s.L1)} <span class="badge" style="background:#1b1b3a;color:var(--purple)">${s.L2}</span> ${srcBadge(s.context_source)}</h2>
    <button class="dp-close" onclick="document.getElementById('tr-detail').classList.remove('vis')">✕ Close</button></div>
    <div class="empty">Loading...</div>`;
  dp.scrollIntoView({behavior:'smooth',block:'start'});
  fetch('/api/sample/'+encodeURIComponent(sid)).then(r=>r.json()).then(d=>{
    if(!d||d.error){dp.querySelector('.empty').textContent='Not found';return}
    let ctbl=`<table class="ctable"><tr><th>ID</th><th>Name</th><th>Type</th><th>Checker</th><th>Rendered Text</th><th>Params</th></tr>`;
    (d.constraints||[]).forEach(c=>{
      const tp=c.type==='hard'?'<span class="tp tp-hard">hard</span>':'<span class="tp tp-soft">soft</span>';
      const params=c.params?`<code style="font-size:10px;color:var(--muted)">${esc(JSON.stringify(c.params).substring(0,100))}</code>`:'—';
      ctbl+=`<tr><td>${c.id}</td><td>${esc(c.name||'')}</td><td>${tp}</td><td class="ck">${c.checker||'—'}</td><td>${esc(c.rendered_text||'')}</td><td>${params}</td></tr>`;
    });
    ctbl+='</table>';
    let htbl='';
    if(d.hidden_checkers&&d.hidden_checkers.length){
      htbl=`<div class="sec" style="margin-top:14px"><h2>Hidden Checkers (${d.hidden_checkers.length})</h2><table class="ctable"><tr><th>ID</th><th>Checker</th><th>Params</th></tr>`;
      d.hidden_checkers.forEach(c=>{
        htbl+=`<tr><td>${c.id}</td><td class="ck">${c.checker}</td><td><code style="font-size:10px;color:var(--muted)">${esc(JSON.stringify(c.params).substring(0,150))}</code></td></tr>`;
      });
      htbl+='</table></div>';
    }
    dp.innerHTML=`
      <div class="dp-top"><h2>${sid} ${l1badge(d.L1)} <span class="badge" style="background:#1b1b3a;color:var(--purple)">${d.L2}</span> ${srcBadge(d.context_source)}</h2>
      <button class="dp-close" onclick="document.getElementById('tr-detail').classList.remove('vis')">✕ Close</button></div>
      <div class="tabs" id="tr-tabs">
        <div class="tab on" onclick="trTab(0,this)">Full Prompt</div>
        <div class="tab" onclick="trTab(1,this)">Constraints</div>
      </div>
      <div class="tc on" id="trc-0"><div class="tblk">${esc(d.prompt)}</div></div>
      <div class="tc" id="trc-1">${ctbl}${htbl}</div>`;
  });
}
function trTab(idx,el){
  document.querySelectorAll('#tr-tabs .tab').forEach(t=>t.classList.remove('on'));
  el.classList.add('on');
  for(let i=0;i<2;i++) document.getElementById('trc-'+i).classList.toggle('on',i===idx);
}

// ---- Panel switch ----
function switchPanel(name){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('p-'+name).classList.add('active');
  document.querySelectorAll('.mtab').forEach(t=>t.classList.remove('active'));
  document.querySelector(`.mtab[onclick*="${name}"]`).classList.add('active');
}

// ---- Evaluation ----
const MODEL_COLORS=['#58a6ff','#3fb950','#d29922','#a371f7','#f85149','#f0883e','#79c0ff','#7ee787','#e3b341','#bc8cff'];

function initEvaluation(){
  const models=SC.models||[];
  if(!models.length){
    document.getElementById('ev-stats').innerHTML='<div class="sc" style="grid-column:1/-1"><div class="n">—</div><div class="l">No score files found in output/</div></div>';
    return;
  }

  // Stats cards
  const bestOverall=models.reduce((a,b)=>a.overall>=b.overall?a:b);
  const hasDual=models.some(m=>m.compliance!==null||m.correctness!==null);
  const cards=[
    [models.length,'Models Evaluated'],
    [bestOverall.overall+'%','Best Overall ('+bestOverall.model+')'],
  ];
  if(hasDual){
    const bestComp=models.filter(m=>m.compliance!==null).reduce((a,b)=>(a&&a.compliance>=b.compliance)?a:b,null);
    const bestCorr=models.filter(m=>m.correctness!==null).reduce((a,b)=>(a&&a.correctness>=b.correctness)?a:b,null);
    if(bestComp) cards.push([bestComp.compliance+'%','Best Compliance ('+bestComp.model+')']);
    if(bestCorr) cards.push([bestCorr.correctness+'%','Best Correctness ('+bestCorr.model+')']);
  }
  renderStats('ev-stats',cards);

  // Overall ranking bars
  const overallData={};
  const overallColors=[];
  models.sort((a,b)=>b.overall-a.overall).forEach((m,i)=>{
    overallData[m.model]=m.overall;
    overallColors.push(MODEL_COLORS[i%MODEL_COLORS.length]);
  });
  renderBars('ev-overall-bars',overallData,overallColors);

  // Dual-axis grouped bars
  renderDualBars(models);

  // Scatter plot
  renderScatter(models);

  // Table
  renderEvalTable(models);
}

function renderDualBars(models){
  const el=document.getElementById('ev-dual-bars');
  const legend=document.getElementById('ev-dual-legend');
  const hasDual=models.some(m=>m.compliance!==null||m.correctness!==null);
  const sorted=[...models].sort((a,b)=>b.overall-a.overall);

  // Determine max value for scaling
  let maxVal=0;
  sorted.forEach(m=>{
    maxVal=Math.max(maxVal,m.overall||0);
    if(m.compliance!==null) maxVal=Math.max(maxVal,m.compliance);
    if(m.correctness!==null) maxVal=Math.max(maxVal,m.correctness);
  });
  maxVal=Math.max(maxVal,1);

  let h='';
  sorted.forEach(m=>{
    const ov=m.overall||0;
    const comp=m.compliance;
    const corr=m.correctness;
    h+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;min-width:0">';

    if(hasDual&&(comp!==null||corr!==null)){
      // Grouped: compliance + correctness
      const compVal=comp!==null?comp:0;
      const corrVal=corr!==null?corr:0;
      const compPct=Math.max(2,compVal/maxVal*100);
      const corrPct=Math.max(2,corrVal/maxVal*100);
      h+='<div style="display:flex;gap:1px;align-items:end;width:100%;height:100%">';
      h+=`<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:end;height:100%">`;
      h+=`<div class="bv">${comp!==null?compVal:'—'}</div>`;
      h+=`<div style="width:100%;border-radius:3px 3px 0 0;background:var(--green);height:${compPct}%"></div>`;
      h+=`</div>`;
      h+=`<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:end;height:100%">`;
      h+=`<div class="bv">${corr!==null?corrVal:'—'}</div>`;
      h+=`<div style="width:100%;border-radius:3px 3px 0 0;background:var(--purple);height:${corrPct}%"></div>`;
      h+=`</div>`;
      h+='</div>';
    } else {
      // Fallback: single overall bar
      const pct=Math.max(2,ov/maxVal*100);
      h+=`<div class="bv">${ov}</div>`;
      h+=`<div style="width:100%;border-radius:3px 3px 0 0;background:var(--accent);height:${pct}%;min-height:2px"></div>`;
    }
    h+=`<div class="bl">${m.model}</div></div>`;
  });
  el.innerHTML=h;

  if(hasDual){
    legend.innerHTML=`
      <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;border-radius:2px;background:var(--green)"></span>Compliance</span>
      <span style="display:flex;align-items:center;gap:4px"><span style="width:12px;height:12px;border-radius:2px;background:var(--purple)"></span>Correctness</span>`;
  } else {
    legend.innerHTML='<span style="color:var(--muted);font-size:11px">Dual-axis data not yet available — showing overall scores only</span>';
  }
}

function renderScatter(models){
  const el=document.getElementById('ev-scatter');
  const hasDual=models.some(m=>m.compliance!==null&&m.correctness!==null);
  if(!hasDual){
    el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:12px">Dual-axis data not yet available</div>';
    return;
  }
  const pts=models.filter(m=>m.compliance!==null&&m.correctness!==null);
  // SVG scatter
  const pad=40,w=el.clientWidth||360,h=240;
  const xMin=Math.max(0,Math.min(...pts.map(p=>p.compliance))-5);
  const xMax=Math.min(100,Math.max(...pts.map(p=>p.compliance))+5);
  const yMin=Math.max(0,Math.min(...pts.map(p=>p.correctness))-5);
  const yMax=Math.min(100,Math.max(...pts.map(p=>p.correctness))+5);
  const sx=v=>(v-xMin)/(xMax-xMin)*(w-2*pad)+pad;
  const sy=v=>h-pad-(v-yMin)/(yMax-yMin)*(h-2*pad);

  let svg=`<svg width="${w}" height="${h}" style="width:100%;height:100%">`;
  // Grid lines
  for(let v=Math.ceil(xMin/10)*10;v<=xMax;v+=10){
    svg+=`<line x1="${sx(v)}" y1="${pad}" x2="${sx(v)}" y2="${h-pad}" stroke="var(--border)" stroke-dasharray="3"/>`;
    svg+=`<text x="${sx(v)}" y="${h-pad+14}" fill="var(--muted)" font-size="10" text-anchor="middle">${v}</text>`;
  }
  for(let v=Math.ceil(yMin/10)*10;v<=yMax;v+=10){
    svg+=`<line x1="${pad}" y1="${sy(v)}" x2="${w-pad}" y2="${sy(v)}" stroke="var(--border)" stroke-dasharray="3"/>`;
    svg+=`<text x="${pad-6}" y="${sy(v)+4}" fill="var(--muted)" font-size="10" text-anchor="end">${v}</text>`;
  }
  // Axis labels
  svg+=`<text x="${w/2}" y="${h-4}" fill="var(--muted)" font-size="11" text-anchor="middle">Compliance %</text>`;
  svg+=`<text x="12" y="${h/2}" fill="var(--muted)" font-size="11" text-anchor="middle" transform="rotate(-90,12,${h/2})">Correctness %</text>`;
  // Points
  pts.forEach((p,i)=>{
    const cx=sx(p.compliance),cy=sy(p.correctness);
    const c=MODEL_COLORS[i%MODEL_COLORS.length];
    svg+=`<circle cx="${cx}" cy="${cy}" r="6" fill="${c}" stroke="#fff" stroke-width="1.5" opacity="0.9"/>`;
    svg+=`<text x="${cx}" y="${cy-10}" fill="var(--text)" font-size="10" text-anchor="middle">${p.model}</text>`;
  });
  svg+='</svg>';
  el.innerHTML=svg;
}

function renderEvalTable(models){
  const tbody=document.getElementById('ev-table-body');
  const fmt=v=>v!==null&&v!==undefined?v.toFixed(1)+'%':'N/A';
  const fmtClass=v=>v!==null&&v!==undefined?(v>=80?'color:var(--green)':v>=60?'color:var(--yellow)':'color:var(--red)'):'color:var(--muted)';
  const sorted=[...models].sort((a,b)=>b.overall-a.overall);
  let rows='';
  sorted.forEach((m,i)=>{
    rows+=`<tr>
      <td><span style="font-weight:600;color:var(--accent)">${esc(m.model)}</span></td>
      <td style="${fmtClass(m.overall)};font-weight:700">${fmt(m.overall)}</td>
      <td style="${fmtClass(m.compliance)}">${fmt(m.compliance)}</td>
      <td style="${fmtClass(m.correctness)}">${fmt(m.correctness)}</td>
      <td style="${fmtClass(m.T1)}">${fmt(m.T1)}</td>
      <td style="${fmtClass(m.T2)}">${fmt(m.T2)}</td>
      <td style="${fmtClass(m.T3)}">${fmt(m.T3)}</td>
      <td style="color:var(--muted)">${m.n_cases}</td>
    </tr>`;
  });
  tbody.innerHTML=rows;
}

// ---- Init ----
initBenchmark();
initTraining();
initEvaluation();
</script>
</body>
</html>"""


def build_html(bm_data, tr_data, sc_data):
    bm_json = json.dumps(bm_data, ensure_ascii=False)
    tr_json = json.dumps(tr_data, ensure_ascii=False)
    sc_json = json.dumps(sc_data, ensure_ascii=False)
    return (HTML
            .replace("__BENCHMARK_DATA__", bm_json)
            .replace("__TRAINING_DATA__", tr_json)
            .replace("__SCORES_DATA__", sc_json))


class Handler(SimpleHTTPRequestHandler):
    html_content = b""
    full_map = {}
    scores_data = {}

    def do_GET(self):
        if self.path.startswith("/api/sample/"):
            from urllib.parse import unquote
            sid = unquote(self.path[len("/api/sample/"):])
            data = self.full_map.get(sid, {"error": "not found"})
            self._json_response(data)
        elif self.path == "/api/scores":
            self._json_response(self.scores_data)
        elif self.path == "/" or self.path == "":
            body = self.html_content
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main():
    print("Loading benchmark data...")
    bm = load_benchmark()
    print(f"  {bm['stats']['total']} cases, {bm['stats']['total_constraints']} constraints")

    print("Loading training data...")
    tr, full_map = load_training()
    print(f"  {tr['stats']['total']} samples")

    print("Loading evaluation scores...")
    sc = load_scores()
    print(f"  {len(sc['models'])} models found")

    print("Building HTML...")
    Handler.html_content = build_html(bm, tr, sc).encode("utf-8")
    Handler.full_map = full_map
    Handler.scores_data = sc
    html_kb = len(Handler.html_content) // 1024
    print(f"  HTML size: {html_kb} KB")

    port = 18926
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n  → http://localhost:{port}\n")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
