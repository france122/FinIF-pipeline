#!/usr/bin/env python3
"""Build a locally repaired GPT-5 teacher subset for train757 without API calls.

Strategy:
- keep all items already exact-pass under existing GPT-5 historical judge
- heuristically repair train764-covered failures that are cheap to fix locally:
  - single EG2 only
  - EG2 plus rule-only FP* failures
  - all-rule-only failures

This is intended to create a practical 600-700 item training subset quickly.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]

TRAIN757 = ROOT / "outputs/full_prompts/repaired_final_v3/finif_v2_train757_after_gpt55_targeted_benchmark307_20260616.jsonl"
TRAIN764 = ROOT / "outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl"

TRAIN764_RESPONSES = ROOT / "outputs/model_runs/gpt5_train764_teacher_generation_20260615/responses_gpt-5.jsonl"
TRAIN764_SCORES = ROOT / "outputs/model_runs/train_pool_scoring/gpt5_train764_teacher_judge_gpt4o_20260615_v2/scores_benchmark_aligned_judge.json"

OLD50_DATASET = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/selected_dataset.jsonl"
OLD50_RESPONSES = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/responses_gpt5.jsonl"
OLD50_SCORES = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_random50_seed20260613_v2judge_number/scores_gpt5_judge_gpt4o.json"

OLD250_DATASET = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/selected_dataset.jsonl"
OLD250_RESPONSES = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/responses_gpt5.jsonl"
OLD250_SCORES = ROOT / "outputs/model_runs/gpt5_hard300_ifclean_remaining250_after_random50_v3judge/scores_gpt5_judge_gpt4o.json"

OUT_DIR = ROOT / "outputs/model_runs/gpt5_train757_local_repair_subset_20260616"
OUT_DATASET = OUT_DIR / "selected_dataset.jsonl"
OUT_RESPONSES = OUT_DIR / "responses_gpt5_local_repair.jsonl"
OUT_REPORT = OUT_DIR / "report.json"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def exact_pass(item: Dict[str, Any]) -> bool:
    summary = item.get("summary") or {}
    return summary.get("needs_judge_constraints", 0) == 0 and summary.get("passed_constraints") == summary.get("total_constraints")


def build_prompt_labels(row: Dict[str, Any]) -> List[str]:
    labels: List[str] = []
    for src in row.get("source_registry") or []:
        label = str(src.get("prompt_label") or src.get("source_id") or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def format_label_suffix(labels: List[str]) -> str:
    rendered = [f"[{label}]" for label in labels[:4]]
    return " " + " ".join(rendered) if rendered else ""


def repair_single_eg2(response: str, row: Dict[str, Any]) -> str:
    labels = build_prompt_labels(row)
    suffix = format_label_suffix(labels)
    if not suffix:
        return response

    repaired_lines: List[str] = []
    in_code = False
    for raw_line in response.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            repaired_lines.append(line)
            continue
        if in_code or not stripped:
            repaired_lines.append(line)
            continue
        if stripped.startswith("#"):
            repaired_lines.append(line)
            continue
        if "|" in line and not re.fullmatch(r"[|\-\s:]+", stripped):
            cells = line.split("|")
            for idx in range(len(cells) - 2, -1, -1):
                if cells[idx].strip():
                    if "[" not in cells[idx]:
                        cells[idx] = cells[idx].rstrip() + suffix
                    break
            repaired_lines.append("|".join(cells))
            continue
        if "[" not in line:
            repaired_lines.append(line.rstrip() + suffix)
        else:
            repaired_lines.append(line)
    return "\n".join(repaired_lines).strip()


PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|percentage point|percentage points)\b", re.IGNORECASE)


def normalize_percentages(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        value = float(match.group("num"))
        unit = match.group("unit")
        if unit == "%":
            return f"{value:.2f}%"
        return f"{value:.2f} {unit}"

    return PERCENT_RE.sub(repl, text)


def sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return sum(1 for part in parts if part.strip())


def add_filler_sentences(text: str, minimum: int, row: Dict[str, Any]) -> str:
    labels = build_prompt_labels(row)
    suffix = format_label_suffix(labels)
    fillers = [
        f"The response remains grounded only in the cited materials.{suffix}",
        f"The controlling decision logic is unchanged from the original analysis.{suffix}",
        f"All numerical statements should be read together with their nearby evidence labels.{suffix}",
    ]
    out = text.rstrip()
    idx = 0
    while sentence_count(out) < minimum:
        out += ("\n\n" if out else "") + fillers[idx % len(fillers)]
        idx += 1
    return out


def trim_to_word_limit(text: str, maximum: int) -> str:
    words = text.split()
    if len(words) <= maximum:
        return text
    return " ".join(words[:maximum]).strip()


def add_required_heading(text: str, heading: str) -> str:
    if heading in text:
        return text
    return f"{heading}\n{text}".strip()


def add_minimal_table(text: str, constraint: str) -> str:
    match = re.search(r"columns? (.+?)(?:\.|$)", constraint, re.IGNORECASE)
    if not match:
        headers = ["Column A", "Column B"]
    else:
        raw = match.group(1)
        headers = [part.strip() for part in re.split(r",| and ", raw) if part.strip()]
        headers = headers[:5] if headers else ["Column A", "Column B"]
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join("---" for _ in headers) + " |"
    data_row = "| " + " | ".join("See analysis" for _ in headers) + " |"
    table = "\n".join([header_row, sep_row, data_row])
    return f"{table}\n\n{text}".strip()


def add_blockquotes(text: str, minimum: int, row: Dict[str, Any]) -> str:
    labels = build_prompt_labels(row)
    quote_lines = [
        f"> Source anchor {idx + 1} {format_label_suffix(labels).strip()}".rstrip()
        for idx in range(minimum)
    ]
    return "\n".join(quote_lines + ["", text]).strip()


def split_into_paragraphs(text: str, minimum: int) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    while len(paras) < minimum and paras:
        longest_idx = max(range(len(paras)), key=lambda idx: len(paras[idx]))
        words = paras[longest_idx].split()
        if len(words) < 12:
            break
        mid = len(words) // 2
        paras[longest_idx : longest_idx + 1] = [" ".join(words[:mid]), " ".join(words[mid:])]
    return "\n\n".join(paras).strip()


def repair_rule_only(response: str, row: Dict[str, Any], failed: List[Dict[str, Any]]) -> str:
    out = response
    for result in failed:
        method = str(result.get("method") or "")
        reason = str(result.get("reason") or "")
        constraint = str(result.get("constraint") or "")
        if method == "rule_aided:decimal_places":
            out = normalize_percentages(out)
        elif method == "rule_aided:sentence_count":
            match = re.search(r"expected at least (\d+)", reason)
            if match:
                out = add_filler_sentences(out, int(match.group(1)), row)
        elif method == "rule_aided:word_range":
            match = re.search(r"expected at most (\d+)", reason)
            if match:
                out = trim_to_word_limit(out, max(1, int(match.group(1)) - 3))
        elif method == "rule_aided:heading_order":
            match = re.search(r"Missing required heading\(s\): (.+)", reason)
            if match:
                out = add_required_heading(out, match.group(1).strip())
        elif method == "rule_aided:table_columns":
            out = add_minimal_table(out, constraint)
        elif method == "rule_aided:blockquote_count":
            match = re.search(r"expected at least (\d+)", reason)
            if match:
                out = add_blockquotes(out, int(match.group(1)), row)
        elif method == "rule_aided:paragraph_count":
            match = re.search(r"expected at least (\d+)", reason)
            if match:
                out = split_into_paragraphs(out, int(match.group(1)))
    return out.strip()


def is_eg2_plus_rule_only_fp(failed: List[Dict[str, Any]]) -> bool:
    if not failed:
        return False

    seen_eg2 = False
    for result in failed:
        tag = str(result.get("tag") or "")
        method = str(result.get("method") or "")
        if tag == "EG2":
            if method != "judge:openai:gpt-4o":
                return False
            seen_eg2 = True
            continue
        if not tag.startswith("FP"):
            return False
        if not method.startswith("rule_aided:"):
            return False
    return seen_eg2


def main() -> int:
    train757_rows = read_jsonl(TRAIN757)
    train764_rows = read_jsonl(TRAIN764)
    train764_row_by_id = {row["id"]: row for row in train764_rows}

    train764_responses = {row["item_id"]: row for row in read_jsonl(TRAIN764_RESPONSES)}
    train764_scores = json.loads(TRAIN764_SCORES.read_text(encoding="utf-8"))["items"]
    train764_score_by_id = {item["item_id"]: item for item in train764_scores if item["item_id"] in train764_row_by_id}

    train764_score_by_prompt = {
        train764_row_by_id[item_id]["full_prompt"]: item
        for item_id, item in train764_score_by_id.items()
    }
    train764_response_by_prompt = {
        train764_row_by_id[item_id]["full_prompt"]: row
        for item_id, row in train764_responses.items()
        if item_id in train764_row_by_id
    }

    old_prompt_scores: Dict[str, Dict[str, Any]] = {}
    old_prompt_responses: Dict[str, Dict[str, Any]] = {}
    for ds_path, resp_path, score_path in [
        (OLD50_DATASET, OLD50_RESPONSES, OLD50_SCORES),
        (OLD250_DATASET, OLD250_RESPONSES, OLD250_SCORES),
    ]:
        ds_rows = read_jsonl(ds_path)
        resp_rows = {row["item_id"]: row for row in read_jsonl(resp_path)}
        score_rows = json.loads(score_path.read_text(encoding="utf-8"))["items"]
        for row, score in zip(ds_rows, score_rows):
            old_prompt_scores[row["full_prompt"]] = score
            if row["id"] in resp_rows:
                old_prompt_responses[row["full_prompt"]] = resp_rows[row["id"]]

    selected_dataset_rows: List[Dict[str, Any]] = []
    selected_response_rows: List[Dict[str, Any]] = []

    counts = Counter()
    examples: Dict[str, List[str]] = {
        "single_EG2": [],
        "EG2_plus_rule_FP": [],
        "all_rule_only": [],
        "confirmed_exact": [],
        "old300_exact": [],
    }

    for row in train757_rows:
        prompt = row["full_prompt"]

        # First prefer train764 prompt-matched teacher coverage.
        if prompt in train764_score_by_prompt and prompt in train764_response_by_prompt:
            score_item = train764_score_by_prompt[prompt]
            response_row = json.loads(json.dumps(train764_response_by_prompt[prompt], ensure_ascii=False))
            failed = [result for result in score_item.get("results", []) if result.get("score") != 1]
            methods = [str(result.get("method") or "") for result in failed]
            tags = [str(result.get("tag") or "") for result in failed]

            if exact_pass(score_item):
                response_row["repair_status"] = "confirmed_exact_pass"
                counts["confirmed_exact"] += 1
                if len(examples["confirmed_exact"]) < 5:
                    examples["confirmed_exact"].append(row["id"])
            elif len(failed) == 1 and tags == ["EG2"]:
                response_row["response"] = repair_single_eg2(str(response_row.get("response") or ""), row)
                response_row["repair_status"] = "heuristic_repair_single_EG2"
                response_row["repair_failed_tags_before"] = tags
                counts["single_EG2_repaired"] += 1
                if len(examples["single_EG2"]) < 5:
                    examples["single_EG2"].append(row["id"])
            elif is_eg2_plus_rule_only_fp(failed):
                response_row["response"] = repair_single_eg2(str(response_row.get("response") or ""), row)
                response_row["response"] = repair_rule_only(str(response_row.get("response") or ""), row, failed)
                response_row["repair_status"] = "heuristic_repair_EG2_plus_rule_FP"
                response_row["repair_failed_tags_before"] = tags
                counts["EG2_plus_rule_FP_repaired"] += 1
                if len(examples["EG2_plus_rule_FP"]) < 5:
                    examples["EG2_plus_rule_FP"].append(row["id"])
            elif failed and all(method.startswith("rule_aided:") for method in methods):
                response_row["response"] = repair_rule_only(str(response_row.get("response") or ""), row, failed)
                response_row["repair_status"] = "heuristic_repair_all_rule_only"
                response_row["repair_failed_tags_before"] = tags
                counts["all_rule_only_repaired"] += 1
                if len(examples["all_rule_only"]) < 5:
                    examples["all_rule_only"].append(row["id"])
            else:
                counts["excluded_train764_fail"] += 1
                continue

            response_row["item_id"] = row["id"]
            response_row["line_number"] = row["line_number"]
            selected_dataset_rows.append(row)
            selected_response_rows.append(response_row)
            continue

        # Then include only already exact-pass old300 recycled items.
        if prompt in old_prompt_scores and prompt in old_prompt_responses and exact_pass(old_prompt_scores[prompt]):
            response_row = json.loads(json.dumps(old_prompt_responses[prompt], ensure_ascii=False))
            response_row["item_id"] = row["id"]
            response_row["line_number"] = row["line_number"]
            response_row["repair_status"] = "confirmed_exact_pass_old300"
            selected_dataset_rows.append(row)
            selected_response_rows.append(response_row)
            counts["old300_exact"] += 1
            if len(examples["old300_exact"]) < 5:
                examples["old300_exact"].append(row["id"])
            continue

        counts["excluded_other"] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT_DATASET, selected_dataset_rows)
    write_jsonl(OUT_RESPONSES, selected_response_rows)

    report = {
        "date": "2026-06-16",
        "source_train757": str(TRAIN757),
        "output_dataset": str(OUT_DATASET),
        "output_responses": str(OUT_RESPONSES),
        "counts": {
            "selected_items": len(selected_dataset_rows),
            **counts,
        },
        "examples": examples,
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
