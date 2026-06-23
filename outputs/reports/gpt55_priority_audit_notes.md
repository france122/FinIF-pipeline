# GPT-5.5 Priority Audit Queue

Selection logic: prioritize high-quality or high-IF failures on the main semantic tension tags, because those are the best candidates for judge-rubric tightening or benchmark text repair.

## Tag counts in GPT-5.5 hard300 fail cases

| Tag | Failed constraints | Audit focus |
|---|---:|---|
| EG2 | 107 | Key facts, thresholds, calculations, and decisions should carry active source labels at the point of use. |
| QV2 | 30 | Each required calculation should show source inputs, formula/comparison, result, and business implication. |
| DB9 | 27 | Evidence, rule, and action should form one reasoning chain rather than disconnected fragments. |
| QV5 | 7 | Date/deadline tests should show source dates, timing logic, final status, and business implication. |
| DB7 | 12 | Approver, authority evidence, prerequisite, or escalation boundary must be named explicitly. |

## Review prompts

- `EG2`: Did the response actually miss source labels at key use points, or is the judge over-penalizing perfectly readable local evidence anchoring?
- `QV2`: Is the missing piece a real calculation-lineage failure, or did the answer already imply enough formula/result context for an audit-ready reader?
- `DB9`: Is the reasoning truly fragmented, or is the judge preferring one rhetorical style over another coherent workflow style?
- `QV5`: Did the response omit timing logic, or is the requirement itself too broad for simple date-status tasks?
- `DB7`: Did the answer really miss approver/prerequisite naming, or is the packet itself underspecified and the response appropriately conservative?

## Recommended training implication

- Distillation teacher priority: `GPT-5.5` first, `GPT-5` second.
- Improvement target for smaller models: train toward evidence placement, quantitative lineage, and action-boundary closure rather than only generic report fluency.
