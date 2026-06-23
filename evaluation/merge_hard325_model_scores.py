#!/usr/bin/env python3
"""Merge retained hard300 scores with new hard325 swap-in scores."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from . import evaluate_responses as ev
except ImportError:  # pragma: no cover
    import evaluate_responses as ev


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_ifclean_swap_in125_out100.jsonl"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_rows_by_prompt(path: Path) -> Dict[str, Dict[str, Any]]:
    return {row["full_prompt"]: row for row in read_jsonl(path)}


def load_scored_items(scores_path: Path) -> Dict[str, Dict[str, Any]]:
    payload = json.loads(scores_path.read_text(encoding="utf-8"))
    return {str(item.get("item_id") or ""): item for item in payload.get("items", []) if item.get("item_id")}


def load_old_prompt_scored_map(dataset_path: Path, scores_path: Path) -> Dict[str, Dict[str, Any]]:
    dataset_rows = read_jsonl(dataset_path)
    scored_by_id = load_scored_items(scores_path)
    out: Dict[str, Dict[str, Any]] = {}
    for row in dataset_rows:
        item_id = str(row.get("id") or "")
        scored = scored_by_id.get(item_id)
        if scored is not None:
            out[row["full_prompt"]] = scored
    return out


def fully_decided(item: Dict[str, Any]) -> bool:
    summary = item.get("summary") or {}
    total = summary.get("total_constraints")
    decided = summary.get("decided_constraints")
    coverage = summary.get("coverage")
    return isinstance(total, int) and isinstance(decided, int) and total == decided and float(coverage or 0) >= 1.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--old-dataset", type=Path, required=True)
    parser.add_argument("--old-scores", type=Path, required=True)
    parser.add_argument("--new-dataset", type=Path, required=True)
    parser.add_argument("--new-scores", type=Path, required=True)
    parser.add_argument("--model-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    benchmark_rows = read_jsonl(args.benchmark)
    benchmark_by_prompt = {row["full_prompt"]: row for row in benchmark_rows}
    old_prompt_map = load_old_prompt_scored_map(args.old_dataset, args.old_scores)
    new_prompt_map = load_old_prompt_scored_map(args.new_dataset, args.new_scores)

    merged_items: List[Dict[str, Any]] = []
    reused = 0
    new_added = 0
    missing: List[str] = []
    for row in benchmark_rows:
        prompt = row["full_prompt"]
        item = None
        source = None
        if prompt in old_prompt_map:
            item = json.loads(json.dumps(old_prompt_map[prompt], ensure_ascii=False))
            source = "retained_old"
            reused += 1
        elif prompt in new_prompt_map:
            item = json.loads(json.dumps(new_prompt_map[prompt], ensure_ascii=False))
            source = "swap_in_new"
            new_added += 1
        if item is None:
            missing.append(str(row.get("id") or ""))
            continue
        item["hard325_item_id"] = row.get("id")
        item["hard325_line_number"] = row.get("line_number")
        item["hard325_merge_source"] = source
        merged_items.append(item)

    merged_items.sort(key=lambda item: int(item.get("hard325_line_number") or 0))
    output = {
        "schema_version": "finif-v2-hard325-merged-results-1.0",
        "benchmark": str(args.benchmark),
        "old_dataset": str(args.old_dataset),
        "old_scores": str(args.old_scores),
        "new_dataset": str(args.new_dataset),
        "new_scores": str(args.new_scores),
        "model_label": args.model_label,
        "summary": ev.summarize_dataset(merged_items),
        "merge_stats": {
            "benchmark_items": len(benchmark_rows),
            "reused_retained_items": reused,
            "new_swapin_items": new_added,
            "missing_items": missing,
            "fully_decided_items": sum(1 for item in merged_items if fully_decided(item)),
            "source_counts": dict(Counter(str(item.get("hard325_merge_source") or "") for item in merged_items)),
        },
        "items": merged_items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": output["summary"], "merge_stats": output["merge_stats"]}, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
