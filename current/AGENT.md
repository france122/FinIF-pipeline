# FinIF Benchmark — Current Status & Next Steps

## Project Overview

FinIF (Financial Instruction Following) Benchmark：金融指令遵循能力评测。
目标是测量大模型（GPT-4o, GPT-5）和小模型（Qwen3-8B）在金融场景下的**计算、推理、判断**能力差异。

- 54 个 case，分三层：T1（数据提取+计算, 27个）、T2（分析+洞察, 15个）、T3（合规核验+推断, 12个）
- 227 个约束（160 hard + 67 soft）
- Hard constraint 由 `checkers.py` 中的 Python 函数执行
- Soft constraint 由 LLM judge（GPT-4o）评判

## File Structure

```
current/
├── benchmark_all.json        # 54 cases: case_id, prompt, context
├── benchmark_all.jsonl        # 同上，逐行格式（供外部平台使用）
├── eval_config_all.json       # 227 约束配置 {"constraints": {"T1.1-001#C1": {...}, ...}}
├── checkers.py                # Hard constraint checker 函数库（16 种 checker）
├── eval_responses.py          # 评测脚本：hard check + LLM judge
├── gen_responses.py           # 回复生成脚本（调用 gpt_call_all.py）
├── upgrade_benchmark.py       # query 升级脚本（记录从 v1→v2 的改写逻辑）
├── qwen-3-output.jsonl        # Qwen3-8B 原始回复（外部生成）
├── viewer.html / viewer.py    # 可视化工具
└── output/
    ├── responses_*.jsonl       # 三模型回复（GPT-4o, GPT-5, Qwen3-8B）
    └── scores_*.json           # 三模型评分结果
```

## Current Evaluation Results

| Model | T1 | T2 | T3 | Overall |
|---|---|---|---|---|
| GPT-5 | 71.6% | 75.7% | 83.6% | **75.4%** |
| Qwen3-8B | 70.7% | 70.7% | 77.2% | **72.1%** |
| GPT-4o | 61.4% | 80.7% | 81.9% | **71.3%** |

**问题：三模型差距太小（GPT-5 vs Qwen3-8B 仅 3.3pp），benchmark 无法有效区分大小模型。**

## Root Cause Analysis: Hard Checker 设计缺陷

这是当前最核心的问题。分析详情：

### 1. 72.5% 的 hard constraint 三模型全过，零区分度
160 个 hard constraint 中有 116 个三模型全部 PASS，完全没有区分能力。

### 2. `check_has_calculation`（62 个）— 只检测有没有算式
这个 checker 只看输出中是否包含 `+`, `-`, `×`, `/`, `=` 等运算符号。任何模型只要 show work 就能过，完全不验证计算结果是否正确。GPT-4o pass rate 98.4%, Qwen3-8B 90.3%。

### 3. `check_computation_result`（40 个）— 做的是"关键词+数字共现"而非计算验证
这个 checker 的逻辑是：在输出中找到包含 `label`（如"涨幅空间"）的行，然后看该行是否有一个数字落在 `expected ± tolerance` 范围内。

**致命问题**：它测的是**用词**而非**计算能力**。例如：
- GPT-5 算出了正确答案 `11.83%`，但它写的是"距涨停约 11.83%"而不是"涨幅空间 11.83%"，label "涨幅空间" 匹配不上 → **FAIL**
- Qwen3-8B 写了"上涨空间百分比 ≈ 11.83%"，包含"空间" → **PASS**
- 同一个正确答案，因为用词不同，结果相反

### 4. `check_value_exact`（10 个）— 同样的 label 匹配问题
要求 key-value 同行出现，但不同模型对同一数据的表述方式不同。

### 5. 所有模型都 FAIL 的约束（11 个）— 约束设计本身有问题
包括 `check_word_limit`（字数限制太严）、`check_ranking`（排序检测逻辑有 bug）、`check_table_sort_alpha` 等。

### 6. Per-checker pass rate summary

| Checker | Count | GPT-4o | GPT-5 | Qwen3-8B | 区分度 |
|---|---|---|---|---|---|
| check_has_calculation | 62 | 98.4% | 87.1% | 90.3% | 低 |
| check_computation_result | 40 | 75.0% | 70.0% | 77.5% | 极低（Qwen > GPT-5） |
| check_markdown_table | 12 | 83.3% | 75.0% | 100.0% | 反向（小模型更高） |
| check_value_exact | 10 | 60.0% | 80.0% | 80.0% | 反向 |
| check_arithmetic_correct | 7 | 100% | 100% | 100% | 零 |
| check_field_coverage | 6 | 100% | 100% | 100% | 零 |
| check_keyword_presence | 6 | 100% | 100% | 100% | 零 |

## What Needs to Be Done

### Priority 1: 重写 Hard Checker（最关键）

当前 checker 本质上是**字符串匹配测试**，不是**推理能力测试**。需要彻底重新设计：

**A. `check_computation_result` 需要改为真正的计算验证：**
- 不应该依赖 label 关键词匹配
- 应该从 context 中提取原始数据，独立计算 expected 值，然后在输出中搜索该数值（不依赖 label）
- 或者：constraint 中直接给出 expected 数值范围，在整个输出中搜索是否出现该数值

**B. `check_has_calculation` 需要升级为 `check_calculation_correct`：**
- 不能只检测"有没有算式"，要验证"算式结果是否正确"
- 方案：用 Python `eval()` 或正则提取算式并验算
- 或者：改为 soft constraint 交给 LLM judge 验证

**C. 减少零区分度约束：**
- `check_field_coverage`, `check_keyword_presence`, `check_arithmetic_correct` 全部三模型 100%，应删除或替换
- `check_markdown_table` 对小模型反而更友好，应删除

### Priority 2: 约束类型重新分配

当前 160 hard / 67 soft 的比例不合理。建议：
- 将无法用代码精确验证的"计算正确性"类约束改为 soft（交给 LLM judge）
- Hard constraint 只保留可以 100% 确定性验证的（如：数值精确匹配、格式检查）
- 目标：hard 约束少而精，每个都有区分度

### Priority 3: 增加真正有区分度的约束

需要新增能区分大小模型的约束类型：
- **多步推理链验证**：要求模型完成 A→B→C 的推导，验证中间步骤
- **反事实推理**：如"如果利率上调 50bp 而非 25bp，影响如何"
- **矛盾检测**：在 context 中埋入矛盾数据，看模型能否识别
- **定量判断**：给出计算结果后的定性判断（如"属于强势/弱势"），小模型往往判断失误

## Dependencies

- `gen_responses.py` 依赖项目根目录的 `gpt_call_all.py`（minimax API 代理调用）
- GPT-5 是推理模型，`max_tokens` 需设为 16384+（已在 gen_responses.py 中处理）
- LLM judge 使用 GPT-4o (`eval_responses.py` 中 `JUDGE_MODEL = "gpt-4o-2024-11-20"`)

## Key Design Decisions

- **Context 不变**：54 个 case 的原始文档内容（context 字段）保持不变，只修改 query
- **Query 升级模式**：A（提取+计算）、B（分析+洞察）、C（核验+推断）
- **升级脚本**：`upgrade_benchmark.py` 包含完整的 NEW_QUERIES 和 NEW_CONSTRAINTS 字典，记录了所有改写逻辑
