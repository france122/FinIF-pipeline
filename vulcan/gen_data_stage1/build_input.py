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

DEFAULT_SYSTEM_PROMPT = (
    "你是中文金融 Instruction-Following benchmark 的候选作答模型。"
    "请直接回答用户问题，并严格满足所有附加要求。"
    "不要解释你如何遵循要求，不要输出多余前言，也不要输出与任务无关的说明。"
)

PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Vulcan input JSONL for stage-1 response generation with gpt-oss-120b."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Filled tracks JSON path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output JSONL path.")
    parser.add_argument(
        "--splits",
        nargs="*",
        choices=["train", "test"],
        help="Optional split filter. Example: --splits test",
    )
    parser.add_argument(
        "--tracks",
        nargs="*",
        choices=["Hard-track", "Soft-track", "Mixed-track"],
        help="Optional track filter. Example: --tracks Mixed-track",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional record limit.")
    return parser.parse_args()


def load_samples(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_to_record(sample: dict) -> dict:
    prompt = sample["prompt"]
    constraints = []
    for constraint in sample.get("constraints", []):
        constraints.append(
            {
                "id": constraint["id"],
                "type": constraint["type"],
                "text": constraint["text"],
                "is_parametric": constraint.get("is_parametric", False),
                "filled_params": constraint.get("filled_params"),
            }
        )

    return {
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "metadata": {
            "task_name": "gen_data_stage1",
            "target_model": "gpt-oss-120b",
            "data_version": "ds_5500_run1_materialized",
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

    if args.splits:
        split_set = set(args.splits)
        samples = [sample for sample in samples if sample["split"] in split_set]
    if args.tracks:
        track_set = set(args.tracks)
        samples = [sample for sample in samples if sample["track"] in track_set]
    if args.limit is not None:
        samples = samples[: args.limit]

    placeholder_count = sum(1 for sample in samples if PLACEHOLDER_RE.search(sample["prompt"]))
    if placeholder_count:
        raise ValueError(f"发现 {placeholder_count} 条 prompt 仍含占位符，不能直接用于生成任务。")

    records = [sample_to_record(sample) for sample in samples]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "input_path": str(args.input),
                "output_path": str(args.output),
                "record_count": len(records),
                "splits": args.splits or ["train", "test"],
                "tracks": args.tracks or ["Hard-track", "Soft-track", "Mixed-track"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
