from app.services.session_coherence import SessionCoherenceLayer


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    curriculum_role: str = "active",
    review_intensity: str = "medium",
    pedagogical_mode: str = "conceptual_reinforcement",
    cognitive_load_score: float = 0.56,
    retrieval_intensity: str = "medium",
    narrative_relation: str = "continuation",
    continuity_signal: float = 0.62,
    pedagogical_expression_mode: str = "progressive_anchor",
    micro_intervention: str = "verification_step",
    question_index: int = 1,
) -> dict:
    return {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "topic_title": topic_id,
        "curriculum_role": curriculum_role,
        "review_intensity": review_intensity,
        "pedagogical_mode": pedagogical_mode,
        "cognitive_load_score": cognitive_load_score,
        "retrieval_intensity": retrieval_intensity,
        "narrative_relation": narrative_relation,
        "continuity_signal": continuity_signal,
        "pedagogical_expression_mode": pedagogical_expression_mode,
        "micro_intervention": micro_intervention,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }


def test_session_coherence_is_deterministic():
    blocks = [
        build_block(block_id="a", block_type="summary", question_index=0),
        build_block(block_id="b"),
        build_block(block_id="c", topic_id="topic-b", narrative_relation="contrast"),
    ]

    first = SessionCoherenceLayer().annotate(blocks)
    second = SessionCoherenceLayer().annotate(blocks)

    assert first == second


def test_session_coherence_detects_stable_progression():
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0, cognitive_load_score=0.54),
        build_block(block_id="q1", cognitive_load_score=0.56, continuity_signal=0.72),
        build_block(block_id="q2", cognitive_load_score=0.58, continuity_signal=0.74),
    ]

    annotated = SessionCoherenceLayer().annotate(blocks)

    assert annotated[-1]["session_coherence_state"] in {"stable_progression", "conceptually_progressive"}
    assert 0.0 <= annotated[-1]["progression_continuity"] <= 1.0


def test_session_coherence_detects_retrieval_transition():
    blocks = [
        build_block(
            block_id="q1",
            pedagogical_mode="active_recall",
            retrieval_intensity="high",
            narrative_relation="contextual_recall",
            pedagogical_expression_mode="retrieval_softener",
            cognitive_load_score=0.62,
        ),
        build_block(
            block_id="q2",
            pedagogical_mode="reinforcement_check",
            retrieval_intensity="low",
            narrative_relation="recall",
            pedagogical_expression_mode="retrieval_softener",
            cognitive_load_score=0.34,
        ),
    ]

    annotated = SessionCoherenceLayer().annotate(blocks)

    assert annotated[1]["session_coherence_state"] == "retrieval_transition"
    assert annotated[1]["pacing_transition_reason"]


def test_session_coherence_detects_reconstruction_cluster():
    blocks = [
        build_block(
            block_id="q1",
            pedagogical_mode="guided_explanation",
            pedagogical_expression_mode="focused_reconstruction",
            micro_intervention="guided_reconstruction",
            cognitive_load_score=0.72,
        ),
        build_block(
            block_id="q2",
            pedagogical_mode="conceptual_reinforcement",
            pedagogical_expression_mode="focused_reconstruction",
            micro_intervention="guided_reconstruction",
            cognitive_load_score=0.7,
        ),
    ]

    annotated = SessionCoherenceLayer().annotate(blocks)

    assert annotated[1]["session_coherence_state"] == "reconstruction_cluster"


def test_session_coherence_preserves_order_and_bounded_signals():
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", cognitive_load_score=0.82, pedagogical_expression_mode="conceptual_clarifier"),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            cognitive_load_score=0.28,
            retrieval_intensity="low",
            narrative_relation="cumulative_resurfacing",
            curriculum_role="cumulative",
            review_intensity="light",
            pedagogical_expression_mode="cumulative_reactivation",
        ),
    ]

    annotated = SessionCoherenceLayer().annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["progression_continuity"] <= 1.0
        assert 0.0 <= block["framing_stability"] <= 1.0
        assert 0.0 <= block["cognitive_rhythm"] <= 1.0
