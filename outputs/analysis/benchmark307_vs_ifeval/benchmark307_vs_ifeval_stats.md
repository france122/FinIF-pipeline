# benchmark307 / FinIF-test Data Statistics

## Core comparison

- FinIF-test (`benchmark307`) items: 307
- IFEval items: 541
- FinIF-test full_prompt words: mean 680.4625, median 506, min 380, max 2184
- IFEval prompt words: mean 37.0702, median 34, min 9, max 294
- FinIF-test full_prompt chars: mean 4731.8958, median 3543, min 2644, max 15435
- IFEval prompt chars: mean 210.7505, median 191, min 53, max 1858
- FinIF-test / IFEval mean word-length ratio: 18.3561
- FinIF-test / IFEval median word-length ratio: 14.8824
- FinIF-test IF constraints per item: mean 10.6906, median 11, min 7, max 16
- IFEval constraints per item: mean 1.5416, median 1, min 1, max 3
- FinIF-test / IFEval mean constraint ratio: 6.9347

## FinIF-test structure

- Source materials per item: mean 2.8762, median 3, min 2, max 4
- Source-material words per item: mean 320.759, median 133, min 61, max 1822
- Query-only words: mean 257.2573, median 257, min 215, max 318
- LLM constraints per item: mean 6.127
- Rule constraints per item: mean 4.5635
- Format constraints per item: mean 4.7394
- Semantic constraints per item: mean 5.9511
- Items with public excerpt overlay: 94 / 307 (30.62%)
- Workflow coverage: 5 workflows
- Task coverage: 38 task types

## Workflow counts

- Execution, Monitoring, Reporting, and Operations: 62
- Risk and Compliance Review: 62
- Intake and Profiling: 61
- Research and Due Diligence: 61
- Decision and Structuring: 61

## Workflow means

- Execution, Monitoring, Reporting, and Operations: mean prompt words 459.5484, mean IF constraints 9.8387, mean source docs 2.5484
- Risk and Compliance Review: mean prompt words 814.9032, mean IF constraints 10.8871, mean source docs 3.1452
- Intake and Profiling: mean prompt words 941.377, mean IF constraints 11.2459, mean source docs 2.9508
- Research and Due Diligence: mean prompt words 584.6885, mean IF constraints 10.9508, mean source docs 2.7377
- Decision and Structuring: mean prompt words 603.2131, mean IF constraints 10.541, mean source docs 3

## Top task counts

- AML red-flag review: 11
- Client risk profiling: 11
- Service scope explanation: 11
- Loan application intake: 10
- Earnings review: 10
- KYC onboarding: 10
- Counterparty / issuer profile construction: 10
- Investment due diligence: 10
- Missing information checklist: 9
- Industry and market research: 9
- Background screening: 9
- Credit due diligence: 9
- Sales-script / communication compliance: 8
- Underwriting memo: 8
- Credit memo drafting: 8

## Constraint family counts

- Evidence and Grounding: 675
- Decision and Boundary: 746
- Quantitative Verification: 398
- Format and Presentation: 1455
- Required Content Coverage: 8

## Top constraint tags

- FP3: 526
- FP6: 312
- FP4: 310
- EG2: 308
- DB9: 307
- QV2: 287
- FP2: 239
- EG1: 199
- DB4: 147
- DB7: 126
- EG5: 115
- DB6: 70
- FP1: 68
- QV6: 44
- QV5: 43
- DB8: 40
- EG3: 35
- DB1: 25
- DB2: 21
- EG4: 17
