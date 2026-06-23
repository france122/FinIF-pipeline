#!/usr/bin/env python3
"""Build a training pool that excludes only the exact-source hard300 items."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_hard300_aligned_ifclean.jsonl")
DEFAULT_BENCHMARK_360 = Path("outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl")
DEFAULT_HARD300 = Path("outputs/benchmark/finif_v2_tonight_hard300_ifclean.jsonl")
DEFAULT_OUTPUT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl")
DEFAULT_SUMMARY = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean_summary.json")
DEFAULT_AUDIT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean_audit.json")

IFCLEAN_BUILDER = REPO_ROOT / "outputs/benchmark/build_ifclean_benchmark.py"
VERSION = "train764-excluding-hard300-v1"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--benchmark360", type=Path, default=DEFAULT_BENCHMARK_360)
    parser.add_argument("--hard300", type=Path, default=DEFAULT_HARD300)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    ifclean_mod = load_module(IFCLEAN_BUILDER, "ifclean_builder")

    train_rows = load_jsonl(args.input)
    bench_rows = load_jsonl(args.benchmark360)
    hard_rows = load_jsonl(args.hard300)

    benchmark_id_by_line = {index + 1: row["id"] for index, row in enumerate(bench_rows)}
    excluded_ids = []
    for row in hard_rows:
        line_number = row.get("line_number")
        if line_number not in benchmark_id_by_line:
            raise KeyError(f"hard300 line_number {line_number!r} not found in benchmark360")
        excluded_ids.append(benchmark_id_by_line[line_number])
    excluded_set = set(excluded_ids)

    kept_rows = [row for row in train_rows if row.get("id") not in excluded_set]
    kept_ids = {row.get("id") for row in kept_rows}

    if len(excluded_set) != 300:
        raise ValueError(f"Expected 300 unique excluded ids, got {len(excluded_set)}")
    if len(kept_rows) != len(train_rows) - len(excluded_set):
        raise ValueError(
            f"Unexpected retained size: input={len(train_rows)} excluded={len(excluded_set)} kept={len(kept_rows)}"
        )
    if kept_ids & excluded_set:
        raise ValueError("Excluded hard300 source ids still remain in filtered train pool")

    write_jsonl(args.output, kept_rows)

    summary = ifclean_mod.summarize(kept_rows)
    summary.update(
        {
            "version": VERSION,
            "input": str(args.input),
            "benchmark360": str(args.benchmark360),
            "hard300": str(args.hard300),
            "output": str(args.output),
            "input_items": len(train_rows),
            "excluded_hard300_source_items": len(excluded_set),
            "retained_items": len(kept_rows),
        }
    )
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    audit = {
        "version": VERSION,
        "input_items": len(train_rows),
        "excluded_hard300_source_items": len(excluded_set),
        "retained_items": len(kept_rows),
        "excluded_source_ids_sample": sorted(excluded_set)[:50],
        "retained_overlap_with_excluded": len(kept_ids & excluded_set),
    }
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
