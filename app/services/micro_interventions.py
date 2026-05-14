from __future__ import annotations

from app.domain.models import (
    InterventionContext,
    InterventionSignal,
    MicroIntervention,
    MicroInterventionType,
)


def resolve_micro_intervention(
    *,
    block_type: str,
    curriculum_role: str | None,
    review_intensity: str | None,
    pedagogical_profile: dict[str, object] | object,
    relationship_signal: dict[str, object] | None,
    facet_profile: dict[str, object] | object | None = None,
    trajectory_profile: dict[str, object] | object | None = None,
) -> MicroIntervention:
    profile = _normalize_profile(pedagogical_profile)
    relationship = dict(relationship_signal or {})
    facets = _normalize_profile(facet_profile)
    trajectory = _normalize_profile(trajectory_profile)
    context = InterventionContext(
        block_type="question" if block_type == "questions" else block_type,
        curriculum_role=str(curriculum_role or "active"),
        review_intensity=str(review_intensity or "light"),
        pedagogical_mode=str(profile.get("pedagogical_mode") or "reinforcement_check"),
        explanation_depth=str(profile.get("explanation_depth") or "light"),
        retrieval_intensity=str(profile.get("retrieval_intensity") or "low"),
        stabilization_stage=str(profile.get("stabilization_stage") or "unstable"),
        longitudinal_retention=_clamp(float(profile.get("longitudinal_retention", 0.0) or 0.0)),
        intervention_fatigue=_clamp(float(profile.get("intervention_fatigue", 0.0) or 0.0)),
        relationship_type=str(relationship.get("relationship_type") or "") or None,
        prerequisite_signal=_clamp(float(relationship.get("prerequisite_signal", 0.0) or 0.0)),
        conceptual_anchor=str(relationship.get("conceptual_anchor") or "") or None,
    )
    return _resolve_from_context(context, facets, trajectory)


def _resolve_from_context(
    context: InterventionContext,
    facets: dict[str, object],
    trajectory: dict[str, object],
) -> MicroIntervention:
    dominant_facet = str(facets.get("dominant_facet") or "")
    transfer_signal = _clamp(float(facets.get("transfer_signal", 0.0) or 0.0))
    reconstruction_signal = _clamp(float(facets.get("reconstruction_signal", 0.0) or 0.0))
    recognition_signal = _clamp(float(facets.get("recognition_signal", 0.0) or 0.0))
    trajectory_state = str(trajectory.get("trajectory_state") or "")
    false_fluency = _clamp(float(trajectory.get("false_fluency_signal", 0.0) or 0.0))
    trajectory_reconstruction = _clamp(float(trajectory.get("reconstruction_fragility", 0.0) or 0.0))
    trajectory_transfer = _clamp(float(trajectory.get("transfer_fragility", 0.0) or 0.0))

    if context.relationship_type == "applied_by" and context.prerequisite_signal >= 0.45:
        return _build_intervention(
            MicroInterventionType.PREREQUISITE_RECALL,
            "A aplicacao pede uma ancora conceitual imediata antes da recuperacao contextual.",
            "Reativar rapidamente a base necessaria para a aplicacao.",
            retrieval_support_reason="A lembranca da regra-base reduz erro de contexto na aplicacao.",
            conceptual_support_reason=_anchor_reason(context, "A regra-base precisa reaparecer brevemente antes da aplicacao."),
            intervention_transition="foundation_before_application",
            why_this_intervention="Este momento ganhou um lembrete de prerequisito para sustentar a transferencia do conceito.",
            local_cognitive_strategy="Relembrar a base, depois julgar a aplicacao.",
            support_strength=0.68,
            retrieval_shift=0.44,
            fatigue_mitigation=0.08,
        )

    if context.relationship_type == "exception_of" and context.prerequisite_signal >= 0.35:
        return _build_intervention(
            MicroInterventionType.EXCEPTION_ALIGNMENT,
            "A excecao precisa ser reconciliada com a regra base antes do julgamento fino.",
            "Alinhar regra e excecao para evitar leitura isolada da ressalva.",
            retrieval_support_reason="A recuperacao da regra reduz erro por excecao fora de contexto.",
            conceptual_support_reason=_anchor_reason(context, "A excecao depende da regra-base imediatamente anterior."),
            intervention_transition="rule_before_exception",
            why_this_intervention="Este momento recebeu alinhamento de excecao para preservar contraste sem perder a base.",
            local_cognitive_strategy="Confirmar a regra-base e depois ajustar pela excecao.",
            support_strength=0.62,
            retrieval_shift=0.28,
            fatigue_mitigation=0.06,
        )

    if context.relationship_type == "cumulative_extension" and context.curriculum_role == "cumulative":
        return _build_intervention(
            MicroInterventionType.CUMULATIVE_BRIDGE,
            "O microtopico reapareceu como ponte cumulativa para manter continuidade leve.",
            "Conectar um reaparecimento antigo ao contexto atual com baixo custo cognitivo.",
            retrieval_support_reason="A ponte cumulativa sustenta recall sem reabrir explicacao longa.",
            conceptual_support_reason=_anchor_reason(context, "O ponto reaparece ligado a uma ancora cumulativa ja conhecida."),
            intervention_transition="cumulative_reactivation",
            why_this_intervention="Este momento recebeu uma ponte cumulativa para manter retencao ampla sem sobrecarga.",
            local_cognitive_strategy="Fazer recall curto e manter a trilha cumulativa ativa.",
            support_strength=0.42,
            retrieval_shift=0.38,
            fatigue_mitigation=0.18,
        )

    if (
        trajectory_state == "transfer_fragile"
        and dominant_facet in {"application", "contextual_transfer"}
        and trajectory_transfer >= 0.5
    ):
        return _build_intervention(
            MicroInterventionType.CUMULATIVE_BRIDGE,
            "A transferencia contextual ainda oscila e ganhou uma ponte mais explicita.",
            "Sustentar o salto entre contextos antes de exigir resposta independente.",
            retrieval_support_reason="A ponte reduz colapso de contexto em reapresentacoes sucessivas.",
            conceptual_support_reason="A transferencia continua ligada a uma base anterior antes do julgamento atual.",
            intervention_transition="transfer_fragility_bridge",
            why_this_intervention="Este momento recebeu uma ponte mais forte porque a trajetoria ainda mostra fragilidade de transferencia.",
            local_cognitive_strategy="Recuperar o contexto-base e so depois mover a regra.",
            support_strength=0.46,
            retrieval_shift=0.34,
            fatigue_mitigation=0.16,
        )

    if (
        trajectory_state in {"reconstruction_fragile", "superficially_stable"}
        and (
            trajectory_reconstruction >= 0.45
            or (dominant_facet == "recognition" and false_fluency >= 0.48)
        )
    ):
        return _build_intervention(
            MicroInterventionType.GUIDED_RECONSTRUCTION,
            "A trajetoria indica que reconhecer rapido ainda nao garante reconstrucao estavel.",
            "Reconstruir o encadeamento central antes de confiar no acerto superficial.",
            retrieval_support_reason="A reconstrucao guiada checa se o acerto recente se sustenta sem pista forte.",
            conceptual_support_reason="O bloco pede validar a sequencia do raciocinio, nao apenas o marcador final.",
            intervention_transition="trajectory_reconstruction_check",
            why_this_intervention="Este momento recebeu reconstrucao guiada porque a trajetoria sugere fluencia superficial ou reconstrucao fragil.",
            local_cognitive_strategy="Refazer a cadeia do raciocinio antes de aceitar a resposta como dominada.",
            support_strength=0.48,
            retrieval_shift=0.22,
            fatigue_mitigation=0.1,
        )

    if (
        dominant_facet == "contextual_transfer"
        and transfer_signal >= 0.55
        and context.block_type == "question"
        and context.curriculum_role == "cumulative"
    ):
        return _build_intervention(
            MicroInterventionType.CUMULATIVE_BRIDGE,
            "A transferencia contextual reapareceu como ponte cumulativa para reativar comparacoes anteriores.",
            "Sustentar transferencia entre contextos com baixo atrito cumulativo.",
            retrieval_support_reason="A ponte cumulativa preserva o contexto antes do novo julgamento.",
            intervention_transition="contextual_bridge",
            why_this_intervention="Este momento ganhou uma ponte cumulativa porque a faceta dominante ainda depende de contexto transferido.",
            local_cognitive_strategy="Reconectar o contexto anterior antes de decidir no contexto atual.",
            support_strength=0.4,
            retrieval_shift=0.36,
            fatigue_mitigation=0.2,
        )

    if context.stabilization_stage in {"consolidated", "resilient"} and context.longitudinal_retention >= 0.5:
        if context.block_type == "question":
            if recognition_signal >= 0.35:
                support_reason = "A verificacao foi reduzida a reconhecimento rapido porque o traço ja parece estavel."
            else:
                support_reason = "A pergunta funciona como confirmacao leve de dominio."
            return _build_intervention(
                MicroInterventionType.CONFIDENCE_CHECK,
                "O conceito ja mostra estabilidade suficiente para um cheque rapido de confianca.",
                "Verificar retencao sem reabrir explicacao densa.",
                retrieval_support_reason=support_reason,
                intervention_transition="stability_check",
                why_this_intervention="Este momento usa um cheque de confianca para evitar reforco excessivo.",
                local_cognitive_strategy="Confirmar rapidamente o ponto central sem apoio pesado.",
                support_strength=0.22,
                retrieval_shift=0.26,
                fatigue_mitigation=0.3,
            )
        return _build_intervention(
            MicroInterventionType.LIGHTWEIGHT_RETRIEVAL,
            "O conceito estabilizado reaparece em formato mais leve para manter sustentabilidade.",
            "Reativar o ponto com baixo custo e alta legibilidade.",
            retrieval_support_reason="A reativacao leve preserva o traço sem densidade desnecessaria.",
            intervention_transition="light_reactivation",
            why_this_intervention="Este momento foi suavizado porque a retencao ja parece longitudinalmente estavel.",
            local_cognitive_strategy="Ler de forma enxuta e testar lembranca sem aprofundamento extra.",
            support_strength=0.18,
            retrieval_shift=0.34,
            fatigue_mitigation=0.34,
        )

    if dominant_facet == "recognition" and recognition_signal >= 0.45:
        return _build_intervention(
            MicroInterventionType.VERIFICATION_STEP,
            "A faceta local pede verificacao curta por reconhecimento, sem expandir densidade.",
            "Checar rapidamente o marcador certo antes do julgamento final.",
            retrieval_support_reason="O reconhecimento rapido reduz custo cognitivo quando a faceta ja esta bem delimitada.",
            intervention_transition="recognition_check",
            why_this_intervention="Este momento recebeu uma verificacao curta porque o foco atual e mais de reconhecimento do que de reconstrucao.",
            local_cognitive_strategy="Reconhecer o marcador central antes da decisao final.",
            support_strength=0.16,
            retrieval_shift=0.18,
            fatigue_mitigation=0.18,
        )

    if dominant_facet == "reconstruction" and reconstruction_signal >= 0.45:
        return _build_intervention(
            MicroInterventionType.GUIDED_RECONSTRUCTION,
            "A faceta local pede reconstrucao do encadeamento antes do detalhe final.",
            "Refazer a sequencia logica do microtopico antes da resposta.",
            conceptual_support_reason="A reconstrucao guiada melhora o encaixe entre etapas do raciocinio.",
            intervention_transition="facet_reconstruction",
            why_this_intervention="Este momento foi empurrado para reconstrucao guiada porque a faceta dominante exige recompor a logica.",
            local_cognitive_strategy="Reconstituir a ordem do raciocinio antes de decidir.",
            support_strength=0.44,
            retrieval_shift=0.2,
            fatigue_mitigation=0.08,
        )

    if context.pedagogical_mode == "guided_explanation":
        return _build_intervention(
            MicroInterventionType.GUIDED_RECONSTRUCTION,
            "A explicacao principal foi mantida com reconstrucao guiada do encadeamento conceitual.",
            "Reconstruir passo a passo a logica do microtopico.",
            conceptual_support_reason="A reconstrucao guiada melhora a consolidacao do raciocinio-base.",
            intervention_transition="guided_density",
            why_this_intervention="Este momento recebeu reconstrucao guiada porque a carga explicativa ainda e util.",
            local_cognitive_strategy="Refazer mentalmente a cadeia do conceito antes de responder.",
            support_strength=0.46,
            retrieval_shift=0.18,
            fatigue_mitigation=0.05,
        )

    if context.pedagogical_mode == "active_recall":
        return _build_intervention(
            MicroInterventionType.SEMANTIC_REACTIVATION,
            "A recuperacao ativa foi refinada para reativar o nucleo semantico com pouco apoio.",
            "Puxar a conexao central do microtopico antes do julgamento.",
            retrieval_support_reason="A reativacao semantica curta melhora recuperacao sem expandir a explicacao.",
            intervention_transition="reactivation_step",
            why_this_intervention="Este momento recebeu reativacao semantica para melhorar reconstrucao com pouca pista.",
            local_cognitive_strategy="Buscar primeiro a ideia central, depois validar o detalhe.",
            support_strength=0.34,
            retrieval_shift=0.4,
            fatigue_mitigation=0.1,
        )

    if context.pedagogical_mode in {"rapid_review", "reinforcement_check"}:
        return _build_intervention(
            MicroInterventionType.RAPID_ANCHOR,
            "A revisao leve recebeu uma ancora curta para preservar orientacao conceitual.",
            "Fixar rapidamente o ponto de partida antes da verificacao.",
            retrieval_support_reason="A ancora curta reduz erro por desorientacao em blocos leves.",
            intervention_transition="quick_anchor",
            why_this_intervention="Este momento ganhou uma ancora curta para manter fluidez sem aumentar densidade.",
            local_cognitive_strategy="Fixar a palavra-chave e responder com economia cognitiva.",
            support_strength=0.2,
            retrieval_shift=0.22,
            fatigue_mitigation=0.2,
        )

    return _build_intervention(
        MicroInterventionType.VERIFICATION_STEP,
        "Foi aplicado um passo simples de verificacao para manter precisao local.",
        "Checar o detalhe decisivo sem alterar a estrategia principal do bloco.",
        retrieval_support_reason="Uma verificacao curta ajuda a reduzir lapsos sem expandir o bloco.",
        intervention_transition="verification",
        why_this_intervention="Este momento recebeu uma verificacao leve para preservar precisao com baixa interferencia.",
        local_cognitive_strategy="Conferir o detalhe-chave antes do julgamento final.",
        support_strength=0.14,
        retrieval_shift=0.16,
        fatigue_mitigation=0.12,
    )


def _build_intervention(
    intervention_type: MicroInterventionType,
    intervention_reason: str,
    cognitive_goal: str,
    *,
    retrieval_support_reason: str | None = None,
    conceptual_support_reason: str | None = None,
    intervention_transition: str | None = None,
    why_this_intervention: str,
    local_cognitive_strategy: str,
    support_strength: float,
    retrieval_shift: float,
    fatigue_mitigation: float,
) -> MicroIntervention:
    return MicroIntervention(
        intervention_type=intervention_type.value,
        intervention_reason=intervention_reason,
        cognitive_goal=cognitive_goal,
        retrieval_support_reason=retrieval_support_reason,
        conceptual_support_reason=conceptual_support_reason,
        intervention_transition=intervention_transition,
        why_this_intervention=why_this_intervention,
        local_cognitive_strategy=local_cognitive_strategy,
        intervention_signal=InterventionSignal(
            support_strength=_clamp(support_strength),
            retrieval_shift=_clamp(retrieval_shift),
            fatigue_mitigation=_clamp(fatigue_mitigation),
        ),
    )


def _anchor_reason(context: InterventionContext, fallback: str) -> str:
    if context.conceptual_anchor:
        return f"{fallback} Ancora atual: {context.conceptual_anchor}."
    return fallback


def _normalize_profile(profile: dict[str, object] | object) -> dict[str, object]:
    if hasattr(profile, "model_dump"):
        return profile.model_dump(mode="json")
    if isinstance(profile, dict):
        return dict(profile)
    return {}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
