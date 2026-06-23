#!/usr/bin/env python3
"""Run the GPT-5 teacher train-pool pipeline after generation is complete.

This script assumes responses have already been generated and archived.
It then runs:
1. benchmark-aligned GPT-4o judging on the full 764-item train pool
2. fail-only repair rounds with GPT-5 + benchmark-aligned re-judging
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_DATASET = Path(
    "outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl"
)
DEFAULT_RESPONSES = Path("outputs/model_runs/gpt5_train764_teacher_generation_20260615/responses_gpt-5.jsonl")
DEFAULT_KEY = Path("key.md")


def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--judge-run-name", default="gpt5_train764_teacher_judge_gpt4o_20260615_r0")
    parser.add_argument("--repair-run-name", default="gpt5_train764_teacher_repair_loop_20260615")
    parser.add_argument("--judge-workers", type=int, default=16)
    parser.add_argument("--repair-workers", type=int, default=16)
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--repair-max-output-tokens", type=int, default=8192)
    parser.add_argument("--repair-reasoning-effort", default="low")
    parser.add_argument("--max-rounds", type=int, default=2)
    args = parser.parse_args()

    judge_cmd = [
        sys.executable,
        "evaluation/score_train_pool_with_benchmark_judge.py",
        "--dataset",
        str(args.dataset),
        "--responses",
        str(args.responses),
        "--run-name",
        args.judge_run_name,
        "--openai-key-file",
        str(args.key_file),
        "--judge-workers",
        str(args.judge_workers),
        "--judge-max-output-tokens",
        str(args.judge_max_output_tokens),
    ]
    run(judge_cmd)

    scores_path = Path("outputs/model_runs/train_pool_scoring") / args.judge_run_name / "scores_benchmark_aligned_judge.json"
    repair_cmd = [
        sys.executable,
        "evaluation/repair_train_pool_failed_items.py",
        "--dataset",
        str(args.dataset),
        "--responses",
        str(args.responses),
        "--scores",
        str(scores_path),
        "--key-file",
        str(args.key_file),
        "--run-name",
        args.repair_run_name,
        "--workers",
        str(args.repair_workers),
        "--judge-workers",
        str(args.judge_workers),
        "--judge-max-output-tokens",
        str(args.judge_max_output_tokens),
        "--max-output-tokens",
        str(args.repair_max_output_tokens),
        "--reasoning-effort",
        args.repair_reasoning_effort,
        "--max-rounds",
        str(args.max_rounds),
    ]
    run(repair_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
