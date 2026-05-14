from app.services.cognitive_trajectory import analyze_cognitive_trajectory


def build_performance(**overrides):
    base = {
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "recent_errors": 0,
    }
    base.update(overrides)
    return base


def build_memory(**overrides):
    base = {
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "resurfacing_cycles": 0,
        "successful_resurfacing_cycles": 0,
        "stabilization_level": 0.0,
        "retrieval_success_trend": 0.5,
        "fatigue_exposure": 0.0,
    }
    base.update(overrides)
    return base


def build_facet(**overrides):
    base = {
        "dominant_facet": "recognition",
        "recognition_signal": 0.5,
        "reconstruction_signal": 0.1,
        "transfer_signal": 0.1,
    }
    base.update(overrides)
    return base


def test_superficial_stabilization_detection():
    trajectory = analyze_cognitive_trajectory(
        performance=build_performance(consecutive_correct=3),
        pedagogical_memory=build_memory(
            recent_effectiveness="effective",
            stabilization_level=0.55,
            resurfacing_cycles=3,
            successful_resurfacing_cycles=0,
            retrieval_success_trend=0.55,
        ),
        facet_profile=build_facet(dominant_facet="recognition", recognition_signal=0.75),
    )

    assert trajectory.trajectory_state == "superficially_stable"
    assert trajectory.false_fluency_signal > 0.0


def test_recognition_and_reconstruction_can_diverge():
    trajectory = analyze_cognitive_trajectory(
        performance=build_performance(consecutive_correct=1, consecutive_incorrect=2, recent_errors=1),
        pedagogical_memory=build_memory(recent_effectiveness="ineffective", stabilization_level=0.3),
        facet_profile=build_facet(
            dominant_facet="reconstruction",
            recognition_signal=0.65,
            reconstruction_signal=0.8,
        ),
    )

    assert trajectory.trajectory_state in {"reconstruction_fragile", "unstable"}
    assert trajectory.reconstruction_fragility >= trajectory.false_fluency_signal


def test_transfer_fragility_detection():
    trajectory = analyze_cognitive_trajectory(
        performance=build_performance(consecutive_correct=1, recent_errors=1),
        pedagogical_memory=build_memory(
            recent_effectiveness="ineffective",
            resurfacing_cycles=4,
            successful_resurfacing_cycles=1,
            stabilization_level=0.35,
        ),
        facet_profile=build_facet(
            dominant_facet="contextual_transfer",
            transfer_signal=0.82,
            recognition_signal=0.2,
        ),
    )

    assert trajectory.trajectory_state == "transfer_fragile"
    assert trajectory.transfer_fragility > 0.0


def test_consolidated_trajectory_requires_longitudinal_success():
    trajectory = analyze_cognitive_trajectory(
        performance=build_performance(consecutive_correct=4),
        pedagogical_memory=build_memory(
            recent_effectiveness="effective",
            consecutive_successes=4,
            resurfacing_cycles=4,
            successful_resurfacing_cycles=4,
            stabilization_level=0.85,
            retrieval_success_trend=0.9,
        ),
        facet_profile=build_facet(dominant_facet="definition", recognition_signal=0.2),
    )

    assert trajectory.trajectory_state == "consolidated"
    assert trajectory.longitudinal_consistency >= 0.0


def test_cognitive_trajectory_is_bounded_and_tolerant():
    trajectory = analyze_cognitive_trajectory(
        performance={},
        pedagogical_memory={},
        facet_profile={},
    )

    assert trajectory.trajectory_state
    assert 0.0 <= trajectory.stabilization_quality <= 1.0
    assert 0.0 <= trajectory.false_fluency_signal <= 1.0
    assert 0.0 <= trajectory.reconstruction_fragility <= 1.0
    assert 0.0 <= trajectory.transfer_fragility <= 1.0
    assert 0.0 <= trajectory.longitudinal_consistency <= 1.0
