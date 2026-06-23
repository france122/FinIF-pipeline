# FinIF: Can Your LLMs Follow Instructions in Financial Tasks?

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

**FinIF** is a benchmark and evaluation framework for measuring how well large language models (LLMs) follow complex, multi-constraint instructions in realistic financial workflows. Unlike general-purpose instruction-following benchmarks (e.g., IFEval), FinIF targets **domain-specific, constraint-rich instructions** drawn from real financial work products — compliance memos, risk assessments, investment reports, audit checklists, and regulatory filings.

Key features:
- **307 test instructions** with **3,282 IF constraints** (avg. 10.7 per instruction)
- **38 task types** across **5 financial workflows** covering the full financial service lifecycle
- **4-family constraint taxonomy**: Format & Presentation, Decision & Boundary, Evidence & Grounding, Quantitative Verification
- **Hybrid evaluation engine**: deterministic rule checkers (~50 Python functions) + calibrated LLM judges
- **SFT training pipeline**: 621 teacher-generated training samples for instruction-tuning
- **8-model leaderboard**: GPT-5.5, GPT-5, DeepSeek-V4, GLM-5.1, Qwen3.5 series

## Project Structure

```
FinIF-pipeline/
├── README.md
└── FinIF/
    ├── data/                              # Benchmark data
    │   ├── finif_test.jsonl               # 307 test instructions with constraints
    │   ├── finif_train.json               # 621 SFT training samples (ShareGPT)
    │   └── constraint_taxonomy.md         # 4-family constraint taxonomy (26 tags)
    │
    ├── evaluation/                        # Evaluation engine
    │   ├── evaluate.py                    # Main evaluation entry point
    │   ├── rule_checkers.py               # ~50 deterministic rule checkers (1391 lines)
    │   ├── checkers.py                    # Alias of rule_checkers (for import compat)
    │   ├── evaluator_spec.json            # Evaluation spec with judge prompts
    │   ├── checker_probe.py               # Checker coverage analysis
    │   ├── routing_audit.py               # Constraint → checker routing audit
    │   ├── build_model_results_table.py   # Leaderboard table generation
    │   ├── build_paper_figure1.py         # Paper Figure 1 (case study)
    │   ├── build_dashboard.py             # HTML evaluation dashboard
    │   ├── plot_finif_test_data_statistics.py
    │   ├── analyze_benchmark307_vs_ifeval.py
    │   ├── run_gpt5_*.py                  # GPT-5/5.5 evaluation runners
    │   ├── run_deepseek_*.py              # DeepSeek-V4 evaluation runners
    │   ├── run_siliconflow_*.py           # Qwen/GLM evaluation via SiliconFlow
    │   └── ...                            # SFT repair & export utilities
    │
    ├── pipeline/                          # Data construction & SFT pipeline
    │   ├── step1_prepare_contexts.py      # Extract & normalize financial contexts
    │   ├── step3_assemble_constraints.py  # Sample IF constraints per query
    │   ├── step4_scale_to_2000.py         # Scale to 2000+ training samples
    │   ├── step5_export.py                # Export to messages format
    │   ├── step6_expand_benchmark.py      # Expand benchmark with regulatory docs
    │   ├── step8_redistribute.py          # Redistribute train/test split
    │   ├── step9_gen_sft_responses.py     # Generate teacher responses (GPT-5)
    │   ├── gen_responses_ds.py            # Multi-model response generation
    │   ├── gen_async.py                   # Async parallel generation
    │   ├── score_sft_responses.py         # SFT quality scoring + LLaMA-Factory export
    │   ├── plot_radar.py                  # Radar chart visualization
    │   ├── build_stats.py                 # Statistics dashboard
    │   ├── trim_constraints.py            # Constraint trimming utility
    │   ├── dashboard.py                   # HTTP server-based dashboard
    │   ├── sft_data/                      # SFT data repair pipeline
    │   │   ├── iterative_repair.py        # Iterative constraint repair
    │   │   ├── async_repair.py            # Async batch repair
    │   │   ├── repair_round3.py           # Round 3 repair
    │   │   ├── verify_repairs.py          # Verify repair quality
    │   │   └── convert_sharegpt.py        # Export to ShareGPT format
    │   ├── scripts/                       # Parameterization scripts
    │   ├── visualization/                 # HTML chart generators
    │   └── *.drawio                       # Pipeline architecture diagrams
    │
    ├── figures/                           # Paper figures & analysis
    │   ├── fig_finif_constraint_taxonomy.py
    │   ├── fig_finif_prompt_length.py
    │   ├── fig_response_length_boxplot.py
    │   ├── fig_sft_isr_by_workflow.py
    │   ├── pdf/                           # Output PDFs
    │   └── analysis/                      # Analysis figures (PNG + PDF)
    │
    └── raw_contexts/                      # Source financial documents
        ├── *.pdf                           # SEC, FDIC, FinCEN, 证监会, 上市公司公告
        ├── *.png                           # Statistical bureau data screenshots
        └── *.md                            # Court case documents
```

## Pipeline Flow

The complete FinIF pipeline consists of 4 major phases:

### Phase 1: Data Construction

```
Real Financial Documents (SEC, FDIC, FinCEN, 证监会, 上市公司公告)
  │
  ▼
step1_prepare_contexts.py ── Extract & normalize contexts
  │
  ▼
step3_assemble_constraints.py ── Sample IF constraints per query
  │                               (visible constraints + hidden checkers)
  ▼
step4_scale_to_2000.py ── Scale to 2000+ training samples
  │                        (strict context partition: A=benchmark, B=training)
  ▼
step5_export.py ── Export to messages format
  │
  ▼
step6_expand_benchmark.py ── Expand benchmark using real regulatory documents
  │
  ▼
step8_redistribute.py ── Redistribute contexts (train/test split)
```

### Phase 2: Teacher Response Generation & SFT Data

```
step9_gen_sft_responses.py ── Generate N candidate responses per query
  │                            via teacher model (GPT-5)
  ▼
score_sft_responses.py ── Score with rule checkers + LLM judge
  │
  ▼
iterative_repair.py ── Repair failed constraints iteratively
  │
  ▼
verify_repairs.py ── Verify repair quality
  │
  ▼
convert_sharegpt.py ── Export to LLaMA-Factory ShareGPT format
```

### Phase 3: Evaluation

```
Model Response (any LLM)
  │
  ▼
evaluate.py ── Item-level hybrid evaluation
  │
  ├── Rule Checkers (rule_checkers.py)
  │   └── ~50 deterministic Python functions
  │       (JSON validity, keyword presence, table structure,
  │        word count, numeric precision, section headings, ...)
  │
  └── LLM Judge
      └── Batched semantic evaluation
          (per-constraint binary score + holistic quality 0-10)
  │
  ▼
Metrics: ISR / CSR / Quality Score
```

### Phase 4: Analysis & Visualization

| Script | Output |
|--------|--------|
| `fig_finif_constraint_taxonomy.py` | Constraint taxonomy donut chart |
| `fig_finif_prompt_length.py` | FinIF vs IFEval prompt length distribution (log-log) |
| `fig_response_length_boxplot.py` | Response length boxplot across 8 models |
| `fig_sft_isr_by_workflow.py` | SFT ISR improvement by workflow (before/after) |
| `build_paper_figure1.py` | Paper Figure 1: case study of GPT-5.5 IF failures |
| `plot_finif_test_data_statistics.py` | Test data statistics (prompt length + constraint count) |
| `plot_radar.py` | Radar chart: model performance by constraint type |
| `analyze_benchmark307_vs_ifeval.py` | FinIF vs IFEval comparative analysis |

## Evaluation Metrics

### ISR (Instruction-level Satisfaction Rate)

The primary metric. An instruction is satisfied only if **all** of its IF constraints pass:

$$\text{ISR} = \frac{|\{i : \text{all constraints of } i \text{ pass}\}|}{N}$$

### CSR (Constraint-level Satisfaction Rate)

A softer metric that measures the fraction of individual constraints that pass:

$$\text{CSR} = \frac{\sum_{i} \text{passed}(i)}{\sum_{i} \text{total}(i)}$$

### Quality Score

A holistic content quality score (0–10) assigned by the LLM judge, evaluating accuracy, completeness, and decision-usefulness independent of IF constraints.

## Leaderboard (FinIF-Test, 307 Items)

| Model | ISR ↑ | CSR | Quality (0-10) |
|-------|-------|-----|----------------|
| GPT-5.5 | 48.86% | 92.20% | 7.09 |
| GPT-5 | 32.90% | 90.44% | 7.47 |
| GLM-5.1 | 19.22% | 81.81% | 4.99 |
| DS-V4-Pro | 14.66% | 81.38% | 5.03 |
| DS-V4-Flash | 9.45% | 78.31% | 4.69 |
| Qwen3.5-27B | 7.17% | 77.79% | 4.08 |
| Qwen3.5-9B | 3.58% | 71.85% | 3.76 |
| Qwen3.5-4B | 0.65% | 62.16% | 3.82 |

> Even GPT-5.5 achieves only ~49% ISR, highlighting the difficulty of satisfying all constraints simultaneously in complex financial tasks.

## Constraint Taxonomy

| Family | Share | Description |
|--------|-------|-------------|
| Format & Presentation (FP) | 44.3% | Structure, format, length, terminology, tone, layout |
| Decision & Boundary (DB) | 22.7% | Decisions, escalation, classification, regulatory boundaries |
| Evidence & Grounding (EG) | 20.8% | Citations, source fidelity, content coverage, factual grounding |
| Quantitative Verification (QV) | 12.1% | Calculations, thresholds, deadlines, reconciliation, numeric accuracy |

See [`FinIF/data/constraint_taxonomy.md`](FinIF/data/constraint_taxonomy.md) for the full taxonomy with 26 fine-grained tags.

## Financial Workflows

| Workflow | Code | Test Items |
|----------|------|-----------|
| Intake and Profiling | T1 | 61 |
| Research and Due Diligence | T2 | 61 |
| Decision and Structuring | T3 | 61 |
| Risk and Compliance Review | T4 | 62 |
| Execution, Monitoring, Reporting, and Operations | T5 | 62 |

## Quick Start

### Evaluate Your Model

```bash
# 1. Generate responses (JSONL: {"id": "...", "response": "..."})
#    Each id must match an instruction id in finif_test.jsonl

# 2. Rule-only evaluation (no LLM API needed)
python FinIF/evaluation/evaluate.py \
  --dataset FinIF/data/finif_test.jsonl \
  --responses your_responses.jsonl \
  --output results.json \
  --hard-only

# 3. Full evaluation with LLM judge
python FinIF/evaluation/evaluate.py \
  --dataset FinIF/data/finif_test.jsonl \
  --responses your_responses.jsonl \
  --output results.json \
  --judge-provider your_judge_module:YourJudgeClass
```

### Run the Full Pipeline

```bash
# Set API keys as environment variables
export DEEPSEEK_API_KEY="your-deepseek-key"
export SILICONFLOW_API_KEY="your-siliconflow-key"
export OPENAI_API_KEY="your-openai-key"

# Phase 1: Data Construction
python FinIF/pipeline/step1_prepare_contexts.py
python FinIF/pipeline/step3_assemble_constraints.py
python FinIF/pipeline/step4_scale_to_2000.py
python FinIF/pipeline/step5_export.py
python FinIF/pipeline/step6_expand_benchmark.py
python FinIF/pipeline/step8_redistribute.py

# Phase 2: Teacher Response Generation
python FinIF/pipeline/step9_gen_sft_responses.py --mode training --model gpt-5 --n 3
python FinIF/pipeline/score_sft_responses.py score --judge-workers 20
python FinIF/pipeline/sft_data/iterative_repair.py
python FinIF/pipeline/sft_data/convert_sharegpt.py

# Phase 4: Generate Figures
python FinIF/figures/fig_finif_constraint_taxonomy.py
python FinIF/figures/fig_finif_prompt_length.py
python FinIF/figures/fig_response_length_boxplot.py
python FinIF/figures/fig_sft_isr_by_workflow.py
```

## Dependencies

```bash
pip install openai matplotlib numpy aiofiles
# Optional: for IFEval comparison
pip install datasets
```

## Data Schema

### Test Items (`FinIF/data/finif_test.jsonl`)

| Field | Description |
|-------|-------------|
| `id` | Unique instruction identifier |
| `full_prompt` | Self-contained prompt (context + query + constraints) |
| `workflow` | Financial workflow category |
| `task` | Task type (one of 38) |
| `work_product` | Requested deliverable type |
| `extracted_constraints` | List of IF constraints with `constraint`, `tag`, `family`, `check_type` |
| `diagnostic_constraints` | Quality constraints (not counted in ISR/CSR) |
| `source_registry` | Provenance of context documents |

### Train Items (`FinIF/data/finif_train.json`)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `conversations` | ShareGPT format: `[{role, content}, ...]` |
| `workflow` | Financial workflow category |
| `task` | Task type |
| `work_product` | Deliverable type |
| `repair_status` | Whether the teacher response was repaired |

## Raw Context Sources

The `FinIF/raw_contexts/` directory contains the original financial documents used to construct benchmark instructions, including:
- 中国证监会 administrative penalty decisions and market ban orders
- Listed company annual report summaries (年度报告摘要)
- Stock trading risk warning announcements
- Exchange inquiry letters (问询函)
- National Bureau of Statistics data releases
- Supreme Court case compilations

## License

This project is released for research purposes.

## Citation

If you use FinIF in your research, please cite:

```bibtex
@misc{finif2026,
  title={FinIF: Can Your LLMs Follow Instructions in Financial Tasks?},
  year={2026},
}
```
