from __future__ import annotations

from app.domain.models import PedagogicalMode, PedagogicalOutcome, PedagogicalProfile


ERROR_TYPE_PRIORITY = ["conceptual", "interpretation", "memory", "attention"]
CURRICULUM_DENSITY = {
    "active": 1.0,
    "cumulative": 0.4,
}
REVIEW_DENSITY = {
    "deep": 1.0,
    "medium": 0.65,
    "light": 0.35,
}


def resolve_pedagogical_profile(
    *,
    curriculum_role: str | None,
    review_intensity: str | None,
    weakness_signal: float,
    resurfacing_signal: float,
    performance: dict[str, object] | None,
    pedagogical_memory: dict[str, object] | None = None,
) -> PedagogicalProfile:
    normalized_performance = _normalize_performance(performance)
    normalized_memory = _normalize_pedagogical_memory(pedagogical_memory)
    normalized_weakness = _clamp(weakness_signal)
    normalized_resurfacing = _clamp(resurfacing_signal)
    stabilization_signal = _clamp(
        max(
            normalized_performance["consecutive_correct"] / 5.0,
            normalized_memory["stabilization_level"],
            normalized_memory["consecutive_successes"] / 4.0,
        )
    )
    incorrect_pressure = _clamp(
        max(
            normalized_performance["consecutive_incorrect"] / 4.0,
            normalized_memory["escalation_level"],
            normalized_memory["consecutive_failures"] / 3.0,
        )
    )
    curriculum_density = CURRICULUM_DENSITY.get(curriculum_role or "", 0.6)
    review_density = REVIEW_DENSITY.get(review_intensity or "", 0.5)
    dominant_error_type = _dominant_error_type(normalized_performance["error_distribution"])
    escalation_signal = _clamp(
        max(
            incorrect_pressure,
            normalized_memory["escalation_level"],
            (1.0 - normalized_memory["retrieval_success_trend"]) * 0.5,
        )
    )
    base_mode = compute_pedagogical_mode(
        dominant_error_type=dominant_error_type,
        curriculum_role=curriculum_role,
        review_intensity=review_intensity,
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
        stabilization_signal=stabilization_signal,
        incorrect_pressure=incorrect_pressure,
    )
    pedagogical_mode, transition_reason = _apply_pedagogical_memory_transition(
        base_mode=base_mode,
        dominant_error_type=dominant_error_type,
        curriculum_role=curriculum_role,
        review_intensity=review_intensity,
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
        stabilization_signal=stabilization_signal,
        escalation_signal=escalation_signal,
        pedagogical_memory=normalized_memory,
    )

    breakdown = {
        "weakness_signal": normalized_weakness,
        "resurfacing_signal": normalized_resurfacing,
        "stabilization_signal": stabilization_signal,
        "incorrect_pressure": incorrect_pressure,
        "escalation_signal": escalation_signal,
        "curriculum_density": curriculum_density,
        "review_density": review_density,
        "retrieval_trend": normalized_memory["retrieval_success_trend"],
    }

    explanation_depth = compute_explanation_depth(
        pedagogical_mode=pedagogical_mode,
        review_intensity=review_intensity,
        weakness_signal=normalized_weakness,
        incorrect_pressure=incorrect_pressure,
    )
    retrieval_intensity = compute_retrieval_intensity(
        pedagogical_mode=pedagogical_mode,
        review_intensity=review_intensity,
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
    )
    reinforcement_level = _compute_reinforcement_level(
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
        stabilization_signal=stabilization_signal,
        incorrect_pressure=incorrect_pressure,
    )
    cognitive_load = _compute_cognitive_load(
        curriculum_density=curriculum_density,
        review_density=review_density,
        pedagogical_mode=pedagogical_mode,
    )
    chosen_history = normalized_memory["intervention_history"].get(
        pedagogical_mode.value,
        {},
    )
    pedagogical_confidence = _clamp(
        chosen_history.get("confidence", 0.5) * 0.7
        + stabilization_signal * 0.2
        + (1.0 - escalation_signal) * 0.1
    )
    intervention_effectiveness = normalized_memory["recent_effectiveness"]
    pedagogical_stability = _pedagogical_stability(
        stabilization_signal=stabilization_signal,
        escalation_signal=escalation_signal,
    )
    adaptation_reasoning = _build_adaptation_reasoning(
        pedagogical_mode=pedagogical_mode,
        transition_reason=transition_reason,
        intervention_effectiveness=intervention_effectiveness,
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
    )

    return PedagogicalProfile(
        pedagogical_mode=pedagogical_mode.value,
        intervention_reason=_build_intervention_reason(
            pedagogical_mode=pedagogical_mode,
            dominant_error_type=dominant_error_type,
            curriculum_role=curriculum_role,
            review_intensity=review_intensity,
            weakness_signal=normalized_weakness,
            resurfacing_signal=normalized_resurfacing,
        ),
        explanation_depth=explanation_depth,
        retrieval_intensity=retrieval_intensity,
        reinforcement_level=reinforcement_level,
        cognitive_load=cognitive_load,
        intervention_transition_reason=transition_reason,
        stabilization_signal=stabilization_signal,
        escalation_signal=escalation_signal,
        pedagogical_confidence=pedagogical_confidence,
        intervention_effectiveness=intervention_effectiveness,
        pedagogical_stability=pedagogical_stability,
        adaptation_reasoning=adaptation_reasoning,
        intervention_history_summary={
            "last_mode": normalized_memory["last_pedagogical_mode"],
            "known_modes": len(normalized_memory["intervention_history"]),
            "recent_effectiveness": intervention_effectiveness,
            "consecutive_successes": normalized_memory["consecutive_successes"],
            "consecutive_failures": normalized_memory["consecutive_failures"],
        },
        profile_breakdown=breakdown,
    )


def compute_pedagogical_mode(
    *,
    dominant_error_type: str | None,
    curriculum_role: str | None,
    review_intensity: str | None,
    weakness_signal: float,
    resurfacing_signal: float,
    stabilization_signal: float,
    incorrect_pressure: float,
) -> PedagogicalMode:
    if stabilization_signal >= 0.8 and weakness_signal <= 0.25 and incorrect_pressure <= 0.1:
        return PedagogicalMode.REINFORCEMENT_CHECK

    if (
        dominant_error_type == "conceptual"
        and (weakness_signal >= 0.45 or incorrect_pressure >= 0.4)
    ):
        if curriculum_role == "active" or review_intensity == "deep":
            return PedagogicalMode.GUIDED_EXPLANATION
        return PedagogicalMode.CONCEPTUAL_REINFORCEMENT

    if dominant_error_type == "interpretation" and (weakness_signal >= 0.3 or incorrect_pressure >= 0.25):
        return PedagogicalMode.CONTEXTUAL_APPLICATION

    if dominant_error_type == "memory" and (weakness_signal >= 0.2 or resurfacing_signal >= 0.25):
        return PedagogicalMode.ACTIVE_RECALL

    if dominant_error_type == "attention" and weakness_signal >= 0.15:
        return PedagogicalMode.RAPID_REVIEW

    if curriculum_role == "cumulative" and resurfacing_signal >= 0.65:
        return PedagogicalMode.ACTIVE_RECALL

    if (
        curriculum_role == "cumulative"
        and review_intensity == "light"
        and incorrect_pressure <= 0.1
        and weakness_signal <= 0.5
    ):
        return PedagogicalMode.RAPID_REVIEW

    if weakness_signal >= 0.6 and curriculum_role == "active":
        return PedagogicalMode.GUIDED_EXPLANATION

    if weakness_signal >= 0.45:
        return PedagogicalMode.CONCEPTUAL_REINFORCEMENT

    if curriculum_role == "cumulative":
        return PedagogicalMode.RAPID_REVIEW

    return PedagogicalMode.REINFORCEMENT_CHECK


def compute_explanation_depth(
    *,
    pedagogical_mode: PedagogicalMode,
    review_intensity: str | None,
    weakness_signal: float,
    incorrect_pressure: float,
) -> str:
    if pedagogical_mode == PedagogicalMode.GUIDED_EXPLANATION:
        return "deep"
    if pedagogical_mode == PedagogicalMode.CONCEPTUAL_REINFORCEMENT:
        return "deep" if weakness_signal >= 0.7 or review_intensity == "deep" else "medium"
    if pedagogical_mode == PedagogicalMode.CONTEXTUAL_APPLICATION:
        return "medium"
    if pedagogical_mode == PedagogicalMode.ACTIVE_RECALL:
        return "medium" if weakness_signal >= 0.7 or incorrect_pressure >= 0.75 else "light"
    return "light"


def compute_retrieval_intensity(
    *,
    pedagogical_mode: PedagogicalMode,
    review_intensity: str | None,
    weakness_signal: float,
    resurfacing_signal: float,
) -> str:
    if pedagogical_mode == PedagogicalMode.ACTIVE_RECALL:
        return "high"
    if pedagogical_mode == PedagogicalMode.CONTEXTUAL_APPLICATION:
        return "high" if review_intensity == "deep" or weakness_signal >= 0.7 else "medium"
    if pedagogical_mode in {PedagogicalMode.GUIDED_EXPLANATION, PedagogicalMode.CONCEPTUAL_REINFORCEMENT}:
        return "medium"
    if pedagogical_mode == PedagogicalMode.RAPID_REVIEW:
        return "medium" if resurfacing_signal >= 0.45 else "low"
    return "low"


def _apply_pedagogical_memory_transition(
    *,
    base_mode: PedagogicalMode,
    dominant_error_type: str | None,
    curriculum_role: str | None,
    review_intensity: str | None,
    weakness_signal: float,
    resurfacing_signal: float,
    stabilization_signal: float,
    escalation_signal: float,
    pedagogical_memory: dict[str, object],
) -> tuple[PedagogicalMode, str | None]:
    last_mode = pedagogical_memory.get("last_pedagogical_mode")
    effectiveness = pedagogical_memory.get("recent_effectiveness", PedagogicalOutcome.NEUTRAL.value)

    if (
        last_mode == PedagogicalMode.ACTIVE_RECALL.value
        and effectiveness == PedagogicalOutcome.INEFFECTIVE.value
        and escalation_signal >= 0.55
    ):
        return PedagogicalMode.GUIDED_EXPLANATION, "Intervencao anterior de recall falhou repetidamente; explicacao guiada intensificada."

    if (
        last_mode == PedagogicalMode.RAPID_REVIEW.value
        and effectiveness == PedagogicalOutcome.INEFFECTIVE.value
        and weakness_signal >= 0.35
    ):
        if dominant_error_type == "interpretation":
            return PedagogicalMode.CONTEXTUAL_APPLICATION, "Revisao rapida mostrou baixa efetividade; migracao para aplicacao contextual."
        return PedagogicalMode.CONCEPTUAL_REINFORCEMENT, "Revisao rapida mostrou baixa efetividade; reforco conceitual ativado."

    if (
        effectiveness == PedagogicalOutcome.EFFECTIVE.value
        and stabilization_signal >= 0.7
        and weakness_signal <= 0.25
    ):
        if curriculum_role == "cumulative" or review_intensity == "light" or resurfacing_signal >= 0.3:
            return PedagogicalMode.REINFORCEMENT_CHECK, "Microtopico estabilizado; intervencao reduzida para manutencao leve."
        return PedagogicalMode.RAPID_REVIEW, "Boa resposta pedagogica recente; pressao reduzida para revisao compacta."

    if (
        last_mode == PedagogicalMode.RAPID_REVIEW.value
        and effectiveness == PedagogicalOutcome.EFFECTIVE.value
        and stabilization_signal >= 0.6
    ):
        return PedagogicalMode.REINFORCEMENT_CHECK, "Revisoes rapidas estabilizaram o microtopico; checagem leve mantida."

    return base_mode, None


def _compute_reinforcement_level(
    *,
    weakness_signal: float,
    resurfacing_signal: float,
    stabilization_signal: float,
    incorrect_pressure: float,
) -> str:
    pressure = max(weakness_signal, incorrect_pressure, resurfacing_signal * 0.7)
    pressure -= stabilization_signal * 0.35
    if pressure >= 0.7:
        return "high"
    if pressure >= 0.35:
        return "medium"
    return "low"


def _compute_cognitive_load(
    *,
    curriculum_density: float,
    review_density: float,
    pedagogical_mode: PedagogicalMode,
) -> str:
    load = curriculum_density * 0.5 + review_density * 0.35
    if pedagogical_mode in {
        PedagogicalMode.GUIDED_EXPLANATION,
        PedagogicalMode.CONTEXTUAL_APPLICATION,
    }:
        load += 0.15
    if load >= 0.72:
        return "high"
    if load >= 0.42:
        return "medium"
    return "low"


def _build_intervention_reason(
    *,
    pedagogical_mode: PedagogicalMode,
    dominant_error_type: str | None,
    curriculum_role: str | None,
    review_intensity: str | None,
    weakness_signal: float,
    resurfacing_signal: float,
) -> str:
    error_label = dominant_error_type or "sem fragilidade dominante"
    return (
        f"Modo {pedagogical_mode.value} aplicado por {error_label}, "
        f"papel curricular {curriculum_role or 'neutro'}, intensidade {review_intensity or 'light'}, "
        f"fragilidade {weakness_signal:.2f} e resurfacing {resurfacing_signal:.2f}."
    )


def _build_adaptation_reasoning(
    *,
    pedagogical_mode: PedagogicalMode,
    transition_reason: str | None,
    intervention_effectiveness: str,
    weakness_signal: float,
    resurfacing_signal: float,
) -> list[str]:
    reasons = [
        f"Modo final: {pedagogical_mode.value}.",
        f"Eficacia recente: {intervention_effectiveness}.",
        f"Fragilidade {weakness_signal:.2f} e resurfacing {resurfacing_signal:.2f}.",
    ]
    if transition_reason:
        reasons.append(transition_reason)
    return reasons


def _pedagogical_stability(*, stabilization_signal: float, escalation_signal: float) -> str:
    if stabilization_signal >= 0.65 and escalation_signal < 0.4:
        return "stabilized"
    if escalation_signal >= 0.55:
        return "escalating"
    return "adaptive"


def _dominant_error_type(distribution: dict[str, int]) -> str | None:
    best_type = None
    best_value = 0
    for error_type in ERROR_TYPE_PRIORITY:
        value = int(distribution.get(error_type, 0) or 0)
        if value > best_value:
            best_type = error_type
            best_value = value
    return best_type


def _normalize_performance(performance: dict[str, object] | None) -> dict[str, object]:
    distribution = {
        "conceptual": 0,
        "interpretation": 0,
        "memory": 0,
        "attention": 0,
    }
    if performance:
        distribution.update(performance.get("error_distribution", {}) or {})
    return {
        "error_distribution": distribution,
        "consecutive_correct": int((performance or {}).get("consecutive_correct", 0) or 0),
        "consecutive_incorrect": int((performance or {}).get("consecutive_incorrect", 0) or 0),
    }


def _normalize_pedagogical_memory(pedagogical_memory: dict[str, object] | None) -> dict[str, object]:
    intervention_history = dict((pedagogical_memory or {}).get("intervention_history", {}) or {})
    return {
        "last_pedagogical_mode": (pedagogical_memory or {}).get("last_pedagogical_mode"),
        "recent_effectiveness": (pedagogical_memory or {}).get(
            "recent_effectiveness",
            PedagogicalOutcome.NEUTRAL.value,
        ),
        "consecutive_successes": int((pedagogical_memory or {}).get("consecutive_successes", 0) or 0),
        "consecutive_failures": int((pedagogical_memory or {}).get("consecutive_failures", 0) or 0),
        "stabilization_level": _clamp((pedagogical_memory or {}).get("stabilization_level", 0.0)),
        "escalation_level": _clamp((pedagogical_memory or {}).get("escalation_level", 0.0)),
        "retrieval_success_trend": _clamp((pedagogical_memory or {}).get("retrieval_success_trend", 0.5)),
        "intervention_history": intervention_history,
    }


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
