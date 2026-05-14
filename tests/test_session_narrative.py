from app.services.session_narrative import SessionNarrativeLayer


def build_block(
    *,
    block_id: str,
    block_type: str = "question",
    topic_id: str = "topic-a",
    topic_title: str = "Topic A",
    curriculum_role: str = "active",
    review_intensity: str = "deep",
    pedagogical_mode: str = "guided_explanation",
    cognitive_load_score: float = 0.8,
    explanation_depth: str = "deep",
    retrieval_intensity: str = "high",
    stabilization_stage: str = "unstable",
    longitudinal_retention: float = 0.1,
    microtopic_id: str | None = "mt-a",
    question_index: int = 1,
) -> dict:
    return {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "topic_title": topic_title,
        "curriculum_role": curriculum_role,
        "review_intensity": review_intensity,
        "pedagogical_mode": pedagogical_mode,
        "cognitive_load_score": cognitive_load_score,
        "cognitive_load": "high" if cognitive_load_score >= 0.72 else "medium",
        "explanation_depth": explanation_depth,
        "retrieval_intensity": retrieval_intensity,
        "stabilization_stage": stabilization_stage,
        "longitudinal_retention": longitudinal_retention,
        "microtopic_id": microtopic_id,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }


def test_session_narrative_detects_application_after_explanation():
    blocks = [
        build_block(
            block_id="summary-a",
            block_type="summary",
            topic_id="topic-ripam",
            topic_title="RIPAM",
            pedagogical_mode="guided_explanation",
            microtopic_id=None,
            question_index=0,
        ),
        build_block(
            block_id="question-a",
            topic_id="topic-ripam",
            topic_title="RIPAM",
            pedagogical_mode="contextual_application",
            cognitive_load_score=0.61,
            explanation_depth="medium",
            retrieval_intensity="medium",
            microtopic_id="mt-excecao",
            question_index=0,
        ),
    ]

    annotated = SessionNarrativeLayer().annotate(blocks)

    assert annotated[1]["narrative_relation"] == "application"
    assert annotated[1]["narrative_role"] == "same_topic_progression"
    assert annotated[1]["continuity_signal"] > 0.0
    assert annotated[1]["contextual_anchor"] == "RIPAM"
    assert "contextualiza" in annotated[1]["why_this_after_previous"].lower()


def test_session_narrative_marks_cumulative_resurfacing():
    blocks = [
        build_block(
            block_id="question-active",
            topic_id="topic-active",
            topic_title="Tema Ativo",
            curriculum_role="active",
            pedagogical_mode="guided_explanation",
            cognitive_load_score=0.84,
            microtopic_id="mt-ativo",
        ),
        build_block(
            block_id="question-cumulative",
            topic_id="topic-old",
            topic_title="Tema Antigo",
            curriculum_role="cumulative",
            review_intensity="light",
            pedagogical_mode="reinforcement_check",
            cognitive_load_score=0.24,
            explanation_depth="light",
            retrieval_intensity="low",
            stabilization_stage="consolidated",
            longitudinal_retention=0.83,
            microtopic_id="mt-old",
        ),
    ]

    annotated = SessionNarrativeLayer().annotate(blocks)

    assert annotated[1]["narrative_relation"] == "cumulative_resurfacing"
    assert annotated[1]["recall_reason"]
    assert annotated[1]["continuity_signal"] >= 0.15


def test_session_narrative_breaks_heavy_followup_streak_with_local_swap():
    blocks = [
        build_block(
            block_id="summary-a",
            block_type="summary",
            topic_id="topic-a",
            topic_title="Topic A",
            pedagogical_mode="guided_explanation",
            cognitive_load_score=0.78,
            microtopic_id=None,
            question_index=0,
        ),
        build_block(
            block_id="question-a0",
            topic_id="topic-a",
            topic_title="Topic A",
            pedagogical_mode="guided_explanation",
            cognitive_load_score=0.86,
            microtopic_id="mt-a0",
            question_index=0,
        ),
        build_block(
            block_id="question-a1",
            topic_id="topic-a",
            topic_title="Topic A",
            pedagogical_mode="conceptual_reinforcement",
            cognitive_load_score=0.83,
            microtopic_id="mt-a1",
            question_index=1,
        ),
        build_block(
            block_id="question-b1",
            topic_id="topic-b",
            topic_title="Topic B",
            curriculum_role="cumulative",
            review_intensity="light",
            pedagogical_mode="reinforcement_check",
            cognitive_load_score=0.21,
            explanation_depth="light",
            retrieval_intensity="low",
            stabilization_stage="consolidated",
            longitudinal_retention=0.88,
            microtopic_id="mt-b1",
            question_index=1,
        ),
    ]

    annotated = SessionNarrativeLayer().annotate(blocks)

    assert [block["id"] for block in annotated] == [
        "summary-a",
        "question-a0",
        "question-b1",
        "question-a1",
    ]


def test_session_narrative_preserves_deterministic_order_and_bounded_signals():
    blocks = [
        build_block(block_id="question-1", topic_id="topic-a", topic_title="Tema A", microtopic_id="mt-1"),
        build_block(
            block_id="question-2",
            topic_id="topic-b",
            topic_title="Tema B",
            pedagogical_mode="active_recall",
            cognitive_load_score=0.42,
            explanation_depth="light",
            retrieval_intensity="high",
            microtopic_id="mt-2",
        ),
    ]

    layer = SessionNarrativeLayer()
    first = layer.annotate(blocks)
    second = layer.annotate(blocks)

    assert [block["id"] for block in first] == [block["id"] for block in second]
    for block in first:
        assert 0.0 <= block["continuity_signal"] <= 1.0
        assert block["transition_reason"]
        assert block["narrative_relation"]


def test_session_narrative_uses_exception_relationship_as_local_contrast():
    blocks = [
        build_block(
            block_id="question-rule",
            topic_id="topic-nav",
            topic_title="Navegacao",
            pedagogical_mode="guided_explanation",
            microtopic_id="mt-rule",
            question_index=0,
        ),
        build_block(
            block_id="question-exception",
            topic_id="topic-nav",
            topic_title="Navegacao",
            pedagogical_mode="conceptual_reinforcement",
            cognitive_load_score=0.64,
            microtopic_id="mt-exception",
            question_index=1,
        )
        | {
            "relationship_type": "exception_of",
            "relationship_reason": "A excecao depende da regra geral imediatamente anterior.",
            "conceptual_transition": "rule_before_exception",
        },
    ]

    annotated = SessionNarrativeLayer().annotate(blocks)

    assert annotated[1]["narrative_relation"] == "contrast"
    assert annotated[1]["comparison_reason"]


def test_session_narrative_keeps_transition_reason_stable_for_local_progression():
    blocks = [
        build_block(
            block_id="summary-a",
            block_type="summary",
            topic_id="topic-a",
            topic_title="Topic A",
            pedagogical_mode="guided_explanation",
            microtopic_id=None,
            question_index=0,
        ),
        build_block(
            block_id="question-a",
            topic_id="topic-a",
            topic_title="Topic A",
            pedagogical_mode="conceptual_reinforcement",
            cognitive_load_score=0.6,
            explanation_depth="medium",
            retrieval_intensity="medium",
            microtopic_id="mt-a",
            question_index=0,
        ) | {
            "pedagogical_expression_mode": "progressive_anchor",
        },
    ]

    annotated = SessionNarrativeLayer().annotate(blocks)

    assert "Refino expressivo" in annotated[1]["transition_reason"]
