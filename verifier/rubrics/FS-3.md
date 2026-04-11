# FS-3

## Score Type Decision

- score_type: binary
- rationale: 约束遵循评测只关心"是否满足"，1=满足，0=不满足，半对算错。

## Judge Instruction

judge 判断回答中专业术语缩写首次出现时是否给出了中文全称。

## Scoring Rubric

| 分值 | 描述 |
|------|------|
| 1 | 缩写首次出现时给出了全称（如'ROE（净资产收益率）'） |
| 0 | 缩写直接使用未给全称 |

---
