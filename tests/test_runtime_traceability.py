from app.services.runtime_traceability import RuntimeTraceabilityLayer, resolve_runtime_traceability


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    pedagogical_mode: str = "conceptual_reinforcement",
    micro_intervention: str = "guided_reconstruction",
    pedagogical_expression_mode: str = "focused_reconstruction",
    cognitive_compression_mode: str = "reconstruction_scaffolded",
    adaptive_signal_state: str = "reconstruction_pressure",
    pedagogical_observability_state: str = "scaffold_saturated",
    cognitive_momentum: str = "pressured",
    session_coherence_state: str = "reconstruction_cluster",
    trajectory_state: str = "reconstruction_fragile",
    retrieval_intensity: str = "medium",
    cognitive_load_score: float = 0.66,
    reconstruction_fragility: float = 0.74,
    transfer_fragility: float = 0.18,
    progression_continuity: float = 0.52,
    longitudinal_consistency: float = 0.44,
    signal_overlap_density: float = 0.58,
    retrieval_pressure_accumulation: float = 0.34,
    scaffold_density: float = 0.62,
    modulation_overlap: float = 0.48,
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "pedagogical_mode": pedagogical_mode,
        "micro_intervention": micro_intervention,
        "pedagogical_expression_mode": pedagogical_expression_mode,
        "cognitive_compression_mode": cognitive_compression_mode,
        "adaptive_signal_state": adaptive_signal_state,
        "pedagogical_observability_state": pedagogical_observability_state,
        "cognitive_momentum": cognitive_momentum,
        "session_coherence_state": session_coherence_state,
        "trajectory_state": trajectory_state,
        "retrieval_intensity": retrieval_intensity,
        "cognitive_load_score": cognitive_load_score,
        "reconstruction_fragility": reconstruction_fragility,
        "transfer_fragility": transfer_fragility,
        "progression_continuity": progression_continuity,
        "longitudinal_consistency": longitudinal_consistency,
        "signal_overlap_density": signal_overlap_density,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "scaffold_density": scaffold_density,
        "modulation_overlap": modulation_overlap,
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


def test_runtime_traceability_is_deterministic():
    kwargs = dict(
        current_block=build_block(block_id="q1"),
        recent_blocks=[build_block(block_id="s1", block_type="summary", question_index=0)],
    )

    first = resolve_runtime_traceability(**kwargs)
    second = resolve_runtime_traceability(**kwargs)

    assert first == second


def test_runtime_traceability_detects_retrieval_cluster():
    layer = RuntimeTraceabilityLayer()
    annotated = layer.annotate(
        [
            build_block(
                block_id="q1",
                pedagogical_mode="active_recall",
                micro_intervention="lightweight_retrieval",
                pedagogical_expression_mode="retrieval_softener",
                cognitive_compression_mode="retrieval_focused",
                adaptive_signal_state="retrieval_saturation",
                pedagogical_observability_state="retrieval_dense",
                cognitive_momentum="retrieval_heavy",
                session_coherence_state="retrieval_transition",
                trajectory_state="superficially_stable",
                retrieval_intensity="high",
                reconstruction_fragility=0.12,
                signal_overlap_density=0.34,
                retrieval_pressure_accumulation=0.62,
                scaffold_density=0.18,
                modulation_overlap=0.3,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                pedagogical_mode="active_recall",
                micro_intervention="semantic_reactivation",
                pedagogical_expression_mode="retrieval_softener",
                cognitive_compression_mode="retrieval_focused",
                adaptive_signal_state="retrieval_saturation",
                pedagogical_observability_state="retrieval_dense",
                cognitive_momentum="retrieval_heavy",
                session_coherence_state="retrieval_transition",
                trajectory_state="superficially_stable",
                retrieval_intensity="high",
                reconstruction_fragility=0.1,
                signal_overlap_density=0.32,
                retrieval_pressure_accumulation=0.66,
                scaffold_density=0.16,
                modulation_overlap=0.28,
                question_index=2,
            ),
        ]
    )

    assert annotated[-1]["runtime_trace_state"] == "retrieval_clustered"
    assert annotated[-1]["retrieval_density_trace"]


def test_runtime_traceability_detects_support_accumulation():
    layer = RuntimeTraceabilityLayer()
    annotated = layer.annotate(
        [
            build_block(block_id="q1", question_index=1),
            build_block(block_id="q2", question_index=2),
        ]
    )

    assert annotated[-1]["runtime_trace_state"] == "support_accumulated"
    assert annotated[-1]["support_overlap_trace"]


def test_runtime_traceability_preserves_order_and_bounds():
    layer = RuntimeTraceabilityLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            pedagogical_mode="reinforcement_check",
            micro_intervention="confidence_check",
            pedagogical_expression_mode="stabilization_reassurance",
            cognitive_compression_mode="stable_compressed",
            adaptive_signal_state="compressed_stability",
            pedagogical_observability_state="adaptively_balanced",
            cognitive_momentum="balanced",
            session_coherence_state="continuity_stable",
            trajectory_state="consolidated",
            retrieval_intensity="low",
            cognitive_load_score=0.24,
            reconstruction_fragility=0.08,
            transfer_fragility=0.06,
            progression_continuity=0.74,
            longitudinal_consistency=0.72,
            signal_overlap_density=0.22,
            retrieval_pressure_accumulation=0.12,
            scaffold_density=0.18,
            modulation_overlap=0.16,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["trace_alignment"] <= 1.0


def test_runtime_traceability_handles_sparse_legacy_blocks():
    annotated = RuntimeTraceabilityLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("runtime_trace_state" in block for block in annotated)
