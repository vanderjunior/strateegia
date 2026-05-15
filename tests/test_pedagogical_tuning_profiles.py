from app.services.pedagogical_tuning_profiles import (
    PedagogicalTuningProfilesLayer,
    resolve_pedagogical_tuning_profile,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_pressure_accumulation: float = 0.22,
    scaffold_density: float = 0.24,
    continuity_stability: float = 0.66,
    progression_continuity: float = 0.64,
    reconstruction_fragility: float = 0.18,
    compression_safety_metric: float = 0.7,
    modulation_overlap: float = 0.2,
    signal_overlap_density: float = 0.22,
    stabilization_quality: float = 0.7,
    stabilization_sustainability_metric: float = 0.68,
    pacing_adjustment: float = 0.5,
    intervention_repetition_signal: float = 0.18,
    retrieval_family: str = "retrieval_balanced",
    support_family: str = "support_light",
    continuity_family: str = "continuity_stable",
    stabilization_family: str = "stabilized",
    overlap_family: str = "overlap_low",
    pedagogical_observability_state: str = "adaptively_balanced",
    session_stability_state: str = "balanced",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_pressure_accumulation": retrieval_pressure_accumulation,
        "scaffold_density": scaffold_density,
        "continuity_stability": continuity_stability,
        "progression_continuity": progression_continuity,
        "reconstruction_fragility": reconstruction_fragility,
        "compression_safety_metric": compression_safety_metric,
        "modulation_overlap": modulation_overlap,
        "signal_overlap_density": signal_overlap_density,
        "stabilization_quality": stabilization_quality,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "pacing_adjustment": pacing_adjustment,
        "intervention_repetition_signal": intervention_repetition_signal,
        "retrieval_family": retrieval_family,
        "support_family": support_family,
        "continuity_family": continuity_family,
        "stabilization_family": stabilization_family,
        "overlap_family": overlap_family,
        "pedagogical_observability_state": pedagogical_observability_state,
        "session_stability_state": session_stability_state,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }
    if block_type == "summary":
        payload["content"] = "Resumo"
    else:
        payload["statement"] = "Pergunta"
        payload["correct_answer"] = True
        payload["explanation"] = "Explicacao"
        payload["question_id"] = f"{topic_id}-{question_index}"
    return payload


def test_pedagogical_tuning_profile_is_deterministic():
    blocks = [
        build_block(block_id="s1", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
    ]

    first = resolve_pedagogical_tuning_profile(blocks)
    second = resolve_pedagogical_tuning_profile(blocks)

    assert first == second


def test_pedagogical_tuning_profile_detects_retrieval_sensitive_configuration():
    profile = resolve_pedagogical_tuning_profile(
        [
            build_block(
                block_id="q1",
                retrieval_pressure_accumulation=0.82,
                retrieval_family="retrieval_dense",
                session_stability_state="retrieval_heavy",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                retrieval_pressure_accumulation=0.78,
                retrieval_family="retrieval_dense",
                session_stability_state="retrieval_heavy",
                question_index=2,
            ),
        ]
    )

    assert profile.pedagogical_tuning_state == "retrieval_sensitive"
    assert profile.retrieval_tolerance >= 0.5


def test_pedagogical_tuning_profile_detects_reconstruction_protective_configuration():
    profile = resolve_pedagogical_tuning_profile(
        [
            build_block(
                block_id="q1",
                scaffold_density=0.8,
                reconstruction_fragility=0.78,
                support_family="support_heavy",
                pedagogical_observability_state="support_heavy",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                scaffold_density=0.76,
                reconstruction_fragility=0.74,
                support_family="support_heavy",
                pedagogical_observability_state="support_heavy",
                question_index=2,
            ),
        ]
    )

    assert profile.pedagogical_tuning_state == "reconstruction_protective"
    assert profile.reconstruction_support_level >= 0.5
    assert profile.scaffold_sensitivity >= 0.5


def test_pedagogical_tuning_profile_detects_compression_conservative_configuration():
    profile = resolve_pedagogical_tuning_profile(
        [
            build_block(
                block_id="q1",
                compression_safety_metric=0.84,
                continuity_stability=0.72,
                progression_continuity=0.7,
                stabilization_sustainability_metric=0.76,
                stabilization_family="stabilized",
                question_index=1,
            ),
            build_block(
                block_id="q2",
                compression_safety_metric=0.82,
                continuity_stability=0.74,
                progression_continuity=0.72,
                stabilization_sustainability_metric=0.78,
                stabilization_family="stabilized",
                question_index=2,
            ),
        ]
    )

    assert profile.pedagogical_tuning_state == "compression_conservative"
    assert profile.compression_conservatism >= 0.6


def test_pedagogical_tuning_layer_preserves_order_and_bounds():
    layer = PedagogicalTuningProfilesLayer()
    blocks = [
        build_block(block_id="summary", block_type="summary", question_index=0),
        build_block(block_id="q1", question_index=1),
        build_block(
            block_id="q2",
            topic_id="topic-b",
            retrieval_pressure_accumulation=0.18,
            scaffold_density=0.2,
            continuity_stability=0.7,
            progression_continuity=0.68,
            reconstruction_fragility=0.12,
            compression_safety_metric=0.74,
            modulation_overlap=0.16,
            signal_overlap_density=0.18,
            stabilization_quality=0.74,
            stabilization_sustainability_metric=0.72,
            pacing_adjustment=0.48,
            intervention_repetition_signal=0.16,
            question_index=2,
        ),
    ]

    annotated = layer.annotate(blocks)

    assert [block["id"] for block in annotated] == ["summary", "q1", "q2"]
    for block in annotated:
        assert 0.0 <= block["retrieval_tolerance"] <= 1.0
        assert 0.0 <= block["scaffold_sensitivity"] <= 1.0
        assert 0.0 <= block["continuity_smoothing_strength"] <= 1.0
        assert 0.0 <= block["compression_conservatism"] <= 1.0
        assert 0.0 <= block["reconstruction_support_level"] <= 1.0
        assert 0.0 <= block["pacing_relief_sensitivity"] <= 1.0
        assert 0.0 <= block["overlap_tolerance"] <= 1.0
        assert 0.0 <= block["stabilization_threshold"] <= 1.0
        assert 0.0 <= block["modulation_density_tolerance"] <= 1.0
        assert 0.0 <= block["intervention_rotation_sensitivity"] <= 1.0


def test_pedagogical_tuning_layer_handles_sparse_legacy_blocks():
    annotated = PedagogicalTuningProfilesLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("pedagogical_tuning_state" in block for block in annotated)
