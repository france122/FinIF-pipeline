# SFT 数据修复 & 导出 TODO

## 现状
- 2132 条 GPT-5.4 回复已评测（`sft_data/sft_scores.json`）
- 1737 条全过（81.5%），395 条有约束不过
- 修复任务已提取：`sft_data/repair_v2.json`（395 条，含 judge reason）
- 修复脚本已写好：`sft_data/async_repair.py`

## 待办

### Step 1: 试跑 100 条修复
```bash
cd /Users/minimax/Desktop/FinIF/current
python3 -u sft_data/async_repair.py --limit 100
```
- 输出：`sft_data/flash_repair_v2.json`（100 条）
- 30 并发 async 调 ds-v4-flash
- 每条输入：原始回复 + 未通过约束 + judge reason + 所有约束列表
- 脚本末尾自动跑 hard checker 验证

### Step 2: 评测这 100 条修复结果
```bash
python3 -u sft_data/verify_repairs.py
```
- 对 `flash_repair_v2.json` 中的 100 条跑**所有约束**（hard + soft）
- Hard：本地 `checkers.py`（秒级）
- Soft：async 调 ds-v4-flash judge
- 输出：`sft_data/repair_scores.json` + 打印统计
- **看修复质量如何，确认链路没问题**

**脚本需要新写**（`sft_data/verify_repairs.py`），逻辑：
1. 加载 `flash_repair_v2.json` 和 `constraint_gen_output_v3.jsonl`
2. 对每条修复后的回复，跑该 sample 的所有约束（不只是之前失败的）
3. Hard：调 `checkers.py` 函数
4. Soft：async 调 ds-v4-flash judge（复用 `score_sft_responses.py` 的 judge prompt）
5. 输出每条 pass/fail 详情 + 整体统计

### Step 3: 质量 OK → 全量修复剩余 295 条
```bash
python3 -u sft_data/async_repair.py              # 全量 395 条
# 或者只跑剩余 295 条（跳过已修的 100 条），需要加 --skip-existing 逻辑
```

### Step 4: 评测剩余 295 条
```bash
python3 -u sft_data/verify_repairs.py             # 自动只评新增的 295 条
```

### Step 5: 生成 review HTML
- 行级 diff 高亮（红删绿增），不是简单左右对比
- 按 tag 过滤
- 显示约束 + judge reason

### Step 6: 导出 LLaMA-Factory 格式
```bash
python3 score_sft_responses.py export --threshold 1.0
```
- 合并 1737 条原始通过 + 修复通过的样本
- ShareGPT 格式 + 空 think 标签
- 输出 `finif_sft_train.json` + `dataset_info.json`

## 注意事项
- 1737 条全过数据在 `sft_data.jsonl` 里，用 `sft_scores.json` 的 `all_pass=true` 过滤
- 之前 sub-agent 修复质量差（只做表面修改），已弃用
- `async_repair.py` 的 prompt 包含 judge reason，指导 ds-v4-flash 精准修改
- 修复后必须重新评测验证，不能直接用
- 仍不通过的样本丢弃

## 数据位置
| 文件 | 说明 |
|------|------|
| `sft_data/sft_data.jsonl` | 2132 条 GPT-5.4 原始回复（全量，Vulcan 格式，`trace_id` 为 sample_id，回复在 `vulcan_output.llm_response`） |
| `sft_data/sft_scores.json` | 2132 条评测结果，每条有 `all_pass` 字段标记是否全过，`checks` 里有各约束 pass/fail + judge reason |
| `sft_data/constraint_gen_output_v3.jsonl` | 2134 条约束配置（`sampled_constraints` 数组） |
| `sft_data/repair_v2.json` | 395 条不合格样本的修复任务（含原始回复 + 失败约束 + judge reason + 所有约束列表） |
| `sft_data/async_repair.py` | async 修复脚本（AsyncOpenAI, 30 并发，`--limit N` 控制数量） |
| `sft_data/verify_repairs.py` | **待写** — 只对修复后的回复跑评测 |
| `score_sft_responses.py` | 评测 + 导出脚本（`score` / `export` 子命令） |
| `checkers.py` | hard checker 函数 |

**注意**：1737 条全过的数据没有单独导出过，目前混在 `sft_data.jsonl` 全量文件里，通过 `sft_scores.json` 的 `all_pass=true` 过滤。最终导出时 `score_sft_responses.py export` 会自动合并。
