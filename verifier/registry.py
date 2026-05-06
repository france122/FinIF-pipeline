from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_TABLE_PATH = REPO_ROOT / "docs" / "constraint_reference_table.csv"
RULES_DIR = REPO_ROOT / "verifier" / "rules"
RUBRICS_DIR = REPO_ROOT / "verifier" / "rubrics"
VALID_HARDNESS = {"hard", "soft"}
VALID_CHECK_MODES = {"rule", "LLM-as-a-judge"}
VALID_SCORE_TYPES = {"binary"}


def _validate_row(row: dict[str, str]) -> dict[str, str]:
    constraint_id = row["constraint_id"]
    module = row["module"]
    prefix = constraint_id.split("-", 1)[0]

    if prefix != module:
        raise ValueError(f"{constraint_id} 的 module={module} 与 ID 前缀不一致")

    hardness = row["hardness"]
    if hardness not in VALID_HARDNESS:
        raise ValueError(f"{constraint_id} 的 hardness 非法: {hardness}")

    check_mode = row["check_mode"]
    if check_mode not in VALID_CHECK_MODES:
        raise ValueError(f"{constraint_id} 的 check_mode 非法: {check_mode}")

    score_type = row["score_type"]
    if score_type not in VALID_SCORE_TYPES:
        raise ValueError(f"{constraint_id} 的 score_type 非法: {score_type}")

    if check_mode == "rule" and hardness != "hard":
        raise ValueError(f"{constraint_id} 为 rule，但 hardness 不是 hard")

    if check_mode == "LLM-as-a-judge" and hardness != "soft":
        raise ValueError(f"{constraint_id} 为 LLM-as-a-judge，但 hardness 不是 soft")

    if check_mode == "rule" and score_type != "binary":
        raise ValueError(f"{constraint_id} 为 rule，但 score_type 不是 binary")

    return row


@lru_cache(maxsize=1)
def load_constraint_registry() -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    with REFERENCE_TABLE_PATH.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            validated = _validate_row(row)
            registry[validated["constraint_id"]] = validated
    return registry


def list_constraints() -> list[dict[str, str]]:
    return [load_constraint_registry()[cid] for cid in sorted(load_constraint_registry())]


def get_constraint_meta(constraint_id: str) -> dict[str, str]:
    registry = load_constraint_registry()
    if constraint_id not in registry:
        raise KeyError(f"未知 constraint_id: {constraint_id}")
    return registry[constraint_id]


def get_rule_path(constraint_id: str) -> Path:
    return RULES_DIR / f"{constraint_id}.py"


def get_rubric_path(constraint_id: str) -> Path:
    return RUBRICS_DIR / f"{constraint_id}.md"
