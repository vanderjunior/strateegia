from app.services.pedagogical_adapter import resolve_pedagogical_profile


def build_performance(**overrides):
    base = {
        "error_distribution": {
            "conceptual": 0,
            "interpretation": 0,
            "memory": 0,
            "attention": 0,
        },
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
    }
    base.update(overrides)
    return base


def build_pedagogical_memory(**overrides):
    base = {
        "last_pedagogical_mode": None,
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "consecutive_failures": 0,
        "stabilization_level": 0.0,
        "escalation_level": 0.0,
        "retrieval_success_trend": 0.5,
        "intervention_history": {},
        "resurfacing_cycles": 0,
        "successful_resurfacing_cycles": 0,
        "fatigue_exposure": 0.0,
        "recovery_count": 0,
        "last_stabilized_at": None,
    }
    base.update(overrides)
    return base


def test_conceptual_weakness_uses_deeper_explanation_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="deep",
        weakness_signal=0.8,
        resurfacing_signal=0.2,
        performance=build_performance(error_distribution={"conceptual": 3}),
    )

    assert profile.pedagogical_mode in {"guided_explanation", "conceptual_reinforcement"}
    assert profile.explanation_depth == "deep"


def test_interpretation_weakness_uses_contextual_question_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="medium",
        weakness_signal=0.7,
        resurfacing_signal=0.1,
        performance=build_performance(error_distribution={"interpretation": 2}),
    )

    assert profile.pedagogical_mode == "contextual_application"


def test_memory_weakness_uses_rapid_recall_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.6,
        resurfacing_signal=0.3,
        performance=build_performance(error_distribution={"memory": 2}),
    )

    assert profile.pedagogical_mode == "active_recall"
    assert profile.retrieval_intensity == "high"


def test_attention_weakness_uses_lightweight_verification_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.35,
        resurfacing_signal=0.2,
        performance=build_performance(error_distribution={"attention": 2}),
    )

    assert profile.pedagogical_mode == "rapid_review"


def test_stabilized_microtopic_uses_minimal_reinforcement_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.1,
        resurfacing_signal=0.15,
        performance=build_performance(consecutive_correct=5),
    )

    assert profile.pedagogical_mode == "reinforcement_check"
    assert profile.reinforcement_level == "low"


def test_active_topics_receive_stronger_pedagogical_density_than_cumulative():
    active = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="deep",
        weakness_signal=0.3,
        resurfacing_signal=0.1,
        performance=build_performance(),
    )
    cumulative = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.3,
        resurfacing_signal=0.1,
        performance=build_performance(),
    )

    assert active.cognitive_load != cumulative.cognitive_load


def test_resurfaced_microtopic_prefers_recall_oriented_intervention():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.2,
        resurfacing_signal=0.8,
        performance=build_performance(),
    )

    assert profile.pedagogical_mode in {"active_recall", "reinforcement_check"}


def test_repeated_incorrect_streak_intensifies_pedagogy():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="medium",
        weakness_signal=0.5,
        resurfacing_signal=0.2,
        performance=build_performance(consecutive_incorrect=3, error_distribution={"conceptual": 1}),
    )

    assert profile.reinforcement_level in {"high", "medium"}
    assert profile.explanation_depth in {"medium", "deep"}


def test_repeated_correct_streak_reduces_intervention_pressure():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="medium",
        weakness_signal=0.2,
        resurfacing_signal=0.1,
        performance=build_performance(consecutive_correct=4),
    )

    assert profile.reinforcement_level in {"low", "medium"}


def test_pedagogical_mode_selection_is_deterministic():
    kwargs = dict(
        curriculum_role="active",
        review_intensity="deep",
        weakness_signal=0.7,
        resurfacing_signal=0.4,
        performance=build_performance(error_distribution={"conceptual": 2}),
    )

    first = resolve_pedagogical_profile(**kwargs)
    second = resolve_pedagogical_profile(**kwargs)

    assert first == second


def test_pedagogical_breakdown_is_bounded():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="deep",
        weakness_signal=1.0,
        resurfacing_signal=1.0,
        performance=build_performance(consecutive_incorrect=5, error_distribution={"conceptual": 5}),
    )

    assert all(0.0 <= value <= 1.0 for value in profile.profile_breakdown.values())
    assert 0.0 <= profile.cognitive_load_score <= 1.0


def test_pedagogical_adapter_handles_missing_metadata_safely():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.0,
        resurfacing_signal=0.0,
        performance={},
    )

    assert profile.pedagogical_mode
    assert profile.intervention_reason


def test_ineffective_active_recall_escalates_to_guided_explanation():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="medium",
        weakness_signal=0.55,
        resurfacing_signal=0.25,
        performance=build_performance(
            error_distribution={"memory": 3},
            consecutive_incorrect=2,
        ),
        pedagogical_memory=build_pedagogical_memory(
            last_pedagogical_mode="active_recall",
            recent_effectiveness="ineffective",
            consecutive_failures=2,
            escalation_level=0.7,
            intervention_history={
                "active_recall": {
                    "pedagogical_mode": "active_recall",
                    "total_attempts": 3,
                    "successful_attempts": 0,
                    "failed_attempts": 3,
                    "consecutive_failures": 2,
                    "confidence": 0.2,
                }
            },
        ),
    )

    assert profile.pedagogical_mode == "guided_explanation"
    assert profile.intervention_transition_reason
    assert profile.escalation_signal > 0.0


def test_effective_guided_explanation_can_stabilize_into_lighter_mode():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.18,
        resurfacing_signal=0.35,
        performance=build_performance(consecutive_correct=3),
        pedagogical_memory=build_pedagogical_memory(
            last_pedagogical_mode="guided_explanation",
            recent_effectiveness="effective",
            consecutive_successes=3,
            stabilization_level=0.8,
            retrieval_success_trend=0.9,
            intervention_history={
                "guided_explanation": {
                    "pedagogical_mode": "guided_explanation",
                    "total_attempts": 4,
                    "successful_attempts": 4,
                    "failed_attempts": 0,
                    "consecutive_successes": 3,
                    "confidence": 0.9,
                }
            },
        ),
    )

    assert profile.pedagogical_mode in {"reinforcement_check", "rapid_review"}
    assert profile.stabilization_signal > profile.escalation_signal


def test_pedagogical_profile_exposes_effectiveness_and_confidence_metadata():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="deep",
        weakness_signal=0.45,
        resurfacing_signal=0.2,
        performance=build_performance(error_distribution={"conceptual": 2}),
        pedagogical_memory=build_pedagogical_memory(
            last_pedagogical_mode="guided_explanation",
            recent_effectiveness="effective",
            intervention_history={
                "guided_explanation": {
                    "pedagogical_mode": "guided_explanation",
                    "total_attempts": 3,
                    "successful_attempts": 2,
                    "failed_attempts": 1,
                    "confidence": 0.72,
                }
            },
        ),
    )

    assert profile.intervention_effectiveness in {"effective", "neutral", "ineffective"}
    assert 0.0 <= profile.pedagogical_confidence <= 1.0
    assert profile.intervention_history_summary
    assert profile.adaptation_reasoning


def test_pedagogical_profile_exposes_longitudinal_stability_metadata():
    profile = resolve_pedagogical_profile(
        curriculum_role="cumulative",
        review_intensity="light",
        weakness_signal=0.15,
        resurfacing_signal=0.55,
        performance=build_performance(consecutive_correct=5),
        pedagogical_memory=build_pedagogical_memory(
            recent_effectiveness="effective",
            stabilization_level=0.75,
            retrieval_success_trend=0.88,
            resurfacing_cycles=4,
            successful_resurfacing_cycles=4,
            fatigue_exposure=0.25,
            recovery_count=1,
        ),
    )

    assert profile.longitudinal_retention >= 0.5
    assert profile.stabilization_stage in {"stabilizing", "consolidated", "resilient"}
    assert profile.retention_reasoning


def test_pedagogical_adapter_avoids_contextual_application_without_prerequisite_basis():
    profile = resolve_pedagogical_profile(
        curriculum_role="active",
        review_intensity="medium",
        weakness_signal=0.55,
        resurfacing_signal=0.1,
        performance=build_performance(error_distribution={"interpretation": 2}),
        relationship_signal={
            "relationship_type": "applied_by",
            "prerequisite_signal": 0.65,
            "relationship_reason": "Aplicacao depende de regra anterior.",
        },
    )

    assert profile.pedagogical_mode in {"guided_explanation", "conceptual_reinforcement"}
    assert "relationship" in profile.profile_breakdown
