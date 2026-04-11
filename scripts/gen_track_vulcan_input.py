#!/usr/bin/env python3
"""
生成 Vulcan Track 生成任务的输入 JSONL。

502 queries × 9 tracks = 4,518 行

9 tracks per query:
  hard_1:    1 Hard, 0 Soft
  hard_2:    2 Hard, 0 Soft
  hard_3:    3 Hard, 0 Soft
  soft_1:    0 Hard, 1 Soft
  soft_2:    0 Hard, 2 Soft
  soft_3:    0 Hard, 3 Soft
  mixed_1h1s: 1 Hard, 1 Soft
  mixed_1h2s: 1 Hard, 2 Soft
  mixed_2h1s: 2 Hard, 1 Soft

用法:
  python scripts/gen_track_vulcan_input.py \
    --query-pool data/query_pool/query_pool_v3.json \
    --system-prompt prompts/track_gen_system_prompt.md \
    --user-template prompts/track_gen_user_template.md \
    --output data/tracks/vulcan_track_gen_input.jsonl
"""
import argparse, json
from pathlib import Path

TRACK_CONFIGS = [
    ("hard_1",    1, 0),
    ("hard_2",    2, 0),
    ("hard_3",    3, 0),
    ("soft_1",    0, 1),
    ("soft_2",    0, 2),
    ("soft_3",    0, 3),
    ("mixed_1h1s", 1, 1),
    ("mixed_1h2s", 1, 2),
    ("mixed_2h1s", 2, 1),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-pool", required=True)
    parser.add_argument("--system-prompt", required=True)
    parser.add_argument("--user-template", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.query_pool) as f:
        queries = json.load(f)
    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8")
    user_template = Path(args.user_template).read_text(encoding="utf-8")

    rows = []
    for q in queries:
        qid = q.get("query_id", q.get("id", ""))
        query_text = q.get("input", q.get("query_text", ""))

        for track_type, n_hard, n_soft in TRACK_CONFIGS:
            user_content = user_template.format(
                track_type=track_type,
                n_hard=n_hard,
                n_soft=n_soft,
                query_id=qid,
                query_text=query_text,
            )

            row = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "query_id": qid,
                "track_type": track_type,
                "n_hard": n_hard,
                "n_soft": n_soft,
            }
            rows.append(row)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Generated {len(rows)} rows ({len(queries)} queries × {len(TRACK_CONFIGS)} tracks)")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
