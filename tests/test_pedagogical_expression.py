from app.services.pedagogical_expression import resolve_pedagogical_expression


def test_expression_is_deterministic():
    kwargs = dict(
        block_type="summary",
        pedagogical_mode="guided_explanation",
        curriculum_role="active",
        review_intensity="deep",
        cognitive_load="high",
        retrieval_intensity="medium",
        narrative_relation="reinforcement",
        cognitive_momentum="conceptually_dense",
        micro_intervention="guided_reconstruction",
        dominant_facet="rule",
        trajectory_state="stabilizing",
    )

    first = resolve_pedagogical_expression(**kwargs)
    second = resolve_pedagogical_expression(**kwargs)

    assert first == second


def test_expression_prefers_conceptual_clarifier_for_dense_explanation():
    expression = resolve_pedagogical_expression(
        block_type="summary",
        pedagogical_mode="guided_explanation",
        curriculum_role="active",
        review_intensity="deep",
        cognitive_load="high",
        retrieval_intensity="medium",
        narrative_relation="reinforcement",
        cognitive_momentum="conceptually_dense",
        micro_intervention="guided_reconstruction",
        dominant_facet="definition",
        trajectory_state="emerging",
    )

    assert expression.pedagogical_expression_mode == "conceptual_clarifier"
    assert expression.explanation_density <= 1.0


def test_expression_softens_retrieval_when_session_is_retrieval_heavy():
    expression = resolve_pedagogical_expression(
        block_type="questions",
        pedagogical_mode="active_recall",
        curriculum_role="cumulative",
        review_intensity="light",
        cognitive_load="medium",
        retrieval_intensity="high",
        narrative_relation="contextual_recall",
        cognitive_momentum="retrieval_heavy",
        micro_intervention="semantic_reactivation",
        dominant_facet="recognition",
        trajectory_state="superficially_stable",
    )

    assert expression.pedagogical_expression_mode == "retrieval_softener"
    assert expression.retrieval_framing >= 0.0


def test_expression_reactivates_cumulative_content_smoothly():
    expression = resolve_pedagogical_expression(
        block_type="questions",
        pedagogical_mode="reinforcement_check",
        curriculum_role="cumulative",
        review_intensity="light",
        cognitive_load="low",
        retrieval_intensity="low",
        narrative_relation="cumulative_resurfacing",
        cognitive_momentum="balanced",
        micro_intervention="cumulative_bridge",
        dominant_facet="contextual_transfer",
        trajectory_state="transfer_fragile",
    )

    assert expression.pedagogical_expression_mode == "cumulative_reactivation"
    assert expression.transition_support_reason


def test_expression_handles_missing_metadata():
    expression = resolve_pedagogical_expression(
        block_type="summary",
        pedagogical_mode="",
        curriculum_role="",
        review_intensity="",
        cognitive_load="",
        retrieval_intensity="",
        narrative_relation="",
        cognitive_momentum="",
        micro_intervention="",
        dominant_facet="",
        trajectory_state="",
    )

    assert expression.pedagogical_expression_mode
    assert 0.0 <= expression.readability_adjustment <= 1.0
    assert 0.0 <= expression.pacing_adjustment <= 1.0
    assert 0.0 <= expression.cognitive_friction_reduction <= 1.0


def test_expression_family_helper_is_stable():
    from app.services.pedagogical_expression import expression_family

    assert expression_family("conceptual_clarifier") == "clarity"
    assert expression_family("retrieval_softener") == "retrieval"
    assert expression_family("unknown") == "neutral"
