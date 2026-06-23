# FinIF v2 Benchmark Evaluation Method

## Benchmark Data

Benchmark file:

```text
outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl
```

Sampling source:

```text
outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl
```

Sampling policy:

- fixed random seed: `20260612`;
- sample size: `360`;
- all 38 task types covered;
- each task contributes 5-10 items;
- within each task, sample randomly while preferring distinct normalized query skeletons.

## Model Input

For each benchmark item, send the `full_prompt` field to the evaluated model.

The prompt already contains:

```text
Context:
<self-contained documents>

Task:
<query>
```

No external context files are needed at evaluation time.

## Constraint and Quality Scoring

Each model response is scored against every object in `extracted_constraints`.

Each constraint has:

- `constraint`: the explicit requirement;
- `tag`: one fine-grained FinIF v2 tag;
- `family`: one of the five paper-facing families;
- `check_type`: original data-level evaluator hint, either `rule_aided` or `judge`.

The evaluator uses the stricter tag-level policy in:

```text
constraint_taxonomy_v2.md
evaluation/evaluator_spec.json
evaluation/evaluate_responses.py
```

The runner evaluates one benchmark item per judge call after local rule checks.
Mechanically decidable constraints are scored first by deterministic checkers.
All remaining semantic or unresolved constraints for the same item are sent to
the LLM judge together in one batched request. The same judge call also returns
one holistic `quality_score` from 0 to 10.

## Rule-Based Checks

Use deterministic checks whenever a constraint is mechanically verifiable.

Examples:

- valid JSON;
- required fields or table columns;
- required keywords or forbidden phrases;
- word, section, item, or table-row counts;
- explicit numbers, thresholds, deadlines, dates, labels, or regex patterns.

If a rule checker cannot make a reliable binary decision, it must return `needs_judge` instead of guessing.

## LLM-as-a-Judge

For semantic constraints, or rule-based constraints that return `needs_judge`,
use LLM-as-a-judge. Judge input contains the evaluated prompt, the model
response, and the list of constraints that still need judgment for that item.

```text
Evaluate each listed constraint independently using the prompt as ground truth.
Return binary constraint scores and one holistic quality score.
```

The judge must return strict JSON:

```json
{
  "constraint_scores": [
    {"constraint_index": 1, "score": 1, "reason": "Short reason."}
  ],
  "quality_score": 5,
  "quality_reason": "Short reason."
}
```

Allowed scores:

- constraint `score`: `1` pass, `0` fail
- `quality_score`: integer `0` to `10`

Recommended judge settings:

- temperature `0`;
- strict JSON parsing;
- retry malformed judge outputs;
- save raw judge outputs;
- optional repeated judging with majority vote for audits.

## Aggregation

Primary score:

```text
micro constraint pass rate = passed decided constraints / decided constraints
```

Auxiliary quality score:

```text
mean quality_score on a 0-10 scale
```

Optional combined score:

```text
final_score = 0.8 * IF_micro_score + 0.2 * mean(quality_score / 10)
```

Also report:

- macro item score;
- constraint coverage;
- mean quality score;
- optional combined score;
- score by task;
- score by workflow;
- score by constraint family and tag;
- number of `needs_judge` constraints if running in hard-only mode.

In official runs, unresolved `needs_judge` constraints should not be silently counted as passed. They should be judged or reported as unresolved coverage.

## QA Commands

Dataset schema QA:

```bash
python3 evaluation/qa_dataset.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl
```

Query diversity QA:

```bash
python3 evaluation/query_skeleton_qa.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl --max-per-skeleton 3 --min-skeletons-per-task 5
```

Response evaluation runner:

```bash
python3 evaluation/evaluate_responses.py \
  --dataset outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl \
  --responses <model_responses.jsonl> \
  --output <scores.json>
```

## Adversarial Long-Context Variant

Use this sidecar benchmark when the experiment needs to test the stronger bet:
finance-domain instruction following degrades under long, noisy, authority
conflicting context, even for strong models.

Dataset builder:

```bash
python3 outputs/benchmark/build_adversarial_longctx_benchmark.py
```

Generated files:

```text
outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v7_adversarial_longctx.jsonl
outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v7_adversarial_longctx_summary.json
```

The v7 builder preserves the original v6 active case and constraints, then
adds:

- an active DOC-ID and visible-label citation registry;
- copied-forward archive packets that are explicitly non-authoritative;
- stale draft-answer markers, obsolete templates, and shadow numeric values;
- same-workflow and same-task archive search hits after the active case;
- rule-aided checks for ARCH label leakage and stale marker copying;
- judge-scored constraints for granular citations, calculation lineage,
  active-trigger decisions, missing-evidence boundaries, and live-template
  precedence.

Smoke command:

```bash
python3 evaluation/run_gpt5_smoke_eval.py \
  --dataset outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v7_adversarial_longctx.jsonl \
  --selected-output outputs/benchmark/smoke_gpt5_5_v7_adversarial_longctx_dataset.jsonl \
  --responses-output outputs/benchmark/smoke_gpt5_5_v7_adversarial_longctx_responses.jsonl \
  --scores-output outputs/benchmark/smoke_gpt5_5_v7_adversarial_longctx_scores.json \
  --lines 1,2,3,4,5 \
  --response-model gpt-5 \
  --judge-model gpt-4o \
  --response-max-output-tokens 6000 \
  --judge-max-output-tokens 3200
```

Current 5-item smoke comparison:

| Dataset | Final score | IF micro | Macro item | Exact item pass | Mean quality | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v6 base smoke | 0.973143 | 0.971429 | 0.960000 | n/a | 9.80 | 1.00 |
| old longctx smoke | 0.964000 | 0.960000 | 0.956818 | n/a | 9.80 | 1.00 |
| domain longctx smoke | 0.900000 | 0.900000 | 0.902273 | n/a | 9.00 | 1.00 |
| v7 adversarial longctx smoke | 0.886857 | 0.928571 | 0.917949 | 0.600000 | 7.20 | 1.00 |
