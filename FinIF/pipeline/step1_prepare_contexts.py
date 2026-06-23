#!/usr/bin/env python3
"""
Step 1: Context 准备
从 benchmark_all.json 提取 54 个 context，
从 eval_config_all.json 提取已有的数值和计算关系（hard constraints 里已经有了）。
纯确定性，不调 API。

输出: data/context_pool.jsonl
"""
import json, os

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = os.path.dirname(PIPELINE_DIR)


def main():
    with open(os.path.join(CURRENT_DIR, "benchmark", "benchmark_all.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    with open(os.path.join(CURRENT_DIR, "benchmark", "eval_config_all.json"), encoding="utf-8") as f:
        constraints = json.load(f)["constraints"]

    case_map = {}
    for c in cases:
        cid = c["case_id"]
        l2 = cid.split("-")[0]
        l1 = l2.split(".")[0]
        context = c["context"]
        prompt = c["prompt"]
        query = prompt[len(context):].strip() if prompt.startswith(context) else prompt

        case_map[cid] = {
            "context_id": f"CTX-{cid}",
            "case_id": cid,
            "L1": l1,
            "L2": l2,
            "source": "benchmark",
            "text": context,
            "query": query,
            "char_count": len(context),
            "extracted_values": {},
            "computable_relations": [],
        }

    for key, cfg in constraints.items():
        cid = key.split("#")[0]
        if cid not in case_map:
            continue

        if cfg["type"] == "hard":
            checker = cfg.get("checker", "")
            params = cfg.get("params", {})

            if checker == "check_value_exact":
                for k, v in params.get("expected_values", {}).items():
                    case_map[cid]["extracted_values"][k] = v

            elif checker == "check_computation_result":
                for r in params.get("results", []):
                    case_map[cid]["computable_relations"].append({
                        "label": r["label"],
                        "expected": r["expected"],
                        "tolerance": r.get("tolerance", 0.5),
                        "source_constraint": key,
                    })

            elif checker == "check_value_derivation":
                for chk in params.get("checks", []):
                    case_map[cid]["computable_relations"].append({
                        "label": chk.get("label", cfg.get("description", "")),
                        "expected": chk.get("expected"),
                        "tolerance": chk.get("tolerance", 0.01),
                        "formula": chk.get("formula", ""),
                        "source_constraint": key,
                        "derivation": True,
                    })

            elif checker == "check_ranking":
                case_map[cid]["extracted_values"]["_ranking"] = json.dumps(
                    params.get("ranking", []), ensure_ascii=False
                )

    output_file = os.path.join(PIPELINE_DIR, "data", "context_pool.jsonl")
    with open(output_file, "w", encoding="utf-8") as f:
        for cid in sorted(case_map.keys()):
            f.write(json.dumps(case_map[cid], ensure_ascii=False) + "\n")

    total_vals = sum(len(c["extracted_values"]) for c in case_map.values())
    total_rels = sum(len(c["computable_relations"]) for c in case_map.values())
    print(f"Processed {len(case_map)} contexts")
    print(f"Total extracted values: {total_vals}")
    print(f"Total computable relations: {total_rels}")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
