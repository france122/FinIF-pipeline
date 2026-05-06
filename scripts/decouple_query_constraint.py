#!/usr/bin/env python3
"""
用 LLM 将 query 中内嵌的约束剥离，产出 base_instruction + extracted constraints。

用法：
  export OPENAI_API_KEY=sk-xxx
  export OPENAI_BASE_URL=https://api.deepseek.com/v1
  python scripts/decouple_query_constraint.py \
    --input  data/query_pool/expansion/new_seed_queries_for_review.json \
    --output data/query_pool/expansion/decoupled_queries.json \
    --model  deepseek-chat
"""
import argparse, json, os, sys, time, urllib.request

SYSTEM_PROMPT = """你是指令遵循数据集的标注专家。将一条金融 query 分解为：
1. base_instruction：完整的任务描述（含所有输入数据、背景材料、计算参数）
2. constraints：仅提取对"输出"的格式/风格/结构要求

## 关键区分

### 属于 base_instruction（必须保留，不可剥离）：
- 任务目的："分析某公司财报""起草一份合同""计算违约概率"
- 输入数据/参数：波动率45%、净利润2000万、债务期限2.7年等——这些是完成任务所需的素材
- 背景上下文：公司名称、行业、市场环境
- 附带的材料/报告原文/对话记录

### 属于 constraints（必须剥离）：
- 输出格式："以JSON格式输出""用Markdown表格""包含代码块"
- 输出长度："不少于8000字""限制在200字以内""3000字深度分析"
- 输出结构："分为N个部分""包含以下章节""按照以下模板"
- 输出风格："以专业分析师口吻""用通俗语言""以财经媒体文章风格"
- 输出内容指定："重点包含以下方面：1)...2)...3)...""必须涵盖XX和YY"
- 精度/展示规则："保留四位小数""以百分比形式展示"
- 禁止项："不准使用列表""避免使用专业术语"
- 排列要求："按重要性从高到低排序"

## 判断原则
问自己：这个要求是在限定"输出长什么样"还是在描述"任务是什么"？前者是约束，后者保留。

## 示例

### 示例1：纯任务（is_bare=true）
输入query：某公司在2018年的净利润为2000万元，2019年的净利润为2500万元。请计算该公司的年均利润增长率。
输出：
{"is_bare":true,"base_instruction":"某公司在2018年的净利润为2000万元，2019年的净利润为2500万元。请计算该公司的年均利润增长率。","constraints":[],"confidence":0.95,"note":"仅含任务描述和输入数据，无输出要求"}

### 示例2：含约束（is_bare=false）
输入query：请撰写一份约3000字的面向投资分析师的专业分析报告，主题为滴滴与美团出行业务成本结构对比分析。采用投行研报的标准格式和写作风格，包含详实的数据支撑和图表分析。
输出：
{"is_bare":false,"base_instruction":"撰写一份面向投资分析师的分析报告，主题为滴滴与美团出行业务成本结构对比分析。","constraints":["报告长度约3000字","采用投行研报的标准格式和写作风格","包含详实的数据支撑和图表分析"],"confidence":0.95,"note":"字数、格式风格、图表要求均为输出约束"}

### 示例3：含约束（is_bare=false）
输入query：以财经媒体专业分析文章的风格，撰写一篇3000字的蔚来汽车2023第四季度财报深度分析。重点包含：1）毛利率改善措施的实施效果；2）BaaS电池租用模式分析；3）研发投入与技术储备。
输出：
{"is_bare":false,"base_instruction":"撰写一篇蔚来汽车2023第四季度财报深度分析，涵盖毛利率改善、BaaS电池租用模式、研发投入与技术储备。","constraints":["以财经媒体专业分析文章的风格撰写","文章长度3000字","重点包含以下方面：1）毛利率改善措施的实施效果；2）BaaS电池租用模式分析；3）研发投入与技术储备"],"confidence":0.9,"note":"风格、字数为输出约束；'重点包含1/2/3'是对输出内容结构的指定，属于约束"}

### 示例4：纯任务（is_bare=true）
输入query：创业板指数连续下跌，跌势持续加剧，这是否意味着创业板的"高成长"光环正在逐渐淡化？请您分析一下这个问题。
输出：
{"is_bare":true,"base_instruction":"创业板指数连续下跌，跌势持续加剧，这是否意味着创业板的"高成长"光环正在逐渐淡化？请您分析一下这个问题。","constraints":[],"confidence":0.95,"note":"纯分析类提问，无任何输出格式或风格要求"}

严格输出 JSON，无其他内容。"""

def call_llm(*, base_url, api_key, model, query, timeout=60):
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({"model": model, "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"分析以下query，分离任务与约束：\n---\n{query[:4000]}\n---"}
    ], "temperature": 0.1, "max_tokens": 2048}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode())
    content = result["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"): content = content[4:]
    return json.loads(content)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1"))
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key: sys.exit(f"错误：请设置 {args.api_key_env}")

    with open(args.input) as f: queries = json.load(f)
    print(f"Loaded {len(queries)} queries")

    done_ids, results = set(), []
    if args.resume and os.path.exists(args.output):
        with open(args.output) as f: results = json.load(f)
        done_ids = {r["query_id"] for r in results}
        print(f"Resume: {len(done_ids)} done")

    for i, q in enumerate(queries):
        if q["query_id"] in done_ids: continue
        print(f"[{i+1}/{len(queries)}] {q['query_id']}...", end=" ", flush=True)
        try:
            r = call_llm(base_url=args.base_url, api_key=api_key, model=args.model, query=q["query_text"])
            entry = {**q, "is_bare": r.get("is_bare"), "base_instruction": r.get("base_instruction", q["query_text"]),
                     "constraints": r.get("constraints", []), "confidence": r.get("confidence", 0), "note": r.get("note", "")}
            print("BARE" if entry["is_bare"] else f"DECOUPLED ({len(entry['constraints'])} constraints)")
        except Exception as e:
            entry = {**q, "is_bare": None, "base_instruction": q["query_text"], "constraints": [], "note": str(e), "error": True}
            print(f"ERROR: {e}")
        results.append(entry)
        if len(results) % 5 == 0:
            with open(args.output, "w") as f: json.dump(results, f, ensure_ascii=False, indent=2)
        time.sleep(args.delay)

    with open(args.output, "w") as f: json.dump(results, f, ensure_ascii=False, indent=2)
    pure = sum(1 for r in results if r.get("is_pure") is True)
    dec = sum(1 for r in results if r.get("is_pure") is False)
    cons = sum(len(r.get("constraints", [])) for r in results)
    print(f"\nDone: {len(results)} total, {pure} pure, {dec} decoupled, {cons} constraints extracted")

if __name__ == "__main__":
    main()
