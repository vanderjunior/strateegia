from app.services.comparative_session_analytics import (
    ComparativeSessionAnalyticsLayer,
    build_session_signature,
    compare_session_analytics,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_density_metric: float = 0.28,
    scaffold_load_metric: float = 0.24,
    continuity_smoothness_metric: float = 0.72,
    reconstruction_pressure_metric: float = 0.22,
    compression_safety_metric: float = 0.74,
    stabilization_sustainability_metric: float = 0.72,
    pacing_stability_metric: float = 0.68,
    cognitive_balance_metric: float = 0.7,
    support_density: float = 0.24,
    adaptive_overlap_signal: float = 0.2,
    validation_confidence: float = 0.72,
    false_fluency_risk: float = 0.18,
    scaffold_dependency_signal: float = 0.22,
    resurfacing_effectiveness_signal: float = 0.68,
    transfer_stability_signal: float = 0.7,
    compression_safety_signal: float = 0.74,
    runtime_behavior_delta: float = 0.04,
    validation_dataset_state: str = "validation_ready",
    pedagogical_scenario_family: str = "balanced_validation",
    scientific_validation_state: str = "validation_stable",
    sustainability_validation_state: str = "sustainability_supported",
    regression_detection_state: str = "regression_stable",
    runtime_benchmark_state: str = "benchmark_watch",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_density_metric": retrieval_density_metric,
        "scaffold_load_metric": scaffold_load_metric,
        "continuity_smoothness_metric": continuity_smoothness_metric,
        "reconstruction_pressure_metric": reconstruction_pressure_metric,
        "compression_safety_metric": compression_safety_metric,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "pacing_stability_metric": pacing_stability_metric,
        "cognitive_balance_metric": cognitive_balance_metric,
        "support_density": support_density,
        "adaptive_overlap_signal": adaptive_overlap_signal,
        "validation_confidence": validation_confidence,
        "false_fluency_risk": false_fluency_risk,
        "scaffold_dependency_signal": scaffold_dependency_signal,
        "resurfacing_effectiveness_signal": resurfacing_effectiveness_signal,
        "transfer_stability_signal": transfer_stability_signal,
        "compression_safety_signal": compression_safety_signal,
        "runtime_behavior_delta": runtime_behavior_delta,
        "validation_dataset_state": validation_dataset_state,
        "pedagogical_scenario_family": pedagogical_scenario_family,
        "scientific_validation_state": scientific_validation_state,
        "sustainability_validation_state": sustainability_validation_state,
        "regression_detection_state": regression_detection_state,
        "runtime_benchmark_state": runtime_benchmark_state,
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


def test_comparative_session_analytics_is_deterministic():
    baseline = [build_block(block_id="b1")]
    candidate = [build_block(block_id="c1")]

    first = compare_session_analytics(baseline, candidate)
    second = compare_session_analytics(baseline, candidate)

    assert first == second


def test_session_signature_is_compact_and_deterministic():
    signature = build_session_signature([build_block(block_id="s1"), build_block(block_id="s2")])

    assert signature.retrieval_level >= 0.0
    assert signature.balance_level >= 0.0
    assert signature == build_session_signature([build_block(block_id="s1"), build_block(block_id="s2")])


def test_comparative_session_analytics_detects_behaviorally_stable_comparison():
    baseline = [build_block(block_id="b1"), build_block(block_id="b2", question_index=2)]
    candidate = [build_block(block_id="c1"), build_block(block_id="c2", question_index=2)]

    profile = compare_session_analytics(baseline, candidate)

    assert profile.comparative_session_state == "behavior_consistent"
    assert profile.behavioral_drift_signal <= 0.06


def test_comparative_session_analytics_detects_retrieval_increase():
    baseline = [build_block(block_id="b1", retrieval_density_metric=0.24)]
    candidate = [build_block(block_id="c1", retrieval_density_metric=0.78, validation_dataset_state="retrieval_intensive")]

    profile = compare_session_analytics(baseline, candidate)

    assert profile.comparative_session_state == "retrieval_increased"
    assert profile.retrieval_delta > 0


def test_comparative_session_analytics_detects_scaffold_increase():
    baseline = [build_block(block_id="b1", scaffold_load_metric=0.22, support_density=0.22)]
    candidate = [build_block(block_id="c1", scaffold_load_metric=0.76, support_density=0.72, scaffold_dependency_signal=0.74)]

    profile = compare_session_analytics(baseline, candidate)

    assert profile.comparative_session_state == "scaffold_increased"
    assert profile.scaffold_delta > 0


def test_comparative_session_analytics_detects_compression_risk():
    baseline = [build_block(block_id="b1", compression_safety_metric=0.84, compression_safety_signal=0.84)]
    candidate = [build_block(block_id="c1", compression_safety_metric=0.44, compression_safety_signal=0.44)]

    profile = compare_session_analytics(baseline, candidate)

    assert profile.comparative_session_state == "compression_riskier"
    assert profile.compression_delta < 0


def test_comparative_session_analytics_detects_continuity_change():
    baseline = [build_block(block_id="b1", continuity_smoothness_metric=0.52)]
    candidate = [build_block(block_id="c1", continuity_smoothness_metric=0.82)]

    improved = compare_session_analytics(baseline, candidate)
    degraded = compare_session_analytics(candidate, baseline)

    assert improved.comparative_session_state == "continuity_improved"
    assert degraded.comparative_session_state == "continuity_degraded"


def test_comparative_session_analytics_detects_regression_risk():
    baseline = [build_block(block_id="b1", retrieval_density_metric=0.28, scaffold_load_metric=0.24)]
    candidate = [
        build_block(
            block_id="c1",
            retrieval_density_metric=0.78,
            scaffold_load_metric=0.74,
            reconstruction_pressure_metric=0.72,
            support_density=0.72,
            scaffold_dependency_signal=0.76,
            regression_detection_state="retrieval_inflation",
            scientific_validation_state="regression_watch",
        )
    ]

    profile = compare_session_analytics(baseline, candidate)

    assert profile.comparative_session_state == "pedagogical_regression_risk"
    assert profile.pedagogical_regression_signal == "retrieval_inflation"


def test_comparative_session_analytics_detects_sustainability_change():
    baseline = [build_block(block_id="b1", stabilization_sustainability_metric=0.48, sustainability_validation_state="sustainability_watch")]
    candidate = [build_block(block_id="c1", stabilization_sustainability_metric=0.82, sustainability_validation_state="sustainability_supported")]

    improved = compare_session_analytics(baseline, candidate)
    degraded = compare_session_analytics(candidate, baseline)

    assert improved.comparative_session_state == "sustainability_improved"
    assert degraded.comparative_session_state == "sustainability_degraded"


def test_comparative_session_analytics_is_inconclusive_without_baseline():
    profile = compare_session_analytics(None, [build_block(block_id="c1")])

    assert profile.comparative_session_state == "comparison_inconclusive"


def test_comparative_session_analytics_handles_sparse_legacy_blocks():
    annotated = ComparativeSessionAnalyticsLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("comparative_session_state" in block for block in annotated)
