#!/usr/bin/env bash
# Example: evaluate model responses against FinIF-Test
#
# Prerequisites:
#   pip install openai   # only needed for LLM judge mode
#
# Response file format (JSONL):
#   {"id": "item_id", "response": "model output text"}

set -euo pipefail

DATASET="data/finif_test.jsonl"
RESPONSES="${1:?Usage: $0 <responses.jsonl> [output.json]}"
OUTPUT="${2:-results.json}"

# Rule-only mode (no LLM API needed)
python evaluation/evaluate.py \
  --dataset "$DATASET" \
  --responses "$RESPONSES" \
  --output "$OUTPUT" \
  --hard-only

echo "Results written to $OUTPUT"
echo "To run full evaluation with LLM judge, remove --hard-only and add --judge-provider"
