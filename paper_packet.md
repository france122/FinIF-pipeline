# Paper Packet: FinIF v2

Generated on 2026-06-12 from repository state under `/Users/minimax/Desktop/lunwen`.

Scope note: `AGENT.md` says the active project is FinIF v2 and that `current/` is legacy. This packet treats FinIF v2 as the paper-facing system. Current project status is benchmark construction and evaluator scaffolding, not completed model experiments. Any experiment, ablation, latency, or SFT result not yet run is written below as a planned analysis or expected hypothesis, not as a result. No API keys or secret values were inspected or copied.

## 1. Task Definition

FinIF v2 is a finance workflow instruction-following benchmark and data pipeline. It tests whether an LLM can read supplied finance materials, complete a workflow-specific deliverable, and obey explicit constraints about format, evidence use, quantitative checks, decisions, boundaries, and required content.

The core problem is not open-domain financial QA. Each item simulates a financial work product at a workflow node, such as a KYC review note, credit memo, underwriting memo, suitability review, AML escalation report, reconciliation exception report, board report, or remediation tracker.

Inputs:

| Input | Description | Main locations |
| --- | --- | --- |
| `full_prompt` | Evaluated model input. It must be self-contained and include usable context plus task requirements. | `outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl`, `outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources.jsonl` |
| `context.documents[]` | Structured source documents with `id`, `title`, and `content` for data construction and QA. | v3 full-prompt dataset |
| `source_registry[]` | Benchmark rephrase metadata mapping original source IDs to prompt-visible labels and content. It is metadata, not a substitute for prompt context. | v6 benchmark rephrase |
| `query` | Natural-language work request for a finance deliverable. | v3 full-prompt dataset and original 360 benchmark |
| `extracted_constraints[]` | Explicit checkable requirements from query or context, each with one v2 tag, family, and `check_type`. | all v2 datasets |
| model `response` | Candidate answer to be evaluated. | response JSONL files passed to `evaluation/evaluate_responses.py` |

Outputs:

- A finance workflow deliverable produced by the model, e.g. a memo, note, checklist, decision table, JSON handoff, or client-facing message.
- Item-level evaluation results with binary constraint scores, a holistic quality score, coverage, and breakdowns by method and tag.
- Dataset-level summaries such as micro constraint pass rate, macro item score, coverage, mean quality, optional combined score, and family/tag breakdowns.

Intended users and workflow participants:

- Benchmark/data builders who create finance tasks, contexts, queries, and constraints.
- Model developers evaluating financial instruction-following behavior.
- Financial analysts, risk/compliance reviewers, operations reviewers, and supervisors as the simulated end users of the generated work products.
- Human reviewers who inspect QA reports, repair shards, and sensitive or low-diversity items before release.

## 2. System Overview

### Main pipeline stages

1. Define finance workflow taxonomy.
   - Source: `task_workflow_final.md`.
   - Five workflow stages: Intake and Profiling; Research and Due Diligence; Decision and Structuring; Risk and Compliance Review; Execution, Monitoring, Reporting, and Operations.
   - Active task set in `AGENT.md`: 38 task types, each with 28 items in the main v3 dataset.

2. Source or synthesize context packs.
   - Source plan: `context_source_catalog_en.md`.
   - Public context files and manifests: `outputs/context_raw_en/*/manifest.jsonl`.
   - Context text cache: `outputs/context_text_cache/` has 23 cached text extractions.
   - Manifest status observed: Decision and Structuring 5 ok / 1 failed; Execution 5 ok / 3 failed; Intake 5 ok; Research 4 ok / 2 failed; Risk and Compliance 23 ok / 5 failed.
   - Public sources include SEC filings, FINRA rules, SEC/FinCEN/FDIC/SBA/IRS materials, eCFR/XML, and other regulator or primary-source pages. Customer, borrower, account, and internal policy records are synthetic or mixed to avoid private data.

3. Build full-prompt datasets.
   - Scaled shard merge: `outputs/full_prompts/scaled_final/merge_scaled_dataset.py`.
     - Key functions: `read_jsonl`, `validate_and_normalize`, `main`.
   - Repair merge v3: `outputs/full_prompts/repaired_final_v3/build_repaired_final_v3_dataset.py`.
     - Key functions: `read_jsonl`, `constraints`, `validate`, `load_repairs`, `main`.
   - Active full dataset: `outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl`.

4. QA and query-diversity repair.
   - Schema QA: `evaluation/qa_dataset.py`.
     - Key functions/classes: `QAError`, `validate_item`, `validate_jsonl`, `check_item_required_fields`, `check_prompt_shape`, `check_constraints`, `check_tag_family_mapping`.
   - Query skeleton QA: `evaluation/query_skeleton_qa.py`.
     - Key function: `normalize_query`.
   - QA reports: `evaluation/qa_reports/*.md`.
   - Earlier scaled shards had template repetition, e.g. `evaluation/qa_reports/risk_compliance_scaled_coverage_qa.md` found 4 query patterns repeated 7 times per task. The repaired v3 dataset now passes query skeleton QA with 28 unique normalized query skeletons per task.

5. Sample benchmark.
   - Script: `outputs/benchmark/build_finif_v2_benchmark.py`.
   - Key functions: `allocate_counts`, `sample_task_rows`, `main`.
   - Policy: fixed seed `20260612`, target size 360, all 38 task types, 5 to 10 items per task, random sampling while preferring distinct normalized query skeletons.
   - Original 360 benchmark: `outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl`.

6. Rephrase benchmark prompts for more realistic prompt style.
   - Current benchmark rephrase: `outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources.jsonl`.
   - Summary: `outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources_summary.json`.
   - Observed properties: 360 rows; constraints identical to source; every original context document content appears inside `full_prompt`; `source_registry` contains 1,031 document entries; no global `Context:` or `Task:` labels; exact original query text copied 0 times; 360 unique first lines.
   - I did not find a checked-in Python script that regenerates this exact v6 rephrase from source, only the artifact and summary.

7. Generate model responses.
   - Current v2 sample response files:
     - `outputs/benchmark/v6_random10_seed20260612.jsonl`: 10 sampled v6 items.
     - `outputs/benchmark/v6_random10_seed20260612_responses.jsonl`: 10 responses, model not recorded.
     - `outputs/benchmark/v6_random10_seed20260612_gpt55_responses.jsonl`: 10 `gpt-5.5` responses, 0 errors in `v6_random10_seed20260612_gpt55_errors.jsonl`.
   - Smoke runner: `evaluation/run_gpt5_smoke_eval.py`.
     - Key functions/classes: `read_api_key`, `output_text`, `create_response`, `create_json_response`, `OpenAIJudgeProvider`, `load_selected_rows`, `main`.
     - Risk: it reads API keys from `key.md`; do not publish that file or secret values.

8. Evaluate responses.
   - Main evaluator: `evaluation/evaluate_responses.py`.
   - Key classes/functions: `JudgeRequest`, `JudgeProvider`, `StubJudgeProvider`, `load_dataset`, `load_responses`, `response_for_item`, `strict_parse_item_judge`, `documents_from_item`, `build_item_judge_prompt`, `judge_item_with_retries`, `evaluate_item`, `summarize_results`, `summarize_dataset`, `main`.
   - Rule checkers: `evaluation/checkers.py`.
   - Key functions: `evaluate_constraint`, `get_checker_type`, `infer_checker_type`, `checker_config`, `build_judge_prompt`.
   - Supported local checker types include required keyword, forbidden phrase, required fields, word limits, section/item counts, valid JSON, Markdown table, table columns/rows, checkbox, number/threshold/deadline/exact value, decimal places, first/last line, conditional trigger, and regex.

9. Visualize and inspect.
   - Dashboard builder: `evaluation/build_dashboard.py`, especially `compute_stats` and `main`.
   - Response viewer: `evaluation/build_response_viewer.py`.
   - Artifacts: `outputs/benchmark/dashboard.html`, `outputs/benchmark/responses_viewer.html`.

### Constraint taxonomy and scoring logic

Active v2 taxonomy: `constraint_taxonomy_v2.md`.

| Family | Tags | Meaning |
| --- | --- | --- |
| Format and Presentation | `FP1` to `FP6` | structure, format, length/count/precision, wording, tone/audience, opening/closing |
| Evidence and Grounding | `EG1` to `EG7` | context-only grounding, citations, fact/inference separation, unknown handling, source fidelity, source-status caveats, records |
| Decision and Boundary | `DB1` to `DB8` | decisions, triggers, escalation/reporting, non-commitment, breach/gap, classification, approval, regulated communication boundaries |
| Quantitative Verification | `QV1` to `QV7` | calculations, recalculation, reconciliation, thresholds, deadlines, comparisons/ranking, stress/scenario checks |
| Required Content Coverage | `RC1` to `RC8` | deliverable, topics, issues, actions, alternatives, customer/account profile, controls/governance, risk/impact |

Evaluation policy:

- `evaluation/checkers.py` tries deterministic checks first for mechanically checkable constraints.
- `evaluation/evaluate_responses.py` also has `RULE_FIRST_TAGS`, so some constraints are rule-aided by tag default even if the stored `check_type` says `judge`.
- If local checking cannot decide reliably, it returns `score: null` / `status: needs_judge`.
- Unresolved constraints for the same item are batched into one LLM-as-judge call.
- The judge returns strict JSON with one binary score per pending constraint and one `quality_score` from 0 to 10.
- Parser rules are strict: integer 0/1 scores only, integer quality 0-10 only, all pending indexes exactly once, no fuzzy parsing.
- Repeated judging is supported by `--repeats`; majority vote is implemented by `majority_score`.

Fallback, routing, caching, and human-in-the-loop logic:

- Local-first routing reduces judge calls and cost.
- `needs_judge` fallback prevents brittle rule checkers from guessing semantic finance judgments.
- `--hard-only` mode reports unresolved coverage instead of silently passing or failing semantic constraints.
- `StubJudgeProvider` allows offline evaluation runs that expose unresolved constraints.
- `documents_from_item` can recover source documents from `context.documents`, `documents`, or `source_registry`.
- `strict_parse_item_judge` plus `parse_retries` handles malformed judge JSON.
- Query-diversity repair is human/agent-in-the-loop through task repair shards in `outputs/full_prompts/task_repair_shards/` and status tracking in `task_repair.md`.

## 3. Evaluation Setup

### Current v2 datasets

| Dataset | Path | Size and notes |
| --- | --- | --- |
| Full repaired v3 data | `outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl` | 1,064 items, 38 tasks, 28 items/task, 7,851 constraints |
| Original 360 benchmark | `outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl` | 360 items, 38 tasks, 2,641 constraints, seed 20260612 |
| Rephrased v6 benchmark | `outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources.jsonl` | 360 items, constraints unchanged, full original context included in every prompt, `source_registry` with 1,031 docs |
| 10-item v6 smoke/sample | `outputs/benchmark/v6_random10_seed20260612.jsonl` | 10 items, with response samples but no score JSON |

Validation I ran:

```bash
python3 evaluation/qa_dataset.py outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl
# OK: checked 1064 item(s); no QA errors found.

python3 evaluation/query_skeleton_qa.py outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl --max-per-skeleton 3 --min-skeletons-per-task 16
# No warnings; every task has 28 unique normalized query skeletons.

python3 evaluation/qa_dataset.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl
# OK: checked 360 item(s); no QA errors found.

python3 evaluation/query_skeleton_qa.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl --max-per-skeleton 3 --min-skeletons-per-task 5
# No warnings; every task has unique skeleton count equal to item count.
```

Note: `evaluation/qa_dataset.py` expects `context` and `query` fields and a `Context:` / `Task:` prompt shape, so it applies to the v3 full-prompt data and original benchmark, not directly to the v6 rephrased artifact whose fields are only `full_prompt`, `source_registry`, and `extracted_constraints`.

### Metrics computed by v2 evaluator

From `evaluation/evaluate_responses.py` and `evaluation/evaluator_spec.json`:

| Metric | Definition |
| --- | --- |
| micro constraint pass rate | `passed decided constraints / decided constraints` |
| macro item score | mean of item-level constraint pass scores |
| coverage | `decided constraints / total constraints` |
| `needs_judge_constraints` | unresolved constraints in offline or hard-only mode |
| quality score | judge-provided holistic content quality, 0 to 10 |
| combined score | optional `0.8 * IF_micro_score + 0.2 * mean(quality_score / 10)` |
| by-method breakdown | counts and pass rates by rule/judge method family |
| by-tag breakdown | counts and pass rates by v2 fine tag |

### Planned baselines and current response artifacts

Current v2:

- No completed full 360-item v2 model score files were found in `outputs/benchmark/`.
- Response samples exist for 10 v6 items, including a `gpt-5.5` response sample file.
- `evaluation/run_gpt5_smoke_eval.py` can generate and score a 5-item smoke test using an OpenAI-compatible judge provider, but only `outputs/benchmark/smoke_gpt5_5_dataset.jsonl` is present; no corresponding smoke score file was found.

Recommended model baselines to run for the Industry Track paper:

- Strong proprietary model baseline, e.g. a current frontier model.
- Mid-cost production model baseline.
- Open-weight or local model baseline.
- Optional finance-tuned or FinIF-trained model if training is completed later.
- Optional no-reasoning versus reasoning-mode comparison if the chosen model family supports it.

Legacy `current/` score files exist, but they belong to a previous 100-case setup and should not be used as current paper results.

### Reproduction commands

Build the current v2 360-item benchmark sample:

```bash
python3 outputs/benchmark/build_finif_v2_benchmark.py
```

Run v2 dataset QA:

```bash
python3 evaluation/qa_dataset.py outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl
python3 evaluation/query_skeleton_qa.py outputs/full_prompts/repaired_final_v3/finif_v2_repaired_v3_full_prompts.jsonl --max-per-skeleton 3 --min-skeletons-per-task 16
python3 evaluation/qa_dataset.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl
python3 evaluation/query_skeleton_qa.py outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl --max-per-skeleton 3 --min-skeletons-per-task 5
```

Evaluate a model response file on v2:

```bash
python3 evaluation/evaluate_responses.py \
  --dataset outputs/benchmark/finif_v2_benchmark_360_seed20260612_rephrased_v6_full_context_mixed_sources.jsonl \
  --responses <model_responses.jsonl> \
  --output <scores.json> \
  --judge-provider <module.path:Provider> \
  --repeats 1 \
  --parse-retries 2
```

Offline hard-only run:

```bash
python3 evaluation/evaluate_responses.py \
  --dataset outputs/benchmark/finif_v2_benchmark_360_seed20260612.jsonl \
  --responses <model_responses.jsonl> \
  --output <scores_hard_only.json> \
  --hard-only
```

## 4. Results

### Current v2 dataset and benchmark readiness

| Artifact | Items | Tasks | Constraints | Rule-aided | Judge | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Repaired v3 full data | 1,064 | 38 | 7,851 | 4,729 | 3,122 | QA passed; 28 items/task; no warnings in summary |
| Original 360 benchmark | 360 | 38 | 2,641 | 1,620 | 1,021 | QA passed; 7-10 items/task; 360 unique query skeletons |
| Rephrased v6 benchmark | 360 | not stored in summary | unchanged from source | not repeated in v6 summary | not repeated in v6 summary | full context included in every prompt; constraints identical; 360 unique first lines |

V3 family counts:

| Family | Count |
| --- | ---: |
| Evidence and Grounding | 1,990 |
| Required Content Coverage | 1,904 |
| Decision and Boundary | 1,885 |
| Quantitative Verification | 1,456 |
| Format and Presentation | 616 |

Original 360 benchmark family counts:

| Family | Count |
| --- | ---: |
| Evidence and Grounding | 658 |
| Required Content Coverage | 642 |
| Decision and Boundary | 626 |
| Quantitative Verification | 513 |
| Format and Presentation | 202 |

Rephrased v6 prompt QA summary:

| Check | Value |
| --- | ---: |
| Rows | 360 |
| Constraints identical to source | true |
| Full prompt contains every original context content | true |
| Missing context content count | 0 |
| Source registry document entries | 1,031 |
| Visible `DOC` marker rows in full prompt | 15 |
| Global `Context:` label count | 0 |
| Global `Task:` label count | 0 |
| Exact original query copied | 0 |
| Unique first lines | 360 |
| Word count min / median / max | 139 / 230 / 526 |

### Current experimental status

No complete current-v2 360-item model score file was found. Do not claim model rankings, SFT gains, ablation deltas, latency numbers, or cost numbers until scored outputs from `evaluation/evaluate_responses.py` exist.

The only current-v2 response artifacts found are sample/smoke files:

| File | Rows | Score file found? | Notes |
| --- | ---: | --- | --- |
| `outputs/benchmark/v6_random10_seed20260612_responses.jsonl` | 10 | No | Response rows include `line_number` and `response`, no model name |
| `outputs/benchmark/v6_random10_seed20260612_gpt55_responses.jsonl` | 10 | No | Model recorded as `gpt-5.5`; error file has 0 rows |
| `outputs/benchmark/smoke_gpt5_5_dataset.jsonl` | 5 | No | Selected smoke dataset only |

### Planned main-results table

Fill this table only after running full response generation and scoring on the v6 360-item benchmark.

| Model | IF micro | Macro item | Coverage | Quality 0-10 | Final score | Rule-decided share | Judge-decided share | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `<frontier model>` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | planned baseline |
| `<mid-cost model>` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | planned baseline |
| `<open/local model>` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | planned baseline |
| `<finance-tuned model, if available>` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | optional |

Expected result pattern, to be treated as hypotheses:

- Larger or stronger general models are expected to score higher overall, especially on semantic `EG*`, `DB*`, and `RC*` constraints.
- Smaller or cheaper models may do reasonably well on mechanical `FP*` constraints but struggle more with boundary, evidence, and quantitative reasoning.
- Long-context, multi-document, high-constraint-count, and decision-boundary items are expected to be harder than simple formatting or extraction items.
- Finance-specific SFT, if run, is expected to improve instruction adherence on finance workflow constraints, but this must be tested on v2 before making any claim.

### Planned ablations

These are experiment concepts, not completed results.

| Ablation | Purpose | Expected observation |
| --- | --- | --- |
| Rule-only vs rule-plus-judge scoring | Quantify how much of the benchmark can be scored deterministically and how much needs semantic judgment. | Rule-only should have lower coverage; rule-plus-judge should provide full or near-full coverage. |
| Original benchmark prompt vs v6 rephrased prompt | Test whether more realistic prompt presentation changes model behavior. | V6 may reduce overfitting to artificial `Context:` / `Task:` wrappers and expose more natural workflow IF failures. |
| With source labels vs mixed/hidden source labels | Test robustness of citation and evidence behavior. | Explicit source labels should help citation constraints; mixed labels test whether models can follow nonstandard evidence names. |
| Low vs high constraint count | Measure instruction-load sensitivity. | Pass rate is expected to drop as constraints per item increase. |
| Rule-aided checker configs for numeric constraints | Measure benefit of adding exact expected values/tolerances. | More calibrated configs should raise deterministic coverage and reduce judge cost. |
| Judge model sensitivity | Check whether ranking changes with different judge providers. | Absolute scores may shift; robust claims should survive judge changes. |
| Finance-specific tuning, if performed | Test whether training on FinIF-style data improves v2 IF. | Expected gains should be largest on repeated workflow constraints, but this is unmeasured. |

### Planned latency, cost, and runtime reporting

Current v2 has no measured latency or cost table. The paper can still describe the design expectation:

- Local rule checks should be fast and cheap.
- Item-batched judge calls should reduce judge-call count compared with one call per constraint.
- `--hard-only` mode gives a cheap coverage estimate before paid judging.
- Strict parsing and retry add reliability overhead; report parse retry rates once measured.

Recommended runtime/cost table to fill later:

| Run | Items | Responses generated | Judge calls | Rule-decided constraints | Judge-decided constraints | Total time | Estimated cost | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| full v2 benchmark, model A | TBD | TBD | TBD | TBD | TBD | TBD | TBD | planned |
| full v2 benchmark, model B | TBD | TBD | TBD | TBD | TBD | TBD | TBD | planned |

### Conceptual expected findings for the paper

These are safe to write as motivations or hypotheses before experiments:

- Financial instruction following is not only about answer correctness; real work products also need evidence discipline, boundary control, format compliance, and operational next steps.
- A workflow-grounded benchmark should reveal failures that generic IF tests miss, especially around escalation, non-commitment, missing evidence, and quantitative verification.
- A local-first plus LLM-judge evaluator is practical for industry settings because it separates cheap mechanical checks from expensive semantic checks.
- Self-contained prompts and synthetic private records make the benchmark easier to run, audit, and share without exposing customer data.

### Known weaknesses or unstable numbers

- The current active v2 benchmark lacks completed full model scores in the repo.
- The v2 deterministic checkers are conservative and often need explicit checker configs for numeric correctness. Without configs, many QV constraints may fall back to the judge.
- Judge agreement or human calibration results are not present for v2.
- Some context manifests have failed downloads; the final data may still be self-contained, but source-collection coverage has gaps.
- `evaluation/qa_dataset.py` and the v6 rephrased benchmark have a schema mismatch: v6 is valid for evaluator input through `source_registry`, but it does not satisfy the older full-prompt QA script's required fields.
- The exact v6 rephrase generation script was not found, which weakens reproducibility for prompt-style rephrasing.

## 5. Deployment Relevance

Real-world constraints addressed:

- Privacy: private customer, borrower, account, and internal records are synthetic or mixed; public primary sources are used where appropriate.
- Grounding: prompts require use of supplied materials only, citations, source fidelity, missing/unknown handling, and fact-vs-inference separation.
- Compliance and authority boundaries: `DB*` constraints cover escalation, reporting, approval boundaries, non-commitment, regulated communication, and not overstating incomplete evidence.
- Quantitative reliability: `QV*` constraints cover formulas, thresholds, deadlines, reconciliation, stress scenarios, and verification.
- Human review: task repair shards, QA reports, dashboard/viewer artifacts, and strict schema checks support reviewer workflows.
- Cost and latency: local-first rule checks reduce LLM judge calls; item-batched judge calls evaluate all unresolved constraints for one item in a single call.
- Reliability: strict JSON judge parsing, parse retries, raw judge-output storage, optional repeated judging, coverage reporting, and hard-only mode make failures visible.

Industry Track emphasis:

- Frame the system as evaluation infrastructure for finance work products, not only a benchmark dataset.
- Emphasize workflow grounding: each item maps to real roles and operational deliverables.
- Emphasize deployability: privacy-preserving synthetic private records plus public regulatory/filing context.
- Emphasize reviewability: explicit constraints, source labels, audit metadata, dashboards, and QA reports.
- Emphasize operational metrics: constraint-level IF, coverage, quality score, family/tag breakdowns, and unresolved-constraint reporting.
- Emphasize cost-aware evaluation: deterministic rules first, LLM judge only where semantic review is needed.

## 6. Paper Risks

Missing experiments:

- Full current-v2 360-item model evaluations are missing.
- No v2 human agreement study for LLM judge or checker false-positive/false-negative rates was found.
- No v2 latency/cost table was found.
- No v2 generic-IF vs FinIF-train ablation was found.
- No robustness study across judge models was found.
- No explicit correctness-vs-instruction-following decoupling result was found for active v2.

Weak claims to avoid:

- Do not claim any model ranking until v2 scores are produced.
- Do not claim SFT improvement until v2 training/evaluation is actually run.
- Do not claim generic IF ablation evidence unless new experiments are added.
- Do not overstate rule-based quantitative correctness; many numeric constraints require explicit expected values or judge review.
- Do not call the v6 rephrase process fully reproducible unless the exact generation script is added or documented.

Sensitive or anonymization risks:

- `key.md` exists and `evaluation/run_gpt5_smoke_eval.py` can read API keys from it. Do not commit or disclose secrets.
- Some legacy docs contain local machine paths such as `/home/zyz26/...`; anonymize paths in the paper if those docs are referenced.
- API providers and internal platforms such as Vulcan, DeepSeek, SiliconFlow, and local checkpoint paths may need anonymization depending on release policy.
- Ensure all customer/person/company examples used in paper excerpts are synthetic or public. The v2 data contains synthetic personal names and fictional entities; label them clearly.
- Avoid publishing local file paths from manifests as evidence of source provenance; use public URLs and clean source IDs instead.

Results not to overstate:

- The active v2 system is benchmark-ready, but not experimentally evaluated in the checked-in artifacts.
- Judge-based quality scores are useful operational signals, not ground-truth human quality labels unless calibrated.
- Passing schema and query-diversity QA means the data is structurally ready; it does not prove every finance judgment is correct.

Recommended next steps before EMNLP Industry Track submission:

1. Run full v2 response generation for selected models on the v6 360-item benchmark.
2. Score those responses with `evaluation/evaluate_responses.py` using a fixed judge provider and report coverage.
3. Add a small human-audited calibration set for judge agreement and checker error rates.
4. Add runtime and cost logging: response generation time, rule-check time, judge-call count, judge tokens/cost, and end-to-end throughput.
5. Add or document the exact script that generated the v6 full-context mixed-source rephrased benchmark.
6. Add experiment results tables only after actual v2 runs are complete.
