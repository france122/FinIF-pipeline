#!/usr/bin/env python3
"""Plot FinIF-test data statistics figures.

Default input is the current official FinIF-test slice (`benchmark307`).
The script outputs:
1. prompt length distribution
2. IF-constraint-count distribution
3. a combined 1x2 summary figure
4. a small JSON summary for paper writing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from statistics import mean, median

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "xdg-cache"))

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path("/Users/minimax/Desktop/lunwen")
DEFAULT_INPUT = ROOT / "outputs/benchmark/finif_v2_gpt55_targeted_benchmark307_20260616.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "outputs/analysis/finif_test_data_statistics"
WORD_RE = re.compile(r"\S+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot FinIF-test data statistics.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the FinIF-test JSONL file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for output figures and summary JSON.",
    )
    return parser.parse_args()


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def collect_stats(rows: list[dict]) -> dict:
    prompt_words = []
    if_constraint_counts = []
    diagnostic_constraint_counts = []
    llm_counts = []
    rule_counts = []
    workflow_counts = Counter()

    for row in rows:
        constraints = row.get("extracted_constraints", [])
        if_constraints = [c for c in constraints if c.get("include_in_isr", True)]
        diagnostic_constraints = row.get("diagnostic_constraints", [])

        prompt_words.append(count_words(row.get("full_prompt", "")))
        if_constraint_counts.append(len(if_constraints))
        diagnostic_constraint_counts.append(len(diagnostic_constraints))
        llm_counts.append(sum(1 for c in if_constraints if c.get("check_type") == "LLM"))
        rule_counts.append(sum(1 for c in if_constraints if c.get("check_type") == "rule"))
        workflow_counts[row.get("workflow", "Unknown")] += 1

    return {
        "prompt_words": prompt_words,
        "if_constraint_counts": if_constraint_counts,
        "diagnostic_constraint_counts": diagnostic_constraint_counts,
        "llm_counts": llm_counts,
        "rule_counts": rule_counts,
        "workflow_counts": dict(workflow_counts),
    }


def summarize(values: list[int]) -> dict:
    arr = np.asarray(values, dtype=float)
    return {
        "n": int(arr.size),
        "mean": round(float(arr.mean()), 4),
        "median": round(float(median(values)), 4),
        "min": int(arr.min()),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p90": round(float(np.percentile(arr, 90)), 4),
        "max": int(arr.max()),
    }


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#666666",
            "axes.linewidth": 0.8,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def plot_prompt_length_histogram(prompt_words: list[int], output_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.hist(
        prompt_words,
        bins=24,
        color="#8fb9e8",
        edgecolor="white",
        linewidth=0.9,
        alpha=0.9,
    )
    ax.axvline(mean(prompt_words), color="#2f5e9c", linestyle="--", linewidth=1.6, label=f"Mean = {mean(prompt_words):.1f}")
    ax.axvline(median(prompt_words), color="#d97706", linestyle="-.", linewidth=1.6, label=f"Median = {median(prompt_words):.0f}")
    ax.set_xlabel("Prompt length (words)")
    ax.set_ylabel("Count")
    ax.set_title("FinIF-test Prompt Length Distribution")
    ax.grid(axis="y")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_base.with_suffix(".png"), dpi=240, bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_constraint_count_bar(if_constraint_counts: list[int], output_base: Path) -> None:
    counter = Counter(if_constraint_counts)
    xs = sorted(counter)
    ys = [counter[x] for x in xs]

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    bars = ax.bar(xs, ys, width=0.72, color="#74b39a", edgecolor="white", linewidth=0.9)
    ax.axvline(mean(if_constraint_counts), color="#1f6f54", linestyle="--", linewidth=1.6, label=f"Mean = {mean(if_constraint_counts):.2f}")
    ax.set_xlabel("IF constraints per item")
    ax.set_ylabel("Count")
    ax.set_title("FinIF-test Constraint Count Distribution")
    ax.set_xticks(xs)
    ax.grid(axis="y")
    ax.legend(frameon=False)

    for bar, y in zip(bars, ys):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y + 1.2,
            str(y),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#374151",
        )

    fig.tight_layout()
    fig.savefig(output_base.with_suffix(".png"), dpi=240, bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_summary(prompt_words: list[int], if_constraint_counts: list[int], output_base: Path) -> None:
    counter = Counter(if_constraint_counts)
    xs = sorted(counter)
    ys = [counter[x] for x in xs]

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))

    axes[0].hist(
        prompt_words,
        bins=24,
        color="#8fb9e8",
        edgecolor="white",
        linewidth=0.9,
        alpha=0.9,
    )
    axes[0].axvline(mean(prompt_words), color="#2f5e9c", linestyle="--", linewidth=1.6)
    axes[0].axvline(median(prompt_words), color="#d97706", linestyle="-.", linewidth=1.6)
    axes[0].set_xlabel("Prompt length (words)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Prompt Length")
    axes[0].grid(axis="y")

    bars = axes[1].bar(xs, ys, width=0.72, color="#74b39a", edgecolor="white", linewidth=0.9)
    axes[1].axvline(mean(if_constraint_counts), color="#1f6f54", linestyle="--", linewidth=1.6)
    axes[1].set_xlabel("IF constraints per item")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Constraint Count")
    axes[1].set_xticks(xs)
    axes[1].grid(axis="y")
    for bar, y in zip(bars, ys):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            y + 1.2,
            str(y),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#374151",
        )

    fig.suptitle("FinIF-test Data Statistics", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_base.with_suffix(".png"), dpi=240, bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def write_summary(stats: dict, input_path: Path, output_path: Path) -> None:
    summary = {
        "dataset": str(input_path),
        "items": len(stats["prompt_words"]),
        "prompt_words": summarize(stats["prompt_words"]),
        "if_constraints_per_item": summarize(stats["if_constraint_counts"]),
        "diagnostic_constraints_per_item": summarize(stats["diagnostic_constraint_counts"]),
        "llm_constraints_per_item": summarize(stats["llm_counts"]),
        "rule_constraints_per_item": summarize(stats["rule_counts"]),
        "workflow_counts": stats["workflow_counts"],
    }
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    apply_style()

    rows = read_jsonl(args.input)
    stats = collect_stats(rows)

    plot_prompt_length_histogram(
        stats["prompt_words"],
        args.output_dir / "finif_test_prompt_length_distribution",
    )
    plot_constraint_count_bar(
        stats["if_constraint_counts"],
        args.output_dir / "finif_test_constraint_count_distribution",
    )
    plot_summary(
        stats["prompt_words"],
        stats["if_constraint_counts"],
        args.output_dir / "finif_test_data_statistics_summary",
    )
    write_summary(
        stats,
        args.input,
        args.output_dir / "finif_test_data_statistics_summary.json",
    )

    print(
        json.dumps(
            {
                "input": str(args.input),
                "output_dir": str(args.output_dir),
                "files": [
                    "finif_test_prompt_length_distribution.png",
                    "finif_test_prompt_length_distribution.pdf",
                    "finif_test_constraint_count_distribution.png",
                    "finif_test_constraint_count_distribution.pdf",
                    "finif_test_data_statistics_summary.png",
                    "finif_test_data_statistics_summary.pdf",
                    "finif_test_data_statistics_summary.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
