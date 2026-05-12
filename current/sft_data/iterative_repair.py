#!/usr/bin/env python3
"""
迭代修复：对 verify 不通过的样本做第二轮 LLM 修复 + N3 小数位数程序化后处理
- LLM 修复：prompt 包含精确诊断（当前字数/段落数 vs 要求）
- 程序化后处理：仅 N3（小数位数），其余全靠 LLM
- 仍不过的列出来留给人工
"""
import json, asyncio, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checkers
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-07ddf2d18dbd4cd4a98640d03c4b3643",
    base_url="https://api.deepseek.com",
)

BASE = os.path.dirname(os.path.abspath(__file__))


def load_data():
    with open(os.path.join(BASE, "flash_repair_v2.json")) as f:
        repairs = json.load(f)
    with open(os.path.join(BASE, "repair_scores.json")) as f:
        scores = json.load(f)
    with open(os.path.join(BASE, "constraint_gen_output_v3.jsonl")) as f:
        constraints = {json.loads(l)["sample_id"]: json.loads(l) for l in f}
    return repairs, scores, constraints


def diagnose_hard(checker_name, params, text):
    """精确诊断 hard checker 失败原因"""
    params = params or {}
    if checker_name == "check_word_range":
        cn = len(re.findall(r'[一-鿿]', text))
        en = len(re.findall(r'[a-zA-Z]+', text))
        cur = cn + en
        lo, hi = params.get("min_words", 0), params.get("max_words", 99999)
        if cur < lo:
            return f"当前{cur}字，要求{lo}-{hi}字，需增加约{lo-cur}字"
        elif cur > hi:
            return f"当前{cur}字，要求{lo}-{hi}字，需删减约{cur-hi}字"
    elif checker_name == "check_paragraph_count":
        paras = [p for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
        cur = len(paras)
        lo = params.get("min_count", 1)
        hi = params.get("max_count")
        if hi and cur > hi:
            return f"当前{cur}个段落，要求{lo}-{hi}个，需合并一些段落"
        elif cur < lo:
            return f"当前{cur}个段落，要求{lo}-{hi or '∞'}个，需拆分一些段落"
    elif checker_name == "check_first_last_line":
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        first_req = params.get("first_line")
        last_req = params.get("last_line")
        issues = []
        if first_req and (not lines or first_req not in lines[0]):
            issues.append(f"首行必须包含「{first_req}」，当前首行：「{lines[0][:50] if lines else '空'}」")
        if last_req and (not lines or last_req not in lines[-1]):
            issues.append(f"末行必须包含「{last_req}」，当前末行：「{lines[-1][:50] if lines else '空'}」")
        return "；".join(issues) if issues else None
    elif checker_name == "check_first_word":
        word = params.get("word", "")
        if not text.strip().startswith(word):
            return f"回复必须以「{word}」开头，当前开头：「{text.strip()[:30]}」"
    elif checker_name == "check_first_line_format":
        fmt = params.get("format", "bold")
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        first = lines[0] if lines else ""
        fmt_desc = {"bold": "加粗（**文字**）", "heading": "标题（# 文字）", "numbered": "编号（1. 文字）"}
        return f"首行必须是{fmt_desc.get(fmt, fmt)}格式，当前首行：「{first[:50]}」"
    elif checker_name == "check_decimal_places":
        n = params.get("places", 2)
        violations = []
        for m in re.finditer(r'(\d[\d,]*\.\d+)', text):
            dec = m.group(1).split('.')[1]
            if len(dec) != n:
                violations.append(f"{m.group(1)}(当前{len(dec)}位)")
        if violations:
            return f"所有小数必须保留{n}位，违规数值：{', '.join(violations[:5])}"
    elif checker_name == "check_ordered_list_count":
        items = re.findall(r'^\d+[.、)）]\s', text, re.MULTILINE)
        cur = len(items)
        lo = params.get("min_count")
        hi = params.get("max_count")
        exact = params.get("exact_count")
        if exact:
            return f"需要恰好{exact}个有序列表项，当前{cur}个"
        return f"需要{lo}-{hi}个有序列表项，当前{cur}个"
    elif checker_name == "check_json_format":
        return "输出必须是合法JSON格式"
    return None


def postfix_decimal_places(text, params):
    """程序化修复小数位数，跳过标题行和章节编号"""
    n = params.get("places", 2)
    skip_units = r'[年月日号期季届次个条只家人份款项批组套件篇章节段点步]'

    def fix_line(line):
        # 跳过 Markdown 标题行（## 1.1 xxx）
        if re.match(r'^\s*#{1,6}\s', line):
            return line
        # 跳过表格分隔行（|---|---|）
        if re.match(r'^\s*\|[\s\-:]+\|', line):
            return line

        def fix_match(m):
            full = m.group(0)
            num_str = m.group(1)
            unit = m.group(2) or ''
            if re.match(skip_units, unit):
                return full
            # 跳过章节编号（如 1.1、2.3.1 后面紧跟中文或空格+中文）
            end_pos = m.end()
            rest = line[end_pos:end_pos + 5] if end_pos < len(line) else ''
            if re.match(r'^[\s]*[一-鿿]', rest) and len(num_str.split('.')[0]) <= 2 and len(num_str.split('.')[1]) <= 2:
                return full
            integer, dec = num_str.split('.')
            if len(dec) == n:
                return full
            if len(dec) < n:
                dec = dec + '0' * (n - len(dec))
            else:
                dec = dec[:n]
            return integer + '.' + dec + unit

        return re.sub(r'(\d[\d,]*\.\d+)\s*(%|％|[^\d\s,.;:!?。，；：！？\n])?', fix_match, line)

    return '\n'.join(fix_line(line) for line in text.split('\n'))


def apply_n3_postfix(text, constraints_list):
    """只对 N3 小数位数做程序化后处理"""
    for c in constraints_list:
        if c["type"] == "hard" and c.get("checker") == "check_decimal_places":
            text = postfix_decimal_places(text, c.get("params", {}))
    return text


SYSTEM = (
    "你是金融文档修复专家。用户会给你一段金融回复和它未通过的约束条件及精确诊断。"
    "你需要对回复做最小化修改使其满足所有约束。\n"
    "关键要求：\n"
    "- 字数约束：严格计算中文字符+英文单词数量，确保在范围内\n"
    "- 段落数约束：段落以空行分隔，数清楚段落数量\n"
    "- 首尾约束：自然地融入首行/末行要求的文本，保持逻辑连贯\n"
    "- 小数位数约束：所有小数统一保留指定位数\n"
    "- 只修改不合格的部分，保留原文的事实内容和数据\n"
    "直接输出修改后的完整回复，不要加任何解释。"
)


def build_repair_prompt(text, failed_checks, all_constraints):
    lines = ["## 未通过的约束及精确诊断\n"]
    for fc in failed_checks:
        lines.append(f"### 约束 [{fc['tag']}]")
        desc = fc.get("description") or fc.get("text_hint") or ""
        if desc:
            lines.append(f"- 描述: {desc}")
        lines.append(f"- Checker: {fc['checker']}")
        lines.append(f"- 参数: {json.dumps(fc['params'], ensure_ascii=False)}")
        if fc.get("diagnostic"):
            lines.append(f"- **精确诊断: {fc['diagnostic']}**")
        lines.append("")

    lines.append("## 所有约束（修改时不要破坏已通过的约束）\n")
    for i, c in enumerate(all_constraints):
        desc = c.get("description") or c.get("text_hint") or c.get("checker", "")
        lines.append(f"{i+1}. [{c['tag']}] {desc}")
    lines.append("")
    lines.append("## 当前回复（需修改）\n")
    lines.append(text)
    return "\n".join(lines)


async def llm_repair(sem, sid, text, failed_checks, all_constraints):
    prompt = build_repair_prompt(text, failed_checks, all_constraints)
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                    max_tokens=8192,
                )
                result = resp.choices[0].message.content
                if result and len(result) > 50:
                    return sid, result
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"  FAILED {sid}: {e}", flush=True)
                    return sid, None
        return sid, None


async def main():
    repairs, scores, constraints = load_data()

    failed = [r for r in scores["results"] if not r["all_pass"]]
    print(f"Total repairs: {len(repairs)}, Failed: {len(failed)}")

    # Build repair tasks
    repair_tasks = []
    for r in failed:
        sid = r["sample_id"]
        text = repairs[sid]
        cons = constraints[sid]["sampled_constraints"]

        failed_checks = []
        for k, v in r["checks"].items():
            if not v.get("pass"):
                idx = int(k[1:])
                c = cons[idx]
                entry = {
                    "tag": c.get("tag", ""),
                    "description": c.get("description", ""),
                    "text_hint": c.get("text_hint", ""),
                    "checker": c.get("checker", "soft_judge"),
                    "params": c.get("params", {}),
                }
                if v.get("type") == "hard":
                    entry["diagnostic"] = diagnose_hard(c["checker"], c.get("params"), text)
                else:
                    entry["diagnostic"] = v.get("reason", "")
                failed_checks.append(entry)

        if failed_checks:
            repair_tasks.append((sid, text, failed_checks, cons))

    print(f"Repair tasks: {len(repair_tasks)}")

    # LLM repair
    sem = asyncio.Semaphore(30)
    coros = [llm_repair(sem, sid, text, fc, cons) for sid, text, fc, cons in repair_tasks]
    done = 0
    llm_fixed = {}
    for coro in asyncio.as_completed(coros):
        sid, result = await coro
        done += 1
        if result:
            llm_fixed[sid] = result
        if done % 10 == 0 or done == len(repair_tasks):
            print(f"  [{done}/{len(repair_tasks)}] LLM repaired", flush=True)

    print(f"LLM repaired: {len(llm_fixed)}/{len(repair_tasks)}")

    # N3 programmatic post-fix on all repaired samples
    n3_count = 0
    for sid in llm_fixed:
        cons = constraints[sid]["sampled_constraints"]
        before = llm_fixed[sid]
        after = apply_n3_postfix(before, cons)
        if after != before:
            n3_count += 1
            llm_fixed[sid] = after
    print(f"N3 post-fixes applied: {n3_count}")

    # Merge back
    for sid, text in llm_fixed.items():
        repairs[sid] = text

    # Hard-check verification
    pass_count = 0
    still_fail = []
    for r in failed:
        sid = r["sample_id"]
        text = repairs[sid]
        cons = constraints[sid]["sampled_constraints"]
        all_ok = True
        fails = []
        for c in cons:
            if c["type"] == "hard":
                fn = getattr(checkers, c["checker"], None)
                if fn and not fn(text, c.get("params")):
                    all_ok = False
                    diag = diagnose_hard(c["checker"], c.get("params"), text)
                    fails.append(f"{c.get('tag')}({diag})" if diag else c.get("tag"))
        if all_ok:
            pass_count += 1
        else:
            still_fail.append({"sid": sid, "tags": fails})

    print(f"\nHard-check after repair: {pass_count}/{len(failed)} all-pass")
    if still_fail:
        print(f"\nStill failing ({len(still_fail)}) — 需人工修复:")
        for sf in still_fail:
            print(f"  {sf['sid']}: {sf['tags']}")

    # Save
    out = os.path.join(BASE, "flash_repair_v2.json")
    with open(out, "w") as f:
        json.dump(repairs, f, ensure_ascii=False, indent=2)
    print(f"\n→ {out} (updated {len(llm_fixed)} entries)")


if __name__ == "__main__":
    asyncio.run(main())
