#!/usr/bin/env python3
"""Run a 5-item GPT-5 response + batched-judge smoke test."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

try:
    from . import evaluate_responses as ev
except ImportError:  # pragma: no cover - direct script execution.
    import evaluate_responses as ev


DEFAULT_DATASET = Path("outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources.jsonl")
DEFAULT_SELECTED = Path("outputs/benchmark/smoke_gpt5_5_dataset.jsonl")
DEFAULT_RESPONSES = Path("outputs/benchmark/smoke_gpt5_5_responses.jsonl")
DEFAULT_SCORES = Path("outputs/benchmark/smoke_gpt5_5_scores.json")
DEFAULT_KEY = Path("key.md")


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if not match:
        raise ValueError(f"No OpenAI API key found in {path}")
    return match.group(0)


def output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    chunks: List[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if isinstance(value, str):
                chunks.append(value)
    if chunks:
        return "\n".join(chunks).strip()
    if hasattr(response, "model_dump"):
        data = response.model_dump()
        for item in data.get("output", []) or []:
            for content in item.get("content", []) or []:
                value = content.get("text")
                if isinstance(value, str):
                    chunks.append(value)
                elif isinstance(value, dict) and isinstance(value.get("value"), str):
                    chunks.append(value["value"])
    return "\n".join(chunks).strip()


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    return str(value)


def create_response(client: OpenAI, model: str, prompt: str, *, max_output_tokens: int) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": "low"},
    }
    try:
        return client.responses.create(**kwargs)
    except Exception:
        kwargs.pop("reasoning", None)
        return client.responses.create(**kwargs)


def create_json_response(client: OpenAI, model: str, instructions: str, prompt: str, *, max_output_tokens: int) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": 0,
        "text": {"format": {"type": "json_object"}},
    }
    try:
        return client.responses.create(**kwargs)
    except Exception:
        kwargs.pop("text", None)
        return client.responses.create(**kwargs)


class OpenAIJudgeProvider(ev.JudgeProvider):
    name = "openai"

    def __init__(self, client: OpenAI, model: str, max_output_tokens: int):
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.name = f"openai:{model}"

    def judge(self, request: ev.JudgeRequest, system_prompt: str) -> str:
        response = create_json_response(
            self.client,
            self.model,
            system_prompt,
            request.prompt,
            max_output_tokens=self.max_output_tokens,
        )
        return output_text(response)


def load_selected_rows(dataset_path: Path, line_numbers: List[int]) -> List[Dict[str, Any]]:
    selected = set(line_numbers)
    rows: List[Dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number not in selected:
                continue
            item = json.loads(line)
            item["id"] = f"v6_line_{line_number:03d}"
            item["line_number"] = line_number
            rows.append(item)
    missing = sorted(selected - {row["line_number"] for row in rows})
    if missing:
        raise ValueError(f"Requested line(s) not found: {missing}")
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 5 GPT-5 responses and evaluate them with item-batched judge scoring.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--selected-output", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--responses-output", type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument("--scores-output", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--lines", default="1,2,3,4,5")
    parser.add_argument("--response-model", default="gpt-5")
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--response-max-output-tokens", type=int, default=5000)
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--parse-retries", type=int, default=2)
    parser.add_argument("--workers", type=int, default=1, help="Parallel response generation workers.")
    parser.add_argument("--judge-workers", type=int, default=1, help="Parallel item judge workers.")
    parser.add_argument("--reuse-responses", action="store_true", help="Reuse an existing responses JSONL and only rerun judging.")
    parser.add_argument("--generate-only", action="store_true", help="Generate responses and selected dataset, then stop before judge scoring.")
    args = parser.parse_args()

    api_key = read_api_key(args.key_file)
    client = OpenAI(api_key=api_key)
    line_numbers = [int(part.strip()) for part in args.lines.split(",") if part.strip()]

    items = load_selected_rows(args.dataset, line_numbers)
    write_jsonl(args.selected_output, items)

    if args.reuse_responses:
        if not args.responses_output.exists():
            raise FileNotFoundError(f"--reuse-responses requested but {args.responses_output} does not exist")
        print(f"reusing {args.responses_output}", flush=True)
    else:
        response_rows: List[Dict[str, Any]] = []

        def generate_one(item: Dict[str, Any]) -> Dict[str, Any]:
            response = create_response(
                client,
                args.response_model,
                item["full_prompt"],
                max_output_tokens=args.response_max_output_tokens,
            )
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": args.response_model,
                "response_id": getattr(response, "id", None),
                "status": getattr(response, "status", None),
                "incomplete_details": jsonable(getattr(response, "incomplete_details", None)),
                "response": output_text(response),
            }

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            future_to_item = {executor.submit(generate_one, item): item for item in items}
            for future in as_completed(future_to_item):
                row = future.result()
                response_rows.append(row)
                response_rows.sort(key=lambda r: int(r.get("line_number") or 0))
                write_jsonl(args.responses_output, response_rows)
                item = future_to_item[future]
                print(
                    f"generated line {item['line_number']} response "
                    f"({len(row['response'])} chars, status={row['status']})",
                    flush=True,
                )

    if args.generate_only:
        print(f"generate-only requested; skipped judge scoring.", flush=True)
        print(f"wrote {args.selected_output}")
        print(f"wrote {args.responses_output}")
        return 0

    dataset = ev.load_dataset(args.selected_output)
    responses = ev.load_responses(args.responses_output)
    provider = OpenAIJudgeProvider(client, args.judge_model, args.judge_max_output_tokens)

    evaluated_items = []
    missing = []
    judge_jobs = []
    for item_id, item in sorted(dataset.items(), key=lambda pair: pair[1].get("_line_number", 0)):
        response = ev.response_for_item(item, responses)
        if response is None:
            missing.append(item_id)
            continue
        judge_jobs.append((item_id, item, response))

    def judge_one(job: Any) -> Dict[str, Any]:
        _item_id, item, response = job
        return ev.evaluate_item(
            item=item,
            response=response,
            provider=provider,
            hard_only=False,
            repeats=1,
            parse_retries=args.parse_retries,
        )

    with ThreadPoolExecutor(max_workers=max(1, args.judge_workers)) as executor:
        future_to_job = {executor.submit(judge_one, job): job for job in judge_jobs}
        for future in as_completed(future_to_job):
            latest = future.result()
            evaluated_items.append(latest)
            evaluated_items.sort(key=lambda item: item.get("line_number") or 0)
            print(
                f"scored {latest['item_id']}: IF={latest['summary']['score']} "
                f"quality={latest['quality'].get('score')}",
                flush=True,
            )

    output = {
        "schema_version": "finif-v2-gpt5-smoke-results-1.0",
        "dataset": str(args.selected_output),
        "source_dataset": str(args.dataset),
        "responses": str(args.responses_output),
        "response_model": args.response_model,
        "judge_model": args.judge_model,
        "summary": ev.summarize_dataset(evaluated_items),
        "missing_responses": missing,
        "items": evaluated_items,
    }
    args.scores_output.parent.mkdir(parents=True, exist_ok=True)
    args.scores_output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {args.selected_output}")
    print(f"wrote {args.responses_output}")
    print(f"wrote {args.scores_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
