#!/usr/bin/env python3
"""Generate DeepSeek hard300 responses and score them with GPT-4o judge."""

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

try:
    from . import evaluate_responses as ev
except ImportError:  # pragma: no cover - direct script execution.
    import evaluate_responses as ev


DEFAULT_DATASET = Path("outputs/benchmark/finif_v2_tonight_hard300_ifclean.jsonl")
DEFAULT_DS_KEY = Path("key_ds.md")
DEFAULT_OPENAI_KEY = Path("key.md")
DEFAULT_OUTPUT_ROOT = Path("outputs/model_runs")
DS_BASE_URL = "https://api.deepseek.com"


MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "ds-v4-flash": {
        "provider": "deepseek",
        "api_model": "deepseek-v4-flash",
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 8192,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "thinking": False,
    },
    "ds-v4-pro": {
        "provider": "deepseek",
        "api_model": "deepseek-v4-pro",
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 8192,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "thinking": False,
    },
}


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if not match:
        raise ValueError(f"No API key found in {path}")
    return match.group(0)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["id"] = row.get("id") or f"v6_line_{line_number:03d}"
            row["line_number"] = row.get("line_number") or line_number
            rows.append(row)
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
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            item_id = str(row.get("item_id") or row.get("id") or "")
            if item_id:
                out[item_id] = row
    return out


def deepseek_generate(client: OpenAI, item: Dict[str, Any], model_key: str) -> Dict[str, Any]:
    cfg = MODEL_CONFIG[model_key]
    kwargs: Dict[str, Any] = {
        "model": cfg["api_model"],
        "messages": [{"role": "user", "content": item["full_prompt"]}],
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "max_tokens": cfg["max_tokens"],
        "stream": cfg["stream"],
        "frequency_penalty": cfg["frequency_penalty"],
        "presence_penalty": cfg["presence_penalty"],
    }
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": model_key,
                "api_model": cfg["api_model"],
                "provider": "deepseek",
                "response_id": getattr(response, "id", None),
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "response": content,
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else None,
            }
        except Exception as exc:  # pragma: no cover - depends on provider errors.
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


def generate_responses(
    *,
    dataset_rows: List[Dict[str, Any]],
    model_key: str,
    output_path: Path,
    key_file: Path,
    workers: int,
) -> List[Dict[str, Any]]:
    existing = load_existing_responses(output_path)
    done_ids = set(existing)
    todo = [row for row in dataset_rows if str(row["id"]) not in done_ids]
    print(f"{model_key}: {len(done_ids)} existing, {len(todo)} to generate", flush=True)
    if not todo:
        return [existing[str(row["id"])] for row in dataset_rows if str(row["id"]) in existing]

    client = OpenAI(api_key=read_api_key(key_file), base_url=DS_BASE_URL)
    rows = [existing[str(row["id"])] for row in dataset_rows if str(row["id"]) in existing]

    def one(item: Dict[str, Any]) -> Dict[str, Any]:
        return deepseek_generate(client, item, model_key)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(one, item): item for item in todo}
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            rows.append(row)
            rows.sort(key=lambda r: int(r.get("line_number") or 0))
            write_jsonl(output_path, rows)
            print(
                f"{model_key}: generated line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, finish={row.get('finish_reason')})",
                flush=True,
            )
    return rows


def create_json_response(
    client: OpenAI,
    model: str,
    instructions: str,
    prompt: str,
    *,
    max_output_tokens: int,
) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": 0,
        "top_p": 1,
        "text": {"format": {"type": "json_object"}},
    }
    try:
        return client.responses.create(**kwargs)
    except Exception:
        kwargs.pop("text", None)
        return client.responses.create(**kwargs)


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


def apply_manual_overrides(evaluated_item: Dict[str, Any]) -> Dict[str, Any]:
    """Apply audited local corrections that do not require another judge call."""
    changed = False
    if evaluated_item.get("item_id") == "v6_line_001":
        for result in evaluated_item.get("results", []):
            if (
                result.get("tag") == "DB4"
                and result.get("constraint")
                == "The table must not mark the item reconciled if the adjusted break remains above threshold."
                and result.get("score") == 0
                and "exactly at the threshold" in str(result.get("reason", "")).lower()
            ):
                result["manual_audit_original_score"] = result.get("score")
                result["manual_audit_original_status"] = result.get("status")
                result["manual_audit_original_reason"] = result.get("reason")
                result["manual_audit_override"] = {
                    "date": "2026-06-14",
                    "conclusion": "judge_over_strict_false_fail",
                    "rationale": "Exactly at threshold is not above threshold; DB4 is satisfied.",
                }
                result["score"] = 1
                result["status"] = "pass"
                result["reason"] = (
                    "Manual audit override: adjusted break is exactly at the threshold, "
                    "not above it; DB4 is satisfied."
                )
                changed = True
    if changed:
        evaluated_item["summary"] = ev.summarize_results(
            evaluated_item.get("results", []),
            evaluated_item.get("quality", {}),
        )
    return evaluated_item


def score_responses(
    *,
    dataset_path: Path,
    responses_path: Path,
    scores_path: Path,
    openai_key_file: Path,
    response_model: str,
    judge_model: str,
    judge_max_output_tokens: int,
    parse_retries: int,
    judge_workers: int,
) -> Dict[str, Any]:
    dataset = ev.load_dataset(dataset_path)
    responses = ev.load_responses(responses_path)
    provider = OpenAIJudgeProvider(
        OpenAI(api_key=read_api_key(openai_key_file)),
        judge_model,
        judge_max_output_tokens,
    )
    evaluated_items: List[Dict[str, Any]] = []
    existing_by_id: Dict[str, Dict[str, Any]] = {}
    if scores_path.exists():
        old = json.loads(scores_path.read_text(encoding="utf-8"))
        existing_by_id = {str(item.get("item_id")): item for item in old.get("items", [])}
        evaluated_items = list(existing_by_id.values())
        print(f"{response_model}: reusing {len(evaluated_items)} existing scored items", flush=True)

    missing = []
    jobs = []
    for item_id, item in sorted(dataset.items(), key=lambda pair: pair[1].get("_line_number", 0)):
        if item_id in existing_by_id:
            continue
        response = ev.response_for_item(item, responses)
        if response is None:
            missing.append(item_id)
            continue
        jobs.append((item_id, item, response))

    def judge_one(job: Any) -> Dict[str, Any]:
        _item_id, item, response = job
        return apply_manual_overrides(
            ev.evaluate_item(
                item=item,
                response=response,
                provider=provider,
                hard_only=False,
                repeats=1,
                parse_retries=parse_retries,
            )
        )

    with ThreadPoolExecutor(max_workers=max(1, judge_workers)) as executor:
        futures = {executor.submit(judge_one, job): job for job in jobs}
        for future in as_completed(futures):
            latest = future.result()
            evaluated_items = [item for item in evaluated_items if item.get("item_id") != latest.get("item_id")]
            evaluated_items.append(latest)
            evaluated_items.sort(key=lambda item: int(item.get("line_number") or 0))
            output = {
                "schema_version": "finif-v2-deepseek-hard300-results-1.0",
                "dataset": str(dataset_path),
                "responses": str(responses_path),
                "response_model": response_model,
                "judge_model": judge_model,
                "judge_provider": provider.name,
                "repeats": 1,
                "parse_retries": parse_retries,
                "summary": ev.summarize_dataset(evaluated_items),
                "missing_responses": missing,
                "items": evaluated_items,
            }
            scores_path.parent.mkdir(parents=True, exist_ok=True)
            scores_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                f"{response_model}: scored {latest['item_id']} "
                f"IF={latest['summary']['score']} quality={latest['quality'].get('score')}",
                flush=True,
            )

    output = {
        "schema_version": "finif-v2-deepseek-hard300-results-1.0",
        "dataset": str(dataset_path),
        "responses": str(responses_path),
        "response_model": response_model,
        "judge_model": judge_model,
        "judge_provider": provider.name,
        "repeats": 1,
        "parse_retries": parse_retries,
        "summary": ev.summarize_dataset(evaluated_items),
        "missing_responses": missing,
        "items": evaluated_items,
    }
    scores_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_manifest(
    run_dir: Path,
    *,
    model_key: str,
    dataset_path: Path,
    responses_path: Path,
    scores_path: Path,
    judge_model: str,
    args: argparse.Namespace,
    summary: Optional[Dict[str, Any]] = None,
) -> None:
    cfg = MODEL_CONFIG[model_key]
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dataset": str(dataset_path),
        "response_model": model_key,
        "response_provider": "deepseek",
        "response_api": "chat.completions",
        "response_base_url": DS_BASE_URL,
        "response_parameters": cfg,
        "judge_model": judge_model,
        "judge_provider": "openai",
        "judge_api": "responses.create",
        "judge_parameters": {
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": args.judge_max_output_tokens,
            "response_format": "json_object",
            "repeats": 1,
            "parse_retries": args.parse_retries,
            "judge_workers": args.judge_workers,
        },
        "selected_dataset": str(run_dir / "selected_dataset.jsonl"),
        "responses": str(responses_path),
        "scores": str(scores_path),
        "summary": summary,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--models", nargs="+", default=["ds-v4-flash", "ds-v4-pro"])
    parser.add_argument("--ds-key-file", type=Path, default=DEFAULT_DS_KEY)
    parser.add_argument("--openai-key-file", type=Path, default=DEFAULT_OPENAI_KEY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--judge-workers", type=int, default=1)
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--parse-retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N dataset rows.")
    parser.add_argument("--reuse-responses", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()

    dataset_rows = read_jsonl(args.dataset)
    if args.limit is not None:
        dataset_rows = dataset_rows[: args.limit]
    for model_key in args.models:
        if model_key not in MODEL_CONFIG:
            raise ValueError(f"Unknown model {model_key}; choose from {sorted(MODEL_CONFIG)}")
        run_dir = args.output_root / f"{model_key}_hard300_ifclean_temp0_judge_gpt4o"
        run_dir.mkdir(parents=True, exist_ok=True)
        selected_path = run_dir / "selected_dataset.jsonl"
        responses_path = run_dir / f"responses_{model_key}.jsonl"
        scores_path = run_dir / f"scores_{model_key}_judge_gpt4o.json"
        write_jsonl(selected_path, dataset_rows)
        write_manifest(
            run_dir,
            model_key=model_key,
            dataset_path=args.dataset,
            responses_path=responses_path,
            scores_path=scores_path,
            judge_model=args.judge_model,
            args=args,
        )

        if args.reuse_responses and not responses_path.exists():
            raise FileNotFoundError(f"--reuse-responses requested but {responses_path} does not exist")
        if not args.reuse_responses:
            generate_responses(
                dataset_rows=dataset_rows,
                model_key=model_key,
                output_path=responses_path,
                key_file=args.ds_key_file,
                workers=args.workers,
            )
        if args.generate_only:
            print(f"{model_key}: generate-only; skipping judge", flush=True)
            continue
        output = score_responses(
            dataset_path=selected_path,
            responses_path=responses_path,
            scores_path=scores_path,
            openai_key_file=args.openai_key_file,
            response_model=model_key,
            judge_model=args.judge_model,
            judge_max_output_tokens=args.judge_max_output_tokens,
            parse_retries=args.parse_retries,
            judge_workers=args.judge_workers,
        )
        write_manifest(
            run_dir,
            model_key=model_key,
            dataset_path=args.dataset,
            responses_path=responses_path,
            scores_path=scores_path,
            judge_model=args.judge_model,
            args=args,
            summary=output["summary"],
        )
        print(json.dumps(output["summary"], ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
