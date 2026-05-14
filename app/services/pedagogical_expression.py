from __future__ import annotations

from app.domain.models import PedagogicalExpressionProfile


def resolve_pedagogical_expression(
    *,
    block_type: str,
    pedagogical_mode: str | None,
    curriculum_role: str | None,
    review_intensity: str | None,
    cognitive_load: str | None,
    retrieval_intensity: str | None,
    narrative_relation: str | None,
    cognitive_momentum: str | None,
    micro_intervention: str | None,
    dominant_facet: str | None,
    trajectory_state: str | None,
) -> PedagogicalExpressionProfile:
    block_type = str(block_type or "")
    pedagogical_mode = str(pedagogical_mode or "")
    curriculum_role = str(curriculum_role or "")
    review_intensity = str(review_intensity or "")
    cognitive_load = str(cognitive_load or "")
    retrieval_intensity = str(retrieval_intensity or "")
    narrative_relation = str(narrative_relation or "")
    cognitive_momentum = str(cognitive_momentum or "")
    micro_intervention = str(micro_intervention or "")
    dominant_facet = str(dominant_facet or "")
    trajectory_state = str(trajectory_state or "")

    mode = "concise_reinforcement"
    reason = "Expressao mantida em reforco conciso para preservar clareza local."
    transition_reason = "O bloco atual manteve framing enxuto e estavel."

    if micro_intervention == "cumulative_bridge" or narrative_relation == "cumulative_resurfacing":
        mode = "cumulative_reactivation"
        reason = "O bloco cumulativo recebeu reativacao textual mais suave e conectiva."
        transition_reason = "A revisita cumulativa foi apresentada com ponte curta para reduzir atrito."
    elif cognitive_momentum == "retrieval_heavy" and retrieval_intensity == "high":
        mode = "retrieval_softener"
        reason = "A sessao acumulou recuperacao intensa e pediu framing menos abrupto."
        transition_reason = "A recuperacao foi suavizada para manter ritmo sem perder pressao."
    elif cognitive_momentum in {"pressured", "conceptually_dense"} and pedagogical_mode in {
        "guided_explanation",
        "conceptual_reinforcement",
    }:
        mode = "conceptual_clarifier"
        reason = "A densidade conceitual alta pediu explicacao mais segmentada e direta."
        transition_reason = "A explicacao foi clarificada para reduzir friccao conceitual."
    elif trajectory_state in {"reconstruction_fragile", "superficially_stable"}:
        mode = "focused_reconstruction"
        reason = "A trajetoria ainda pede reconstrucao mais focal do que mera confirmacao."
        transition_reason = "A expressao foi focada para testar a cadeia do raciocinio com menos ruido."
    elif trajectory_state == "transfer_fragile" or dominant_facet == "contextual_transfer":
        mode = "contextual_bridge"
        reason = "A transferencia contextual ganhou ponte de leitura para sustentar continuidade."
        transition_reason = "A passagem entre contextos foi ancorada para evitar quebra local."
    elif narrative_relation in {"application", "continuation", "reinforcement"} and curriculum_role == "active":
        mode = "progressive_anchor"
        reason = "A progressao ativa ganhou ancora curta para reforcar sensacao de trilha."
        transition_reason = "A passagem local foi ancorada para manter progressao perceptivel."
    elif cognitive_momentum == "continuity_fragile":
        mode = "transition_smoother"
        reason = "A continuidade local enfraqueceu e pediu uma transicao mais suave."
        transition_reason = "A mudanca de foco foi suavizada para preservar coerencia."
    elif cognitive_momentum == "balanced" and curriculum_role == "cumulative":
        mode = "stabilization_reassurance"
        reason = "O bloco estavel recebeu framing de manutencao leve e confiante."
        transition_reason = "A revisao foi apresentada como confirmacao sustentavel do dominio."
    elif cognitive_load == "high" and block_type == "summary":
        mode = "pacing_relief"
        reason = "A carga alta pediu compressao e alivio local de pacing."
        transition_reason = "O bloco foi condensado para melhorar conforto cognitivo."

    return PedagogicalExpressionProfile(
        pedagogical_expression_mode=mode,
        expression_reasoning=[
            f"Modo de expressao: {mode}.",
            reason,
            f"Momentum local: {cognitive_momentum or 'stable'}.",
        ],
        readability_adjustment=_readability_adjustment(mode),
        pacing_adjustment=_pacing_adjustment(mode),
        continuity_support=_continuity_support(mode),
        retrieval_framing=_retrieval_framing(mode),
        explanation_density=_explanation_density(mode, cognitive_load=cognitive_load, review_intensity=review_intensity),
        cognitive_friction_reduction=_friction_reduction(mode),
        transition_support_reason=transition_reason,
        why_this_expression_now=_why_this_expression_now(mode),
    )


def expression_family(mode: str | None) -> str:
    mode = str(mode or "")
    return {
        "concise_reinforcement": "reinforcement",
        "progressive_anchor": "progression",
        "contextual_bridge": "continuity",
        "retrieval_softener": "retrieval",
        "conceptual_clarifier": "clarity",
        "transition_smoother": "continuity",
        "pacing_relief": "relief",
        "focused_reconstruction": "reconstruction",
        "cumulative_reactivation": "cumulative",
        "stabilization_reassurance": "stabilization",
    }.get(mode, "neutral")


def _readability_adjustment(mode: str) -> float:
    return {
        "conceptual_clarifier": 0.76,
        "pacing_relief": 0.74,
        "transition_smoother": 0.68,
        "retrieval_softener": 0.62,
        "contextual_bridge": 0.58,
        "progressive_anchor": 0.55,
        "cumulative_reactivation": 0.52,
        "focused_reconstruction": 0.5,
        "stabilization_reassurance": 0.48,
        "concise_reinforcement": 0.42,
    }.get(mode, 0.4)


def _pacing_adjustment(mode: str) -> float:
    return {
        "pacing_relief": 0.78,
        "retrieval_softener": 0.72,
        "transition_smoother": 0.68,
        "cumulative_reactivation": 0.6,
        "stabilization_reassurance": 0.54,
        "progressive_anchor": 0.5,
        "conceptual_clarifier": 0.46,
        "contextual_bridge": 0.42,
        "focused_reconstruction": 0.4,
        "concise_reinforcement": 0.34,
    }.get(mode, 0.3)


def _continuity_support(mode: str) -> float:
    return {
        "contextual_bridge": 0.78,
        "progressive_anchor": 0.7,
        "transition_smoother": 0.68,
        "cumulative_reactivation": 0.66,
        "stabilization_reassurance": 0.52,
        "conceptual_clarifier": 0.46,
        "retrieval_softener": 0.4,
        "focused_reconstruction": 0.38,
        "pacing_relief": 0.34,
        "concise_reinforcement": 0.28,
    }.get(mode, 0.3)


def _retrieval_framing(mode: str) -> float:
    return {
        "retrieval_softener": 0.82,
        "focused_reconstruction": 0.66,
        "stabilization_reassurance": 0.56,
        "cumulative_reactivation": 0.52,
        "contextual_bridge": 0.44,
        "progressive_anchor": 0.42,
        "concise_reinforcement": 0.34,
        "conceptual_clarifier": 0.3,
        "transition_smoother": 0.28,
        "pacing_relief": 0.24,
    }.get(mode, 0.3)


def _explanation_density(mode: str, *, cognitive_load: str, review_intensity: str) -> float:
    base = {
        "conceptual_clarifier": 0.58,
        "focused_reconstruction": 0.52,
        "contextual_bridge": 0.46,
        "progressive_anchor": 0.42,
        "cumulative_reactivation": 0.36,
        "stabilization_reassurance": 0.3,
        "retrieval_softener": 0.26,
        "transition_smoother": 0.28,
        "pacing_relief": 0.24,
        "concise_reinforcement": 0.22,
    }.get(mode, 0.24)
    if cognitive_load == "high":
        base -= 0.04
    if review_intensity == "deep" and mode in {"conceptual_clarifier", "focused_reconstruction"}:
        base += 0.08
    return _clamp(base)


def _friction_reduction(mode: str) -> float:
    return {
        "transition_smoother": 0.74,
        "pacing_relief": 0.72,
        "retrieval_softener": 0.68,
        "conceptual_clarifier": 0.62,
        "contextual_bridge": 0.58,
        "cumulative_reactivation": 0.54,
        "focused_reconstruction": 0.48,
        "stabilization_reassurance": 0.42,
        "progressive_anchor": 0.38,
        "concise_reinforcement": 0.34,
    }.get(mode, 0.3)


def _why_this_expression_now(mode: str) -> str:
    return {
        "concise_reinforcement": "A expressao foi mantida enxuta para reforco direto sem ruido.",
        "progressive_anchor": "A expressao ganhou ancora curta para manter sensacao de progressao.",
        "contextual_bridge": "A expressao ganhou ponte curta para sustentar continuidade entre contextos.",
        "retrieval_softener": "A expressao foi suavizada para reduzir brusquidao de recuperacao.",
        "conceptual_clarifier": "A expressao foi clarificada para reduzir densidade desnecessaria.",
        "transition_smoother": "A expressao foi suavizada para preservar continuidade local.",
        "pacing_relief": "A expressao foi condensada para aliviar pressao cognitiva.",
        "focused_reconstruction": "A expressao foi focada para reconstruir sem verbosidade extra.",
        "cumulative_reactivation": "A expressao retomou o ponto cumulativo com framing mais leve.",
        "stabilization_reassurance": "A expressao sinaliza manutencao estavel sem peso excessivo.",
    }.get(mode, "A expressao foi mantida em faixa neutra e estavel.")


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
