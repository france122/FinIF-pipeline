# FinIF v2 Explicit Constraint Taxonomy

Date: 2026-06-10

## Purpose

This taxonomy is for extracting constraints from `context + query` in FinIF v2.

A constraint is an explicit, checkable requirement stated in the query or explicitly triggered by the provided context.
Default expectations such as "be professional", "be legal", "be compliant", or "understand finance" are not constraints unless the query or context explicitly states them.

## Relationship to the old taxonomy

The previous taxonomy in `current/benchmark/constraint_taxonomy.json` is partially reusable.

Reusable:

- `F*` format and structure constraints.
- `N*` length, count, precision, and numeric presentation constraints.
- `L*` keyword, forbidden wording, terminology, and notation constraints.
- `S*` tone, role, audience, and style constraints.
- `C5` conditional trigger constraints.
- Parts of `C1`, `C2`, `C6` if they are made explicit and grounded in the context/query.

Needs revision:

- Old `C1 Coverage` was too broad; split into required-field coverage and task-substantive completeness.
- Old `C2 Evidence` was too broad; keep only explicit evidence/citation/grounding requirements.
- Old `C3/C4` are usable only when a perspective or scenario is explicitly requested.
- Old `C6 Computation` should no longer be treated as only a hidden correctness axis. In v2 it can be an explicit constraint when the query/context requires a calculation, threshold check, reconciliation, or formula.

Not reusable as-is:

- Any sampled constraint that was artificially appended to the prompt but is not natural to the current `context + query`.
- Any implicit financial best practice that is not stated in the query or context.

## Paper-Facing Families

For the paper, FinIF v2 uses five top-level constraint families:

| Family | 中文名 | Meaning |
| --- | --- | --- |
| Format and Presentation | 格式与表达 | Output form, structure, wording, terminology, tone, audience, length, and presentation requirements. |
| Evidence and Grounding | 证据与依据 | Requirements about using the provided context, citing evidence, preserving source fidelity, handling unknowns, and retaining documentation. |
| Decision and Boundary | 决策与边界 | Workflow decisions, classification, escalation, reporting, approval, exception handling, and regulated claim boundaries. |
| Quantitative Verification | 量化核验 | Calculations, independent verification, reconciliation, thresholds, deadlines, ranking, stress scenarios, and quantitative checks. |
| Required Content Coverage | 必要内容覆盖 | Required fields, topics, issues, profile factors, control areas, action items, and alternatives to cover. |

The fine-grained tags below are implementation-level subtypes. Final benchmark data should assign exactly one primary fine-grained `tag` to each extracted constraint. Do not keep secondary tag arrays in the final JSONL; if a constraint appears to need many tags, rewrite or split it, then choose the most central tag.

## v2 Fine-Grained Tags

The second layer is aligned with the five paper-facing families:

| Family | Fine Tag Prefix |
| --- | --- |
| Format and Presentation | `FP*` |
| Evidence and Grounding | `EG*` |
| Decision and Boundary | `DB*` |
| Quantitative Verification | `QV*` |
| Required Content Coverage | `RC*` |

### FP: Format and Presentation

Family: `Format and Presentation`

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| FP1 | Structure / sections | Required sections, headings, memo structure, order of sections, summary placement, or named parts. |
| FP2 | Output format | Checklist, list, table, matrix, JSON, markup, fixed fields, or other concrete presentation format. |
| FP3 | Length / count / precision / ordering | Word/page limits, exact number of findings, decimal places, percentage formatting, tolerance, sorting, or ranking as presentation. |
| FP4 | Wording / terminology | Mandatory phrase, keyword, label, disclaimer, legal term, forbidden wording, plain-language requirement, or terminology control. |
| FP5 | Tone / role / audience | Neutral, conservative, formal, client-friendly, board-facing, regulator-facing, or role-specific expression. |
| FP6 | Opening / closing | Start with conclusion, end with recommendation, include executive summary, or close with next steps. |

### EG: Evidence and Grounding

Family: `Evidence and Grounding`

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| EG1 | Context-only grounding | Use only provided context; no outside facts, external assumptions, or unsupported additions. |
| EG2 | Evidence citation / mapping | Cite document, field, excerpt, figure, source evidence, or map expectations to evidence. |
| EG3 | Fact-vs-inference separation | Distinguish observed facts, customer statements, assumptions, inferences, and conclusions. |
| EG4 | Missing / unknown handling | Mark missing data, unknown facts, unresolved matches, incomplete records, or open questions. |
| EG5 | Source fidelity | Preserve source figures, terms, dates, names, thresholds, and legal/rule references. |
| EG6 | Source-status caveat | State source status, such as staff guidance, proposal, non-binding guide, rule text, current obligation, or no-new-obligations caveat. |
| EG7 | Records / documentation | Preserve or list required records, supporting documentation, logs, workpapers, copies, or retention materials. |

### DB: Decision and Boundary

Family: `Decision and Boundary`

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

Family: `Quantitative Verification`

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| QV1 | Formula / calculation | Compute ratio, exposure, proceeds, variance, stress loss, threshold amount, turnover, or cost-equity value. |
| QV2 | Verification / recalculation | Independently verify or recalculate borrower, client, model, disclosure, or reported figures against source data. |
| QV3 | Reconciliation | Compare records, identify mismatches, compute differences, or avoid marking items reconciled when mismatch remains. |
| QV4 | Threshold | Monetary, ratio, percentage, exposure, concentration, SAR/CTR, page-count, investor-count, or approval thresholds. |
| QV5 | Time window / deadline | Filing deadlines, review periods, reporting cadence, due dates, retention periods, as-of dates, or loss-recognition quarters. |
| QV6 | Quantitative comparison / ranking | Compare alternatives, scenarios, amounts, risks, severity, performance, or structural protections. |
| QV7 | Stress / scenario / sensitivity | Apply specified stress scenario, assumption, shock, time horizon, sensitivity, or supervisory scenario component. |

### RC: Required Content Coverage

Family: `Required Content Coverage`

| Tag | Name | Use When Explicitly Required |
| --- | --- | --- |
| RC1 | Work product / required deliverable | Produce a named memo, note, report, review, checklist, workpaper, disclosure, procedure, or other requested deliverable. |
| RC2 | Required topic coverage | Cover named topics such as CIP, beneficial ownership, SAR timing, product types, rule areas, obligations, or review areas. |
| RC3 | Required issue coverage | Identify listed red flags, conflicts, deficiencies, breaches, missing items, abuse typologies, suspicious behaviors, or event types. |
| RC4 | Action / remediation coverage | Include next steps, owners, deadlines, corrective actions, remediation, follow-up, information to collect, or evidence to obtain. |
| RC5 | Alternative / trade-off coverage | Compare options, alternatives, risks and rewards, costs, pros and cons, or less complex substitutes. |
| RC6 | Customer / account profile coverage | Document required profile factors such as age, investment objective, liquidity need, risk tolerance, experience, account type, beneficial ownership, or transaction history. |
| RC7 | Control / governance coverage | Cover policies, procedures, supervision, training, testing, internal controls, audit planning, monitoring, inspection, or governance responsibilities. |
| RC8 | Risk / impact coverage | Cover risks, limitations, exposure, volatility, leverage, downside, consequences, customer harm, regulatory impact, operational impact, or structural investor protection effects. |

## Evaluation Method By Tag

Evaluation should maximize deterministic `rule_aided` checks when the constraint can be checked mechanically. To preserve accuracy, a rule checker must return `needs_judge` instead of guessing when the expected value, exact label, count, field, phrase, or regex is not available.

Use this decision order:

1. If the constraint includes an explicit checker config (`evaluator`, `checker`, or `rule`), run that deterministic checker first.
2. Otherwise use the default method below for the fine tag.
3. If the default is `rule_aided` but the checker lacks enough parameters, return `needs_judge` and send the single constraint to LLM-as-a-judge.
4. If the default is `judge`, use LLM-as-a-judge unless the constraint is clearly reducible to exact labels, fields, counts, dates, numbers, keywords, forbidden phrases, or table/JSON structure.

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
| QV6 | `rule_aided` | Expected order, closed-set comparison, or explicit ranking basis is available. | Ranking depends on qualitative importance or trade-off judgment. |
| QV7 | `rule_aided` | Stress shock, assumption, horizon, sensitivity, or scenario component is explicit. | Need to judge stress narrative adequacy or scenario interpretation. |
| RC1 | `rule_aided` | Named deliverable, memo/report/checklist/workpaper type, or exact title is required. | Need to judge whether the deliverable substantively fulfills the task. |
| RC2 | `rule_aided` | Named topic list can be checked by required labels/keywords/columns. | Need to judge substantive topic coverage. |
| RC3 | `rule_aided` | Listed red flags, issue names, deficiencies, or event types are exact. | Need to judge whether unlisted or semantic issues were identified. |
| RC4 | `rule_aided` | Required owners, dates, next-step labels, corrective actions, or evidence items are explicit. | Need to judge adequacy of remediation or follow-up. |
| RC5 | `rule_aided` | Alternatives/options/pros/cons labels or named choices are explicit. | Need to judge trade-off quality. |
| RC6 | `rule_aided` | Profile factor names, account attributes, objectives, or risk fields are explicit. | Need to judge completeness or suitability of profile analysis. |
| RC7 | `rule_aided` | Control areas, training cadence, testing frequency, governance labels, or policy names are explicit. | Need to judge control design or governance adequacy. |
| RC8 | `rule_aided` | Named risks, impacts, exposures, harms, or numeric losses are explicit. | Need to judge risk materiality, impact severity, or completeness. |

## Extraction Schema

Each extracted constraint should use this shape:

```json
{
  "tag": "EG2",
  "constraint": "Cite supporting evidence for each red flag.",
  "source": "query",
  "evidence": "Query says: identify suspicious signals, cite the supporting evidence.",
  "check_type": "rule_or_judge",
  "scope": "output|content|decision|calculation|evidence",
  "notes": ""
}
```

Allowed `source` values:

- `query`: directly stated by the query.
- `context`: explicitly stated or triggered by the context.

Do not use:

- `domain_default`
- `best_practice`
- `inferred_from_finance`

## Evaluation Method

FinIF v2 does not require a separate rubric for LLM-as-judge constraints.

For each model response and each extracted constraint, the judge prompt should ask only:

```text
Given the response and the constraint, does the response satisfy this constraint?
Answer pass or fail, and give a short reason.
```

The constraint text itself is the judging standard.

Use deterministic or rule-aided checks only when the constraint is mechanically checkable, for example:

- valid JSON or table format;
- required field exists;
- required keyword is present;
- forbidden phrase is absent;
- number of sections/items;
- deadline or threshold value appears;
- simple calculation or reconciliation can be verified.

Otherwise use LLM-as-judge directly against the constraint.

No extra per-constraint rubric should be generated unless later error analysis shows that a specific constraint type is ambiguous.

## Mapping From Old Tags

The old `F/N/L/S/E/D/Q/R/M` labels should not be used in new JSONL outputs.
They are only historical references.

| Old Pattern | New v2 Handling |
| --- | --- |
| `F*`, `L*`, `S*`, `N1-N3` | Map into `FP*`. |
| `E*` | Map into `EG*`. |
| `D*`, `M*` | Map into `DB*`. Marketing and advertising constraints now use `DB8`. |
| `Q*`, `N4-N5` | Map into `QV*`. |
| `R*` | Map into `RC*`. |
| Old `C1 Coverage` | Split into `RC1-RC8`. |
| Old `C2 Evidence` | Split into `EG1-EG7`. |
| Old `C3 Perspective` | Map to `FP5` when explicit. |
| Old `C4 Scenario` | Map to `QV7` or `DB2` when explicit. |
| Old `C5 Conditional Trigger` | Map to `DB2`. |
| Old `C6 Computation` | Split into `QV1-QV7`; keep correctness checks downstream. |

## Observed v2 Constraint Patterns From The First Risk and Compliance Batch

The first self-contained batch contains 23 items and 187 explicit constraints.
The highest-frequency patterns were:

- Work product / structure requirements: map mainly to `RC1`, `FP1`, or `FP2`.
- Named topic coverage: map to `RC2`, `RC3`, `RC6`, `RC7`, or `RC8`.
- Reporting, escalation, approval, and filing triggers: map to `DB3`, `DB7`, `QV4`, or `QV5`.
- Thresholds and deadlines: map to `QV4` or `QV5`; use `DB3` when the central requirement is reporting or filing.
- Evidence and documentation: map to `EG2`, `EG4`, or `EG7`.
- Source caveats such as "no legal force" or "proposal rather than current obligation": map to `EG6`.
- Marketing and communication restrictions: map to `DB8`.
- Computation, independent verification, stress testing, and reconciliation: map to `QV1-QV7`.

For extraction, prefer the most specific single tag. For example:

- "Do not describe a fuzzy screening match as a confirmed sanctions hit" -> `DB4`, not generic `FP4`.
- "Include FIN-2025-CVCKIOSK in SAR field 2" -> `FP4`, because the exact required wording or field content is the central constraint.
- "Gross performance must be accompanied by net performance" -> `DB8`, not generic `RC2`.
- "Classify the communication as retail/correspondence/institutional" -> `DB6`.
- "Maintain copies of social media posts and performance support" -> `EG7`.
- "Use the same control framework as management" -> `EG5` or `RC7`, depending on whether the constraint is about fidelity to the source or audit planning coverage.

## Practical Rule

When extracting constraints, first ask:

1. Is the requirement explicitly written in the query?
2. If not, is it explicitly written or mechanically triggered by the context?
3. Can a judge/checker verify whether the model followed it?

If any answer is no, do not extract it as a constraint.
