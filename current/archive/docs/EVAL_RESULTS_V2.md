# FinIF Benchmark V2 评测结果

## Benchmark 概况

- **Case 数量**: 100
- **约束总数**: 558（372 hard + 186 soft）
- **双轴评测**: Compliance 397（附加要求约束）+ Correctness 161（C6计算 + query正文C1/C2）
- **评测层级**: T1（信息提取）、T2（分析评估）、T3（计算推导）
- **Judge 模型**: deepseek-v4-flash
- **评测时间**: 2026-05-08
- **变更说明**: V2 相对 V1 重构了约束体系（26 标签 × 4-slot 采样），修复了数据质量问题，新增 Compliance/Correctness 双轴评测

### L2 类别分布


| L1  | L2   | 描述       | Case 数 |
| --- | ---- | -------- | ------ |
| T1  | T1.1 | 金融查询检索   | 19     |
| T1  | T1.2 | 证券公告解读   | 12     |
| T1  | T1.3 | 行政处罚决定书  | 14     |
| T2  | T2.1 | 财务业绩分析   | 8      |
| T2  | T2.2 | 招股说明书分析  | 6      |
| T2  | T2.3 | 市场趋势分析   | 6      |
| T2  | T2.4 | 融资融券分析   | 7      |
| T2  | T2.5 | 资金流向分析   | 6      |
| T3  | T3.1 | 结构化计算    | 7      |
| T3  | T3.2 | 两融绕标推导   | 8      |
| T3  | T3.3 | 股东权益变动计算 | 7      |


### 约束标签分布


| 大类         | 标签      | 数量  | 说明         |
| ---------- | ------- | --- | ---------- |
| Format     | F1 章节   | 31  | 章节数/标题层级   |
| Format     | F2 列表   | 22  | 有序列表项数     |
| Format     | F3 表格   | 23  | 表格存在/禁止    |
| Format     | F5 引用块  | 14  | 引用块数量      |
| Format     | F6 首尾   | 45  | 首行/末行/首词格式 |
| Format     | F7 特殊   | 4   | 复选框等特殊格式   |
| Number     | N1 字数   | 54  | 字数范围/上限    |
| Number     | N2 元素计数 | 46  | 句子数/段落数    |
| Number     | N3 精度   | 9   | 小数位数       |
| Linguistic | L1 关键词  | 22  | 关键词存在/风险提示 |
| Linguistic | L2 禁止模式 | 19  | 禁止特定表达     |
| Linguistic | L3 术语   | 22  | 术语规范       |
| Linguistic | L4 金融符号 | 13  | 货币单位/百分号   |
| Style      | S1 语气   | 14  | 正式/客观      |
| Style      | S2 角色   | 32  | 分析师/投资者视角  |
| Style      | S3 连贯性  | 5   | 结论先行等      |
| Style      | S4 修辞   | 3   | 修辞手法       |
| Content    | C1 覆盖度  | 11  | 内容完整性      |
| Content    | C2 证据   | 27  | 数据支撑       |
| Content    | C3 视角   | 11  | ESG/多维度视角  |
| Content    | C5 条件触发 | 8   | 条件逻辑       |
| Content    | C6 计算   | 123 | 数值计算结果     |


### Hard Checker 分布


| Checker                   | 数量  | 说明             |
| ------------------------- | --- | -------------- |
| check_computation_result  | 52  | 数值计算结果校验       |
| check_word_range          | 29  | 字数范围约束         |
| check_sentence_count      | 26  | 句子数约束          |
| check_word_limit          | 25  | 字数上限约束         |
| check_paragraph_count     | 20  | 段落数约束          |
| check_markdown_table      | 15  | Markdown 表格存在性 |
| check_value_exact         | 14  | 精确数值匹配         |
| check_section_count       | 14  | 章节数量           |
| check_blockquote_count    | 14  | 引用块数量          |
| check_ordered_list_count  | 14  | 有序列表项数         |
| check_first_line_format   | 12  | 首行格式           |
| check_forbidden_pattern   | 12  | 禁止模式           |
| check_risk_disclaimer     | 12  | 风险提示声明         |
| check_keyword_presence    | 10  | 关键词存在          |
| check_first_word          | 10  | 首词约束           |
| check_first_last_line     | 10  | 首尾行约束          |
| check_decimal_places      | 9   | 小数位数           |
| check_value_derivation    | 9   | 数值推导过程         |
| check_heading_depth       | 9   | 标题层级           |
| check_no_table            | 8   | 禁止表格           |
| check_conditional_trigger | 8   | 条件触发           |
| check_no_list             | 8   | 禁止列表           |
| check_currency_format     | 8   | 货币单位格式         |
| check_heading_level       | 8   | 标题级别           |
| check_no_percent          | 5   | 禁止百分号          |
| check_first_person        | 5   | 第一人称           |
| check_checkbox_format     | 4   | 复选框格式          |
| check_no_arabic_numerals  | 2   | 禁止阿拉伯数字        |


---

## 评测配置

与 V1 相同，详见 `EVAL_RESULTS.md` 评测配置章节。

---

## 模型评分

### 总表（按 H+S 降序）


| Model                | Hard      | Soft      | H+S       | Comp      | Corr      | T1        | T2        | T3        |
| -------------------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- | --------- |
| ds-v4-pro-thinking   | 86.8%     | 82.3%     | **85.3%** | **89.7%** | 74.5%     | 85.6%     | **86.3%** | **82.3%** |
| ds-v4-flash          | 83.9%     | **83.3%** | 83.7%     | 85.4%     | **79.5%** | **84.5%** | 82.9%     | 81.8%     |
| ds-v4-flash-thinking | **87.1%** | 76.9%     | 83.7%     | 87.4%     | 74.5%     | 85.9%     | 84.0%     | 77.7%     |
| ds-v4-pro            | 85.5%     | 78.0%     | 83.0%     | 87.2%     | 72.7%     | 83.1%     | 83.8%     | 81.2%     |


### 双轴分维度细分（Hard/Soft × Comp/Corr）


| 维度              | flash | flash-thinking | pro   | pro-thinking |
| --------------- | ----- | -------------- | ----- | ------------ |
| Hard-Comp (297) | 84.5% | 88.6%          | 88.6% | 88.9%        |
| Hard-Corr (75)  | 81.3% | 81.3%          | 73.3% | 78.7%        |
| Soft-Comp (100) | 88.0% | 84.0%          | 83.0% | 92.0%        |
| Soft-Corr (86)  | 77.9% | 68.6%          | 72.1% | 70.9%        |


**注**: Hard checker 为确定性评判（代码校验），Soft 由 LLM judge 评判。flash 两次评测 Hard-Corr 完全一致（81.3%），Soft-Corr 波动约 5-10pp，说明 Correctness 差异主要来自 judge 噪声而非模型能力差异。

### L2 细分得分（H+S）


| L2   | ds-v4-flash | flash-thinking | ds-v4-pro | pro-thinking |
| ---- | ----------- | -------------- | --------- | ------------ |
| T1.1 | 87.2%       | 85.6%          | 86.0%     | **89.3%**    |
| T1.2 | 83.6%       | **88.6%**      | 86.4%     | 86.7%        |
| T1.3 | 81.5%       | **83.9%**      | 76.5%     | 79.8%        |
| T2.1 | 75.4%       | **84.2%**      | 75.4%     | 76.2%        |
| T2.2 | 90.0%       | 87.2%          | 90.6%     | **93.3%**    |
| T2.3 | 75.0%       | 77.8%          | 81.1%     | **88.3%**    |
| T2.4 | **85.7%**   | 81.0%          | 83.8%     | 83.3%        |
| T2.5 | 90.6%       | 90.6%          | 91.1%     | **93.9%**    |
| T3.1 | **81.9%**   | 79.5%          | 79.5%     | 79.0%        |
| T3.2 | **81.7%**   | 74.2%          | 79.2%     | 80.8%        |
| T3.3 | 81.9%       | 80.0%          | 85.2%     | **87.1%**    |


### Hard Checker 通过率


| Checker                   | 总数  | flash      | flash-think | pro        | pro-think  |
| ------------------------- | --- | ---------- | ----------- | ---------- | ---------- |
| check_computation_result  | 52  | 86.5%      | 86.5%       | 78.8%      | 80.8%      |
| check_word_range          | 29  | **69.0%**  | 62.1%       | 62.1%      | 58.6%      |
| check_sentence_count      | 26  | 92.3%      | **100.0%**  | **100.0%** | 96.2%      |
| check_word_limit          | 25  | 84.0%      | 92.0%       | 88.0%      | **100.0%** |
| check_paragraph_count     | 20  | 35.0%      | 45.0%       | **55.0%**  | 50.0%      |
| check_markdown_table      | 15  | 93.3%      | **100.0%**  | **100.0%** | **100.0%** |
| check_value_exact         | 14  | 92.9%      | 92.9%       | 85.7%      | **100.0%** |
| check_section_count       | 14  | **92.9%**  | 85.7%       | 57.1%      | 71.4%      |
| check_blockquote_count    | 14  | 92.9%      | 92.9%       | 92.9%      | 92.9%      |
| check_ordered_list_count  | 14  | **100.0%** | **100.0%**  | 92.9%      | 92.9%      |
| check_first_line_format   | 12  | 100.0%     | 100.0%      | 100.0%     | 100.0%     |
| check_forbidden_pattern   | 12  | 91.7%      | 91.7%       | **100.0%** | **100.0%** |
| check_risk_disclaimer     | 12  | 91.7%      | **100.0%**  | **100.0%** | 91.7%      |
| check_keyword_presence    | 10  | 100.0%     | 100.0%      | 100.0%     | 100.0%     |
| check_first_word          | 10  | 90.0%      | **100.0%**  | **100.0%** | **100.0%** |
| check_first_last_line     | 10  | 100.0%     | 100.0%      | 100.0%     | 100.0%     |
| check_decimal_places      | 9   | **100.0%** | **100.0%**  | 88.9%      | **100.0%** |
| check_value_derivation    | 9   | **33.3%**  | **33.3%**   | 22.2%      | **33.3%**  |
| check_heading_depth       | 9   | 77.8%      | 88.9%       | **100.0%** | **100.0%** |
| check_no_table            | 8   | 100.0%     | 100.0%      | 100.0%     | 100.0%     |
| check_conditional_trigger | 8   | 87.5%      | 87.5%       | **100.0%** | 87.5%      |
| check_no_list             | 8   | 100.0%     | 100.0%      | 100.0%     | 100.0%     |
| check_currency_format     | 8   | 87.5%      | 75.0%       | **100.0%** | 87.5%      |
| check_heading_level       | 8   | 62.5%      | 75.0%       | **100.0%** | **100.0%** |
| check_no_percent          | 5   | 40.0%      | **100.0%**  | 80.0%      | 80.0%      |
| check_first_person        | 5   | **100.0%** | **100.0%**  | 80.0%      | **100.0%** |
| check_checkbox_format     | 4   | 75.0%      | **100.0%**  | **100.0%** | **100.0%** |
| check_no_arabic_numerals  | 2   | 50.0%      | **100.0%**  | **100.0%** | **100.0%** |


---

## 分析

### 1. Thinking 模式影响


| 对比                      | Hard   | Soft   | H+S    | Comp   | Corr   | T3     |
| ----------------------- | ------ | ------ | ------ | ------ | ------ | ------ |
| flash-thinking vs flash | +3.2pp | -6.4pp | +0.0pp | +2.0pp | -5.0pp | -4.1pp |
| pro-thinking vs pro     | +1.3pp | +4.3pp | +2.3pp | +2.5pp | +1.8pp | +1.1pp |


- **Hard Compliance 一致提升**：Thinking 帮助模型更精确地遵循格式/数值约束（Hard-Comp: flash +4.1pp, pro +0.3pp）
- **Hard Correctness**：flash 完全一致（81.3%），pro 提升 +5.4pp — 说明 thinking 对计算准确性有正面或中性影响
- **Soft 评判噪声显著**：同一模型（flash）在两次评测中 Soft-Corr 波动达 9pp，Soft-Comp 波动 4pp。Correctness 的"下降"主要来自 LLM judge 噪声

### 2. Flash vs Pro


| 指标                 | flash | pro   | Δ      |
| ------------------ | ----- | ----- | ------ |
| Hard               | 83.9% | 85.5% | +1.6pp |
| Soft               | 83.3% | 78.0% | -5.3pp |
| H+S                | 83.7% | 83.0% | -0.7pp |
| Comp               | 85.4% | 87.2% | +1.8pp |
| computation_result | 86.5% | 78.8% | -7.7pp |


Pro 在 Hard-Comp 上与 flash 持平（88.6%），但 check_computation_result 显著低于 flash（78.8% vs 86.5%），拉低了 Correctness。Pro 在结构类 checker（heading_level, heading_depth）上全部 100%，优于 flash。

### 3. 约束难度梯度

按 4 模型平均 Hard 通过率排序：


| 难度  | Checker                                                                     | 4模型平均 | 特点            |
| --- | --------------------------------------------------------------------------- | ----- | ------------- |
| 易   | first_line_format / keyword_presence / first_last_line / no_table / no_list | 100%  | 所有模型全通过       |
| 中   | sentence_count / markdown_table / blockquote_count                          | 95%+  | 结构类普遍擅长       |
| 中   | computation_result                                                          | 83.2% | 数值计算，区分度大     |
| 难   | paragraph_count                                                             | 46.3% | 段落数控制困难       |
| 难   | word_range                                                                  | 62.8% | 字数范围精确控制      |
| 难   | value_derivation                                                            | 30.6% | 推导过程校验，所有模型弱项 |


**核心发现**：V2 的 IF 约束区分度更高 — paragraph_count（46.3%）和 word_range（62.8%）成为新的难点 checker，比 V1 中仅靠 computation_result 区分模型更加多元。

---

## V1 → V2 对比


| 指标               | V1 (441 约束) | V2 (558 约束) | 变化     |
| ---------------- | ----------- | ----------- | ------ |
| ds-v4-flash H+S  | 82.4%       | 83.7%       | +1.3pp |
| ds-v4-flash Hard | 81.8%       | 83.9%       | +2.1pp |
| ds-v4-flash T1   | 83.9%       | 84.5%       | +0.6pp |
| ds-v4-flash T2   | 81.6%       | 82.9%       | +1.3pp |
| ds-v4-flash T3   | 80.3%       | 81.8%       | +1.5pp |


V2 新增约束以 IF（Compliance）类为主（N1/N2/F1-F6/L1-L4 等），ds-v4-flash 在新增 IF 约束上表现良好。约束从 441→558 增加 26.5%，但 H+S 仅上升 1.3pp，说明 benchmark 难度保持稳定。

---

## 待补充

- ds-v4-flash
- ds-v4-flash-thinking
- ds-v4-pro
- ds-v4-pro-thinking
- Qwen3 系列（qwen3-4b / 8b / 14b / 32b）
- GPT 系列（gpt-5 / 5.1 / 5.4）

