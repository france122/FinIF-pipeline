#!/usr/bin/env python3
"""Build benchmark_stats.html with constraint distribution + model performance analytics."""
import json, os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    with open(os.path.join(SCRIPT_DIR, "benchmark", "eval_config_all.json"), encoding="utf-8") as f:
        eval_cfg = json.load(f)["constraints"]
    with open(os.path.join(SCRIPT_DIR, "benchmark", "benchmark_all.json"), encoding="utf-8") as f:
        bench = json.load(f)["cases"]

    models = ["ds-v4-flash", "ds-v4-flash-thinking", "ds-v4-pro", "ds-v4-pro-thinking", "qwen3-8b"]
    scores = {}
    for m in models:
        with open(os.path.join(SCRIPT_DIR, f"benchmark/scores/scores_{m}.json"), encoding="utf-8") as f:
            scores[m] = json.load(f)

    # --- Constraint distribution stats (existing) ---
    tag_counts = defaultdict(int)
    cat_counts = defaultdict(int)
    hard_count = soft_count = 0
    for key, cfg in eval_cfg.items():
        tag = cfg.get("tag", "?")
        tag_name = cfg.get("tag_name", "")
        tag_counts[(tag, tag_name)] += 1
        cat = tag[0]
        cat_map = {"F": "Format", "S": "Style", "L": "Linguistic", "N": "Number", "C": "Content"}
        cat_counts[cat_map.get(cat, cat)] += 1
        if cfg["type"] == "hard":
            hard_count += 1
        else:
            soft_count += 1
    total_constraints = hard_count + soft_count

    # Per-case constraint count distribution
    case_cons = defaultdict(int)
    for key in eval_cfg:
        cid = key.split("#")[0]
        case_cons[cid] += 1
    count_dist = defaultdict(int)
    for cnt in case_cons.values():
        count_dist[cnt] += 1

    # L1/L2 tier distribution
    tier_case_count = defaultdict(int)
    l2_case_count = defaultdict(int)
    for c in bench:
        cid = c["case_id"]
        tier = cid.split(".")[0]  # T1, T2, T3
        l2 = cid.split("-")[0]    # T1.1, T2.3, etc.
        tier_case_count[tier] += 1
        l2_case_count[l2] += 1

    # --- Model performance analytics ---
    # Per-tag pass rates
    tag_results = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "total": 0}))
    # Per-category pass rates
    cat_results = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "total": 0}))
    # Hard vs soft pass rates
    type_results = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "total": 0}))
    # Per-constraint pass rates
    constraint_results = {}
    # Per-L2 pass rates
    l2_results = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "total": 0}))
    # Easy (<=4) vs Hard (>=5) set pass rates
    easy_hard_results = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "total": 0}))

    cat_map = {"F": "Format", "S": "Style", "L": "Linguistic", "N": "Number", "C": "Content"}

    for key, cfg in eval_cfg.items():
        cid = key.split("#")[0]
        tag = cfg.get("tag", "?")
        tag_name = cfg.get("tag_name", "")
        ctype = cfg["type"]
        cat = cat_map.get(tag[0], tag[0])
        l2 = cid.split("-")[0]
        n_cons = case_cons[cid]
        difficulty = "easy" if n_cons <= 3 else "hard"

        if key not in constraint_results:
            constraint_results[key] = {
                "description": cfg.get("description", ""),
                "tag": tag,
                "tag_name": tag_name,
                "type": ctype,
            }

        for m in models:
            res = scores[m]["results"].get(cid, {}).get(key, {})
            passed = res.get("pass") is True

            tag_results[(tag, tag_name)][m]["total"] += 1
            if passed:
                tag_results[(tag, tag_name)][m]["pass"] += 1

            cat_results[cat][m]["total"] += 1
            if passed:
                cat_results[cat][m]["pass"] += 1

            type_results[ctype][m]["total"] += 1
            if passed:
                type_results[ctype][m]["pass"] += 1

            l2_results[l2][m]["total"] += 1
            if passed:
                l2_results[l2][m]["pass"] += 1

            easy_hard_results[difficulty][m]["total"] += 1
            if passed:
                easy_hard_results[difficulty][m]["pass"] += 1

            constraint_results[key].setdefault(m, passed)

    # Sort tags by average pass rate ascending
    def tag_avg(tag_key):
        rates = []
        for m in models:
            d = tag_results[tag_key][m]
            rates.append(d["pass"] / d["total"] if d["total"] else 1)
        return sum(rates) / len(rates)

    sorted_tags = sorted(tag_results.keys(), key=tag_avg)

    # Build data for JS
    analytics = {
        "models": models,
        "tier_scores": {m: {k: round(v * 100, 1) if isinstance(v, float) else v for k, v in scores[m]["tier_scores"].items()} for m in models},
        "tag_pass_rates": {
            "labels": [f"{t[0]} {t[1]}" for t in sorted_tags],
            **{m: [round(tag_results[t][m]["pass"] / tag_results[t][m]["total"] * 100, 1) if tag_results[t][m]["total"] else 0 for t in sorted_tags] for m in models},
            "counts": [tag_results[t][models[0]]["total"] for t in sorted_tags],
        },
        "cat_pass_rates": {},
        "type_pass_rates": {},
        "l2_pass_rates": {},
        "easy_hard_pass_rates": {},
        "constraint_table": [],
    }

    for cat in ["Format", "Style", "Linguistic", "Number", "Content"]:
        analytics["cat_pass_rates"][cat] = {}
        for m in models:
            d = cat_results[cat][m]
            analytics["cat_pass_rates"][cat][m] = round(d["pass"] / d["total"] * 100, 1) if d["total"] else 0

    for ctype in ["hard", "soft"]:
        analytics["type_pass_rates"][ctype] = {}
        for m in models:
            d = type_results[ctype][m]
            analytics["type_pass_rates"][ctype][m] = round(d["pass"] / d["total"] * 100, 1) if d["total"] else 0
        analytics["type_pass_rates"][ctype]["count"] = type_results[ctype][models[0]]["total"]

    for l2 in sorted(l2_results.keys()):
        analytics["l2_pass_rates"][l2] = {}
        for m in models:
            d = l2_results[l2][m]
            analytics["l2_pass_rates"][l2][m] = round(d["pass"] / d["total"] * 100, 1) if d["total"] else 0

    for diff in ["easy", "hard"]:
        analytics["easy_hard_pass_rates"][diff] = {}
        for m in models:
            d = easy_hard_results[diff][m]
            analytics["easy_hard_pass_rates"][diff][m] = round(d["pass"] / d["total"] * 100, 1) if d["total"] else 0
        analytics["easy_hard_pass_rates"][diff]["count"] = easy_hard_results[diff][models[0]]["total"]

    for key in sorted(constraint_results.keys()):
        cr = constraint_results[key]
        row = {
            "key": key,
            "description": cr["description"],
            "tag": cr["tag"],
            "tag_name": cr["tag_name"],
            "type": cr["type"],
        }
        for m in models:
            row[m] = cr.get(m, False)
        analytics["constraint_table"].append(row)

    # Existing static data
    sorted_tag_labels = sorted(tag_counts.keys(), key=lambda x: tag_counts[x], reverse=True)
    tag_chart_labels = [f"{t[0]} {t[1]}" for t in sorted_tag_labels]
    tag_chart_values = [tag_counts[t] for t in sorted_tag_labels]
    cat_labels = ["Format", "Style", "Linguistic", "Number", "Content"]
    cat_values = [cat_counts[c] for c in cat_labels]
    count_labels = sorted(count_dist.keys())
    count_values = [count_dist[k] for k in count_labels]
    easy_cases = sum(v for k, v in count_dist.items() if k <= 3)
    hard_cases = sum(v for k, v in count_dist.items() if k >= 4)
    l2_sorted = sorted(l2_case_count.keys())
    l2_labels = l2_sorted
    l2_values = [l2_case_count[k] for k in l2_sorted]

    static_data = {
        "total": total_constraints,
        "hard": hard_count,
        "soft": soft_count,
        "tag_labels": tag_chart_labels,
        "tag_values": tag_chart_values,
        "cat_labels": cat_labels,
        "cat_values": cat_values,
        "tier_counts": [tier_case_count.get(t, 0) for t in ["T1", "T2", "T3"]],
        "l2_labels": l2_labels,
        "l2_values": l2_values,
        "count_labels": [f"{k} 条" for k in count_labels],
        "count_keys": count_labels,
        "count_values": count_values,
        "easy_cases": easy_cases,
        "hard_cases": hard_cases,
    }

    data_json = json.dumps({"static": static_data, "analytics": analytics}, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)

    out_path = os.path.join(SCRIPT_DIR, "benchmark_stats.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {out_path}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FinIF Benchmark 数据统计 & 模型分析</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #0f172a; color: #e2e8f0; min-height: 100vh;
}
.header {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-bottom: 1px solid #334155; padding: 32px 48px;
  display: flex; justify-content: space-between; align-items: center;
}
.header h1 { font-size: 28px; font-weight: 700; color: #f1f5f9; }
.header p { margin-top: 8px; font-size: 15px; color: #94a3b8; }
.header .nav-btn {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: #fff;
  border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px;
  cursor: pointer; font-weight: 600; text-decoration: none; white-space: nowrap;
}
.header .nav-btn:hover { opacity: 0.9; }
.stats-bar {
  display: flex; gap: 16px; padding: 20px 48px;
  background: #1e293b; border-bottom: 1px solid #334155; flex-wrap: wrap;
}
.stat-card {
  background: #0f172a; border: 1px solid #334155; border-radius: 10px;
  padding: 16px 24px; min-width: 140px; text-align: center;
}
.stat-card .num {
  font-size: 32px; font-weight: 700;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.stat-card.flash .num { background: linear-gradient(135deg, #f97316, #f59e0b); -webkit-background-clip: text; }
.stat-card.pro .num { background: linear-gradient(135deg, #8b5cf6, #a78bfa); -webkit-background-clip: text; }
.stat-card.qwen .num { background: linear-gradient(135deg, #22c55e, #4ade80); -webkit-background-clip: text; }
.stat-card .label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
.section-title {
  font-size: 22px; font-weight: 700; color: #f1f5f9;
  padding: 32px 48px 0; display: flex; align-items: center; gap: 12px;
}
.section-title::before {
  content: ''; display: block; width: 4px; height: 24px;
  background: linear-gradient(180deg, #3b82f6, #8b5cf6); border-radius: 2px;
}
.grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px;
  padding: 24px 48px; max-width: 1400px; margin: 0 auto;
}
.card {
  background: #1e293b; border: 1px solid #334155; border-radius: 14px;
  padding: 24px; transition: border-color 0.2s;
}
.card:hover { border-color: #475569; }
.card.wide { grid-column: span 2; }
.card h2 {
  font-size: 16px; font-weight: 600; color: #f1f5f9; margin-bottom: 16px;
  display: flex; align-items: center; gap: 8px;
}
.card h2 .badge {
  font-size: 11px; background: #334155; color: #94a3b8;
  padding: 2px 8px; border-radius: 20px; font-weight: 500;
}
.chart-wrap { position: relative; width: 100%; }
.chart-wrap.pie { max-width: 320px; margin: 0 auto; }
.card .inner-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: center; }

/* Constraint table */
.table-controls { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.table-controls select, .table-controls input {
  background: #0f172a; border: 1px solid #334155; color: #e2e8f0;
  padding: 6px 12px; border-radius: 6px; font-size: 13px;
}
.con-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.con-table th {
  background: #0f172a; color: #94a3b8; padding: 10px 8px; text-align: left;
  border-bottom: 2px solid #334155; cursor: pointer; white-space: nowrap;
  user-select: none;
}
.con-table th:hover { color: #e2e8f0; }
.con-table td { padding: 8px; border-bottom: 1px solid #1e293b; }
.con-table tr:hover { background: #0f172a; }
.pass-true { color: #22c55e; font-weight: 600; }
.pass-false { color: #ef4444; font-weight: 600; }
.type-hard { background: #1e40af; color: #93c5fd; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.type-soft { background: #6b21a8; color: #d8b4fe; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.tag-badge { background: #334155; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 11px; }

@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; padding: 16px; }
  .card.wide { grid-column: span 1; }
  .stats-bar { padding: 16px; }
  .header { padding: 24px 16px; flex-direction: column; gap: 12px; }
  .inner-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>FinIF Benchmark 数据统计 & 模型分析</h1>
    <p>金融指令遵循评测基准 — 约束分布 + 五模型评测结果对比</p>
  </div>
  <a class="nav-btn" href="review_responses.html">查看模型回复详情 &rarr;</a>
</div>

<div class="stats-bar" id="stats-bar"></div>

<!-- ==================== Section 1: Constraint Distribution ==================== -->
<div class="section-title">约束体系分布</div>
<div class="grid" id="grid-dist">
  <div class="card wide">
    <h2>约束标签 (Tag) 分布 <span class="badge" id="tag-badge"></span></h2>
    <div class="chart-wrap"><canvas id="tagChart"></canvas></div>
  </div>
  <div class="card">
    <h2>约束大类分布 <span class="badge">5 categories</span></h2>
    <div class="inner-grid">
      <div class="chart-wrap pie"><canvas id="catPie"></canvas></div>
      <div id="catLegend" style="font-size:14px;line-height:2;"></div>
    </div>
  </div>
  <div class="card">
    <h2>Hard vs Soft & 难度分组</h2>
    <div class="inner-grid">
      <div class="chart-wrap pie"><canvas id="typePie"></canvas></div>
      <div class="chart-wrap pie"><canvas id="diffPie"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h2>L1 任务难度分布 <span class="badge">3 tiers</span></h2>
    <div class="inner-grid">
      <div class="chart-wrap pie"><canvas id="l1Pie"></canvas></div>
      <div id="l1Desc" style="font-size:13px;line-height:2.2;color:#cbd5e1;"></div>
    </div>
  </div>
  <div class="card">
    <h2>L2 任务子类分布 <span class="badge">11 subtypes</span></h2>
    <div class="chart-wrap"><canvas id="l2Bar"></canvas></div>
  </div>
  <div class="card wide">
    <h2>每 Case 约束数分布 <span class="badge" id="case-dist-badge"></span></h2>
    <div class="chart-wrap" style="max-width:700px;margin:0 auto;"><canvas id="perCaseBar"></canvas></div>
  </div>
</div>

<!-- ==================== Section 2: Model Performance ==================== -->
<div class="section-title">模型评测结果对比</div>
<div class="grid" id="grid-perf">
  <div class="card wide">
    <h2>各约束标签通过率 <span class="badge">按平均通过率升序</span></h2>
    <div class="chart-wrap"><canvas id="tagPassChart"></canvas></div>
  </div>
  <div class="card">
    <h2>约束大类通过率</h2>
    <div class="chart-wrap"><canvas id="catPassChart"></canvas></div>
  </div>
  <div class="card">
    <h2>Hard / Soft 通过率</h2>
    <div class="chart-wrap"><canvas id="typePassChart"></canvas></div>
  </div>
  <div class="card">
    <h2>L1 Tier 通过率</h2>
    <div class="chart-wrap"><canvas id="tierPassChart"></canvas></div>
  </div>
  <div class="card">
    <h2>Easy (1-3条) vs Hard (4-6条) 通过率</h2>
    <div class="chart-wrap"><canvas id="easyHardChart"></canvas></div>
  </div>
  <div class="card wide">
    <h2>L2 子类通过率</h2>
    <div class="chart-wrap"><canvas id="l2PassChart"></canvas></div>
  </div>
  <div class="card wide">
    <h2>逐条约束通过明细 <span class="badge" id="con-table-badge"></span></h2>
    <div class="table-controls">
      <select id="filter-tag"><option value="">全部标签</option></select>
      <select id="filter-type">
        <option value="">全部类型</option>
        <option value="hard">Hard</option>
        <option value="soft">Soft</option>
      </select>
      <select id="filter-status">
        <option value="">全部状态</option>
        <option value="both-pass">全部通过</option>
        <option value="both-fail">全部失败</option>
        <option value="diff">有差异</option>
      </select>
      <input type="text" id="filter-search" placeholder="搜索描述...">
    </div>
    <div style="max-height:600px;overflow-y:auto;">
      <table class="con-table" id="con-table">
        <thead>
          <tr>
            <th data-col="key">约束 ID</th>
            <th data-col="type">类型</th>
            <th data-col="tag">标签</th>
            <th data-col="description">描述</th>
            <th data-col="ds-v4-flash">Flash</th>
            <th data-col="ds-v4-flash-thinking">Flash-T</th>
            <th data-col="ds-v4-pro">Pro</th>
            <th data-col="ds-v4-pro-thinking">Pro-T</th>
            <th data-col="qwen3-8b">Qwen3-8B</th>
          </tr>
        </thead>
        <tbody id="con-tbody"></tbody>
      </table>
    </div>
  </div>
</div>

<div style="text-align:center;padding:40px;color:#475569;font-size:13px;">
  FinIF Benchmark — Auto-generated by build_stats.py
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;
const S = DATA.static;
const A = DATA.analytics;

Chart.register(ChartDataLabels);
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif';
Chart.defaults.plugins.datalabels.display = false;

const flashColor = '#f97316';
const flashThinkColor = '#fb923c';
const proColor = '#8b5cf6';
const proThinkColor = '#a78bfa';
const qwenColor = '#22c55e';
const modelColors = {'ds-v4-flash': flashColor, 'ds-v4-flash-thinking': flashThinkColor, 'ds-v4-pro': proColor, 'ds-v4-pro-thinking': proThinkColor, 'qwen3-8b': qwenColor};
const modelShort = {'ds-v4-flash': 'Flash', 'ds-v4-flash-thinking': 'Flash-Think', 'ds-v4-pro': 'Pro', 'ds-v4-pro-thinking': 'Pro-Think', 'qwen3-8b': 'Qwen3-8B'};
const models = A.models;
const catColorMap = {'C':'#ef4444','F':'#3b82f6','S':'#8b5cf6','N':'#f59e0b','L':'#22c55e'};
const catPalette = ['#3b82f6','#8b5cf6','#22c55e','#f59e0b','#ef4444'];
const T = S.total;

const pctLabel = {
  display: true, color: '#f1f5f9', font: { size: 13, weight: 'bold' },
  formatter: (val, ctx) => {
    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
    const pct = (val / total * 100).toFixed(1);
    return pct >= 5 ? pct + '%' : '';
  },
};

// ===== Stats bar =====
const statsBar = document.getElementById('stats-bar');
const baseCards = [
  ['100', 'Cases', ''],
  [T, 'IF 约束', ''],
  [S.hard, 'Hard', ''],
  [S.soft, 'Soft', ''],
];
models.forEach(m => {
  const ov = A.tier_scores[m].overall;
  baseCards.push([ov + '%', modelShort[m] + ' 通过率', m.includes('qwen') ? 'qwen' : m.includes('flash') ? 'flash' : 'pro']);
});
baseCards.forEach(([num, label, cls]) => {
  statsBar.innerHTML += `<div class="stat-card ${cls}"><div class="num">${num}</div><div class="label">${label}</div></div>`;
});

// ===== Section 1: Constraint Distribution =====

document.getElementById('tag-badge').textContent = `${S.tag_labels.length} tags / ${T} constraints`;

new Chart(document.getElementById('tagChart'), {
  type: 'bar',
  data: {
    labels: S.tag_labels,
    datasets: [{ data: S.tag_values, backgroundColor: S.tag_labels.map(l => catColorMap[l[0]] || '#6366f1'), borderRadius: 4, barThickness: 20 }]
  },
  options: {
    indexAxis: 'y', responsive: true,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `${ctx.raw} 约束 (${(ctx.raw/T*100).toFixed(1)}%)` } } },
    scales: { x: { grid: { color: '#1e293b' }, ticks: { stepSize: 10 } }, y: { grid: { display: false }, ticks: { font: { size: 12 } } } }
  }
});

new Chart(document.getElementById('catPie'), {
  type: 'doughnut',
  data: { labels: S.cat_labels, datasets: [{ data: S.cat_values, backgroundColor: catPalette, borderWidth: 0 }] },
  options: { responsive: true, cutout: '55%', plugins: { legend: { display: false }, datalabels: pctLabel } }
});
const legendDiv = document.getElementById('catLegend');
S.cat_labels.forEach((l, i) => {
  legendDiv.innerHTML += `<div><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:${catPalette[i]};margin-right:8px;vertical-align:middle;"></span>${l} <span style="color:#64748b">${S.cat_values[i]} (${(S.cat_values[i]/T*100).toFixed(0)}%)</span></div>`;
});

new Chart(document.getElementById('typePie'), {
  type: 'doughnut',
  data: { labels: [`Hard (${S.hard})`, `Soft (${S.soft})`], datasets: [{ data: [S.hard, S.soft], backgroundColor: ['#3b82f6','#8b5cf6'], borderWidth: 0 }] },
  options: { responsive: true, cutout: '50%', plugins: { legend: { position: 'bottom', labels: { padding: 12, font: { size: 12 } } }, title: { display: true, text: 'Hard vs Soft', color: '#cbd5e1', font: { size: 13 } }, datalabels: pctLabel } }
});

const easyCases = S.easy_cases, hardCases = S.hard_cases;
new Chart(document.getElementById('diffPie'), {
  type: 'doughnut',
  data: { labels: [`Easy 1-3条 (${easyCases})`, `Hard 4-6条 (${hardCases})`], datasets: [{ data: [easyCases, hardCases], backgroundColor: ['#22c55e','#ef4444'], borderWidth: 0 }] },
  options: { responsive: true, cutout: '50%', plugins: { legend: { position: 'bottom', labels: { padding: 12, font: { size: 12 } } }, title: { display: true, text: '难度分组', color: '#cbd5e1', font: { size: 13 } }, datalabels: pctLabel } }
});

new Chart(document.getElementById('l1Pie'), {
  type: 'doughnut',
  data: { labels: ['T1 基础提取与计算', 'T2 综合分析', 'T3 复杂推理与验证'], datasets: [{ data: S.tier_counts, backgroundColor: ['#3b82f6','#f59e0b','#ef4444'], borderWidth: 0 }] },
  options: { responsive: true, cutout: '50%', plugins: { legend: { display: false }, datalabels: pctLabel } }
});
const l1Desc = document.getElementById('l1Desc');
[['T1', '基础提取与计算', S.tier_counts[0], '#3b82f6', '数据提取、四则运算、结构化输出'],
 ['T2', '综合分析', S.tier_counts[1], '#f59e0b', '多维分析、趋势研判、风险评估'],
 ['T3', '复杂推理与验证', S.tier_counts[2], '#ef4444', '异常审查、跨期核验、报告撰写']
].forEach(([id, name, n, color, desc]) => {
  l1Desc.innerHTML += `<div style="margin-bottom:8px;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${color};margin-right:6px;vertical-align:middle;"></span><strong style="color:#f1f5f9">${id}</strong> ${name} <span style="color:#64748b">(${n})</span><div style="font-size:12px;color:#64748b;margin-left:18px;">${desc}</div></div>`;
});

const l2Names = ['行情数据提取计算','财务比率计算','字段提取结构化','多维综合分析','竞争优势评估','时序趋势研判','风险指标计算','高格式密度','数据异常审查','专业报告撰写','跨表一致性核验'];
new Chart(document.getElementById('l2Bar'), {
  type: 'bar',
  data: {
    labels: S.l2_labels,
    datasets: [{ data: S.l2_values, backgroundColor: S.l2_labels.map(l => l.startsWith('T1') ? '#3b82f6' : l.startsWith('T2') ? '#f59e0b' : '#ef4444'), borderRadius: 6, barThickness: 28 }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false }, tooltip: { callbacks: { title: ctx => `${ctx[0].label} — ${l2Names[ctx[0].dataIndex] || ''}`, label: ctx => `${ctx.raw} cases` } } },
    scales: { y: { beginAtZero: true, grid: { color: '#1e293b' }, ticks: { stepSize: 5 } }, x: { grid: { display: false }, ticks: { font: { size: 12 } } } }
  }
});

document.getElementById('case-dist-badge').textContent = `avg = ${(T / 100).toFixed(1)} / Easy ${easyCases} / Hard ${hardCases}`;
new Chart(document.getElementById('perCaseBar'), {
  type: 'bar',
  data: {
    labels: S.count_labels,
    datasets: [{ data: S.count_values, backgroundColor: S.count_keys.map(k => k <= 3 ? '#22c55e' : '#ef4444'), borderRadius: 6, barThickness: 56 }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false }, datalabels: { display: true, color: '#f1f5f9', anchor: 'end', align: 'end', font: { size: 14, weight: 'bold' }, formatter: v => v } },
    scales: { y: { beginAtZero: true, max: Math.max(...S.count_values) + 5, grid: { color: '#1e293b' }, ticks: { stepSize: 5 } }, x: { grid: { display: false } } }
  }
});

// ===== Section 2: Model Performance =====

function groupedBar(canvasId, labels, modelDataMap, opts = {}) {
  const datasets = models.map(m => ({
    label: modelShort[m], data: modelDataMap[m], backgroundColor: modelColors[m], borderRadius: 4, barPercentage: 0.7,
  }));
  new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      indexAxis: opts.horizontal ? 'y' : 'x',
      responsive: true,
      plugins: {
        legend: { position: 'top', labels: { padding: 12, font: { size: 12 } } },
        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw}%` } },
        datalabels: {
          display: opts.showLabels !== false,
          color: '#f1f5f9', font: { size: 10, weight: 'bold' },
          anchor: opts.horizontal ? 'end' : 'end',
          align: opts.horizontal ? 'end' : 'end',
          formatter: v => v + '%',
        }
      },
      scales: {
        [opts.horizontal ? 'x' : 'y']: { beginAtZero: true, max: 100, grid: { color: '#1e293b' }, ticks: { callback: v => v + '%' } },
        [opts.horizontal ? 'y' : 'x']: { grid: { display: false }, ticks: { font: { size: 12 } } }
      }
    }
  });
}

// Tag pass rates
const tagModelData = {};
models.forEach(m => { tagModelData[m] = A.tag_pass_rates[m]; });
groupedBar('tagPassChart', A.tag_pass_rates.labels, tagModelData, { horizontal: true, showLabels: false });

// Category pass rates
const catOrder = ['Format','Style','Linguistic','Number','Content'];
const catModelData = {};
models.forEach(m => { catModelData[m] = catOrder.map(c => A.cat_pass_rates[c][m]); });
groupedBar('catPassChart', catOrder, catModelData);

// Hard/Soft pass rates
const typeModelData = {};
models.forEach(m => { typeModelData[m] = [A.type_pass_rates.hard[m], A.type_pass_rates.soft[m]]; });
groupedBar('typePassChart',
  [`Hard (${A.type_pass_rates.hard.count})`, `Soft (${A.type_pass_rates.soft.count})`],
  typeModelData
);

// Tier pass rates
const tiers = ['T1', 'T2', 'T3'];
const tierModelData = {};
models.forEach(m => { tierModelData[m] = tiers.map(t => A.tier_scores[m][t]); });
groupedBar('tierPassChart', tiers, tierModelData);

// Easy/Hard pass rates
const ehModelData = {};
models.forEach(m => { ehModelData[m] = [A.easy_hard_pass_rates.easy[m], A.easy_hard_pass_rates.hard[m]]; });
groupedBar('easyHardChart',
  [`Easy 1-3条 (${A.easy_hard_pass_rates.easy.count}约束)`, `Hard 4-6条 (${A.easy_hard_pass_rates.hard.count}约束)`],
  ehModelData
);

// L2 pass rates
const l2Keys = Object.keys(A.l2_pass_rates).sort();
const l2ModelData = {};
models.forEach(m => { l2ModelData[m] = l2Keys.map(k => A.l2_pass_rates[k][m]); });
groupedBar('l2PassChart', l2Keys, l2ModelData);

// ===== Constraint Table =====
const tbody = document.getElementById('con-tbody');
const tableData = A.constraint_table;

document.getElementById('con-table-badge').textContent = `${tableData.length} 条约束`;

const tagSelect = document.getElementById('filter-tag');
const tags = [...new Set(tableData.map(r => r.tag))].sort();
tags.forEach(t => { tagSelect.innerHTML += `<option value="${t}">${t} ${tableData.find(r => r.tag === t)?.tag_name || ''}</option>`; });

function renderTable() {
  const tagF = document.getElementById('filter-tag').value;
  const typeF = document.getElementById('filter-type').value;
  const statusF = document.getElementById('filter-status').value;
  const searchF = document.getElementById('filter-search').value.toLowerCase();

  let rows = tableData.filter(r => {
    if (tagF && r.tag !== tagF) return false;
    if (typeF && r.type !== typeF) return false;
    if (searchF && !r.description.toLowerCase().includes(searchF) && !r.key.toLowerCase().includes(searchF)) return false;
    const allPass = models.every(m => r[m]);
    const allFail = models.every(m => !r[m]);
    const hasDiff = !allPass && !allFail;
    if (statusF === 'both-pass' && !allPass) return false;
    if (statusF === 'both-fail' && !allFail) return false;
    if (statusF === 'diff' && !hasDiff) return false;
    return true;
  });

  if (currentSort) {
    rows.sort((a, b) => {
      let va = a[currentSort.col], vb = b[currentSort.col];
      if (typeof va === 'boolean') { va = va ? 1 : 0; vb = vb ? 1 : 0; }
      if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
      return currentSort.asc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
  }

  tbody.innerHTML = rows.map(r => {
    const modelCells = models.map(m =>
      `<td class="${r[m] ? 'pass-true' : 'pass-false'}">${r[m] ? 'PASS' : 'FAIL'}</td>`
    ).join('');
    return `<tr>
    <td style="font-size:12px;color:#94a3b8;white-space:nowrap">${r.key}</td>
    <td><span class="type-${r.type}">${r.type}</span></td>
    <td><span class="tag-badge">${r.tag}</span></td>
    <td>${r.description}</td>
    ${modelCells}
  </tr>`;
  }).join('');
}

let currentSort = null;
document.querySelectorAll('.con-table th').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (currentSort && currentSort.col === col) currentSort.asc = !currentSort.asc;
    else currentSort = { col, asc: true };
    renderTable();
  });
});

document.getElementById('filter-tag').addEventListener('change', renderTable);
document.getElementById('filter-type').addEventListener('change', renderTable);
document.getElementById('filter-status').addEventListener('change', renderTable);
document.getElementById('filter-search').addEventListener('input', renderTable);

renderTable();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
