"""
Stage 1 — 为 test split 生成 Vulcan input JSONL，用于 GPT-5.1 回复生成。

无 system prompt，仅发送 user message（query + 附加要求）。
"""

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = (
    REPO_ROOT
    / "data"
    / "tracks"
    / "ds_5500_run1_materialized"
    / "id_heldout_all_tracks_filled.json"
)
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "input.jsonl"

DATA_VERSION = "1650_v2"
TASK_NAME = "eval_response_test"

PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Vulcan input JSONL — Stage 1 response generation (test split, no SP)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--tracks",
        nargs="*",
        choices=["Hard-track", "Soft-track", "Mixed-track"],
        help="Optional track filter.",
    )
    parser.add_argument(
        "--exclude-high-risk",
        action="store_true",
        help="Exclude high-risk samples (19 findiag meta-question queries).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Record limit for smoke test.")
    return parser.parse_args()


def load_samples(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_to_record(sample: dict) -> dict:
    """将一条 track sample 转为 Vulcan input record。不加 system message。"""
    prompt = sample["prompt"]
    constraints = []
    for c in sample.get("constraints", []):
        constraints.append(
            {
                "id": c["id"],
                "type": c["type"],
                "text": c.get("rendered_text") or c["text"],
                "is_parametric": c.get("is_parametric", False),
                "filled_params": c.get("filled_params"),
            }
        )

    return {
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "metadata": {
            "task_name": TASK_NAME,
            "data_version": DATA_VERSION,
            "sample_id": sample["sample_id"],
            "query_id": sample["query_id"],
            "split": sample["split"],
            "track": sample["track"],
            "source_type": sample.get("source_type"),
            "origin_task": sample.get("origin_task"),
            "template_id": sample.get("template_id"),
            "template_name": sample.get("template_name"),
            "role_mode": sample.get("role_mode"),
            "role": sample.get("role"),
            "title": sample.get("title"),
            "material_type": sample.get("material_type"),
            "query_input": sample.get("query_input"),
            "base_query_input": sample.get("base_query_input"),
            "rendered_prompt": prompt,
            "constraint_ids": sample.get("constraint_ids", []),
            "parametric_constraint_ids": sample.get("parametric_constraint_ids", []),
            "constraints": constraints,
            "quality_review": sample.get("quality_review"),
        },
    }


def main() -> None:
    args = parse_args()
    samples = load_samples(args.input)

    # 只保留 test split
    samples = [s for s in samples if s["split"] == "test"]

    if args.tracks:
        track_set = set(args.tracks)
        samples = [s for s in samples if s["track"] in track_set]

    if args.exclude_high_risk:
        before = len(samples)
        samples = [
            s for s in samples
            if s.get("quality_review", {}).get("risk_level") != "high"
        ]
        print(f"Excluded {before - len(samples)} high-risk samples.")

    if args.limit is not None:
        samples = samples[: args.limit]

    # 检查占位符
    placeholder_count = sum(1 for s in samples if PLACEHOLDER_RE.search(s["prompt"]))
    if placeholder_count:
        raise ValueError(f"{placeholder_count} prompts still contain placeholders.")

    records = [sample_to_record(s) for s in samples]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "input_path": str(args.input),
        "output_path": str(args.output),
        "record_count": len(records),
        "split": "test",
        "tracks": args.tracks or ["Hard-track", "Soft-track", "Mixed-track"],
        "exclude_high_risk": args.exclude_high_risk,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
