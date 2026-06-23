# QA Report: Risk and Compliance Review scaled shard coverage

Reviewed files:

- `outputs/full_prompts/scaled_shards/risk_compliance_scaled_full_prompts.jsonl`
- `task_workflow_final.md`
- `constraint_taxonomy_v2.md`
- Reference demo: `outputs/full_prompts/risk_compliance_ready_full_prompts_tagged.jsonl`

Scope: assess whether the scaled Risk and Compliance Review shard truly covers the eight fine-grained task types, rather than only expanding templates with noun/number substitutions.

## Executive judgment

The shard passes the mechanical distribution requirement: 224 total items, with 8 tasks x 28 items each.

However, coverage depth is only partially acceptable. The shard does cover the eight task labels and generally keeps context/query/work_product aligned with each task. But within each task, generation is highly templated: normalized query analysis shows only 4 query patterns per task, each repeated 7 times. Most tasks also show only 4 normalized scenario bodies repeated 7 times. The result is closer to "4 scenario templates per task scaled to 28" than to 28 meaningfully distinct task instances.

The scaled shard is not merely a copy of the demo. It adds self-contained synthetic case facts, calculations, thresholds, decision tables, and named case files. But it appears to scale the demo's task archetypes by slot-filling, not by adding broad scenario diversity.

## Distribution check

Task counts:

| Task | Count | Distribution result |
| --- | ---: | --- |
| AML red-flag review | 28 | Pass |
| Covenant check | 28 | Pass |
| Suitability review | 28 | Pass |
| Sales-script / communication compliance | 28 | Pass |
| Stress testing | 28 | Pass |
| Risk disclosure review | 28 | Pass |
| Internal control review | 28 | Pass |
| Regulatory issue escalation | 28 | Pass |

## Repetition and template evidence

Normalized pattern check:

| Task | Unique normalized query patterns | Max repeat per query pattern | Unique normalized main case bodies | Main concern |
| --- | ---: | ---: | ---: | --- |
| AML red-flag review | 4 | 7 | 4 | Good task fit, but repeated alert archetypes. |
| Covenant check | 4 | 7 | 4 | Repeats covenant formula templates by quarter/covenant. |
| Suitability review | 4 | 7 | 4 | Repeats four client/product archetypes; profile fields increment mechanically. |
| Sales-script / communication compliance | 4 | 7 | 4 | Repeats four communication issue archetypes. |
| Stress testing | 4 | 7 | 4 | Repeats two-exposure stress calculation structure. |
| Risk disclosure review | 4 | 7 | 1 for shared source body, 4 draft-risk archetypes | Weakest diversity; nearly all items share same source and same task structure. |
| Internal control review | 4 | 7 | 4 | Repeats four control exceptions with varying amounts/materiality. |
| Regulatory issue escalation | 4 | 7 | 4 | Repeats four FINRA/reportability issue archetypes. |

Constraint pattern check: constraints are mostly explicit and judgeable, but they are also repeated. Across the shard, 1,764 extracted constraints are sourced from query and 231 from context. Each task has near-identical tag sets across all 28 items, e.g. covenant always uses `RC1, EG1, EG2, FP2, QV1, QV4, DB5, EG4, RC4`; stress testing always uses `RC1, EG1, EG5, QV7, QV1, QV4, QV6, FP2, DB3`.

This supports the finding that constraints are explicit, but not highly diverse.

## Demo comparison

The original demo is broader at the archetype level. For example, AML demo items include AML obligation checklist, low-priced securities escalation, FINRA exam readiness, bank BSA/AML examination finding, CVC red-flag memo, and CVC kiosk memo. The scaled AML shard narrows these into four repeated alert patterns: low-priced securities liquidation, CVC kiosk scam pattern, CVC mixer exposure, and foreign correspondent wire activity.

The scaled shard improves over the demo in one important way: it often gives a real case packet with synthetic facts, thresholds, calculations, and required output tables. That makes individual items more testable.

But compared with the demo, the scaled shard loses scenario breadth. It generally turns each demo archetype into a fixed query/workflow template, then cycles firm names, IDs, dates, amounts, product names, and thresholds. This is useful for quantity, but not enough to claim broad scaled coverage.

## Per-task QA

### AML red-flag review: needs review

Sampled: `risk_compliance_scaled_aml_001`, `risk_compliance_scaled_aml_014`, `risk_compliance_scaled_aml_028`.

Task fit: good. The samples ask for SAR/AML escalation outputs, use AML alerts, require red-flag identification, threshold checks, document citations, missing information, and escalation decisions.

Issues:

- The query text is nearly identical across sampled items: "Use only the provided materials...", "Present the review as a table...", "Identify suspicious signals...", "calculate whether reviewed activity aggregates to at least $5,000...".
- Four alert archetypes repeat seven times each. Example repeat group: `risk_compliance_scaled_aml_001`, `_005`, `_009`, `_013`, `_017`, `_021`, `_025` all use the low-priced securities liquidation pattern with mostly amount/date/entity changes.
- Some surface grammar issues remain: `risk_compliance_scaled_aml_014` says "Prepare a AML alert review note".

Actionable feedback: keep the current four archetypes, but replace at least half the repeats with different AML review situations such as structuring/CTR, elderly exploitation, trade-based money laundering, high-risk MSB, PEP/adverse media escalation, sanctions true-hit vs false-positive handling, negative news refresh, or nested correspondent risk.

### Covenant check: needs review

Sampled: `risk_compliance_scaled_covenant_001`, `risk_compliance_scaled_covenant_014`, `risk_compliance_scaled_covenant_028`.

Task fit: good. The samples ask for covenant notes, recalculation, required level comparison, breach/waiver classification, missing support, and next steps before advances.

Issues:

- Four covenant templates repeat: DSCR, total leverage, fixed charge coverage, and minimum liquidity.
- The work product changes, but the deliverable structure is fixed: same table columns, same "Compliant/Breach/Waiver needed" classification, same missing support and next-advance logic.
- Repeat group example: `risk_compliance_scaled_covenant_001`, `_005`, `_009`, `_013`, `_017`, `_021`, `_025` are the same DSCR review pattern.

Actionable feedback: add non-financial covenants and information covenants: late financial statements, insurance certificates, borrowing-base certificates, change of control, permitted debt, collateral reporting, EBITDA add-back disputes, cure rights, waiver already executed vs requested, and cross-default triggers.

### Suitability review: needs review

Sampled: `risk_compliance_scaled_suitability_001`, `risk_compliance_scaled_suitability_014`, `risk_compliance_scaled_suitability_028`.

Task fit: good. The samples use client profiles, product risk facts, concentration calculations, alternatives, and proceed/reject/supervisory approval decisions.

Issues:

- Four profile/product patterns repeat seven times. Example repeat group: `risk_compliance_scaled_suitability_001`, `_005`, `_009`, `_013`, `_017`, `_021`, `_025` repeats the low-risk/capital-preservation profile while mainly increasing age and portfolio value.
- Query is identical except product/client/work_product substitution.
- Missing facts are repeated verbatim across profiles: current debt obligations and emergency cash reserve are not documented.

Actionable feedback: introduce different suitability scenarios: excessive trading/quantitative suitability, rollover recommendation, annuity or structured note replacement, institutional exemption, options approval, margin/leverage, illiquidity mismatch, elderly client concentration, taxable vs IRA conflicts, and self-directed vs recommended transaction boundaries.

### Sales-script / communication compliance: needs review

Sampled: `risk_compliance_scaled_communications_001`, `risk_compliance_scaled_communications_014`, `risk_compliance_scaled_communications_028`.

Task fit: good. The samples ask for communication classification, problematic claim identification, replacement wording, approval/recordkeeping triggers, and approve/edit/reject conclusions.

Issues:

- Four communication archetypes repeat seven times: guaranteed/SEC-approved performance, testimonial/referral/gross returns, chatbot recommendation/safety claim, institutional factsheet/risk-free/no net performance.
- Query is fixed across samples and changes only draft ID/work product/source title.
- Some items blur task label and work product wording: `risk_compliance_scaled_communications_014` is under "Sales-script / communication compliance" but the context is a draft advisor website testimonial, not a sales script. It still fits communication compliance, but the work product name "sales-script compliance review" is less precise.

Actionable feedback: add more communication formats and rule issues: call transcript, text message, podcast/webinar Q&A, private placement deck, social media post, AI chatbot retention, ranking methodology, hypothetical performance audience restrictions, third-party rating substantiation, retail vs institutional forwarding controls, and principal approval vs filing distinction.

### Stress testing: needs review

Sampled: `risk_compliance_scaled_stress_001`, `risk_compliance_scaled_stress_014`, `risk_compliance_scaled_stress_028`.

Task fit: good. The samples require preserving scenario assumptions, applying shock formulas, exposure-level loss, total loss, limit comparison, ranking, and escalation decision.

Issues:

- The task is almost always a two-exposure arithmetic worksheet with a board limit.
- Four exposure category patterns repeat seven times, with amounts/shocks/limits changed.
- It does not cover much of the stress-testing task surface from the workflow: liquidity stress, counterparty exposure, ALM, deposits, market shock, multi-scenario comparison, model validation questions, sensitivity table interpretation, or data-quality caveats.

Actionable feedback: diversify beyond single-scenario loss math. Add multi-scenario comparison, liquidity runway, deposit outflow, collateral haircut, counterparty default, VaR/sensitivity reconciliation, failed limit with management action plan, and cases where source scenario assumptions conflict with internal methodology.

### Risk disclosure review: fail

Sampled: `risk_compliance_scaled_risk_disclosure_001`, `risk_compliance_scaled_risk_disclosure_014`, `risk_compliance_scaled_risk_disclosure_028`.

Task fit: basic fit is present: each asks for Item 105/plain-English risk disclosure review, generic-risk identification, summary-trigger check, and rewrite.

Reason for fail: this task has the weakest actual scenario diversity. All 28 items share the same source pattern and nearly the same query. The draft risk under review rotates among four short risk sentences and business updates, while section length increments. This is too close to template scaling.

Specific repeat evidence:

- `risk_compliance_scaled_risk_disclosure_001` to `_008` show the same DOC1 Item 105 source, same DOC2 Plain English Handbook source, same DOC3 structure, same comment table, same generic-risk issue, same rewrite requirement.
- The only meaningful variations are issuer letter, draft section length, four risk topics, and work product label.
- Grammar issue: `risk_compliance_scaled_risk_disclosure_003` and `_007` say "Prepare a Item 105 disclosure review memo".

Actionable feedback: replace at least 14 of 28 items with materially different disclosure review scenarios: MD&A risk cross-reference, cybersecurity incident risk update, climate/legal proceeding risk, offering-specific dilution risk, fund prospectus principal risks, risk factor ordering/summary-only issue, overbroad safe-harbor language, missing risk from known trend, conflict-of-interest disclosure, and inconsistent risk disclosure versus business section.

### Internal control review: needs review

Sampled: `risk_compliance_scaled_internal_control_001`, `risk_compliance_scaled_internal_control_014`, `risk_compliance_scaled_internal_control_028`.

Task fit: good. The samples ask for ICFR deficiency memos, observed fact vs judgment separation, likelihood/magnitude, deficiency classification, materiality comparison, compensating controls, and remediation.

Issues:

- Four control exceptions repeat seven times: journal entry approval, user access, reconciliation review, and model change control.
- The same compensating-control caveat repeats broadly: quarterly controller review evidence missing.
- The query is identical except issue ID/work product.

Actionable feedback: add control review cases covering segregation of duties outside journal entries, cash disbursement approval, valuation model governance, loan review override, stale user access with privileged roles, SOC report gaps, spreadsheet control, management review precision, automated control failure, and evidence sufficiency disagreements.

### Regulatory issue escalation: needs review

Sampled: `risk_compliance_scaled_escalation_001`, `risk_compliance_scaled_escalation_014`, `risk_compliance_scaled_escalation_028`.

Task fit: good. The samples require reportability decision, deadline, owner, missing facts, preliminary-facts caveat, and escalation to Compliance Reporting.

Issues:

- Four issue types repeat seven times: written customer complaints, associated person violation conclusion, systemic supervision failure, and disciplinary threshold.
- Query structure is fixed across all samples.
- Some work product grammar issues remain: `risk_compliance_scaled_escalation_028` says "Prepare a issue escalation workpaper".

Actionable feedback: add escalation scenarios beyond FINRA 4530-style reportability: regulatory exam finding escalation, late remediation, AML/sanctions escalation, privacy breach, trading halt/market manipulation alert, unauthorized discretion, branch inspection issue, books-and-records failure, customer harm threshold, legal hold, and board/regulator notification distinction.

## Constraint quality

Overall, extracted constraints are explicit and checkable. Common constraints such as "use only provided materials", "cite document IDs", exact table columns, threshold calculations, classification choices, and non-overstatement caveats are good benchmark constraints.

Main constraint issue: constraints are too uniform. Since each task repeats the same tag set across all 28 items, the shard tests the same instruction-following behaviors repeatedly. This reduces benchmark value even when each individual item is valid.

Potential context/query mismatch issues are limited. Most sampled items align with their task. The main mismatch is not semantic contradiction, but overly broad or imprecise work product naming, especially communication items where "sales-script" is used for website/factsheet materials.

## Overall QA result

Overall result: needs review.

The shard should not be rejected as wholly invalid: it has correct task distribution, task-aligned work products, usable case packets, and explicit constraints. But it should not be accepted as strong scaled coverage without revision. The current shard mostly covers 4 scenario templates per task, repeated 7 times each.

Minimum remediation before acceptance:

1. For each task, replace at least 10-14 of the 28 items with new scenario archetypes rather than numeric/name variants.
2. Reduce identical query skeletons; vary deliverable structures where realistic.
3. Add task-specific edge cases and negative cases, not only threshold calculations.
4. Fix article/grammar issues in generated queries: "a AML", "a Item 105", "a issue".
5. For Risk disclosure review, perform the most substantial rewrite; it currently fails scenario-diversity expectations.

