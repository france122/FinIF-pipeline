#!/usr/bin/env python3
"""Generate FinIF responses with an OpenAI Responses API model, without judging."""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


DEFAULT_DATASET = Path("outputs/benchmark/finif_v2_tonight_hard300_ifclean.jsonl")
DEFAULT_KEY = Path("key.md")
DEFAULT_OUTPUT_ROOT = Path("outputs/model_runs")
DEFAULT_HYPERPARAMETERS_DIR = Path("outputs/model_runs/hyperparameters")


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if not match:
        raise ValueError(f"No OpenAI API key found in {path}")
    return match.group(0)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for row_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["id"] = row.get("id") or row.get("item_id") or row.get("case_id") or f"row_{row_number:03d}"
            row["line_number"] = row.get("line_number") or row_number
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
    return "\n".join(chunks).strip()


def load_existing(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = str(row.get("item_id") or row.get("id") or "")
            if item_id:
                out[item_id] = row
    return out


def create_response(
    client: OpenAI,
    *,
    model: str,
    prompt: str,
    max_output_tokens: int,
    reasoning_effort: Optional[str],
) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    try:
        return client.responses.create(**kwargs)
    except Exception:
        if "reasoning" not in kwargs:
            raise
        kwargs.pop("reasoning", None)
        return client.responses.create(**kwargs)


def generate_one(
    client: OpenAI,
    item: Dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    reasoning_effort: Optional[str],
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = create_response(
                client,
                model=model,
                prompt=item["full_prompt"],
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
            )
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": model,
                "provider": "openai",
                "api": "responses.create",
                "response_id": getattr(response, "id", None),
                "status": getattr(response, "status", None),
                "incomplete_details": jsonable(getattr(response, "incomplete_details", None)),
                "response": output_text(response),
                "usage": jsonable(getattr(response, "usage", None)),
            }
        except Exception as exc:  # pragma: no cover - provider dependent.
            last_error = exc
            message = str(exc).lower()
            if any(token in message for token in ("rate", "429", "timeout", "temporarily", "overload")):
                time.sleep(min(30, 2 ** attempt))
                continue
            if attempt < 3:
                time.sleep(1 + attempt)
                continue
            raise
    raise RuntimeError(f"Generation failed after retries: {last_error}")


def write_manifest(
    run_dir: Path,
    *,
    args: argparse.Namespace,
    selected_path: Path,
    responses_path: Path,
    total_selected_count: int,
    response_count: int,
) -> None:
    status = "responses_generated" if response_count == total_selected_count else "generation_in_progress"
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "source_dataset": str(args.dataset),
        "selected_dataset": str(selected_path),
        "selected_count": total_selected_count,
        "responses": str(responses_path),
        "response_count": response_count,
        "response_generation": {
            "provider": "openai",
            "api": "responses.create",
            "model": args.model,
            "temperature": "unsupported/not set",
            "top_p": "not set",
            "max_output_tokens": args.max_output_tokens,
            "reasoning": {"effort": args.reasoning_effort} if args.reasoning_effort else None,
            "workers": args.workers,
        },
        "judge": None,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_hyperparameters(
    run_dir: Path,
    *,
    args: argparse.Namespace,
    selected_path: Path,
    responses_path: Path,
    total_selected_count: int,
    response_count: int,
) -> None:
    status = "responses_generated" if response_count == total_selected_count else "generation_in_progress"
    args.hyperparameters_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_name": run_dir.name,
        "record_created_local": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "source_dataset": str(args.dataset),
        "selected_dataset": str(selected_path),
        "selected_count": total_selected_count,
        "response_generation": {
            "provider": "openai",
            "api": "responses.create",
            "model": args.model,
            "temperature": "unsupported/not set",
            "top_p": "not set",
            "max_output_tokens": args.max_output_tokens,
            "reasoning": {"effort": args.reasoning_effort} if args.reasoning_effort else None,
            "workers": args.workers,
        },
        "outputs": {
            "responses": str(responses_path),
            "manifest": str(run_dir / "manifest.json"),
        },
        "response_count": response_count,
    }
    (args.hyperparameters_dir / f"{run_dir.name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--hyperparameters-dir", type=Path, default=DEFAULT_HYPERPARAMETERS_DIR)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    rows = read_jsonl(args.dataset)
    if args.limit is not None:
        rows = rows[: args.limit]

    run_dir = args.output_root / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_path = run_dir / "selected_dataset.jsonl"
    responses_path = run_dir / f"responses_{args.model.replace('/', '_')}.jsonl"
    write_jsonl(selected_path, rows)

    existing = load_existing(responses_path)
    todo = [row for row in rows if str(row["id"]) not in existing]
    print(f"{args.model}: {len(existing)} existing, {len(todo)} to generate", flush=True)

    client = OpenAI(api_key=read_api_key(args.key_file))
    output_rows = [existing[str(row["id"])] for row in rows if str(row["id"]) in existing]

    def one(item: Dict[str, Any]) -> Dict[str, Any]:
        return generate_one(
            client,
            item,
            model=args.model,
            max_output_tokens=args.max_output_tokens,
            reasoning_effort=args.reasoning_effort,
        )

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(one, item): item for item in todo}
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            output_rows = [old for old in output_rows if old.get("item_id") != row.get("item_id")]
            output_rows.append(row)
            output_rows.sort(key=lambda r: int(r.get("line_number") or 0))
            write_jsonl(responses_path, output_rows)
            write_manifest(
                run_dir,
                args=args,
                selected_path=selected_path,
                responses_path=responses_path,
                total_selected_count=len(rows),
                response_count=len(output_rows),
            )
            write_hyperparameters(
                run_dir,
                args=args,
                selected_path=selected_path,
                responses_path=responses_path,
                total_selected_count=len(rows),
                response_count=len(output_rows),
            )
            print(
                f"{args.model}: generated line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, status={row.get('status')})",
                flush=True,
            )

    write_manifest(
        run_dir,
        args=args,
        selected_path=selected_path,
        responses_path=responses_path,
        total_selected_count=len(rows),
        response_count=len(output_rows),
    )
    write_hyperparameters(
        run_dir,
        args=args,
        selected_path=selected_path,
        responses_path=responses_path,
        total_selected_count=len(rows),
        response_count=len(output_rows),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
