from __future__ import annotations

from copy import deepcopy

from app.domain.models import PedagogicalValidationProfile


class PedagogicalValidationLayer:
    WINDOW_SIZE = 4

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        recent: list[dict] = []
        for block in [deepcopy(item) for item in runtime_blocks]:
            profile = resolve_pedagogical_validation(current_block=block, recent_blocks=recent)
            annotated_block = {**block, **profile.model_dump(mode="json")}
            annotated.append(annotated_block)
            recent.append(annotated_block)
            recent = recent[-self.WINDOW_SIZE :]
        return annotated


def resolve_pedagogical_validation(
    *,
    current_block: dict,
    recent_blocks: list[dict] | None = None,
) -> PedagogicalValidationProfile:
    recent_blocks = list(recent_blocks or [])
    window = (recent_blocks[-3:] if recent_blocks else []) + [current_block]

    retrieval_effectiveness_signal = _retrieval_effectiveness_signal(current_block, window)
    stabilization_quality_signal = _stabilization_quality_signal(current_block, window)
    false_fluency_risk = _false_fluency_risk(current_block)
    scaffold_dependency_signal = _scaffold_dependency_signal(current_block, window)
    transfer_stability_signal = _transfer_stability_signal(current_block)
    reconstruction_progress_signal = _reconstruction_progress_signal(current_block, window)
    adaptation_overlap_signal = _adaptation_overlap_signal(current_block, window)
    reinforcement_density_signal = _reinforcement_density_signal(current_block, window)
    longitudinal_validation_signal = _longitudinal_validation_signal(current_block, window)
    validation_alignment = _validation_alignment(
        retrieval_effectiveness_signal=retrieval_effectiveness_signal,
        stabilization_quality_signal=stabilization_quality_signal,
        false_fluency_risk=false_fluency_risk,
        scaffold_dependency_signal=scaffold_dependency_signal,
        transfer_stability_signal=transfer_stability_signal,
        reconstruction_progress_signal=reconstruction_progress_signal,
        adaptation_overlap_signal=adaptation_overlap_signal,
        reinforcement_density_signal=reinforcement_density_signal,
        longitudinal_validation_signal=longitudinal_validation_signal,
    )

    state = _state(
        current_block=current_block,
        retrieval_effectiveness_signal=retrieval_effectiveness_signal,
        stabilization_quality_signal=stabilization_quality_signal,
        false_fluency_risk=false_fluency_risk,
        scaffold_dependency_signal=scaffold_dependency_signal,
        transfer_stability_signal=transfer_stability_signal,
        reconstruction_progress_signal=reconstruction_progress_signal,
        adaptation_overlap_signal=adaptation_overlap_signal,
        reinforcement_density_signal=reinforcement_density_signal,
        longitudinal_validation_signal=longitudinal_validation_signal,
        validation_alignment=validation_alignment,
    )

    return PedagogicalValidationProfile(
        pedagogical_validation_state=state,
        learning_effect_profile=_learning_effect_profile(state),
        validation_reasoning=[
            f"Estado de validacao: {state}.",
            f"Eficacia de retrieval: {retrieval_effectiveness_signal:.2f}.",
            f"Risco de falsa fluencia: {false_fluency_risk:.2f}.",
        ],
        retrieval_effectiveness_signal=round(retrieval_effectiveness_signal, 4),
        stabilization_quality_signal=round(stabilization_quality_signal, 4),
        false_fluency_risk=round(false_fluency_risk, 4),
        scaffold_dependency_signal=round(scaffold_dependency_signal, 4),
        transfer_stability_signal=round(transfer_stability_signal, 4),
        reconstruction_progress_signal=round(reconstruction_progress_signal, 4),
        adaptation_overlap_signal=round(adaptation_overlap_signal, 4),
        reinforcement_density_signal=round(reinforcement_density_signal, 4),
        longitudinal_validation_signal=round(longitudinal_validation_signal, 4),
        validation_alignment=round(validation_alignment, 4),
        why_this_validation_now=_why_now(state),
    )


def _retrieval_effectiveness_signal(current_block: dict, window: list[dict]) -> float:
    retrieval = {"high": 0.22, "medium": 0.16, "low": 0.08}.get(str(current_block.get("retrieval_intensity") or ""), 0.08)
    retention = _clamp(current_block.get("longitudinal_retention", 0.0)) * 0.24
    stability = _clamp(current_block.get("stabilization_quality", 0.0)) * 0.24
    momentum_bonus = {"balanced": 0.1, "stable": 0.08}.get(str(current_block.get("cognitive_momentum") or ""), 0.0)
    pressure_penalty = _clamp(current_block.get("retrieval_pressure_accumulation", 0.0)) * 0.18
    return _clamp(retrieval + retention + stability + momentum_bonus - pressure_penalty)


def _stabilization_quality_signal(current_block: dict, window: list[dict]) -> float:
    stage_bonus = {
        "consolidated": 0.34,
        "resilient": 0.36,
        "stabilizing": 0.22,
        "emerging": 0.1,
    }.get(str(current_block.get("stabilization_stage") or ""), 0.04)
    return _clamp(
        stage_bonus
        + _clamp(current_block.get("stabilization_quality", 0.0)) * 0.34
        + _clamp(current_block.get("longitudinal_consistency", 0.0)) * 0.24
        + _clamp(current_block.get("longitudinal_retention", 0.0)) * 0.18
    )


def _false_fluency_risk(current_block: dict) -> float:
    return _clamp(
        _clamp(current_block.get("false_fluency_signal", 0.0)) * 0.58
        + (0.16 if str(current_block.get("trajectory_state") or "") == "superficially_stable" else 0.0)
        + (0.12 if str(current_block.get("cognitive_compression_mode") or "") == "stable_compressed" else 0.0)
        + (0.08 if str(current_block.get("pedagogical_expression_mode") or "") == "stabilization_reassurance" else 0.0)
        - _clamp(current_block.get("retrieval_pressure_accumulation", 0.0)) * 0.08
    )


def _scaffold_dependency_signal(current_block: dict, window: list[dict]) -> float:
    return _clamp(
        _clamp(current_block.get("scaffold_density", 0.0)) * 0.34
        + _clamp(current_block.get("explanatory_expansion", 0.0)) * 0.22
        + _clamp(current_block.get("signal_overlap_density", 0.0)) * 0.18
        + _clamp(current_block.get("reconstruction_fragility", 0.0)) * 0.18
        + (0.14 if str(current_block.get("runtime_trace_state") or "") == "support_accumulated" else 0.0)
        + (0.12 if str(current_block.get("pedagogical_observability_state") or "") == "scaffold_saturated" else 0.0)
    )


def _transfer_stability_signal(current_block: dict) -> float:
    return _clamp(
        0.62
        - _clamp(current_block.get("transfer_fragility", 0.0)) * 0.44
        + (0.1 if str(current_block.get("trajectory_state") or "") != "transfer_fragile" else -0.06)
        + _clamp(current_block.get("longitudinal_consistency", 0.0)) * 0.14
    )


def _reconstruction_progress_signal(current_block: dict, window: list[dict]) -> float:
    base = 0.52 - _clamp(current_block.get("reconstruction_fragility", 0.0)) * 0.34
    if str(current_block.get("trajectory_state") or "") == "reconstruction_fragile":
        base -= 0.12
    if str(current_block.get("micro_intervention") or "") == "guided_reconstruction":
        base += 0.14
    if str(current_block.get("runtime_trace_state") or "") == "reconstruction_supported":
        base += 0.08
    return _clamp(base)


def _adaptation_overlap_signal(current_block: dict, window: list[dict]) -> float:
    return _clamp(
        _clamp(current_block.get("modulation_overlap", 0.0)) * 0.42
        + _clamp(current_block.get("signal_overlap_density", 0.0)) * 0.32
        + (0.14 if str(current_block.get("adaptive_signal_state") or "") in {"reconstruction_pressure", "retrieval_saturation", "support_convergent"} else 0.0)
        + (0.1 if str(current_block.get("runtime_trace_state") or "") in {"support_accumulated", "adaptation_convergent"} else 0.0)
    )


def _reinforcement_density_signal(current_block: dict, window: list[dict]) -> float:
    return _clamp(
        _clamp(current_block.get("reinforcement_convergence", 0.0)) * 0.42
        + (0.14 if str(current_block.get("pedagogical_mode") or "") in {"conceptual_reinforcement", "reinforcement_check"} else 0.0)
        + (0.12 if str(current_block.get("micro_intervention") or "") in {"confidence_check", "verification_step"} else 0.0)
        + _clamp(current_block.get("modulation_overlap", 0.0)) * 0.18
    )


def _longitudinal_validation_signal(current_block: dict, window: list[dict]) -> float:
    return _clamp(
        _clamp(current_block.get("longitudinal_retention", 0.0)) * 0.34
        + _clamp(current_block.get("longitudinal_consistency", 0.0)) * 0.38
        + _clamp(current_block.get("stabilization_quality", 0.0)) * 0.18
        - _clamp(current_block.get("false_fluency_signal", 0.0)) * 0.12
    )


def _validation_alignment(
    *,
    retrieval_effectiveness_signal: float,
    stabilization_quality_signal: float,
    false_fluency_risk: float,
    scaffold_dependency_signal: float,
    transfer_stability_signal: float,
    reconstruction_progress_signal: float,
    adaptation_overlap_signal: float,
    reinforcement_density_signal: float,
    longitudinal_validation_signal: float,
) -> float:
    positive = (
        retrieval_effectiveness_signal
        + stabilization_quality_signal
        + transfer_stability_signal
        + reconstruction_progress_signal
        + longitudinal_validation_signal
    ) / 5
    pressure = (false_fluency_risk + scaffold_dependency_signal + adaptation_overlap_signal) / 3
    return _clamp(positive * 0.72 + (1.0 - pressure) * 0.28 - reinforcement_density_signal * 0.08)


def _state(
    *,
    current_block: dict,
    retrieval_effectiveness_signal: float,
    stabilization_quality_signal: float,
    false_fluency_risk: float,
    scaffold_dependency_signal: float,
    transfer_stability_signal: float,
    reconstruction_progress_signal: float,
    adaptation_overlap_signal: float,
    reinforcement_density_signal: float,
    longitudinal_validation_signal: float,
    validation_alignment: float,
) -> str:
    if false_fluency_risk >= 0.56:
        return "surface_fluency_detected"
    if scaffold_dependency_signal >= 0.56:
        return "scaffold_dependency_risk"
    if str(current_block.get("trajectory_state") or "") == "transfer_fragile" or transfer_stability_signal <= 0.32:
        return "transfer_fragile"
    if str(current_block.get("trajectory_state") or "") == "reconstruction_fragile" and reconstruction_progress_signal >= 0.44:
        return "reconstruction_improving"
    if str(current_block.get("adaptive_signal_state") or "") in {"reconstruction_pressure", "retrieval_saturation", "support_convergent"} and adaptation_overlap_signal >= 0.42:
        return "adaptation_overlapping"
    if reinforcement_density_signal >= 0.52:
        return "reinforcement_redundant"
    if str(current_block.get("adaptive_signal_state") or "") == "retrieval_saturation" or str(current_block.get("pedagogical_observability_state") or "") == "retrieval_dense":
        return "retrieval_saturated"
    if retrieval_effectiveness_signal >= 0.5 and false_fluency_risk <= 0.28 and stabilization_quality_signal >= 0.48:
        return "retrieval_effective"
    if stabilization_quality_signal >= 0.66 and longitudinal_validation_signal >= 0.62:
        return "stabilization_sustainable"
    if longitudinal_validation_signal >= 0.68 and validation_alignment >= 0.58:
        return "longitudinally_stable"
    if validation_alignment >= 0.52:
        return "support_balanced"
    return "validation_inconclusive"


def _learning_effect_profile(state: str) -> str:
    return {
        "retrieval_effective": "A recuperacao parece contribuir para consolidacao sem sinais fortes de saturacao.",
        "surface_fluency_detected": "Os sinais sugerem dominio aparente mais rapido do que a consolidacao sustentada.",
        "scaffold_dependency_risk": "O suporte atual parece alto o bastante para indicar dependencia de scaffold.",
        "transfer_fragile": "A transferencia continua observacionalmente instavel.",
        "reconstruction_improving": "A reconstrucao ainda exige suporte, mas ha sinais de melhora.",
        "adaptation_overlapping": "As camadas adaptativas parecem convergir demais sobre o mesmo problema.",
        "reinforcement_redundant": "O reforco parece mais denso do que o necessario nesta janela.",
        "stabilization_sustainable": "A estabilizacao atual parece sustentavel nesta janela observada.",
        "retrieval_saturated": "A recuperacao parece estar se acumulando em excesso localmente.",
        "support_balanced": "A combinacao atual de suporte parece equilibrada e legivel.",
        "longitudinally_stable": "Os sinais longitudinais recentes parecem consistentes.",
        "validation_inconclusive": "Os sinais atuais ainda nao apontam para um efeito pedagogico claro.",
    }.get(state, "O efeito pedagogico observado permaneceu neutro.")


def _why_now(state: str) -> str:
    return {
        "retrieval_effective": "Os sinais atuais favorecem leitura de retrieval produtivo sem sobrecarga evidente.",
        "surface_fluency_detected": "A combinacao atual sugere fluencia aparente com sustentacao ainda incerta.",
        "scaffold_dependency_risk": "A combinacao atual empilhou apoio demais para uma leitura confortavel de autonomia.",
        "transfer_fragile": "A combinacao atual ainda nao sustenta transferencia com estabilidade suficiente.",
        "reconstruction_improving": "A combinacao atual mostra fragilidade, mas com melhora observavel.",
        "adaptation_overlapping": "A combinacao atual mostra varias camadas reagindo ao mesmo fenomeno.",
        "reinforcement_redundant": "A combinacao atual concentrou reforco em densidade acima da faixa desejavel.",
        "stabilization_sustainable": "A combinacao atual sugere estabilizacao consistente e sustentavel.",
        "retrieval_saturated": "A combinacao atual acumulou pressao de retrieval acima da faixa confortavel.",
        "support_balanced": "A combinacao atual permanece equilibrada e auditavel.",
        "longitudinally_stable": "A combinacao atual parece coerente com consolidacao ao longo do tempo.",
        "validation_inconclusive": "A combinacao atual ainda nao permite inferencia observacional mais forte.",
    }.get(state, "A leitura atual permaneceu em faixa validacional neutra.")


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
