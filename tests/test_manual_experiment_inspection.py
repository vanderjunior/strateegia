from copy import deepcopy

from app.domain.models import (
    ControlledTuningExperimentRegistry,
    EmpiricalValidationCaseResult,
    EmpiricalValidationDatasetSummary,
    TuningProfileBenchmarkComparison,
)
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
from app.services.manual_experiment_inspection import (
    build_manual_experiment_inspection,
)
from app.services.pedagogical_benchmark_runner import run_pedagogical_benchmark
from app.services.tuning_profile_benchmark_comparison import (
    compare_tuning_profiles_against_benchmark,
)


CASE_EXPECTATIONS = {
    "sustainable_retrieval_case": "case_passed",
    "false_fluency_case": "case_regression_detected",
    "scaffold_dependency_case": "case_regression_detected",
    "unsafe_compression_case": "case_regression_detected",
    "transfer_fragility_case": "case_passed",
    "reconstruction_improving_case": "case_partially_matched",
    "resurfacing_effective_case": "case_passed",
    "continuity_degraded_case": "case_passed",
    "retrieval_inflation_case": "case_regression_detected",
    "pedagogically_stable_baseline_case": "case_passed",
}


def make_case_result(
    case_id: str,
    *,
    actual_state: str | None = None,
    alignment: float = 1.0,
    regression_flags: list[str] | None = None,
) -> EmpiricalValidationCaseResult:
    return EmpiricalValidationCaseResult(
        case_id=case_id,
        case_name=case_id.replace("_", " ").title(),
        case_category="fixture",
        expected_states={"expected_case_state": CASE_EXPECTATIONS[case_id]},
        observed_states={},
        expectation_alignment=alignment,
        case_result_state=actual_state or CASE_EXPECTATIONS[case_id],
        case_reasoning=["fixture"],
        mismatch_reasons=[],
        regression_flags=regression_flags or [],
        validation_confidence=0.72,
        why_this_case_result="fixture",
    )


def make_benchmark_result():
    results = [
        make_case_result("sustainable_retrieval_case", regression_flags=["retrieval_high"]),
        make_case_result("false_fluency_case", regression_flags=["false_fluency_risk"]),
        make_case_result("scaffold_dependency_case", regression_flags=["scaffold_dependency_risk"]),
        make_case_result("unsafe_compression_case", regression_flags=["compression_risk"]),
        make_case_result("transfer_fragility_case", regression_flags=["transfer_fragile"]),
        make_case_result("reconstruction_improving_case", alignment=0.82),
        make_case_result("resurfacing_effective_case", regression_flags=["resurfacing_effective"]),
        make_case_result("continuity_degraded_case", regression_flags=["continuity_fragile"]),
        make_case_result("retrieval_inflation_case", regression_flags=["retrieval_high", "regression_risk"]),
        make_case_result("pedagogically_stable_baseline_case"),
    ]
    dataset_summary = EmpiricalValidationDatasetSummary(
        empirical_dataset_state="dataset_validated",
        empirical_dataset_summary="fixture",
        empirical_dataset_reasoning=["fixture"],
        validation_case_results=results,
        passed_cases=[case.case_id for case in results if case.case_result_state == "case_passed"],
        failed_cases=[],
        inconclusive_cases=[case.case_id for case in results if case.case_result_state == "case_partially_matched"],
        dataset_alignment_score=0.88,
        dataset_regression_flags=sorted(
            {
                flag
                for case in results
                for flag in case.regression_flags
                if flag and flag != "regression_stable"
            }
        ),
        dataset_coverage_summary="fixture",
        empirical_validation_context="fixture",
        why_this_dataset_result="fixture",
    )
    return run_pedagogical_benchmark(dataset_summary=dataset_summary)


def make_comparison():
    return compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )


def test_manual_experiment_inspection_is_deterministic():
    comparison = make_comparison()

    first = build_manual_experiment_inspection(comparison=comparison)
    second = build_manual_experiment_inspection(comparison=comparison)

    assert first == second


def test_no_profiles_fallback():
    registry = build_controlled_tuning_experiment_registry(experiments=[])

    inspection = build_manual_experiment_inspection(registry=registry)

    assert inspection.manual_experiment_inspection_state == "inspection_inconclusive"
    assert inspection.inspection_readiness == "inspection_no_profiles"


def test_no_comparison_fallback():
    registry = build_controlled_tuning_experiment_registry()
    comparison = TuningProfileBenchmarkComparison(
        tuning_profile_comparison_state="comparison_inconclusive",
        tuning_profile_comparison_summary="fixture",
        total_profiles_compared=0,
        comparison_readiness="comparison_insufficient",
    )

    inspection = build_manual_experiment_inspection(
        registry=registry,
        comparison=comparison,
    )

    assert inspection.manual_experiment_inspection_state == "inspection_inconclusive"
    assert inspection.inspection_readiness == "inspection_no_comparison"


def test_promising_candidate_detection():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "compression_conservative_profile" in inspection.promising_candidate_profiles


def test_redundant_profile_detection():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "scaffold_sensitive_profile" in inspection.redundant_profiles


def test_tradeoff_sensitive_profile_detection():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "support_lightweight_profile" in inspection.tradeoff_sensitive_profiles


def test_low_coverage_profile_detection():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "baseline_current_behavior" in inspection.low_coverage_profiles


def test_not_ready_profile_detection():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "support_lightweight_profile" in inspection.not_ready_profiles


def test_caution_flags_are_exposed():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert "profile_redundancy" in inspection.caution_flags
    assert "high_tradeoff_sensitivity" in inspection.caution_flags


def test_manual_decision_summary_is_exposed():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert inspection.manual_decision_summary.decision_state
    assert inspection.manual_decision_summary.decision_summary


def test_inspection_readiness_is_exposed():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert inspection.inspection_readiness == "inspection_ready"


def test_per_profile_inspection_reasoning_exists():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())
    target = next(
        item
        for item in inspection.experiment_review_items
        if item.experiment_id == "retrieval_inflation_guarded_profile"
    )

    assert target.candidate_reasoning
    assert target.manual_review_summary
    assert target.why_this_candidate_status


def test_all_inspection_output_is_read_only():
    inspection = build_manual_experiment_inspection(comparison=make_comparison())

    assert all(item.read_only for item in inspection.experiment_review_items)
    assert all(not item.executable for item in inspection.experiment_review_items)


def test_manual_experiment_inspection_does_not_mutate_inputs():
    registry = build_controlled_tuning_experiment_registry()
    comparison = make_comparison()
    registry_snapshot = deepcopy(registry)
    comparison_snapshot = deepcopy(comparison)

    build_manual_experiment_inspection(registry=registry, comparison=comparison)

    assert registry == registry_snapshot
    assert comparison == comparison_snapshot

