# Vulcan Gen Data Stage 1 for `gpt-oss-120b`

这套文件用于第一阶段“生成回复”任务，不负责打分。

数据源默认使用当前已物化完成的 `5500` 口径 filled tracks：

- `data/tracks/ds_5500_run1_materialized/id_heldout_all_tracks_filled.json`

## 文件说明

- `build_input.py`
  - 从新的 filled tracks 生成 Vulcan 输入 `input.jsonl`
- `preprocess.py`
  - 提取 `system` 到顶层，并设置适合 `gpt-oss-120b` 的生成参数
- `postprocess.py`
  - 提取模型回复并保留样本级 metadata，便于后续做评分任务

## 推荐参数

当前默认写在 `preprocess.py` 中：

- `temperature = 0.2`
- `top_p = 0.95`
- `max_tokens = 1800`

这套配置偏保守，目标是：

- 尽量稳定遵循附加约束
- 保留一定生成灵活性
- 避免过长回答影响后续 verifier 和 judge 任务

如果后续发现模型回答过短或过于模板化，可以优先尝试：

- 把 `max_tokens` 提到 `2200`
- 或把 `temperature` 微调到 `0.3`

## 生成输入数据

生成全量 `5500` 条：

```bash
python3 vulcan/gen_data_stage1_gpt_oss_120b/build_input.py
```

只生成测试集：

```bash
python3 vulcan/gen_data_stage1_gpt_oss_120b/build_input.py --splits test
```

只生成某个 track：

```bash
python3 vulcan/gen_data_stage1_gpt_oss_120b/build_input.py --tracks Mixed-track
```

例如只生成 `Hard-track`：

```bash
python3 vulcan/gen_data_stage1_gpt_oss_120b/build_input.py --tracks Hard-track
```

小样本冒烟：

```bash
python3 vulcan/gen_data_stage1_gpt_oss_120b/build_input.py --splits test --limit 20
```

## Vulcan 侧使用建议

任务类型建议设为“单轮生成”。

模型选择：

- `gpt-oss-120b`

上传文件：

1. 输入数据：`input.jsonl`
2. 前处理：`preprocess.py`
3. 后处理：`postprocess.py`

## 输出结果用途

这一步输出的是候选回答，后续应再展开为第二阶段评分任务：

- `hard` 约束走 `rule` 程序校验
- `soft` 约束走 `LLM-as-a-judge`
