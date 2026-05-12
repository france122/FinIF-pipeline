# Qwen3-8B LoRA SFT 实验报告

> 文档记录本次对 Qwen3-8B 进行金融指令微调（SFT）、checkpoint 选择、以及 FinIF 推理侧问题修复与 clean 重跑的最新状态。

---

## 1. 任务目标

使用金融公告领域的结构化指令数据，对 Qwen3-8B 基座模型进行监督微调（Supervised Fine-Tuning），提升模型在 Financial IF Benchmark 上的指令遵循和数值计算能力，同时控制小数据集场景下的过拟合风险。

---

## 2. 基础模型与框架

| 项目 | 值 |
|---|---|
| 模型名称 | Qwen3-8B |
| 本地路径 | `/home/zyz26/models/Qwen/Qwen3-8B` |
| 微调框架 | LLaMA-Factory |
| 推理方式 | Base model + PEFT LoRA adapter |
| 对话模板 | Qwen Chat 模板 |
| Python 环境 | conda `llamafactory` |
| CUDA / PyTorch | CUDA 12.1 / PyTorch 2.5.1+cu121 |

---

## 3. 数据与预处理

### 3.1 原始 SFT 数据

| 项目 | 值 |
|---|---|
| 原始文件 | `finetune/data/raw_sftdata_shareGPT.json` |
| 原始格式 | ShareGPT |
| 转换后文件 | `finetune/data/qwen3_8b_sft.json` |
| 训练样本总数 | 2,132 |
| 训练集 / 验证集 | 2,089 / 43 |
| 注册名 | `financial_if_qwen3_8b_sft` |

### 3.2 数据特点

样本主要来自金融公告、财报、行情与基金问答场景。任务普遍要求模型从长文本中抽取关键字段、完成简单计算，并严格遵守输出格式约束，例如 JSON 输出、段落数限制、是否禁止列表、首词约束、风险提示声明等。

---

## 4. 最终训练配置

### 4.1 微调方法

由于单卡 24 GB 显存无法稳定承载 8B 模型的全精度 LoRA，本次正式实验采用 QLoRA：

| 配置项 | 值 |
|---|---|
| 微调类型 | LoRA |
| 基座量化 | 4-bit NF4 |
| double quantization | true |
| LoRA target | `all` |
| LoRA rank / alpha / dropout | 8 / 16 / 0.05 |
| cutoff length | 3072 |

### 4.2 训练超参

| 配置项 | 值 |
|---|---|
| GPU | RTX 3090 × 8 |
| per-device train batch size | 1 |
| gradient accumulation | 1 |
| 等效 global batch size | 8 |
| learning rate | 1e-4 |
| lr scheduler | cosine |
| warmup ratio | 0.03 |
| weight decay | 0.01 |
| gradient checkpointing | true |
| epochs | 5 |
| total steps | 1310 |
| eval / save strategy | epoch |

说明：8 卡正式训练从基座模型启动，不是在早期单卡实验产物上继续训练。

---

## 5. 训练结果

### 5.1 完成情况

8 卡正式训练已完成，最终输出目录为：

`/home/zyz26/paper_for_financial_if_benchmark/finetune/outputs/qwen3_8b_lora_8gpu`

监控日志显示最终训练在约 **33 分 58 秒** 内完成 1310 step，最后一次评估 loss 为 **0.6815587878**。

### 5.2 各 epoch Eval Loss

| Epoch | Step | Checkpoint | Eval Loss |
|---|---:|---|---:|
| 1 | 262 | `checkpoint-262` | 0.7140936255 |
| 2 | 524 | `checkpoint-524` | 0.6782875061 |
| 3 | 786 | `checkpoint-786` | 0.6705432534 |
| 4 | 1048 | `checkpoint-1048` | 0.6741762757 |
| 5 | 1310 | `checkpoint-1310` | 0.6815587878 |

### 5.3 训练结论

从 loss 曲线看，验证集表现从 epoch 1 到 epoch 3 持续改善，**epoch 3 (`checkpoint-786`) 达到最低 eval loss**。此后 epoch 4、epoch 5 开始回升，说明在当前 2,132 条样本规模下，模型已经出现轻微过拟合迹象。

因此，若仅依据 eval loss 进行粗筛，`checkpoint-786` 是最合理的候选；同时按照“指标接近时优先更早 epoch”的原则，epoch 3 也优于后续 epoch。

### 5.4 Loss 图

已生成两张 SVG 图，便于复核：

- `finetune/outputs/qwen3_8b_lora_8gpu/eval_loss_by_epoch.svg`
- `finetune/outputs/qwen3_8b_lora_8gpu/train_eval_loss_by_epoch.svg`

---

## 6. FinIF 推理与 checkpoint 选择

### 6.1 推理范围

FinIF 基准集原始文件为：

`/home/zyz26/paper_for_financial_if_benchmark/data/FinIF.jsonl`

已转换为本地生成输入：

`/home/zyz26/paper_for_financial_if_benchmark/data/FinIF_generation_input.jsonl`

本轮先只对 **epoch 3 / checkpoint-786** 做全量回复生成，用于后续交给其他 agent 打分。

### 6.2 初始推理问题

首轮生成出的 `FinIF_responses_checkpoint786.jsonl` / `FinIF_responses_checkpoint786_dedup.jsonl` 存在明显脏输出，主要表现为：

1. `response` 中混入原始 prompt 尾部，常见于“附加要求”“请基于以上...”等片段。
2. 少量样本携带 `<think>...</think>` 或 `assistant` 前缀。
3. 旧文件多次续跑后出现重复样本，原始文件一度达到 105 行。

用户抽查结论是：100 条里有 56 条存在 prompt 泄漏，另有 5 条带 thinking 标签。

### 6.3 根因分析

问题不在数据转换，而在推理脚本 `scripts/generate_local_responses_peft.py` 的 batch 解码逻辑：

- 推理时采用了 `tokenizer.padding_side = "left"`
- 旧逻辑使用 `attention_mask.sum(dim=1)` 作为切分起点
- 在左侧 padding 的 batch 场景下，`generated_ids` 包含的是“补齐后的完整 prompt + 续写”，因此旧切分会把 prompt 尾部错误地并入回复

这会直接导致 prompt 泄漏，看起来像模型把题目复述进了 `response`。

### 6.4 已完成的推理修复

脚本已修复，核心改动如下：

1. **修正 assistant 回复截取逻辑**  
   不再按 `attention_mask.sum()` 切分，而是按 batch 统一的 `prompt_width = input_ids.shape[1]` 截取，只保留真实续写部分。

2. **默认关闭 thinking 模式**  
   现在默认走 non-thinking 生成；如未来需要，可显式传 `--enable-thinking`。

3. **增加后处理兜底**  
   自动清理残留的 `<think>...</think>` 块，以及开头的 `assistant` / `Assistant:` 前缀。

4. **保留自适应 batch OOM 处理**  
   若 batch=4 OOM，则自动回退到 2 或 1，避免全量任务中断。

---

## 7. Clean 重跑状态

为避免污染旧结果，本次修复后重新输出到新文件：

- clean 输出：`data/FinIF_responses_checkpoint786_clean.jsonl`
- clean 监控：`data/FinIF_responses_checkpoint786_clean.monitor.log`

截至 **2026-05-12 00:06**，clean 重跑进度为：

| 项目 | 值 |
|---|---:|
| 已生成样本 | 28 |
| 总样本数 | 100 |
| 当前进度 | 28% |

已抽查前几条 clean 结果，`response` 开头正常，未再看到 prompt 尾巴、`assistant` 前缀或 `<think>` 标签混入。

---

## 8. 工程问题与解决记录

| 问题 | 原因 | 解决方案 |
|---|---|---|
| GitHub clone 失败 | 网络无法稳定访问 GitHub | 改用 Gitee 镜像克隆 |
| `av` / `librosa` / `tiktoken` 构建失败 | 缺少系统多媒体库或 Rust 编译器 | 安装时跳过非必要依赖 |
| `pyarrow` 构建失败 | 本地编译链不完整 | 强制安装预编译 wheel |
| `numpy` 版本冲突 | `pyarrow` 拉起 numpy 2.x | 显式约束 `numpy<2.0.0` |
| 单卡训练 OOM | 8B + LoRA + 长上下文超出 24 GB 显存 | 切换 QLoRA，缩短上下文到 3072 |
| `bitsandbytes` 缺失 | QLoRA 依赖未自动装齐 | 手动安装 |
| 8 卡恢复训练时报 `_pickle.UnpicklingError` | `rng_state_*.pth` 与当前 `torch.load(weights_only=True)` 兼容性问题 | 迁出 checkpoint 内 `rng_state_*.pth` 后继续 |
| 训练日志绘图缺失前半段 | `trainer_log.jsonl` 在 resume 后不完整 | 从所有 `checkpoint-*/trainer_state.json` 汇总 eval loss |
| 推理 batch=4 OOM | 显存碎片 / 并发旧进程占用 | 清理旧进程 + 自适应 batch 回退 |
| 推理结果混入 prompt / `<think>` | 左 padding 场景下 assistant 截取逻辑错误 | 改按 `prompt_width` 切分，默认 non-thinking，并做后处理清洗 |

---

## 9. 当前结论

1. SFT 训练本身已经顺利完成，5 个 epoch 中 **epoch 3 / checkpoint-786** 的 eval loss 最优。
2. 模型在训练侧有正向收敛迹象，但从 epoch 4 开始验证 loss 回升，存在轻微过拟合风险。
3. 第一版 FinIF 推理结果受推理脚本 bug 影响，不宜直接用于正式评测。
4. 推理脚本已修复，clean 重跑正在进行中；正式打分应优先使用 `FinIF_responses_checkpoint786_clean.jsonl`。

---

## 10. 关键文件索引

```text
finetune/
├── configs/
│   └── sft_qwen3_8b_lora.yaml
├── outputs/qwen3_8b_lora_8gpu/
│   ├── checkpoint-262/
│   ├── checkpoint-524/
│   ├── checkpoint-786/
│   ├── checkpoint-1048/
│   ├── checkpoint-1310/
│   ├── eval_loss_by_epoch.svg
│   ├── train_eval_loss_by_epoch.svg
│   └── monitor.log
├── scripts/
│   ├── prepare_sft_data.py
│   ├── monitor_training.py
│   ├── plot_eval_loss.py
│   ├── plot_train_eval_loss.py
│   └── generate_local_responses_peft.py
└── SFT_REPORT.md

data/
├── FinIF.jsonl
├── FinIF_generation_input.jsonl
├── FinIF_responses_checkpoint786.jsonl
├── FinIF_responses_checkpoint786_dedup.jsonl
├── FinIF_responses_checkpoint786_clean.jsonl
└── FinIF_responses_checkpoint786_clean.monitor.log
```
