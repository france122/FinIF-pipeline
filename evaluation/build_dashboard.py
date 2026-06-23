#!/usr/bin/env python3
"""Build a self-contained FinIF benchmark dashboard (single HTML file)."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMILY_ORDER = [
    "Format and Presentation",
    "Evidence and Grounding",
    "Quantitative Verification",
    "Required Content Coverage",
    "Decision and Boundary",
]


def compute_stats(items):
    constraints = [c for it in items for c in it["constraints"]]
    n_items = len(items)
    n_c = len(constraints)
    by_tag = Counter(c["tag"] for c in constraints)
    by_workflow = Counter(it["workflow"] for it in items)
    by_task = Counter(it["task"] for it in items)
    route = Counter(c["route"] for c in constraints)
    fam_route = defaultdict(lambda: {"rule": 0, "judge": 0})
    for c in constraints:
        fam_route[c["family"]][c["route"]] += 1
    wf_route = defaultdict(lambda: {"rule": 0, "judge": 0})
    for it in items:
        for c in it["constraints"]:
            wf_route[it["workflow"]][c["route"]] += 1
    judge_docs = sum(1 for c in constraints if c.get("judge_uses_docs"))
    return {
        "n_items": n_items,
        "n_constraints": n_c,
        "n_workflows": len(by_workflow),
        "n_tasks": len(by_task),
        "avg_c_per_item": round(n_c / n_items, 2) if n_items else 0,
        "route": {"rule": route.get("rule", 0), "judge": route.get("judge", 0)},
        "by_tag": dict(by_tag.most_common()),
        "by_workflow": dict(by_workflow),
        "fam_route": {k: dict(v) for k, v in fam_route.items()},
        "wf_route": {k: dict(v) for k, v in wf_route.items()},
        "judge_docs": judge_docs,
    }


def normalize_constraint(raw):
    check_type = raw.get("check_type") or ""
    route = "rule" if check_type == "rule" else "judge"
    return {
        "tag": raw.get("tag", ""),
        "constraint": raw.get("constraint", ""),
        "family": raw.get("family", ""),
        "route": route,
        "judge_uses_docs": bool(raw.get("judge_uses_docs")),
    }


def load_benchmark_items(path: Path):
    items = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for item in items:
        out.append(
            {
                "id": item.get("id", ""),
                "workflow": item.get("workflow", ""),
                "task": item.get("task", ""),
                "work_product": item.get("work_product", ""),
                "query": item.get("query", ""),
                "full_prompt": item.get("full_prompt", ""),
                "documents": item.get("documents", []),
                "constraints": item.get("constraints", []),
            }
        )
    return out


def load_train_items(path: Path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        constraints = [normalize_constraint(c) for c in item.get("extracted_constraints", [])]
        documents = []
        for doc in item.get("source_registry", []):
            documents.append(
                {
                    "id": doc.get("source_id", ""),
                    "label": doc.get("prompt_label", ""),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                }
            )
        out.append(
            {
                "id": item.get("id", ""),
                "workflow": item.get("workflow", ""),
                "task": item.get("task", ""),
                "work_product": item.get("work_product", ""),
                "query": item.get("query", ""),
                "full_prompt": item.get("full_prompt", ""),
                "documents": documents,
                "constraints": constraints,
            }
        )
    return out

HTML=r"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>FinIF Benchmark Dashboard</title>
<style>
:root{--bg:#0e1117;--panel:#161b22;--panel2:#1c2330;--border:#2a3340;--fg:#e6edf3;--muted:#8b98a9;--accent:#58a6ff;--rule:#3fb950;--judge:#d29922;--chip:#21262d;}
*{box-sizing:border-box;}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;}
header{padding:18px 26px;border-bottom:1px solid var(--border);background:var(--panel);position:sticky;top:0;z-index:10;}
header h1{margin:0;font-size:18px;font-weight:650;}header .sub{color:var(--muted);font-size:12.5px;margin-top:3px;}
.dataset-switch{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
.dataset-btn{padding:7px 12px;background:var(--chip);border:1px solid var(--border);border-radius:999px;cursor:pointer;font-size:12.5px;color:var(--muted);}
.dataset-btn.active{color:var(--fg);border-color:var(--accent);background:rgba(88,166,255,.12);}
.wrap{max-width:1280px;margin:0 auto;padding:20px 26px 60px;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px;}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px;}
.card .v{font-size:24px;font-weight:680;}.card .l{color:var(--muted);font-size:12px;margin-top:2px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;}@media(max-width:900px){.grid2{grid-template-columns:1fr;}}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin-bottom:18px;}
.panel h2{margin:0 0 14px;font-size:14px;font-weight:620;}.panel h2 .hint{color:var(--muted);font-weight:400;font-size:11.5px;}
.bar-row{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:12.5px;}
.bar-row .name{width:210px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.bar-row .name.sm{width:78px;}.bar{flex:1;height:18px;background:var(--chip);border-radius:5px;overflow:hidden;display:flex;}
.bar .seg{height:100%;}.bar .seg.rule{background:var(--rule);}.bar .seg.judge{background:var(--judge);}.bar .seg.solid{background:var(--accent);}
.bar-row .num{width:108px;text-align:right;color:var(--muted);flex-shrink:0;font-variant-numeric:tabular-nums;}
.legend{display:flex;gap:16px;margin-bottom:10px;font-size:12px;color:var(--muted);}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px;}
.tabs{display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;}
.tab{padding:7px 14px;background:var(--panel);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;color:var(--muted);}
.tab.active{color:var(--fg);border-color:var(--accent);background:var(--panel2);}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;align-items:center;}
select,input[type=text]{background:var(--panel2);color:var(--fg);border:1px solid var(--border);border-radius:7px;padding:7px 10px;font-size:13px;}
input[type=text]{min-width:240px;}
.item{background:var(--panel);border:1px solid var(--border);border-radius:10px;margin-bottom:12px;overflow:hidden;}
.item-head{padding:12px 16px;cursor:pointer;display:flex;gap:12px;align-items:center;}.item-head:hover{background:var(--panel2);}
.item-head .wf{font-size:11px;color:var(--accent);background:rgba(88,166,255,.1);padding:2px 8px;border-radius:5px;white-space:nowrap;}
.item-head .task{font-size:11px;color:var(--muted);}.item-head .q{flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.item-head .meta{font-size:11.5px;color:var(--muted);white-space:nowrap;}
.pill{font-size:10.5px;padding:1px 7px;border-radius:9px;margin-left:5px;}.pill.rule{background:rgba(63,185,80,.15);color:var(--rule);}.pill.judge{background:rgba(210,153,34,.15);color:var(--judge);}
.item-body{display:none;padding:0 16px 16px;border-top:1px solid var(--border);}.item.open .item-body{display:block;}
.sec{margin-top:14px;}.sec h4{margin:0 0 7px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}
.doc{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:9px 12px;margin:6px 0;font-size:12.5px;}
.doc .dt{color:var(--accent);font-weight:600;font-size:11.5px;}.doc .lab{color:var(--judge);}
.query-box{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:12.5px;white-space:pre-wrap;}
.query-box.prompt{max-height:420px;overflow:auto;font-family:ui-monospace,Menlo,monospace;font-size:12px;line-height:1.6;}
table.cons{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px;}
table.cons th{text-align:left;color:var(--muted);font-weight:500;padding:6px 8px;border-bottom:1px solid var(--border);font-size:11px;}
table.cons td{padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top;}table.cons tr:last-child td{border-bottom:none;}
.tag{font-family:ui-monospace,monospace;font-size:11px;color:var(--accent);}
.badge{font-size:10px;padding:1px 6px;border-radius:5px;white-space:nowrap;}.badge.rule{background:rgba(63,185,80,.15);color:var(--rule);}.badge.judge{background:rgba(210,153,34,.15);color:var(--judge);}.badge.docs{background:rgba(88,166,255,.15);color:var(--accent);margin-left:4px;}
.fam{font-size:11px;color:var(--muted);}.hide{display:none!important;}.count{color:var(--muted);font-size:12.5px;margin-bottom:10px;}
</style></head><body>
<header><h1>FinIF Benchmark Dashboard</h1><div class="sub" id="subtitle"></div><div class="dataset-switch" id="datasetSwitch"></div></header>
<div class="wrap">
<div class="tabs"><div class="tab active" data-tab="overview">总览 Overview</div><div class="tab" data-tab="browse">浏览数据 Browse</div></div>
<div id="tab-overview">
<div class="cards" id="cards"></div>
<div class="grid2">
<div class="panel"><h2>约束按 Family 分布 <span class="hint">/ 规则 vs Judge</span></h2><div class="legend"><span><i style="background:var(--rule)"></i>规则</span><span><i style="background:var(--judge)"></i>Judge</span></div><div id="famRoute"></div></div>
<div class="panel"><h2>Workflow 分布 <span class="hint">/ 规则 vs Judge</span></h2><div class="legend"><span><i style="background:var(--rule)"></i>规则</span><span><i style="background:var(--judge)"></i>Judge</span></div><div id="wfRoute"></div></div>
</div>
<div class="panel"><h2>约束 Tag 分布</h2><div id="tagDist"></div></div>
</div>
<div id="tab-browse" class="hide">
<div class="filters">
<select id="fWorkflow"><option value="">全部 Workflow</option></select>
<select id="fFamily"><option value="">全部 Family</option></select>
<select id="fRoute"><option value="">全部路由</option><option value="rule">仅规则</option><option value="judge">仅 Judge</option></select>
<input type="text" id="fSearch" placeholder="搜索 query / 约束文本…"></div>
<div class="count" id="browseCount"></div><div id="itemList"></div>
</div></div>
<script>
const DATASETS=__DATASETS__;const FAM_ORDER=__FAMORDER__;
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function stackedRow(name,rule,judge){const tot=rule+judge,rr=tot?100*rule/tot:0,jj=tot?100*judge/tot:0;return `<div class="bar-row"><div class="name" title="${esc(name)}">${esc(name)}</div><div class="bar"><div class="seg rule" style="width:${rr}%"></div><div class="seg judge" style="width:${jj}%"></div></div><div class="num">${rule} / ${judge}</div></div>`;}
function solidRow(name,val,max){const w=max?100*val/max:0;return `<div class="bar-row"><div class="name sm">${esc(name)}</div><div class="bar"><div class="seg solid" style="width:${w}%"></div></div><div class="num">${val}</div></div>`;}
document.querySelectorAll('.tab').forEach(tab=>{tab.onclick=()=>{document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));tab.classList.add('active');const id=tab.dataset.tab;document.getElementById('tab-overview').classList.toggle('hide',id!=='overview');document.getElementById('tab-browse').classList.toggle('hide',id!=='browse');if(id==='browse')renderBrowse();};});
const fWorkflow=document.getElementById('fWorkflow'),fFamily=document.getElementById('fFamily'),fRoute=document.getElementById('fRoute'),fSearch=document.getElementById('fSearch');
FAM_ORDER.forEach(f=>fFamily.add(new Option(f,f)));
[fWorkflow,fFamily,fRoute].forEach(el=>el.onchange=renderBrowse);
let st;fSearch.oninput=()=>{clearTimeout(st);st=setTimeout(renderBrowse,180);};
let currentKey=Object.keys(DATASETS)[0];
function currentDataset(){return DATASETS[currentKey];}
function renderDatasetSwitch(){const wrap=document.getElementById('datasetSwitch');wrap.innerHTML='';for(const [key,ds] of Object.entries(DATASETS)){const btn=document.createElement('button');btn.className='dataset-btn'+(key===currentKey?' active':'');btn.textContent=ds.label;btn.onclick=()=>{currentKey=key;renderAll();};wrap.appendChild(btn);}}
function renderFilters(){const data=currentDataset().items;const priorWorkflow=fWorkflow.value;fWorkflow.innerHTML='<option value="">全部 Workflow</option>';[...new Set(data.map(d=>d.workflow))].sort().forEach(w=>fWorkflow.add(new Option(w,w)));if([...fWorkflow.options].some(o=>o.value===priorWorkflow))fWorkflow.value=priorWorkflow;}
function renderOverview(){const ds=currentDataset();const stats=ds.stats;document.getElementById('subtitle').textContent=`${ds.label} · ${ds.description} · ${stats.n_items} cases · ${stats.n_constraints} IF constraints · ${stats.n_workflows} workflows · ${stats.n_tasks} tasks · ${stats.avg_c_per_item}/case`;const rp=stats.n_constraints?(100*stats.route.rule/stats.n_constraints).toFixed(1):'0.0',jp=stats.n_constraints?(100*stats.route.judge/stats.n_constraints).toFixed(1):'0.0';const cards=[['Cases',stats.n_items],['IF Constraints',stats.n_constraints],['约束/case',stats.avg_c_per_item],['规则直判',`${stats.route.rule||0} (${rp}%)`],['LLM Judge',`${stats.route.judge||0} (${jp}%)`],['Judge带原文',stats.judge_docs]];document.getElementById('cards').innerHTML=cards.map(([l,v])=>`<div class="card"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');document.getElementById('famRoute').innerHTML=FAM_ORDER.filter(f=>stats.fam_route[f]).map(f=>{const r=stats.fam_route[f];return stackedRow(f,r.rule||0,r.judge||0);}).join('');document.getElementById('wfRoute').innerHTML=Object.keys(stats.wf_route).map(w=>{const r=stats.wf_route[w];return stackedRow(w,r.rule||0,r.judge||0);}).join('');const tags=Object.entries(stats.by_tag);const tagMax=tags.length?Math.max(...tags.map(([,v])=>v)):0;document.getElementById('tagDist').innerHTML=tags.map(([t,v])=>solidRow(t,v,tagMax)).join('');}
function renderBrowse(){const data=currentDataset().items;const wf=fWorkflow.value,fam=fFamily.value,rt=fRoute.value,q=fSearch.value.trim().toLowerCase();const list=document.getElementById('itemList');list.innerHTML='';let shown=0;
for(const it of data){if(wf&&it.workflow!==wf)continue;let cons=it.constraints;if(fam)cons=cons.filter(c=>c.family===fam);if(rt)cons=cons.filter(c=>c.route===rt);if((fam||rt)&&!cons.length)continue;
if(q){const hay=(it.query+' '+it.constraints.map(c=>c.constraint).join(' ')).toLowerCase();if(!hay.includes(q))continue;}shown++;
const nr=it.constraints.filter(c=>c.route==='rule').length,nj=it.constraints.length-nr;const el=document.createElement('div');el.className='item';
el.innerHTML=`<div class="item-head"><span class="wf">${esc(it.workflow)}</span><span class="task">${esc(it.task)}</span><span class="q">${esc(it.query)}</span><span class="meta">${it.constraints.length}约束<span class="pill rule">${nr}规则</span><span class="pill judge">${nj}judge</span></span></div>
<div class="item-body"><div class="sec"><h4>Query</h4><div class="query-box">${esc(it.query)}</div></div>
<div class="sec"><h4>Full Prompt <span style="text-transform:none;color:var(--muted)">（${it.full_prompt.length}字符）</span></h4><div class="query-box prompt">${esc(it.full_prompt)}</div></div>
<div class="sec"><h4>源文档 (${it.documents.length})</h4>${it.documents.map(d=>`<div class="doc"><div class="dt">${esc(d.id)}${d.label?' · <span class="lab">「'+esc(d.label)+'」</span>':''} — ${esc(d.title)}</div>${esc(d.content)}</div>`).join('')}</div>
<div class="sec"><h4>约束 (${it.constraints.length})</h4><table class="cons"><thead><tr><th style="width:54px">Tag</th><th>约束</th><th style="width:150px">Family</th><th style="width:120px">路由</th></tr></thead><tbody>${it.constraints.map(c=>`<tr><td><span class="tag">${esc(c.tag)}</span></td><td>${esc(c.constraint)}</td><td class="fam">${esc(c.family)}</td><td><span class="badge ${c.route}">${c.route==='rule'?'规则':'Judge'}</span>${c.judge_uses_docs?'<span class="badge docs">带原文</span>':''}</td></tr>`).join('')}</tbody></table></div></div>`;
el.querySelector('.item-head').onclick=()=>el.classList.toggle('open');list.appendChild(el);}
document.getElementById('browseCount').textContent=`显示 ${shown} / ${data.length} cases`;}
function renderAll(){renderDatasetSwitch();renderFilters();renderOverview();renderBrowse();}
renderAll();
</script></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("outputs/benchmark/_dashboard_data.json"))
    ap.add_argument(
        "--train-data",
        type=Path,
        default=Path(
            "outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl"
        ),
    )
    ap.add_argument("--output", type=Path, default=Path("outputs/benchmark/dashboard.html"))
    ap.add_argument("--benchmark-label", default="Benchmark Hard300")
    ap.add_argument("--benchmark-description", default="正式 hard300 IF-clean benchmark")
    ap.add_argument("--train-label", default="Train764")
    ap.add_argument("--train-description", default="训练池，排除 hard300 后的 IF-clean train set")
    args = ap.parse_args()
    benchmark_items = load_benchmark_items(args.data)
    train_items = load_train_items(args.train_data)
    datasets = {
        "benchmark_hard300": {
            "label": args.benchmark_label,
            "description": args.benchmark_description,
            "items": benchmark_items,
            "stats": compute_stats(benchmark_items),
        },
        "train764": {
            "label": args.train_label,
            "description": args.train_description,
            "items": train_items,
            "stats": compute_stats(train_items),
        },
    }
    html = (
        HTML.replace("__DATASETS__", json.dumps(datasets, ensure_ascii=False))
        .replace("__FAMORDER__", json.dumps(FAMILY_ORDER, ensure_ascii=False))
    )
    args.output.write_text(html, encoding="utf-8")
    print(f"wrote {args.output} ({len(html)/1024/1024:.2f} MB)")

if __name__=="__main__":
    main()
