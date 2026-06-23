# Hard300 Swap Screening Top50 (2026-06-16)

## 目标
- 做一版约 50 条规模的 swap screening。
- `swap-in` 优先补非 `EG2` 主导、但能拉高 benchmark 张力的标签。
- `swap-out` 仅从当前 hard300 中 `GPT-5 exact pass` 的安全样本里取。

## 方法
1. 用 `train764` 完整 judge 结果筛 `GPT-5` failed items。
2. 优先标签：`DB7 / DB9 / QV2 / QV5 / QV6 / EG3 / DB4 / EG5`。
3. `swap-in` 两阶段筛选：先取更强的 non-EG2 / 高质量失败，再放宽到 50 条。
4. `swap-out` 用 GPT-5 历史正式跑分的 `selected_dataset` 与当前 hard300 通过 `full_prompt` hash 精确对齐，只保留 exact-pass 子集。
5. `swap-out` 优先选语义标签更通用、稀缺标签更少、同任务中 exact-pass 更充足的样本。

## 结果概览
- `swap-in` 候选数：`50`
- `swap-out` 候选数：`50`
- `swap-in` 标签覆盖：`{'DB9': 29, 'DB7': 28, 'QV2': 19, 'QV5': 10, 'QV6': 2, 'DB4': 1}`
- `swap-in` workflow 分布：`{'Execution, Monitoring, Reporting, and Operations': 10, 'Intake and Profiling': 12, 'Risk and Compliance Review': 10, 'Decision and Structuring': 13, 'Research and Due Diligence': 5}`
- `swap-out` workflow 分布：`{'Intake and Profiling': 12, 'Research and Due Diligence': 10, 'Execution, Monitoring, Reporting, and Operations': 12, 'Risk and Compliance Review': 7, 'Decision and Structuring': 9}`

## Top 15 Swap-In
| ID | Workflow | Task | Quality | Micro | Failed Tags | Priority Tags |
| --- | --- | --- | ---: | ---: | --- | --- |
| execution_month_end_close_financial_reporting_support_repaired_28 | Execution, Monitoring, Reporting, and Operations | Month-end close / financial reporting support | 3 | 0.800 | DB7, DB9 | DB7, DB9 |
| intake_service_scope_repaired_017 | Intake and Profiling | Service scope explanation | 3 | 0.800 | DB7, DB9 | DB7, DB9 |
| intake_counterparty_issuer_profile_construction_repaired_021 | Intake and Profiling | Counterparty / issuer profile construction | 3 | 0.667 | DB7, DB9, FP3 | DB7, DB9 |
| execution_risk_alert_generation_repaired_023 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | 4 | 0.818 | QV2, QV5 | QV2, QV5 |
| intake_service_scope_repaired_014 | Intake and Profiling | Service scope explanation | 6 | 0.917 | QV2 | QV2 |
| intake_counterparty_issuer_profile_construction_repaired_019 | Intake and Profiling | Counterparty / issuer profile construction | 6 | 0.909 | DB9 | DB9 |
| risk_suitability_review_repaired_018 | Risk and Compliance Review | Suitability review | 3 | 0.909 | DB7 | DB7 |
| decision_structuring_capital_structure_financing_proposal_018 | Decision and Structuring | Capital structure / financing proposal | 3 | 0.900 | DB7 | DB7 |
| decision_structuring_loan_approval_package_repaired_017 | Decision and Structuring | Loan approval package | 3 | 0.889 | DB7 | DB7 |
| research_background_screening_repaired_019 | Research and Due Diligence | Background screening | 3 | 0.889 | DB7 | DB7 |
| risk_compliance_internal_control_review_repaired_023 | Risk and Compliance Review | Internal control review | 3 | 0.889 | DB7 | DB7 |
| decision_structuring_trade_order_ticket_preparation_009 | Decision and Structuring | Trade order ticket preparation | 3 | 0.875 | DB7 | DB7 |
| decision_structuring_investment_memo_020 | Decision and Structuring | Investment memo | 6 | 0.900 | QV5 | QV5 |
| execution_reconciliation_repaired_016 | Execution, Monitoring, Reporting, and Operations | Reconciliation | 6 | 0.900 | QV5 | QV5 |
| risk_disclosure_review_repaired_012 | Risk and Compliance Review | Risk disclosure review | 4 | 0.900 | QV2 | QV2 |

## Top 15 Swap-Out
| Benchmark ID | Workflow | Task | Semantic Tags | Keep Hits | Generic Hits |
| --- | --- | --- | --- | ---: | ---: |
| tonight_hard_line_150 | Intake and Profiling | Counterparty / issuer profile construction | DB4, DB6, DB9, EG1, EG2, EG5, QV2 | 0 | 7 |
| tonight_hard_line_087 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_330 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_017 | Intake and Profiling | Counterparty / issuer profile construction | DB4, DB6, DB9, EG1, EG2, QV2 | 0 | 6 |
| tonight_hard_line_083 | Research and Due Diligence | Background screening | DB6, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_092 | Intake and Profiling | Missing information checklist | DB4, DB6, DB9, EG1, EG2, EG5, QV2 | 0 | 7 |
| tonight_hard_line_101 | Intake and Profiling | Counterparty / issuer profile construction | DB4, DB8, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_104 | Research and Due Diligence | Background screening | DB2, DB6, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_088 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_206 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_262 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_358 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_146 | Research and Due Diligence | Industry and market research | DB6, DB9, EG1, EG2, EG5, QV2 | 0 | 6 |
| tonight_hard_line_072 | Risk and Compliance Review | Internal control review | DB4, DB9, EG1, EG2, EG5, FP1, QV2 | 0 | 6 |
| tonight_hard_line_357 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | DB4, DB9, EG1, EG2, QV2 | 0 | 5 |

## 明细文件
- `outputs/reports/hard300_swap_in_candidates_train764_top50_20260616.csv`
- `outputs/reports/hard300_swap_out_candidates_exactpass_top50_20260616.csv`