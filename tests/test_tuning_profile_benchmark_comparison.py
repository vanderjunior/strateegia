from copy import deepcopy

from app.domain.models import (
    EmpiricalValidationCaseResult,
    EmpiricalValidationDatasetSummary,
)
from app.services.controlled_tuning_experiments import build_controlled_tuning_experiment_registry
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


def test_tuning_profile_benchmark_comparison_is_deterministic():
    registry = build_controlled_tuning_experiment_registry()
    benchmark = make_benchmark_result()

    first = compare_tuning_profiles_against_benchmark(registry=registry, benchmark_result=benchmark)
    second = compare_tuning_profiles_against_benchmark(registry=registry, benchmark_result=benchmark)

    assert first == second


def test_registry_with_profiles_is_compared():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert comparison.total_profiles_compared == 8


def test_empty_registry_fallback():
    empty_registry = build_controlled_tuning_experiment_registry(experiments=[])

    comparison = compare_tuning_profiles_against_benchmark(
        registry=empty_registry,
        benchmark_result=make_benchmark_result(),
    )

    assert comparison.tuning_profile_comparison_state == "comparison_inconclusive"
    assert comparison.comparison_readiness == "comparison_registry_empty"


def test_missing_benchmark_fallback():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=None,
    )

    assert comparison.comparison_readiness == "comparison_benchmark_missing"


def test_benchmark_case_coverage_summary_is_exposed():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert "false_fluency_case" in comparison.benchmark_case_coverage_summary


def test_high_coverage_profile_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert "compression_conservative_profile" in comparison.high_coverage_profiles


def test_low_coverage_profile_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    baseline = next(
        result for result in comparison.profile_comparison_results if result.experiment_id == "baseline_current_behavior"
    )

    assert baseline.comparison_state == "low_coverage_profile"


def test_redundant_profile_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert "scaffold_sensitive_profile" in comparison.redundant_profiles


def test_complementary_profile_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert "retrieval_inflation_guarded_profile" in comparison.complementary_profiles


def test_tradeoff_sensitive_profile_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert "support_lightweight_profile" in comparison.tradeoff_sensitive_profiles


def test_coverage_gap_detection():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert comparison.uncovered_benchmark_cases == []


def test_regression_sensitive_case_coverage_is_preserved():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    target = next(
        result
        for result in comparison.profile_comparison_results
        if result.experiment_id == "retrieval_inflation_guarded_profile"
    )

    assert "retrieval_inflation_case" in target.covered_benchmark_cases


def test_comparison_readiness():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert comparison.comparison_readiness == "comparison_ready"


def test_per_profile_comparison_reasoning_exists():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    target = next(
        result
        for result in comparison.profile_comparison_results
        if result.experiment_id == "compression_conservative_profile"
    )

    assert target.profile_candidate_reasoning
    assert target.why_this_profile_state


def test_all_profile_comparisons_are_read_only():
    comparison = compare_tuning_profiles_against_benchmark(
        registry=build_controlled_tuning_experiment_registry(),
        benchmark_result=make_benchmark_result(),
    )

    assert all(result.read_only for result in comparison.profile_comparison_results)
    assert all(not result.executable for result in comparison.profile_comparison_results)


def test_comparison_does_not_mutate_inputs():
    registry = build_controlled_tuning_experiment_registry()
    benchmark = make_benchmark_result()
    registry_snapshot = deepcopy(registry)
    benchmark_snapshot = deepcopy(benchmark)

    compare_tuning_profiles_against_benchmark(registry=registry, benchmark_result=benchmark)

    assert registry == registry_snapshot
    assert benchmark == benchmark_snapshot
