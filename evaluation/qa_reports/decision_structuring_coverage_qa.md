# Decision and Structuring Coverage QA

## Scope

Reviewed shard:

- `/Users/minimax/Desktop/lunwen/outputs/full_prompts/scaled_shards/decision_structuring_full_prompts.jsonl`

Reference files:

- `/Users/minimax/Desktop/lunwen/task_workflow_final.md`
- `/Users/minimax/Desktop/lunwen/constraint_taxonomy_v2.md`

This QA checks whether the shard covers the eight `Decision and Structuring` task types as real subtask variants, not only as parameterized prompt templates.

## Summary Finding

Distribution is correct, but coverage quality is weak. The shard contains 224 items and each of the 8 tasks has 28 items. However, most tasks use one fixed query/work-product pattern repeated across 7 names or entities, usually 4 variants per name. Contexts often differ in numbers or missing items, but the user work requested is usually the same. This means the shard is closer to "template with substituted borrower/security/client" than broad coverage of each task type.

Overall QA result: **needs review**, with one task-level **fail** for DCF valuation / pricing analysis due to a repeated realism/task-fit problem.

## Task Distribution

| Task | Count | Expected | Distribution result |
|---|---:|---:|---|
| Credit memo drafting | 28 | 28 | pass |
| Underwriting memo | 28 | 28 | pass |
| Loan approval package | 28 | 28 | pass |
| DCF valuation / pricing analysis | 28 | 28 | pass |
| Investment memo | 28 | 28 | pass |
| Capital structure / financing proposal | 28 | 28 | pass |
| Portfolio proposal | 28 | 28 | pass |
| Trade order ticket preparation | 28 | 28 | pass |

## Repetition / Template Signals

| Task | Unique query texts | Unique normalized query skeletons | Unique constraint sets | QA implication |
|---|---:|---:|---:|---|
| Credit memo drafting | 7 | 1 | 8 | Same memo request repeated across 7 borrowers; task fit is fine, but coverage is shallow. |
| Underwriting memo | 28 | 1 | 4 | Query varies mainly by applicant / owner percentage / missing item; all are SBA underwriting support memos. |
| Loan approval package | 7 | 1 | 1 | One checklist template repeated across borrowers. |
| DCF valuation / pricing analysis | 7 | 2 | 1 | One DCF/pricing template repeated; many items apply corporate DCF mechanics to ETFs/model sleeve. |
| Investment memo | 28 | 2 | 8 | Better than most because sizing/limit values vary, but still one IC memo structure. |
| Capital structure / financing proposal | 7 | 1 | 1 | One three-option financing comparison repeated across companies. |
| Portfolio proposal | 7 | 1 | 1 | One allocation drift/rebalance proposal repeated across client labels. |
| Trade order ticket preparation | 1 | 1 | 1 | All 28 use exactly the same query and constraint set. Context values vary, but the work product does not. |

Note: `full_prompt` and `context` hashes are unique for all 224 items, so these are not byte-for-byte duplicate full prompts. The problem is semantic coverage, not exact duplication.

## Sample Review

Three items were reviewed for each task: first, midpoint, and last item within the task block.

| Task | Sampled item IDs | Context/query/work product fit | Main QA notes |
|---|---|---|---|
| Credit memo drafting | `decision_structuring_credit_memo_drafting_001`, `015`, `028` | Fits. Context gives borrower request, DSCR/LTV inputs, policy thresholds, collateral, approval matrix. Query requests an internal credit memo. | Needs review because the query skeleton is identical across the task. Items `001` and `015` even use the same borrower name and same query text, with only hidden context values changing. Add different credit memo scenarios: renewal, covenant waiver, criticized credit, collateral shortfall, guarantor weakness, sponsor support, downgrade/upgrade recommendation. |
| Underwriting memo | `decision_structuring_underwriting_memo_001`, `015`, `028` | Fits for SBA underwriting. Context includes SBA Form 1920 excerpts, guarantor threshold, construction/renovation trigger, DSCR/equity inputs. | Needs review because all sampled items are SBA 7(a)-style underwriting support memos. This does not cover the broader task definition: loan, insurance, securities, or project finance underwriting. Add non-SBA examples and change the analytical frame, not only applicant values. |
| Loan approval package | `decision_structuring_loan_approval_package_001`, `015`, `028` | Fits. Context includes package intake, standard columns, source/use reconciliation, missing evidence. | Needs review because all items ask for the same checklist table with the same readiness classification. Constraint set is identical across all 28. Add approval packages with authority matrix questions, guarantor exceptions, covenant packages, collateral perfection, regulatory form completeness, and multi-facility structures. |
| DCF valuation / pricing analysis | `decision_structuring_dcf_valuation_pricing_analysis_001`, `015`, `028` | Partially fits. Apple examples fit a corporate DCF summary. `028` gives a synthetic DCF model for Treasury Inflation-Protected Securities ETF and asks for enterprise value/equity value/share value. | Fail for coverage realism. Items for ETFs/model sleeve are forced into corporate issuer DCF. Problem IDs include `003`, `004`, `005`, `007`, `010`, `011`, `012`, `014`, `017`, `018`, `019`, `021`, `024`, `025`, `026`, `028`. Replace these with security-appropriate pricing tasks, e.g. NAV premium/discount, yield/duration scenario, bond price/yield sensitivity, comparable multiples, transaction comps, or keep DCF only for operating companies. |
| Investment memo | `decision_structuring_investment_memo_001`, `015`, `028` | Fits. Context includes thesis notes, risk excerpts, IC standard, sizing/limit comparison. Query asks for IC memo and recommendation. | Needs review. This is one IC memo mold across ETFs, bonds, and equities. It is more varied than loan/checklist tasks because recommendation and sizing values differ, but still undersamples actual investment memo types. Add new structures: initiate/exit/add/trim, manager selection, private investment, watchlist downgrade, tactical allocation, rejection memo, and risk-only memo. |
| Capital structure / financing proposal | `decision_structuring_capital_structure_financing_proposal_001`, `015`, `028` | Fits. Context provides current capitalization, three financing options, covenant levels, maturity/control concerns. | Needs review. All items use the same Option A senior debt / Option B preferred equity / Option C refinancing table and same trade-off list. Add true capital structure variants: refinancing only, debt maturity ladder, rescue financing, equity raise dilution, covenant amendment, asset sale/deleveraging, recapitalization, sponsor vs lender proposal. |
| Portfolio proposal | `decision_structuring_portfolio_proposal_001`, `015`, `028` | Fits. Context has IPS target/current allocations, restrictions, liquidity need, drift policy. Query asks for allocation table and rebalance/hold/no-action recommendation. | Needs review. All items are the same three-asset-class drift calculation and rebalance proposal. Add tax-aware rebalancing, cash-raise proposal, concentrated-stock transition, ESG/restriction conflict, retirement income allocation, risk-tolerance mismatch, model portfolio migration, and IPS exception memo. |
| Trade order ticket preparation | `decision_structuring_trade_order_ticket_preparation_001`, `015`, `028` | Fits the task. Context includes client order message, security master/account restrictions, and order memorandum rule excerpt. Query asks for structured JSON order ticket. | Needs review due to extreme templating: all 28 have exactly one query text and one constraint set. Add different trade tickets: market order, stop/stop-limit, buy vs sell, mutual fund order, bond order, missing quantity, ambiguous account, restricted security, short-sale conflict, discretionary order indicator, cancellation/modification, partial order instructions. |

## Constraint QA

The sampled extracted constraints are mostly explicit under `constraint_taxonomy_v2.md`: format requirements, use-only-provided-documents, document citations, calculations, threshold comparisons, classification/status, and forbidden final-approval/guaranteed-return language are stated in the query or mechanically triggered by context.

No sampled item showed a major case where constraints were entirely invented. The main constraint weakness is repetition:

- `Loan approval package`, `Capital structure / financing proposal`, `Portfolio proposal`, and `Trade order ticket preparation` each have only 1 unique constraint set across 28 items.
- `DCF valuation / pricing analysis` has only 1 unique constraint set despite covering operating companies, ETFs, bond ETFs, and a municipal bond model sleeve.
- Reused constraints are valid locally, but they reinforce the template-skin problem because every item tests the same skills.

## Task-Level Judgments

| Task | Judgment | Concrete item IDs / issue pattern |
|---|---|---|
| Credit memo drafting | needs review | `001`, `015`, `028`; all sampled items use the same memo sections and calculations. Borrowers repeat every 7 items. |
| Underwriting memo | needs review | `001`, `015`, `028`; all sampled items are SBA underwriting memos, not broader underwriting. |
| Loan approval package | needs review | `001`, `015`, `028`; one checklist template and one constraint set across all 28. |
| DCF valuation / pricing analysis | fail | `003`, `004`, `005`, `007`, `010`, `011`, `012`, `014`, `017`, `018`, `019`, `021`, `024`, `025`, `026`, `028` use ETF/model-sleeve entities with corporate DCF-style enterprise/equity value mechanics. |
| Investment memo | needs review | `001`, `015`, `028`; task fit is acceptable, but the IC memo format is nearly fixed. |
| Capital structure / financing proposal | needs review | `001`, `015`, `028`; same three-option comparison repeated across companies. |
| Portfolio proposal | needs review | `001`, `015`, `028`; same allocation drift/rebalance table repeated across clients. |
| Trade order ticket preparation | needs review | `001`, `015`, `028`; all 28 share the exact same query and constraint set. |

## Actionable Recommendations

1. Keep the 8 x 28 distribution, but require at least 4-6 genuinely different scenario archetypes per task.
2. Cap repeated query skeletons. A practical rule: no more than 4 items per task may share the same normalized query skeleton unless the context creates a clearly different reasoning workflow.
3. For every task, vary the requested work product, not only the entity:
   - Credit memo: recommendation memo, exception memo, renewal memo, downgrade memo, covenant-waiver memo.
   - Underwriting memo: SBA, CRE, insurance, project finance, securities issuance, equipment finance.
   - Loan approval package: approval checklist, exception summary, authority routing, missing-evidence cure plan, collateral/guarantor package.
   - DCF/pricing: corporate DCF, comparable multiples, bond pricing/yield, ETF NAV analysis, sensitivity-only note, valuation bridge.
   - Investment memo: buy/add/trim/exit/watchlist/decline, public equity, ETF, bond, private fund, manager/product selection.
   - Capital structure: refinance, recap, amendment, equity raise, preferred/private credit comparison, maturity-wall plan.
   - Portfolio proposal: rebalance, tax-aware transition, IPS exception, cash raise, concentrated position reduction, restriction-aware allocation.
   - Trade order ticket: order entry, clarification hold, cancellation, modification, restricted order, missing-field ticket, fixed income order.
4. Replace or rewrite DCF items for ETFs/model sleeves. If the benchmark wants pricing analysis for funds or fixed income, the query and constraints should test NAV/yield/duration/spread mechanics rather than enterprise value and diluted shares.
5. Add a QA lint before release: report per task unique query count, normalized skeleton count, unique constraint set count, and source-title repetition. Flag any task with only 1-2 skeletons or 1 constraint set across 28 items.

