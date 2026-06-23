"""Build hard300 reporting assets from existing score and fail-case files.

This script is local-only: it reads already-generated model run artifacts and
produces:

1. A consolidated hard300 results table in CSV and Markdown.
2. A priority GPT-5.5 audit queue for high-tension semantic tags.
3. A short Markdown note summarizing the audit focus and teacher choice.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "reports"

RUNS = [
    {
        "model": "GPT-5.5",
        "score_path": ROOT
        / "outputs/model_runs/gpt5.5_hard300_ifclean_generation_only_20260614/scores_gpt-5.5_judge_gpt4o.json",
        "fail_path": ROOT
        / "outputs/model_runs/gpt5.5_hard300_ifclean_generation_only_20260614/fail_cases/all_fail_cases.jsonl",
    },
    {
        "model": "GPT-5",
        "score_path": ROOT
        / "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/scores_gpt5_judge_gpt4o_combined.json",
        "fail_path": ROOT
        / "outputs/model_runs/gpt5_hard300_ifclean_combined_random50_plus_remaining250/fail_cases/all_fail_cases.jsonl",
    },
    {
        "model": "GLM5.1",
        "score_path": ROOT
        / "outputs/model_runs/glm5.1_siliconflow_hard300_ifclean_temp0_generation_only_20260614/scores_glm5.1_siliconflow_judge_gpt4o.json",
    },
    {
        "model": "DS-v4-pro",
        "score_path": ROOT
        / "outputs/model_runs/ds-v4-pro_hard300_ifclean_temp0_judge_gpt4o/scores_ds-v4-pro_judge_gpt4o.json",
    },
    {
        "model": "DS-v4-flash",
        "score_path": ROOT
        / "outputs/model_runs/ds-v4-flash_hard300_ifclean_temp0_judge_gpt4o/scores_ds-v4-flash_judge_gpt4o.json",
    },
    {
        "model": "Qwen3.5-27B",
        "score_path": ROOT
        / "outputs/model_runs/qwen3.5-27b_siliconflow_hard300_ifclean_temp0_judge_gpt4o/scores_qwen3.5-27b_siliconflow_judge_gpt4o.json",
    },
    {
        "model": "Qwen3.5-9B",
        "score_path": ROOT
        / "outputs/model_runs/qwen3.5-9b_siliconflow_hard300_ifclean_temp0_judge_gpt4o/scores_qwen3.5-9b_siliconflow_judge_gpt4o.json",
    },
    {
        "model": "Qwen3.5-4B",
        "score_path": ROOT
        / "outputs/model_runs/qwen3.5-4b_siliconflow_hard300_ifclean_temp0_judge_gpt4o/scores_qwen3.5-4b_siliconflow_judge_gpt4o.json",
    },
]

AUDIT_TAGS = ("EG2", "QV2", "DB9", "QV5", "DB7")
TAG_DESCRIPTIONS = {
    "EG2": "Key facts, thresholds, calculations, and decisions should carry active source labels at the point of use.",
    "QV2": "Each required calculation should show source inputs, formula/comparison, result, and business implication.",
    "DB9": "Evidence, rule, and action should form one reasoning chain rather than disconnected fragments.",
    "QV5": "Date/deadline tests should show source dates, timing logic, final status, and business implication.",
    "DB7": "Approver, authority evidence, prerequisite, or escalation boundary must be named explicitly.",
}


def read_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def format_pct(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{100 * float(value):.2f}%"


def build_results_rows() -> list[dict]:
    rows: list[dict] = []
    for run in RUNS:
        score_data = read_json(run["score_path"])
        summary = score_data.get("summary", score_data)
        items = score_data.get("items", [])
        if items:
            msr = sum(
                1
                for item in items
                if all(
                    result["score"] == 1
                    for result in item.get("results", [])
                    if result.get("effective_check_type") == "LLM"
                    or result.get("check_type") == "LLM"
                )
            ) / len(items)
            rsr = sum(
                1
                for item in items
                if all(
                    result["score"] == 1
                    for result in item.get("results", [])
                    if result.get("effective_check_type") == "rule"
                    or result.get("check_type") == "rule"
                )
            ) / len(items)
        else:
            msr = None
            rsr = None
        row = {
            "model": run["model"],
            "items": summary.get("items"),
            "msr": format_pct(msr),
            "rsr": format_pct(rsr),
            "osr_exact_item_pass_rate": format_pct(summary.get("exact_item_pass_rate")),
            "quality_mean_0_10": (
                f"{summary.get('quality_score_mean_0_10'):.2f}"
                if summary.get("quality_score_mean_0_10") is not None
                else ""
            ),
            "strict_failed_items": summary.get("strict_failed_items"),
            "passed_constraints": summary.get("passed_constraints"),
            "total_constraints": summary.get("total_constraints"),
            "score_path": str(run["score_path"].relative_to(ROOT)),
        }
        rows.append(row)
    rows.sort(key=lambda x: float(x["osr_exact_item_pass_rate"].rstrip("%")), reverse=True)
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_results_markdown(path: Path, rows: list[dict]) -> None:
    headers = [
        "Model",
        "MSR",
        "RSR",
        "OSR",
        "Quality",
    ]
    lines = [
        "# Hard300 Formal Results",
        "",
        "Compact reporting view for the formal hard300 comparison.",
        "`MSR`: prompt-level pass rate when all `LLM`-judged constraints pass.",
        "`RSR`: prompt-level pass rate when all `rule` constraints pass.",
        "`OSR`: prompt-level pass rate when all constraints pass.",
        "",
        "| " + " | ".join(headers) + " |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    row["msr"],
                    row["rsr"],
                    row["osr_exact_item_pass_rate"],
                    row["quality_mean_0_10"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Teacher recommendation for same-style distillation: prioritize `GPT-5.5`, with `GPT-5` as a secondary teacher or contrast baseline.",
            "Reason: they are the only models above 90% micro IF, and they preserve much higher work-product quality than the open-weight or lower-cost baselines.",
            "",
            "Caution: the original benchmark goal for the strongest model was `OSR <= 50%`; `GPT-5.5` is currently `58.67%`, so the benchmark is useful but still easier than the desired target line.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def build_eg2_findings() -> tuple[list[dict], dict[str, int]]:
    gpt55_run = next(run for run in RUNS if run["model"] == "GPT-5.5")
    fail_cases = read_jsonl(gpt55_run["fail_path"])
    findings: list[dict] = []
    counts = {
        "eg2_failed_cases": 0,
        "query_explicit": 0,
        "full_prompt_explicit": 0,
        "constraint_present": 0,
        "only_eg2_failed": 0,
    }
    for case in fail_cases:
        if "EG2" not in case.get("failed_tags", []):
            continue
        counts["eg2_failed_cases"] += 1
        query = case.get("query") or ""
        full_prompt = case.get("full_prompt") or ""
        eg2_constraints = [c for c in case.get("all_constraints", []) if c.get("tag") == "EG2"]
        query_explicit = "keep active source labels beside" in query.lower()
        prompt_explicit = "keep active source labels beside" in full_prompt.lower()
        if query_explicit:
            counts["query_explicit"] += 1
        if prompt_explicit:
            counts["full_prompt_explicit"] += 1
        if eg2_constraints:
            counts["constraint_present"] += 1
        eg2_only = case.get("failed_tags") == ["EG2"]
        if eg2_only:
            counts["only_eg2_failed"] += 1
        findings.append(
            {
                "item_id": case.get("item_id"),
                "workflow": case.get("workflow"),
                "task": case.get("task"),
                "if_score": case.get("summary", {}).get("score"),
                "quality_raw": case.get("quality", {}).get(
                    "raw_score", case.get("quality", {}).get("score")
                ),
                "failed_tags": ",".join(case.get("failed_tags", [])),
                "eg2_only": "yes" if eg2_only else "no",
                "query_explicit": "yes" if query_explicit else "no",
                "full_prompt_explicit": "yes" if prompt_explicit else "no",
                "constraint_present": "yes" if eg2_constraints else "no",
                "eg2_constraint": eg2_constraints[0].get("constraint") if eg2_constraints else "",
                "judge_reason": next(
                    fc.get("reason", "")
                    for fc in case.get("failed_constraints", [])
                    if fc.get("tag") == "EG2"
                ),
                "response_excerpt": case.get("response_excerpt", ""),
            }
        )
    findings.sort(
        key=lambda row: (
            row["eg2_only"] != "yes",
            -(row["quality_raw"] or -1),
            -(row["if_score"] or -1),
            row["item_id"],
        )
    )
    return findings, counts


def write_eg2_markdown(path: Path, counts: dict[str, int], findings: list[dict]) -> None:
    lines = [
        "# GPT-5.5 EG2 Findings",
        "",
        "Goal: determine whether EG2 failures come from missing constraints, model behavior, or judge tension.",
        "",
        "## Hard facts",
        "",
        f"- EG2 fail cases in GPT-5.5 hard300: `{counts['eg2_failed_cases']}`",
        f"- Cases whose `query` explicitly contains the hardening phrase: `{counts['query_explicit']}/{counts['eg2_failed_cases']}`",
        f"- Cases whose `full_prompt` explicitly contains the hardening phrase: `{counts['full_prompt_explicit']}/{counts['eg2_failed_cases']}`",
        f"- Cases whose `all_constraints` explicitly contain an EG2 constraint: `{counts['constraint_present']}/{counts['eg2_failed_cases']}`",
        f"- Cases where EG2 is the only failed tag: `{counts['only_eg2_failed']}/{counts['eg2_failed_cases']}`",
        "",
        "## Preliminary conclusion",
        "",
        "- `query 没写这条约束` is not the main explanation for GPT-5.5 EG2 failures in the current hard300 run.",
        "- Many EG2 fails are genuine model misses under the current benchmark wording: the response includes some labels, but not consistently at every controlling use point.",
        "- The main audit-risk subset is the `EG2-only` group, especially high-quality cases with `if_score >= 0.90`; these are the best candidates for checking whether judge interpretation of `active` and `next to` is too strict.",
        "",
        "## Manual audit shortlist",
        "",
        "Recommended first-pass EG2-only review items:",
    ]
    shortlist = 0
    for row in findings:
        if row["eg2_only"] != "yes":
            continue
        lines.append(
            f"- `{row['item_id']}` | {row['workflow']} | {row['task']} | IF `{row['if_score']:.3f}` | quality `{row['quality_raw']}` | {row['judge_reason']}"
        )
        shortlist += 1
        if shortlist >= 15:
            break
    lines.extend(
        [
            "",
            "## What to check in review",
            "",
            "- If unlabeled sentences merely restate a nearby labeled fact, decide whether that should still fail under the current rubric.",
            "- If a decision sentence or business-implication sentence has no label at the point of use, that looks more like a true model miss than a judge bug.",
            "- If the answer uses many labels but the judge still claims a broad EG2 failure, mark it as a potential rubric-tightening candidate.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def build_audit_queue_rows(limit_per_tag: int = 10) -> tuple[list[dict], dict[str, int]]:
    gpt55_run = next(run for run in RUNS if run["model"] == "GPT-5.5")
    fail_cases = read_jsonl(gpt55_run["fail_path"])
    tag_counts: Counter[str] = Counter()
    candidates: dict[str, list[dict]] = {tag: [] for tag in AUDIT_TAGS}

    for case in fail_cases:
        base = {
            "item_id": case.get("item_id"),
            "source_line": case.get("source_line"),
            "workflow": case.get("workflow"),
            "task": case.get("task"),
            "work_product": case.get("work_product"),
            "if_score": case.get("summary", {}).get("if_score"),
            "quality_score": case.get("quality", {}).get("score"),
            "failed_tag_count": len(case.get("failed_tags", [])),
            "failed_tags": ",".join(case.get("failed_tags", [])),
        }
        for constraint in case.get("failed_constraints", []):
            tag = constraint.get("tag")
            if tag not in AUDIT_TAGS:
                continue
            tag_counts[tag] += 1
            row = dict(base)
            row.update(
                {
                    "tag": tag,
                    "family": constraint.get("family"),
                    "check_type": constraint.get("check_type"),
                    "method": constraint.get("method"),
                    "constraint": constraint.get("constraint"),
                    "reason": constraint.get("reason"),
                    "audit_focus": TAG_DESCRIPTIONS[tag],
                }
            )
            candidates[tag].append(row)

    selected: list[dict] = []
    for tag in AUDIT_TAGS:
        rows = candidates[tag]
        rows.sort(
            key=lambda row: (
                -(row.get("quality_score") or -1),
                -(row.get("if_score") or -1),
                row.get("failed_tag_count") or 99,
                row.get("workflow") or "",
                row.get("item_id") or "",
            )
        )
        seen_items: set[str] = set()
        tag_selected = 0
        for row in rows:
            item_id = row["item_id"]
            if item_id in seen_items:
                continue
            seen_items.add(item_id)
            row["priority_rank_within_tag"] = tag_selected + 1
            selected.append(row)
            tag_selected += 1
            if tag_selected >= limit_per_tag:
                break
    selected.sort(key=lambda row: (AUDIT_TAGS.index(row["tag"]), row["priority_rank_within_tag"]))
    return selected, dict(tag_counts)


def write_audit_markdown(path: Path, queue_rows: list[dict], tag_counts: dict[str, int]) -> None:
    lines = [
        "# GPT-5.5 Priority Audit Queue",
        "",
        "Selection logic: prioritize high-quality or high-IF failures on the main semantic tension tags, because those are the best candidates for judge-rubric tightening or benchmark text repair.",
        "",
        "## Tag counts in GPT-5.5 hard300 fail cases",
        "",
        "| Tag | Failed constraints | Audit focus |",
        "|---|---:|---|",
    ]
    for tag in AUDIT_TAGS:
        lines.append(f"| {tag} | {tag_counts.get(tag, 0)} | {TAG_DESCRIPTIONS[tag]} |")

    lines.extend(
        [
            "",
            "## Review prompts",
            "",
            "- `EG2`: Did the response actually miss source labels at key use points, or is the judge over-penalizing perfectly readable local evidence anchoring?",
            "- `QV2`: Is the missing piece a real calculation-lineage failure, or did the answer already imply enough formula/result context for an audit-ready reader?",
            "- `DB9`: Is the reasoning truly fragmented, or is the judge preferring one rhetorical style over another coherent workflow style?",
            "- `QV5`: Did the response omit timing logic, or is the requirement itself too broad for simple date-status tasks?",
            "- `DB7`: Did the answer really miss approver/prerequisite naming, or is the packet itself underspecified and the response appropriately conservative?",
            "",
            "## Recommended training implication",
            "",
            "- Distillation teacher priority: `GPT-5.5` first, `GPT-5` second.",
            "- Improvement target for smaller models: train toward evidence placement, quantitative lineage, and action-boundary closure rather than only generic report fluency.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results_rows = build_results_rows()
    write_csv(
        OUTPUT_DIR / "hard300_formal_results.csv",
        results_rows,
        [
            "model",
            "items",
            "msr",
            "rsr",
            "osr_exact_item_pass_rate",
            "quality_mean_0_10",
            "strict_failed_items",
            "passed_constraints",
            "total_constraints",
            "score_path",
        ],
    )
    write_results_markdown(OUTPUT_DIR / "hard300_formal_results.md", results_rows)

    audit_rows, tag_counts = build_audit_queue_rows()
    write_csv(
        OUTPUT_DIR / "gpt55_priority_audit_queue.csv",
        audit_rows,
        [
            "tag",
            "priority_rank_within_tag",
            "item_id",
            "source_line",
            "workflow",
            "task",
            "work_product",
            "if_score",
            "quality_score",
            "failed_tag_count",
            "failed_tags",
            "family",
            "check_type",
            "method",
            "constraint",
            "reason",
            "audit_focus",
        ],
    )
    write_audit_markdown(OUTPUT_DIR / "gpt55_priority_audit_notes.md", audit_rows, tag_counts)

    eg2_rows, eg2_counts = build_eg2_findings()
    write_csv(
        OUTPUT_DIR / "gpt55_eg2_findings.csv",
        eg2_rows,
        [
            "item_id",
            "workflow",
            "task",
            "if_score",
            "quality_raw",
            "failed_tags",
            "eg2_only",
            "query_explicit",
            "full_prompt_explicit",
            "constraint_present",
            "eg2_constraint",
            "judge_reason",
            "response_excerpt",
        ],
    )
    write_eg2_markdown(OUTPUT_DIR / "gpt55_eg2_findings.md", eg2_counts, eg2_rows)


if __name__ == "__main__":
    main()
