# QA Report: Execution, Monitoring, Reporting, and Operations Coverage

Reviewed files:

- `/Users/minimax/Desktop/lunwen/outputs/full_prompts/scaled_shards/execution_monitoring_reporting_operations_full_prompts.jsonl`
- `/Users/minimax/Desktop/lunwen/task_workflow_final.md`
- `/Users/minimax/Desktop/lunwen/constraint_taxonomy_v2.md`

Scope: check whether the shard truly covers the 9 fine-grained task types in the workflow, rather than being mostly template substitution. This report does not modify the data JSONL or specification files.

## 1. Distribution Check

Result: pass for count balance.

The JSONL has 252 items. The 9 task labels each have exactly 28 items:

| Task | Count |
|---|---:|
| Trade / loan / investment execution check | 28 |
| Portfolio monitoring | 28 |
| Post-investment / post-loan review | 28 |
| Risk alert generation | 28 |
| Client review report | 28 |
| Reconciliation | 28 |
| Month-end close / financial reporting support | 28 |
| Board / regulatory reporting | 28 |
| Remediation tracking | 28 |

## 2. Cross-Cutting Findings

### A. Strong within-task template repetition

Every task has exactly one repeated query body across all 28 items. Only the requested work product, account/entity, period, or finding ID changes. Every task also has one repeated extracted-constraint tag sequence across all 28 items.

Examples:

- `Trade / loan / investment execution check`: all 28 ask to compare order ticket, execution confirmation, and funding notes; calculate quantity/price differences; decide complete/exception; cite mismatches; list owners.
- `Portfolio monitoring`: all 28 ask for allocation drift, 5.00 percentage point rebalance trigger, 10.00% issuer concentration, benchmark comparison, and No action/Watch/Escalate.
- `Remediation tracking`: all 28 ask for the same tracker table, same status taxonomy, days past due, steering committee escalation, and closure prohibition.

This is not a fatal issue by itself because the contexts contain different numbers and fact patterns. But it means the shard covers each task as one narrow operational pattern, not the full task variety described in `task_workflow_final.md`.

Actionable fix: for each task, keep about half of the existing pattern if desired, but add 2-4 genuinely different sub-patterns per task. For example, portfolio monitoring should include risk dashboard exposure, benchmark underperformance, concentration-only review, drift/rebalance, and liquidity restriction cases rather than one repeated drift/concentration template.

### B. Context/query alignment is usually adequate, but some work-product labels overstate coverage

Most sampled contexts support the query constraints explicitly. The bigger issue is that some work-product names imply a different operational process than the provided context actually supports.

Most important example:

- `trade_loan_investment_execution_check_execution_02`, `_05`, `_08`, `_11`, `_14`, `_17`, `_20`, `_23`, `_26` are labeled `loan funding execution checklist`, but the context is still a securities order/execution confirmation packet with FINRA/SEA confirmation rules, mark-up disclosure, trade capacity, order ticket, and settlement date. These are not loan closing/funding checklists in substance.

Actionable fix: either rename these to securities/fixed-income trade execution reviews, or rewrite the context to include loan closing checklist, funding memo, wire instruction, conditions precedent, covenant/approval conditions, borrower account, and disbursement authorization.

### C. Constraints are mostly explicit and checkable

The extracted constraints generally satisfy `constraint_taxonomy_v2.md`: they are explicit in query or directly triggered by policy/template text in context, and they are checkable. I did not find a systemic pattern of constraints being invented outside context/query.

Minor caveat: several context-sourced constraints are very stable boilerplate copied from policy documents. They are valid, but their repetition contributes to template feel.

### D. Minor grammar/polish defects

Several generated queries have article errors:

- `trade_loan_investment_execution_check_execution_03`: "Prepare a investment allocation execution review..."
- All `investment allocation execution review` items likely share the same "a investment" issue.
- `remediation_tracking_remediation_14`: "Create a audit finding remediation update..."
- All `audit finding remediation update` items likely share the same "a audit" issue.

Actionable fix: correct article generation for work products beginning with vowel sounds.

## 3. Per-Task QA

### Trade / loan / investment execution check

Quality judgment: needs review.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `trade_loan_investment_execution_check_execution_01` | trade execution exception memo | Fits the task well. Context contains order ticket, confirmation, funding/booking notes, unresolved condition, and desk standard. |
| `trade_loan_investment_execution_check_execution_14` | loan funding execution checklist | Query/context are internally coherent for a securities execution review, but not for a loan funding checklist. Uses securities confirmation, units, mark-up, principal capacity, and settlement fields. |
| `trade_loan_investment_execution_check_execution_28` | trade execution exception memo | Fits the trade execution subtask, but repeats the same structure as item 01. |

Concrete issue IDs:

- Needs substantive rewrite or relabel: `trade_loan_investment_execution_check_execution_02`, `_05`, `_08`, `_11`, `_14`, `_17`, `_20`, `_23`, `_26`.
- Polish issue: `trade_loan_investment_execution_check_execution_03`, `_06`, `_09`, `_12`, `_15`, `_18`, `_21`, `_24`, `_27` use "a investment".

Recommended fix:

- Split this task into three real subtypes: securities trade execution, loan funding/closing execution, and investment allocation implementation.
- For loan items, replace order-ticket/confirmation materials with closing checklist, wire instruction, funding authorization, borrower conditions precedent, collateral/insurance evidence, and unresolved funding blockers.
- For investment allocation items, use allocation notice, portfolio model, sleeve targets, restriction list, and trade implementation record.

### Portfolio monitoring

Quality judgment: pass, with diversity improvement recommended.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `portfolio_monitoring_portfolio_01` | portfolio monitoring report | Good fit. Context supports drift, concentration, benchmark comparison, and restrictions. |
| `portfolio_monitoring_portfolio_14` | drift and concentration review | Good fit. Actual/target allocation, issuer exposure, return, benchmark, and restrictions are present. |
| `portfolio_monitoring_portfolio_28` | portfolio monitoring report | Good fit, but same query/constraint pattern as other items. |

Concrete issue IDs:

- No sampled item fails on context/query mismatch.
- Diversity risk applies to all 28: `portfolio_monitoring_portfolio_01` through `_28`.

Recommended fix:

- Add subtypes beyond allocation drift: liquidity monitoring, VaR/exposure monitoring, sector/issuer concentration-only review, IPS drift with client restriction, benchmark underperformance watch, and rebalance trigger list.

### Post-investment / post-loan review

Quality judgment: needs review.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `post_investment_post_loan_review_postreview_01` | post-loan review memo | Strong fit for loan review. Context has approval case, revenue, DSCR, LTV, missing insurance evidence, and action-item standard. |
| `post_investment_post_loan_review_postreview_14` | post-investment performance review | Internally supported, but it is still a borrower/loan-style post-closing review using DSCR/LTV and insurance upload. It does not meaningfully differ from post-loan review. |
| `post_investment_post_loan_review_postreview_28` | post-loan review memo | Strong fit, but repeats same review pattern. |

Concrete issue IDs:

- Work-product/subtask overreach: `post_investment_post_loan_review_postreview_02`, `_05`, `_08`, `_11`, `_14`, `_17`, `_20`, `_23`, `_26` labeled post-investment performance review but still use loan-style DSCR/LTV/insurance evidence.
- Template risk applies to all 28.

Recommended fix:

- Keep DSCR/LTV for loan review items.
- For investment review items, use investment thesis, actual KPI/performance versus underwriting, valuation change, liquidity/covenant/board update, exit risk, and portfolio company evidence instead of loan-only metrics.

### Risk alert generation

Quality judgment: pass, with diversity improvement recommended.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `risk_alert_generation_riskalert_01` | risk alert notice | Good fit. Context has thresholds and no breaches, making "do not create alert for non-breach" testable. |
| `risk_alert_generation_riskalert_14` | limit breach alert | Good fit. Context has VaR and drawdown breaches, negative outlook, severity procedure, owner/review-date requirements. |
| `risk_alert_generation_riskalert_28` | risk alert notice | Good fit, but repeats same dashboard/procedure pattern. |

Concrete issue IDs:

- No sampled item fails on context/query mismatch.
- Diversity risk applies to all 28: all use the same VaR/drawdown/payment-delay/news-status template.

Recommended fix:

- Add alert types for rating downgrade notices, delinquency reports, market-news-driven issuer alerts, operational exception alerts, limit utilization alerts, and stale-data alerts.
- Include at least some cases where the alert is triggered by non-numeric news/rating evidence, since the workflow definition includes news events and exception reports.

### Client review report

Quality judgment: needs review.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `client_review_report_clientreport_01` | client quarterly review report | Fits client reporting. Context supports performance, fees, holdings, net-of-fee disclosure, prohibited guarantee language, and advisory if discrepancy exists. |
| `client_review_report_clientreport_14` | client account review letter | Mostly fits, but context is structurally identical to item 01 and has the same holdings and same "client asked about certain returns" note. |
| `client_review_report_clientreport_28` | client quarterly review report | Fits the format, but again repeats the same statement structure and holdings. |

Concrete issue IDs:

- Diversity risk applies to all 28.
- The "account-discrepancy advisory if relevant" condition is under-tested because sampled records do not actually include an account discrepancy; the context only contains a general rule excerpt and a note about guaranteed-return language.

Recommended fix:

- Add cases with actual discrepancy/inaccuracy notes so the advisory condition is triggered.
- Vary client types and reporting issues: high concentration, fee change, gross-of-fee performance, tax lot consequences, account activity, dual introducing/carrying firm advisory, and negative performance explanation.

### Reconciliation

Quality judgment: pass.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `reconciliation_recon_01` | reconciliation exception report | Good fit. Context has cash, position, fee records, thresholds, timing item, and no write-off memo. |
| `reconciliation_recon_14` | cash and position break workpaper | Good fit. Position break is present and threshold logic is explicit. |
| `reconciliation_recon_28` | reconciliation exception report | Good fit. Multiple variances are present and retention records are explicit. |

Concrete issue IDs:

- No sampled item fails.
- Template risk applies to all 28 because all items reconcile the same three record types with the same thresholds.

Recommended fix:

- Add more reconciliation types: trade blotter versus settlement report, cash ledger versus bank statement, GL versus subledger, invoice versus fee schedule, journal-entry support, and custodian holdings versus internal positions.

### Month-end close / financial reporting support

Quality judgment: pass, with diversity improvement recommended.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `month_end_close_financial_reporting_support_monthend_01` | month-end close review memo | Good fit. Context supports variance calculations, approval threshold, checklist status, due date, and blocker logic. |
| `month_end_close_financial_reporting_support_monthend_14` | financial reporting support workpaper | Good fit. Missing subledger evidence is present and close-blocker logic is explicit. |
| `month_end_close_financial_reporting_support_monthend_28` | month-end close review memo | Good fit, but same template as item 01. |

Concrete issue IDs:

- No sampled item fails.
- Diversity risk applies to all 28 because every item uses revenue/operating expense variance plus one accrued-revenue adjusting entry.

Recommended fix:

- Add close support cases for journal-entry approval, account reconciliation, flux analysis, disclosure tie-out, management reporting package review, regulatory reporting template support, and unsigned reviewer escalation.

### Board / regulatory reporting

Quality judgment: pass.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `board_regulatory_reporting_boardreg_01` | board and regulatory reporting package | Good fit. Context supports board audience, Form N-PORT timing, exception triggers, missing evidence, and draft-only evidence handling. |
| `board_regulatory_reporting_boardreg_14` | board risk reporting memo | Good fit. Illiquid investment breach is present; other triggers can be evaluated as non-breaches. |
| `board_regulatory_reporting_boardreg_28` | board and regulatory reporting package | Good fit, but same template pattern. |

Concrete issue IDs:

- No sampled item fails.
- Diversity risk applies to all 28.

Recommended fix:

- Add reporting packages for management committee reporting, regulatory readiness without board action, breach-only board memo, missing-evidence escalation, and filing calendar/status update.

### Remediation tracking

Quality judgment: pass, with minor polish issue.

Sampled items:

| Item ID | Work product | QA finding |
|---|---|---|
| `remediation_tracking_remediation_01` | remediation status tracker | Good fit. Context supports finding ID, owner, due date, evidence, validation, closure condition, and escalation logic. |
| `remediation_tracking_remediation_14` | audit finding remediation update | Good fit substantively; article error in query: "Create a audit..." |
| `remediation_tracking_remediation_28` | remediation status tracker | Good fit, but same tracker pattern. |

Concrete issue IDs:

- Polish issue: `remediation_tracking_remediation_02`, `_05`, `_08`, `_11`, `_14`, `_17`, `_20`, `_23`, `_26` use "a audit".
- No sampled item fails on context/query mismatch.

Recommended fix:

- Add more remediation variants: validation testing failed, evidence uploaded but incomplete, extension approved, owner changed, board action overdue, compensating control accepted, and closure package ready for independent review.

## 4. Overall Judgment

Overall shard judgment: needs review.

The shard passes the mechanical distribution requirement and most individual sampled items are coherent. However, it does not yet fully demonstrate coverage of the fine-grained task types. Each task is represented by one narrow template repeated 28 times, often with only entity, date, work product, and numeric values changed. This is especially problematic for:

- `Trade / loan / investment execution check`, where "loan funding execution checklist" items are actually securities trade execution reviews.
- `Post-investment / post-loan review`, where "post-investment performance review" items are still loan-style DSCR/LTV post-closing reviews.
- `Client review report`, where conditional discrepancy advisory coverage is weak and the statement pattern is highly repetitive.

Recommended acceptance condition before final use:

1. Keep the current balanced 9 x 28 distribution.
2. For each task, replace at least 30-50% of items with genuinely distinct subtypes and source materials.
3. Ensure work-product labels match the actual documents and decision logic.
4. Add triggered and non-triggered variants for conditional constraints.
5. Fix article-generation errors in work products beginning with vowel sounds.

