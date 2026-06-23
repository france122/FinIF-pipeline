#!/usr/bin/env python3
"""Build a markdown result table from scored model JSON files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_summary(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["summary"]


def pct(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{100 * float(value):.2f}%"


def flt(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-label", required=True)
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--judge-label", default="GPT-4o")
    parser.add_argument("--entry", action="append", default=[], help="Model Label::/abs/path/to/score.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows: List[Dict[str, Any]] = []
    for entry in args.entry:
        label, path_text = entry.split("::", 1)
        path = Path(path_text)
        summary = load_summary(path)
        rows.append(
            {
                "label": label,
                "path": path_text,
                "passed": summary.get("exact_item_passed"),
                "decided": summary.get("exact_item_decided"),
                "isr": summary.get("exact_item_pass_rate"),
                "micro": summary.get("micro_score"),
                "macro": summary.get("macro_item_score"),
                "quality": summary.get("quality_score_mean_0_10"),
                "coverage": summary.get("coverage"),
            }
        )

    rows.sort(key=lambda row: float(row["isr"] or -1), reverse=True)
    lines = [
        f"# {args.dataset_label} Formal Model Results",
        "",
        "日期：2026-06-16",
        "",
        "口径说明：",
        "",
        f"- 基准集：`{args.dataset_path}`",
        "- 主指标：`ISR = summary.exact_item_pass_rate`",
        "- Judge 统一口径：`GPT-4o`",
        "",
        "## 正式结果表",
        "",
        "| Model | Passed / Total | ISR / OSR | Micro IF | Macro IF | Quality | Coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['passed']}/{row['decided']} | {pct(row['isr'])} | {pct(row['micro'])} | {pct(row['macro'])} | {flt(row['quality'])} | {pct(row['coverage'])} |"
        )
    lines.extend(
        [
            "",
            "## 正式分数文件索引",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['label']}`")
        lines.append(f"  - `{row['path']}`")

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
