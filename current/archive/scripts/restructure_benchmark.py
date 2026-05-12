#!/usr/bin/env python3
"""
Benchmark IF 约束重构脚本 v3

去槽位自由采样 + Easy/Hard 分级（3-4 vs 5-6 条 IF 约束）

用法:
  python3 restructure_benchmark.py restore          # 从 .bak 还原原始文件
  python3 restructure_benchmark.py step1            # 生成约束分配
  python3 restructure_benchmark.py step3            # 应用分配，更新文件
  python3 restructure_benchmark.py stats            # 统计约束分布
  python3 restructure_benchmark.py tag              # 打分类标签
"""
import json, os, re, random, sys, shutil
from collections import defaultdict, Counter

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_PATH = os.path.join(BASE_DIR, "benchmark_all.json")
EVAL_CONFIG_PATH = os.path.join(BASE_DIR, "eval_config_all.json")
ASSIGNMENTS_PATH = os.path.join(BASE_DIR, "constraint_assignments.json")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ============================================================
# Constraint Classification
# ============================================================

IF_CHECKERS = {
    "check_word_range", "check_word_limit", "check_json_format",
    "check_section_count", "check_ordered_list_count", "check_qa_format",
    "check_table_sort_alpha", "check_markdown_table", "check_ranking",
    "check_markdown_format", "check_list_format", "check_heading_level",
    "check_forbidden_pattern", "check_first_line_format", "check_blockquote_count",
    "check_checkbox_format", "check_numbered_list", "check_json_structure",
    "check_sentence_count", "check_paragraph_count", "check_heading_depth",
    "check_first_word", "check_code_block", "check_first_last_line",
    "check_no_table", "check_no_list", "check_first_person",
    "check_risk_disclaimer", "check_conditional_trigger", "check_decimal_places",
    "check_currency_format", "check_no_percent", "check_no_arabic_numerals",
    "check_keyword_presence", "check_keyword_absence",
}

CORRECTNESS_CHECKERS = {
    "check_computation_result", "check_value_exact", "check_value_derivation",
    "check_arithmetic_correct", "check_source_fidelity",
}

# ============================================================
# Constraint Pool — Slot 1: Length (pick 1 per case)
# ============================================================
# Each template: {"id", "checker", "tasks", "gen": fn(l1)->(params, text, desc)}

def _gen_word_range(l1):
    ranges = {"T1": [(300,600),(400,700)], "T2": [(500,800),(600,1000)], "T3": [(800,1200),(1000,1500)]}
    r = random.choice(ranges.get(l1, [(500,800)]))
    return {"min_words": r[0], "max_words": r[1]}, f"全文控制在{r[0]}到{r[1]}字之间", f"字数{r[0]}-{r[1]}字"

def _gen_word_limit(l1):
    limits = {"T1": [400,500,600], "T2": [600,800,1000], "T3": [800,1000,1200]}
    n = random.choice(limits.get(l1, [800]))
    return {"max_words": n}, f"回答不超过{n}个字", f"不超过{n}字"

def _gen_sentence_count(l1):
    counts = {"T1": [8,10,12], "T2": [12,15,18], "T3": [15,20,25]}
    n = random.choice(counts.get(l1, [12]))
    return {"min_count": n}, f"回答至少包含{n}个完整句子", f"至少{n}个句子"

def _gen_paragraph_count(l1):
    counts = {"T1": [(3,5),(4,6)], "T2": [(4,6),(5,7)], "T3": [(5,8),(6,9)]}
    r = random.choice(counts.get(l1, [(4,6)]))
    return {"min_count": r[0], "max_count": r[1]}, f"回答分为{r[0]}到{r[1]}个段落", f"{r[0]}-{r[1]}个段落"

def _gen_section_count(l1):
    counts = {"T1": [2,3], "T2": [3,4], "T3": [3,4,5]}
    n = random.choice(counts.get(l1, [3]))
    return {"min_sections": n}, f"至少包含{n}个独立章节（用标题分隔）", f"至少{n}个章节"

def _gen_heading_level(l1):
    n = random.choice([2,3,4])
    return {"level": 2, "min_count": n}, f"使用{n}个二级标题（##）组织内容", f"{n}个二级标题"

def _gen_heading_depth(l1):
    return {"min_depth": 2}, "使用至少两层标题层级（如##和###）", "至少两层标题层级"

def _gen_ordered_list(l1):
    ranges = {"T1": [(3,5),(4,6)], "T2": [(3,6),(4,7)], "T3": [(4,6),(5,8)]}
    r = random.choice(ranges.get(l1, [(3,5)]))
    return {"min_count": r[0], "max_count": r[1]}, f"使用{r[0]}到{r[1]}条有序列表组织要点", f"{r[0]}-{r[1]}条有序列表"

def _gen_markdown_table(l1):
    return None, "使用Markdown表格展示关键数据", "包含Markdown表格"

def _gen_blockquote(l1):
    n = random.choice([2,3])
    return {"min_count": n}, f"使用引用块（>）引用原文关键段落，至少{n}处", f"至少{n}处引用块"

def _gen_no_table(l1):
    return None, "全文不得使用任何表格", "禁止表格"

def _gen_no_list(l1):
    return None, "全文不得使用任何列表（编号列表或项目符号列表），用自然段落表达", "禁止列表"

def _gen_first_last_line(l1):
    variants = [
        ({"last_line": "以上内容仅供参考"}, '最后一行必须是"以上内容仅供参考"', "末行指定文本"),
        ({"last_line": "---"}, '最后一行必须是分隔线"---"', "末行分隔线"),
        ({"first_line": "摘要"}, '首行必须包含"摘要"二字', "首行含摘要"),
    ]
    v = random.choice(variants)
    return v
_FORBIDDEN_VARIANTS = [
    ({"forbidden": ["！", "!"]}, "不要使用感叹号"),
    ({"forbidden": ["投资建议", "建议买入", "建议卖出", "建议持有"]}, "不要给出投资建议"),
    ({"forbidden": ["个人观点", "我认为", "我觉得"]}, "不要使用第一人称主观表述"),
    ({"forbidden": ["（注", "（备注", "注：", "备注："]}, "不要添加注释或备注"),
    ({"forbidden": ["综上所述", "总而言之"]}, '不要使用"综上所述""总而言之"等总结套话'),
    ({"forbidden": ["首先", "其次", "最后"]}, '不要使用"首先、其次、最后"的递进结构'),
]

_FIRST_WORD_VARIANTS = [
    ("总结", '开头第一个词必须是"总结"'),
    ("根据", '开头第一个词必须是"根据"'),
    ("从", '开头第一个词必须是"从"'),
    ("截至", '开头第一个词必须是"截至"'),
]

_CONDITIONAL_TRIGGERS = [
    ({"trigger": "个股", "followup": "风险提示"}, "若提到个股名称，必须附上风险提示"),
    ({"trigger": "涨幅", "followup": "回调"}, "若提到涨幅，必须同时说明回调风险"),
    ({"trigger": "利好", "followup": "风险"}, "若提到利好因素，必须同时指出潜在风险"),
    ({"trigger": "收益", "followup": "风险"}, "若提到收益，必须同时提及对应风险"),
]

def _gen_forbidden(l1):
    v = random.choice(_FORBIDDEN_VARIANTS)
    return v[0], v[1], v[1]

def _gen_first_word(l1):
    v = random.choice(_FIRST_WORD_VARIANTS)
    return {"word": v[0]}, v[1], v[1]

def _gen_first_line_bold(l1):
    return {"format": "bold"}, "首行用加粗文字给出一句话核心结论", "首行加粗总结"

def _gen_first_person(l1):
    return {"forbidden_phrases": ["本报告", "本文", "本分析", "本研究", "报告认为"]}, \
           '以第一人称视角撰写，不要使用"本报告""本文"等表述', "第一人称叙事"

def _gen_risk_disclaimer(l1):
    return {"risk_line": "以上内容仅供参考，不构成投资建议"}, \
           "文末必须包含风险提示声明", "末尾风险提示"

def _gen_conditional_trigger(l1):
    v = random.choice(_CONDITIONAL_TRIGGERS)
    return v[0], v[1], v[1]

def _gen_decimal_places(l1):
    n = random.choice([2, 2, 4])
    return {"places": n}, f"所有数值统一保留{n}位小数", f"数值保留{n}位小数"

def _gen_currency_format(l1):
    variants = [
        ({"unit": "万元", "forbidden_units": []}, '金额统一使用"万元"为单位'),
        ({"unit": "亿元", "forbidden_units": []}, '金额统一使用"亿元"为单位'),
    ]
    v = random.choice(variants)
    return v[0], v[1], v[1]

def _gen_no_percent(l1):
    return None, '全文不得出现百分号（%）符号，百分比用文字表达（如"百分之五"）', "禁止百分号"

def _gen_no_arabic_numerals(l1):
    return None, "全文不得出现阿拉伯数字，所有数字用中文大写表达", "禁止阿拉伯数字"

def _gen_json_format(l1):
    return None, "以JSON格式输出结果，字段名用中文", "JSON格式输出"

def _gen_checkbox(l1):
    return None, "使用Checkbox格式（[x]/[ ]）标记已确认/待确认事项", "Checkbox格式"

def _gen_keyword_presence(l1):
    kw_sets = [
        (["风险", "机遇"], '回答中必须同时包含"风险"和"机遇"两个关键词'),
        (["优势", "劣势"], '回答中必须同时包含"优势"和"劣势"两个关键词'),
        (["短期", "长期"], '回答中必须同时包含"短期"和"长期"两个关键词'),
    ]
    v = random.choice(kw_sets)
    return {"required_keywords": v[0], "match_all": True}, v[1], v[1]


# ============================================================
# Unified Constraint Pool (no slots)
# ============================================================

CONSTRAINT_POOL = [
    # Length
    {"id": "GH-1-range", "type": "hard", "checker": "check_word_range", "tasks": ["T1","T2","T3"], "gen": _gen_word_range},
    {"id": "GH-1-limit", "type": "hard", "checker": "check_word_limit", "tasks": ["T1","T2","T3"], "gen": _gen_word_limit},
    {"id": "GH-2", "type": "hard", "checker": "check_sentence_count", "tasks": ["T1","T2","T3"], "gen": _gen_sentence_count},
    {"id": "GH-3", "type": "hard", "checker": "check_paragraph_count", "tasks": ["T1","T2","T3"], "gen": _gen_paragraph_count},
    # Structure
    {"id": "GH-4", "type": "hard", "checker": "check_section_count", "tasks": ["T1","T2","T3"], "gen": _gen_section_count},
    {"id": "GH-5", "type": "hard", "checker": "check_heading_depth", "tasks": ["T2","T3"], "gen": _gen_heading_depth},
    {"id": "GH-6", "type": "hard", "checker": "check_ordered_list_count", "tasks": ["T1","T2","T3"], "gen": _gen_ordered_list},
    {"id": "GH-7", "type": "hard", "checker": "check_markdown_table", "tasks": ["T1","T2","T3"], "gen": _gen_markdown_table},
    {"id": "GH-hl", "type": "hard", "checker": "check_heading_level", "tasks": ["T2","T3"], "gen": _gen_heading_level},
    {"id": "GH-14", "type": "hard", "checker": "check_first_last_line", "tasks": ["T2","T3"], "gen": _gen_first_last_line},
    {"id": "GH-18", "type": "hard", "checker": "check_no_table", "tasks": ["T1","T2","T3"], "gen": _gen_no_table, "max_uses": 8},
    {"id": "GH-19", "type": "hard", "checker": "check_no_list", "tasks": ["T1","T2","T3"], "gen": _gen_no_list, "max_uses": 8},
    {"id": "GH-bq", "type": "hard", "checker": "check_blockquote_count", "tasks": ["T1","T2"], "gen": _gen_blockquote},
    # Diverse
    {"id": "GH-10", "type": "hard", "checker": "check_forbidden_pattern", "tasks": ["T1","T2","T3"], "gen": _gen_forbidden},
    {"id": "GH-11", "type": "hard", "checker": "check_first_word", "tasks": ["T1","T2","T3"], "gen": _gen_first_word},
    {"id": "GH-20", "type": "hard", "checker": "check_first_person", "tasks": ["T2","T3"], "gen": _gen_first_person, "max_uses": 5},
    {"id": "GH-fl", "type": "hard", "checker": "check_first_line_format", "tasks": ["T1","T2","T3"], "gen": _gen_first_line_bold},
    {"id": "GH-9", "type": "hard", "checker": "check_keyword_presence", "tasks": ["T1","T2","T3"], "gen": _gen_keyword_presence},
    {"id": "GH-8", "type": "hard", "checker": "check_json_format", "tasks": ["T1"], "gen": _gen_json_format, "max_uses": 5},
    {"id": "GH-12", "type": "hard", "checker": "check_checkbox_format", "tasks": ["T3"], "gen": _gen_checkbox, "max_uses": 4},
    {"id": "FH-1", "type": "hard", "checker": "check_risk_disclaimer", "tasks": ["T1","T2","T3"], "gen": _gen_risk_disclaimer},
    {"id": "FH-3", "type": "hard", "checker": "check_conditional_trigger", "tasks": ["T1","T2","T3"], "gen": _gen_conditional_trigger},
    {"id": "FH-4", "type": "hard", "checker": "check_decimal_places", "tasks": ["T1","T2","T3"], "gen": _gen_decimal_places},
    {"id": "FH-5", "type": "hard", "checker": "check_currency_format", "tasks": ["T1","T3"], "gen": _gen_currency_format},
    {"id": "FH-8", "type": "hard", "checker": "check_no_percent", "tasks": ["T1"], "gen": _gen_no_percent, "max_uses": 5},
    {"id": "FH-9", "type": "hard", "checker": "check_no_arabic_numerals", "tasks": ["T2","T3"], "gen": _gen_no_arabic_numerals, "max_uses": 3},
    # Soft
    {"id": "GS-1", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "先给出结论，再展开分析过程",
     "rubric": "检查输出是否在开头1-3句话给出核心结论或判断，后续段落再展开详细分析。首段不应包含大量数据细节。"},
    {"id": "GS-2", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "回答末尾必须包含一段总结",
     "rubric": "检查输出最后一段是否为概括性总结，归纳前文核心要点。总结段应简洁（2-4句），不引入新信息。"},
    {"id": "GS-3", "type": "soft", "tasks": ["T2","T3"],
     "desc": "使用正式书面语，不得口语化",
     "rubric": "检查输出是否使用正式书面语。不应出现'挺好的''差不多''搞清楚'等口语化表达。专业术语使用规范。"},
    {"id": "GS-4", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "语气客观中立，不包含主观投资建议",
     "rubric": "检查输出整体语气是否客观中立，不含'建议买入/卖出'等投资建议。允许客观陈述分析结论，但不应有明确投资操作建议。"},
    {"id": "GS-5", "type": "soft", "tasks": ["T2","T3"],
     "desc": "段落间逻辑连贯，有明确过渡",
     "rubric": "检查段落之间是否有逻辑过渡（如'进一步分析''与此相关''从另一角度'等），论述是否连贯。各段主题衔接不跳跃。"},
    {"id": "GS-7", "type": "soft", "tasks": ["T2","T3"],
     "desc": "使用类比或举例来辅助解释",
     "rubric": "检查输出是否使用至少一处类比（如'类似于...'）或具体例子来辅助解释复杂概念或论点。"},
    {"id": "GS-8a", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "以普通投资者能理解的方式撰写",
     "rubric": "检查输出是否适合无金融背景的普通投资者阅读。避免过多未解释的专业术语，用词通俗，解释清晰。"},
    {"id": "GS-8b", "type": "soft", "tasks": ["T2","T3"],
     "desc": "以机构投资者为目标读者撰写",
     "rubric": "检查输出是否面向机构投资者，使用专业金融术语，分析深度和数据密度符合专业水平。"},
    {"id": "GS-9a", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "以专业分析师的口吻撰写",
     "rubric": "检查输出是否使用分析师报告风格。应使用'同比增长''环比下降''净流入'等专业术语，段落结构清晰专业。"},
    {"id": "GS-9b", "type": "soft", "tasks": ["T2","T3"],
     "desc": "以谨慎保守的语气撰写",
     "rubric": "检查输出语气是否谨慎保守。应多使用'可能''或许''需关注'等措辞，避免过于绝对的判断如'必然''一定''肯定'。"},
    {"id": "FS-1", "type": "soft", "tasks": ["T2","T3"],
     "desc": "从ESG（环境、社会、治理）角度进行评价",
     "rubric": "检查输出是否从ESG角度分析，至少涉及环境(E)、社会(S)、治理(G)中的一个维度，而非纯财务指标分析。"},
    {"id": "FS-3", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "专业术语英文缩写需给出中文全称",
     "rubric": "检查输出中出现的金融专业术语英文缩写（如ROE、PE、EBITDA等）是否给出了中文全称解释（至少首次出现时）。",
     "excludes": {"FS-10"}},
    {"id": "FS-6", "type": "soft", "tasks": ["T2","T3"],
     "desc": "从风险管理的角度分析",
     "rubric": "检查输出是否从风险管理角度进行分析，重点关注风险因素识别、风险度量和风险控制措施，而非纯收益分析。"},
    {"id": "FS-7", "type": "soft", "tasks": ["T2","T3"],
     "desc": "站在监管机构的立场回答",
     "rubric": "检查输出是否采用监管视角，关注合规性、信息披露规范、市场秩序维护等监管关切，而非投资收益角度。",
     "max_uses": 5},
    {"id": "FS-8", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "从零售投资者的视角分析",
     "rubric": "检查输出是否从零售投资者（散户）角度分析，关注实际投资决策所需信息，用通俗语言，不假设读者有专业背景。"},
    {"id": "FS-9", "type": "soft", "tasks": ["T2","T3"],
     "desc": "从宏观经济的角度分析",
     "rubric": "检查输出是否从宏观经济角度分析，关注政策、利率、汇率、经济周期等宏观因素对标的的影响。"},
    {"id": "FS-10", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "使用通俗语言，避免专业术语和行话",
     "rubric": "检查输出是否使用通俗易懂的语言。应避免或解释'alpha''beta''夏普比率'等专业术语，让非专业读者能理解。",
     "excludes": {"FS-3"}},
    {"id": "FS-13", "type": "soft", "tasks": ["T1","T2","T3"],
     "desc": "不得使用金融术语英文缩写（如ROE/PE/EBITDA等）",
     "rubric": "检查输出是否避免了金融术语的英文缩写。ROE应写为'净资产收益率'，PE应写为'市盈率'，不允许出现英文缩写形式。",
     "max_uses": 8},
]

# ============================================================
# Exclusion Rules (unified, no slot concept)
# ============================================================

EXCLUSION_PAIRS = [
    ("GH-7", "GH-18"),    # markdown_table ↔ no_table
    ("GH-6", "GH-19"),    # ordered_list ↔ no_list
    ("FS-3", "FS-10"),    # 术语全称 ↔ 避免术语
]

JSON_EXCLUDES = {"GH-7", "GH-6", "GH-4", "GH-hl", "GH-5", "GH-bq", "GH-18", "GH-19"}


# ============================================================
# Helper Functions
# ============================================================

def extract_query(prompt):
    markers = ["请基于", "请根据", "请你", "请从", "请完成", "请对", "请分析", "请审查", "请撰写"]
    best = -1
    for m in markers:
        pos = prompt.rfind(m)
        if pos > best:
            best = pos
    return prompt[best:] if best >= 0 else prompt[-500:]


def classify_constraint(cval):
    if cval["type"] == "hard":
        checker = cval.get("checker", "")
        if checker in IF_CHECKERS:
            return "if_hard"
        elif checker in CORRECTNESS_CHECKERS:
            return "correctness_hard"
        else:
            return "other_hard"
    else:
        desc = cval.get("description", "") + " " + cval.get("rubric", "")
        if_keywords = ["格式", "表格", "结构", "章节", "列表", "字数", "排序", "口吻", "风格",
                       "标题", "section", "段落", "加粗", "感叹", "引用块", "首行", "投资建议",
                       "第一人称", "备注", "客观中立", "专业口吻", "独立成段", "总结", "角度",
                       "立场", "视角", "术语", "缩写", "通俗", "书面语", "正式", "语气",
                       "过渡", "类比", "读者", "受众", "ESG", "风险管理", "监管", "宏观"]
        if any(kw in desc for kw in if_keywords):
            return "if_soft"
        return "correctness_soft"


def weighted_sample(pool, usage_counter, k=1):
    """Sample k items from pool, weighted by inverse usage count."""
    if not pool:
        return []
    weights = [1.0 / (usage_counter[t["id"]] + 1) for t in pool]
    total = sum(weights)
    weights = [w / total for w in weights]
    chosen = []
    remaining = list(pool)
    remaining_w = list(weights)
    for _ in range(min(k, len(remaining))):
        if not remaining:
            break
        r = random.random() * sum(remaining_w)
        cumulative = 0
        idx = 0
        for i, w in enumerate(remaining_w):
            cumulative += w
            if r <= cumulative:
                idx = i
                break
        chosen.append(remaining[idx])
        remaining.pop(idx)
        remaining_w.pop(idx)
    return chosen


# ============================================================
# Conflict Detection
# ============================================================

QUERY_CONFLICT_MAP = {
    "check_no_table": ["表格", "制表", "表格形式", "表格呈现"],
    "check_no_list": ["列表", "清单形式", "用列表", "以列表"],
}


def check_pair_exclusion(selected_ids, candidate_id):
    for a, b in EXCLUSION_PAIRS:
        if candidate_id == a and b in selected_ids:
            return False
        if candidate_id == b and a in selected_ids:
            return False
    if candidate_id == "GH-8":
        if selected_ids & JSON_EXCLUDES:
            return False
    if "GH-8" in selected_ids:
        if candidate_id in JSON_EXCLUDES:
            return False
    return True


def check_soft_exclusion(selected_ids, candidate):
    excludes = candidate.get("excludes", set())
    return not (excludes & selected_ids)


# ============================================================
# Step 1: Generate Constraint Assignments (Free Sampling + Easy/Hard)
# ============================================================

def step1():
    benchmark = load_json(BENCHMARK_PATH)
    cases = benchmark["cases"]
    config = load_json(EVAL_CONFIG_PATH)
    constraints = config["constraints"]

    case_constraints = defaultdict(dict)
    for cid, cval in constraints.items():
        case_id = cid.split("#")[0]
        case_constraints[case_id][cid] = cval

    # Assign Easy/Hard: stratified by L1, shuffle within each tier
    tier_cases = defaultdict(list)
    for case in cases:
        l1 = case["case_id"].split(".")[0]
        tier_cases[l1].append(case)

    level_map = {}
    for l1, tier in tier_cases.items():
        shuffled = list(tier)
        random.shuffle(shuffled)
        half = len(shuffled) // 2
        for i, case in enumerate(shuffled):
            level_map[case["case_id"]] = "Easy" if i < half else "Hard"

    easy_count = sum(1 for v in level_map.values() if v == "Easy")
    hard_count = sum(1 for v in level_map.values() if v == "Hard")
    print(f"Level split: {easy_count} Easy, {hard_count} Hard")

    usage = defaultdict(int)
    assignments = []

    for case in cases:
        case_id = case["case_id"]
        l1 = case_id.split(".")[0]
        query = extract_query(case["prompt"])
        existing = case_constraints.get(case_id, {})
        level = level_map[case_id]

        # --- Classify existing constraints ---
        keep, remove = [], []

        for cid, cval in existing.items():
            cat = classify_constraint(cval)
            checker = cval.get("checker", "")

            if cat == "correctness_hard":
                if len([k for k in keep if k["category"] == "correctness_hard"]) < 1:
                    keep.append({"cid": cid, "category": cat, "checker": checker, "description": cval["description"]})
                else:
                    remove.append({"cid": cid, "reason": "correctness_hard超过1条上限"})
            elif cat in ("if_hard", "if_soft"):
                remove.append({"cid": cid, "reason": "将由新IF约束替代"})
            elif cat == "correctness_soft":
                if len([k for k in keep if k["category"] == "correctness_soft"]) < 1:
                    keep.append({"cid": cid, "category": cat, "description": cval["description"]})
                else:
                    remove.append({"cid": cid, "reason": "correctness_soft超过1条上限"})
            else:
                keep.append({"cid": cid, "category": cat, "description": cval.get("description", "")})

        # --- Determine n_if for this case ---
        if level == "Easy":
            n_if = random.choice([3, 4])
        else:
            n_if = random.choice([5, 6])

        # --- Free sample n_if constraints ---
        # Query conflict detection
        query_blocked = set()
        for checker, keywords in QUERY_CONFLICT_MAP.items():
            if any(kw in query for kw in keywords):
                for c in CONSTRAINT_POOL:
                    if c.get("checker") == checker:
                        query_blocked.add(c["id"])

        selected_ids = set()
        new_if = []
        max_cn = 0
        for cid in existing:
            cn = int(cid.split("#C")[1])
            max_cn = max(max_cn, cn)

        for _ in range(n_if):
            valid = []
            for c in CONSTRAINT_POOL:
                cid = c["id"]
                if cid in selected_ids:
                    continue
                if cid in query_blocked:
                    continue
                if l1 not in c["tasks"]:
                    continue
                cap = c.get("max_uses", 999)
                if usage.get(cid, 0) >= cap:
                    continue
                if not check_pair_exclusion(selected_ids, cid):
                    continue
                if c["type"] == "soft" and not check_soft_exclusion(selected_ids, c):
                    continue
                valid.append(c)

            if not valid:
                break

            chosen = weighted_sample(valid, usage, k=1)
            if not chosen:
                break

            t = chosen[0]
            selected_ids.add(t["id"])
            usage[t["id"]] = usage.get(t["id"], 0) + 1

            if t["type"] == "hard":
                result = t["gen"](l1)
                if isinstance(result, tuple) and len(result) == 3:
                    params, text, desc = result
                else:
                    continue
                new_if.append({
                    "pool_id": t["id"],
                    "type": "hard",
                    "checker": t["checker"],
                    "params": params,
                    "rendered_text": text,
                    "description": desc,
                })
            else:
                new_if.append({
                    "pool_id": t["id"],
                    "type": "soft",
                    "rendered_text": t["desc"],
                    "description": t["desc"],
                    "rubric": t["rubric"],
                })

        signals = [c["rendered_text"] for c in new_if]

        kept_if = sum(1 for k in keep if k["category"].startswith("if"))
        new_if_count = len(new_if)
        total_after = len(keep) + new_if_count
        if_after = kept_if + new_if_count
        if_ratio = round(if_after / max(total_after, 1) * 100, 1)

        assignments.append({
            "case_id": case_id,
            "L1": l1,
            "level": level,
            "n_if": len(new_if),
            "query_preview": query[:150],
            "existing_count": len(existing),
            "keep": keep,
            "remove": remove,
            "new_if": new_if,
            "max_existing_cn": max_cn,
            "query_if_signals": signals,
            "stats": {
                "total_after": total_after,
                "if_count": if_after,
                "if_ratio": if_ratio,
            },
        })

    save_json(assignments, ASSIGNMENTS_PATH)

    # --- Summary ---
    ratios = [a["stats"]["if_ratio"] for a in assignments]
    print(f"Generated assignments for {len(assignments)} cases")
    print(f"IF ratio: avg={sum(ratios)/len(ratios):.1f}%, min={min(ratios):.1f}%, max={max(ratios):.1f}%")

    # Level distribution
    level_n = defaultdict(list)
    for a in assignments:
        level_n[a["level"]].append(a["n_if"])
    for level in ["Easy", "Hard"]:
        ns = level_n[level]
        dist = Counter(ns)
        print(f"\n{level} ({len(ns)} cases):")
        for n in sorted(dist):
            print(f"  {n} IF constraints: {dist[n]} cases")

    # Constraint diversity
    all_pool_ids = []
    for a in assignments:
        for c in a["new_if"]:
            all_pool_ids.append(c["pool_id"])

    id_counter = Counter(all_pool_ids)
    print(f"\nUnique constraint types used: {len(id_counter)}/{len(CONSTRAINT_POOL)}")
    print(f"Constraint distribution (top 15):")
    for cid, cnt in id_counter.most_common(15):
        print(f"  {cid}: {cnt}")

    all_texts = [c["rendered_text"] for a in assignments for c in a["new_if"]]
    text_counter = Counter(all_texts)
    print(f"\nUnique IF requirement texts: {len(text_counter)}")
    print(f"Most common (top 10):")
    for t, cnt in text_counter.most_common(10):
        print(f"  [{cnt}x] {t}")

    print(f"\nSaved to {ASSIGNMENTS_PATH}")


# ============================================================
# Step 3: Apply Assignments
# ============================================================

def step3():
    assignments = load_json(ASSIGNMENTS_PATH)
    benchmark = load_json(BENCHMARK_PATH)
    config = load_json(EVAL_CONFIG_PATH)

    save_json(benchmark, BENCHMARK_PATH + ".bak2")
    save_json(config, EVAL_CONFIG_PATH + ".bak2")

    cases_map = {c["case_id"]: c for c in benchmark["cases"]}
    constraints = config["constraints"]

    total_added, total_removed = 0, 0

    for assign in assignments:
        case_id = assign["case_id"]

        for r in assign["remove"]:
            if r["cid"] in constraints:
                del constraints[r["cid"]]
                total_removed += 1

        cn = assign["max_existing_cn"]
        for new_c in assign["new_if"]:
            cn += 1
            cid = f"{case_id}#C{cn}"
            if new_c["type"] == "hard":
                entry = {
                    "type": "hard",
                    "checker": new_c["checker"],
                    "description": new_c["description"],
                }
                if new_c["params"] is not None:
                    entry["params"] = new_c["params"]
            else:
                entry = {
                    "type": "soft",
                    "description": new_c["description"],
                    "rubric": new_c["rubric"],
                }
            constraints[cid] = entry
            total_added += 1

        case = cases_map.get(case_id)
        if case:
            prompt = case["prompt"]
            signals = assign["query_if_signals"]
            req_lines = [f"（{i+1}）{s}" for i, s in enumerate(signals)]
            req_block = "\n请在回答时严格遵守以下附加要求：\n" + "\n".join(req_lines)
            prompt = re.sub(r'\n*输出要求[：:].+$', '', prompt, flags=re.DOTALL)
            prompt = re.sub(r'\n*请在回答时严格遵守以下附加要求[：:].+$', '', prompt, flags=re.DOTALL)
            case["prompt"] = prompt.rstrip() + "\n" + req_block

    hard_count = sum(1 for c in constraints.values() if c["type"] == "hard")
    soft_count = sum(1 for c in constraints.values() if c["type"] == "soft")
    case_ids = set(cid.split("#")[0] for cid in constraints)

    config["constraints"] = constraints
    config["stats"] = {
        "total": len(constraints),
        "hard": hard_count,
        "soft": soft_count,
        "cases": len(case_ids),
        "avg_per_case": round(len(constraints) / len(case_ids), 1),
    }

    save_json(config, EVAL_CONFIG_PATH)
    save_json(benchmark, BENCHMARK_PATH)

    if_hard = sum(1 for c in constraints.values()
                  if c["type"] == "hard" and c.get("checker", "") in IF_CHECKERS)
    if_soft = sum(1 for c in constraints.values()
                  if c["type"] == "soft" and classify_constraint(c) == "if_soft")
    total = len(constraints)

    print(f"\n=== Step 3 Complete ===")
    print(f"Removed: {total_removed}, Added: {total_added}")
    print(f"Total: {total} (Hard: {hard_count}, Soft: {soft_count})")
    print(f"IF hard: {if_hard}, IF soft: {if_soft}")
    print(f"IF ratio: {(if_hard + if_soft) / total * 100:.1f}%")


# ============================================================
# Stats: Analyze current constraint distribution
# ============================================================

def stats():
    config = load_json(EVAL_CONFIG_PATH)
    constraints = config["constraints"]

    categories = defaultdict(int)
    checkers = Counter()
    per_case = defaultdict(lambda: {"if_hard": 0, "correctness_hard": 0, "if_soft": 0, "correctness_soft": 0, "total": 0})

    for cid, cval in constraints.items():
        case_id = cid.split("#")[0]
        cat = classify_constraint(cval)
        categories[cat] += 1
        per_case[case_id][cat] += 1
        per_case[case_id]["total"] += 1
        if cval.get("checker"):
            checkers[cval["checker"]] += 1

    total = len(constraints)
    if_total = categories["if_hard"] + categories["if_soft"]

    print(f"=== Constraint Stats ===")
    print(f"Total: {total}")
    for cat, cnt in sorted(categories.items()):
        print(f"  {cat}: {cnt} ({cnt/total*100:.1f}%)")
    print(f"IF total: {if_total} ({if_total/total*100:.1f}%)")

    print(f"\nChecker distribution (top 15):")
    for ch, cnt in checkers.most_common(15):
        print(f"  {ch}: {cnt}")

    ratios = []
    for case_id, pc in per_case.items():
        if_count = pc["if_hard"] + pc["if_soft"]
        ratio = if_count / max(pc["total"], 1) * 100
        ratios.append(ratio)
    print(f"\nPer-case IF ratio: avg={sum(ratios)/len(ratios):.1f}%, min={min(ratios):.1f}%")
    print(f"Cases below 60%: {sum(1 for r in ratios if r < 60)}")

    # Unique descriptions
    hard_descs = [c["description"] for c in constraints.values() if c["type"] == "hard" and c.get("checker", "") in IF_CHECKERS]
    print(f"\nUnique IF hard descriptions: {len(set(hard_descs))}")
    desc_counter = Counter(hard_descs)
    print("Most common (top 10):")
    for d, cnt in desc_counter.most_common(10):
        print(f"  [{cnt}x] {d}")


# ============================================================
# Restore: Copy .bak files back
# ============================================================

def restore():
    for path in [BENCHMARK_PATH, EVAL_CONFIG_PATH]:
        bak = path + ".bak"
        if os.path.exists(bak):
            shutil.copy2(bak, path)
            print(f"Restored {path} from {bak}")
        else:
            print(f"WARNING: {bak} not found, skipping")


# ============================================================
# Tag: Assign taxonomy labels to all constraints
# ============================================================

TAG_NAMES = {
    "F1": "Section/Heading",   "F2": "List",          "F3": "Table",
    "F4": "JSON/Structured",   "F5": "Blockquote",    "F6": "Opening/Closing",
    "F7": "Special Format",    "F8": "Sorting/Ordering",
    "N1": "Word Count",        "N2": "Element Count",  "N3": "Precision",
    "N4": "Duration",
    "L1": "Keyword/Mandatory", "L2": "Forbidden Pattern", "L3": "Terminology",
    "L4": "Currency/Notation",
    "S1": "Tone",              "S2": "Role/Persona",   "S3": "Coherence",
    "S4": "Rhetoric",
    "C1": "Coverage",          "C2": "Evidence",       "C3": "Analysis Perspective",
    "C4": "Conditional/Scenario", "C5": "Conditional Trigger", "C6": "Computation",
}

IF_TAGS = {t for t in TAG_NAMES if t != "C6"}

CHECKER_TO_TAG = {
    # Format
    "check_section_count": "F1", "check_heading_level": "F1", "check_heading_depth": "F1",
    "check_section_titles": "F1",
    "check_ordered_list_count": "F2", "check_numbered_list": "F2",
    "check_list_format": "F2", "check_no_list": "F2",
    "check_markdown_table": "F3", "check_two_tables": "F3", "check_no_table": "F3",
    "check_table_row_count": "F3", "check_table_column_names": "F3", "check_header_row": "F3",
    "check_json_format": "F4", "check_json_structure": "F4", "check_json_field_count": "F4",
    "check_json_field_item_limit": "F4", "check_json_field_word_limit": "F4", "check_no_extra": "F4",
    "check_blockquote_count": "F5",
    "check_first_line_format": "F6", "check_first_word": "F6", "check_first_last_line": "F6",
    "check_first_row": "F6", "check_last_row": "F6", "check_bold_values": "F6",
    "check_email_in_last_line": "F6",
    "check_qa_format": "F7", "check_checkbox_format": "F7",
    "check_code_block": "F7", "check_markdown_format": "F7",
    "check_ranking": "F8", "check_table_sort_alpha": "F8",
    "check_sort_date": "F8", "check_sort_value_desc": "F8",
    # Number
    "check_word_limit": "N1", "check_word_range": "N1", "check_item_word_limit": "N1",
    "check_sentence_count": "N2", "check_paragraph_count": "N2",
    "check_decimal_places": "N3",
    # Linguistic
    "check_keyword_presence": "L1", "check_risk_disclaimer": "L1",
    "check_keyword_absence": "L2", "check_forbidden_pattern": "L2",
    "check_first_person": "L2", "check_no_arabic_numerals": "L2",
    "check_filter": "L2", "check_lang_cn": "L2",
    "check_no_percent": "L4", "check_currency_format": "L4",
    # Content
    "check_conditional_trigger": "C5",
    "check_computation_result": "C6", "check_value_exact": "C6",
    "check_value_derivation": "C6", "check_arithmetic_correct": "C6",
    "check_source_fidelity": "C6", "check_has_calculation": "C6",
    "check_comparison": "C6", "check_judgment": "C6",
    "check_conclusion_label": "C6", "check_direction_label": "C6",
    "check_field_coverage": "C1",
    "check_investment_rating": "C6", "check_risk_grade": "C6",
}

# Ordered rules for soft constraints: first match wins
SOFT_TAG_RULES = [
    # F6 Opening/Closing
    (["先给出结论", "先给结论", "首段为全文要点"], "F6"),
    (["末尾必须包含一段总结", "回答末尾"], "F6"),
    # F8 Sorting
    (["排序输出", "从高到低排序", "从低到高排列"], "F8"),
    # L3 Terminology
    (["术语", "缩写", "全称", "通俗语言", "避免专业术语", "英文缩写", "ROE", "PE", "EBITDA"], "L3"),
    # S1 Tone
    (["客观中立", "正式书面语", "口语化", "谨慎保守", "不带主观", "语气"], "S1"),
    # S2 Role/Persona
    (["分析师", "口吻", "监管.*立场", "立场回答", "零售投资者", "机构投资者",
      "受众", "读者", "普通投资者.*理解", "目标读者"], "S2"),
    # S3 Coherence
    (["逻辑连贯", "过渡", "独立成段", "不混杂"], "S3"),
    # S4 Rhetoric
    (["类比", "举例", "辅助解释"], "S4"),
    # C3 Analysis Perspective
    (["ESG", "风险管理.*角度", "宏观经济.*角度", "从.*角度分析"], "C3"),
    # C1 Coverage
    (["覆盖.*股东", "覆盖.*对象", "覆盖.*公司", "完整列出", "完整提取",
      "维度分析完整", "维度.*完整", "统计了"], "C1"),
    # C6 Computation (展示计算/计算了/正确/验证)
    (["展示了.*计算", "计算了", "正确计算", "正确分析", "正确判断", "正确识别",
      "正确分类", "正确标注", "反推", "反算", "推算", "验证", "核验",
      "CAGR", "完成率", "完成度", "损失合计", "合计验证", "一致性",
      "投资评级", "盈亏转换", "恩格尔系数", "涨跌幅极值", "箭头标注",
      "问答对数量", "星期几", "日期间隔", "时间跨度", "行业数量"], "C6"),
    # C2 Evidence / Quality
    (["分析有深度", "分析合理", "分析.*合理", "有深度", "数据支撑", "数据佐证",
      "引用.*数据", "引用具体", "分析.*风险", "风险分析", "来源", "简洁有力",
      "仅基于", "核心摘要", "质量", "评估", "金额对比", "经济数据分类",
      "驱动力", "信用利差", "增长率之差", "贡献", "行业集中", "未来增长",
      "回款风险", "可持续性", "转正分析", "行业分化", "萎缩分析",
      "密集型判断", "拖累量化", "内需风险", "动能分析", "新旧动能",
      "收窄判断", "支付方式", "收入质量", "营收占比", "负增长行业"], "C2"),
    # C4 Conditional/Scenario
    (["假设.*环境", "假设.*条件", "前提下", "首要考量"], "C4"),
]


def tag_constraint(cid, cval):
    """Assign taxonomy tag to a single constraint."""
    # Hard constraints: use checker mapping
    if cval["type"] == "hard":
        checker = cval.get("checker", "")
        if checker in CHECKER_TO_TAG:
            return CHECKER_TO_TAG[checker]
        if checker == "rubric":
            pass  # fall through to soft rules
        else:
            return "C6"  # unknown hard checker → default to computation

    # Soft constraints (and rubric-type): match description only
    desc = cval.get("description", "")
    for keywords, tag in SOFT_TAG_RULES:
        for kw in keywords:
            if re.search(kw, desc):
                return tag

    # Fallback: check rubric for broader matching
    full = desc + " " + cval.get("rubric", "")
    if "计算" in full or "正确" in full:
        return "C6"
    return "C2"


def tag():
    """Tag all constraints with taxonomy labels and write back."""
    config = load_json(EVAL_CONFIG_PATH)
    constraints = config["constraints"]

    tag_counts = Counter()
    category_counts = defaultdict(lambda: {"total": 0, "hard": 0, "soft": 0})
    untagged = []

    for cid, cval in constraints.items():
        t = tag_constraint(cid, cval)
        cval["tag"] = t
        cval["tag_name"] = TAG_NAMES[t]
        cval["is_if"] = t in IF_TAGS

        tag_counts[t] += 1
        cat = t[0]  # F/N/L/S/C
        category_counts[cat]["total"] += 1
        category_counts[cat][cval["type"]] += 1

    save_json(config, EVAL_CONFIG_PATH)

    # --- Report ---
    total = len(constraints)
    if_total = sum(c.get("is_if", False) for c in constraints.values())
    cap_total = total - if_total

    print(f"=== Taxonomy Tagging Complete ===")
    print(f"Total: {total} constraints tagged")
    print(f"IF: {if_total} ({if_total/total*100:.1f}%)  |  Capability(C6): {cap_total} ({cap_total/total*100:.1f}%)")

    print(f"\n{'Cat':<5} {'Tag':<5} {'Name':<22} {'Hard':>5} {'Soft':>5} {'Total':>5}")
    print("-" * 52)
    for cat_letter in "FNLSC":
        cat_name = {"F":"Format","N":"Number","L":"Linguistic","S":"Style","C":"Content"}[cat_letter]
        cat_total = category_counts[cat_letter]["total"]
        cat_h = category_counts[cat_letter]["hard"]
        cat_s = category_counts[cat_letter]["soft"]
        first = True
        for tag_id in sorted(t for t in tag_counts if t.startswith(cat_letter)):
            sub_h = sum(1 for c in constraints.values() if c.get("tag")==tag_id and c["type"]=="hard")
            sub_s = sum(1 for c in constraints.values() if c.get("tag")==tag_id and c["type"]=="soft")
            prefix = cat_name if first else ""
            print(f"{prefix:<5} {tag_id:<5} {TAG_NAMES[tag_id]:<22} {sub_h:>5} {sub_s:>5} {sub_h+sub_s:>5}")
            first = False
        if cat_total > 0:
            print(f"{'':>5} {'':>5} {'(subtotal)':<22} {cat_h:>5} {cat_s:>5} {cat_total:>5}")
            print()

    # Per-case tag variety
    case_tags = defaultdict(set)
    for cid, cval in constraints.items():
        case_id = cid.split("#")[0]
        case_tags[case_id].add(cval.get("tag", ""))
    avg_variety = sum(len(v) for v in case_tags.values()) / len(case_tags)
    print(f"Per-case tag variety: avg={avg_variety:.1f} unique tags/case")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 restructure_benchmark.py [restore|step1|step3|stats|tag]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "restore":
        restore()
    elif cmd == "step1":
        step1()
    elif cmd == "step3":
        step3()
    elif cmd == "stats":
        stats()
    elif cmd == "tag":
        tag()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
