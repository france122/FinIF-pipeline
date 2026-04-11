# Chinese Financial Instruction-Following Benchmark

中文金融领域指令遵循（Instruction Following）评测基准，填补"中文 + 金融 + IF"的交叉空白。

## 项目概况

| 项 | 数量 |
|---|---|
| Query 池 | 502 条（FinEval 113 + FIFE 142 + DISC 152 + WritingBench 95） |
| 约束池 | 60 条（GH 19 + GS 8 + FH 9 + FS 24） |
| Track | 4,611 条（9 种 track type + 100 条 inverse） |
| Train / Test | 452q·4,147t / 50q·464t（query 零重叠） |

## 快速开始

```bash
# 启动评分 review 前端
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/score_review.html
```

## 详细文档

- **`AGENT.md`** — AI agent 导引（目录结构、数据索引、工作规范）
- **`docs/constraint_pool.md`** — 60 条约束池完整文档
- **`docs/constraint_reference_table.csv`** — 约束元数据权威表
- **`../memory/project_overview.md`** — 项目进展与待做事项
