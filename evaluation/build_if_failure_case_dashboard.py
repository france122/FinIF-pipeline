#!/usr/bin/env python3
"""Build a small static dashboard of high-quality FinIF failures."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_SCORES = Path(
    "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/"
    "scores_gpt5_judge_gpt4o_combined.json"
)
DEFAULT_OUTPUT = Path(
    "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/"
    "if_failure_case_dashboard.html"
)
RESPONSE_FILES = [
    Path("outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/responses_gpt5.jsonl"),
    Path("outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/responses_gpt5.jsonl"),
]
SELECTED_DATASETS = [
    Path("outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/selected_dataset.jsonl"),
    Path("outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/selected_dataset.jsonl"),
]

CASE_IDS = [
    "v6_line_011",
    "v6_line_063",
    "v6_line_142",
    "v6_line_189",
    "v6_line_021",
    "v6_line_089",
]


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def first_sentence(text: str, limit: int = 320) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def load_response_map() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for path in RESPONSE_FILES:
        for row in read_jsonl(path):
            item_id = str(row.get("item_id") or "")
            if item_id:
                out[item_id] = str(row.get("response") or "")
    return out


def load_dataset_map() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in SELECTED_DATASETS:
        for row in read_jsonl(path):
            item_id = str(row.get("id") or row.get("item_id") or "")
            if item_id:
                out[item_id] = row
    return out


def case_note(item_id: str) -> str:
    notes = {
        "v6_line_011": "Excellent finance answer, but it missed a required audit table and used one-decimal percentages.",
        "v6_line_063": "The answer is substantively strong, yet the rule checker catches a percent-word precision miss.",
        "v6_line_142": "The model conveyed evidence, but formatted nested quotes as list items instead of Markdown blockquote lines.",
        "v6_line_189": "Borderline example: high-quality answer, but 433 words exceeded the 430-word cap.",
        "v6_line_021": "Useful AML review, but source labels, calculation lineage, and final escalation chain did not close tightly enough.",
        "v6_line_089": "Finance reasoning is present, but liquidity/timing details and required approval boundary were not explicit enough.",
    }
    return notes.get(item_id, "")


def classify_case(fails: List[Dict[str, Any]], quality: Optional[int]) -> str:
    tags = {str(row.get("tag") or "") for row in fails}
    if quality is not None and quality >= 9:
        return "High Quality, Mechanical IF Miss"
    if {"EG2", "QV2", "DB9"} & tags:
        return "Substantive Finance IF Miss"
    return "Instruction Detail Miss"


def build_cases(scores: Dict[str, Any]) -> List[Dict[str, Any]]:
    responses = load_response_map()
    datasets = load_dataset_map()
    by_id = {str(item.get("item_id") or ""): item for item in scores.get("items", [])}
    cases = []
    for item_id in CASE_IDS:
        scored = by_id[item_id]
        dataset = datasets.get(item_id, {})
        response = responses.get(item_id, "")
        fails = [row for row in scored.get("results", []) if row.get("score") == 0]
        quality = scored.get("quality", {}).get("score")
        cases.append(
            {
                "id": item_id,
                "workflow": dataset.get("workflow") or "",
                "task": dataset.get("task") or "",
                "work_product": dataset.get("work_product") or "",
                "quality": quality,
                "if_score": scored.get("summary", {}).get("score"),
                "case_type": classify_case(fails, quality),
                "note": case_note(item_id),
                "query": dataset.get("query") or "",
                "response": response,
                "response_excerpt": first_sentence(response, 900),
                "failures": [
                    {
                        "tag": row.get("tag") or "",
                        "family": row.get("family") or "",
                        "method": row.get("method") or "",
                        "constraint": row.get("constraint") or "",
                        "reason": row.get("reason") or "",
                    }
                    for row in fails
                ],
            }
        )
    return cases


def build_html(scores: Dict[str, Any], cases: List[Dict[str, Any]]) -> str:
    summary = scores.get("summary", {})
    failed_tags = Counter()
    failed_methods = Counter()
    for item in scores.get("items", []):
        for result in item.get("results", []):
            if result.get("score") == 0:
                failed_tags[str(result.get("tag") or "UNKNOWN")] += 1
                failed_methods[str(result.get("method") or "UNKNOWN")] += 1

    top_tags = failed_tags.most_common(8)
    max_tag = max([count for _, count in top_tags] or [1])
    top_methods = failed_methods.most_common(6)
    max_method = max([count for _, count in top_methods] or [1])

    data = {
        "summary": summary,
        "top_tags": top_tags,
        "max_tag": max_tag,
        "top_methods": top_methods,
        "max_method": max_method,
        "cases": cases,
        "figure_cases": ["v6_line_063", "v6_line_189", "v6_line_142", "v6_line_011"],
    }
    payload = json.dumps(data, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FinIF Failure Case Board</title>
  <style>
    :root {{
      --bg: #0b0f14;
      --panel: #141a22;
      --panel2: #1b2330;
      --ink: #e8edf3;
      --muted: #93a2b7;
      --line: #2b3646;
      --blue: #6aa5ff;
      --green: #4bc27d;
      --amber: #f0b84f;
      --red: #ff6b6b;
      --violet: #a78bfa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 18px 28px;
      border-bottom: 1px solid var(--line);
      background: rgba(11, 15, 20, .95);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0; font-size: 20px; letter-spacing: 0; }}
    .sub {{ color: var(--muted); margin-top: 4px; font-size: 12.5px; }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 22px 28px 64px; }}
    .cards {{ display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; min-height: 88px; }}
    .card .num {{ font-size: 25px; font-weight: 700; }}
    .card .lab {{ color: var(--muted); font-size: 12px; margin-top: 5px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 18px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    h2 {{ margin: 0 0 12px; font-size: 15px; }}
    .barrow {{ display: grid; grid-template-columns: 76px 1fr 72px; gap: 10px; align-items: center; margin: 8px 0; }}
    .barrow.method {{ grid-template-columns: 190px 1fr 72px; }}
    .barname {{ color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar {{ height: 18px; background: #232c38; border-radius: 5px; overflow: hidden; }}
    .fill {{ height: 100%; background: var(--blue); }}
    .method .fill {{ background: var(--violet); }}
    .barnum {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .section-title {{ display:flex; align-items:end; justify-content:space-between; margin: 24px 0 12px; }}
    .section-title h2 {{ margin: 0; font-size: 18px; }}
    .hint {{ color: var(--muted); font-size: 12.5px; }}
    .case {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin-bottom: 14px; overflow: hidden; }}
    .case-head {{ display: grid; grid-template-columns: 1fr auto; gap: 14px; padding: 16px; background: var(--panel2); border-bottom: 1px solid var(--line); }}
    .case-title {{ font-weight: 700; font-size: 15px; }}
    .meta {{ color: var(--muted); font-size: 12.5px; margin-top: 4px; }}
    .chips {{ display:flex; gap: 8px; flex-wrap:wrap; justify-content:flex-end; }}
    .chip {{ border:1px solid var(--line); border-radius: 999px; padding: 3px 9px; font-size: 12px; color: var(--muted); background: #111820; }}
    .chip.good {{ color: var(--green); border-color: rgba(75,194,125,.35); }}
    .chip.bad {{ color: var(--red); border-color: rgba(255,107,107,.35); }}
    .chip.type {{ color: var(--amber); border-color: rgba(240,184,79,.35); }}
    .case-body {{ padding: 16px; }}
    .note {{ border-left: 3px solid var(--amber); padding: 8px 12px; background: #191813; color: #f5d58b; margin-bottom: 14px; }}
    .cols {{ display: grid; grid-template-columns: .9fr 1.1fr; gap: 14px; }}
    .box {{ background: #10161f; border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 80px; }}
    .box h3 {{ margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }}
    .text {{ white-space: pre-wrap; color: #d6dde8; max-height: 260px; overflow: auto; }}
    .fail {{ border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; }}
    .fail:first-child {{ border-top: 0; padding-top: 0; margin-top: 0; }}
    .tag {{ color: var(--blue); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700; }}
    .reason {{ color: #f2c46d; }}
    .constraint {{ color: #cbd5e1; margin-top: 4px; }}
    .method {{ color: var(--muted); font-size: 12px; margin-top: 3px; }}
    .figure-strip {{ display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }}
    .mini {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .mini .mid {{ color: var(--blue); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700; }}
    .mini .mtitle {{ margin-top: 6px; font-weight: 700; }}
    .mini .mdetail {{ color: var(--muted); margin-top: 8px; font-size: 12.5px; }}
    .mini .miss {{ color: var(--red); margin-top: 8px; font-size: 12.5px; }}
    .caption {{ background:#10161f; border:1px solid var(--line); border-radius:8px; padding:12px 14px; color:#d8e0eb; margin-bottom:18px; }}
    @media (max-width: 980px) {{
      .cards {{ grid-template-columns: repeat(2, 1fr); }}
      .grid, .cols, .case-head, .figure-strip {{ grid-template-columns: 1fr; }}
      .chips {{ justify-content:flex-start; }}
    }}
  </style>
</head>
<body>
<header>
  <h1>FinIF: High-Quality Answers That Still Fail IF</h1>
  <div class="sub">典型金融 case：答案质量高或业务方向正确，但 source labels、计算链条、格式/数量等 instruction-following 细节没完全遵守。</div>
</header>
<main>
  <div class="cards" id="cards"></div>
  <div class="grid">
    <section class="panel">
      <h2>Top Failed Constraint Tags</h2>
      <div id="tagbars"></div>
    </section>
    <section class="panel">
      <h2>Failure Methods</h2>
      <div id="methodbars"></div>
    </section>
  </div>
  <div class="section-title">
    <h2>Figure 1 Support Cases</h2>
    <div class="hint">Simple-looking requests, high output quality, failed exact IF</div>
  </div>
  <div class="caption">
    Suggested framing: In these finance tasks, GPT-5 produced useful, high-quality answers, yet failed exact compliance because it missed simple prescribed details such as two-decimal percentage formatting, a word cap, Markdown blockquote lines, or a required audit table.
  </div>
  <div class="figure-strip" id="figureCases"></div>
  <div class="section-title">
    <h2>Representative Cases</h2>
    <div class="hint">Selected from GPT-5 hard300, judged by GPT-4o</div>
  </div>
  <div id="cases"></div>
</main>
<script>
const DATA = {payload};
const pct = (x) => (100*x).toFixed(1) + "%";
const esc = (s) => (s || "").replace(/[&<>]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]));
const s = DATA.summary;
document.getElementById("cards").innerHTML = [
  ["Hard300 ISR", pct(s.exact_item_pass_rate), "exact_item_pass_rate"],
  ["Coverage", pct(s.coverage), "all constraints decided"],
  ["Micro IF", s.micro_score.toFixed(3), "constraint-level compliance"],
  ["Quality Mean", s.quality_score_mean_0_10.toFixed(2), "0-10 diagnostic"],
  ["Strict Fails", s.strict_failed_items, "items with any IF miss"]
].map(([label, num, desc]) => `<div class="card"><div class="num">${{num}}</div><div class="lab">${{label}}</div><div class="lab">${{desc}}</div></div>`).join("");
function bars(rows, max, id, method=false) {{
  document.getElementById(id).innerHTML = rows.map(([name, count]) => `
    <div class="barrow ${{method ? "method" : ""}}">
      <div class="barname" title="${{esc(name)}}">${{esc(name)}}</div>
      <div class="bar"><div class="fill" style="width:${{100*count/max}}%"></div></div>
      <div class="barnum">${{count}}</div>
    </div>`).join("");
}}
bars(DATA.top_tags, DATA.max_tag, "tagbars");
bars(DATA.top_methods, DATA.max_method, "methodbars", true);
const byId = Object.fromEntries(DATA.cases.map(c => [c.id, c]));
document.getElementById("figureCases").innerHTML = DATA.figure_cases.map(id => {{
  const c = byId[id];
  const first = c.failures[0] || {{}};
  return `<div class="mini">
    <div class="mid">${{esc(c.id)}}</div>
    <div class="mtitle">${{esc(c.work_product || c.task)}}</div>
    <div class="mdetail">Quality ${{c.quality}}/10 · IF ${{(100*c.if_score).toFixed(1)}}%</div>
    <div class="miss">${{esc(first.tag)}}: ${{esc(first.reason)}}</div>
  </div>`;
}}).join("");
document.getElementById("cases").innerHTML = DATA.cases.map(c => `
  <article class="case">
    <div class="case-head">
      <div>
        <div class="case-title">${{esc(c.id)}} · ${{esc(c.task)}} · ${{esc(c.work_product)}}</div>
        <div class="meta">${{esc(c.workflow)}}</div>
      </div>
      <div class="chips">
        <span class="chip type">${{esc(c.case_type)}}</span>
        <span class="chip good">Quality ${{c.quality}}/10</span>
        <span class="chip bad">IF ${{(100*c.if_score).toFixed(1)}}%</span>
      </div>
    </div>
    <div class="case-body">
      <div class="note">${{esc(c.note)}}</div>
      <div class="cols">
        <div class="box">
          <h3>Task Query</h3>
          <div class="text">${{esc(c.query)}}</div>
        </div>
        <div class="box">
          <h3>Model Response Excerpt</h3>
          <div class="text">${{esc(c.response_excerpt)}}</div>
        </div>
      </div>
      <div class="box" style="margin-top:14px">
        <h3>Failed IF Constraints</h3>
        ${{c.failures.map(f => `
          <div class="fail">
            <div><span class="tag">${{esc(f.tag)}}</span> <span class="reason">${{esc(f.reason)}}</span></div>
            <div class="constraint">${{esc(f.constraint)}}</div>
            <div class="method">${{esc(f.family)}} · ${{esc(f.method)}}</div>
          </div>`).join("")}}
      </div>
    </div>
  </article>`).join("");
</script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scores = json.loads(args.scores.read_text(encoding="utf-8"))
    cases = build_cases(scores)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(scores, cases), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
