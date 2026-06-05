# FinIF — Conference Paper Outline

**Title:** FinIF: Can Your LLM Follow Instructions in Financial Tasks?

---

## 1. Introduction
- Finance is a high-stakes deployment domain for LLMs: tasks come with explicit source material, an explicit question, and explicit delivery requirements.
- Central claim: usability in finance depends on two independent axes — answer **correctness** and **instruction following (IF)** of delivery requirements.
- Motivation: even frontier models comply poorly with simple financial instructions (Figure 1: a strong model that is correct yet violates delivery requirements, plus an aggregate two-metric comparison).
- We present **FinIF**, comprising **FinIF-Test** (evaluation) and **FinIF-Train** (training), built by a single scalable, automatic synthesis pipeline; we score both IF and correctness via two tracks (rule/rubric checkers and an LLM judge).
- Contributions:
  1. A dual-axis (IF + correctness) financial instruction-following dataset.
  2. A scalable automatic pipeline paired with a dual-track evaluation protocol.
  3. FinIF-Train: SFT lifts an 8B model to frontier-level financial IF; data and code released.

## 2. Related Work
- 2.1 Instruction-Following Evaluation — general-domain IF benchmarks (e.g., IFEval, IFBench, AgentIF) that are non-financial and omit delivery requirements; instruction tuning and distillation lack financial IF supervision.
- 2.2 Financial Evaluation — LLM financial-capability benchmarks (e.g., FinEval, CFinBench) that emphasize correctness and overlook IF, motivating our dual-axis design.

## 3. The FinIF Dataset
> Overview sentence: FinIF consists of FinIF-Test (100 cases, 300 constraints) for evaluation and FinIF-Train (2,134 examples) for training, both produced by one pipeline.
- 3.1 Taxonomy — task taxonomy (T1–T3, 11 L2 types) and constraint taxonomy (5 families, 20 tags: F/N/L/S/C). Each constraint is annotated as rule-verifiable or rubric-based, which determines its scoring track (§4.1).
- 3.2 Data Synthesis — context, query, gradient constraint sampling (1–5 per case), conflict detection, LLM generation, assembly. Scalability is argued in the text rather than the heading.
- 3.3 Statistics — sizes of Test and Train reported separately, constraint distributions, and human-verification rates.

## 4. Evaluation
- 4.1 Dual-Track Scoring — deterministic rule checkers for verifiable constraints; an LLM judge (DS-V4-Flash, T=0) with rubrics for the rest (~90% agreement with human labels).
- 4.2 Metrics — two independently reported scores: Instruction Following (prompt-level and instruction-level pass rates) and Correctness.

## 5. Experiments
- 5.1 Setup — 10 evaluated models, judge configuration, inference details.
- 5.2 Evaluation
  - Opening sentence framing the section, then main results (10 models × IF / Correctness).
  - By-type analysis, each a boldface declarative paragraph (no subsections):
    - IF degrades as the number of constraints grows.
    - Thinking mode yields limited and inconsistent IF gains.
    - Compliance varies across task types (T1–T3) and constraint tags.
    - IF and correctness are decoupled.
- 5.3 Training
  - SFT before/after on both metrics (Qwen3-8B 62% → 77%, matching frontier models).
  - Ablation (variant B): fine-tuning the same model on a size-matched generic IF set improves FinIF-Test far less than FinIF-Train, showing the gains come from financial-domain supervision rather than instruction tuning in general.

## 6. Conclusion and Limitations
- Limitations: single Chinese financial domain, judge bias, scale, and correctness-annotation coverage.

---

## Figures and Tables
- Figure 1 — Strong-model IF failure case with a two-metric bar chart (§1).
- Figure 2 — Data synthesis pipeline (§3.2).
- Table 1 — Task taxonomy T1–T3 statistics (§3.1).
- Table 2 — Main results, 10 models × (IF / Correctness) (§5.2).
- Figure 3 — IF vs. Correctness decoupling scatter (§5.2).
- Figure 4 — IF vs. number of constraints (§5.2).
- Figure 5 — Per-tag weakness radar (§5.2).
- Figure 6 — SFT before/after on both metrics (§5.3).

---

## Locked Decisions (do not change unless the user overrides)
- Title kept as the user's original question form.
- Correctness retained; report IF and Correctness as two metrics.
- §5 split into Evaluation and Training.
- By-type analysis as declarative paragraphs, not subsections.
- Per-tag up-weighting (N3/S3/F4 ×3) — dropped.
- Ablation uses variant B: a generic IF dataset as the contrast.
- Top-level headings kept as terse nouns; emphasis lives in the prose and finding sentences.
