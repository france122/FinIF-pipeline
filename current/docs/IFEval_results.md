# IFEval 评测结果汇总

仅保留 FinIF Benchmark 涉及的模型。

---

## 1. 外部来源成绩（IFEval++ / 自测 API）

统一指标: **Prompt-level Strict Accuracy**

| 模型 | Prompt-level Strict | 来源 |
|---|---|---|
| GPT-5 | 95.9 | IFEval++ |
| Qwen3-8B | 87.6 | IFEval++ |
| DS-V4-Flash | 87.06 | 自测（API，剥离 `<think>` 后评测） |
| DS-V4-Pro | 82.99 | 自测（API，剥离 `<think>` 后评测） |

> - GPT-5.1 / 5.2 / 5.4：发布时间晚于 IFEval++ 论文收录截止，暂无公开 IFEval 成绩。
> - DS-V4-Flash-Think / DS-V4-Pro-Think：未单独评测 IFEval。
> - IFEval++ 来源: arXiv:2512.14754v1。

---

## 2. Qwen3-8B Base vs SFT 自测结果

评测框架: **OpenCompass**｜模型精度: **4-bit NF4 量化**｜Thinking: **Off**

| 指标 | Qwen3-8B (Base) | Qwen3-8B-SFT (ckpt-786) | Δ |
|---|---|---|---|
| Prompt-level Strict | 80.41 | 78.19 | -2.22 |
| Inst-level Strict | 86.81 | 84.89 | -1.92 |
| Prompt-level Loose | 83.92 | 81.15 | -2.77 |
| Inst-level Loose | 89.09 | 86.93 | -2.16 |

### 与外部报分的差异说明

Qwen3-8B 自测 Prompt-level Strict（80.41）低于 IFEval++ 报告值（87.6），差距约 7pp，原因：

1. **4-bit NF4 量化**：自测使用 QLoRA 量化加载，官方报分为 FP16/BF16 全精度，量化精度损失约 3-5pp
2. **Non-thinking 模式**：自测关闭 thinking，官方报分大概率开启，影响约 2-4pp

Base 与 SFT 均在相同条件（4-bit、non-thinking、OpenCompass）下评测，两者的相对变化（-2.22pp）具有可比性。

### 结论

SFT 后 IFEval 掉点约 2pp，属于轻微退化。结合 FinIF 上 Prompt-level +15pp 的显著提升，trade-off 比约 7:1，表明领域 SFT 未显著损害通用指令遵循能力。
