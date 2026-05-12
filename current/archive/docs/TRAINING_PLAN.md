# FinIF 训练方案

## 概述

基于 FinIF benchmark 评测结果，对 Qwen3-8B 进行针对性 SFT + GRPO 训练，目标是在金融指令遵循任务上达到/超过 Qwen3-32B base（H+S 78.0%），接近 DeepSeek-V4-Flash（H+S 82.4%）。

## 评测数据支撑

### 当前模型表现（FinIF 100 case / 441 约束）

| Model | Hard | H+S | T1 | T2 | T3 |
|-------|------|-----|-----|-----|-----|
| ds-v4-flash-thinking | 81.1% | 83.7% | 86.2% | 79.4% | 85.2% |
| ds-v4-flash | 81.8% | 82.4% | 83.9% | 81.6% | 80.3% |
| ds-v4-pro-thinking | 79.5% | 81.1% | 80.2% | 79.4% | 85.4% |
| gpt-5.4 | 80.9% | 81.3% | 83.8% | 80.8% | 77.0% |
| ds-v4-pro | 78.3% | 80.9% | 81.7% | 81.1% | 79.1% |
| gpt-5-2025-08-07 | 83.1% | 80.3% | 81.6% | 81.1% | 76.7% |
| qwen3-32b | 80.0% | 78.0% | 80.1% | 78.6% | 72.9% |
| gpt-5.1-2025-11-13 | 77.8% | 77.6% | 79.0% | 78.0% | 74.1% |
| qwen3-14b | 76.7% | 75.3% | 77.9% | 73.5% | 72.8% |
| **qwen3-8b** | **72.5%** | **71.2%** | **73.5%** | **69.0%** | **69.5%** |
| qwen3-8b-thinking | 76.6% | 72.6% | 75.7% | 70.3% | 70.0% |
| qwen3-4b | 76.1% | 69.0% | 72.9% | 64.7% | 67.6% |

**关键发现**：GPT-5.1（H+S 77.6%）低于 Qwen3-32B（78.0%），主要因字数控制能力退化（check_word_range/limit 通过率 0%）。说明 FinIF 衡量的是指令遵循能力而非通用智能，模型迭代不一定带来 IF 能力的单调提升。

### 8B 主要弱项（与 Flash 对比）

| 弱项 | 8B | Flash | Gap |
|------|-----|-------|-----|
| T1.3 行政处罚文书 | 59.9% | 84.4% | 24.5pp |
| T2.4 融资融券分析 | 52.1% | 74.0% | 21.9pp |
| check_computation_result | 63.6% | 86.4% | 22.8pp |
| T2.1 财务业绩分析 | 76.7% | 78.8% | 2.1pp |
| T3.3 股东权益变动计算 | 61.4% | 89.5% | 28.1pp |

### 关键设计决策的数据依据

| 决策 | 选择 | 数据依据 |
|------|------|----------|
| 底座模型 | Qwen3-8B | 部署成本低；base H+S 71.2%，与教师差距 11.2pp，SFT 提升空间充足 |
| 教师模型 | DS-V4-Flash-Thinking | H+S 83.7%（全部模型最高）；T3 比 non-thinking 高 5pp |
| SFT 不教 reasoning | 只取 `content`，空 `<think></think>` 标签 | CoT SFT 损害 IF 能力（arXiv:2505.14810）；大→小推理蒸馏性能降 20.5%（arXiv:2509.22230）；Qwen3 自带 thinking 开关，推理能力无需 SFT 教 |
| GRPO 而非 DPO | - | 有现成 checker（确定性 reward），且 GRPO 利用多回复排序信息 |

---

## Stage 1: SFT（拒绝采样蒸馏）

### 1.1 方法

Verifier-Guided Rejection Sampling Distillation（基于约束验证的拒绝采样蒸馏）。

对于每条训练 prompt $x_i$：

1. **多次采样**：教师模型（DS-V4-Flash-Thinking, temperature=0.7）生成 K=8 个候选回复
2. **剥离推理**：所有候选回复只取 `message.content`（DeepSeek 的 reasoning 在独立的 `reasoning_content` 字段，不混入正文），不学习推理过程
3. **约束验证**：每个候选经过两级评分：
   - Hard 约束：12 类确定性 checker（`checkers.py`），binary pass/fail
   - Soft 约束：LLM judge（DS-V4-Flash, temperature=0），binary pass/fail
4. **评分与筛选**：每个候选的得分为约束总通过率 $S(y_i^{(k)}) = \frac{\sum_{j=1}^{N} \mathbb{1}[c_j(y_i^{(k)}) = \text{pass}]}{N}$（Hard + Soft 不区分，直接算通过率），选得分最高的候选；若最高分 < τ=0.7 则丢弃该 prompt
5. **SFT 训练**：在筛选后的 $(x_i, y_i^*)$ 上做标准 SFT

**不学 reasoning 的文献依据**：
- *Scaling Reasoning, Losing Control*（arXiv:2505.14810）：CoT SFT 会损害指令遵循能力，且 CoT 越长退化越严重
- *In Their Own Words*（arXiv:2509.22230）：大模型推理链直接蒸馏给小模型，因分布不对齐导致性能下降 20.5%
- Qwen3 官方建议（GitHub Discussion #1429）：non-thinking SFT 应使用空 think 标签格式

**训练数据格式**（遵循 Qwen3 官方建议）：
```
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
<think>
</think>
{教师最终回复}<|im_end|>
```

**采样温度说明**：教师采样使用 temperature=0.7（与 benchmark 生成一致），保证候选回复有足够多样性供筛选。temperature 过低会导致 K 个候选高度相似，丧失拒绝采样的意义。

### 1.2 训练数据

**数据规模**：~2000 条（已有 2134 条 prompt 生成完毕，剔除 benchmark context 重叠后）

**Pipeline 进度**：
- [x] Step 0-3：prompt 合成（context 生成 + query 生成 + 约束组装 + 参数化扩增 → 2394 条）
- [x] Context 去重：剔除与 benchmark 100 条重叠的 260 条 → 2134 条 clean prompts
- [ ] Step 4：教师回复生成（DS-V4-Flash-Thinking, K=4~8）
- [ ] Step 5：约束打分与拒绝采样筛选（τ=0.7）
- [ ] Step 6：格式化为 Qwen3 SFT 格式（non-thinking: 空 `<think></think>` 标签）

**Pipeline 文件位置**：`sft_pipeline/`
- `data/samples_clean_2134.jsonl` — 去重后的 prompt 数据
- `data/query_pool.jsonl` — 270 条 query 种子
- `data/context_pool.jsonl` — 54 条 context（含合成 + 外部）
- `config/constraint_pool.json` — 约束池（G1-G10 通用 + F1-F12 金融专用）

**Context 来源**：不复用 benchmark 的 100 条 context。来源策略：
- **合成 context**：用真实文档作为种子，生成结构相似但数据不同的 context（已完成，占主体）
- **外部 context**：从公开年报摘要等提取的真实金融文档（6 份年报已入库）
- **语义去重**：训练 context 与 benchmark 100 条做前缀匹配剔除，防止训练-测试泄漏

**数据配比**（按 8B 弱项加权）：

| 类别 | 占比 | 依据 |
|------|------|------|
| T3 计算推导（全部） | 30% | 整体 69.5%，计算类 checker 差距最大（22.8pp） |
| T1.1/T1.2 信息提取 | 20% | 基础能力巩固 |
| T2 其他分析任务 | 20% | 分析评估能力 |
| T2.4 融资融券分析 | 15% | 8B 仅 52.1%，gap 22pp |
| T1.3 行政处罚文书 | 10% | gap 24pp，但 context 多样性受限（处罚决定书格式固定） |
| 预留 buffer | 5% | 补充训练中发现的其他弱项 |

### 1.3 SFT 超参数

| 参数 | 值 |
|------|-----|
| 底座模型 | Qwen3-8B |
| 学习率 | 1e-5 ~ 2e-5 |
| Epochs | 2-3 |
| 训练目标 | 最终回复（不含 `<think>`） |

### 1.4 SFT Checkpoint 评测（Stage Gate）

SFT 完成后、进入 GRPO 之前，必须先在 FinIF benchmark 上评测 SFT checkpoint：

- **通过条件**：H+S > 8B base（71.2%），且 Hard 不下降
- **若未通过**：排查训练数据质量（是否有大量低质量样本）、学习率是否过大、是否过拟合
- **若通过**：记录 SFT checkpoint 的完整评测结果，作为 GRPO 的 baseline，进入 Stage 2

**目的**：确认 SFT 本身有效，避免在差底座上做 GRPO 浪费资源。

---

## Stage 2: GRPO（约束导向强化学习）

在 SFT 模型基础上做 Group Relative Policy Optimization。

### 2.1 Reward 设计

**GRPO 阶段仅使用 Hard checker 作为 reward**（零 API 成本，可大量采样）：

- **Reward**：$R(y) = \frac{\sum_{j=1}^{N_h} \mathbb{1}[\text{checker}_j(y) = \text{pass}]}{N_h}$
- 12 类 Python checker，调用成本为零
- `check_computation_result`（118 条，占 Hard 64%）是主要优化目标

**为什么 GRPO 阶段不用 Soft judge**：
- Soft judge 需要调用 DS-V4-Flash API，每条 prompt × G 个回复 × 每回复多条约束 = 成本过高
- Hard checker 已覆盖 8B 与 Flash 的主要差距（计算准确性、格式规范）
- SFT 阶段已用 Soft judge 筛选过训练数据，Soft 质量有基础保障

### 2.2 GRPO 流程

1. 每条 prompt 采样 G=8~16 个回复（Hard-only reward 零成本，可提高采样量）
2. 全部过 `checkers.py`，计算 Hard reward
3. 组内回复按 reward 排序，做相对策略优化

### 2.3 为什么 GRPO 而非 DPO

- DPO 只用 pair（chosen/rejected），浪费了多回复的排序信息
- GRPO 利用全部 G 个回复的相对排序，数据效率更高
- Hard checker 是确定性函数（Python 代码），调用成本为零，天然适合 GRPO 的大量采样评估

### 2.4 实现框架

推荐使用 HuggingFace [TRL](https://github.com/huggingface/trl) 的 `GRPOTrainer`，实现复杂度可控。若自研实现成本过高，可退化为 SFT-only 方案（仍有完整叙事）。

---

## Stage 3: 评测

### 3.1 评测矩阵

| 评测集 | 目的 | 指标 |
|--------|------|------|
| FinIF（100 case / 441 约束） | 主指标，验证金融 IF 提升 | H+S, Hard, T1/T2/T3 |
| IFEval（500 条） | 防过拟合，验证通用 IF 不掉分 | Prompt-level / Instruction-level accuracy |
| CFBench（1000 条） | 防过拟合，验证金融通用能力 | CSR |

### 3.2 对比实验

```
                    Base      SFT       SFT+GRPO
qwen3-4b            69.0%     -         -          ← scaling 基准
qwen3-8b            71.2%     ?         ?          ← 训练目标
qwen3-8b-thinking   72.6%     -         -          ← thinking 对照
qwen3-14b           75.3%     -         -          ← scaling 对照
gpt-5.1             77.6%     -         -          ← 商业模型对照
qwen3-32b           78.0%     -         -          ← 目标线 1
gpt-5               80.3%     -         -          ← 商业模型对照
gpt-5.4             81.3%     -         -          ← 商业模型对照
ds-v4-flash         82.4%     -         -          ← 目标线 2（天花板）
```

### 3.3 目标

- **最低目标**：8B-SFT-GRPO > qwen3-14b base（75.3%）→ "SFT 等效 1.75 倍 scaling"
- **理想目标**：8B-SFT-GRPO > qwen3-32b base（78.0%）→ "SFT 等效 4 倍 scaling"
- **IFEval / CFBench 不掉分**：证明学到的是 IF 能力，不是过拟合 benchmark

### 3.4 推理时部署策略

| 任务类型 | enable_thinking | 理由 |
|---------|----------------|------|
| T1 信息提取 | false | 不需要推理，直接输出，速度快 |
| T2 分析评估 | false | thinking 对 T2 无增益甚至负面 |
| T3 计算推导 | true | 8B-thinking 比 non-thinking Hard +4.1pp |

### 3.5 论文表达建议

"SFT 等效 N 倍 scaling" 的说法需要准备 **compute-matched 对比**：

| 方案 | 模型参数量 | 训练成本 | 推理成本/token | FinIF H+S |
|------|-----------|---------|---------------|-----------|
| qwen3-32b base | 32B | 0 | ~4x of 8B | 78.0% |
| qwen3-8b-SFT-GRPO | 8B | SFT + GRPO 训练 | 1x（基准） | ? |

若 8B-SFT-GRPO 达到 78%+，实际推理成本仅为 32B 的 ~1/4，且训练成本（500-1000 条 SFT + GRPO）相比 32B 预训练可忽略不计。这比"等效 4 倍 scaling"更严谨。

---

## 消融实验

### 必做

| 实验 | 变量 | 目的 |
|------|------|------|
| SFT-only vs SFT+GRPO | 是否加 GRPO | 量化 GRPO 的增量贡献 |
| 8B base vs 8B-SFT checkpoint | SFT 是否有效 | Stage Gate 验证 |

### 建议做

| 实验 | 变量 | 目的 |
|------|------|------|
| GRPO α 消融 | α ∈ {0.5, 0.6, 0.7, 0.8, 1.0} | 找 Hard/Soft reward 最优权重（若后续加入 Soft reward） |
| 拒绝采样 K 消融 | K ∈ {1, 4, 8, 16} | 量化多采样筛选的收益 |
| 数据配比消融 | 均匀 vs 弱项加权 | 验证加权策略是否有效 |

**注**：当前 GRPO 仅用 Hard reward（α=1.0），若后续引入 Soft reward 再做 α 消融。

---

## 风险与退化方案

| 风险 | 应对 |
|------|------|
| SFT 效果不明显 | 检查训练数据质量；降低 τ 增加数据量；增加 epochs |
| GRPO 实现复杂度过高 | 退化为 SFT-only 方案，仍有完整叙事（拒绝采样蒸馏 + 评测） |
| 训练-测试泄漏 | 语义去重检查（embedding cosine similarity > 0.85 剔除） |
| IFEval/CFBench 掉分 | 混入通用 IF 数据（IFEval 训练集）做多任务 SFT |

---

## 核心卖点

1. **一套基础设施两个用途**：`checkers.py` + judge pipeline 同时服务于 benchmark 评测、SFT 数据筛选、GRPO reward，无需额外训练 reward model
2. **训练策略完全由评测数据驱动**：教师选择、数据配比、reward 设计均基于 benchmark 量化结果
3. **SFT 与 thinking 解耦**：SFT 教约束遵循，thinking 由模型自带机制控制，两者正交
4. **成本可控**：GRPO 阶段仅用 Hard checker（零 API 成本），SFT 阶段一次性使用 Soft judge
