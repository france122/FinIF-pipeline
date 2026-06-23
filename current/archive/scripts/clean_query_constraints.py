#!/usr/bin/env python3
"""
Query 清洗：用 LLM 剥离 query 中的格式/结构类指令。

bench: 清洗 benchmark_all.json 中的 prompt
sft:   清洗 samples_clean_2134.jsonl 中的 query_text
"""
import json, os, re, argparse
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DS_API_KEY, base_url=DS_BASE_URL)

FILTER_KEYWORDS = [
    "表格", "列表", "字数", "段落", "标题", "格式",
    "JSON", "Markdown", "编号", "制表", "清单",
    "引用块", "加粗", "百分号", "饼图",
]

SYSTEM_PROMPT = """你是金融NLP数据清洗员。你的任务是改写query，只保留信息获取需求，删除所有关于输出格式、结构、排版的指令。

需要删除的指令类型：
- 表格/列表/JSON/Markdown等输出格式要求（如"以表格形式""制作表格""用JSON格式输出""用列表列出"）
- 字数/段落/标题/章节等结构要求（如"控制在500字""分3个段落""使用二级标题"）
- 格式动词短语（如"以下列格式输出""以xx格式完成""按照以下结构"）
- 排版要求（如"编号列表""加粗关键词""使用引用块"）

保留的内容：
- 核心信息需求（要什么数据、做什么分析、比较什么）
- 具体数据字段（如"包含收益率、风险指标、持仓占比"）
- 计算/推理任务（如"计算超额收益率""判断是否超买"）
- 分析角度/维度（如"从风险控制角度""对比两只基金"）

改写原则：
- 最小改动，只删格式指令，其余文字尽量保留原样
- 保持query的信息完整性和可读性
- 如果某个子项同时包含格式指令和信息需求（如"制作对比表格，包含收益率和风险指标"），保留信息需求部分（"对比收益率和风险指标"），删除格式部分（"制作表格"）
- 如果整个子项纯粹是格式指令（如"在表格下方注明数据来源"），改为信息需求（"注明数据来源"）
- 不要改变query的金融含义
- 不要添加任何原文没有的内容"""

USER_TEMPLATE = """## 该样本分配的约束（仅供参考，帮助你理解哪些格式要求已移至约束中）
{constraints}

## 原始Query
{query}

请输出JSON（不要包裹在markdown代码块中）：
{{"needs_edit": true/false, "cleaned_query": "修改后的query", "removed": ["被删除的格式指令1", "被删除的格式指令2"]}}

如果query不含任何格式/结构/排版类指令，needs_edit设为false，cleaned_query原样返回query，removed为空数组。"""


def parse_response(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def call_llm(query, constraints_text):
    prompt = USER_TEMPLATE.format(query=query, constraints=constraints_text)
    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4096,
        )
        text = resp.choices[0].message.content
        return parse_response(text)
    except Exception as e:
        return {"error": str(e)}


def strip_constraint_block(prompt):
    return re.sub(r'\n*请在回答时严格遵守以下附加要求[：:].*$', '', prompt, flags=re.DOTALL).rstrip()


def extract_constraint_block(prompt):
    m = re.search(r'(请在回答时严格遵守以下附加要求[：:].*$)', prompt, flags=re.DOTALL)
    return m.group(1) if m else ""


def needs_filter(text):
    return any(kw in text for kw in FILTER_KEYWORDS)


# ── bench ──────────────────────────────────────────────────────


def clean_bench(workers=5):
    bench_path = os.path.join(SCRIPT_DIR, "benchmark_all.json")
    config_path = os.path.join(SCRIPT_DIR, "eval_config_all.json")

    with open(bench_path, encoding="utf-8") as f:
        bench_data = json.load(f)
    cases = bench_data["cases"]

    with open(config_path, encoding="utf-8") as f:
        all_constraints = json.load(f)["constraints"]

    def get_constraints_text(case_id):
        lines = []
        for key, cfg in sorted(all_constraints.items()):
            if key.startswith(case_id + "#") and cfg.get("is_if"):
                desc = cfg.get("description", "")
                lines.append(f"- {desc}")
        return "\n".join(lines) if lines else "(无)"

    tasks = []
    for i, case in enumerate(cases):
        query = strip_constraint_block(case["prompt"])
        if needs_filter(query):
            constraints_text = get_constraints_text(case["case_id"])
            tasks.append((i, case["case_id"], query, constraints_text))

    print(f"Benchmark: {len(cases)} cases, {len(tasks)} need LLM cleaning")

    if not tasks:
        print("No cases need cleaning.")
        return

    results = {}
    done = [0]

    def process(task):
        idx, case_id, query, constraints_text = task
        result = call_llm(query, constraints_text)
        done[0] += 1
        if done[0] % 10 == 0 or done[0] == len(tasks):
            print(f"  [{done[0]}/{len(tasks)}] processed", flush=True)
        return idx, case_id, result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for idx, case_id, result in pool.map(process, tasks):
            results[idx] = (case_id, result)

    edited = 0
    for idx, (case_id, result) in sorted(results.items()):
        if not result or result.get("error"):
            print(f"  ✗ {case_id}: error - {result}")
            continue
        if not result.get("needs_edit"):
            continue

        cleaned = result["cleaned_query"]
        removed = result.get("removed", [])
        constraint_block = extract_constraint_block(cases[idx]["prompt"])

        old_query = strip_constraint_block(cases[idx]["prompt"])
        if cleaned.strip() == old_query.strip():
            continue

        if constraint_block:
            cases[idx]["prompt"] = cleaned.rstrip() + "\n\n" + constraint_block
        else:
            cases[idx]["prompt"] = cleaned

        edited += 1
        print(f"\n  ✓ {case_id}: removed {removed}")
        print(f"    before: {old_query[:100]}...")
        print(f"    after:  {cleaned[:100]}...")

    with open(bench_path, "w", encoding="utf-8") as f:
        json.dump(bench_data, f, ensure_ascii=False, indent=2)

    print(f"\nBenchmark cleaning done: {edited}/{len(tasks)} cases modified → {bench_path}")


# ── sft ────────────────────────────────────────────────────────


def clean_sft(workers=5):
    samples_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_2134.jsonl")
    output_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "samples_clean_v2_2134.jsonl")
    constraint_path = os.path.join(SCRIPT_DIR, "sft_pipeline", "data", "constraint_gen_output_v3.jsonl")

    with open(samples_path, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]

    constraint_map = {}
    if os.path.exists(constraint_path):
        with open(constraint_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    constraint_map[obj["sample_id"]] = obj.get("constraint_text", "")

    tasks = []
    for i, sample in enumerate(samples):
        query = sample.get("query_text", "")
        if needs_filter(query):
            ct = constraint_map.get(sample["sample_id"], "(无)")
            tasks.append((i, sample["sample_id"], query, ct))

    print(f"SFT: {len(samples)} samples, {len(tasks)} need LLM cleaning")

    if not tasks:
        print("No samples need cleaning.")
        return

    results = {}
    done = [0]

    def process(task):
        idx, sid, query, constraints_text = task
        result = call_llm(query, constraints_text)
        done[0] += 1
        if done[0] % 50 == 0 or done[0] == len(tasks):
            print(f"  [{done[0]}/{len(tasks)}] processed", flush=True)
        return idx, sid, result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for idx, sid, result in pool.map(process, tasks):
            results[idx] = (sid, result)

    edited = 0
    for idx, (sid, result) in sorted(results.items()):
        if not result or result.get("error"):
            print(f"  ✗ {sid}: error - {result}")
            continue
        if not result.get("needs_edit"):
            continue

        cleaned = result["cleaned_query"]
        old = samples[idx].get("query_text", "")
        if cleaned.strip() == old.strip():
            continue

        samples[idx]["query_text"] = cleaned
        edited += 1

    with open(output_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\nSFT cleaning done: {edited}/{len(tasks)} samples modified → {output_path}")

    if edited > 0:
        import random
        random.seed(42)
        edited_samples = [(idx, sid, results[idx]) for idx, (sid, r) in results.items()
                          if r and r.get("needs_edit") and r.get("cleaned_query", "").strip() != ""]
        show = random.sample(edited_samples, min(5, len(edited_samples))) if edited_samples else []
        if show:
            print("\n── 抽样展示修改 ──")
            for idx, sid, (_, result) in show:
                print(f"\n  {sid}:")
                print(f"    removed: {result.get('removed', [])}")
                print(f"    cleaned: {result['cleaned_query'][:150]}...")


def main():
    parser = argparse.ArgumentParser(description="Query清洗：剥离格式/约束类指令")
    parser.add_argument("mode", choices=["bench", "sft"])
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "bench":
        clean_bench(args.workers)
    else:
        clean_sft(args.workers)


if __name__ == "__main__":
    main()
