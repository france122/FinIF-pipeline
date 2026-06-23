# FinIF — 金融指令遵循评测 & SFT 训练

## 项目概况

FinIF (Financial Instruction Following) Benchmark：评测大模型在金融场景下的指令遵循能力。
配套 SFT 训练 pipeline，通过针对性训练让 Qwen3-8B 达到大模型水平。**工程与论文初稿已完成，当前进入会议论文改造与流程优化阶段。**

- **Benchmark**: 100 case / 300 约束（187 hard + 113 soft），全部为 IF 约束，eval-prompt 完全对齐，10 模型已评测
- **约束数分布**: 1条(15) / 2条(20) / 3条(30) / 4条(20) / 5条(15)
- **设计决策**: C6 计算正确性约束已移除；query 隐式约束（C1 覆盖度/C2 证据等）也已清理，eval_config 只包含 prompt「附加要求」中显式列出的约束
- **约束分类体系**: 5 大类 20 子标签（F1-F7 / N1-N3 / L1-L4 / S1-S4 / C3,C5）
- **SFT Pipeline**: 2134 条 prompt → 2132 条 ShareGPT 训练数据（GPT-5.4 teacher + 3 轮修复），已完成训练
- **论文进度**: 毕设/完整论文初稿已写完；下一阶段压缩为会议论文版本，突出贡献、实验主线和可复现流程

## 当前阶段（2026-06-02）

- [x] Benchmark 数据、评测、SFT 数据、训练与结果分析完成
- [x] 论文完整初稿完成
- [ ] 写会议论文标题大纲与 abstract
- [ ] 定稿任务分类体系、约束分类体系与合成数据方案
- [ ] 迭代 FinIF，让大模型的评分在 20 以下
- [ ] 改造成会议论文：收束叙事、压缩背景与工程细节、强化 contribution / method / experiment / limitation
- [ ] 优化流程复现：统一脚本路径、整理图表生成入口、补齐环境依赖与一键评测/出图说明
- [ ] 清理文档状态：把历史 TODO、旧路径、阶段性草稿与最终产物分开

## 协作原则

- 保持独立思考，不盲从用户，不为了显得配合而谄媚。若用户判断、实验口径或实现方向存在问题，应直接指出并给出更可靠的依据或替代方案；事实、证据和项目目标优先于迎合。

## 最新评测结果（2026-05-12，10 模型）

| 排名 | 模型 | Prompt-level | Instruction-level | Hard | Soft |
|:----:|------|:-----------:|:-----------------:|:----:|:----:|
| 1 | GPT-5.4 | **88.00%** | **96.0%** | 94.7% | **98.2%** |
| 2 | GPT-5.2 | 87.00% | 95.7% | 94.7% | 97.3% |
| 3 | GPT-5 | 77.00% | 92.0% | 92.0% | 92.0% |
| 3 | **Qwen3-8B-SFT** | **77.00%** | **91.3%** | **92.0%** | **90.3%** |
| 3 | DS-V4-Pro-Think | 77.00% | 90.7% | 90.4% | 91.2% |
| 6 | DS-V4-Pro | 76.00% | 90.0% | 88.8% | 92.0% |
| 6 | DS-V4-Flash | 75.00% | 90.0% | 89.3% | 91.2% |
| 8 | DS-V4-Flash-Think | 73.00% | 89.7% | 89.3% | 90.3% |
| 9 | GPT-5.1 | 69.00% | 88.0% | 85.0% | 92.9% |
| 10 | Qwen3-8B (SFT前) | 62.00% | 84.3% | 86.1% | 81.4% |

- Prompt-level: 全部约束通过才算 pass
- Instruction-level: 单条约束维度通过率
- Judge: ds-v4-flash (temperature=0)
- Hard checker: 本地规则函数，完全确定性
- Soft checker: LLM-as-Judge，agreement ~90%
- 详细结果见 `docs/FinIF_eval_results.md`

## 目录结构

```
current/
├── AGENT.md                     # 本文件
├── DATA_INDEX.md                # 数据文件分类索引
├── checkers.py                  # ~50 个 checker 函数
├── gen_async.py                 # 异步并行回复生成（多 provider: DS + SiliconFlow）
├── gen_responses_ds.py          # 回复生成 + 评测（gen/eval 子命令，--models 过滤）
├── score_sft_responses.py       # SFT 训练数据打分
├── build_stats.py               # HTML dashboard 生成
├── trim_constraints.py          # 约束数量裁剪脚本（3-6 → 1-5）
│
├── benchmark/                   # Benchmark 数据 + 评测结果
│   ├── benchmark_all.json       # 100 cases: case_id, prompt, context
│   ├── benchmark_prompts_100.jsonl  # 100 条组装好的推理输入
│   ├── eval_config_all.json     # 300 IF 约束配置（eval-prompt 对齐）
│   ├── constraint_taxonomy.json # 约束体系规范（5大类20子标签）
│   ├── responses/               # 10 模型回复（responses_*.jsonl）
│   └── scores/                  # 10 模型评分（scores_*.json）
│
├── sft_data/                    # SFT 训练数据 + 修复脚本
│   ├── sft_input_2134.jsonl     # 最终 SFT 输入 prompt
│   ├── sft_data.jsonl           # GPT-5.4 teacher 原始回复（2132 条）
│   ├── sft_scores.json          # 训练数据打分结果
│   ├── flash_repair_v2.json     # 374 条自动修复回复（DS-V4-Flash 3 轮）
│   ├── manual_repair_15.jsonl   # 15 条人工修复记录
│   ├── sft_sharegpt_2132.json   # 最终 ShareGPT 训练数据（2132 条）
│   ├── constraint_gen_output_v3.jsonl  # 约束采样结果（冲突清理后）
│   ├── convert_sharegpt.py      # 转换为 ShareGPT 训练格式
│   ├── async_repair.py          # Round 1 批量修复
│   ├── iterative_repair.py      # Round 2 迭代修复
│   ├── repair_round3.py         # Round 3 精准修复
│   ├── verify_repairs.py        # 修复结果验证
│   ├── manual_repair_review.html # 人工修复审查页面
│   └── sft_stats.html           # SFT 数据约束分布统计
│
├── sft_pipeline/                # SFT pipeline 代码 + 中间数据
│   ├── config/task_labels.json  # L1/L2 任务标签定义
│   ├── data/samples_clean_2134.jsonl  # 清洗后的 sample
│   ├── gen_constraint_text.py   # 约束采样 + LLM 生成（N=1-5, TAG_BOOST）
│   └── step1~step9             # SFT pipeline 各步骤脚本
│
├── docs/                        # 文档资料
│   ├── pipeline.md              # 全流程 Pipeline 详细说明
│   ├── FinIF_eval_results.md    # 10 模型详细评测报告
│   ├── IFEval_results.md        # IFEval 通用 IF 评测结果
│   ├── sft_train.md             # SFT 训练实验报告
│   ├── sft_findings.md          # SFT 训练效果分析
│   ├── 项目总结.md              # 项目总结
│   ├── todo.md                  # 待办事项
│   └── 毕设项目.docx            # 毕设项目文档
│
├── html/                        # HTML 可视化页面
│   ├── benchmark_stats.html     # 10 模型对比 dashboard
│   ├── data_review.html         # 100 case 数据审查
│   └── review_responses.html    # 模型回复详情查看
│
├── diagrams/                    # 流程图
│   ├── pipeline.drawio
│   ├── pipeline copy.drawio
│   └── whole_pipeline.drawio
│
└── archive/                     # 归档（旧版脚本/数据/打分）
```

## 评测流程

```
benchmark_all.json + eval_config_all.json (300 IF constraints)
         │
         ▼
   gen_async.py <model_key>       → benchmark/responses/responses_*.jsonl
         │                          (支持 DS/SiliconFlow 多 provider，20 并发)
         │                          (GPT 模型通过 Vulcan 平台生成，手动转换格式)
         ▼
   gen_responses_ds.py eval --models <model> --judge-workers 20
         ├── Hard checker (checkers.py, 本地规则函数) → bool
         └── Soft checker (ds-v4-flash LLM-as-Judge + rubric) → {pass, reason}
         │
         ▼
   benchmark/scores/scores_*.json  (per-case → T1/T2/T3 tier → overall)
         │
         ▼
   build_stats.py                 → html/benchmark_stats.html (10模型对比 dashboard)
```

## 约束体系

### 分类标签

| 大类 | 标签 | 说明 |
|------|------|------|
| Format | F1 章节, F2 列表, F3 表格, F4 JSON, F5 引用块, F6 首尾, F7 特殊 | 结构/格式约束 |
| Number | N1 字数, N2 元素计数, N3 精度 | 数值约束 |
| Linguistic | L1 关键词, L2 禁止模式, L3 术语, L4 金融符号 | 语言学约束 |
| Style | S1 语气, S2 角色, S3 连贯性, S4 修辞 | 风格约束 |
| Content | C3 视角, C5 条件触发 | 内容约束 |

### 约束池

| 类型 | 数量 | 说明 |
|------|------|------|
| Hard checker（参数化规则） | 14 tags | F1-F7, L1-L2, L4, N1-N3, C5 |
| Soft rubric（LLM-as-Judge） | 9 tags | C3, F4, F6, F7, L3, S1-S4 |

Benchmark 约束数分布：1条(15) / 2条(20) / 3条(30) / 4条(20) / 5条(15) = 300 约束。
SFT 约束数分布：1条(10%) / 2条(20%) / 3条(30%) / 4条(25%) / 5条(15%)，共 2134 条。

详见 `constraint_taxonomy.json`。

## L2 类别

| L1 | L2 | 描述 | Case 数 |
|----|-----|------|---------|
| T1 | T1.1 | 行情/基金/宏观数据提取与四则运算 | 19 |
| T1 | T1.2 | 基于公告/财报的财务比率计算 | 12 |
| T1 | T1.3 | 公告/文书关键字段提取与结构化输出 | 14 |
| T2 | T2.1 | 多维度业绩或宏观经济综合分析 | 8 |
| T2 | T2.2 | 竞争优势/业务结构/收入质量评估 | 6 |
| T2 | T2.3 | 时序趋势研判与跨实体横向对比 | 6 |
| T2 | T2.4 | 量化风险指标计算与风险定性判断 | 7 |
| T2 | T2.5 | 高格式密度：摘要+指标+结构化并行 | 6 |
| T3 | T3.1 | 财务数据异常审查与逻辑验证 | 7 |
| T3 | T3.2 | 撰写专业金融报告 | 8 |
| T3 | T3.3 | 跨表/跨期一致性核验与数学推导 | 7 |

## SFT Pipeline 进度

- [x] Step 0-3: prompt 合成（context + query + 约束 + 参数化扩增 → 2394 条）
- [x] Context 去重（剔除 benchmark 重叠 260 条 → 2134 条 clean）
- [x] Step 3.5: 约束文本动态生成（1-5 条梯度采样 + 冲突检测 + LLM 生成 + 弱项加权 N3/S3/F4）
- [x] Benchmark query 清洗（格式指令从正文移到约束块）
- [x] SFT query 清洗（566/2134 修改）
- [x] 约束数量裁剪（Benchmark: 3-6 → 1-5，SFT: 同步调整）
- [x] Benchmark 10 模型评测（DS×4 + GPT×4 + Qwen3-8B + Qwen3-8B-SFT）
- [x] SFT 输入拼装（sft_data/sft_input_2134.jsonl）
- [x] Step 4: teacher response 生成（GPT-5.4 via Vulcan，2132 条）
- [x] Step 5: 约束打分 + 自动修复（sft_scores → 374 条 Flash 3 轮修复 + 15 条人工修复）
- [x] Step 6: 格式化 ShareGPT 训练格式（sft_sharegpt_2132.json，2132 条）
- [x] SFT 训练 + 评测（Qwen3-8B-SFT: 77.00% prompt / 91.3% instruction，排名第 3）
- ~~GRPO（可选）— 未执行~~

## API 配置

| 用途 | Provider | Base URL | Model |
|------|----------|----------|-------|
| Benchmark 回复生成 | DeepSeek | `https://api.deepseek.com` | deepseek-v4-flash / v4-pro |
| Soft Judge | DeepSeek | `https://api.deepseek.com` | deepseek-v4-flash |
| Teacher (SFT) | DeepSeek | `https://api.deepseek.com` | deepseek-v4-flash (thinking) |
| Qwen3-8B 推理 | SiliconFlow | `https://api.siliconflow.cn/v1` | Qwen/Qwen3-8B |
| GPT-5/5.1/5.2/5.4 | Vulcan 平台 | — | gpt-5 / gpt-5.1 / gpt-5.2 / gpt-5.4 |

### gen_async.py 模型配置

| Key | API Model | Provider | Thinking |
|-----|-----------|----------|----------|
| ds-v4-flash | deepseek-v4-flash | DeepSeek | No |
| ds-v4-pro | deepseek-v4-pro | DeepSeek | No |
| ds-v4-flash-thinking | deepseek-v4-flash | DeepSeek | Yes (high) |
| ds-v4-pro-thinking | deepseek-v4-pro | DeepSeek | Yes (high) |
| qwen3-8b | Qwen/Qwen3-8B | SiliconFlow | No (enable_thinking=False) |

## 关键设计决策

| 决策 | 选择 | 依据 |
|------|------|------|
| 评测框架 | 纯 IF compliance（C6 correctness 独立评测） | 参考 SciIF 双轴设计 |
| eval-prompt 对齐 | eval_config 只含 prompt「附加要求」中的约束 | query 隐式要求不公平 |
| 约束数梯度 | 1-5 条/case，分布 15/20/30/20/15 | 难度梯度 + 统计充分 |
| Judge 模型 | DS-V4-Flash (temperature=0) | 成本低、速度快、agreement ~90% |
| SFT 底座 | Qwen3-8B | 部署成本低，提升空间充足 |
| SFT Teacher | GPT-5.4 (via Vulcan) | Benchmark 最强模型，96% instruction-level |
| SFT 弱项加权 | N3/S3/F4 权重 ×3.0 | Qwen3-8B baseline 这三类最弱 |
| SFT 不教 reasoning | 空 think 标签 | CoT SFT 损害 IF（文献支持） |
| GRPO reward | 仅 Hard checker | 零 API 成本，可大量采样 |

## 常用命令

```bash
# 生成回复（支持多模型并行）
python3 gen_async.py ds-v4-flash ds-v4-pro

# 单模型评测（只评指定模型，不影响其他）
python3 gen_responses_ds.py eval --judge-workers 20 --models ds-v4-pro

# 生成 HTML dashboard
python3 build_stats.py

# SFT 约束采样
cd sft_pipeline && python3 gen_constraint_text.py prepare
```
