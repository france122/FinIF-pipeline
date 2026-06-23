#!/usr/bin/env python3
"""Apply a benchmark/train swap and emit dashboard-ready artifacts."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_ifclean(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    axis_counts: Counter[str] = Counter()
    tag_axis_counts: Counter[str] = Counter()
    check_type_counts: Counter[str] = Counter()
    if_subtype_counts: Counter[str] = Counter()
    if_supertype_counts: Counter[str] = Counter()
    per_item: List[int] = []
    per_item_format: List[int] = []
    per_item_semantic: List[int] = []
    workflow_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    for row in rows:
        workflow_counts[str(row.get("workflow") or "Unknown")] += 1
        task_counts[str(row.get("task") or "Unknown")] += 1
        per_item.append(len(row.get("extracted_constraints") or []))
        item_format = 0
        item_semantic = 0
        for constraint in row.get("extracted_constraints") or []:
            axis_counts["IF"] += 1
            check_type_counts[str(constraint.get("check_type") or "unknown")] += 1
            tag_axis_counts[f"{constraint.get('tag')}::IF"] += 1
            subtype = str(constraint.get("if_subtype") or "other_if")
            supertype = str(constraint.get("if_supertype") or "semantic")
            if_subtype_counts[subtype] += 1
            if_supertype_counts[supertype] += 1
            if supertype == "format":
                item_format += 1
            else:
                item_semantic += 1
        per_item_format.append(item_format)
        per_item_semantic.append(item_semantic)
        for constraint in row.get("diagnostic_constraints") or []:
            axis = str(constraint.get("score_axis") or "diagnostic")
            axis_counts[axis] += 1
            tag_axis_counts[f"{constraint.get('tag')}::{axis}"] += 1
    return {
        "items": len(rows),
        "if_constraints": axis_counts.get("IF", 0),
        "diagnostic_constraints": sum(value for key, value in axis_counts.items() if key != "IF"),
        "axis_counts": dict(axis_counts),
        "if_check_type_counts": dict(check_type_counts),
        "if_supertype_counts": dict(if_supertype_counts),
        "if_subtype_counts": dict(if_subtype_counts),
        "if_constraints_per_item": {
            "min": min(per_item) if per_item else 0,
            "max": max(per_item) if per_item else 0,
            "mean": round(sum(per_item) / len(per_item), 2) if per_item else 0,
        },
        "if_format_constraints_per_item": {
            "min": min(per_item_format) if per_item_format else 0,
            "max": max(per_item_format) if per_item_format else 0,
            "mean": round(sum(per_item_format) / len(per_item_format), 2) if per_item_format else 0,
        },
        "if_semantic_constraints_per_item": {
            "min": min(per_item_semantic) if per_item_semantic else 0,
            "max": max(per_item_semantic) if per_item_semantic else 0,
            "mean": round(sum(per_item_semantic) / len(per_item_semantic), 2) if per_item_semantic else 0,
        },
        "tag_axis_counts": dict(tag_axis_counts.most_common()),
        "workflow_counts": dict(workflow_counts),
        "task_counts": dict(task_counts),
    }


def normalize_dashboard_constraints(raw_constraints: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in raw_constraints:
        constraint = dict(raw)
        check_type = str(raw.get("check_type") or "")
        route = "rule" if check_type == "rule" else "judge"
        constraint["route"] = route
        constraint["judge_uses_docs"] = bool(raw.get("judge_uses_docs"))
        out.append(constraint)
    return out


def train_row_to_dashboard_item(row: Dict[str, Any], *, new_id: str) -> Dict[str, Any]:
    documents = []
    for doc in row.get("source_registry", []) or []:
        documents.append(
            {
                "id": doc.get("source_id", ""),
                "label": doc.get("prompt_label", ""),
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
            }
        )
    return {
        "id": new_id,
        "workflow": row.get("workflow", ""),
        "task": row.get("task", ""),
        "work_product": row.get("work_product", ""),
        "query": row.get("query", ""),
        "full_prompt": row.get("full_prompt", ""),
        "documents": documents,
        "constraints": normalize_dashboard_constraints(row.get("extracted_constraints", [])),
    }


def make_swapped_benchmark_row(row: Dict[str, Any], *, new_id: str, new_line_number: int) -> Dict[str, Any]:
    out = json.loads(json.dumps(row, ensure_ascii=False))
    out["swap_meta"] = {
        "swap_role": "swap_in",
        "source_dataset": "train764_excluding_hard300_ifclean",
        "source_id": row.get("id"),
        "source_line_number": row.get("line_number"),
    }
    out["id"] = new_id
    out["line_number"] = new_line_number
    return out


def make_swapped_train_row(row: Dict[str, Any], *, new_line_number: int) -> Dict[str, Any]:
    out = json.loads(json.dumps(row, ensure_ascii=False))
    out["swap_meta"] = {
        "swap_role": "swap_out_from_benchmark",
        "source_dataset": "tonight_hard300_ifclean",
        "source_id": row.get("id"),
        "source_line_number": row.get("line_number"),
    }
    out["line_number"] = new_line_number
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the agreed hard/train swap.")
    parser.add_argument(
        "--benchmark-jsonl",
        type=Path,
        default=ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard300_ifclean.jsonl",
    )
    parser.add_argument(
        "--benchmark-dashboard",
        type=Path,
        default=ROOT / "outputs" / "benchmark" / "_dashboard_data.json",
    )
    parser.add_argument(
        "--train-jsonl",
        type=Path,
        default=ROOT
        / "outputs"
        / "full_prompts"
        / "repaired_final_v3"
        / "finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl",
    )
    parser.add_argument(
        "--swap-in-csv",
        type=Path,
        default=ROOT / "outputs" / "reports" / "hard300_swap_in_noEG2_balanced_125_20260616.csv",
    )
    parser.add_argument(
        "--swap-out-csv",
        type=Path,
        default=ROOT / "outputs" / "reports" / "hard300_swap_out_exactpass_balanced_around100_20260616.csv",
    )
    parser.add_argument(
        "--out-benchmark-jsonl",
        type=Path,
        default=ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_ifclean_swap_in125_out100.jsonl",
    )
    parser.add_argument(
        "--out-benchmark-summary",
        type=Path,
        default=ROOT / "outputs" / "benchmark" / "finif_v2_tonight_hard325_ifclean_swap_in125_out100_summary.json",
    )
    parser.add_argument(
        "--out-benchmark-dashboard",
        type=Path,
        default=ROOT / "outputs" / "benchmark" / "_dashboard_data_swap_in125_out100.json",
    )
    parser.add_argument(
        "--out-train-jsonl",
        type=Path,
        default=ROOT
        / "outputs"
        / "full_prompts"
        / "repaired_final_v3"
        / "finif_v2_repaired_v3_train739_after_hardswap_in125_out100_ifclean.jsonl",
    )
    parser.add_argument(
        "--out-train-summary",
        type=Path,
        default=ROOT
        / "outputs"
        / "full_prompts"
        / "repaired_final_v3"
        / "finif_v2_repaired_v3_train739_after_hardswap_in125_out100_ifclean_summary.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "outputs" / "reports" / "hard300_train_swap_in125_out100_manifest_20260616.json",
    )
    args = parser.parse_args()

    benchmark_rows = read_jsonl(args.benchmark_jsonl)
    benchmark_dashboard_rows = json.loads(args.benchmark_dashboard.read_text(encoding="utf-8"))
    train_rows = read_jsonl(args.train_jsonl)
    swap_in_rows = read_csv_rows(args.swap_in_csv)
    swap_out_rows = read_csv_rows(args.swap_out_csv)

    bench_by_id = {str(row.get("id")): row for row in benchmark_rows}
    bench_dashboard_by_id = {str(row.get("id")): row for row in benchmark_dashboard_rows}
    train_by_id = {str(row.get("id")): row for row in train_rows}

    swap_in_ids = [str(row["id"]) for row in swap_in_rows]
    swap_out_ids = [str(row["bench_id"]) for row in swap_out_rows]

    missing_swap_in = [item_id for item_id in swap_in_ids if item_id not in train_by_id]
    missing_swap_out = [item_id for item_id in swap_out_ids if item_id not in bench_by_id]
    if missing_swap_in or missing_swap_out:
        raise SystemExit(
            json.dumps(
                {
                    "missing_swap_in": missing_swap_in[:10],
                    "missing_swap_out": missing_swap_out[:10],
                },
                ensure_ascii=False,
            )
        )

    kept_benchmark_rows = [row for row in benchmark_rows if str(row.get("id")) not in set(swap_out_ids)]
    kept_benchmark_dashboard_rows = [
        row for row in benchmark_dashboard_rows if str(row.get("id")) not in set(swap_out_ids)
    ]
    kept_train_rows = [row for row in train_rows if str(row.get("id")) not in set(swap_in_ids)]

    max_benchmark_line = max(int(row.get("line_number") or 0) for row in benchmark_rows)
    max_train_line = max(int(row.get("line_number") or 0) for row in train_rows)

    swapped_in_benchmark_rows: List[Dict[str, Any]] = []
    swapped_in_dashboard_rows: List[Dict[str, Any]] = []
    for index, item_id in enumerate(swap_in_ids, start=1):
        new_id = f"tonight_hard_swapin_{index:03d}"
        new_line_number = max_benchmark_line + index
        source_row = train_by_id[item_id]
        swapped_in_benchmark_rows.append(
            make_swapped_benchmark_row(source_row, new_id=new_id, new_line_number=new_line_number)
        )
        swapped_in_dashboard_rows.append(train_row_to_dashboard_item(source_row, new_id=new_id))

    swapped_out_train_rows: List[Dict[str, Any]] = []
    for index, item_id in enumerate(swap_out_ids, start=1):
        new_line_number = max_train_line + index
        source_row = bench_by_id[item_id]
        swapped_out_train_rows.append(make_swapped_train_row(source_row, new_line_number=new_line_number))

    new_benchmark_rows = kept_benchmark_rows + swapped_in_benchmark_rows
    new_benchmark_dashboard_rows = kept_benchmark_dashboard_rows + swapped_in_dashboard_rows
    new_train_rows = kept_train_rows + swapped_out_train_rows

    write_jsonl(args.out_benchmark_jsonl, new_benchmark_rows)
    write_jsonl(args.out_train_jsonl, new_train_rows)
    args.out_benchmark_dashboard.write_text(
        json.dumps(new_benchmark_dashboard_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    benchmark_summary = summarize_ifclean(new_benchmark_rows)
    benchmark_summary.update(
        {
            "version": "hard325-swap-in125-out100-v1",
            "input": str(args.benchmark_jsonl.relative_to(ROOT)),
            "swap_in_csv": str(args.swap_in_csv.relative_to(ROOT)),
            "swap_out_csv": str(args.swap_out_csv.relative_to(ROOT)),
            "output": str(args.out_benchmark_jsonl.relative_to(ROOT)),
            "dashboard_output": str(args.out_benchmark_dashboard.relative_to(ROOT)),
            "retained_benchmark_items": len(kept_benchmark_rows),
            "removed_exact_pass_items": len(swap_out_ids),
            "added_train_fail_items": len(swap_in_ids),
        }
    )
    args.out_benchmark_summary.write_text(
        json.dumps(benchmark_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    train_summary = summarize_ifclean(new_train_rows)
    train_summary.update(
        {
            "version": "train739-after-hardswap-in125-out100-v1",
            "input": str(args.train_jsonl.relative_to(ROOT)),
            "swap_in_csv": str(args.swap_out_csv.relative_to(ROOT)),
            "swap_out_csv": str(args.swap_in_csv.relative_to(ROOT)),
            "output": str(args.out_train_jsonl.relative_to(ROOT)),
            "retained_train_items": len(kept_train_rows),
            "removed_failed_items": len(swap_in_ids),
            "added_benchmark_exact_pass_items": len(swap_out_ids),
        }
    )
    args.out_train_summary.write_text(
        json.dumps(train_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "benchmark_before": {"items": len(benchmark_rows), "gpt5_exact_pass": 142, "pass_rate": 0.47333333333333333},
        "train_before": {"items": len(train_rows), "gpt5_exact_pass": 406, "pass_rate": 0.5314136125654451},
        "benchmark_after": {
            "items": len(new_benchmark_rows),
            "gpt5_exact_pass": 42,
            "pass_rate": 0.12923076923076923,
        },
        "train_after": {
            "items": len(new_train_rows),
            "gpt5_exact_pass": 506,
            "pass_rate": 0.6847090663058186,
        },
        "swap_in_count": len(swap_in_ids),
        "swap_out_count": len(swap_out_ids),
        "swap_in_workflow_counts": dict(Counter(row["workflow"] for row in swap_in_rows)),
        "swap_out_workflow_counts": dict(Counter(row["workflow"] for row in swap_out_rows)),
        "artifacts": {
            "benchmark_jsonl": str(args.out_benchmark_jsonl.relative_to(ROOT)),
            "benchmark_summary": str(args.out_benchmark_summary.relative_to(ROOT)),
            "benchmark_dashboard": str(args.out_benchmark_dashboard.relative_to(ROOT)),
            "train_jsonl": str(args.out_train_jsonl.relative_to(ROOT)),
            "train_summary": str(args.out_train_summary.relative_to(ROOT)),
        },
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
