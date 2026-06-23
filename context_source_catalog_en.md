# English Context Source Catalog for FinIF

Date: 2026-06-04

## Purpose

This file starts the context-sourcing phase for FinIF.

It follows the pipeline defined in [task_workflow_final.md](D:/Documents/Codex/2026-06-04/o-net/outputs/task_workflow_final.md):

```text
workflow + task + deliverable
-> select / synthesize context
-> write query
-> extract constraints from context + query
-> build protocol
```

This catalog is not yet a full benchmark dataset. It is a sourcing artifact that identifies:

- which English context documents can be sourced from public primary materials,
- which task families they support,
- which parts still need synthetic documents because they would normally contain private or institution-internal data.

## Source Selection Rules

- Prefer primary public sources.
- Prefer official agency, regulator, exchange, or SEC filing pages.
- Use public company filings for research, diligence, and valuation tasks.
- Keep customer-specific, borrower-specific, and account-specific materials synthetic.
- Build mixed context packs whenever a realistic task needs both public reference material and synthetic private records.

## Recommended Pilot Coverage

This first sourcing pass covers 8 context bundles across the 5 workflow stages:

1. KYC onboarding
2. Loan application intake
3. Public company financial statement analysis
4. Credit due diligence / underwriting
5. Investment memo / valuation
6. Suitability review
7. AML red-flag review
8. Trade confirmation / reconciliation

## Bundle 1

**Workflow:** Intake and Profiling  
**Task:** KYC onboarding  
**Work product:** KYC review note  
**Source mode:** Mixed

**Public source documents**

1. FinCEN, `CDD Final Rule`
   URL: https://www.fincen.gov/index.php/resources/statutes-and-regulations/cdd-final-rule
   Use: beneficial ownership and legal-entity customer due diligence requirements.

2. SEC, `Anti-Money Laundering (AML) Source Tool for Broker-Dealers`
   URL: https://www.sec.gov/about/divisions-offices/division-trading-markets/broker-dealers/anti-money-laundering-aml-source-tool-broker-dealers
   Use: customer identification program requirements and account-opening controls.

3. IRS, `Form W-9`
   URL: https://www.irs.gov/forms-pubs/about-form-w-9
   PDF: https://www.irs.gov/pub/irs-pdf/fw9.pdf
   Use: TIN collection and requester-side onboarding documentation.

**Synthetic documents still needed**

- customer intake form
- beneficial ownership declaration
- sanctions screening result
- PEP screening result
- adverse media summary
- proof of address

**Why this bundle matters**

This bundle supports tasks where the model must determine whether account opening materials are complete, what is missing, and whether the customer should be escalated for enhanced review.

**Likely context-triggered constraints**

- identify missing beneficial ownership information
- do not mark KYC complete without required identity fields
- escalate if screening results indicate unresolved high-risk issues

## Bundle 2

**Workflow:** Intake and Profiling  
**Task:** Loan application intake  
**Work product:** missing-document checklist  
**Source mode:** Mixed

**Public source documents**

1. SBA, `Borrower Information Form (SBA Form 1919)`
   URL: https://www.sba.gov/document/sba-form-1919-borrower-information-form
   PDF: https://catweb2.sba.gov/library/pdf/Form1919_Borrower_Information.pdf
   Use: borrower identity, ownership, indebtedness, and background fields.

2. SBA, `Application submission`
   URL: https://www.sba.gov/about-sba/sba-locations/loan-guaranty-centers/loan-guaranty-processing-center-citrus-heights-ca-hazard-ky/application-submission
   Use: required submission artifacts and lender-side checklist references.

**Synthetic documents still needed**

- borrower financial statements
- tax returns
- debt schedule
- collateral description
- employment or revenue verification
- lender-specific intake checklist

**Why this bundle matters**

This bundle supports tasks where the model must review an incoming loan package and determine whether it is ready for underwriting.

**Likely context-triggered constraints**

- distinguish required from optional missing items
- do not move the file forward if core borrower identity or indebtedness data are missing
- ask only necessary follow-up questions

## Bundle 3

**Workflow:** Research and Due Diligence  
**Task:** Financial statement analysis  
**Work product:** financial analysis summary  
**Source mode:** Public

**Public source documents**

1. SEC, `Apple Inc. 2024 Form 10-K`
   URL: https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm
   Use: audited financial statements, segment information, risk factors, management discussion.

2. FRED, `DGS10 - 10-Year Treasury Constant Maturity Rate`
   URL: https://fred.stlouisfed.org/series/DGS10
   Use: macro rate reference for valuation and market context.

3. FRED, `EFFR - Effective Federal Funds Rate`
   URL: https://fred.stlouisfed.org/series/EFFR
   Use: short-rate context for market environment.

**Synthetic documents still needed**

- competitor benchmark table
- analyst-style summary sheet
- management interview notes

**Why this bundle matters**

This bundle supports research tasks that require extracting trends from public financials and relating them to a macro backdrop without depending on private customer data.

**Likely context-triggered constraints**

- use only disclosed figures from the filing
- separate reported facts from analyst interpretation
- flag when the context does not support a stronger conclusion

## Bundle 4

**Workflow:** Research and Due Diligence  
**Task:** Credit due diligence / underwriting support  
**Work product:** due diligence checklist or underwriting note  
**Source mode:** Mixed

**Public source documents**

1. OCC, `Underwriting`
   URL: https://occ.treas.gov/topics/supervision-and-examination/credit/commercial-credit/underwriting.html
   Use: underwriting dimensions such as financial and collateral requirements, repayment programs, maturities, pricing, and covenants.

2. FDIC, `Commercial Real Estate Lending`
   URL: https://www.fdic.gov/credit/commercial-real-estate-lending
   Use: prudent underwriting discipline, credit administration, and CRE risk management references.

3. OCC, `Comptroller's Handbook: Commercial Real Estate Lending`
   URL: https://www.occ.treas.gov/publications-and-resources/publications/comptrollers-handbook/files/commercial-real-estate-lending/index-commercial-real-estate-lending.html
   Use: fuller supervisory language for CRE underwriting and risk review.

**Synthetic documents still needed**

- borrower financial statements
- rent roll or property cash flow
- collateral appraisal
- covenant schedule
- guarantor information
- internal approval authority matrix

**Why this bundle matters**

This bundle supports realistic underwriting tasks while keeping borrower-specific records synthetic and controllable.

**Likely context-triggered constraints**

- identify missing collateral support
- compute and check required ratios when data are present
- escalate when requested credit exceeds delegated authority

## Bundle 5

**Workflow:** Decision and Structuring  
**Task:** Investment memo / valuation  
**Work product:** investment memo or valuation summary  
**Source mode:** Public + Synthetic

**Public source documents**

1. SEC, `Apple Inc. 2024 Form 10-K`
   URL: https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm

2. FRED, `DGS10 - 10-Year Treasury Constant Maturity Rate`
   URL: https://fred.stlouisfed.org/series/DGS10

3. FRED, `EFFR - Effective Federal Funds Rate`
   URL: https://fred.stlouisfed.org/series/EFFR

**Synthetic documents still needed**

- normalized forecast assumptions
- comparable company table
- DCF worksheet
- investment committee template
- risk factor summary sheet

**Why this bundle matters**

The public materials provide the factual base, while synthetic modeling sheets provide the controllable assumptions needed for valuation, recommendation, and sensitivity tasks.

**Likely context-triggered constraints**

- separate facts, assumptions, and recommendation
- show which conclusions depend on synthetic valuation assumptions
- avoid unsupported certainty if assumptions are sparse or conflicting

## Bundle 6

**Workflow:** Risk and Compliance Review  
**Task:** Suitability review  
**Work product:** suitability review note  
**Source mode:** Mixed

**Public source documents**

1. FINRA, `Suitability`
   URL: https://www.finra.org/rules-guidance/key-topics/suitability
   Use: customer investment profile factors and suitability framing.

2. FINRA, `Rule 2111`
   URL: https://www.finra.org/rules-guidance/rulebooks/finra-rules/2111
   Use: rule text and suitability obligations.

3. SEC, `Regulation Best Interest`
   URL: https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/regulation-best-interest
   Use: broker-dealer recommendation obligations for retail customers.

4. Investor.gov, `Updated Investor Bulletin: Leveraged and Inverse ETFs`
   URL: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec
   Use: product-risk context for leveraged ETF suitability scenarios.

**Synthetic documents still needed**

- client risk profile
- holdings report
- proposed trade request
- product risk rating table
- disclosure delivery log

**Why this bundle matters**

This bundle supports cases where the model must decide whether a recommendation matches a client profile and whether escalation or additional disclosure is required.

**Likely context-triggered constraints**

- identify suitability conflict between client profile and product risk
- do not recommend proceeding when the record is incomplete
- distinguish product features from recommendation language

## Bundle 7

**Workflow:** Risk and Compliance Review  
**Task:** AML red-flag review  
**Work product:** compliance escalation report  
**Source mode:** Mixed

**Public source documents**

1. FinCEN, `Frequently Asked Questions Regarding the FinCEN Suspicious Activity Report (SAR)`
   URL: https://www.fincen.gov/index.php/frequently-asked-questions-regarding-fincen-suspicious-activity-report-sar
   Use: SAR expectations, process, and reporting context.

2. FinCEN, `Suspicious Activity Report Supporting Documentation`
   URL: https://www.fincen.gov/resources/statutes-regulations/guidance/suspicious-activity-report-supporting-documentation
   Use: supporting documentation and retention expectations.

3. FinCEN, `CDD Final Rule`
   URL: https://www.fincen.gov/index.php/resources/statutes-and-regulations/cdd-final-rule
   Use: customer due diligence baseline for account-level AML scenarios.

4. SEC, `AML Source Tool for Broker-Dealers`
   URL: https://www.sec.gov/about/divisions-offices/division-trading-markets/broker-dealers/anti-money-laundering-aml-source-tool-broker-dealers
   Use: broker-dealer AML program references.

**Synthetic documents still needed**

- transaction monitoring alert
- customer transaction history
- sanctions screening result
- internal case narrative
- customer due diligence file

**Why this bundle matters**

The public materials define the reporting and documentation environment, while the suspicious activity itself should be synthetic so that red flags, severity, and escalation conditions are fully controllable.

**Likely context-triggered constraints**

- cite evidence for each red flag
- distinguish suspicious indicators from confirmed wrongdoing
- escalate unresolved high-risk activity

## Bundle 8

**Workflow:** Execution, Monitoring, Reporting, and Operations  
**Task:** Trade confirmation / reconciliation  
**Work product:** reconciliation exception report  
**Source mode:** Mixed

**Public source documents**

1. FINRA, `Customer Confirmations (Rule 2232)`
   URL: https://www.finra.org/rules-guidance/rulebooks/finra-rules/2232
   Use: fields expected in customer trade confirmations.

2. FINRA, `Are You Checking Your Trade Confirmations?`
   URL: https://www.finra.org/investors/insights/checking-trade-confirmations
   Use: practical confirmation details such as date, price, quantity, and execution details.

3. SEC, `Books and Records Requirements for Brokers and Dealers`
   URL: https://www.sec.gov/file/final-rule-rel-no-34-44992
   Use: order ticket and account record expectations.

4. SEC, `Account Statement Rule` overview in investor-protection release
   URL: https://www.sec.gov/newsroom/press-releases/2013-141
   Use: quarterly account statement expectations and customer-protection framing.

**Synthetic documents still needed**

- trade blotter
- custodian statement
- cash ledger
- settlement exception log
- operations commentary

**Why this bundle matters**

This bundle supports reconciliation, settlement exception, and trade-confirmation cross-check tasks that are highly objective and useful for protocol-driven evaluation.

**Likely context-triggered constraints**

- reconcile price, quantity, and settlement fields across records
- flag unmatched transactions or balances
- do not mark the account reconciled if there is a numeric difference

## Suggested Next Build Step

The next concrete step should be to turn these bundles into 5-10 pilot `context_pack` instances, one or two per workflow, with:

- public reference documents linked here,
- synthetic private documents created locally,
- a chosen work product,
- a query,
- extracted constraints,
- and a draft evaluation protocol.

## Pilot Priority Order

If we want the fastest path to usable pilot items, build these first:

1. `AML red-flag review`
2. `Credit memo drafting`
3. `Suitability review`
4. `Reconciliation`
5. `KYC onboarding`

These five cover the best mix of long context, policy triggers, structured outputs, and objectively checkable behavior.
