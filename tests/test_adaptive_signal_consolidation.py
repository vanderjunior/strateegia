from app.services.adaptive_signal_consolidation import resolve_adaptive_signal_consolidation


def test_adaptive_signal_consolidation_is_deterministic():
    kwargs = dict(
        pedagogical_mode="conceptual_reinforcement",
        micro_intervention="guided_reconstruction",
        cognitive_trajectory="reconstruction_fragile",
        cognitive_momentum="retrieval_heavy",
        session_coherence="pacing_fragile",
        compression_mode="reconstruction_scaffolded",
        expression_mode="focused_reconstruction",
        stabilization_state="stabilizing",
        retrieval_intensity="high",
        cognitive_load_score=0.72,
        informational_density=0.58,
        explanation_density=0.54,
        reconstruction_fragility=0.76,
        transfer_fragility=0.18,
        longitudinal_retention=0.34,
        progression_continuity=0.44,
    )

    first = resolve_adaptive_signal_consolidation(**kwargs)
    second = resolve_adaptive_signal_consolidation(**kwargs)

    assert first == second


def test_adaptive_signal_consolidation_detects_reconstruction_pressure():
    profile = resolve_adaptive_signal_consolidation(
        pedagogical_mode="conceptual_reinforcement",
        micro_intervention="guided_reconstruction",
        cognitive_trajectory="reconstruction_fragile",
        cognitive_momentum="pressured",
        session_coherence="reconstruction_cluster",
        compression_mode="reconstruction_scaffolded",
        expression_mode="focused_reconstruction",
        stabilization_state="emerging",
        retrieval_intensity="medium",
        cognitive_load_score=0.74,
        informational_density=0.62,
        explanation_density=0.58,
        reconstruction_fragility=0.82,
        transfer_fragility=0.1,
        longitudinal_retention=0.18,
        progression_continuity=0.48,
    )

    assert profile.adaptive_signal_state == "reconstruction_pressure"
    assert profile.reconstruction_support_balance > 0.0


def test_adaptive_signal_consolidation_detects_retrieval_saturation():
    profile = resolve_adaptive_signal_consolidation(
        pedagogical_mode="active_recall",
        micro_intervention="lightweight_retrieval",
        cognitive_trajectory="superficially_stable",
        cognitive_momentum="retrieval_heavy",
        session_coherence="retrieval_transition",
        compression_mode="retrieval_focused",
        expression_mode="retrieval_softener",
        stabilization_state="stabilizing",
        retrieval_intensity="high",
        cognitive_load_score=0.38,
        informational_density=0.28,
        explanation_density=0.24,
        reconstruction_fragility=0.12,
        transfer_fragility=0.08,
        longitudinal_retention=0.42,
        progression_continuity=0.68,
    )

    assert profile.adaptive_signal_state == "retrieval_saturation"
    assert profile.retrieval_pressure_balance > 0.0


def test_adaptive_signal_consolidation_detects_compressed_stability():
    profile = resolve_adaptive_signal_consolidation(
        pedagogical_mode="reinforcement_check",
        micro_intervention="confidence_check",
        cognitive_trajectory="consolidated",
        cognitive_momentum="balanced",
        session_coherence="continuity_stable",
        compression_mode="stable_compressed",
        expression_mode="stabilization_reassurance",
        stabilization_state="consolidated",
        retrieval_intensity="low",
        cognitive_load_score=0.24,
        informational_density=0.22,
        explanation_density=0.26,
        reconstruction_fragility=0.06,
        transfer_fragility=0.08,
        longitudinal_retention=0.84,
        progression_continuity=0.78,
    )

    assert profile.adaptive_signal_state == "compressed_stability"
    assert profile.stabilization_consolidation > 0.0


def test_adaptive_signal_consolidation_handles_missing_metadata():
    profile = resolve_adaptive_signal_consolidation(
        pedagogical_mode="",
        micro_intervention="",
        cognitive_trajectory="",
        cognitive_momentum="",
        session_coherence="",
        compression_mode="",
        expression_mode="",
        stabilization_state="",
        retrieval_intensity="",
        cognitive_load_score=0.0,
        informational_density=0.0,
        explanation_density=0.0,
        reconstruction_fragility=0.0,
        transfer_fragility=0.0,
        longitudinal_retention=0.0,
        progression_continuity=0.0,
    )

    assert profile.adaptive_signal_state
    assert 0.0 <= profile.modulation_overlap <= 1.0
    assert 0.0 <= profile.reinforcement_convergence <= 1.0
    assert 0.0 <= profile.retrieval_pressure_balance <= 1.0
    assert 0.0 <= profile.reconstruction_support_balance <= 1.0
    assert 0.0 <= profile.pacing_consolidation <= 1.0
    assert 0.0 <= profile.stabilization_consolidation <= 1.0
    assert 0.0 <= profile.cognitive_signal_alignment <= 1.0
