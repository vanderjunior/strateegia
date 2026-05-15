from app.services.empirical_validation_dataset import (
    build_empirical_validation_dataset,
    evaluate_empirical_validation_dataset,
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


def case_only(case_id: str):
    dataset = build_empirical_validation_dataset()
    target = next(case for case in dataset.cases if case.case_id == case_id)
    return dataset.model_copy(update={"cases": [target]})


def test_empirical_validation_dataset_is_deterministic():
    blocks = [build_block(block_id="q1")]
    dataset = case_only("pedagogically_stable_baseline_case")

    first = evaluate_empirical_validation_dataset(blocks, dataset)
    second = evaluate_empirical_validation_dataset(blocks, dataset)

    assert first == second


def test_empirical_validation_dataset_includes_controlled_cases():
    dataset = build_empirical_validation_dataset()
    ids = {case.case_id for case in dataset.cases}

    assert ids == {
        "sustainable_retrieval_case",
        "false_fluency_case",
        "scaffold_dependency_case",
        "unsafe_compression_case",
        "transfer_fragility_case",
        "reconstruction_improving_case",
        "resurfacing_effective_case",
        "continuity_degraded_case",
        "retrieval_inflation_case",
        "pedagogically_stable_baseline_case",
    }


def test_sustainable_retrieval_case_passes():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", retrieval_density_metric=0.78, validation_dataset_state="retrieval_intensive")],
        case_only("sustainable_retrieval_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_passed"


def test_false_fluency_case_detects_regression():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", false_fluency_risk=0.78, scientific_validation_state="sustainability_watch")],
        case_only("false_fluency_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_regression_detected"


def test_scaffold_dependency_case_detects_risk():
    result = evaluate_empirical_validation_dataset(
        [
            build_block(
                block_id="q1",
                scaffold_load_metric=0.78,
                support_density=0.76,
                scaffold_dependency_signal=0.74,
                validation_dataset_state="scaffold_sensitive",
                scientific_validation_state="sustainability_watch",
            )
        ],
        case_only("scaffold_dependency_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_regression_detected"


def test_unsafe_compression_case_detects_risk():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", compression_safety_metric=0.42, compression_safety_signal=0.4, scientific_validation_state="regression_watch")],
        case_only("unsafe_compression_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_regression_detected"


def test_transfer_fragility_case_passes():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", transfer_stability_signal=0.32, validation_dataset_state="transfer_fragile")],
        case_only("transfer_fragility_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_passed"


def test_reconstruction_improving_case_partially_matches():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", reconstruction_pressure_metric=0.48, support_density=0.42, scientific_validation_state="validation_stable")],
        case_only("reconstruction_improving_case"),
    )

    assert result.validation_case_results[0].case_result_state in {"case_partially_matched", "case_passed"}


def test_resurfacing_effective_case_passes():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", resurfacing_effectiveness_signal=0.82, scientific_validation_state="validation_stable", validation_dataset_state="stabilization_progressive")],
        case_only("resurfacing_effective_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_passed"


def test_continuity_degraded_case_passes():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1", continuity_smoothness_metric=0.34, scientific_validation_state="regression_watch", validation_dataset_state="continuity_fragile")],
        case_only("continuity_degraded_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_passed"


def test_retrieval_inflation_case_detects_regression():
    result = evaluate_empirical_validation_dataset(
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
        ],
        case_only("retrieval_inflation_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_regression_detected"


def test_stable_baseline_case_passes():
    result = evaluate_empirical_validation_dataset(
        [build_block(block_id="q1")],
        case_only("pedagogically_stable_baseline_case"),
    )

    assert result.validation_case_results[0].case_result_state == "case_passed"


def test_dataset_handles_inconclusive_source():
    result = evaluate_empirical_validation_dataset([], case_only("pedagogically_stable_baseline_case"))

    assert result.empirical_dataset_state == "dataset_inconclusive"


def test_dataset_summary_and_alignment_are_bounded():
    result = evaluate_empirical_validation_dataset([build_block(block_id="q1")], build_empirical_validation_dataset())

    assert 0.0 <= result.dataset_alignment_score <= 1.0
    assert result.dataset_coverage_summary
    assert isinstance(result.validation_case_results, list)


def test_dataset_handles_sparse_legacy_blocks():
    result = evaluate_empirical_validation_dataset(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ],
        case_only("pedagogically_stable_baseline_case"),
    )

    assert result.validation_case_results[0].case_result_state in {"case_inconclusive", "case_partially_matched", "case_failed", "case_passed"}
