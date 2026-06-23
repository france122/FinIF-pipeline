# FinIF Constraint Taxonomy

## Purpose

This taxonomy defines the constraint types used in the FinIF benchmark for evaluating instruction following in financial workflows.

A constraint is an explicit, checkable requirement stated in the query or explicitly triggered by the provided context. Default expectations such as "be professional", "be legal", "be compliant", or "understand finance" are not constraints unless the query or context explicitly states them.

## Constraint Families

FinIF uses four top-level constraint families:

| Family | Meaning |
| --- | --- |
| Format and Presentation (FP) | Output form, structure, wording, terminology, tone, audience, length, and presentation requirements. |
| Evidence and Grounding (EG) | Requirements about using the provided context, citing evidence, preserving source fidelity, handling unknowns, retaining documentation, and covering required deliverables, topics, issues, profile factors, control areas, action items, and alternatives. |
| Decision and Boundary (DB) | Workflow decisions, classification, escalation, reporting, approval, exception handling, and regulated claim boundaries. |
| Quantitative Verification (QV) | Calculations, independent verification, reconciliation, thresholds, deadlines, ranking, stress scenarios, and quantitative checks. |

The fine-grained tags below are implementation-level subtypes. Each extracted constraint is assigned exactly one primary fine-grained tag.

## Fine-Grained Tags

| Family | Fine Tag Prefix |
| --- | --- |
| Format and Presentation | `FP*` |
| Evidence and Grounding | `EG*` and `RC*` |
| Decision and Boundary | `DB*` |
| Quantitative Verification | `QV*` |

### FP: Format and Presentation

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| FP1 | Structure / sections | Required sections, headings, memo structure, order of sections, summary placement, or named parts. |
| FP2 | Output format | Checklist, list, table, matrix, JSON, markup, fixed fields, or other concrete presentation format. |
| FP3 | Length / count / precision / ordering | Word/page limits, exact number of findings, decimal places, percentage formatting, tolerance, sorting, or ranking as presentation. |
| FP4 | Wording / terminology | Mandatory phrase, keyword, label, disclaimer, legal term, forbidden wording, plain-language requirement, or terminology control. |
| FP5 | Tone / role / audience | Neutral, conservative, formal, client-friendly, board-facing, regulator-facing, or role-specific expression. |
| FP6 | Opening / closing | Start with conclusion, end with recommendation, include executive summary, or close with next steps. |

### EG: Evidence and Grounding

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| EG1 | Context-only grounding | Use only provided context; no outside facts, external assumptions, or unsupported additions. |
| EG2 | Evidence citation / mapping | Cite document, field, excerpt, figure, source evidence, or map expectations to evidence. |
| EG3 | Fact-vs-inference separation | Distinguish observed facts, customer statements, assumptions, inferences, and conclusions. |
| EG4 | Missing / unknown handling | Mark missing data, unknown facts, unresolved matches, incomplete records, or open questions. |
| EG5 | Source fidelity | Preserve source figures, terms, dates, names, thresholds, and legal/rule references. |
| EG6 | Source-status caveat | State source status, such as staff guidance, proposal, non-binding guide, rule text, current obligation, or no-new-obligations caveat. |
| EG7 | Records / documentation | Preserve or list required records, supporting documentation, logs, workpapers, copies, or retention materials. |
| RC1 | Work product / required deliverable | Produce a named memo, note, report, review, checklist, workpaper, disclosure, procedure, or other requested deliverable. |
| RC2 | Required topic coverage | Cover named topics such as CIP, beneficial ownership, SAR timing, product types, rule areas, obligations, or review areas. |
| RC3 | Required issue coverage | Identify listed red flags, conflicts, deficiencies, breaches, missing items, abuse typologies, suspicious behaviors, or event types. |
| RC4 | Action / remediation coverage | Include next steps, owners, deadlines, corrective actions, remediation, follow-up, information to collect, or evidence to obtain. |
| RC5 | Alternative / trade-off coverage | Compare options, alternatives, risks and rewards, costs, pros and cons, or less complex substitutes. |
| RC6 | Customer / account profile coverage | Document required profile factors such as age, investment objective, liquidity need, risk tolerance, experience, account type, beneficial ownership, or transaction history. |
| RC7 | Control / governance coverage | Cover policies, procedures, supervision, training, testing, internal controls, audit planning, monitoring, inspection, or governance responsibilities. |
| RC8 | Risk / impact coverage | Cover risks, limitations, exposure, volatility, leverage, downside, consequences, customer harm, regulatory impact, operational impact, or structural investor protection effects. |

### DB: Decision and Boundary

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| DB1 | Required decision / evaluation | Choose or evaluate proceed, escalate, decline, approve, reject, hold, reportable, non-reportable, suitable, effective, or applicable. |
| DB2 | Conditional trigger | If context condition X is present, output action Y. |
| DB3 | Escalation / reporting / filing | Escalate to Compliance, Credit Risk, manager, board, regulator, or file/report/submit a required item. |
| DB4 | Boundary / non-commitment | Do not promise approval, returns, tax outcome, legal conclusion, confirmed misconduct, or deterministic treatment from incomplete evidence. |
| DB5 | Exception / breach / gap | Flag policy exception, breach, waiver need, deficiency, unresolved inconsistency, control gap, or non-compliance indicator. |
| DB6 | Classification | Classify a communication, customer, product, event, complaint, account, control issue, recommendation, advertisement, or risk level into explicit categories. |
| DB7 | Approval / authorization | Identify required approval, principal review, manager approval, filing approval, authority boundary, or approval prerequisite. |
| DB8 | Regulated communication boundary | Apply marketing, advertising, testimonial, endorsement, rating, ranking, performance, sponsor, logo, fair-and-balanced, misleading-claim, or substantiation restrictions. |
| DB9 | Evidence-rule-action chain | Connect active evidence, governing rule or task standard, and final action without presenting facts, calculations, and decisions as disconnected fragments. |

### QV: Quantitative Verification

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| QV1 | Formula / calculation | Compute ratio, exposure, proceeds, variance, stress loss, threshold amount, turnover, or cost-equity value. |
| QV2 | Verification / recalculation | Independently verify or recalculate borrower, client, model, disclosure, or reported figures against source data. |
| QV3 | Reconciliation | Compare records, identify mismatches, compute differences, or avoid marking items reconciled when mismatch remains. |
| QV4 | Threshold | Monetary, ratio, percentage, exposure, concentration, SAR/CTR, page-count, investor-count, or approval thresholds. |
| QV5 | Time window / deadline | Filing deadlines, review periods, reporting cadence, due dates, retention periods, as-of dates, or loss-recognition quarters. |
| QV6 | Quantitative comparison / ranking | Compare alternatives, scenarios, amounts, risks, severity, performance, or structural protections. |
| QV7 | Stress / scenario / sensitivity | Apply specified stress scenario, assumption, shock, time horizon, sensitivity, or supervisory scenario component. |

## Evaluation Method

### Dual-Track Scoring

Each constraint is evaluated by one of two methods:

1. **Rule-based checks**: Deterministic checkers for mechanically verifiable constraints (JSON validity, keyword presence, table structure, numeric values, etc.). If a rule checker cannot make a reliable binary decision, it returns `needs_judge`.

2. **LLM-as-a-judge**: For semantic constraints and unresolved rule checks. The judge receives the prompt, model response, and all pending constraints for the item, then returns a binary pass/fail per constraint plus one holistic quality score.

### Evaluation Method By Tag

| Tag | Default | Prefer `rule_aided` When | Use LLM Judge When |
| --- | --- | --- | --- |
| FP1 | `rule_aided` | Required section names, headings, order, or labels are explicit. | Section quality or substantive organization must be judged semantically. |
| FP2 | `rule_aided` | JSON/table/checklist/matrix/field format or column names are explicit. | The requested format is loose or depends on whether content is useful. |
| FP3 | `rule_aided` | Word/item/section/table-row count, decimal places, precision, sorting key, or exact number of findings is explicit. | Ranking/order requires subjective importance or finance judgment. |
| FP4 | `rule_aided` | Required phrase, forbidden phrase, disclaimer, label, term, ticker, code, or notation is explicit. | Plain-language quality, misleadingness, or wording adequacy is semantic. |
| FP5 | `judge` | The role/audience requirement is an exact label or required phrase. | Tone, neutrality, client-friendliness, board/regulator suitability, or style quality is requested. |
| FP6 | `rule_aided` | First line, opening section, closing statement, recommendation label, or next-step label is explicit. | The opening/closing must be substantively appropriate. |
| EG1 | `judge` | The constraint only bans obvious external-source phrases or requires an explicit no-outside-sources statement. | Need to determine whether the response introduced unsupported facts or assumptions. |
| EG2 | `rule_aided` | Required citations, DOC IDs, evidence columns, source fields, or mapping labels are explicit. | Need to judge whether cited evidence actually supports the claim. |
| EG3 | `rule_aided` | Required labels such as Facts, Assumptions, Inferences, Conclusions, or Customer statements are explicit. | Need to judge whether facts and inferences are correctly separated. |
| EG4 | `rule_aided` | Required missing/unknown/open-item labels or specific missing fields are explicit. | Need to judge whether all material unknowns were identified. |
| EG5 | `rule_aided` | Exact source figures, dates, names, thresholds, legal references, or required terms can be matched. | Need to judge faithful paraphrase or source interpretation. |
| EG6 | `rule_aided` | Exact caveat terms such as proposal, staff guidance, no legal force, or no new obligations are required. | Need to judge nuanced source-status explanation. |
| EG7 | `rule_aided` | Exact records, document names, retention periods, logs, workpapers, or copies are listed. | Need to judge documentation sufficiency. |
| RC1 | `rule_aided` | Named deliverable, memo/report/checklist/workpaper type, or exact title is required. | Need to judge whether the deliverable substantively fulfills the task. |
| RC2 | `rule_aided` | Named topic list can be checked by required labels/keywords/columns. | Need to judge substantive topic coverage. |
| RC3 | `rule_aided` | Listed red flags, issue names, deficiencies, or event types are exact. | Need to judge whether unlisted or semantic issues were identified. |
| RC4 | `rule_aided` | Required owners, dates, next-step labels, corrective actions, or evidence items are explicit. | Need to judge adequacy of remediation or follow-up. |
| RC5 | `rule_aided` | Alternatives/options/pros/cons labels or named choices are explicit. | Need to judge trade-off quality. |
| RC6 | `rule_aided` | Profile factor names, account attributes, objectives, or risk fields are explicit. | Need to judge completeness or suitability of profile analysis. |
| RC7 | `rule_aided` | Control areas, training cadence, testing frequency, governance labels, or policy names are explicit. | Need to judge control design or governance adequacy. |
| RC8 | `rule_aided` | Named risks, impacts, exposures, harms, or numeric losses are explicit. | Need to judge risk materiality, impact severity, or completeness. |
| DB1 | `judge` | Decision labels are closed-set and explicit, such as approve/reject/escalate/hold/reportable/non-reportable. | Need to judge whether the decision is correct or well supported. |
| DB2 | `rule_aided` | Both trigger and required follow-up are exact strings or closed-set labels. | Need to infer whether a condition is present or what action it should trigger. |
| DB3 | `rule_aided` | Required escalation target, filing/report name, deadline, threshold, or office is explicit. | Need to judge whether escalation/reporting is warranted. |
| DB4 | `rule_aided` | Forbidden promises, conclusions, guarantees, or non-commitment phrases are explicit. | Need to judge implied overstatement or boundary compliance. |
| DB5 | `judge` | Named breach/exception/waiver/gap labels are explicit and can be searched. | Need to judge whether a breach, exception, or gap exists. |
| DB6 | `rule_aided` | Classification choices are closed-set and the output must include one of those labels. | Need to judge whether the chosen class is correct. |
| DB7 | `rule_aided` | Required approval authority, reviewer, prerequisite, or approval label is explicit. | Need to judge approval sufficiency or authority boundary. |
| DB8 | `rule_aided` | Required/prohibited advertising, performance, ranking, testimonial, endorsement, logo, or disclaimer phrases are explicit. | Need to judge fair-and-balanced presentation or misleadingness. |
| QV1 | `rule_aided` | Formula, inputs, expected result, or tolerance is explicit or derivable from context. | Calculation correctness cannot be verified from available values. |
| QV2 | `rule_aided` | Source values and expected tie-out/recalculation target are explicit. | Verification requires financial interpretation or unstated assumptions. |
| QV3 | `rule_aided` | Records, differences, mismatch labels, or reconciliation status rules are explicit. | Need to judge materiality or root cause adequacy. |
| QV4 | `rule_aided` | Threshold amount, ratio, percentage, limit, or comparison operator is explicit. | Need to judge whether a threshold should apply. |
| QV5 | `rule_aided` | Date, deadline, review window, cadence, retention period, or as-of date is explicit. | Need to interpret ambiguous timing or regulatory applicability. |
| QV6 | `judge` | Expected order, closed-set comparison, or explicit ranking basis is available. | Ranking depends on qualitative importance or trade-off judgment. |
| QV7 | `rule_aided` | Stress shock, assumption, horizon, sensitivity, or scenario component is explicit. | Need to judge stress narrative adequacy or scenario interpretation. |

### Aggregation

Primary metric:

```
ISR (Instruction Satisfaction Rate) = passed constraints / total decided constraints
```

Auxiliary quality score:

```
Mean quality_score on a 0-10 scale
```

Also reported per task, per workflow, per constraint family, and per fine-grained tag.
