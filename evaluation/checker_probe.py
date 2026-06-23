#!/usr/bin/env python3
"""Smoke probes for FinIF local rule-aided checkers.

These are intentionally small, fast examples that cover every checker type.
They do not replace semantic judge audits; they catch local checker regressions
before an expensive response/judge run.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

try:
    from .checkers import ALIASES, CHECKERS, evaluate_constraint, get_checker_type
except ImportError:  # pragma: no cover - direct script execution.
    from checkers import ALIASES, CHECKERS, evaluate_constraint, get_checker_type


Case = Dict[str, Any]


CASES: List[Case] = [
    {
        "name": "required_keyword pass",
        "response": "The memo flags escalation and missing evidence.",
        "constraint": {"check_type": "rule_aided", "checker_type": "required_keyword", "keywords": ["escalation", "missing evidence"]},
        "score": 1,
    },
    {
        "name": "required_keyword fail",
        "response": "The memo flags escalation.",
        "constraint": {"check_type": "rule_aided", "checker_type": "required_keyword", "keywords": ["missing evidence"]},
        "score": 0,
    },
    {
        "name": "forbidden_phrase pass",
        "response": "Conditional approval only.",
        "constraint": {"check_type": "rule_aided", "checker_type": "forbidden_phrase", "phrases": ["final approval"]},
        "score": 1,
    },
    {
        "name": "forbidden_phrase fail",
        "response": "This is final approval.",
        "constraint": {"check_type": "rule_aided", "checker_type": "forbidden_phrase", "phrases": ["final approval"]},
        "score": 0,
    },
    {
        "name": "min_words pass",
        "response": "one two three four five",
        "constraint": {"check_type": "rule_aided", "checker_type": "min_words", "min": 5},
        "score": 1,
    },
    {
        "name": "max_words fail",
        "response": "one two three four five six",
        "constraint": {"check_type": "rule_aided", "checker_type": "max_words", "max": 5},
        "score": 0,
    },
    {
        "name": "min_sections pass",
        "response": "Facts:\nA\n\nDecision:\nB",
        "constraint": {"check_type": "rule_aided", "checker_type": "min_sections", "min": 2},
        "score": 1,
    },
    {
        "name": "max_sections fail",
        "response": "Alpha:\n1\nBeta:\n2\nGamma:\n3",
        "constraint": {"check_type": "rule_aided", "checker_type": "max_sections", "max": 2},
        "score": 0,
    },
    {
        "name": "item_count pass",
        "response": "1. Risk\n2. Mitigant",
        "constraint": {"check_type": "rule_aided", "checker_type": "item_count", "count": 2},
        "score": 1,
    },
    {
        "name": "ordered_list_count pass",
        "response": "1. Risk\n2. Mitigant\n3. Action",
        "constraint": {"check_type": "rule_aided", "checker_type": "ordered_list_count", "min_count": 3, "max_count": 4},
        "score": 1,
    },
    {
        "name": "no_list fail",
        "response": "- Risk\n- Mitigant",
        "constraint": {"check_type": "rule_aided", "checker_type": "no_list"},
        "score": 0,
    },
    {
        "name": "paragraph_count pass",
        "response": "One paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
        "constraint": {"check_type": "rule_aided", "checker_type": "paragraph_count", "exact_count": 3},
        "score": 1,
    },
    {
        "name": "paragraph_count ignores standalone markdown headings",
        "response": "\n\n".join(f"## Section {i}\n\nEvidence-test-action paragraph {i}." for i in range(1, 10)),
        "constraint": {"check_type": "rule_aided", "checker_type": "paragraph_count", "min_count": 4, "max_count": 9},
        "score": 1,
    },
    {
        "name": "paragraph_count ignores standalone bold title",
        "response": "**Control Memo**\n\nOne paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n\nFourth paragraph.",
        "constraint": {"check_type": "rule_aided", "checker_type": "paragraph_count", "exact_count": 4},
        "score": 1,
    },
    {
        "name": "valid_json fail",
        "response": "{\"a\": 1",
        "constraint": {"check_type": "rule_aided", "checker_type": "valid_json"},
        "score": 0,
    },
    {
        "name": "required_fields json pass",
        "response": "{\"status\":\"Open\",\"owner\":\"Ops\"}",
        "constraint": {"check_type": "rule_aided", "checker_type": "required_fields", "required_fields": ["status", "owner"], "format": "json"},
        "score": 1,
    },
    {
        "name": "markdown_table pass",
        "response": "| A | B |\n|---|---|\n| 1 | 2 |",
        "constraint": {"check_type": "rule_aided", "checker_type": "markdown_table"},
        "score": 1,
    },
    {
        "name": "no_table fail",
        "response": "| A | B |\n|---|---|\n| 1 | 2 |",
        "constraint": {"check_type": "rule_aided", "checker_type": "no_table"},
        "score": 0,
    },
    {
        "name": "table_columns fail",
        "response": "| Status | Owner |\n|---|---|\n| Open | Ops |",
        "constraint": {"check_type": "rule_aided", "checker_type": "table_columns", "columns": ["Status", "Aging"]},
        "score": 0,
    },
    {
        "name": "table_columns inferred pass",
        "response": "| Trigger | Evidence | Required recipient |\n|---|---|---|\n| Breach | DOC1 | CCO |",
        "constraint": {
            "check_type": "rule_aided",
            "constraint": "The response must use a table with Trigger, Evidence, and Required recipient.",
            "tag": "FP2",
        },
        "score": 1,
    },
    {
        "name": "table_columns inferred fail",
        "response": "| Trigger | Evidence |\n|---|---|\n| Breach | DOC1 |",
        "constraint": {
            "check_type": "rule_aided",
            "constraint": "The response must use a table with Trigger, Evidence, and Required recipient.",
            "tag": "FP2",
        },
        "score": 0,
    },
    {
        "name": "table_row_count pass",
        "response": "| Status | Owner |\n|---|---|\n| Open | Ops |\n| Hold | Legal |",
        "constraint": {"check_type": "rule_aided", "checker_type": "table_row_count", "exact_rows": 2},
        "score": 1,
    },
    {
        "name": "checkbox pass",
        "response": "- [x] Evidence received",
        "constraint": {"check_type": "rule_aided", "checker_type": "checkbox"},
        "score": 1,
    },
    {
        "name": "blockquote_count fail",
        "response": "> Evidence excerpt\n\nDecision follows.",
        "constraint": {"check_type": "rule_aided", "checker_type": "blockquote_count", "min_count": 2},
        "score": 0,
    },
    {
        "name": "contains_number pass",
        "response": "The threshold is $3,600,000.",
        "constraint": {"check_type": "rule_aided", "checker_type": "contains_number", "numbers": ["3600000"]},
        "score": 1,
    },
    {
        "name": "threshold fail",
        "response": "The limit is $2,000.",
        "constraint": {"check_type": "rule_aided", "checker_type": "threshold", "thresholds": ["5000"]},
        "score": 0,
    },
    {
        "name": "deadline pass",
        "response": "Report within 30 calendar days.",
        "constraint": {"check_type": "rule_aided", "checker_type": "deadline", "deadlines": ["30 calendar days"]},
        "score": 1,
    },
    {
        "name": "exact_value pass",
        "response": "Status: Open. Owner: Treasury Operations.",
        "constraint": {"check_type": "rule_aided", "checker_type": "exact_value", "expected_values": {"Status": "Open", "Owner": "Treasury Operations"}},
        "score": 1,
    },
    {
        "name": "decimal_places fail on integer",
        "response": "Amount: $10.",
        "constraint": {"check_type": "rule_aided", "checker_type": "decimal_places", "count": 2},
        "score": 0,
    },
    {
        "name": "decimal_places percent words pass",
        "response": "The cushion is 25.00 percent and the sensitivity is 3.50 percentage points.",
        "constraint": {"check_type": "rule_aided", "checker_type": "decimal_places", "count": 2, "target": "percent"},
        "score": 1,
    },
    {
        "name": "decimal_places percent words fail",
        "response": "The cushion is 25 percent and the sensitivity is 3.5 percentage points.",
        "constraint": {"check_type": "rule_aided", "checker_type": "decimal_places", "count": 2, "target": "percent"},
        "score": 0,
    },
    {
        "name": "first_line pass",
        "response": "Open\nDetails follow.",
        "constraint": {"check_type": "rule_aided", "checker_type": "first_line", "line": "Open"},
        "score": 1,
    },
    {
        "name": "first_line_format pass",
        "response": "**Decision: Hold**\nDetails follow.",
        "constraint": {"check_type": "rule_aided", "checker_type": "first_line_format", "format": "bold"},
        "score": 1,
    },
    {
        "name": "last_line fail",
        "response": "Details\nClosed",
        "constraint": {"check_type": "rule_aided", "checker_type": "last_line", "line": "Open"},
        "score": 0,
    },
    {
        "name": "conditional_trigger fail",
        "response": "Escalate due to breach.",
        "constraint": {"check_type": "rule_aided", "checker_type": "conditional_trigger", "trigger": "breach", "followup": "CCO"},
        "score": 0,
    },
    {
        "name": "simple_regex pass",
        "response": "Case ID: ESC-2015",
        "constraint": {"check_type": "rule_aided", "checker_type": "simple_regex", "pattern": r"ESC-\d+"},
        "score": 1,
    },
    {
        "name": "forbidden_regex fail",
        "response": "Cited ARCH-001.",
        "constraint": {"check_type": "rule_aided", "checker_type": "forbidden_regex", "forbidden_regex": r"ARCH-\d{3}"},
        "score": 0,
    },
    {
        "name": "regex_count pass",
        "response": "DOC1 supports A. DOC2 supports B.",
        "constraint": {"check_type": "rule_aided", "checker_type": "regex_count", "pattern": r"DOC\d", "exact_count": 2},
        "score": 1,
    },
    {
        "name": "forbidden_regex_before_heading pass",
        "response": "Intro\n\nAllowed:\nARCH-001 appears after heading.",
        "constraint": {"check_type": "rule_aided", "checker_type": "forbidden_regex_before_heading", "forbidden_regex": r"ARCH-\d{3}", "heading": "Allowed"},
        "score": 1,
    },
    {
        "name": "heading_order fail",
        "response": "Decision:\nNo\n\nEvidence:\nDOC1",
        "constraint": {"check_type": "rule_aided", "checker_type": "heading_order", "headings": ["Evidence", "Decision"]},
        "score": 0,
    },
    {
        "name": "heading_level pass",
        "response": "## Evidence\nDOC1\n\n## Decision\nHold",
        "constraint": {"check_type": "rule_aided", "checker_type": "heading_level", "level": 2, "exact_count": 2},
        "score": 1,
    },
    {
        "name": "heading_depth fail",
        "response": "## Evidence\nDOC1\n\n## Decision\nHold",
        "constraint": {"check_type": "rule_aided", "checker_type": "heading_depth", "min_depth": 2},
        "score": 0,
    },
    {
        "name": "word_range pass current style",
        "response": "一二三 four five",
        "constraint": {"check_type": "rule", "checker": "check_word_range", "params": {"min_words": 5, "max_words": 8}},
        "score": 1,
    },
    {
        "name": "section_titles pass",
        "response": "Organization Finding\nA\n\nItem 105 Basis\nB",
        "constraint": {"check_type": "rule", "checker_type": "section_titles", "required_titles": ["Organization Finding", "Item 105 Basis"]},
        "score": 1,
    },
    {
        "name": "sentence_count pass",
        "response": "First sentence is useful. Second sentence is useful.",
        "constraint": {"check_type": "rule", "checker_type": "sentence_count", "min_count": 2},
        "score": 1,
    },
    {
        "name": "json_field_count pass",
        "response": "{\"items\":[\"a\",\"b\"]}",
        "constraint": {"check_type": "rule", "checker_type": "json_field_count", "field": "items", "exact_count": 2},
        "score": 1,
    },
    {
        "name": "json_field_item_limit fail",
        "response": "{\"items\":[\"short\",\"too long\"]}",
        "constraint": {"check_type": "rule", "checker_type": "json_field_item_limit", "field": "items", "max_chars": 5},
        "score": 0,
    },
    {
        "name": "json_field_word_limit fail",
        "response": "{\"summary\":\"abcdef\"}",
        "constraint": {"check_type": "rule", "checker_type": "json_field_word_limit", "field": "summary", "max_chars": 3},
        "score": 0,
    },
    {
        "name": "code_block pass",
        "response": "```text\nformula\n```",
        "constraint": {"check_type": "rule", "checker_type": "code_block", "min_count": 1},
        "score": 1,
    },
    {
        "name": "first_word pass",
        "response": "**截至** the file remains open.",
        "constraint": {"check_type": "rule", "checker": "check_first_word", "params": {"word": "截至"}},
        "score": 1,
    },
    {
        "name": "first_last_line pass",
        "response": "Summary\nDetails\n---",
        "constraint": {"check_type": "rule", "checker": "check_first_last_line", "params": {"first_line": "Summary", "last_line": "---"}},
        "score": 1,
    },
    {
        "name": "keyword_presence pass",
        "response": "风险 and 机遇 are both covered.",
        "constraint": {"check_type": "rule", "checker": "check_keyword_presence", "params": {"required_keywords": ["风险", "机遇"], "match_all": True}},
        "score": 1,
    },
    {
        "name": "keyword_absence fail",
        "response": "This says 建议买入.",
        "constraint": {"check_type": "rule", "checker_type": "keyword_absence", "forbidden_keywords": ["建议买入"]},
        "score": 0,
    },
    {
        "name": "first_person fail",
        "response": "本报告认为该事项仍需观察。",
        "constraint": {"check_type": "rule", "checker": "check_first_person", "params": {"forbidden_phrases": ["本报告", "报告认为"]}},
        "score": 0,
    },
    {
        "name": "risk_disclaimer pass",
        "response": "Details.\n以上内容仅供参考，不构成投资建议",
        "constraint": {"check_type": "rule", "checker": "check_risk_disclaimer", "params": {"risk_line": "以上内容仅供参考，不构成投资建议"}},
        "score": 1,
    },
    {
        "name": "currency_format fail",
        "response": "金额为100元。",
        "constraint": {"check_type": "rule", "checker": "check_currency_format", "params": {"unit": "亿元", "forbidden_units": []}},
        "score": 0,
    },
    {
        "name": "no_percent fail",
        "response": "增长5%。",
        "constraint": {"check_type": "rule", "checker": "check_no_percent"},
        "score": 0,
    },
    {
        "name": "no_arabic_numerals fail",
        "response": "金额为100元。",
        "constraint": {"check_type": "rule", "checker": "check_no_arabic_numerals"},
        "score": 0,
    },
]


def main() -> int:
    covered = set()
    failures = []
    for case in CASES:
        result = evaluate_constraint(case["response"], case["constraint"])
        checker_type = case["constraint"].get("checker_type")
        if not checker_type:
            checker_type = ALIASES.get(get_checker_type(case["constraint"]) or "", get_checker_type(case["constraint"]))
        covered.add(checker_type)
        if result.get("score") != case["score"]:
            failures.append(
                {
                    "name": case["name"],
                    "checker_type": checker_type,
                    "expected": case["score"],
                    "actual": result.get("score"),
                    "status": result.get("status"),
                    "reason": result.get("reason"),
                }
            )

    missing = sorted(set(CHECKERS) - covered)
    output = {
        "cases": len(CASES),
        "covered_checkers": sorted(covered),
        "missing_checkers": missing,
        "failures": failures,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if failures or missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
