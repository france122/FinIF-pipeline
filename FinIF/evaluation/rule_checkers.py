#!/usr/bin/env python3
"""Lightweight FinIF v2 constraint checkers.

The checker returns a local binary score when a constraint is mechanically
checkable. Semantic constraints return score None with the standard judge prompt.
"""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional


JUDGE_PROMPT_TEMPLATE = """Given the response and the constraint, does the response satisfy this constraint?
Answer pass or fail, and give a short reason.

Constraint:
{constraint}

Response:
{response}"""


JUDGE_PROMPT_TEMPLATE_WITH_DOCS = """Given the response and the constraint, does the response satisfy this constraint?
Treat the source documents below as the only ground truth for facts, figures, dates, citations, and what counts as a supplied document. Any factual claim, number, or citation in the response that is not supported by these documents fails a grounding or accuracy constraint. Answer pass or fail, and give a short reason.

Constraint:
{constraint}

Source documents:
{documents}

Response:
{response}"""


Result = Dict[str, Any]
Constraint = Dict[str, Any]


def format_documents(documents: Any) -> str:
    parts: List[str] = []
    for doc in as_list(documents):
        if not isinstance(doc, dict):
            continue
        doc_id = str(doc.get("id") or "DOC").strip()
        title = str(doc.get("title") or "").strip()
        content = str(doc.get("content") or "").strip()
        header = f"[{doc_id} - {title}]" if title else f"[{doc_id}]"
        parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)


def build_judge_prompt(response: str, constraint: Constraint, documents: Any = None) -> str:
    docs_text = format_documents(documents).strip() if documents else ""
    if docs_text:
        return JUDGE_PROMPT_TEMPLATE_WITH_DOCS.format(
            constraint=constraint.get("constraint", "").strip(),
            documents=docs_text,
            response=response.strip(),
        )
    return JUDGE_PROMPT_TEMPLATE.format(
        constraint=constraint.get("constraint", "").strip(),
        response=response.strip(),
    )


def unresolved(response: str, constraint: Constraint, method: str = "judge") -> Result:
    return {
        "score": None,
        "status": "needs_judge",
        "reason": build_judge_prompt(response, constraint),
        "method": method,
    }


def pass_result(reason: str, method: str) -> Result:
    return {"score": 1, "status": "pass", "reason": reason, "method": method}


def fail_result(reason: str, method: str) -> Result:
    return {"score": 0, "status": "fail", "reason": reason, "method": method}


def normalize(text: str, case_sensitive: bool = False) -> str:
    return text if case_sensitive else text.casefold()


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def checker_config(constraint: Constraint) -> Dict[str, Any]:
    """Merge supported checker config locations into one dict."""
    config: Dict[str, Any] = {}
    for key in ("evaluator", "checker", "rule", "params"):
        value = constraint.get(key)
        if isinstance(value, dict):
            config.update(value)
    for key in (
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
        "field",
        "first_line",
        "last_line",
        "max_chars",
        "min_words",
        "max_words",
        "required_keywords",
        "forbidden_keywords",
        "required_titles",
        "risk_line",
        "unit",
        "forbidden_units",
        "places",
    ):
        if key in constraint and key not in config:
            config[key] = constraint[key]
    return config


def get_checker_type(constraint: Constraint) -> Optional[str]:
    config = checker_config(constraint)
    raw = (
        config.get("type")
        or config.get("checker_type")
        or config.get("name")
        or config.get("method")
        or constraint.get("checker")
    )
    if isinstance(raw, str):
        raw = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return raw or infer_checker_type(constraint)


def infer_checker_type(constraint: Constraint) -> Optional[str]:
    text = constraint.get("constraint", "").casefold()
    tag = str(constraint.get("tag", "")).upper()
    if "valid json" in text or "json" in text and "format" in text:
        return "valid_json"
    if any(term in text for term in ("forbidden", "do not use", "must not use", "avoid the phrase")):
        return "forbidden_phrase"
    if any(term in text for term in ("deadline", "within", "days", "calendar-day", "annual", "annually")):
        if tag == "QV5" or "timing" in text or "deadline" in text:
            return "deadline"
    if any(term in text for term in ("threshold", "$", "%", "at least", "minimum", "maximum")):
        if tag == "QV4" or re.search(r"[$]?\d", text):
            return "contains_number"
    if tag.startswith("FP"):
        if "table" in text or "matrix" in text:
            if any(term in text for term in ("column", "columns", "two-column", "headers")) or re.search(r"\btable with\b[^.]*,", text):
                return "table_columns"
            return "markdown_table"
        if "checklist" in text or "checkbox" in text:
            return "checkbox"
        if any(term in text for term in ("section", "heading")):
            return "min_sections"
        if any(term in text for term in ("word", "words")):
            if any(term in text for term in ("no more than", "maximum", "under", "fewer than")):
                return "max_words"
            return "min_words"
    return None


def word_count(response: str) -> int:
    return len(re.findall(r"\b[\w][\w'-]*\b", response))


def mixed_word_count(response: str) -> int:
    """Count English words plus CJK characters for legacy/current constraints."""
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", response))
    english_words = len(re.findall(r"[A-Za-z]+", response))
    return cjk_chars + english_words


def section_count(response: str) -> int:
    headings = re.findall(r"(?m)^\s{0,3}#{1,6}\s+\S+", response)
    if headings:
        return len(headings)
    label_headings = re.findall(r"(?m)^\s*(?:\d+[.)]\s*)?[\w][\w\s/&-]{1,80}:\s*$", response)
    return len(label_headings)


def item_count(response: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S+", response))


def ordered_list_count(response: str) -> int:
    return len(re.findall(r"(?m)^\s*\d+[.)]\s+\S+", response))


def paragraph_count(response: str) -> int:
    blocks = re.split(r"\n\s*\n", response.strip())
    count = 0
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1:
            line = lines[0]
            if re.match(r"^#{1,6}\s+\S+", line):
                continue
            if re.match(r"^\*\*[^*][\s\S]*\*\*$", line):
                continue
        count += 1
    return count


def sentence_count(response: str) -> int:
    sentences = re.split(r"[。！？!?]+|(?<=[A-Za-z0-9][.])\s+", response)
    return len([s for s in sentences if len(s.strip()) > 5])


def blockquote_count(response: str) -> int:
    return len(re.findall(r"(?m)^\s*>\s+\S+", response))


def heading_level_count(response: str, level: int) -> int:
    if level < 1 or level > 6:
        return 0
    pattern = rf"(?m)^\s{{0,3}}#{{{level}}}\s+\S+"
    return len(re.findall(pattern, response))


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```\w*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def markdown_table_lines(response: str) -> List[str]:
    return [line.strip() for line in response.splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]


def has_markdown_table(response: str) -> bool:
    lines = markdown_table_lines(response)
    if len(lines) < 2:
        return False
    return any(re.match(r"^\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$", line) for line in lines)


def json_value(response: str) -> Any:
    return json.loads(strip_code_fence(response))


def extract_numbers(text: str) -> List[str]:
    raw_numbers = re.findall(r"(?<!\w)(?:[$€£])?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|days?|calendar-days?|years?)?", text, flags=re.I)
    return [canonical_number(number) for number in raw_numbers]


def canonical_number(value: Any) -> str:
    text = str(value).strip().casefold()
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("percent", "%")
    return text


def check_required_keyword(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    keywords = [str(k) for k in as_list(config.get("keywords") or config.get("keyword"))]
    if not keywords:
        keywords = quoted_terms(constraint.get("constraint", ""))
    if not keywords:
        return unresolved(response, constraint, "rule_aided:required_keyword")
    case_sensitive = bool(config.get("case_sensitive", False))
    haystack = normalize(response, case_sensitive)
    missing = [kw for kw in keywords if normalize(kw, case_sensitive) not in haystack]
    if missing:
        return fail_result(f"Missing required keyword(s): {', '.join(missing)}.", "rule_aided:required_keyword")
    return pass_result("All required keyword(s) were found.", "rule_aided:required_keyword")


def check_forbidden_phrase(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    phrases = [str(p) for p in as_list(config.get("phrases") or config.get("phrase") or config.get("keywords"))]
    if not phrases:
        phrases = quoted_terms(constraint.get("constraint", ""))
    if not phrases:
        return unresolved(response, constraint, "rule_aided:forbidden_phrase")
    case_sensitive = bool(config.get("case_sensitive", False))
    haystack = normalize(response, case_sensitive)
    found = [phrase for phrase in phrases if normalize(phrase, case_sensitive) in haystack]
    if found:
        return fail_result(f"Found forbidden phrase(s): {', '.join(found)}.", "rule_aided:forbidden_phrase")
    return pass_result("No forbidden phrase(s) were found.", "rule_aided:forbidden_phrase")


def quoted_terms(text: str) -> List[str]:
    terms = re.findall(r'"([^"]+)"|“([^”]+)”|\'([^\']+)\'', text)
    return [next(part for part in term if part).strip() for term in terms]


def configured_int(constraint: Constraint, key: str) -> Optional[int]:
    config = checker_config(constraint)
    value = config.get(key)
    if value is None and key == "count":
        value = config.get("exact")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_word_limit(constraint: Constraint, kind: str) -> Optional[int]:
    text = constraint.get("constraint", "")
    patterns = {
        "min": [r"at least\s+(\d+)\s+words?", r"minimum of\s+(\d+)\s+words?"],
        "max": [r"no more than\s+(\d+)\s+words?", r"maximum of\s+(\d+)\s+words?", r"under\s+(\d+)\s+words?", r"fewer than\s+(\d+)\s+words?"],
    }
    for pattern in patterns[kind]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return int(match.group(1))
    return None


def check_min_words(response: str, constraint: Constraint) -> Result:
    limit = configured_int(constraint, "min") or infer_word_limit(constraint, "min")
    if limit is None:
        return unresolved(response, constraint, "rule_aided:min_words")
    count = word_count(response)
    if count < limit:
        return fail_result(f"Response has {count} words; expected at least {limit}.", "rule_aided:min_words")
    return pass_result(f"Response has {count} words; expected at least {limit}.", "rule_aided:min_words")


def check_max_words(response: str, constraint: Constraint) -> Result:
    limit = configured_int(constraint, "max") or infer_word_limit(constraint, "max")
    if limit is None:
        return unresolved(response, constraint, "rule_aided:max_words")
    count = word_count(response)
    if count > limit:
        return fail_result(f"Response has {count} words; expected at most {limit}.", "rule_aided:max_words")
    return pass_result(f"Response has {count} words; expected at most {limit}.", "rule_aided:max_words")


def check_word_range(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    minimum = config.get("min_words", config.get("min"))
    maximum = config.get("max_words", config.get("max"))
    try:
        minimum = int(minimum) if minimum is not None else None
        maximum = int(maximum) if maximum is not None else None
    except (TypeError, ValueError):
        return unresolved(response, constraint, "rule_aided:word_range")
    if minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:word_range")
    count = mixed_word_count(response)
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} mixed word/character unit(s); expected at least {minimum}.", "rule_aided:word_range")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} mixed word/character unit(s); expected at most {maximum}.", "rule_aided:word_range")
    return pass_result(f"Response has {count} mixed word/character unit(s).", "rule_aided:word_range")


def check_min_sections(response: str, constraint: Constraint) -> Result:
    minimum = configured_int(constraint, "min")
    if minimum is None:
        minimum = len(quoted_terms(constraint.get("constraint", ""))) or None
    if minimum is None:
        return unresolved(response, constraint, "rule_aided:min_sections")
    count = section_count(response)
    if count < minimum:
        return fail_result(f"Response has {count} section(s); expected at least {minimum}.", "rule_aided:min_sections")
    return pass_result(f"Response has {count} section(s); expected at least {minimum}.", "rule_aided:min_sections")


def check_max_sections(response: str, constraint: Constraint) -> Result:
    maximum = configured_int(constraint, "max")
    if maximum is None:
        return unresolved(response, constraint, "rule_aided:max_sections")
    count = section_count(response)
    if count > maximum:
        return fail_result(f"Response has {count} section(s); expected at most {maximum}.", "rule_aided:max_sections")
    return pass_result(f"Response has {count} section(s); expected at most {maximum}.", "rule_aided:max_sections")


def check_item_count(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    mode = str(config.get("mode") or "exact").lower()
    target = configured_int(constraint, "count") or configured_int(constraint, "min")
    if target is None:
        match = re.search(r"(?:exactly|at least)\s+(\d+)\s+(?:items?|findings?|bullets?|points?)", constraint.get("constraint", ""), flags=re.I)
        if match:
            target = int(match.group(1))
            mode = "at_least" if match.group(0).casefold().startswith("at least") else "exact"
    if target is None:
        return unresolved(response, constraint, "rule_aided:item_count")
    count = item_count(response)
    if mode in ("at_least", "minimum", "min"):
        passed = count >= target
        expectation = f"at least {target}"
    else:
        passed = count == target
        expectation = f"exactly {target}"
    if not passed:
        return fail_result(f"Response has {count} item(s); expected {expectation}.", "rule_aided:item_count")
    return pass_result(f"Response has {count} item(s); expected {expectation}.", "rule_aided:item_count")


def check_ordered_list_count(response: str, constraint: Constraint) -> Result:
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:ordered_list_count")
    count = ordered_list_count(response)
    if exact is not None and count != exact:
        return fail_result(f"Response has {count} ordered list item(s); expected exactly {exact}.", "rule_aided:ordered_list_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} ordered list item(s); expected at least {minimum}.", "rule_aided:ordered_list_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} ordered list item(s); expected at most {maximum}.", "rule_aided:ordered_list_count")
    return pass_result(f"Response has {count} ordered list item(s).", "rule_aided:ordered_list_count")


def check_no_list(response: str, constraint: Constraint) -> Result:
    if re.search(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S+", response):
        return fail_result("A list item was found.", "rule_aided:no_list")
    return pass_result("No list items were found.", "rule_aided:no_list")


def check_paragraph_count(response: str, constraint: Constraint) -> Result:
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:paragraph_count")
    count = paragraph_count(response)
    if exact is not None and count != exact:
        return fail_result(f"Response has {count} paragraph(s); expected exactly {exact}.", "rule_aided:paragraph_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} paragraph(s); expected at least {minimum}.", "rule_aided:paragraph_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} paragraph(s); expected at most {maximum}.", "rule_aided:paragraph_count")
    return pass_result(f"Response has {count} paragraph(s).", "rule_aided:paragraph_count")


def check_sentence_count(response: str, constraint: Constraint) -> Result:
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:sentence_count")
    count = sentence_count(response)
    if exact is not None and count != exact:
        return fail_result(f"Response has {count} sentence(s); expected exactly {exact}.", "rule_aided:sentence_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} sentence(s); expected at least {minimum}.", "rule_aided:sentence_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} sentence(s); expected at most {maximum}.", "rule_aided:sentence_count")
    return pass_result(f"Response has {count} sentence(s).", "rule_aided:sentence_count")


def check_valid_json(response: str, constraint: Constraint) -> Result:
    try:
        json_value(response)
    except json.JSONDecodeError as exc:
        return fail_result(f"Response is not valid JSON: {exc.msg}.", "rule_aided:valid_json")
    return pass_result("Response is valid JSON.", "rule_aided:valid_json")


def check_required_fields(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    fields = [str(field) for field in as_list(config.get("required_fields") or config.get("fields"))]
    if not fields:
        fields = quoted_terms(constraint.get("constraint", ""))
    if not fields:
        return unresolved(response, constraint, "rule_aided:required_fields")

    if config.get("format") == "json" or get_checker_type({"evaluator": config}) == "valid_json":
        try:
            obj = json_value(response)
        except json.JSONDecodeError as exc:
            return fail_result(f"Cannot check fields because response is not valid JSON: {exc.msg}.", "rule_aided:required_fields")
        if not isinstance(obj, dict):
            return fail_result("Response JSON is not an object with named fields.", "rule_aided:required_fields")
        missing = [field for field in fields if field not in obj]
    else:
        missing = [field for field in fields if re.search(rf"(?im)^\s*(?:[-*]\s*)?{re.escape(field)}\s*[:|]", response) is None and field not in response]

    if missing:
        return fail_result(f"Missing required field(s): {', '.join(missing)}.", "rule_aided:required_fields")
    return pass_result("All required field(s) were found.", "rule_aided:required_fields")


def check_json_field_count(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    field = config.get("field")
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    if exact is None:
        return unresolved(response, constraint, "rule_aided:json_field_count")
    try:
        obj = json_value(response)
    except json.JSONDecodeError as exc:
        return fail_result(f"Response is not valid JSON: {exc.msg}.", "rule_aided:json_field_count")
    target = obj.get(field) if field and isinstance(obj, dict) else obj
    if isinstance(target, (list, dict)):
        count = len(target)
    else:
        return fail_result("Target JSON value is not a list or object.", "rule_aided:json_field_count")
    if count != exact:
        return fail_result(f"JSON target has {count} item(s); expected exactly {exact}.", "rule_aided:json_field_count")
    return pass_result(f"JSON target has exactly {exact} item(s).", "rule_aided:json_field_count")


def check_json_field_item_limit(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    field = config.get("field")
    max_chars = configured_int(constraint, "max_chars") or configured_int(constraint, "max")
    if field is None or max_chars is None:
        return unresolved(response, constraint, "rule_aided:json_field_item_limit")
    try:
        obj = json_value(response)
    except json.JSONDecodeError as exc:
        return fail_result(f"Response is not valid JSON: {exc.msg}.", "rule_aided:json_field_item_limit")
    items = obj.get(field) if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return fail_result(f"JSON field {field!r} is not a list.", "rule_aided:json_field_item_limit")
    too_long = [str(item) for item in items if len(str(item)) > max_chars]
    if too_long:
        return fail_result(f"{len(too_long)} JSON field item(s) exceed {max_chars} characters.", "rule_aided:json_field_item_limit")
    return pass_result(f"All JSON field items are within {max_chars} characters.", "rule_aided:json_field_item_limit")


def check_json_field_word_limit(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    field = config.get("field")
    max_chars = configured_int(constraint, "max_chars") or configured_int(constraint, "max")
    if field is None or max_chars is None:
        return unresolved(response, constraint, "rule_aided:json_field_word_limit")
    try:
        obj = json_value(response)
    except json.JSONDecodeError as exc:
        return fail_result(f"Response is not valid JSON: {exc.msg}.", "rule_aided:json_field_word_limit")
    value = obj.get(field) if isinstance(obj, dict) else None
    if value is None:
        return pass_result(f"JSON field {field!r} is absent; no field word limit applies.", "rule_aided:json_field_word_limit")
    if len(str(value)) > max_chars:
        return fail_result(f"JSON field {field!r} exceeds {max_chars} characters.", "rule_aided:json_field_word_limit")
    return pass_result(f"JSON field {field!r} is within {max_chars} characters.", "rule_aided:json_field_word_limit")


def clean_column_name(value: str) -> str:
    value = strip_inline_markup(value)
    value = re.sub(r"\s+", " ", value).strip(" .;:|")
    value = re.sub(r"^(?:and|or)\s+", "", value, flags=re.I)
    return value.strip()


def strip_inline_markup(value: str) -> str:
    """Remove Markdown emphasis/code markup so header cells compare on text."""
    value = value.replace("`", "")
    value = re.sub(r"\*{1,3}|_{1,3}", "", value)
    return value


def split_column_segment(segment: str, *, force_and_split: bool = False) -> List[str]:
    segment = re.sub(r"\s+", " ", segment).strip(" .;:")
    if "," in segment:
        raw_parts = [part.strip() for part in segment.split(",")]
        parts: List[str] = []
        for part in raw_parts:
            if re.search(r"\s+and\s+", part, flags=re.I):
                part = re.sub(r"^\s*and\s+", "", part, flags=re.I)
            parts.append(part)
    elif force_and_split:
        parts = re.split(r"\s+and\s+", segment, flags=re.I)
    else:
        parts = [segment]
    return [clean_column_name(part) for part in parts if clean_column_name(part)]


def infer_table_columns(text: str) -> List[str]:
    """Infer explicit table column names from common benchmark phrasing.

    This stays conservative: it only extracts short segments after words such
    as "columns" or "two-column table of". Semantic table requirements still
    defer to the judge.
    """
    patterns = [
        (r"(?:columns?|headers?)\s+(?:named\s+)?(.+?)(?:\.|;|$)", False),
        (r"two-column table of\s+(.+?)(?:\.|;|$)", True),
        (r"table with\s+(.+?)(?:\.|;|$)", False),
    ]
    for pattern, force_and_split in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue
        columns = split_column_segment(match.group(1), force_and_split=force_and_split)
        columns = [column for column in columns if len(column.split()) <= 6]
        if len(columns) >= 2:
            return columns
    return []


def check_markdown_table(response: str, constraint: Constraint) -> Result:
    if has_markdown_table(response):
        return pass_result("A Markdown table was found.", "rule_aided:markdown_table")
    return fail_result("No Markdown table was found.", "rule_aided:markdown_table")


def check_no_table(response: str, constraint: Constraint) -> Result:
    if has_markdown_table(response):
        return fail_result("A Markdown table was found.", "rule_aided:no_table")
    return pass_result("No Markdown table was found.", "rule_aided:no_table")


def check_table_columns(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    columns = [str(column) for column in as_list(config.get("required_columns") or config.get("columns"))]
    if not columns:
        columns = quoted_terms(constraint.get("constraint", ""))
    if not columns:
        columns = infer_table_columns(constraint.get("constraint", ""))
    if not columns:
        return unresolved(response, constraint, "rule_aided:table_columns")
    lines = markdown_table_lines(response)
    if not has_markdown_table(response):
        return fail_result("No Markdown table was found.", "rule_aided:table_columns")
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    normalized_header = {normalize(strip_inline_markup(column).strip()) for column in header}
    missing = [column for column in columns if normalize(strip_inline_markup(column).strip()) not in normalized_header]
    if missing:
        return fail_result(f"Missing required table column(s): {', '.join(missing)}.", "rule_aided:table_columns")
    return pass_result("All required table column(s) were found.", "rule_aided:table_columns")


def check_table_row_count(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    exact = configured_int(constraint, "exact_rows")
    minimum = configured_int(constraint, "min_rows")
    maximum = configured_int(constraint, "max_rows")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:table_row_count")
    lines = markdown_table_lines(response)
    if not has_markdown_table(response):
        return fail_result("No Markdown table was found.", "rule_aided:table_row_count")
    data_rows = [
        line for line in lines[2:]
        if not re.match(r"^\|\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$", line)
    ]
    count = len(data_rows)
    if exact is not None and count != exact:
        return fail_result(f"Table has {count} data row(s); expected exactly {exact}.", "rule_aided:table_row_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Table has {count} data row(s); expected at least {minimum}.", "rule_aided:table_row_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Table has {count} data row(s); expected at most {maximum}.", "rule_aided:table_row_count")
    return pass_result(f"Table has {count} data row(s).", "rule_aided:table_row_count")


def check_checkbox(response: str, constraint: Constraint) -> Result:
    if re.search(r"(?m)^\s*(?:[-*]\s*)?\[(?: |x|X)?\]\s+\S+", response):
        return pass_result("A checkbox item was found.", "rule_aided:checkbox")
    return fail_result("No checkbox item was found.", "rule_aided:checkbox")


def check_code_block(response: str, constraint: Constraint) -> Result:
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min") or 1
    count = response.count("```") // 2
    if count < minimum:
        return fail_result(f"Response has {count} fenced code block(s); expected at least {minimum}.", "rule_aided:code_block")
    return pass_result(f"Response has {count} fenced code block(s).", "rule_aided:code_block")


def check_blockquote_count(response: str, constraint: Constraint) -> Result:
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:blockquote_count")
    count = blockquote_count(response)
    if exact is not None and count != exact:
        return fail_result(f"Response has {count} blockquote line(s); expected exactly {exact}.", "rule_aided:blockquote_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} blockquote line(s); expected at least {minimum}.", "rule_aided:blockquote_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} blockquote line(s); expected at most {maximum}.", "rule_aided:blockquote_count")
    return pass_result(f"Response has {count} blockquote line(s).", "rule_aided:blockquote_count")


def required_numbers(constraint: Constraint, field: str = "numbers") -> List[str]:
    config = checker_config(constraint)
    configured = as_list(config.get(field) or config.get("number"))
    values = configured or extract_numbers(constraint.get("constraint", ""))
    return [canonical_number(value) for value in values]


def configured_numbers(constraint: Constraint, field: str = "numbers") -> List[str]:
    """Numbers taken ONLY from explicit checker config, never scraped from the
    constraint text. A bare value-inclusion check is only reliable when the
    expected values are configured; otherwise the constraint usually requires a
    calculation, comparison, or polarity judgement that string presence cannot
    decide, so the caller should defer to the judge."""
    config = checker_config(constraint)
    configured = as_list(config.get(field) or config.get("number"))
    return [canonical_number(value) for value in configured]


def check_contains_number(response: str, constraint: Constraint) -> Result:
    numbers = configured_numbers(constraint, "numbers")
    if not numbers:
        return unresolved(response, constraint, "rule_aided:contains_number")
    found_numbers = set(extract_numbers(response))
    response_flat = canonical_number(response)
    missing = [number for number in numbers if number not in found_numbers and number not in response_flat]
    if missing:
        return fail_result(f"Missing required number(s): {', '.join(missing)}.", "rule_aided:contains_number")
    return pass_result("All required number(s) were found.", "rule_aided:contains_number")


def check_threshold(response: str, constraint: Constraint) -> Result:
    thresholds = configured_numbers(constraint, "thresholds")
    if not thresholds:
        return unresolved(response, constraint, "rule_aided:threshold")
    result = check_contains_number(response, {**constraint, "evaluator": {"numbers": thresholds}})
    result["method"] = "rule_aided:threshold"
    if result["score"] == 1:
        result["reason"] = "All required threshold value(s) were found."
    return result


def check_deadline(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    deadlines = [canonical_number(value) for value in as_list(config.get("deadlines") or config.get("deadline"))]
    if not deadlines:
        return unresolved(response, constraint, "rule_aided:deadline")
    response_flat = canonical_number(response)
    missing = [deadline for deadline in deadlines if deadline not in response_flat]
    if missing:
        return fail_result(f"Missing required deadline/timing value(s): {', '.join(missing)}.", "rule_aided:deadline")
    return pass_result("All required deadline/timing value(s) were found.", "rule_aided:deadline")


def check_exact_value(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    expected = config.get("expected_values")
    if not isinstance(expected, dict) or not expected:
        return unresolved(response, constraint, "rule_aided:exact_value")
    flat = canonical_number(response)
    missing = []
    for label, value in expected.items():
        label_text = str(label)
        value_text = canonical_number(value)
        if label_text.casefold() not in flat or value_text not in flat:
            missing.append(f"{label_text}={value}")
    if missing:
        return fail_result(f"Missing expected label/value pair(s): {', '.join(missing)}.", "rule_aided:exact_value")
    return pass_result("All expected label/value pair(s) were found.", "rule_aided:exact_value")


def decimal_places(value: str) -> Optional[int]:
    try:
        cleaned = value.replace(",", "").replace("%", "")
        cleaned = re.sub(r"\bpercent(?:age)?(?:\s+points?)?\b", "", cleaned, flags=re.I).strip()
        decimal = Decimal(cleaned)
    except InvalidOperation:
        return None
    exponent = decimal.as_tuple().exponent
    return abs(exponent) if exponent < 0 else 0


def check_decimal_places(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    places = configured_int(constraint, "places") or configured_int(constraint, "count")
    if places is None:
        places = configured_int(constraint, "exact")
    if places is None:
        match = re.search(r"(\d+)\s+decimal places?", constraint.get("constraint", ""), flags=re.I)
        if match:
            places = int(match.group(1))
    if places is None:
        return unresolved(response, constraint, "rule_aided:decimal_places")
    target = str(config.get("target") or config.get("mode") or "all").casefold()
    if target in {"percent", "percentage", "percentages", "percent_only"}:
        numbers = re.findall(
            r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?(?:%|\s+percent(?:age)?(?:\s+points?)?\b)",
            response,
            flags=re.I,
        )
    else:
        numbers = re.findall(r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?%?", response)
    if not numbers:
        if target in {"percent", "percentage", "percentages", "percent_only"}:
            return pass_result("No percentage values were found, so the percentage decimal-place constraint is vacuously satisfied.", "rule_aided:decimal_places")
        return fail_result("No numeric values were found.", "rule_aided:decimal_places")
    bad = [number for number in numbers if decimal_places(number) != places]
    if bad:
        return fail_result(f"Number(s) do not use exactly {places} decimal place(s): {', '.join(bad[:5])}.", "rule_aided:decimal_places")
    return pass_result(f"All decimal numeric values use {places} decimal place(s).", "rule_aided:decimal_places")


def check_first_line(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    required = str(config.get("line") or config.get("word") or "").strip()
    if not required:
        terms = quoted_terms(constraint.get("constraint", ""))
        required = terms[0] if terms else ""
    if not required:
        return unresolved(response, constraint, "rule_aided:first_line")
    first = next((line.strip() for line in response.splitlines() if line.strip()), "")
    if first.startswith(required):
        return pass_result(f"First non-empty line starts with {required!r}.", "rule_aided:first_line")
    return fail_result(f"First non-empty line does not start with {required!r}.", "rule_aided:first_line")


def check_first_line_format(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    fmt = str(config.get("format") or "").strip().lower()
    if not fmt:
        return unresolved(response, constraint, "rule_aided:first_line_format")
    first = next((line.strip() for line in response.splitlines() if line.strip()), "")
    if not first:
        return fail_result("Response has no non-empty first line.", "rule_aided:first_line_format")
    if fmt == "bold":
        passed = re.match(r"^\*\*.+\*\*", first) is not None
        detail = "Markdown bold"
    elif fmt == "heading":
        passed = re.match(r"^#{1,6}\s+\S+", first) is not None
        detail = "Markdown heading"
    elif fmt == "numbered":
        passed = re.match(r"^1[.)]\s+\S+", first) is not None
        detail = "numbered item"
    else:
        return unresolved(response, constraint, "rule_aided:first_line_format")
    if passed:
        return pass_result(f"First non-empty line uses {detail} format.", "rule_aided:first_line_format")
    return fail_result(f"First non-empty line does not use {detail} format.", "rule_aided:first_line_format")


def check_last_line(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    required = str(config.get("line") or config.get("word") or "").strip()
    if not required:
        terms = quoted_terms(constraint.get("constraint", ""))
        required = terms[0] if terms else ""
    if not required:
        return unresolved(response, constraint, "rule_aided:last_line")
    last = next((line.strip() for line in reversed(response.splitlines()) if line.strip()), "")
    if required in last:
        return pass_result(f"Last non-empty line contains {required!r}.", "rule_aided:last_line")
    return fail_result(f"Last non-empty line does not contain {required!r}.", "rule_aided:last_line")


def check_conditional_trigger(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    trigger = str(config.get("trigger") or "").strip()
    followup = str(config.get("followup") or config.get("required_if_present") or "").strip()
    if not trigger or not followup:
        return unresolved(response, constraint, "rule_aided:conditional_trigger")
    case_sensitive = bool(config.get("case_sensitive", False))
    haystack = normalize(response, case_sensitive)
    if normalize(trigger, case_sensitive) not in haystack:
        return pass_result(f"Trigger {trigger!r} is absent, so the conditional requirement is not activated.", "rule_aided:conditional_trigger")
    if normalize(followup, case_sensitive) in haystack:
        return pass_result(f"Trigger {trigger!r} and required follow-up {followup!r} were found.", "rule_aided:conditional_trigger")
    return fail_result(f"Trigger {trigger!r} was found without required follow-up {followup!r}.", "rule_aided:conditional_trigger")


def check_simple_regex(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    pattern = config.get("pattern") or config.get("regex")
    if not pattern:
        return unresolved(response, constraint, "rule_aided:simple_regex")
    flags = 0 if config.get("case_sensitive") else re.I
    try:
        matched = re.search(str(pattern), response, flags=flags) is not None
    except re.error as exc:
        return fail_result(f"Invalid regex pattern: {exc}.", "rule_aided:simple_regex")
    if not matched:
        return fail_result("Regex pattern was not found in the response.", "rule_aided:simple_regex")
    return pass_result("Regex pattern was found in the response.", "rule_aided:simple_regex")


def check_forbidden_regex(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    pattern = config.get("forbidden_regex") or config.get("pattern") or config.get("regex")
    if not pattern:
        return unresolved(response, constraint, "rule_aided:forbidden_regex")
    flags = 0 if config.get("case_sensitive") else re.I
    try:
        match = re.search(str(pattern), response, flags=flags)
    except re.error as exc:
        return fail_result(f"Invalid regex pattern: {exc}.", "rule_aided:forbidden_regex")
    if match:
        return fail_result(f"Forbidden regex matched: {match.group(0)!r}.", "rule_aided:forbidden_regex")
    return pass_result("Forbidden regex was not found.", "rule_aided:forbidden_regex")


def check_regex_count(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    pattern = config.get("pattern") or config.get("regex")
    if not pattern:
        return unresolved(response, constraint, "rule_aided:regex_count")
    flags = 0 if config.get("case_sensitive") else re.I
    try:
        count = len(re.findall(str(pattern), response, flags=flags))
    except re.error as exc:
        return fail_result(f"Invalid regex pattern: {exc}.", "rule_aided:regex_count")

    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if exact is None and minimum is None and maximum is None:
        return unresolved(response, constraint, "rule_aided:regex_count")
    if exact is not None and count != exact:
        return fail_result(f"Regex matched {count} time(s); expected exactly {exact}.", "rule_aided:regex_count")
    if minimum is not None and count < minimum:
        return fail_result(f"Regex matched {count} time(s); expected at least {minimum}.", "rule_aided:regex_count")
    if maximum is not None and count > maximum:
        return fail_result(f"Regex matched {count} time(s); expected at most {maximum}.", "rule_aided:regex_count")
    return pass_result(f"Regex matched {count} time(s).", "rule_aided:regex_count")


def heading_start_index(response: str, heading: str, *, case_sensitive: bool = False) -> Optional[int]:
    escaped = re.escape(heading.strip())
    if not escaped:
        return None
    flags = re.M if case_sensitive else re.M | re.I
    patterns = [
        rf"^\s*#{{1,6}}\s+{escaped}\s*$",
        rf"^\s*(?:\d+[.)]\s*)?{escaped}\s*:?\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, response, flags=flags)
        if match:
            return match.start()
    return None


def check_forbidden_regex_before_heading(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    pattern = config.get("forbidden_regex") or config.get("pattern") or config.get("regex")
    heading = str(config.get("heading") or "").strip()
    if not pattern or not heading:
        return unresolved(response, constraint, "rule_aided:forbidden_regex_before_heading")
    case_sensitive = bool(config.get("case_sensitive", False))
    split_at = heading_start_index(response, heading, case_sensitive=case_sensitive)
    haystack = response if split_at is None else response[:split_at]
    flags = 0 if case_sensitive else re.I
    try:
        match = re.search(str(pattern), haystack, flags=flags)
    except re.error as exc:
        return fail_result(f"Invalid regex pattern: {exc}.", "rule_aided:forbidden_regex_before_heading")
    if match:
        return fail_result(
            f"Forbidden regex matched before heading {heading!r}: {match.group(0)!r}.",
            "rule_aided:forbidden_regex_before_heading",
        )
    return pass_result(f"Forbidden regex was not found before heading {heading!r}.", "rule_aided:forbidden_regex_before_heading")


def check_first_word(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    word = str(config.get("word") or "").strip()
    if not word:
        terms = quoted_terms(constraint.get("constraint", ""))
        word = terms[0] if terms else ""
    if not word:
        return unresolved(response, constraint, "rule_aided:first_word")
    text = re.sub(r"^(?:\*{1,2}|#{1,6}\s*)", "", response.strip())
    if text.startswith(word):
        return pass_result(f"Response starts with {word!r}.", "rule_aided:first_word")
    return fail_result(f"Response does not start with {word!r}.", "rule_aided:first_word")


def check_first_last_line(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    first_required = str(config.get("first_line") or "").strip()
    last_required = str(config.get("last_line") or "").strip()
    if not first_required and not last_required:
        return unresolved(response, constraint, "rule_aided:first_last_line")
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not lines:
        return fail_result("Response has no non-empty lines.", "rule_aided:first_last_line")
    if first_required and first_required not in lines[0]:
        return fail_result(f"First non-empty line does not contain {first_required!r}.", "rule_aided:first_last_line")
    if last_required and last_required not in lines[-1]:
        return fail_result(f"Last non-empty line does not contain {last_required!r}.", "rule_aided:first_last_line")
    return pass_result("First/last line requirement is satisfied.", "rule_aided:first_last_line")


def check_heading_order(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    headings = [str(heading).strip() for heading in as_list(config.get("headings") or config.get("fields")) if str(heading).strip()]
    if not headings:
        headings = quoted_terms(constraint.get("constraint", ""))
    if not headings:
        return unresolved(response, constraint, "rule_aided:heading_order")

    case_sensitive = bool(config.get("case_sensitive", False))
    positions = []
    missing = []
    for heading in headings:
        position = heading_start_index(response, heading, case_sensitive=case_sensitive)
        if position is None:
            missing.append(heading)
        else:
            positions.append((heading, position))
    if missing:
        return fail_result(f"Missing required heading(s): {', '.join(missing)}.", "rule_aided:heading_order")
    if any(curr[1] <= prev[1] for prev, curr in zip(positions, positions[1:])):
        order = ", ".join(f"{heading}@{position}" for heading, position in positions)
        return fail_result(f"Headings are not in the required order: {order}.", "rule_aided:heading_order")
    return pass_result("Required headings were found in order.", "rule_aided:heading_order")


def check_heading_level(response: str, constraint: Constraint) -> Result:
    level = configured_int(constraint, "level")
    exact = configured_int(constraint, "exact_count") or configured_int(constraint, "exact")
    minimum = configured_int(constraint, "min_count") or configured_int(constraint, "min")
    maximum = configured_int(constraint, "max_count") or configured_int(constraint, "max")
    if level is None or (exact is None and minimum is None and maximum is None):
        return unresolved(response, constraint, "rule_aided:heading_level")
    count = heading_level_count(response, level)
    if exact is not None and count != exact:
        return fail_result(f"Response has {count} level-{level} heading(s); expected exactly {exact}.", "rule_aided:heading_level")
    if minimum is not None and count < minimum:
        return fail_result(f"Response has {count} level-{level} heading(s); expected at least {minimum}.", "rule_aided:heading_level")
    if maximum is not None and count > maximum:
        return fail_result(f"Response has {count} level-{level} heading(s); expected at most {maximum}.", "rule_aided:heading_level")
    return pass_result(f"Response has {count} level-{level} heading(s).", "rule_aided:heading_level")


def check_heading_depth(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    minimum = configured_int(constraint, "min_depth") or configured_int(constraint, "min")
    if minimum is None:
        return unresolved(response, constraint, "rule_aided:heading_depth")
    levels = set()
    for line in response.splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+\S+", line)
        if match:
            levels.add(len(match.group(1)))
    count = len(levels)
    if count < minimum:
        return fail_result(f"Response uses {count} heading level(s); expected at least {minimum}.", "rule_aided:heading_depth")
    return pass_result(f"Response uses {count} heading level(s); expected at least {minimum}.", "rule_aided:heading_depth")


def check_section_titles(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    titles = [str(title).strip() for title in as_list(config.get("required_titles") or config.get("headings") or config.get("fields")) if str(title).strip()]
    if not titles:
        titles = quoted_terms(constraint.get("constraint", ""))
    if not titles:
        return unresolved(response, constraint, "rule_aided:section_titles")
    missing = [title for title in titles if title not in response]
    if missing:
        return fail_result(f"Missing required section title(s): {', '.join(missing)}.", "rule_aided:section_titles")
    return pass_result("All required section title(s) were found.", "rule_aided:section_titles")


def check_keyword_presence(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    keywords = [str(k) for k in as_list(config.get("required_keywords") or config.get("keywords"))]
    if not keywords:
        return unresolved(response, constraint, "rule_aided:keyword_presence")
    match_all = bool(config.get("match_all", True))
    found = [keyword for keyword in keywords if keyword in response]
    if match_all and len(found) != len(keywords):
        missing = [keyword for keyword in keywords if keyword not in found]
        return fail_result(f"Missing required keyword(s): {', '.join(missing)}.", "rule_aided:keyword_presence")
    if not match_all and not found:
        return fail_result("None of the required alternative keyword(s) were found.", "rule_aided:keyword_presence")
    return pass_result("Keyword presence requirement is satisfied.", "rule_aided:keyword_presence")


def check_keyword_absence(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    forbidden = [str(k) for k in as_list(config.get("forbidden_keywords") or config.get("forbidden") or config.get("phrases"))]
    if not forbidden:
        return unresolved(response, constraint, "rule_aided:keyword_absence")
    found = [keyword for keyword in forbidden if keyword in response]
    if found:
        return fail_result(f"Found forbidden keyword(s): {', '.join(found)}.", "rule_aided:keyword_absence")
    return pass_result("No forbidden keyword(s) were found.", "rule_aided:keyword_absence")


def check_first_person(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    forbidden = [
        str(phrase)
        for phrase in as_list(
            config.get("forbidden_phrases")
            or config.get("forbidden_keywords")
            or ["本报告", "本文", "本分析", "本研究", "报告认为", "分析认为"]
        )
    ]
    found = [phrase for phrase in forbidden if phrase in response]
    if found:
        return fail_result(f"Found forbidden report-language phrase(s): {', '.join(found)}.", "rule_aided:first_person")
    return pass_result("No forbidden report-language phrase(s) were found.", "rule_aided:first_person")


def check_risk_disclaimer(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    risk_line = str(config.get("risk_line") or "以上内容仅供参考，不构成投资建议")
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not lines:
        return fail_result("Response has no non-empty lines.", "rule_aided:risk_disclaimer")
    tail = "\n".join(lines[-5:])
    if risk_line in tail or any(term in tail for term in ("风险提示", "免责声明", "仅供参考", "不构成投资建议")):
        return pass_result("Risk disclaimer appears near the end.", "rule_aided:risk_disclaimer")
    return fail_result("Risk disclaimer was not found near the end.", "rule_aided:risk_disclaimer")


def check_currency_format(response: str, constraint: Constraint) -> Result:
    config = checker_config(constraint)
    required_unit = str(config.get("unit") or "").strip()
    forbidden_units = [str(unit) for unit in as_list(config.get("forbidden_units"))]
    if not required_unit and not forbidden_units:
        return unresolved(response, constraint, "rule_aided:currency_format")
    currency_units = ["万元", "亿元", "百万元", "千万元", "元", "万亿元", "万亿", "百万", "千万"]
    has_any_currency = any(unit in response for unit in currency_units)
    if has_any_currency and required_unit and required_unit not in response:
        return fail_result(f"Currency values were found but required unit {required_unit!r} was not used.", "rule_aided:currency_format")
    found_forbidden = [unit for unit in forbidden_units if unit in response]
    if found_forbidden:
        return fail_result(f"Forbidden currency unit(s) found: {', '.join(found_forbidden)}.", "rule_aided:currency_format")
    return pass_result("Currency format requirement is satisfied.", "rule_aided:currency_format")


def check_no_percent(response: str, constraint: Constraint) -> Result:
    if "%" in response or "％" in response:
        return fail_result("A percent symbol was found.", "rule_aided:no_percent")
    return pass_result("No percent symbol was found.", "rule_aided:no_percent")


def check_no_arabic_numerals(response: str, constraint: Constraint) -> Result:
    text = re.sub(r"^#{1,6}\s.*$", "", response, flags=re.M)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.M)
    if re.search(r"[0-9]", text):
        return fail_result("Arabic numeral(s) were found.", "rule_aided:no_arabic_numerals")
    return pass_result("No Arabic numeral(s) were found outside headings/tables.", "rule_aided:no_arabic_numerals")


CHECKERS: Dict[str, Callable[[str, Constraint], Result]] = {
    "required_keyword": check_required_keyword,
    "forbidden_phrase": check_forbidden_phrase,
    "min_words": check_min_words,
    "max_words": check_max_words,
    "word_range": check_word_range,
    "min_sections": check_min_sections,
    "max_sections": check_max_sections,
    "section_titles": check_section_titles,
    "item_count": check_item_count,
    "ordered_list_count": check_ordered_list_count,
    "no_list": check_no_list,
    "paragraph_count": check_paragraph_count,
    "sentence_count": check_sentence_count,
    "valid_json": check_valid_json,
    "required_fields": check_required_fields,
    "json_field_count": check_json_field_count,
    "json_field_item_limit": check_json_field_item_limit,
    "json_field_word_limit": check_json_field_word_limit,
    "markdown_table": check_markdown_table,
    "no_table": check_no_table,
    "table_columns": check_table_columns,
    "table_row_count": check_table_row_count,
    "checkbox": check_checkbox,
    "code_block": check_code_block,
    "blockquote_count": check_blockquote_count,
    "contains_number": check_contains_number,
    "threshold": check_threshold,
    "deadline": check_deadline,
    "exact_value": check_exact_value,
    "decimal_places": check_decimal_places,
    "first_line": check_first_line,
    "first_line_format": check_first_line_format,
    "last_line": check_last_line,
    "conditional_trigger": check_conditional_trigger,
    "simple_regex": check_simple_regex,
    "forbidden_regex": check_forbidden_regex,
    "regex_count": check_regex_count,
    "forbidden_regex_before_heading": check_forbidden_regex_before_heading,
    "heading_order": check_heading_order,
    "heading_level": check_heading_level,
    "heading_depth": check_heading_depth,
    "first_word": check_first_word,
    "first_last_line": check_first_last_line,
    "keyword_presence": check_keyword_presence,
    "keyword_absence": check_keyword_absence,
    "first_person": check_first_person,
    "risk_disclaimer": check_risk_disclaimer,
    "currency_format": check_currency_format,
    "no_percent": check_no_percent,
    "no_arabic_numerals": check_no_arabic_numerals,
}


ALIASES = {
    "check_required_keyword": "required_keyword",
    "required_keywords": "required_keyword",
    "keyword": "required_keyword",
    "keywords": "required_keyword",
    "check_keyword_presence": "keyword_presence",
    "check_keyword_absence": "keyword_absence",
    "check_forbidden_pattern": "keyword_absence",
    "forbidden_pattern": "keyword_absence",
    "check_forbidden_phrase": "forbidden_phrase",
    "forbidden": "forbidden_phrase",
    "forbidden_phrases": "forbidden_phrase",
    "check_word_limit": "max_words",
    "check_word_range": "word_range",
    "min_word_count": "min_words",
    "max_word_count": "max_words",
    "minimum_words": "min_words",
    "maximum_words": "max_words",
    "word_limit": "max_words",
    "word_range": "word_range",
    "check_section_count": "min_sections",
    "check_section_titles": "section_titles",
    "section_count_min": "min_sections",
    "section_count_max": "max_sections",
    "section_count": "min_sections",
    "section_titles": "section_titles",
    "check_item_count": "item_count",
    "items": "item_count",
    "exact_item_count": "item_count",
    "at_least_item_count": "item_count",
    "check_ordered_list_count": "ordered_list_count",
    "ordered_list": "ordered_list_count",
    "ordered_list_count": "ordered_list_count",
    "numbered_list": "ordered_list_count",
    "check_no_list": "no_list",
    "no_list": "no_list",
    "check_paragraph_count": "paragraph_count",
    "paragraphs": "paragraph_count",
    "paragraph_count": "paragraph_count",
    "check_sentence_count": "sentence_count",
    "sentence_count": "sentence_count",
    "check_blockquote_count": "blockquote_count",
    "blockquote": "blockquote_count",
    "blockquote_count": "blockquote_count",
    "check_json_format": "valid_json",
    "json": "valid_json",
    "json_format": "valid_json",
    "check_json_structure": "valid_json",
    "check_required_fields": "required_fields",
    "required_field": "required_fields",
    "fields": "required_fields",
    "field_coverage": "required_fields",
    "check_json_field_count": "json_field_count",
    "check_json_field_item_limit": "json_field_item_limit",
    "check_json_field_word_limit": "json_field_word_limit",
    "json_field_count": "json_field_count",
    "json_field_item_limit": "json_field_item_limit",
    "json_field_word_limit": "json_field_word_limit",
    "check_markdown_table": "markdown_table",
    "table": "markdown_table",
    "markdown_table_format": "markdown_table",
    "check_no_table": "no_table",
    "no_markdown_table": "no_table",
    "check_table_column_names": "table_columns",
    "check_header_row": "table_columns",
    "table_columns": "table_columns",
    "required_columns": "table_columns",
    "check_table_row_count": "table_row_count",
    "table_rows": "table_row_count",
    "check_checkbox_format": "checkbox",
    "checkbox_format": "checkbox",
    "check_code_block": "code_block",
    "code_block": "code_block",
    "number": "contains_number",
    "numbers": "contains_number",
    "check_value_exact": "exact_value",
    "value_exact": "exact_value",
    "check_first_word": "first_word",
    "first_word": "first_word",
    "opening": "first_line",
    "check_first_line_format": "first_line_format",
    "first_line_format": "first_line_format",
    "check_first_last_line": "first_last_line",
    "first_last_line": "first_last_line",
    "closing": "last_line",
    "check_conditional_trigger": "conditional_trigger",
    "conditional": "conditional_trigger",
    "check_risk_disclaimer": "risk_disclaimer",
    "keyword_presence": "keyword_presence",
    "keyword_absence": "keyword_absence",
    "check_first_person": "first_person",
    "first_person": "first_person",
    "risk_disclaimer": "risk_disclaimer",
    "check_currency_format": "currency_format",
    "currency_format": "currency_format",
    "check_no_percent": "no_percent",
    "no_percent": "no_percent",
    "check_no_arabic_numerals": "no_arabic_numerals",
    "no_arabic_numerals": "no_arabic_numerals",
    "check_decimal_places": "decimal_places",
    "check_first_line": "first_line",
    "check_last_line": "last_line",
    "check_heading_order": "heading_order",
    "check_heading_level": "heading_level",
    "check_heading_depth": "heading_depth",
    "regex": "simple_regex",
    "required_regex": "simple_regex",
    "check_forbidden_regex": "forbidden_regex",
    "forbidden_regex": "forbidden_regex",
    "check_regex_count": "regex_count",
    "regex_count": "regex_count",
    "heading_order": "heading_order",
    "heading_level": "heading_level",
    "heading_depth": "heading_depth",
}


def evaluate_constraint(response: str, constraint: Constraint) -> Result:
    """Evaluate one response against one FinIF v2 constraint."""
    check_type = str(constraint.get("check_type", "judge")).strip().lower()
    if check_type in {"judge", "llm"}:
        return unresolved(response, constraint, "judge")
    if check_type not in {"rule", "rule_aided"}:
        return fail_result(f"Unsupported check_type: {constraint.get('check_type')!r}.", "schema")

    checker_type = get_checker_type(constraint)
    checker_type = ALIASES.get(checker_type or "", checker_type)
    if checker_type not in CHECKERS:
        return unresolved(response, constraint, "rule_aided:unresolved")
    return CHECKERS[checker_type](response, constraint)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one FinIF v2 constraint checker.")
    parser.add_argument("--response", help="Response text. Use --response-file for longer responses.")
    parser.add_argument("--response-file", help="Path to a file containing the response text.")
    parser.add_argument("--constraint-json", required=True, help="Constraint object as JSON.")
    args = parser.parse_args()

    if args.response_file:
        with open(args.response_file, "r", encoding="utf-8") as handle:
            response = handle.read()
    else:
        response = args.response or ""

    constraint = json.loads(args.constraint_json)
    print(json.dumps(evaluate_constraint(response, constraint), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
