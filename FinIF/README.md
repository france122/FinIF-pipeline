# FinIF: Can Your LLMs Follow Instructions in Financial Tasks?

## Overview

FinIF is a benchmark for evaluating instruction-following (IF) ability of large language models in realistic financial workflows. Unlike general-purpose IF benchmarks, FinIF targets **domain-specific, multi-constraint instructions** drawn from real financial work products — compliance memos, risk assessments, investment reports, audit checklists, and more.

FinIF features an **automated data pipeline** that synthesizes diverse, constraint-rich financial instructions:

1. **Context Acquisition** — Retrieves real regulatory documents, financial filings, and market data to serve as grounding context.
2. **Query Synthesis** — Generates realistic financial task queries seeded from the O\*NET occupational database, covering 38 task types across 5 financial workflows.
3. **Constraint Annotation** — Automatically annotates each query with fine-grained IF constraints organized into a 4-family taxonomy.

The benchmark employs a **hybrid verification engine**: deterministic Python rule-checkers handle mechanically verifiable constraints (keyword presence, table structure, numeric values, etc.), while calibrated LLM judges evaluate semantic constraints that require contextual understanding.

## Dataset Statistics

| Statistic | Value |
|-----------|-------|
| Test instructions | 307 |
| Total IF constraints | 3,282 |
| Avg. constraints per instruction | 10.7 |
| Avg. prompt length (words) | 680 |
| Task types | 38 |
| Financial workflows | 5 |
| Train samples (SFT) | 621 |

## Contents

```
FinIF/
├── README.md
├── data/
│   ├── finif_test.jsonl              # 307 test instructions with constraints
│   ├── finif_train.json              # 621 SFT training samples (ShareGPT format)
│   └── constraint_taxonomy.md        # 4-family constraint taxonomy
├── evaluation/
│   ├── rule_checkers.py              # ~50 deterministic rule checkers
│   ├── evaluate.py                   # Main evaluation script (rule + LLM judge)
│   └── evaluator_config.json         # Evaluation config with judge prompt
└── examples/
    └── run_evaluation.sh             # Example evaluation command
```

## Constraint Taxonomy

Constraints are organized into 4 families:

| Family | Share | Description |
|--------|-------|-------------|
| Format & Presentation (FP) | 44.3% | Structure, format, length, terminology, tone, and layout requirements |
| Decision & Boundary (DB) | 22.7% | Decisions, escalation triggers, classification, and regulatory boundaries |
| Evidence & Grounding (EG) | 20.8% | Citations, source fidelity, content coverage, and factual grounding |
| Quantitative Verification (QV) | 12.1% | Calculations, thresholds, deadlines, reconciliation, and numeric accuracy |

See `data/constraint_taxonomy.md` for the full taxonomy with all fine-grained tags.

## Financial Workflows

| Workflow | Test Items |
|----------|-----------|
| Intake and Profiling | 61 |
| Research and Due Diligence | 61 |
| Decision and Structuring | 61 |
| Risk and Compliance Review | 62 |
| Execution, Monitoring, Reporting, and Operations | 62 |

## Evaluation Metrics

**ISR (Instruction-level Satisfaction Rate)** — the primary metric. An instruction is satisfied only if **all** of its IF constraints pass. ISR is the fraction of instructions that are fully satisfied:

$$\text{ISR} = \frac{|\{i : \text{all constraints of instruction } i \text{ pass}\}|}{N}$$

**CSR (Constraint-level Satisfaction Rate)** — a softer metric that measures the overall fraction of individual constraints that pass:

$$\text{CSR} = \frac{\sum_{i} \text{passed}(i)}{\sum_{i} \text{total}(i)}$$

**Quality Score** — a holistic content quality score (0–10) assigned by the LLM judge, evaluating accuracy, completeness, and decision-usefulness of the response independent of IF constraints.

## Data Schema

### Test Items (`finif_test.jsonl`)

Each line is a JSON object with:

| Field | Description |
|-------|-------------|
| `id` | Unique instruction identifier |
| `full_prompt` | Self-contained prompt (context documents + task query + IF constraints) |
| `workflow` | Financial workflow category |
| `task` | Task type (one of 38) |
| `work_product` | Requested deliverable type |
| `extracted_constraints` | List of IF constraints, each with `constraint`, `tag`, `family`, `check_type` |
| `diagnostic_constraints` | Auxiliary quality constraints (not counted in ISR/CSR) |
| `source_registry` | Provenance of embedded context documents |

### Train Items (`finif_train.json`)

Each item contains:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `conversations` | ShareGPT format: `[{role, content}, ...]` (system, user, assistant) |
| `workflow` | Financial workflow category |
| `task` | Task type |
| `work_product` | Deliverable type |
| `repair_status` | Whether the teacher response was repaired for constraint compliance |

## Evaluation

### Setup

The evaluation pipeline has two tracks:

1. **Rule-based checkers** (`evaluation/rule_checkers.py`): ~50 deterministic Python functions for mechanically verifiable constraints. Each checker returns pass, fail, or `needs_judge` when uncertain.

2. **LLM judge** (`evaluation/evaluator_config.json`): For semantic constraints and unresolved rule checks. The judge evaluates all pending constraints for an instruction in a single batched call, returning binary pass/fail per constraint plus a holistic quality score.

### Running Evaluation

```bash
# Rule-only evaluation (no LLM API needed)
python evaluation/evaluate.py \
  --dataset data/finif_test.jsonl \
  --responses your_responses.jsonl \
  --output results.json \
  --hard-only

# Full evaluation with LLM judge
python evaluation/evaluate.py \
  --dataset data/finif_test.jsonl \
  --responses your_responses.jsonl \
  --output results.json \
  --judge-provider your_judge_module:YourJudgeClass
```

### Response Format

Prepare model responses as a JSONL file where each line contains:

```json
{"id": "<matching instruction id>", "response": "<model output>"}
```

## License

This dataset is released for research purposes.
