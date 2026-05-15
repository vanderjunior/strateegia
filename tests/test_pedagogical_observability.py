from app.services.pedagogical_observability import PedagogicalObservabilityLayer, resolve_pedagogical_observability


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    pedagogical_mode: str = "conceptual_reinforcement",
    micro_intervention: str = "guided_reconstruction",
    retrieval_intensity: str = "medium",
    pedagogical_expression_mode: str = "focused_reconstruction",
    cognitive_compression_mode: str = "reconstruction_scaffolded",
    session_coherence_state: str = "stable_progression",
    cognitive_momentum: str = "stable",
    trajectory_state: str = "reconstruction_fragile",
    stabilization_stage: str = "stabilizing",
    explanation_density: float = 0.56,
    informational_density: float = 0.58,
    progression_continuity: float = 0.62,
    longitudinal_consistency: float = 0.48,
    reconstruction_fragility: float = 0.72,
    transfer_fragility: float = 0.12,
    cognitive_load_score: float = 0.64,
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "pedagogical_mode": pedagogical_mode,
        "micro_intervention": micro_intervention,
        "retrieval_intensity": retrieval_intensity,
        "pedagogical_expression_mode": pedagogical_expression_mode,
        "cognitive_compression_mode": cognitive_compression_mode,
        "session_coherence_state": session_coherence_state,
        "cognitive_momentum": cognitive_momentum,
        "trajectory_state": trajectory_state,
        "stabilization_stage": stabilization_stage,
        "explanation_density": explanation_density,
        "informational_density": informational_density,
        "progression_continuity": progression_continuity,
        "longitudinal_consistency": longitudinal_consistency,
        "reconstruction_fragility": reconstruction_fragility,
        "transfer_fragility": transfer_fragility,
        "cognitive_load_score": cognitive_load_score,
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


def test_pedagogical_observability_is_deterministic():
    kwargs = dict(
        current_block=build_block(block_id="q1"),
        recent_blocks=[build_block(block_id="s1", block_type="summary", question_index=0)],
    )

    first = resolve_pedagogical_observability(**kwargs)
    second = resolve_pedagogical_observability(**kwargs)

    assert first == second


def test_pedagogical_observability_detects_retrieval_dense_window():
    layer = PedagogicalObservabilityLayer()
    annotated = layer.annotate(
        [
            build_block(
                block_id="q1",
                retrieval_intensity="high",
                cognitive_momentum="retrieval_heavy",
                pedagogical_expression_mode="retrieval_softener",
                cognitive_compression_mode="retrieval_focused",
                micro_intervention="lightweight_retrieval",
                trajectory_state="superficially_stable",
                reconstruction_fragility=0.16,
                explanation_density=0.24,
                informational_density=0.28,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_intensity="high",
                cognitive_momentum="retrieval_heavy",
                pedagogical_expression_mode="retrieval_softener",
                cognitive_compression_mode="retrieval_focused",
                micro_intervention="semantic_reactivation",
                trajectory_state="superficially_stable",
                reconstruction_fragility=0.14,
                explanation_density=0.22,
                informational_density=0.26,
                question_index=2,
            ),
        ]
    )

    assert annotated[-1]["pedagogical_observability_state"] == "retrieval_dense"
    assert annotated[-1]["retrieval_pressure_accumulation"] > 0.0


def test_pedagogical_observability_detects_scaffold_saturation():
    layer = PedagogicalObservabilityLayer()
    annotated = layer.annotate(
        [
            build_block(block_id="q1", question_index=1),
            build_block(block_id="q2", question_index=2),
            build_block(block_id="q3", question_index=3),
        ]
    )

    assert annotated[-1]["pedagogical_observability_state"] == "scaffold_saturated"
    assert annotated[-1]["scaffold_density"] > 0.0


def test_pedagogical_observability_preserves_order_and_bounds():
    layer = PedagogicalObservabilityLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", topic_id="topic-a", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            session_coherence_state="continuity_stable",
            cognitive_momentum="balanced",
            pedagogical_expression_mode="stabilization_reassurance",
            cognitive_compression_mode="stable_compressed",
            micro_intervention="confidence_check",
            trajectory_state="consolidated",
            stabilization_stage="consolidated",
            reconstruction_fragility=0.08,
            explanation_density=0.24,
            informational_density=0.22,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["signal_overlap_density"] <= 1.0
        assert 0.0 <= block["retrieval_pressure_accumulation"] <= 1.0
        assert 0.0 <= block["compression_support_alignment"] <= 1.0
        assert 0.0 <= block["scaffold_density"] <= 1.0
        assert 0.0 <= block["continuity_stability"] <= 1.0
        assert 0.0 <= block["modulation_redundancy"] <= 1.0
        assert 0.0 <= block["expression_variation_balance"] <= 1.0
        assert 0.0 <= block["intervention_repetition_signal"] <= 1.0
        assert 0.0 <= block["trajectory_consistency"] <= 1.0


def test_pedagogical_observability_handles_sparse_legacy_blocks():
    annotated = PedagogicalObservabilityLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("pedagogical_observability_state" in block for block in annotated)
