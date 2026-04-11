# FS-4

## Score Type Decision

- score_type: binary
- rationale: 约束遵循评测只关心"是否满足"，1=满足，0=不满足，半对算错。

## Judge Instruction

judge 判断回答是否引用了具体财务指标数据（如'ROE为15.3%'）。

## Scoring Rubric

| 分值 | 描述 |
|------|------|
| 1 | 回答中出现了具体的财务指标及其数值 |
| 0 | 无任何具体财务指标数据，仅定性描述 |

---
