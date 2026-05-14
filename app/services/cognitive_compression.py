from __future__ import annotations

from app.domain.models import CognitiveCompressionProfile
from app.services.pedagogical_expression import expression_compression_hint


def resolve_cognitive_compression(
    *,
    block_type: str,
    pedagogical_mode: str | None,
    curriculum_role: str | None,
    review_intensity: str | None,
    relationship_signal: dict[str, object] | None,
    pedagogical_profile: dict[str, object] | object | None,
    facet_profile: dict[str, object] | object | None,
    trajectory_profile: dict[str, object] | object | None,
    expression_profile: dict[str, object] | object | None,
    session_coherence: dict[str, object] | object | None,
    cognitive_momentum: dict[str, object] | object | None,
) -> CognitiveCompressionProfile:
    block_type = str(block_type or "")
    pedagogical_mode = str(pedagogical_mode or "")
    curriculum_role = str(curriculum_role or "")
    review_intensity = str(review_intensity or "")
    relationship = _normalize(relationship_signal)
    pedagogical = _normalize(pedagogical_profile)
    facet = _normalize(facet_profile)
    trajectory = _normalize(trajectory_profile)
    expression = _normalize(expression_profile)
    coherence = _normalize(session_coherence)
    momentum = _normalize(cognitive_momentum)

    mode = expression_compression_hint(expression.get("pedagogical_expression_mode"))
    reason = "Compressao mantida em faixa explicita e controlada por compatibilidade."
    transition_reason = "O bloco manteve densidade informacional padrao."

    prerequisite_signal = _clamp(float(relationship.get("prerequisite_signal", 0.0) or 0.0))
    transfer_fragility = _clamp(float(trajectory.get("transfer_fragility", 0.0) or 0.0))
    reconstruction_fragility = _clamp(float(trajectory.get("reconstruction_fragility", 0.0) or 0.0))
    retention = _clamp(float(pedagogical.get("longitudinal_retention", 0.0) or 0.0))
    fatigue = _clamp(float(pedagogical.get("intervention_fatigue", 0.0) or 0.0))
    retrieval_framing = _clamp(float(expression.get("retrieval_framing", 0.0) or 0.0))
    explanation_density = _clamp(float(expression.get("explanation_density", 0.0) or 0.0))
    progression = _clamp(float(coherence.get("progression_continuity", 0.0) or 0.0))
    momentum_label = str(momentum.get("cognitive_momentum") or "")
    trajectory_state = str(trajectory.get("trajectory_state") or "")
    dominant_facet = str(facet.get("dominant_facet") or "")

    if prerequisite_signal >= 0.6 and str(relationship.get("relationship_type") or "") in {"applied_by", "exception_of", "prerequisite"}:
        mode = "prerequisite_supported"
        reason = "A compressao preservou apoio explicito de prerequisito antes de condensar demais."
        transition_reason = "A base previa precisou permanecer mais visivel neste bloco."
    elif trajectory_state == "transfer_fragile" or (dominant_facet == "contextual_transfer" and transfer_fragility >= 0.5):
        mode = "transfer_expanded"
        reason = "A transferencia ainda esta fragil e pediu mais contexto do que compactacao."
        transition_reason = "O bloco expandiu um pouco o apoio contextual para evitar salto prematuro."
    elif trajectory_state == "reconstruction_fragile" or reconstruction_fragility >= 0.5:
        mode = "reconstruction_scaffolded"
        reason = "A reconstrucao ainda oscila e pediu scaffold mais explicito."
        transition_reason = "A compressao foi contida para preservar encadeamento cognitivo."
    elif curriculum_role == "cumulative" and review_intensity == "light" and retention >= 0.7:
        mode = "cumulative_lightweight"
        reason = "O reaparecimento cumulativo esta estavel e pode ser mais leve."
        transition_reason = "A revisita cumulativa foi comprimida para reduzir redundancia."
    elif momentum_label == "retrieval_heavy" and retrieval_framing >= 0.6:
        mode = "retrieval_focused"
        reason = "A sessao ficou retrieval-heavy e pediu enunciacao mais curta e direta."
        transition_reason = "A compactacao atual reduz atrito de recuperacao."
    elif retention >= 0.75 and fatigue <= 0.2 and progression >= 0.65:
        mode = "stable_compressed"
        reason = "O bloco ja conta com boa consolidacao e pode reduzir redundancia."
        transition_reason = "A estabilidade atual permitiu compactacao mais segura."
    elif str(relationship.get("relationship_type") or "") in {"applied_by", "exception_of"}:
        mode = "context_supported"
        reason = "A relacao conceitual local pede suporte de contexto antes de comprimir demais."
        transition_reason = "O contexto imediato foi mantido visivel para preservar leitura correta."
    elif pedagogical_mode in {"conceptual_reinforcement", "reinforcement_check"} and explanation_density <= 0.35:
        mode = "reinforcement_condensed"
        reason = "O reforco atual admite compressao leve sem perda de intencao."
        transition_reason = "A formulacao foi condensada para manter ritmo sem perder o reforco."
    elif explanation_density <= 0.42:
        mode = "guided_compact"
        reason = "A densidade local ja estava controlada e foi mantida compacta."
        transition_reason = "A compressao acompanhou a densidade ja reduzida do bloco."
    else:
        mode = "fully_explicit"
        reason = "O bloco manteve formulacao mais explicita para nao esconder apoio necessario."
        transition_reason = "A carga atual ainda nao recomendou compressao adicional."

    informational_density = _informational_density(
        mode=mode,
        explanation_density=explanation_density,
        momentum_label=momentum_label,
    )
    contextual_support_level = _contextual_support_level(
        mode=mode,
        prerequisite_signal=prerequisite_signal,
        transfer_fragility=transfer_fragility,
    )
    retrieval_compaction = _retrieval_compaction(
        mode=mode,
        retrieval_framing=retrieval_framing,
    )
    explanatory_expansion = _explanatory_expansion(
        mode=mode,
        reconstruction_fragility=reconstruction_fragility,
        transfer_fragility=transfer_fragility,
    )
    redundancy_adjustment = _redundancy_adjustment(
        mode=mode,
        retention=retention,
        fatigue=fatigue,
    )

    return CognitiveCompressionProfile(
        cognitive_compression_mode=mode,
        compression_reasoning=[
            f"Modo de compressao: {mode}.",
            reason,
            f"Momentum/coerencia: {momentum_label or 'stable'} / {coherence.get('session_coherence_state') or 'stable_progression'}.",
        ],
        informational_density=informational_density,
        contextual_support_level=contextual_support_level,
        retrieval_compaction=retrieval_compaction,
        explanatory_expansion=explanatory_expansion,
        redundancy_adjustment=redundancy_adjustment,
        prerequisite_support_signal=_clamp(prerequisite_signal),
        compression_transition_reason=transition_reason,
        why_this_compression_now=_why_now(mode),
    )


def _informational_density(*, mode: str, explanation_density: float, momentum_label: str) -> float:
    base = {
        "fully_explicit": 0.78,
        "guided_compact": 0.48,
        "stable_compressed": 0.32,
        "retrieval_focused": 0.28,
        "context_supported": 0.56,
        "reconstruction_scaffolded": 0.64,
        "transfer_expanded": 0.66,
        "cumulative_lightweight": 0.24,
        "reinforcement_condensed": 0.3,
        "prerequisite_supported": 0.62,
    }.get(mode, 0.5)
    if momentum_label == "conceptually_dense":
        base -= 0.04
    return _clamp((base + explanation_density * 0.25))


def _contextual_support_level(*, mode: str, prerequisite_signal: float, transfer_fragility: float) -> float:
    base = {
        "fully_explicit": 0.42,
        "guided_compact": 0.3,
        "stable_compressed": 0.18,
        "retrieval_focused": 0.16,
        "context_supported": 0.72,
        "reconstruction_scaffolded": 0.48,
        "transfer_expanded": 0.82,
        "cumulative_lightweight": 0.24,
        "reinforcement_condensed": 0.22,
        "prerequisite_supported": 0.78,
    }.get(mode, 0.3)
    return _clamp(base + prerequisite_signal * 0.12 + transfer_fragility * 0.08)


def _retrieval_compaction(*, mode: str, retrieval_framing: float) -> float:
    base = {
        "fully_explicit": 0.18,
        "guided_compact": 0.42,
        "stable_compressed": 0.66,
        "retrieval_focused": 0.82,
        "context_supported": 0.28,
        "reconstruction_scaffolded": 0.24,
        "transfer_expanded": 0.2,
        "cumulative_lightweight": 0.7,
        "reinforcement_condensed": 0.62,
        "prerequisite_supported": 0.22,
    }.get(mode, 0.3)
    return _clamp(base * 0.7 + retrieval_framing * 0.3)


def _explanatory_expansion(*, mode: str, reconstruction_fragility: float, transfer_fragility: float) -> float:
    base = {
        "fully_explicit": 0.54,
        "guided_compact": 0.26,
        "stable_compressed": 0.08,
        "retrieval_focused": 0.06,
        "context_supported": 0.34,
        "reconstruction_scaffolded": 0.82,
        "transfer_expanded": 0.72,
        "cumulative_lightweight": 0.04,
        "reinforcement_condensed": 0.14,
        "prerequisite_supported": 0.48,
    }.get(mode, 0.2)
    return _clamp(base + reconstruction_fragility * 0.08 + transfer_fragility * 0.06)


def _redundancy_adjustment(*, mode: str, retention: float, fatigue: float) -> float:
    base = {
        "fully_explicit": 0.08,
        "guided_compact": 0.26,
        "stable_compressed": 0.74,
        "retrieval_focused": 0.68,
        "context_supported": 0.18,
        "reconstruction_scaffolded": 0.12,
        "transfer_expanded": 0.12,
        "cumulative_lightweight": 0.78,
        "reinforcement_condensed": 0.62,
        "prerequisite_supported": 0.14,
    }.get(mode, 0.2)
    return _clamp(base + retention * 0.08 - fatigue * 0.05)


def _why_now(mode: str) -> str:
    return {
        "fully_explicit": "O bloco ainda precisa de formulacao mais aberta e explicita.",
        "guided_compact": "O bloco pode ser mantido compacto sem perder apoio essencial.",
        "stable_compressed": "A estabilidade atual permite reduzir redundancia com seguranca.",
        "retrieval_focused": "A recuperacao atual pede formulacao mais curta e orientada ao nucleo.",
        "context_supported": "O contexto imediato ainda precisa permanecer visivel neste bloco.",
        "reconstruction_scaffolded": "A reconstrucao ainda pede apoio mais explicito do que compactacao.",
        "transfer_expanded": "A transferencia contextual precisa de um pouco mais de suporte agora.",
        "cumulative_lightweight": "A revisita cumulativa pode reaparecer em formato mais leve.",
        "reinforcement_condensed": "O reforco pode ser mais condensado sem perder funcao pedagogica.",
        "prerequisite_supported": "O prerequisito ainda precisa aparecer de forma mais visivel antes da compressao.",
    }.get(mode, "A compressao foi mantida em faixa neutra.")


def _normalize(value: dict[str, object] | object | None) -> dict[str, object]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    return {}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
