#!/usr/bin/env python3
"""Audit FinIF constraint routing before running an API judge.

This script is intentionally static: it does not need model responses and it
does not call a judge. It answers two practical questions:

- Which constraints are explicitly routed to deterministic local rules?
- Which constraints are explicitly routed to the LLM judge?
- Are any rule-routed constraints missing explicit checker configuration?
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from .checkers import ALIASES, evaluate_constraint, get_checker_type
    from .evaluate_responses import has_explicit_rule_config, normalize_check_type
except ImportError:  # pragma: no cover - allows direct script execution.
    from checkers import ALIASES, evaluate_constraint, get_checker_type
    from evaluate_responses import has_explicit_rule_config, normalize_check_type


Constraint = Dict[str, Any]


PROBE_RESPONSE = "\n".join(
    [
        "Evidence:",
        "| Status | Owner |",
        "|---|---|",
        "| Open | Ops |",
        "1. Example item",
        "- [x] Example checkbox",
        "Decision: Hold.",
        "Amount: $10.",
    ]
)


def load_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            yield line_number, obj


def constraints_for_item(item: Dict[str, Any]) -> List[Constraint]:
    constraints = item.get("extracted_constraints") or item.get("constraints") or []
    if not isinstance(constraints, list):
        return []
    return [constraint for constraint in constraints if isinstance(constraint, dict)]


def normalized_checker_type(constraint: Constraint) -> str:
    checker_type = get_checker_type(constraint)
    checker_type = ALIASES.get(checker_type or "", checker_type)
    return checker_type or "unresolved"


def local_probe(constraint: Constraint) -> Dict[str, Any]:
    result = evaluate_constraint(PROBE_RESPONSE, {**constraint, "check_type": "rule"})
    return {
        "score": result.get("score"),
        "status": result.get("status"),
        "method": result.get("method"),
        "checker_type": normalized_checker_type(constraint),
        "decidable": result.get("score") in (0, 1),
        "reason": result.get("reason"),
    }


def current_route(constraint: Constraint) -> Dict[str, Any]:
    declared = normalize_check_type(constraint.get("check_type", "LLM"))
    tag = str(constraint.get("tag") or "").upper()
    explicit = has_explicit_rule_config(constraint)
    probe = None

    if declared == "rule":
        if not explicit:
            route = "rule_config_error"
        else:
            probe = local_probe(constraint)
            route = "local_binary" if probe["decidable"] else "rule_config_error"
    elif declared == "LLM":
        route = "judge_direct"
    else:
        route = "schema_error"
    checker_type = normalized_checker_type(constraint) if declared == "rule" or explicit else "LLM"

    return {
        "declared_check_type": declared,
        "tag": tag or "unknown",
        "explicit_rule_config": explicit,
        "rule_first": declared == "rule",
        "route": route,
        "checker_type": checker_type,
        "potentially_rule_decidable": bool(probe and probe["decidable"]),
        "probe_method": probe["method"] if probe else None,
        "probe_reason": probe["reason"] if probe else None,
    }


def item_id(item: Dict[str, Any], line_number: int) -> str:
    return str(item.get("id") or item.get("item_id") or item.get("case_id") or line_number)


def audit(path: Path, example_limit: int) -> Dict[str, Any]:
    by_route: Counter[str] = Counter()
    by_declared: Counter[str] = Counter()
    by_checker: Counter[str] = Counter()
    by_tag_route: Counter[Tuple[str, str]] = Counter()
    examples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total = 0
    items = 0

    for line_number, item in load_jsonl(path):
        items += 1
        iid = item_id(item, line_number)
        for index, constraint in enumerate(constraints_for_item(item)):
            total += 1
            route = current_route(constraint)
            by_route[route["route"]] += 1
            by_declared[route["declared_check_type"]] += 1
            by_checker[route["checker_type"]] += 1
            by_tag_route[(route["tag"], route["route"])] += 1

            bucket = None
            if route["route"] in {"rule_config_error", "schema_error"}:
                bucket = route["route"]
            elif route["route"] == "judge_direct" and route["explicit_rule_config"]:
                bucket = "judge_direct_with_rule_config"

            if bucket and len(examples[bucket]) < example_limit:
                examples[bucket].append(
                    {
                        "item_id": iid,
                        "line_number": line_number,
                        "constraint_index": index,
                        "tag": route["tag"],
                        "declared_check_type": route["declared_check_type"],
                        "checker_type": route["checker_type"],
                        "constraint": constraint.get("constraint", ""),
                        "probe_method": route["probe_method"],
                        "probe_reason": route["probe_reason"],
                    }
                )

    return {
        "dataset": str(path),
        "items": items,
        "total_constraints": total,
        "by_route": dict(by_route.most_common()),
        "by_declared_check_type": dict(by_declared.most_common()),
        "by_checker_type_probe": dict(by_checker.most_common()),
        "by_tag_route": {
            f"{tag}::{route}": count
            for (tag, route), count in by_tag_route.most_common()
        },
        "examples": dict(examples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local-vs-judge constraint routing.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument("--example-limit", type=int, default=8)
    args = parser.parse_args()

    report = audit(args.dataset, args.example_limit)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
