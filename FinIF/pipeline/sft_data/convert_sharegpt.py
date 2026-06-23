#!/usr/bin/env python3
"""将 SFT 数据转为 LLaMA Factory ShareGPT 格式"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))


with open(os.path.join(BASE, "sft_input_2134.jsonl"), encoding="utf-8") as f:
    prompts = {json.loads(l)["sample_id"]: json.loads(l)["prompt"] for l in f}

with open(os.path.join(BASE, "sft_data.jsonl"), encoding="utf-8") as f:
    responses = {json.loads(l)["trace_id"]: json.loads(l)["vulcan_output"]["llm_response"] for l in f}

with open(os.path.join(BASE, "flash_repair_v2.json"), encoding="utf-8") as f:
    repairs = json.load(f)

for sid, text in repairs.items():
    responses[sid] = text

print(f"Prompts: {len(prompts)}, Responses: {len(responses)}, Repairs applied: {len(repairs)}")

conversations = []
skipped = []
for sid in sorted(prompts.keys()):
    if sid not in responses:
        skipped.append(sid)
        continue
    resp = responses[sid]
    if not resp or not resp.strip():
        skipped.append(sid)
        continue
    conversations.append({
        "conversations": [
            {"from": "human", "value": prompts[sid]},
            {"from": "gpt", "value": resp},
        ]
    })

out_path = os.path.join(BASE, "sft_sharegpt_2132.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(conversations, f, ensure_ascii=False, indent=2)

print(f"\nOutput: {out_path}")
print(f"Total: {len(conversations)} samples")
if skipped:
    print(f"Skipped ({len(skipped)}): {skipped}")

print(f"\n--- Sample 1 ---")
s = conversations[0]
print(f"  human:  {s['conversations'][0]['value'][:80]}...")
print(f"  gpt:    {s['conversations'][1]['value'][:80]}...")

print(f"\n--- Sample 2 ---")
s = conversations[1]
print(f"  human:  {s['conversations'][0]['value'][:80]}...")
print(f"  gpt:    {s['conversations'][1]['value'][:80]}...")
