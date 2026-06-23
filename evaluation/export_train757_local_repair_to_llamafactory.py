#!/usr/bin/env python3
"""Export the current GPT-5 local-repair training subset to LLaMA-Factory formats.

Outputs:
- ShareGPT-style JSON with system / human / gpt turns
- Alpaca-style JSON with instruction / input / output
- dataset_info.json entries for both formats
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = ROOT / "outputs/model_runs/gpt5_train757_local_repair_subset_20260616/selected_dataset.jsonl"
RESPONSES_PATH = ROOT / "outputs/model_runs/gpt5_train757_local_repair_subset_20260616/responses_gpt5_local_repair.jsonl"
OUT_DIR = ROOT / "outputs/training/llamafactory_train621_20260616"

SYSTEM_PROMPT = (
    "You are a careful financial workflow assistant. Use only the provided materials, "
    "follow every explicit instruction in the prompt, and produce an audit-ready final answer."
)


def read_jsonl(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, rows: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(list(rows), handle, ensure_ascii=False, indent=2)


def main() -> int:
    dataset_rows = read_jsonl(DATASET_PATH)
    response_rows = {row["item_id"]: row for row in read_jsonl(RESPONSES_PATH)}

    sharegpt_rows = []
    alpaca_rows = []

    for row in dataset_rows:
        item_id = row["id"]
        response_row = response_rows.get(item_id)
        if not response_row:
            continue

        prompt = str(row.get("full_prompt") or "").strip()
        answer = str(response_row.get("response") or "").strip()
        if not prompt or not answer:
            continue

        metadata = {
            "id": item_id,
            "workflow": row.get("workflow"),
            "task": row.get("task"),
            "work_product": row.get("work_product"),
            "line_number": row.get("line_number"),
            "repair_status": response_row.get("repair_status"),
        }

        sharegpt_rows.append(
            {
                "conversations": [
                    {"from": "system", "value": SYSTEM_PROMPT},
                    {"from": "human", "value": prompt},
                    {"from": "gpt", "value": answer},
                ],
                **metadata,
            }
        )

        alpaca_rows.append(
            {
                "instruction": prompt,
                "input": "",
                "output": answer,
                **metadata,
            }
        )

    sharegpt_path = OUT_DIR / "finif_train621_sharegpt.json"
    alpaca_path = OUT_DIR / "finif_train621_alpaca.json"
    info_path = OUT_DIR / "dataset_info.json"
    manifest_path = OUT_DIR / "manifest.json"

    write_json(sharegpt_path, sharegpt_rows)
    write_json(alpaca_path, alpaca_rows)

    dataset_info = {
        "finif_train621_sharegpt": {
            "file_name": sharegpt_path.name,
            "formatting": "sharegpt",
            "columns": {"messages": "conversations"},
            "tags": {
                "role_tag": "from",
                "content_tag": "value",
                "user_tag": "human",
                "assistant_tag": "gpt",
                "system_tag": "system",
            },
        },
        "finif_train621_alpaca": {
            "file_name": alpaca_path.name,
            "formatting": "alpaca",
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output",
            },
        },
    }
    write_json(info_path, dataset_info.items())
    # Re-write dataset_info as a mapping rather than a list.
    info_path.write_text(json.dumps(dataset_info, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "source_dataset": str(DATASET_PATH),
        "source_responses": str(RESPONSES_PATH),
        "output_dir": str(OUT_DIR),
        "samples": len(sharegpt_rows),
        "system_prompt": SYSTEM_PROMPT,
        "files": {
            "sharegpt": str(sharegpt_path),
            "alpaca": str(alpaca_path),
            "dataset_info": str(info_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
