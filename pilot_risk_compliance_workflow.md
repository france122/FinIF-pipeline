# Pilot Workflow Chain: Risk and Compliance Review

Date: 2026-06-04

## Goal

This file is the first depth-first execution pass for FinIF.

Instead of broadening across all workflows, it focuses on one workflow only:

- `Risk and Compliance Review`

Within this workflow, it selects 3 tasks and pushes each one through the same chain:

```text
task -> work product -> context -> query -> extracted constraints -> protocol
```

The purpose is to prove that the pipeline is executable before we scale coverage.

## Chosen Workflow

`Risk and Compliance Review`

Why this workflow first:

- It naturally supports long and heterogeneous context.
- It has explicit triggers, thresholds, and escalation logic.
- It gives us both objective checks and judgment-heavy outputs.
- It fits the benchmark’s core instruction-following story especially well.

## Task 1

### Task

`AML red-flag review`

### Work Product

Primary:

- `compliance escalation report`

Optional future variant:

- `case review note`

### Context

```yaml
documents:
  - id: DOC1
    type: customer profile
    content: |
      Customer Name: BlueRiver Imports LLC
      Customer Type: Legal entity
      Industry: Consumer electronics wholesale
      Incorporation Country: United States
      Expected Monthly Account Activity: USD 80,000 to USD 120,000
      Expected Geographies: United States and Canada
      Beneficial Owner: Daniel Lee
      Onboarding Risk Rating: Medium
      Notes: Customer stated that most payments would relate to consumer electronics inventory purchases.

  - id: DOC2
    type: transaction monitoring alert
    content: |
      Alert Type: Unusual wire activity
      Review Period: Last 5 business days
      Account Activity Summary:
      - 7 incoming wires totaling USD 640,000
      - 6 outgoing wires totaling USD 618,000
      - 3 outgoing wires sent to a newly added beneficiary in the UAE
      - 4 incoming wires originated from unrelated counterparties not previously seen on the account
      Analyst Note: Activity is materially above expected monthly account activity and shows rapid movement of funds.

  - id: DOC3
    type: sanctions screening result
    content: |
      Screening Subject: Gulf Horizon Trading FZE
      Screening Result: No exact sanctions hit
      Secondary Result: One fuzzy name match to a sanctions-listed entity requires manual review
      Match Confidence: Medium
      Status: Unresolved

  - id: DOC4
    type: AML policy excerpt
    content: |
      Escalation to Compliance Review is required when any of the following are present:
      1. Rapid movement of funds inconsistent with expected customer activity.
      2. Newly added foreign beneficiaries combined with unusual transaction velocity.
      3. Unresolved sanctions or screening matches that cannot be cleared by frontline review.
      Frontline analysts must cite the supporting evidence for each red flag and must distinguish suspicious indicators from confirmed misconduct.
```

### Query

```text
Review the provided materials and prepare a compliance escalation report.
Identify suspicious signals, cite the supporting evidence, and recommend whether the case should be escalated.
Use only the provided materials.
```

### Extracted Constraints

- Output must be a compliance escalation report.
- Use only the provided materials.
- Identify suspicious signals and cite supporting evidence for each.
- Distinguish suspicious indicators from confirmed misconduct.
- Recommend escalation when unresolved high-risk issues are present.

### Protocol

`delivery_quality`

- Must identify that transaction activity is materially above expected levels.
- Must identify rapid movement of funds.
- Must identify the newly added UAE beneficiary as a risk signal.
- Must identify the unresolved fuzzy screening match.
- Must produce a usable escalation rationale rather than a fact list only.

`instruction_adherence`

- Must use only the provided materials.
- Must cite evidence for each red flag.
- Must recommend escalation.
- Must not describe the fuzzy match as a confirmed sanctions hit.

## Task 2

### Task

`Suitability review`

### Work Product

Primary:

- `suitability review note`

Optional future variant:

- `client recommendation hold notice`

### Context

```yaml
documents:
  - id: DOC1
    type: client profile
    content: |
      Client Name: Maria Chen
      Client Classification: Retail
      Investment Objective: Capital preservation with moderate income
      Risk Tolerance: Conservative
      Time Horizon: 3 to 5 years
      Liquidity Need: High
      Investment Experience: Limited experience with mutual funds and investment-grade bond funds
      Concentration Limit: No single position should exceed 15% of investable assets

  - id: DOC2
    type: current holdings summary
    content: |
      Total Investable Assets: USD 800,000
      Current Cash and Short-Term Bonds: 62%
      Investment-Grade Bond Funds: 28%
      Equity Exposure: 10%

  - id: DOC3
    type: proposed trade request
    content: |
      Proposed Product: Leveraged Nasdaq 100 ETF
      Proposed Allocation: USD 180,000
      Proposed Percentage of Investable Assets: 22.5%
      Intended Rationale: Increase upside exposure over the next quarter

  - id: DOC4
    type: product disclosure excerpt
    content: |
      Leveraged ETFs seek daily investment results and may be significantly riskier than traditional ETFs.
      They are generally not designed to achieve their stated objective over periods longer than one day.
      Performance can differ significantly from the underlying index over longer holding periods.

  - id: DOC5
    type: suitability policy excerpt
    content: |
      Recommendations must consider the customer’s risk tolerance, investment objective, liquidity needs, investment experience, and concentration exposure.
      If a proposed product materially conflicts with the customer profile or concentration limits, the case must be escalated or declined rather than recommended as suitable.
```

### Query

```text
Using only the provided materials, prepare a suitability review note.
Assess whether the proposed trade is suitable for the client, explain the main conflicts or supporting factors,
and recommend proceed, escalate, or decline.
```

### Extracted Constraints

- Output must be a suitability review note.
- Use only the provided materials.
- Assess suitability using the client profile and product information.
- Explain the main conflicts or supporting factors.
- Provide a final recommendation of proceed, escalate, or decline.
- Escalate or decline if the proposed trade materially conflicts with the client profile or concentration limits.

### Protocol

`delivery_quality`

- Must identify conflict with conservative risk tolerance.
- Must identify conflict with high liquidity need and short-term leveraged product behavior.
- Must identify limited investment experience as relevant.
- Must identify concentration conflict because 22.5% exceeds the 15% limit.
- Must produce a coherent recommendation, not only isolated risk bullets.

`instruction_adherence`

- Must use only the provided materials.
- Must explain the main conflicts or supporting factors.
- Must provide one of the requested final actions.
- Must not recommend `proceed` without addressing the concentration and profile conflicts.

## Task 3

### Task

`Covenant check`

### Work Product

Primary:

- `covenant compliance note`

Optional future variant:

- `lender exception summary`

### Context

```yaml
documents:
  - id: DOC1
    type: loan agreement excerpt
    content: |
      Borrower must maintain:
      - Minimum DSCR of 1.25x tested quarterly
      - Maximum Total Debt / EBITDA of 3.50x tested quarterly
      Any covenant breach must be reported to Credit Risk.

  - id: DOC2
    type: quarterly borrower financial summary
    content: |
      Quarter: Q2 2026
      EBITDA: USD 420,000
      Interest Expense: USD 95,000
      Scheduled Principal Payments: USD 210,000
      Total Debt: USD 1,650,000

  - id: DOC3
    type: borrower compliance certificate draft
    content: |
      Reported DSCR: 1.42x
      Reported Total Debt / EBITDA: 3.20x
      Management Comment: All financial covenants are in compliance.

  - id: DOC4
    type: lender review procedure excerpt
    content: |
      Reviewers must independently verify borrower-reported covenant calculations using the definitions in the loan agreement.
      If a borrower-reported figure appears inconsistent with the underlying financial summary, the reviewer must flag the inconsistency and state whether escalation is required.
```

### Query

```text
Using only the provided materials, prepare a covenant compliance note.
Independently assess whether the borrower is in compliance, identify any inconsistency in the borrower certificate,
and state whether the matter must be escalated to Credit Risk.
```

### Extracted Constraints

- Output must be a covenant compliance note.
- Use only the provided materials.
- Independently assess compliance rather than relying on the borrower certificate.
- Identify inconsistencies between borrower-reported figures and underlying financial data.
- State whether escalation to Credit Risk is required.

### Protocol

`delivery_quality`

- Must compute or reason that DSCR based on EBITDA / (interest + principal) is below the borrower-reported 1.42x.
- Must identify inconsistency between reported covenant values and underlying figures.
- Must assess Debt / EBITDA using the provided totals.
- Must conclude that escalation is required if a breach or unresolved inconsistency exists.

`instruction_adherence`

- Must not rely only on the borrower compliance certificate.
- Must identify at least one inconsistency.
- Must state whether escalation to Credit Risk is required.
- Must use only the provided materials.

## Summary

This chain is now concrete for one workflow and three tasks:

- `AML red-flag review`
- `Suitability review`
- `Covenant check`

For each task, we now have:

- a chosen work product,
- a concrete English context,
- a query,
- extracted constraints,
- and a draft protocol.

This is the first executable slice of the benchmark pipeline.
