#!/usr/bin/env python3
"""Score SFT Qwen responses on benchmark307 with GPT-4o judge."""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_responses as ev

DATASET = Path("outputs/benchmark/finif_v2_gpt55_targeted_benchmark307_20260616.jsonl")
RESPONSES = Path("outputs/model_runs/sft_qwen_benchmark307_20260617/responses_sft_qwen_standardized.jsonl")
SCORES_OUT = Path("outputs/model_runs/sft_qwen_benchmark307_20260617/scores_sft_qwen_benchmark307_judge_gpt4o.json")
KEY_FILE = Path("key.md")

JUDGE_MODEL = "gpt-4o"
JUDGE_MAX_TOKENS = 2400
REPEATS = 1
PARSE_RETRIES = 3
WORKERS = 1


def read_api_key(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    if match:
        return match.group(0)
    raise ValueError(f"No API key in {path}")


def output_text(response) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text:
        return text
    parts = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            piece = getattr(content, "text", None)
            if piece:
                parts.append(piece)
    return "".join(parts)


def create_json_response(client, model, instructions, prompt, max_output_tokens):
    kwargs = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "temperature": 0,
        "top_p": 1,
        "text": {"format": {"type": "json_object"}},
    }
    for attempt in range(4):
        try:
            return client.responses.create(**kwargs)
        except Exception as exc:
            error_text = str(exc).lower()
            if "text" in kwargs:
                fallback = dict(kwargs)
                fallback.pop("text", None)
                try:
                    return client.responses.create(**fallback)
                except Exception as fb_exc:
                    error_text = str(fb_exc).lower()
                    exc = fb_exc
            if any(t in error_text for t in ("rate", "429", "timeout", "temporarily", "overload")):
                wait = min(30, 2 ** attempt)
                print(f"  [retry {attempt+1}] rate limit, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("create_json_response exhausted retries")


class OpenAIJudgeProvider(ev.JudgeProvider):
    name = "openai"

    def __init__(self, client, model, max_output_tokens):
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.name = f"openai:{model}"

    def judge(self, request, system_prompt):
        resp = create_json_response(
            self.client, self.model, system_prompt, request.prompt,
            self.max_output_tokens,
        )
        return output_text(resp)


def main():
    api_key = read_api_key(KEY_FILE)
    client = OpenAI(api_key=api_key)
    provider = OpenAIJudgeProvider(client, JUDGE_MODEL, JUDGE_MAX_TOKENS)

    dataset = ev.load_dataset(DATASET)  # dict: item_id -> item
    responses = ev.load_responses(RESPONSES)  # dict: item_id -> response_text

    evaluated = []
    missing = []
    items_list = list(dataset.items())  # [(item_id, item_dict), ...]
    total = len(items_list)

    def process_item(item_id, item):
        resp_text = responses.get(item_id)
        if resp_text is None:
            return item_id, None, "missing"
        result = ev.evaluate_item(item, resp_text, provider, hard_only=False, repeats=REPEATS, parse_retries=PARSE_RETRIES)
        return item_id, result, "ok"

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(process_item, iid, item): iid for iid, item in items_list}
        for future in as_completed(futures):
            item_id, result, status = future.result()
            done += 1
            if status == "missing":
                missing.append(item_id)
                print(f"[{done}/{total}] {item_id}: MISSING")
            else:
                s = result.get("summary", {})
                passed = s.get("passed_constraints", 0)
                t = s.get("total_constraints", 0)
                print(f"[{done}/{total}] {item_id}: {passed}/{t}")
                evaluated.append(result)

    summary = ev.summarize_dataset(evaluated)
    payload = {
        "schema_version": "finif-v2-sft-qwen-benchmark307-results-1.0",
        "created_at": datetime.now().isoformat(),
        "dataset": str(DATASET),
        "responses": str(RESPONSES),
        "model": "sft-qwen3.5-4b",
        "judge_model": JUDGE_MODEL,
        "judge_provider": f"openai:{JUDGE_MODEL}",
        "summary": summary,
        "missing_responses": missing,
        "items": evaluated,
    }

    SCORES_OUT.parent.mkdir(parents=True, exist_ok=True)
    SCORES_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {SCORES_OUT}")
    print(f"Items: {len(evaluated)}, Missing: {len(missing)}")
    print(f"ISR: {summary.get('exact_item_pass_rate', 0)*100:.2f}%")
    print(f"Micro IF: {summary.get('micro_if_score', 0)*100:.2f}%")
    print(f"Quality: {summary.get('quality_mean_0_10', 'N/A')}")


if __name__ == "__main__":
    main()
