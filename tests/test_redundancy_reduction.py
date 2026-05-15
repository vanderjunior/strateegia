from app.services.runtime_signal_normalization import normalize_runtime_signal_families


def build_block(**overrides):
    base = {
        "retrieval_intensity": "medium",
        "cognitive_momentum": "stable",
        "pedagogical_expression_mode": "progressive_anchor",
        "cognitive_compression_mode": "guided_compact",
        "adaptive_signal_state": "balanced_support",
        "pedagogical_observability_state": "stable",
        "runtime_trace_state": "trace_stable",
        "session_coherence_state": "stable_progression",
        "trajectory_state": "stabilizing",
        "stabilization_stage": "stabilizing",
        "modulation_overlap": 0.2,
        "signal_overlap_density": 0.22,
        "scaffold_density": 0.18,
        "retrieval_pressure_accumulation": 0.2,
        "longitudinal_retention": 0.58,
        "longitudinal_consistency": 0.6,
        "stabilization_quality": 0.56,
    }
    base.update(overrides)
    return base


def test_runtime_signal_normalization_is_deterministic():
    block = build_block(
        retrieval_intensity="high",
        cognitive_momentum="retrieval_heavy",
        pedagogical_expression_mode="retrieval_softener",
        cognitive_compression_mode="retrieval_focused",
        adaptive_signal_state="retrieval_saturation",
        pedagogical_observability_state="retrieval_dense",
        runtime_trace_state="retrieval_clustered",
    )

    first = normalize_runtime_signal_families(block)
    second = normalize_runtime_signal_families(block)

    assert first == second


def test_runtime_signal_normalization_groups_retrieval_signals():
    profile = normalize_runtime_signal_families(
        build_block(
            retrieval_intensity="high",
            cognitive_momentum="retrieval_heavy",
            pedagogical_expression_mode="retrieval_softener",
            cognitive_compression_mode="retrieval_focused",
            adaptive_signal_state="retrieval_saturation",
            pedagogical_observability_state="retrieval_dense",
            runtime_trace_state="retrieval_clustered",
            retrieval_pressure_accumulation=0.64,
        )
    )

    assert profile.retrieval_family == "retrieval_dense"


def test_runtime_signal_normalization_groups_support_signals():
    profile = normalize_runtime_signal_families(
        build_block(
            trajectory_state="reconstruction_fragile",
            cognitive_compression_mode="reconstruction_scaffolded",
            adaptive_signal_state="reconstruction_pressure",
            pedagogical_observability_state="scaffold_saturated",
            runtime_trace_state="support_accumulated",
            scaffold_density=0.68,
            signal_overlap_density=0.58,
        )
    )

    assert profile.support_family == "support_heavy"


def test_runtime_signal_normalization_groups_continuity_and_stabilization():
    profile = normalize_runtime_signal_families(
        build_block(
            session_coherence_state="continuity_stable",
            cognitive_momentum="balanced",
            trajectory_state="consolidated",
            stabilization_stage="consolidated",
            longitudinal_retention=0.84,
            longitudinal_consistency=0.78,
            stabilization_quality=0.8,
        )
    )

    assert profile.continuity_family == "continuity_stable"
    assert profile.stabilization_family == "stabilized"


def test_runtime_signal_normalization_bounds_overlap_descriptor():
    profile = normalize_runtime_signal_families(
        build_block(
            modulation_overlap=0.62,
            signal_overlap_density=0.58,
            adaptive_signal_state="support_convergent",
            pedagogical_observability_state="signal_redundant",
        )
    )

    assert profile.overlap_family in {"overlap_high", "overlap_moderate", "overlap_low"}
    assert profile.runtime_semantic_summary
