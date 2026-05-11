from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from app.domain.models import LearningPlanEntry, MicroTopic, StudyBlock, TopicNode
from app.services.learning_engine import compute_microtopic_priority
from app.services.microtopic_extractor import MicroTopicExtractor


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
        review_stage,
        limit=_resolve_selection_limit(block, review_stage),
        fallback_topic_id=block.topic_id,
    )
    selected_microtopics = selection["selected_microtopics"]

    if block.type == "summary":
        depth = block.depth or "light"
        return {
            "type": "summary",
            "topic_id": block.topic_id,
            "depth": depth,
            "content": _generate_summary_content(topic_name, depth, selected_microtopics),
            **_selection_metadata(selection),
        }
    if block.type == "questions":
        quantity = max(1, int(block.quantity or 1))
        return {
            "type": "questions",
            "topic_id": block.topic_id,
            "questions": _generate_questions(topic_name, selected_microtopics, quantity),
            **_selection_metadata(selection),
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
    review_stage: str,
    *,
    limit: int,
    fallback_topic_id: str = "",
) -> dict[str, object]:
    microtopics = _resolve_microtopics(fallback_topic_id, topic_node)
    if not microtopics:
        return {
            "selected_microtopics": [],
            "resurfaced_microtopics": [],
            "weak_microtopics": [],
            "review_intensity": review_stage,
            "adaptive_reasoning": ["Nenhum microtopico encontrado; fallback seguro aplicado."],
        }

    performance_map = dict(microtopic_performance or {})
    profiles = [
        _build_microtopic_profile(microtopic, performance_map.get(microtopic.id), review_stage)
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

    selected_profiles = _choose_profiles(ranked_profiles, review_stage=review_stage, limit=max(1, limit))
    weak_profiles = [profile for profile in ranked_profiles if profile["is_weak"]]
    resurfaced_profiles = [profile for profile in selected_profiles if profile["is_resurfaced"]]

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
    review_stage: str,
) -> dict[str, object]:
    performance = _normalize_microtopic_performance(raw_performance)
    weights = REVIEW_STAGE_WEIGHTS[review_stage]
    total_questions = int(performance["total_questions"])
    correct_answers = int(performance["correct_answers"])
    recent_errors = int(performance["recent_errors"])
    accuracy = correct_answers / max(total_questions, 1)
    weakness_signal = min(
        compute_microtopic_priority(performance) / MICROTOPIC_PRIORITY_CAP,
        1.0,
    )
    resurfacing_signal = _resurfacing_signal(performance["last_seen_at"])
    difficulty_signal = min(max(microtopic.difficulty_weight - 1.0, 0.0) / 0.4, 1.0)
    mastered = total_questions >= 3 and accuracy >= 0.75 and recent_errors == 0
    cumulative_signal = max(resurfacing_signal, 0.35 if mastered else 0.15)

    selection_score = (
        weakness_signal * weights["weakness"]
        + resurfacing_signal * weights["resurfacing"]
        + difficulty_signal * weights["difficulty"]
        + cumulative_signal * weights["cumulative"]
    )
    if mastered and review_stage == "light":
        selection_score += 0.08

    return {
        "microtopic": microtopic,
        "selection_score": round(selection_score, 6),
        "weakness_signal": round(weakness_signal, 6),
        "resurfacing_signal": round(resurfacing_signal, 6),
        "difficulty_weight": microtopic.difficulty_weight,
        "is_mastered": mastered,
        "is_weak": recent_errors > 0 or weakness_signal >= 0.6,
        "is_resurfaced": mastered and resurfacing_signal >= 0.5,
        "position": 0,
    }


def _choose_profiles(
    ranked_profiles: list[dict[str, object]],
    *,
    review_stage: str,
    limit: int,
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

    return selected[:limit]


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
    return {
        "selected_microtopics": _serialize_microtopics(selection["selected_microtopics"]),
        "resurfaced_microtopics": _serialize_microtopics(selection["resurfaced_microtopics"]),
        "weak_microtopics": _serialize_microtopics(selection["weak_microtopics"]),
        "review_intensity": selection["review_intensity"],
        "adaptive_reasoning": selection["adaptive_reasoning"],
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


def _generate_summary_content(topic_name: str, depth: str, microtopics: list[MicroTopic]) -> str:
    if not microtopics:
        return (
            f"Visao rapida de {topic_name}: regra central, palavra-chave e ponto de maior risco em prova."
        )

    sections = [
        f"{microtopic.title}: {_short_content(microtopic.content)}"
        for microtopic in microtopics
    ]

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
        if index % 2 == 0:
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
