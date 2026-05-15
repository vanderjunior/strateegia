from app.services.session_stability_metrics import (
    SessionStabilityMetricsLayer,
    resolve_session_stability_metrics,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_pressure_accumulation: float = 0.22,
    scaffold_density: float = 0.24,
    continuity_stability: float = 0.66,
    progression_continuity: float = 0.64,
    reconstruction_fragility: float = 0.18,
    compression_support_alignment: float = 0.68,
    stabilization_quality: float = 0.7,
    stabilization_quality_signal: float = 0.68,
    longitudinal_validation_signal: float = 0.66,
    longitudinal_consistency: float = 0.68,
    modulation_overlap: float = 0.2,
    signal_overlap_density: float = 0.22,
    retrieval_effectiveness_signal: float = 0.62,
    pacing_adjustment: float = 0.5,
    false_fluency_risk: float = 0.12,
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilization_stable",
    overlap_family: str = "overlap_light",
    pedagogical_observability_state: str = "adaptively_balanced",
    runtime_trace_state: str = "runtime_balanced",
    pedagogical_validation_state: str = "support_balanced",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "scaffold_density": scaffold_density,
        "continuity_stability": continuity_stability,
        "progression_continuity": progression_continuity,
        "reconstruction_fragility": reconstruction_fragility,
        "compression_support_alignment": compression_support_alignment,
        "stabilization_quality": stabilization_quality,
        "stabilization_quality_signal": stabilization_quality_signal,
        "longitudinal_validation_signal": longitudinal_validation_signal,
        "longitudinal_consistency": longitudinal_consistency,
        "modulation_overlap": modulation_overlap,
        "signal_overlap_density": signal_overlap_density,
        "retrieval_effectiveness_signal": retrieval_effectiveness_signal,
        "pacing_adjustment": pacing_adjustment,
        "false_fluency_risk": false_fluency_risk,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
        "pedagogical_observability_state": pedagogical_observability_state,
        "runtime_trace_state": runtime_trace_state,
        "pedagogical_validation_state": pedagogical_validation_state,
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


def test_session_stability_metrics_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(block_id="q2", question_index=2),
    ]

    first = resolve_session_stability_metrics(blocks)
    second = resolve_session_stability_metrics(blocks)

    assert first == second


def test_session_stability_metrics_detects_retrieval_heavy_session():
    profile = resolve_session_stability_metrics(
        [
            build_block(
                block_id="q1",
                retrieval_pressure_accumulation=0.82,
                retrieval_effectiveness_signal=0.44,
                retrieval_family="retrieval_dense",
                pedagogical_observability_state="retrieval_dense",
                runtime_trace_state="retrieval_clustered",
                pedagogical_validation_state="retrieval_saturated",
            ),
            build_block(
                block_id="q2",
                retrieval_pressure_accumulation=0.78,
                retrieval_effectiveness_signal=0.42,
                retrieval_family="retrieval_dense",
                pedagogical_observability_state="retrieval_dense",
                runtime_trace_state="retrieval_clustered",
                pedagogical_validation_state="retrieval_saturated",
                question_index=2,
            ),
        ]
    )

    assert profile.session_stability_state == "retrieval_heavy"
    assert profile.retrieval_density_metric > 0.0


def test_session_stability_metrics_detects_support_dense_session():
    profile = resolve_session_stability_metrics(
        [
            build_block(
                block_id="q1",
                scaffold_density=0.82,
                compression_support_alignment=0.76,
                support_family="support_dense",
                overlap_family="overlap_convergent",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                scaffold_density=0.78,
                reconstruction_fragility=0.62,
                compression_support_alignment=0.8,
                support_family="support_dense",
                overlap_family="overlap_convergent",
                question_index=2,
            ),
        ]
    )

    assert profile.session_stability_state == "support_dense"
    assert profile.scaffold_load_metric >= 0.5
    assert profile.support_density >= 0.5


def test_session_stability_metrics_detects_stabilization_progression():
    profile = resolve_session_stability_metrics(
        [
            build_block(
                block_id="s1",
                block_type="summary",
                stabilization_quality=0.82,
                stabilization_quality_signal=0.8,
                longitudinal_validation_signal=0.78,
                longitudinal_consistency=0.76,
                continuity_stability=0.74,
                progression_continuity=0.72,
                stabilization_family="stabilization_progressive",
                pedagogical_validation_state="stabilization_sustainable",
                question_index=0,
            ),
            build_block(
                block_id="q1",
                stabilization_quality=0.8,
                stabilization_quality_signal=0.78,
                longitudinal_validation_signal=0.76,
                longitudinal_consistency=0.74,
                continuity_stability=0.72,
                progression_continuity=0.7,
                stabilization_family="stabilization_progressive",
                pedagogical_validation_state="longitudinally_stable",
                question_index=1,
            ),
        ]
    )

    assert profile.session_stability_state == "stabilization_progressive"
    assert profile.stabilization_sustainability_metric >= 0.6


def test_session_stability_layer_preserves_order_and_bounds():
    layer = SessionStabilityMetricsLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            retrieval_pressure_accumulation=0.18,
            scaffold_density=0.2,
            continuity_stability=0.7,
            progression_continuity=0.68,
            reconstruction_fragility=0.12,
            compression_support_alignment=0.72,
            stabilization_quality=0.74,
            stabilization_quality_signal=0.72,
            longitudinal_validation_signal=0.7,
            longitudinal_consistency=0.7,
            modulation_overlap=0.16,
            signal_overlap_density=0.18,
            retrieval_effectiveness_signal=0.66,
            pacing_adjustment=0.48,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["retrieval_density_metric"] <= 1.0
        assert 0.0 <= block["scaffold_load_metric"] <= 1.0
        assert 0.0 <= block["continuity_smoothness_metric"] <= 1.0
        assert 0.0 <= block["reconstruction_pressure_metric"] <= 1.0
        assert 0.0 <= block["compression_safety_metric"] <= 1.0
        assert 0.0 <= block["modulation_convergence_metric"] <= 1.0
        assert 0.0 <= block["stabilization_sustainability_metric"] <= 1.0
        assert 0.0 <= block["cognitive_balance_metric"] <= 1.0


def test_session_stability_layer_handles_sparse_legacy_blocks():
    annotated = SessionStabilityMetricsLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("session_stability_state" in block for block in annotated)
