# Train-Pool Judge Alignment

训练数据筛样时，judge 逻辑必须与当前 FinIF-Test / hard300 benchmark 对齐。

## Locked Protocol

- evaluator：`evaluation/evaluate_responses.py`
- dataset：当前 IF-clean schema 数据集
- route policy：
  - `check_type=rule` 只走本地 checker
  - `check_type=LLM` 只走 item-batched LLM judge
  - 不允许 rule/LLM 隐式 fallback
- judge model：`gpt-4o`
- judge API：`responses.create`
- judge temperature：`0`
- judge top_p：`1`
- judge response format：`json_object`
- repeats：`1`
- parse_retries：`2`
- strict usable-sample rule：
  - 只保留 `summary.exact_item_pass_rate` 口径下 **item 全 IF constraints 通过** 的样本
  - 不能用 `micro_score`、`final_score_0_1`、`quality_score` 替代 strict pass

## Official Script

训练池打分默认使用：

- `evaluation/score_train_pool_with_benchmark_judge.py`

这个 wrapper 会强制复用 benchmark evaluator 和 judge 参数，并把 manifest / hyperparameter 归档写全。

## Current Official Train Pool

- dataset:
  - `outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_train764_excluding_hard300_ifclean.jsonl`

## Notes

- 如果 benchmark judge protocol 将来变动，训练池 judge protocol 必须同步更新。
- 任何“为了省钱/省时”单独改 judge model、judge prompt、repeats、parse_retries、quality cap 或 route policy 的做法，都要明确记录为非 benchmark-aligned。
