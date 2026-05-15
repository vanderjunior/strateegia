from __future__ import annotations

from app.domain.models import (
    ControlledTuningExperimentRegistry,
    PedagogicalBenchmarkResult,
    TuningProfileBenchmarkAlignment,
    TuningProfileBenchmarkComparison,
    TuningProfileComparisonResult,
)
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
from app.services.runtime_profile_utils import clamp_value, state_message, state_reasoning

_PRIORITY_CASES = {
    "false_fluency_case",
    "scaffold_dependency_case",
    "unsafe_compression_case",
    "retrieval_inflation_case",
    "continuity_degraded_case",
    "pedagogically_stable_baseline_case",
}
_ALL_BENCHMARK_CASES = {
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


def compare_tuning_profiles_against_benchmark(
    *,
    registry: ControlledTuningExperimentRegistry | None = None,
    benchmark_result: PedagogicalBenchmarkResult | dict | None = None,
) -> TuningProfileBenchmarkComparison:
    current_registry = registry or build_controlled_tuning_experiment_registry()
    experiments = list(current_registry.tuning_experiments)
    if not experiments:
        return TuningProfileBenchmarkComparison(
            tuning_profile_comparison_state="comparison_inconclusive",
            tuning_profile_comparison_summary=_summary("comparison_inconclusive"),
            tuning_profile_comparison_reasoning=state_reasoning(
                "Comparacao de tuning",
                "comparison_inconclusive",
                ["Nao havia perfis declarativos para comparar."],
            ),
            benchmark_case_coverage_summary={},
            comparison_readiness="comparison_registry_empty",
            why_this_tuning_profile_comparison=_why("comparison_inconclusive"),
        )

    comparison_results = [
        _compare_experiment(experiment, experiments, benchmark_result)
        for experiment in experiments
    ]
    high_coverage = [
        result.experiment_id for result in comparison_results if result.comparison_state == "high_coverage_profile"
    ]
    redundant = [
        result.experiment_id for result in comparison_results if result.comparison_state == "redundant_profile"
    ]
    complementary = [
        result.experiment_id for result in comparison_results if result.comparison_state == "complementary_profile"
    ]
    tradeoff_sensitive = [
        result.experiment_id for result in comparison_results if result.comparison_state == "tradeoff_sensitive_profile"
    ]
    covered_cases = {case for result in comparison_results for case in result.covered_benchmark_cases}
    uncovered_cases = sorted(_ALL_BENCHMARK_CASES - covered_cases)
    readiness = _readiness(current_registry, benchmark_result)
    state = _comparison_state(readiness, uncovered_cases, redundant)
    return TuningProfileBenchmarkComparison(
        tuning_profile_comparison_state=state,
        tuning_profile_comparison_summary=_summary(state),
        tuning_profile_comparison_reasoning=state_reasoning(
            "Comparacao de tuning",
            state,
            [
                f"Perfis={len(comparison_results)}; high_coverage={len(high_coverage)}; redundant={len(redundant)}.",
                f"Tradeoff-sensitive={len(tradeoff_sensitive)}; uncovered_cases={len(uncovered_cases)}; readiness={readiness}.",
            ],
        ),
        profile_comparison_results=comparison_results,
        total_profiles_compared=len(comparison_results),
        high_coverage_profiles=high_coverage,
        redundant_profiles=redundant,
        complementary_profiles=complementary,
        tradeoff_sensitive_profiles=tradeoff_sensitive,
        uncovered_benchmark_cases=uncovered_cases,
        profile_overlap_summary=f"redundant={len(redundant)} complementary={len(complementary)} tradeoff_sensitive={len(tradeoff_sensitive)}",
        benchmark_case_coverage_summary=current_registry.benchmark_case_coverage,
        comparison_readiness=readiness,
        why_this_tuning_profile_comparison=_why(state),
    )


def _compare_experiment(experiment, all_experiments, benchmark_result):
    covered = sorted(set(experiment.relevant_benchmark_cases))
    uncovered_priority = sorted(_PRIORITY_CASES - set(covered))
    shared_cases = sorted(
        {
            case
            for other in all_experiments
            if other.experiment_id != experiment.experiment_id
            for case in set(covered).intersection(other.relevant_benchmark_cases)
        }
    )
    experiment_dimensions = {dimension.dimension_id for dimension in experiment.tuning_dimensions}
    shared_dimensions = sorted(
        {
            dimension.dimension_id
            for other in all_experiments
            if other.experiment_id != experiment.experiment_id
            for dimension in other.tuning_dimensions
            if dimension.dimension_id in experiment_dimensions
        }
    )
    overlap_signal = clamp_value((len(shared_cases) / max(len(covered), 1)) * 0.7 + (len(shared_dimensions) / max(len(experiment_dimensions), 1)) * 0.3)
    coverage_gap_signal = clamp_value(len(uncovered_priority) / max(len(_PRIORITY_CASES), 1))
    expected_benefits = list(experiment.expected_directional_effects)
    expected_risks = _expected_risks(experiment)
    tradeoffs = _possible_tradeoffs(experiment)
    alignment = _alignment(experiment, benchmark_result)
    state = _profile_state(
        experiment=experiment,
        covered=covered,
        shared_cases=shared_cases,
        shared_dimensions=shared_dimensions,
        overlap_signal=overlap_signal,
        tradeoffs=tradeoffs,
    )
    return TuningProfileComparisonResult(
        experiment_id=experiment.experiment_id,
        experiment_name=experiment.experiment_name,
        comparison_state=state,
        covered_benchmark_cases=covered,
        uncovered_priority_cases=uncovered_priority,
        shared_benchmark_cases=shared_cases,
        shared_tuning_dimensions=shared_dimensions,
        expected_benefits=expected_benefits,
        expected_risks=expected_risks,
        possible_tradeoffs=tradeoffs,
        profile_overlap_signal=round(overlap_signal, 4),
        coverage_gap_signal=round(coverage_gap_signal, 4),
        benchmark_alignment=alignment,
        profile_candidate_reasoning=state_reasoning(
            "Perfil de tuning",
            state,
            [
                f"Coverage={len(covered)}; shared_cases={len(shared_cases)}; shared_dimensions={len(shared_dimensions)}.",
                f"Overlap={overlap_signal:.2f}; gap={coverage_gap_signal:.2f}; benchmark_available={alignment.benchmark_available}.",
            ],
        ),
        why_this_profile_state=_why_profile(state),
        read_only=experiment.read_only,
        executable=experiment.executable,
    )


def _profile_state(*, experiment, covered, shared_cases, shared_dimensions, overlap_signal, tradeoffs):
    if experiment.risk_level == "high" or "may_under_support_fragile_contexts" in tradeoffs:
        return "tradeoff_sensitive_profile"
    if len(covered) >= 3:
        return "high_coverage_profile"
    if len(covered) <= 1:
        return "low_coverage_profile"
    if overlap_signal >= 0.6 and shared_cases and shared_dimensions:
        return "redundant_profile"
    if _unique_case_count(experiment, covered) >= 1:
        return "complementary_profile"
    return "profile_candidate_for_future_experiment"


def _alignment(experiment, benchmark_result):
    if benchmark_result is None:
        return TuningProfileBenchmarkAlignment(
            alignment_state="benchmark_missing",
            covered_regression_sensitive_cases=sorted(_PRIORITY_CASES.intersection(experiment.relevant_benchmark_cases)),
            benchmark_available=False,
            alignment_reasoning=["Benchmark result was not available; comparison stayed declarative."],
        )
    benchmark_cases = _benchmark_case_ids(benchmark_result)
    covered_sensitive = sorted(_PRIORITY_CASES.intersection(experiment.relevant_benchmark_cases).intersection(benchmark_cases))
    state = "aligned" if covered_sensitive else "gap_sensitive"
    return TuningProfileBenchmarkAlignment(
        alignment_state=state,
        covered_regression_sensitive_cases=covered_sensitive,
        benchmark_available=True,
        alignment_reasoning=[
            f"Benchmark cases available={len(benchmark_cases)}.",
            f"Regression-sensitive covered={len(covered_sensitive)}.",
        ],
    )


def _expected_risks(experiment) -> list[str]:
    risks = []
    for dimension in experiment.tuning_dimensions:
        if dimension.hypothetical_direction in {"decrease", "slight_increase"}:
            risks.append(f"{dimension.dimension_id}:{dimension.hypothetical_direction}")
    if experiment.risk_level == "high":
        risks.append("high_risk_profile")
    return sorted(set(risks))


def _possible_tradeoffs(experiment) -> list[str]:
    tradeoffs = []
    dimension_map = {dimension.dimension_id: dimension.hypothetical_direction for dimension in experiment.tuning_dimensions}
    if dimension_map.get("scaffold_sensitivity") == "decrease":
        tradeoffs.append("may_under_support_fragile_contexts")
    if dimension_map.get("compression_conservatism") == "increase":
        tradeoffs.append("may_increase_support_density")
    if dimension_map.get("continuity_smoothing_strength") == "decrease":
        tradeoffs.append("may_preserve_more_fragmentation_signals")
    if dimension_map.get("stabilization_threshold") == "increase":
        tradeoffs.append("may_delay_stability_declaration")
    return tradeoffs


def _unique_case_count(experiment, covered_cases: list[str]) -> int:
    registry = build_controlled_tuning_experiment_registry()
    case_counts = {
        case_id: len(experiment_ids)
        for case_id, experiment_ids in registry.benchmark_case_coverage.items()
    }
    return sum(1 for case in covered_cases if case_counts.get(case, 0) == 1 and case in experiment.relevant_benchmark_cases)


def _readiness(registry, benchmark_result):
    if not registry.tuning_experiments:
        return "comparison_registry_empty"
    if benchmark_result is None:
        return "comparison_benchmark_missing"
    if not registry.benchmark_case_coverage:
        return "comparison_insufficient"
    if not _PRIORITY_CASES.issubset(set(registry.benchmark_case_coverage)):
        return "comparison_partial"
    return "comparison_ready"


def _benchmark_case_ids(benchmark_result: PedagogicalBenchmarkResult | dict) -> set[str]:
    if isinstance(benchmark_result, dict):
        reports = list(benchmark_result.get("benchmark_case_reports") or [])
        return {str(report.get("case_id") or "") for report in reports if report.get("case_id")}
    return {report.case_id for report in benchmark_result.benchmark_case_reports}


def _comparison_state(readiness: str, uncovered_cases: list[str], redundant_profiles: list[str]) -> str:
    if readiness in {"comparison_registry_empty", "comparison_insufficient"}:
        return "comparison_inconclusive"
    if uncovered_cases:
        return "benchmark_gap_detected"
    if readiness == "comparison_partial":
        return "comparison_partial"
    if redundant_profiles:
        return "comparison_ready"
    return "comparison_ready"


def _summary(state: str) -> str:
    return state_message(
        state,
        {
            "comparison_ready": "Tuning profile comparison is ready for read-only benchmark inspection.",
            "comparison_partial": "Tuning profile comparison is only partially covered by benchmark references.",
            "comparison_inconclusive": "Tuning profile comparison remained inconclusive due to missing registry or coverage.",
            "benchmark_gap_detected": "Tuning profile comparison detected uncovered benchmark cases.",
        },
        "Tuning profile comparison remained observationally neutral.",
    )


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "comparison_ready": "The registry covers the benchmark space well enough for comparative inspection.",
            "comparison_partial": "Some benchmark references are present, but coverage is not yet complete.",
            "comparison_inconclusive": "There was not enough registry or benchmark structure for a confident comparison.",
            "benchmark_gap_detected": "At least one benchmark case still lacks declarative tuning coverage.",
        },
        "The comparison remained observationally neutral.",
    )


def _why_profile(state: str) -> str:
    return state_message(
        state,
        {
            "high_coverage_profile": "This profile covers a broad part of the benchmark case space.",
            "low_coverage_profile": "This profile intentionally or structurally covers a narrow case slice.",
            "redundant_profile": "This profile overlaps materially with others in cases and dimensions.",
            "complementary_profile": "This profile covers at least one useful benchmark area with low redundancy.",
            "tradeoff_sensitive_profile": "This profile has explicit directional tradeoffs that deserve careful manual inspection.",
            "profile_candidate_for_future_experiment": "This profile remains a plausible future candidate for controlled comparison.",
        },
        "The profile remained observationally neutral.",
    )
