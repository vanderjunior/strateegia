from app.services.pedagogical_validation import (
    PedagogicalValidationLayer,
    resolve_pedagogical_validation,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    trajectory_state: str = "stabilizing",
    stabilization_stage: str = "stabilizing",
    retrieval_intensity: str = "medium",
    cognitive_momentum: str = "balanced",
    session_coherence_state: str = "continuity_stable",
    pedagogical_expression_mode: str = "stabilization_reassurance",
    cognitive_compression_mode: str = "stable_compressed",
    micro_intervention: str = "confidence_check",
    adaptive_signal_state: str = "compressed_stability",
    pedagogical_observability_state: str = "adaptively_balanced",
    runtime_trace_state: str = "runtime_balanced",
    longitudinal_retention: float = 0.72,
    longitudinal_consistency: float = 0.68,
    stabilization_quality: float = 0.7,
    false_fluency_signal: float = 0.12,
    reconstruction_fragility: float = 0.18,
    transfer_fragility: float = 0.16,
    scaffold_density: float = 0.22,
    signal_overlap_density: float = 0.24,
    retrieval_pressure_accumulation: float = 0.22,
    modulation_overlap: float = 0.18,
    reinforcement_convergence: float = 0.34,
    explanatory_expansion: float = 0.14,
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "trajectory_state": trajectory_state,
        "stabilization_stage": stabilization_stage,
        "retrieval_intensity": retrieval_intensity,
        "cognitive_momentum": cognitive_momentum,
        "session_coherence_state": session_coherence_state,
        "pedagogical_expression_mode": pedagogical_expression_mode,
        "cognitive_compression_mode": cognitive_compression_mode,
        "micro_intervention": micro_intervention,
        "adaptive_signal_state": adaptive_signal_state,
        "pedagogical_observability_state": pedagogical_observability_state,
        "runtime_trace_state": runtime_trace_state,
        "longitudinal_retention": longitudinal_retention,
        "longitudinal_consistency": longitudinal_consistency,
        "stabilization_quality": stabilization_quality,
        "false_fluency_signal": false_fluency_signal,
        "reconstruction_fragility": reconstruction_fragility,
        "transfer_fragility": transfer_fragility,
        "scaffold_density": scaffold_density,
        "signal_overlap_density": signal_overlap_density,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "modulation_overlap": modulation_overlap,
        "reinforcement_convergence": reinforcement_convergence,
        "explanatory_expansion": explanatory_expansion,
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


def test_pedagogical_validation_is_deterministic():
    kwargs = dict(
        current_block=build_block(block_id="q1"),
        recent_blocks=[build_block(block_id="s1", block_type="summary", question_index=0)],
    )

    first = resolve_pedagogical_validation(**kwargs)
    second = resolve_pedagogical_validation(**kwargs)

    assert first == second


def test_pedagogical_validation_detects_surface_fluency():
    profile = resolve_pedagogical_validation(
        current_block=build_block(
            block_id="q1",
            trajectory_state="superficially_stable",
            stabilization_stage="stabilizing",
            false_fluency_signal=0.78,
            retrieval_intensity="low",
            cognitive_compression_mode="stable_compressed",
            pedagogical_expression_mode="stabilization_reassurance",
            longitudinal_retention=0.44,
            longitudinal_consistency=0.38,
        ),
        recent_blocks=[],
    )

    assert profile.pedagogical_validation_state == "surface_fluency_detected"
    assert profile.false_fluency_risk > 0.0


def test_pedagogical_validation_detects_scaffold_dependency_risk():
    layer = PedagogicalValidationLayer()
    annotated = layer.annotate(
        [
            build_block(
                block_id="q1",
                trajectory_state="reconstruction_fragile",
                stabilization_stage="emerging",
                pedagogical_expression_mode="focused_reconstruction",
                cognitive_compression_mode="reconstruction_scaffolded",
                micro_intervention="guided_reconstruction",
                adaptive_signal_state="reconstruction_pressure",
                pedagogical_observability_state="scaffold_saturated",
                runtime_trace_state="support_accumulated",
                scaffold_density=0.66,
                signal_overlap_density=0.58,
                explanatory_expansion=0.74,
                reconstruction_fragility=0.82,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                trajectory_state="reconstruction_fragile",
                stabilization_stage="emerging",
                pedagogical_expression_mode="focused_reconstruction",
                cognitive_compression_mode="reconstruction_scaffolded",
                micro_intervention="guided_reconstruction",
                adaptive_signal_state="reconstruction_pressure",
                pedagogical_observability_state="scaffold_saturated",
                runtime_trace_state="support_accumulated",
                scaffold_density=0.68,
                signal_overlap_density=0.6,
                explanatory_expansion=0.76,
                reconstruction_fragility=0.84,
                question_index=2,
            ),
        ]
    )

    assert annotated[-1]["pedagogical_validation_state"] == "scaffold_dependency_risk"
    assert annotated[-1]["scaffold_dependency_signal"] > 0.0


def test_pedagogical_validation_detects_retrieval_effective():
    profile = resolve_pedagogical_validation(
        current_block=build_block(
            block_id="q1",
            trajectory_state="stabilizing",
            stabilization_stage="stabilizing",
            retrieval_intensity="medium",
            cognitive_momentum="balanced",
            longitudinal_retention=0.76,
            longitudinal_consistency=0.72,
            stabilization_quality=0.74,
            retrieval_pressure_accumulation=0.24,
            false_fluency_signal=0.1,
        ),
        recent_blocks=[build_block(block_id="s1", block_type="summary", question_index=0)],
    )

    assert profile.pedagogical_validation_state == "retrieval_effective"
    assert profile.retrieval_effectiveness_signal > 0.0


def test_pedagogical_validation_preserves_order_and_bounds():
    layer = PedagogicalValidationLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            trajectory_state="consolidated",
            stabilization_stage="consolidated",
            retrieval_intensity="low",
            cognitive_momentum="balanced",
            session_coherence_state="continuity_stable",
            pedagogical_expression_mode="stabilization_reassurance",
            cognitive_compression_mode="stable_compressed",
            micro_intervention="confidence_check",
            adaptive_signal_state="compressed_stability",
            pedagogical_observability_state="adaptively_balanced",
            runtime_trace_state="runtime_balanced",
            longitudinal_retention=0.84,
            longitudinal_consistency=0.78,
            stabilization_quality=0.8,
            false_fluency_signal=0.08,
            reconstruction_fragility=0.06,
            transfer_fragility=0.08,
            scaffold_density=0.18,
            signal_overlap_density=0.16,
            retrieval_pressure_accumulation=0.12,
            modulation_overlap=0.12,
            reinforcement_convergence=0.28,
            explanatory_expansion=0.08,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["retrieval_effectiveness_signal"] <= 1.0
        assert 0.0 <= block["stabilization_quality_signal"] <= 1.0
        assert 0.0 <= block["false_fluency_risk"] <= 1.0
        assert 0.0 <= block["scaffold_dependency_signal"] <= 1.0
        assert 0.0 <= block["transfer_stability_signal"] <= 1.0
        assert 0.0 <= block["reconstruction_progress_signal"] <= 1.0
        assert 0.0 <= block["adaptation_overlap_signal"] <= 1.0
        assert 0.0 <= block["reinforcement_density_signal"] <= 1.0
        assert 0.0 <= block["longitudinal_validation_signal"] <= 1.0
        assert 0.0 <= block["validation_alignment"] <= 1.0


def test_pedagogical_validation_handles_sparse_legacy_blocks():
    annotated = PedagogicalValidationLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("pedagogical_validation_state" in block for block in annotated)
