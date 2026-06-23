# Submission And Training Readiness

Date: 2026-06-15

This note checks the five highest-priority reviewer risks and records whether each is already covered, partially covered, or still blocking. It is written to decide whether the project can move into the training stage without pretending that every paper-facing issue is already closed.

## Bottom Line

- We are ready to move into training.
- We are not yet ready to claim that the paper-side evaluation-credibility question is fully closed.
- The main remaining paper blocker is not benchmark construction anymore; it is human audit of the highest-tension semantic tags, especially `EG2 / QV2 / DB9`.

## 1. Evaluation Credibility

Status: `partially addressed, still needs human audit`

What is already established:

- `GPT-5.5` EG2 failures are not caused by missing benchmark constraints.
- In `107/107` GPT-5.5 EG2 fail cases, the hardening phrase appears in the `query`.
- In `107/107` GPT-5.5 EG2 fail cases, the phrase also appears in `full_prompt`.
- In `107/107` GPT-5.5 EG2 fail cases, an explicit EG2 constraint exists in `all_constraints`.
- `60/107` GPT-5.5 EG2 fail cases are `EG2-only`, which makes them the highest-value audit subset.

Current interpretation:

- This rules out the easiest benchmark bug explanation: “the query never actually asked for this.”
- It does not yet fully rule out judge over-strictness.
- The remaining uncertainty is specifically whether `active` and `next to` are being interpreted too aggressively in some high-quality cases.

Supporting artifacts:

- `outputs/reports/gpt55_eg2_findings.md`
- `outputs/reports/gpt55_eg2_findings.csv`

What still needs to happen:

- Human audit for `EG2 / QV2 / DB9`
- Outcome labels should be at least:
  - `model_true_fail`
  - `judge_too_strict`
  - `constraint_wording_ambiguous`

Conclusion for training:

- This is a paper-credibility blocker, not a training blocker.
- Training can proceed while the audit runs in parallel.

## 2. Are Constraints Real Task Requirements?

Status: `not fully resolved; needs honest positioning`

Important correction:

- We should **not** use `source=query` as evidence that constraints come from natural real-world user requests.
- In the current benchmark, many `query` fields are synthetic or rewritten.
- Therefore, `query/context` source counts show benchmark-internal placement, not real-world provenance.

What we can now say with evidence:

- Hard300 IF-clean has `3134` IF constraints total.
- `471` are base constraints already present before tonight hardening.
- `2663` are explicit `tonight_hardening` constraints.
- Constraint source fields in hard300 IF-clean:
  - `query`: `3088`
  - `context`: `46`

Correct interpretation:

- These counts show where constraints are encoded in the benchmark artifact.
- They do **not** prove that the constraints are all naturally sourced from real financial user requests.
- The current benchmark is better described as:
  - workflow-grounded
  - built from finance work-product settings
  - then explicitly hardened with audit-ready delivery constraints

What the paper must say clearly:

- Which constraints come directly from base workflow/task requirements
- Which are benchmark hardening constraints added by the authors
- Why those hardening constraints are still operationally meaningful rather than arbitrary formatting pressure
- That FinIF is not a pure capture of raw real-world requests, but a workflow-grounded benchmark designed to stress audit-ready delivery

Conclusion for training:

- Not a blocker.
- But the training objective should be described honestly as `training toward FinIF-style audit-ready delivery constraints`, not as pure imitation of untouched real-world prompts.

## 3. Task And Constraint Distribution

Status: `already supported by local evidence, should be surfaced more explicitly`

Hard300 IF-clean distribution:

- Items: `300`
- Workflow stages: `5`
- Unique task types: `38`
- Constraints: `3134`
- Rule-checked constraints: `1346`
- LLM-judged constraints: `1788`
- Constraints per item: min `7`, median `10`, max `16`

Workflow item counts:

- `Execution, Monitoring, Reporting, and Operations`: `74`
- `Risk and Compliance Review`: `64`
- `Decision and Structuring`: `63`
- `Intake and Profiling`: `54`
- `Research and Due Diligence`: `45`

Top IF tags:

- `FP3`: `507`
- `FP6`: `305`
- `FP4`: `302`
- `DB9`: `300`
- `EG2`: `300`
- `QV2`: `287`
- `FP2`: `204`
- `EG1`: `195`
- `DB4`: `130`
- `EG5`: `122`
- `DB7`: `113`

Family distribution:

- `Format and Presentation`: `1391`
- `Decision and Boundary`: `690`
- `Evidence and Grounding`: `673`
- `Quantitative Verification`: `374`
- `Required Content Coverage`: `6`

Interpretation:

- The benchmark is broad in task coverage, but not symmetric in constraint-family weight.
- It is heavily shaped by delivery-format and audit-readiness hardening, which is consistent with the project’s intended claim.
- The paper should present this as a feature of the benchmark design, not as an incidental property.

Conclusion for training:

- Helpful, not blocking.
- Supports choosing FinIF as a targeted training objective rather than a generic financial-task objective.

## 4. Contribution Definition

Status: `conceptually present, needs sharper wording`

The strongest claim supported by current evidence is:

> FinIF measures whether models can convert financially plausible analysis into workflow-specific, constraint-satisfying, audit-ready deliverables.

What should be avoided:

- “another financial benchmark”
- “general financial reasoning benchmark”
- implying that the main novelty is just more finance tasks or more instructions

What the current evidence actually supports:

- workflow grounding
- dense delivery constraints
- explicit separation of rule-side compliance, judge-side compliance, and full strict pass
- strong-model gap between local competence and full work-product readiness

Conclusion for training:

- Not a blocker.
- It helps define the teacher target more cleanly: we are not just training for better finance answers; we are training for better audit-ready financial deliverables.

## 5. Quality Versus OSR

Status: `already meaningful, now needs explicit interpretation`

Observed pattern:

- `GPT-5.5`: `OSR 58.67%`, `Quality 7.40`
- `GPT-5`: `OSR 47.33%`, `Quality 7.05`
- Many items fail strict IF while still looking fairly good.

Additional local evidence:

- `GPT-5.5` has `68/300` failed items whose raw quality score is still `>= 6`.
- Several of those are pure local format-rule failures such as `FP3` or `FP2`.
- Several others are `EG2-only` failures where the output is otherwise highly usable.

Interpretation:

- Quality and strict compliance are related but not interchangeable.
- This is not metric incoherence by itself.
- It is direct evidence for the benchmark’s core thesis: a financial answer can be useful or persuasive while still not being audit-ready.

What still needs caution:

- The paper must say clearly that `Quality` is a diagnostic axis, not a replacement for IF compliance.
- High-quality failures are the most valuable case-study pool, but also the area where evaluator tension is most visible.

Conclusion for training:

- Strongly supports entering training.
- These high-quality-but-not-fully-compliant failures define the exact gap training should target.

## Training Decision

Training stage status: `go`

Reason:

- The benchmark is now defined clearly enough to act as a training target.
- The remaining unresolved issue is evaluation calibration, not task identity.
- That means we can start training while continuing paper-facing audit and calibration work.

Recommended training interpretation:

- Teacher priority: `GPT-5.5`, then `GPT-5`
- Optimization target:
  - evidence placement (`EG2`)
  - quantitative lineage (`QV2`)
  - evidence-rule-action closure (`DB9`)
  - approval/prerequisite/date-status closure (`DB7 / QV5`)

## Remaining Pre-Submission Must-Fix Items

- Human audit for `EG2 / QV2 / DB9`
- Paper-facing explanation of base constraints versus hardening constraints
- Cleaner benchmark positioning against existing financial and IF benchmarks
- One explicit section or figure explaining why `MSR / RSR / OSR / Quality` together reveal the deployment gap
