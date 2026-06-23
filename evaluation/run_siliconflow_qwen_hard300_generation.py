#!/usr/bin/env python3
"""Generate SiliconFlow Qwen3.5-4B responses for FinIF hard300 IF-clean.

This runner intentionally does generation only. It does not call any judge.
"""

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
DEFAULT_OUTPUT_ROOT = Path("outputs/model_runs")
DEFAULT_RUN_NAME = "qwen3.5-4b_siliconflow_hard300_ifclean_temp0_judge_gpt4o"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_KEY = "qwen3.5-4b"
API_MODEL = "Qwen/Qwen3.5-4B"

GENERATION_CONFIG: Dict[str, Any] = {
    "provider": "siliconflow",
    "base_url": SILICONFLOW_BASE_URL,
    "api": "chat.completions",
    "model": API_MODEL,
    "temperature": 0,
    "top_p": 1,
    "max_tokens": 8192,
    "stream": False,
    "enable_thinking": False,
}


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if not match:
        raise ValueError(f"No API key found in {path}")
    return match.group(0)


def resolve_key_file() -> Path:
    for path in (Path("key_silicon_flow.md"), Path("key_siliconflow.md")):
        if path.exists():
            return path
    raise FileNotFoundError("Expected key_silicon_flow.md or key_siliconflow.md")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("id"):
                raise ValueError(f"{path}:{line_number}: dataset row missing explicit id")
            row["line_number"] = row.get("line_number") or line_number
            rows.append(row)
    ids = [str(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Dataset contains duplicate ids")
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_existing_responses(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = str(row.get("item_id") or "")
            response = row.get("response")
            if not item_id:
                raise ValueError(f"{path}:{line_number}: response row missing item_id")
            if response is None:
                continue
            out[item_id] = row
    return out


def transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("429", "503", "rate", "timeout", "temporarily", "overload"))


def generate_one(client: OpenAI, item: Dict[str, Any]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": API_MODEL,
        "messages": [{"role": "user", "content": item["full_prompt"]}],
        "temperature": GENERATION_CONFIG["temperature"],
        "top_p": GENERATION_CONFIG["top_p"],
        "max_tokens": GENERATION_CONFIG["max_tokens"],
        "stream": GENERATION_CONFIG["stream"],
        "extra_body": {"enable_thinking": GENERATION_CONFIG["enable_thinking"]},
    }
    last_error: Optional[Exception] = None
    for attempt in range(5):
        try:
            response = client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": MODEL_KEY,
                "api_model": API_MODEL,
                "provider": "siliconflow",
                "response_id": getattr(response, "id", None),
                "finish_reason": choice.finish_reason,
                "response": content,
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else None,
                "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as exc:  # pragma: no cover - depends on provider errors.
            last_error = exc
            if transient_error(exc):
                time.sleep(min(90, 5 * (attempt + 1) * (attempt + 1)))
                continue
            if attempt < 2:
                time.sleep(2 + attempt)
                continue
            raise
    raise RuntimeError(f"Generation failed after retries: {last_error}")


def generation_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    finish_counts: Dict[str, int] = {}
    empty = 0
    for row in rows:
        finish = str(row.get("finish_reason") or "unknown")
        finish_counts[finish] = finish_counts.get(finish, 0) + 1
        if not str(row.get("response") or "").strip():
            empty += 1
    return {
        "responses": len(rows),
        "empty_responses": empty,
        "finish_reason_counts": finish_counts,
        "length_finish_count": finish_counts.get("length", 0),
    }


def validate_response_ids(dataset_rows: List[Dict[str, Any]], response_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dataset_ids = {str(row["id"]) for row in dataset_rows}
    response_ids = {str(row.get("item_id") or "") for row in response_rows}
    missing = sorted(dataset_ids - response_ids)
    extra = sorted(response_ids - dataset_ids)
    return {
        "dataset_items": len(dataset_ids),
        "response_items": len(response_ids),
        "matched": not missing and not extra,
        "missing_response_ids": missing,
        "extra_response_ids": extra,
    }


def write_manifest(
    run_dir: Path,
    *,
    dataset_path: Path,
    selected_path: Path,
    responses_path: Path,
    workers: int,
    limit: Optional[int],
    response_rows: List[Dict[str, Any]],
    id_validation: Dict[str, Any],
) -> None:
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dataset": str(dataset_path),
        "selected_dataset": str(selected_path),
        "responses": str(responses_path),
        "scores": None,
        "response_model": MODEL_KEY,
        "response_provider": "siliconflow",
        "response_api": "chat.completions",
        "response_base_url": SILICONFLOW_BASE_URL,
        "response_parameters": {
            **GENERATION_CONFIG,
            "workers": workers,
        },
        "judge_status": "not_run",
        "judge_note": "Generation-only run. Do not call GPT-4o judge until matching logic is confirmed.",
        "limit": limit,
        "generation_summary": generation_stats(response_rows),
        "item_id_validation": id_validation,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_hyperparameters(
    path: Path,
    *,
    run_dir: Path,
    dataset_path: Path,
    workers: int,
    status: str,
    summary: Dict[str, Any],
) -> None:
    payload = {
        "run_name": run_dir.name,
        "record_created_local": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "source_dataset": str(dataset_path),
        "response_generation": {
            **GENERATION_CONFIG,
            "workers": workers,
        },
        "judge": {
            "status": "not_run",
            "planned_provider": "openai",
            "planned_api": "responses.create",
            "planned_model": "gpt-4o",
            "planned_temperature": 0,
            "planned_top_p": 1,
            "planned_max_output_tokens": 2400,
            "planned_repeats": 1,
            "planned_parse_retries": 2,
            "planned_judge_workers": 1,
        },
        "generation_summary": summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_responses(
    *,
    dataset_rows: List[Dict[str, Any]],
    responses_path: Path,
    key_file: Path,
    workers: int,
) -> List[Dict[str, Any]]:
    existing = load_existing_responses(responses_path)
    dataset_ids = {str(row["id"]) for row in dataset_rows}
    reusable = {item_id: row for item_id, row in existing.items() if item_id in dataset_ids}
    todo = [row for row in dataset_rows if str(row["id"]) not in reusable]
    print(f"{MODEL_KEY}: {len(reusable)} existing successful responses, {len(todo)} to generate", flush=True)
    rows = [reusable[str(row["id"])] for row in dataset_rows if str(row["id"]) in reusable]
    if not todo:
        return rows

    client = OpenAI(
        api_key=read_api_key(key_file),
        base_url=SILICONFLOW_BASE_URL,
        timeout=180,
        max_retries=0,
    )

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(generate_one, client, item): item for item in todo}
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            rows = [old for old in rows if str(old.get("item_id")) != str(row["item_id"])]
            rows.append(row)
            rows.sort(key=lambda r: int(r.get("line_number") or 0))
            write_jsonl(responses_path, rows)
            print(
                f"{MODEL_KEY}: generated {item['id']} line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, finish={row.get('finish_reason')})",
                flush=True,
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dataset_rows = read_jsonl(args.dataset)
    if args.limit is not None:
        dataset_rows = dataset_rows[: args.limit]

    run_dir = args.output_root / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_path = run_dir / "selected_dataset.jsonl"
    responses_path = run_dir / "responses_qwen3.5-4b_siliconflow.jsonl"
    hyperparameters_path = args.output_root / "hyperparameters" / f"{args.run_name}.json"

    write_jsonl(selected_path, dataset_rows)
    response_rows = generate_responses(
        dataset_rows=dataset_rows,
        responses_path=responses_path,
        key_file=resolve_key_file(),
        workers=args.workers,
    )
    id_validation = validate_response_ids(dataset_rows, response_rows)
    summary = generation_stats(response_rows)
    write_manifest(
        run_dir,
        dataset_path=args.dataset,
        selected_path=selected_path,
        responses_path=responses_path,
        workers=args.workers,
        limit=args.limit,
        response_rows=response_rows,
        id_validation=id_validation,
    )
    write_hyperparameters(
        hyperparameters_path,
        run_dir=run_dir,
        dataset_path=args.dataset,
        workers=args.workers,
        status="generation_complete" if id_validation["matched"] else "generation_partial",
        summary={**summary, "item_id_validation": id_validation},
    )
    print(json.dumps({"run_dir": str(run_dir), "summary": summary, "item_id_validation": id_validation}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
