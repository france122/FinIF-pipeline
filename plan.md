# Finance Instruction-Following Benchmark Plan

## Core Workflow

The benchmark is organized around the following chain:

```text
occupation -> task -> work product -> financial constraints -> evaluation rules
```

Synthetic data generation should follow:

```text
task -> context -> query -> constraint -> protocol
```

The key design choice is to use O*NET occupations and tasks as seeds, but rewrite them into finance workflow task types. A task should be neither as broad as "do credit analysis" nor as narrow as a single O*NET sentence. It should describe a reusable work operation performed by a specific occupation to produce a specific work product.

## Recommended Task System

Use:

```text
occupation x atomic task type x work product
```

Recommended v1 scale:

- 12 finance-related occupations
- 100-140 reusable task types
- 450-700 benchmark items after synthesis

Each task type can be expanded into 4-6 concrete samples with varied context length, financial constraints, query form, and scoring protocol.

## Priority Occupations

### Core Occupations

These should receive denser coverage, around 12 task types each:

- Credit Analysts
- Loan Officers
- Financial and Investment Analysts
- Financial Risk Specialists
- Financial Examiners
- Securities, Commodities, and Financial Services Sales Agents

### Supplementary Occupations

These should receive lighter coverage, around 6-8 task types each:

- Personal Financial Advisors
- Accountants and Auditors
- Tax Preparers
- Financial Quantitative Analysts
- Financial Managers
- Compliance Officers / AML-KYC related roles

Approximate task type count:

- Core occupations: 6 x 12 = 72 task types
- Supplementary occupations: 6 x 7 = 42 task types
- Total: about 110-120 task types

## Task Categories

Each occupation should draw from 3-5 of these categories:

| Task category | Typical work product | Benchmark value |
| --- | --- | --- |
| Information extraction and filing | Client profile, risk profile, field checklist | Tests long-context retrieval and output formatting |
| Rule matching and eligibility judgment | Approval decision, compliance checklist, exception note | Tests multi-constraint reasoning and policy priority |
| Calculation and verification | Ratio table, cash-flow model, tax/risk metric | Tests numerical accuracy and auditability |
| Analysis and recommendation | Investment memo, credit recommendation, risk report | Tests separation of facts, assumptions, and recommendations |
| Exception and anomaly detection | Audit finding, suspicious activity note, missing-item list | Tests evidence grounding and conservative judgment |
| Client communication | Client email, explanation letter, meeting summary | Tests compliant language, tone, and prohibited claims |
| Internal reporting | Approval summary, management briefing, regulatory response | Tests compression, structure, and role constraints |
| Pre-execution operational check | Trade confirmation, loan submission checklist, escalation decision | Tests workflow adherence and safe refusal |

## Task Definition Template

```yaml
occupation: Credit Analyst
task_type: Assess borrower creditworthiness from a multi-document loan package
work_product: Internal credit memo
context_sources:
  - loan application
  - borrower financial statements
  - bank statements
  - credit report
  - collateral appraisal
  - lending policy excerpt
query_type:
  - approve / reject / escalate recommendation
financial_constraints:
  - use only provided documents
  - cite evidence for each risk factor
  - calculate DTI and LTV
  - do not promise approval
  - flag missing or inconsistent information
evaluation_rules:
  - numerical correctness
  - evidence grounding
  - policy compliance
  - format compliance
  - appropriate uncertainty / escalation
```

## Design Principle

Use O*NET occupations as the occupation pool and O*NET tasks as task seeds, but convert them into finance workflow task types centered on work products. This makes the later generation chain more controllable:

```text
task -> context -> query -> constraint -> protocol
```

The benchmark should measure whether a model can follow instructions under realistic financial workflow constraints, especially when the relevant evidence is embedded in long, heterogeneous context.
