from __future__ import annotations

from app.domain.models import (
    CognitiveTrajectory,
    ConsolidationState,
    FacetTrajectory,
    TrajectorySignal,
)


def analyze_cognitive_trajectory(
    *,
    performance: dict[str, object] | None,
    pedagogical_memory: dict[str, object] | None,
    facet_profile: dict[str, object] | object | None,
) -> CognitiveTrajectory:
    normalized_performance = _normalize_performance(performance)
    normalized_memory = _normalize_memory(pedagogical_memory)
    normalized_facet = _normalize_facet_profile(facet_profile)

    consecutive_correct = normalized_performance["consecutive_correct"]
    consecutive_incorrect = normalized_performance["consecutive_incorrect"]
    recent_errors = normalized_performance["recent_errors"]
    resurfacing_cycles = normalized_memory["resurfacing_cycles"]
    successful_cycles = normalized_memory["successful_resurfacing_cycles"]
    resurfacing_success = successful_cycles / max(resurfacing_cycles, 1)
    retrieval_trend = normalized_memory["retrieval_success_trend"]
    stabilization_level = normalized_memory["stabilization_level"]
    fatigue_exposure = normalized_memory["fatigue_exposure"]
    recent_effectiveness = normalized_memory["recent_effectiveness"]

    stabilization_quality = _clamp(
        stabilization_level * 0.34
        + retrieval_trend * 0.2
        + resurfacing_success * 0.22
        + min(consecutive_correct / 5.0, 1.0) * 0.14
        - min(consecutive_incorrect / 4.0, 1.0) * 0.1
        - min(recent_errors / 3.0, 1.0) * 0.08
    )
    longitudinal_consistency = _clamp(
        resurfacing_success * 0.42
        + retrieval_trend * 0.26
        + stabilization_level * 0.18
        + min(normalized_memory["consecutive_successes"] / 4.0, 1.0) * 0.1
        - fatigue_exposure * 0.08
    )
    false_fluency_signal = _clamp(
        normalized_facet["recognition_signal"] * 0.42
        + min(consecutive_correct / 4.0, 1.0) * 0.18
        + max(0.0, 0.55 - resurfacing_success) * 0.28
        + max(0.0, 0.52 - longitudinal_consistency) * 0.18
        - min(consecutive_incorrect / 4.0, 1.0) * 0.08
    )
    reconstruction_fragility = _clamp(
        normalized_facet["reconstruction_signal"] * 0.48
        + min(consecutive_incorrect / 4.0, 1.0) * 0.2
        + min(recent_errors / 3.0, 1.0) * 0.12
        + (0.16 if recent_effectiveness == "ineffective" else 0.0)
        - min(consecutive_correct / 5.0, 1.0) * 0.08
    )
    transfer_fragility = _clamp(
        normalized_facet["transfer_signal"] * 0.48
        + max(0.0, 0.6 - resurfacing_success) * 0.2
        + min(recent_errors / 3.0, 1.0) * 0.12
        + (0.14 if recent_effectiveness == "ineffective" else 0.0)
        - min(consecutive_correct / 5.0, 1.0) * 0.08
    )

    state = _resolve_state(
        dominant_facet=normalized_facet["dominant_facet"],
        consecutive_correct=consecutive_correct,
        consecutive_incorrect=consecutive_incorrect,
        stabilization_quality=stabilization_quality,
        longitudinal_consistency=longitudinal_consistency,
        false_fluency_signal=false_fluency_signal,
        reconstruction_fragility=reconstruction_fragility,
        transfer_fragility=transfer_fragility,
    )
    support_reason = _trajectory_support_reason(
        dominant_facet=normalized_facet["dominant_facet"],
        state=state,
    )
    reasoning = _trajectory_reasoning(
        state=state,
        stabilization_quality=stabilization_quality,
        longitudinal_consistency=longitudinal_consistency,
        false_fluency_signal=false_fluency_signal,
        reconstruction_fragility=reconstruction_fragility,
        transfer_fragility=transfer_fragility,
    )
    return CognitiveTrajectory(
        cognitive_trajectory=state.value,
        trajectory_state=state.value,
        trajectory_reasoning=reasoning,
        consolidation_state=state.value,
        stabilization_quality=round(stabilization_quality, 4),
        false_fluency_signal=round(false_fluency_signal, 4),
        reconstruction_fragility=round(reconstruction_fragility, 4),
        transfer_fragility=round(transfer_fragility, 4),
        longitudinal_consistency=round(longitudinal_consistency, 4),
        why_this_trajectory_now=_why_this_now(state),
        trajectory_support_reason=support_reason,
        trajectory_signal=TrajectorySignal(
            stabilization_quality=round(stabilization_quality, 4),
            false_fluency_signal=round(false_fluency_signal, 4),
            reconstruction_fragility=round(reconstruction_fragility, 4),
            transfer_fragility=round(transfer_fragility, 4),
            longitudinal_consistency=round(longitudinal_consistency, 4),
        ),
        facet_trajectories=_facet_trajectories(
            normalized_facet=normalized_facet,
            state=state,
            false_fluency_signal=false_fluency_signal,
            reconstruction_fragility=reconstruction_fragility,
            transfer_fragility=transfer_fragility,
            stabilization_quality=stabilization_quality,
        ),
    )


def _resolve_state(
    *,
    dominant_facet: str | None,
    consecutive_correct: int,
    consecutive_incorrect: int,
    stabilization_quality: float,
    longitudinal_consistency: float,
    false_fluency_signal: float,
    reconstruction_fragility: float,
    transfer_fragility: float,
) -> ConsolidationState:
    if dominant_facet == "contextual_transfer" and transfer_fragility >= 0.54:
        return ConsolidationState.TRANSFER_FRAGILE
    if dominant_facet == "reconstruction" and reconstruction_fragility >= 0.52:
        return ConsolidationState.RECONSTRUCTION_FRAGILE
    if false_fluency_signal >= 0.52 and consecutive_correct >= 2 and longitudinal_consistency < 0.5:
        return ConsolidationState.SUPERFICIALLY_STABLE
    if stabilization_quality >= 0.72 and longitudinal_consistency >= 0.62:
        return ConsolidationState.CONSOLIDATED
    if consecutive_incorrect >= 2 or stabilization_quality <= 0.3:
        return ConsolidationState.UNSTABLE
    if stabilization_quality >= 0.5:
        return ConsolidationState.STABILIZING
    return ConsolidationState.EMERGING


def _facet_trajectories(
    *,
    normalized_facet: dict[str, object],
    state: ConsolidationState,
    false_fluency_signal: float,
    reconstruction_fragility: float,
    transfer_fragility: float,
    stabilization_quality: float,
) -> list[FacetTrajectory]:
    dominant = str(normalized_facet["dominant_facet"] or "definition")
    trajectories = [
        FacetTrajectory(
            facet_type=dominant,
            consolidation_state=state.value,
            strength=round(
                _clamp(
                    max(
                        stabilization_quality,
                        false_fluency_signal,
                        reconstruction_fragility,
                        transfer_fragility,
                    )
                ),
                4,
            ),
            reason=f"Faceta dominante acompanhada longitudinalmente como {state.value}.",
        )
    ]
    if normalized_facet["recognition_signal"] >= 0.35 and dominant != "recognition":
        trajectories.append(
            FacetTrajectory(
                facet_type="recognition",
                consolidation_state=(
                    ConsolidationState.SUPERFICIALLY_STABLE.value
                    if false_fluency_signal >= 0.45
                    else ConsolidationState.STABILIZING.value
                ),
                strength=round(normalized_facet["recognition_signal"], 4),
                reason="Reconhecimento monitorado separadamente para evitar falsa fluencia.",
            )
        )
    if normalized_facet["reconstruction_signal"] >= 0.35 and dominant != "reconstruction":
        trajectories.append(
            FacetTrajectory(
                facet_type="reconstruction",
                consolidation_state=(
                    ConsolidationState.RECONSTRUCTION_FRAGILE.value
                    if reconstruction_fragility >= 0.45
                    else ConsolidationState.STABILIZING.value
                ),
                strength=round(normalized_facet["reconstruction_signal"], 4),
                reason="Reconstrucao acompanhada separadamente para evitar estabilidade superficial.",
            )
        )
    return trajectories[:3]


def _trajectory_reasoning(
    *,
    state: ConsolidationState,
    stabilization_quality: float,
    longitudinal_consistency: float,
    false_fluency_signal: float,
    reconstruction_fragility: float,
    transfer_fragility: float,
) -> list[str]:
    reasoning = [f"Estado longitudinal atual: {state.value}."]
    reasoning.append(f"Qualidade de estabilizacao: {stabilization_quality:.2f}.")
    reasoning.append(f"Consistencia longitudinal: {longitudinal_consistency:.2f}.")
    if false_fluency_signal >= 0.42:
        reasoning.append("Ha indicio de fluencia superficial acima do ideal.")
    if reconstruction_fragility >= 0.42:
        reasoning.append("A reconstrucao ainda oscila mais do que o reconhecimento.")
    if transfer_fragility >= 0.42:
        reasoning.append("A transferencia contextual segue mais fragil do que a base conceitual.")
    return reasoning


def _why_this_now(state: ConsolidationState) -> str:
    mapping = {
        ConsolidationState.EMERGING: "A consolidacao ainda e inicial e precisa de leitura cuidadosa.",
        ConsolidationState.STABILIZING: "O conceito mostra progresso, mas ainda nao estabilizou de forma duravel.",
        ConsolidationState.UNSTABLE: "O comportamento recente ainda e instavel e pede apoio adicional.",
        ConsolidationState.SUPERFICIALLY_STABLE: "O sucesso recente parece rapido demais para relaxar a intervencao.",
        ConsolidationState.CONSOLIDATED: "A consolidacao longitudinal ja permite manutencao mais leve.",
        ConsolidationState.TRANSFER_FRAGILE: "A transferencia entre contextos ainda colapsa com facilidade.",
        ConsolidationState.RECONSTRUCTION_FRAGILE: "A reconstrucao do raciocinio ainda precisa de apoio mais claro.",
    }
    return mapping[state]


def _trajectory_support_reason(*, dominant_facet: str | None, state: ConsolidationState) -> str | None:
    if state == ConsolidationState.SUPERFICIALLY_STABLE and dominant_facet == "recognition":
        return "O reconhecimento estabilizou antes da reconstrucao e merece checagem mais cuidadosa."
    if state == ConsolidationState.TRANSFER_FRAGILE:
        return "A transferencia contextual continua precisando de ponte explicita entre cenarios."
    if state == ConsolidationState.RECONSTRUCTION_FRAGILE:
        return "A reconstrucao ainda pede encadeamento mais guiado antes de reduzir suporte."
    return None


def _normalize_performance(performance: dict[str, object] | None) -> dict[str, object]:
    source = dict(performance or {})
    return {
        "consecutive_correct": int(source.get("consecutive_correct", 0) or 0),
        "consecutive_incorrect": int(source.get("consecutive_incorrect", 0) or 0),
        "recent_errors": int(source.get("recent_errors", 0) or 0),
    }


def _normalize_memory(memory: dict[str, object] | None) -> dict[str, object]:
    source = dict(memory or {})
    return {
        "recent_effectiveness": str(source.get("recent_effectiveness", "neutral") or "neutral"),
        "consecutive_successes": int(source.get("consecutive_successes", 0) or 0),
        "resurfacing_cycles": int(source.get("resurfacing_cycles", 0) or 0),
        "successful_resurfacing_cycles": int(source.get("successful_resurfacing_cycles", 0) or 0),
        "stabilization_level": _clamp(source.get("stabilization_level", 0.0) or 0.0),
        "retrieval_success_trend": _clamp(source.get("retrieval_success_trend", 0.5) or 0.5),
        "fatigue_exposure": _clamp(source.get("fatigue_exposure", 0.0) or 0.0),
    }


def _normalize_facet_profile(facet_profile: dict[str, object] | object | None) -> dict[str, object]:
    if hasattr(facet_profile, "model_dump"):
        source = facet_profile.model_dump(mode="json")
    elif isinstance(facet_profile, dict):
        source = dict(facet_profile)
    else:
        source = {}
    return {
        "dominant_facet": str(source.get("dominant_facet") or "") or None,
        "recognition_signal": _clamp(source.get("recognition_signal", 0.0) or 0.0),
        "reconstruction_signal": _clamp(source.get("reconstruction_signal", 0.0) or 0.0),
        "transfer_signal": _clamp(source.get("transfer_signal", 0.0) or 0.0),
    }


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
