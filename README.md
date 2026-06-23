# FinIF: Can Your LLMs Follow Instructions in Financial Tasks?

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

**FinIF** is a benchmark and evaluation framework for measuring how well large language models (LLMs) follow complex, multi-constraint instructions in realistic financial workflows. Unlike general-purpose instruction-following benchmarks (e.g., IFEval), FinIF targets **domain-specific, constraint-rich instructions** drawn from real financial work products — compliance memos, risk assessments, investment reports, audit checklists, and regulatory filings.

Key features:
- **307 test instructions** with **3,282 IF constraints** (avg. 10.7 per instruction)
- **38 task types** across **5 financial workflows** covering the full financial service lifecycle
- **4-family constraint taxonomy** (Format & Presentation, Decision & Boundary, Evidence & Grounding, Quantitative Verification)
- **Hybrid evaluation engine**: deterministic rule checkers + calibrated LLM judges
- **SFT training pipeline**: 621 teacher-generated training samples for instruction-tuning
- **8-model leaderboard**: GPT-5.5, GPT-5, DeepSeek-V4, GLM-5.1, Qwen3.5 series

## Project Structure

```
FinIF-pipeline/
│
├── README.md
├── FinIF/                             # Benchmark package (data + evaluator)
│   ├── data/
│   │   ├── finif_test.jsonl           # 307 test instructions with constraints
│   │   ├── finif_train.json           # 621 SFT training samples (ShareGPT)
│   │   └── constraint_taxonomy.md     # 4-family constraint taxonomy
│   ├── evaluation/
│   │   ├── evaluate.py                # Main evaluation script
│   │   └── rule_checkers.py           # ~50 deterministic rule checkers
│   └── examples/
│       └── run_evaluation.sh
│
├── evaluation/                        # Full evaluation pipeline
│   ├── checkers.py                    # Extended rule-checker library (~1400 lines)
│   ├── evaluate_responses.py          # Item-level evaluator (rule + LLM judge)
│   ├── evaluator_spec.json            # Evaluation spec with judge prompts
│   ├── run_gpt5_*.py                  # GPT-5/5.5 evaluation runners
│   ├── run_deepseek_*.py              # DeepSeek-V4 evaluation runners
│   ├── run_siliconflow_*.py           # Qwen/GLM evaluation via SiliconFlow
│   ├── build_model_results_table.py   # Leaderboard table generation
│   ├── build_paper_figure1.py         # Paper Figure 1 (case study)
│   ├── plot_finif_test_data_statistics.py
│   ├── analyze_benchmark307_vs_ifeval.py
│   └── ...
│
├── current/                           # Data construction & SFT pipeline
│   ├── sft_pipeline/                  # Full data construction pipeline
│   │   ├── step1_prepare_contexts.py
│   │   ├── step3_assemble_constraints.py
│   │   ├── step4_scale_to_2000.py
│   │   ├── step5_export.py
│   │   ├── step6_expand_benchmark.py
│   │   ├── step8_redistribute.py
│   │   ├── step9_gen_sft_responses.py
│   │   └── gen_constraint_text.py
│   ├── sft_data/                      # SFT data repair pipeline
│   │   ├── iterative_repair.py
│   │   ├── verify_repairs.py
│   │   └── convert_sharegpt.py
│   ├── checkers.py                    # Constraint checker library
│   ├── gen_responses_ds.py            # Multi-model response generation
│   ├── gen_async.py                   # Async parallel generation
│   ├── score_sft_responses.py         # SFT quality scoring
│   ├── plot_radar.py                  # Radar chart visualization
│   └── build_stats.py                 # Statistics dashboard
│
└── outputs/                           # Generated figures
    ├── paper_figures/
    │   ├── scripts/                   # Figure generation scripts
    │   └── pdf/                       # Output PDFs
    ├── figures/                       # Analysis figures (PNG + PDF)
    └── analysis/                      # Comparative analysis outputs
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
step6_expand_benchmark.py ── Expand benchmark (54 → ~100 items)
  │                           using real regulatory documents
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
evaluate_responses.py ── Item-level hybrid evaluation
  │
  ├── Rule Checkers (checkers.py)
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
| `build_stats.py` | Interactive HTML benchmark statistics dashboard |
| `analyze_benchmark307_vs_ifeval.py` | FinIF vs IFEval comparative analysis |
| `build_model_results_table.py` | Markdown leaderboard table generation |

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
cd FinIF
python evaluation/evaluate.py \
  --dataset data/finif_test.jsonl \
  --responses your_responses.jsonl \
  --output results.json \
  --hard-only

# 3. Full evaluation with LLM judge
python evaluation/evaluate.py \
  --dataset data/finif_test.jsonl \
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

# Step 1: Prepare contexts
python current/sft_pipeline/step1_prepare_contexts.py

# Step 3: Assemble constraints
python current/sft_pipeline/step3_assemble_constraints.py

# Step 4: Scale to 2000+ samples
python current/sft_pipeline/step4_scale_to_2000.py

# Step 5: Export training format
python current/sft_pipeline/step5_export.py

# Step 9: Generate teacher responses
python current/sft_pipeline/step9_gen_sft_responses.py \
  --mode training --model gpt-5 --n 3

# Score and repair
python current/score_sft_responses.py score --judge-workers 20
python current/sft_data/iterative_repair.py
python current/sft_data/convert_sharegpt.py
```

### Generate Paper Figures

```bash
# All figure scripts output to outputs/paper_figures/pdf/
python outputs/paper_figures/scripts/fig_finif_constraint_taxonomy.py
python outputs/paper_figures/scripts/fig_finif_prompt_length.py
python outputs/paper_figures/scripts/fig_response_length_boxplot.py
python outputs/paper_figures/scripts/fig_sft_isr_by_workflow.py

# Additional analysis figures
python evaluation/build_paper_figure1.py
python evaluation/plot_finif_test_data_statistics.py
python current/plot_radar.py
```

## Paper Figures

| Figure | Script | Description |
|--------|--------|-------------|
| Constraint Taxonomy | `fig_finif_constraint_taxonomy.py` | Donut chart of 4-family constraint distribution |
| Prompt Length Distribution | `fig_finif_prompt_length.py` | FinIF vs IFEval prompt length comparison (log-log) |
| Response Length | `fig_response_length_boxplot.py` | Boxplot of response word counts across 8 models |
| SFT Improvement | `fig_sft_isr_by_workflow.py` | Before/after SFT ISR by workflow + quality score |
| Case Study (Figure 1) | `build_paper_figure1.py` | GPT-5.5 IF failure case study |
| Test Data Statistics | `plot_finif_test_data_statistics.py` | Prompt length + constraint count distributions |
| Radar Chart | `plot_radar.py` | Model pass rate by constraint sub-category |

## Dependencies

```bash
pip install openai matplotlib numpy
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
