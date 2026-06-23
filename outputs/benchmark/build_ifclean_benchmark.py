#!/usr/bin/env python3
"""Build an IF-clean benchmark view by separating task coverage from IF constraints.

The input benchmark prompt is unchanged.  The output keeps only instruction-
following constraints in ``extracted_constraints`` so existing evaluators can
score ISR from the clean IF denominator.  Excluded constraints are preserved in
``diagnostic_constraints`` with a diagnostic axis.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_INPUT = Path("outputs/benchmark/finif_v2_tonight_hard300.jsonl")
DEFAULT_OUTPUT = Path("outputs/benchmark/finif_v2_tonight_hard300_ifclean.jsonl")
DEFAULT_SUMMARY = Path("outputs/benchmark/finif_v2_tonight_hard300_ifclean_summary.json")


WORK_PRODUCT_RE = re.compile(
    r"^(?:the (?:output|response|table|memo|review|brief|note|checklist|matrix|proposal|"
    r"worksheet|log|email|summary)|output|response)\s+must\s+(?:be|produce|fill out)\s+(?:a|an)\b",
    re.I,
)

COVERAGE_VERB_RE = re.compile(
    r"\bmust\s+(?:cover|include|identify|state|list|summarize|address|explain|assign|"
    r"classify|calculate|compute|compare|show|present|evaluate|prepare|provide|describe|"
    r"recommend|decide|determine|record|route|label|flag)\b",
    re.I,
)

FORMAT_RE = re.compile(
    r"\b(?:first non-empty line|next action:|markdown|json|table with columns|columns? "
    r"(?:contains?|must include)|required fields?|exact(?:ly)? (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)|"
    r"at least (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)|"
    r"at most (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)|"
    r"between \w+ and \w+|numbered|ordered-list|paragraphs?|headings?|blockquote|"
    r"one-sentence|two-column|valid json|regex|label .+?:)\b",
    re.I,
)

CITATION_RE = re.compile(
    r"\b(?:cite|source labels?|visible material labels?|active source labels?|"
    r"labels? next to|collected end-only citations)\b",
    re.I,
)

FORBIDDEN_RE = re.compile(
    r"\b(?:must not|do not|cannot|should not|avoid|not mark|not state|not make|"
    r"do not say|must avoid|without .+ must not|unless .+ must not|no external)\b",
    re.I,
)

CONDITIONAL_RE = re.compile(
    r"\b(?:if|unless|when|only if|greater than|less than|above|below|over|under|"
    r"threshold|trigger|stale|missing|unsupported|unresolved|conflicting|blank|"
    r"not provided|not supplied|no .+ attached|open item|hold|escalat|closing condition)\b",
    re.I,
)

LINEAGE_RE = re.compile(
    r"\b(?:source inputs?|formula|comparison|final result|business implication|"
    r"evidence-test-action|active evidence.*governing rule|controlling .* trigger|"
    r"why a softer or opposite outcome is not supported)\b",
    re.I,
)

MECHANICAL_CHECKERS = {
    "blockquote_count",
    "first_line_format",
    "heading_level",
    "heading_order",
    "markdown_table",
    "ordered_list_count",
    "paragraph_count",
    "sentence_count",
    "required_keyword",
    "table_columns",
    "valid_json",
    "required_fields",
    "regex_count",
    "word_range",
    "max_words",
    "min_words",
    "item_count",
    "decimal_places",
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
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


def checker_type(constraint: Dict[str, Any]) -> str:
    checker = constraint.get("checker")
    return str((checker or {}).get("checker_type") or constraint.get("checker_type") or "")


def classify_constraint(constraint: Dict[str, Any]) -> Tuple[str, str]:
    text = str(constraint.get("constraint") or "").strip()
    tag = str(constraint.get("tag") or "").upper()
    check_type = str(constraint.get("check_type") or "").lower()
    ctype = checker_type(constraint)

    if check_type == "rule" and ctype in MECHANICAL_CHECKERS:
        return "IF", "mechanically verifiable format/field/count constraint"
    if FORMAT_RE.search(text):
        return "IF", "explicit format, count, field, or presentation constraint"
    if WORK_PRODUCT_RE.search(text):
        return "coverage", "basic work-product request, not an independent constraint"
    if CITATION_RE.search(text):
        return "IF", "explicit citation/source-label placement constraint"
    if LINEAGE_RE.search(text):
        return "IF", "explicit reasoning-lineage or auditability constraint"
    if FORBIDDEN_RE.search(text):
        return "IF", "explicit forbidden action or boundary constraint"
    if CONDITIONAL_RE.search(text) and (
        FORBIDDEN_RE.search(text)
        or re.search(r"\b(?:mark|classif|label|escalat|hold|open item|closing condition|required next|must be identified)\b", text, re.I)
    ):
        return "IF", "condition-triggered required response behavior"
    if re.search(r"\buse only\b|\brely on .+ only\b|\bsupplied documents only\b|\bprovided materials only\b", text, re.I):
        return "IF", "explicit evidence-scope restriction"

    if tag.startswith("RC"):
        return "coverage", "required-content/task-coverage diagnostic"
    if tag.startswith("QV"):
        return "finance_validity", "calculation/task-validity diagnostic without clean IF verifier"
    if tag.startswith("EG"):
        return "quality", "evidence-grounding diagnostic without specific citation/label restriction"
    if tag.startswith("DB"):
        return "finance_validity", "decision-quality diagnostic without explicit boundary trigger"
    if COVERAGE_VERB_RE.search(text):
        return "coverage", "task step or content coverage phrased as a requirement"
    return "quality", "not clearly separable from task quality"


def if_subtype(constraint: Dict[str, Any]) -> str:
    text = str(constraint.get("constraint") or "")
    tag = str(constraint.get("tag") or "").upper()
    check_type = str(constraint.get("check_type") or "").lower()

    if check_type == "rule":
        return "format_rule"
    if tag.startswith("FP"):
        return "format_semantic"
    if tag.startswith("EG") or re.search(r"cite|source labels?|visible material labels?|active source|evidence|provided context|provided materials|supplied documents", text, re.I):
        return "evidence_grounding"
    if tag.startswith("QV") or re.search(r"calculation|reconciliation|variance|threshold|formula|comparison|result|business implication|inputs?", text, re.I):
        return "finance_quant_lineage"
    if tag.startswith("DB") or re.search(r"approve|approval|recommendation|hold|escalat|boundary|trigger|open item|closing condition|not mark|must not|do not", text, re.I):
        return "finance_decision_boundary"
    if tag.startswith("RC"):
        return "finance_workflow_requirement"
    return "other_if"


def is_strong_source_label_constraint(constraint: Dict[str, Any]) -> bool:
    text = str(constraint.get("constraint") or "")
    return bool(
        re.search(r"active source labels?.+next to|collected end-only citations", text, re.I)
    )


def is_subsumed_generic_citation_constraint(constraint: Dict[str, Any]) -> bool:
    text = str(constraint.get("constraint") or "")
    if is_strong_source_label_constraint(constraint):
        return False
    return bool(
        re.search(r"\bcit(?:e|ed|es|ing|ations?)\b", text, re.I)
        or re.search(r"\bcite\b.+(?:visible material labels?|source labels?)", text, re.I)
        or re.search(r"(?:visible material labels?|source labels?)\s+citations?\b", text, re.I)
        or re.search(r"\buse\s+(?:visible material labels?|source labels?)\s+as evidence\b", text, re.I)
        or re.search(r"(?:figures|findings|facts|statements).+\bcite\b.+(?:visible material labels?|source labels?)", text, re.I)
        or re.search(r"\bcite\b.+(?:source|support|supplied documents?|provided documents?|documents?)", text, re.I)
        or re.search(r"(?:red flags?|inputs?|factors?|findings?).+\bcite\b.+(?:source|support|documents?)", text, re.I)
    )


def annotate(constraint: Dict[str, Any], axis: str, reason: str) -> Dict[str, Any]:
    obj = dict(constraint)
    obj["score_axis"] = axis
    obj["include_in_isr"] = axis == "IF"
    obj["axis_reason"] = reason
    if axis == "IF":
        subtype = if_subtype(constraint)
        obj["if_subtype"] = subtype
        obj["if_supertype"] = "format" if subtype.startswith("format") else "semantic"
    return obj


def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    if_constraints: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    raw_constraints = [c for c in row.get("extracted_constraints") or [] if isinstance(c, dict)]
    has_strong_source_label = any(is_strong_source_label_constraint(c) for c in raw_constraints)
    for constraint in raw_constraints:
        if not isinstance(constraint, dict):
            continue
        axis, reason = classify_constraint(constraint)
        if axis == "IF" and has_strong_source_label and is_subsumed_generic_citation_constraint(constraint):
            axis = "quality"
            reason = "generic citation requirement subsumed by stricter active-source-label placement constraint"
        annotated = annotate(constraint, axis, reason)
        if axis == "IF":
            if_constraints.append(annotated)
        else:
            diagnostics.append(annotated)
    out["original_extracted_constraints_count"] = len(row.get("extracted_constraints") or [])
    out["extracted_constraints"] = if_constraints
    out["diagnostic_constraints"] = diagnostics
    out["ifclean"] = {
        "version": "ifclean-constraint-axis-v1",
        "if_constraints": len(if_constraints),
        "diagnostic_constraints": len(diagnostics),
    }
    return out


def summarize(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    axis_counts: Counter[str] = Counter()
    tag_axis_counts: Counter[str] = Counter()
    check_type_counts: Counter[str] = Counter()
    if_subtype_counts: Counter[str] = Counter()
    if_supertype_counts: Counter[str] = Counter()
    per_item = []
    per_item_format = []
    per_item_semantic = []
    for row in rows:
        per_item.append(len(row.get("extracted_constraints") or []))
        item_format = 0
        item_semantic = 0
        for c in row.get("extracted_constraints") or []:
            axis_counts["IF"] += 1
            check_type_counts[str(c.get("check_type") or "unknown")] += 1
            tag_axis_counts[f"{c.get('tag')}::IF"] += 1
            subtype = str(c.get("if_subtype") or "other_if")
            supertype = str(c.get("if_supertype") or "semantic")
            if_subtype_counts[subtype] += 1
            if_supertype_counts[supertype] += 1
            if supertype == "format":
                item_format += 1
            else:
                item_semantic += 1
        per_item_format.append(item_format)
        per_item_semantic.append(item_semantic)
        for c in row.get("diagnostic_constraints") or []:
            axis = str(c.get("score_axis") or "diagnostic")
            axis_counts[axis] += 1
            tag_axis_counts[f"{c.get('tag')}::{axis}"] += 1
    return {
        "items": len(rows),
        "if_constraints": axis_counts.get("IF", 0),
        "diagnostic_constraints": sum(v for k, v in axis_counts.items() if k != "IF"),
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
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows = [clean_row(row) for row in load_jsonl(args.input)]
    write_jsonl(args.output, rows)
    summary = summarize(rows)
    summary.update({"input": str(args.input), "output": str(args.output)})
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
