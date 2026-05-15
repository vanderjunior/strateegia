from copy import deepcopy

from app.domain.models import (
    EmpiricalValidationCaseResult,
    EmpiricalValidationDatasetSummary,
)
from app.services.empirical_validation_dataset import build_empirical_validation_dataset
from app.services.pedagogical_benchmark_runner import run_pedagogical_benchmark


CASE_INDEX = {case.case_id: case for case in build_empirical_validation_dataset().cases}


def make_case_result(
    case_id: str,
    *,
    actual_state: str | None = None,
    alignment: float = 1.0,
    regression_flags: list[str] | None = None,
    validation_confidence: float = 0.72,
) -> EmpiricalValidationCaseResult:
    case = CASE_INDEX[case_id]
    expected_state = case.expected_states.expected_case_state or "case_passed"
    return EmpiricalValidationCaseResult(
        case_id=case.case_id,
        case_name=case.case_name,
        case_category=case.case_category,
        expected_states=case.expected_states.model_dump(mode="json"),
        observed_states={"pedagogical_regression_signal": "regression_stable"},
        expectation_alignment=alignment,
        case_result_state=actual_state or expected_state,
        case_reasoning=[f"Case {case.case_id} reasoning."],
        mismatch_reasons=[],
        regression_flags=regression_flags or [],
        validation_confidence=validation_confidence,
        why_this_case_result="Test fixture",
    )


def make_dataset_summary(case_results: list[EmpiricalValidationCaseResult]) -> EmpiricalValidationDatasetSummary:
    passed = [case.case_id for case in case_results if case.case_result_state == "case_passed"]
    failed = [case.case_id for case in case_results if case.case_result_state == "case_failed"]
    inconclusive = [
        case.case_id
        for case in case_results
        if case.case_result_state in {"case_inconclusive", "case_partially_matched"}
    ]
    regression_flags = sorted(
        {
            flag
            for case in case_results
            for flag in case.regression_flags
            if flag and flag != "regression_stable"
        }
    )
    return EmpiricalValidationDatasetSummary(
        empirical_dataset_state="dataset_validated",
        empirical_dataset_summary="Dataset fixture",
        empirical_dataset_reasoning=["Dataset fixture reasoning."],
        validation_case_results=case_results,
        passed_cases=passed,
        failed_cases=failed,
        inconclusive_cases=inconclusive,
        dataset_alignment_score=0.88,
        dataset_regression_flags=regression_flags,
        dataset_coverage_summary="fixture",
        empirical_validation_context="Fixture Dataset",
        why_this_dataset_result="Fixture result",
    )


def stable_case_results() -> list[EmpiricalValidationCaseResult]:
    return [
        make_case_result("sustainable_retrieval_case", regression_flags=["retrieval_high"]),
        make_case_result(
            "false_fluency_case",
            actual_state="case_regression_detected",
            regression_flags=["false_fluency_risk"],
        ),
        make_case_result(
            "scaffold_dependency_case",
            actual_state="case_regression_detected",
            regression_flags=["scaffold_dependency_risk"],
        ),
        make_case_result(
            "unsafe_compression_case",
            actual_state="case_regression_detected",
            regression_flags=["compression_risk"],
        ),
        make_case_result("transfer_fragility_case", regression_flags=["transfer_fragile"]),
        make_case_result("reconstruction_improving_case", actual_state="case_partially_matched", alignment=0.82),
        make_case_result("resurfacing_effective_case", regression_flags=["resurfacing_effective"]),
        make_case_result("continuity_degraded_case", regression_flags=["continuity_fragile"]),
        make_case_result(
            "retrieval_inflation_case",
            actual_state="case_regression_detected",
            regression_flags=["retrieval_high", "regression_risk"],
        ),
        make_case_result("pedagogically_stable_baseline_case"),
    ]


def test_pedagogical_benchmark_runner_is_deterministic():
    dataset_summary = make_dataset_summary(stable_case_results())

    first = run_pedagogical_benchmark(dataset_summary=dataset_summary)
    second = run_pedagogical_benchmark(dataset_summary=dataset_summary)

    assert first == second


def test_pedagogical_benchmark_runner_does_not_mutate_runtime_source():
    runtime_blocks = [
        {
            "type": "question",
            "topic_id": "topic-a",
            "statement": "Pergunta",
            "correct_answer": True,
            "explanation": "Explicacao",
            "question_id": "q1",
            "retrieval_density_metric": 0.82,
            "validation_dataset_state": "retrieval_intensive",
            "scientific_validation_state": "validation_stable",
            "comparative_session_state": "behavior_consistent",
            "_entry_index": 0,
            "_block_index": 0,
            "_question_index": 0,
        }
    ]
    snapshot = deepcopy(runtime_blocks)

    run_pedagogical_benchmark(runtime_source=runtime_blocks)

    assert runtime_blocks == snapshot


def test_benchmark_stable_when_expected_case_states_match():
    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(stable_case_results()))

    assert result.pedagogical_benchmark_state == "benchmark_stable"
    assert result.benchmark_readiness == "benchmark_ready"
    assert result.benchmark_regression_severity == "none"
    assert "false_fluency_case" in result.benchmark_regression_cases
    assert "pedagogically_stable_baseline_case" in result.benchmark_passed_cases


def test_benchmark_handles_failed_case_and_detects_regression_risk():
    results = stable_case_results()
    results[-1] = make_case_result(
        "pedagogically_stable_baseline_case",
        actual_state="case_failed",
        alignment=0.18,
        regression_flags=["regression_risk"],
    )

    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(results))

    assert result.pedagogical_benchmark_state == "benchmark_regression_detected"
    assert result.benchmark_regression_severity == "high"
    assert "pedagogically_stable_baseline_case" in result.regression_report.regression_case_ids


def test_benchmark_handles_inconclusive_cases():
    results = [make_case_result("pedagogically_stable_baseline_case", actual_state="case_inconclusive", alignment=0.0)]

    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(results))

    assert result.pedagogical_benchmark_state == "benchmark_inconclusive"
    assert result.benchmark_readiness == "benchmark_insufficient"


def test_benchmark_handles_partial_stability():
    results = stable_case_results()
    results[0] = make_case_result("sustainable_retrieval_case", actual_state="case_partially_matched", alignment=0.7)

    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(results))

    assert result.pedagogical_benchmark_state == "benchmark_partially_stable"
    assert "sustainable_retrieval_case" in result.benchmark_inconclusive_cases


def test_benchmark_case_report_preserves_regression_detected_status():
    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(stable_case_results()))

    false_fluency = next(report for report in result.benchmark_case_reports if report.case_id == "false_fluency_case")

    assert false_fluency.benchmark_case_status == "regression_detected"


def test_benchmark_highlights_sensitive_cases():
    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(stable_case_results()))
    case_ids = {report.case_id for report in result.benchmark_case_reports}

    assert "false_fluency_case" in case_ids
    assert "scaffold_dependency_case" in case_ids
    assert "unsafe_compression_case" in case_ids
    assert "retrieval_inflation_case" in case_ids
    assert "pedagogically_stable_baseline_case" in case_ids


def test_benchmark_alignment_indicator_is_bounded():
    result = run_pedagogical_benchmark(dataset_summary=make_dataset_summary(stable_case_results()))

    assert 0.0 <= result.benchmark_alignment_score <= 1.0


def test_benchmark_supports_missing_metadata_with_inconclusive_result():
    sparse_summary = EmpiricalValidationDatasetSummary(
        empirical_dataset_state="dataset_inconclusive",
        empirical_dataset_summary="Sparse",
        empirical_dataset_reasoning=[],
        validation_case_results=[],
        passed_cases=[],
        failed_cases=[],
        inconclusive_cases=[],
        dataset_alignment_score=0.0,
        dataset_regression_flags=[],
        dataset_coverage_summary="empty",
        empirical_validation_context="Sparse",
        why_this_dataset_result="Sparse",
    )

    result = run_pedagogical_benchmark(dataset_summary=sparse_summary)

    assert result.pedagogical_benchmark_state == "benchmark_inconclusive"
    assert result.benchmark_readiness == "benchmark_insufficient"
