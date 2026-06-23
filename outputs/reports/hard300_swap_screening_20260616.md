# Hard300 Swap Screening (2026-06-16)

筛选原则：
- `swap-in` 来自 `train764`，优先补非 `EG2` 主导的高张力失败标签。
- `swap-out` 只来自当前 hard300 中可安全映射到现行 benchmark 的 `GPT-5 exact-pass` 样本。
- `swap-in` 以标签多样性优先，task/workflow 只做软分散。
- `swap-out` 优先移出标签结构更通用、稀缺语义标签更少的 exact-pass 样本。

## 核心观察
- `train764` 最终 `GPT-5` strict exact-pass rate 为 `53.14%`，高于当前 hard300 上的 `47.33%`。
- 训练池失败项里，非 `EG2` 失败标签主要集中在 `FP3 135 / DB7 46 / DB9 39 / QV2 37 / QV5 21`。
- 为避免 benchmark 继续被 `EG2` 单标签主导，本轮 `swap-in` 优先覆盖 `DB7 / DB9 / QV2 / QV5 / QV6`。
- 可安全用于 `swap-out` 的当前 benchmark exact-pass 子集共有 `124` 条；它们是通过旧 GPT-5 正式跑分样本与当前 benchmark `full_prompt` 精确对齐得到的保守安全池。

## Swap-In 候选统计（本轮选出 24 条）
- workflow 分布：`{'Risk and Compliance Review': 3, 'Decision and Structuring': 3, 'Intake and Profiling': 3, 'Execution, Monitoring, Reporting, and Operations': 2}`
- target tag 覆盖：`{'QV2': 7, 'DB7': 6, 'DB9': 6, 'QV5': 4, 'QV6': 2, 'DB4': 1, 'EG5': 1}`

| ID | Workflow | Task | Quality | Micro | Failed Tags | Why Keep |
| --- | --- | --- | ---: | ---: | --- | --- |
| risk_suitability_review_repaired_005 | Risk and Compliance Review | Suitability review | 2 | 0.500 | DB7, DB9, EG2, QV2, QV6 | DB7/DB9/QV2/QV6 |
| decision_structuring_trade_order_ticket_preparation_027 | Decision and Structuring | Trade order ticket preparation | 3 | 0.600 | DB7, DB9, EG2, QV2 | DB7/DB9/QV2 |
| decision_structuring_capital_structure_financing_proposal_004 | Decision and Structuring | Capital structure / financing proposal | 3 | 0.556 | DB7, DB9, EG2, QV2 | DB7/DB9/QV2 |
| decision_structuring_capital_structure_financing_proposal_025 | Decision and Structuring | Capital structure / financing proposal | 3 | 0.500 | DB7, DB9, EG2, FP3, QV2 | DB7/DB9/QV2 |
| intake_kyc_onboarding_repaired_022 | Intake and Profiling | KYC onboarding | 2 | 0.444 | DB7, DB9, EG2, QV5 | DB7/DB9/QV5 |
| execution_risk_alert_generation_repaired_023 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | 4 | 0.818 | QV2, QV5 | non-EG2, QV2/QV5 |
| execution_board_regulatory_reporting_repaired_014 | Execution, Monitoring, Reporting, and Operations | Board / regulatory reporting | 3 | 0.667 | EG2, QV2, QV5 | QV2/QV5 |
| risk_disclosure_review_repaired_020 | Risk and Compliance Review | Risk disclosure review | 3 | 0.600 | EG2, FP3, QV2, QV5 | QV2/QV5 |
| intake_missing_information_checklist_repaired_027 | Intake and Profiling | Missing information checklist | 3 | 0.750 | DB4, DB7, EG2 | DB4/DB7 |
| intake_client_risk_profiling_repaired_002 | Intake and Profiling | Client risk profiling | 3 | 0.727 | DB9, EG2, QV6 | DB9/QV6 |
| risk_compliance_internal_control_review_repaired_020 | Risk and Compliance Review | Internal control review | 3 | 0.700 | EG2, EG5, FP3 | EG5 |

完整明细：`outputs/reports/hard300_swap_in_candidates_train764_20260616.csv`

## Swap-Out 候选统计（本轮选出 24 条）
- workflow 分布：`{'Research and Due Diligence': 5, 'Execution, Monitoring, Reporting, and Operations': 5, 'Risk and Compliance Review': 5, 'Decision and Structuring': 4, 'Intake and Profiling': 5}`
- 这些候选均来自 `GPT-5 exact-pass` 且已与当前 benchmark `full_prompt` 精确对齐。

| Benchmark ID | Workflow | Task | Semantic Tags | Why Swap Out First |
| --- | --- | --- | --- | --- |
| tonight_hard_line_080 | Research and Due Diligence | Due diligence checklist completion | DB9, EG2, QV2 | no scarce keep-tags |
| tonight_hard_line_302 | Research and Due Diligence | Credit due diligence | DB9, EG1, EG2, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_357 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | DB4, DB9, EG1, EG2, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_312 | Risk and Compliance Review | Internal control review | DB9, EG1, EG2, EG5, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_347 | Decision and Structuring | Underwriting memo | DB9, EG1, EG2, EG5, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_059 | Execution, Monitoring, Reporting, and Operations | Board / regulatory reporting | DB6, DB9, EG2, QV2 | no scarce keep-tags, generic tag profile |
| tonight_hard_line_242 | Risk and Compliance Review | Covenant check | DB6, DB9, EG2, QV2 | no scarce keep-tags, generic tag profile |
| tonight_hard_line_053 | Intake and Profiling | Client risk profiling | DB6, DB9, EG2, QV2 | no scarce keep-tags, generic tag profile |
| tonight_hard_line_106 | Decision and Structuring | Trade order ticket preparation | DB6, DB9, EG1, EG2, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_087 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_330 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |
| tonight_hard_line_088 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | no scarce keep-tags, task has many exact-pass items, generic tag profile |

完整明细：`outputs/reports/hard300_swap_out_candidates_exactpass_20260616.csv`

## 备注
- 这是一版筛选结果，不是最终一对一 swap 名单。
- 更稳的下一步是先从这 24 条里再压成 `12-20` 条小批次，再做同数目 exact-pass 回填。