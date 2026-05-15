from app.services.scientific_runtime_validation import (
    ScientificRuntimeValidationLayer,
    resolve_scientific_runtime_validation,
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
    signal_overlap_density: float = 0.18,
    validation_confidence: float = 0.7,
    false_fluency_risk: float = 0.18,
    longitudinal_validation_signal: float = 0.7,
    retrieval_shift: float = 0.0,
    scaffold_shift: float = 0.0,
    continuity_shift: float = 0.0,
    overlap_shift: float = 0.0,
    runtime_behavior_delta: float = 0.04,
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilized",
    overlap_family: str = "overlap_low",
    validation_dataset_state: str = "validation_ready",
    pedagogical_scenario_family: str = "balanced_validation",
    behavioral_diff_state: str = "behavior_stable",
    validation_harness_state: str = "support_balanced",
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
        "signal_overlap_density": signal_overlap_density,
        "validation_confidence": validation_confidence,
        "false_fluency_risk": false_fluency_risk,
        "longitudinal_validation_signal": longitudinal_validation_signal,
        "retrieval_shift": retrieval_shift,
        "scaffold_shift": scaffold_shift,
        "continuity_shift": continuity_shift,
        "overlap_shift": overlap_shift,
        "runtime_behavior_delta": runtime_behavior_delta,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
        "validation_dataset_state": validation_dataset_state,
        "pedagogical_scenario_family": pedagogical_scenario_family,
        "behavioral_diff_state": behavioral_diff_state,
        "validation_harness_state": validation_harness_state,
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


def test_scientific_runtime_validation_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = resolve_scientific_runtime_validation(blocks)
    second = resolve_scientific_runtime_validation(blocks)

    assert first == second


def test_scientific_runtime_validation_detects_retrieval_inflation():
    profile = resolve_scientific_runtime_validation(
        [
            build_block(
                block_id="q1",
                retrieval_pressure_accumulation=0.8,
                retrieval_density_metric=0.82,
                retrieval_shift=0.16,
                pacing_stability_metric=0.6,
                retrieval_family="retrieval_dense",
                validation_dataset_state="retrieval_intensive",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_pressure_accumulation=0.78,
                retrieval_density_metric=0.8,
                retrieval_shift=0.14,
                pacing_stability_metric=0.58,
                retrieval_family="retrieval_dense",
                validation_dataset_state="retrieval_intensive",
                question_index=2,
            ),
        ]
    )

    assert profile.scientific_validation_state == "regression_watch"
    assert profile.regression_detection_state == "retrieval_inflation"
    assert profile.retrieval_reliability_profile == "retrieval_fragile"


def test_scientific_runtime_validation_detects_scaffold_dependency_risk():
    profile = resolve_scientific_runtime_validation(
        [
            build_block(
                block_id="q1",
                scaffold_density=0.8,
                scaffold_load_metric=0.82,
                support_density=0.78,
                reinforcement_density_signal=0.74,
                modulation_overlap=0.62,
                adaptive_overlap_signal=0.64,
                support_family="support_heavy",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                scaffold_density=0.78,
                scaffold_load_metric=0.8,
                support_density=0.76,
                reinforcement_density_signal=0.72,
                modulation_overlap=0.6,
                adaptive_overlap_signal=0.62,
                support_family="support_heavy",
                question_index=2,
            ),
        ]
    )

    assert profile.sustainability_validation_state == "sustainability_fragile"
    assert profile.scaffold_dependency_profile == "scaffold_dependent"
    assert profile.reinforcement_redundancy_profile == "reinforcement_redundant"


def test_scientific_runtime_validation_detects_benchmark_ready_context():
    profile = resolve_scientific_runtime_validation(
        [
            build_block(
                block_id="q1",
                continuity_smoothness_metric=0.82,
                continuity_sustainability_signal=0.82,
                reconstruction_fragility=0.16,
                reconstruction_sustainability_signal=0.8,
                compression_safety_metric=0.84,
                compression_safety_signal=0.84,
                transfer_fragility=0.12,
                transfer_stability_signal=0.82,
                stabilization_sustainability_metric=0.82,
                stabilization_reliability_signal=0.84,
                pacing_stability_metric=0.8,
                adaptive_overlap_signal=0.16,
                validation_confidence=0.84,
                false_fluency_risk=0.1,
                longitudinal_validation_signal=0.82,
                validation_dataset_state="validation_ready",
                pedagogical_scenario_family="balanced_validation",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                continuity_smoothness_metric=0.84,
                continuity_sustainability_signal=0.84,
                reconstruction_fragility=0.14,
                reconstruction_sustainability_signal=0.82,
                compression_safety_metric=0.86,
                compression_safety_signal=0.86,
                transfer_fragility=0.1,
                transfer_stability_signal=0.84,
                stabilization_sustainability_metric=0.84,
                stabilization_reliability_signal=0.86,
                pacing_stability_metric=0.82,
                adaptive_overlap_signal=0.14,
                validation_confidence=0.86,
                false_fluency_risk=0.08,
                longitudinal_validation_signal=0.84,
                validation_dataset_state="validation_ready",
                pedagogical_scenario_family="balanced_validation",
                question_index=2,
            ),
        ]
    )

    assert profile.scientific_validation_state == "benchmark_ready"
    assert profile.runtime_benchmark_state == "benchmark_ready"
    assert profile.comparative_runtime_alignment >= 0.75


def test_scientific_runtime_validation_preserves_order_and_bounds():
    layer = ScientificRuntimeValidationLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(block_id="q2", topic_id="topic-b", question_index=2),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["comparative_runtime_alignment"] <= 1.0
        assert block["scientific_validation_state"]
        assert block["runtime_benchmark_summary"]


def test_scientific_runtime_validation_handles_sparse_legacy_blocks():
    annotated = ScientificRuntimeValidationLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("scientific_validation_state" in block for block in annotated)
