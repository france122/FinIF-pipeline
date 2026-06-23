# Tonight Benchmark 约束重生设计方案

状态：待审定。审定后再生成，不先改数据。

## 1. 诊断（为什么要做）

`outputs/benchmark/finif_v2_tonight_hard300.jsonl`，4043 条约束：

- **2243 条 query 派生**：其中 2083 条（RC/QV/DB/EG）是**把 query 的提问改写成「output must be ...」**，不是 output constraint，是任务复述。它们占了全部 judge 约束的 66%，且无法 rule-check（因为本就不是约束）。
- **1800 条硬化包**：900 条 FP 格式类（已 rule 化，真约束）+ 900 条 DB1/EG2/QV2 三句模板（每个 item 都挂同样三句）。
- **后果**：去重后 distinct 约束文本仅 ~160 条；300 个 item 的 IF 约束几乎雷同，全是「加粗标题 + Next action: + 三句英文套话」，**金融特定约束几乎为零**。这对一个金融 IF benchmark 是致命的。

根因：tonight 这套约束是临时拼的，**完全没接 `current/benchmark/constraint_taxonomy.json` 里成熟的金融约束体系**（26 hard checker + 18 soft，双轴 compliance/correctness）。

## 2. 目标

用 `current/` 的金融约束体系，给 tonight 300 个 item 重新配约束：
- 金融特定（货币格式、风险声明、监管视角、投资建议禁令、术语全称…）
- 300 item 多样化（不再雷同）
- rule/judge 比例健康（结构/格式/correctness 走 rule，语义视角走 judge）
- correctness 轴用 `expected + tolerance` 程序验证落地，不是印象分

## 3. 可复用的现成资产

| 资产 | 路径 | 用途 |
|---|---|---|
| 金融约束 taxonomy | `current/benchmark/constraint_taxonomy.json` | 26 hard + 18 soft，双轴定义、slot 采样规则、exclusion/mixing rules |
| slot 采样产物样例 | `current/sft_data/constraint_gen_output_v3.jsonl` | 4-slot 采样 + hidden correctness checker 的实际格式 |
| 已实现 checker | `evaluation/checkers.py` | 50 个 check_ 函数 |

每个 tonight item 自带语境：`workflow / task / work_product / posture / source_registry`（真实金融文档+数字）。

## 4. 约束生成设计（每 item 4-6 条）

沿用 `current/` 的 4-slot + correctness：

| Slot | 类型 | 选 | checker 来源 | 金融化点 |
|---|---|---|---|---|
| 1 长度 | hard | 1 | check_word_range / check_max_words / check_paragraph_count | 按 task 难度档 T1/T2/T3 定字数区间 |
| 2 结构 | hard | 1 | heading_level / table_columns / ordered_list / blockquote | 复用现有 FP 变体 |
| 3 金融格式/语言 | hard | 1 | **L1 风险声明 / L2 禁第一人称·禁口语 / L4 货币单位·百分号 / N3 小数精度** | 真·金融特定，当前一条没用 |
| 4 金融语义视角 | soft(judge) | 1 | **S 系列**：posture→视角映射（见 §5） | 真·金融特定 judge 约束 |
| 5 correctness | hard | 0-2 | **C6**：从 source_registry 数字算 expected+tolerance | 仅当 task 含计算时挂 |

保留：每 item 仍保留 1-2 条 FP 格式锚点（首行加粗 + Next action:），因为它们是干净的真约束。

## 5. posture → 金融语义视角映射（slot 4，judge）

利用 item 已有的 8 种 posture，避免 300 item 雷同：

| posture | 配的 soft 约束（current/ 模板） |
|---|---|
| Compliance escalation | S-14 监管视角 + S-04 不含投资建议 |
| Credit committee | S-08 机构读者 + S-13 风险管理视角 |
| Controller review | S-10 谨慎措辞 + L1 风险声明 |
| Reconciliation | S-03 正式书面语 + N3 小数精度 |
| Disclosure-review | S-04 不含投资建议 + S-12 缩写给全称 |
| Diligence challenge | S-13 风险视角 + C2 证据深度 |
| Operations handoff | S-09 分析师口吻 + C1 覆盖度 |
| Adversarial audit | S-10 谨慎 + S-14 监管视角 |

（具体配比审定时可调；exclusion_rules 防冲突，如 S-12↔S-17。）

## 6. correctness 轴（C6）—— 关键且最难

正确做法（参照 `current/` 的 hidden_checkers）：
```json
{"checker":"check_computation_result",
 "params":{"results":[{"label":"调整后现金差异","expected":100.00,"tolerance":0.5}]}}
```
- expected 由**建表脚本从 source_registry 数字按约束语义算出**（如银行−内部−在途）。
- **风险红线**：算错的 expected 比 judge 更糟（冤枉对的答案）。因此 correctness 这部分**必须人工抽检**，且只对「数字明确、算法单一」的 item 上（reconciliation / covenant / margin / DCF 等），其余 item 不挂 C6、correctness 留给 quality_score。

## 7. ⚠️ 工程缺口（必须先补，否则方案落不了地）

`current/` taxonomy 引用的金融 checker，**evaluation/checkers.py 里大多没实现，且命名不一致**：
- 缺失约 37 个，含全部 C6 correctness（check_computation_result / check_value_exact / check_risk_grade / check_judgment …）
- 命名不一致：current 叫 `check_value_exact`，eval 里叫 `exact_value`；current `check_table_column_names` ↔ eval `table_columns`
- L2 金融语言类（check_first_person / check_no_arabic_numerals）eval 里**已有**，可直接用；L4（no_percent / currency_format）**已有**。

**落地前置任务**：
1. 建一张 current→eval 的 checker 名称映射表
2. 补实现缺失的金融 checker（重点：check_computation_result、check_field_coverage、check_value_exact 别名）
3. 校验所有新约束的 checker 都能返回二元分（否则 evaluate_responses.py 会 raise）

## 8. 建议执行顺序

1. **审定本方案**（slot 配比、posture 映射、correctness 范围）
2. 补 §7 的 checker 缺口 + 映射表
3. **10 item 试点**：生成新约束 → 跑 checker_probe → 人工核对 correctness expected → 看金融相关性/多样性
4. 试点 OK → 铺到 300，重跑 routing_audit + 一次 smoke 评测
5. 更新 MEMORY 与 summary

## 9. 已顺手修复（与本方案独立）

`evaluation/checkers.py` `check_table_columns`：加粗/代码表头（`**Evidence**`、`` `Evidence` ``）此前被判列缺失（误杀 58 个 table_columns item）。已加 `strip_inline_markup` 修复并回归验证。
