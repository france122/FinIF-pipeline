# FinIF Benchmark 评测结果

## Benchmark 概况

- **Case 数量**: 100
- **约束总数**: 441（185 hard / 256 soft）
- **评测层级**: T1（信息提取）、T2（分析评估）、T3（计算推导）
- **Judge 模型**: deepseek-v4-flash
- **评测时间**: 2026-05-07 ~ 2026-05-08

### L2 类别分布

| L1 | L2 | 描述 | Case 数 |
|----|-----|------|---------|
| T1 | T1.1 | 金融查询检索 | 19 |
| T1 | T1.2 | 证券公告解读 | 12 |
| T1 | T1.3 | 行政处罚决定书 | 14 |
| T2 | T2.1 | 财务业绩分析 | 8 |
| T2 | T2.2 | 招股说明书分析 | 6 |
| T2 | T2.3 | 市场趋势分析 | 6 |
| T2 | T2.4 | 融资融券分析 | 7 |
| T2 | T2.5 | 资金流向分析 | 6 |
| T3 | T3.1 | 结构化计算 | 7 |
| T3 | T3.2 | 两融绕标推导 | 8 |
| T3 | T3.3 | 股东权益变动计算 | 7 |

### Hard 约束 Checker 分布

| Checker | 数量 | 说明 |
|---------|------|------|
| check_computation_result | 118 | 数值计算结果校验 |
| check_value_exact | 25 | 精确数值匹配 |
| check_value_derivation | 10 | 数值推导过程校验 |
| check_json_format | 9 | JSON 格式检查 |
| check_markdown_table | 8 | Markdown 表格存在性 |
| check_word_range | 7 | 字数范围约束 |
| check_word_limit | 3 | 字数上限约束 |
| check_ranking | 1 | 排名约束 |
| check_ordered_list_count | 1 | 有序列表项数 |
| check_qa_format | 1 | 问答格式 |
| check_section_count | 1 | 章节数量 |
| check_table_sort_alpha | 1 | 表格字母排序 |

---

## 评测配置

### 通用设置

- **System Prompt**: 无（空字符串，不传 system message）
- **API Base URL**: `https://api.deepseek.com`（DeepSeek 官方 API）
- **stream**: False
- **重试策略**: 最多 3 次，遇到 429/rate limit 时指数退避（2^attempt 秒）

### DeepSeek 模型超参数

| 参数 | ds-v4-flash | ds-v4-flash-thinking | ds-v4-pro | ds-v4-pro-thinking |
|------|-------------|----------------------|-----------|---------------------|
| api_model | deepseek-v4-flash | deepseek-v4-flash | deepseek-v4-pro | deepseek-v4-pro |
| thinking | Off | On | Off | On |
| reasoning_effort | - | high | - | high |
| temperature | 0.7 | -（thinking 模式不设） | 0.7 | -（thinking 模式不设） |
| max_tokens | 8192 | - | 8192 | - |
| max_completion_tokens | - | 16384 | - | 16384 |
| extra_body | - | `{"thinking": {"type": "enabled"}, "reasoning_effort": "high"}` | - | `{"thinking": {"type": "enabled"}, "reasoning_effort": "high"}` |
| 生成并发 workers | 8 | 8 | 8 | 8 |

**注**: Thinking 模式下使用 `max_completion_tokens`（通过 extra_body 传递）替代 `max_tokens`，且不设置 temperature（由模型内部控制）。

### Qwen 模型超参数

#### 本地推理模型（qwen3-4b / qwen3-8b / qwen3-8b-thinking）

| 参数 | qwen3-4b | qwen3-8b | qwen3-8b-thinking |
|------|----------|----------|-------------------|
| 推理方式 | 本地 HuggingFace | 本地 HuggingFace | 本地 HuggingFace |
| 模型路径 | /home/zyz26/models/Qwen/Qwen3-4B | /home/zyz26/models/Qwen/Qwen3-8B | /home/zyz26/models/Qwen/Qwen3-8B |
| torch_dtype | float16 | float16 | float16 |
| device_map | auto | auto | auto |
| thinking | Off（`--disable-thinking`） | Off（`--disable-thinking`） | On（默认 thinking mode） |
| do_sample | False（greedy decoding） | False（greedy decoding） | False（greedy decoding） |
| temperature | 1.0（不生效，greedy） | 1.0（不生效，greedy） | 1.0（不生效，greedy） |
| top_p | 1.0 | 1.0 | 1.0 |
| top_k | 50 | 50 | 50 |
| max_new_tokens | 3072 | 3072 | 3072（补跑 10 条用 8192） |
| system_prompt | 无 | 无 | 无 |
| GPU 并行 | 8 分片，每张 GPU 1 进程 | 4 分片，每分片 2 GPU | 4 分片，每分片 2 GPU |
| 后处理 | - | - | 剥离 `<think>...</think>`；7 条未闭合 `</think>` 保留原始内容 |

**注**：`do_sample=False` 时 temperature/top_p/top_k 不生效，实际为 greedy decoding。

#### SiliconFlow API 模型（qwen3-14b / qwen3-32b）

| 参数 | qwen3-14b | qwen3-32b | qwen3-32b-thinking |
|------|-----------|-----------|---------------------|
| API 平台 | SiliconFlow | SiliconFlow | SiliconFlow |
| API Base URL | `https://api.siliconflow.cn/v1` | `https://api.siliconflow.cn/v1` | `https://api.siliconflow.cn/v1` |
| api_model | Qwen/Qwen3-14B | Qwen/Qwen3-32B | Qwen/Qwen3-32B |
| thinking | Off | Off | On |
| enable_thinking | 不设 | 不设 | `true`（extra_body） |
| temperature | 0.7 | 0.7 | -（thinking 模式不设） |
| max_tokens | 8192 | 8192 | 8192 |
| system_prompt | 无 | 无 | 无 |
| 生成并发 workers | 2（RPM 限制降速） | 8 | 8 |

### GPT 模型超参数

全部使用模型默认值，未主动设置任何参数。

| 参数 | gpt-5-2025-08-07 | gpt-5.1-2025-11-13 | gpt-5.4 | gpt-4o-2024-11-20 |
|------|-------------------|---------------------|---------|---------------------|
| API 平台 | OpenAI | OpenAI | OpenAI | OpenAI |
| temperature | 1.0 | 1.0 | 1.0 | 1.0 |
| top_p | 1.0 | 1.0 | 0.98 | 1.0 |
| max_output_tokens | None（无限制） | None | None | None |
| reasoning effort | **medium** | none | none | - |
| has_reasoning_output | **Yes** | No | No | No |
| output tokens (100 case) | 390,557 | 169,632 | 165,540 | - |
| system_prompt | 无 | 无 | 无 | 无 |

**注**: GPT-5 默认开启 `reasoning: medium`（带思考），output tokens 是其他模型的约 2 倍。GPT-5.1 和 GPT-5.4 都是 `reasoning: none`（non-thinking）。

### 评测（Judge）设置

| 参数 | 值 |
|------|-----|
| Judge 模型 | deepseek-v4-flash |
| Judge API | DeepSeek 官方 API（`https://api.deepseek.com`） |
| Judge api_model | deepseek-v4-flash |
| Judge thinking | Off |
| Judge temperature | 0 |
| Judge max_tokens | 256 |
| Judge system_prompt | 金融文档评测专家角色（见下方） |
| Soft judge 并发 workers | 15 |
| Hard checker | 本地 Python 函数（checkers.py），12 种 checker |
| Judge 重试 | 最多 3 次，429 时指数退避（2^attempt 秒） |

**Judge System Prompt**:
> 你是一个金融文档评测专家。判断模型输出是否满足给定的约束条件。
> 流程：1.引用证据 2.评估 3.判断。
> 规则：基于实际内容判断；有Markdown表格则表格约束PASS；有计算步骤则计算过程约束PASS；找不到才判FAIL。
> 输出JSON：{"pass": true/false, "reason": "一句话", "evidence": "摘录≤100字"}

**Judge User Prompt 结构**: 约束描述 → 评判标准（rubric）→ 原始上下文（截取前3000字）→ 模型输出（截取前4000字）→ 要求输出 JSON

**注**: 所有模型（包括 Qwen 系列）均使用同一 Judge 模型和参数评分，确保评分一致性。

---

## 模型评分

### 总表（按 H+S 降序）

| Model | Hard | H+S | T1 | T2 | T3 |
|-------|------|-----|-----|-----|-----|
| ds-v4-flash-thinking | 81.1% | **83.7%** | **86.2%** | 79.4% | **85.2%** |
| ds-v4-flash | **81.8%** | 82.4% | 83.9% | **81.6%** | 80.3% |
| ds-v4-pro-thinking | 79.5% | 81.1% | 80.2% | 79.4% | 85.4% |
| gpt-5.4 | 80.9% | 81.3% | 83.8% | 80.8% | 77.0% |
| ds-v4-pro | 78.3% | 80.9% | 81.7% | 81.1% | 79.1% |
| gpt-5-2025-08-07 | 83.1% | 80.3% | 81.6% | 81.1% | 76.7% |
| qwen3-32b | 80.0% | 78.0% | 80.1% | 78.6% | 72.9% |
| gpt-5.1-2025-11-13 | 77.8% | 77.6% | 79.0% | 78.0% | 74.1% |
| qwen3-14b | 76.7% | 75.3% | 77.9% | 73.5% | 72.8% |
| qwen3-8b-thinking | 76.6% | 72.6% | 75.7% | 70.3% | 70.0% |
| qwen3-8b | 72.5% | 71.2% | 73.5% | 69.0% | 69.5% |
| qwen3-4b | 76.1% | 69.0% | 72.9% | 64.7% | 67.6% |

### L2 细分得分（H+S）

| L2 | ds-v4-flash | flash-think | ds-v4-pro | pro-think | gpt-5 | gpt-5.1 | gpt-5.4 | qwen3-32b | qwen3-14b | qwen3-8b-think | qwen3-8b | qwen3-4b |
|----|-------------|-------------|-----------|-----------|-------|---------|---------|-----------|-----------|----------------|-----------|-----------|
| T1.1 | 86.2% | 87.5% | 78.9% | 81.2% | 84.5% | 75.2% | 84.3% | 78.7% | 81.0% | 75.5% | 81.9% | 75.1% |
| T1.2 | 86.9% | 83.6% | 86.2% | 81.9% | 77.4% | 89.2% | 85.3% | 84.3% | 79.9% | 77.6% | 76.0% | 84.6% |
| T1.3 | 84.4% | 86.5% | 81.8% | 77.4% | 81.2% | 75.6% | 81.8% | 78.5% | 72.0% | 74.2% | 59.9% | 59.9% |
| T2.1 | 78.8% | 74.6% | 74.6% | 67.3% | 79.4% | 75.0% | 74.0% | 71.5% | 69.4% | 62.9% | 76.7% | 59.6% |
| T2.2 | 87.5% | 79.2% | 87.5% | 91.7% | 87.5% | 95.8% | 87.5% | 91.7% | 87.5% | 83.3% | 70.8% | 79.2% |
| T2.3 | 100.0% | 95.8% | 91.7% | 96.7% | 95.8% | 70.8% | 88.3% | 87.5% | 79.2% | 80.0% | 71.7% | 70.8% |
| T2.4 | 74.0% | 73.3% | 74.0% | 70.5% | 65.0% | 76.2% | 76.2% | 66.2% | 61.4% | 53.1% | 52.1% | 49.0% |
| T2.5 | 77.5% | 76.7% | 80.8% | 76.7% | 80.8% | 73.3% | 80.8% | 80.8% | 73.3% | 77.5% | 74.2% | 69.2% |
| T3.1 | 78.1% | 81.2% | 76.2% | 81.0% | 73.3% | 68.1% | 72.9% | 75.0% | 76.9% | 68.8% | 67.4% | 67.4% |
| T3.2 | 74.0% | 77.9% | 72.9% | 78.5% | 74.0% | 72.7% | 75.8% | 78.5% | 70.4% | 73.3% | 78.5% | 65.2% |
| T3.3 | 89.5% | **97.6%** | 89.0% | **97.6%** | 83.1% | 81.7% | 82.4% | 64.3% | 71.4% | 67.4% | 61.4% | 70.5% |

### Hard Checker 通过率

| Checker | 总数 | flash | flash-think | pro | pro-think | gpt-5 | gpt-5.1 | gpt-5.4 | qwen3-32b | qwen3-14b | qwen3-8b-think | qwen3-8b | qwen3-4b |
|---------|------|-------|-------------|-----|-----------|-------|---------|---------|-----------|-----------|----------------|-----------|-----------|
| check_computation_result | 118 | 86.4% | 83.9% | 83.1% | 81.4% | 84.7% | 83.9% | 83.1% | 82.2% | 78.0% | 71.2% | 63.6% | 68.6% |
| check_value_exact | 25 | 80.0% | 84.0% | 72.0% | 80.0% | 80.0% | 72.0% | 92.0% | 80.0% | 80.0% | 84.0% | 84.0% | 80.0% |
| check_value_derivation | 10 | 50.0% | 50.0% | 30.0% | 40.0% | 30.0% | 40.0% | 50.0% | 40.0% | 40.0% | 40.0% | 40.0% | 40.0% |
| check_json_format | 9 | 100.0% | 100.0% | 88.9% | 100.0% | 100.0% | 77.8% | 100.0% | 100.0% | 100.0% | 88.9% | 77.8% | 100.0% |
| check_markdown_table | 8 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 87.5% | 100.0% | 100.0% |
| check_word_range | 7 | 14.3% | 14.3% | 28.6% | 28.6% | 71.4% | 0.0% | 28.6% | 14.3% | 0.0% | 71.4% | 71.4% | 57.1% |
| check_word_limit | 3 | 33.3% | 33.3% | 100.0% | 33.3% | 100.0% | 0.0% | 33.3% | 66.7% | 66.7% | 66.7% | 66.7% | 66.7% |

---

## 分析

### 1. 模型间对比

**GPT-5 vs DeepSeek**：GPT-5.4（H+S 81.3%）是 GPT 系列最佳，接近 ds-v4-pro（80.9%）和 ds-v4-flash（82.4%）。GPT-5（H+S 80.3%，带 reasoning: medium）Hard 最高（83.1%），但 reasoning 带来的额外 token 开销（390K vs 165K）并未显著提升 H+S。GPT-5.1（H+S 77.6%）反而最低，主要因字数控制能力退化（check_word_range/limit 通过率 0%）。

**GPT 系列演进**：GPT-5→5.1→5.4 的 IF 能力非单调提升，印证了 FinIF 衡量的是指令遵循能力而非通用智能。GPT-5.4 在 check_value_exact（92.0%）上全场最高，表明精确提取能力持续改善，但字数控制（28.6%/33.3%）仍是短板。

**DeepSeek Flash vs Pro**：Flash 在 hard（81.8% vs 78.3%）和 H+S（82.4% vs 80.9%）上均优于 Pro。推测 Flash 模型在指令跟随上更精确，生成格式更规范。Pro 在部分 L2 类别（T2.2 招股书、T2.5 资金流向）上略优，但整体不如 Flash。

**DeepSeek vs Qwen-3**：DeepSeek 全线领先 Qwen 系列。Qwen3-32B（H+S 78.0%）比 8B（71.2%）提升 6.8pp，hard 检查达到 80%（接近 DeepSeek），但 H+S 仍比 DeepSeek 低 3-5pp。Qwen3-32B 的 hard 通过率（80.0%）已接近 ds-v4-pro（78.3%），差距主要在 soft 约束（judge 评分）上。T3.3（股东权益变动）是 Qwen 的明显弱项（64.3% vs DeepSeek 89-97%）。

**Qwen 模型规模效应**：4B→8B→14B→32B 呈现清晰的 scaling 趋势：

| 指标 | qwen3-4b | qwen3-8b | qwen3-14b | qwen3-32b | 4B→8B Δ | 8B→14B Δ | 14B→32B Δ |
|------|----------|----------|-----------|-----------|---------|----------|-----------|
| H+S | 69.0% | 71.2% | 75.3% | 78.0% | +2.2pp | +4.1pp | +2.7pp |
| Hard | 76.1% | 72.5% | 76.7% | 80.0% | -3.6pp | +4.2pp | +3.3pp |
| T1 | 72.9% | 73.5% | 77.9% | 80.1% | +0.6pp | +4.4pp | +2.2pp |
| T2 | 64.7% | 69.0% | 73.5% | 78.6% | +4.3pp | +4.5pp | +5.1pp |
| T3 | 67.6% | 69.5% | 72.8% | 72.9% | +1.9pp | +3.3pp | +0.1pp |
| check_computation | 68.6% | 63.6% | 78.0% | 82.2% | -5.0pp | +14.4pp | +4.2pp |

H+S 随规模稳定提升（69.0%→78.0%），但 Hard 通过率出现反常：4B（76.1%）高于 8B（72.5%）。分析发现 4B 在 check_computation（68.6%）也高于 8B（63.6%），可能与 8B 模型的 non-thinking 模式下生成风格有关（8B 倾向输出更长但不够精确的回复）。T2（分析评估）的 scaling 效果最线性（64.7%→69.0%→73.5%→78.6%），每次 scaling 提升 4-5pp。T3（计算推导）在 14B→32B 几乎无提升（+0.1pp），表明计算推导能力在 14B 已接近 Qwen 架构上限。

### 2. Thinking 模式影响

| 对比 | T1 | T2 | T3 | Overall (H+S) | Hard |
|------|-----|-----|-----|---------|------|
| flash-thinking vs flash | +0.3pp | -3.6pp | **+5.0pp** | +0.1pp | -0.7pp |
| pro-thinking vs pro | -1.5pp | -1.6pp | **+6.3pp** | +0.2pp | +1.2pp |
| qwen3-8b-thinking vs 8b | +2.2pp | +1.3pp | +0.5pp | +1.4pp | **+4.1pp** |

- **DeepSeek T3 显著受益**：Thinking 模式对 DeepSeek 的计算推导类（T3）提升最大，特别是 T3.3（股东权益变动）从 89% 跳升至 97.6%
- **Qwen3-8B thinking 主要提升 Hard**：Hard 通过率从 72.5%→76.6%（+4.1pp），但 H+S 仅 +1.4pp，说明 thinking 改善了计算准确性（check_computation 63.6%→71.2%）但 soft 约束未同步提升
- **T2 表现分化**：DeepSeek thinking 在 T2 略有下降（-2~4pp），可能因过度推理偏离约束；Qwen3-8B thinking 在 T2 略有提升（+1.3pp）
- **T1 基本持平**：信息提取类不需要深度推理，thinking 无明显增益（DeepSeek）或仅小幅提升（Qwen +2.2pp）

### 3. 约束类型难度梯度

按 6 个模型平均通过率排序：

| 难度 | Checker | 平均通过率 | 特点 |
|------|---------|-----------|------|
| 易 | check_markdown_table | 100.0% | 所有模型均能生成 Markdown 表格 |
| 易 | check_json_format | 94.4% | 格式类约束，模型普遍擅长 |
| 中 | check_value_exact | 80.0% | 精确数值匹配，依赖 context 信息提取能力 |
| 中 | check_computation_result | 80.1% | 数值计算，数量最多（118条），区分度最大 |
| 难 | check_value_derivation | 40.0% | 推导过程校验，要求步骤完整且结果正确 |
| 难 | check_word_range | 28.6% | 字数范围控制，模型普遍难以精确控制输出长度 |
| 难 | check_word_limit | 55.6% | 字数上限，同上 |

**核心发现**：格式类约束（表格、JSON）对模型几乎无区分度；**计算类约束**（118条，占 hard 的 64%）是主要区分因子；**字数控制**是所有模型的共同弱点。

### 4. L2 类别难度

| 难度 | L2 | 5 模型平均 H+S | 特点 |
|------|-----|---------------|------|
| 易 | T2.3 市场趋势 | 91.2% | 趋势分析相对模板化 |
| 中 | T1.1 金融查询 | 83.1% | 信息定位准确度依赖 context 质量 |
| 中 | T1.2 证券公告 | 82.9% | 公告格式化信息提取 |
| 难 | T2.4 融资融券 | 68.8% | 涉及多日数据对比、趋势计算 |
| 难 | T1.3 行政处罚 | 78.0% | 法律文书理解，Qwen 显著拉低 |

---

## 待补充

- [x] qwen3-14b non-thinking（SiliconFlow API，已完成）
- [x] gpt-5-2025-08-07（H+S 80.3%，Hard 83.1%，reasoning: medium）
- [x] gpt-5.1-2025-11-13（H+S 77.6%，Hard 77.8%，reasoning: none）
- [x] gpt-5.4（H+S 81.3%，Hard 80.9%，reasoning: none）
- [ ] qwen3-32b-thinking（SiliconFlow API，enable_thinking=true）
- [x] qwen3-8b thinking 模式（已完成，H+S 72.6%，Hard 76.6%）
- [ ] gpt-4o-2024-11-20 重新打分（当前仅 59 条，非完整 100 case）
