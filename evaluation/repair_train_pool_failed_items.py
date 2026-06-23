#!/usr/bin/env python3
"""Repair failed teacher responses using benchmark-aligned judge feedback.

Workflow:
1. Read the full train-pool dataset, full responses, and benchmark-aligned scores.
2. Select only failed items.
3. Ask the teacher model to revise each failed draft using failed-constraint feedback.
4. Re-judge only the repaired subset with the benchmark-aligned judge logic.
5. Merge repaired responses/scores back into the full corpus.
6. Repeat for a bounded number of rounds and export a pass-only teacher corpus.
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

try:
    from . import evaluate_responses as ev
    from . import run_openai_generation_only as gen
    from . import score_train_pool_with_benchmark_judge as judge_mod
except ImportError:  # pragma: no cover
    import evaluate_responses as ev
    import run_openai_generation_only as gen
    import score_train_pool_with_benchmark_judge as judge_mod


DEFAULT_DATASET = Path(
    "outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl"
)
DEFAULT_KEY = Path("key.md")
DEFAULT_OUTPUT_ROOT = Path("outputs/model_runs")
DEFAULT_HYPERPARAMETERS_DIR = Path("outputs/model_runs/hyperparameters")


def load_scores(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def item_is_exact_pass(item: Dict[str, Any]) -> bool:
    summary = item.get("summary") or {}
    total = summary.get("total_constraints")
    decided = summary.get("decided_constraints")
    passed = summary.get("passed_constraints")
    coverage = summary.get("coverage")
    if total is None or decided is None or passed is None:
        return False
    return total == decided == passed and float(coverage or 0) >= 1.0


def failed_results(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [result for result in item.get("results", []) if result.get("status") != "pass"]


def build_repair_prompt(
    dataset_item: Dict[str, Any],
    previous_response: str,
    score_item: Dict[str, Any],
) -> str:
    failures = failed_results(score_item)
    lines = [
        "You are revising a draft answer for a financial instruction-following benchmark.",
        "Return only the corrected final answer. Do not add any preface, explanation, or notes about the revision.",
        "",
        "Your goal is to satisfy the original task prompt and every constraint in it.",
        "The earlier draft failed the checks below. Fix those failures while preserving correct content.",
        "",
        "ORIGINAL TASK PROMPT",
        dataset_item["full_prompt"],
        "",
        "PREVIOUS DRAFT",
        previous_response or "[empty draft]",
        "",
        "FAILED CONSTRAINTS",
    ]
    for idx, result in enumerate(failures, start=1):
        constraint_id = result.get("constraint_id") or f"C{idx}"
        tag = result.get("tag") or "NA"
        check_type = result.get("check_type") or result.get("effective_check_type") or "NA"
        constraint_text = result.get("constraint") or ""
        reason = result.get("reason") or "No reason provided."
        lines.extend(
            [
                f"{idx}. [{constraint_id} | {tag} | {check_type}] {constraint_text}",
                f"   Failure reason: {reason}",
            ]
        )
    lines.extend(
        [
            "",
            "REVISION RULES",
            "- Use only the source materials already present in the original task prompt.",
            "- Keep correct calculations, facts, and structure unless they conflict with a failed constraint.",
            "- Fix formatting, counts, decimals, table structure, labels, citations, decision boundaries, and evidence placement wherever needed.",
            "- Do not mention the failed checks, the judge, or this repair brief.",
            "- Return only the revised final answer.",
        ]
    )
    return "\n".join(lines)


def generate_repair_one(
    client: OpenAI,
    item: Dict[str, Any],
    score_item: Dict[str, Any],
    prior_response: Dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    reasoning_effort: Optional[str],
    round_index: int,
) -> Dict[str, Any]:
    prompt = build_repair_prompt(item, prior_response.get("response") or "", score_item)
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = gen.create_response(
                client,
                model=model,
                prompt=prompt,
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
            )
            return {
                "item_id": item["id"],
                "line_number": item["line_number"],
                "model": model,
                "provider": "openai",
                "api": "responses.create",
                "repair_round": round_index,
                "source_response_id": prior_response.get("response_id"),
                "response_id": getattr(response, "id", None),
                "status": getattr(response, "status", None),
                "incomplete_details": gen.jsonable(getattr(response, "incomplete_details", None)),
                "response": gen.output_text(response),
                "usage": gen.jsonable(getattr(response, "usage", None)),
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
    raise RuntimeError(f"Repair generation failed after retries: {last_error}")


def write_round_manifest(
    path: Path,
    payload: Dict[str, Any],
) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_teacher_corpus(
    *,
    dataset_rows: List[Dict[str, Any]],
    response_map: Dict[str, Dict[str, Any]],
    score_map: Dict[str, Dict[str, Any]],
    output_dir: Path,
    teacher_model: str,
) -> Dict[str, Any]:
    passed_rows: List[Dict[str, Any]] = []
    failed_rows: List[Dict[str, Any]] = []
    for row in dataset_rows:
        item_id = str(row["id"])
        response_row = response_map[item_id]
        score_item = score_map[item_id]
        enriched = dict(row)
        enriched["teacher_response"] = response_row.get("response") or ""
        enriched["teacher_response_model"] = teacher_model
        enriched["teacher_response_status"] = response_row.get("status")
        enriched["teacher_exact_pass"] = item_is_exact_pass(score_item)
        enriched["teacher_score_summary"] = score_item.get("summary")
        enriched["teacher_quality"] = score_item.get("quality")
        if enriched["teacher_exact_pass"]:
            passed_rows.append(enriched)
        else:
            enriched["teacher_failed_constraints"] = failed_results(score_item)
            failed_rows.append(enriched)

    pass_path = output_dir / "teacher_pass_only.jsonl"
    fail_path = output_dir / "teacher_fail_remaining.jsonl"
    gen.write_jsonl(pass_path, passed_rows)
    gen.write_jsonl(fail_path, failed_rows)
    summary = {
        "teacher_model": teacher_model,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed_count": len(passed_rows),
        "failed_count": len(failed_rows),
        "total_count": len(dataset_rows),
        "pass_rate": (len(passed_rows) / len(dataset_rows)) if dataset_rows else 0,
        "pass_only_path": str(pass_path),
        "fail_remaining_path": str(fail_path),
    }
    (output_dir / "teacher_corpus_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--hyperparameters-dir", type=Path, default=DEFAULT_HYPERPARAMETERS_DIR)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--judge-max-output-tokens", type=int, default=2400)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--parse-retries", type=int, default=2)
    parser.add_argument("--judge-workers", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=2)
    args = parser.parse_args()

    dataset_rows = gen.read_jsonl(args.dataset)
    dataset_map = {str(row["id"]): row for row in dataset_rows}
    current_response_map = gen.load_existing(args.responses)
    current_scores_payload = load_scores(args.scores)
    current_score_map = {str(item["item_id"]): item for item in current_scores_payload["items"]}

    missing_responses = [row["id"] for row in dataset_rows if str(row["id"]) not in current_response_map]
    missing_scores = [row["id"] for row in dataset_rows if str(row["id"]) not in current_score_map]
    if missing_responses:
        raise ValueError(f"Missing responses for {len(missing_responses)} items before repair.")
    if missing_scores:
        raise ValueError(f"Missing scores for {len(missing_scores)} items before repair.")

    run_dir = args.output_root / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAI(api_key=gen.read_api_key(args.key_file))
    latest_responses_path = args.responses
    latest_scores_path = args.scores
    round_summaries: List[Dict[str, Any]] = []

    for round_index in range(1, args.max_rounds + 1):
        failed_ids = [row["id"] for row in dataset_rows if not item_is_exact_pass(current_score_map[str(row["id"])])]
        if not failed_ids:
            break

        round_dir = run_dir / f"repair_round_{round_index:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        failed_rows = [dataset_map[str(item_id)] for item_id in failed_ids]
        failed_dataset_path = round_dir / "selected_failed_dataset.jsonl"
        repaired_responses_path = round_dir / f"responses_{args.model.replace('/', '_')}_repair.jsonl"
        subset_scores_path = round_dir / "scores_repaired_subset.json"
        merged_responses_path = round_dir / "responses_merged.jsonl"
        merged_scores_path = round_dir / "scores_merged.json"

        gen.write_jsonl(failed_dataset_path, failed_rows)

        existing_repairs = gen.load_existing(repaired_responses_path)
        repair_output_rows = [existing_repairs[str(row["id"])] for row in failed_rows if str(row["id"]) in existing_repairs]
        todo_rows = [row for row in failed_rows if str(row["id"]) not in existing_repairs]
        print(
            f"repair round {round_index}: {len(failed_rows)} failed items, "
            f"{len(existing_repairs)} existing repairs, {len(todo_rows)} to generate",
            flush=True,
        )

        def one(item: Dict[str, Any]) -> Dict[str, Any]:
            return generate_repair_one(
                client,
                item,
                current_score_map[str(item["id"])],
                current_response_map[str(item["id"])],
                model=args.model,
                max_output_tokens=args.max_output_tokens,
                reasoning_effort=args.reasoning_effort,
                round_index=round_index,
            )

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(one, item): item for item in todo_rows}
            for future in as_completed(futures):
                item = futures[future]
                row = future.result()
                repair_output_rows = [old for old in repair_output_rows if old.get("item_id") != row.get("item_id")]
                repair_output_rows.append(row)
                repair_output_rows.sort(key=lambda r: int(r.get("line_number") or 0))
                gen.write_jsonl(repaired_responses_path, repair_output_rows)
                print(
                    f"repair round {round_index}: revised line {item['line_number']} "
                    f"({len(row.get('response') or '')} chars, status={row.get('status')})",
                    flush=True,
                )

        judged_subset = judge_mod.score_responses(
            dataset_path=failed_dataset_path,
            responses_path=repaired_responses_path,
            scores_path=subset_scores_path,
            openai_key_file=args.key_file,
            judge_model=args.judge_model,
            judge_max_output_tokens=args.judge_max_output_tokens,
            repeats=args.repeats,
            parse_retries=args.parse_retries,
            judge_workers=args.judge_workers,
        )

        repaired_score_map = {str(item["item_id"]): item for item in judged_subset["items"]}
        for item_id, response_row in {str(row["item_id"]): row for row in repair_output_rows}.items():
            current_response_map[item_id] = response_row
        for item_id, score_item in repaired_score_map.items():
            current_score_map[item_id] = score_item

        merged_response_rows = [current_response_map[str(row["id"])] for row in dataset_rows]
        gen.write_jsonl(merged_responses_path, merged_response_rows)

        merged_items = [current_score_map[str(row["id"])] for row in dataset_rows]
        merged_summary = ev.summarize_dataset(merged_items)
        merged_payload = {
            "schema_version": "finif-v2-train-pool-repaired-results-1.0",
            "dataset": str(args.dataset),
            "base_responses": str(latest_responses_path),
            "base_scores": str(latest_scores_path),
            "repair_subset_dataset": str(failed_dataset_path),
            "repair_subset_scores": str(subset_scores_path),
            "repair_round": round_index,
            "judge_model": args.judge_model,
            "judge_protocol": {
                "temperature": 0,
                "top_p": 1,
                "response_format": "json_object",
                "repeats": args.repeats,
                "parse_retries": args.parse_retries,
            },
            "summary": merged_summary,
            "items": merged_items,
        }
        merged_scores_path.write_text(json.dumps(merged_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        failed_after = sum(1 for item in merged_items if not item_is_exact_pass(item))
        round_summary = {
            "round_index": round_index,
            "failed_before": len(failed_rows),
            "failed_after": failed_after,
            "repaired_subset_size": len(repair_output_rows),
            "subset_summary": judged_subset["summary"],
            "merged_summary": merged_summary,
            "paths": {
                "failed_dataset": str(failed_dataset_path),
                "repaired_responses": str(repaired_responses_path),
                "subset_scores": str(subset_scores_path),
                "merged_responses": str(merged_responses_path),
                "merged_scores": str(merged_scores_path),
            },
        }
        round_summaries.append(round_summary)
        write_round_manifest(round_dir / "manifest.json", round_summary)

        latest_responses_path = merged_responses_path
        latest_scores_path = merged_scores_path

    final_response_rows = [current_response_map[str(row["id"])] for row in dataset_rows]
    final_items = [current_score_map[str(row["id"])] for row in dataset_rows]
    final_summary = ev.summarize_dataset(final_items)

    final_responses_path = run_dir / "final_responses.jsonl"
    final_scores_path = run_dir / "final_scores.json"
    gen.write_jsonl(final_responses_path, final_response_rows)
    final_scores_path.write_text(
        json.dumps(
            {
                "schema_version": "finif-v2-train-pool-repaired-results-1.0",
                "dataset": str(args.dataset),
                "responses": str(final_responses_path),
                "summary": final_summary,
                "items": final_items,
                "round_summaries": round_summaries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    teacher_summary = export_teacher_corpus(
        dataset_rows=dataset_rows,
        response_map=current_response_map,
        score_map=current_score_map,
        output_dir=run_dir,
        teacher_model=args.model,
    )

    top_manifest = {
        "run_name": run_dir.name,
        "created_at_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed",
        "source_dataset": str(args.dataset),
        "initial_responses": str(args.responses),
        "initial_scores": str(args.scores),
        "final_responses": str(final_responses_path),
        "final_scores": str(final_scores_path),
        "teacher_corpus_summary": teacher_summary,
        "repair_generation": {
            "provider": "openai",
            "api": "responses.create",
            "model": args.model,
            "temperature": "unsupported/not set",
            "top_p": "not set",
            "max_output_tokens": args.max_output_tokens,
            "reasoning": {"effort": args.reasoning_effort} if args.reasoning_effort else None,
            "workers": args.workers,
            "max_rounds": args.max_rounds,
        },
        "judge": {
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
        },
        "round_summaries": round_summaries,
        "final_summary": final_summary,
    }
    write_round_manifest(run_dir / "manifest.json", top_manifest)

    args.hyperparameters_dir.mkdir(parents=True, exist_ok=True)
    (args.hyperparameters_dir / f"{run_dir.name}.json").write_text(
        json.dumps(top_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"final_summary": final_summary, "teacher_corpus_summary": teacher_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
