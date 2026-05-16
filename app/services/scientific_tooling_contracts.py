from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def safe_list(value: object) -> list[object]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def safe_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


def ensure_reasoning_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def normalize_availability_state(value: object, default: str = "not_available") -> str:
    text = str(value or "").strip()
    return text or default


def readonly_copy(value: object) -> object:
    return deepcopy(value)


def json_safe_profile(value: object, default: object | None = None) -> object:
    target = default if value is None else value
    if target is None:
        return {}
    return json.loads(json.dumps(target, default=_json_default, ensure_ascii=True))


def scientific_payload_defaults(
    *,
    controlled_tuning_registry: object,
    tuning_profile_benchmark_comparison: object,
    manual_experiment_inspection: object,
    longitudinal_retention: object,
) -> dict[str, object]:
    return {
        "inspection_available": False,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {
            "session_id": None,
            "completed": None,
            "current_block_index": None,
            "total_blocks": 0,
            "current_block_type": None,
            "topic_id": None,
        },
        "benchmark_summary": {
            "pedagogical_benchmark_state": "not_available",
            "pedagogical_benchmark_summary": "No runtime data available.",
            "benchmark_readiness": "benchmark_insufficient",
            "benchmark_alignment_score": 0.0,
            "benchmark_regression_severity": "none",
            "benchmark_total_cases": 0,
            "benchmark_passed_cases": [],
            "benchmark_failed_cases": [],
            "benchmark_inconclusive_cases": [],
            "benchmark_regression_cases": [],
        },
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": json_safe_profile(controlled_tuning_registry),
        "tuning_profile_benchmark_comparison": json_safe_profile(
            tuning_profile_benchmark_comparison
        ),
        "manual_experiment_inspection": json_safe_profile(manual_experiment_inspection),
        "longitudinal_retention": json_safe_profile(longitudinal_retention),
        "raw_runtime_block": {},
    }


def _json_default(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
