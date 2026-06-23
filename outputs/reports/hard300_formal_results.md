# Hard300 Formal Results

Compact reporting view for the formal hard300 comparison.
`MSR`: prompt-level pass rate when all `LLM`-judged constraints pass.
`RSR`: prompt-level pass rate when all `rule` constraints pass.
`OSR`: prompt-level pass rate when all constraints pass.

| Model | MSR | RSR | OSR | Quality |
|---|---:|---:|---:|---:|
| GPT-5.5 | 62.67% | 92.33% | 58.67% | 7.40 |
| GPT-5 | 58.00% | 81.00% | 47.33% | 7.05 |
| GLM5.1 | 26.67% | 79.33% | 20.33% | 4.88 |
| DS-v4-pro | 23.67% | 66.67% | 16.00% | 4.68 |
| DS-v4-flash | 17.67% | 62.33% | 9.00% | 4.27 |
| Qwen3.5-27B | 15.33% | 63.67% | 9.00% | 4.08 |
| Qwen3.5-9B | 8.67% | 51.33% | 4.00% | 3.60 |
| Qwen3.5-4B | 9.33% | 1.67% | 0.00% | 3.63 |

Teacher recommendation for same-style distillation: prioritize `GPT-5.5`, with `GPT-5` as a secondary teacher or contrast baseline.
Reason: they are the only models above 90% micro IF, and they preserve much higher work-product quality than the open-weight or lower-cost baselines.

Caution: the original benchmark goal for the strongest model was `OSR <= 50%`; `GPT-5.5` is currently `58.67%`, so the benchmark is useful but still easier than the desired target line.
