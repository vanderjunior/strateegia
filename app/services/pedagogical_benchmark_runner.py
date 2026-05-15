from __future__ import annotations

from app.domain.models import (
    EmpiricalValidationCaseResult,
    EmpiricalValidationDataset,
    EmpiricalValidationDatasetSummary,
    PedagogicalBenchmarkCaseReport,
    PedagogicalBenchmarkRegressionReport,
    PedagogicalBenchmarkResult,
    PedagogicalBenchmarkRun,
    PedagogicalBenchmarkSummary,
)
from app.services.empirical_validation_dataset import (
    build_empirical_validation_dataset,
    evaluate_empirical_validation_dataset,
)
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning

_REGRESSION_SENSITIVE_CASE_IDS = {
    "false_fluency_case",
    "scaffold_dependency_case",
    "unsafe_compression_case",
    "retrieval_inflation_case",
    "continuity_degraded_case",
    "pedagogically_stable_baseline_case",
}


def run_pedagogical_benchmark(
    runtime_source: list[dict] | dict | None = None,
    dataset: EmpiricalValidationDataset | None = None,
    dataset_summary: EmpiricalValidationDatasetSummary | None = None,
) -> PedagogicalBenchmarkResult:
    current_dataset = dataset or build_empirical_validation_dataset()
    summary = dataset_summary or evaluate_empirical_validation_dataset(runtime_source, current_dataset)
    case_reports = [_case_report(case) for case in summary.validation_case_results]

    passed_cases = [report.case_id for report in case_reports if report.benchmark_case_status == "passed"]
    failed_cases = [report.case_id for report in case_reports if report.benchmark_case_status == "failed"]
    inconclusive_cases = [
        report.case_id
        for report in case_reports
        if report.benchmark_case_status in {"inconclusive", "partially_matched"}
    ]
    regression_cases = [
        report.case_id
        for report in case_reports
        if report.benchmark_case_status == "regression_detected"
    ]
    alignment_score = clamp_value(
        average_values([case.expectation_alignment for case in summary.validation_case_results])
    )
    readiness = _benchmark_readiness(summary.validation_case_results)
    state = _benchmark_state(summary.validation_case_results)
    regression_report = _regression_report(summary.validation_case_results)
    coverage_summary = (
        f"passed={len(passed_cases)} failed={len(failed_cases)} "
        f"inconclusive={len(inconclusive_cases)} regressions={len(regression_cases)} "
        f"total={len(case_reports)}"
    )
    run = PedagogicalBenchmarkRun(
        benchmark_id="pedagogical_benchmark_v1",
        benchmark_name="Pedagogical Benchmark Runner",
        dataset_id=current_dataset.dataset_id,
        dataset_name=current_dataset.dataset_name,
        case_ids=[case.case_id for case in current_dataset.cases],
    )
    summary_profile = PedagogicalBenchmarkSummary(
        benchmark_total_cases=len(case_reports),
        benchmark_passed_cases=passed_cases,
        benchmark_failed_cases=failed_cases,
        benchmark_inconclusive_cases=inconclusive_cases,
        benchmark_regression_cases=regression_cases,
        benchmark_alignment_score=round(alignment_score, 4),
        benchmark_coverage_summary=coverage_summary,
        benchmark_readiness=readiness,
    )
    return PedagogicalBenchmarkResult(
        benchmark_run=run,
        benchmark_summary_profile=summary_profile,
        regression_report=regression_report,
        pedagogical_benchmark_state=state,
        pedagogical_benchmark_summary=_benchmark_summary(state),
        pedagogical_benchmark_reasoning=state_reasoning(
            "Benchmark pedagogico",
            state,
            [
                f"Casos={len(case_reports)}; passed={len(passed_cases)}; failed={len(failed_cases)}; inconclusive={len(inconclusive_cases)}.",
                f"Regressions={len(regression_cases)}; readiness={readiness}; alignment={alignment_score:.2f}.",
            ],
        ),
        benchmark_case_reports=case_reports,
        benchmark_total_cases=summary_profile.benchmark_total_cases,
        benchmark_passed_cases=passed_cases,
        benchmark_failed_cases=failed_cases,
        benchmark_inconclusive_cases=inconclusive_cases,
        benchmark_regression_cases=regression_cases,
        benchmark_regression_flags=regression_report.regression_flags,
        benchmark_regression_severity=regression_report.regression_severity,
        benchmark_readiness=readiness,
        benchmark_alignment_score=round(alignment_score, 4),
        benchmark_coverage_summary=coverage_summary,
        why_this_benchmark_result=_why_benchmark(state),
    )


def _case_report(case: EmpiricalValidationCaseResult) -> PedagogicalBenchmarkCaseReport:
    status = _benchmark_case_status(case)
    return PedagogicalBenchmarkCaseReport(
        case_id=case.case_id,
        case_name=case.case_name,
        case_category=case.case_category,
        case_result_state=case.case_result_state,
        expectation_alignment=case.expectation_alignment,
        regression_flags=list(case.regression_flags),
        validation_confidence=case.validation_confidence,
        benchmark_case_status=status,
        case_benchmark_summary=_case_summary(status),
        case_benchmark_reasoning=state_reasoning(
            "Caso de benchmark",
            status,
            [
                f"Case={case.case_id}; resultado={case.case_result_state}; alignment={case.expectation_alignment:.2f}.",
                f"Flags={','.join(case.regression_flags) if case.regression_flags else 'none'}.",
            ],
        ),
    )


def _benchmark_case_status(case: EmpiricalValidationCaseResult) -> str:
    return {
        "case_passed": "passed",
        "case_failed": "failed",
        "case_inconclusive": "inconclusive",
        "case_partially_matched": "partially_matched",
        "case_regression_detected": "regression_detected",
    }.get(case.case_result_state, "inconclusive")


def _case_matches_expectation(case: EmpiricalValidationCaseResult) -> bool:
    expected = str(case.expected_states.get("expected_case_state") or "case_passed")
    if expected == "case_partially_matched":
        return case.case_result_state in {"case_partially_matched", "case_passed"}
    return case.case_result_state == expected


def _benchmark_state(case_results: list[EmpiricalValidationCaseResult]) -> str:
    if not case_results or all(case.case_result_state == "case_inconclusive" for case in case_results):
        return "benchmark_inconclusive"

    mismatched_sensitive = [
        case
        for case in case_results
        if case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case)
    ]
    general_failed = [
        case
        for case in case_results
        if case.case_id not in _REGRESSION_SENSITIVE_CASE_IDS
        and not _case_matches_expectation(case)
        and case.case_result_state == "case_failed"
    ]
    any_other_mismatch = any(
        not _case_matches_expectation(case)
        for case in case_results
        if case.case_id not in _REGRESSION_SENSITIVE_CASE_IDS
    )

    if mismatched_sensitive:
        return "benchmark_regression_detected"
    if general_failed:
        return "benchmark_failed"
    if any_other_mismatch or any(case.case_result_state == "case_inconclusive" for case in case_results):
        return "benchmark_partially_stable"
    return "benchmark_stable"


def _benchmark_readiness(case_results: list[EmpiricalValidationCaseResult]) -> str:
    case_ids = {case.case_id for case in case_results}
    if not case_results or "pedagogically_stable_baseline_case" not in case_ids:
        return "benchmark_insufficient"
    if all(case.case_result_state == "case_inconclusive" for case in case_results):
        return "benchmark_insufficient"
    if not _REGRESSION_SENSITIVE_CASE_IDS.issubset(case_ids):
        return "benchmark_partial"
    if any(
        case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case)
        for case in case_results
    ):
        return "benchmark_regression_sensitive"
    return "benchmark_ready"


def _regression_report(
    case_results: list[EmpiricalValidationCaseResult],
) -> PedagogicalBenchmarkRegressionReport:
    regression_case_ids = [
        case.case_id
        for case in case_results
        if case.case_result_state == "case_regression_detected"
        or (case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case))
    ]
    regression_flags = sorted(
        {
            flag
            for case in case_results
            for flag in case.regression_flags
            if (
                case.case_result_state == "case_regression_detected"
                or (case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case))
            )
            if flag and flag != "regression_stable"
        }
    )
    severity = _regression_severity(case_results)
    return PedagogicalBenchmarkRegressionReport(
        regression_case_ids=regression_case_ids,
        regression_flags=regression_flags,
        regression_summary=_regression_summary(severity),
        regression_severity=severity,
        regression_reasoning=state_reasoning(
            "Regressao de benchmark",
            severity,
            [
                f"Sensitive mismatches={len([case for case in case_results if case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case)])}.",
                f"Regression cases={len(regression_case_ids)}; flags={len(regression_flags)}.",
            ],
        ),
    )


def _regression_severity(case_results: list[EmpiricalValidationCaseResult]) -> str:
    mismatched_sensitive = [
        case
        for case in case_results
        if case.case_id in _REGRESSION_SENSITIVE_CASE_IDS and not _case_matches_expectation(case)
    ]
    baseline_mismatch = any(
        case.case_id == "pedagogically_stable_baseline_case" and not _case_matches_expectation(case)
        for case in case_results
    )
    general_failed = [
        case
        for case in case_results
        if case.case_result_state == "case_failed" and case.case_id not in _REGRESSION_SENSITIVE_CASE_IDS
    ]
    if baseline_mismatch or len(mismatched_sensitive) >= 2:
        return "high"
    if len(mismatched_sensitive) == 1 or len(general_failed) >= 2:
        return "medium"
    if general_failed:
        return "low"
    return "none"


def _case_summary(status: str) -> str:
    return state_message(
        status,
        {
            "passed": "Benchmark case matched the expected validation behavior.",
            "failed": "Benchmark case diverged from the expected validation behavior.",
            "inconclusive": "Benchmark case remained inconclusive under the current evidence.",
            "partially_matched": "Benchmark case matched only part of the expected validation behavior.",
            "regression_detected": "Benchmark case confirmed the expected regression-sensitive pattern.",
        },
        "Benchmark case remained observationally neutral.",
    )


def _benchmark_summary(state: str) -> str:
    return state_message(
        state,
        {
            "benchmark_stable": "Benchmark stable: all expected risk scenarios were detected and baseline remained stable.",
            "benchmark_regression_detected": "Regression risk: at least one regression-sensitive benchmark case diverged from expectation.",
            "benchmark_partially_stable": "Benchmark partially stable: some cases remained partial or inconclusive.",
            "benchmark_inconclusive": "Benchmark inconclusive: insufficient aligned cases for a strong benchmark reading.",
            "benchmark_failed": "Benchmark failed: one or more non-sensitive benchmark cases diverged clearly.",
        },
        "Benchmark remained in a neutral observational band.",
    )


def _why_benchmark(state: str) -> str:
    return state_message(
        state,
        {
            "benchmark_stable": "The controlled validation suite remained reproducible and expectation-aligned.",
            "benchmark_regression_detected": "A regression-sensitive scenario no longer matched the expected protective behavior.",
            "benchmark_partially_stable": "Some cases aligned while others remained partial or weakly evidenced.",
            "benchmark_inconclusive": "The benchmark did not have enough aligned evidence to be considered reliable.",
            "benchmark_failed": "At least one benchmark case failed outside the expected regression-sensitive envelope.",
        },
        "The benchmark remained observationally neutral.",
    )


def _regression_summary(severity: str) -> str:
    return state_message(
        severity,
        {
            "none": "No unexpected benchmark regression was detected.",
            "low": "A low-severity benchmark regression signal was detected.",
            "medium": "A medium-severity benchmark regression signal was detected.",
            "high": "A high-severity benchmark regression signal was detected.",
        },
        "Benchmark regression severity remained observationally neutral.",
    )
