#!/usr/bin/env python3
"""
FinIF Benchmark 数据质量审核

用法:
  python3 quality_audit.py prepare     # 生成待审核数据 quality_audit_input.jsonl
  python3 quality_audit.py run         # 调用 API 执行审核（需要 OPENAI_API_KEY）
  python3 quality_audit.py report      # 汇总审核结果
"""
import json, os, sys, re
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_PATH = os.path.join(BASE_DIR, "benchmark_all.json")
EVAL_CONFIG_PATH = os.path.join(BASE_DIR, "eval_config_all.json")
INPUT_PATH = os.path.join(BASE_DIR, "quality_review_input.jsonl")
OUTPUT_PATH = os.path.join(BASE_DIR, "quality_audit_output.jsonl")

SYSTEM_PROMPT = r"""你是FinIF benchmark的数据质量审核员。给定一条benchmark数据（case_id + query + 约束列表），执行以下四项检查。

【FinIF双轴评测框架】
FinIF将模型评测拆成两个独立维度分别打分：
- Compliance（遵从性）：指令听没听。格式、篇幅、用词、风格是否按要求输出。标记为 [COMP]。
- Correctness（正确性）：内容对不对。计算结果、数据提取、推导过程是否准确。标记为 [CORR]。
区分方法：约束检查"输出长什么样"→ Compliance，检查"输出算没算对"→ Correctness。
每条数据独立报两个分，汇总时分别呈现。

【约束标签说明】
每条约束标注了分类标签（tag）、类型和所属评测轴：
- F = Format（格式/结构）: F1 章节, F2 列表, F3 表格, F4 JSON, F5 引用块, F6 首尾格式, F7 特殊格式, F8 排序 → COMP
- N = Number（数值约束）: N1 字数, N2 元素计数, N3 精度 → COMP
- L = Linguistic（语言学）: L1 关键词/必含声明, L2 禁止模式, L3 术语控制, L4 金融符号 → COMP
- S = Style（风格）: S1 语气, S2 角色/视角, S3 连贯性, S4 修辞 → COMP
- C = Content（内容）: C1 覆盖度, C2 证据, C3 分析视角, C4 条件/情景, C5 条件触发 → COMP；C6 计算正确性 → CORR
- type: hard = 程序验证, soft = LLM judge
- axis: COMP = 遵从性轴, CORR = 正确性轴
- INV 标记 = 反直觉约束（要求模型违背常规做法，如禁止数字/表格/列表）

【已知互斥对】（同时出现即为冲突）
- 使用表格(F3) ↔ 禁止表格(F3-INV)
- 使用列表(F2) ↔ 禁止列表(F2-INV)
- 术语全称(L3/FS-3) ↔ 通俗语言避免术语(L3/FS-10)
- 禁百分号(L4/FH-8) ↔ 引用具体财务指标百分比
- 禁阿拉伯数字(L2/FH-9) ↔ 需要数值计算或数据提取

────────────────────────────

【检查1：约束矛盾 conflict_check】
逐对检查所有约束，判断是否存在：

(a) 直接矛盾：两条约束逻辑上不可能同时满足
    例：「使用Markdown表格」+「禁止表格」
(b) 资源矛盾：约束组合的最低输出量超出字数上限
    例：要求「4个章节 + 表格 + 引用块」但字数上限仅300字
    估算规则：每个章节≈80-150字，一个表格≈60-100字，一个引用块≈30字
(c) Query-约束冲突：query明确要求计算/提取数值，但约束禁止使用阿拉伯数字或百分号
    例：query要「计算涨跌幅百分比」+ 约束「禁止百分号」→ 这是合法的IF测试（反直觉约束），不算冲突
    注意：反直觉约束(INV)是故意设计的高难度IF测试，仅当约束导致query根本无法完成时才算冲突

无矛盾 → "PASS"
有矛盾 → 冲突对列表

【检查2：Query复杂度 query_complexity】
评估query本身的任务难度（仅看任务指令，不含"附加要求"中的IF约束），1-5分：

1分: 单步提取/复制（从context中找一个值）
2分: 多步提取 + 简单汇总（提取多个值，列表展示）
3分: 需要计算或跨信息整合（计算百分比、对比多来源数据）
4分: 多步计算 + 推理 + 判断（复合计算链 + 趋势判断）
5分: 开放式综合分析（投资建议、风险评估、多维度报告）

低于3分 → query_flag = "TOO_SIMPLE"

【检查3：约束适配度 fitness_check】
检查IF约束对于这条query是否合理：

(a) 字数可行性：query要求的分析工作量（提取N个值 + 计算M步 + 判断K点）在字数限制内是否能完成？
(b) INV约束适配：反直觉约束是否构成有效的IF测试？
    - GOOD: 约束虽然反直觉但不阻止任务完成（如"禁百分号"→可用"百分之五"表达）
    - WARN: 约束使任务几乎不可能完成（如"禁阿拉伯数字"+ 复杂数值计算任务 → 模型基本无法用中文大写完成所有计算）
(c) 格式约束合理性：结构约束是否与query性质匹配？
    - 例：纯计算query强制要求"4个章节"可能导致注水
(d) INV标注验证：标记为[INV]的约束在金融文本场景下是否真的反直觉？
    - 正确INV：禁止表格、禁止列表、禁止百分号、禁止阿拉伯数字、第一人称叙事——这些违背金融文本常规
    - 错误INV：正式书面语、避免投资建议、客观中立——这些是行业常规做法，不应标INV
    若发现INV标注有误，在issues中指出

输出 "GOOD" 或 {"status": "WARN", "issues": [...]}

【检查4：双轴平衡 axis_balance】
检查每条case的Compliance和Correctness约束配比：

(a) 计算 n_comp（COMP约束数）和 n_corr（CORR约束数）
(b) 判断是否合理：
    - BALANCED: n_comp >= 2 且 n_corr >= 0（允许纯Compliance，因为本benchmark侧重IF遵从性测试）
    - WARN_NO_COMP: n_comp == 0（缺乏遵从性约束，不像IF benchmark数据）
    - WARN_COMP_LOW: n_comp == 1（遵从性约束太少，区分度不足）
    - WARN_CORR_HEAVY: n_corr > n_comp（正确性约束多于遵从性，更像QA测试）

────────────────────────────

输出严格JSON，不要输出其他内容：
{
  "case_id": "...",
  "conflict_check": "PASS" | [{"pair": ["Cx#tag","Cy#tag"], "type": "direct|resource|query_conflict", "reason": "..."}],
  "query_complexity": <1-5>,
  "query_flag": "OK" | "TOO_SIMPLE",
  "fitness_check": "GOOD" | {"status": "WARN", "issues": ["..."]},
  "axis_balance": {"n_comp": <int>, "n_corr": <int>, "status": "BALANCED|WARN_NO_COMP|WARN_COMP_LOW|WARN_CORR_HEAVY"}
}"""


def extract_query(prompt, context):
    """Extract the query portion (without context) from the full prompt."""
    if context and prompt.startswith(context):
        return prompt[len(context):].strip()
    markers = ["请基于", "请根据", "请你", "请从", "请完成", "请对", "请分析", "请审查", "请撰写"]
    best = -1
    for m in markers:
        pos = prompt.rfind(m)
        if pos > best:
            best = pos
    return prompt[best:].strip() if best >= 0 else prompt[-800:].strip()


def format_constraint(key, c):
    """Format a single constraint for the audit prompt."""
    tag = c.get("tag", "?")
    tag_name = c.get("tag_name", "")
    tp = c["type"]
    is_if = c.get("is_if", True)
    checker = c.get("checker", "judge")
    desc = c.get("description", "")

    inv = ""
    if checker in ("check_no_table", "check_no_list", "check_first_person",
                    "check_no_percent", "check_no_arabic_numerals"):
        inv = " [INV]"
    INV_PATTERNS = ["禁止表格", "禁止列表", "禁止百分号", "禁止阿拉伯数字",
                    "不得使用任何表格", "不得使用任何列表", "不得出现百分号",
                    "不得出现阿拉伯数字", "第一人称"]
    if not inv and any(p in desc for p in INV_PATTERNS):
        inv = " [INV]"

    axis = "COMP" if is_if else "CORR"
    params_str = ""
    if c.get("params"):
        p = c["params"]
        parts = []
        for k, v in p.items():
            if isinstance(v, (dict, list)) and len(str(v)) > 60:
                parts.append(f"{k}=...")
            else:
                parts.append(f"{k}={v}")
        params_str = f" ({', '.join(parts)})"

    return f"  {key} [{tag}/{tag_name}] {tp}/{axis}{inv}: {desc}{params_str}"


def prepare():
    """Prepare audit input data."""
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    with open(EVAL_CONFIG_PATH, encoding="utf-8") as f:
        constraints = json.load(f)["constraints"]

    case_map = {}
    for k, v in constraints.items():
        cid = k.split("#")[0]
        case_map.setdefault(cid, []).append((k, v))

    items = []
    for c in cases:
        cid = c["case_id"]
        context = c.get("context", "")
        query = extract_query(c["prompt"], context)
        cs = case_map.get(cid, [])

        constraint_lines = []
        for k, v in sorted(cs, key=lambda x: x[0]):
            constraint_lines.append(format_constraint(k, v))

        user_msg = f"""case_id: {cid}

【Query】
{query}

【约束列表】（共{len(cs)}条）
{chr(10).join(constraint_lines)}"""

        items.append({
            "case_id": cid,
            "system": SYSTEM_PROMPT,
            "user": user_msg,
            "n_constraints": len(cs),
        })

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Prepared {len(items)} audit tasks → {INPUT_PATH}")

    # Show a sample
    print(f"\n=== Sample: {items[0]['case_id']} ===")
    print(items[0]["user"][:600])
    print("...")


def run():
    """Run audit via OpenAI-compatible API."""
    try:
        from openai import OpenAI
    except ImportError:
        print("pip install openai")
        return

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DS_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("DS_BASE_URL")
    model = os.environ.get("AUDIT_MODEL", "deepseek-chat")

    if not api_key:
        print("Set OPENAI_API_KEY or DS_API_KEY")
        return

    client = OpenAI(api_key=api_key, base_url=base_url)

    with open(INPUT_PATH, encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    done = set()
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    done.add(r.get("case_id", ""))
        print(f"Resuming: {len(done)} already done")

    remaining = [t for t in tasks if t["case_id"] not in done]
    print(f"Running {len(remaining)} tasks (model={model})...")

    with open(OUTPUT_PATH, "a", encoding="utf-8") as fout:
        for i, task in enumerate(remaining):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": task["system"]},
                        {"role": "user", "content": task["user"]},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                )
                content = resp.choices[0].message.content.strip()
                # Extract JSON from response
                m = re.search(r'\{[\s\S]*\}', content)
                if m:
                    result = json.loads(m.group())
                else:
                    result = {"case_id": task["case_id"], "error": "no JSON", "raw": content}
            except Exception as e:
                result = {"case_id": task["case_id"], "error": str(e)}

            result["case_id"] = task["case_id"]
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")
            fout.flush()

            status = "OK"
            if result.get("query_flag") == "TOO_SIMPLE":
                status = "TOO_SIMPLE"
            if result.get("conflict_check") != "PASS" and result.get("conflict_check"):
                status = "CONFLICT"
            if isinstance(result.get("fitness_check"), dict):
                status += "+WARN"

            print(f"  [{i+1}/{len(remaining)}] {task['case_id']}: {status}")

    print(f"\nDone → {OUTPUT_PATH}")


def report():
    """Summarize audit results."""
    if not os.path.exists(OUTPUT_PATH):
        print(f"Not found: {OUTPUT_PATH}")
        return

    with open(OUTPUT_PATH, encoding="utf-8") as f:
        results = [json.loads(line) for line in f if line.strip()]

    total = len(results)
    errors = [r for r in results if r.get("error")]
    conflicts = [r for r in results if r.get("conflict_check") not in ("PASS", None) and isinstance(r.get("conflict_check"), list)]
    too_simple = [r for r in results if r.get("query_flag") == "TOO_SIMPLE"]
    warns = [r for r in results if isinstance(r.get("fitness_check"), dict)]
    axis_warns = [r for r in results if isinstance(r.get("axis_balance"), dict) and r["axis_balance"].get("status", "").startswith("WARN")]
    clean = total - len(errors) - len(conflicts) - len(too_simple) - len(warns) - len(axis_warns)
    # Deduplicate: some cases may have multiple flags
    flagged_ids = set()
    for r in errors + conflicts + too_simple + warns + axis_warns:
        flagged_ids.add(r.get("case_id", ""))
    clean = total - len(flagged_ids)

    print(f"=== Quality Audit Report ({total} cases) ===\n")
    print(f"  PASS (clean):    {clean}")
    print(f"  CONFLICT:        {len(conflicts)}")
    print(f"  TOO_SIMPLE:      {len(too_simple)}")
    print(f"  WARN (fitness):  {len(warns)}")
    print(f"  WARN (axis):     {len(axis_warns)}")
    print(f"  ERROR:           {len(errors)}")

    # Complexity distribution
    complexity = Counter()
    for r in results:
        c = r.get("query_complexity")
        if c:
            complexity[c] += 1
    print(f"\nQuery Complexity Distribution:")
    for level in sorted(complexity):
        bar = "█" * complexity[level]
        print(f"  {level}: {complexity[level]:>3} {bar}")

    # List conflicts
    if conflicts:
        print(f"\n--- CONFLICTS ({len(conflicts)}) ---")
        for r in conflicts:
            print(f"\n  {r['case_id']}:")
            for pair in r["conflict_check"]:
                if isinstance(pair, dict):
                    print(f"    {pair.get('pair',[])} [{pair.get('type','')}]: {pair.get('reason','')}")

    # List TOO_SIMPLE
    if too_simple:
        print(f"\n--- TOO_SIMPLE ({len(too_simple)}) ---")
        for r in too_simple:
            print(f"  {r['case_id']}: complexity={r.get('query_complexity')}")

    # List WARN
    if warns:
        print(f"\n--- FITNESS WARNINGS ({len(warns)}) ---")
        for r in warns:
            fc = r["fitness_check"]
            issues = fc.get("issues", []) if isinstance(fc, dict) else []
            print(f"  {r['case_id']}: {'; '.join(issues)}")

    # List axis balance warnings
    if axis_warns:
        print(f"\n--- AXIS BALANCE WARNINGS ({len(axis_warns)}) ---")
        for r in axis_warns:
            ab = r["axis_balance"]
            print(f"  {r['case_id']}: {ab.get('status','')} (COMP={ab.get('n_comp',0)}, CORR={ab.get('n_corr',0)})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 quality_audit.py [prepare|run|report]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare()
    elif cmd == "run":
        run()
    elif cmd == "report":
        report()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
