from app.services.cognitive_compression import resolve_cognitive_compression


def test_cognitive_compression_is_deterministic():
    kwargs = dict(
        block_type="summary",
        pedagogical_mode="conceptual_reinforcement",
        curriculum_role="active",
        review_intensity="deep",
        relationship_signal={"prerequisite_signal": 0.2, "relationship_type": None},
        pedagogical_profile={"intervention_fatigue": 0.1, "longitudinal_retention": 0.2},
        facet_profile={"dominant_facet": "rule", "transfer_signal": 0.1, "reconstruction_signal": 0.2},
        trajectory_profile={"trajectory_state": "stabilizing", "transfer_fragility": 0.1, "reconstruction_fragility": 0.2},
        expression_profile={"pedagogical_expression_mode": "conceptual_clarifier", "explanation_density": 0.6},
        session_coherence={"session_coherence_state": "stable_progression", "progression_continuity": 0.72},
        cognitive_momentum={"cognitive_momentum": "conceptually_dense"},
    )

    first = resolve_cognitive_compression(**kwargs)
    second = resolve_cognitive_compression(**kwargs)

    assert first == second


def test_cognitive_compression_scaffolds_reconstruction_when_fragile():
    profile = resolve_cognitive_compression(
        block_type="questions",
        pedagogical_mode="conceptual_reinforcement",
        curriculum_role="active",
        review_intensity="medium",
        relationship_signal={"prerequisite_signal": 0.15, "relationship_type": None},
        pedagogical_profile={"intervention_fatigue": 0.1, "longitudinal_retention": 0.25},
        facet_profile={"dominant_facet": "reconstruction", "transfer_signal": 0.1, "reconstruction_signal": 0.76},
        trajectory_profile={"trajectory_state": "reconstruction_fragile", "transfer_fragility": 0.1, "reconstruction_fragility": 0.74},
        expression_profile={"pedagogical_expression_mode": "focused_reconstruction", "explanation_density": 0.52},
        session_coherence={"session_coherence_state": "reconstruction_cluster", "progression_continuity": 0.68},
        cognitive_momentum={"cognitive_momentum": "pressured"},
    )

    assert profile.cognitive_compression_mode == "reconstruction_scaffolded"
    assert profile.explanatory_expansion > 0.0


def test_cognitive_compression_expands_transfer_support_when_fragile():
    profile = resolve_cognitive_compression(
        block_type="summary",
        pedagogical_mode="contextual_application",
        curriculum_role="active",
        review_intensity="medium",
        relationship_signal={"prerequisite_signal": 0.32, "relationship_type": "applied_by"},
        pedagogical_profile={"intervention_fatigue": 0.1, "longitudinal_retention": 0.3},
        facet_profile={"dominant_facet": "contextual_transfer", "transfer_signal": 0.8, "reconstruction_signal": 0.2},
        trajectory_profile={"trajectory_state": "transfer_fragile", "transfer_fragility": 0.78, "reconstruction_fragility": 0.2},
        expression_profile={"pedagogical_expression_mode": "contextual_bridge", "explanation_density": 0.46},
        session_coherence={"session_coherence_state": "contextual_shift_softened", "progression_continuity": 0.58},
        cognitive_momentum={"cognitive_momentum": "continuity_fragile"},
    )

    assert profile.cognitive_compression_mode == "transfer_expanded"
    assert profile.contextual_support_level > 0.0


def test_cognitive_compression_lightens_cumulative_resurfacing():
    profile = resolve_cognitive_compression(
        block_type="questions",
        pedagogical_mode="reinforcement_check",
        curriculum_role="cumulative",
        review_intensity="light",
        relationship_signal={"prerequisite_signal": 0.0, "relationship_type": "cumulative_extension"},
        pedagogical_profile={"intervention_fatigue": 0.08, "longitudinal_retention": 0.82},
        facet_profile={"dominant_facet": "recognition", "transfer_signal": 0.1, "reconstruction_signal": 0.1},
        trajectory_profile={"trajectory_state": "consolidated", "transfer_fragility": 0.05, "reconstruction_fragility": 0.08},
        expression_profile={"pedagogical_expression_mode": "cumulative_reactivation", "explanation_density": 0.3},
        session_coherence={"session_coherence_state": "cumulative_relief", "progression_continuity": 0.71},
        cognitive_momentum={"cognitive_momentum": "balanced"},
    )

    assert profile.cognitive_compression_mode == "cumulative_lightweight"
    assert profile.redundancy_adjustment >= 0.0


def test_cognitive_compression_supports_prerequisites_when_needed():
    profile = resolve_cognitive_compression(
        block_type="questions",
        pedagogical_mode="contextual_application",
        curriculum_role="active",
        review_intensity="medium",
        relationship_signal={"prerequisite_signal": 0.72, "relationship_type": "applied_by"},
        pedagogical_profile={"intervention_fatigue": 0.1, "longitudinal_retention": 0.22},
        facet_profile={"dominant_facet": "application", "transfer_signal": 0.58, "reconstruction_signal": 0.2},
        trajectory_profile={"trajectory_state": "emerging", "transfer_fragility": 0.32, "reconstruction_fragility": 0.18},
        expression_profile={"pedagogical_expression_mode": "progressive_anchor", "explanation_density": 0.42},
        session_coherence={"session_coherence_state": "stable_progression", "progression_continuity": 0.74},
        cognitive_momentum={"cognitive_momentum": "stable"},
    )

    assert profile.cognitive_compression_mode == "prerequisite_supported"
    assert profile.prerequisite_support_signal > 0.0


def test_cognitive_compression_handles_missing_metadata():
    profile = resolve_cognitive_compression(
        block_type="summary",
        pedagogical_mode="",
        curriculum_role="",
        review_intensity="",
        relationship_signal={},
        pedagogical_profile={},
        facet_profile={},
        trajectory_profile={},
        expression_profile={},
        session_coherence={},
        cognitive_momentum={},
    )

    assert profile.cognitive_compression_mode
    assert 0.0 <= profile.informational_density <= 1.0
    assert 0.0 <= profile.contextual_support_level <= 1.0
    assert 0.0 <= profile.retrieval_compaction <= 1.0
    assert 0.0 <= profile.explanatory_expansion <= 1.0
