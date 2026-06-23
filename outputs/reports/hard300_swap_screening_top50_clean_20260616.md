# Hard300 Swap Screening Top50 Clean (2026-06-16)

这版只保留两个最终集合，不做配对：
- `50 in`: 从 train764 里挑出的更适合换入 benchmark 的 clean 候选
- `50 out`: 从当前 hard300 里挑出的 GPT-5 exact-pass clean 候选

## Clean 过滤规则
- `swap-in` 剔除：纯 `EG2` 失败、明显 `FP2/FP3` 规则污染、已知 prompt tension 边缘样本、低质量项。
- `swap-out` 剔除：带 `DB8 / QV4 / RC4 / DB1 / DB2 / QV6 / EG3 / DB7 / QV5` 等长尾锚点的 exact-pass 样本。

## 结果摘要
- `swap-in clean 50` workflow：`{'Decision and Structuring': 11, 'Execution, Monitoring, Reporting, and Operations': 7, 'Intake and Profiling': 7, 'Risk and Compliance Review': 9, 'Research and Due Diligence': 4}`
- `swap-in clean 50` priority tags：`{'DB7': 18, 'DB9': 18, 'QV2': 14, 'QV5': 8, 'QV6': 1}`
- `swap-out clean 50` workflow：`{'Intake and Profiling': 8, 'Research and Due Diligence': 7, 'Execution, Monitoring, Reporting, and Operations': 10, 'Risk and Compliance Review': 7, 'Decision and Structuring': 6}`
- `swap-out clean 50` semantic tags：`{'DB9': 38, 'EG2': 38, 'QV2': 38, 'EG1': 29, 'DB4': 25, 'EG5': 22, 'DB6': 16, 'FP1': 2, 'QV7': 2, 'DB5': 2}`

## Top 15 Swap-In Clean
| ID | Workflow | Task | Quality | Micro | Failed Tags | Priority Tags |
| --- | --- | --- | ---: | ---: | --- | --- |
| decision_structuring_trade_order_ticket_preparation_027 | Decision and Structuring | Trade order ticket preparation | 3 | 0.600 | DB7, DB9, EG2, QV2 | DB7, DB9, QV2 |
| decision_structuring_capital_structure_financing_proposal_004 | Decision and Structuring | Capital structure / financing proposal | 3 | 0.556 | DB7, DB9, EG2, QV2 | DB7, DB9, QV2 |
| execution_month_end_close_financial_reporting_support_repaired_28 | Execution, Monitoring, Reporting, and Operations | Month-end close / financial reporting support | 3 | 0.800 | DB7, DB9 | DB7, DB9 |
| intake_service_scope_repaired_017 | Intake and Profiling | Service scope explanation | 3 | 0.800 | DB7, DB9 | DB7, DB9 |
| execution_risk_alert_generation_repaired_023 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | 4 | 0.818 | QV2, QV5 | QV2, QV5 |
| intake_missing_information_checklist_repaired_012 | Intake and Profiling | Missing information checklist | 3 | 0.727 | DB7, DB9, EG2 | DB7, DB9 |
| risk_sales_script_communication_compliance_repaired_026 | Risk and Compliance Review | Sales-script / communication compliance | 3 | 0.727 | DB7, DB9, EG2 | DB7, DB9 |
| intake_client_risk_profiling_repaired_008 | Intake and Profiling | Client risk profiling | 3 | 0.692 | DB7, DB9, EG2 | DB7, DB9 |
| risk_aml_red_flag_review_repaired_010 | Risk and Compliance Review | AML red-flag review | 3 | 0.667 | DB7, DB9, EG2 | DB7, DB9 |
| risk_compliance_internal_control_review_repaired_009 | Risk and Compliance Review | Internal control review | 3 | 0.636 | DB7, DB9, EG2 | DB7, DB9 |
| execution_board_regulatory_reporting_repaired_026 | Execution, Monitoring, Reporting, and Operations | Board / regulatory reporting | 3 | 0.625 | DB7, DB9, EG2 | DB7, DB9 |
| risk_aml_red_flag_review_repaired_009 | Risk and Compliance Review | AML red-flag review | 3 | 0.625 | DB7, DB9, EG2 | DB7, DB9 |
| decision_structuring_portfolio_proposal_023 | Decision and Structuring | Portfolio proposal | 3 | 0.727 | DB9, EG2, QV2 | DB9, QV2 |
| decision_underwriting_memo_repaired_007 | Decision and Structuring | Underwriting memo | 3 | 0.727 | DB9, EG2, QV2 | DB9, QV2 |
| decision_structuring_capital_structure_financing_proposal_010 | Decision and Structuring | Capital structure / financing proposal | 3 | 0.700 | DB9, EG2, QV2 | DB9, QV2 |

## Top 15 Swap-Out Clean
| Benchmark ID | Workflow | Task | Semantic Tags | Task Pass Count |
| --- | --- | --- | --- | ---: |
| tonight_hard_line_150 | Intake and Profiling | Counterparty / issuer profile construction | DB4, DB6, DB9, EG1, EG2, EG5, QV2 | 6 |
| tonight_hard_line_087 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | 6 |
| tonight_hard_line_330 | Intake and Profiling | Loan application intake | DB4, DB9, EG1, EG2, EG5, QV2 | 6 |
| tonight_hard_line_017 | Intake and Profiling | Counterparty / issuer profile construction | DB4, DB6, DB9, EG1, EG2, QV2 | 6 |
| tonight_hard_line_083 | Research and Due Diligence | Background screening | DB6, DB9, EG1, EG2, EG5, QV2 | 6 |
| tonight_hard_line_092 | Intake and Profiling | Missing information checklist | DB4, DB6, DB9, EG1, EG2, EG5, QV2 | 4 |
| tonight_hard_line_088 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 5 |
| tonight_hard_line_206 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 5 |
| tonight_hard_line_262 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 5 |
| tonight_hard_line_358 | Execution, Monitoring, Reporting, and Operations | Post-investment / post-loan review | DB4, DB9, EG1, EG2, EG5, QV2 | 5 |
| tonight_hard_line_146 | Research and Due Diligence | Industry and market research | DB6, DB9, EG1, EG2, EG5, QV2 | 5 |
| tonight_hard_line_072 | Risk and Compliance Review | Internal control review | DB4, DB9, EG1, EG2, EG5, FP1, QV2 | 5 |
| tonight_hard_line_357 | Execution, Monitoring, Reporting, and Operations | Risk alert generation | DB4, DB9, EG1, EG2, QV2 | 6 |
| tonight_hard_line_110 | Decision and Structuring | Portfolio proposal | DB4, DB9, EG1, EG2, EG5, QV2 | 4 |
| tonight_hard_line_175 | Decision and Structuring | Portfolio proposal | DB4, DB9, EG1, EG2, EG5, QV2 | 4 |

## 文件
- `outputs/reports/hard300_swap_in_candidates_train764_top50_clean_20260616.csv`
- `outputs/reports/hard300_swap_out_candidates_exactpass_top50_clean_20260616.csv`