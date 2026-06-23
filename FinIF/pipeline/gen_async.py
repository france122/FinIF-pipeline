#!/usr/bin/env python3
"""
FinIF Benchmark — Async 并行回复生成
两个模型同时跑，每个模型 20 并发
"""
import json, os, sys, time, asyncio, aiofiles
from openai import AsyncOpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE_URL = "https://api.deepseek.com"

SF_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SF_BASE_URL = "https://api.siliconflow.cn/v1"

ds_client = AsyncOpenAI(api_key=DS_API_KEY, base_url=DS_BASE_URL)
sf_client = AsyncOpenAI(api_key=SF_API_KEY, base_url=SF_BASE_URL)

MODEL_CONFIG = {
    "ds-v4-flash": {"api_model": "deepseek-v4-flash", "max_tokens": 8192, "thinking": False, "client": "ds"},
    "ds-v4-pro":   {"api_model": "deepseek-v4-pro",   "max_tokens": 8192, "thinking": False, "client": "ds"},
    "ds-v4-flash-thinking": {"api_model": "deepseek-v4-flash", "max_tokens": 16384, "thinking": True, "reasoning_effort": "high", "client": "ds"},
    "ds-v4-pro-thinking":   {"api_model": "deepseek-v4-pro",   "max_tokens": 16384, "thinking": True, "reasoning_effort": "high", "client": "ds"},
    "qwen3-8b": {"api_model": "Qwen/Qwen3-8B", "max_tokens": 8192, "thinking": False, "client": "sf", "enable_thinking": False},
}

CLIENTS = {"ds": ds_client, "sf": sf_client}

CONCURRENCY = 20  # per model


async def gen_one(prompt, model_key, sem):
    cfg = MODEL_CONFIG[model_key]
    api_client = CLIENTS[cfg["client"]]
    kwargs = {
        "model": cfg["api_model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if cfg.get("thinking"):
        kwargs["extra_body"] = {
            "thinking": {"type": "enabled"},
            "reasoning_effort": cfg.get("reasoning_effort", "high"),
            "max_completion_tokens": cfg["max_tokens"],
        }
    else:
        kwargs["max_tokens"] = cfg["max_tokens"]
        kwargs["temperature"] = 0.7

    if "enable_thinking" in cfg:
        kwargs.setdefault("extra_body", {})["enable_thinking"] = cfg["enable_thinking"]

    async with sem:
        for attempt in range(3):
            try:
                resp = await api_client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                if content:
                    return content
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                if "rate" in str(e).lower() or "429" in str(e) or "403" in str(e):
                    await asyncio.sleep(2 ** attempt)
                    continue
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                raise
    return None


def load_benchmark():
    path = os.path.join(SCRIPT_DIR, "benchmark", "benchmark_all.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["cases"]


def load_existing(out_path):
    existing = set()
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing.add(json.loads(line)["case_id"])
    return existing


async def gen_model(model_key, cases, out_path, sem):
    existing = load_existing(out_path)
    todo = [c for c in cases if c["case_id"] not in existing]
    print(f"  {model_key}: {len(existing)} done, {len(todo)} todo")
    if not todo:
        return

    done = 0
    failed = 0
    total = len(todo)
    lock = asyncio.Lock()

    async def process(case):
        nonlocal done, failed
        try:
            resp = await gen_one(case["prompt"], model_key, sem)
            if resp:
                record = {
                    "case_id": case["case_id"],
                    "model": model_key,
                    "response": resp,
                    "context": case.get("context", ""),
                }
                async with lock:
                    async with aiofiles.open(out_path, "a") as f:
                        await f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    done += 1
                    print(f"  [{done+failed}/{total}] {model_key} {case['case_id']} OK ({len(resp)} chars)", flush=True)
            else:
                async with lock:
                    failed += 1
                    print(f"  [{done+failed}/{total}] {model_key} {case['case_id']} FAILED: None", flush=True)
        except Exception as e:
            async with lock:
                failed += 1
                print(f"  [{done+failed}/{total}] {model_key} {case['case_id']} FAILED: {e}", flush=True)

    tasks = [process(c) for c in todo]
    await asyncio.gather(*tasks)
    print(f"  {model_key}: {done} OK, {failed} failed")


async def main():
    cases = load_benchmark()
    resp_dir = os.path.join(SCRIPT_DIR, "benchmark", "responses")
    os.makedirs(resp_dir, exist_ok=True)

    model_keys = sys.argv[1:] if len(sys.argv) > 1 else ["ds-v4-flash", "ds-v4-pro"]
    for mk in model_keys:
        if mk not in MODEL_CONFIG:
            print(f"Unknown model: {mk}, available: {list(MODEL_CONFIG.keys())}")
            sys.exit(1)
    sems = {mk: asyncio.Semaphore(4 if MODEL_CONFIG[mk]["client"] == "sf" else CONCURRENCY) for mk in model_keys}

    print(f"Generating responses for {model_keys}, concurrency={CONCURRENCY}/model")
    t0 = time.time()

    await asyncio.gather(*[
        gen_model(mk, cases, os.path.join(resp_dir, f"responses_{mk}.jsonl"), sems[mk])
        for mk in model_keys
    ])

    elapsed = time.time() - t0
    print(f"\nAll done in {elapsed:.1f}s")

    for mk in model_keys:
        path = os.path.join(resp_dir, f"responses_{mk}.jsonl")
        n = sum(1 for _ in open(path)) if os.path.isfile(path) else 0
        print(f"  {mk}: {n} responses")


if __name__ == "__main__":
    asyncio.run(main())
