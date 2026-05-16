from __future__ import annotations

from app.domain.models import (
    ControlledTuningExperimentRegistry,
    ManualExperimentCautionFlag,
    ManualExperimentDecisionSummary,
    ManualExperimentInspectionItem,
    ManualExperimentInspectionProfile,
    ManualExperimentRecommendation,
    TuningProfileBenchmarkComparison,
)
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
from app.services.runtime_profile_utils import state_message, state_reasoning
from app.services.tuning_profile_benchmark_comparison import (
    compare_tuning_profiles_against_benchmark,
)


def build_manual_experiment_inspection(
    *,
    registry: ControlledTuningExperimentRegistry | None = None,
    comparison: TuningProfileBenchmarkComparison | None = None,
    benchmark_result: object | None = None,
) -> ManualExperimentInspectionProfile:
    current_registry = registry or build_controlled_tuning_experiment_registry()
    if not current_registry.tuning_experiments:
        return ManualExperimentInspectionProfile(
            manual_experiment_inspection_state="inspection_inconclusive",
            manual_experiment_inspection_summary=_summary("inspection_inconclusive"),
            manual_experiment_inspection_reasoning=state_reasoning(
                "Inspecao manual de experimentos",
                "inspection_inconclusive",
                ["Nao havia perfis declarativos para revisar manualmente."],
            ),
            inspection_readiness="inspection_no_profiles",
            why_this_manual_inspection_state=_why("inspection_inconclusive"),
        )

    current_comparison = comparison or compare_tuning_profiles_against_benchmark(
        registry=current_registry,
        benchmark_result=benchmark_result,
    )
    if not current_comparison.profile_comparison_results:
        return ManualExperimentInspectionProfile(
            manual_experiment_inspection_state="inspection_inconclusive",
            manual_experiment_inspection_summary=_summary("inspection_inconclusive"),
            manual_experiment_inspection_reasoning=state_reasoning(
                "Inspecao manual de experimentos",
                "inspection_inconclusive",
                ["Nao havia resultados comparativos suficientes para interpretacao manual."],
            ),
            inspection_readiness="inspection_no_comparison",
            why_this_manual_inspection_state=_why("inspection_inconclusive"),
        )

    items = [_inspection_item(result) for result in current_comparison.profile_comparison_results]
    promising = [item.experiment_id for item in items if item.manual_inspection_state == "candidate_promising"]
    redundant = [item.experiment_id for item in items if item.manual_inspection_state == "candidate_redundant"]
    tradeoff_sensitive = [
        item.experiment_id
        for item in items
        if item.manual_inspection_state == "candidate_tradeoff_sensitive"
    ]
    low_coverage = [
        item.experiment_id for item in items if item.manual_inspection_state == "candidate_low_coverage"
    ]
    not_ready = [
        item.experiment_id
        for item in items
        if item.manual_inspection_state
        in {
            "candidate_not_ready",
            "candidate_requires_more_benchmarking",
            "candidate_tradeoff_sensitive",
            "candidate_low_coverage",
        }
    ]
    caution_flag_ids = sorted({flag for item in items for flag in item.caution_flags})
    caution_flag_details = [
        _flag_detail(flag_id, [item.experiment_id for item in items if flag_id in item.caution_flags])
        for flag_id in caution_flag_ids
    ]
    readiness = _readiness(current_comparison, items)
    state = _inspection_state(readiness, promising, not_ready)
    return ManualExperimentInspectionProfile(
        manual_experiment_inspection_state=state,
        manual_experiment_inspection_summary=_summary(state),
        manual_experiment_inspection_reasoning=state_reasoning(
            "Inspecao manual de experimentos",
            state,
            [
                f"Promising={len(promising)}; redundant={len(redundant)}; tradeoff_sensitive={len(tradeoff_sensitive)}.",
                f"Low_coverage={len(low_coverage)}; not_ready={len(not_ready)}; readiness={readiness}.",
            ],
        ),
        promising_candidate_profiles=promising,
        redundant_profiles=redundant,
        tradeoff_sensitive_profiles=tradeoff_sensitive,
        low_coverage_profiles=low_coverage,
        not_ready_profiles=not_ready,
        caution_flags=caution_flag_ids,
        caution_flag_details=caution_flag_details,
        manual_decision_summary=ManualExperimentDecisionSummary(
            decision_state=state,
            decision_summary=_decision_summary(state, promising, not_ready),
            recommended_profiles=promising,
            blocked_profiles=sorted(set(tradeoff_sensitive + low_coverage)),
            caution_flags=caution_flag_ids,
        ),
        inspection_readiness=readiness,
        experiment_review_items=items,
        why_this_manual_inspection_state=_why(state),
    )


def _inspection_item(result) -> ManualExperimentInspectionItem:
    caution_flags = _caution_flags(result)
    readiness_blockers = _readiness_blockers(result, caution_flags)
    state = _candidate_state(result, caution_flags, readiness_blockers)
    return ManualExperimentInspectionItem(
        experiment_id=result.experiment_id,
        experiment_name=result.experiment_name,
        manual_inspection_state=state,
        candidate_status=_candidate_status(state),
        candidate_reasoning=state_reasoning(
            "Candidato manual",
            state,
            [
                f"Alignment={result.benchmark_alignment.alignment_state}; shared_cases={len(result.shared_benchmark_cases)}.",
                f"Tradeoffs={len(result.possible_tradeoffs)}; blockers={len(readiness_blockers)}.",
            ],
        ),
        caution_flags=caution_flags,
        readiness_blockers=readiness_blockers,
        benchmark_case_coverage=list(result.covered_benchmark_cases),
        overlap_summary=(
            f"shared_cases={len(result.shared_benchmark_cases)} "
            f"shared_dimensions={len(result.shared_tuning_dimensions)} "
            f"overlap_signal={result.profile_overlap_signal:.2f}"
        ),
        tradeoff_summary=", ".join(result.possible_tradeoffs) or "none",
        manual_review_summary=_review_summary(state),
        recommendation=ManualExperimentRecommendation(
            experiment_id=result.experiment_id,
            decision_state=state,
            candidate_readiness="ready_for_manual_review" if state == "candidate_promising" else "review_constrained",
            reasoning=state_reasoning(
                "Recomendacao manual",
                state,
                [f"Covered_cases={len(result.covered_benchmark_cases)}; overlap={result.profile_overlap_signal:.2f}."],
            ),
        ),
        caution_flag_details=[_flag_detail(flag_id, [result.experiment_id]) for flag_id in caution_flags],
        why_this_candidate_status=_why_candidate(state),
        read_only=result.read_only,
        executable=result.executable,
    )


def _candidate_state(result, caution_flags: list[str], readiness_blockers: list[str]) -> str:
    if result.comparison_state == "redundant_profile":
        return "candidate_redundant"
    if result.comparison_state == "tradeoff_sensitive_profile":
        return "candidate_tradeoff_sensitive"
    if result.comparison_state == "low_coverage_profile":
        return "candidate_low_coverage"
    if (
        result.comparison_state in {"high_coverage_profile", "complementary_profile"}
        and not readiness_blockers
        and result.read_only
        and not result.executable
        and result.expected_benefits
    ):
        return "candidate_promising"
    if "insufficient_benchmark_coverage" in caution_flags or "regression_case_missing" in caution_flags:
        return "candidate_requires_more_benchmarking"
    if readiness_blockers:
        return "candidate_not_ready"
    return "inspect_candidate"


def _candidate_status(state: str) -> str:
    return {
        "candidate_promising": "promising",
        "candidate_redundant": "redundant",
        "candidate_tradeoff_sensitive": "tradeoff_sensitive",
        "candidate_low_coverage": "low_coverage",
        "candidate_not_ready": "not_ready",
        "candidate_requires_more_benchmarking": "requires_more_benchmarking",
        "inspect_candidate": "inspect",
    }.get(state, "inspect")


def _caution_flags(result) -> list[str]:
    flags: list[str] = []
    covered = set(result.covered_benchmark_cases)
    risks = " ".join(result.expected_risks)
    if len(result.covered_benchmark_cases) <= 1 or (
        not result.benchmark_alignment.covered_regression_sensitive_cases
        and len(result.uncovered_priority_cases) >= 4
    ):
        flags.append("insufficient_benchmark_coverage")
    if result.comparison_state == "tradeoff_sensitive_profile":
        flags.append("high_tradeoff_sensitivity")
    if result.comparison_state == "redundant_profile":
        flags.append("profile_redundancy")
    if not result.benchmark_alignment.covered_regression_sensitive_cases:
        flags.append("regression_case_missing")
    if "pedagogically_stable_baseline_case" not in covered:
        flags.append("baseline_protection_missing")
    if "scaffold_dependency_case" in covered or "scaffold" in risks:
        flags.append("scaffold_dependency_risk")
    if "unsafe_compression_case" in covered or "compression" in risks:
        flags.append("compression_safety_risk")
    if "retrieval_inflation_case" in covered or "retrieval" in risks:
        flags.append("retrieval_inflation_risk")
    if "false_fluency_case" in covered:
        flags.append("false_fluency_risk")
    if flags:
        flags.append("manual_review_required")
    return sorted(set(flags))


def _readiness_blockers(result, caution_flags: list[str]) -> list[str]:
    blockers: list[str] = []
    if "insufficient_benchmark_coverage" in caution_flags:
        blockers.append("insufficient_benchmark_coverage")
    if "high_tradeoff_sensitivity" in caution_flags:
        blockers.append("high_tradeoff_sensitivity")
    if "profile_redundancy" in caution_flags:
        blockers.append("profile_redundancy")
    if "regression_case_missing" in caution_flags:
        blockers.append("regression_case_missing")
    if result.executable:
        blockers.append("unexpected_executable_profile")
    return blockers


def _flag_detail(flag_id: str, affected_profiles: list[str]) -> ManualExperimentCautionFlag:
    return ManualExperimentCautionFlag(
        flag_id=flag_id,
        flag_summary=_flag_summary(flag_id),
        affected_profiles=sorted(set(affected_profiles)),
        reasoning=[_flag_summary(flag_id)],
    )


def _flag_summary(flag_id: str) -> str:
    return state_message(
        flag_id,
        {
            "insufficient_benchmark_coverage": "Benchmark coverage is too narrow for confident manual comparison.",
            "high_tradeoff_sensitivity": "The profile affects fragile dimensions and deserves extra manual caution.",
            "profile_redundancy": "The profile overlaps heavily with other declarative experiments.",
            "regression_case_missing": "Regression-sensitive benchmark cases are not clearly represented.",
            "baseline_protection_missing": "The stable baseline case is not covered by this profile.",
            "scaffold_dependency_risk": "The profile touches scaffold-sensitive scenarios.",
            "compression_safety_risk": "The profile touches compression-sensitive scenarios.",
            "retrieval_inflation_risk": "The profile touches retrieval-inflation-sensitive scenarios.",
            "false_fluency_risk": "The profile touches false-fluency-sensitive scenarios.",
            "manual_review_required": "The profile should remain under manual review before any future controlled experiment.",
        },
        "This caution flag remains observational.",
    )


def _readiness(comparison: TuningProfileBenchmarkComparison, items: list[ManualExperimentInspectionItem]) -> str:
    if not items:
        return "inspection_no_comparison"
    if comparison.comparison_readiness == "comparison_registry_empty":
        return "inspection_no_profiles"
    if comparison.comparison_readiness in {"comparison_benchmark_missing", "comparison_insufficient"}:
        return "inspection_insufficient"
    if all(item.manual_inspection_state in {"candidate_not_ready", "candidate_requires_more_benchmarking"} for item in items):
        return "inspection_insufficient"
    if comparison.comparison_readiness == "comparison_partial":
        return "inspection_partial"
    return "inspection_ready"


def _inspection_state(readiness: str, promising: list[str], not_ready: list[str]) -> str:
    if readiness in {"inspection_no_profiles", "inspection_no_comparison", "inspection_insufficient"}:
        return "inspection_inconclusive"
    if promising:
        return "inspect_candidate"
    if not_ready:
        return "candidate_requires_more_benchmarking"
    return "inspection_inconclusive"


def _decision_summary(state: str, promising: list[str], not_ready: list[str]) -> str:
    return {
        "inspect_candidate": (
            "Manual inspection identified bounded candidates that look promising for future controlled comparison."
        ),
        "candidate_requires_more_benchmarking": (
            "Manual inspection found profiles that still need more benchmark coverage before deeper review."
        ),
        "inspection_inconclusive": "Manual inspection remained inconclusive with the current comparison evidence.",
    }.get(state, f"Promising profiles={len(promising)}; constrained profiles={len(not_ready)}.")


def _summary(state: str) -> str:
    return state_message(
        state,
        {
            "inspect_candidate": "Manual experiment inspection identified candidate profiles for cautious human review.",
            "candidate_requires_more_benchmarking": "Manual experiment inspection found profiles that need more benchmark coverage.",
            "inspection_inconclusive": "Manual experiment inspection remained inconclusive.",
        },
        "Manual experiment inspection remained observationally neutral.",
    )


def _review_summary(state: str) -> str:
    return state_message(
        state,
        {
            "candidate_promising": "Promising read-only candidate for future controlled benchmarking review.",
            "candidate_redundant": "Redundant candidate with limited unique benchmark contribution.",
            "candidate_tradeoff_sensitive": "Tradeoff-sensitive candidate that needs extra manual caution.",
            "candidate_low_coverage": "Low-coverage candidate with weak benchmark support.",
            "candidate_not_ready": "Not-ready candidate blocked by coverage or tradeoff constraints.",
            "candidate_requires_more_benchmarking": "Candidate requires more benchmark support before deeper manual review.",
            "inspect_candidate": "Candidate is suitable for bounded manual inspection.",
        },
        "Candidate remains neutral pending manual inspection.",
    )


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "inspect_candidate": "The comparison exposed at least one non-executable profile with useful benchmark coverage and bounded risk.",
            "candidate_requires_more_benchmarking": "The comparison is available, but coverage and readiness still constrain manual interpretation.",
            "inspection_inconclusive": "Available comparison evidence was insufficient for reliable manual inspection.",
        },
        "Manual inspection stays read-only and interpretive.",
    )


def _why_candidate(state: str) -> str:
    return state_message(
        state,
        {
            "candidate_promising": "The profile has meaningful coverage without high overlap or strong tradeoff blockers.",
            "candidate_redundant": "The profile overlaps strongly with existing declarative experiments.",
            "candidate_tradeoff_sensitive": "The profile affects sensitive runtime dimensions and remains caution-heavy.",
            "candidate_low_coverage": "The profile covers too few benchmark cases to support confident review.",
            "candidate_not_ready": "The profile remains blocked by readiness constraints.",
            "candidate_requires_more_benchmarking": "The profile needs broader or clearer benchmark support before deeper review.",
            "inspect_candidate": "The profile is bounded enough for manual inspection without becoming executable.",
        },
        "The candidate remains observational only.",
    )
