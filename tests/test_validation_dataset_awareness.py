from app.services.validation_dataset_awareness import (
    ValidationDatasetAwarenessLayer,
    resolve_validation_dataset_awareness,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_pressure_accumulation: float = 0.24,
    retrieval_density_metric: float = 0.28,
    scaffold_density: float = 0.22,
    scaffold_load_metric: float = 0.24,
    continuity_smoothness_metric: float = 0.72,
    continuity_sustainability_signal: float = 0.7,
    reconstruction_fragility: float = 0.2,
    reconstruction_pressure_metric: float = 0.24,
    reconstruction_sustainability_signal: float = 0.64,
    compression_safety_metric: float = 0.72,
    compression_safety_signal: float = 0.72,
    transfer_fragility: float = 0.18,
    transfer_stability_signal: float = 0.68,
    stabilization_sustainability_metric: float = 0.7,
    stabilization_reliability_signal: float = 0.72,
    support_density: float = 0.24,
    reinforcement_density_signal: float = 0.26,
    pacing_stability_metric: float = 0.68,
    pacing_sustainability_signal: float = 0.7,
    modulation_overlap: float = 0.18,
    adaptive_overlap_signal: float = 0.2,
    validation_confidence: float = 0.7,
    resurfacing_effectiveness_signal: float = 0.68,
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilized",
    overlap_family: str = "overlap_low",
    session_stability_state: str = "balanced",
    validation_harness_state: str = "support_balanced",
    behavioral_diff_state: str = "behavior_stable",
    session_snapshot_state: str = "pedagogically_consistent",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "retrieval_density_metric": retrieval_density_metric,
        "scaffold_density": scaffold_density,
        "scaffold_load_metric": scaffold_load_metric,
        "continuity_smoothness_metric": continuity_smoothness_metric,
        "continuity_sustainability_signal": continuity_sustainability_signal,
        "reconstruction_fragility": reconstruction_fragility,
        "reconstruction_pressure_metric": reconstruction_pressure_metric,
        "reconstruction_sustainability_signal": reconstruction_sustainability_signal,
        "compression_safety_metric": compression_safety_metric,
        "compression_safety_signal": compression_safety_signal,
        "transfer_fragility": transfer_fragility,
        "transfer_stability_signal": transfer_stability_signal,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "stabilization_reliability_signal": stabilization_reliability_signal,
        "support_density": support_density,
        "reinforcement_density_signal": reinforcement_density_signal,
        "pacing_stability_metric": pacing_stability_metric,
        "pacing_sustainability_signal": pacing_sustainability_signal,
        "modulation_overlap": modulation_overlap,
        "adaptive_overlap_signal": adaptive_overlap_signal,
        "validation_confidence": validation_confidence,
        "resurfacing_effectiveness_signal": resurfacing_effectiveness_signal,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
        "session_stability_state": session_stability_state,
        "validation_harness_state": validation_harness_state,
        "behavioral_diff_state": behavioral_diff_state,
        "session_snapshot_state": session_snapshot_state,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }
    if block_type == "summary":
        payload["content"] = "Resumo"
    else:
        payload["statement"] = "Pergunta"
        payload["correct_answer"] = True
        payload["explanation"] = "Explicacao"
        payload["question_id"] = f"{topic_id}-{question_index}"
    return payload


def test_validation_dataset_awareness_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = resolve_validation_dataset_awareness(blocks)
    second = resolve_validation_dataset_awareness(blocks)

    assert first == second


def test_validation_dataset_awareness_detects_retrieval_intensive_context():
    profile = resolve_validation_dataset_awareness(
        [
            build_block(
                block_id="q1",
                retrieval_pressure_accumulation=0.78,
                retrieval_density_metric=0.8,
                pacing_stability_metric=0.62,
                pacing_sustainability_signal=0.64,
                retrieval_family="retrieval_dense",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_pressure_accumulation=0.76,
                retrieval_density_metric=0.78,
                pacing_stability_metric=0.6,
                pacing_sustainability_signal=0.62,
                retrieval_family="retrieval_dense",
                question_index=2,
            ),
        ]
    )

    assert profile.validation_dataset_state == "retrieval_intensive"
    assert profile.retrieval_condition_profile == "retrieval_intensive"
    assert profile.pedagogical_scenario_family == "retrieval"


def test_validation_dataset_awareness_detects_scaffold_sensitive_context():
    profile = resolve_validation_dataset_awareness(
        [
            build_block(
                block_id="q1",
                scaffold_density=0.78,
                scaffold_load_metric=0.8,
                support_density=0.74,
                reinforcement_density_signal=0.72,
                support_family="support_heavy",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                scaffold_density=0.76,
                scaffold_load_metric=0.78,
                support_density=0.72,
                reinforcement_density_signal=0.7,
                support_family="support_heavy",
                question_index=2,
            ),
        ]
    )

    assert profile.validation_dataset_state == "scaffold_sensitive"
    assert profile.scaffold_condition_profile == "scaffold_sensitive"
    assert profile.reinforcement_condition_profile == "reinforcement_dense"


def test_validation_dataset_awareness_detects_validation_ready_context():
    profile = resolve_validation_dataset_awareness(
        [
            build_block(
                block_id="q1",
                retrieval_pressure_accumulation=0.22,
                retrieval_density_metric=0.3,
                continuity_smoothness_metric=0.8,
                reconstruction_fragility=0.16,
                compression_safety_metric=0.82,
                transfer_fragility=0.14,
                stabilization_sustainability_metric=0.8,
                pacing_stability_metric=0.78,
                adaptive_overlap_signal=0.18,
                validation_confidence=0.82,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_pressure_accumulation=0.2,
                retrieval_density_metric=0.28,
                continuity_smoothness_metric=0.82,
                reconstruction_fragility=0.14,
                compression_safety_metric=0.84,
                transfer_fragility=0.12,
                stabilization_sustainability_metric=0.82,
                pacing_stability_metric=0.8,
                adaptive_overlap_signal=0.16,
                validation_confidence=0.84,
                question_index=2,
            ),
        ]
    )

    assert profile.validation_dataset_state == "validation_ready"
    assert profile.pedagogical_scenario_family == "balanced_validation"
    assert profile.comparative_validation_alignment >= 0.7


def test_validation_dataset_awareness_preserves_order_and_bounds():
    layer = ValidationDatasetAwarenessLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(block_id="q2", topic_id="topic-b", question_index=2),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["comparative_validation_alignment"] <= 1.0
        assert block["validation_dataset_state"]
        assert block["dataset_awareness_summary"]


def test_validation_dataset_awareness_handles_sparse_legacy_blocks():
    annotated = ValidationDatasetAwarenessLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("validation_dataset_state" in block for block in annotated)
