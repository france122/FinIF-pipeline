#!/usr/bin/env python3
"""Build self-contained review HTML for ds-v4-flash vs ds-v4-pro."""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_jsonl(path):
    data = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                data[obj["case_id"]] = obj
    return data

def main():
    bench = json.load(open(os.path.join(SCRIPT_DIR, "benchmark_all.json"), encoding="utf-8"))["cases"]
    eval_cfg = json.load(open(os.path.join(SCRIPT_DIR, "eval_config_all.json"), encoding="utf-8"))["constraints"]

    resp_flash = load_jsonl(os.path.join(SCRIPT_DIR, "benchmark_responses/responses_ds-v4-flash.jsonl"))
    resp_pro = load_jsonl(os.path.join(SCRIPT_DIR, "benchmark_responses/responses_ds-v4-pro.jsonl"))

    scores_flash = json.load(open(os.path.join(SCRIPT_DIR, "output/scores_ds-v4-flash.json"), encoding="utf-8"))
    scores_pro = json.load(open(os.path.join(SCRIPT_DIR, "output/scores_ds-v4-pro.json"), encoding="utf-8"))

    cases = {}
    for c in bench:
        cid = c["case_id"]
        tier = cid.split(".")[0]
        constraints = []
        for key, cfg in eval_cfg.items():
            if key.startswith(cid + "#"):
                con_id = key.split("#")[1]
                entry = {
                    "id": con_id,
                    "key": key,
                    "type": cfg["type"],
                    "tag": cfg.get("tag", ""),
                    "description": cfg.get("description", ""),
                }
                fr = scores_flash["results"].get(cid, {}).get(key, {})
                pr = scores_pro["results"].get(cid, {}).get(key, {})
                entry["flash_pass"] = fr.get("pass")
                entry["flash_reason"] = fr.get("reason", "")
                entry["pro_pass"] = pr.get("pass")
                entry["pro_reason"] = pr.get("reason", "")
                constraints.append(entry)
        constraints.sort(key=lambda x: x["id"])

        def calc_score(results, cid, cons):
            hard_pass = sum(1 for c in cons if c["type"] == "hard" and results.get(cid, {}).get(c["key"], {}).get("pass") is True)
            hard_total = sum(1 for c in cons if c["type"] == "hard")
            soft_pass = sum(1 for c in cons if c["type"] == "soft" and results.get(cid, {}).get(c["key"], {}).get("pass") is True)
            soft_total = sum(1 for c in cons if c["type"] == "soft")
            total = hard_total + soft_total
            passed = hard_pass + soft_pass
            return {
                "score": passed / total if total else 0,
                "hard": {"passed": hard_pass, "total": hard_total},
                "soft": {"passed": soft_pass, "total": soft_total},
            }
        sf = calc_score(scores_flash["results"], cid, constraints)
        sp = calc_score(scores_pro["results"], cid, constraints)

        cases[cid] = {
            "case_id": cid,
            "tier": tier,
            "prompt": c["prompt"],
            "context": c.get("context", ""),
            "flash_response": resp_flash.get(cid, {}).get("response", "(no response)"),
            "pro_response": resp_pro.get(cid, {}).get("response", "(no response)"),
            "flash_score": sf,
            "pro_score": sp,
            "constraints": constraints,
        }

    tier_scores = {
        "flash": scores_flash["tier_scores"],
        "pro": scores_pro["tier_scores"],
    }

    data_json = json.dumps({"cases": cases, "tier_scores": tier_scores}, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)

    out_path = os.path.join(SCRIPT_DIR, "review_responses.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {out_path} ({len(html)//1024} KB)")


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FinIF Response Review — Flash vs Pro</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#333;display:flex;height:100vh;overflow:hidden}
.sidebar{width:300px;min-width:300px;background:#1a1a2e;color:#eee;display:flex;flex-direction:column}
.sidebar-header{padding:16px;border-bottom:1px solid #333}
.sidebar-header h2{font-size:15px;color:#8888cc;margin-bottom:8px}
.overall-scores{display:flex;gap:12px;font-size:12px;color:#aaa}
.overall-scores span{display:flex;align-items:center;gap:4px}
.flash-color{color:#4fc3f7}
.pro-color{color:#ab47bc}
.filter-bar{display:flex;padding:8px;gap:4px;border-bottom:1px solid #333}
.filter-btn{flex:1;padding:6px 0;text-align:center;background:#16213e;color:#aaa;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600}
.filter-btn.active{background:#4a9eff;color:#fff}
.filter-btn:hover:not(.active){background:#1e2d4a}
.search-box{margin:8px;padding:8px 12px;background:#16213e;border:1px solid #333;border-radius:4px;color:#eee;font-size:13px;outline:none}
.search-box:focus{border-color:#4a9eff}
.case-list{flex:1;overflow-y:auto}
.case-item{padding:10px 16px;cursor:pointer;border-left:3px solid transparent;transition:all .15s}
.case-item:hover{background:#16213e}
.case-item.active{background:#16213e;border-left-color:#4a9eff}
.case-item .case-id{font-weight:600;font-size:13px;display:flex;justify-content:space-between;align-items:center}
.case-item .score-bars{display:flex;gap:4px;margin-top:4px;font-size:11px}
.score-bar{flex:1;height:18px;background:#16213e;border-radius:3px;position:relative;overflow:hidden}
.score-bar .fill{height:100%;border-radius:3px;transition:width .3s}
.score-bar .label{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:10px;font-weight:600;color:#fff;text-shadow:0 0 3px rgba(0,0,0,.5)}
.fill-flash{background:linear-gradient(90deg,#0288d1,#4fc3f7)}
.fill-pro{background:linear-gradient(90deg,#7b1fa2,#ab47bc)}
.tier-badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600}
.tier-T1{background:#1a73e8;color:#fff}
.tier-T2{background:#e87a1a;color:#fff}
.tier-T3{background:#d32f2f;color:#fff}
.main{flex:1;overflow-y:auto;padding:24px 32px}
.section{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.section h3{font-size:14px;color:#666;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:8px}
.case-header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.case-header h1{font-size:22px}
.score-summary{display:flex;gap:20px;margin-top:8px}
.score-card{padding:8px 16px;border-radius:6px;font-size:14px;font-weight:600}
.score-card-flash{background:#e1f5fe;color:#0277bd;border:1px solid #b3e5fc}
.score-card-pro{background:#f3e5f5;color:#7b1fa2;border:1px solid #ce93d8}
.score-detail{font-size:12px;font-weight:400;color:#666;margin-top:2px}
.text-block{background:#fafafa;border:1px solid #e8e8e8;border-radius:6px;padding:16px;font-size:14px;line-height:1.7;white-space:pre-wrap;word-break:break-word;max-height:400px;overflow-y:auto}
.collapsible{cursor:pointer;user-select:none}
.collapsible::before{content:"\25B6";margin-right:8px;font-size:11px;transition:transform .2s;display:inline-block}
.collapsible.open::before{transform:rotate(90deg)}
.collapsible-content{display:none;margin-top:12px}
.collapsible-content.show{display:block}
.responses{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.response-col h4{font-size:13px;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.response-col .text-block{font-size:13px;max-height:600px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#f8f8f8;text-align:left;padding:8px 10px;font-weight:600;border-bottom:2px solid #e0e0e0;white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top}
tr:hover{background:#fafafa}
.pass-true{color:#2e7d32;font-weight:600}
.pass-false{color:#c62828;font-weight:600}
.pass-null{color:#999}
.type-badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600}
.type-hard{background:#e8f0fe;color:#1a73e8}
.type-soft{background:#fef3e8;color:#e87a1a}
.tag-badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;background:#f0f0f0;color:#666}
.diff-row{background:#fff8e1}
.reason-cell{font-size:11px;color:#666;max-width:200px;overflow:hidden;text-overflow:ellipsis}
.reason-cell:hover{white-space:normal;overflow:visible}
.filter-diff{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:12px;color:#666}
.filter-diff input{cursor:pointer}
.empty-state{text-align:center;color:#999;padding:60px 20px;font-size:16px}
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <h2>FinIF Review — Flash vs Pro</h2>
    <div class="overall-scores">
      <span class="flash-color">Flash: <b id="overall-flash"></b></span>
      <span class="pro-color">Pro: <b id="overall-pro"></b></span>
    </div>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" data-tier="all">All</button>
    <button class="filter-btn" data-tier="T1">T1</button>
    <button class="filter-btn" data-tier="T2">T2</button>
    <button class="filter-btn" data-tier="T3">T3</button>
  </div>
  <input class="search-box" placeholder="Search case_id..." id="search">
  <div class="case-list" id="case-list"></div>
</div>
<div class="main" id="main">
  <div class="empty-state">Select a case from the sidebar to start reviewing.</div>
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;

const caseIds = Object.keys(DATA.cases).sort();
const tierScores = DATA.tier_scores;

document.getElementById("overall-flash").textContent = tierScores.flash.overall.toFixed(1) + "%";
document.getElementById("overall-pro").textContent = tierScores.pro.overall.toFixed(1) + "%";

function renderSidebar(filter, search) {
  const list = document.getElementById("case-list");
  list.innerHTML = "";
  const q = (search || "").toLowerCase();
  caseIds.forEach(cid => {
    const c = DATA.cases[cid];
    if (filter !== "all" && c.tier !== filter) return;
    if (q && !cid.toLowerCase().includes(q)) return;
    const fs = c.flash_score.score || 0;
    const ps = c.pro_score.score || 0;
    const div = document.createElement("div");
    div.className = "case-item";
    div.dataset.cid = cid;
    div.innerHTML = `
      <div class="case-id">
        <span>${cid}</span>
        <span class="tier-badge tier-${c.tier}">${c.tier}</span>
      </div>
      <div class="score-bars">
        <div class="score-bar">
          <div class="fill fill-flash" style="width:${fs*100}%"></div>
          <div class="label">${(fs*100).toFixed(0)}%</div>
        </div>
        <div class="score-bar">
          <div class="fill fill-pro" style="width:${ps*100}%"></div>
          <div class="label">${(ps*100).toFixed(0)}%</div>
        </div>
      </div>`;
    div.onclick = () => selectCase(cid);
    list.appendChild(div);
  });
}

let currentCid = null;

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function selectCase(cid) {
  currentCid = cid;
  document.querySelectorAll(".case-item").forEach(el => {
    el.classList.toggle("active", el.dataset.cid === cid);
  });
  const c = DATA.cases[cid];
  const fs = c.flash_score, ps = c.pro_score;
  const main = document.getElementById("main");

  let consRows = "";
  c.constraints.forEach(con => {
    const isDiff = con.flash_pass !== con.pro_pass;
    const rowClass = isDiff ? "diff-row" : "";
    const fpClass = con.flash_pass === true ? "pass-true" : con.flash_pass === false ? "pass-false" : "pass-null";
    const ppClass = con.pro_pass === true ? "pass-true" : con.pro_pass === false ? "pass-false" : "pass-null";
    const fpText = con.flash_pass === true ? "PASS" : con.flash_pass === false ? "FAIL" : "N/A";
    const ppText = con.pro_pass === true ? "PASS" : con.pro_pass === false ? "FAIL" : "N/A";
    consRows += `<tr class="${rowClass}">
      <td>${escapeHtml(con.id)}</td>
      <td><span class="type-badge type-${con.type}">${con.type}</span></td>
      <td><span class="tag-badge">${escapeHtml(con.tag)}</span></td>
      <td>${escapeHtml(con.description)}</td>
      <td class="${fpClass}">${fpText}</td>
      <td class="${ppClass}">${ppText}</td>
      <td class="reason-cell" title="${escapeHtml(con.flash_reason)}">${escapeHtml(con.flash_reason)}</td>
      <td class="reason-cell" title="${escapeHtml(con.pro_reason)}">${escapeHtml(con.pro_reason)}</td>
    </tr>`;
  });

  main.innerHTML = `
    <div class="section">
      <div class="case-header">
        <h1>${cid}</h1>
        <span class="tier-badge tier-${c.tier}">${c.tier}</span>
      </div>
      <div class="score-summary">
        <div class="score-card score-card-flash">
          Flash: ${((fs.score||0)*100).toFixed(1)}%
          <div class="score-detail">Hard ${fs.hard?.passed||0}/${fs.hard?.total||0} · Soft ${fs.soft?.passed||0}/${fs.soft?.total||0}</div>
        </div>
        <div class="score-card score-card-pro">
          Pro: ${((ps.score||0)*100).toFixed(1)}%
          <div class="score-detail">Hard ${ps.hard?.passed||0}/${ps.hard?.total||0} · Soft ${ps.soft?.passed||0}/${ps.soft?.total||0}</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h3>Prompt</h3>
      <div class="text-block">${escapeHtml(c.prompt)}</div>
    </div>

    <div class="section">
      <h3 class="collapsible" onclick="toggleCollapsible(this)">Context</h3>
      <div class="collapsible-content">
        <div class="text-block">${escapeHtml(c.context || "(no context)")}</div>
      </div>
    </div>

    <div class="section">
      <h3>Responses</h3>
      <div class="responses">
        <div class="response-col">
          <h4><span class="flash-color">ds-v4-flash</span> <span style="font-size:11px;color:#999">${c.flash_response.length} chars</span></h4>
          <div class="text-block">${escapeHtml(c.flash_response)}</div>
        </div>
        <div class="response-col">
          <h4><span class="pro-color">ds-v4-pro</span> <span style="font-size:11px;color:#999">${c.pro_response.length} chars</span></h4>
          <div class="text-block">${escapeHtml(c.pro_response)}</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h3>
        Constraints (${c.constraints.length})
        <label class="filter-diff"><input type="checkbox" id="diff-only" onchange="filterDiff()"> Only show differences</label>
      </h3>
      <table id="cons-table">
        <thead>
          <tr>
            <th>ID</th><th>Type</th><th>Tag</th><th>Description</th>
            <th class="flash-color">Flash</th><th class="pro-color">Pro</th>
            <th class="flash-color">Flash Reason</th><th class="pro-color">Pro Reason</th>
          </tr>
        </thead>
        <tbody>${consRows}</tbody>
      </table>
    </div>`;
}

function toggleCollapsible(el) {
  el.classList.toggle("open");
  const content = el.nextElementSibling;
  content.classList.toggle("show");
}

function filterDiff() {
  const only = document.getElementById("diff-only")?.checked;
  document.querySelectorAll("#cons-table tbody tr").forEach(tr => {
    if (only) {
      tr.style.display = tr.classList.contains("diff-row") ? "" : "none";
    } else {
      tr.style.display = "";
    }
  });
}

// Filter buttons
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderSidebar(btn.dataset.tier, document.getElementById("search").value);
  };
});

document.getElementById("search").oninput = (e) => {
  const active = document.querySelector(".filter-btn.active");
  renderSidebar(active?.dataset.tier || "all", e.target.value);
};

// Keyboard navigation
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  const items = [...document.querySelectorAll(".case-item")];
  if (!items.length) return;
  const idx = items.findIndex(el => el.dataset.cid === currentCid);
  if (e.key === "ArrowDown" || e.key === "j") {
    e.preventDefault();
    const next = items[Math.min(idx + 1, items.length - 1)];
    next?.click();
    next?.scrollIntoView({block: "nearest"});
  } else if (e.key === "ArrowUp" || e.key === "k") {
    e.preventDefault();
    const prev = items[Math.max(idx - 1, 0)];
    prev?.click();
    prev?.scrollIntoView({block: "nearest"});
  }
});

renderSidebar("all", "");
</script>
</body>
</html>'''


if __name__ == "__main__":
    main()
