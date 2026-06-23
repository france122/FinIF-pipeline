# FinIF v2 Evaluation

This directory defines the item-level batched evaluation layer for FinIF v2 full-prompt data.

## Evaluation Unit

Each model response is evaluated item by item. The evaluator receives:

- the evaluated model `full_prompt`;
- the model `response`;
- all constraint objects from `extracted_constraints`;
- optional checker parameters, when a constraint is mechanically checkable.

The evaluator runs local rule checks first. Constraints that cannot be decided
locally are sent to the LLM judge in one batched request for the item. The same
judge call also returns a holistic `quality_score` from 0 to 10. The final item
IF score is still computed by aggregating per-constraint binary scores.

## Hard and Soft Constraints

FinIF v2 uses two evaluation modes:

1. `rule_aided` for hard, mechanical, or rule-assisted constraints.
2. `judge` for constraints that require semantic judgment.

Hard constraints should use deterministic checkers only when the mechanical target is
explicit. Examples include valid JSON, required or forbidden wording, table/field
presence, section counts, item counts, word limits, required numbers, threshold
values, deadlines, exact labels, simple conditional keywords, and simple regular
expressions. A rule-aided checker returns `score: null` and `status: "needs_judge"`
when the constraint is too semantic or under-specified for a reliable local rule.

Soft constraints use LLM-as-a-judge. FinIF v2 does not generate separate
per-constraint rubrics. The LLM judge receives the prompt, response, and all
remaining constraints for one item, then returns one binary score per constraint
plus one holistic quality score.

Judge prompt:

```text
Evaluate each listed constraint independently using the prompt as ground truth.
Return binary constraint scores and one holistic quality score.
```

Expected judge output, with no surrounding prose:

```json
{
  "constraint_scores": [
    {"constraint_index": 1, "score": 1, "reason": "Short reason."}
  ],
  "quality_score": 5,
  "quality_reason": "Short reason."
}
```

Use `score: 1` for pass and `score: 0` for fail.
Use `quality_score` from `0` to `10`, where `10` is an excellent grounded
finance-workflow answer and `0` is unusable or off-task.

The evaluator parser is intentionally strict:

- each constraint `score` must be integer `0` or `1`, not `"pass"`, `"fail"`, `true`, or `false`;
- every pending `constraint_index` must appear exactly once;
- `quality_score` must be an integer from `0` to `10`;
- reasons must be non-empty short strings;
- malformed JSON is retried, then preserved in `raw_judge_outputs`;
- no fuzzy parsing is used for final scoring.

## Default Method Mapping

The default mapping is stored in `evaluator_spec.json`.

- `FP*` and `QV*` tags are mostly `rule_aided`, because many format, count, precision, threshold, deadline, and calculation requirements can be checked mechanically or with light rule assistance.
- `EG*`, `DB*`, and `RC*` tags are mostly `judge`, because evidence use, decision boundaries, issue coverage, and substantive completeness usually require semantic review.
- Keyword, deadline, threshold, count, JSON, field-format, and simple pattern constraints can be overridden to `rule_aided` even when their tag normally defaults to `judge`.

## Checker Interface

`checkers.py` exposes:

```python
from checkers import evaluate_constraint

result = evaluate_constraint(response, constraint)
```

The result shape is:

```json
{
  "score": 1,
  "status": "pass",
  "reason": "All required keywords were found.",
  "method": "rule_aided:required_keyword"
}
```

`score` is `1`, `0`, or `None`. `None` means the local checker did not make a binary decision. The result will have `status: "needs_judge"` and a standard judge prompt in `reason`.

Useful explicit checker fields can be placed under `constraint["evaluator"]`, `constraint["checker"]`, or at the constraint top level:

```json
{
  "constraint": "Mention the $5,000 SAR threshold.",
  "check_type": "rule_aided",
  "tag": "QV4",
  "evaluator": {
    "type": "contains_number",
    "numbers": ["5000"]
  }
}
```

Supported checker types:

- `required_keyword`
- `forbidden_phrase`
- `required_fields`
- `min_words`
- `max_words`
- `min_sections`
- `max_sections`
- `item_count`
- `valid_json`
- `markdown_table`
- `no_table`
- `table_columns`
- `table_row_count`
- `checkbox`
- `contains_number`
- `threshold`
- `deadline`
- `exact_value`
- `decimal_places`
- `first_line`
- `last_line`
- `conditional_trigger`
- `simple_regex`

## Rule-Based Boundary

Reliable rule-based checks:

- format validity: JSON, Markdown table, checkbox/list syntax;
- explicit field or column names;
- exact required or forbidden phrases;
- word, item, section, row, or simple count limits when a numeric target is explicit;
- exact numbers, thresholds, dates, cadence terms, and named labels;
- simple conditional trigger checks where both trigger and required follow-up are exact strings;
- simple regular expressions supplied by the evaluator config.

Do not hard-judge these unless the constraint provides exact checker parameters:

- substantive topic coverage (`RC*`) beyond exact named terms;
- evidence quality, source fidelity, missing-data handling, or fact-vs-inference separation (`EG*`) beyond exact labels or citations;
- decision correctness, escalation appropriateness, boundary compliance, or classification when semantic reasoning is needed (`DB*`);
- tone, audience, readability, neutrality, or conservatism (`FP5`);
- calculations/reconciliations where expected inputs or outputs are not explicitly configured;
- ranking/comparison by importance unless the expected order is explicit.

The conservative default is: if a local checker would need to infer meaning,
intent, sufficiency, financial correctness, or evidentiary adequacy, return
`needs_judge`.

## Evaluating Response Files

`evaluate_responses.py` evaluates a response JSONL against a FinIF v2 dataset
JSONL. The response file must contain one object per item with `item_id`, `id`,
`case_id`, or `line_number`, plus `response` or `output`.

Offline hard-only run:

```bash
python3 evaluation/evaluate_responses.py \
  --dataset outputs/full_prompts/repaired_final_v2/finif_v2_repaired_v2_full_prompts.jsonl \
  --responses responses_model.jsonl \
  --output evaluation/results_model.json \
  --hard-only
```

With a real judge provider:

```bash
python3 evaluation/evaluate_responses.py \
  --dataset data.jsonl \
  --responses responses.jsonl \
  --output scores.json \
  --judge-provider my_package.my_judge:Provider \
  --repeats 3 \
  --parse-retries 2
```

The provider is an adapter with:

```python
class Provider:
    name = "provider-name"

    def judge(self, request, system_prompt: str) -> str:
        # Call the model at temperature=0 and return raw model text.
        ...
```

The runner handles strict JSON parsing, parse-failure retry, repeated
judging/majority vote, raw judge output storage, item/dataset aggregation, and
the combined score:

```text
final_score = 0.8 * IF_micro_score + 0.2 * mean(quality_score / 10)
```

## Dataset QA

`qa_dataset.py` validates full-prompt JSONL files for the FinIF v2 schema rules:

- no `context_text`;
- `full_prompt`, `context`, and `query` are present;
- constraints contain required fields;
- no `tags` array remains;
- tag prefix matches the declared family;
- no `source_path`, `slice_id`, or local path leakage;
- `check_type` is either `judge` or `rule_aided`.

Run QA:

```bash
python3 evaluation/qa_dataset.py outputs/full_prompts/risk_compliance_ready_full_prompts_tagged.jsonl
```

Run one checker example:

```bash
python3 evaluation/checkers.py \
  --response-file response.txt \
  --constraint-json '{"constraint":"Mention the $5,000 SAR threshold.","check_type":"rule_aided","tag":"QV4","evaluator":{"type":"contains_number","numbers":["5000"]}}'
```
