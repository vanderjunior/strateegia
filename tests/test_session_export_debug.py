from app.services.session_export_debug import (
    SessionExportDebugLayer,
    build_behavioral_diff_export,
    build_session_export_snapshot,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    pedagogical_mode: str = "conceptual_reinforcement",
    micro_intervention: str = "guided_reconstruction",
    trajectory_state: str = "stabilizing",
    cognitive_compression_mode: str = "guided_compact",
    pedagogical_expression_mode: str = "conceptual_clarifier",
    session_coherence_state: str = "continuity_stable",
    session_stability_state: str = "balanced",
    pedagogical_tuning_state: str = "balanced_support",
    validation_harness_state: str = "validation_stable",
    behavioral_diff_state: str = "behavior_stable",
    runtime_trace_state: str = "runtime_balanced",
    pedagogical_validation_state: str = "support_balanced",
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilized",
    overlap_family: str = "overlap_low",
    retrieval_density_metric: float = 0.22,
    scaffold_load_metric: float = 0.24,
    continuity_smoothness_metric: float = 0.72,
    reconstruction_pressure_metric: float = 0.18,
    compression_safety_metric: float = 0.74,
    stabilization_sustainability_metric: float = 0.7,
    validation_confidence: float = 0.7,
    runtime_behavior_delta: float = 0.06,
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "pedagogical_mode": pedagogical_mode,
        "micro_intervention": micro_intervention,
        "trajectory_state": trajectory_state,
        "cognitive_compression_mode": cognitive_compression_mode,
        "pedagogical_expression_mode": pedagogical_expression_mode,
        "session_coherence_state": session_coherence_state,
        "session_stability_state": session_stability_state,
        "pedagogical_tuning_state": pedagogical_tuning_state,
        "validation_harness_state": validation_harness_state,
        "behavioral_diff_state": behavioral_diff_state,
        "runtime_trace_state": runtime_trace_state,
        "pedagogical_validation_state": pedagogical_validation_state,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
        "retrieval_density_metric": retrieval_density_metric,
        "scaffold_load_metric": scaffold_load_metric,
        "continuity_smoothness_metric": continuity_smoothness_metric,
        "reconstruction_pressure_metric": reconstruction_pressure_metric,
        "compression_safety_metric": compression_safety_metric,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "validation_confidence": validation_confidence,
        "runtime_behavior_delta": runtime_behavior_delta,
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


def test_session_export_snapshot_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = build_session_export_snapshot(blocks)
    second = build_session_export_snapshot(blocks)

    assert first == second


def test_session_export_snapshot_exposes_normalized_sections():
    snapshot = build_session_export_snapshot(
        [
            build_block(
                block_id="q1",
                session_stability_state="retrieval_heavy",
                validation_harness_state="retrieval_fragile",
                behavioral_diff_state="retrieval_increased",
                retrieval_density_metric=0.82,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                session_stability_state="retrieval_heavy",
                validation_harness_state="retrieval_fragile",
                behavioral_diff_state="retrieval_increased",
                retrieval_density_metric=0.78,
                question_index=2,
            ),
        ]
    )

    assert snapshot.session_export_state == "export_ready"
    assert snapshot.runtime_export_summary
    assert snapshot.pedagogical_runtime_snapshot["pedagogical_mode"] == "conceptual_reinforcement"
    assert snapshot.behavioral_diff_snapshot["state"] == "retrieval_increased"
    assert snapshot.retrieval_snapshot["density"] >= 0.7


def test_behavioral_diff_export_detects_divergent_runtime():
    export = build_behavioral_diff_export(
        [
            build_block(
                block_id="q1",
                behavioral_diff_state="overlap_increased",
                runtime_behavior_delta=0.22,
                question_index=1,
            ),
            build_block(
                block_id="q2",
                behavioral_diff_state="behaviorally_divergent",
                runtime_behavior_delta=0.28,
                question_index=2,
            ),
        ]
    )

    assert export.behavioral_diff_state == "behaviorally_divergent"
    assert export.runtime_behavior_delta > 0.0
    assert export.divergence_summary


def test_session_export_debug_layer_preserves_order():
    layer = SessionExportDebugLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(block_id="q2", topic_id="topic-b", question_index=2),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    assert all("session_export_state" in block for block in annotated)
    assert all("runtime_export_summary" in block for block in annotated)


def test_session_export_debug_layer_handles_sparse_legacy_blocks():
    annotated = SessionExportDebugLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("session_export_state" in block for block in annotated)
