#!/usr/bin/env python3
"""FinIF SFT Training Data Viewer"""

import json, os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from collections import Counter

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_data():
    samples = []
    with open(os.path.join(PIPELINE_DIR, "data", "samples_raw.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def build_api_data(samples):
    l1_counter = Counter()
    l2_counter = Counter()
    variant_counter = Counter()
    constraint_counter = Counter()
    type_counter = Counter()

    for s in samples:
        l1_counter[s["L1"]] += 1
        l2_counter[s["L2"]] += 1
        variant_counter[s.get("variant_type", "")] += 1
        for c in s["constraints"]:
            constraint_counter[c["id"]] += 1
            type_counter[c["type"]] += 1

    stats = {
        "total": len(samples),
        "avg_constraints": round(sum(s["n_constraints"] for s in samples) / len(samples), 1),
        "avg_general": round(sum(s.get("n_general", 0) for s in samples) / len(samples), 1),
        "avg_financial_soft": round(sum(s.get("n_financial_soft", 0) for s in samples) / len(samples), 1),
        "avg_hidden": round(sum(s.get("n_hidden_checkers", 0) for s in samples) / len(samples), 1),
        "by_l1": dict(sorted(l1_counter.items())),
        "by_l2": dict(sorted(l2_counter.items())),
        "by_variant": dict(sorted(variant_counter.items())),
        "by_constraint": dict(sorted(constraint_counter.items())),
        "hard_total": sum(1 for s in samples for c in s["constraints"] if c["type"] == "hard"),
        "soft_total": sum(1 for s in samples for c in s["constraints"] if c["type"] == "soft"),
    }

    items = []
    for s in samples:
        items.append({
            "sample_id": s["sample_id"],
            "case_id": s["case_id"],
            "L1": s["L1"],
            "L2": s["L2"],
            "variant_type": s.get("variant_type", ""),
            "n_constraints": s["n_constraints"],
            "n_general": s.get("n_general", 0),
            "n_financial_soft": s.get("n_financial_soft", 0),
            "n_hidden_checkers": s.get("n_hidden_checkers", 0),
            "context_text": s["context_text"],
            "query_text": s["query_text"],
            "constraints": s["constraints"],
            "prompt": s["prompt"],
        })

    return {"stats": stats, "samples": items}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FinIF SFT Training Data Viewer</title>
<style>
:root{--bg:#0f1117;--card:#1a1a2e;--border:#2a2a4a;--accent:#7eb8ff;--green:#4ade80;--red:#f87171;--yellow:#facc15;--text:#e0e0e0;--muted:#888}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text)}

.header{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:18px 28px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:20px;color:#fff}
.header .sub{color:var(--muted);font-size:12px}

.container{max-width:1500px;margin:0 auto;padding:20px}
.sec{margin-bottom:24px}
.sec h2{font-size:15px;margin-bottom:8px;color:#ccc;border-left:3px solid var(--accent);padding-left:8px}

.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:12px;text-align:center}
.stat-card .num{font-size:24px;font-weight:700;color:var(--accent)}
.stat-card .lbl{font-size:11px;color:var(--muted);margin-top:3px}

.bar-chart{display:flex;gap:6px;align-items:end;height:100px;margin:10px 0;padding:0 4px}
.bar-item{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px}
.bar{background:var(--accent);border-radius:3px 3px 0 0;min-height:4px;width:100%;opacity:.8}
.bar-lbl{font-size:9px;color:var(--muted);writing-mode:vertical-rl;text-orientation:mixed;max-height:60px;overflow:hidden}
.bar-val{font-size:10px;color:#aaa}

table.dt{width:100%;border-collapse:collapse;background:var(--card);border-radius:6px;overflow:hidden;font-size:13px}
table.dt th{background:#222244;padding:7px 12px;text-align:left;color:#aaa;font-size:11px;text-transform:uppercase;cursor:pointer}
table.dt td{padding:7px 12px;border-top:1px solid var(--border)}
table.dt tr:hover{background:#222244}

.filters{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.fbtn{padding:4px 12px;border-radius:16px;border:1px solid var(--border);background:transparent;color:#aaa;cursor:pointer;font-size:12px;transition:all .15s}
.fbtn:hover{border-color:var(--accent);color:var(--accent)}
.fbtn.active{background:var(--accent);color:var(--bg);border-color:var(--accent);font-weight:600}
.sbox{padding:4px 10px;border-radius:16px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:12px;width:180px}

.clist{display:flex;flex-direction:column;gap:4px;max-height:500px;overflow-y:auto}
.citem{background:var(--card);border:1px solid var(--border);border-radius:5px;padding:8px 14px;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:10px;font-size:12px}
.citem:hover,.citem.sel{border-color:var(--accent);background:#1e1e36}
.sid{font-weight:700;color:var(--accent);min-width:160px;font-size:11px;font-family:monospace}
.tbadge{font-size:10px;padding:1px 5px;border-radius:3px;font-weight:600}
.tT1{background:#1e3a5f;color:#60a5fa}.tT2{background:#3b2f0a;color:#fbbf24}.tT3{background:#3b1c1c;color:#f87171}
.vbadge{font-size:10px;padding:1px 5px;border-radius:3px;background:#1b2e1b;color:#86efac}
.cbadge{font-size:10px;padding:1px 5px;border-radius:3px;background:#2d1b69;color:#a78bfa}
.cdesc{flex:1;font-size:11px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

.dpanel{display:none;margin-top:18px}
.dpanel.vis{display:block}
.dbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.dbar h2{font-size:17px;color:#fff}
.closeb{padding:3px 8px;border-radius:3px;border:1px solid var(--border);background:transparent;color:#aaa;cursor:pointer;font-size:12px}
.closeb:hover{border-color:var(--red);color:var(--red)}

.navbtns{display:flex;gap:6px}
.navb{padding:3px 10px;border-radius:3px;border:1px solid var(--border);background:transparent;color:#aaa;cursor:pointer;font-size:12px}
.navb:hover{border-color:var(--accent);color:var(--accent)}

.tabs{display:flex;gap:2px;margin-bottom:12px;border-bottom:1px solid var(--border)}
.tab{padding:6px 16px;cursor:pointer;color:var(--muted);font-size:13px;border-bottom:2px solid transparent;transition:all .15s}
.tab:hover{color:#ccc}.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tc{display:none}.tc.active{display:block}

.tblk{background:#12121e;border:1px solid var(--border);border-radius:5px;padding:12px;font-size:12px;line-height:1.8;white-space:pre-wrap;word-break:break-all;max-height:500px;overflow-y:auto}

.ctbl{width:100%;border-collapse:collapse;font-size:12px;background:#12121e;border-radius:5px;overflow:hidden}
.ctbl th{background:#1a1a2e;padding:5px 8px;text-align:left;color:#aaa;font-size:11px}
.ctbl td{padding:5px 8px;border-top:1px solid #1e1e2e;vertical-align:top}
.ctbl tr:hover{background:#1a1a2e}
.cht{color:var(--accent);font-weight:600}.chs{color:var(--green);font-weight:600}
</style>
</head>
<body>

<div class="header">
    <div><h1>FinIF SFT Training Data Viewer</h1><div class="sub" id="headerSub"></div></div>
</div>

<div class="container">
    <div class="sec">
        <h2>Overview</h2>
        <div class="stats-grid" id="statsGrid"></div>
    </div>
    <div class="sec">
        <h2>Constraint Distribution</h2>
        <div class="bar-chart" id="cDistChart"></div>
    </div>
    <div class="sec">
        <h2>Samples</h2>
        <div class="filters">
            <button class="fbtn active" data-f="all">All</button>
            <button class="fbtn" data-f="T1">T1</button>
            <button class="fbtn" data-f="T2">T2</button>
            <button class="fbtn" data-f="T3">T3</button>
            <input class="sbox" type="text" placeholder="Search case_id..." id="searchBox">
        </div>
        <div class="clist" id="sampleList"></div>
    </div>
    <div class="dpanel" id="dp">
        <div class="dbar">
            <h2 id="dTitle"></h2>
            <div style="display:flex;gap:8px">
                <div class="navbtns"><button class="navb" id="prevBtn">Prev</button><button class="navb" id="nextBtn">Next</button></div>
                <button class="closeb" id="closeBtn">Close</button>
            </div>
        </div>
        <div class="tabs" id="tabBar"></div>
        <div class="tc active" id="tc-context"><div class="tblk" id="contextBox"></div></div>
        <div class="tc" id="tc-query"><div class="tblk" id="queryBox"></div></div>
        <div class="tc" id="tc-constraints"><div id="constraintBox"></div></div>
        <div class="tc" id="tc-prompt"><div class="tblk" id="promptBox"></div></div>
    </div>
</div>

<script>
const D = __DATA__;
const S = D.stats;
let filter='all', search='', selIdx=-1;

const esc = s => { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; };

// Stats
document.getElementById('headerSub').textContent = `${S.total} samples | avg ${S.avg_constraints} constraints/sample`;
{
    const cards = [
        {n:S.total, l:'Total Samples'},
        {n:S.avg_constraints, l:'Avg Constraints'},
        {n:S.avg_general, l:'Avg General'},
        {n:S.avg_financial_soft, l:'Avg Fin-Soft'},
        {n:S.avg_hidden, l:'Avg Hidden Checkers'},
        {n:S.by_l1['T1']||0, l:'T1 Samples'},
        {n:S.by_l1['T2']||0, l:'T2 Samples'},
        {n:S.by_l1['T3']||0, l:'T3 Samples'},
        {n:S.hard_total, l:'Hard Total'},
        {n:S.soft_total, l:'Soft Total'},
    ];
    document.getElementById('statsGrid').innerHTML = cards.map(c =>
        `<div class="stat-card"><div class="num">${c.n}</div><div class="lbl">${c.l}</div></div>`
    ).join('');
}

// Constraint dist chart
{
    const cd = S.by_constraint;
    const maxV = Math.max(...Object.values(cd));
    document.getElementById('cDistChart').innerHTML = Object.entries(cd).map(([k,v]) => {
        const h = Math.round(v/maxV*80);
        const isG = k.startsWith('G');
        const color = isG ? 'var(--accent)' : 'var(--green)';
        return `<div class="bar-item"><div class="bar-val">${v}</div><div class="bar" style="height:${h}px;background:${color}"></div><div class="bar-lbl">${k}</div></div>`;
    }).join('');
}

// Filters
document.querySelectorAll('.fbtn').forEach(b => b.addEventListener('click', () => {
    filter = b.dataset.f;
    document.querySelectorAll('.fbtn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    renderList();
}));
document.getElementById('searchBox').addEventListener('input', e => { search=e.target.value; renderList(); });

function getFiltered() {
    return D.samples.filter(s => {
        if (filter !== 'all' && s.L1 !== filter) return false;
        if (search && !s.case_id.toLowerCase().includes(search.toLowerCase()) && !s.sample_id.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });
}

function renderList() {
    const filtered = getFiltered();
    let h = '';
    filtered.forEach((s, i) => {
        const cIds = s.constraints.map(c => c.id).join(', ');
        h += `<div class="citem${selIdx===i?' sel':''}" data-idx="${i}">
            <span class="sid">${s.sample_id}</span>
            <span class="tbadge t${s.L1}">${s.L2}</span>
            <span class="vbadge">${s.variant_type}</span>
            <span class="cbadge">${s.n_general}G+${s.n_financial_soft}F=${s.n_constraints}C</span>
            <span class="cdesc">${esc(cIds)}</span>
        </div>`;
    });
    document.getElementById('sampleList').innerHTML = h || '<div style="padding:20px;color:#666;text-align:center">No samples match filter</div>';
    document.querySelectorAll('.citem').forEach(el => el.addEventListener('click', () => openSample(parseInt(el.dataset.idx))));
}

function openSample(idx) {
    const filtered = getFiltered();
    selIdx = idx;
    const s = filtered[idx];
    if (!s) return;

    document.getElementById('dTitle').textContent = `${s.sample_id} [${s.L2}] ${s.variant_type}`;
    document.getElementById('contextBox').textContent = s.context_text;
    document.getElementById('queryBox').textContent = s.query_text;
    document.getElementById('promptBox').textContent = s.prompt;

    // Constraints table
    let ct = '<table class="ctbl"><thead><tr><th>ID</th><th>Name</th><th>Type</th><th>Checker</th><th>Rendered Text</th><th>Params</th></tr></thead><tbody>';
    s.constraints.forEach(c => {
        const tc = c.type==='hard'?'cht':'chs';
        ct += `<tr><td class="${tc}" style="font-family:monospace">${c.id}</td><td>${esc(c.name)}</td>`;
        ct += `<td><span style="font-size:10px;padding:1px 4px;border-radius:2px;${c.type==='hard'?'background:#2d1b69;color:#a78bfa':'background:#1b4332;color:#6ee7b7'}">${c.type}</span></td>`;
        ct += `<td style="font-family:monospace;font-size:10px;color:#666">${c.checker||'-'}</td>`;
        ct += `<td style="font-size:11px">${esc(c.rendered_text)}</td>`;
        ct += `<td style="font-size:10px;color:#666;max-width:200px;overflow:hidden;text-overflow:ellipsis">${c.params ? esc(JSON.stringify(c.params)).substring(0,120) : '-'}</td></tr>`;
    });
    ct += '</tbody></table>';
    document.getElementById('constraintBox').innerHTML = ct;

    // Tab bar
    document.getElementById('tabBar').innerHTML = ['Context','Query','Constraints','Full Prompt'].map((t,i) =>
        `<div class="tab${i===0?' active':''}" data-t="${['context','query','constraints','prompt'][i]}">${t}</div>`
    ).join('');
    document.querySelectorAll('#tabBar .tab').forEach(t => t.addEventListener('click', () => switchTab(t.dataset.t)));

    document.getElementById('dp').classList.add('vis');
    switchTab('context');
    renderList();
    document.getElementById('dp').scrollIntoView({behavior:'smooth'});
}

// Nav
document.getElementById('prevBtn').addEventListener('click', () => { if(selIdx>0) openSample(selIdx-1); });
document.getElementById('nextBtn').addEventListener('click', () => { const f=getFiltered(); if(selIdx<f.length-1) openSample(selIdx+1); });
document.getElementById('closeBtn').addEventListener('click', () => { selIdx=-1; document.getElementById('dp').classList.remove('vis'); renderList(); });

function switchTab(name) {
    document.querySelectorAll('#tabBar .tab').forEach(t => t.classList.toggle('active', t.dataset.t===name));
    ['context','query','constraints','prompt'].forEach(n => document.getElementById('tc-'+n).classList.toggle('active', n===name));
}

renderList();
</script>
</body>
</html>"""


def build_html(api_data):
    data_json = json.dumps(api_data, ensure_ascii=False)
    return HTML_TEMPLATE.replace("__DATA__", data_json)


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, html_content=None, **kwargs):
        self.html_content = html_content
        super().__init__(*args, **kwargs)
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.html_content.encode("utf-8"))
        else:
            super().do_GET()
    def log_message(self, fmt, *args):
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18925)
    args = parser.parse_args()
    samples = load_data()
    api_data = build_api_data(samples)
    html = build_html(api_data)
    handler = lambda *a, **kw: ViewerHandler(*a, html_content=html, **kw)
    server = HTTPServer(("0.0.0.0", args.port), handler)
    print(f"FinIF SFT Data Viewer: http://localhost:{args.port}")
    print(f"Loaded {len(samples)} samples")
    server.serve_forever()

if __name__ == "__main__":
    main()
