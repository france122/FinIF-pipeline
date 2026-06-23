#!/usr/bin/env python3
"""Export all failed FinIF cases with prompt, response, constraints, and a filterable HTML board."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_SCORES = Path(
    "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/"
    "scores_gpt5_judge_gpt4o_combined.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/fail_cases"
)
RESPONSE_FILES = [
    Path("outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/responses_gpt5.jsonl"),
    Path("outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/responses_gpt5.jsonl"),
]
DATASET_FILES = [
    Path("outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/selected_dataset.jsonl"),
    Path("outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/selected_dataset.jsonl"),
]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def item_id_from_row(row: Dict[str, Any]) -> str:
    return str(row.get("item_id") or row.get("id") or row.get("case_id") or "")


def load_map(paths: Iterable[Path], value_key: str | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for path in paths:
        for row in read_jsonl(path):
            item_id = item_id_from_row(row)
            if not item_id:
                continue
            out[item_id] = row.get(value_key) if value_key else row
    return out


def source_line(item_id: str) -> int | None:
    match = re.search(r"(\d+)$", item_id)
    return int(match.group(1)) if match else None


def truncate(text: str, limit: int) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def existing_paths(paths: Iterable[Path]) -> List[Path]:
    return [path for path in paths if path.exists()]


def score_linked_paths(scores: Dict[str, Any], key: str, fallback: Iterable[Path]) -> List[Path]:
    linked = scores.get(key)
    if isinstance(linked, str) and linked:
        path = Path(linked)
        if path.exists():
            return [path]
    return existing_paths(fallback)


def label_for_scores(scores: Dict[str, Any], fallback: str = "model") -> str:
    return str(scores.get("response_model") or scores.get("model") or fallback)


def build_fail_cases(scores: Dict[str, Any], model_label: str | None = None) -> List[Dict[str, Any]]:
    model = model_label or label_for_scores(scores)
    datasets = load_map(score_linked_paths(scores, "dataset", DATASET_FILES))
    responses = load_map(score_linked_paths(scores, "responses", RESPONSE_FILES), "response")
    out = []
    for scored in scores.get("items", []):
        item_id = str(scored.get("item_id") or "")
        failed = [result for result in scored.get("results", []) if result.get("score") == 0]
        if not failed:
            continue
        dataset = datasets.get(item_id, {})
        response = str(responses.get(item_id) or "")
        out.append(
            {
                "case_id": f"{model}::{item_id}",
                "model": model,
                "item_id": item_id,
                "source_line": source_line(item_id),
                "workflow": dataset.get("workflow") or "",
                "task": dataset.get("task") or "",
                "work_product": dataset.get("work_product") or "",
                "query": dataset.get("query") or "",
                "full_prompt": dataset.get("full_prompt") or "",
                "response": response,
                "response_excerpt": truncate(response, 1200),
                "source_registry": dataset.get("source_registry") or [],
                "all_constraints": dataset.get("extracted_constraints") or [],
                "failed_constraints": [
                    {
                        "index": result.get("index"),
                        "tag": result.get("tag") or "",
                        "family": result.get("family") or "",
                        "constraint": result.get("constraint") or "",
                        "check_type": result.get("check_type") or "",
                        "method": result.get("method") or "",
                        "reason": result.get("reason") or "",
                    }
                    for result in failed
                ],
                "failed_tags": sorted({str(result.get("tag") or "") for result in failed}),
                "failed_families": sorted({str(result.get("family") or "") for result in failed}),
                "failed_methods": sorted({str(result.get("method") or "") for result in failed}),
                "summary": scored.get("summary") or {},
                "quality": scored.get("quality") or {},
            }
        )
    out.sort(key=lambda row: (row.get("source_line") or 10**9, row.get("model") or "", row.get("item_id") or ""))
    return out


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "model",
        "item_id",
        "source_line",
        "workflow",
        "task",
        "work_product",
        "if_score",
        "quality_score",
        "failed_tags",
        "failed_methods",
        "failed_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_id": row["item_id"],
                    "model": row.get("model", ""),
                    "source_line": row["source_line"],
                    "workflow": row["workflow"],
                    "task": row["task"],
                    "work_product": row["work_product"],
                    "if_score": row.get("summary", {}).get("score"),
                    "quality_score": row.get("quality", {}).get("score"),
                    "failed_tags": ";".join(row["failed_tags"]),
                    "failed_methods": ";".join(row["failed_methods"]),
                    "failed_reasons": " | ".join(
                        f"{fail['tag']}: {fail['reason']}" for fail in row["failed_constraints"]
                    ),
                }
            )


def summary_stats(
    rows: List[Dict[str, Any]],
    scores: Dict[str, Any] | None = None,
    score_summaries_by_model: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    failed_tag_counts = Counter(
        fail["tag"] for row in rows for fail in row.get("failed_constraints", [])
    )
    failed_family_counts = Counter(
        fail["family"] for row in rows for fail in row.get("failed_constraints", [])
    )
    failed_method_counts = Counter(
        fail["method"] for row in rows for fail in row.get("failed_constraints", [])
    )
    workflow_counts = Counter(row["workflow"] for row in rows)
    model_counts = Counter(row.get("model", "") for row in rows)
    return {
        "score_summary": (scores or {}).get("summary") or {},
        "score_summaries_by_model": score_summaries_by_model or {},
        "failed_items": len(rows),
        "failed_constraint_count": sum(len(row.get("failed_constraints", [])) for row in rows),
        "failed_tag_counts": dict(failed_tag_counts.most_common()),
        "failed_family_counts": dict(failed_family_counts.most_common()),
        "failed_method_counts": dict(failed_method_counts.most_common()),
        "failed_workflow_counts": dict(workflow_counts.most_common()),
        "failed_model_counts": dict(model_counts.most_common()),
    }


def option_values(rows: List[Dict[str, Any]], key: str) -> List[str]:
    values = sorted({str(value) for row in rows for value in row.get(key, []) if str(value)})
    return values


def build_html(rows: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    payload = json.dumps({"rows": rows, "stats": stats}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FinIF Failed Case Explorer</title>
  <style>
    :root {{ --bg:#0b0f14; --panel:#141a22; --panel2:#1b2330; --line:#2b3646; --ink:#e8edf3; --muted:#94a3b8; --blue:#6aa5ff; --red:#ff7777; --amber:#f2bd5b; --green:#4bc27d; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; }}
    header {{ position:sticky; top:0; z-index:5; padding:18px 28px; background:rgba(11,15,20,.96); border-bottom:1px solid var(--line); }}
    h1 {{ margin:0; font-size:20px; }}
    .sub {{ color:var(--muted); margin-top:4px; font-size:12.5px; }}
    main {{ max-width:1360px; margin:0 auto; padding:20px 28px 64px; }}
    .cards {{ display:grid; grid-template-columns:repeat(5,minmax(150px,1fr)); gap:12px; margin-bottom:16px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px 16px; }}
    .num {{ font-size:24px; font-weight:750; }}
    .lab {{ color:var(--muted); font-size:12px; margin-top:4px; }}
    .filters {{ display:grid; grid-template-columns:repeat(7,minmax(120px,1fr)); gap:8px; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; margin-bottom:14px; }}
    .field {{ display:grid; gap:5px; color:var(--muted); font-size:12px; }}
    select,input {{ width:100%; background:var(--panel2); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:8px 10px; font-size:13px; }}
    .type-filter {{ margin-bottom:14px; }}
    .type-filter-head {{ display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:10px; color:var(--muted); font-size:12px; }}
    .tag-buttons {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .tag-btn {{ display:inline-flex; align-items:center; gap:8px; background:var(--panel2); color:var(--ink); border:1px solid var(--line); border-radius:7px; padding:7px 10px; cursor:pointer; font:13px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .tag-btn:hover,.tag-btn.active {{ border-color:rgba(106,165,255,.8); background:rgba(106,165,255,.14); }}
    .tag-count {{ color:var(--muted); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif; font-size:12px; }}
    .count {{ color:var(--muted); margin:12px 0; }}
    .layout {{ display:grid; grid-template-columns:360px 1fr; gap:14px; align-items:start; }}
    .list {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; max-height:calc(100vh - 220px); overflow:auto; }}
    .item {{ padding:12px; border-bottom:1px solid var(--line); cursor:pointer; }}
    .item:hover,.item.active {{ background:var(--panel2); }}
    .item-title {{ font-weight:700; color:var(--blue); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .item-meta {{ color:var(--muted); font-size:12px; margin-top:4px; }}
    .chips {{ display:flex; gap:5px; flex-wrap:wrap; margin-top:8px; }}
    .chip {{ border:1px solid var(--line); border-radius:999px; padding:1px 7px; font-size:11px; color:var(--muted); }}
    .chip.fail {{ color:var(--red); border-color:rgba(255,119,119,.4); }}
    .detail {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; min-height:520px; }}
    .detail-head {{ padding:16px; border-bottom:1px solid var(--line); background:var(--panel2); }}
    .detail-title {{ font-size:17px; font-weight:750; }}
    .metrics {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }}
    .metric {{ border:1px solid var(--line); border-radius:999px; padding:3px 9px; font-size:12px; color:var(--muted); }}
    .metric.good {{ color:var(--green); border-color:rgba(75,194,125,.35); }}
    .metric.bad {{ color:var(--red); border-color:rgba(255,119,119,.35); }}
    .body {{ padding:16px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px; }}
    .box {{ background:#10161f; border:1px solid var(--line); border-radius:8px; padding:12px; }}
    .box h3 {{ margin:0 0 8px; font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
    .box-head {{ display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:8px; }}
    .box-head h3 {{ margin:0; }}
    .copy-btn {{ flex:0 0 auto; background:var(--panel2); color:var(--muted); border:1px solid var(--line); border-radius:6px; padding:4px 8px; cursor:pointer; font-size:12px; line-height:1.2; }}
    .copy-btn:hover,.copy-btn.copied {{ color:var(--ink); border-color:rgba(106,165,255,.75); background:rgba(106,165,255,.14); }}
    .fail-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }}
    .fail-main {{ min-width:0; }}
    .text {{ white-space:pre-wrap; max-height:320px; overflow:auto; color:#d9e1ec; }}
    .fail {{ border-top:1px solid var(--line); padding-top:10px; margin-top:10px; }}
    .fail:first-child {{ border-top:0; padding-top:0; margin-top:0; }}
    .tag {{ color:var(--blue); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:750; }}
    .reason {{ color:var(--amber); }}
    .constraint {{ margin-top:5px; color:#d8dee9; }}
    .method {{ margin-top:4px; color:var(--muted); font-size:12px; }}
    .barrow {{ display:grid; grid-template-columns:70px 1fr 48px; gap:8px; align-items:center; width:100%; margin:6px 0; padding:0; color:var(--ink); background:transparent; border:0; cursor:pointer; font:inherit; text-align:left; }}
    .barrow.active .tag {{ color:var(--green); }}
    .bar {{ height:16px; background:#232c38; border-radius:5px; overflow:hidden; }}
    .fill {{ height:100%; background:var(--blue); }}
    @media(max-width:1000px) {{ .cards,.filters,.layout,.grid {{ grid-template-columns:1fr; }} .list {{ max-height:360px; }} }}
  </style>
</head>
<body>
<header>
  <h1>FinIF Failed Case Explorer</h1>
  <div class="sub">All hard300 non-exact-pass cases with prompt, response, failed constraints, and judge/checker reasons.</div>
</header>
<main>
  <div class="cards" id="cards"></div>
  <section class="box" style="margin-bottom:14px">
    <h3>Failure Tag Distribution</h3>
    <div id="bars"></div>
  </section>
  <section class="box type-filter">
    <div class="type-filter-head">
      <h3 style="margin:0">错误约束类型筛选</h3>
      <span id="constraintFilterHint"></span>
    </div>
    <div class="tag-buttons" id="tagButtons"></div>
  </section>
  <section class="filters">
    <label class="field"><span>Model</span><select id="model"><option value="">All models</option></select></label>
    <label class="field"><span>错误约束类型</span><select id="tag"><option value="">All error constraint types</option></select></label>
    <label class="field"><span>约束家族</span><select id="family"><option value="">All families</option></select></label>
    <label class="field"><span>判分方法</span><select id="method"><option value="">All methods</option></select></label>
    <label class="field"><span>Workflow</span><select id="workflow"><option value="">All workflows</option></select></label>
    <label class="field"><span>Quality</span><select id="quality"><option value="">All quality</option><option value="high">Quality ≥ 9</option><option value="mid">Quality 4-8</option><option value="low">Quality ≤ 3</option></select></label>
    <label class="field"><span>Search</span><input id="search" placeholder="Prompt / response / reason" /></label>
  </section>
  <div class="count" id="count"></div>
  <section class="layout">
    <div class="list" id="list"></div>
    <div class="detail" id="detail"></div>
  </section>
</main>
<script>
const DATA = {payload};
const rows = DATA.rows;
const stats = DATA.stats;
const esc = (s) => (s || "").toString().replace(/[&<>]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]));
const pct = (x) => (100 * Number(x || 0)).toFixed(1) + "%";
const hasScoreSummary = stats.score_summary && Object.keys(stats.score_summary).length > 0;
const metricOrMixed = (key, formatter) => hasScoreSummary && stats.score_summary[key] !== undefined
  ? formatter(stats.score_summary[key])
  : "mixed";
const tagCaseCounts = rows.reduce((acc, row) => {{
  [...new Set(row.failed_tags || [])].forEach(tag => acc[tag] = (acc[tag] || 0) + 1);
  return acc;
}}, {{}});
const tagEntries = Object.entries(tagCaseCounts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
document.getElementById("cards").innerHTML = [
  ["Models", Object.keys(stats.score_summaries_by_model || {{}}).length || 1, "score files"],
  ["Hard300 ISR", metricOrMixed("exact_item_pass_rate", pct), "exact pass rate"],
  ["Failed Cases", stats.failed_items, "non-exact-pass items"],
  ["Failed Constraints", stats.failed_constraint_count, "constraint-level fails"],
  ["Micro IF", metricOrMixed("micro_score", x => Number(x).toFixed(3)), "all constraints"]
].map(([a,b,c]) => `<div class="card"><div class="num">${{b}}</div><div class="lab">${{a}}</div><div class="lab">${{c}}</div></div>`).join("");
const tagMax = Math.max(...Object.values(tagCaseCounts));
document.getElementById("bars").innerHTML = tagEntries.slice(0, 12).map(([tag, count]) => `
  <button class="barrow" type="button" data-tag="${{esc(tag)}}"><div class="tag">${{esc(tag)}}</div><div class="bar"><div class="fill" style="width:${{100*count/tagMax}}%"></div></div><div>${{count}}</div></button>`).join("");
document.getElementById("tagButtons").innerHTML = [
  ["", rows.length],
  ...tagEntries
].map(([tag, count]) => `
  <button class="tag-btn" type="button" data-tag="${{esc(tag)}}">
    <span>${{tag ? esc(tag) : "ALL"}}</span><span class="tag-count">${{count}} cases</span>
  </button>`).join("");
function addOptions(id, values) {{
  const el = document.getElementById(id);
  values.forEach(v => el.add(new Option(v, v)));
}}
addOptions("tag", tagEntries.map(([tag]) => tag));
addOptions("model", [...new Set(rows.map(r => r.model))].sort());
addOptions("family", [...new Set(rows.flatMap(r => r.failed_families))].sort());
addOptions("method", [...new Set(rows.flatMap(r => r.failed_methods))].sort());
addOptions("workflow", [...new Set(rows.map(r => r.workflow))].sort());
const controls = ["model","tag","family","method","workflow","quality","search"].map(id => document.getElementById(id));
controls.forEach(el => el.addEventListener(el.tagName === "INPUT" ? "input" : "change", render));
function setTagFilter(tag) {{
  document.getElementById("tag").value = tag || "";
  render();
}}
document.querySelectorAll("[data-tag]").forEach(el => {{
  el.addEventListener("click", () => setTagFilter(el.dataset.tag));
}});
function updateTypeFilterUI(data) {{
  const tag = document.getElementById("tag").value;
  document.querySelectorAll("[data-tag]").forEach(el => el.classList.toggle("active", el.dataset.tag === tag));
  const label = tag || "ALL";
  document.getElementById("constraintFilterHint").textContent = `${{label}} · ${{data.length}} / ${{rows.length}} cases`;
}}
async function copyText(text, button) {{
  const original = button.textContent;
  try {{
    if (navigator.clipboard && window.isSecureContext) {{
      await navigator.clipboard.writeText(text);
    }} else {{
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }}
    button.textContent = "Copied";
    button.classList.add("copied");
    window.setTimeout(() => {{
      button.textContent = original;
      button.classList.remove("copied");
    }}, 1200);
  }} catch (err) {{
    button.textContent = "Copy failed";
    window.setTimeout(() => button.textContent = original, 1200);
  }}
}}
function bindCopyButtons(copyValues) {{
  document.getElementById("detail").querySelectorAll("[data-copy-key]").forEach(button => {{
    button.addEventListener("click", () => copyText(copyValues[button.dataset.copyKey] || "", button));
  }});
}}
let current = null;
function qualityOk(row, mode) {{
  const q = row.quality && row.quality.score;
  if (!mode) return true;
  if (mode === "high") return q >= 9;
  if (mode === "mid") return q >= 4 && q <= 8;
  if (mode === "low") return q <= 3;
  return true;
}}
function filtered() {{
  const tag = document.getElementById("tag").value;
  const model = document.getElementById("model").value;
  const family = document.getElementById("family").value;
  const method = document.getElementById("method").value;
  const workflow = document.getElementById("workflow").value;
  const quality = document.getElementById("quality").value;
  const search = document.getElementById("search").value.trim().toLowerCase();
  return rows.filter(row => {{
    if (model && row.model !== model) return false;
    if (tag && !row.failed_tags.includes(tag)) return false;
    if (family && !row.failed_families.includes(family)) return false;
    if (method && !row.failed_methods.includes(method)) return false;
    if (workflow && row.workflow !== workflow) return false;
    if (!qualityOk(row, quality)) return false;
    if (search) {{
      const hay = [row.query, row.full_prompt, row.response, ...row.failed_constraints.map(f => f.reason + " " + f.constraint)].join(" ").toLowerCase();
      if (!hay.includes(search)) return false;
    }}
    return true;
  }});
}}
function render() {{
  const data = filtered();
  updateTypeFilterUI(data);
  document.getElementById("count").textContent = `Showing ${{data.length}} / ${{rows.length}} failed cases`;
  const list = document.getElementById("list");
  list.innerHTML = data.map(row => `
    <div class="item ${{current === row.case_id ? "active" : ""}}" data-id="${{esc(row.case_id)}}">
      <div class="item-title">${{esc(row.item_id)}}</div>
      <div class="item-meta">${{esc(row.model)}} · ${{esc(row.workflow)}} · ${{esc(row.task)}}</div>
      <div class="item-meta">IF ${{pct(row.summary.score)}} · Quality ${{row.quality.score ?? "NA"}}/10</div>
      <div class="chips">${{row.failed_tags.map(t => `<span class="chip fail">${{esc(t)}}</span>`).join("")}}</div>
    </div>`).join("");
  list.querySelectorAll(".item").forEach(el => el.onclick = () => select(el.dataset.id));
  if (!data.some(row => row.case_id === current)) current = data[0]?.case_id || null;
  if (current) select(current, false); else document.getElementById("detail").innerHTML = "";
}}
function select(id, rerenderList=true) {{
  current = id;
  const row = rows.find(r => r.case_id === id);
  if (!row) return;
  if (rerenderList) document.querySelectorAll(".item").forEach(el => el.classList.toggle("active", el.dataset.id === id));
  const activeTag = document.getElementById("tag").value;
  const visibleFailedConstraints = activeTag ? row.failed_constraints.filter(f => f.tag === activeTag) : row.failed_constraints;
  const failedMetric = activeTag
    ? `${{visibleFailedConstraints.length}}/${{row.failed_constraints.length}} ${{activeTag}} failed constraints`
    : `${{row.failed_constraints.length}} failed constraints`;
  const failedTitle = activeTag ? `Failed Constraints: ${{activeTag}}` : "Failed Constraints";
  const copyValues = {{
    prompt: row.full_prompt || row.query || "",
    response: row.response || ""
  }};
  visibleFailedConstraints.forEach((f, index) => {{
    copyValues[`constraint-${{index}}`] = f.constraint || "";
  }});
  document.getElementById("detail").innerHTML = `
    <div class="detail-head">
      <div class="detail-title">${{esc(row.item_id)}} · ${{esc(row.task)}} · ${{esc(row.work_product)}}</div>
      <div class="item-meta">${{esc(row.model)}} · ${{esc(row.workflow)}} · source line ${{row.source_line}}</div>
      <div class="metrics">
        <span class="metric bad">IF ${{pct(row.summary.score)}}</span>
        <span class="metric ${{row.quality.score >= 9 ? "good" : "bad"}}">Quality ${{row.quality.score ?? "NA"}}/10</span>
        <span class="metric">${{esc(failedMetric)}}</span>
      </div>
    </div>
    <div class="body">
      <div class="grid">
        <div class="box"><div class="box-head"><h3>Prompt / Full Prompt</h3><button class="copy-btn" type="button" data-copy-key="prompt">Copy</button></div><div class="text">${{esc(row.full_prompt || row.query)}}</div></div>
        <div class="box"><div class="box-head"><h3>${{esc(row.model)}} Response</h3><button class="copy-btn" type="button" data-copy-key="response">Copy</button></div><div class="text">${{esc(row.response)}}</div></div>
      </div>
      <div class="box">
        <h3>${{esc(failedTitle)}}</h3>
        ${{visibleFailedConstraints.map((f, index) => `
          <div class="fail">
            <div class="fail-head">
              <div class="fail-main">
                <div><span class="tag">${{esc(f.tag)}}</span> <span class="reason">${{esc(f.reason)}}</span></div>
                <div class="constraint">${{esc(f.constraint)}}</div>
                <div class="method">${{esc(f.family)}} · ${{esc(f.check_type)}} · ${{esc(f.method)}}</div>
              </div>
              <button class="copy-btn" type="button" data-copy-key="constraint-${{index}}">Copy constraint</button>
            </div>
          </div>`).join("") || `<div class="item-meta">No failed constraints match ${{esc(activeTag)}}.</div>`}}
      </div>
    </div>`;
  bindCopyButtons(copyValues);
}}
render();
</script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument(
        "--score",
        action="append",
        nargs=2,
        metavar=("LABEL", "PATH"),
        help="Add a labeled score file to a combined dashboard. Can be repeated.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.score:
        rows: List[Dict[str, Any]] = []
        score_summaries_by_model: Dict[str, Any] = {}
        for label, path_text in args.score:
            scores = json.loads(Path(path_text).read_text(encoding="utf-8"))
            rows.extend(build_fail_cases(scores, label))
            score_summaries_by_model[label] = scores.get("summary") or {}
        rows.sort(key=lambda row: (row.get("source_line") or 10**9, row.get("model") or "", row.get("item_id") or ""))
        stats = summary_stats(rows, None, score_summaries_by_model)
    else:
        scores = json.loads(args.scores.read_text(encoding="utf-8"))
        rows = build_fail_cases(scores)
        stats = summary_stats(rows, scores, {label_for_scores(scores): scores.get("summary") or {}})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "all_fail_cases.jsonl", rows)
    write_csv(args.output_dir / "fail_case_index.csv", rows)
    (args.output_dir / "summary.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "fail_case_dashboard.html").write_text(
        build_html(rows, stats), encoding="utf-8"
    )
    print(json.dumps({
        "output_dir": str(args.output_dir),
        "failed_items": len(rows),
        "failed_constraints": stats["failed_constraint_count"],
        "dashboard": str(args.output_dir / "fail_case_dashboard.html"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
