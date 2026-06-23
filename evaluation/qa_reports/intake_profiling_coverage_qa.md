# Intake and Profiling Coverage QA

QA date: 2026-06-10  
Reviewed shard: `outputs/full_prompts/scaled_shards/intake_profiling_full_prompts.jsonl`  
Reference specs: `task_workflow_final.md`, `constraint_taxonomy_v2.md`

## Executive judgment

This shard covers the six intended Intake and Profiling task labels at the correct count, and the six task families are mostly distinguishable by work product and core operation. However, it is not yet strong evidence of broad subtype coverage inside each task. Every task uses one fixed query skeleton across all 28 items; most variation is in entity name, numeric fields, missing fields, thresholds, or a small set of intake case types. The shard is therefore better described as six well-formed templates with parameter variation, not full coverage of fine-grained task diversity.

Overall recommendation: **needs review before using as a final scaled shard**. Do not discard the shard, but revise a meaningful subset of each task to introduce different work products, context pack shapes, and task-specific questions.

## 1. Task distribution

Distribution check passes.

| Task | Count | Expected | Result |
| --- | ---: | ---: | --- |
| KYC onboarding | 28 | 28 | pass |
| Client risk profiling | 28 | 28 | pass |
| Loan application intake | 28 | 28 | pass |
| Counterparty / issuer profile construction | 28 | 28 | pass |
| Missing information checklist | 28 | 28 | pass |
| Service scope explanation | 28 | 28 | pass |
| Total | 168 | 168 | pass |

Query-template check: after replacing only the target entity/case name, each of the six tasks has **1 unique query skeleton across 28 items**. This is the main coverage concern.

## 2. Sample review by task

### KYC onboarding

Sampled items: `intake_kyc_onboarding_001`, `intake_kyc_onboarding_015`, `intake_kyc_onboarding_028`  
Quality judgment: **needs review**

What works:

- The work product is task-appropriate: KYC onboarding review note.
- Context includes customer intake details plus CDD/account-opening policy.
- Query asks for CIP, beneficial ownership, control person, tax documentation, expected activity, source of funds, screening, missing items, evidence citations, and no approval promise. These are aligned with KYC onboarding.
- Extracted constraints are mostly explicit and checkable: table format, context-only, document id citations, unknown handling, beneficial-owner threshold, compliance hold blockers, non-approval boundary.

Problems:

- All sampled queries use the same instruction skeleton. The only real changes are customer names and field values.
- Entity-name/entity-type mismatches appear in many KYC files, which may create artificial noise rather than meaningful KYC difficulty. Examples: `intake_kyc_onboarding_001` has "Northstar Components LLC" but entity type "Corporation"; `intake_kyc_onboarding_015` has "Aster Microelectronics Inc." but entity type "LLC"; `intake_kyc_onboarding_028` has "Arcadia Office Supply LLC" but entity type "Corporation".
- Items using the SEC AML Source Tool include source-status language saying it is staff views, not a rule, and creates no new obligations, but extracted constraints do not require preserving that caveat. Affected KYC items include all even-numbered KYC items from `intake_kyc_onboarding_002` through `intake_kyc_onboarding_028`.

Actionable fixes:

- Fix or intentionally frame entity-name/entity-type inconsistencies as explicit items to flag. If intentional, add a query/context requirement to treat inconsistent legal identity data as a KYC discrepancy.
- Add 6-10 KYC variants with different deliverables, such as CIP exception memo, beneficial ownership gap note, sanctions/PEP unresolved-match intake note, address verification checklist, or EDD referral note.
- For SEC staff-source contexts, add an explicit source-status/caveat constraint or remove the non-binding source if it is not meant to be tested.

### Client risk profiling

Sampled items: `intake_client_risk_profiling_001`, `intake_client_risk_profiling_015`, `intake_client_risk_profiling_028`  
Quality judgment: **needs review**

What works:

- The task is clearly client risk profiling, not generic KYC.
- Context includes investor questionnaire data and a risk profiling policy.
- Query requires profile factors, recalculation, classification, liquidity/concentration triggers, missing information, fact-vs-conclusion separation, and no product/trade recommendation.
- Constraints are explicit and appropriately tagged, including `QV1`, `DB6`, `DB2`, `QV4`, and `DB4`.

Problems:

- All 28 items use the same query skeleton and same work product: client risk profile completeness note.
- The task subtype is narrow: mostly raw-score classification plus liquidity/concentration overrides. It does not cover other common profiling subtasks such as capacity-for-loss review, contradictory questionnaire answers, profile update after changed circumstances, joint-account authority, entity/institutional profile, or suitability-data sufficiency for a specific account type.

Actionable fixes:

- Keep some score-band samples, but replace at least 8-10 with different profiling work products: profile update memo, contradiction log, profile-data sufficiency checklist, profile override rationale, or client-facing missing-profile-fields request.
- Add scenarios where the risk score and narrative conflict, where liquidity need is qualitatively described rather than a clean percentage, and where account authority or trusted contact information changes the intake next step.

### Loan application intake

Sampled items: `intake_loan_application_001`, `intake_loan_application_015`, `intake_loan_application_028`  
Quality judgment: **needs review**

What works:

- The task is well aligned to loan intake: loan packet, SBA Form 1919 reference, small business loan checklist, DSCR calculation, missing-document table, owner requirements, stale information, and no approve/decline boundary.
- Context/query/work product match cleanly in the sampled items.
- Constraints are explicit and useful: DSCR formula, 1.20 threshold, owner coverage, missing/stale information, citations, and no approval/decline.

Problems:

- All 28 items use the same query skeleton and the same work product.
- The loan task mostly tests one calculation and one checklist policy. It undercovers borrower-intake subtasks such as collateral sufficiency intake, guarantor information intake, use-of-proceeds validation, employment/income verification for consumer loans, commercial real estate intake, or authorization/privacy defects.
- Some requirements are generic across all loan cases even when the stated purpose differs. Example: `intake_loan_application_028` is commercial real estate purchase but still asks for missing vendor quotes, which fits equipment purchases better than CRE.

Actionable fixes:

- Add loan-intake variants with distinct collateral packages, guarantor/owner gaps, CRE-specific documentation, consumer income verification, and use-of-proceeds inconsistencies.
- Make purpose-specific requirements conditional in the context, so equipment-purchase cases ask for vendor quotes while CRE cases ask for purchase agreement, appraisal, rent roll, environmental report, or title items.

### Counterparty / issuer profile construction

Sampled items: `intake_counterparty_profile_001`, `intake_counterparty_profile_015`, `intake_counterparty_profile_028`  
Quality judgment: **needs review**

What works:

- The work product is distinct from KYC: counterparty/issuer profile with profile card, evidence map, leverage, preliminary risk classification, red flags, missing evidence, and next diligence steps.
- Context includes entity role, industry, jurisdictions, ownership/control, financials, requested exposure, screening/adverse media, legal/regulatory notes, and profile standard.
- Constraints are explicit and task-relevant: debt/EBITDA calculation, Low/Medium/High classification, high-risk triggers, observed fact vs analyst judgment, and no recommendation/approval/authorization.

Problems:

- All 28 items use the same query skeleton and same profile standard.
- The profile construction task is overly centered on debt-to-EBITDA and a single risk-tier policy. It undercovers issuer-specific profile work such as business description synthesis, management/background summary, offering/project profile, counterparty exposure mapping, issuer document index, and jurisdiction/ownership complexity.
- Some synthetic pairings feel arbitrary rather than finance-realistic. Example: `intake_counterparty_profile_015` uses Orchard City Pharmacy LLC with industry "consumer finance"; `intake_counterparty_profile_028` uses Maple Bay Apparel LLC with industry "industrial equipment".

Actionable fixes:

- Add variants that do not all require leverage classification: issuer profile for an offering memo, project/company profile, counterparty exposure profile, management/background profile, and document-evidence map.
- Clean up entity/industry/name coherence or make inconsistencies explicit red flags to identify.

### Missing information checklist

Sampled items: `intake_missing_info_001`, `intake_missing_info_015`, `intake_missing_info_028`  
Quality judgment: **needs review**

What works:

- The work product is exactly the intended task: missing information checklist.
- Context includes an intake file index and a stage-gate policy.
- The query asks for blocker/follow-up/nice-to-have classification, evidence citations, owner, due date, present-but-questionable items, and no assumption that pending screening or unsigned forms are complete.
- Constraints are explicit and mostly grounded in query/policy, including due-date handling and blocker triggers.

Problems:

- All 28 items use the same query skeleton and same checklist structure.
- The stage-gate policy is broad but repetitive; many cases differ only in which fields are complete/missing and the blocker due date.
- Some case types appear, but the checklist does not adapt enough to them. Distribution observed: 5 new brokerage account, 5 legal entity KYC refresh, 5 small business loan intake, 5 issuer onboarding, 4 client risk profile update, 4 service engagement opening.
- SEC staff-source caveat is not captured where SEC AML Source Tool appears: `intake_missing_info_004`, `008`, `012`, `016`, `020`, `024`, `028`.

Actionable fixes:

- Create task-specific checklist variants: KYC refresh missing-evidence list, loan pre-underwriting blocker list, issuer diligence intake gaps, advisory profile update missing fields, and service engagement authorization checklist.
- Vary output forms: blocker-only escalation note, client request list, internal file-completeness matrix, and stage-gate decision note.
- Add or remove source-status constraints consistently for non-binding SEC staff-source documents.

### Service scope explanation

Sampled items: `intake_service_scope_001`, `intake_service_scope_015`, `intake_service_scope_028`  
Quality judgment: **needs review**

What works:

- The task is clearly client-facing service scope explanation, and the query enforces a different output mode from the other tasks: concise email, no internal document ids, no tax/legal advice.
- Context includes client request, provided/missing materials, and service-scope communication policy.
- Constraints are explicit: client-friendly tone, context-only, no internal doc ids, explain what the firm can/cannot do, timing, next documents, mark unavailable facts, no guarantees/tax/legal advice.

Problems:

- All 28 items use the same query skeleton and same work product.
- The client asks the same unrealistic bundle across task types: guarantee approval by end of week, guarantee investment returns, confirm tax treatment, and waive missing documentation. This makes many items feel like a scripted compliance exercise rather than varied service-scope explanations.
- The task undercovers other service-scope subtasks: explaining intake vs advice boundary, data/privacy use, planning-only engagement boundary, underwriting not started, third-party document dependency, and handoff to compliance/credit.

Actionable fixes:

- Replace some repeated client request bundles with narrower, realistic asks tied to each case type.
- Add variants for phone-call follow-up note, client-facing missing-document request, intake-stage scope paragraph, and boundary clarification email after a client asks for advice outside scope.
- For planning-consultation and risk-profile requests, remove "loan/account approval" language where not applicable and use scope boundaries that fit the actual service.

## 3. Cross-task template and coverage findings

Major issue: **one query skeleton per task**. This is the strongest evidence that the shard is partly template-swapped. Although each task has a distinct skeleton, there is little within-task instruction diversity.

Context variation exists but is shallow:

- Names, jurisdictions, scores, financial amounts, missing fields, timing, and flags vary.
- Policy documents and context structures are highly repeated.
- Most contexts have exactly the same three-document shape: external/regulatory reference, synthetic case file, synthetic internal policy.

Task distinction is still real:

- KYC onboarding focuses on legal entity onboarding, CIP, beneficial ownership, tax/address/screening, and account activation boundary.
- Client risk profiling focuses on profile factors, score classification, liquidity/concentration triggers, and no product recommendation.
- Loan intake focuses on loan packet completeness, owner requirements, DSCR, and no approval/decline.
- Counterparty/issuer profile focuses on entity profile, leverage, risk tier, and no recommendation/authorization.
- Missing information checklist focuses on stage-gate completeness classification.
- Service scope explanation focuses on client-facing boundary communication.

So the shard is not merely one global template with labels changed. It is six task-specific templates. The remaining problem is lack of subtype richness inside each template.

## 4. Context/query/work product alignment

Alignment is mostly acceptable in the sampled items, but with specific issues to repair:

- `intake_kyc_onboarding_001`, `015`, `028`: work product and query align with KYC, but entity suffix/entity type mismatches should be fixed or made explicit as discrepancies.
- `intake_loan_application_028`: query asks for missing vendor quotes while stated purpose is commercial real estate purchase. Use purpose-specific documentation requirements.
- `intake_counterparty_profile_015`, `028`: entity names and industries feel inconsistent; either clean them or ask the model to flag inconsistent profile data.
- `intake_service_scope_015`, `028`: repeated "guarantee investment returns / confirm tax treatment / waive missing documentation" request appears across unrelated services. Vary the client ask to match loan intake, issuer onboarding, planning, KYC refresh, or brokerage account opening.

## 5. Constraint explicitness review

Most extracted constraints are explicit and checkable under `constraint_taxonomy_v2.md`.

Positive findings:

- The constraint sources are usually justified by direct query language or explicit policy text.
- Good use of context-triggered quantitative and decision constraints: DSCR formula and threshold, risk-score bands, beneficial-owner thresholds, blocker due dates, and leverage risk-tier triggers.
- Boundaries such as "do not approve/decline," "do not recommend securities/trades," "do not promise approval/returns," and "do not cite internal document ids" are explicit.

Issues:

- Non-binding source-status language is present in SEC AML Source Tool contexts but not extracted as an `EG6` source-status caveat. Affected items:
  - KYC onboarding: `intake_kyc_onboarding_002`, `004`, `006`, `008`, `010`, `012`, `014`, `016`, `018`, `020`, `022`, `024`, `026`, `028`
  - Missing information checklist: `intake_missing_info_004`, `008`, `012`, `016`, `020`, `024`, `028`
- Some query constraints are broad checklist commands repeated across all items rather than constraints naturally shaped by each individual context. This is acceptable for a template seed set, but weak for a scaled benchmark shard.

Actionable constraint fixes:

- Add `EG6` constraints when the context explicitly states source status, or remove the source-status text from contexts that are not meant to test it.
- Split broad "cover X" constraints into narrower item-specific constraints when the context contains unusual facts, contradictions, or conditional triggers.
- Add constraints for intentional inconsistencies, such as legal name vs entity type, if those inconsistencies remain in the context.

## 6. Per-task final ratings

| Task | Rating | Main reason | Specific item ids |
| --- | --- | --- | --- |
| KYC onboarding | needs review | Strong task fit, but fixed query skeleton, entity-type/name inconsistencies, missing source-status caveats | `intake_kyc_onboarding_001`, `015`, `028`; SEC caveat issue in even-numbered KYC items |
| Client risk profiling | needs review | Good profiling logic, but all items are the same score/classification template | `intake_client_risk_profiling_001`, `015`, `028` |
| Loan application intake | needs review | Good DSCR/checklist task fit, but one repeated skeleton and some purpose-specific document mismatch | `intake_loan_application_001`, `015`, `028` |
| Counterparty / issuer profile construction | needs review | Distinct profile task, but overly centered on leverage risk tier and some synthetic entity/industry incoherence | `intake_counterparty_profile_001`, `015`, `028` |
| Missing information checklist | needs review | Correct checklist task, but highly repetitive stage-gate template and missing source-status caveats | `intake_missing_info_001`, `015`, `028`; SEC caveat issue in `004`, `008`, `012`, `016`, `020`, `024`, `028` |
| Service scope explanation | needs review | Correct client-facing boundary task, but repeated unrealistic client request bundle across services | `intake_service_scope_001`, `015`, `028` |

## 7. Minimum recommended remediation

Before final use, revise about one-third of the shard:

1. For each task, replace 8-10 items with genuinely different work products or context shapes.
2. Keep the balanced 28-per-task distribution.
3. Add at least 3 query skeletons per task rather than 1.
4. Fix synthetic coherence issues: legal suffix vs entity type, industry vs company name, purpose vs required documents.
5. Add explicit `EG6` source-status constraints for non-binding SEC staff-source contexts, or remove those caveats from the source text.
6. Make case-type-specific requirements sharper, especially for loan intake, missing-information checklist, and service-scope explanation.

Bottom line: **distribution passes; task-level identity passes; subtype coverage needs review.**
