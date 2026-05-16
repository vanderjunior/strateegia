from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import (
    LongitudinalRetentionProfile,
    MicroTopicPerformance,
    PedagogicalMemory,
    ProgressState,
    RetentionObservabilitySummary,
    RetentionRecoveryProfile,
    RetentionRiskProfile,
    RetentionSignalProfile,
    RetentionStabilitySummary,
)
from app.services.pedagogical_stability import analyze_pedagogical_stability
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning


def observe_longitudinal_retention(
    *,
    progress: ProgressState | dict | None = None,
    runtime_block: dict[str, object] | None = None,
    microtopic_id: str | None = None,
) -> LongitudinalRetentionProfile:
    normalized_progress = _normalize_progress(progress)
    block = dict(runtime_block or {})
    focus_microtopic_id = (
        microtopic_id
        or str(block.get("microtopic_id") or "")
        or _selected_microtopic_id(block)
        or _latest_microtopic_id(normalized_progress)
    )
    performance = _performance_for_microtopic(normalized_progress, focus_microtopic_id)
    memory = _memory_for_microtopic(normalized_progress, focus_microtopic_id, performance.topic_id)

    evidence_level = _evidence_level(performance, memory, block)
    stability = analyze_pedagogical_stability(
        performance=performance.model_dump(mode="json"),
        pedagogical_memory=memory.model_dump(mode="json"),
        resurfacing_signal=_resurfacing_pressure(performance, memory, block),
    )
    retention_confidence = average_values(
        [
            block.get("retention_confidence"),
            stability.get("retention_confidence"),
            block.get("validation_confidence"),
            block.get("longitudinal_validation_signal"),
            block.get("longitudinal_consistency"),
            stability.get("longitudinal_consistency"),
        ]
    )
    resurfacing_state, resurfacing_signal, resurfacing_reasoning = _resurfacing_observation(
        performance, memory, block
    )
    recovery_state, recovery_signal, recovery_reasoning = _recovery_observation(
        performance, memory, block, stability
    )
    reconstruction_state, reconstruction_signal, reconstruction_reasoning = _reconstruction_observation(
        performance, memory, block
    )
    transfer_state, transfer_signal, transfer_reasoning = _transfer_observation(
        performance, memory, block
    )
    false_fluency_risk, superficial_signal = _false_fluency_observation(
        performance,
        memory,
        block,
        retention_confidence,
        resurfacing_signal,
        reconstruction_signal,
        transfer_signal,
    )
    durability_state, durability_signal, durability_reasoning = _durability_observation(
        evidence_level=evidence_level,
        block=block,
        stability=stability,
        retention_confidence=retention_confidence,
        resurfacing_signal=resurfacing_signal,
        recovery_signal=recovery_signal,
        reconstruction_signal=reconstruction_signal,
        transfer_signal=transfer_signal,
        false_fluency_risk=false_fluency_risk,
        superficial_signal=superficial_signal,
    )
    risk_flags = _risk_flags(
        evidence_level=evidence_level,
        resurfacing_state=resurfacing_state,
        recovery_state=recovery_state,
        reconstruction_state=reconstruction_state,
        transfer_state=transfer_state,
        false_fluency_risk=false_fluency_risk,
        superficial_signal=superficial_signal,
    )
    overall_state = _overall_state(
        evidence_level=evidence_level,
        durability_state=durability_state,
        resurfacing_state=resurfacing_state,
        recovery_state=recovery_state,
        reconstruction_state=reconstruction_state,
        transfer_state=transfer_state,
        false_fluency_risk=false_fluency_risk,
        superficial_signal=superficial_signal,
    )
    summary = _summary(overall_state)
    overall_reasoning = state_reasoning(
        "Retencao longitudinal",
        overall_state,
        [
            f"Evidencia={evidence_level}; durability={durability_state}; resurfacing={resurfacing_state}; recovery={recovery_state}.",
            f"Reconstruction={reconstruction_state}; transfer={transfer_state}; false_fluency={false_fluency_risk:.2f}.",
        ],
    )
    signal_profile = RetentionSignalProfile(
        retention_durability_state=durability_state,
        retention_durability_signal=round(durability_signal, 4),
        resurfacing_effectiveness_state=resurfacing_state,
        resurfacing_effectiveness_signal=round(resurfacing_signal, 4),
        reconstruction_retention_state=reconstruction_state,
        reconstruction_retention_signal=round(reconstruction_signal, 4),
        transfer_retention_state=transfer_state,
        transfer_retention_signal=round(transfer_signal, 4),
    )
    recovery_profile = RetentionRecoveryProfile(
        recovery_state=recovery_state,
        recovery_signal=round(recovery_signal, 4),
        recovery_reasoning=recovery_reasoning,
    )
    risk_profile = RetentionRiskProfile(
        false_fluency_retention_risk=round(false_fluency_risk, 4),
        superficial_stability_signal=round(superficial_signal, 4),
        retention_risk_flags=risk_flags,
    )
    stability_summary = RetentionStabilitySummary(
        longitudinal_retention_state=overall_state,
        longitudinal_retention_summary=summary,
        longitudinal_retention_reasoning=overall_reasoning,
        retention_evidence_level=evidence_level,
        retention_confidence_indicator=round(retention_confidence, 4),
        why_this_retention_state=_why(overall_state),
    )
    observability_summary = RetentionObservabilitySummary(
        reconstruction_retention_reasoning=reconstruction_reasoning,
        transfer_retention_reasoning=transfer_reasoning,
        retention_durability_reasoning=durability_reasoning,
    )
    return LongitudinalRetentionProfile(
        longitudinal_retention_state=overall_state,
        longitudinal_retention_summary=summary,
        longitudinal_retention_reasoning=overall_reasoning,
        retention_durability_state=durability_state,
        retention_durability_signal=round(durability_signal, 4),
        resurfacing_effectiveness_state=resurfacing_state,
        resurfacing_effectiveness_signal=round(resurfacing_signal, 4),
        recovery_state=recovery_state,
        recovery_signal=round(recovery_signal, 4),
        recovery_reasoning=recovery_reasoning,
        reconstruction_retention_state=reconstruction_state,
        reconstruction_retention_signal=round(reconstruction_signal, 4),
        reconstruction_retention_reasoning=reconstruction_reasoning,
        transfer_retention_state=transfer_state,
        transfer_retention_signal=round(transfer_signal, 4),
        transfer_retention_reasoning=transfer_reasoning,
        false_fluency_retention_risk=round(false_fluency_risk, 4),
        superficial_stability_signal=round(superficial_signal, 4),
        retention_risk_flags=risk_flags,
        retention_evidence_level=evidence_level,
        retention_confidence_indicator=round(retention_confidence, 4),
        retention_signal_profile=signal_profile,
        retention_recovery_profile=recovery_profile,
        retention_risk_profile=risk_profile,
        retention_stability_summary=stability_summary,
        retention_observability_summary=observability_summary,
        why_this_retention_state=_why(overall_state),
    )


def _normalize_progress(progress: ProgressState | dict | None) -> ProgressState:
    if isinstance(progress, ProgressState):
        return progress
    if progress is None:
        return ProgressState()
    return ProgressState.model_validate(progress)


def _selected_microtopic_id(block: dict[str, object]) -> str:
    selected = list(block.get("selected_microtopics") or [])
    if not selected:
        return ""
    first = dict(selected[0] or {})
    return str(first.get("id") or "")


def _latest_microtopic_id(progress: ProgressState) -> str:
    if progress.microtopic_performance:
        ranked = sorted(
            progress.microtopic_performance.items(),
            key=lambda item: (
                item[1].last_reviewed_at or item[1].last_seen_at or datetime.min.replace(tzinfo=timezone.utc),
                item[1].total_questions,
                item[0],
            ),
        )
        return ranked[-1][0]
    if progress.pedagogical_memory:
        return sorted(progress.pedagogical_memory)[0]
    return ""


def _performance_for_microtopic(
    progress: ProgressState,
    microtopic_id: str,
) -> MicroTopicPerformance:
    performance = progress.microtopic_performance.get(microtopic_id)
    if performance is not None:
        return performance.model_copy(deep=True)
    return MicroTopicPerformance()


def _memory_for_microtopic(
    progress: ProgressState,
    microtopic_id: str,
    topic_id: str | None,
) -> PedagogicalMemory:
    memory = progress.pedagogical_memory.get(microtopic_id)
    if memory is not None:
        return memory.model_copy(deep=True)
    return PedagogicalMemory(microtopic_id=microtopic_id or None, topic_id=topic_id)


def _evidence_level(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
) -> str:
    evidence_score = average_values(
        [
            min(performance.total_questions / 10.0, 1.0),
            min(memory.resurfacing_cycles / 4.0, 1.0),
            1.0 if (performance.last_reviewed_at or performance.last_seen_at or memory.last_stabilized_at) else 0.0,
            block.get("validation_confidence"),
        ]
    )
    if evidence_score >= 0.7:
        return "high"
    if evidence_score >= 0.4:
        return "medium"
    if evidence_score > 0.0:
        return "low"
    return "insufficient"


def _resurfacing_pressure(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
) -> float:
    return average_values(
        [
            block.get("forgetting_signal"),
            min(performance.recent_errors * 0.2, 1.0),
            1.0 - memory.retrieval_success_trend,
            0.3 if memory.resurfacing_cycles > memory.successful_resurfacing_cycles else 0.0,
        ]
    )


def _resurfacing_observation(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
) -> tuple[str, float, list[str]]:
    cycles = int(memory.resurfacing_cycles or 0)
    successful_cycles = int(memory.successful_resurfacing_cycles or 0)
    if cycles <= 0:
        return (
            "not_enough_cycles",
            0.0,
            state_reasoning("Resurfacing", "not_enough_cycles", ["Nenhum ciclo longitudinal de resurfacing foi observado."]),
        )
    success_ratio = successful_cycles / max(cycles, 1)
    signal = average_values(
        [
            block.get("resurfacing_effectiveness_signal"),
            success_ratio,
            block.get("validation_confidence"),
            min(max(performance.consecutive_correct, 0) / 4.0, 1.0),
            1.0 - min(max(performance.consecutive_incorrect, 0) / 3.0, 1.0),
        ]
    )
    if cycles < 2:
        state = "not_enough_cycles"
    elif signal >= 0.68 and success_ratio >= 0.6:
        state = "effective"
    elif signal <= 0.34 or success_ratio <= 0.34:
        state = "ineffective"
    else:
        state = "inconclusive"
    return (
        state,
        signal,
        state_reasoning(
            "Resurfacing",
            state,
            [f"Cycles={cycles}; success_ratio={success_ratio:.2f}; signal={signal:.2f}."],
        ),
    )


def _recovery_observation(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
    stability: dict[str, object],
) -> tuple[str, float, list[str]]:
    recovered_after_error = _is_after(performance.last_correct_at, performance.last_incorrect_at)
    signal = average_values(
        [
            block.get("recovery_signal"),
            stability.get("recovery_signal"),
            min(memory.recovery_count / 3.0, 1.0),
            min(max(performance.consecutive_correct - 1, 0) / 3.0, 1.0),
            1.0 if recovered_after_error else 0.0,
            1.0 - min(max(performance.recent_errors, 0) / 3.0, 1.0),
        ]
    )
    if (
        memory.recovery_count == 0
        and performance.last_incorrect_at is None
        and performance.last_correct_at is None
        and performance.recent_errors == 0
    ):
        state = "recovery_insufficient_evidence"
    elif signal >= 0.58 and (recovered_after_error or memory.recovery_count >= 1):
        state = "recovery_improving"
    elif signal <= 0.34 and (performance.recent_errors > 0 or performance.consecutive_incorrect > 0):
        state = "recovery_unstable"
    elif memory.recovery_count > 0:
        state = "recovery_stalled"
    else:
        state = "recovery_insufficient_evidence"
    return (
        state,
        signal,
        state_reasoning(
            "Recuperacao",
            state,
            [
                f"Recovery_count={memory.recovery_count}; recovered_after_error={recovered_after_error}; signal={signal:.2f}.",
            ],
        ),
    )


def _reconstruction_observation(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
) -> tuple[str, float, list[str]]:
    fragility = clamp_value(block.get("reconstruction_fragility", 0.0))
    progress_signal = clamp_value(block.get("reconstruction_progress_signal", 0.0))
    signal = average_values(
        [
            1.0 - fragility,
            progress_signal,
            block.get("validation_confidence"),
            block.get("longitudinal_consistency"),
            1.0 - min(max(performance.recent_errors, 0) / 4.0, 1.0),
        ]
    )
    if performance.total_questions <= 0 and fragility == 0.0 and progress_signal == 0.0:
        state = "reconstruction_insufficient_evidence"
    elif fragility >= 0.62 or signal <= 0.34:
        state = "reconstruction_fragile"
    elif signal >= 0.72 and fragility <= 0.24:
        state = "reconstruction_durable"
    else:
        state = "reconstruction_improving"
    return (
        state,
        signal,
        state_reasoning(
            "Reconstrucao",
            state,
            [f"Fragility={fragility:.2f}; progress={progress_signal:.2f}; signal={signal:.2f}."],
        ),
    )


def _transfer_observation(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
) -> tuple[str, float, list[str]]:
    fragility = clamp_value(block.get("transfer_fragility", 0.0))
    stability_signal = clamp_value(block.get("transfer_stability_signal", 0.0))
    signal = average_values(
        [
            1.0 - fragility,
            stability_signal,
            block.get("validation_confidence"),
            block.get("longitudinal_consistency"),
            memory.retrieval_success_trend,
        ]
    )
    if performance.total_questions <= 0 and fragility == 0.0 and stability_signal == 0.0:
        state = "transfer_insufficient_evidence"
    elif fragility >= 0.62 or signal <= 0.34:
        state = "transfer_fragile"
    elif signal >= 0.72 and fragility <= 0.24:
        state = "transfer_durable"
    else:
        state = "transfer_improving"
    return (
        state,
        signal,
        state_reasoning(
            "Transferencia",
            state,
            [f"Fragility={fragility:.2f}; stability={stability_signal:.2f}; signal={signal:.2f}."],
        ),
    )


def _false_fluency_observation(
    performance: MicroTopicPerformance,
    memory: PedagogicalMemory,
    block: dict[str, object],
    retention_confidence: float,
    resurfacing_signal: float,
    reconstruction_signal: float,
    transfer_signal: float,
) -> tuple[float, float]:
    recognition_strength = average_values(
        [
            retention_confidence,
            min(max(performance.consecutive_correct, 0) / 4.0, 1.0),
            memory.retrieval_success_trend,
        ]
    )
    validation_signal = clamp_value(block.get("validation_confidence", 0.0))
    fragility_pressure = clamp_value(
        clamp_value(block.get("false_fluency_signal", 0.0)) * 0.34
        + clamp_value(block.get("false_fluency_risk", 0.0)) * 0.26
        + max(0.0, 0.58 - resurfacing_signal) * 0.18
        + max(0.0, 0.58 - reconstruction_signal) * 0.12
        + max(0.0, 0.58 - transfer_signal) * 0.12
        + max(0.0, 0.55 - validation_signal) * 0.12
    )
    superficial_signal = clamp_value(
        fragility_pressure
        + max(0.0, recognition_strength - 0.68) * 0.18
    )
    return max(clamp_value(block.get("false_fluency_risk", 0.0)), superficial_signal), superficial_signal


def _durability_observation(
    *,
    evidence_level: str,
    block: dict[str, object],
    stability: dict[str, object],
    retention_confidence: float,
    resurfacing_signal: float,
    recovery_signal: float,
    reconstruction_signal: float,
    transfer_signal: float,
    false_fluency_risk: float,
    superficial_signal: float,
) -> tuple[str, float, list[str]]:
    if evidence_level == "insufficient":
        return (
            "insufficient_evidence",
            0.0,
            state_reasoning("Durabilidade", "insufficient_evidence", ["Nao havia evidencia longitudinal suficiente."]),
        )
    stability_signal = average_values(
        [
            block.get("pedagogical_stability_score"),
            stability.get("pedagogical_stability_score"),
            block.get("stabilization_quality_signal"),
            block.get("longitudinal_validation_signal"),
        ]
    )
    signal = clamp_value(
        average_values(
            [
                retention_confidence,
                resurfacing_signal,
                recovery_signal,
                reconstruction_signal,
                transfer_signal,
                stability_signal,
            ]
        )
        - false_fluency_risk * 0.18
        - superficial_signal * 0.12
    )
    if superficial_signal >= 0.62 or false_fluency_risk >= 0.62:
        state = "superficial"
    elif signal >= 0.72 and evidence_level in {"medium", "high"}:
        state = "durable"
    elif signal >= 0.5:
        state = "emerging"
    else:
        state = "unstable"
    return (
        state,
        signal,
        state_reasoning(
            "Durabilidade",
            state,
            [f"Evidence={evidence_level}; confidence={retention_confidence:.2f}; signal={signal:.2f}."],
        ),
    )


def _risk_flags(
    *,
    evidence_level: str,
    resurfacing_state: str,
    recovery_state: str,
    reconstruction_state: str,
    transfer_state: str,
    false_fluency_risk: float,
    superficial_signal: float,
) -> list[str]:
    flags: list[str] = []
    if false_fluency_risk >= 0.55:
        flags.append("false_fluency_risk")
    if resurfacing_state == "ineffective":
        flags.append("resurfacing_failure_risk")
    if reconstruction_state == "reconstruction_fragile":
        flags.append("reconstruction_decay_risk")
    if transfer_state == "transfer_fragile":
        flags.append("transfer_decay_risk")
    if recovery_state in {"recovery_unstable", "recovery_stalled"}:
        flags.append("unstable_recovery_risk")
    if superficial_signal >= 0.55:
        flags.append("superficial_stabilization_risk")
    if evidence_level in {"insufficient", "low"}:
        flags.append("insufficient_longitudinal_evidence")
    return sorted(set(flags))


def _overall_state(
    *,
    evidence_level: str,
    durability_state: str,
    resurfacing_state: str,
    recovery_state: str,
    reconstruction_state: str,
    transfer_state: str,
    false_fluency_risk: float,
    superficial_signal: float,
) -> str:
    if evidence_level == "insufficient":
        return "retention_insufficient_evidence"
    if evidence_level == "low" and durability_state != "superficial":
        return "retention_inconclusive"
    if durability_state == "superficial" or false_fluency_risk >= 0.62 or superficial_signal >= 0.62:
        return "retention_superficial"
    if durability_state == "durable" and reconstruction_state != "reconstruction_fragile" and transfer_state != "transfer_fragile":
        return "retention_sustainable"
    if any(
        state in {"ineffective", "recovery_unstable", "reconstruction_fragile", "transfer_fragile", "unstable"}
        for state in [resurfacing_state, recovery_state, reconstruction_state, transfer_state, durability_state]
    ):
        return "retention_fragile"
    if durability_state == "emerging":
        return "retention_emerging"
    return "retention_inconclusive"


def _summary(state: str) -> str:
    return state_message(
        state,
        {
            "retention_sustainable": "Longitudinal retention appears sustainable across resurfacing, recovery and validation signals.",
            "retention_emerging": "Longitudinal retention appears to be emerging but still needs more repeated evidence.",
            "retention_fragile": "Longitudinal retention shows fragility across one or more durability dimensions.",
            "retention_superficial": "Longitudinal retention looks superficially stable but still carries false-fluency pressure.",
            "retention_inconclusive": "Longitudinal retention remained inconclusive with the available evidence.",
            "retention_insufficient_evidence": "Longitudinal retention does not yet have enough evidence for reliable observation.",
        },
        "Longitudinal retention remained observationally neutral.",
    )


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "retention_sustainable": "Repeated exposure, resurfacing and validation signals stayed aligned without strong fragility pressure.",
            "retention_emerging": "Some durability signals are improving, but longitudinal evidence is still moderate.",
            "retention_fragile": "One or more signals suggest decay, weak transfer, weak reconstruction or unstable recovery.",
            "retention_superficial": "Apparent success remained ahead of resurfacing, reconstruction or transfer durability.",
            "retention_inconclusive": "Available longitudinal evidence was mixed and did not support a clear retention reading.",
            "retention_insufficient_evidence": "The runtime did not have enough repeated exposure data to support longitudinal observation.",
        },
        "Longitudinal retention remains observational only.",
    )


def _is_after(later: datetime | str | None, earlier: datetime | str | None) -> bool:
    later_dt = _to_datetime(later)
    earlier_dt = _to_datetime(earlier)
    if later_dt is None or earlier_dt is None:
        return False
    return later_dt > earlier_dt


def _to_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
