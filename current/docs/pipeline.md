# FinIF 全流程 Pipeline 详细说明

## 流程总览

FinIF 项目的完整工作流分为三大阶段：

```
a) 数据构建  →  FinIF Benchmark (100 cases) + SFT 训练集 (2134 samples)
                        │                              │
                        ▼                              ▼
               c) Benchmark 评测              b) SFT 蒸馏训练
                        ▲                              │
                        │      微调后 Qwen3-8B         │
                        └──────────────────────────────┘
```

---

## a) 数据构建

### Step 1: 金融数据源收集

从四类金融数据源中收集原始数据作为 Context：

| 数据源 | 描述 | 典型内容 |
|--------|------|----------|
| 行情数据 | 股票/基金/指数的日频交易数据 | 开盘价、收盘价、涨跌幅、成交量、换手率等 |
| 公告/财报 | 上市公司公开披露文件 | 年报/季报、减持公告、处罚决定书、招股说明书 |
| 基金数据 | 公募/私募基金的运营数据 | 净值走势、持仓明细、费率结构、业绩归因 |
| 宏观数据 | 宏观经济统计指标 | GDP、CPI、PMI、社融、利率、货币政策 |

**产出**: 原始 Context 文本（金融数据表格、公告原文、行情摘要等）

### Step 2: Context 数据收集

- **Benchmark**: 精选 100 个高质量 Context，覆盖 T1（提取/计算）、T2（分析）、T3（推理）三个难度梯度
- **SFT 训练集**: 扩展收集 2134 个 Context（已去重，剔除与 Benchmark 重叠的 260 条）
- Context 涵盖多种金融文档类型：行情数据表格、财报摘要、公告原文、基金持仓报告、宏观经济数据等

**关键文件**:
- Benchmark Context: `benchmark_all.json` 中每个 case 的 context 字段
- SFT Context: `sft_pipeline/data/samples_clean_2134.jsonl` 中的 `context_text` 字段

### Step 3: Query 合成

基于收集的 Context，合成与之匹配的金融问题（Query）：

- **人工设计**: 针对每个 Context 设计有金融意义的查询问题，确保问题需要利用 Context 中的信息才能回答
- **LLM 辅助**: 利用 LLM 辅助生成 Query 初稿，人工审核修改
- **难度梯度**: Query 复杂度与 L2 分类对齐

| L1 | L2 | 描述 | 典型 Query | Case 数 |
|----|-----|------|-----------|---------|
| T1 | T1.1 | 行情/基金/宏观数据提取与四则运算 | "计算该股票本周涨跌幅" | 19 |
| T1 | T1.2 | 基于公告/财报的财务比率计算 | "计算毛利率变动" | 12 |
| T1 | T1.3 | 公告/文书关键字段提取与结构化输出 | "提取处罚要素并输出JSON" | 14 |
| T2 | T2.1 | 多维度业绩或宏观经济综合分析 | "综合分析本季度经营表现" | 8 |
| T2 | T2.2 | 竞争优势/业务结构/收入质量评估 | "分析核心竞争力" | 6 |
| T2 | T2.3 | 时序趋势研判与跨实体横向对比 | "对比三年营收趋势" | 6 |
| T2 | T2.4 | 量化风险指标计算与风险定性判断 | "评估信贷风险" | 7 |
| T2 | T2.5 | 高格式密度：摘要+指标+结构化并行 | "生成新闻标题+关键指标表+投资建议" | 6 |
| T3 | T3.1 | 财务数据异常审查与逻辑验证 | "识别应付账款异常" | 7 |
| T3 | T3.2 | 撰写专业金融报告 | "撰写审计意见书" | 8 |
| T3 | T3.3 | 跨表/跨期一致性核验与数学推导 | "交叉验证年报与季报数据" | 7 |

**关键文件**:
- Benchmark Query: `benchmark_all.json` 中每个 case 的 prompt 字段（正文部分）
- SFT Query: `sft_pipeline/data/samples_clean_2134.jsonl` 中的 `query_text` 字段

### Step 4: 约束采样 + Prompt 组装

从约束分类体系（`constraint_taxonomy.json`）中为每个 case/sample 采样约束，并组装成完整 Prompt。

#### 4.1 约束分类体系

**约束池规模**: 51 个模板 = 26 Hard Checker + 25 Soft Rubric

**5 大类 · 20 子标签**:

| 大类 | 标签 | 说明 | 类型 |
|------|------|------|------|
| Format | F1 章节 | 要求特定章节数、标题格式 | Hard |
| Format | F2 列表 | 要求列表/编号形式 | Hard |
| Format | F3 表格 | 要求 Markdown 表格 | Hard |
| Format | F4 JSON | 要求 JSON 格式输出 | Hard |
| Format | F5 引用块 | 要求使用引用块格式 | Hard |
| Format | F6 首尾 | 先结论后分析 / 末尾总结 / 按重要性排列 | Hard+Soft |
| Format | F7 特殊 | 分隔线、代码块等特殊格式 | Hard |
| Number | N1 字数 | 字数范围约束 | Hard |
| Number | N2 元素计数 | 要素个数约束 | Hard |
| Number | N3 精度 | 小数位数约束 | Hard |
| Linguistic | L1 关键词 | 必须包含特定关键词 | Hard |
| Linguistic | L2 禁止模式 | 禁止使用特定词汇/模式 | Hard |
| Linguistic | L3 术语 | 缩写全称 / 通俗语言 / 不用缩写 | Soft |
| Linguistic | L4 金融符号 | 货币符号、百分号等规范 | Hard |
| Style | S1 语气 | 正式书面语 / 客观中立 / 谨慎保守 / 简洁干练 | Soft |
| Style | S2 角色 | 以特定角色视角撰写 | Soft |
| Style | S3 连贯性 | 段落过渡 / 数据驱动论述 | Soft |
| Style | S4 修辞 | 类比举例 / 正反对比论述 | Soft |
| Content | C3 视角 | ESG / 风险管理 / 宏观经济 / 产业链 / 估值定价 | Soft |
| Content | C5 条件触发 | 条件-动作约束 | Hard |

#### 4.2 采样策略

- **采样数量**: 每个 case/sample 采样 1-5 条约束（梯度分布）
  - Benchmark 分布: 1条(15) / 2条(20) / 3条(30) / 4条(20) / 5条(15)
  - SFT 分布: 1条(10%) / 2条(20%) / 3条(30%) / 4条(25%) / 5条(15%)
- **冲突检测**: 内置 `CONFLICT_MAP` + `exclusion_rules`，确保采样的约束之间不矛盾
  - 例：不会同时采样"使用列表格式"和"禁止使用列表"
- **随机种子**: `random.seed(42)` 确保可复现

#### 4.3 Prompt 组装

将 Context + Query + 约束文本拼接为完整 Prompt：

```
{context_text}

{query_text}

请在回答时严格遵守以下附加要求：
（1）第一条约束...
（2）第二条约束...
...
```

约束文本由 `gen_constraint_text.py` 通过 LLM 生成自然语言描述（非模板直接输出），使约束表述自然多样。

**关键文件**:
- 约束体系定义: `constraint_taxonomy.json`
- 约束采样脚本: `sft_pipeline/gen_constraint_text.py`
- 采样结果: `sft_pipeline/data/constraint_gen_output_v3.jsonl`

### Step 5: Query 清洗 / 数据质量检查

**目的**: 确保 Prompt 正文（约束块之前的部分）不包含格式/排版类指令，这些指令应该在约束块中以显式约束的形式出现。

**核心思想**: 如果正文中有"以表格形式输出""控制在500字"等格式指令，就把它们从正文中删除，移到约束块中。这样 eval_config 中的约束就能与 prompt 中的约束一一对应（eval-prompt 完全对齐）。

#### 5.1 清洗流程

```
Full Prompt (context + query + 约束块)
         │
         ▼
   assemble_clean_input.py  →  clean_input_*.jsonl  (JSONL格式, id/system/user)
         │
         ▼
   用户在 Vulcan 平台跑 GPT-5
         │
         ▼
   clean_output_*.jsonl  (GPT-5 返回的清洗结果)
         │
         ▼
   apply_clean_bench.py  →  更新 benchmark_all.json / samples_clean_2134.jsonl
```

#### 5.2 LLM 清洗 Prompt 设计

**System Prompt** 指导 LLM 扮演"金融NLP数据清洗员"，任务是：
1. 检查约束块之前的正文部分
2. 找出格式/排版/结构类指令（输出格式要求、字数要求、视觉排版指令等）
3. 从正文中删除这些指令
4. 列出被删除的内容

**判断标准**:
- 去掉这句话后，信息需求本身会缺失 → **保留**（如"包含收益率、风险指标"）
- 去掉这句话后，只是换了个呈现方式 → **移走**（如"以表格形式输出"）

**输出格式**:
```json
{
  "needs_edit": true/false,
  "cleaned_body": "约束块之前的正文（删除格式指令后）",
  "moved_constraints": ["被移走的格式指令1", "被移走的格式指令2"]
}
```

#### 5.3 清洗结果

- **Benchmark**: 8/100 case 有修改，15 个格式指令从正文移到约束块
  - 1 条冲突（T1.1-010 "用markdown列出" vs "禁止列表"）已删除
  - 5 条移入约束补了 eval checker
- **SFT**: 2134 条已完成清洗与输入组装，最终产物见 `sft_data/sft_input_2134.jsonl`

**关键文件**:
- 输入组装: `assemble_clean_input.py`
- Benchmark 应用: `apply_clean_bench.py`
- Benchmark 清洗输入: `clean_input_bench.jsonl`
- Benchmark 清洗输出: `clean_output_bench_v2.jsonl`
- SFT 清洗后最终输入: `sft_data/sft_input_2134.jsonl`

### 数据构建产出

| 产出 | 规模 | 关键指标 |
|------|------|----------|
| **FinIF Benchmark** | 100 cases, 300 约束 | 187 hard + 113 soft, 1-5 约束/case |
| **SFT 训练集** | 2134 samples | 1-5 约束/sample, Context 与 Benchmark 无重叠 |

---

## b) SFT 蒸馏训练

### Step 6: Teacher 回复生成

使用 GPT-5.4 为每个 SFT 样本生成参考回答（每样本 1 条）。

| 参数 | 值 |
|------|-----|
| Teacher 模型 | GPT-5.4（通过 Vulcan 平台调用） |
| 采样数 | 1 条/sample |
| 输入 | 清洗后的完整 Prompt（context + query + 约束块） |
| 输出 | `sft_data/sft_data.jsonl`（2132 条，2 条缺失） |

**关键文件**:
- 输入 Prompt: `sft_data/sft_input_2134.jsonl`（`sample_id` + `prompt` 字段）
- GPT-5.4 回复: `sft_data/sft_data.jsonl`（`vulcan_output.llm_response` 字段）
- 缺失样本: `S-Q-SYN-T2.4-002-V1-R600`, `S-Q-SYN-T2.5-003-V2-R600`

### Step 7: 约束打分

使用 `score_sft_responses.py` 对每条回复进行约束遵循评估，双轨评分机制与 Benchmark 评测一致：

- **Hard Checker**: `checkers.py` 中 26 个规则函数，本地执行，返回 `bool`
- **Soft Judge**: DS-V4-Flash 作为 LLM-as-Judge，输入回复+Rubric，返回 `{pass, reason, evidence}`

```bash
python3 score_sft_responses.py score --judge-workers 20
```

**产出**: `sft_data/sft_scores.json`（逐样本逐约束评分结果）

### Step 8: 多轮修复（替代拒绝采样）

由于每样本仅生成 1 条回复，采用**多轮修复**策略替代传统的拒绝采样：对未通过约束的样本进行迭代修复，直至全部通过。

#### 8.1 自动修复（3 轮）

| 轮次 | 脚本 | 修复模型 | 策略 |
|------|------|----------|------|
| Round 1 | `async_repair.py` | DS-V4-Flash | 批量修复，针对所有 Hard 失败项 |
| Round 2 | `iterative_repair.py` | DS-V4-Flash | 迭代修复，最多重试 3 次/样本 |
| Round 3 | `repair_round3.py` | DS-V4-Flash | 排除约束冲突后精准修复，附带诊断信息 |

修复 Prompt 设计要点：
- System: 金融文档修复专家角色
- User: 包含未通过约束的精确诊断（当前字数 vs 目标范围、段落数不符等）
- 全约束列表作为参考，避免修复 A 时破坏已通过的 B

#### 8.2 约束冲突清理

自动修复后仍有 15 条样本失败，分析发现主要原因是约束之间存在冲突：

| 冲突类型 | 影响样本数 | 处理方式 |
|----------|-----------|----------|
| `ordered_list_count` + `no_arabic_numerals` | 5 | 删除 `ordered_list_count` |
| `first_word` + `json_format` | 1 | 删除 `first_word` |
| 重复字数约束（同一样本两个 word count） | 8 | 保留范围更合理的一个 |

清理范围覆盖全部 2134 条样本（不仅限于失败样本）。

#### 8.3 手动修复

剩余 15 条样本逐一人工审查修复（`manual_repair_15.jsonl`），修复类型包括：
- 文本微调：增删几个字调整字数、合并/拆分段落、调整标题层级
- 逻辑重构：如将 6 条并列项按逻辑重组为 4 段（T1.3-008）
- 约束参数调整：如字数范围 950-1250 → 500-1000（与实际回复匹配）

#### 8.4 修复产出

| 产出 | 说明 |
|------|------|
| `flash_repair_v2.json` | 374 条修复后的回复（覆盖原始回复） |
| `constraint_gen_output_v3.jsonl` | 清理冲突后的约束文件 |
| **最终通过率** | **2134/2134 = 100% Hard Pass** |

**关键文件**:
- 修复回复: `sft_data/flash_repair_v2.json`（sample_id → response text）
- 修复审查: `sft_data/manual_repair_review.html`（22 条修复记录可视化）
- 数据统计: `sft_data/sft_stats.html`（约束分布、通过率等）

### Step 9: ShareGPT 格式化

将 (prompt, response) 对格式化为 LLaMA Factory 的 ShareGPT 格式。

```bash
python3 sft_data/convert_sharegpt.py
```

**格式**（无 System Prompt，与评测时一致）:
```json
[
  {
    "conversations": [
      {"from": "human", "value": "{context + query + 约束块}"},
      {"from": "gpt", "value": "{回复}"}
    ]
  }
]
```

**为什么不加 System Prompt**: 评测时 SP 为空，训练时也保持为空，避免 train-test 分布偏移。Prompt 中已包含完整的约束指令。

**数据组装逻辑**:
1. 从 `sft_input_2134.jsonl` 读取 prompt
2. 从 `sft_data.jsonl` 读取原始 response（`vulcan_output.llm_response`）
3. 用 `flash_repair_v2.json` 覆盖 374 条修复后的 response
4. 跳过 2 条无 response 的样本

**产出**: `sft_data/sft_sharegpt_2132.json`（2132 条，19.6 MB）

### Step 10: LLaMA Factory 微调

使用 LLaMA Factory 对 Qwen3-8B 进行 SFT 微调。

**关键设计决策 — 非思考模式（空 think 标签）**:

文献研究表明，在 SFT 阶段强制模型学习 Chain-of-Thought 推理过程反而会损害指令遵循能力（CoT SFT harms IF）。使用空 think 标签让模型保持 Qwen3 原生的思考框架但不强制填充推理内容。

**训练配置**:

| 配置项 | 值 |
|---|---|
| 微调类型 | QLoRA（4-bit NF4，double quantization） |
| LoRA target | `all` |
| LoRA rank / alpha / dropout | 8 / 16 / 0.05 |
| cutoff length | 3072 |
| GPU | RTX 3090 × 8 |
| per-device batch size | 1 |
| gradient accumulation | 1 |
| 等效 global batch size | 8 |
| learning rate | 1e-4（cosine scheduler） |
| warmup ratio | 0.03 |
| epochs | 5（1310 steps） |
| 最优 checkpoint | checkpoint-786（epoch 3，eval loss 最低） |

**训练结果**:

| Epoch | Step | Eval Loss |
|---|---|---|
| 1 | 262 | 0.7141 |
| 2 | 524 | 0.6783 |
| **3** | **786** | **0.6705**（最优） |
| 4 | 1048 | 0.6742 |
| 5 | 1310 | 0.6816 |

Epoch 3 后 eval loss 回升，出现轻微过拟合。选择 checkpoint-786 用于后续评测。

### SFT 蒸馏训练产出

| 产出 | 规模 | 说明 |
|------|------|------|
| `sft_sharegpt_2132.json` | 2132 条 / 19.6 MB | ShareGPT 格式训练数据 |
| 约束覆盖 | 26/26 Hard + 25/25 Soft | 所有约束类型均有覆盖 |
| **微调后 Qwen3-8B** | Prompt-level 77%，排名第 3 | 追平 GPT-5 |

### (可选) Step 11: GRPO 强化学习

在 SFT 基础上进一步通过 GRPO (Group Relative Policy Optimization) 提升。

| 参数 | 值 | 说明 |
|------|-----|------|
| Reward | 仅 Hard Checker | 零 API 成本，可大量采样 |
| 优势 | 纯规则函数打分 | 不依赖 LLM Judge，训练效率高 |
| 局限 | 不覆盖 Soft 约束 | Soft 约束改善依赖 SFT 阶段 |

---

## c) Benchmark 评测

### Step 12: 多模型回复生成

使用 FinIF Benchmark 的 100 个 Prompt 对多个模型进行推理生成。

| 模型 | Provider | 说明 |
|------|----------|------|
| GPT-5 / 5.1 / 5.2 / 5.4 | Vulcan 平台 | OpenAI GPT 系列 4 代 |
| DS-V4-Flash / Pro | DeepSeek API | 非 thinking 模式 |
| DS-V4-Flash-Think / Pro-Think | DeepSeek API | thinking 模式（effort=high） |
| Qwen3-8B | SiliconFlow API | SFT 前基线 |
| Qwen3-8B-SFT | 本地推理（QLoRA） | SFT 后评测（checkpoint-786） |

**关键命令**:
```bash
# DeepSeek / Qwen 模型
python3 gen_async.py ds-v4-flash ds-v4-pro

# GPT 模型通过 Vulcan 平台生成，手动转换格式
```

**产出**: `benchmark_responses/responses_<model_name>.jsonl`

### Step 13: 双轨评测

对每个模型的回复进行约束遵循评估，使用与 SFT 打分完全相同的双轨机制。

#### 13.1 Hard Checker

```
response text + checker params
         │
         ▼
    checkers.py 中的对应函数
         │
         ▼
    bool (True/False)
```

**~50 个 checker 函数示例**:

| 函数 | 约束类型 | 参数 | 判定 |
|------|----------|------|------|
| `check_word_range` | N1 字数 | min, max | 字数是否在范围内 |
| `check_markdown_table` | F3 表格 | min_rows | 是否包含表格且行数达标 |
| `check_section_count` | F1 章节 | exact/min/max | 章节数是否匹配 |
| `check_bullet_list` | F2 列表 | min_items | 列表项是否足够 |
| `check_json_output` | F4 JSON | required_keys | 是否为合法 JSON 且包含指定字段 |
| `check_forbidden_pattern` | L2 禁止 | pattern (regex) | 是否不包含禁止模式 |
| `check_keyword_presence` | L1 关键词 | keywords | 是否包含所有关键词 |
| `check_starts_with` | F6 首尾 | prefix | 回复是否以指定词开头 |
| `check_decimal_places` | N3 精度 | places | 数值小数位数是否正确 |
| `check_risk_warning` | C5 条件触发 | trigger, action | 条件触发时是否执行了对应动作 |

#### 13.2 Soft Judge

```
response text + rubric template
         │
         ▼
    DS-V4-Flash (LLM-as-Judge)
         │
         ▼
    {pass: bool, reason: str, evidence: str}
```

**Rubric 模板示例**:

| ID | 标签 | Rubric 要点 |
|----|------|------------|
| GS-1 | S1 语气 | 回复是否采用正式书面语，避免口语化和网络用语 |
| GS-2 | S1 语气 | 回复是否保持客观中立立场，不带主观偏好 |
| GS-3 | S1 语气 | 回复是否采用谨慎保守表述，适当使用"可能""或许" |
| FS-1 | S2 角色 | 回复是否体现普通投资者的视角和知识水平 |
| FS-2 | S2 角色 | 回复是否体现机构投资者的专业深度 |
| FS-3 | S2 角色 | 回复是否体现金融分析师的研究方法论 |
| FS-4 | S2 角色 | 回复是否体现监管机构的合规视角 |
| FS-5 | S2 角色 | 回复是否面向零售投资者，通俗易懂 |
| GS-4 | L3 术语 | 专业缩写是否给出中文全称 |
| GS-5 | L3 术语 | 是否使用通俗语言解释专业概念 |
| FS-6 | C3 视角 | 是否从 ESG 角度分析 |
| FS-7 | C3 视角 | 是否从风险管理角度分析 |
| FS-8 | C3 视角 | 是否从宏观经济角度分析 |
| FS-14 | C3 视角 | 是否从产业链/供应链角度分析 |
| FS-15 | C3 视角 | 是否从估值与定价角度分析 |
| FS-16 | S2 角色 | 是否以信用评级分析师的视角撰写 |
| GS-6 | F6 结构 | 是否先结论后分析 |
| GS-7 | F6 结构 | 末尾是否有总结段落 |
| GS-8 | S3 连贯 | 段落之间是否有过渡衔接 |
| GS-9 | S4 修辞 | 是否使用类比或举例来解释 |
| GS-10 | S4 修辞 | 是否正反两面对比论述 |
| GS-11 | S1 语气 | 是否简洁干练，避免冗余修饰 |
| GS-12 | F6 结构 | 是否按重要性/影响程度从大到小排列 |
| GS-13 | S3 连贯 | 每个论点是否有数据佐证 |
| GS-14 | L3 术语 | 是否完全不使用英文缩写 |

**关键命令**:
```bash
python gen_responses_ds.py eval --model <model_name>
```

### Step 14: 逐 Case 评分

每个 case 的约束遵循率 = 通过的约束数 / 总约束数

```
Case T1.1-001:
  Constraint #1 (Hard: word_range)  → ✓ pass
  Constraint #2 (Hard: table)       → ✓ pass
  Constraint #3 (Soft: formal_tone) → ✗ fail
  Constraint #4 (Hard: keyword)     → ✓ pass
  Constraint #5 (Soft: ESG_view)    → ✓ pass
  
  Score = 4/5 = 80.0%
```

### Step 15: Tier 聚合 → Overall Score

按 L1 难度梯度（Tier）分组聚合，再取平均得到 Overall Score：

| Tier | 描述 | Case 数 | 计算方式 |
|------|------|---------|----------|
| T1 | 提取与计算 | 45 | mean(T1 各 case 遵循率) |
| T2 | 综合分析 | 33 | mean(T2 各 case 遵循率) |
| T3 | 推理与报告 | 22 | mean(T3 各 case 遵循率) |
| **Overall** | 加权/等权平均 | 100 | mean(T1_score, T2_score, T3_score) |

### Step 16: 模型对比分析

横向对比各模型在 FinIF Benchmark 上的表现：

**当前评测结果（10 模型）**:

| 排名 | 模型 | Prompt-level | Instruction-level | Hard | Soft |
|:----:|------|:-----------:|:-----------------:|:----:|:----:|
| 1 | GPT-5.4 | **88.0%** | **96.0%** | 94.7% | **98.2%** |
| 2 | GPT-5.2 | 87.0% | 95.7% | 94.7% | 97.3% |
| 3 | GPT-5 | 77.0% | 92.0% | 92.0% | 92.0% |
| 3 | **Qwen3-8B-SFT** | **77.0%** | **91.3%** | **92.0%** | **90.3%** |
| 3 | DS-V4-Pro-Think | 77.0% | 90.7% | 90.4% | 91.2% |
| 6 | DS-V4-Pro | 76.0% | 90.0% | 88.8% | 92.0% |
| 6 | DS-V4-Flash | 75.0% | 90.0% | 89.3% | 91.2% |
| 8 | DS-V4-Flash-Think | 73.0% | 89.7% | 89.3% | 90.3% |
| 9 | GPT-5.1 | 69.0% | 88.0% | 85.0% | 92.9% |
| 10 | Qwen3-8B | 62.0% | 84.3% | 86.1% | 81.4% |

**SFT 效果**：Qwen3-8B 通过 SFT 从末位（62%）跃升至第 3（77%），追平 GPT-5。

**IFEval 通用 IF 鲁棒性检验**（OpenCompass，4-bit NF4，non-thinking）：

| 指标 | Qwen3-8B (Base) | Qwen3-8B-SFT | Δ |
|---|---|---|---|
| Prompt-level Strict | 80.41 | 78.19 | -2.22 |
| Inst-level Strict | 86.81 | 84.89 | -1.92 |

SFT 后 IFEval 仅下降约 2 个百分点，FinIF +15pp vs IFEval -2pp，表明领域微调未显著损害通用指令遵循能力。

**分析维度**:
- Overall Score 对比
- 分 Tier (T1/T2/T3) 对比：检查模型在不同难度上的表现差异
- 分约束类型 (Hard/Soft) 对比：检查模型对规则类 vs 风格类约束的遵循差异
- 分约束标签对比：找出各模型的弱项约束类型
- SFT 前后 Qwen3-8B 的提升幅度分析

**产出**: `output/scores_<model_name>.json`

---

## 跨阶段数据流

```
┌─────────────────────────────────────────────────────────────┐
│                       a) 数据构建                            │
│                                                             │
│  数据源 → Context → Query → 约束采样 → Query清洗            │
│                                                             │
│           ┌──────────────┐    ┌──────────────┐              │
│           │ SFT 训练集    │    │ FinIF Bench  │              │
│           │ (2134)        │    │ (100 cases)  │              │
│           └──────┬───────┘    └──────┬───────┘              │
└──────────────────┼───────────────────┼──────────────────────┘
                   │                   │
         ┌─────────▼─────────┐  ┌──────▼──────────────────┐
         │ b) SFT 蒸馏训练    │  │ c) Benchmark 评测        │
         │                   │  │                         │
         │ GPT-5.4 回复      │  │ GPT-5 / GPT-4o /        │
         │ → 约束打分        │  │ Qwen3-8B / DS-V4        │
         │ → 多轮修复        │  │     │                    │
         │ → ShareGPT格式化  │  │     ▼                    │
         │     │             │  │ 回复生成                  │
         │     ▼             │  │     │                    │
         │ 2132条训练数据 ────┼──┤     ▼                    │
         │     │             │  │ Hard + Soft 评测         │
         │     ▼             │  │     │                    │
         │ Qwen3-8B ─────────┼──┤     ▼                    │
         │ (微调后)    反馈评测│  │ 评分 → Tier → 模型对比    │
         │                   │  │                         │
         └───────────────────┘  └─────────────────────────┘
```

---

## API 配置汇总

| 用途 | Provider | Model | 阶段 |
|------|----------|-------|------|
| 约束文本生成 / Soft Judge | DeepSeek | deepseek-v4-flash | a) 数据构建 / c) 评测 |
| Teacher 回复 | Vulcan 平台 | GPT-5.4 | b) SFT 训练 |
| 回复修复 | DeepSeek | deepseek-v4-flash | b) SFT 训练 |
| Benchmark 回复生成 | DeepSeek | deepseek-v4-flash / v4-pro | c) 评测 |
| Qwen3-8B 推理 | SiliconFlow | Qwen/Qwen3-8B | c) 评测 |
| GPT 系列 | Vulcan 平台 | gpt-5 / 5.1 / 5.2 / 5.4 | c) 评测 |
| Query 清洗 | Vulcan 平台 | GPT-5 | a) 数据构建 |

## 关键设计决策汇总

| 决策 | 选择 | 依据 |
|------|------|------|
| 评测框架 | 纯 IF compliance | 参考 SciIF 双轴设计，C6 correctness 独立评测 |
| eval-prompt 对齐 | eval_config 只含 prompt「附加要求」中的约束 | query 隐式要求不公平 |
| 约束体系 | 5 大类 20 子标签，采样 1-5 条/case | 确保多样性、难度梯度 |
| Judge 模型 | DS-V4-Flash | 成本低、速度快、质量足够 |
| Teacher 模型 | GPT-5.4 | 最强 IF 能力，生成高质量回复 |
| 回复质量保障 | 多轮修复 > 拒绝采样 | 单次生成 + 修复比 K 次采样更高效 |
| 训练数据无 SP | 不加 System Prompt | 与评测环境对齐，避免 train-test 分布偏移 |
| SFT 底座 | Qwen3-8B | 部署成本低，提升空间充足 |
| SFT 不教 reasoning | 空 think 标签 | CoT SFT 损害 IF（文献支持） |
| GRPO reward | 仅 Hard checker | 零 API 成本，可大量采样 |
