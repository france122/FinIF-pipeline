#!/usr/bin/env python3

import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt
import numpy as np
from datasets import load_dataset


ROOT = Path("/Users/minimax/Desktop/lunwen")
BENCHMARK307_PATH = ROOT / "outputs/benchmark/finif_v2_gpt55_targeted_benchmark307_20260616.jsonl"
OUTPUT_DIR = ROOT / "outputs/analysis/benchmark307_vs_ifeval"


WORD_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def percentile(values, q):
    if not values:
        return None
    return float(np.percentile(np.array(values, dtype=float), q))


def summarize(values):
    values = list(values)
    return {
        "n": len(values),
        "mean": round(mean(values), 4) if values else None,
        "median": round(median(values), 4) if values else None,
        "min": min(values) if values else None,
        "p10": round(percentile(values, 10), 4) if values else None,
        "p25": round(percentile(values, 25), 4) if values else None,
        "p75": round(percentile(values, 75), 4) if values else None,
        "p90": round(percentile(values, 90), 4) if values else None,
        "p95": round(percentile(values, 95), 4) if values else None,
        "max": max(values) if values else None,
    }


def load_benchmark307():
    rows = []
    family_counter = Counter()
    tag_counter = Counter()
    with BENCHMARK307_PATH.open() as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            full_prompt = obj["full_prompt"]
            query = obj.get("query", "")
            source_registry = obj.get("source_registry", [])
            extracted_constraints = obj.get("extracted_constraints", [])
            diagnostic_constraints = obj.get("diagnostic_constraints", [])
            for c in extracted_constraints:
                family_counter[c.get("family", "Unknown")] += 1
                tag_counter[c.get("tag", "Unknown")] += 1
            source_word_counts = [count_words(src.get("content", "")) for src in source_registry]
            rows.append(
                {
                    "id": obj["id"],
                    "workflow": obj.get("workflow", "Unknown"),
                    "task": obj.get("task", "Unknown"),
                    "full_prompt_chars": len(full_prompt),
                    "full_prompt_words": count_words(full_prompt),
                    "query_chars": len(query),
                    "query_words": count_words(query),
                    "source_docs": len(source_registry),
                    "source_words_total": sum(source_word_counts),
                    "source_words_mean": round(mean(source_word_counts), 4) if source_word_counts else 0.0,
                    "if_constraints": len(extracted_constraints),
                    "diagnostic_constraints": len(diagnostic_constraints),
                    "llm_constraints": sum(1 for c in extracted_constraints if c.get("check_type") == "LLM"),
                    "rule_constraints": sum(1 for c in extracted_constraints if c.get("check_type") == "rule"),
                    "format_constraints": sum(1 for c in extracted_constraints if c.get("if_supertype") == "format"),
                    "semantic_constraints": sum(1 for c in extracted_constraints if c.get("if_supertype") == "semantic"),
                    "has_public_overlay": bool(obj.get("public_excerpt_overlay")),
                }
            )
    return rows, family_counter, tag_counter


def load_ifeval():
    ds = load_dataset("google/IFEval", split="train")
    rows = []
    for row in ds:
        prompt = row["prompt"]
        instruction_ids = row["instruction_id_list"]
        rows.append(
            {
                "key": row["key"],
                "prompt_chars": len(prompt),
                "prompt_words": count_words(prompt),
                "constraints": len(instruction_ids),
            }
        )
    return rows


def overlap_interval(a_values, b_values):
    lo = max(min(a_values), min(b_values))
    hi = min(max(a_values), max(b_values))
    if lo > hi:
        return None
    return [lo, hi]


def overlap_count(values, interval):
    if not interval:
        return 0
    lo, hi = interval
    return sum(1 for v in values if lo <= v <= hi)


def make_histogram(finif_values, ifeval_values, xlabel, title, out_path, bins=30):
    plt.figure(figsize=(8.5, 5.6))
    plt.hist(finif_values, bins=bins, alpha=0.45, label="FinIF-test (benchmark307)", color="#84b6eb", edgecolor="white")
    plt.hist(ifeval_values, bins=bins, alpha=0.35, label="IFEval", color="#f2b49d", edgecolor="white")
    plt.yscale("log")
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.title(title)
    plt.grid(axis="y", linestyle="--", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()


def make_agentif_style_histogram(finif_values, ifeval_values, xlabel, out_path, x_max=None, bins=26):
    plt.figure(figsize=(6.2, 5.1))
    ax = plt.gca()
    ax.set_facecolor("white")

    if x_max is None:
        x_max = max(max(finif_values), max(ifeval_values))
    bin_edges = np.linspace(0, x_max, bins + 1)

    plt.hist(
        finif_values,
        bins=bin_edges,
        alpha=0.55,
        label="FinIF-test",
        color="#b8d6f1",
        edgecolor="white",
        linewidth=0.8,
    )
    plt.hist(
        ifeval_values,
        bins=bin_edges,
        alpha=0.55,
        label="IFEval",
        color="#f7d2c6",
        edgecolor="white",
        linewidth=0.8,
    )
    plt.yscale("log")
    plt.xlabel(xlabel, fontsize=11)
    plt.ylabel("Count", fontsize=11)
    plt.xlim(0, x_max)
    plt.grid(True, axis="both", linestyle="--", linewidth=0.5, alpha=0.3)
    plt.legend(loc="upper left", ncol=2, frameon=True, fontsize=10)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#666666")
    ax.spines["bottom"].set_color("#666666")
    ax.tick_params(labelsize=10)

    plt.tight_layout()
    plt.savefig(out_path, dpi=260, bbox_inches="tight")
    plt.close()


def make_logx_word_histogram(finif_values, ifeval_values, out_path):
    plt.figure(figsize=(6.4, 5.2))
    ax = plt.gca()
    ax.set_facecolor("white")

    min_word = min(min(finif_values), min(ifeval_values))
    max_word = max(max(finif_values), max(ifeval_values))
    bin_edges = np.logspace(math.log10(min_word), math.log10(max_word), 26)

    plt.hist(
        finif_values,
        bins=bin_edges,
        alpha=0.55,
        label="FinIF-test",
        color="#b8d6f1",
        edgecolor="white",
        linewidth=0.8,
    )
    plt.hist(
        ifeval_values,
        bins=bin_edges,
        alpha=0.55,
        label="IFEval",
        color="#f7d2c6",
        edgecolor="white",
        linewidth=0.8,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Length (words)", fontsize=11)
    plt.ylabel("Count", fontsize=11)
    plt.grid(True, axis="both", linestyle="--", linewidth=0.5, alpha=0.3)
    plt.legend(loc="upper left", ncol=2, frameon=True, fontsize=10)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#666666")
    ax.spines["bottom"].set_color("#666666")
    ax.tick_params(labelsize=10)

    plt.tight_layout()
    plt.savefig(out_path, dpi=260, bbox_inches="tight")
    plt.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close()


def make_summary_figure(finif_rows, ifeval_rows, out_path):
    finif_words = [r["full_prompt_words"] for r in finif_rows]
    ifeval_words = [r["prompt_words"] for r in ifeval_rows]
    finif_chars = [r["full_prompt_chars"] for r in finif_rows]
    ifeval_chars = [r["prompt_chars"] for r in ifeval_rows]
    source_docs = [r["source_docs"] for r in finif_rows]
    if_constraints = [r["if_constraints"] for r in finif_rows]
    ifeval_constraints = [r["constraints"] for r in ifeval_rows]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    axes[0, 0].hist(finif_words, bins=28, alpha=0.45, label="FinIF-test", color="#84b6eb", edgecolor="white")
    axes[0, 0].hist(ifeval_words, bins=28, alpha=0.35, label="IFEval", color="#f2b49d", edgecolor="white")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_xlabel("Full prompt length (words)")
    axes[0, 0].set_ylabel("Count")
    axes[0, 0].set_title("Length Distribution (words)")
    axes[0, 0].legend()
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.25)

    axes[0, 1].hist(finif_chars, bins=28, alpha=0.45, label="FinIF-test", color="#84b6eb", edgecolor="white")
    axes[0, 1].hist(ifeval_chars, bins=28, alpha=0.35, label="IFEval", color="#f2b49d", edgecolor="white")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_xlabel("Full prompt length (characters)")
    axes[0, 1].set_ylabel("Count")
    axes[0, 1].set_title("Length Distribution (characters)")
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.25)

    finif_constraint_counter = Counter(if_constraints)
    ifeval_constraint_counter = Counter(ifeval_constraints)
    xs = sorted(set(finif_constraint_counter) | set(ifeval_constraint_counter))
    axes[1, 0].bar([x - 0.18 for x in xs], [finif_constraint_counter.get(x, 0) for x in xs], width=0.36, label="FinIF-test", color="#84b6eb")
    axes[1, 0].bar([x + 0.18 for x in xs], [ifeval_constraint_counter.get(x, 0) for x in xs], width=0.36, label="IFEval", color="#f2b49d")
    axes[1, 0].set_xlabel("IF constraints per item")
    axes[1, 0].set_ylabel("Count")
    axes[1, 0].set_title("Constraint Density")
    axes[1, 0].legend()
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.25)

    source_counter = Counter(source_docs)
    xs = sorted(source_counter)
    axes[1, 1].bar(xs, [source_counter[x] for x in xs], color="#5aa38d")
    axes[1, 1].set_xlabel("Source materials per FinIF-test item")
    axes[1, 1].set_ylabel("Count")
    axes[1, 1].set_title("Source-Material Density")
    axes[1, 1].grid(axis="y", linestyle="--", alpha=0.25)

    fig.suptitle("FinIF-test (benchmark307) vs IFEval", fontsize=16)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def build_report(finif_rows, ifeval_rows, family_counter, tag_counter):
    workflow_counter = Counter(r["workflow"] for r in finif_rows)
    task_counter = Counter(r["task"] for r in finif_rows)
    workflow_stats = {}
    for workflow in workflow_counter:
        subset = [r for r in finif_rows if r["workflow"] == workflow]
        workflow_stats[workflow] = {
            "items": len(subset),
            "mean_full_prompt_words": round(mean(r["full_prompt_words"] for r in subset), 4),
            "mean_if_constraints": round(mean(r["if_constraints"] for r in subset), 4),
            "mean_source_docs": round(mean(r["source_docs"] for r in subset), 4),
        }

    finif_stats = {
        "file": str(BENCHMARK307_PATH),
        "items": len(finif_rows),
        "full_prompt_words": summarize(r["full_prompt_words"] for r in finif_rows),
        "full_prompt_chars": summarize(r["full_prompt_chars"] for r in finif_rows),
        "query_words": summarize(r["query_words"] for r in finif_rows),
        "source_docs": summarize(r["source_docs"] for r in finif_rows),
        "source_words_total": summarize(r["source_words_total"] for r in finif_rows),
        "if_constraints": summarize(r["if_constraints"] for r in finif_rows),
        "diagnostic_constraints": summarize(r["diagnostic_constraints"] for r in finif_rows),
        "llm_constraints": summarize(r["llm_constraints"] for r in finif_rows),
        "rule_constraints": summarize(r["rule_constraints"] for r in finif_rows),
        "format_constraints": summarize(r["format_constraints"] for r in finif_rows),
        "semantic_constraints": summarize(r["semantic_constraints"] for r in finif_rows),
        "public_overlay_items": sum(1 for r in finif_rows if r["has_public_overlay"]),
        "public_overlay_ratio": round(sum(1 for r in finif_rows if r["has_public_overlay"]) / len(finif_rows), 4),
        "workflow_counts": dict(workflow_counter),
        "workflow_stats": workflow_stats,
        "task_type_count": len(task_counter),
        "top_tasks": task_counter.most_common(15),
        "constraint_family_counts": dict(family_counter),
        "top_constraint_tags": tag_counter.most_common(20),
    }

    ifeval_stats = {
        "source": "google/IFEval train split from Hugging Face datasets",
        "items": len(ifeval_rows),
        "prompt_words": summarize(r["prompt_words"] for r in ifeval_rows),
        "prompt_chars": summarize(r["prompt_chars"] for r in ifeval_rows),
        "constraints": summarize(r["constraints"] for r in ifeval_rows),
    }

    finif_words = [r["full_prompt_words"] for r in finif_rows]
    ifeval_words = [r["prompt_words"] for r in ifeval_rows]
    finif_chars = [r["full_prompt_chars"] for r in finif_rows]
    ifeval_chars = [r["prompt_chars"] for r in ifeval_rows]

    word_overlap = overlap_interval(finif_words, ifeval_words)
    char_overlap = overlap_interval(finif_chars, ifeval_chars)

    comparison = {
        "full_prompt_word_overlap": {
            "overlap_interval": word_overlap,
            "finif_items_in_overlap": overlap_count(finif_words, word_overlap),
            "ifeval_items_in_overlap": overlap_count(ifeval_words, word_overlap),
        },
        "full_prompt_char_overlap": {
            "overlap_interval": char_overlap,
            "finif_items_in_overlap": overlap_count(finif_chars, char_overlap),
            "ifeval_items_in_overlap": overlap_count(ifeval_chars, char_overlap),
        },
        "mean_word_length_ratio_finif_over_ifeval": round(finif_stats["full_prompt_words"]["mean"] / ifeval_stats["prompt_words"]["mean"], 4),
        "median_word_length_ratio_finif_over_ifeval": round(finif_stats["full_prompt_words"]["median"] / ifeval_stats["prompt_words"]["median"], 4),
        "mean_constraint_ratio_finif_over_ifeval": round(finif_stats["if_constraints"]["mean"] / ifeval_stats["constraints"]["mean"], 4),
    }

    return {
        "finif_test_benchmark307": finif_stats,
        "ifeval": ifeval_stats,
        "comparison": comparison,
    }


def write_markdown(report, out_path):
    finif = report["finif_test_benchmark307"]
    ifeval = report["ifeval"]
    comp = report["comparison"]
    lines = [
        "# benchmark307 / FinIF-test Data Statistics",
        "",
        "## Core comparison",
        "",
        f"- FinIF-test (`benchmark307`) items: {finif['items']}",
        f"- IFEval items: {ifeval['items']}",
        f"- FinIF-test full_prompt words: mean {finif['full_prompt_words']['mean']}, median {finif['full_prompt_words']['median']}, min {finif['full_prompt_words']['min']}, max {finif['full_prompt_words']['max']}",
        f"- IFEval prompt words: mean {ifeval['prompt_words']['mean']}, median {ifeval['prompt_words']['median']}, min {ifeval['prompt_words']['min']}, max {ifeval['prompt_words']['max']}",
        f"- FinIF-test full_prompt chars: mean {finif['full_prompt_chars']['mean']}, median {finif['full_prompt_chars']['median']}, min {finif['full_prompt_chars']['min']}, max {finif['full_prompt_chars']['max']}",
        f"- IFEval prompt chars: mean {ifeval['prompt_chars']['mean']}, median {ifeval['prompt_chars']['median']}, min {ifeval['prompt_chars']['min']}, max {ifeval['prompt_chars']['max']}",
        f"- FinIF-test / IFEval mean word-length ratio: {comp['mean_word_length_ratio_finif_over_ifeval']}",
        f"- FinIF-test / IFEval median word-length ratio: {comp['median_word_length_ratio_finif_over_ifeval']}",
        f"- FinIF-test IF constraints per item: mean {finif['if_constraints']['mean']}, median {finif['if_constraints']['median']}, min {finif['if_constraints']['min']}, max {finif['if_constraints']['max']}",
        f"- IFEval constraints per item: mean {ifeval['constraints']['mean']}, median {ifeval['constraints']['median']}, min {ifeval['constraints']['min']}, max {ifeval['constraints']['max']}",
        f"- FinIF-test / IFEval mean constraint ratio: {comp['mean_constraint_ratio_finif_over_ifeval']}",
        "",
        "## FinIF-test structure",
        "",
        f"- Source materials per item: mean {finif['source_docs']['mean']}, median {finif['source_docs']['median']}, min {finif['source_docs']['min']}, max {finif['source_docs']['max']}",
        f"- Source-material words per item: mean {finif['source_words_total']['mean']}, median {finif['source_words_total']['median']}, min {finif['source_words_total']['min']}, max {finif['source_words_total']['max']}",
        f"- Query-only words: mean {finif['query_words']['mean']}, median {finif['query_words']['median']}, min {finif['query_words']['min']}, max {finif['query_words']['max']}",
        f"- LLM constraints per item: mean {finif['llm_constraints']['mean']}",
        f"- Rule constraints per item: mean {finif['rule_constraints']['mean']}",
        f"- Format constraints per item: mean {finif['format_constraints']['mean']}",
        f"- Semantic constraints per item: mean {finif['semantic_constraints']['mean']}",
        f"- Items with public excerpt overlay: {finif['public_overlay_items']} / {finif['items']} ({round(finif['public_overlay_ratio'] * 100, 2)}%)",
        f"- Workflow coverage: {len(finif['workflow_counts'])} workflows",
        f"- Task coverage: {finif['task_type_count']} task types",
        "",
        "## Workflow counts",
        "",
    ]
    for workflow, count in finif["workflow_counts"].items():
        lines.append(f"- {workflow}: {count}")
    lines += [
        "",
        "## Workflow means",
        "",
    ]
    for workflow, stats in finif["workflow_stats"].items():
        lines.append(
            f"- {workflow}: mean prompt words {stats['mean_full_prompt_words']}, mean IF constraints {stats['mean_if_constraints']}, mean source docs {stats['mean_source_docs']}"
        )
    lines += [
        "",
        "## Top task counts",
        "",
    ]
    for task, count in finif["top_tasks"]:
        lines.append(f"- {task}: {count}")
    lines += [
        "",
        "## Constraint family counts",
        "",
    ]
    for family, count in finif["constraint_family_counts"].items():
        lines.append(f"- {family}: {count}")
    lines += [
        "",
        "## Top constraint tags",
        "",
    ]
    for tag, count in finif["top_constraint_tags"]:
        lines.append(f"- {tag}: {count}")
    out_path.write_text("\n".join(lines) + "\n")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    finif_rows, family_counter, tag_counter = load_benchmark307()
    ifeval_rows = load_ifeval()
    report = build_report(finif_rows, ifeval_rows, family_counter, tag_counter)

    stats_path = OUTPUT_DIR / "benchmark307_vs_ifeval_stats.json"
    report_path = OUTPUT_DIR / "benchmark307_vs_ifeval_stats.md"
    word_hist_path = OUTPUT_DIR / "benchmark307_vs_ifeval_full_prompt_words_logcount.png"
    char_hist_path = OUTPUT_DIR / "benchmark307_vs_ifeval_full_prompt_chars_logcount.png"
    char_hist_agentif_style_path = OUTPUT_DIR / "benchmark307_vs_ifeval_full_prompt_chars_agentif_style.png"
    word_hist_agentif_style_path = OUTPUT_DIR / "benchmark307_vs_ifeval_full_prompt_words_agentif_style.png"
    word_hist_logx_path = OUTPUT_DIR / "benchmark307_vs_ifeval_full_prompt_words_logx_logy.png"
    summary_fig_path = OUTPUT_DIR / "benchmark307_vs_ifeval_summary.png"

    stats_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    write_markdown(report, report_path)
    make_histogram(
        [r["full_prompt_words"] for r in finif_rows],
        [r["prompt_words"] for r in ifeval_rows],
        "Length (words)",
        "Full Prompt Length Distribution: FinIF-test vs IFEval",
        word_hist_path,
    )
    make_histogram(
        [r["full_prompt_chars"] for r in finif_rows],
        [r["prompt_chars"] for r in ifeval_rows],
        "Length (characters)",
        "Full Prompt Length Distribution: FinIF-test vs IFEval",
        char_hist_path,
    )
    make_agentif_style_histogram(
        [r["full_prompt_chars"] for r in finif_rows],
        [r["prompt_chars"] for r in ifeval_rows],
        "Length",
        char_hist_agentif_style_path,
        x_max=16000,
        bins=26,
    )
    make_agentif_style_histogram(
        [r["full_prompt_words"] for r in finif_rows],
        [r["prompt_words"] for r in ifeval_rows],
        "Length",
        word_hist_agentif_style_path,
        x_max=2300,
        bins=24,
    )
    make_logx_word_histogram(
        [r["full_prompt_words"] for r in finif_rows],
        [r["prompt_words"] for r in ifeval_rows],
        word_hist_logx_path,
    )
    make_summary_figure(finif_rows, ifeval_rows, summary_fig_path)

    print(json.dumps({
        "stats_json": str(stats_path),
        "stats_md": str(report_path),
        "word_histogram": str(word_hist_path),
        "char_histogram": str(char_hist_path),
        "word_histogram_agentif_style": str(word_hist_agentif_style_path),
        "word_histogram_logx_logy": str(word_hist_logx_path),
        "char_histogram_agentif_style": str(char_hist_agentif_style_path),
        "summary_figure": str(summary_fig_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
