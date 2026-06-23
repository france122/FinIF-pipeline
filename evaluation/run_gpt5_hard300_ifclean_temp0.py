#!/usr/bin/env python3
"""Generate GPT-5 hard300 IF-clean responses at temperature=0 and judge with GPT-4o."""

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
DEFAULT_OPENAI_KEY = Path("key.md")
DEFAULT_RUN_DIR = Path("outputs/model_runs/gpt5_hard300_ifclean_temp0_judge_gpt4o_rerun_20260614")
DEFAULT_HYPERPARAMETERS_DIR = Path("outputs/model_runs/hyperparameters")


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
            if item_id and isinstance(row.get("response"), str) and row["response"].strip():
                out[item_id] = row
    return out


def is_temperature_unsupported(exc: Exception) -> bool:
    message = str(exc).lower()
    return "temperature" in message and any(
        token in message
        for token in (
            "unsupported",
            "not supported",
            "does not support",
            "unknown parameter",
            "unrecognized",
            "invalid parameter",
            "only the default",
            "default value",
        )
    )


def is_retryable(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "rate",
            "429",
            "timeout",
            "temporarily",
            "overload",
            "server error",
            "connection",
            "502",
            "503",
            "504",
        )
    )


def create_gpt5_response(
    client: OpenAI,
    prompt: str,
    *,
    model: str,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
    reasoning_effort: str,
) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def generate_one(
    client: OpenAI,
    item: Dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
    reasoning_effort: str,
    retries: int,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(max(1, retries + 1)):
        try:
            response = create_gpt5_response(
                client,
                item["full_prompt"],
                model=model,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                reasoning_effort=reasoning_effort,
            )
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": model,
                "provider": "openai",
                "api": "responses.create",
                "temperature": temperature,
                "top_p": top_p,
                "max_output_tokens": max_output_tokens,
                "reasoning": {"effort": reasoning_effort} if reasoning_effort else None,
                "response_id": getattr(response, "id", None),
                "status": getattr(response, "status", None),
                "incomplete_details": jsonable(getattr(response, "incomplete_details", None)),
                "usage": jsonable(getattr(response, "usage", None)),
                "response": output_text(response),
            }
        except Exception as exc:  # pragma: no cover - depends on provider errors.
            if is_temperature_unsupported(exc):
                raise
            last_error = exc
            if is_retryable(exc) and attempt < retries:
                time.sleep(min(60, 2 ** attempt))
                continue
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            raise
    raise RuntimeError(f"Generation failed after retries: {last_error}")


def smoke_temperature_probe(
    *,
    client: OpenAI,
    item: Dict[str, Any],
    model: str,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
    reasoning_effort: str,
) -> Dict[str, Any]:
    response = create_gpt5_response(
        client,
        item["full_prompt"],
        model=model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_p=top_p,
        reasoning_effort=reasoning_effort,
    )
    return {
        "ok": True,
        "response_id": getattr(response, "id", None),
        "status": getattr(response, "status", None),
        "incomplete_details": jsonable(getattr(response, "incomplete_details", None)),
        "output_chars": len(output_text(response)),
        "usage": jsonable(getattr(response, "usage", None)),
    }


def generate_responses(
    *,
    dataset_rows: List[Dict[str, Any]],
    output_path: Path,
    key_file: Path,
    model: str,
    max_output_tokens: int,
    temperature: float,
    top_p: float,
    reasoning_effort: str,
    workers: int,
    retries: int,
) -> List[Dict[str, Any]]:
    existing = load_existing_responses(output_path)
    rows = [existing[str(row["id"])] for row in dataset_rows if str(row["id"]) in existing]
    todo = [row for row in dataset_rows if str(row["id"]) not in existing]
    print(f"{model}: {len(existing)} existing complete responses, {len(todo)} to generate", flush=True)
    if not todo:
        return rows

    client = OpenAI(api_key=read_api_key(key_file))

    def one(item: Dict[str, Any]) -> Dict[str, Any]:
        return generate_one(
            client,
            item,
            model=model,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
            reasoning_effort=reasoning_effort,
            retries=retries,
        )

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(one, item): item for item in todo}
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            rows = [old for old in rows if old.get("item_id") != row.get("item_id")]
            rows.append(row)
            rows.sort(key=lambda r: int(r.get("line_number") or 0))
            write_jsonl(output_path, rows)
            print(
                f"{model}: generated line {item['line_number']} "
                f"({len(row.get('response') or '')} chars, status={row.get('status')})",
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


def score_responses(
    *,
    dataset_path: Path,
    responses_path: Path,
    scores_path: Path,
    openai_key_file: Path,
    response_model: str,
    judge_model: str,
    judge_max_output_tokens: int,
    repeats: int,
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

    def write_scores() -> Dict[str, Any]:
        output = {
            "schema_version": "finif-v2-gpt5-hard300-temp0-results-1.0",
            "dataset": str(dataset_path),
            "responses": str(responses_path),
            "response_model": response_model,
            "judge_model": judge_model,
            "judge_provider": provider.name,
            "judge_temperature_policy": 0,
            "judge_top_p": 1,
            "judge_max_output_tokens": judge_max_output_tokens,
            "repeats": repeats,
            "parse_retries": parse_retries,
            "summary": ev.summarize_dataset(evaluated_items),
            "missing_responses": missing,
            "items": evaluated_items,
        }
        scores_path.parent.mkdir(parents=True, exist_ok=True)
        scores_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def judge_one(job: Any) -> Dict[str, Any]:
        _item_id, item, response = job
        return ev.evaluate_item(
            item=item,
            response=response,
            provider=provider,
            hard_only=False,
            repeats=repeats,
            parse_retries=parse_retries,
        )

    with ThreadPoolExecutor(max_workers=max(1, judge_workers)) as executor:
        futures = {executor.submit(judge_one, job): job for job in jobs}
        for future in as_completed(futures):
            latest = future.result()
            evaluated_items = [item for item in evaluated_items if item.get("item_id") != latest.get("item_id")]
            evaluated_items.append(latest)
            evaluated_items.sort(key=lambda item: int(item.get("line_number") or 0))
            write_scores()
            print(
                f"{response_model}: scored {latest['item_id']} "
                f"IF={latest['summary']['score']} quality={latest['quality'].get('score')}",
                flush=True,
            )
    return write_scores()


def write_run_metadata(
    *,
    run_dir: Path,
    hyperparameters_dir: Path,
    dataset_path: Path,
    selected_path: Path,
    responses_path: Path,
    scores_path: Path,
    args: argparse.Namespace,
    status: str,
    temperature_probe: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    response_parameters = {
        "provider": "openai",
        "api": "responses.create",
        "model": args.response_model,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_output_tokens": args.response_max_output_tokens,
        "reasoning": {"effort": args.reasoning_effort} if args.reasoning_effort else None,
        "workers": args.workers,
        "retries": args.retries,
        "temperature_probe": temperature_probe,
    }
    judge_parameters = {
        "provider": "openai",
        "api": "responses.create",
        "model": args.judge_model,
        "temperature": 0,
        "top_p": 1,
        "max_output_tokens": args.judge_max_output_tokens,
        "response_format": "json_object",
        "repeats": args.repeats,
        "parse_retries": args.parse_retries,
        "judge_workers": args.judge_workers,
    }
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "source_dataset": str(dataset_path),
        "selected_dataset": str(selected_path),
        "responses": str(responses_path),
        "scores": str(scores_path),
        "response_model": args.response_model,
        "judge_model": args.judge_model,
        "response_parameters": response_parameters,
        "judge_parameters": judge_parameters,
        "summary": summary,
        "error": error,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    hyperparameters_dir.mkdir(parents=True, exist_ok=True)
    hyper = {
        "run_name": run_dir.name,
        "record_created_local": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "source_dataset": str(dataset_path),
        "response_generation": response_parameters,
        "judge": judge_parameters,
        "outputs": {
            "selected_dataset": str(selected_path),
            "responses": str(responses_path),
            "scores": str(scores_path),
            "manifest": str(run_dir / "manifest.json"),
        },
        "summary": summary,
        "error": error,
    }
    (hyperparameters_dir / f"{run_dir.name}.json").write_text(
        json.dumps(hyper, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--openai-key-file", type=Path, default=DEFAULT_OPENAI_KEY)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--hyperparameters-dir", type=Path, default=DEFAULT_HYPERPARAMETERS_DIR)
    parser.add_argument("--response-model", default="gpt-5")
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--top-p", type=float, default=1)
    parser.add_argument("--response-max-output-tokens", type=int, default=5000)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--judge-workers", type=int, default=3)
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--parse-retries", type=int, default=2)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--reuse-responses", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--skip-temperature-probe", action="store_true")
    args = parser.parse_args()

    dataset_rows = read_jsonl(args.dataset)
    if args.limit is not None:
        dataset_rows = dataset_rows[: args.limit]

    run_dir = args.run_dir
    selected_path = run_dir / "selected_dataset.jsonl"
    responses_path = run_dir / "responses_gpt5.jsonl"
    scores_path = run_dir / "scores_gpt5_judge_gpt4o.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(selected_path, dataset_rows)

    probe_result: Optional[Dict[str, Any]] = None
    if not args.skip_temperature_probe and not args.reuse_responses:
        client = OpenAI(api_key=read_api_key(args.openai_key_file))
        try:
            probe_result = smoke_temperature_probe(
                client=client,
                item=dataset_rows[0],
                model=args.response_model,
                max_output_tokens=min(args.response_max_output_tokens, 512),
                temperature=args.temperature,
                top_p=args.top_p,
                reasoning_effort=args.reasoning_effort,
            )
            print(f"temperature probe OK: {json.dumps(probe_result, ensure_ascii=False)}", flush=True)
        except Exception as exc:  # pragma: no cover - depends on provider errors.
            status = "blocked_temperature_unsupported" if is_temperature_unsupported(exc) else "blocked_probe_error"
            error = str(exc)
            write_run_metadata(
                run_dir=run_dir,
                hyperparameters_dir=args.hyperparameters_dir,
                dataset_path=args.dataset,
                selected_path=selected_path,
                responses_path=responses_path,
                scores_path=scores_path,
                args=args,
                status=status,
                temperature_probe={"ok": False, "error": error},
                error=error,
            )
            print(json.dumps({"status": status, "error": error}, ensure_ascii=False, indent=2), flush=True)
            return 2

    write_run_metadata(
        run_dir=run_dir,
        hyperparameters_dir=args.hyperparameters_dir,
        dataset_path=args.dataset,
        selected_path=selected_path,
        responses_path=responses_path,
        scores_path=scores_path,
        args=args,
        status="running_generation",
        temperature_probe=probe_result,
    )

    if args.reuse_responses and not responses_path.exists():
        raise FileNotFoundError(f"--reuse-responses requested but {responses_path} does not exist")
    if not args.reuse_responses:
        generate_responses(
            dataset_rows=dataset_rows,
            output_path=responses_path,
            key_file=args.openai_key_file,
            model=args.response_model,
            max_output_tokens=args.response_max_output_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            reasoning_effort=args.reasoning_effort,
            workers=args.workers,
            retries=args.retries,
        )

    if args.generate_only:
        write_run_metadata(
            run_dir=run_dir,
            hyperparameters_dir=args.hyperparameters_dir,
            dataset_path=args.dataset,
            selected_path=selected_path,
            responses_path=responses_path,
            scores_path=scores_path,
            args=args,
            status="generated_only",
            temperature_probe=probe_result,
        )
        return 0

    output = score_responses(
        dataset_path=selected_path,
        responses_path=responses_path,
        scores_path=scores_path,
        openai_key_file=args.openai_key_file,
        response_model=args.response_model,
        judge_model=args.judge_model,
        judge_max_output_tokens=args.judge_max_output_tokens,
        repeats=args.repeats,
        parse_retries=args.parse_retries,
        judge_workers=args.judge_workers,
    )
    write_run_metadata(
        run_dir=run_dir,
        hyperparameters_dir=args.hyperparameters_dir,
        dataset_path=args.dataset,
        selected_path=selected_path,
        responses_path=responses_path,
        scores_path=scores_path,
        args=args,
        status="completed",
        temperature_probe=probe_result,
        summary=output["summary"],
    )
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
