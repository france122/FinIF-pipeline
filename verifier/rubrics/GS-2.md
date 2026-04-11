# GS-2

## Score Type Decision

- score_type: binary
- rationale: 约束遵循评测只关心"是否满足"，1=满足，0=不满足，半对算错。

## Judge Instruction

judge 判断回答末尾是否包含一段总结性内容，起归纳收束作用。

## Scoring Rubric

| 分值 | 描述 |
|------|------|
| 1 | 回答最后一段（或明确标注的总结段）对前文进行了归纳总结 |
| 0 | 回答戛然而止，末尾无任何总结归纳 |

---
