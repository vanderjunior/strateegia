from app.services.micro_interventions import resolve_micro_intervention


def build_profile(**overrides):
    base = {
        "pedagogical_mode": "reinforcement_check",
        "intervention_reason": "Base",
        "explanation_depth": "light",
        "retrieval_intensity": "low",
        "reinforcement_level": "low",
        "cognitive_load": "low",
        "cognitive_load_score": 0.28,
        "stabilization_stage": "consolidated",
        "longitudinal_retention": 0.72,
        "intervention_fatigue": 0.18,
        "profile_breakdown": {},
    }
    base.update(overrides)
    return base


def build_relationship(**overrides):
    base = {
        "relationship_type": None,
        "relationship_reason": None,
        "conceptual_anchor": None,
        "prerequisite_signal": 0.0,
        "conceptual_transition": None,
        "semantic_continuity_reason": None,
        "why_this_before_that": None,
    }
    base.update(overrides)
    return base


def test_prerequisite_reminder_selected_before_application():
    intervention = resolve_micro_intervention(
        block_type="question",
        curriculum_role="active",
        review_intensity="medium",
        pedagogical_profile=build_profile(
            pedagogical_mode="contextual_application",
            explanation_depth="medium",
            retrieval_intensity="medium",
            cognitive_load="medium",
            cognitive_load_score=0.58,
            stabilization_stage="emerging",
            longitudinal_retention=0.3,
        ),
        relationship_signal=build_relationship(
            relationship_type="applied_by",
            prerequisite_signal=0.68,
            conceptual_anchor="Conceito",
        ),
        facet_profile={"dominant_facet": "application", "transfer_signal": 0.65, "reconstruction_signal": 0.2, "recognition_signal": 0.1},
    )

    assert intervention.intervention_type == "prerequisite_recall"
    assert intervention.conceptual_support_reason


def test_exception_alignment_selected_for_exception_block():
    intervention = resolve_micro_intervention(
        block_type="summary",
        curriculum_role="active",
        review_intensity="deep",
        pedagogical_profile=build_profile(
            pedagogical_mode="conceptual_reinforcement",
            explanation_depth="deep",
            retrieval_intensity="medium",
            cognitive_load="high",
            cognitive_load_score=0.8,
            stabilization_stage="unstable",
            longitudinal_retention=0.22,
        ),
        relationship_signal=build_relationship(
            relationship_type="exception_of",
            prerequisite_signal=0.55,
            conceptual_anchor="Regra",
        ),
        facet_profile={"dominant_facet": "exception", "transfer_signal": 0.1, "reconstruction_signal": 0.25, "recognition_signal": 0.15},
    )

    assert intervention.intervention_type == "exception_alignment"


def test_lightweight_retrieval_selected_after_stabilization():
    intervention = resolve_micro_intervention(
        block_type="summary",
        curriculum_role="cumulative",
        review_intensity="light",
        pedagogical_profile=build_profile(
            pedagogical_mode="rapid_review",
            stabilization_stage="resilient",
            longitudinal_retention=0.84,
            intervention_fatigue=0.32,
        ),
        relationship_signal=build_relationship(),
    )

    assert intervention.intervention_type == "lightweight_retrieval"


def test_confidence_check_selected_for_stable_question_block():
    intervention = resolve_micro_intervention(
        block_type="question",
        curriculum_role="cumulative",
        review_intensity="light",
        pedagogical_profile=build_profile(
            pedagogical_mode="reinforcement_check",
            stabilization_stage="consolidated",
            longitudinal_retention=0.78,
        ),
        relationship_signal=build_relationship(),
    )

    assert intervention.intervention_type == "confidence_check"


def test_cumulative_bridge_selected_for_resurfacing():
    intervention = resolve_micro_intervention(
        block_type="question",
        curriculum_role="cumulative",
        review_intensity="light",
        pedagogical_profile=build_profile(
            pedagogical_mode="active_recall",
            stabilization_stage="stabilizing",
            longitudinal_retention=0.62,
            retrieval_intensity="high",
            cognitive_load="medium",
            cognitive_load_score=0.48,
        ),
        relationship_signal=build_relationship(
            relationship_type="cumulative_extension",
            conceptual_anchor="Conceito Base",
        ),
        facet_profile={"dominant_facet": "contextual_transfer", "transfer_signal": 0.7, "reconstruction_signal": 0.2, "recognition_signal": 0.15},
    )

    assert intervention.intervention_type == "cumulative_bridge"


def test_micro_intervention_selection_is_deterministic_and_bounded():
    kwargs = dict(
        block_type="question",
        curriculum_role="active",
        review_intensity="medium",
        pedagogical_profile=build_profile(
            pedagogical_mode="contextual_application",
            explanation_depth="medium",
            retrieval_intensity="medium",
            cognitive_load="medium",
            cognitive_load_score=0.58,
            stabilization_stage="emerging",
            longitudinal_retention=0.3,
        ),
        relationship_signal=build_relationship(
            relationship_type="applied_by",
            prerequisite_signal=0.68,
            conceptual_anchor="Conceito",
        ),
        facet_profile={"dominant_facet": "application", "transfer_signal": 0.65, "reconstruction_signal": 0.2, "recognition_signal": 0.1},
    )

    first = resolve_micro_intervention(**kwargs)
    second = resolve_micro_intervention(**kwargs)

    assert first == second
    assert 0.0 <= first.intervention_signal.support_strength <= 1.0
    assert 0.0 <= first.intervention_signal.retrieval_shift <= 1.0
    assert 0.0 <= first.intervention_signal.fatigue_mitigation <= 1.0


def test_micro_intervention_handles_missing_metadata():
    intervention = resolve_micro_intervention(
        block_type="question",
        curriculum_role="active",
        review_intensity="medium",
        pedagogical_profile={},
        relationship_signal={},
        facet_profile={},
    )

    assert intervention.intervention_type
    assert intervention.why_this_intervention
