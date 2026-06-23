#!/usr/bin/env python3
"""Generate FinIF responses with SiliconFlow chat completions, without judging."""

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
DEFAULT_KEY_FILES = [Path("key_silicon_flow.md"), Path("key_siliconflow.md")]
DEFAULT_OUTPUT_ROOT = Path("outputs/model_runs")
BASE_URL = "https://api.siliconflow.cn/v1"


def read_api_key(paths: List[Path]) -> str:
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"sk-[A-Za-z0-9_-]+", text)
        if match:
            return match.group(0)
    raise ValueError(f"No SiliconFlow API key found in {[str(path) for path in paths]}")


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


def generate_one(
    client: OpenAI,
    item: Dict[str, Any],
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    enable_thinking: bool,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": item["full_prompt"]}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": False,
        "extra_body": {"enable_thinking": enable_thinking},
    }
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": model,
                "provider": "siliconflow",
                "api": "chat.completions",
                "response_id": getattr(response, "id", None),
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "response": content,
                "usage": jsonable(getattr(response, "usage", None)),
            }
        except Exception as exc:  # pragma: no cover - provider dependent.
            last_error = exc
            message = str(exc).lower()
            if any(token in message for token in ("rate", "429", "timeout", "temporarily", "overload", "503")):
                time.sleep(min(45, 2 ** attempt))
                continue
            if attempt < 3:
                time.sleep(1 + attempt)
                continue
            raise
    raise RuntimeError(f"Generation failed after retries: {last_error}")


def safe_model_name(model: str) -> str:
    return model.lower().replace("/", "_").replace(".", "_")


def write_manifest(
    run_dir: Path,
    *,
    args: argparse.Namespace,
    selected_path: Path,
    responses_path: Path,
    response_count: int,
) -> None:
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "responses_generated" if response_count == 300 else "generation_in_progress",
        "source_dataset": str(args.dataset),
        "selected_dataset": str(selected_path),
        "responses": str(responses_path),
        "response_count": response_count,
        "response_generation": {
            "provider": "siliconflow",
            "base_url": BASE_URL,
            "api": "chat.completions",
            "model": args.model,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
            "stream": False,
            "enable_thinking": args.enable_thinking,
            "workers": args.workers,
        },
        "judge": None,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    hyper_path = Path("outputs/model_runs/hyperparameters") / f"{run_dir.name}.json"
    hyper_path.parent.mkdir(parents=True, exist_ok=True)
    hyper_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--key-file", action="append", type=Path, default=[])
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--top-p", type=float, default=1)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    rows = read_jsonl(args.dataset)
    if args.limit is not None:
        rows = rows[: args.limit]

    run_dir = args.output_root / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_path = run_dir / "selected_dataset.jsonl"
    responses_path = run_dir / f"responses_{safe_model_name(args.model)}.jsonl"
    write_jsonl(selected_path, rows)

    existing = load_existing(responses_path)
    todo = [row for row in rows if str(row["id"]) not in existing]
    print(f"{args.model}: {len(existing)} existing, {len(todo)} to generate", flush=True)

    key_paths = args.key_file or DEFAULT_KEY_FILES
    client = OpenAI(api_key=read_api_key(key_paths), base_url=BASE_URL)
    output_rows = [existing[str(row["id"])] for row in rows if str(row["id"]) in existing]

    def one(item: Dict[str, Any]) -> Dict[str, Any]:
        return generate_one(
            client,
            item,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            enable_thinking=args.enable_thinking,
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
                response_count=len(output_rows),
            )
            print(
                f"{args.model}: generated line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, finish={row.get('finish_reason')})",
                flush=True,
            )

    write_manifest(
        run_dir,
        args=args,
        selected_path=selected_path,
        responses_path=responses_path,
        response_count=len(output_rows),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
