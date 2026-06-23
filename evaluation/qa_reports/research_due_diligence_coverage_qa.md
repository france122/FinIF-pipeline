# Research and Due Diligence Shard Coverage QA

Date: 2026-06-10

Reviewed file:

- `/Users/minimax/Desktop/lunwen/outputs/full_prompts/scaled_shards/research_due_diligence_full_prompts.jsonl`

Reference files:

- `/Users/minimax/Desktop/lunwen/task_workflow_final.md`
- `/Users/minimax/Desktop/lunwen/constraint_taxonomy_v2.md`

## Executive judgment

Overall judgment: **needs review / partial fail for coverage diversity**.

The shard has the correct top-level task distribution, but it does **not** convincingly demonstrate varied coverage within each Research and Due Diligence task type. After normalizing away company names, dollar amounts, and market labels, each of the 7 task buckets has exactly **1 query skeleton** and exactly **1 extracted-constraint skeleton** across all 28 items. This is strong evidence of template reuse.

The most severe quality issue is not just repeated wording. Several tasks include context documents that are irrelevant to the target company or market, especially Apple/Microsoft excerpts inserted beside synthetic company packs. In some cases, the target company and requested market are mismatched, making the sample look like a stitched template rather than a realistic due diligence task.

## 1. Task distribution

Distribution check: **pass**.

| Task | Count | Expected | Result |
| --- | ---: | ---: | --- |
| Background screening | 28 | 28 | pass |
| Credit due diligence | 28 | 28 | pass |
| Due diligence checklist completion | 28 | 28 | pass |
| Earnings review | 28 | 28 | pass |
| Financial statement analysis | 28 | 28 | pass |
| Industry and market research | 28 | 28 | pass |
| Investment due diligence | 28 | 28 | pass |

Total: 196 items.

## 2. Cross-task coverage and templating findings

### Finding A: one query template per task

For every task, all 28 queries collapse to one skeleton after removing company names, amounts, and market names.

| Task | Unique normalized query skeletons | Unique normalized constraint sets | QA impact |
| --- | ---: | ---: | --- |
| Financial statement analysis | 1 | 1 | Template-heavy |
| Industry and market research | 1 | 1 | Template-heavy plus mismatches |
| Earnings review | 1 | 1 | Template-heavy |
| Credit due diligence | 1 | 1 | Template-heavy |
| Investment due diligence | 1 | 1 | Template-heavy plus irrelevant public docs |
| Background screening | 1 | 1 | Template-heavy |
| Due diligence checklist completion | 1 | 1 | Template-heavy |

Action: For each task, keep at most 8-10 samples from the current template and regenerate the rest with materially different work products, source mixes, output formats, and decision logic.

### Finding B: irrelevant public-company excerpts are repeatedly inserted

Affected item ranges:

- `research_due_diligence_financial_statement_analysis_01` through `_28`: all include an Apple 2024 Form 10-K excerpt, while the query asks for a synthetic target-company analysis.
- `research_due_diligence_earnings_review_01` through `_28`: all include an Apple Q1 2025 Form 10-Q excerpt, while the query asks for a synthetic target-company earnings review.
- `research_due_diligence_industry_market_research_01` through `_28`: all include a Microsoft 2024 Form 10-K excerpt, often not clearly tied to the requested market.
- `research_due_diligence_investment_due_diligence_01` through `_28`: all include either Microsoft or Apple excerpts, often generic and weakly connected to the target investment.

Action: Either make the public-company excerpt explicitly relevant in the query, e.g. "compare the target to the Apple/Microsoft excerpt as a benchmark," or remove it. As written, it mainly creates noise and context/query mismatch risk.

### Finding C: constraints are mostly explicit, but too uniform

Most extracted constraints are explicit in query/context and compatible with `constraint_taxonomy_v2.md`. The issue is not hidden or invented constraints; it is repeated constraint design.

Examples:

- `RC1`, `EG1`, and `EG2` appear in all 196 items.
- Each task has the same constraint set across all 28 items after company normalization.
- Repeated generic requirements such as "use only supplied documents" and "cite DOC IDs" are valid, but they do not create meaningful task-type coverage by themselves.

Action: Add task-specific explicit constraints that vary naturally with the context, such as different thresholds, different missing-evidence rules, different required outputs, and different decision categories.

## 3. Per-task sampled QA

Sampled items: `_01`, `_14`, and `_28` for each task.

### Financial statement analysis

Sampled item ids:

- `research_due_diligence_financial_statement_analysis_01`
- `research_due_diligence_financial_statement_analysis_14`
- `research_due_diligence_financial_statement_analysis_28`

Quality judgment: **needs review**.

What works:

- The work product is appropriate: financial analysis summary.
- Query asks for relevant calculations: revenue growth, gross margin, current ratio, debt-to-equity, operating-cash-flow conversion.
- Constraints are explicit and checkable.

Problems:

- All 28 items use the same query and constraint structure.
- All sampled items include an Apple excerpt that is not integrated into the task. The query asks for Apex/Meadow/Horizon analysis, but does not ask for Apple benchmarking or comparison.
- The synthetic company packs vary numbers and company names, but not the analytical situation.

Concrete examples:

- `_01`: Apple segment sales excerpt appears beside Apex Robotics financial pack, but query only asks for Apex analysis.
- `_14`: Apple gross margin excerpt appears beside Meadow Home Goods financial pack, again without a requested benchmark use.
- `_28`: Apple segment excerpt appears beside Horizon Specialty Finance, with no clear relevance to specialty finance.

Recommended fix:

- Split this bucket into at least 4 subpatterns: profitability bridge, liquidity/working-capital review, segment trend analysis, covenant-style ratio analysis.
- If Apple excerpts remain, explicitly require peer/benchmark comparison; otherwise remove them.

### Industry and market research

Sampled item ids:

- `research_due_diligence_industry_market_research_01`
- `research_due_diligence_industry_market_research_14`
- `research_due_diligence_industry_market_research_28`

Quality judgment: **fail**.

What works:

- The requested work product, market context note, is in-scope for the task.
- The query includes market drivers, rate sensitivity, input costs, and boundary language.

Problems:

- Company-market pairings are often implausible or unexplained.
- Microsoft excerpts are generic and not consistently relevant to the requested target company or market.
- All 28 items use the same query and constraint structure.

Concrete examples:

- `_01`: Apex Robotics Components is assigned to the consumer devices market without explanation.
- `_14`: Meadow Home Goods is assigned to the cloud infrastructure market, a clear context/query mismatch.
- `_28`: Horizon Specialty Finance is assigned to the cloud infrastructure market, again without a bridge explaining why this finance company belongs in that market.

Recommended fix:

- Regenerate this bucket around coherent industry-target pairings.
- Add distinct market research variants: TAM trend note, competitor benchmark, macro sensitivity note, commodity/input-cost brief, rate-cycle impact note.
- Make any Microsoft excerpt a real benchmark/comparable, or remove it.

### Earnings review

Sampled item ids:

- `research_due_diligence_earnings_review_01`
- `research_due_diligence_earnings_review_14`
- `research_due_diligence_earnings_review_28`

Quality judgment: **needs review**.

What works:

- The work product is appropriate: earnings review note.
- Query requires sections, recalculations, fact/commentary separation, and watch items.
- Context includes synthetic earnings release data that supports the task.

Problems:

- Apple 10-Q excerpts are included in all sampled items but are not used by the query.
- Query skeleton and constraints are identical across all 28 items.
- Some generated numeric formatting is rough, e.g. `_28` has `212.60000000000002 million`, which is a data-quality smell.

Concrete examples:

- `_01`: Apple Q1 income statement plus Apex synthetic earnings release; no query instruction to compare Apex with Apple.
- `_14`: Apple product/services excerpt plus Meadow Home Goods release; no relevance bridge.
- `_28`: Horizon Specialty Finance release includes floating-point artifact `212.60000000000002`.

Recommended fix:

- Remove unrelated Apple excerpts, or make them explicit peer benchmarks.
- Add varied earnings tasks: margin bridge, guidance revision analysis, segment/product mix review, analyst Q&A issue extraction.
- Round generated figures before writing JSONL.

### Credit due diligence

Sampled item ids:

- `research_due_diligence_credit_due_diligence_01`
- `research_due_diligence_credit_due_diligence_14`
- `research_due_diligence_credit_due_diligence_28`

Quality judgment: **needs review**.

What works:

- Strong task fit: borrower pack, collateral/debt schedule, policy excerpt, proposed exposure, DSCR/debt-to-EBITDA/collateral coverage, proceed/hold/decline decision.
- Constraints are explicit and checkable.

Problems:

- All 28 items use the same structure: same calculations, same policy thresholds, same missing February bank statement, lien release, and environmental report pattern.
- It covers one flavor of credit due diligence, not the task breadth described in the workflow taxonomy.

Concrete examples:

- `_01`, `_14`, `_28`: all ask for DSCR, debt-to-EBITDA, collateral coverage, underwriting/hold/decline, diligence gaps, escalation triggers, and closing evidence.

Recommended fix:

- Keep some examples, but add variants: unsecured borrower review, borrowing-base diligence, CRE collateral review, covenant-heavy review, guarantor support review, credit history/default review.
- Vary missing documents and threshold triggers rather than repeating the same gap set.

### Investment due diligence

Sampled item ids:

- `research_due_diligence_investment_due_diligence_01`
- `research_due_diligence_investment_due_diligence_14`
- `research_due_diligence_investment_due_diligence_28`

Quality judgment: **needs review**.

What works:

- The requested memo and core sections fit investment due diligence.
- It includes thesis, evidence, valuation scenarios, risks, diligence questions, assumptions, and boundary language.

Problems:

- All 28 items use the same memo skeleton and risk set.
- Apple/Microsoft excerpts are weakly connected or irrelevant unless framed as comparables.
- The investment thesis is repeated across targets: expand recurring revenue, reduce churn, improve procurement savings.

Concrete examples:

- `_01`: Microsoft competition risk excerpt plus Apex investment data sheet; possible relevance, but the query does not ask for public-company risk benchmarking.
- `_14`: Apple product/services excerpt plus Meadow Home Goods investment data sheet; relevance is weak.
- `_28`: Apple product/services excerpt plus Horizon Specialty Finance; relevance is weak.

Recommended fix:

- Add investment variants: fund diligence, bond/security diligence, project investment diligence, management interview issue log, term sheet risk review.
- Vary thesis and risk drivers by company/sector.
- If public filings are used, require explicit benchmark or comparable-company evidence mapping.

### Background screening

Sampled item ids:

- `research_due_diligence_background_screening_01`
- `research_due_diligence_background_screening_14`
- `research_due_diligence_background_screening_28`

Quality judgment: **needs review**.

What works:

- Context/query/work_product are aligned.
- The task covers screening results, unresolved matches, confirmed records, open questions, classification, and legal-boundary language.
- Constraints are explicit and suitable.

Problems:

- All 28 items use the same entity/executive/director structure, same screening categories, same classification choices, and same memo requirements.
- The samples differ mainly by company name and dates of regulatory action.

Concrete examples:

- `_01`, `_14`, `_28`: all ask for Low/Medium/High/Unresolved classification, hit table, follow-up evidence, and boundary statement.

Recommended fix:

- Add variants: management-only screening, issuer adverse media screening, sanctions-name similarity resolution, PEP exposure review, litigation/regulatory history memo.
- Vary the required output, e.g. escalation note, screening disposition log, unresolved-hit workpaper.

### Due diligence checklist completion

Sampled item ids:

- `research_due_diligence_due_diligence_checklist_completion_01`
- `research_due_diligence_due_diligence_checklist_completion_14`
- `research_due_diligence_due_diligence_checklist_completion_28`

Quality judgment: **needs review**.

What works:

- This is clearly in-scope for due diligence checklist completion.
- The data room index, request tracker, and completion standard are coherent.
- The status taxonomy and blocker rules are explicit.

Problems:

- All 28 items use the same checklist matrix query and same completion standard.
- Repeated evidence pattern: audited financials, interim accounts, cap table, customer list, material contracts, tax certificate, cyber insurance, litigation summary, environmental report, lien release, board approval.
- The only meaningful variation is company name and a few expiry/availability details.

Concrete examples:

- `_01`, `_14`, `_28`: all require item/evidence/status/rationale/owner/next action plus phase-gate readiness conclusion.

Recommended fix:

- Add variants: seller data-room readiness, regulatory diligence checklist, credit closing checklist, fund operational diligence checklist, missing-evidence escalation tracker.
- Vary standards and required statuses across subsets instead of repeating one phase-gate rulebook.

## 4. Required remediation before accepting shard

1. Preserve the 7 x 28 distribution, but regenerate at least half of each task bucket with distinct task-specific scenarios.
2. Remove or explicitly operationalize unrelated Apple/Microsoft excerpts.
3. Fix incoherent company-market pairings in Industry and market research.
4. Add intra-task diversity in work products, not just company names.
5. Vary explicit constraints naturally: sections, thresholds, decisions, evidence handling, calculation types, missing-info rules, and boundary statements.
6. Run a duplicate-skeleton check before final acceptance. Target: each 28-item task bucket should have at least 4-5 materially different normalized query skeletons and constraint skeletons.

## 5. Bottom line

The shard is balanced by count and generally uses explicit constraints, but it does **not** yet meet the intended coverage standard. It is mostly a collection of seven templates expanded to 28 company-name variants each. The most urgent fixes are the Industry and market research mismatches, the irrelevant Apple/Microsoft context documents, and the lack of intra-task scenario diversity.
