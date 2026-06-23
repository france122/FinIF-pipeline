# GPT-5.5 EG2 Findings

Goal: determine whether EG2 failures come from missing constraints, model behavior, or judge tension.

## Hard facts

- EG2 fail cases in GPT-5.5 hard300: `107`
- Cases whose `query` explicitly contains the hardening phrase: `107/107`
- Cases whose `full_prompt` explicitly contains the hardening phrase: `107/107`
- Cases whose `all_constraints` explicitly contain an EG2 constraint: `107/107`
- Cases where EG2 is the only failed tag: `60/107`

## Preliminary conclusion

- `query 没写这条约束` is not the main explanation for GPT-5.5 EG2 failures in the current hard300 run.
- Many EG2 fails are genuine model misses under the current benchmark wording: the response includes some labels, but not consistently at every controlling use point.
- The main audit-risk subset is the `EG2-only` group, especially high-quality cases with `if_score >= 0.90`; these are the best candidates for checking whether judge interpretation of `active` and `next to` is too strict.

## Manual audit shortlist

Recommended first-pass EG2-only review items:
- `tonight_hard_line_191` | Intake and Profiling | Service scope explanation | IF `0.923` | quality `6` | Some material facts lack active source labels next to them.
- `tonight_hard_line_028` | Decision and Structuring | Portfolio proposal | IF `0.917` | quality `6` | Some material facts lack active source labels next to them.
- `tonight_hard_line_109` | Risk and Compliance Review | Risk disclosure review | IF `0.917` | quality `6` | Not all material facts and decisions have active source labels next to them.
- `tonight_hard_line_338` | Decision and Structuring | Loan approval package | IF `0.917` | quality `6` | Some facts lack active source labels next to them.
- `tonight_hard_line_034` | Risk and Compliance Review | AML red-flag review | IF `0.909` | quality `6` | Not all material facts and decision points have active source labels next to them.
- `tonight_hard_line_038` | Intake and Profiling | Counterparty / issuer profile construction | IF `0.909` | quality `6` | Some facts lack active source labels next to them.
- `tonight_hard_line_049` | Intake and Profiling | Client risk profiling | IF `0.909` | quality `6` | Lacks active source labels next to all material facts.
- `tonight_hard_line_112` | Research and Due Diligence | Earnings review | IF `0.909` | quality `6` | Not all material facts and calculations have active source labels next to them.
- `tonight_hard_line_169` | Execution, Monitoring, Reporting, and Operations | Risk alert generation | IF `0.909` | quality `6` | Some material facts lack active source labels next to them.
- `tonight_hard_line_213` | Execution, Monitoring, Reporting, and Operations | Remediation tracking | IF `0.909` | quality `6` | Active source labels are not consistently next to material facts and decision points.
- `tonight_hard_line_244` | Intake and Profiling | Client risk profiling | IF `0.909` | quality `6` | Some material facts lack active source labels next to them.
- `tonight_hard_line_298` | Intake and Profiling | KYC onboarding | IF `0.909` | quality `6` | Some facts lack active source labels next to them.
- `tonight_hard_line_308` | Risk and Compliance Review | Regulatory issue escalation | IF `0.909` | quality `6` | Some material facts lack active source labels next to them.
- `tonight_hard_line_309` | Decision and Structuring | Trade order ticket preparation | IF `0.909` | quality `6` | Not all material facts have active source labels next to them.
- `tonight_hard_line_353` | Research and Due Diligence | Credit due diligence | IF `0.909` | quality `6` | Not all material facts and calculations have active source labels next to them.

## What to check in review

- If unlabeled sentences merely restate a nearby labeled fact, decide whether that should still fail under the current rubric.
- If a decision sentence or business-implication sentence has no label at the point of use, that looks more like a true model miss than a judge bug.
- If the answer uses many labels but the judge still claims a broad EG2 failure, mark it as a potential rubric-tightening candidate.
