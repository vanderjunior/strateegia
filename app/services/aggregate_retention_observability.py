from __future__ import annotations

from collections import defaultdict

from app.domain.models import (
    AggregateRetentionEvidenceSummary,
    AggregateRetentionMetric,
    AggregateRetentionPopulationSummary,
    AggregateRetentionProfile,
    AggregateRetentionRiskProfile,
    LongitudinalRetentionProfile,
    ProgressState,
    RetentionCohortSummary,
    TopicRetentionRiskSummary,
)
from app.services.longitudinal_retention_observability import observe_longitudinal_retention
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning


def observe_aggregate_retention(
    *,
    progress: ProgressState | dict | None = None,
    runtime_block: dict[str, object] | None = None,
    runtime_blocks_by_microtopic: dict[str, dict[str, object]] | None = None,
) -> AggregateRetentionProfile:
    normalized_progress = _normalize_progress(progress)
    block_map = {
        str(key): dict(value or {})
        for key, value in dict(runtime_blocks_by_microtopic or {}).items()
    }
    default_runtime_block = dict(runtime_block or {})
    microtopic_ids = _observed_microtopic_ids(normalized_progress, block_map)
    if not microtopic_ids:
        return _empty_profile()

    profiles: list[tuple[str, str, LongitudinalRetentionProfile]] = []
    topic_id_by_microtopic: dict[str, str] = {}
    observed_with_attempts = 0
    observed_with_timestamps = 0
    observed_with_resurfacing_cycles = 0
    observed_with_retention_evidence = 0

    for microtopic_id in microtopic_ids:
        performance = normalized_progress.microtopic_performance.get(microtopic_id)
        memory = normalized_progress.pedagogical_memory.get(microtopic_id)
        topic_id = str(
            (performance.topic_id if performance else None)
            or (memory.topic_id if memory else None)
            or "unknown_topic"
        )
        topic_id_by_microtopic[microtopic_id] = topic_id
        block = block_map.get(microtopic_id)
        if block is None and default_runtime_block.get("microtopic_id") == microtopic_id:
            block = default_runtime_block
        profile = observe_longitudinal_retention(
            progress=normalized_progress,
            runtime_block=block or {},
            microtopic_id=microtopic_id,
        )
        profiles.append((microtopic_id, topic_id, profile))

        total_questions = int(getattr(performance, "total_questions", 0) or 0)
        if total_questions >= 3:
            observed_with_attempts += 1
        if _has_timestamp(performance, memory):
            observed_with_timestamps += 1
        if int(getattr(memory, "resurfacing_cycles", 0) or 0) > 0:
            observed_with_resurfacing_cycles += 1
        if profile.retention_evidence_level != "insufficient":
            observed_with_retention_evidence += 1

    total = len(profiles)
    counts = _population_counts(profiles)
    evidence_summary = _evidence_summary(
        total=total,
        observed_with_attempts=observed_with_attempts,
        observed_with_timestamps=observed_with_timestamps,
        observed_with_resurfacing_cycles=observed_with_resurfacing_cycles,
        observed_with_retention_evidence=observed_with_retention_evidence,
    )
    topic_summaries = _topic_summaries(profiles)
    metrics = _aggregate_metrics(total=total, counts=counts, topic_summaries=topic_summaries, evidence=evidence_summary)
    population_summary = _population_summary(counts, total)
    aggregate_resurfacing_state = _aggregate_resurfacing_state(counts, total)
    aggregate_recovery_state = _aggregate_recovery_state(counts, total)
    aggregate_reconstruction_state = _aggregate_reconstruction_state(counts, total)
    aggregate_transfer_state = _aggregate_transfer_state(counts, total)
    risk_profile = _risk_profile(
        total=total,
        counts=counts,
        topic_summaries=topic_summaries,
        evidence=evidence_summary,
        metrics=metrics,
    )
    aggregate_state = _aggregate_state(
        counts=counts,
        total=total,
        evidence_state=evidence_summary.aggregate_retention_evidence_state,
    )
    durable_ratio = _ratio(counts["durable"], total)
    fragile_ratio = _ratio(counts["fragile"], total)
    superficial_ratio = _ratio(counts["superficial"], total)
    summary = _summary_message(aggregate_state)
    reasoning = state_reasoning(
        "Aggregate retention",
        aggregate_state,
        [
            f"Observed microtopics={total}; durable={counts['durable']}; fragile={counts['fragile']}; superficial={counts['superficial']}.",
            f"Evidence={evidence_summary.aggregate_retention_evidence_state}; resurfacing={aggregate_resurfacing_state}; recovery={aggregate_recovery_state}.",
        ],
    )
    return AggregateRetentionProfile(
        aggregate_retention_state=aggregate_state,
        aggregate_retention_summary=summary,
        aggregate_retention_reasoning=reasoning,
        retention_population_summary=population_summary,
        topic_retention_risk_summary=topic_summaries,
        aggregate_retention_risk_profile=risk_profile,
        aggregate_retention_evidence_summary=evidence_summary,
        aggregate_resurfacing_state=aggregate_resurfacing_state,
        aggregate_recovery_state=aggregate_recovery_state,
        aggregate_reconstruction_state=aggregate_reconstruction_state,
        aggregate_transfer_state=aggregate_transfer_state,
        aggregate_retention_metrics=metrics,
        aggregate_retention_risk_flags=risk_profile.aggregate_retention_risk_flags,
        total_microtopics_observed=total,
        durable_microtopics_count=counts["durable"],
        fragile_microtopics_count=counts["fragile"],
        superficial_microtopics_count=counts["superficial"],
        insufficient_evidence_count=counts["insufficient"],
        false_fluency_count=counts["false_fluency"],
        evidence_coverage_ratio=evidence_summary.evidence_coverage_ratio,
        durable_ratio=durable_ratio,
        fragile_ratio=fragile_ratio,
        superficial_ratio=superficial_ratio,
        why_this_aggregate_retention_state=_why(aggregate_state),
    )


def _normalize_progress(progress: ProgressState | dict | None) -> ProgressState:
    if isinstance(progress, ProgressState):
        return progress.model_copy(deep=True)
    if progress is None:
        return ProgressState()
    return ProgressState.model_validate(progress)


def _observed_microtopic_ids(
    progress: ProgressState,
    runtime_blocks_by_microtopic: dict[str, dict[str, object]],
) -> list[str]:
    observed = set(progress.microtopic_performance) | set(progress.pedagogical_memory) | set(runtime_blocks_by_microtopic)
    return sorted(str(item) for item in observed if str(item))


def _population_counts(profiles: list[tuple[str, str, LongitudinalRetentionProfile]]) -> dict[str, int]:
    counts = defaultdict(int)
    for _, _, profile in profiles:
        if profile.longitudinal_retention_state == "retention_sustainable":
            counts["durable"] += 1
        elif profile.longitudinal_retention_state == "retention_emerging":
            counts["emerging"] += 1
        elif profile.longitudinal_retention_state == "retention_fragile":
            counts["fragile"] += 1
        elif profile.longitudinal_retention_state == "retention_superficial":
            counts["superficial"] += 1
        else:
            counts["insufficient"] += 1

        if profile.false_fluency_retention_risk >= 0.55:
            counts["false_fluency"] += 1
        if profile.resurfacing_effectiveness_state == "effective":
            counts["resurfacing_effective"] += 1
        elif profile.resurfacing_effectiveness_state == "ineffective":
            counts["resurfacing_ineffective"] += 1
        elif profile.resurfacing_effectiveness_state == "not_enough_cycles":
            counts["no_resurfacing_evidence"] += 1
        else:
            counts["resurfacing_inconclusive"] += 1

        if profile.recovery_state == "recovery_improving":
            counts["recovery_improving"] += 1
        elif profile.recovery_state == "recovery_stalled":
            counts["recovery_stalled"] += 1
        elif profile.recovery_state == "recovery_unstable":
            counts["recovery_unstable"] += 1
        else:
            counts["recovery_insufficient"] += 1

        if profile.reconstruction_retention_state == "reconstruction_durable":
            counts["reconstruction_durable"] += 1
        elif profile.reconstruction_retention_state == "reconstruction_improving":
            counts["reconstruction_improving"] += 1
        elif profile.reconstruction_retention_state == "reconstruction_fragile":
            counts["reconstruction_fragile"] += 1

        if profile.transfer_retention_state == "transfer_durable":
            counts["transfer_durable"] += 1
        elif profile.transfer_retention_state == "transfer_improving":
            counts["transfer_improving"] += 1
        elif profile.transfer_retention_state == "transfer_fragile":
            counts["transfer_fragile"] += 1
    return counts


def _evidence_summary(
    *,
    total: int,
    observed_with_attempts: int,
    observed_with_timestamps: int,
    observed_with_resurfacing_cycles: int,
    observed_with_retention_evidence: int,
) -> AggregateRetentionEvidenceSummary:
    if total <= 0:
        return AggregateRetentionEvidenceSummary(
            aggregate_retention_evidence_state="evidence_insufficient",
            aggregate_retention_evidence_reasoning=["No microtopics were observed for aggregate retention."],
            evidence_coverage_ratio=0.0,
            observed_with_attempts=0,
            observed_with_timestamps=0,
            observed_with_resurfacing_cycles=0,
            observed_with_retention_evidence=0,
        )
    coverage_ratio = average_values(
        [
            observed_with_attempts / total,
            observed_with_timestamps / total,
            observed_with_resurfacing_cycles / total,
            observed_with_retention_evidence / total,
        ]
    )
    if coverage_ratio >= 0.65:
        state = "evidence_sufficient"
    elif coverage_ratio >= 0.45:
        state = "evidence_partial"
    elif coverage_ratio > 0.0:
        state = "evidence_sparse"
    else:
        state = "evidence_insufficient"
    return AggregateRetentionEvidenceSummary(
        aggregate_retention_evidence_state=state,
        aggregate_retention_evidence_reasoning=state_reasoning(
            "Aggregate evidence",
            state,
            [
                f"Coverage ratio={coverage_ratio:.2f}; attempts={observed_with_attempts}/{total}; timestamps={observed_with_timestamps}/{total}.",
                f"Resurfacing={observed_with_resurfacing_cycles}/{total}; retention_evidence={observed_with_retention_evidence}/{total}.",
            ],
        ),
        evidence_coverage_ratio=coverage_ratio,
        observed_with_attempts=observed_with_attempts,
        observed_with_timestamps=observed_with_timestamps,
        observed_with_resurfacing_cycles=observed_with_resurfacing_cycles,
        observed_with_retention_evidence=observed_with_retention_evidence,
    )


def _topic_summaries(
    profiles: list[tuple[str, str, LongitudinalRetentionProfile]],
) -> list[TopicRetentionRiskSummary]:
    grouped: dict[str, list[LongitudinalRetentionProfile]] = defaultdict(list)
    for _, topic_id, profile in profiles:
        grouped[topic_id].append(profile)

    summaries: list[TopicRetentionRiskSummary] = []
    for topic_id in sorted(grouped):
        topic_profiles = grouped[topic_id]
        observed = len(topic_profiles)
        durable = sum(1 for profile in topic_profiles if profile.longitudinal_retention_state == "retention_sustainable")
        fragile = sum(1 for profile in topic_profiles if profile.longitudinal_retention_state == "retention_fragile")
        superficial = sum(1 for profile in topic_profiles if profile.longitudinal_retention_state == "retention_superficial")
        insufficient = sum(
            1
            for profile in topic_profiles
            if profile.longitudinal_retention_state in {"retention_insufficient_evidence", "retention_inconclusive"}
        )
        false_fluency = sum(1 for profile in topic_profiles if profile.false_fluency_retention_risk >= 0.55)
        risk_flags: list[str] = []
        if fragile > 0:
            risk_flags.append("topic_fragility_present")
        if superficial > 0:
            risk_flags.append("topic_superficial_stability_present")
        if false_fluency > 0:
            risk_flags.append("topic_false_fluency_present")
        if insufficient == observed:
            state = "topic_retention_insufficient_evidence"
        elif fragile / observed >= 0.5:
            state = "topic_retention_fragile"
        elif superficial / observed >= 0.5:
            state = "topic_retention_superficial"
        elif durable / observed >= 0.6:
            state = "topic_retention_stable"
        elif durable > 0 and (fragile > 0 or superficial > 0):
            state = "topic_retention_mixed"
        else:
            state = "topic_retention_emerging"
        summaries.append(
            TopicRetentionRiskSummary(
                topic_id=topic_id,
                observed_microtopics=observed,
                durable_count=durable,
                fragile_count=fragile,
                superficial_count=superficial,
                insufficient_evidence_count=insufficient,
                false_fluency_count=false_fluency,
                risk_flags=risk_flags,
                topic_retention_state=state,
                topic_retention_reasoning=state_reasoning(
                    "Topic retention",
                    state,
                    [
                        f"Topic={topic_id}; observed={observed}; durable={durable}; fragile={fragile}; superficial={superficial}.",
                    ],
                ),
            )
        )
    return summaries


def _aggregate_metrics(
    *,
    total: int,
    counts: dict[str, int],
    topic_summaries: list[TopicRetentionRiskSummary],
    evidence: AggregateRetentionEvidenceSummary,
) -> list[AggregateRetentionMetric]:
    durable_ratio = _ratio(counts["durable"], total)
    fragile_ratio = _ratio(counts["fragile"], total)
    superficial_ratio = _ratio(counts["superficial"], total)
    false_fluency_ratio = _ratio(counts["false_fluency"], total)
    resurfacing_success_ratio = _ratio(
        counts["resurfacing_effective"],
        counts["resurfacing_effective"] + counts["resurfacing_ineffective"] + counts["resurfacing_inconclusive"],
    )
    recovery_improvement_ratio = _ratio(
        counts["recovery_improving"],
        counts["recovery_improving"] + counts["recovery_stalled"] + counts["recovery_unstable"],
    )
    reconstruction_fragility_ratio = _ratio(
        counts["reconstruction_fragile"],
        counts["reconstruction_fragile"] + counts["reconstruction_durable"] + counts["reconstruction_improving"],
    )
    transfer_fragility_ratio = _ratio(
        counts["transfer_fragile"],
        counts["transfer_fragile"] + counts["transfer_durable"] + counts["transfer_improving"],
    )
    max_topic_risk = max((summary.fragile_count + summary.superficial_count for summary in topic_summaries), default=0)
    total_topic_risk = sum(summary.fragile_count + summary.superficial_count for summary in topic_summaries)
    topic_risk_concentration_ratio = _ratio(max_topic_risk, total_topic_risk)
    return [
        AggregateRetentionMetric(
            metric_name="durable_ratio",
            metric_value=durable_ratio,
            interpretation="Share of observed microtopics classified as durable.",
        ),
        AggregateRetentionMetric(
            metric_name="fragile_ratio",
            metric_value=fragile_ratio,
            interpretation="Share of observed microtopics classified as fragile.",
        ),
        AggregateRetentionMetric(
            metric_name="superficial_ratio",
            metric_value=superficial_ratio,
            interpretation="Share of observed microtopics classified as superficially stable.",
        ),
        AggregateRetentionMetric(
            metric_name="false_fluency_ratio",
            metric_value=false_fluency_ratio,
            interpretation="Share of observed microtopics with elevated false fluency risk.",
        ),
        AggregateRetentionMetric(
            metric_name="evidence_coverage_ratio",
            metric_value=evidence.evidence_coverage_ratio,
            interpretation="Coverage of longitudinal evidence across the observed population.",
        ),
        AggregateRetentionMetric(
            metric_name="resurfacing_success_ratio",
            metric_value=resurfacing_success_ratio,
            interpretation="Success ratio for resurfacing where there is resurfacing evidence.",
        ),
        AggregateRetentionMetric(
            metric_name="recovery_improvement_ratio",
            metric_value=recovery_improvement_ratio,
            interpretation="Improvement ratio for recovery after error where recovery evidence exists.",
        ),
        AggregateRetentionMetric(
            metric_name="reconstruction_fragility_ratio",
            metric_value=reconstruction_fragility_ratio,
            interpretation="Fragility ratio for reconstruction retention.",
        ),
        AggregateRetentionMetric(
            metric_name="transfer_fragility_ratio",
            metric_value=transfer_fragility_ratio,
            interpretation="Fragility ratio for transfer retention.",
        ),
        AggregateRetentionMetric(
            metric_name="topic_risk_concentration_ratio",
            metric_value=topic_risk_concentration_ratio,
            interpretation="Concentration of fragile or superficial microtopics within the riskiest topic.",
        ),
    ]


def _population_summary(counts: dict[str, int], total: int) -> AggregateRetentionPopulationSummary:
    return AggregateRetentionPopulationSummary(
        total_microtopics_observed=total,
        durable_microtopics_count=counts["durable"],
        emerging_microtopics_count=counts["emerging"],
        fragile_microtopics_count=counts["fragile"],
        superficial_microtopics_count=counts["superficial"],
        insufficient_evidence_count=counts["insufficient"],
        false_fluency_count=counts["false_fluency"],
        resurfacing_effective_count=counts["resurfacing_effective"],
        resurfacing_inconclusive_count=counts["resurfacing_inconclusive"],
        resurfacing_ineffective_count=counts["resurfacing_ineffective"],
        no_resurfacing_evidence_count=counts["no_resurfacing_evidence"],
        recovery_improving_count=counts["recovery_improving"],
        recovery_stalled_count=counts["recovery_stalled"],
        recovery_unstable_count=counts["recovery_unstable"],
        recovery_insufficient_evidence_count=counts["recovery_insufficient"],
        reconstruction_fragile_count=counts["reconstruction_fragile"],
        reconstruction_durable_count=counts["reconstruction_durable"],
        reconstruction_improving_count=counts["reconstruction_improving"],
        transfer_fragile_count=counts["transfer_fragile"],
        transfer_durable_count=counts["transfer_durable"],
        transfer_improving_count=counts["transfer_improving"],
        retention_population_reasoning=[
            f"Observed {total} microtopics with durable={counts['durable']}, fragile={counts['fragile']}, superficial={counts['superficial']}.",
        ],
        cohorts=[
            _cohort("durable", counts["durable"], total),
            _cohort("fragile", counts["fragile"], total),
            _cohort("superficial", counts["superficial"], total),
            _cohort("insufficient_evidence", counts["insufficient"], total),
        ],
    )


def _aggregate_resurfacing_state(counts: dict[str, int], total: int) -> str:
    evidence_total = counts["resurfacing_effective"] + counts["resurfacing_ineffective"] + counts["resurfacing_inconclusive"]
    if total <= 0 or evidence_total <= 0:
        return "aggregate_resurfacing_insufficient_evidence"
    if counts["resurfacing_effective"] / evidence_total >= 0.6:
        return "aggregate_resurfacing_effective"
    if counts["resurfacing_ineffective"] / evidence_total > 0.5:
        return "aggregate_resurfacing_fragile"
    return "aggregate_resurfacing_mixed"


def _aggregate_recovery_state(counts: dict[str, int], total: int) -> str:
    evidence_total = counts["recovery_improving"] + counts["recovery_stalled"] + counts["recovery_unstable"]
    if total <= 0 or evidence_total <= 0:
        return "aggregate_recovery_insufficient_evidence"
    if counts["recovery_improving"] / evidence_total >= 0.6:
        return "aggregate_recovery_improving"
    if counts["recovery_unstable"] / evidence_total > 0.5:
        return "aggregate_recovery_unstable"
    return "aggregate_recovery_mixed"


def _aggregate_reconstruction_state(counts: dict[str, int], total: int) -> str:
    evidence_total = counts["reconstruction_durable"] + counts["reconstruction_improving"] + counts["reconstruction_fragile"]
    if total <= 0 or evidence_total <= 0:
        return "aggregate_reconstruction_insufficient_evidence"
    if counts["reconstruction_durable"] / evidence_total >= 0.6:
        return "aggregate_reconstruction_durable"
    if counts["reconstruction_durable"] > 0 and counts["reconstruction_fragile"] > 0:
        return "aggregate_reconstruction_mixed"
    if counts["reconstruction_fragile"] / evidence_total > 0.5:
        return "aggregate_reconstruction_fragile"
    return "aggregate_reconstruction_mixed"


def _aggregate_transfer_state(counts: dict[str, int], total: int) -> str:
    evidence_total = counts["transfer_durable"] + counts["transfer_improving"] + counts["transfer_fragile"]
    if total <= 0 or evidence_total <= 0:
        return "aggregate_transfer_insufficient_evidence"
    if counts["transfer_durable"] / evidence_total >= 0.6:
        return "aggregate_transfer_durable"
    if counts["transfer_durable"] > 0 and counts["transfer_fragile"] > 0:
        return "aggregate_transfer_mixed"
    if counts["transfer_fragile"] / evidence_total > 0.5:
        return "aggregate_transfer_fragile"
    return "aggregate_transfer_mixed"


def _risk_profile(
    *,
    total: int,
    counts: dict[str, int],
    topic_summaries: list[TopicRetentionRiskSummary],
    evidence: AggregateRetentionEvidenceSummary,
    metrics: list[AggregateRetentionMetric],
) -> AggregateRetentionRiskProfile:
    metric_map = {metric.metric_name: metric.metric_value for metric in metrics}
    false_fluency_ratio = metric_map.get("false_fluency_ratio", 0.0)
    reconstruction_fragility_ratio = metric_map.get("reconstruction_fragility_ratio", 0.0)
    transfer_fragility_ratio = metric_map.get("transfer_fragility_ratio", 0.0)
    topic_risk_concentration_ratio = metric_map.get("topic_risk_concentration_ratio", 0.0)
    resurfacing_failure_ratio = _ratio(
        counts["resurfacing_ineffective"],
        counts["resurfacing_effective"] + counts["resurfacing_ineffective"] + counts["resurfacing_inconclusive"],
    )
    unstable_recovery_ratio = _ratio(
        counts["recovery_unstable"],
        counts["recovery_improving"] + counts["recovery_stalled"] + counts["recovery_unstable"],
    )
    superficial_ratio = _ratio(counts["superficial"], total)

    flags: list[str] = []
    if false_fluency_ratio >= 0.25:
        flags.append("aggregate_false_fluency_risk")
    if resurfacing_failure_ratio >= 0.34:
        flags.append("aggregate_resurfacing_failure_risk")
    if reconstruction_fragility_ratio >= 0.3:
        flags.append("aggregate_reconstruction_decay_risk")
    if transfer_fragility_ratio >= 0.3:
        flags.append("aggregate_transfer_decay_risk")
    if unstable_recovery_ratio >= 0.3:
        flags.append("aggregate_unstable_recovery_risk")
    if superficial_ratio >= 0.25:
        flags.append("aggregate_superficial_stabilization_risk")
    if evidence.aggregate_retention_evidence_state in {"evidence_sparse", "evidence_insufficient"}:
        flags.append("aggregate_insufficient_longitudinal_evidence")
    if topic_risk_concentration_ratio >= 0.4 and topic_summaries:
        flags.append("aggregate_topic_risk_concentration")

    return AggregateRetentionRiskProfile(
        aggregate_retention_risk_flags=flags,
        aggregate_false_fluency_risk=false_fluency_ratio,
        aggregate_resurfacing_failure_risk=resurfacing_failure_ratio,
        aggregate_reconstruction_decay_risk=reconstruction_fragility_ratio,
        aggregate_transfer_decay_risk=transfer_fragility_ratio,
        aggregate_unstable_recovery_risk=unstable_recovery_ratio,
        aggregate_superficial_stabilization_risk=superficial_ratio,
        aggregate_topic_risk_concentration=topic_risk_concentration_ratio,
    )


def _aggregate_state(*, counts: dict[str, int], total: int, evidence_state: str) -> str:
    if total <= 0:
        return "aggregate_retention_insufficient_evidence"
    if evidence_state == "evidence_insufficient":
        return "aggregate_retention_insufficient_evidence"
    durable_ratio = _ratio(counts["durable"], total)
    fragile_ratio = _ratio(counts["fragile"], total)
    superficial_ratio = _ratio(counts["superficial"], total)
    emerging_ratio = _ratio(counts["emerging"], total)
    if superficial_ratio >= 0.35:
        return "aggregate_retention_superficial"
    if fragile_ratio >= 0.35:
        return "aggregate_retention_fragile"
    if durable_ratio >= 0.6 and fragile_ratio <= 0.2 and superficial_ratio <= 0.2:
        return "aggregate_retention_sustainable"
    if emerging_ratio >= 0.35 and durable_ratio < 0.5:
        return "aggregate_retention_emerging"
    if evidence_state == "evidence_sparse":
        return "aggregate_retention_inconclusive"
    return "aggregate_retention_mixed"


def _summary_message(state: str) -> str:
    return state_message(
        state,
        {
            "aggregate_retention_sustainable": "Aggregate retention appears sustainable across the observed population.",
            "aggregate_retention_emerging": "Aggregate retention is emerging but not yet fully stable.",
            "aggregate_retention_fragile": "Aggregate retention shows fragile patterns across the observed population.",
            "aggregate_retention_superficial": "Aggregate retention suggests superficial stability or false fluency in part of the population.",
            "aggregate_retention_mixed": "Aggregate retention is mixed across the observed population.",
            "aggregate_retention_inconclusive": "Aggregate retention is inconclusive because evidence remains sparse.",
            "aggregate_retention_insufficient_evidence": "Aggregate retention has insufficient evidence for a reliable summary.",
        },
        "Aggregate retention summary is not available.",
    )


def _cohort(name: str, count: int, total: int) -> RetentionCohortSummary:
    return RetentionCohortSummary(cohort_name=name, count=count, ratio=_ratio(count, total))


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(clamp_value(count / total), 4)


def _has_timestamp(performance, memory) -> bool:
    return bool(
        getattr(performance, "last_reviewed_at", None)
        or getattr(performance, "last_seen_at", None)
        or getattr(performance, "last_correct_at", None)
        or getattr(performance, "last_incorrect_at", None)
        or getattr(memory, "last_stabilized_at", None)
    )


def _empty_profile() -> AggregateRetentionProfile:
    evidence = AggregateRetentionEvidenceSummary(
        aggregate_retention_evidence_state="evidence_insufficient",
        aggregate_retention_evidence_reasoning=["No microtopics were observed for aggregate retention."],
        evidence_coverage_ratio=0.0,
    )
    risk_profile = AggregateRetentionRiskProfile(
        aggregate_retention_risk_flags=["aggregate_insufficient_longitudinal_evidence"]
    )
    return AggregateRetentionProfile(
        aggregate_retention_state="aggregate_retention_insufficient_evidence",
        aggregate_retention_summary="Aggregate retention has insufficient evidence for a reliable summary.",
        aggregate_retention_reasoning=state_reasoning(
            "Aggregate retention",
            "aggregate_retention_insufficient_evidence",
            ["No observed microtopics were available in progress or pedagogical memory."],
        ),
        retention_population_summary=AggregateRetentionPopulationSummary(
            retention_population_reasoning=["No microtopics were observed for aggregate retention."]
        ),
        topic_retention_risk_summary=[],
        aggregate_retention_risk_profile=risk_profile,
        aggregate_retention_evidence_summary=evidence,
        aggregate_resurfacing_state="aggregate_resurfacing_insufficient_evidence",
        aggregate_recovery_state="aggregate_recovery_insufficient_evidence",
        aggregate_reconstruction_state="aggregate_reconstruction_insufficient_evidence",
        aggregate_transfer_state="aggregate_transfer_insufficient_evidence",
        aggregate_retention_metrics=[],
        aggregate_retention_risk_flags=risk_profile.aggregate_retention_risk_flags,
        total_microtopics_observed=0,
        durable_microtopics_count=0,
        fragile_microtopics_count=0,
        superficial_microtopics_count=0,
        insufficient_evidence_count=0,
        false_fluency_count=0,
        evidence_coverage_ratio=0.0,
        durable_ratio=0.0,
        fragile_ratio=0.0,
        superficial_ratio=0.0,
        why_this_aggregate_retention_state=_why("aggregate_retention_insufficient_evidence"),
    )


def _why(state: str) -> str:
    mapping = {
        "aggregate_retention_sustainable": "Most observed microtopics show durable retention with bounded fragility.",
        "aggregate_retention_emerging": "Observed microtopics show progress, but aggregate durability is not yet dominant.",
        "aggregate_retention_fragile": "Fragile retention states are too concentrated in the observed population.",
        "aggregate_retention_superficial": "Superficial stability or false fluency is too visible in the observed population.",
        "aggregate_retention_mixed": "The observed population shows a mixed retention profile across cohorts.",
        "aggregate_retention_inconclusive": "Evidence exists, but it is too sparse for a strong aggregate conclusion.",
        "aggregate_retention_insufficient_evidence": "Aggregate retention evidence is insufficient to support a stronger conclusion.",
    }
    return mapping.get(state, "Aggregate retention state was derived from bounded longitudinal summaries.")
