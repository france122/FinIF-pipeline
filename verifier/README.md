# Verifier Framework

本目录用于把约束评测拆成两条线：

- `rules/`: 能确定性判断的约束，尽量用代码规则检查
- `rubrics/`: 规则难以稳定覆盖的约束，改为 LLM-as-a-judge prompt/rubric

设计原则：

1. `docs/constraint_reference_table.csv` 以 `hardness` 和 `check_mode` 为权威字段
2. 当前主线约定：
   - `hard` 约束统一走 `rule`
   - `soft` 约束统一走 `LLM-as-a-judge`
3. `constraint_id` / `module` 中保留的 `GV/GN/FV/FN` 是历史编号，仅用于兼容既有文件命名和引用
4. 当前不再从 `constraint_id` 中的 `V/N` 推导约束性质；约束性质应直接看表中的 `hardness`
5. 评分统一走 `0-10` 框架：
   - `binary_10`
   - `ternary_10`
   - `continuous_10`
6. 规则与 rubric 分开维护，不混在一个大文件里
7. 文件按 `constraint_id` 拆开，后续可单独迭代

目录结构：

```text
verifier/
  base.py
  registry.py
  rule_runner.py
  rubric_runner.py
  rules/
    _shared.py
    GV-1.py
    ...
  rubrics/
    GV-15.md
    ...
```

常用入口：

- `verifier/rule_runner.py`: 运行某个 rule checker
- `verifier/rubric_runner.py`: 构造某个 `LLM-as-a-judge` 约束的 judge prompt
- `scripts/generate_verifier_scaffold.py`: 批量生成 `rules/` 与 `rubrics/` 下的按约束拆分文件
- `docs/verifier_reference_table.md`: 以 Markdown 表格查看当前 verifier 全貌
