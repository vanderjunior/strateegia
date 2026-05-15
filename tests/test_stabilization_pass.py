from app.services.runtime_profile_utils import (
    average_values,
    clamp_value,
    state_message,
    state_reasoning,
)
from app.services.session_stability_metrics import resolve_session_stability_metrics
from app.services.validation_harness import resolve_validation_harness


def build_block(
    *,
    block_id: str,
    retrieval_pressure_accumulation: float = 0.22,
    scaffold_density: float = 0.24,
    continuity_stability: float = 0.68,
    progression_continuity: float = 0.66,
    reconstruction_fragility: float = 0.18,
    compression_safety_metric: float = 0.72,
    stabilization_quality_signal: float = 0.7,
    longitudinal_validation_signal: float = 0.68,
    question_index: int = 1,
) -> dict:
    return {
        "id": block_id,
        "type": "question",
        "topic_id": "topic-a",
        "question_id": f"q-{question_index}",
        "correct_answer": True,
        "explanation": "ok",
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "scaffold_density": scaffold_density,
        "continuity_stability": continuity_stability,
        "progression_continuity": progression_continuity,
        "reconstruction_fragility": reconstruction_fragility,
        "compression_safety_metric": compression_safety_metric,
        "stabilization_quality_signal": stabilization_quality_signal,
        "longitudinal_validation_signal": longitudinal_validation_signal,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }


def test_runtime_profile_utils_builds_canonical_reasoning():
    reasoning = state_reasoning(
        "Estado agregado da sessao",
        "balanced",
        [
            "Linha 2.",
            "Linha 3.",
        ],
    )

    assert reasoning == [
        "Estado agregado da sessao: balanced.",
        "Linha 2.",
        "Linha 3.",
    ]


def test_runtime_profile_utils_normalizes_messages_and_values():
    assert state_message("known", {"known": "ok"}, "fallback") == "ok"
    assert state_message("missing", {"known": "ok"}, "fallback") == "fallback"
    assert clamp_value(1.4) == 1.0
    assert clamp_value(-0.2) == 0.0
    assert average_values([1.2, -0.2, 0.4]) == 0.4667


def test_session_stability_reasoning_keeps_canonical_prefix():
    profile = resolve_session_stability_metrics(
        [
            build_block(block_id="q1", question_index=1),
            build_block(block_id="q2", question_index=2),
        ]
    )

    assert profile.session_stability_reasoning[0].startswith("Estado agregado da sessao:")


def test_validation_harness_reasoning_keeps_canonical_prefix():
    profile = resolve_validation_harness(
        [
            build_block(block_id="q1", question_index=1),
            build_block(block_id="q2", question_index=2),
        ]
    )

    assert profile.validation_harness_reasoning[0].startswith("Estado da harness:")
