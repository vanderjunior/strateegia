from __future__ import annotations

from datetime import datetime, timezone


def analyze_pedagogical_stability(
    *,
    performance: dict[str, object] | None,
    pedagogical_memory: dict[str, object] | None,
    resurfacing_signal: float,
) -> dict[str, object]:
    normalized_performance = _normalize_performance(performance)
    normalized_memory = _normalize_memory(pedagogical_memory)

    accuracy = normalized_performance["correct_answers"] / max(
        normalized_performance["total_questions"], 1
    )
    successful_resurfacing_ratio = normalized_memory["successful_resurfacing_cycles"] / max(
        normalized_memory["resurfacing_cycles"], 1
    )
    shallow_success = min(normalized_performance["consecutive_correct"] / 3.0, 1.0) * 0.35
    durable_success = (
        normalized_memory["stabilization_level"] * 0.35
        + successful_resurfacing_ratio * 0.2
        + normalized_memory["retrieval_success_trend"] * 0.15
    )
    retention_confidence = _clamp(shallow_success + durable_success)
    forgetting_signal = _clamp(
        normalized_performance["recent_errors"] * 0.18
        + min(normalized_performance["consecutive_incorrect"] * 0.18, 0.36)
        + resurfacing_signal * 0.2
        + (1.0 - normalized_memory["retrieval_success_trend"]) * 0.2
        - normalized_memory["stabilization_level"] * 0.15
    )
    recovery_signal = _clamp(
        normalized_memory["recovery_count"] * 0.2
        + max(normalized_performance["consecutive_correct"] - 1, 0) * 0.08
        + max(normalized_memory["successful_resurfacing_cycles"] - 1, 0) * 0.05
    )
    intervention_fatigue = _clamp(
        normalized_memory["fatigue_exposure"] * 0.55
        + _mode_repetition_pressure(normalized_memory) * 0.25
        + normalized_memory["stabilization_level"] * 0.12
        - forgetting_signal * 0.12
    )
    longitudinal_consistency = _clamp(
        accuracy * 0.3
        + normalized_memory["retrieval_success_trend"] * 0.3
        + successful_resurfacing_ratio * 0.2
        + normalized_memory["stabilization_level"] * 0.2
        - normalized_performance["consecutive_incorrect"] * 0.08
    )
    reinforcement_signal = _clamp(
        forgetting_signal * 0.45
        + (1.0 - retention_confidence) * 0.25
        + max(0.0, 0.35 - longitudinal_consistency) * 0.4
        - intervention_fatigue * 0.18
    )
    pedagogical_stability_score = _clamp(
        normalized_memory["stabilization_level"] * 0.4
        + retention_confidence * 0.25
        + longitudinal_consistency * 0.2
        + recovery_signal * 0.1
        - forgetting_signal * 0.15
    )

    stage = _stabilization_stage(
        pedagogical_stability_score=pedagogical_stability_score,
        retention_confidence=retention_confidence,
        forgetting_signal=forgetting_signal,
        successful_resurfacing_ratio=successful_resurfacing_ratio,
    )

    return {
        "pedagogical_stability_score": pedagogical_stability_score,
        "retention_confidence": retention_confidence,
        "intervention_fatigue": intervention_fatigue,
        "reinforcement_signal": reinforcement_signal,
        "forgetting_signal": forgetting_signal,
        "stabilization_stage": stage,
        "longitudinal_consistency": longitudinal_consistency,
        "recovery_signal": recovery_signal,
        "reinforcement_reason": _reinforcement_reason(forgetting_signal, recovery_signal),
        "fatigue_reason": _fatigue_reason(intervention_fatigue, normalized_memory),
        "stabilization_reasoning": _stabilization_reasoning(
            stage=stage,
            retention_confidence=retention_confidence,
            forgetting_signal=forgetting_signal,
            resurfacing_cycles=normalized_memory["resurfacing_cycles"],
        ),
        "retention_reasoning": _retention_reasoning(
            retention_confidence=retention_confidence,
            successful_resurfacing_ratio=successful_resurfacing_ratio,
            shallow_success=shallow_success,
        ),
    }


def _stabilization_stage(
    *,
    pedagogical_stability_score: float,
    retention_confidence: float,
    forgetting_signal: float,
    successful_resurfacing_ratio: float,
) -> str:
    if pedagogical_stability_score >= 0.82 and retention_confidence >= 0.72 and successful_resurfacing_ratio >= 0.7:
        return "resilient"
    if pedagogical_stability_score >= 0.65 and retention_confidence >= 0.58 and forgetting_signal <= 0.4:
        return "consolidated"
    if pedagogical_stability_score >= 0.48 and retention_confidence >= 0.42:
        return "stabilizing"
    if pedagogical_stability_score >= 0.28:
        return "emerging"
    return "unstable"


def _reinforcement_reason(forgetting_signal: float, recovery_signal: float) -> str:
    if forgetting_signal >= 0.55:
        return "Reforco aumentado por sinais claros de esquecimento e queda de recuperacao."
    if recovery_signal >= 0.35:
        return "Reforco mantido para consolidar recuperacao apos fragilidade previa."
    return "Reforco leve para manutencao cumulativa e prevencao de esquecimento."


def _fatigue_reason(intervention_fatigue: float, memory: dict[str, object]) -> str:
    if intervention_fatigue >= 0.55:
        return "Fadiga moderada detectada por repeticao prolongada do mesmo tipo de intervencao."
    if memory["fatigue_exposure"] > 0.0:
        return "Fadiga leve considerada para evitar excesso de pressao pedagogica."
    return "Sem fadiga relevante; intervencoes podem seguir com pressao habitual."


def _stabilization_reasoning(
    *,
    stage: str,
    retention_confidence: float,
    forgetting_signal: float,
    resurfacing_cycles: int,
) -> list[str]:
    return [
        f"Estagio longitudinal atual: {stage}.",
        f"Confianca de retencao {retention_confidence:.2f} com sinal de esquecimento {forgetting_signal:.2f}.",
        f"Historico de resurfacing observado em {resurfacing_cycles} ciclos.",
    ]


def _retention_reasoning(
    *,
    retention_confidence: float,
    successful_resurfacing_ratio: float,
    shallow_success: float,
) -> list[str]:
    return [
        f"Retencao longitudinal estimada em {retention_confidence:.2f}.",
        f"Sucesso em resurfacing: {successful_resurfacing_ratio:.2f}.",
        f"Sucesso imediato de curto prazo contribuiu {shallow_success:.2f}.",
    ]


def _mode_repetition_pressure(memory: dict[str, object]) -> float:
    last_mode = memory["last_pedagogical_mode"]
    if not last_mode:
        return 0.0
    history = dict(memory.get("intervention_history", {}) or {}).get(last_mode, {}) or {}
    consecutive_successes = int(history.get("consecutive_successes", 0) or 0)
    total_attempts = int(history.get("total_attempts", 0) or 0)
    return _clamp(consecutive_successes * 0.12 + min(total_attempts * 0.02, 0.16))


def _normalize_performance(performance: dict[str, object] | None) -> dict[str, object]:
    base = {
        "total_questions": 0,
        "correct_answers": 0,
        "recent_errors": 0,
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "last_seen_at": None,
        "last_reviewed_at": None,
        "last_correct_at": None,
        "last_incorrect_at": None,
    }
    if performance:
        base.update(performance)
    return {
        "total_questions": int(base.get("total_questions", 0) or 0),
        "correct_answers": int(base.get("correct_answers", 0) or 0),
        "recent_errors": int(base.get("recent_errors", 0) or 0),
        "consecutive_correct": int(base.get("consecutive_correct", 0) or 0),
        "consecutive_incorrect": int(base.get("consecutive_incorrect", 0) or 0),
        "last_seen_at": base.get("last_seen_at"),
        "last_reviewed_at": base.get("last_reviewed_at"),
        "last_correct_at": base.get("last_correct_at"),
        "last_incorrect_at": base.get("last_incorrect_at"),
    }


def _normalize_memory(memory: dict[str, object] | None) -> dict[str, object]:
    base = {
        "last_pedagogical_mode": None,
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "consecutive_failures": 0,
        "last_intervention_at": None,
        "stabilization_level": 0.0,
        "escalation_level": 0.0,
        "retrieval_success_trend": 0.5,
        "intervention_history": {},
        "resurfacing_cycles": 0,
        "successful_resurfacing_cycles": 0,
        "fatigue_exposure": 0.0,
        "recovery_count": 0,
        "last_stabilized_at": None,
    }
    if memory:
        base.update(memory)
    return {
        "last_pedagogical_mode": base.get("last_pedagogical_mode"),
        "recent_effectiveness": base.get("recent_effectiveness", "neutral"),
        "consecutive_successes": int(base.get("consecutive_successes", 0) or 0),
        "consecutive_failures": int(base.get("consecutive_failures", 0) or 0),
        "last_intervention_at": base.get("last_intervention_at"),
        "stabilization_level": _clamp(base.get("stabilization_level", 0.0)),
        "escalation_level": _clamp(base.get("escalation_level", 0.0)),
        "retrieval_success_trend": _clamp(base.get("retrieval_success_trend", 0.5)),
        "intervention_history": dict(base.get("intervention_history", {}) or {}),
        "resurfacing_cycles": int(base.get("resurfacing_cycles", 0) or 0),
        "successful_resurfacing_cycles": int(base.get("successful_resurfacing_cycles", 0) or 0),
        "fatigue_exposure": _clamp(base.get("fatigue_exposure", 0.0)),
        "recovery_count": int(base.get("recovery_count", 0) or 0),
        "last_stabilized_at": base.get("last_stabilized_at"),
    }


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
