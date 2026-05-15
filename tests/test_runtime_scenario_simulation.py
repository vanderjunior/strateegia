from app.services.runtime_scenario_simulation import (
    RuntimeScenarioSimulationLayer,
    build_runtime_scenario_profile,
    simulate_runtime_scenario,
)


def build_block(
    *,
    block_id: str,
    topic_id: str = "topic-a",
    block_type: str = "question",
    retrieval_density_metric: float = 0.28,
    scaffold_load_metric: float = 0.24,
    continuity_smoothness_metric: float = 0.72,
    reconstruction_pressure_metric: float = 0.24,
    compression_safety_metric: float = 0.74,
    stabilization_sustainability_metric: float = 0.72,
    pacing_stability_metric: float = 0.68,
    cognitive_balance_metric: float = 0.72,
    support_density: float = 0.24,
    adaptive_overlap_signal: float = 0.2,
    validation_confidence: float = 0.72,
    false_fluency_risk: float = 0.18,
    scaffold_dependency_signal: float = 0.22,
    resurfacing_effectiveness_signal: float = 0.68,
    transfer_stability_signal: float = 0.72,
    compression_safety_signal: float = 0.74,
    scientific_validation_state: str = "validation_stable",
    validation_dataset_state: str = "validation_ready",
    comparative_session_state: str = "behavior_consistent",
    pedagogical_regression_signal: str = "regression_stable",
    question_index: int = 1,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "retrieval_density_metric": retrieval_density_metric,
        "scaffold_load_metric": scaffold_load_metric,
        "continuity_smoothness_metric": continuity_smoothness_metric,
        "reconstruction_pressure_metric": reconstruction_pressure_metric,
        "compression_safety_metric": compression_safety_metric,
        "stabilization_sustainability_metric": stabilization_sustainability_metric,
        "pacing_stability_metric": pacing_stability_metric,
        "cognitive_balance_metric": cognitive_balance_metric,
        "support_density": support_density,
        "adaptive_overlap_signal": adaptive_overlap_signal,
        "validation_confidence": validation_confidence,
        "false_fluency_risk": false_fluency_risk,
        "scaffold_dependency_signal": scaffold_dependency_signal,
        "resurfacing_effectiveness_signal": resurfacing_effectiveness_signal,
        "transfer_stability_signal": transfer_stability_signal,
        "compression_safety_signal": compression_safety_signal,
        "scientific_validation_state": scientific_validation_state,
        "validation_dataset_state": validation_dataset_state,
        "comparative_session_state": comparative_session_state,
        "pedagogical_regression_signal": pedagogical_regression_signal,
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


def test_runtime_scenario_simulation_is_deterministic():
    blocks = [build_block(block_id="q1")]

    first = simulate_runtime_scenario(blocks)
    second = simulate_runtime_scenario(blocks)

    assert first == second


def test_runtime_scenario_profile_detects_retrieval_heavy_stable():
    profile = build_runtime_scenario_profile(
        [build_block(block_id="q1", retrieval_density_metric=0.78, validation_dataset_state="retrieval_intensive")]
    )

    assert profile.scenario_category == "retrieval_heavy_stable"


def test_runtime_scenario_simulation_passes_retrieval_heavy_stable_scenario():
    result = simulate_runtime_scenario(
        [build_block(block_id="q1", retrieval_density_metric=0.78, validation_dataset_state="retrieval_intensive")]
    )

    assert result.runtime_scenario_state == "scenario_passed"
    assert result.scenario_category == "retrieval_heavy_stable"


def test_runtime_scenario_simulation_detects_scaffold_dependency_risk():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                scaffold_load_metric=0.78,
                support_density=0.76,
                scaffold_dependency_signal=0.74,
                validation_dataset_state="scaffold_sensitive",
                scientific_validation_state="sustainability_watch",
            )
        ]
    )

    assert result.scenario_category == "scaffold_dependent"
    assert result.scenario_regression_signal == "support_dependency_risk"


def test_runtime_scenario_simulation_detects_compression_risky_scenario():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                compression_safety_metric=0.42,
                compression_safety_signal=0.4,
                scientific_validation_state="regression_watch",
            )
        ]
    )

    assert result.scenario_category == "compression_risky"
    assert result.scenario_validation_outcome in {"scenario_passed", "regression_detected"}


def test_runtime_scenario_simulation_detects_reconstruction_fragile_scenario():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                reconstruction_pressure_metric=0.78,
                support_density=0.68,
                scientific_validation_state="sustainability_watch",
            )
        ]
    )

    assert result.scenario_category == "reconstruction_fragile"


def test_runtime_scenario_simulation_detects_false_fluency_risk():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                false_fluency_risk=0.78,
                scientific_validation_state="sustainability_watch",
            )
        ]
    )

    assert result.scenario_category == "false_fluency_risk"


def test_runtime_scenario_simulation_detects_continuity_degraded():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                continuity_smoothness_metric=0.34,
                scientific_validation_state="regression_watch",
            )
        ]
    )

    assert result.scenario_category == "continuity_degraded"


def test_runtime_scenario_simulation_passes_pedagogically_stable_baseline():
    result = simulate_runtime_scenario([build_block(block_id="q1")])

    assert result.scenario_category == "pedagogically_stable"
    assert result.runtime_scenario_state == "scenario_passed"


def test_runtime_scenario_simulation_detects_expectation_mismatch():
    scenario = build_runtime_scenario_profile("scaffold_dependent")
    result = simulate_runtime_scenario([build_block(block_id="q1")], scenario)

    assert result.runtime_scenario_state == "classification_mismatch"
    assert result.scenario_mismatch_reason


def test_runtime_scenario_simulation_is_inconclusive_without_blocks():
    result = simulate_runtime_scenario([])

    assert result.runtime_scenario_state == "scenario_inconclusive"


def test_runtime_scenario_simulation_flags_regression_detected():
    result = simulate_runtime_scenario(
        [
            build_block(
                block_id="q1",
                retrieval_density_metric=0.8,
                scaffold_load_metric=0.74,
                support_density=0.74,
                scaffold_dependency_signal=0.76,
                scientific_validation_state="regression_watch",
                pedagogical_regression_signal="retrieval_inflation",
                validation_dataset_state="retrieval_intensive",
            )
        ]
    )

    assert result.scenario_validation_outcome == "regression_detected"


def test_runtime_scenario_simulation_handles_sparse_legacy_blocks():
    annotated = RuntimeScenarioSimulationLayer().annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(annotated) == 2
    assert all("runtime_scenario_state" in block for block in annotated)
