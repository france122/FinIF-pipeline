#!/usr/bin/env python3
"""Item-level evaluator for FinIF v2 responses.

Each constraint must declare its scoring route up front. ``check_type=rule``
is evaluated only by a deterministic local checker with explicit checker
configuration. ``check_type=LLM`` is evaluated only by the LLM judge. The
evaluator does not silently fall back from one route to the other.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .rule_checkers import evaluate_constraint
except ImportError:  # pragma: no cover - allows direct script execution.
    from rule_checkers import evaluate_constraint


Constraint = Dict[str, Any]
Result = Dict[str, Any]

QUALITY_CAP_TAGS = {
    "EG1", "EG2", "EG3", "EG4", "EG5", "EG6", "EG7",
    "QV1", "QV2", "QV3", "QV4", "QV5", "QV6", "QV7",
    "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7", "DB8", "DB9",
}

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


JUDGE_SYSTEM_PROMPT = """You are an audit-grade FinIF v2 item evaluator.

You receive one finance-workflow prompt, one model response, and a list of
constraints that still need LLM judgment. Treat the supplied prompt/source
materials as the only ground truth for facts, figures, dates, citations, and
allowed assumptions.

Evaluate each listed constraint independently. Do not let the holistic quality
score affect any binary constraint score, and do not add criteria beyond the
constraint text.

This benchmark measures instruction following under finance long-context
pressure. Be deliberately strict. A polished or generally useful answer still
fails a constraint if the exact hidden requirement is not fully satisfied.

Constraint scoring policy:
- Pass only when the response unambiguously and completely satisfies the
  constraint using the supplied prompt/source materials.
- Fail if the response merely implies the requirement, partially satisfies it,
  uses a near-equivalent but not the requested format/label/section, omits a
  required subpart, or makes the judge infer missing work.
- For format constraints, require the requested artifact exactly. If a table,
  JSON object, checklist, fixed fields, named sections, or decision table is
  required, fail unless the response visibly uses that structure.
- For citation/evidence constraints, fail if material facts, calculations, or
  decisions lack the requested source labels, cite the wrong source labels, or
  rely on external knowledge. A citation in the same table row, bullet, or
  sentence may support the facts and decision points in that row/bullet/sentence.
  A section-level, heading-level, introductory, or end-only citation is not enough
  for facts, figures, thresholds, calculation results, missing-evidence triggers,
  or decision points that appear later without a nearby label.
- For quantitative constraints, fail unless the response gives the required
  numeric result and enough calculation/reconciliation detail to verify it from
  the prompt. A correct-looking conclusion without the required computation is
  not enough. Apply this only to calculations, reconciliations, variances,
  threshold tests, date counts, headroom, or shortfalls actually requested or
  required by the prompt/source materials. If no such calculation is requested,
  do not fail merely because the response lacks a formula.
- For timing/date-count constraints, if the source packet lacks the source date,
  as-of date, deadline, or review-window input needed to compute a timing result,
  pass when the response explicitly marks that timing evidence as missing and
  states the resulting open item, boundary, or required next evidence. Do not
  require an impossible date-count formula from absent source dates.
- For threshold wording, preserve the exact comparator and inclusivity in the
  prompt. "Greater than" means strictly >, not >=; "less than" means strictly
  <, not <=; "at least" means >=; "at most" means <=. Do not fail a decision
  merely because a value equals a threshold unless the prompt makes equality a
  breach or failure.
- For decision/boundary constraints, fail if the response softens, omits, or
  contradicts the requested boundary, escalation, refusal, missing-evidence,
  or no-legal/investment-conclusion condition. For approval, rejection, hold,
  escalation, exception, classification, recommendation, and boundary-trigger
  constraints, focus on the principal final outcome(s) and material decision
  boundaries, not every minor observation or next-step sentence.
  If failing a required approver, authority, prerequisite, escalation, or
  review-boundary constraint, the short reason must name the specific missing
  approver, authority evidence, prerequisite, escalation item, or boundary.
- For evidence-rule-action chain constraints, do not fail merely because the
  work product is organized as a checklist, table, bullets, or sections. Pass
  when the response makes the active evidence, governing rule/trigger/standard,
  and final action traceable together in the relevant row, bullet, paragraph, or
  section. Fail when facts, calculations, and decisions are presented as isolated
  fragments that require the judge to infer the missing link.
- For required-content constraints, fail if any named entity, risk, document,
  exception, open question, action, or required comparison in the constraint is
  missing.
- Do not award a pass because the answer is high quality overall. Binary
  constraint scores are exact compliance checks.

Also give one holistic content quality score from 0 to 10:
- 10: excellent, accurate, grounded, complete, decision-useful work product.
- 7-9: good, but with minor omissions, weak evidence linkage, or small format issues.
- 4-6: partially useful, but incomplete, shallow, loosely grounded, or with notable weaknesses.
- 1-3: poor, materially flawed, unsupported, missing required decisions, or hard to use.
- 0: unusable, off-task, empty, or mostly hallucinated.

Quality cap policy:
- If the response fails any grounding/citation, quantitative verification, or
  decision/boundary constraint that is central to the requested finance work
  product, quality_score must be 6 or lower.
- If it fails two or more such central constraints, quality_score must be 4 or
  lower.
- If it uses non-authoritative evidence, gives an unsupported legal/investment
  conclusion, or gets a central calculation/trigger wrong, quality_score must be
  3 or lower.
- A fluent answer with broken finance instruction-following is not high quality.

Return only valid JSON with this exact shape:
{
  "constraint_scores": [
    {"constraint_index": 1, "score": 1, "reason": "Short reason."}
  ],
  "quality_score": 5,
  "quality_reason": "Short reason."
}

Rules:
- constraint_index must exactly match the zero-based indexes provided.
- score must be integer 1 for pass or integer 0 for fail.
- quality_score must be an integer from 0 to 10.
- reasons must be short strings.
- If satisfaction is ambiguous, incomplete, approximate, or not clearly
  evidenced in the response, score 0.
- Do not return text outside JSON."""


@dataclass
class JudgeRequest:
    item_id: str
    constraints: List[Tuple[int, Constraint]]
    response: str
    prompt: str


class JudgeProvider:
    """Adapter interface for real judge clients.

    Implementations should call their model with temperature=0 and return the
    raw text produced by the model. The runner handles parsing and retries.
    """

    name = "base"

    def judge(self, request: JudgeRequest, system_prompt: str) -> str:
        raise NotImplementedError


class StubJudgeProvider(JudgeProvider):
    """Offline provider used when no external judge is configured."""

    name = "stub"

    def judge(self, request: JudgeRequest, system_prompt: str) -> str:
        raise RuntimeError("No judge provider configured.")


def load_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            yield line_number, obj


def unique_strings(values: Iterable[Any]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def item_aliases(
    obj: Dict[str, Any],
    line_number: int,
    *,
    include_row_number_fallback: bool,
) -> List[str]:
    aliases = unique_strings(
        [
            obj.get("id"),
            obj.get("item_id"),
            obj.get("case_id"),
            obj.get("line_number"),
            obj.get("line"),
        ]
    )
    if include_row_number_fallback or not aliases:
        aliases = unique_strings([*aliases, line_number])
    return aliases


def primary_id_aliases(obj: Dict[str, Any]) -> List[str]:
    return unique_strings([obj.get("id"), obj.get("item_id"), obj.get("case_id")])


def fallback_line_aliases(obj: Dict[str, Any], line_number: int) -> List[str]:
    return unique_strings([obj.get("line_number"), obj.get("line"), line_number])


def response_match_aliases(
    obj: Dict[str, Any],
    line_number: int,
    *,
    include_row_number_fallback: bool,
) -> List[str]:
    primary = primary_id_aliases(obj)
    if primary:
        return primary
    aliases = unique_strings([obj.get("line_number"), obj.get("line")])
    if include_row_number_fallback or not aliases:
        aliases = unique_strings([*aliases, line_number])
    return aliases


def load_dataset(path: Path) -> Dict[str, Dict[str, Any]]:
    items: Dict[str, Dict[str, Any]] = {}
    for line_number, obj in load_jsonl(path):
        aliases = item_aliases(obj, line_number, include_row_number_fallback=True)
        item_id = aliases[0]
        obj["_evaluation_id"] = item_id
        obj["_response_aliases"] = response_match_aliases(
            obj,
            line_number,
            include_row_number_fallback=True,
        )
        obj["_line_number"] = line_number
        if item_id in items:
            raise ValueError(f"Duplicate dataset item id/alias {item_id!r}")
        items[item_id] = obj
    return items


def load_responses(path: Path) -> Dict[str, str]:
    responses: Dict[str, str] = {}
    for line_number, obj in load_jsonl(path):
        aliases = response_match_aliases(
            obj,
            line_number,
            include_row_number_fallback=False,
        )
        response = obj.get("response")
        if response is None:
            response = obj.get("output")
        if response is None:
            raise ValueError(f"Response row {line_number} missing response/output")
        for alias in aliases:
            responses[alias] = str(response)
    return responses


def response_for_item(item: Dict[str, Any], responses: Dict[str, str]) -> Optional[str]:
    for alias in item.get("_response_aliases", []):
        if alias in responses:
            return responses[alias]
    return None


def load_provider(spec: Optional[str]) -> JudgeProvider:
    if not spec:
        return StubJudgeProvider()
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError("--judge-provider must look like module.path:ClassName")
    module = importlib.import_module(module_name)
    provider_cls = getattr(module, attr)
    provider = provider_cls()
    if not isinstance(provider, JudgeProvider):
        required = all(hasattr(provider, name) for name in ("judge", "name"))
        if not required:
            raise TypeError("Judge provider must expose name and judge(request, system_prompt)")
    return provider


def has_explicit_rule_config(constraint: Constraint) -> bool:
    if any(isinstance(constraint.get(key), dict) for key in ("evaluator", "checker", "rule")):
        return True
    if isinstance(constraint.get("checker"), str) and constraint.get("checker").strip():
        return True
    return any(key in constraint for key in EXPLICIT_RULE_KEYS)


def normalize_check_type(value: Any) -> str:
    raw = str(value or "LLM").strip().lower()
    if raw in {"llm", "judge"}:
        return "LLM"
    if raw in {"rule", "rule_aided"}:
        return "rule"
    return raw


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    return text


def strict_parse_item_judge(
    raw: str,
    expected_indexes: Sequence[int],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    text = strip_code_fence(raw)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc.msg}"
    if not isinstance(obj, dict):
        return None, "judge output must be a JSON object"

    raw_scores = obj.get("constraint_scores")
    if not isinstance(raw_scores, list):
        return None, "constraint_scores must be a list"

    expected = set(expected_indexes)
    seen = set()
    parsed_scores: Dict[int, Dict[str, Any]] = {}
    for row in raw_scores:
        if not isinstance(row, dict):
            return None, "each constraint score must be an object"
        index = row.get("constraint_index")
        if isinstance(index, bool) or not isinstance(index, int):
            return None, "constraint_index must be an integer"
        if index not in expected:
            return None, f"unexpected constraint_index {index}"
        if index in seen:
            return None, f"duplicate constraint_index {index}"
        seen.add(index)

        score = row.get("score")
        if isinstance(score, bool) or score not in (0, 1):
            return None, f"score for constraint_index {index} must be integer 0 or 1"
        reason = row.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return None, f"reason for constraint_index {index} must be a non-empty string"
        parsed_scores[index] = {"score": int(score), "reason": reason.strip()}

    missing = sorted(expected - seen)
    if missing:
        return None, f"missing constraint_index values: {missing}"

    quality_score = obj.get("quality_score")
    if isinstance(quality_score, bool) or not isinstance(quality_score, int) or not 0 <= quality_score <= 10:
        return None, "quality_score must be an integer from 0 to 10"
    quality_reason = obj.get("quality_reason")
    if not isinstance(quality_reason, str) or not quality_reason.strip():
        return None, "quality_reason must be a non-empty string"

    return {
        "constraint_scores": parsed_scores,
        "quality_score": int(quality_score),
        "quality_reason": quality_reason.strip(),
    }, None


def constraint_id(item_id: str, index: int, constraint: Constraint) -> str:
    return str(constraint.get("id") or constraint.get("constraint_id") or f"{item_id}#C{index + 1}")


def documents_from_item(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    context = item.get("context") or {}
    if isinstance(context, dict) and isinstance(context.get("documents"), list):
        return [doc for doc in context["documents"] if isinstance(doc, dict)]
    if isinstance(item.get("documents"), list):
        return [doc for doc in item["documents"] if isinstance(doc, dict)]
    registry = item.get("source_registry")
    if isinstance(registry, list):
        docs = []
        for entry in registry:
            if not isinstance(entry, dict):
                continue
            docs.append(
                {
                    "id": entry.get("source_id") or entry.get("id"),
                    "label": entry.get("prompt_label"),
                    "title": entry.get("title"),
                    "content": entry.get("content"),
                }
            )
        return docs
    return []


def build_item_judge_prompt(
    item: Dict[str, Any],
    response: str,
    pending_constraints: Sequence[Tuple[int, Constraint]],
) -> str:
    item_id = str(item.get("_evaluation_id") or item.get("id") or item.get("item_id") or item.get("case_id"))
    workflow = item.get("workflow") or ""
    task = item.get("task") or ""
    query = item.get("query") or ""
    full_prompt = item.get("full_prompt") or ""

    constraints_payload = [
        {
            "constraint_index": index,
            "constraint": constraint.get("constraint", ""),
            "tag": constraint.get("tag", ""),
            "family": constraint.get("family", ""),
        }
        for index, constraint in pending_constraints
    ]

    parts = [
        f"Item ID: {item_id}",
    ]
    if workflow or task:
        parts.append(f"Workflow/task: {workflow} / {task}".strip())
    if query:
        parts.append(f"Original task/query:\n{query}")
    if full_prompt:
        parts.append(f"Model prompt evaluated by the response model:\n{full_prompt}")
    else:
        docs = documents_from_item(item)
        if docs:
            parts.append("Source documents:\n" + json.dumps(docs, ensure_ascii=False, indent=2))

    parts.extend(
        [
            "Constraints requiring LLM judgment. Use these zero-based indexes exactly:",
            json.dumps(constraints_payload, ensure_ascii=False, indent=2),
            "Model response to evaluate:",
            response,
        ]
    )
    return "\n\n".join(parts)


def majority_score(votes: Sequence[int]) -> int:
    counts = Counter(votes)
    if counts[1] == counts[0]:
        return votes[-1]
    return 1 if counts[1] > counts[0] else 0


def judge_item_with_retries(
    provider: JudgeProvider,
    request: JudgeRequest,
    repeats: int,
    parse_retries: int,
) -> Dict[str, Any]:
    expected_indexes = [index for index, _constraint in request.constraints]
    raw_outputs: List[str] = []
    parsed_outputs: List[Dict[str, Any]] = []
    errors: List[str] = []

    for _ in range(max(1, repeats)):
        for _attempt in range(max(1, parse_retries + 1)):
            try:
                raw = provider.judge(request, JUDGE_SYSTEM_PROMPT)
            except Exception as exc:
                errors.append(str(exc))
                break
            raw_outputs.append(raw)
            parsed, error = strict_parse_item_judge(raw, expected_indexes)
            if parsed is not None and error is None:
                parsed_outputs.append(parsed)
                break
            errors.append(error or "unknown parse error")

    if not parsed_outputs:
        return {
            "status": "needs_judge",
            "method": f"judge:{provider.name}",
            "raw_judge_outputs": raw_outputs,
            "errors": errors,
            "judge_prompt": request.prompt,
            "constraint_scores": {},
            "quality": {
                "score": None,
                "normalized_score": None,
                "status": "needs_judge",
                "reason": "Judge unavailable or returned unparsable JSON.",
                "method": f"judge:{provider.name}",
            },
        }

    constraint_scores: Dict[int, Dict[str, Any]] = {}
    for index in expected_indexes:
        votes = [parsed["constraint_scores"][index]["score"] for parsed in parsed_outputs]
        final_score = majority_score(votes)
        reason = next(
            parsed["constraint_scores"][index]["reason"]
            for parsed in reversed(parsed_outputs)
            if parsed["constraint_scores"][index]["score"] == final_score
        )
        constraint_scores[index] = {
            "score": final_score,
            "status": "pass" if final_score == 1 else "fail",
            "method": f"judge:{provider.name}",
            "reason": reason,
            "judge_votes": [
                {
                    "score": parsed["constraint_scores"][index]["score"],
                    "reason": parsed["constraint_scores"][index]["reason"],
                }
                for parsed in parsed_outputs
            ],
        }

    quality_votes = [parsed["quality_score"] for parsed in parsed_outputs]
    final_quality = round(sum(quality_votes) / len(quality_votes))
    quality_reason = parsed_outputs[-1]["quality_reason"]

    return {
        "status": "judged",
        "method": f"judge:{provider.name}",
        "raw_judge_outputs": raw_outputs,
        "errors": errors,
        "constraint_scores": constraint_scores,
        "quality": {
            "score": final_quality,
            "normalized_score": final_quality / 10,
            "status": "judged",
            "reason": quality_reason,
            "method": f"judge:{provider.name}",
            "judge_votes": [
                {
                    "score": parsed["quality_score"],
                    "reason": parsed["quality_reason"],
                }
                for parsed in parsed_outputs
            ],
        },
    }


def result_metadata(item_id: str, index: int, constraint: Constraint, result: Result) -> Result:
    check_type = normalize_check_type(constraint.get("check_type", "LLM"))
    return {
        **result,
        "constraint_id": constraint_id(item_id, index, constraint),
        "constraint_index": index,
        "check_type": check_type,
        "tag": constraint.get("tag"),
        "family": constraint.get("family"),
        "constraint": constraint.get("constraint", ""),
    }


def evaluate_item(
    item: Dict[str, Any],
    response: str,
    provider: JudgeProvider,
    hard_only: bool,
    repeats: int,
    parse_retries: int,
) -> Dict[str, Any]:
    item_id = str(item.get("_evaluation_id") or item.get("id") or item.get("item_id") or item.get("case_id"))
    constraints = item.get("extracted_constraints") or item.get("constraints") or []
    if not isinstance(constraints, list):
        raise ValueError(f"Item {item_id} has non-list extracted_constraints/constraints")

    results_by_index: Dict[int, Result] = {}
    pending: List[Tuple[int, Constraint]] = []

    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            raise ValueError(f"Item {item_id} constraint {index} is not an object")
        check_type = normalize_check_type(constraint.get("check_type", "LLM"))
        if check_type == "rule":
            if not has_explicit_rule_config(constraint):
                raise ValueError(f"Item {item_id} constraint {index} is rule but has no explicit checker configuration")
            local = evaluate_constraint(response, {**constraint, "check_type": "rule"})
            if local.get("score") not in (0, 1):
                raise ValueError(
                    f"Item {item_id} constraint {index} is rule but local checker did not return a binary score: "
                    f"{local.get('method')} / {local.get('reason')}"
                )
            local["effective_check_type"] = "rule"
            local["judge_used_full_prompt"] = False
            results_by_index[index] = result_metadata(item_id, index, constraint, local)
        elif check_type == "LLM":
            pending.append((index, constraint))
        else:
            raise ValueError(f"Item {item_id} constraint {index} has unsupported check_type {check_type!r}")

    quality = {
        "score": None,
        "normalized_score": None,
        "status": "needs_judge",
        "reason": "No judge call was made.",
        "method": None,
    }
    item_judge: Dict[str, Any] = {}

    prompt = build_item_judge_prompt(item, response, pending)
    if hard_only:
        if pending:
            item_judge = {
                "status": "needs_judge",
                "method": f"judge:{provider.name}",
                "judge_prompt": prompt,
                "raw_judge_outputs": [],
                "errors": ["Skipped LLM judge in hard-only mode."],
                "constraint_scores": {},
            }
            quality.update(
                {
                    "reason": "Skipped LLM judge in hard-only mode.",
                    "method": f"judge:{provider.name}",
                }
            )
            for index, constraint in pending:
                results_by_index[index] = result_metadata(
                    item_id,
                    index,
                    constraint,
                    {
                        "score": None,
                        "status": "needs_judge",
                        "method": f"judge:{provider.name}",
                        "reason": "Skipped LLM judge in hard-only mode.",
                        "judge_prompt": prompt,
                        "effective_check_type": "LLM",
                        "judge_used_full_prompt": True,
                    },
                )
    else:
        request = JudgeRequest(
            item_id=item_id,
            constraints=pending,
            response=response,
            prompt=prompt,
        )
        item_judge = judge_item_with_retries(provider, request, repeats, parse_retries)
        quality = item_judge["quality"]
        for index, constraint in pending:
            judged = item_judge["constraint_scores"].get(index)
            if judged is None:
                judged = {
                    "score": None,
                    "status": "needs_judge",
                    "method": f"judge:{provider.name}",
                    "reason": "Judge unavailable or returned unparsable JSON.",
                    "judge_prompt": prompt,
                }
            judged["effective_check_type"] = "LLM"
            judged["judge_used_full_prompt"] = True
            results_by_index[index] = result_metadata(item_id, index, constraint, judged)

    results = [results_by_index[index] for index in sorted(results_by_index)]
    quality = apply_posthoc_quality_caps(quality, results)
    return {
        "item_id": item_id,
        "line_number": item.get("line_number") or item.get("line") or item.get("_line_number"),
        "dataset_row_number": item.get("_line_number"),
        "quality": quality,
        "item_judge": {
            key: value
            for key, value in item_judge.items()
            if key not in {"constraint_scores", "quality"}
        },
        "results": results,
        "summary": summarize_results(results, quality),
    }


def summarize_results(results: Sequence[Result], quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    decided = [result for result in results if result.get("score") in (0, 1)]
    passed = [result for result in decided if result.get("score") == 1]
    needs_judge = [result for result in results if result.get("score") is None]
    by_method: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "passed": 0, "needs_judge": 0})
    by_tag: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "passed": 0, "needs_judge": 0})

    for result in results:
        method_family = str(result.get("method", "")).split(":", 1)[0] or "unknown"
        tag = str(result.get("tag") or "unknown")
        for bucket in (by_method[method_family], by_tag[tag]):
            bucket["total"] += 1
            if result.get("score") == 1:
                bucket["passed"] += 1
            if result.get("score") is None:
                bucket["needs_judge"] += 1

    return {
        "total_constraints": len(results),
        "decided_constraints": len(decided),
        "passed_constraints": len(passed),
        "needs_judge_constraints": len(needs_judge),
        "score": len(passed) / len(decided) if decided else None,
        "coverage": len(decided) / len(results) if results else None,
        "quality_score": quality.get("score") if quality else None,
        "quality_normalized_score": quality.get("normalized_score") if quality else None,
        "by_method": dict(sorted(by_method.items())),
        "by_tag": dict(sorted(by_tag.items())),
    }


def is_quality_severe_failure(result: Result) -> bool:
    tag = str(result.get("tag") or "").upper()
    text = str(result.get("constraint") or "").casefold()
    if tag in {"EG1", "EG2", "DB1", "DB3", "DB4"}:
        return True
    trigger_terms = (
        "authority",
        "route",
        "trigger",
        "replace the governed",
        "not ready for sign-off",
        "subsequent-events",
        "escalate",
    )
    return any(term in text for term in trigger_terms)


def apply_posthoc_quality_caps(quality: Dict[str, Any], results: Sequence[Result]) -> Dict[str, Any]:
    score = quality.get("score")
    if not isinstance(score, int):
        return quality

    failed = [result for result in results if result.get("score") == 0]
    central_failed = [result for result in failed if str(result.get("tag") or "").upper() in QUALITY_CAP_TAGS]
    if not central_failed:
        return quality

    cap = 6
    reasons = [f"{len(central_failed)} central IF failure(s)"]
    if len(central_failed) >= 2:
        cap = 4
        reasons.append("multiple central failures")
    if any(is_quality_severe_failure(result) for result in central_failed):
        cap = min(cap, 3)
        reasons.append("severe authority/route/trigger failure")

    adjusted = dict(quality)
    adjusted["raw_score"] = score
    adjusted["raw_normalized_score"] = quality.get("normalized_score")
    adjusted["raw_reason"] = quality.get("reason")
    adjusted["score"] = min(score, cap)
    adjusted["normalized_score"] = adjusted["score"] / 10
    if adjusted["score"] != score:
        base_reason = str(quality.get("reason") or "").strip()
        adjusted["reason"] = f"{base_reason} Quality capped to {adjusted['score']}/10 due to {'; '.join(reasons)}.".strip()
    return adjusted


def summarize_dataset(items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    item_summaries = [item["summary"] for item in items]
    total = sum(summary["total_constraints"] for summary in item_summaries)
    decided = sum(summary["decided_constraints"] for summary in item_summaries)
    passed = sum(summary["passed_constraints"] for summary in item_summaries)
    needs_judge = sum(summary["needs_judge_constraints"] for summary in item_summaries)
    item_scores = [summary["score"] for summary in item_summaries if summary["score"] is not None]
    exact_pass_items = [
        summary
        for summary in item_summaries
        if summary["total_constraints"] > 0
        and summary["decided_constraints"] == summary["total_constraints"]
        and summary["passed_constraints"] == summary["total_constraints"]
    ]
    fully_decided_items = [
        summary
        for summary in item_summaries
        if summary["total_constraints"] > 0
        and summary["decided_constraints"] == summary["total_constraints"]
    ]
    quality_scores = [
        item.get("quality", {}).get("score")
        for item in items
        if isinstance(item.get("quality", {}).get("score"), int)
    ]
    quality_norm = [score / 10 for score in quality_scores]
    if_score = passed / decided if decided else None
    quality_mean = sum(quality_norm) / len(quality_norm) if quality_norm else None
    final_score = None
    if if_score is not None and quality_mean is not None:
        final_score = 0.8 * if_score + 0.2 * quality_mean

    return {
        "items": len(items),
        "total_constraints": total,
        "decided_constraints": decided,
        "passed_constraints": passed,
        "needs_judge_constraints": needs_judge,
        "micro_score": if_score,
        "macro_item_score": sum(item_scores) / len(item_scores) if item_scores else None,
        "exact_item_pass_rate": len(exact_pass_items) / len(fully_decided_items) if fully_decided_items else None,
        "exact_item_passed": len(exact_pass_items),
        "exact_item_decided": len(fully_decided_items),
        "strict_failed_items": len(fully_decided_items) - len(exact_pass_items),
        "coverage": decided / total if total else None,
        "quality_score_mean_0_10": sum(quality_scores) / len(quality_scores) if quality_scores else None,
        "quality_score_mean_0_1": quality_mean,
        "quality_scored_items": len(quality_scores),
        "final_score_0_1": final_score,
        "final_score_policy": "0.8 * IF micro_score + 0.2 * mean quality_score/10",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FinIF v2 responses item by item.")
    parser.add_argument("--dataset", required=True, type=Path, help="FinIF v2 full-prompt JSONL with extracted_constraints.")
    parser.add_argument("--responses", required=True, type=Path, help="JSONL with item_id/id/case_id/line_number and response/output.")
    parser.add_argument("--output", required=True, type=Path, help="Path for JSON evaluation results.")
    parser.add_argument("--judge-provider", help="Optional provider as module.path:ClassName. Default is offline stub.")
    parser.add_argument("--hard-only", action="store_true", help="Do not call judge provider; leave judge-needed constraints and quality undecided.")
    parser.add_argument("--repeats", type=int, default=1, help="Repeated judging calls per item for majority voting.")
    parser.add_argument("--parse-retries", type=int, default=2, help="Retries per repeat after malformed judge JSON.")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    responses = load_responses(args.responses)
    provider = load_provider(args.judge_provider)

    evaluated_items = []
    missing_responses = []
    for item_id, item in sorted(dataset.items(), key=lambda pair: pair[1].get("_line_number", 0)):
        response = response_for_item(item, responses)
        if response is None:
            missing_responses.append(item_id)
            continue
        evaluated_items.append(
            evaluate_item(
                item=item,
                response=response,
                provider=provider,
                hard_only=args.hard_only,
                repeats=args.repeats,
                parse_retries=args.parse_retries,
            )
        )

    output = {
        "schema_version": "finif-v2-item-batched-evaluation-results-1.0",
        "dataset": str(args.dataset),
        "responses": str(args.responses),
        "judge_provider": provider.name,
        "judge_temperature_policy": 0,
        "repeats": args.repeats,
        "parse_retries": args.parse_retries,
        "summary": summarize_dataset(evaluated_items),
        "missing_responses": missing_responses,
        "items": evaluated_items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)

    summary = output["summary"]
    print(
        "OK: evaluated {items} item(s), {decided_constraints}/{total_constraints} "
        "constraints decided, micro_score={micro_score}, quality_mean_0_10={quality_score_mean_0_10}, "
        "final_score_0_1={final_score_0_1}".format(**summary)
    )
    if missing_responses:
        print(f"WARNING: missing responses for {len(missing_responses)} item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
