from app.services.validation_harness import (
    ValidationHarnessLayer,
    resolve_validation_harness,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_effectiveness_signal: float = 0.62,
    retrieval_pressure_accumulation: float = 0.22,
    scaffold_dependency_signal: float = 0.2,
    scaffold_density: float = 0.22,
    reconstruction_progress_signal: float = 0.58,
    reconstruction_fragility: float = 0.18,
    transfer_stability_signal: float = 0.64,
    transfer_fragility: float = 0.16,
    stabilization_quality_signal: float = 0.7,
    longitudinal_validation_signal: float = 0.68,
    compression_safety_metric: float = 0.72,
    continuity_smoothness_metric: float = 0.7,
    pacing_stability_metric: float = 0.66,
    cognitive_balance_metric: float = 0.68,
    modulation_overlap: float = 0.18,
    signal_overlap_density: float = 0.2,
    support_density: float = 0.24,
    intervention_repetition_signal: float = 0.16,
    pedagogical_validation_state: str = "support_balanced",
    session_stability_state: str = "balanced",
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilized",
    overlap_family: str = "overlap_low",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_effectiveness_signal": retrieval_effectiveness_signal,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "scaffold_dependency_signal": scaffold_dependency_signal,
        "scaffold_density": scaffold_density,
        "reconstruction_progress_signal": reconstruction_progress_signal,
        "reconstruction_fragility": reconstruction_fragility,
        "transfer_stability_signal": transfer_stability_signal,
        "transfer_fragility": transfer_fragility,
        "stabilization_quality_signal": stabilization_quality_signal,
        "longitudinal_validation_signal": longitudinal_validation_signal,
        "compression_safety_metric": compression_safety_metric,
        "continuity_smoothness_metric": continuity_smoothness_metric,
        "pacing_stability_metric": pacing_stability_metric,
        "cognitive_balance_metric": cognitive_balance_metric,
        "modulation_overlap": modulation_overlap,
        "signal_overlap_density": signal_overlap_density,
        "support_density": support_density,
        "intervention_repetition_signal": intervention_repetition_signal,
        "pedagogical_validation_state": pedagogical_validation_state,
        "session_stability_state": session_stability_state,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
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


def test_validation_harness_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = resolve_validation_harness(blocks)
    second = resolve_validation_harness(blocks)

    assert first == second


def test_validation_harness_detects_retrieval_sustainable():
    profile = resolve_validation_harness(
        [
            build_block(
                block_id="q1",
                retrieval_effectiveness_signal=0.78,
                retrieval_pressure_accumulation=0.18,
                retrieval_family="retrieval_balanced",
                pedagogical_validation_state="retrieval_effective",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_effectiveness_signal=0.8,
                retrieval_pressure_accumulation=0.16,
                retrieval_family="retrieval_balanced",
                pedagogical_validation_state="retrieval_effective",
                question_index=2,
            ),
        ]
    )

    assert profile.validation_harness_state == "retrieval_sustainable"
    assert profile.retrieval_sustainability_signal >= 0.6


def test_validation_harness_detects_scaffold_dependency_risk():
    profile = resolve_validation_harness(
        [
            build_block(
                block_id="q1",
                scaffold_dependency_signal=0.74,
                scaffold_density=0.78,
                reconstruction_progress_signal=0.38,
                support_density=0.72,
                support_family="support_heavy",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                scaffold_dependency_signal=0.76,
                scaffold_density=0.8,
                reconstruction_progress_signal=0.34,
                support_density=0.74,
                support_family="support_heavy",
                question_index=2,
            ),
        ]
    )

    assert profile.validation_harness_state == "scaffold_dependency_risk"
    assert profile.scaffold_dependency_signal >= 0.6


def test_validation_harness_detects_compression_safe():
    profile = resolve_validation_harness(
        [
            build_block(
                block_id="q1",
                compression_safety_metric=0.84,
                stabilization_quality_signal=0.78,
                longitudinal_validation_signal=0.76,
                continuity_smoothness_metric=0.74,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                compression_safety_metric=0.82,
                stabilization_quality_signal=0.8,
                longitudinal_validation_signal=0.78,
                continuity_smoothness_metric=0.72,
                question_index=2,
            ),
        ]
    )

    assert profile.validation_harness_state == "compression_safe"
    assert profile.compression_safety_signal >= 0.7


def test_validation_harness_preserves_order_and_bounds():
    layer = ValidationHarnessLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            retrieval_effectiveness_signal=0.56,
            retrieval_pressure_accumulation=0.24,
            scaffold_dependency_signal=0.22,
            scaffold_density=0.24,
            reconstruction_progress_signal=0.52,
            reconstruction_fragility=0.2,
            transfer_stability_signal=0.6,
            transfer_fragility=0.18,
            stabilization_quality_signal=0.68,
            longitudinal_validation_signal=0.66,
            compression_safety_metric=0.7,
            continuity_smoothness_metric=0.68,
            pacing_stability_metric=0.64,
            cognitive_balance_metric=0.66,
            modulation_overlap=0.16,
            signal_overlap_density=0.18,
            support_density=0.22,
            intervention_repetition_signal=0.14,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["retrieval_sustainability_signal"] <= 1.0
        assert 0.0 <= block["scaffold_dependency_signal"] <= 1.0
        assert 0.0 <= block["reconstruction_sustainability_signal"] <= 1.0
        assert 0.0 <= block["transfer_stability_signal"] <= 1.0
        assert 0.0 <= block["resurfacing_effectiveness_signal"] <= 1.0
        assert 0.0 <= block["stabilization_reliability_signal"] <= 1.0
        assert 0.0 <= block["compression_safety_signal"] <= 1.0
        assert 0.0 <= block["continuity_sustainability_signal"] <= 1.0
        assert 0.0 <= block["pacing_sustainability_signal"] <= 1.0
        assert 0.0 <= block["cognitive_friction_signal"] <= 1.0
        assert 0.0 <= block["adaptive_overlap_signal"] <= 1.0
        assert 0.0 <= block["pedagogical_balance_signal"] <= 1.0
        assert 0.0 <= block["validation_confidence"] <= 1.0
        assert 0.0 <= block["evidence_alignment"] <= 1.0


def test_validation_harness_handles_sparse_legacy_blocks():
    annotated = ValidationHarnessLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("validation_harness_state" in block for block in annotated)
