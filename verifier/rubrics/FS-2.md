# FS-2

## Score Type Decision

- score_type: binary
- rationale: 约束遵循评测只关心"是否满足"，1=满足，0=不满足，半对算错。

## Judge Instruction

judge 判断回答中的核心主张/数据是否标注了信息来源。

## Scoring Rubric

| 分值 | 描述 |
|------|------|
| 1 | 核心数据或主张标注了来源（如'据XX报告''根据XX数据'） |
| 0 | 数据和主张无任何来源标注 |

---
