# EMNLP Industry 2026 Submission Plan

Working timezone: Asia/Shanghai.

Official submission deadline: June 16, 2026, 23:59 AoE, which is June 17, 2026, 19:59 in China.

## Paper Positioning

Primary paper-facing version: FinIF v2 / hard300.

Working title:

> FinIF: Can Large Language Models Follow Instructions in Financial Tasks?

Core claim:

> Reliable financial LLM deployment requires not only producing plausible financial content, but also satisfying workflow-specific delivery requirements: evidence placement, decision boundaries, quantitative lineage, formatting, escalation, and missing-evidence handling.

Current strongest result:

- GPT-5 on hard300 IF-clean: 300 items, 3,134 IF constraints, 100% evaluation coverage.
- Micro IF: 91.32%.
- Macro item IF: 91.17%.
- Strict item pass rate / ISR: 47.0% (141/300).
- Mean quality: 7.05/10.

This gives the key story: a strong model can satisfy most individual constraints while failing more than half of fully compliant financial work products under strict item-level delivery criteria.

## Version Discipline

Use these terms consistently:

- FinIF v2 full pool: 1,064 workflow-grounded items, 38 task types, 7,851 constraints.
- FinIF-Test / hard300: 300 selected hard items, all 5 workflows, 38/38 task types.
- IF-clean benchmark: 3,134 IF constraints; 1,788 LLM-judged and 1,346 rule-checked constraints.
- Diagnostic axes: coverage, finance validity, and quality are auxiliary; they should not replace IF / compliance as the main metric.

Avoid mixing the older 100-case Chinese FinIF results into the main story unless explicitly framed as preliminary or as an older pilot. If today's SFT result is only available on the older benchmark, treat it as secondary evidence, not the headline result.

## Experiment Gate

Before claiming any new result:

1. Confirm the dataset path and response path.
2. Confirm evaluation coverage is 100%.
3. Report ISR from `summary.exact_item_pass_rate`, not `final_score_0_1`.
4. Record micro IF, macro item IF, mean quality, and failure counts by tag.
5. For any SFT claim, state whether it is evaluated on hard300 IF-clean or on the older 100-case benchmark.

Highest-priority experiments:

- Main hard300 baseline table: GPT-5 plus at least 2-3 additional models if API budget permits.
- SFT experiment: Qwen3-8B base vs Qwen3-8B-SFT on the same benchmark split.
- Constraint-load analysis: ISR / micro IF by number of IF constraints per item.
- Failure taxonomy: EG2, FP3, QV2, DB9, QV5 as headline failure modes for GPT-5 hard300.
- Judge/checker calibration: small human audit or double-judge sanity check if time permits.

## Reverse Schedule

### June 14, 2026

Goal: freeze the experimental story.

- Finish benchmark scoring needed for the main table.
- Run or confirm SFT evaluation on the selected benchmark.
- Generate failure summaries by tag, family, rule-vs-judge, and task/workflow.
- Select Figure 1 case: a strong-model failure that is financial, not just JSON/format failure.
- Write the 180-220 word abstract and the Introduction claim chain.
- Freeze names for dataset versions, metrics, and model labels.

Decision by end of day:

- If SFT on hard300 is complete: headline "FinIF-style SFT improves financial IF."
- If not complete: headline benchmark/evaluation infrastructure; old SFT is only a pilot or appendix result.

### June 15, 2026

Goal: write the paper core.

- Finish Introduction, Related Work, Dataset, and Evaluation sections.
- Build the main result table and 2-3 core figures.
- Write experiment narrative around three findings:
  - Strong models have high micro IF but low strict item pass.
  - Failures concentrate in evidence placement, quantitative lineage, and decision-boundary constraints.
  - SFT improves IF if same-split results are available.
- Add a short reproducibility paragraph: data construction, checker/judge routing, strict JSON judge parsing, and coverage reporting.

### June 16, 2026

Goal: produce submission-ready PDF.

- Finish Experiments, Limitations, Ethics, and Conclusion.
- Compress to page limit; move secondary details to appendix.
- Verify all numbers against JSON artifacts.
- Check anonymization, source labels, secret/path leakage, and whether model/provider names can be disclosed.
- Final pass on figures, tables, references, and PDF formatting.
- Upload a complete draft well before midnight China time, even if final polish continues after.

### June 17, 2026, before 19:59 China time

Goal: submission buffer, not writing from scratch.

- Final PDF compile and OpenReview metadata.
- Check author list, abstract, title, keywords, PDF page count, supplementary files.
- Submit no later than 18:00 China time if possible.

## Paper Skeleton

1. Introduction
   - Financial workflows require grounded work products plus explicit delivery constraints.
   - Existing financial benchmarks emphasize correctness; generic IF benchmarks lack financial workflow constraints.
   - FinIF evaluates whether LLMs can produce compliant financial deliverables.
   - Contributions: dataset/pipeline, dual evaluator, hard300 results, optional SFT evidence.

2. Related Work
   - Instruction Following of LLMs.
   - Financial Capabilities of LLMs.

3. FinIF
   - Workflow taxonomy: 5 workflows, 38 task types.
   - Constraint taxonomy: format, evidence, decision/boundary, quantitative verification, required content.
   - Data construction: context, query, constraints, repair/QA, hard selection.
   - Dataset statistics.

4. Evaluation Protocol
   - IF-clean main axis.
   - Rule checkers for mechanical constraints.
   - Item-batched LLM judge for semantic constraints.
   - Metrics: micro IF, macro item IF, strict item pass rate / ISR, coverage, quality.

5. Experiments
   - Setup.
   - Main results.
   - Failure analysis.
   - SFT or training result, if complete.
   - Optional calibration/robustness.

6. Limitations and Conclusion
   - Judge dependence, synthetic private records, source coverage, model/provider availability, cost, human calibration limits.

## Immediate Writing Ideas

- Figure 1 should show a financial compliance failure, not a generic formatting failure.
- The strongest narrative contrast is micro IF vs strict item pass: "mostly compliant" is not enough for production handoff.
- Treat citation placement as evidence discipline, not cosmetic citation formatting.
- Use "delivery requirements" or "workflow-specific delivery constraints" for industry readers; reserve "instruction following" for benchmark framing.
- Do not overclaim financial correctness. Keep "finance validity / task quality" auxiliary unless we have audited labels.

## Collaboration Loop

For each section, use a tight loop:

1. I propose the claim and paragraph structure.
2. You correct the intended story or provide missing experimental facts.
3. I draft the section in paper style.
4. We compress, check numbers, and lock it.

Recommended next section to draft first: Abstract, then Introduction.
