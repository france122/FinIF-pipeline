#!/usr/bin/env python3
"""第三轮修复：针对前两轮仍失败的样本，排除约束冲突，精准修复"""
import json, asyncio, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import checkers
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com",
)

BASE = os.path.dirname(os.path.abspath(__file__))

SYSTEM = (
    "你是金融文档修复专家。用户会给你一段金融回复和它未通过的约束条件及精确诊断。"
    "你需要对回复做最小化修改使其满足所有约束。\n\n"
    "## 严格禁止的常见错误\n"
    "1. 绝对不要在输出中包含模板变量如 {word}、{first_line}、{last_line}、{min_words} 等\n"
    "2. 如果约束要求JSON格式，整个输出必须是纯JSON（不要混入Markdown格式如**加粗**）\n"
    "3. 如果约束要求\"开头第一个词是X\"，回复必须直接以X开头（可以加粗如**X...**）\n"
    "4. 如果约束要求首行包含某文本，确保第一行自然地包含该文本\n"
    "5. 如果约束要求末行包含某文本（如---），确保最后一行是该文本\n"
    "6. 段落数约束：段落以空行分隔，确保空行数量正确\n"
    "7. 字数约束：严格计算中文字符+英文单词数量\n\n"
    "直接输出修改后的完整回复，不要加任何解释。"
)


def diagnose(checker_name, params, text):
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
    elif checker_name == "check_word_limit":
        cn = len(re.findall(r'[一-鿿]', text))
        en = len(re.findall(r'[a-zA-Z]+', text))
        cur = cn + en
        mx = params.get("max_words", 99999)
        if cur > mx:
            return f"当前{cur}字，上限{mx}字，需删减约{cur-mx}字"
    elif checker_name == "check_paragraph_count":
        paras = [p for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
        cur = len(paras)
        lo = params.get("min_count", 1)
        hi = params.get("max_count")
        if hi and cur > hi:
            return f"当前{cur}个段落，要求{lo}-{hi}个，需合并段落"
        elif cur < lo:
            return f"当前{cur}个段落，要求{lo}-{hi or '∞'}个，需拆分段落（用空行分隔）"
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
        stripped = re.sub(r'^(?:\*{1,2}|#{1,6}\s*)', '', text.strip())
        if not stripped.startswith(word):
            return f"回复必须以「{word}」开头（可加粗），当前开头：「{text.strip()[:30]}」"
    elif checker_name == "check_first_line_format":
        fmt = params.get("format", "bold")
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        first = lines[0] if lines else ""
        fmt_map = {"bold": "**文字**", "heading": "# 文字", "numbered": "1. 文字"}
        return f"首行必须是{fmt_map.get(fmt, fmt)}格式，当前首行：「{first[:50]}」"
    elif checker_name == "check_decimal_places":
        n = params.get("places", 2)
        violations = []
        for m in re.finditer(r'(\d[\d,]*\.\d+)', text):
            dec = m.group(1).split('.')[1]
            if len(dec) != n:
                violations.append(f"{m.group(1)}→需{n}位小数")
        if violations:
            return f"违规数值：{', '.join(violations[:5])}"
    elif checker_name == "check_ordered_list_count":
        items = re.findall(r'^\d+[.、)）]\s', text, re.MULTILINE)
        cur = len(items)
        exact = params.get("exact_count")
        lo = params.get("min_count")
        hi = params.get("max_count")
        if exact:
            return f"需要恰好{exact}个有序列表项，当前{cur}个"
        return f"需要{lo}-{hi}个有序列表项，当前{cur}个"
    elif checker_name == "check_sentence_count":
        sents = re.split(r'[。！？!?]+', text)
        sents = [s.strip() for s in sents if s.strip() and len(s.strip()) > 5]
        mn = params.get("min_count", 1)
        return f"需要至少{mn}个完整句子，当前{len(sents)}个"
    elif checker_name == "check_json_format":
        return "输出必须是合法JSON格式（不能混入Markdown如**加粗**）"
    elif checker_name == "check_section_count":
        mn = params.get("min_sections", 2)
        sections = re.findall(r'^#{1,4}\s', text, re.MULTILINE)
        return f"需要至少{mn}个章节标题，当前{len(sections)}个"
    elif checker_name == "check_heading_depth":
        mn = params.get("min_depth", 2)
        levels = set()
        for line in text.strip().splitlines():
            m = re.match(r'^(#{1,6})\s', line.strip())
            if m:
                levels.add(len(m.group(1)))
        return f"需要至少{mn}层标题层级，当前{len(levels)}层"
    elif checker_name == "check_checkbox_format":
        checks = re.findall(r'^\s*[-*]\s*\[[ xX]\]', text, re.MULTILINE)
        mn = params.get("min_count", 1)
        return f"需要至少{mn}个复选框（- [ ] 或 - [x]），当前{len(checks)}个"
    elif checker_name == "check_forbidden_pattern":
        pattern = params.get("pattern", "")
        return f"输出中不能包含匹配「{pattern}」的内容"
    elif checker_name == "check_conditional_trigger":
        trigger_word = params.get("trigger_word", "")
        required_phrase = params.get("required_phrase", "")
        return f"当出现「{trigger_word}」时，必须同时出现「{required_phrase}」"
    return None


def build_prompt(task):
    lines = ["## 未通过的约束及精确诊断\n"]

    for idx, c in task['hard_fails']:
        tag = c.get('tag', '?')
        desc = c.get('description') or c.get('text_hint') or ''
        checker = c['checker']
        params = c.get('params', {})
        diag = diagnose(checker, params, task['text'])
        lines.append(f"### 约束 [{tag}] (硬约束-程序校验)")
        lines.append(f"- 描述: {desc}")
        lines.append(f"- Checker: {checker}")
        lines.append(f"- 参数: {json.dumps(params, ensure_ascii=False)}")
        if diag:
            lines.append(f"- **诊断: {diag}**")
        lines.append("")

    for idx, c, reason in task['soft_fails']:
        tag = c.get('tag', '?')
        desc = c.get('description') or c.get('text_hint') or ''
        lines.append(f"### 约束 [{tag}] (软约束-LLM评审)")
        lines.append(f"- 描述: {desc}")
        if reason:
            lines.append(f"- **不通过原因: {reason}**")
        lines.append("")

    if task.get('conflict_note'):
        lines.append(f"## 注意\n{task['conflict_note']}\n")

    lines.append("## 所有约束（修改时不要破坏已通过的约束）\n")
    for i, c in enumerate(task['all_constraints']):
        desc = c.get('description') or c.get('text_hint') or c.get('checker', '')
        lines.append(f"{i+1}. [{c.get('tag','?')}] {desc}")
    lines.append("")
    lines.append("## 当前回复（需修改）\n")
    lines.append(task['text'])
    return "\n".join(lines)


async def fix_one(sem, task):
    prompt = build_prompt(task)
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3 if attempt > 0 else 0,
                    max_tokens=8192,
                )
                text = resp.choices[0].message.content
                if text and len(text) > 50:
                    return task['sid'], text
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"  FAILED {task['sid']}: {e}", flush=True)
                    return task['sid'], None
        return task['sid'], None


async def main():
    with open(os.path.join(BASE, 'flash_repair_v2.json')) as f:
        repairs = json.load(f)
    with open(os.path.join(BASE, 'constraint_gen_output_v3.jsonl')) as f:
        all_constraints = {json.loads(l)['sample_id']: json.loads(l) for l in f}
    with open(os.path.join(BASE, 'repair_scores.json')) as f:
        scores = json.load(f)

    old_failed = [r for r in scores['results'] if not r['all_pass']]

    tasks = []
    for r in old_failed:
        sid = r['sample_id']
        text = repairs[sid]
        cons = all_constraints[sid]['sampled_constraints']

        hard_fails = []
        for i, c in enumerate(cons):
            if c['type'] == 'hard':
                fn = getattr(checkers, c['checker'], None)
                if fn and not fn(text, c.get('params')):
                    hard_fails.append((i, c))

        soft_fails_list = []
        for k, v in r['checks'].items():
            if not v.get('pass') and v.get('type') == 'soft':
                idx = int(k[1:])
                soft_fails_list.append((idx, cons[idx], v.get('reason', '')))

        if not hard_fails and not soft_fails_list:
            continue

        checker_set = {c.get('checker', 'soft') for c in cons}
        conflict_checkers = set()
        if 'check_json_format' in checker_set:
            for cw in ['check_first_word', 'check_first_last_line', 'check_first_line_format']:
                if cw in checker_set:
                    conflict_checkers.update({'check_json_format', cw})

        actionable_hard = [(i, c) for i, c in hard_fails if c['checker'] not in conflict_checkers]

        if not actionable_hard and not soft_fails_list:
            continue

        conflict_note = None
        if conflict_checkers:
            conflict_note = (
                "以下约束存在冲突，请优先满足JSON格式约束（F4），"
                f"冲突的约束（{', '.join(conflict_checkers - {'check_json_format'})}）可以忽略。"
            )

        tasks.append({
            'sid': sid,
            'text': text,
            'hard_fails': actionable_hard,
            'soft_fails': soft_fails_list,
            'all_constraints': cons,
            'conflict_note': conflict_note
        })

    print(f"Round 3 tasks: {len(tasks)}", flush=True)

    sem = asyncio.Semaphore(30)
    coros = [fix_one(sem, t) for t in tasks]
    done = 0
    fixes = {}
    for coro in asyncio.as_completed(coros):
        sid, result = await coro
        done += 1
        if result:
            fixes[sid] = result
        if done % 10 == 0 or done == len(tasks):
            print(f"  [{done}/{len(tasks)}] done, {len(fixes)} fixed", flush=True)

    print(f"\nLLM repaired: {len(fixes)}/{len(tasks)}")

    # Merge and verify
    for sid, text in fixes.items():
        repairs[sid] = text

    pass_count = 0
    still_fail = []
    for t in tasks:
        sid = t['sid']
        text = repairs[sid]
        cons = all_constraints[sid]['sampled_constraints']
        fails = []
        for i, c in enumerate(cons):
            if c['type'] == 'hard':
                fn = getattr(checkers, c['checker'], None)
                if fn and not fn(text, c.get('params')):
                    diag = diagnose(c['checker'], c.get('params'), text)
                    fails.append(f"{c.get('tag','?')}({diag})" if diag else c.get('tag','?'))
        if not fails:
            pass_count += 1
        else:
            still_fail.append({'sid': sid, 'fails': fails})

    print(f"\nHard-check after round 3: {pass_count}/{len(tasks)} all-pass")
    if still_fail:
        print(f"Still failing ({len(still_fail)}):")
        for sf in still_fail:
            print(f"  {sf['sid']}: {sf['fails']}")

    with open(os.path.join(BASE, 'flash_repair_v2.json'), 'w') as f:
        json.dump(repairs, f, ensure_ascii=False, indent=2)
    print(f"\n→ flash_repair_v2.json updated ({len(fixes)} entries modified)")


if __name__ == "__main__":
    asyncio.run(main())
