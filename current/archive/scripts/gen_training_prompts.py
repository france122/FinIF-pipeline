#!/usr/bin/env python3
"""
FinIF SFT — Opus-crafted training prompts with precise constraints
每个 prompt 手工设计，expected values 由 Opus 预计算
"""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 加载 context
# ============================================================
with open(os.path.join(SCRIPT_DIR, "training_contexts_raw.json"), encoding="utf-8") as f:
    CONTEXTS = {c["company"]: c["text"] for c in json.load(f)}

ALL_CASES = []
CONSTRAINTS = {}

def add_case(case_id, context_key, instruction, constraints_dict):
    ctx = CONTEXTS[context_key]
    prompt = f"{ctx}\n\n{instruction}"
    ALL_CASES.append({
        "case_id": case_id,
        "company": context_key,
        "prompt": prompt,
        "context": ctx,
    })
    for ck, cv in constraints_dict.items():
        CONSTRAINTS[f"{case_id}#{ck}"] = cv

# ============================================================
# Helper: 构建约束
# ============================================================
def hard(checker, params=None, desc=""):
    c = {"type": "hard", "checker": checker, "description": desc}
    if params: c["params"] = params
    return c

def soft(desc, rubric):
    return {"type": "soft", "description": desc, "rubric": rubric}

# Reusable soft constraints
S_NO_FAB = soft("不编造原文中不存在的数据", "检查输出中的数据是否都能在原文context中找到来源")
S_CALC = soft("计算过程展示完整", "判断是否清晰展示了计算步骤和中间结果")
S_ANALYSIS = soft("分析有深度，不是简单罗列数据", "判断模型是否对数据进行了有意义的分析和解读")
S_PROF = soft("语言专业规范", "判断语言是否专业、客观、规范，符合金融行业报告风格")
S_LOGIC = soft("逻辑连贯，结论有数据支撑", "判断分析过程是否逻辑连贯，结论是否有明确的数据依据")
S_COMPLETE = soft("回答完整，覆盖题目所有要求", "判断回答是否完整覆盖了题目中的所有子任务和要求")
S_RISK = soft("风险提示合理到位", "判断是否对潜在风险进行了合理的提示和分析")
S_COMPARE = soft("对比分析有洞察力", "判断对比分析是否揭示了有意义的差异或趋势")

# ============================================================
# Company 1: ST尔雅 (600107)  服装
# ============================================================
CTX1 = "ST尔雅_600107"

# TR-001: 提取年度财务指标 → 表格
add_case("TR-001", CTX1,
    """请基于以上ST尔雅(600107)2025年年度报告摘要，提取以下年度财务数据并整理为Markdown表格：
- 总资产、归属净资产、营业收入、净利润、扣非净利润、每股收益、加权ROE
- 表格包含"指标"、"2025年"、"2024年"、"同比变动"三列
- 关键负面数据（亏损、下降）用加粗标记

仅输出表格，不添加额外分析文字。""",
    {
        "C1": hard("check_markdown_table", desc="输出包含Markdown表格"),
        "C2": hard("check_value_exact", {"expected_values": {
            "总资产": "748364760.06",
            "营业收入": "236195000.11",
            "每股收益": "-0.25",
        }}, "关键财务数据与原文一致"),
        "C3": hard("check_bold_values", desc="负面数据加粗"),
        "C4": hard("check_table_column_names", {"required_columns": ["指标", "2025年"]}, "表格列名正确"),
        "C5": S_NO_FAB,
    })

# TR-002: 季度营收计算
# Q1=74230286.84 Q2=54892908.37 Q3=43047760.99 Q4=64024043.91 Total=236195000.11
# Q1占比=74230286.84/236195000.11=31.43% Q3占比=18.23%
# Q1-Q3差=74230286.84-43047760.99=31182525.85
add_case("TR-002", CTX1,
    """请基于以上ST尔雅2025年年度报告摘要中的分季度数据，完成以下计算：

1. 列出各季度营业收入数据
2. 计算各季度营业收入占全年比例（百分比，保留两位小数）
3. 找出营收最高和最低的季度
4. 计算最高季度与最低季度的营收差额

输出要求：Markdown格式，包含汇总表格（含"季度"、"营业收入(元)"、"占比"列），展示计算过程。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "Q1占比", "expected": 31.43, "tolerance": 0.5},
            {"label": "Q3占比", "expected": 18.23, "tolerance": 0.5},
        ]}, "季度占比计算正确"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "差额", "expected": 31182525.85, "tolerance": 100},
        ]}, "差额计算正确"),
        "C4": hard("check_table_column_names", {"required_columns": ["季度", "占比"]}, "表格列名"),
        "C5": S_CALC,
        "C6": S_NO_FAB,
    })

# TR-003: 股东持股计算
# 前5大: 73388738+6660000+5374000+4586600+4551900 = 94561238
# 总股本: 73388738/0.2039 ≈ 359925149 (实际应是约360M股)
# 前5占比: 20.39+1.85+1.49+1.27+1.26 = 26.26%
add_case("TR-003", CTX1,
    """请基于以上ST尔雅2025年年度报告摘要中的股东信息，完成以下分析：

1. 列出前5大股东的名称、持股数量、持股比例，整理为Markdown表格
2. 计算前5大股东合计持股比例
3. 说明哪些股东存在质押或冻结情况，涉及多少股份
4. 判断控股股东及实际控制人是谁

输出要求：Markdown格式，包含表格，总字数不超过500字。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_word_limit", {"max_words": 500}, "不超过500字"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "合计持股比例", "expected": 26.26, "tolerance": 0.2},
        ]}, "前5大合计持股比例正确"),
        "C4": hard("check_keyword_presence", {"required_keywords": ["郑继平", "质押"], "match_all": True}, "提及实控人和质押"),
        "C5": S_NO_FAB,
        "C6": S_COMPLETE,
    })

# TR-004: 净利润率和资产负债率
# 净利润率 = -89092646.60/236195000.11 = -37.72%
# 资产负债率 = (748364760.06-401683133.32)/748364760.06 = 46.32%
# 2024: (877115138.16-492191234.30)/877115138.16 = 43.89%
add_case("TR-004", CTX1,
    """请基于以上ST尔雅2025年年度报告摘要，计算以下财务指标：

1. 2025年净利润率 = 归属净利润 / 营业收入 × 100%
2. 2025年资产负债率 = (总资产-归属净资产) / 总资产 × 100%
3. 2024年资产负债率（使用2024年数据计算）
4. 资产负债率同比变动（2025年 - 2024年）

输出要求：展示完整计算公式和过程，结果保留两位小数。总字数不超过400字。""",
    {
        "C1": hard("check_word_limit", {"max_words": 400}, "不超过400字"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "净利润率", "expected": -37.72, "tolerance": 0.5},
        ]}, "净利润率计算正确"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "2025资产负债率", "expected": 46.32, "tolerance": 0.5},
        ]}, "2025资产负债率正确"),
        "C4": hard("check_computation_result", {"results": [
            {"label": "2024资产负债率", "expected": 43.89, "tolerance": 0.5},
        ]}, "2024资产负债率正确"),
        "C5": S_CALC,
        "C6": S_NO_FAB,
    })

# TR-005: 退市风险分析
add_case("TR-005", CTX1,
    """请基于以上ST尔雅2025年年度报告摘要，撰写一份退市风险分析报告：

1. 列出公司面临的退市风险触发条件（从报告中提取）
2. 逐条分析公司是否满足这些条件，引用具体数据
3. 给出风险等级评估（高/中/低）
4. 提出3条投资者关注建议

输出要求：Markdown格式，至少4个章节标题，恰好3条投资者建议（编号列表），总字数300-600字。""",
    {
        "C1": hard("check_section_count", {"min_sections": 4}, "至少4个章节"),
        "C2": hard("check_word_range", {"min_words": 300, "max_words": 600}, "300-600字"),
        "C3": hard("check_ordered_list_count", {"exact_count": 3}, "恰好3条建议"),
        "C4": hard("check_keyword_presence", {"required_keywords": ["退市风险", "营业收入"], "match_all": True}, "包含关键词"),
        "C5": S_RISK,
        "C6": S_LOGIC,
        "C7": S_PROF,
    })

# ============================================================
# Company 2: 美凯龙 (601828)  家居
# ============================================================
CTX2 = "美凯龙_601828"

# TR-006: 提取+对比三年数据
add_case("TR-006", CTX2,
    """请基于以上美凯龙(601828)2025年年度报告摘要，完成以下任务：

1. 提取近3年（2023-2025）的总资产、营业收入、归属净利润数据
2. 整理为Markdown表格，包含"指标"、"2025年"、"2024年"、"2023年"列
3. 计算2025年相比2023年的2年累计变动率：(2025-2023)/2023×100%

输出要求：Markdown格式，展示计算过程。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_value_exact", {"expected_values": {
            "总资产": "87355665991.56",
            "营业收入": "6581940812.80",
        }}, "2025年数据正确"),
        # 2年累计营收变动: (6581940812.80-11514982938.87)/11514982938.87 = -42.84%
        "C3": hard("check_computation_result", {"results": [
            {"label": "营收2年变动", "expected": -42.84, "tolerance": 1.0},
        ]}, "营收2年变动率正确"),
        "C4": S_CALC,
        "C5": S_NO_FAB,
    })

# TR-007: 季度分析 美凯龙
# Q1=1615436680.31 Q2=1721639511.35 Q3=1631585229.51 Q4=1613279391.63
# Total=6581940812.80
# Q2占比=26.16% Q4占比=24.51%
# Q4净利润=-20579663166.70 占全年 = 86.75%
add_case("TR-007", CTX2,
    """请基于以上美凯龙2025年年度报告摘要中的分季度数据，完成以下分析：

1. 各季度营业收入占全年比例
2. 各季度净利润数据及占全年比例
3. 找出净利润亏损最严重的季度，分析可能原因
4. 判断公司Q4是否出现了异常大额亏损

输出要求：Markdown格式，包含两个表格（营收表和净利润表），总字数300-500字。""",
    {
        "C1": hard("check_two_tables", desc="包含两个表格"),
        "C2": hard("check_word_range", {"min_words": 300, "max_words": 500}, "300-500字"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "Q2营收占比", "expected": 26.16, "tolerance": 0.5},
        ]}, "Q2营收占比正确"),
        "C4": S_ANALYSIS,
        "C5": S_NO_FAB,
        "C6": S_COMPARE,
    })

# TR-008: 债务分析 美凯龙
# 资产负债率2025=72.62% 2024=57.40% 增加26.12%（原文直接给出）
# EBITDA全部债务比: -0.85
# 利息保障倍数: -11.96
add_case("TR-008", CTX2,
    """请基于以上美凯龙2025年年度报告摘要中的债务指标数据，完成以下分析：

1. 提取资产负债率、EBITDA全部债务比、利息保障倍数的2025年和2024年数据
2. 整理为Markdown表格
3. 逐项分析各指标的变化趋势及其含义
4. 综合评价公司的偿债能力和财务风险等级

输出要求：Markdown格式，至少3个分析段落，每段对应一个指标。关键数值加粗。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_bold_values", desc="关键数值加粗"),
        "C3": hard("check_value_exact", {"expected_values": {
            "资产负债率": "72.62",
            "利息保障倍数": "-11.96",
        }}, "数据提取正确"),
        "C4": hard("check_section_count", {"min_sections": 3}, "至少3段分析"),
        "C5": S_ANALYSIS,
        "C6": S_RISK,
        "C7": S_PROF,
    })

# TR-009: JSON提取 美凯龙
add_case("TR-009", CTX2,
    """请基于以上美凯龙2025年年度报告摘要，用JSON格式输出以下信息：

```json
{
  "company_name": "公司全称",
  "stock_code_a": "A股代码",
  "stock_code_h": "H股代码",
  "total_revenue_2025": 数字(元),
  "net_profit_2025": 数字(元),
  "eps_2025": 数字,
  "roe_2025": 数字(%),
  "asset_liability_ratio": 数字(%),
  "total_stores": 数字,
  "self_operated_stores": 数字,
  "managed_stores": 数字,
  "audit_opinion": "审计意见类型",
  "dividend_plan": "分红方案"
}
```

仅输出JSON，不添加其他说明。""",
    {
        "C1": hard("check_json_format", desc="有效JSON"),
        "C2": hard("check_keyword_presence", {"required_keywords": ["601828", "01528"], "match_all": True}, "包含A股和H股代码"),
        "C3": S_NO_FAB,
        "C4": S_COMPLETE,
    })

# TR-010: 股东集中度 美凯龙
# 前3大: 23.95+18.94+17.02=59.91% 前5大: +6.00+5.40=71.31%
# 建发+联发一致行动: 23.95+6.00=29.95%
add_case("TR-010", CTX2,
    """请基于以上美凯龙2025年年度报告摘要中的股东信息，完成以下计算：

1. 计算前3大股东合计持股比例
2. 计算前5大股东合计持股比例
3. 厦门建发与联发集团构成一致行动关系，计算两者合计持股比例
4. 红星美凯龙控股集团质押了多少股份？质押比例是多少？

输出要求：Markdown格式，展示计算过程，包含汇总表格。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "前3大合计", "expected": 59.91, "tolerance": 0.2},
            {"label": "前5大合计", "expected": 71.31, "tolerance": 0.2},
        ]}, "持股比例计算正确"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "一致行动合计", "expected": 29.95, "tolerance": 0.1},
        ]}, "一致行动合计正确"),
        "C4": S_CALC,
        "C5": S_NO_FAB,
    })

# ============================================================
# Company 3: 弘元绿能 (603185)  光伏
# ============================================================
CTX3 = "弘元绿能_603185"

# TR-011: 扭亏分析
# 2024净利润: -2696887140.75  2025: 186838017.19 差额: 2883725157.94
# 净利润率2025: 186838017.19/7425484990.95 = 2.52%
add_case("TR-011", CTX3,
    """请基于以上弘元绿能(603185)2025年年度报告摘要，分析公司的扭亏情况：

1. 对比2024年和2025年的归属净利润，计算改善金额
2. 计算2025年净利润率（归属净利润/营业收入×100%）
3. 分析营业收入、扣非净利润、经营现金流的同比变化
4. 判断公司是否实现了真正的盈利改善

输出要求：Markdown格式，展示计算过程，至少3个章节，总字数300-500字。""",
    {
        "C1": hard("check_section_count", {"min_sections": 3}, "至少3个章节"),
        "C2": hard("check_word_range", {"min_words": 300, "max_words": 500}, "300-500字"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "净利润率", "expected": 2.52, "tolerance": 0.1},
        ]}, "净利润率正确"),
        "C4": S_ANALYSIS,
        "C5": S_CALC,
        "C6": S_NO_FAB,
    })

# TR-012: 季度波动分析 弘元绿能
# Q3最高: 2456351366.30 Q2最低: 1571809438.22
# Q3净利润=646450432.99 其他三季度均亏损
# Q3贡献全年净利: 646450432.99/186838017.19 = 345.96% (大于100%因为其他季度亏损)
add_case("TR-012", CTX3,
    """请基于以上弘元绿能2025年年度报告摘要中的分季度数据，完成以下分析：

1. 整理四个季度的营业收入和净利润数据为表格
2. 找出唯一盈利的季度，计算该季度净利润占全年净利润的比例
3. 计算Q3营业收入相比Q2的环比增长率
4. 分析公司收入的季节性特征

输出要求：Markdown格式，包含数据表格和分析文字。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        # Q3/Q2环比: (2456351366.30-1571809438.22)/1571809438.22 = 56.27%
        "C2": hard("check_computation_result", {"results": [
            {"label": "Q3环比增长", "expected": 56.27, "tolerance": 1.0},
        ]}, "Q3环比增长率正确"),
        "C3": S_ANALYSIS,
        "C4": S_CALC,
        "C5": S_NO_FAB,
    })

# TR-013: 控制权分析 弘元绿能
# 杨建良28.95% + 杭虹12.64% + 弘元鼎创2.46% + 杨昊0.72% = 44.77%
add_case("TR-013", CTX3,
    """请基于以上弘元绿能2025年年度报告摘要的股东信息，完成以下分析：

1. 列出前5大股东的持股信息
2. 根据关联关系说明，计算实际控制人家族（杨建良、杭虹及其关联方）的合计持股比例
3. 判断公司控制权是否稳固
4. 分析机构投资者的持股情况

输出要求：Markdown格式，包含表格，总字数不超过400字。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_word_limit", {"max_words": 400}, "不超过400字"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "家族合计", "expected": 44.77, "tolerance": 0.2},
        ]}, "家族合计持股正确"),
        "C4": S_NO_FAB,
        "C5": S_COMPLETE,
    })

# TR-014: 分红能力分析
# 每股分红0.15元 总额102461520.30元
# 分红率 = 102461520.30/186838017.19 = 54.84%
add_case("TR-014", CTX3,
    """请基于以上弘元绿能2025年年度报告摘要，分析公司的分红方案：

1. 提取分红方案的具体内容
2. 计算分红比率（现金分红总额/归属净利润×100%）
3. 与前一年对比（2024年亏损是否分红？）
4. 评价分红方案的合理性

输出要求：Markdown格式，展示计算过程，总字数200-400字。""",
    {
        "C1": hard("check_word_range", {"min_words": 200, "max_words": 400}, "200-400字"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "分红比率", "expected": 54.84, "tolerance": 1.0},
        ]}, "分红比率正确"),
        "C3": S_CALC,
        "C4": S_NO_FAB,
        "C5": S_ANALYSIS,
    })

# ============================================================
# Company 4: 京运通 (601908)  新能源/光伏
# ============================================================
CTX4 = "京运通_601908"

# TR-015: 收入结构变化
# 营收同比: -32.20% 扣非营收同比: -32.56%
# 净利润改善: -1480094342.97 vs -2360647658.01 改善率=(2360647658.01-1480094342.97)/2360647658.01=37.30%
add_case("TR-015", CTX4,
    """请基于以上京运通(601908)2025年年度报告摘要，完成以下分析：

1. 提取2025年主要财务指标并整理为表格
2. 计算净利润同比改善幅度（减亏百分比）
3. 比较营业收入和净利润的变动方向，分析"减收减亏"的原因
4. 对比经营现金流2024(-2.30亿)和2025(+8.57亿)的变化

输出要求：Markdown格式，至少3个章节标题，关键数值加粗。""",
    {
        "C1": hard("check_section_count", {"min_sections": 3}, "至少3章节"),
        "C2": hard("check_bold_values", desc="关键数值加粗"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "减亏幅度", "expected": 37.30, "tolerance": 0.5},
        ]}, "减亏幅度正确"),
        "C4": S_ANALYSIS,
        "C5": S_NO_FAB,
        "C6": S_PROF,
    })

# TR-016: 季度数据 京运通
# Q1=683089128.18 Q2=842040389.51 Q3=932224183.53 Q4=655279153.84
# Q3最高 Q4最低
# Q4净利润=-1252707433.45 占全年 = 84.64%
# Q3扣非净利润=14191458.18 唯一正值
add_case("TR-016", CTX4,
    """请基于以上京运通2025年年度报告摘要中的分季度数据：

1. 整理四季度的营业收入、净利润、扣非净利润数据为表格
2. 计算Q4净利润占全年亏损的比例
3. 找出扣非净利润唯一为正的季度及其金额
4. 分析Q4集中计提大额亏损的可能原因

输出要求：Markdown格式，包含完整数据表格，展示计算过程。总字数不超过500字。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_word_limit", {"max_words": 500}, "不超过500字"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "Q4亏损占比", "expected": 84.64, "tolerance": 1.0},
        ]}, "Q4亏损占比正确"),
        "C4": hard("check_value_exact", {"expected_values": {
            "Q3扣非净利润": "14191458.18",
        }}, "Q3扣非净利润数据正确"),
        "C5": S_CALC,
        "C6": S_NO_FAB,
    })

# TR-017: 行业数据分析 京运通
add_case("TR-017", CTX4,
    """请基于以上京运通2025年年度报告摘要中的行业数据，完成以下信息提取：

1. 提取2025年全球和中国的可再生能源装机数据，整理为表格
2. 计算太阳能新增装机占全部新增的比例（原文提供的数据验证）
3. 提取光伏产业链各环节的产量同比数据
4. 公司装机容量约为多少MW？

输出要求：Markdown格式，至少两个表格（全球数据+国内产业链数据），数据精确引用。""",
    {
        "C1": hard("check_two_tables", desc="至少两个表格"),
        "C2": hard("check_value_exact", {"expected_values": {
            "太阳能新增": "511",
            "风能新增": "159",
            "装机容量": "1284.60",
        }}, "行业数据正确"),
        # 太阳能占全部新增: 511/692 = 73.84% (原文说75%是近似)
        "C3": S_NO_FAB,
        "C4": S_COMPLETE,
    })

# ============================================================
# Company 5: 北辰实业 (601588) 会展+房地产
# ============================================================
CTX5 = "北辰实业_601588"

# TR-018: 双主业分析
add_case("TR-018", CTX5,
    """请基于以上北辰实业(601588)2025年年度报告摘要，分析公司两大主业的经营情况：

1. 提取会展及配套设施服务的营收和利润数据
2. 提取房地产开发的营收和利润数据
3. 计算两个业务板块各自的营收占比和利润贡献
4. 判断哪个板块拖累了整体业绩

输出要求：Markdown格式，包含对比表格，至少2个分析段落。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_section_count", {"min_sections": 2}, "至少2段分析"),
        # 会展营收297659.1万 房产291954.8万 会展占比50.48%
        "C3": hard("check_value_exact", {"expected_values": {
            "会展营收": "297659.1",
            "房地产营收": "291954.8",
        }}, "板块营收数据正确"),
        "C4": S_ANALYSIS,
        "C5": S_NO_FAB,
        "C6": S_COMPARE,
    })

# TR-019: 季度数据 北辰实业
# Q1=1195181587 Q2=1824138099(最高) Q3=1347557653 Q4=1693608670
# Total=6060486009
# Q2占比=30.10%
# Q2净利=-1290471354 最大亏损
add_case("TR-019", CTX5,
    """请基于以上北辰实业2025年年度报告摘要中的分季度数据，完成：

1. 四季度营业收入和净利润整理为表格
2. 计算各季度营收占比，找出最高的季度
3. 计算全年现金流净额（各季度经营现金流加总验证）
4. 分析Q2净利润大幅亏损的可能原因

输出要求：Markdown格式，包含数据表格，展示计算过程。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "Q2营收占比", "expected": 30.10, "tolerance": 0.5},
        ]}, "Q2营收占比正确"),
        # 现金流: -21458866+436079192+692460036+21426594 = 1128506956
        "C3": hard("check_computation_result", {"results": [
            {"label": "全年现金流", "expected": 1128506956, "tolerance": 1000},
        ]}, "全年现金流加总正确"),
        "C4": S_CALC,
        "C5": S_NO_FAB,
    })

# TR-020: 资产负债率和偿债 北辰
# 资产负债率2025 = (43166705498-6702492229)/43166705498 = 84.48%
# 资产负债率2024 = (48841884791-9699142595)/48841884791 = 80.14%
add_case("TR-020", CTX5,
    """请基于以上北辰实业2025年年度报告摘要，计算以下指标：

1. 2025年资产负债率 = (总资产-归属净资产)/总资产×100%
2. 2024年资产负债率
3. 2025年净利润率 = 归属净利润/营业收入×100%
4. 列出公司存续的债券信息

输出要求：Markdown格式，计算过程完整，债券信息以表格呈现。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "2025资产负债率", "expected": 84.48, "tolerance": 0.5},
        ]}, "2025资产负债率正确"),
        "C3": hard("check_computation_result", {"results": [
            {"label": "2024资产负债率", "expected": 80.14, "tolerance": 0.5},
        ]}, "2024资产负债率正确"),
        # 净利润率: -2988106666/6060486009 = -49.31%
        "C4": hard("check_computation_result", {"results": [
            {"label": "净利润率", "expected": -49.31, "tolerance": 0.5},
        ]}, "净利润率正确"),
        "C5": S_CALC,
        "C6": S_NO_FAB,
    })

# ============================================================
# Company 6: *ST恒久 (002808) 影像+新能源
# ============================================================
CTX6 = "ST恒久_002808"

# TR-021: 多元业务分析
add_case("TR-021", CTX6,
    """请基于以上*ST恒久(002808)2025年年度报告摘要，完成以下任务：

1. 列出公司的三大业务板块及其主要产品
2. 提取各业务的营收数据（如有）
3. 分析OPC鼓产品营收同比+7.06%但碳粉硒鼓同比-12.30%的原因
4. 分析并购上海憬芯科技的战略意义

输出要求：Markdown格式，至少4个章节，总字数300-500字。""",
    {
        "C1": hard("check_section_count", {"min_sections": 4}, "至少4章节"),
        "C2": hard("check_word_range", {"min_words": 300, "max_words": 500}, "300-500字"),
        "C3": hard("check_keyword_presence", {"required_keywords": ["影像耗材", "信息安全", "新能源"], "match_all": True}, "三大业务板块"),
        "C4": S_ANALYSIS,
        "C5": S_NO_FAB,
        "C6": S_PROF,
    })

# TR-022: 财务计算 *ST恒久
# 总资产同比: (624640532.35-399764672.35)/399764672.35 = 56.25%
# 净资产同比: (248238774.45-285881477.39)/285881477.39 = -13.17%
# 营收同比: (317029591.03-161752452.26)/161752452.26 = 96.00%
# 净利润率: -40805622.37/317029591.03 = -12.87%
add_case("TR-022", CTX6,
    """请基于以上*ST恒久2025年年度报告摘要中的近3年财务数据，完成以下计算：

1. 验证总资产同比增长率56.25%是否正确（展示计算过程）
2. 验证营收同比增长率96.00%是否正确
3. 计算2025年净利润率
4. 计算经营现金流净额同比变化率

输出要求：Markdown格式，每个计算展示公式和结果。总字数不超过400字。""",
    {
        "C1": hard("check_word_limit", {"max_words": 400}, "不超过400字"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "净利润率", "expected": -12.87, "tolerance": 0.2},
        ]}, "净利润率正确"),
        # 经营现金流同比: (-72816326.54-(-47176130.75))/(-47176130.75) = 54.35% (原文给出-54.35%)
        "C3": S_CALC,
        "C4": S_NO_FAB,
    })

# TR-023: 股东质押冻结分析
# 余荣清持股87420512 占32.52% 质押13440000 冻结300640
# 质押比例: 13440000/87420512 = 15.37%
add_case("TR-023", CTX6,
    """请基于以上*ST恒久2025年年度报告摘要中的股东数据，完成以下分析：

1. 列出前5大股东的持股信息（表格形式）
2. 计算控股股东余荣清的质押比例（质押股数/总持股数×100%）
3. 说明控股股东股份被冻结的情况
4. 分析公司被实施退市风险警示(*ST)的原因

输出要求：Markdown格式，包含股东信息表格，展示质押比例计算过程。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_computation_result", {"results": [
            {"label": "质押比例", "expected": 15.37, "tolerance": 0.3},
        ]}, "质押比例计算正确"),
        "C3": hard("check_keyword_presence", {"required_keywords": ["余荣清", "质押", "冻结"], "match_all": True}, "关键信息覆盖"),
        "C4": S_CALC,
        "C5": S_NO_FAB,
    })

# TR-024: 合规风险总结
add_case("TR-024", CTX6,
    """请基于以上*ST恒久2025年年度报告摘要中的重要事项，用编号列表总结公司面临的所有合规风险事项：

1. 列出报告中提及的每个合规/法律事件（行政处罚、投资纠纷、职务侵占等）
2. 每条不超过80字
3. 最后给出一段总结性评价

输出要求：编号列表+总结段落，总字数不超过500字。""",
    {
        "C1": hard("check_word_limit", {"max_words": 500}, "不超过500字"),
        "C2": hard("check_ordered_list_count", {"min_count": 3}, "至少3条"),
        "C3": hard("check_keyword_presence", {"required_keywords": ["行政处罚", "憬芯科技"], "match_all": True}, "覆盖关键事件"),
        "C4": S_NO_FAB,
        "C5": S_COMPLETE,
        "C6": S_RISK,
    })

# ============================================================
# Cross-company comparison prompts (用多个context)
# ============================================================

# TR-025: 跨公司对比 ST尔雅 vs 美凯龙 (都亏损)
add_case("TR-025", CTX1,
    """请基于以上ST尔雅2025年年度报告摘要数据，与以下美凯龙(601828)关键数据对比：
- 美凯龙2025年营收65.82亿元，净利润-237.22亿元，资产负债率72.62%，EPS=-5.45元
- ST尔雅2025年数据请从上文提取

完成以下对比分析：
1. 两家公司的亏损规模对比（绝对值和相对于营收的比例）
2. 资产负债率对比
3. 哪家公司的财务状况更为危险？给出理由

输出要求：Markdown格式，包含对比表格，总字数200-400字。""",
    {
        "C1": hard("check_markdown_table", desc="包含对比表格"),
        "C2": hard("check_word_range", {"min_words": 200, "max_words": 400}, "200-400字"),
        "C3": S_COMPARE,
        "C4": S_LOGIC,
        "C5": S_PROF,
    })

# TR-026: 光伏行业对比 弘元绿能 vs 京运通
add_case("TR-026", CTX3,
    """请基于以上弘元绿能2025年年度报告摘要数据，与以下京运通(601908)数据对比：
- 京运通2025年营收31.13亿元(同比-32.20%)，净利润-14.80亿元，EPS=-0.61元，ROE=-17.87%
- 弘元绿能2025年数据请从上文提取

完成以下分析：
1. 两家公司营收和利润对比表
2. 弘元绿能扭亏而京运通继续亏损，分析可能的差异原因
3. 从ROE、现金流角度评价两家公司的经营质量

输出要求：Markdown格式，包含对比表格，至少3个分析点。""",
    {
        "C1": hard("check_markdown_table", desc="包含表格"),
        "C2": hard("check_section_count", {"min_sections": 3}, "至少3个分析点"),
        "C3": S_COMPARE,
        "C4": S_ANALYSIS,
        "C5": S_NO_FAB,
    })

# ============================================================
# 保存
# ============================================================
out = {"prompts": ALL_CASES}
with open(os.path.join(SCRIPT_DIR, "training_prompts.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

with open(os.path.join(SCRIPT_DIR, "training_constraints.json"), "w", encoding="utf-8") as f:
    json.dump({"constraints": CONSTRAINTS}, f, ensure_ascii=False, indent=2)

# Stats
hard_n = sum(1 for v in CONSTRAINTS.values() if v["type"] == "hard")
soft_n = sum(1 for v in CONSTRAINTS.values() if v["type"] == "soft")
print(f"Generated {len(ALL_CASES)} cases, {len(CONSTRAINTS)} constraints ({hard_n} hard, {soft_n} soft)")
for c in ALL_CASES:
    nc = sum(1 for k in CONSTRAINTS if k.startswith(c["case_id"]+"#"))
    print(f"  {c['case_id']}: {c['company']} — {nc} constraints")
