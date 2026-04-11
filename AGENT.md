# AGENT.md — 项目导引

> 本文件供 AI agent 新 session 时快速了解项目结构和工作规范。

## 项目简介

**中文金融指令遵循（Instruction Following）Benchmark**，填补"中文 + 金融 + IF"的空白。

核心流程：`query 池 × constraint 池 → LLM 选约束组合 → 生成 track → 被评测模型生成 response → 评分 → SFT 训练数据`

## 快速上手

1. 先读本文件了解项目结构
2. 读 `../memory/project_overview.md` 了解当前状态
3. 读 `../memory/progress.md` 看 TODO 和接着做什么
4. 按需读 `../memory/query_pool_status.md`（数据/评分详情）或 `../memory/literature_and_benchmarks.md`（文献引用）

## 关键规范

| 规范 | 说明 |
|------|------|
| 语言 | 所有 query 必须是**中文** |
| 评分 | **binary 1/0**，`result_pass` score=1, `result_fail` score=0，半对算错 |
| Hard 约束 | 用 rule checker 本地验证（`verifier/rules/*.py`） |
| Soft 约束 | 用 LLM-as-a-judge 评分（GPT-5, temperature=0） |
| 约束 ID | `G/F × H/S`（GH=通用硬, GS=通用软, FH=金融硬, FS=金融软） |
| 反直觉约束 | 每条 track 最多选 1 个 |
| 互斥约束对 | FS-3↔FS-10, GH-7↔GH-18, GH-6↔GH-19, FH-8↔FS-4, FH-9↔FS-4, FH-9↔FS-5 |

## 目录结构

```
paper_for_financial_if_benchmark/
├── AGENT.md                          ← 本文件（项目导引）
│
├── data/
│   ├── fineval_raw/                  ← FinEval 原始考试题（4 个 JSON）
│   ├── query_pool/
│   │   ├── query_pool_v3.json        ← 502 条 query（权威版本）
│   │   └── expansion/
│   │       └── decoupled_queries.json← 外部 query 的 constraint 解耦结果
│   ├── tracks/
│   │   ├── all_tracks.jsonl          ← 全量 4,611 条 track
│   │   ├── train_tracks.jsonl        ← Train 452q, 4,147t
│   │   ├── test_tracks.jsonl         ← Test 50q, 464t
│   │   ├── test_response_input.jsonl ← Test 集 response 生成输入（464 条，送 Vulcan）
│   │   └── {all,train,test}_stats.*  ← 数据统计（JSON + PNG 图表）
│   └── scores/
│       ├── hard_scores.json          ← Hard 约束评分结果（rule checker 输出）
│       ├── soft_scores_raw.jsonl     ← Soft 约束评分原始结果（含 10 条污染数据）
│       ├── soft_scores_clean.jsonl   ← Soft 约束评分结果（排除污染，214 条有效）
│       └── review_data.json          ← Hard+Soft 合并的评分 review 数据（供 score_review.html）
│
├── docs/
│   ├── constraint_pool.md            ← 60 条约束池完整文档（分类/描述/互斥对/来源）
│   ├── constraint_reference_table.csv← 约束元数据权威表（ID/hardness/check_mode/text）
│   └── survey_scholarpeer.md         ← 文献综述
│
├── verifier/                         ← 评分系统
│   ├── base.py                       ← CheckResult 基类（score=1 pass / score=0 fail）
│   ├── registry.py                   ← 约束注册表（从 CSV 加载，校验 hardness/check_mode）
│   ├── rule_runner.py                ← Hard rule 执行器
│   ├── rubric_runner.py              ← Soft rubric prompt 构建（binary 1/0 system prompt）
│   ├── rules/*.py                    ← 28 个 Hard rule checker（每个文件对应一个约束 ID）
│   └── rubrics/*.md                  ← 32 个 Soft rubric（每个文件对应一个约束 ID）
│
├── scripts/
│   ├── gen_track_vulcan_input.py     ← 生成 Vulcan track 生成任务的输入 JSONL
│   ├── score_responses.py            ← 评分主脚本（hard + soft）
│   ├── score_soft_local.py           ← Soft 本地评分（3 并发调 GPT-5 via Minimax 代理）
│   ├── generate_verifier_scaffold.py ← 约束池变更时自动生成 checker/rubric 骨架
│   └── decouple_query_constraint.py  ← query-constraint 解耦（从外部 query 提取约束）
│
├── prompts/
│   ├── track_gen_system_prompt.md    ← Track 生成 system prompt（约束池全文 + 选约束规则）
│   └── track_gen_user_template.md    ← Track 生成 user prompt 模板
│
├── skills/vulcan_gen.md              ← Vulcan 平台任务配置（Track 生成 / Response 生成 / 评分）
├── ref_local_gpt.py                  ← Minimax 代理调 GPT/Gemini/Claude API
├── query_review.html                 ← Query 解耦审核前端（加载 decoupled_queries.json）
├── score_review.html                 ← 评分 review 前端（加载 review_data.json）
├── vulcan/                           ← Vulcan 平台任务数据
├── surveys/                          ← 文献调研笔记（InfoBench 等）
├── history/                          ← 已废弃的旧文件（仅供追溯，不参与当前流程）
└── logs/                             ← 运行日志
```

## 数据文件索引

### data/query_pool/ — Query 池

| 文件 | 内容 | 格式 | 条数 |
|------|------|------|------|
| `query_pool_v3.json` | 502 条中文金融 query，来自 FinEval/FIFE/DISC/WritingBench 四个来源 | JSON array，每条含 query_id / query / source_type | 502 |
| `expansion/decoupled_queries.json` | 从 DISC/WritingBench 的 250 条外部 query 中解耦出的 base_instruction + constraints | JSON array | 472 条约束 |

### data/tracks/ — Track 数据

| 文件 | 内容 | 格式 | 条数 |
|------|------|------|------|
| `all_tracks.jsonl` | 全量 track（每条 = 1 query + N 个约束 + 参数化后的 prompt） | JSONL，每行一个 JSON | 4,611 |
| `train_tracks.jsonl` | 训练集 track（452 个 query，与 test 零重叠） | 同上 | 4,147 |
| `test_tracks.jsonl` | 测试集 track（50 个 query） | 同上 | 464 |
| `test_response_input.jsonl` | 测试集 response 生成输入（送 Vulcan GPT-5.4 生成回答） | JSONL，含 messages 字段 | 464 |
| `{all,train,test}_stats.json` | 各切分的约束覆盖/分布统计 | JSON | — |
| `{all,train,test}_stats.png` | 统计可视化图表 | PNG | — |

### data/scores/ — 评分结果

| 文件 | 内容 | 格式 | 条数 |
|------|------|------|------|
| `hard_scores.json` | Hard 约束评分（rule checker 输出），每条含 constraint_id / passed / message | JSON array | 324 |
| `soft_scores_raw.jsonl` | Soft 约束评分原始结果（GPT-5 judge），含 10 条 prompt 污染数据 | JSONL | 224 |
| `soft_scores_clean.jsonl` | Soft 约束评分清洗版（排除污染），用于最终统计 | JSONL | 214 |
| `review_data.json` | Hard + Soft 合并的评分数据，供 `score_review.html` 展示 review | JSON array | 245 |

### data/fineval_raw/ — 原始数据源

| 文件 | 内容 |
|------|------|
| `agent/apiutil-eval.json` | FinEval API 工具类考试题（原始） |
| `agent/findiag-eval.json` | FinEval 金融诊断类考试题（原始） |
| `industry/finsales-eval.json` | FinEval 金融销售类考试题（原始） |
| `industry/finsuggestion-eval.json` | FinEval 金融建议类考试题（原始） |

## 约束池概览（60 条）

| 模块 | 数量 | 验证方式 | 示例 |
|------|------|----------|------|
| GH | 19 | rule checker | 字数限制、Markdown、关键词、JSON 格式 |
| GS | 8 | LLM judge | 先结论后分析、书面语、客观中立 |
| FH | 9 | rule checker | 风险提示、免责声明、小数位数、禁%/禁数字 |
| FS | 24 | LLM judge | ESG 视角、排序输出、通俗语言、竞品对比 |

权威定义见 `docs/constraint_reference_table.csv`（每行含 constraint_id / module / hardness / check_mode / score_type / constraint_text）

## 各环节模型

| 环节 | 模型 | 平台 |
|------|------|------|
| Track 组合（选约束+参数化） | GPT-5.1 | Vulcan |
| Test Response 生成 | GPT-5.4 | Vulcan |
| Soft 评分 Judge | GPT-5 (gpt-5-2025-08-07) | 本地 `ref_local_gpt.py` 调 Minimax 代理 |
| Hard 评分 | rule checker | 本地 `verifier/` |

## 修改约束池的 checklist

新增/修改/删除约束时，需同步更新以下文件：

1. `docs/constraint_reference_table.csv` — 约束元数据（ID/module/hardness/check_mode/score_type/text）
2. `docs/constraint_pool.md` — 约束池文档（分类表格、条数统计）
3. Hard 约束 → `verifier/rules/{ID}.py`（rule checker）
4. Soft 约束 → `verifier/rubrics/{ID}.md`（rubric）
5. `prompts/track_gen_system_prompt.md` — track 生成 prompt 中的约束池全文
6. 验证：`python3 -c "from verifier.registry import load_constraint_registry; r = load_constraint_registry(); print(len(r))"` 应无报错

## GPT-5 API 注意事项

- Vulcan 平台 GPT 系列用 Responses API：前处理传 `input`（不是 `messages`），后处理从 `output[].type=="message" → content[].type=="output_text" → text` 提取
- GPT-5 需要 `max_completion_tokens`（不是 `max_tokens`），且包含 reasoning tokens，需预留 +2048
- `ref_local_gpt.py` 中已有 GPT-5 分支处理

## 已知问题

- Soft judge 宽判：GS 模块 100% pass 可能偏高，考虑双 judge 或更严格 prompt
- 约束数量分布不均：1约束:2约束:3约束 ≈ 2:3:4
- Track 数据中旧 FH-4（排序）和旧 FH-10（禁英文缩写）需批量替换为 FS-12 / FS-13
