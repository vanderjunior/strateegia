from app.services.session_snapshot_diff import (
    SessionSnapshotDiffLayer,
    build_session_snapshot,
    compare_session_snapshots,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_density_metric: float = 0.22,
    scaffold_load_metric: float = 0.24,
    continuity_smoothness_metric: float = 0.7,
    reconstruction_pressure_metric: float = 0.18,
    compression_safety_metric: float = 0.74,
    modulation_convergence_metric: float = 0.22,
    stabilization_sustainability_metric: float = 0.7,
    pacing_stability_metric: float = 0.68,
    cognitive_balance_metric: float = 0.7,
    support_density: float = 0.24,
    adaptive_overlap_signal: float = 0.18,
    validation_confidence: float = 0.7,
    session_stability_state: str = "balanced",
    validation_harness_state: str = "validation_stable",
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
        "modulation_convergence_metric": modulation_convergence_metric,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "pacing_stability_metric": pacing_stability_metric,
        "cognitive_balance_metric": cognitive_balance_metric,
        "support_density": support_density,
        "adaptive_overlap_signal": adaptive_overlap_signal,
        "validation_confidence": validation_confidence,
        "session_stability_state": session_stability_state,
        "validation_harness_state": validation_harness_state,
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


def test_session_snapshot_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = build_session_snapshot(blocks)
    second = build_session_snapshot(blocks)

    assert first == second


def test_session_snapshot_detects_retrieval_heavy_profile():
    snapshot = build_session_snapshot(
        [
            build_block(
                block_id="q1",
                retrieval_density_metric=0.82,
                cognitive_balance_metric=0.46,
                session_stability_state="retrieval_heavy",
                validation_harness_state="retrieval_fragile",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_density_metric=0.78,
                cognitive_balance_metric=0.44,
                session_stability_state="retrieval_heavy",
                validation_harness_state="retrieval_fragile",
                question_index=2,
            ),
        ]
    )

    assert snapshot.session_snapshot_state == "retrieval_heavy"
    assert snapshot.retrieval_density >= 0.7


def test_behavioral_diff_detects_scaffold_accumulation():
    previous = build_session_snapshot(
        [
            build_block(block_id="q1", scaffold_load_metric=0.24, support_density=0.22, question_index=1),
            build_block(block_id="q2", scaffold_load_metric=0.26, support_density=0.24, question_index=2),
        ]
    )
    current = build_session_snapshot(
        [
            build_block(block_id="q1", scaffold_load_metric=0.62, support_density=0.6, question_index=1),
            build_block(block_id="q2", scaffold_load_metric=0.68, support_density=0.64, question_index=2),
        ]
    )

    diff = compare_session_snapshots(previous, current)

    assert diff.behavioral_diff_state == "scaffold_accumulated"
    assert diff.scaffold_shift > 0.0


def test_behavioral_diff_detects_continuity_improvement():
    previous = build_session_snapshot(
        [
            build_block(block_id="q1", continuity_smoothness_metric=0.38, pacing_stability_metric=0.42, question_index=1),
            build_block(block_id="q2", continuity_smoothness_metric=0.4, pacing_stability_metric=0.44, question_index=2),
        ]
    )
    current = build_session_snapshot(
        [
            build_block(block_id="q1", continuity_smoothness_metric=0.74, pacing_stability_metric=0.68, question_index=1),
            build_block(block_id="q2", continuity_smoothness_metric=0.76, pacing_stability_metric=0.7, question_index=2),
        ]
    )

    diff = compare_session_snapshots(previous, current)

    assert diff.behavioral_diff_state == "continuity_improved"
    assert diff.continuity_shift > 0.0


def test_snapshot_diff_layer_preserves_order_and_bounds():
    layer = SessionSnapshotDiffLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            retrieval_density_metric=0.3,
            scaffold_load_metric=0.28,
            continuity_smoothness_metric=0.72,
            reconstruction_pressure_metric=0.24,
            compression_safety_metric=0.76,
            modulation_convergence_metric=0.2,
            stabilization_sustainability_metric=0.72,
            pacing_stability_metric=0.7,
            cognitive_balance_metric=0.72,
            support_density=0.26,
            adaptive_overlap_signal=0.16,
            validation_confidence=0.72,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["runtime_behavior_delta"] <= 1.0
        assert 0.0 <= block["retrieval_shift"] <= 1.0
        assert -1.0 <= block["scaffold_shift"] <= 1.0
        assert -1.0 <= block["continuity_shift"] <= 1.0
        assert -1.0 <= block["pacing_shift"] <= 1.0
        assert -1.0 <= block["compression_shift"] <= 1.0
        assert -1.0 <= block["stabilization_shift"] <= 1.0
        assert -1.0 <= block["overlap_shift"] <= 1.0
        assert -1.0 <= block["validation_shift"] <= 1.0


def test_snapshot_diff_layer_handles_sparse_legacy_blocks():
    annotated = SessionSnapshotDiffLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("session_snapshot_state" in block for block in annotated)
    assert all("behavioral_diff_state" in block for block in annotated)
