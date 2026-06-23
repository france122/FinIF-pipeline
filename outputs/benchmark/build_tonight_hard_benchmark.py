#!/usr/bin/env python3
"""Build a scoreable hard benchmark for tonight's GPT5.5 run.

Input is the v6 real-public-excerpt sidecar. This builder adds longer, more
varied task directives and compound finance-logic constraints, then emits both
a full sidecar and a hard50 slice selected for real-source coverage, QV/DB/EG
pressure, and controlled length.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


DEFAULT_INPUT = Path("outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_real_public_excerpts.jsonl")
DEFAULT_BASE = Path("outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl")
DEFAULT_OUTPUT = Path("outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_tonight_hard.jsonl")
DEFAULT_SELECTED = Path("outputs/benchmark/finif_v2_tonight_hard50.jsonl")
DEFAULT_SUMMARY = Path("outputs/benchmark/finif_v2_tonight_hard_summary.json")

FAMILY_CN = {
    "Evidence and Grounding": "证据与依据",
    "Quantitative Verification": "量化核验",
    "Decision and Boundary": "决策与边界",
    "Format and Presentation": "格式与表达",
    "Required Content Coverage": "必要内容覆盖",
}


POSTURES = [
    (
        "Controller review posture",
        "Before answering, treat the packet as a controller review workpaper. Tie each material source fact to the relevant rule, policy, threshold, template field, or missing-evidence trigger. Where a calculation is requested, do not stop at the number: state whether the computed result clears, breaches, reconciles, fails to reconcile, or leaves an open item. If a conclusion depends on an assumption that is not in the active packet, mark it unsupported rather than filling the gap.",
    ),
    (
        "Credit committee posture",
        "Before answering, read the packet as if the output will go to a credit or investment committee. Separate the controlling evidence from background context, identify the governing standard, then connect the standard to the requested action. When there are two plausible routes, state why the route you reject is not supported by the active materials. Do not let a favorable mitigant erase an unresolved blocker unless the active rule says it can.",
    ),
    (
        "Compliance escalation posture",
        "Before answering, apply a compliance escalation lens. For each red flag, exception, prohibited wording, unresolved document, stale value, or threshold breach, state the active source, the trigger, and the resulting boundary on what may be approved, represented, filed, or closed. If the packet contains public rule text and private case facts, use the public text as the standard and the private facts as the test case.",
    ),
    (
        "Reconciliation posture",
        "Before answering, handle the work as a reconciliation and exception memo. Do not merely repeat figures. Compare the relevant source values, show the difference or threshold relationship, and state the operational consequence of the mismatch or match. If the provided evidence does not support final clearance, keep the item open and identify the exact evidence needed to close it.",
    ),
    (
        "Disclosure-review posture",
        "Before answering, treat the output as a disclosure or client-communication control review. Distinguish reported facts, management or customer assertions, reviewer interpretation, and prohibited or unsupported claims. If wording should be softened, escalated, rejected, or changed from hypothetical to actual/current, explain the source-based reason and do not draft beyond the requested scope.",
    ),
    (
        "Diligence challenge posture",
        "Before answering, challenge the packet like a diligence reviewer rather than a summarizer. Identify the decisive evidence chain, then test whether the requested conclusion follows. Explicitly preserve conflicts among source documents, missing supporting records, stale dates, unexplained variances, or threshold failures. Do not convert partial support into a final recommendation.",
    ),
    (
        "Operations handoff posture",
        "Before answering, produce an operations-ready handoff: the reader should be able to see the source evidence, the required test, the result, and the next action without reverse-engineering your reasoning. Put source labels next to the facts and figures where they are used. If the correct next action is hold, return, escalate, revise, or do not approve, say so directly and name the trigger.",
    ),
    (
        "Adversarial audit posture",
        "Before answering, assume the file will be audited for unsupported leaps. Every material decision must survive three checks: active evidence exists, the governing rule or task standard applies, and the final action follows from that combination. Mention the most tempting unsupported conclusion and why the packet does not allow it. Keep format requirements, but do not let format hide the reasoning chain.",
    ),
]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            row["_source_line"] = line_number
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def tags_of(constraints: Iterable[Dict[str, Any]]) -> Set[str]:
    return {str(c.get("tag") or "").upper() for c in constraints if isinstance(c, dict)}


def has_prefix(tags: Set[str], prefix: str) -> bool:
    return any(tag.startswith(prefix) for tag in tags)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def constraint(
    text: str,
    *,
    tag: str,
    family: str,
    scope: str,
    check_type: str = "LLM",
    checker: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    obj = {
        "constraint": text,
        "source": "query",
        "rationale": "Added for the tonight hard benchmark to test compound finance instruction following.",
        "tag": tag,
        "scope": scope,
        "check_type": check_type,
        "judge_method": "Ask an LLM judge for a strict binary pass/fail score. The constraint is satisfied only when the response follows the full compound requirement, not merely one part.",
        "family": family,
        "family_cn": FAMILY_CN[family],
        "tonight_hardening": True,
    }
    if checker:
        obj["checker"] = checker
        obj["judge_method"] = "Evaluate with a deterministic local checker using the explicit checker configuration."
    return obj


def rule_constraint(text: str, *, checker_type: str, params: Dict[str, Any], tag: str, scope: str) -> Dict[str, Any]:
    return constraint(
        text,
        tag=tag,
        family="Format and Presentation",
        scope=scope,
        check_type="rule",
        checker={"checker_type": checker_type, **params},
    )


EXPLICIT_RULE_KEYS = {
    "type",
    "checker_type",
    "keywords",
    "phrases",
    "numbers",
    "thresholds",
    "deadlines",
    "pattern",
    "regex",
    "min",
    "max",
    "count",
    "mode",
    "case_sensitive",
    "format",
    "fields",
    "required_fields",
    "headings",
    "columns",
    "required_columns",
    "exact",
    "min_count",
    "max_count",
    "exact_count",
    "min_rows",
    "max_rows",
    "exact_rows",
    "level",
    "min_depth",
    "word",
    "line",
    "position",
    "trigger",
    "followup",
    "required_if_present",
    "tolerance",
    "expected_values",
    "forbidden_regex",
    "heading",
    "checker",
    "params",
}


def normalize_check_type_value(value: Any) -> str:
    raw = str(value or "LLM").strip().lower()
    if raw in {"judge", "llm"}:
        return "LLM"
    if raw in {"rule", "rule_aided"}:
        return "rule"
    return "LLM"


def has_explicit_rule_config(constraint_obj: Dict[str, Any]) -> bool:
    if any(isinstance(constraint_obj.get(key), dict) for key in ("evaluator", "checker", "rule")):
        return True
    if isinstance(constraint_obj.get("checker"), str) and constraint_obj.get("checker").strip():
        return True
    return any(key in constraint_obj for key in EXPLICIT_RULE_KEYS)


def split_title_list(segment: str) -> List[str]:
    segment = re.sub(r"\s+", " ", segment).strip(" .;:")
    if not segment:
        return []
    parts = [part.strip() for part in segment.split(",")]
    cleaned = []
    for part in parts:
        part = re.sub(r"^\s*(?:and|or)\s+", "", part, flags=re.I)
        part = part.strip(" .;:")
        if part:
            cleaned.append(part)
    if len(cleaned) == 1 and re.search(r"\s+and\s+", cleaned[0], flags=re.I):
        cleaned = [part.strip(" .;:") for part in re.split(r"\s+and\s+", cleaned[0], flags=re.I) if part.strip(" .;:")]
    return cleaned


def normalize_constraint_routes(constraints: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for original in constraints:
        c = attach_safe_rule_checker(dict(original))
        check_type = normalize_check_type_value(c.get("check_type"))
        if check_type == "rule" and not has_explicit_rule_config(c):
            c["check_type"] = "LLM"
            c["routing_note"] = "Converted from legacy rule_aided because no explicit local checker configuration was present."
            c["judge_method"] = "Ask an LLM judge for a strict binary pass/fail score; this constraint is not deterministically checkable from explicit checker configuration."
        elif check_type == "rule":
            c["check_type"] = "rule"
            c["judge_method"] = "Evaluate with a deterministic local checker using the explicit checker configuration."
        else:
            c["check_type"] = "LLM"
            if "judge_method" not in c:
                c["judge_method"] = "Ask an LLM judge for a strict binary pass/fail score."
        normalized.append(c)
    return normalized


def visible_source_label_map(row: Dict[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    registry = row.get("source_registry")
    if not isinstance(registry, list):
        return mapping
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        source_id = str(entry.get("source_id") or entry.get("id") or "").strip()
        prompt_label = str(entry.get("prompt_label") or "").strip()
        if source_id and prompt_label:
            mapping[source_id] = prompt_label
    return mapping


BASE_DOC_RE = re.compile(
    r"\[(DOC\d+)\s+-\s+([^\]]+)\]\n(.*?)(?=\n\n\[DOC\d+\s+-|\n\nTask:|\Z)",
    flags=re.S,
)

PUBLIC_TITLE_RE = re.compile(
    r"\b(?:SEC|FINRA|FDIC|SBA|IRS|FinCEN|CFR|17\s+CFR|Apple|Microsoft|Form\s+\d+|"
    r"Regulation|Rule\s+\d+|Know Your Customer|Customer Due Diligence|Plain English|"
    r"Risk Factors|Books and Records|Marketing Rule|AML Source Tool)\b",
    flags=re.I,
)

CASE_OR_WORKPAPER_TITLE_RE = re.compile(
    r"\b(?:Synthetic|Issue Intake|Current Portfolio Facts|Sponsor Terms|Commitment Dashboard|"
    r"Dashboard|Ticket|Profile|Worksheet|Schedule|File|Log|Matrix|Note|Checklist|Standard|"
    r"Instruction|Instructions|Policy Excerpt|Review Instruction|Source Excerpt|Request|"
    r"Snapshot|Portfolio Facts|Pacing Plan|Recommendation|Document Inventory|Inventory|"
    r"Floating-Rate Exposure|Term Sheet|Exposure|Diligence Standard)\b",
    flags=re.I,
)

EXCLUDED_SOURCE_LINES = {
    # Base v6 lacks the sale-candidate/gain-loss inputs requested by the query.
    98,
    # Base v6 lacks the non-USD exposure and 25% currency-limit inputs requested by the query.
    225,
}


def parse_base_docs(prompt: str) -> Dict[str, Dict[str, str]]:
    docs: Dict[str, Dict[str, str]] = {}
    for match in BASE_DOC_RE.finditer(prompt or ""):
        docs[match.group(1)] = {
            "title": match.group(2).strip(),
            "content": match.group(3).strip(),
        }
    return docs


def should_restore_case_doc(entry: Dict[str, Any]) -> bool:
    if not isinstance(entry.get("provenance"), dict):
        return False
    title = str(entry.get("title") or "")
    if PUBLIC_TITLE_RE.search(title):
        return False
    return bool(CASE_OR_WORKPAPER_TITLE_RE.search(title))


def refresh_public_excerpt_overlay(row: Dict[str, Any]) -> None:
    registry = row.get("source_registry") or []
    sources = []
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        provenance = entry.get("provenance")
        if isinstance(provenance, dict) and provenance.get("source_id"):
            sources.append(str(provenance["source_id"]))

    overlay = dict(row.get("public_excerpt_overlay") or {})
    if overlay or sources:
        overlay["replaced_public_docs"] = len(sources)
        overlay["sources"] = sources
        row["public_excerpt_overlay"] = overlay


def repair_overlaid_case_docs(row: Dict[str, Any], base_row: Dict[str, Any]) -> None:
    """Restore private case/workpaper docs if the public excerpt overlay replaced them."""
    registry = row.get("source_registry")
    if not isinstance(registry, list):
        return
    base_docs = parse_base_docs(str(base_row.get("full_prompt") or ""))
    if not base_docs:
        return

    prompt = str(row.get("full_prompt") or "")
    repaired = []
    for entry in registry:
        if not isinstance(entry, dict) or not should_restore_case_doc(entry):
            continue
        source_id = str(entry.get("source_id") or "")
        base_doc = base_docs.get(source_id)
        if not base_doc:
            continue
        old_content = str(entry.get("content") or "")
        new_content = base_doc["content"]
        if not old_content or not new_content or old_content == new_content:
            continue
        prompt = prompt.replace(old_content, new_content)
        entry["content"] = new_content
        entry["restored_from_base_due_to_public_overlay"] = entry.pop("provenance", None)
        repaired.append(
            {
                "source_id": source_id,
                "prompt_label": entry.get("prompt_label"),
                "title": entry.get("title"),
            }
        )

    if repaired:
        row["full_prompt"] = prompt
        row["source_overlay_repairs"] = repaired
        refresh_public_excerpt_overlay(row)


def rewrite_hidden_doc_refs(text: str, source_labels: Dict[str, str]) -> str:
    """Rewrite hidden registry IDs in constraint text to prompt-visible labels."""
    if not source_labels or not text:
        return text

    def branded_repl(match: re.Match[str]) -> str:
        prefix = match.group(1).strip()
        doc_id = match.group(2)
        label = source_labels.get(doc_id)
        return f"{prefix} material labeled {label}" if label else match.group(0)

    def repl(match: re.Match[str]) -> str:
        doc_id = match.group(0)
        label = source_labels.get(doc_id)
        return f"the material labeled {label}" if label else doc_id

    text = re.sub(r"\b([A-Z][A-Za-z0-9&.'-]*)\s+(DOC\d+)\b", branded_repl, text)
    text = re.sub(r"\bDOC\d+\b", repl, text)
    text = re.sub(r"\bdocument ids?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bDOC numbers?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bDOC IDs?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bDOC citations?\b", "visible material label citations", text, flags=re.I)
    text = re.sub(r"\bcite documents\b", "cite visible material labels", text, flags=re.I)
    return text


def rewrite_constraint_source_refs(
    constraints: Sequence[Dict[str, Any]],
    source_labels: Dict[str, str],
) -> List[Dict[str, Any]]:
    if not source_labels:
        return [dict(c) for c in constraints]
    rewritten = []
    for original in constraints:
        c = dict(original)
        for key in ("constraint", "rationale", "judge_method", "routing_note"):
            if isinstance(c.get(key), str):
                c[key] = rewrite_hidden_doc_refs(c[key], source_labels)
        rewritten.append(c)
    return rewritten


def remove_hidden_source_id_instruction(prompt: str, source_labels: Optional[Dict[str, str]] = None) -> str:
    prompt = prompt.replace(
        "When the answer uses evidence, cite the material labels shown above; the structured registry keeps the original source IDs.",
        "When the answer uses evidence, cite the material labels shown above.",
    )
    prompt = prompt.replace(
        "cite document IDs for material facts",
        "cite the visible material labels for material facts",
    )
    prompt = re.sub(r"\bcite (?:DOC|document) ids?\b", "cite visible material labels", prompt, flags=re.I)
    prompt = re.sub(r"\bcite the (?:DOC|document) ids?\b", "cite the visible material labels", prompt, flags=re.I)
    if source_labels:
        prompt = rewrite_hidden_doc_refs(prompt, source_labels)
    return prompt


def attach_safe_rule_checker(constraint_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Attach explicit rule checkers only for mechanically verifiable wording."""
    text = str(constraint_obj.get("constraint") or "")
    tag = str(constraint_obj.get("tag") or "").upper()
    if has_explicit_rule_config(constraint_obj):
        return constraint_obj

    if tag.startswith("FP"):
        match = re.search(r"sections?\s+titled\s+(.+?)(?:\.|$)", text, flags=re.I)
        if match:
            titles = split_title_list(match.group(1))
            if len(titles) >= 2:
                constraint_obj["check_type"] = "rule"
                constraint_obj["checker"] = {"checker_type": "heading_order", "headings": titles}
                constraint_obj["judge_method"] = "Evaluate with a deterministic local checker that the required section titles appear as headings/labels in the listed order."
                constraint_obj["routing_note"] = "Converted to rule because the section-title order is mechanically checkable."
    return constraint_obj


def added_constraints(tags: Set[str], prompt: str) -> List[Dict[str, Any]]:
    """Add a small, high-signal hardening pack without overloading each item."""
    folded = prompt.casefold()
    core = [
        constraint(
            "The response must connect active evidence, governing rule or task standard, and final action in a single reasoning chain; it must not present facts, calculations, and recommendations as disconnected checklist fragments.",
            tag="DB9",
            family="Decision and Boundary",
            scope="decision",
        ),
        constraint(
            "Material facts, numeric inputs, thresholds, calculation results, missing-evidence triggers, and decision points must have active source labels next to the sentence, row, or bullet where they are used; collected end-only citations are not sufficient.",
            tag="EG2",
            family="Evidence and Grounding",
            scope="evidence",
        ),
    ]
    candidates: List[Dict[str, Any]] = []
    if has_prefix(tags, "QV") or any(token in prompt.casefold() for token in ("calculate", "compute", "reconcile", "threshold", "variance", "basis point", "bps", "ratio")):
        candidates.append(
            constraint(
                "For every requested calculation, reconciliation, variance, threshold test, date count, headroom, or shortfall, the response must show source inputs, formula or comparison, final result, and business implication; a bare computed number does not satisfy this requirement.",
                tag="QV2",
                family="Quantitative Verification",
                scope="calculation",
            )
        )
    if has_prefix(tags, "DB") or any(token in prompt.casefold() for token in ("approve", "reject", "hold", "escalat", "exception", "breach", "refer", "not approve")):
        candidates.append(
            constraint(
                "Every approval, rejection, hold, escalation, exception, classification, recommendation, or boundary must name the controlling active-case trigger and state why a softer or opposite outcome is not supported.",
                tag="DB7",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    if any(token in prompt.casefold() for token in ("missing", "not provided", "not supplied", "blank", "none attached", "delayed", "stale", "unsupported", "conflict", "shortfall")):
        candidates.append(
            constraint(
                "If evidence is missing, stale, conflicting, delayed, blank, unsupported, or below a stated threshold, the response must preserve that limitation as an open item, exception, hold, escalation, or required next evidence rather than treating the workflow as cleared.",
                tag="EG4",
                family="Evidence and Grounding",
                scope="evidence",
            )
        )
    if has_prefix(tags, "FP"):
        candidates.append(
            constraint(
                "The required output format must carry the evidence-test-action chain inside the relevant rows, bullets, fields, or sections; format compliance alone is insufficient if the reasoning dependency is separated or hidden.",
                tag="FP2",
                family="Format and Presentation",
                scope="output",
            )
        )
    if not candidates:
        candidates.append(
            constraint(
                "The response must identify at least one unsupported or rejected alternative conclusion when the packet contains an unresolved blocker, conflicting evidence, threshold failure, stale item, or missing support; the answer must explain why the active packet does not allow that alternative.",
                tag="DB4",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    specialized: List[Dict[str, Any]] = []
    precision_constraints: List[Dict[str, Any]] = []
    if any(token in folded for token in ("assumption", "inference", "assertion", "reported fact", "customer statement", "management claim")):
        specialized.append(
            constraint(
                "The response must separate source-stated facts from reviewer inferences, assumptions, customer statements, or management assertions; it must not present inferred conclusions as source facts.",
                tag="EG3",
                family="Evidence and Grounding",
                scope="evidence",
            )
        )
    if any(token in folded for token in ("quote", "preserve", "exact", "legal reference", "rule reference", "source term", "threshold")):
        specialized.append(
            constraint(
                "The response must preserve exact source figures, dates, thresholds, names, and rule references when they control the decision; it must not round, rename, or paraphrase them in a way that changes the controlling source meaning.",
                tag="EG5",
                family="Evidence and Grounding",
                scope="evidence",
            )
        )
    if any(token in folded for token in ("breach", "exception", "gap", "deficiency", "non-compliance", "waiver", "unresolved inconsistency")):
        specialized.append(
            constraint(
                "If the packet shows a breach, exception, waiver need, deficiency, unresolved inconsistency, control gap, or non-compliance indicator, the response must identify it as an active issue rather than treating the workflow as cleared.",
                tag="DB5",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    if any(token in folded for token in ("classify", "classification", "category", "risk level", "status as", "label any")):
        specialized.append(
            constraint(
                "When the task requires classification, status, or risk-level labeling, the response must use the explicit category labels supported by the packet and must not substitute a softer or unlisted label.",
                tag="DB6",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    if any(token in folded for token in ("approval", "authorization", "authority", "approver", "principal review", "manager approval")):
        specialized.append(
            constraint(
                "If approval, authorization, authority evidence, or a review prerequisite controls the outcome, the response must name the required approver or prerequisite and must not imply approval while that prerequisite is missing.",
                tag="DB7",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    if any(token in folded for token in ("advertising", "testimonial", "endorsement", "performance", "misleading", "sales claim", "communication", "script")):
        specialized.append(
            constraint(
                "The response must not convert hypothetical, projected, target, testimonial, endorsement, ranking, or sales-claim language into a current, certain, approved, or substantiated performance claim unless the packet supports that boundary.",
                tag="DB8",
                family="Decision and Boundary",
                scope="decision",
            )
        )
    if any(token in folded for token in ("deadline", "due date", "days late", "date count", "review period", "retention", "as-of", "aging")):
        specialized.append(
            constraint(
                "For every requested deadline, review window, date count, aging bucket, retention period, or as-of-date test, the response must show source dates, formula or comparison, final timing status, and business implication.",
                tag="QV5",
                family="Quantitative Verification",
                scope="calculation",
            )
        )
    if any(token in folded for token in ("compare", "rank", "ranking", "alternative", "scenario", "trade-off", "versus")):
        specialized.append(
            constraint(
                "For every requested comparison, ranking, alternative, scenario, or trade-off, the response must state the comparison basis, source inputs, result, and decision implication rather than listing options without a supported ordering or boundary.",
                tag="QV6",
                family="Quantitative Verification",
                scope="calculation",
            )
        )
    if any(token in folded for token in ("stress", "sensitivity", "shock", "downside", "scenario")):
        specialized.append(
            constraint(
                "For every requested stress, sensitivity, shock, downside, or scenario test, the response must keep the assumption, horizon, source inputs, formula or comparison, and final result tied together; it must not present the scenario result as a base-case fact.",
                tag="QV7",
                family="Quantitative Verification",
                scope="calculation",
            )
        )
    if any(token in folded for token in ("%", "percent", "percentage", "margin", "growth", "ratio", "bps", "basis point", "yield", "irr", "dscr")):
        precision_constraints.append(
            constraint(
                "Every percentage value in the response, including values written with percent or percentage points, must use exactly two decimal places.",
                tag="FP3",
                family="Format and Presentation",
                scope="output",
                check_type="rule",
                checker={"checker_type": "decimal_places", "places": 2, "target": "percent"},
            )
        )

    return core + candidates[:1] + specialized[:2] + precision_constraints[:1]


def semantic_query_clauses(semantic_constraints: Sequence[Dict[str, Any]]) -> List[str]:
    clauses = []
    for c in semantic_constraints:
        text = str(c.get("constraint") or "")
        if text.startswith("The response must connect active evidence"):
            clauses.append("connect each final action to the active evidence and the governing rule, policy, task standard, or active-case trigger")
        elif text.startswith("Material facts"):
            clauses.append("keep active source labels beside the material facts, figures, thresholds, missing-evidence triggers, and decision points where they are used")
        elif text.startswith("For every requested calculation"):
            clauses.append("for any calculation or reconciliation, show the source inputs, formula or comparison, result, and business implication")
        elif text.startswith("Every approval"):
            clauses.append("for any approval, rejection, hold, escalation, exception, classification, recommendation, or boundary, name the controlling trigger and why a softer or opposite outcome is not supported")
        elif text.startswith("If evidence is missing"):
            clauses.append("preserve missing, stale, conflicting, delayed, blank, unsupported, or below-threshold evidence as an open item, hold, escalation, or required next evidence")
        elif text.startswith("The required output format"):
            clauses.append("carry the evidence-test-action chain inside the relevant rows, bullets, fields, or sections")
        elif text.startswith("The response must identify at least one unsupported"):
            clauses.append("identify at least one tempting but unsupported or rejected alternative conclusion when the packet contains a blocker, conflict, stale item, missing support, or threshold failure")
        elif text.startswith("The response must separate source-stated facts"):
            clauses.append("separate source-stated facts from reviewer inferences, assumptions, customer statements, or management assertions")
        elif text.startswith("The response must preserve exact source"):
            clauses.append("preserve exact source figures, dates, thresholds, names, and rule references when they control the decision")
        elif text.startswith("If the packet shows a breach"):
            clauses.append("identify any active breach, exception, waiver need, deficiency, unresolved inconsistency, control gap, or non-compliance indicator rather than treating the workflow as cleared")
        elif text.startswith("When the task requires classification"):
            clauses.append("use only packet-supported category, status, classification, or risk-level labels")
        elif text.startswith("If approval, authorization"):
            clauses.append("name any required approver, authority evidence, authorization, or review prerequisite that controls the outcome")
        elif text.startswith("The response must not convert hypothetical"):
            clauses.append("keep hypothetical, projected, target, testimonial, endorsement, ranking, sales-claim, and performance language inside the boundary supported by the packet")
        elif text.startswith("For every requested deadline"):
            clauses.append("for any deadline, review window, date count, aging bucket, retention period, or as-of-date test, show source dates, formula or comparison, timing status, and business implication")
        elif text.startswith("For every requested comparison"):
            clauses.append("for any comparison, ranking, alternative, scenario, or trade-off, state the comparison basis, source inputs, result, and decision implication")
        elif text.startswith("For every requested stress"):
            clauses.append("for any stress, sensitivity, shock, downside, or scenario test, keep the assumption, horizon, source inputs, formula or comparison, and final result tied together")
        elif text.startswith("Every percentage value"):
            clauses.append("write every percentage value, including percent or percentage-point values, with exactly two decimal places")
    return clauses


def format_rule_pack(index: int, work_product: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Natural format IF requirements adapted from current/ benchmark checkers."""
    product = work_product.strip() or "work product"
    clauses = [
        f"Open the {product} with a Markdown bold title on the first non-empty line.",
        "Near the end, include the exact handoff label Next action:; if the packet supports no next action, write Next action: none supported by the packet.",
    ]
    constraints = [
        rule_constraint(
            "The first non-empty line must be a Markdown bold title.",
            checker_type="first_line_format",
            params={"format": "bold"},
            tag="FP6",
            scope="output",
        ),
        rule_constraint(
            "The response must include the exact label Next action:.",
            checker_type="required_keyword",
            params={"keywords": ["Next action:"], "case_sensitive": True},
            tag="FP4",
            scope="output",
        ),
    ]

    variant = index % 5
    if variant == 0:
        clauses.append("Include one Markdown table for the audit trail whose header contains the columns Evidence, Test, Result, and Action.")
        clauses.append("Keep the full response between 180 and 430 words.")
        constraints.append(
            rule_constraint(
                "The response must include a Markdown table with columns Evidence, Test, Result, and Action.",
                checker_type="table_columns",
                params={"required_columns": ["Evidence", "Test", "Result", "Action"]},
                tag="FP2",
                scope="output",
            )
        )
        constraints.append(
            rule_constraint(
                "The response must be between 180 and 430 words.",
                checker_type="word_range",
                params={"min_words": 180, "max_words": 430},
                tag="FP3",
                scope="output",
            )
        )
    elif variant == 1:
        clauses.append(f"Structure the {product} with at least three level-2 Markdown headings that start with ##.")
        constraints.append(
            rule_constraint(
                "The response must use at least three level-2 Markdown headings.",
                checker_type="heading_level",
                params={"level": 2, "min_count": 3},
                tag="FP1",
                scope="output",
            )
        )
    elif variant == 2:
        clauses.append("Use at least four numbered list items in the 1. / 2. / 3. style for checks, blockers, steps, or required actions.")
        clauses.append("Keep the full response between 220 and 520 words.")
        constraints.append(
            rule_constraint(
                "The response must include at least four ordered-list items using numeric list markers.",
                checker_type="ordered_list_count",
                params={"min_count": 4},
                tag="FP2",
                scope="output",
            )
        )
        constraints.append(
            rule_constraint(
                "The response must be between 220 and 520 words.",
                checker_type="word_range",
                params={"min_words": 220, "max_words": 520},
                tag="FP3",
                scope="output",
            )
        )
    elif variant == 3:
        clauses.append("Include at least two short Markdown blockquote lines beginning with > for source or rule excerpts that anchor the decision.")
        clauses.append("Use at least eight complete sentences in the full response.")
        constraints.append(
            rule_constraint(
                "The response must include at least two Markdown blockquote lines.",
                checker_type="blockquote_count",
                params={"min_count": 2},
                tag="FP2",
                scope="output",
            )
        )
        constraints.append(
            rule_constraint(
                "The response must contain at least eight complete sentences.",
                checker_type="sentence_count",
                params={"min_count": 8},
                tag="FP3",
                scope="output",
            )
        )
    else:
        clauses.append(f"Keep the {product} to between four and nine non-empty paragraphs, counting any table or list as part of the paragraph where it appears.")
        constraints.append(
            rule_constraint(
                "The response must use between four and nine non-empty paragraphs.",
                checker_type="paragraph_count",
                params={"min_count": 4, "max_count": 9},
                tag="FP3",
                scope="output",
            )
        )

    return clauses, constraints


def compose_enhanced_query(
    base_query: str,
    *,
    work_product: str,
    posture_name: str,
    posture_text: str,
    format_clauses: Sequence[str],
    semantic_clauses: Sequence[str],
) -> str:
    """Fold hardening constraints into the user-facing work-product request."""
    product = work_product.strip() or "work product"
    query = base_query.strip().rstrip()
    if query and query[-1] not in ".!?":
        query += "."
    natural_format = " ".join(clause.strip().rstrip(".") + "." for clause in format_clauses if clause.strip())
    posture_label = posture_name.strip().lower()
    semantic_text = "; ".join(clause.strip().rstrip(".") for clause in semantic_clauses if clause.strip())
    audit_chain = (
        f"Produce the {product} under an audit-ready {posture_label}: {semantic_text}."
        if semantic_text
        else f"Produce the {product} under an audit-ready {posture_label}."
    )
    return (
        f"{query} {audit_chain} {natural_format} "
        "Treat the layout as part of the requested finance work product, but do not omit required evidence, calculations, boundaries, or decisions just to satisfy presentation."
    ).strip()


def append_final_request(prompt: str, enhanced_query: str) -> str:
    prompt = prompt.strip()
    final_request = (
        "\n\nFinal work-product request\n"
        f"{enhanced_query}\n"
    )
    return prompt + final_request


def dedupe_constraints(constraints: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for c in constraints:
        text = str(c.get("constraint") or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def harden_row(row: Dict[str, Any], base_row: Dict[str, Any], index: int) -> Dict[str, Any]:
    obj = {k: v for k, v in row.items() if not k.startswith("_")}
    if isinstance(obj.get("source_registry"), list):
        obj["source_registry"] = [dict(entry) if isinstance(entry, dict) else entry for entry in obj["source_registry"]]
    repair_overlaid_case_docs(obj, base_row)
    constraints = [dict(c) for c in obj.get("extracted_constraints") or [] if isinstance(c, dict)]
    source_labels = visible_source_label_map(obj)
    for entry in obj.get("source_registry") or []:
        if isinstance(entry, dict) and isinstance(entry.get("content"), str):
            entry["content"] = remove_hidden_source_id_instruction(entry["content"], source_labels)
    constraints = rewrite_constraint_source_refs(constraints, source_labels)
    tags = tags_of(constraints)
    posture_name, posture_text = POSTURES[index % len(POSTURES)]
    work_product = str(base_row.get("work_product") or "")
    format_clauses, format_constraints = format_rule_pack(index, work_product)
    semantic_constraints = added_constraints(tags, f"{obj.get('full_prompt') or ''}\n{base_row.get('query') or ''}")
    base_query = remove_hidden_source_id_instruction(str(base_row.get("query") or ""), source_labels)
    enhanced_query = compose_enhanced_query(
        base_query,
        work_product=work_product,
        posture_name=posture_name,
        posture_text=posture_text,
        format_clauses=format_clauses,
        semantic_clauses=semantic_query_clauses(semantic_constraints),
    )
    obj["full_prompt"] = append_final_request(
        remove_hidden_source_id_instruction(str(obj.get("full_prompt") or ""), source_labels),
        enhanced_query,
    )
    obj["extracted_constraints"] = normalize_constraint_routes(
        dedupe_constraints(constraints + semantic_constraints + format_constraints)
    )
    obj["id"] = obj.get("id") or f"tonight_hard_line_{index + 1:03d}"
    obj["workflow"] = base_row.get("workflow")
    obj["task"] = base_row.get("task")
    obj["work_product"] = base_row.get("work_product")
    obj["query"] = enhanced_query
    obj["tonight_hardening"] = {
        "version": "tonight-hard-2-natural-query",
        "source_line": row.get("_source_line"),
        "posture": posture_name,
        "format_variant": index % 5,
        "format_clauses": format_clauses,
        "added_constraints": len(obj["extracted_constraints"]) - len(constraints),
    }
    return obj


def has_real_public_excerpt(row: Dict[str, Any]) -> bool:
    registry = row.get("source_registry") or []
    return any(isinstance(entry, dict) and isinstance(entry.get("provenance"), dict) for entry in registry)


def hardness_score(row: Dict[str, Any]) -> float:
    constraints = row.get("extracted_constraints") or []
    tags = tags_of(constraints)
    score = 0.0
    score += 5.0 if has_real_public_excerpt(row) else 0.0
    score += 1.5 * sum(tag.startswith("QV") for tag in tags)
    score += 1.5 * sum(tag.startswith("DB") for tag in tags)
    score += 1.2 * sum(tag.startswith("EG") for tag in tags)
    score += 0.4 * len(constraints)
    text = str(row.get("full_prompt") or "").casefold()
    for token in ("missing", "unsupported", "threshold", "shortfall", "breach", "escalat", "reconcile", "not provided", "conflict"):
        if token in text:
            score += 1.0
    words = word_count(str(row.get("full_prompt") or ""))
    if 700 <= words <= 2200:
        score += 3.0
    elif words > 3000:
        score -= 4.0
    return score


def select_hard(rows: Sequence[Dict[str, Any]], target: int) -> List[Dict[str, Any]]:
    real_public_available = sum(1 for row in rows if has_real_public_excerpt(row))
    desired_real_public = 46 if target <= 50 else real_public_available
    min_real_public = min(desired_real_public, target, real_public_available)
    ranked = sorted(enumerate(rows), key=lambda pair: hardness_score(pair[1]), reverse=True)
    selected: List[Dict[str, Any]] = []
    selected_indexes = set()
    workflow_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()

    def try_add(index: int, row: Dict[str, Any], *, relaxed: bool = False) -> bool:
        workflow = str(row.get("workflow") or "Unknown")
        task = str(row.get("task") or "Unknown")
        if not relaxed and workflow_counts[workflow] >= 14:
            return False
        if not relaxed and task_counts[task] >= 3:
            return False
        if word_count(str(row.get("full_prompt") or "")) > (3600 if relaxed else 3000):
            return False
        selected.append({**row, "line_number": index + 1})
        selected_indexes.add(index)
        workflow_counts[workflow] += 1
        task_counts[task] += 1
        return True

    for index, row in ranked:
        if len(selected) >= min_real_public:
            break
        if int(row.get("tonight_hardening", {}).get("source_line") or 0) in EXCLUDED_SOURCE_LINES:
            continue
        if index in selected_indexes or not has_real_public_excerpt(row):
            continue
        try_add(index, row)

    if len(selected) < min_real_public:
        for index, row in ranked:
            if len(selected) >= min_real_public:
                break
            if int(row.get("tonight_hardening", {}).get("source_line") or 0) in EXCLUDED_SOURCE_LINES:
                continue
            if index in selected_indexes or not has_real_public_excerpt(row):
                continue
            try_add(index, row, relaxed=True)

    if len(selected) < target:
        for index, row in ranked:
            if index in selected_indexes:
                continue
            if int(row.get("tonight_hardening", {}).get("source_line") or 0) in EXCLUDED_SOURCE_LINES:
                continue
            try_add(index, row)
            if len(selected) >= target:
                break

    if len(selected) < target:
        for index, row in ranked:
            if index in selected_indexes:
                continue
            if int(row.get("tonight_hardening", {}).get("source_line") or 0) in EXCLUDED_SOURCE_LINES:
                continue
            try_add(index, row, relaxed=True)
            if len(selected) >= target:
                break
    return selected


def distribution(values: Sequence[int]) -> Dict[str, Any]:
    ordered = sorted(values)
    return {
        "min": min(ordered),
        "median": statistics.median(ordered),
        "mean": round(statistics.mean(ordered), 1),
        "p90": ordered[int((len(ordered) - 1) * 0.9)],
        "max": max(ordered),
    }


def summarize(rows: Sequence[Dict[str, Any]], selected: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    def stats(part: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "items": len(part),
            "prompt_words": distribution([word_count(str(r.get("full_prompt") or "")) for r in part]),
            "prompt_chars": distribution([len(str(r.get("full_prompt") or "")) for r in part]),
            "constraints": distribution([len(r.get("extracted_constraints") or []) for r in part]),
            "rows_with_real_public_excerpt": sum(1 for r in part if has_real_public_excerpt(r)),
            "rule_aided_constraints": sum(
                1
                for r in part
                for c in r.get("extracted_constraints") or []
                if isinstance(c, dict) and str(c.get("check_type", "")).lower() == "rule"
            ),
            "workflow_counts": dict(Counter(str(r.get("workflow") or "Unknown") for r in part)),
            "posture_counts": dict(Counter(str((r.get("tonight_hardening") or {}).get("posture")) for r in part)),
        }
    return {
        "full": stats(rows),
        "selected": stats(selected),
        "selection_policy": "hardness score with real-public-excerpt preference, QV/DB/EG/explicit-format pressure, workflow/task spread, and <=3000 word first-pass cap",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build tonight hard benchmark and hard50 slice.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--selected-output", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--target", type=int, default=50)
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    base_rows = load_jsonl(args.base)
    if len(rows) != len(base_rows):
        raise ValueError(f"input rows {len(rows)} != base rows {len(base_rows)}")
    hardened = [harden_row(row, base_rows[index], index) for index, row in enumerate(rows)]
    selected = select_hard(hardened, args.target)
    summary = summarize(hardened, selected)
    summary.update({"input": str(args.input), "output": str(args.output), "selected_output": str(args.selected_output)})

    write_jsonl(args.output, hardened)
    write_jsonl(args.selected_output, selected)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
