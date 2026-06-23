#!/usr/bin/env python3
"""Score train-pool responses with the same judge logic used by FinIF-Test.

This wrapper intentionally reuses:
- `evaluation/evaluate_responses.py` item-batched evaluator
- the same OpenAI GPT-4o judge route
- temperature=0 / top_p=1 / json_object format
- repeats=1 / parse_retries=2
- the same strict exact-pass definition from `summary.exact_item_pass_rate`

It exists to keep teacher-data filtering aligned with benchmark scoring.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

try:
    from . import evaluate_responses as ev
except ImportError:  # pragma: no cover
    import evaluate_responses as ev


DEFAULT_DATASET = Path(
    "outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl"
)
DEFAULT_OPENAI_KEY = Path("key.md")
DEFAULT_RUN_ROOT = Path("outputs/model_runs/train_pool_scoring")
DEFAULT_HYPERPARAMETERS_DIR = Path("outputs/model_runs/hyperparameters")


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if match:
        return match.group(0)
    raise ValueError(f"No OpenAI API key found in {path}")


def output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text:
        return text
    parts: List[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            piece = getattr(content, "text", None)
            if piece:
                parts.append(piece)
    return "".join(parts)


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
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            return client.responses.create(**kwargs)
        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()
            if "text" in kwargs:
                fallback_kwargs = dict(kwargs)
                fallback_kwargs.pop("text", None)
                try:
                    return client.responses.create(**fallback_kwargs)
                except Exception as fallback_exc:
                    last_error = fallback_exc
                    error_text = str(fallback_exc).lower()
            if any(token in error_text for token in ("rate", "429", "timeout", "temporarily", "overload")):
                time.sleep(min(30, 2 ** attempt))
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("create_json_response failed without an explicit exception")


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


def item_is_fully_decided(item: Dict[str, Any]) -> bool:
    summary = item.get("summary") or {}
    total = summary.get("total_constraints")
    decided = summary.get("decided_constraints")
    coverage = summary.get("coverage")
    return (
        isinstance(total, int)
        and isinstance(decided, int)
        and total == decided
        and float(coverage or 0) >= 1.0
    )


def load_existing_scored_items(scores_path: Path) -> Dict[str, Dict[str, Any]]:
    if not scores_path.exists():
        return {}
    try:
        payload = json.loads(scores_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items")
    if not isinstance(items, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for item in items:
        item_id = str(item.get("item_id") or "")
        if item_id:
            out[item_id] = item
    return out


def build_output_payload(
    *,
    dataset_path: Path,
    responses_path: Path,
    judge_model: str,
    judge_max_output_tokens: int,
    repeats: int,
    parse_retries: int,
    missing: List[str],
    evaluated_items: List[Dict[str, Any]],
    status: str,
) -> Dict[str, Any]:
    return {
        "schema_version": "finif-v2-train-pool-benchmark-aligned-results-1.0",
        "status": status,
        "dataset": str(dataset_path),
        "responses": str(responses_path),
        "judge_model": judge_model,
        "judge_provider": f"openai:{judge_model}",
        "judge_temperature_policy": 0,
        "judge_top_p": 1,
        "judge_max_output_tokens": judge_max_output_tokens,
        "repeats": repeats,
        "parse_retries": parse_retries,
        "summary": ev.summarize_dataset(evaluated_items),
        "missing_responses": missing,
        "items": evaluated_items,
        "alignment_note": "Judge logic aligned to current FinIF-Test benchmark evaluator and GPT-4o judge settings.",
    }


def score_responses(
    *,
    dataset_path: Path,
    responses_path: Path,
    scores_path: Path,
    openai_key_file: Path,
    judge_model: str,
    judge_max_output_tokens: int,
    repeats: int,
    parse_retries: int,
    judge_workers: int,
    resume: bool,
) -> Dict[str, Any]:
    dataset = ev.load_dataset(dataset_path)
    responses = ev.load_responses(responses_path)
    api_key = read_api_key(openai_key_file)
    existing_scored = load_existing_scored_items(scores_path) if resume else {}

    evaluated_items_map: Dict[str, Dict[str, Any]] = {}
    for item_id, item in existing_scored.items():
        if item_is_fully_decided(item):
            evaluated_items_map[item_id] = item
    missing = []
    jobs = []
    for item_id, item in sorted(dataset.items(), key=lambda pair: pair[1].get("_line_number", 0)):
        if item_id in evaluated_items_map:
            continue
        response = ev.response_for_item(item, responses)
        if response is None:
            missing.append(item_id)
            continue
        jobs.append((item_id, item, response))

    def judge_one(job: Any) -> Dict[str, Any]:
        _item_id, item, response = job
        provider = OpenAIJudgeProvider(
            OpenAI(api_key=api_key),
            judge_model,
            judge_max_output_tokens,
        )
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
            evaluated_items_map[str(latest.get("item_id"))] = latest
            evaluated_items = sorted(
                evaluated_items_map.values(),
                key=lambda item: int(item.get("line_number") or 0),
            )
            partial_output = build_output_payload(
                dataset_path=dataset_path,
                responses_path=responses_path,
                judge_model=judge_model,
                judge_max_output_tokens=judge_max_output_tokens,
                repeats=repeats,
                parse_retries=parse_retries,
                missing=missing,
                evaluated_items=evaluated_items,
                status="running",
            )
            scores_path.parent.mkdir(parents=True, exist_ok=True)
            scores_path.write_text(json.dumps(partial_output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                f"judge progress: {len(evaluated_items_map)}/{len(dataset)} "
                f"(line {latest.get('line_number')}, item_id={latest.get('item_id')})",
                flush=True,
            )
    evaluated_items = sorted(
        evaluated_items_map.values(),
        key=lambda item: int(item.get("line_number") or 0),
    )
    output = build_output_payload(
        dataset_path=dataset_path,
        responses_path=responses_path,
        judge_model=judge_model,
        judge_max_output_tokens=judge_max_output_tokens,
        repeats=repeats,
        parse_retries=parse_retries,
        missing=missing,
        evaluated_items=evaluated_items,
        status="completed",
    )
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_run_metadata(
    *,
    run_dir: Path,
    hyperparameters_dir: Path,
    dataset_path: Path,
    responses_path: Path,
    scores_path: Path,
    args: argparse.Namespace,
    summary: Dict[str, Any],
) -> None:
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
        "evaluator_script": "evaluation/evaluate_responses.py",
        "strict_pass_metric": "summary.exact_item_pass_rate",
        "selection_rule": "teacher sample usable only if every IF constraint passes",
    }
    manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "scored",
        "source_dataset": str(dataset_path),
        "responses": str(responses_path),
        "scores": str(scores_path),
        "judge_parameters": judge_parameters,
        "summary": summary,
        "alignment_note": "This train-pool run is benchmark-aligned by construction.",
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    hyperparameters_dir.mkdir(parents=True, exist_ok=True)
    hyper = {
        "run_name": run_dir.name,
        "record_created_local": datetime.now().strftime("%Y-%m-%d"),
        "status": "scored",
        "source_dataset": str(dataset_path),
        "judge": judge_parameters,
        "outputs": {
            "responses": str(responses_path),
            "scores": str(scores_path),
            "manifest": str(run_dir / "manifest.json"),
        },
        "summary": summary,
        "alignment_note": "Judge logic intentionally matches current hard300 benchmark protocol.",
    }
    (hyperparameters_dir / f"{run_dir.name}.json").write_text(
        json.dumps(hyper, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--openai-key-file", type=Path, default=DEFAULT_OPENAI_KEY)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--hyperparameters-dir", type=Path, default=DEFAULT_HYPERPARAMETERS_DIR)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--parse-retries", type=int, default=2)
    parser.add_argument("--judge-workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_root / args.run_name
    scores_path = run_dir / "scores_benchmark_aligned_judge.json"

    output = score_responses(
        dataset_path=args.dataset,
        responses_path=args.responses,
        scores_path=scores_path,
        openai_key_file=args.openai_key_file,
        judge_model=args.judge_model,
        judge_max_output_tokens=args.judge_max_output_tokens,
        repeats=args.repeats,
        parse_retries=args.parse_retries,
        judge_workers=args.judge_workers,
        resume=args.resume,
    )
    write_run_metadata(
        run_dir=run_dir,
        hyperparameters_dir=args.hyperparameters_dir,
        dataset_path=args.dataset,
        responses_path=args.responses,
        scores_path=scores_path,
        args=args,
        summary=output["summary"],
    )
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
