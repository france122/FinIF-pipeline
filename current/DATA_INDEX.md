# FinIF 数据索引

核心数据文件的分类索引，按数据流顺序组织。

---

## 1. 任务分类体系

| 文件 | 说明 |
|------|------|
| `sft_pipeline/config/task_labels.json` | L1/L2 任务标签定义（T1 提取计算 / T2 综合分析 / T3 推理验证，共 11 个 L2 子类） |

## 2. 约束分类体系

| 文件 | 说明 |
|------|------|
| `benchmark/constraint_taxonomy.json` | 约束体系规范：5 大类 20 子标签（F/N/L/S/C），包含 hard checker 参数定义和 soft rubric 模板 |

## 3. Benchmark 数据

| 文件 | 说明 |
|------|------|
| `benchmark/benchmark_all.json` | 100 cases 完整数据（case_id + context + prompt），724K |
| `benchmark/benchmark_prompts_100.jsonl` | 100 条组装好的 prompt（case_id + prompt），直接用于模型推理输入，392K |
| `benchmark/eval_config_all.json` | 300 条 IF 约束配置（每个 case 1-5 条），与 prompt「附加要求」对齐，92K |

## 4. 打分体系

| 文件 | 说明 |
|------|------|
| `checkers.py` | ~50 个 Hard checker 函数（规则判定，返回 bool） |
| `gen_responses_ds.py` | Benchmark 评测主脚本（gen 生成回复 / eval 双轨打分） |
| `score_sft_responses.py` | SFT 训练数据打分脚本（同样的双轨机制） |

## 5. 训练数据

| 文件 | 说明 |
|------|------|
| `sft_pipeline/data/samples_clean_2134.jsonl` | 2134 条清洗后的 sample（context_text + query_text），18M |
| `sft_pipeline/data/constraint_gen_output_v3.jsonl` | 约束采样结果（pipeline 原始输出），3.0M |
| `sft_data/constraint_gen_output_v3.jsonl` | 约束采样结果（冲突清理后的最终版），3.0M |
| `sft_data/sft_input_2134.jsonl` | 最终 SFT 输入 prompt（context + query + 约束块拼装完成），7.8M |

> `sft_pipeline/data/sft_input_2134.jsonl` 与 `sft_data/sft_input_2134.jsonl` 内容完全相同（md5 一致），前者为 pipeline 产出位置，后者为训练引用位置。

## 6. 各模型对 Benchmark 的回复

目录：`benchmark/responses/`

| 文件 | 模型 | 大小 |
|------|------|------|
| `responses_gpt5.jsonl` | GPT-5 | 704K |
| `responses_gpt5.1.jsonl` | GPT-5.1 | 992K |
| `responses_gpt5.2.jsonl` | GPT-5.2 | 732K |
| `responses_gpt5.4.jsonl` | GPT-5.4 | 924K |
| `responses_ds-v4-flash.jsonl` | DS-V4-Flash | 660K |
| `responses_ds-v4-flash-thinking.jsonl` | DS-V4-Flash-Think | 652K |
| `responses_ds-v4-pro.jsonl` | DS-V4-Pro | 696K |
| `responses_ds-v4-pro-thinking.jsonl` | DS-V4-Pro-Think | 684K |
| `responses_qwen3-8b.jsonl` | Qwen3-8B (base) | 664K |
| `responses_qwen3-8b-sft.jsonl` | Qwen3-8B-SFT | 2.0M |

## 7. Benchmark 打分

目录：`benchmark/scores/`

| 文件 | 模型 |
|------|------|
| `scores_gpt5.json` | GPT-5 |
| `scores_gpt5.1.json` | GPT-5.1 |
| `scores_gpt5.2.json` | GPT-5.2 |
| `scores_gpt5.4.json` | GPT-5.4 |
| `scores_ds-v4-flash.json` | DS-V4-Flash |
| `scores_ds-v4-flash-thinking.json` | DS-V4-Flash-Think |
| `scores_ds-v4-pro.json` | DS-V4-Pro |
| `scores_ds-v4-pro-thinking.json` | DS-V4-Pro-Think |
| `scores_qwen3-8b.json` | Qwen3-8B (base) |
| `scores_qwen3-8b-sft.json` | Qwen3-8B-SFT |

## 8. GPT-5.4 对训练数据的原始回复

| 文件 | 说明 |
|------|------|
| `sft_data/sft_data.jsonl` | GPT-5.4 通过 Vulcan 平台生成的 teacher 回复（2132 条，2 条缺失），34M。回复在 `vulcan_output.llm_response` 字段 |

## 9. 处理后的训练数据回复

| 文件 | 说明 |
|------|------|
| `sft_data/sft_scores.json` | 原始回复的逐约束打分结果，1.4M |
| `sft_data/flash_repair_v2.json` | 374 条自动修复后的回复（DS-V4-Flash 3 轮修复），覆盖原始回复，1.6M |
| `sft_data/manual_repair_15.jsonl` | 15 条人工修复记录，128K |
| `sft_data/sft_sharegpt_2132.json` | **最终训练数据**：ShareGPT 格式（原始回复 + 374 条修复覆盖），2132 条，19M |

数据组装关系：`sft_data.jsonl`（原始）→ `flash_repair_v2.json`（374 条覆盖）→ `manual_repair_15.jsonl`（15 条覆盖）→ `sft_sharegpt_2132.json`（最终）

---

## 其他文件

### 脚本

| 文件 | 说明 |
|------|------|
| `gen_async.py` | 异步并行回复生成（多 provider: DS / SiliconFlow） |
| `build_stats.py` | HTML dashboard 生成 |
| `trim_constraints.py` | 约束数量裁剪（3-6 → 1-5），已完成 |
| `sft_data/convert_sharegpt.py` | 转换为 ShareGPT 训练格式 |
| `sft_data/async_repair.py` | Round 1 批量修复 |
| `sft_data/iterative_repair.py` | Round 2 迭代修复 |
| `sft_data/repair_round3.py` | Round 3 精准修复 |
| `sft_data/verify_repairs.py` | 修复结果验证 |
| `sft_pipeline/gen_constraint_text.py` | 约束采样 + LLM 生成约束文本 |
| `sft_pipeline/step1~step9` | SFT pipeline 各步骤脚本 |

### HTML 可视化

| 文件 | 说明 |
|------|------|
| `html/benchmark_stats.html` | 10 模型对比 dashboard |
| `html/data_review.html` | 100 case 数据审查页面 |
| `html/review_responses.html` | 模型回复详情查看 |
| `html/constraint_count_chart.py` | 约束数量 vs prompt-level 准确率出图脚本 |
| `html/task_taxonomy_chart.py` | FinIF 任务分类体系旭日图出图脚本 |
| `sft_data/manual_repair_review.html` | 15 条手动修复审查 |
| `sft_data/sft_stats.html` | SFT 数据约束分布统计 |

### 文档

| 文件 | 说明 |
|------|------|
| `AGENT.md` | 项目总览（模型配置、评测结果、目录结构） |
| `docs/pipeline.md` | 全流程 Pipeline 详细说明 |
| `docs/FinIF_eval_results.md` | 10 模型 FinIF 评测详细报告 |
| `docs/IFEval_results.md` | IFEval 通用 IF 评测结果 |
| `docs/sft_train.md` | SFT 训练实验报告 |
| `docs/sft_findings.md` | SFT 训练效果分析 |
| `docs/项目总结.md` | 项目总结 |
| `docs/todo.md` | 会议论文改造与流程优化 TODO |
| `docs/毕设项目.docx` | 毕设项目文档 |

### 流程图

| 文件 | 说明 |
|------|------|
| `diagrams/pipeline.drawio` | Pipeline 流程图 |
| `diagrams/pipeline copy.drawio` | Pipeline 流程图副本 |
| `diagrams/whole_pipeline.drawio` | 全流程图 |

### 归档

| 目录 | 说明 |
|------|------|
| `archive/` | 旧版脚本、数据、打分、文档（含 GPT Vulcan 原始格式回复） |
