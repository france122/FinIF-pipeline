#!/usr/bin/env python3
"""Extract the swap-in subset from the hard325 benchmark."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_ifclean_swap_in125_out100.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_swapin125_only.jsonl"
DEFAULT_SUMMARY = ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_swapin125_only_summary.json"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    swapin_rows = [row for row in rows if isinstance(row.get("swap_meta"), dict) and row["swap_meta"].get("swap_role") == "swap_in"]
    write_jsonl(args.output, swapin_rows)

    summary = {
        "input": str(args.input.relative_to(ROOT)),
        "output": str(args.output.relative_to(ROOT)),
        "items": len(swapin_rows),
        "workflow_counts": dict(Counter(str(row.get("workflow") or "Unknown") for row in swapin_rows)),
        "task_counts": dict(Counter(str(row.get("task") or "Unknown") for row in swapin_rows)),
        "source_dataset_counts": dict(Counter(str((row.get("swap_meta") or {}).get("source_dataset") or "") for row in swapin_rows)),
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
