from __future__ import annotations

from app.domain.models import PedagogicalMode, PedagogicalProfile


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
) -> PedagogicalProfile:
    normalized_performance = _normalize_performance(performance)
    normalized_weakness = _clamp(weakness_signal)
    normalized_resurfacing = _clamp(resurfacing_signal)
    stabilization_signal = _clamp(normalized_performance["consecutive_correct"] / 5.0)
    incorrect_pressure = _clamp(normalized_performance["consecutive_incorrect"] / 4.0)
    curriculum_density = CURRICULUM_DENSITY.get(curriculum_role or "", 0.6)
    review_density = REVIEW_DENSITY.get(review_intensity or "", 0.5)
    dominant_error_type = _dominant_error_type(normalized_performance["error_distribution"])

    breakdown = {
        "weakness_signal": normalized_weakness,
        "resurfacing_signal": normalized_resurfacing,
        "stabilization_signal": stabilization_signal,
        "incorrect_pressure": incorrect_pressure,
        "curriculum_density": curriculum_density,
        "review_density": review_density,
    }

    pedagogical_mode = compute_pedagogical_mode(
        dominant_error_type=dominant_error_type,
        curriculum_role=curriculum_role,
        review_intensity=review_intensity,
        weakness_signal=normalized_weakness,
        resurfacing_signal=normalized_resurfacing,
        stabilization_signal=stabilization_signal,
        incorrect_pressure=incorrect_pressure,
    )
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


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
