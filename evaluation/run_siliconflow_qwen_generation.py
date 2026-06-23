#!/usr/bin/env python3
"""Generate SiliconFlow Qwen hard300 responses without running a judge."""

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
DEFAULT_RUN_NAME = "qwen3.5-9b_siliconflow_hard300_ifclean_temp0_judge_gpt4o"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_KEY = "qwen3.5-9b-siliconflow"

MODEL_CONFIG: Dict[str, Any] = {
    "provider": "siliconflow",
    "api_model": "Qwen/Qwen3.5-9B",
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


def default_key_file() -> Path:
    preferred = Path("key_silicon_flow.md")
    fallback = Path("key_siliconflow.md")
    if preferred.exists():
        return preferred
    if fallback.exists():
        return fallback
    raise FileNotFoundError("Missing key_silicon_flow.md and key_siliconflow.md")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row_id = row.get("id") or row.get("item_id") or row.get("case_id")
            if not row_id:
                raise ValueError(f"{path}:{line_number}: missing id/item_id/case_id")
            row["id"] = str(row_id)
            row["line_number"] = row.get("line_number") or line_number
            rows.append(row)
    ids = [row["id"] for row in rows]
    duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate dataset ids: {duplicates[:10]}")
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def response_item_id(row: Dict[str, Any]) -> str:
    return str(row.get("item_id") or row.get("id") or row.get("case_id") or "")


def load_existing_responses(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = response_item_id(row)
            if not item_id:
                raise ValueError(f"{path}:{line_number}: response row missing item_id/id/case_id")
            if not str(row.get("response") or ""):
                continue
            out[item_id] = row
    return out


def sorted_response_rows(dataset_rows: List[Dict[str, Any]], existing: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [existing[row["id"]] for row in dataset_rows if row["id"] in existing]


def is_rate_limit_or_unavailable(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("429", "503", "rate", "too many", "temporarily", "unavailable", "overload"))


def generate_one(client: OpenAI, item: Dict[str, Any]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": MODEL_CONFIG["api_model"],
        "messages": [{"role": "user", "content": item["full_prompt"]}],
        "temperature": MODEL_CONFIG["temperature"],
        "top_p": MODEL_CONFIG["top_p"],
        "max_tokens": MODEL_CONFIG["max_tokens"],
        "stream": MODEL_CONFIG["stream"],
        "extra_body": {"enable_thinking": MODEL_CONFIG["enable_thinking"]},
    }
    last_error: Optional[Exception] = None
    for attempt in range(5):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": MODEL_KEY,
                "api_model": MODEL_CONFIG["api_model"],
                "provider": "siliconflow",
                "response_id": getattr(response, "id", None),
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "response": content,
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else None,
                "generated_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as exc:  # pragma: no cover - depends on provider behavior.
            last_error = exc
            if is_rate_limit_or_unavailable(exc):
                time.sleep(min(60, 3 * (attempt + 1)))
                continue
            if attempt < 4:
                time.sleep(2 + attempt)
                continue
            raise
    raise RuntimeError(f"Generation failed after retries: {last_error}")


def strict_id_status(dataset_rows: List[Dict[str, Any]], response_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dataset_ids = [row["id"] for row in dataset_rows]
    response_ids = [response_item_id(row) for row in response_rows]
    duplicate_responses = sorted({item_id for item_id in response_ids if response_ids.count(item_id) > 1})
    dataset_set = set(dataset_ids)
    response_set = set(response_ids)
    return {
        "dataset_items": len(dataset_ids),
        "response_items": len(response_ids),
        "ids_match": dataset_set == response_set and not duplicate_responses,
        "missing_response_ids": sorted(dataset_set - response_set),
        "extra_response_ids": sorted(response_set - dataset_set),
        "duplicate_response_ids": duplicate_responses,
    }


def write_manifest(
    run_dir: Path,
    *,
    dataset_path: Path,
    selected_path: Path,
    responses_path: Path,
    args: argparse.Namespace,
    status: Dict[str, Any],
    final: bool,
) -> None:
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dataset": str(dataset_path),
        "response_model": MODEL_KEY,
        "response_provider": "siliconflow",
        "response_api": "chat.completions",
        "response_base_url": SILICONFLOW_BASE_URL,
        "response_parameters": {**MODEL_CONFIG, "workers": args.workers},
        "judge_model": "gpt-4o",
        "judge_status": "not_run_per_user_pause",
        "judge_parameters_planned": {
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 2400,
            "repeats": 1,
            "parse_retries": 2,
            "judge_workers": 1,
        },
        "selected_dataset": str(selected_path),
        "responses": str(responses_path),
        "scores": None,
        "generation_status": status,
        "final": final,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_hyperparameters(path: Path, *, dataset_path: Path, args: argparse.Namespace, status: Dict[str, Any]) -> None:
    payload = {
        "run_name": DEFAULT_RUN_NAME,
        "record_created_local": datetime.now().strftime("%Y-%m-%d"),
        "status": "generation_completed" if status.get("ids_match") else "generation_incomplete",
        "source_dataset": str(dataset_path),
        "response_generation": {
            "provider": "siliconflow",
            "base_url": SILICONFLOW_BASE_URL,
            "api": "chat.completions",
            "model": MODEL_CONFIG["api_model"],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 8192,
            "stream": False,
            "enable_thinking": False,
            "workers": args.workers,
        },
        "judge": {
            "provider": "openai",
            "api": "responses.create",
            "model": "gpt-4o",
            "status": "not_run_per_user_pause",
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 2400,
            "repeats": 1,
            "parse_retries": 2,
            "judge_workers": 1,
        },
        "generation_status": status,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_responses(
    *,
    dataset_rows: List[Dict[str, Any]],
    responses_path: Path,
    key_file: Path,
    workers: int,
) -> Dict[str, Any]:
    existing = load_existing_responses(responses_path)
    dataset_ids = {row["id"] for row in dataset_rows}
    existing = {item_id: row for item_id, row in existing.items() if item_id in dataset_ids}
    todo = [row for row in dataset_rows if row["id"] not in existing]
    print(f"{MODEL_KEY}: {len(existing)} existing successful responses, {len(todo)} to generate", flush=True)
    if not todo:
        rows = sorted_response_rows(dataset_rows, existing)
        write_jsonl(responses_path, rows)
        return strict_id_status(dataset_rows, rows)

    client = OpenAI(api_key=read_api_key(key_file), base_url=SILICONFLOW_BASE_URL)
    observed_rate_limit = 0

    def one(item: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal observed_rate_limit
        try:
            return generate_one(client, item)
        except Exception as exc:
            if is_rate_limit_or_unavailable(exc):
                observed_rate_limit += 1
            raise

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(one, item): item for item in todo}
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            existing[row["item_id"]] = row
            rows = sorted_response_rows(dataset_rows, existing)
            write_jsonl(responses_path, rows)
            print(
                f"{MODEL_KEY}: generated line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, finish={row.get('finish_reason')})",
                flush=True,
            )

    status = strict_id_status(dataset_rows, sorted_response_rows(dataset_rows, existing))
    status["observed_rate_limit_or_503_failures"] = observed_rate_limit
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--key-file", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    key_file = args.key_file or default_key_file()
    dataset_rows = read_jsonl(args.dataset)
    if args.limit is not None:
        dataset_rows = dataset_rows[: args.limit]

    run_dir = args.output_root / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_path = run_dir / "selected_dataset.jsonl"
    responses_path = run_dir / "responses_qwen3.5-9b_siliconflow.jsonl"
    hyper_path = args.output_root / "hyperparameters" / f"{args.run_name}.json"

    write_jsonl(selected_path, dataset_rows)
    initial_status = strict_id_status(dataset_rows, sorted_response_rows(dataset_rows, load_existing_responses(responses_path)))
    write_manifest(
        run_dir,
        dataset_path=args.dataset,
        selected_path=selected_path,
        responses_path=responses_path,
        args=args,
        status=initial_status,
        final=False,
    )

    status = generate_responses(
        dataset_rows=dataset_rows,
        responses_path=responses_path,
        key_file=key_file,
        workers=args.workers,
    )
    write_manifest(
        run_dir,
        dataset_path=args.dataset,
        selected_path=selected_path,
        responses_path=responses_path,
        args=args,
        status=status,
        final=True,
    )
    write_hyperparameters(hyper_path, dataset_path=args.dataset, args=args, status=status)
    print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
