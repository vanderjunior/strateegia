from __future__ import annotations

from copy import deepcopy

from app.domain.models import PedagogicalObservabilityProfile


class PedagogicalObservabilityLayer:
    WINDOW_SIZE = 4

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        recent: list[dict] = []
        for block in [deepcopy(item) for item in runtime_blocks]:
            profile = resolve_pedagogical_observability(current_block=block, recent_blocks=recent)
            annotated_block = {**block, **profile.model_dump(mode="json")}
            annotated.append(annotated_block)
            recent.append(annotated_block)
            recent = recent[-self.WINDOW_SIZE :]
        return annotated


def resolve_pedagogical_observability(
    *,
    current_block: dict,
    recent_blocks: list[dict] | None = None,
) -> PedagogicalObservabilityProfile:
    recent_blocks = list(recent_blocks or [])
    window = (recent_blocks[-3:] if recent_blocks else []) + [current_block]

    signal_overlap_density = _signal_overlap_density(current_block)
    retrieval_pressure_accumulation = _retrieval_pressure_accumulation(window)
    compression_support_alignment = _compression_support_alignment(current_block)
    scaffold_density = _scaffold_density(window)
    continuity_stability = _continuity_stability(window)
    modulation_redundancy = _modulation_redundancy(
        signal_overlap_density=signal_overlap_density,
        scaffold_density=scaffold_density,
        retrieval_pressure_accumulation=retrieval_pressure_accumulation,
        compression_support_alignment=compression_support_alignment,
    )
    expression_variation_balance = _expression_variation_balance(window)
    intervention_repetition_signal = _intervention_repetition_signal(window)
    trajectory_consistency = _trajectory_consistency(window)

    state = _state(
        signal_overlap_density=signal_overlap_density,
        retrieval_pressure_accumulation=retrieval_pressure_accumulation,
        compression_support_alignment=compression_support_alignment,
        scaffold_density=scaffold_density,
        continuity_stability=continuity_stability,
        modulation_redundancy=modulation_redundancy,
        expression_variation_balance=expression_variation_balance,
        intervention_repetition_signal=intervention_repetition_signal,
        trajectory_consistency=trajectory_consistency,
    )

    return PedagogicalObservabilityProfile(
        pedagogical_observability_state=state,
        observability_reasoning=[
            f"Estado observacional: {state}.",
            f"Sobreposicao de sinais: {signal_overlap_density:.2f}.",
            f"Redundancia modular: {modulation_redundancy:.2f}.",
        ],
        signal_overlap_density=round(signal_overlap_density, 4),
        retrieval_pressure_accumulation=round(retrieval_pressure_accumulation, 4),
        compression_support_alignment=round(compression_support_alignment, 4),
        scaffold_density=round(scaffold_density, 4),
        continuity_stability=round(continuity_stability, 4),
        modulation_redundancy=round(modulation_redundancy, 4),
        expression_variation_balance=round(expression_variation_balance, 4),
        intervention_repetition_signal=round(intervention_repetition_signal, 4),
        trajectory_consistency=round(trajectory_consistency, 4),
        adaptive_behavior_summary=_adaptive_behavior_summary(state),
        signal_overlap_reason=_signal_overlap_reason(signal_overlap_density),
        support_density_reason=_support_density_reason(scaffold_density, compression_support_alignment),
        retrieval_balance_reason=_retrieval_balance_reason(retrieval_pressure_accumulation),
        modulation_consistency=_modulation_consistency(modulation_redundancy, expression_variation_balance),
        continuity_observation=_continuity_observation(continuity_stability),
        stability_profile=_stability_profile(trajectory_consistency, intervention_repetition_signal),
        why_this_observation_now=_why_now(state),
    )


def _signal_overlap_density(block: dict) -> float:
    score = 0.0
    if str(block.get("trajectory_state") or "") in {"reconstruction_fragile", "transfer_fragile"}:
        score += 0.22
    if str(block.get("micro_intervention") or "") in {"guided_reconstruction", "prerequisite_recall", "semantic_reactivation"}:
        score += 0.16
    if str(block.get("pedagogical_expression_mode") or "") in {"focused_reconstruction", "contextual_bridge", "retrieval_softener"}:
        score += 0.14
    if str(block.get("cognitive_compression_mode") or "") in {"reconstruction_scaffolded", "transfer_expanded", "prerequisite_supported", "retrieval_focused"}:
        score += 0.18
    if str(block.get("adaptive_signal_state") or "") in {"reconstruction_pressure", "retrieval_saturation", "support_convergent"}:
        score += 0.14
    return _clamp(score)


def _retrieval_pressure_accumulation(window: list[dict]) -> float:
    score = 0.0
    for block in window:
        score += {"high": 0.24, "medium": 0.12, "low": 0.03}.get(str(block.get("retrieval_intensity") or ""), 0.03)
        score += {"retrieval_heavy": 0.16, "pressured": 0.08}.get(str(block.get("cognitive_momentum") or ""), 0.0)
        score += {"retrieval_focused": 0.12}.get(str(block.get("cognitive_compression_mode") or ""), 0.0)
        score += {"retrieval_softener": 0.1}.get(str(block.get("pedagogical_expression_mode") or ""), 0.0)
    return _clamp(score / max(len(window), 1))


def _compression_support_alignment(block: dict) -> float:
    compression = str(block.get("cognitive_compression_mode") or "")
    expression = str(block.get("pedagogical_expression_mode") or "")
    trajectory = str(block.get("trajectory_state") or "")
    score = 0.18
    if compression == "reconstruction_scaffolded" and trajectory == "reconstruction_fragile":
        score += 0.34
    if compression == "transfer_expanded" and trajectory == "transfer_fragile":
        score += 0.34
    if compression in {"stable_compressed", "cumulative_lightweight"} and expression in {"stabilization_reassurance", "cumulative_reactivation"}:
        score += 0.22
    if compression == "retrieval_focused" and expression == "retrieval_softener":
        score += 0.2
    return _clamp(score)


def _scaffold_density(window: list[dict]) -> float:
    score = 0.0
    for block in window:
        if str(block.get("micro_intervention") or "") == "guided_reconstruction":
            score += 0.2
        if str(block.get("pedagogical_expression_mode") or "") in {"focused_reconstruction", "conceptual_clarifier"}:
            score += 0.16
        if str(block.get("cognitive_compression_mode") or "") in {"reconstruction_scaffolded", "prerequisite_supported", "transfer_expanded"}:
            score += 0.18
        score += _clamp(block.get("explanatory_expansion", 0.0)) * 0.08
    return _clamp(score / max(len(window), 1))


def _continuity_stability(window: list[dict]) -> float:
    values = []
    for block in window:
        values.append(_clamp(block.get("progression_continuity", block.get("continuity_signal", 0.55))))
        state = str(block.get("session_coherence_state") or "")
        if state in {"stable_progression", "continuity_stable", "contextual_shift_softened"}:
            values.append(0.72)
        elif state == "pacing_fragile":
            values.append(0.28)
    return _clamp(sum(values) / max(len(values), 1))


def _modulation_redundancy(
    *,
    signal_overlap_density: float,
    scaffold_density: float,
    retrieval_pressure_accumulation: float,
    compression_support_alignment: float,
) -> float:
    return _clamp(
        signal_overlap_density * 0.34
        + scaffold_density * 0.26
        + retrieval_pressure_accumulation * 0.18
        + compression_support_alignment * 0.14
    )


def _expression_variation_balance(window: list[dict]) -> float:
    modes = [str(block.get("pedagogical_expression_mode") or "") for block in window if block.get("pedagogical_expression_mode")]
    if not modes:
        return 0.42
    unique = len(set(modes))
    if unique == 1:
        return 0.72
    if unique == 2:
        return 0.58
    return 0.44


def _intervention_repetition_signal(window: list[dict]) -> float:
    interventions = [str(block.get("micro_intervention") or "") for block in window if block.get("micro_intervention")]
    if not interventions:
        return 0.0
    last = interventions[-1]
    consecutive = 0
    for value in reversed(interventions):
        if value == last:
            consecutive += 1
        else:
            break
    return _clamp(max(0.0, (consecutive - 1) * 0.28))


def _trajectory_consistency(window: list[dict]) -> float:
    states = [str(block.get("trajectory_state") or "") for block in window if block.get("trajectory_state")]
    if not states:
        return 0.4
    dominant = max(states.count(state) for state in set(states))
    longitudinal_average = sum(_clamp(block.get("longitudinal_consistency", 0.4)) for block in window) / max(len(window), 1)
    return _clamp(dominant / len(states) * 0.58 + longitudinal_average * 0.42)


def _state(
    *,
    signal_overlap_density: float,
    retrieval_pressure_accumulation: float,
    compression_support_alignment: float,
    scaffold_density: float,
    continuity_stability: float,
    modulation_redundancy: float,
    expression_variation_balance: float,
    intervention_repetition_signal: float,
    trajectory_consistency: float,
) -> str:
    if scaffold_density >= 0.48 and modulation_redundancy >= 0.34:
        return "scaffold_saturated"
    if retrieval_pressure_accumulation >= 0.42:
        return "retrieval_dense"
    if modulation_redundancy >= 0.42 and signal_overlap_density >= 0.42:
        return "signal_redundant"
    if continuity_stability >= 0.68:
        return "continuity_consistent"
    if compression_support_alignment >= 0.6 and trajectory_consistency >= 0.5:
        return "support_heavy"
    if expression_variation_balance >= 0.64:
        return "expression_stable"
    if trajectory_consistency >= 0.56 and intervention_repetition_signal <= 0.28:
        return "adaptively_balanced"
    if modulation_redundancy <= 0.28 and signal_overlap_density <= 0.3:
        return "modulation_balanced"
    return "stable"


def _adaptive_behavior_summary(state: str) -> str:
    return {
        "stable": "Os sinais adaptativos permaneceram legiveis e sem acumulacao incomum.",
        "support_heavy": "O bloco concentrou apoio explicativo consistente, mas ainda auditavel.",
        "retrieval_dense": "A janela recente acumulou mais pressao de recuperacao do que o normal.",
        "modulation_balanced": "As modulacoes atuais permaneceram leves e sem sobrecarga evidente.",
        "scaffold_saturated": "A sessao concentrou scaffold demais em uma janela curta.",
        "continuity_consistent": "A continuidade local permaneceu bem sustentada ao longo da janela.",
        "signal_redundant": "Varios sinais parecem convergir sobre a mesma condicao cognitiva.",
        "expression_stable": "A expressao pedagogica ficou muito estavel na janela recente.",
        "adaptively_balanced": "A sessao parece adaptativamente equilibrada sem convergencia excessiva.",
    }.get(state, "A observabilidade permaneceu em faixa neutra.")


def _signal_overlap_reason(value: float) -> str:
    if value >= 0.42:
        return "Ha forte sobreposicao local entre camadas reagindo ao mesmo fenomeno."
    if value <= 0.2:
        return "A sobreposicao local de sinais permaneceu baixa."
    return "A sobreposicao local de sinais ficou moderada."


def _support_density_reason(scaffold_density: float, alignment: float) -> str:
    if scaffold_density >= 0.48:
        return "A densidade de scaffold ficou alta nesta janela curta."
    if alignment >= 0.6:
        return "Compressao e suporte cognitivo ficaram bem alinhados."
    return "O suporte atual permaneceu em faixa moderada."


def _retrieval_balance_reason(value: float) -> str:
    if value >= 0.42:
        return "A recuperacao vem se acumulando com intensidade perceptivel."
    if value <= 0.16:
        return "A pressao de recuperacao permaneceu baixa."
    return "A recuperacao ficou em faixa intermediaria."


def _modulation_consistency(redundancy: float, variation: float) -> str:
    if redundancy >= 0.42:
        return "A janela atual mostra sinais de redundancia modular."
    if variation >= 0.64:
        return "A expressao ficou muito estavel, o que favorece leitura mas pode mascarar repeticao."
    return "A consistencia de modulacao permaneceu controlada."


def _continuity_observation(value: float) -> str:
    if value >= 0.68:
        return "A continuidade local parece sustentada ao longo da janela."
    if value <= 0.34:
        return "A continuidade local parece fragil nesta janela."
    return "A continuidade local permaneceu intermediaria."


def _stability_profile(trajectory: float, repetition: float) -> str:
    if trajectory >= 0.56 and repetition <= 0.28:
        return "Trajetoria relativamente consistente com repeticao controlada."
    if repetition >= 0.42:
        return "A repeticao de intervencao cresceu mais rapido do que a consistencia observada."
    return "Estabilidade observacional moderada."


def _why_now(state: str) -> str:
    return {
        "stable": "A observacao atual resume um comportamento local estavel.",
        "support_heavy": "A janela atual concentrou apoio suficiente para justificar observacao explicita.",
        "retrieval_dense": "A janela atual acumulou varios sinais ligados a recuperacao.",
        "modulation_balanced": "A janela atual permaneceu leve o bastante para indicar equilibrio.",
        "scaffold_saturated": "A janela atual empilhou varios sinais de scaffold ao mesmo tempo.",
        "continuity_consistent": "A janela atual sustentou continuidade de forma consistente.",
        "signal_redundant": "A janela atual concentrou sinais que parecem descrever a mesma pressao.",
        "expression_stable": "A janela atual repetiu framing suficiente para merecer observacao.",
        "adaptively_balanced": "A janela atual manteve adaptacao legivel sem inflacao evidente.",
    }.get(state, "A observacao atual permaneceu em faixa neutra.")


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
