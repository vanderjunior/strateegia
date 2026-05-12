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
