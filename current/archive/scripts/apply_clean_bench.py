#!/usr/bin/env python3
"""
将 LLM 清洗结果应用回 benchmark_all.json。

用法:
  python3 apply_clean_bench.py
  # 读 clean_output_bench.jsonl → 修改 benchmark_all.json
"""
import json, os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def extract_constraint_block(prompt):
    m = re.search(r'(\n*请在回答时严格遵守以下附加要求[：:].*$)', prompt, flags=re.DOTALL)
    return m.group(1).strip() if m else ""


def strip_constraint_block(prompt):
    return re.sub(r'\n*请在回答时严格遵守以下附加要求[：:].*$', '', prompt, flags=re.DOTALL).rstrip()


def count_existing_constraints(constraint_block):
    return len(re.findall(r'（\d+）', constraint_block))


def main():
    output_path = os.path.join(SCRIPT_DIR, "clean_output_bench_v2.jsonl")
    bench_path = os.path.join(SCRIPT_DIR, "benchmark_all.json")

    with open(output_path, encoding="utf-8") as f:
        results = {}
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj["id"]
            try:
                llm_resp = json.loads(obj["vulcan_output"]["llm_response"])
            except (json.JSONDecodeError, TypeError):
                print(f"  SKIP {cid}: invalid llm_response")
                continue
            results[cid] = llm_resp

    with open(bench_path, encoding="utf-8") as f:
        bench_data = json.load(f)

    cases = bench_data["cases"]
    edited = 0
    skipped = 0

    for case in cases:
        cid = case["case_id"]
        if cid not in results:
            continue

        resp = results[cid]
        if not resp.get("needs_edit"):
            skipped += 1
            continue

        cleaned_body = resp["cleaned_body"]
        moved = [re.sub(r'^[（(]\s*|\s*[）)]$', '', m.strip()) for m in resp.get("moved_constraints", [])]

        constraint_block = extract_constraint_block(case["prompt"])

        if constraint_block and moved:
            n = count_existing_constraints(constraint_block)
            for i, mc in enumerate(moved, start=n + 1):
                constraint_block += f"\n（{i}）{mc}"

        if constraint_block:
            new_prompt = cleaned_body.rstrip() + "\n\n" + constraint_block
        else:
            if moved:
                new_prompt = cleaned_body.rstrip() + "\n\n请在回答时严格遵守以下附加要求：\n"
                for i, mc in enumerate(moved, start=1):
                    new_prompt += f"（{i}）{mc}\n"
                new_prompt = new_prompt.rstrip()
            else:
                new_prompt = cleaned_body

        case["prompt"] = new_prompt
        edited += 1
        print(f"  {cid}: moved {moved}")

    with open(bench_path, "w", encoding="utf-8") as f:
        json.dump(bench_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {edited} edited, {skipped} unchanged, {len(cases)} total")
    print(f"  → {bench_path}")


if __name__ == "__main__":
    main()
