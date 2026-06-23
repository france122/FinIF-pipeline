#!/usr/bin/env python3
"""Align the repaired v3 full dataset to the current hard300 IF-clean schema.

This script keeps the original 1,064-row source file untouched and writes a
new hard300-aligned training pool with:

- prompt-visible material labels in `source_registry`
- rewritten prompt/query/constraint references away from hidden DOC IDs
- current hard300-style hardening and format constraints
- IF-clean routing fields (`score_axis`, `include_in_isr`, `if_subtype`, ...)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl")
DEFAULT_OUTPUT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_hard300_aligned_ifclean.jsonl")
DEFAULT_SUMMARY = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_hard300_aligned_ifclean_summary.json")
DEFAULT_AUDIT = Path("outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_hard300_aligned_ifclean_audit.json")

TONIGHT_BUILDER = REPO_ROOT / "outputs/benchmark/build_tonight_hard_benchmark.py"
IFCLEAN_BUILDER = REPO_ROOT / "outputs/benchmark/build_ifclean_benchmark.py"

ALIGNMENT_VERSION = "hard300-train-align-v1"

LEAD_VARIANTS = [
    "Review file {line}: {product}",
    "Case file {line}: {product}",
    "Assignment {line}: {product}",
    "Analyst packet {line} for {product}",
]

INSTRUCTION_HEADINGS = [
    "Analyst instructions",
    "Reviewer request",
    "Completion instructions",
    "Output rules",
]

INSTRUCTION_PATTERNS = [
    "The answer needs to cover this request: {query}",
    "Please complete this request: {query}",
    "For the final response, handle this assignment: {query}",
    "The analyst should return this output: {query}",
]

MATERIALS_HEADINGS = [
    "Materials supplied",
    "Source materials",
    "Review packet contents",
    "Evidence in the file",
    "Reference materials",
]

TITLE_LABEL_KEYWORDS = {
    "questionnaire",
    "worksheet",
    "matrix",
    "checklist",
    "procedure",
    "policy",
    "standard",
    "guide",
    "rule",
    "memo",
    "note",
    "file",
    "packet",
    "profile",
    "history",
    "snapshot",
    "statement",
    "schedule",
    "request",
    "proposal",
    "extract",
    "excerpt",
    "dashboard",
    "review",
    "ticket",
    "sheet",
    "facts",
    "factor",
    "screen",
    "scoring",
    "bands",
    "pricing",
    "tear",
    "bridge",
    "screening",
    "guidance",
}

TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "by",
    "corp",
    "corporation",
    "draft",
    "excerpt",
    "for",
    "from",
    "funds",
    "guide",
    "holding",
    "holdings",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "mei",
    "lin",
    "northstar",
    "original",
    "overview",
    "plc",
    "public",
    "repaired",
    "services",
    "source",
    "summary",
    "synthetic",
    "the",
    "updated",
}


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
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


def normalize_spaces(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def display_product(text: str) -> str:
    text = normalize_spaces(text)
    if not text:
        return "Work product"
    return text[0].upper() + text[1:]


def label_from_title(title: str) -> str:
    raw = normalize_spaces(title.split(" - ", 1)[0])
    raw = re.sub(r"\([^)]*\)", " ", raw)
    raw = raw.replace("&", " and ")
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", raw)
    lowered = [token.lower() for token in tokens if token.strip()]
    if not lowered:
        return "source material"

    best_idx = None
    for idx in range(len(lowered) - 1, -1, -1):
        token = lowered[idx]
        if token in TITLE_LABEL_KEYWORDS:
            best_idx = idx
            break

    if best_idx is None:
        phrase_tokens = [token for token in lowered if token not in TITLE_STOPWORDS][-3:]
    else:
        start = max(0, best_idx - 2)
        phrase_tokens = lowered[start : best_idx + 1]
        if all(token in TITLE_STOPWORDS for token in phrase_tokens):
            phrase_tokens = lowered[max(0, best_idx - 1) : best_idx + 1]

    cleaned = [token for token in phrase_tokens if token not in TITLE_STOPWORDS]
    if not cleaned:
        cleaned = [token for token in lowered[-2:] if token not in TITLE_STOPWORDS] or lowered[-2:]

    label = " ".join(cleaned)
    label = re.sub(r"\bsummary\b", "", label).strip()
    label = re.sub(r"\s+", " ", label)
    return label or "source material"


def build_source_registry(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    context = row.get("context")
    if not isinstance(context, dict):
        raise ValueError(f"{row.get('id')}: missing context object")
    documents = context.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError(f"{row.get('id')}: missing context.documents")

    registry: List[Dict[str, Any]] = []
    seen_labels: set[str] = set()
    for position, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"{row.get('id')}: non-object document at position {position}")
        source_id = str(document.get("id") or f"DOC{position}").strip() or f"DOC{position}"
        title = normalize_spaces(str(document.get("title") or source_id))
        content = normalize_spaces(str(document.get("content") or ""))
        base_label = label_from_title(title)
        label = base_label
        suffix = 2
        while label in seen_labels:
            label = f"{base_label} {suffix}"
            suffix += 1
        seen_labels.add(label)
        registry.append(
            {
                "source_id": source_id,
                "prompt_label": label,
                "title": title,
                "content": content,
            }
        )
    return registry


def label_map(registry: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in registry:
        source_id = str(entry.get("source_id") or "").strip()
        prompt_label = str(entry.get("prompt_label") or "").strip()
        if source_id and prompt_label:
            mapping[source_id] = prompt_label
    return mapping


def rewrite_doc_refs(text: str, labels: Dict[str, str]) -> str:
    if not text:
        return text

    text = normalize_spaces(text)
    text = re.sub(r"\buse only the context\b", "use only the provided materials", text, flags=re.I)
    text = re.sub(r"\buse only the supplied context\b", "use only the provided materials", text, flags=re.I)
    text = re.sub(r"\bcite document ids?\b", "cite visible material labels", text, flags=re.I)
    text = re.sub(r"\bcite doc ids?\b", "cite visible material labels", text, flags=re.I)
    text = re.sub(r"\bdocument ids?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bdoc ids?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bdoc numbers?\b", "visible material labels", text, flags=re.I)
    text = re.sub(r"\bdoc citations?\b", "visible material label citations", text, flags=re.I)
    text = re.sub(r"\bdoc citation\b", "visible material label citation", text, flags=re.I)
    text = re.sub(r"\bcite each statement to the documents\b", "cite each statement to the visible material labels", text, flags=re.I)

    for source_id, label in sorted(labels.items(), key=lambda pair: pair[0], reverse=True):
        safe_id = re.escape(source_id)
        text = re.sub(
            rf"\bunder {safe_id}\b",
            f"under the material labeled {label}",
            text,
            flags=re.I,
        )
        text = re.sub(
            rf"\busing {safe_id}\b",
            f"using the material labeled {label}",
            text,
            flags=re.I,
        )
        text = re.sub(
            rf"\bfrom {safe_id}\b",
            f"from the material labeled {label}",
            text,
            flags=re.I,
        )
        text = re.sub(
            rf"\bin {safe_id}\b",
            f"in the material labeled {label}",
            text,
            flags=re.I,
        )
        text = re.sub(
            rf"\b{safe_id}\b",
            f"the material labeled {label}",
            text,
        )

    text = re.sub(r"\bthe material labeled ([^ ]+) and the material labeled ([^ ]+)\b", r"the materials labeled \1 and \2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def rewrite_constraint(constraint: Dict[str, Any], labels: Dict[str, str]) -> Dict[str, Any]:
    rewritten = dict(constraint)
    for key in ("constraint", "rationale", "judge_method", "routing_note"):
        if isinstance(rewritten.get(key), str):
            rewritten[key] = rewrite_doc_refs(rewritten[key], labels)
    return rewritten


def render_source_block(entry: Dict[str, Any], variant: int) -> str:
    label = entry["prompt_label"]
    title = entry["title"]
    content = entry["content"]
    style = variant % 3
    if style == 0:
        return f"{label} ({title})\n{content}"
    if style == 1:
        return f"{label} -- {content}"
    return f"Name for this material: {label}. Content: {content}"


def render_base_prompt(
    row: Dict[str, Any],
    *,
    line_number: int,
    registry: Sequence[Dict[str, Any]],
    rewritten_query: str,
) -> str:
    product = display_product(str(row.get("work_product") or row.get("task") or "work product"))
    lead = LEAD_VARIANTS[(line_number - 1) % len(LEAD_VARIANTS)].format(line=line_number, product=product)
    instruction_heading = INSTRUCTION_HEADINGS[(line_number - 1) % len(INSTRUCTION_HEADINGS)]
    instruction_line = INSTRUCTION_PATTERNS[(line_number - 1) % len(INSTRUCTION_PATTERNS)].format(query=rewritten_query)
    materials_heading = MATERIALS_HEADINGS[(line_number - 1) % len(MATERIALS_HEADINGS)]
    material_blocks = [
        render_source_block(entry, line_number + offset)
        for offset, entry in enumerate(registry)
    ]
    prompt = "\n\n".join(
        [
            lead,
            instruction_heading + "\n" + instruction_line,
            materials_heading + "\n" + "\n\n".join(material_blocks),
            "When the answer uses evidence, cite the material labels shown above.",
        ]
    )
    return normalize_spaces(prompt)


def count_doc_refs(text: str) -> int:
    return len(re.findall(r"\bDOC(?:\d+)?\b", text or ""))


def enrich_row(
    row: Dict[str, Any],
    *,
    hard_mod: Any,
    ifclean_mod: Any,
) -> Dict[str, Any]:
    line_number = int(row["_source_line"])
    registry = build_source_registry(row)
    labels = label_map(registry)

    base_query = rewrite_doc_refs(str(row.get("query") or ""), labels)
    prompt = render_base_prompt(row, line_number=line_number, registry=registry, rewritten_query=base_query)
    constraints = [
        rewrite_constraint(constraint, labels)
        for constraint in row.get("extracted_constraints") or []
        if isinstance(constraint, dict)
    ]

    tags = hard_mod.tags_of(constraints)
    work_product = str(row.get("work_product") or "")
    posture_name, _ = hard_mod.POSTURES[(line_number - 1) % len(hard_mod.POSTURES)]
    format_clauses, format_constraints = hard_mod.format_rule_pack(line_number - 1, work_product)
    semantic_constraints = hard_mod.added_constraints(tags, f"{prompt}\n{base_query}")
    enhanced_query = hard_mod.compose_enhanced_query(
        base_query,
        work_product=work_product,
        posture_name=posture_name,
        posture_text="",
        format_clauses=format_clauses,
        semantic_clauses=hard_mod.semantic_query_clauses(semantic_constraints),
    )
    full_prompt = hard_mod.append_final_request(prompt, enhanced_query)
    normalized_constraints = hard_mod.normalize_constraint_routes(
        hard_mod.dedupe_constraints(constraints + semantic_constraints + format_constraints)
    )

    aligned = {
        "id": row.get("id") or f"repaired_v3_line_{line_number:04d}",
        "workflow": row.get("workflow"),
        "task": row.get("task"),
        "work_product": row.get("work_product"),
        "query": enhanced_query,
        "full_prompt": full_prompt,
        "source_registry": registry,
        "extracted_constraints": normalized_constraints,
        "line_number": line_number,
        "alignment": {
            "version": ALIGNMENT_VERSION,
            "source_dataset": str(DEFAULT_INPUT),
            "source_line": line_number,
            "source_id": row.get("id"),
        },
        "tonight_hardening": {
            "version": "hard300-aligned-train-v1",
            "source_line": line_number,
            "posture": posture_name,
            "format_variant": (line_number - 1) % 5,
            "format_clauses": format_clauses,
            "added_constraints": len(normalized_constraints) - len(constraints),
        },
    }
    return ifclean_mod.clean_row(aligned)


def build_audit(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    items_with_query_doc_refs: List[str] = []
    items_with_prompt_doc_refs: List[str] = []
    items_with_constraint_doc_refs: List[str] = []
    items_with_duplicate_labels: List[str] = []
    source_count_distribution: Counter[int] = Counter()
    workflow_counts: Counter[str] = Counter()

    for row in rows:
        item_id = str(row.get("id") or "")
        workflow_counts[str(row.get("workflow") or "Unknown")] += 1
        registry = row.get("source_registry") or []
        source_count_distribution[len(registry)] += 1
        labels = [str(entry.get("prompt_label") or "") for entry in registry if isinstance(entry, dict)]
        if len(labels) != len(set(labels)):
            items_with_duplicate_labels.append(item_id)
        if count_doc_refs(str(row.get("query") or "")):
            items_with_query_doc_refs.append(item_id)
        if count_doc_refs(str(row.get("full_prompt") or "")):
            items_with_prompt_doc_refs.append(item_id)
        if any(count_doc_refs(str(c.get("constraint") or "")) for c in row.get("extracted_constraints") or []):
            items_with_constraint_doc_refs.append(item_id)
        if any(count_doc_refs(str(c.get("constraint") or "")) for c in row.get("diagnostic_constraints") or []):
            items_with_constraint_doc_refs.append(item_id)

    return {
        "version": ALIGNMENT_VERSION,
        "items": len(rows),
        "workflow_counts": dict(workflow_counts),
        "source_count_distribution": dict(sorted(source_count_distribution.items())),
        "items_with_query_doc_refs": items_with_query_doc_refs[:50],
        "items_with_query_doc_refs_count": len(items_with_query_doc_refs),
        "items_with_full_prompt_doc_refs": items_with_prompt_doc_refs[:50],
        "items_with_full_prompt_doc_refs_count": len(items_with_prompt_doc_refs),
        "items_with_constraint_doc_refs": items_with_constraint_doc_refs[:50],
        "items_with_constraint_doc_refs_count": len(items_with_constraint_doc_refs),
        "items_with_duplicate_labels": items_with_duplicate_labels[:50],
        "items_with_duplicate_labels_count": len(items_with_duplicate_labels),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    hard_mod = load_module(TONIGHT_BUILDER, "hard300_builder")
    ifclean_mod = load_module(IFCLEAN_BUILDER, "ifclean_builder")

    source_rows = load_jsonl(args.input)
    aligned_rows = [enrich_row(row, hard_mod=hard_mod, ifclean_mod=ifclean_mod) for row in source_rows]
    write_jsonl(args.output, aligned_rows)

    summary = ifclean_mod.summarize(aligned_rows)
    summary.update(
        {
            "version": ALIGNMENT_VERSION,
            "input": str(args.input),
            "output": str(args.output),
            "source_items": len(source_rows),
        }
    )
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    audit = build_audit(aligned_rows)
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
