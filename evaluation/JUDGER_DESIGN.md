# FinIF v2 Item-Batched Judger Design

## Current Legacy Logic Worth Reusing

`current/` is legacy, but several implementation patterns are useful:

- Parameterized hard checkers: old `current/checkers.py` uses `checker + params`
  functions for JSON, Markdown tables, keywords, section/list counts, word
  ranges, table rows/columns, first/last line checks, conditional triggers, and
  some numeric checks. This is the right shape for v2 rule-aided constraints.
- Local-first evaluation: old runners run hard checks before judge calls. v2
  should keep this to reduce cost and improve consistency.
- Judge retry and raw parsing discipline: old runners strip code fences, retry
  malformed judge outputs, and save reason/evidence. v2 keeps retry/raw output
  storage, but uses a strict item-batched schema rather than fuzzy pass/fail
  parsing.
- Aggregation: old runners report per-case and overall pass rates. v2 should
  aggregate item-level and dataset-level scores, while also reporting coverage
  because some constraints may remain `needs_judge`.

What should not be reused directly:

- Old soft checks use generated rubrics. v2 says the single constraint text is
  the judging standard; no per-constraint rubric should be introduced.
- Some old hard checkers return `True` when parameters are absent or evidence is
  too weak. v2 should return `needs_judge` instead.
- Semantic finance correctness, evidence sufficiency, and decision quality
  should not be forced into brittle local regex checks.

## Rule-Based Reliability Boundary

Reliable rule-based constraints:

- Valid output format: JSON, Markdown table, checklist/checkbox syntax.
- Required field, table column, heading, label, keyword, forbidden phrase, or
  exact disclaimer.
- Word, item, section, table-row, or decimal-place counts when numeric targets
  are explicit.
- Required numbers, thresholds, dates, deadlines, cadence terms, or named
  source references.
- Simple conditionals where both trigger and required follow-up are exact
  strings.
- Regex patterns supplied by evaluator config.

Unreliable as hard checks unless exact parameters are provided:

- `RC*` substantive coverage, issue completeness, action adequacy, or risk
  impact coverage.
- `EG*` grounding quality, fact-vs-inference separation, missing-data handling,
  or source fidelity beyond exact citations/labels/values.
- `DB*` decision correctness, escalation/reporting appropriateness, boundary
  compliance, and semantic classification.
- `FP5` tone, role, audience, neutrality, client-friendliness, or conservative
  style.
- `QV*` calculation/reconciliation correctness when expected inputs, formulas,
  tolerances, or outputs are not configured.
- Ranking/comparison by importance unless the expected order is explicit.

The default rule is conservative: if the checker needs to infer meaning,
intent, sufficiency, financial correctness, or evidentiary adequacy, it returns
`score: null` and `status: "needs_judge"`.

## Evaluator Flow

Input per item:

```json
{
  "item_id": "string",
  "response": "model answer",
  "full_prompt": "evaluated model input",
  "constraints": ["objects from extracted_constraints"]
}
```

For each constraint:

1. If `check_type == "rule_aided"`, run `evaluation.checkers.evaluate_constraint`.
2. If the local result has `score` 0 or 1, record it as final.
3. If local result has `score: null`, enqueue that constraint for the item-level
   batched judge.
4. If `check_type == "judge"`, enqueue it for the item-level batched judge.
5. The batched judge receives the prompt, response, and all queued constraints
   once, then returns one binary score per queued constraint plus one holistic
   quality score from 0 to 10.
6. If judge is unavailable or hard-only mode is enabled, preserve the item judge
   prompt and leave queued constraints and quality as `needs_judge`.

Judge prompt:

```text
Evaluate each listed constraint independently using the evaluated prompt as
ground truth. Return binary constraint scores and one holistic quality score.
```

Judge output must be strict JSON:

```json
{
  "constraint_scores": [
    {"constraint_index": 1, "score": 1, "reason": "Short reason."}
  ],
  "quality_score": 5,
  "quality_reason": "Short reason."
}
```

Consistency policy:

- temperature must be 0 in real providers;
- parser accepts only integer constraint `score` values 0 or 1;
- parser accepts only integer `quality_score` values from 0 to 10;
- booleans, strings such as `"pass"`, and fuzzy text are invalid;
- parse failure is retried;
- repeated judging can be enabled and aggregated by majority vote;
- all raw judge outputs are saved;
- reasons should be short and diagnostic.

## Implemented Files

- `evaluation/checkers.py`: deterministic checker library with explicit
  `pass` / `fail` / `needs_judge` statuses.
- `evaluation/evaluate_responses.py`: offline-capable item-batched runner,
  strict judge parser, provider adapter interface, retry/majority logic,
  quality scoring, and aggregation.
- `evaluation/evaluator_spec.json`: machine-readable policy and strict judge
  schema.
- `evaluation/README.md`: usage and rule-based boundary documentation.

## Aggregation

Per item:

- `total_constraints`
- `decided_constraints`
- `passed_constraints`
- `needs_judge_constraints`
- `score = passed_constraints / decided_constraints`
- `coverage = decided_constraints / total_constraints`
- `quality_score` from 0 to 10
- breakdowns by method and tag

Dataset:

- micro score over all decided constraints;
- macro item score over item scores;
- coverage over all constraints;
- mean quality score on the 0-10 scale;
- optional combined score: `0.8 * IF_micro_score + 0.2 * mean(quality_score/10)`;
- missing response list.

Undecided constraints are not silently counted as failures because a hard-only
or offline run is incomplete. Final benchmark reporting should include both
score and coverage.

## Remaining Decisions

- Choose the real judge provider and model.
- Confirm whether official benchmark reports should treat unresolved
  `needs_judge` as excluded, failed, or invalid runs. The current runner reports
  coverage and excludes unresolved constraints from score denominators.
- Add calibrated checker configs to data or sidecar files for high-value
  quantitative constraints where exact expected values/tolerances are known.
- Optionally add a small gold set for judge agreement and checker false
  positive/false negative audits.
