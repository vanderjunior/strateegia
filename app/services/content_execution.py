from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from app.domain.models import LearningPlanEntry, MicroTopic, StudyBlock, TopicNode
from app.services.conceptual_relationships import (
    ConceptualRelationshipsLayer,
    build_relationship_signals,
)
from app.services.learning_engine import compute_microtopic_priority
from app.services.microtopic_extractor import MicroTopicExtractor
from app.services.pedagogical_adapter import resolve_pedagogical_profile


REVIEW_STAGE_WEIGHTS = {
    "deep": {
        "weakness": 0.45,
        "resurfacing": 0.15,
        "difficulty": 0.20,
        "cumulative": 0.20,
    },
    "medium": {
        "weakness": 0.35,
        "resurfacing": 0.20,
        "difficulty": 0.15,
        "cumulative": 0.30,
    },
    "light": {
        "weakness": 0.20,
        "resurfacing": 0.20,
        "difficulty": 0.10,
        "cumulative": 0.50,
    },
}
MICROTOPIC_PRIORITY_CAP = 1.5
RESURFACING_DAYS_CAP = 14.0


def execute_study_block(block: StudyBlock) -> dict:
    topic_node = block.topic_node
    topic_name = _resolve_topic_name(block.topic_id, topic_node)
    review_stage = _resolve_review_stage(block)
    selection = select_relevant_microtopics(
        topic_node,
        block.microtopic_performance,
        block.pedagogical_memory,
        review_stage,
        limit=_resolve_selection_limit(block, review_stage),
        fallback_topic_id=block.topic_id,
        selected_microtopic_ids=block.selected_microtopic_ids,
    )
    selected_microtopics = selection["selected_microtopics"]
    pedagogical_profile = _resolve_pedagogical_profile(block, selection)
    pedagogical_metadata = _pedagogical_metadata(pedagogical_profile)

    if block.type == "summary":
        depth = block.depth or "light"
        return {
            "type": "summary",
            "topic_id": block.topic_id,
            "depth": depth,
            "content": _generate_summary_content(
                topic_name,
                depth,
                selected_microtopics,
                pedagogical_profile,
            ),
            **_selection_metadata(selection),
            **pedagogical_metadata,
        }
    if block.type == "questions":
        quantity = max(1, int(block.quantity or 1))
        return {
            "type": "questions",
            "topic_id": block.topic_id,
            "questions": _generate_questions(
                topic_name,
                selected_microtopics,
                quantity,
                pedagogical_profile,
            ),
            **_selection_metadata(selection),
            **pedagogical_metadata,
        }
    raise ValueError(f"Unsupported study block type: {block.type}")


def execute_learning_plan(plan: list[LearningPlanEntry]) -> list[dict]:
    executed_session: list[dict] = []
    for entry in plan:
        for block in entry.study_blocks:
            executed_session.append(execute_study_block(block))
    return executed_session


def select_relevant_microtopics(
    topic_node: TopicNode | None,
    microtopic_performance: dict[str, dict[str, object]] | None,
    pedagogical_memory: dict[str, dict[str, object]] | None,
    review_stage: str,
    *,
    limit: int,
    fallback_topic_id: str = "",
    selected_microtopic_ids: list[str] | None = None,
) -> dict[str, object]:
    microtopics = _resolve_microtopics(fallback_topic_id, topic_node)
    if not microtopics:
        return {
            "selected_microtopics": [],
            "resurfaced_microtopics": [],
            "weak_microtopics": [],
            "review_intensity": review_stage,
            "adaptive_reasoning": ["Nenhum microtopico encontrado; fallback seguro aplicado."],
            "why_this_now": ["Nao havia microtopicos estruturados; o bloco foi mantido por compatibilidade."],
            "selected_profiles": [],
        }

    preferred_ids = set(selected_microtopic_ids or [])
    if preferred_ids and limit == 1:
        selected_ids = set(selected_microtopic_ids)
        microtopics = [microtopic for microtopic in microtopics if microtopic.id in selected_ids] or microtopics

    performance_map = dict(microtopic_performance or {})
    pedagogical_memory_map = dict(pedagogical_memory or {})
    relationships = ConceptualRelationshipsLayer().extract(topic_node, microtopics)
    relationship_signals = build_relationship_signals(microtopics, relationships)
    profiles = [
        _build_microtopic_profile(
            microtopic,
            performance_map.get(microtopic.id),
            pedagogical_memory_map.get(microtopic.id),
            review_stage,
            relationship_signals.get(microtopic.id),
            preferred=microtopic.id in preferred_ids,
        )
        for microtopic in microtopics
    ]
    ranked_profiles = sorted(
        profiles,
        key=lambda profile: (
            -profile["selection_score"],
            -profile["difficulty_weight"],
            profile["position"],
            profile["microtopic"].id,
        ),
    )

    selected_profiles = _choose_profiles(
        ranked_profiles,
        review_stage=review_stage,
        limit=max(1, limit),
        preferred_ids=preferred_ids,
    )
    if preferred_ids:
        selected_profiles = _apply_conceptual_support(
            selected_profiles,
            ranked_profiles,
            limit=max(1, limit),
        )
    weak_profiles = [profile for profile in ranked_profiles if profile["is_weak"]]
    resurfaced_profiles = [profile for profile in selected_profiles if profile["is_resurfaced"]]
    selected_ids = {profile["microtopic"].id for profile in selected_profiles}

    return {
        "selected_microtopics": [profile["microtopic"] for profile in selected_profiles],
        "resurfaced_microtopics": [profile["microtopic"] for profile in resurfaced_profiles],
        "weak_microtopics": [profile["microtopic"] for profile in weak_profiles],
        "review_intensity": review_stage,
        "adaptive_reasoning": _build_adaptive_reasoning(
            review_stage=review_stage,
            selected_profiles=selected_profiles,
            weak_profiles=weak_profiles,
            resurfaced_profiles=resurfaced_profiles,
        ),
        "why_this_now": _build_why_this_now(selected_profiles, review_stage=review_stage),
        "selected_profiles": selected_profiles,
        "relationship_signal": _primary_relationship_signal(selected_profiles),
        "conceptual_relationships": [
            relationship.model_dump(mode="json")
            for relationship in relationships
            if relationship.source_microtopic_id in selected_ids
            and relationship.target_microtopic_id in selected_ids
        ],
    }


def _resolve_microtopics(topic_id: str, topic_node: TopicNode | None) -> list[MicroTopic]:
    if topic_node is None:
        return _fallback_microtopics(topic_id=topic_id, topic_name=_humanize_topic_id(topic_id), content="")

    extracted = MicroTopicExtractor().extract(topic_node)
    if extracted:
        return extracted
    return _fallback_microtopics(
        topic_id=topic_id,
        topic_name=topic_node.title,
        content=topic_node.content,
    )


def _fallback_microtopics(topic_id: str, topic_name: str, content: str) -> list[MicroTopic]:
    fallback_content = _normalize_text(content) or (
        f"Regra central e ponto de prova sobre {_humanize_topic_id(topic_id)}."
    )
    return [
        MicroTopic(
            id=f"fallback-{topic_id or 'tema'}",
            title=topic_name or _humanize_topic_id(topic_id),
            content=fallback_content,
            source_topic_title=topic_name or _humanize_topic_id(topic_id),
            difficulty_weight=1.0,
        )
    ]


def _resolve_selection_limit(block: StudyBlock, review_stage: str) -> int:
    if block.type == "summary":
        return _summary_limit(block.depth or review_stage)
    return max(1, int(block.quantity or 1))


def _summary_limit(depth: str) -> int:
    if depth == "deep":
        return 3
    if depth == "medium":
        return 2
    return 1


def _resolve_review_stage(block: StudyBlock) -> str:
    if block.type == "summary":
        return block.depth or "light"
    quantity = max(1, int(block.quantity or 1))
    if quantity >= 5:
        return "deep"
    if quantity >= 3:
        return "medium"
    return "light"


def _build_microtopic_profile(
    microtopic: MicroTopic,
    raw_performance: dict[str, object] | None,
    raw_pedagogical_memory: dict[str, object] | None,
    review_stage: str,
    relationship_signal: dict[str, object] | None,
    *,
    preferred: bool,
) -> dict[str, object]:
    performance = _normalize_microtopic_performance(raw_performance)
    pedagogical_memory = _normalize_pedagogical_memory(raw_pedagogical_memory)
    weights = REVIEW_STAGE_WEIGHTS[review_stage]
    total_questions = int(performance["total_questions"])
    correct_answers = int(performance["correct_answers"])
    recent_errors = int(performance["recent_errors"])
    consecutive_correct = int(performance["consecutive_correct"])
    consecutive_incorrect = int(performance["consecutive_incorrect"])
    accuracy = correct_answers / max(total_questions, 1)
    weakness_signal = min(
        compute_microtopic_priority(performance) / MICROTOPIC_PRIORITY_CAP,
        1.0,
    )
    resurfacing_signal = _resurfacing_signal(
        performance["last_reviewed_at"] or performance["last_seen_at"]
    )
    difficulty_signal = min(max(microtopic.difficulty_weight - 1.0, 0.0) / 0.4, 1.0)
    mastered = total_questions >= 3 and accuracy >= 0.75 and recent_errors == 0
    cumulative_signal = max(resurfacing_signal, 0.35 if mastered else 0.15)
    temporal_reinforcement = min(consecutive_incorrect * 0.12, 0.3)
    stabilization_discount = min(consecutive_correct * 0.05, 0.2)
    temporal_signal = _temporal_reinforcement_signal(
        resurfacing_signal=resurfacing_signal,
        pedagogical_memory=pedagogical_memory,
    )
    pedagogical_discount = min(pedagogical_memory["stabilization_level"] * 0.08, 0.08)
    pedagogical_escalation = min(pedagogical_memory["escalation_level"] * 0.10, 0.10)
    normalized_relationship = dict(relationship_signal or {})
    prerequisite_signal = min(
        max(float(normalized_relationship.get("prerequisite_signal", 0.0) or 0.0), 0.0),
        1.0,
    )
    support_signal = min(
        max(float(normalized_relationship.get("support_signal", 0.0) or 0.0), 0.0),
        1.0,
    )
    relationship_bonus = min(support_signal * 0.08 + prerequisite_signal * 0.05, 0.1)
    preferred_bonus = 0.12 if preferred else 0.0

    selection_score = (
        weakness_signal * weights["weakness"]
        + resurfacing_signal * weights["resurfacing"]
        + difficulty_signal * weights["difficulty"]
        + cumulative_signal * weights["cumulative"]
        + temporal_reinforcement
        + temporal_signal
        + pedagogical_escalation
        + relationship_bonus
        + preferred_bonus
        - stabilization_discount
        - pedagogical_discount
    )
    if mastered and review_stage == "light":
        selection_score += 0.08

    return {
        "microtopic": microtopic,
        "selection_score": round(selection_score, 6),
        "weakness_signal": round(weakness_signal, 6),
        "resurfacing_signal": round(resurfacing_signal, 6),
        "difficulty_weight": microtopic.difficulty_weight,
        "temporal_signal": round(temporal_signal, 6),
        "is_mastered": mastered,
        "is_weak": recent_errors > 0 or weakness_signal >= 0.6 or consecutive_incorrect >= 2,
        "is_resurfaced": (mastered and resurfacing_signal >= 0.5) or temporal_signal >= 0.12,
        "relationship_signal": normalized_relationship,
        "preferred": preferred,
        "position": 0,
    }


def _choose_profiles(
    ranked_profiles: list[dict[str, object]],
    *,
    review_stage: str,
    limit: int,
    preferred_ids: set[str],
) -> list[dict[str, object]]:
    for position, profile in enumerate(ranked_profiles):
        profile["position"] = position

    weak_profiles = [profile for profile in ranked_profiles if profile["is_weak"]]
    resurfaced_profiles = [profile for profile in ranked_profiles if profile["is_resurfaced"]]

    selected: list[dict[str, object]] = []
    weak_quota = {
        "deep": max(1, ceil(limit * 0.6)),
        "medium": max(1, ceil(limit * 0.5)),
        "light": 0,
    }[review_stage]

    if review_stage == "light" and resurfaced_profiles:
        selected.append(resurfaced_profiles[0])
    else:
        selected.extend(weak_profiles[:weak_quota])

    if len(selected) < limit and resurfaced_profiles and not any(
        profile["microtopic"].id == resurfaced_profiles[0]["microtopic"].id for profile in selected
    ):
        selected.append(resurfaced_profiles[0])

    for profile in ranked_profiles:
        if len(selected) >= limit:
            break
        if any(profile["microtopic"].id == chosen["microtopic"].id for chosen in selected):
            continue
        selected.append(profile)

    for preferred_id in preferred_ids:
        if any(profile["microtopic"].id == preferred_id for profile in selected):
            continue
        preferred_profile = next(
            (profile for profile in ranked_profiles if profile["microtopic"].id == preferred_id),
            None,
        )
        if preferred_profile is None:
            continue
        if len(selected) < limit:
            selected.append(preferred_profile)
        else:
            selected[-1] = preferred_profile

    return selected[:limit]


def _apply_conceptual_support(
    selected_profiles: list[dict[str, object]],
    ranked_profiles: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    if limit <= 1 or not selected_profiles:
        return selected_profiles

    by_id = {profile["microtopic"].id: profile for profile in ranked_profiles}
    selected = list(selected_profiles)
    selected_ids = {profile["microtopic"].id for profile in selected}

    for profile in list(selected_profiles):
        relationship_signal = dict(profile.get("relationship_signal", {}) or {})
        anchor_id = relationship_signal.get("anchor_microtopic_id")
        prerequisite_signal = float(relationship_signal.get("prerequisite_signal", 0.0) or 0.0)
        if not anchor_id or prerequisite_signal < 0.3 or anchor_id in selected_ids:
            continue
        anchor_profile = by_id.get(anchor_id)
        if anchor_profile is None:
            continue
        insertion_index = selected.index(profile)
        selected.insert(insertion_index, anchor_profile)
        selected_ids.add(anchor_id)

    deduped: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for profile in selected:
        microtopic_id = profile["microtopic"].id
        if microtopic_id in seen_ids:
            continue
        seen_ids.add(microtopic_id)
        deduped.append(profile)
    return _relationship_order(deduped[:limit])


def _relationship_order(selected_profiles: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(selected_profiles) <= 1:
        return selected_profiles

    ordered = list(selected_profiles)
    index_by_id = {profile["microtopic"].id: index for index, profile in enumerate(ordered)}
    for profile in list(ordered):
        relationship_signal = dict(profile.get("relationship_signal", {}) or {})
        anchor_id = relationship_signal.get("anchor_microtopic_id")
        prerequisite_signal = float(relationship_signal.get("prerequisite_signal", 0.0) or 0.0)
        if not anchor_id or prerequisite_signal < 0.3:
            continue
        anchor_index = index_by_id.get(anchor_id)
        profile_index = index_by_id.get(profile["microtopic"].id)
        if anchor_index is None or profile_index is None or anchor_index < profile_index:
            continue
        ordered.insert(profile_index, ordered.pop(anchor_index))
        index_by_id = {item["microtopic"].id: index for index, item in enumerate(ordered)}
    return ordered


def _build_adaptive_reasoning(
    *,
    review_stage: str,
    selected_profiles: list[dict[str, object]],
    weak_profiles: list[dict[str, object]],
    resurfaced_profiles: list[dict[str, object]],
) -> list[str]:
    reasons = [f"Review intensity definida como {review_stage}."]
    if weak_profiles:
        reasons.append("Microtopicos com maior fragilidade receberam prioridade adicional.")
    if resurfaced_profiles:
        reasons.append("Conceitos dominados reapareceram para reforco cumulativo e deteccao de esquecimento.")
    if not weak_profiles:
        reasons.append("Sem fragilidade forte detectada; selecao equilibrada por dificuldade e resurfacing.")
    if selected_profiles:
        reasons.append(
            "Selecao final: "
            + ", ".join(profile["microtopic"].title for profile in selected_profiles)
            + "."
        )
    return reasons


def _selection_metadata(selection: dict[str, object]) -> dict[str, object]:
    relationship_signal = dict(selection.get("relationship_signal", {}) or {})
    return {
        "selected_microtopics": _serialize_microtopics(selection["selected_microtopics"]),
        "resurfaced_microtopics": _serialize_microtopics(selection["resurfaced_microtopics"]),
        "weak_microtopics": _serialize_microtopics(selection["weak_microtopics"]),
        "review_intensity": selection["review_intensity"],
        "adaptive_reasoning": selection["adaptive_reasoning"],
        "why_this_now": selection.get("why_this_now", []),
        "conceptual_relationships": selection.get("conceptual_relationships", []),
        "relationship_type": relationship_signal.get("relationship_type"),
        "relationship_reason": relationship_signal.get("relationship_reason"),
        "conceptual_anchor": relationship_signal.get("conceptual_anchor"),
        "prerequisite_signal": relationship_signal.get("prerequisite_signal", 0.0),
        "conceptual_transition": relationship_signal.get("conceptual_transition"),
        "semantic_continuity_reason": relationship_signal.get("semantic_continuity_reason"),
        "why_this_before_that": relationship_signal.get("why_this_before_that"),
    }


def _serialize_microtopics(microtopics: list[MicroTopic]) -> list[dict[str, object]]:
    return [
        {
            "id": microtopic.id,
            "title": microtopic.title,
            "difficulty_weight": microtopic.difficulty_weight,
        }
        for microtopic in microtopics
    ]


def _generate_summary_content(
    topic_name: str,
    depth: str,
    microtopics: list[MicroTopic],
    pedagogical_profile,
) -> str:
    if not microtopics:
        return (
            f"Visao rapida de {topic_name}: regra central, palavra-chave e ponto de maior risco em prova."
        )

    sections = [
        f"{microtopic.title}: {_short_content(microtopic.content)}"
        for microtopic in microtopics
    ]

    if pedagogical_profile.pedagogical_mode == "guided_explanation":
        return (
            f"Resumo aprofundado de {topic_name}: "
            + " ".join(
                f"{index + 1}. {section}" for index, section in enumerate(sections)
            )
            + " Compare a regra geral com a excecao aplicavel, destaque o contraste conceitual e observe o ponto que muda o julgamento. "
            + "Exemplo de prova: identifique qual detalhe normativo altera o resultado."
        )
    if pedagogical_profile.pedagogical_mode == "contextual_application":
        return (
            f"Resumo estruturado de {topic_name}: pontos de prova em contexto pratico. "
            + " ".join(sections)
            + " Priorize comparacoes entre cenarios e a condicao que muda a resposta."
        )
    if pedagogical_profile.pedagogical_mode == "active_recall":
        return f"Visao rapida de {topic_name}: relembre sem apoio total. " + " ".join(sections[: max(1, min(2, len(sections)))])
    if pedagogical_profile.pedagogical_mode in {"rapid_review", "reinforcement_check"}:
        return f"Visao rapida de {topic_name}: {sections[0]}"
    if depth == "deep":
        return (
            f"Resumo aprofundado de {topic_name}: "
            + " ".join(
                f"{index + 1}. {section}" for index, section in enumerate(sections)
            )
            + " Exemplo de prova: compare a regra geral com a excecao aplicavel e identifique o detalhe que altera o resultado."
        )
    if depth == "medium":
        return f"Resumo estruturado de {topic_name}: pontos de prova e focos especificos. " + " ".join(
            sections
        )
    return f"Visao rapida de {topic_name}: {sections[0]}"


def _generate_questions(
    topic_name: str,
    microtopics: list[MicroTopic],
    quantity: int,
    pedagogical_profile,
) -> list[dict]:
    selected = microtopics or _fallback_microtopics(
        topic_id=topic_name.lower().replace(" ", "-"),
        topic_name=topic_name,
        content="",
    )
    questions: list[dict] = []
    for index in range(quantity):
        microtopic = selected[index % len(selected)]
        focus = _short_content(microtopic.content)
        if pedagogical_profile.pedagogical_mode == "contextual_application":
            if index % 2 == 0:
                statement = (
                    f"Considere uma situacao pratica de {topic_name}: no microtopico {microtopic.title}, {focus.lower()}."
                )
                answer = True
                explanation = (
                    f"Certo. Em contexto aplicado, {microtopic.title} exige comparar cenarios e reconhecer que {focus}"
                )
            else:
                statement = (
                    f"Em {topic_name}, o microtopico {microtopic.title} pode ser aplicado sem diferenciar o contexto fatico relevante."
                )
                answer = False
                explanation = (
                    f"Errado. A leitura correta depende do contexto especifico de {microtopic.title}: {focus}"
                )
        elif pedagogical_profile.pedagogical_mode == "active_recall":
            if index % 2 == 0:
                statement = (
                    f"Recorde rapidamente em {topic_name}: no microtopico {microtopic.title}, {focus.lower()}."
                )
                answer = True
                explanation = f"Certo. A lembranca-chave de {microtopic.title} e: {focus}"
            else:
                statement = (
                    f"Em {topic_name}, o microtopico {microtopic.title} dispensa recuperacao precisa de seu detalhe central."
                )
                answer = False
                explanation = f"Errado. O detalhe central a recuperar em {microtopic.title} e: {focus}"
        elif index % 2 == 0:
            statement = (
                f"Em {topic_name}, no microtopico {microtopic.title}, deve-se considerar que {focus.lower()}."
            )
            answer = True
            explanation = (
                f"Certo. O foco de {microtopic.title} em {topic_name} e: {focus}"
            )
        else:
            statement = (
                f"Em {topic_name}, o microtopico {microtopic.title} pode ser resolvido sem analisar ressalvas especificas do ponto estudado."
            )
            answer = False
            explanation = (
                f"Errado. {microtopic.title} exige atencao ao seguinte recorte: {focus}"
            )
        questions.append(
            {
                "statement": statement,
                "answer": answer,
                "explanation": explanation,
                "microtopic_id": microtopic.id,
            }
        )
    return questions


def _resolve_pedagogical_profile(block: StudyBlock, selection: dict[str, object]):
    selected_profiles = selection.get("selected_profiles", []) or []
    primary_profile = selected_profiles[0] if selected_profiles else {}
    selected_microtopics = selection.get("selected_microtopics", []) or []
    primary_microtopic_id = selected_microtopics[0].id if selected_microtopics else None
    raw_performance = {}
    raw_pedagogical_memory = {}
    if primary_microtopic_id:
        raw_performance = dict((block.microtopic_performance or {}).get(primary_microtopic_id, {}) or {})
        raw_pedagogical_memory = dict((block.pedagogical_memory or {}).get(primary_microtopic_id, {}) or {})
    return resolve_pedagogical_profile(
        curriculum_role=block.curriculum_role,
        review_intensity=block.review_intensity or selection.get("review_intensity"),
        weakness_signal=float(primary_profile.get("weakness_signal", 0.0) or 0.0),
        resurfacing_signal=float(primary_profile.get("resurfacing_signal", 0.0) or 0.0),
        performance=raw_performance,
        pedagogical_memory=raw_pedagogical_memory,
        relationship_signal=selection.get("relationship_signal"),
    )


def _primary_relationship_signal(selected_profiles: list[dict[str, object]]) -> dict[str, object]:
    if not selected_profiles:
        return {}
    for profile in selected_profiles:
        relationship_signal = dict(profile.get("relationship_signal", {}) or {})
        if relationship_signal.get("relationship_type"):
            return relationship_signal
    return dict(selected_profiles[0].get("relationship_signal", {}) or {})


def _pedagogical_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_mode": profile.pedagogical_mode,
        "intervention_reason": profile.intervention_reason,
        "cognitive_load": profile.cognitive_load,
        "cognitive_load_score": profile.cognitive_load_score,
        "explanation_depth": profile.explanation_depth,
        "retrieval_intensity": profile.retrieval_intensity,
        "pedagogical_reasoning": profile.adaptation_reasoning or [profile.intervention_reason],
        "pedagogical_breakdown": profile.profile_breakdown,
        "intervention_transition_reason": profile.intervention_transition_reason,
        "pedagogical_confidence": profile.pedagogical_confidence,
        "intervention_effectiveness": profile.intervention_effectiveness,
        "pedagogical_stability": profile.pedagogical_stability,
        "stabilization_stage": profile.stabilization_stage,
        "longitudinal_retention": profile.longitudinal_retention,
        "intervention_fatigue": profile.intervention_fatigue,
        "reinforcement_reason": profile.reinforcement_reason,
        "fatigue_reason": profile.fatigue_reason,
        "stabilization_reasoning": profile.stabilization_reasoning,
        "retention_reasoning": profile.retention_reasoning,
        "recovery_signal": profile.recovery_signal,
        "intervention_history_summary": profile.intervention_history_summary,
        "adaptation_reasoning": profile.adaptation_reasoning,
    }


def _normalize_pedagogical_memory(raw_memory: dict[str, object] | None) -> dict[str, object]:
    memory = {
        "last_pedagogical_mode": None,
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "consecutive_failures": 0,
        "last_intervention_at": None,
        "stabilization_level": 0.0,
        "escalation_level": 0.0,
        "retrieval_success_trend": 0.5,
        "resurfacing_cycles": 0,
        "successful_resurfacing_cycles": 0,
        "fatigue_exposure": 0.0,
        "recovery_count": 0,
        "last_stabilized_at": None,
        "intervention_history": {},
    }
    if not raw_memory:
        return memory
    memory.update(raw_memory)
    memory["stabilization_level"] = max(0.0, min(float(memory.get("stabilization_level", 0.0) or 0.0), 1.0))
    memory["escalation_level"] = max(0.0, min(float(memory.get("escalation_level", 0.0) or 0.0), 1.0))
    memory["retrieval_success_trend"] = max(0.0, min(float(memory.get("retrieval_success_trend", 0.5) or 0.5), 1.0))
    memory["consecutive_successes"] = int(memory.get("consecutive_successes", 0) or 0)
    memory["consecutive_failures"] = int(memory.get("consecutive_failures", 0) or 0)
    memory["resurfacing_cycles"] = int(memory.get("resurfacing_cycles", 0) or 0)
    memory["successful_resurfacing_cycles"] = int(memory.get("successful_resurfacing_cycles", 0) or 0)
    memory["fatigue_exposure"] = max(0.0, min(float(memory.get("fatigue_exposure", 0.0) or 0.0), 1.0))
    memory["recovery_count"] = int(memory.get("recovery_count", 0) or 0)
    return memory


def _temporal_reinforcement_signal(
    *,
    resurfacing_signal: float,
    pedagogical_memory: dict[str, object],
) -> float:
    intervention_resurfacing = _resurfacing_signal(pedagogical_memory.get("last_intervention_at"))
    retrieval_decay = max(0.0, 0.55 - float(pedagogical_memory.get("retrieval_success_trend", 0.5) or 0.5))
    escalation = float(pedagogical_memory.get("escalation_level", 0.0) or 0.0)
    stability_discount = float(pedagogical_memory.get("stabilization_level", 0.0) or 0.0) * 0.05
    return max(
        0.0,
        min(
            0.18,
            max(resurfacing_signal, intervention_resurfacing) * 0.08
            + retrieval_decay * 0.10
            + escalation * 0.08
            - stability_discount,
        ),
    )


def _build_why_this_now(selected_profiles: list[dict[str, object]], *, review_stage: str) -> list[str]:
    if not selected_profiles:
        return ["Nenhum microtopico especifico disponivel; fallback seguro aplicado."]
    reasons = [f"Bloco acionado em intensidade {review_stage}."]
    primary = selected_profiles[0]
    if primary.get("weakness_signal", 0.0) >= 0.55:
        reasons.append("Fragilidade local elevou a prioridade deste microtopico agora.")
    elif primary.get("resurfacing_signal", 0.0) >= 0.5 or primary.get("temporal_signal", 0.0) >= 0.12:
        reasons.append("O microtopico reapareceu por resurfacing cumulativo e reforco temporal leve.")
    else:
        reasons.append("O microtopico entrou para manter variedade cognitiva e continuidade curricular.")
    return reasons


def _normalize_microtopic_performance(raw_performance: dict[str, object] | None) -> dict[str, object]:
    performance = {
        "total_questions": 0,
        "correct_answers": 0,
        "recent_errors": 0,
        "error_distribution": {
            "conceptual": 0,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        },
        "last_seen_at": None,
        "last_reviewed_at": None,
        "last_correct_at": None,
        "last_incorrect_at": None,
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
    }
    if not raw_performance:
        return performance

    performance["total_questions"] = int(raw_performance.get("total_questions", 0) or 0)
    performance["correct_answers"] = int(raw_performance.get("correct_answers", 0) or 0)
    performance["recent_errors"] = int(raw_performance.get("recent_errors", 0) or 0)
    distribution = dict(performance["error_distribution"])
    distribution.update(raw_performance.get("error_distribution", {}) or {})
    performance["error_distribution"] = distribution
    performance["last_seen_at"] = raw_performance.get("last_seen_at")
    performance["last_reviewed_at"] = raw_performance.get("last_reviewed_at")
    performance["last_correct_at"] = raw_performance.get("last_correct_at")
    performance["last_incorrect_at"] = raw_performance.get("last_incorrect_at")
    performance["consecutive_correct"] = int(raw_performance.get("consecutive_correct", 0) or 0)
    performance["consecutive_incorrect"] = int(raw_performance.get("consecutive_incorrect", 0) or 0)
    return performance


def _resurfacing_signal(last_seen_at: object) -> float:
    if not last_seen_at:
        return 0.6
    parsed = _parse_datetime(last_seen_at)
    if parsed is None:
        return 0.4
    days_since = max((datetime.now(timezone.utc) - parsed).total_seconds() / 86400, 0.0)
    return min(days_since / RESURFACING_DAYS_CAP, 1.0)


def _parse_datetime(raw_value: object) -> datetime | None:
    if isinstance(raw_value, datetime):
        return raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)
    if not isinstance(raw_value, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _resolve_topic_name(topic_id: str, topic_node: TopicNode | None) -> str:
    if topic_node and topic_node.title.strip():
        return topic_node.title.strip()
    return _humanize_topic_id(topic_id)


def _short_content(content: str, *, limit: int = 140) -> str:
    normalized = _normalize_text(content)
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[: limit - 3].rstrip(" ,.;:")
    return f"{clipped}..."


def _normalize_text(content: str) -> str:
    return " ".join(content.replace("\n", " ").split())


def _humanize_topic_id(topic_id: str) -> str:
    cleaned = topic_id.replace("_", " ").replace("-", " ").strip()
    return " ".join(token.capitalize() for token in cleaned.split()) or "Tema"
