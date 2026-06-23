# FinIF v2 Task Repair Status

Date: 2026-06-11

This file tracks task-level repair progress. Use it to avoid assigning the same task type twice.

## Status Legend

- `MERGED_REPAIRED`: repaired shard has already been merged into `outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl`.
- `REPAIRED_SHARD_READY`: repaired shard exists, but it has not yet been merged into the repaired final dataset.
- `IN_PROGRESS`: a worker agent is currently repairing this task; do not reassign it.
- `NOT_REPAIRED`: no repaired shard is currently recorded.

Current count:

- `MERGED_REPAIRED`: 38 task types
- `REPAIRED_SHARD_READY`: 0 task types
- `IN_PROGRESS`: 0 task types
- `NOT_REPAIRED`: 0 task types
- Total: 38 task types

## Active Quality Rule

Repair should prioritize query diversity.

- Target at least 16 unique normalized query skeletons per task.
- Max normalized query skeleton repeat should be no more than 3.
- Do not only paraphrase one query template.
- If query intent changes, context, full_prompt, and extracted_constraints must change too.
- Scenario archetypes are optional scaffolding, not the evaluation target.

## Intake and Profiling

| Task | Status | Repaired shard |
| --- | --- | --- |
| KYC onboarding | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_kyc_onboarding_repaired.jsonl` |
| Client risk profiling | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_client_risk_profiling_repaired.jsonl` |
| Loan application intake | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_loan_application_intake_repaired.jsonl` |
| Counterparty / issuer profile construction | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_counterparty_issuer_profile_construction_repaired.jsonl` |
| Missing information checklist | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_missing_information_checklist_repaired.jsonl` |
| Service scope explanation | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/intake_service_scope_explanation_repaired.jsonl` |

## Research and Due Diligence

| Task | Status | Repaired shard |
| --- | --- | --- |
| Financial statement analysis | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_financial_statement_analysis_repaired.jsonl` |
| Industry and market research | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_industry_market_research_repaired.jsonl` |
| Earnings review | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_earnings_review_repaired.jsonl` |
| Credit due diligence | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_credit_due_diligence_repaired.jsonl` |
| Investment due diligence | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_investment_due_diligence_repaired.jsonl` |
| Background screening | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_background_screening_repaired.jsonl` |
| Due diligence checklist completion | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/research_due_diligence_checklist_completion_repaired.jsonl` |

## Decision and Structuring

| Task | Status | Repaired shard |
| --- | --- | --- |
| Credit memo drafting | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_credit_memo_drafting_repaired.jsonl` |
| Underwriting memo | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_underwriting_memo_repaired.jsonl` |
| Loan approval package | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_loan_approval_package_repaired.jsonl` |
| DCF valuation / pricing analysis | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_dcf_pricing_repaired.jsonl` |
| Investment memo | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_investment_memo_repaired.jsonl` |
| Capital structure / financing proposal | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_capital_structure_financing_proposal_repaired.jsonl` |
| Portfolio proposal | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_portfolio_proposal_repaired.jsonl` |
| Trade order ticket preparation | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/decision_trade_order_ticket_preparation_repaired.jsonl` |

## Risk and Compliance Review

| Task | Status | Repaired shard |
| --- | --- | --- |
| AML red-flag review | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_aml_red_flag_review_repaired.jsonl` |
| Covenant check | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_covenant_check_repaired.jsonl` |
| Suitability review | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_suitability_review_repaired.jsonl` |
| Sales-script / communication compliance | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_sales_script_communication_compliance_repaired.jsonl` |
| Stress testing | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_stress_testing_repaired.jsonl` |
| Risk disclosure review | `MERGED_REPAIRED` | `outputs/full_prompts/repair_shards/risk_disclosure_review_repaired.jsonl` |
| Internal control review | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_internal_control_review_repaired.jsonl` |
| Regulatory issue escalation | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/risk_regulatory_issue_escalation_repaired.jsonl` |

## Execution, Monitoring, Reporting, and Operations

| Task | Status | Repaired shard |
| --- | --- | --- |
| Trade / loan / investment execution check | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_trade_loan_investment_execution_check_repaired.jsonl` |
| Portfolio monitoring | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_portfolio_monitoring_repaired.jsonl` |
| Post-investment / post-loan review | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_post_investment_post_loan_review_repaired.jsonl` |
| Risk alert generation | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_risk_alert_generation_repaired.jsonl` |
| Client review report | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_client_review_report_repaired.jsonl` |
| Reconciliation | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_reconciliation_repaired.jsonl` |
| Month-end close / financial reporting support | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_month_end_close_financial_reporting_support_repaired.jsonl` |
| Board / regulatory reporting | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_board_regulatory_reporting_repaired.jsonl` |
| Remediation tracking | `MERGED_REPAIRED` | `outputs/full_prompts/task_repair_shards/execution_remediation_tracking_repaired.jsonl` |

## Suggested Next Assignments

Highest-priority unassigned repairs:

```text
None currently. All task types are either merged, ready for integration, or in progress.
```

## Current Repaired Dataset

```text
outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl
outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts_summary.json
```

Current merged status:

- Total items: 1064
- Total constraints: 7851
- Merged repaired task types: 38
- Ready but unmerged repaired task types: 0
- In-progress task types: 0
- Not repaired task types: 0
- Pending ready shards: 0

## Pending Integration

The following `REPAIRED_SHARD_READY` task shards still need to be QA-checked by the main thread and merged into the next repaired final dataset:

```text
None currently.
```
