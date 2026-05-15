from __future__ import annotations

from copy import deepcopy

from app.domain.models import ValidationHarnessProfile


class ValidationHarnessLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        profile = resolve_validation_harness(runtime_blocks)
        payload = profile.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def resolve_validation_harness(runtime_blocks: list[dict] | None) -> ValidationHarnessProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return ValidationHarnessProfile(
            validation_harness_state="pedagogically_inconclusive",
            validation_harness_reasoning=["Nao havia blocos suficientes para consolidar evidencia."],
            runtime_validation_summary="Sessao sem evidencia suficiente para validacao observacional.",
            why_this_validation_state="A harness recebeu uma sessao vazia ou sem sinais aproveitaveis.",
        )

    retrieval_sustainability_signal = _retrieval_sustainability_signal(blocks)
    scaffold_dependency_signal = _scaffold_dependency_signal(blocks)
    reconstruction_sustainability_signal = _reconstruction_sustainability_signal(blocks)
    transfer_stability_signal = _transfer_stability_signal(blocks)
    resurfacing_effectiveness_signal = _resurfacing_effectiveness_signal(blocks)
    stabilization_reliability_signal = _stabilization_reliability_signal(blocks)
    compression_safety_signal = _compression_safety_signal(blocks)
    continuity_sustainability_signal = _continuity_sustainability_signal(blocks)
    pacing_sustainability_signal = _pacing_sustainability_signal(blocks)
    cognitive_friction_signal = _cognitive_friction_signal(blocks)
    adaptive_overlap_signal = _adaptive_overlap_signal(blocks)
    pedagogical_balance_signal = _pedagogical_balance_signal(
        retrieval_sustainability_signal=retrieval_sustainability_signal,
        scaffold_dependency_signal=scaffold_dependency_signal,
        reconstruction_sustainability_signal=reconstruction_sustainability_signal,
        transfer_stability_signal=transfer_stability_signal,
        stabilization_reliability_signal=stabilization_reliability_signal,
        compression_safety_signal=compression_safety_signal,
        continuity_sustainability_signal=continuity_sustainability_signal,
        pacing_sustainability_signal=pacing_sustainability_signal,
        cognitive_friction_signal=cognitive_friction_signal,
        adaptive_overlap_signal=adaptive_overlap_signal,
    )
    evidence_alignment = _evidence_alignment(
        retrieval_sustainability_signal=retrieval_sustainability_signal,
        reconstruction_sustainability_signal=reconstruction_sustainability_signal,
        transfer_stability_signal=transfer_stability_signal,
        stabilization_reliability_signal=stabilization_reliability_signal,
        compression_safety_signal=compression_safety_signal,
        continuity_sustainability_signal=continuity_sustainability_signal,
        adaptive_overlap_signal=adaptive_overlap_signal,
        scaffold_dependency_signal=scaffold_dependency_signal,
    )
    validation_confidence = _validation_confidence(blocks, evidence_alignment)

    state = _state(
        retrieval_sustainability_signal=retrieval_sustainability_signal,
        scaffold_dependency_signal=scaffold_dependency_signal,
        reconstruction_sustainability_signal=reconstruction_sustainability_signal,
        transfer_stability_signal=transfer_stability_signal,
        resurfacing_effectiveness_signal=resurfacing_effectiveness_signal,
        stabilization_reliability_signal=stabilization_reliability_signal,
        compression_safety_signal=compression_safety_signal,
        continuity_sustainability_signal=continuity_sustainability_signal,
        pacing_sustainability_signal=pacing_sustainability_signal,
        cognitive_friction_signal=cognitive_friction_signal,
        adaptive_overlap_signal=adaptive_overlap_signal,
        pedagogical_balance_signal=pedagogical_balance_signal,
    )

    return ValidationHarnessProfile(
        validation_harness_state=state,
        validation_harness_reasoning=[
            f"Estado da harness: {state}.",
            f"Retrieval={retrieval_sustainability_signal:.2f}; scaffold={scaffold_dependency_signal:.2f}; reconstrucao={reconstruction_sustainability_signal:.2f}.",
            f"Compressao={compression_safety_signal:.2f}; continuidade={continuity_sustainability_signal:.2f}; overlap={adaptive_overlap_signal:.2f}.",
        ],
        retrieval_sustainability_signal=round(retrieval_sustainability_signal, 4),
        scaffold_dependency_signal=round(scaffold_dependency_signal, 4),
        reconstruction_sustainability_signal=round(reconstruction_sustainability_signal, 4),
        transfer_stability_signal=round(transfer_stability_signal, 4),
        resurfacing_effectiveness_signal=round(resurfacing_effectiveness_signal, 4),
        stabilization_reliability_signal=round(stabilization_reliability_signal, 4),
        compression_safety_signal=round(compression_safety_signal, 4),
        continuity_sustainability_signal=round(continuity_sustainability_signal, 4),
        pacing_sustainability_signal=round(pacing_sustainability_signal, 4),
        cognitive_friction_signal=round(cognitive_friction_signal, 4),
        adaptive_overlap_signal=round(adaptive_overlap_signal, 4),
        pedagogical_balance_signal=round(pedagogical_balance_signal, 4),
        validation_confidence=round(validation_confidence, 4),
        runtime_validation_summary=_summary(state),
        evidence_alignment=round(evidence_alignment, 4),
        why_this_validation_state=_why(state),
    )


def _retrieval_sustainability_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("retrieval_effectiveness_signal", 0.0)) * 0.56
        score += (1.0 - _clamp(block.get("retrieval_pressure_accumulation", 0.0))) * 0.22
        if str(block.get("pedagogical_validation_state") or "") == "retrieval_effective":
            score += 0.16
        if str(block.get("retrieval_family") or "") == "retrieval_dense":
            score -= 0.08
        values.append(_clamp(score))
    return _average(values)


def _scaffold_dependency_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("scaffold_dependency_signal", 0.0)) * 0.64
        score += _clamp(block.get("scaffold_density", 0.0)) * 0.18
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _reconstruction_sustainability_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("reconstruction_progress_signal", 0.0)) * 0.54
        score += (1.0 - _clamp(block.get("reconstruction_fragility", 0.0))) * 0.24
        if str(block.get("session_stability_state") or "") == "reconstruction_loaded":
            score -= 0.14
        values.append(_clamp(score))
    return _average(values)


def _transfer_stability_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("transfer_stability_signal", 0.0)) * 0.76
        score += (1.0 - _clamp(block.get("transfer_fragility", 0.0))) * 0.16
        values.append(_clamp(score))
    return _average(values)


def _resurfacing_effectiveness_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("longitudinal_validation_signal", 0.0)) * 0.42
        score += _clamp(block.get("stabilization_quality_signal", 0.0)) * 0.26
        score += _clamp(block.get("retrieval_effectiveness_signal", 0.0)) * 0.18
        values.append(_clamp(score))
    return _average(values)


def _stabilization_reliability_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("stabilization_quality_signal", 0.0)) * 0.54
        score += _clamp(block.get("longitudinal_validation_signal", 0.0)) * 0.28
        if str(block.get("stabilization_family") or "") in {"stabilized", "stabilization_progressive"}:
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _compression_safety_signal(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("compression_safety_metric", 0.0)) for block in blocks])


def _continuity_sustainability_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("continuity_smoothness_metric", 0.0)) * 0.64
        if str(block.get("continuity_family") or "") == "continuity_stable":
            score += 0.14
        elif str(block.get("continuity_family") or "") == "continuity_fragile":
            score -= 0.14
        values.append(_clamp(score))
    return _average(values)


def _pacing_sustainability_signal(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("pacing_stability_metric", 0.0)) for block in blocks])


def _cognitive_friction_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        friction = (
            _clamp(block.get("retrieval_pressure_accumulation", 0.0)) * 0.28
            + _clamp(block.get("scaffold_density", 0.0)) * 0.18
            + _clamp(block.get("modulation_overlap", 0.0)) * 0.16
            + _clamp(block.get("signal_overlap_density", 0.0)) * 0.14
            + (1.0 - _clamp(block.get("continuity_smoothness_metric", 0.5))) * 0.14
        )
        values.append(_clamp(friction))
    return _average(values)


def _adaptive_overlap_signal(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        overlap = max(
            _clamp(block.get("modulation_overlap", 0.0)),
            _clamp(block.get("signal_overlap_density", 0.0)),
        )
        if str(block.get("overlap_family") or "") in {"overlap_high", "overlap_convergent"}:
            overlap += 0.12
        values.append(_clamp(overlap))
    return _average(values)


def _pedagogical_balance_signal(
    *,
    retrieval_sustainability_signal: float,
    scaffold_dependency_signal: float,
    reconstruction_sustainability_signal: float,
    transfer_stability_signal: float,
    stabilization_reliability_signal: float,
    compression_safety_signal: float,
    continuity_sustainability_signal: float,
    pacing_sustainability_signal: float,
    cognitive_friction_signal: float,
    adaptive_overlap_signal: float,
) -> float:
    positive = (
        retrieval_sustainability_signal
        + reconstruction_sustainability_signal
        + transfer_stability_signal
        + stabilization_reliability_signal
        + compression_safety_signal
        + continuity_sustainability_signal
        + pacing_sustainability_signal
    ) / 7
    pressure = (scaffold_dependency_signal + cognitive_friction_signal + adaptive_overlap_signal) / 3
    return _clamp(positive * 0.76 + (1.0 - pressure) * 0.24)


def _evidence_alignment(
    *,
    retrieval_sustainability_signal: float,
    reconstruction_sustainability_signal: float,
    transfer_stability_signal: float,
    stabilization_reliability_signal: float,
    compression_safety_signal: float,
    continuity_sustainability_signal: float,
    adaptive_overlap_signal: float,
    scaffold_dependency_signal: float,
) -> float:
    positive = (
        retrieval_sustainability_signal
        + reconstruction_sustainability_signal
        + transfer_stability_signal
        + stabilization_reliability_signal
        + compression_safety_signal
        + continuity_sustainability_signal
    ) / 6
    risk = (adaptive_overlap_signal + scaffold_dependency_signal) / 2
    return _clamp(positive * 0.78 + (1.0 - risk) * 0.22)


def _validation_confidence(blocks: list[dict], evidence_alignment: float) -> float:
    sample_factor = min(len(blocks), 4) / 4
    return _clamp(evidence_alignment * 0.82 + sample_factor * 0.18)


def _state(
    *,
    retrieval_sustainability_signal: float,
    scaffold_dependency_signal: float,
    reconstruction_sustainability_signal: float,
    transfer_stability_signal: float,
    resurfacing_effectiveness_signal: float,
    stabilization_reliability_signal: float,
    compression_safety_signal: float,
    continuity_sustainability_signal: float,
    pacing_sustainability_signal: float,
    cognitive_friction_signal: float,
    adaptive_overlap_signal: float,
    pedagogical_balance_signal: float,
) -> str:
    if scaffold_dependency_signal >= 0.62:
        return "scaffold_dependency_risk"
    if adaptive_overlap_signal >= 0.62:
        return "modulation_overlapping"
    if retrieval_sustainability_signal >= 0.68 and cognitive_friction_signal <= 0.34:
        return "retrieval_sustainable"
    if retrieval_sustainability_signal <= 0.42:
        return "retrieval_fragile"
    if reconstruction_sustainability_signal >= 0.62 and cognitive_friction_signal <= 0.42:
        return "reconstruction_sustainable"
    if reconstruction_sustainability_signal <= 0.4:
        return "reconstruction_unstable"
    if transfer_stability_signal >= 0.64:
        return "transfer_supported"
    if transfer_stability_signal <= 0.4:
        return "transfer_fragile"
    if compression_safety_signal >= 0.76 and continuity_sustainability_signal >= 0.6:
        return "compression_safe"
    if compression_safety_signal <= 0.44:
        return "compression_risky"
    if resurfacing_effectiveness_signal >= 0.64 and stabilization_reliability_signal >= 0.62:
        return "resurfacing_effective"
    if continuity_sustainability_signal >= 0.7 and pacing_sustainability_signal >= 0.62:
        return "continuity_sustainable"
    if pedagogical_balance_signal >= 0.68 and cognitive_friction_signal <= 0.34:
        return "cognitively_balanced"
    if resurfacing_effectiveness_signal <= 0.46:
        return "resurfacing_inconclusive"
    return "validation_stable"


def _summary(state: str) -> str:
    return {
        "validation_stable": "A evidência atual permanece estável, mas sem dominância diagnóstica forte.",
        "retrieval_sustainable": "A recuperação parece sustentável na janela observada.",
        "retrieval_fragile": "A recuperação ainda parece frágil ou pouco eficiente localmente.",
        "scaffold_dependency_risk": "Há indícios de dependência excessiva de scaffold na sessão.",
        "support_overextended": "O suporte parece mais extenso do que o necessário na janela atual.",
        "reconstruction_sustainable": "A reconstrução parece sustentada sem atrito elevado.",
        "reconstruction_unstable": "A reconstrução ainda parece instável ou dependente de apoio.",
        "transfer_supported": "A transferência conceitual parece bem sustentada na sessão.",
        "transfer_fragile": "A transferência ainda mostra fragilidade observável.",
        "resurfacing_effective": "O resurfacing parece contribuir para consolidação e estabilidade.",
        "resurfacing_inconclusive": "O resurfacing atual ainda não mostra efeito claro o suficiente.",
        "compression_safe": "A compressão permaneceu segura e compatível com os demais sinais.",
        "compression_risky": "A compressão parece menos segura no contexto observado.",
        "continuity_sustainable": "A continuidade e o ritmo permaneceram sustentáveis.",
        "modulation_overlapping": "As camadas modulatórias parecem sobrepostas além da faixa leve.",
        "cognitively_balanced": "A sessão parece cognitivamente equilibrada na janela observada.",
        "pedagogically_inconclusive": "A evidência atual ainda é insuficiente para uma leitura clara.",
    }.get(state, "A evidência atual ficou em faixa observacional neutra.")


def _why(state: str) -> str:
    return {
        "validation_stable": "Os sinais estão coerentes, mas sem um padrão dominante claro.",
        "retrieval_sustainable": "Há boa eficácia de retrieval com baixa pressão acumulada.",
        "retrieval_fragile": "A eficácia de retrieval ainda não compensou a pressão observada.",
        "scaffold_dependency_risk": "Scaffold e dependência de suporte convergiram para uma faixa alta.",
        "support_overextended": "O apoio parece mais denso do que a sessão precisa agora.",
        "reconstruction_sustainable": "A reconstrução mostra melhora sem dependência excessiva.",
        "reconstruction_unstable": "A reconstrução ainda enfrenta fragilidade ou baixa sustentabilidade.",
        "transfer_supported": "A transferência está estável o suficiente na janela atual.",
        "transfer_fragile": "Os sinais de transferência ainda são insuficientemente estáveis.",
        "resurfacing_effective": "Os sinais de retenção e estabilização sustentaram o resurfacing.",
        "resurfacing_inconclusive": "A reaparição ainda não acumulou evidência suficiente de benefício.",
        "compression_safe": "A compressão está alinhada com estabilidade e continuidade suficientes.",
        "compression_risky": "A compressão perdeu margem de segurança observacional nesta janela.",
        "continuity_sustainable": "Continuidade e pacing seguiram estáveis ao longo da janela.",
        "modulation_overlapping": "Overlap e convergência adaptativa ficaram altos demais localmente.",
        "cognitively_balanced": "Os eixos observados mantiveram bom equilíbrio cognitivo.",
        "pedagogically_inconclusive": "Os sinais ainda não se alinharam o bastante para uma conclusão clara.",
    }.get(state, "O estado veio de uma agregação local e puramente observacional.")


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return _clamp(sum(values) / len(values))


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
