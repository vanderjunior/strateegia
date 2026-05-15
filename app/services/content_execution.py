from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from app.domain.models import LearningPlanEntry, MicroTopic, StudyBlock, TopicNode
from app.services.cognitive_facets import resolve_facet_profile
from app.services.cognitive_trajectory import analyze_cognitive_trajectory
from app.services.conceptual_relationships import (
    ConceptualRelationshipsLayer,
    build_relationship_signals,
)
from app.services.cognitive_compression import resolve_cognitive_compression
from app.services.comparative_session_analytics import compare_session_analytics
from app.services.empirical_validation_dataset import evaluate_empirical_validation_dataset
from app.services.pedagogical_benchmark_runner import run_pedagogical_benchmark
from app.services.pedagogical_observability import resolve_pedagogical_observability
from app.services.pedagogical_validation import resolve_pedagogical_validation
from app.services.runtime_traceability import resolve_runtime_traceability
from app.services.runtime_signal_normalization import normalize_runtime_signal_families
from app.services.pedagogical_tuning_profiles import resolve_pedagogical_tuning_profile
from app.services.session_export_debug import build_session_export_snapshot
from app.services.session_stability_metrics import resolve_session_stability_metrics
from app.services.session_snapshot_diff import build_session_snapshot, compare_session_snapshots
from app.services.scientific_runtime_validation import resolve_scientific_runtime_validation
from app.services.runtime_scenario_simulation import simulate_runtime_scenario
from app.services.validation_dataset_awareness import resolve_validation_dataset_awareness
from app.services.validation_harness import resolve_validation_harness
from app.services.learning_engine import compute_microtopic_priority
from app.services.micro_interventions import resolve_micro_intervention
from app.services.microtopic_extractor import MicroTopicExtractor
from app.services.adaptive_signal_consolidation import resolve_adaptive_signal_consolidation
from app.services.pedagogical_adapter import resolve_pedagogical_profile
from app.services.pedagogical_expression import resolve_pedagogical_expression


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
    facet_profile = _resolve_facet_profile(selection)
    trajectory_profile = _resolve_trajectory_profile(block, selection, facet_profile)
    pedagogical_profile = _resolve_pedagogical_profile(
        block,
        selection,
        facet_profile,
        trajectory_profile,
    )
    pedagogical_metadata = _pedagogical_metadata(pedagogical_profile)
    micro_intervention = resolve_micro_intervention(
        block_type=block.type,
        curriculum_role=block.curriculum_role,
        review_intensity=block.review_intensity or selection.get("review_intensity"),
        pedagogical_profile=pedagogical_profile,
        relationship_signal=selection.get("relationship_signal"),
        facet_profile=facet_profile,
        trajectory_profile=trajectory_profile,
    )
    facet_metadata = _facet_metadata(facet_profile)
    trajectory_metadata = _trajectory_metadata(trajectory_profile)
    micro_intervention_metadata = _micro_intervention_metadata(micro_intervention)
    expression_profile = _resolve_expression_profile(
        block,
        selection,
        pedagogical_profile,
        micro_intervention,
        facet_profile,
        trajectory_profile,
    )
    expression_metadata = _expression_metadata(expression_profile)
    compression_profile = _resolve_compression_profile(
        block,
        selection,
        pedagogical_profile,
        facet_profile,
        trajectory_profile,
        expression_profile,
    )
    compression_metadata = _compression_metadata(compression_profile)
    consolidation_profile = _resolve_adaptive_signal_consolidation_profile(
        pedagogical_profile,
        micro_intervention,
        trajectory_profile,
        expression_profile,
        compression_profile,
    )
    consolidation_metadata = _adaptive_signal_consolidation_metadata(consolidation_profile)
    observability_profile = _resolve_pedagogical_observability_profile(
        block,
        pedagogical_profile,
        micro_intervention,
        trajectory_profile,
        expression_profile,
        compression_profile,
        consolidation_profile,
    )
    observability_metadata = _pedagogical_observability_metadata(observability_profile)
    traceability_profile = _resolve_runtime_traceability_profile(
        block,
        pedagogical_profile,
        micro_intervention,
        trajectory_profile,
        expression_profile,
        compression_profile,
        consolidation_profile,
        observability_profile,
    )
    traceability_metadata = _runtime_traceability_metadata(traceability_profile)
    validation_profile = _resolve_pedagogical_validation_profile(
        block,
        pedagogical_profile,
        micro_intervention,
        trajectory_profile,
        expression_profile,
        compression_profile,
        consolidation_profile,
        observability_profile,
        traceability_profile,
    )
    validation_metadata = _pedagogical_validation_metadata(validation_profile)
    normalized_signal_profile = _resolve_runtime_signal_normalization_profile(
        pedagogical_profile,
        micro_intervention,
        trajectory_profile,
        expression_profile,
        compression_profile,
        consolidation_profile,
        observability_profile,
        traceability_profile,
        validation_profile,
    )
    normalized_signal_metadata = _runtime_signal_normalization_metadata(normalized_signal_profile)
    session_stability_profile = _resolve_session_stability_metrics_profile(
        block,
        pedagogical_profile,
        trajectory_profile,
        expression_profile,
        compression_profile,
        consolidation_profile,
        observability_profile,
        validation_profile,
        normalized_signal_profile,
    )
    session_stability_metadata = _session_stability_metrics_metadata(session_stability_profile)
    tuning_profile = _resolve_pedagogical_tuning_profile(
        block,
        trajectory_profile,
        expression_profile,
        observability_profile,
        validation_profile,
        normalized_signal_profile,
        session_stability_profile,
    )
    tuning_metadata = _pedagogical_tuning_metadata(tuning_profile)
    validation_harness_profile = _resolve_validation_harness_profile(
        block,
        trajectory_profile,
        observability_profile,
        validation_profile,
        session_stability_profile,
        normalized_signal_profile,
    )
    validation_harness_metadata = _validation_harness_metadata(validation_harness_profile)
    session_snapshot_profile, behavioral_diff_profile = _resolve_session_snapshot_diff_profiles(
        block,
        session_stability_profile,
        validation_harness_profile,
    )
    session_snapshot_diff_metadata = _session_snapshot_diff_metadata(
        session_snapshot_profile,
        behavioral_diff_profile,
    )
    session_export_snapshot = _resolve_session_export_snapshot(
        block,
        session_snapshot_profile,
        behavioral_diff_profile,
        validation_harness_profile,
    )
    session_export_metadata = _session_export_debug_metadata(session_export_snapshot)
    validation_dataset_awareness_profile = _resolve_validation_dataset_awareness_profile(
        block,
        session_stability_profile,
        validation_harness_profile,
        session_snapshot_profile,
        behavioral_diff_profile,
        normalized_signal_profile,
    )
    validation_dataset_awareness_metadata = _validation_dataset_awareness_metadata(
        validation_dataset_awareness_profile
    )
    scientific_runtime_validation_profile = _resolve_scientific_runtime_validation_profile(
        block,
        session_stability_profile,
        validation_harness_profile,
        validation_profile,
        normalized_signal_profile,
        behavioral_diff_profile,
        validation_dataset_awareness_profile,
    )
    scientific_runtime_validation_metadata = _scientific_runtime_validation_metadata(
        scientific_runtime_validation_profile
    )
    comparative_session_analytics_profile = _resolve_comparative_session_analytics_profile(
        block,
        session_stability_profile,
        validation_harness_profile,
        session_export_snapshot,
        validation_dataset_awareness_profile,
        scientific_runtime_validation_profile,
    )
    comparative_session_analytics_metadata = _comparative_session_analytics_metadata(
        comparative_session_analytics_profile
    )
    runtime_scenario_simulation_profile = _resolve_runtime_scenario_simulation_profile(
        block,
        session_stability_profile,
        validation_harness_profile,
        validation_profile,
        session_export_snapshot,
        validation_dataset_awareness_profile,
        scientific_runtime_validation_profile,
        comparative_session_analytics_profile,
    )
    runtime_scenario_simulation_metadata = _runtime_scenario_simulation_metadata(
        runtime_scenario_simulation_profile
    )
    empirical_validation_dataset_summary = _resolve_empirical_validation_dataset_summary(
        block,
        session_stability_profile,
        validation_harness_profile,
        validation_profile,
        validation_dataset_awareness_profile,
        scientific_runtime_validation_profile,
        comparative_session_analytics_profile,
    )
    empirical_validation_dataset_metadata = _empirical_validation_dataset_metadata(
        empirical_validation_dataset_summary
    )
    pedagogical_benchmark_result = _resolve_pedagogical_benchmark_result(
        empirical_validation_dataset_summary
    )
    pedagogical_benchmark_metadata = _pedagogical_benchmark_metadata(
        pedagogical_benchmark_result
    )

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
                micro_intervention,
                facet_profile,
                expression_profile,
                compression_profile,
                consolidation_profile,
            ),
            **_selection_metadata(selection),
            **pedagogical_metadata,
            **facet_metadata,
            **trajectory_metadata,
            **micro_intervention_metadata,
            **expression_metadata,
            **compression_metadata,
            **consolidation_metadata,
            **observability_metadata,
            **traceability_metadata,
            **validation_metadata,
            **normalized_signal_metadata,
            **session_stability_metadata,
            **tuning_metadata,
            **validation_harness_metadata,
            **session_snapshot_diff_metadata,
            **session_export_metadata,
            **validation_dataset_awareness_metadata,
            **scientific_runtime_validation_metadata,
            **comparative_session_analytics_metadata,
            **runtime_scenario_simulation_metadata,
            **empirical_validation_dataset_metadata,
            **pedagogical_benchmark_metadata,
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
                micro_intervention,
                facet_profile,
                expression_profile,
                compression_profile,
                consolidation_profile,
            ),
            **_selection_metadata(selection),
            **pedagogical_metadata,
            **facet_metadata,
            **trajectory_metadata,
            **micro_intervention_metadata,
            **expression_metadata,
            **compression_metadata,
            **consolidation_metadata,
            **observability_metadata,
            **traceability_metadata,
            **validation_metadata,
            **normalized_signal_metadata,
            **session_stability_metadata,
            **tuning_metadata,
            **validation_harness_metadata,
            **session_snapshot_diff_metadata,
            **session_export_metadata,
            **validation_dataset_awareness_metadata,
            **scientific_runtime_validation_metadata,
            **comparative_session_analytics_metadata,
            **runtime_scenario_simulation_metadata,
            **empirical_validation_dataset_metadata,
            **pedagogical_benchmark_metadata,
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
    relationship_bonus = min(support_signal * 0.14 + prerequisite_signal * 0.015, 0.1)
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
    micro_intervention,
    facet_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
) -> str:
    if not microtopics:
        content = (
            f"Visao rapida de {topic_name}: regra central, palavra-chave e ponto de maior risco em prova."
        )
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )

    sections = [
        f"{microtopic.title}: {_short_content(microtopic.content)}"
        for microtopic in microtopics
    ]

    if pedagogical_profile.pedagogical_mode == "guided_explanation":
        content = (
            f"Resumo aprofundado de {topic_name}: "
            + " ".join(
                f"{index + 1}. {section}" for index, section in enumerate(sections)
            )
            + " Compare a regra geral com a excecao aplicavel, destaque o contraste conceitual e observe o ponto que muda o julgamento. "
            + "Exemplo de prova: identifique qual detalhe normativo altera o resultado."
        )
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    if pedagogical_profile.pedagogical_mode == "contextual_application":
        content = (
            f"Resumo estruturado de {topic_name}: pontos de prova em contexto pratico. "
            + " ".join(sections)
            + " Priorize comparacoes entre cenarios e a condicao que muda a resposta."
        )
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    if pedagogical_profile.pedagogical_mode == "active_recall":
        content = f"Visao rapida de {topic_name}: relembre sem apoio total. " + " ".join(sections[: max(1, min(2, len(sections)))])
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    if pedagogical_profile.pedagogical_mode in {"rapid_review", "reinforcement_check"}:
        content = f"Visao rapida de {topic_name}: {sections[0]}"
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    if depth == "deep":
        content = (
            f"Resumo aprofundado de {topic_name}: "
            + " ".join(
                f"{index + 1}. {section}" for index, section in enumerate(sections)
            )
            + " Exemplo de prova: compare a regra geral com a excecao aplicavel e identifique o detalhe que altera o resultado."
        )
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    if depth == "medium":
        content = f"Resumo estruturado de {topic_name}: pontos de prova e focos especificos. " + " ".join(
            sections
        )
        return _apply_signal_consolidation_to_summary(
            _apply_compression_to_summary(
                _apply_expression_to_summary(
                    _apply_intervention_to_summary(content, micro_intervention, facet_profile),
                    expression_profile,
                ),
                compression_profile,
            ),
            consolidation_profile,
        )
    return _apply_signal_consolidation_to_summary(
        _apply_compression_to_summary(
            _apply_expression_to_summary(
                _apply_intervention_to_summary(
                    f"Visao rapida de {topic_name}: {sections[0]}",
                    micro_intervention,
                    facet_profile,
                ),
                expression_profile,
            ),
            compression_profile,
        ),
        consolidation_profile,
    )


def _generate_questions(
    topic_name: str,
    microtopics: list[MicroTopic],
    quantity: int,
    pedagogical_profile,
    micro_intervention,
    facet_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
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
                "statement": _apply_intervention_to_question_statement(
                    statement,
                    micro_intervention,
                    facet_profile,
                    expression_profile,
                    compression_profile,
                    consolidation_profile,
                    index=index,
                ),
                "answer": answer,
                "explanation": _apply_intervention_to_question_explanation(
                    explanation,
                    micro_intervention,
                    facet_profile,
                    expression_profile,
                    compression_profile,
                    consolidation_profile,
                    index=index,
                ),
                "microtopic_id": microtopic.id,
            }
        )
    return questions


def _resolve_pedagogical_profile(
    block: StudyBlock,
    selection: dict[str, object],
    facet_profile,
    trajectory_profile,
):
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
        facet_profile=facet_profile,
        trajectory_profile=trajectory_profile,
    )


def _resolve_facet_profile(selection: dict[str, object]):
    selected_microtopics = selection.get("selected_microtopics", []) or []
    primary_microtopic = selected_microtopics[0] if selected_microtopics else None
    if primary_microtopic is None:
        return resolve_facet_profile(
            MicroTopic(
                id="fallback-facet",
                title="Conceito",
                content="Conceito central mantido por compatibilidade.",
                source_topic_title="Tema",
                difficulty_weight=1.0,
            )
        )
    return resolve_facet_profile(
        primary_microtopic,
        relationship_signal=selection.get("relationship_signal"),
    )


def _resolve_trajectory_profile(
    block: StudyBlock,
    selection: dict[str, object],
    facet_profile,
):
    selected_microtopics = selection.get("selected_microtopics", []) or []
    primary_microtopic_id = selected_microtopics[0].id if selected_microtopics else None
    raw_performance = {}
    raw_pedagogical_memory = {}
    if primary_microtopic_id:
        raw_performance = dict((block.microtopic_performance or {}).get(primary_microtopic_id, {}) or {})
        raw_pedagogical_memory = dict((block.pedagogical_memory or {}).get(primary_microtopic_id, {}) or {})
    return analyze_cognitive_trajectory(
        performance=raw_performance,
        pedagogical_memory=raw_pedagogical_memory,
        facet_profile=facet_profile,
    )


def _resolve_expression_profile(
    block: StudyBlock,
    selection: dict[str, object],
    pedagogical_profile,
    micro_intervention,
    facet_profile,
    trajectory_profile,
):
    return resolve_pedagogical_expression(
        block_type=block.type,
        pedagogical_mode=pedagogical_profile.pedagogical_mode,
        curriculum_role=block.curriculum_role,
        review_intensity=block.review_intensity or selection.get("review_intensity"),
        cognitive_load=pedagogical_profile.cognitive_load,
        retrieval_intensity=pedagogical_profile.retrieval_intensity,
        narrative_relation="cumulative_resurfacing"
        if block.curriculum_role == "cumulative" and (block.review_intensity or selection.get("review_intensity")) == "light"
        else "reinforcement",
        cognitive_momentum="conceptually_dense"
        if pedagogical_profile.cognitive_load == "high"
        else "balanced",
        micro_intervention=micro_intervention.intervention_type,
        dominant_facet=facet_profile.dominant_facet,
        trajectory_state=trajectory_profile.trajectory_state,
    )


def _resolve_compression_profile(
    block: StudyBlock,
    selection: dict[str, object],
    pedagogical_profile,
    facet_profile,
    trajectory_profile,
    expression_profile,
):
    return resolve_cognitive_compression(
        block_type=block.type,
        pedagogical_mode=pedagogical_profile.pedagogical_mode,
        curriculum_role=block.curriculum_role,
        review_intensity=block.review_intensity or selection.get("review_intensity"),
        relationship_signal=selection.get("relationship_signal"),
        pedagogical_profile=pedagogical_profile,
        facet_profile=facet_profile,
        trajectory_profile=trajectory_profile,
        expression_profile=expression_profile,
        session_coherence={
            "session_coherence_state": "stable_progression",
            "progression_continuity": 0.68,
        },
        cognitive_momentum={
            "cognitive_momentum": "retrieval_heavy"
            if pedagogical_profile.retrieval_intensity == "high"
            else "conceptually_dense"
            if pedagogical_profile.cognitive_load == "high"
            else "stable",
        },
    )


def _resolve_adaptive_signal_consolidation_profile(
    pedagogical_profile,
    micro_intervention,
    trajectory_profile,
    expression_profile,
    compression_profile,
):
    return resolve_adaptive_signal_consolidation(
        pedagogical_mode=pedagogical_profile.pedagogical_mode,
        micro_intervention=micro_intervention.intervention_type,
        cognitive_trajectory=trajectory_profile.trajectory_state,
        cognitive_momentum="retrieval_heavy"
        if pedagogical_profile.retrieval_intensity == "high"
        else "conceptually_dense"
        if pedagogical_profile.cognitive_load == "high"
        else "balanced"
        if trajectory_profile.longitudinal_consistency >= 0.55
        else "stable",
        session_coherence="stable_progression"
        if trajectory_profile.longitudinal_consistency >= 0.5
        else "pacing_fragile"
        if trajectory_profile.reconstruction_fragility >= 0.6
        else "continuity_stable",
        compression_mode=compression_profile.cognitive_compression_mode,
        expression_mode=expression_profile.pedagogical_expression_mode,
        stabilization_state=pedagogical_profile.stabilization_stage,
        retrieval_intensity=pedagogical_profile.retrieval_intensity,
        cognitive_load_score=pedagogical_profile.cognitive_load_score,
        informational_density=compression_profile.informational_density,
        explanation_density=expression_profile.explanation_density,
        reconstruction_fragility=trajectory_profile.reconstruction_fragility,
        transfer_fragility=trajectory_profile.transfer_fragility,
        longitudinal_retention=pedagogical_profile.longitudinal_retention,
        progression_continuity=trajectory_profile.longitudinal_consistency,
    )


def _resolve_pedagogical_observability_profile(
    block: StudyBlock,
    pedagogical_profile,
    micro_intervention,
    trajectory_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
):
    return resolve_pedagogical_observability(
        current_block={
            "type": block.type,
            "pedagogical_mode": pedagogical_profile.pedagogical_mode,
            "micro_intervention": micro_intervention.intervention_type,
            "retrieval_intensity": pedagogical_profile.retrieval_intensity,
            "pedagogical_expression_mode": expression_profile.pedagogical_expression_mode,
            "cognitive_compression_mode": compression_profile.cognitive_compression_mode,
            "session_coherence_state": "stable_progression"
            if trajectory_profile.longitudinal_consistency >= 0.5
            else "pacing_fragile",
            "cognitive_momentum": "retrieval_heavy"
            if pedagogical_profile.retrieval_intensity == "high"
            else "conceptually_dense"
            if pedagogical_profile.cognitive_load == "high"
            else "balanced",
            "trajectory_state": trajectory_profile.trajectory_state,
            "stabilization_stage": pedagogical_profile.stabilization_stage,
            "explanation_density": expression_profile.explanation_density,
            "informational_density": compression_profile.informational_density,
            "progression_continuity": trajectory_profile.longitudinal_consistency,
            "longitudinal_consistency": trajectory_profile.longitudinal_consistency,
            "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
            "transfer_fragility": trajectory_profile.transfer_fragility,
            "cognitive_load_score": pedagogical_profile.cognitive_load_score,
            "adaptive_signal_state": consolidation_profile.adaptive_signal_state,
            "explanatory_expansion": compression_profile.explanatory_expansion,
        },
        recent_blocks=[],
    )


def _resolve_runtime_traceability_profile(
    block: StudyBlock,
    pedagogical_profile,
    micro_intervention,
    trajectory_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    observability_profile,
):
    return resolve_runtime_traceability(
        current_block={
            "type": block.type,
            "pedagogical_mode": pedagogical_profile.pedagogical_mode,
            "micro_intervention": micro_intervention.intervention_type,
            "pedagogical_expression_mode": expression_profile.pedagogical_expression_mode,
            "cognitive_compression_mode": compression_profile.cognitive_compression_mode,
            "adaptive_signal_state": consolidation_profile.adaptive_signal_state,
            "pedagogical_observability_state": observability_profile.pedagogical_observability_state,
            "cognitive_momentum": "retrieval_heavy"
            if pedagogical_profile.retrieval_intensity == "high"
            else "conceptually_dense"
            if pedagogical_profile.cognitive_load == "high"
            else "balanced",
            "session_coherence_state": "stable_progression"
            if trajectory_profile.longitudinal_consistency >= 0.5
            else "pacing_fragile",
            "trajectory_state": trajectory_profile.trajectory_state,
            "retrieval_intensity": pedagogical_profile.retrieval_intensity,
            "cognitive_load_score": pedagogical_profile.cognitive_load_score,
            "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
            "transfer_fragility": trajectory_profile.transfer_fragility,
            "progression_continuity": trajectory_profile.longitudinal_consistency,
            "longitudinal_consistency": trajectory_profile.longitudinal_consistency,
            "signal_overlap_density": observability_profile.signal_overlap_density,
            "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
            "scaffold_density": observability_profile.scaffold_density,
            "modulation_overlap": consolidation_profile.modulation_overlap,
            "stabilization_stage": pedagogical_profile.stabilization_stage,
        },
        recent_blocks=[],
    )


def _resolve_pedagogical_validation_profile(
    block: StudyBlock,
    pedagogical_profile,
    micro_intervention,
    trajectory_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    observability_profile,
    traceability_profile,
):
    return resolve_pedagogical_validation(
        current_block={
            "type": block.type,
            "trajectory_state": trajectory_profile.trajectory_state,
            "stabilization_stage": pedagogical_profile.stabilization_stage,
            "retrieval_intensity": pedagogical_profile.retrieval_intensity,
            "cognitive_momentum": "retrieval_heavy"
            if pedagogical_profile.retrieval_intensity == "high"
            else "conceptually_dense"
            if pedagogical_profile.cognitive_load == "high"
            else "balanced",
            "session_coherence_state": "stable_progression"
            if trajectory_profile.longitudinal_consistency >= 0.5
            else "pacing_fragile",
            "pedagogical_expression_mode": expression_profile.pedagogical_expression_mode,
            "cognitive_compression_mode": compression_profile.cognitive_compression_mode,
            "micro_intervention": micro_intervention.intervention_type,
            "adaptive_signal_state": consolidation_profile.adaptive_signal_state,
            "pedagogical_observability_state": observability_profile.pedagogical_observability_state,
            "runtime_trace_state": traceability_profile.runtime_trace_state,
            "longitudinal_retention": pedagogical_profile.longitudinal_retention,
            "longitudinal_consistency": trajectory_profile.longitudinal_consistency,
            "stabilization_quality": trajectory_profile.stabilization_quality,
            "false_fluency_signal": trajectory_profile.false_fluency_signal,
            "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
            "transfer_fragility": trajectory_profile.transfer_fragility,
            "scaffold_density": observability_profile.scaffold_density,
            "signal_overlap_density": observability_profile.signal_overlap_density,
            "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
            "modulation_overlap": consolidation_profile.modulation_overlap,
            "reinforcement_convergence": consolidation_profile.reinforcement_convergence,
            "explanatory_expansion": compression_profile.explanatory_expansion,
        },
        recent_blocks=[],
    )


def _resolve_runtime_signal_normalization_profile(
    pedagogical_profile,
    micro_intervention,
    trajectory_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    observability_profile,
    traceability_profile,
    validation_profile,
):
    return normalize_runtime_signal_families(
        {
            "retrieval_intensity": pedagogical_profile.retrieval_intensity,
            "cognitive_momentum": "retrieval_heavy"
            if pedagogical_profile.retrieval_intensity == "high"
            else "conceptually_dense"
            if pedagogical_profile.cognitive_load == "high"
            else "balanced",
            "pedagogical_expression_mode": expression_profile.pedagogical_expression_mode,
            "cognitive_compression_mode": compression_profile.cognitive_compression_mode,
            "adaptive_signal_state": consolidation_profile.adaptive_signal_state,
            "pedagogical_observability_state": observability_profile.pedagogical_observability_state,
            "runtime_trace_state": traceability_profile.runtime_trace_state,
            "session_coherence_state": "stable_progression"
            if trajectory_profile.longitudinal_consistency >= 0.5
            else "pacing_fragile",
            "trajectory_state": trajectory_profile.trajectory_state,
            "stabilization_stage": pedagogical_profile.stabilization_stage,
            "modulation_overlap": consolidation_profile.modulation_overlap,
            "signal_overlap_density": observability_profile.signal_overlap_density,
            "scaffold_density": observability_profile.scaffold_density,
            "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
            "longitudinal_retention": pedagogical_profile.longitudinal_retention,
            "pedagogical_validation_state": validation_profile.pedagogical_validation_state,
        }
    )


def _resolve_session_stability_metrics_profile(
    block: StudyBlock,
    pedagogical_profile,
    trajectory_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    observability_profile,
    validation_profile,
    normalized_signal_profile,
):
    return resolve_session_stability_metrics(
        [
            {
                "type": block.type,
                "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
                "scaffold_density": observability_profile.scaffold_density,
                "continuity_stability": observability_profile.continuity_stability,
                "progression_continuity": trajectory_profile.longitudinal_consistency,
                "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
                "compression_support_alignment": observability_profile.compression_support_alignment,
                "stabilization_quality": trajectory_profile.stabilization_quality,
                "stabilization_quality_signal": validation_profile.stabilization_quality_signal,
                "longitudinal_validation_signal": validation_profile.longitudinal_validation_signal,
                "longitudinal_consistency": trajectory_profile.longitudinal_consistency,
                "modulation_overlap": consolidation_profile.modulation_overlap,
                "signal_overlap_density": observability_profile.signal_overlap_density,
                "retrieval_effectiveness_signal": validation_profile.retrieval_effectiveness_signal,
                "pacing_adjustment": expression_profile.pacing_adjustment,
                "false_fluency_risk": validation_profile.false_fluency_risk,
                "retrieval_family": normalized_signal_profile.retrieval_family,
                "support_family": normalized_signal_profile.support_family,
                "continuity_family": normalized_signal_profile.continuity_family,
                "stabilization_family": normalized_signal_profile.stabilization_family,
                "overlap_family": normalized_signal_profile.overlap_family,
                "pedagogical_observability_state": observability_profile.pedagogical_observability_state,
                "runtime_trace_state": "runtime_balanced",
                "pedagogical_validation_state": validation_profile.pedagogical_validation_state,
            }
        ]
    )


def _resolve_pedagogical_tuning_profile(
    block: StudyBlock,
    trajectory_profile,
    expression_profile,
    observability_profile,
    validation_profile,
    normalized_signal_profile,
    session_stability_profile,
):
    return resolve_pedagogical_tuning_profile(
        [
            {
                "type": block.type,
                "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
                "scaffold_density": observability_profile.scaffold_density,
                "continuity_stability": observability_profile.continuity_stability,
                "progression_continuity": trajectory_profile.longitudinal_consistency,
                "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "modulation_overlap": session_stability_profile.modulation_convergence_metric,
                "signal_overlap_density": observability_profile.signal_overlap_density,
                "stabilization_quality": trajectory_profile.stabilization_quality,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "pacing_adjustment": expression_profile.pacing_adjustment,
                "intervention_repetition_signal": observability_profile.intervention_repetition_signal,
                "retrieval_family": normalized_signal_profile.retrieval_family,
                "support_family": normalized_signal_profile.support_family,
                "continuity_family": normalized_signal_profile.continuity_family,
                "stabilization_family": normalized_signal_profile.stabilization_family,
                "overlap_family": normalized_signal_profile.overlap_family,
                "pedagogical_observability_state": observability_profile.pedagogical_observability_state,
                "session_stability_state": session_stability_profile.session_stability_state,
            }
        ]
    )


def _resolve_validation_harness_profile(
    block: StudyBlock,
    trajectory_profile,
    observability_profile,
    validation_profile,
    session_stability_profile,
    normalized_signal_profile,
):
    return resolve_validation_harness(
        [
            {
                "type": block.type,
                "retrieval_effectiveness_signal": validation_profile.retrieval_effectiveness_signal,
                "retrieval_pressure_accumulation": observability_profile.retrieval_pressure_accumulation,
                "scaffold_dependency_signal": validation_profile.scaffold_dependency_signal,
                "scaffold_density": observability_profile.scaffold_density,
                "reconstruction_progress_signal": validation_profile.reconstruction_progress_signal,
                "reconstruction_fragility": trajectory_profile.reconstruction_fragility,
                "transfer_stability_signal": validation_profile.transfer_stability_signal,
                "transfer_fragility": trajectory_profile.transfer_fragility,
                "stabilization_quality_signal": validation_profile.stabilization_quality_signal,
                "longitudinal_validation_signal": validation_profile.longitudinal_validation_signal,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "cognitive_balance_metric": session_stability_profile.cognitive_balance_metric,
                "modulation_overlap": observability_profile.modulation_redundancy,
                "signal_overlap_density": observability_profile.signal_overlap_density,
                "support_density": session_stability_profile.support_density,
                "intervention_repetition_signal": observability_profile.intervention_repetition_signal,
                "pedagogical_validation_state": validation_profile.pedagogical_validation_state,
                "session_stability_state": session_stability_profile.session_stability_state,
                "retrieval_family": normalized_signal_profile.retrieval_family,
                "support_family": normalized_signal_profile.support_family,
                "continuity_family": normalized_signal_profile.continuity_family,
                "stabilization_family": normalized_signal_profile.stabilization_family,
                "overlap_family": normalized_signal_profile.overlap_family,
            }
        ]
    )


def _resolve_session_snapshot_diff_profiles(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
):
    current_snapshot = build_session_snapshot(
        [
            {
                "type": block.type,
                "retrieval_density_metric": session_stability_profile.retrieval_density_metric,
                "scaffold_load_metric": session_stability_profile.scaffold_load_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "reconstruction_pressure_metric": session_stability_profile.reconstruction_pressure_metric,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "modulation_convergence_metric": session_stability_profile.modulation_convergence_metric,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "cognitive_balance_metric": session_stability_profile.cognitive_balance_metric,
                "support_density": session_stability_profile.support_density,
                "adaptive_overlap_signal": validation_harness_profile.adaptive_overlap_signal,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "session_stability_state": session_stability_profile.session_stability_state,
                "validation_harness_state": validation_harness_profile.validation_harness_state,
            }
        ]
    )
    behavioral_diff = compare_session_snapshots(None, current_snapshot)
    return current_snapshot, behavioral_diff


def _resolve_session_export_snapshot(
    block: StudyBlock,
    session_snapshot_profile,
    behavioral_diff_profile,
    validation_harness_profile,
):
    return build_session_export_snapshot(
        [
            {
                "type": block.type,
                "topic_id": block.topic_id,
                "pedagogical_mode": "",
                "micro_intervention": "",
                "trajectory_state": "",
                "cognitive_compression_mode": "",
                "pedagogical_expression_mode": "",
                "session_coherence_state": "",
                "session_stability_state": session_snapshot_profile.session_snapshot_state,
                "pedagogical_tuning_state": "",
                "validation_harness_state": validation_harness_profile.validation_harness_state,
                "behavioral_diff_state": behavioral_diff_profile.behavioral_diff_state,
                "runtime_trace_state": "",
                "pedagogical_validation_state": "",
                "retrieval_family": "",
                "support_family": "",
                "continuity_family": "",
                "stabilization_family": "",
                "overlap_family": "",
                "retrieval_density_metric": session_snapshot_profile.retrieval_density,
                "scaffold_load_metric": session_snapshot_profile.scaffold_load,
                "continuity_smoothness_metric": session_snapshot_profile.continuity_smoothness,
                "reconstruction_pressure_metric": session_snapshot_profile.reconstruction_pressure,
                "compression_safety_metric": session_snapshot_profile.compression_safety,
                "stabilization_sustainability_metric": session_snapshot_profile.stabilization_sustainability,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "runtime_behavior_delta": behavioral_diff_profile.runtime_behavior_delta,
            }
        ]
    )


def _resolve_validation_dataset_awareness_profile(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
    session_snapshot_profile,
    behavioral_diff_profile,
    normalized_signal_profile,
):
    return resolve_validation_dataset_awareness(
        [
            {
                "type": block.type,
                "topic_id": block.topic_id,
                "retrieval_pressure_accumulation": session_stability_profile.retrieval_density_metric,
                "retrieval_density_metric": session_stability_profile.retrieval_density_metric,
                "scaffold_density": session_stability_profile.scaffold_load_metric,
                "scaffold_load_metric": session_stability_profile.scaffold_load_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "continuity_sustainability_signal": validation_harness_profile.continuity_sustainability_signal,
                "reconstruction_fragility": 1.0 - validation_harness_profile.reconstruction_sustainability_signal,
                "reconstruction_pressure_metric": session_stability_profile.reconstruction_pressure_metric,
                "reconstruction_sustainability_signal": validation_harness_profile.reconstruction_sustainability_signal,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "compression_safety_signal": validation_harness_profile.compression_safety_signal,
                "transfer_fragility": 1.0 - validation_harness_profile.transfer_stability_signal,
                "transfer_stability_signal": validation_harness_profile.transfer_stability_signal,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "stabilization_reliability_signal": validation_harness_profile.stabilization_reliability_signal,
                "support_density": session_stability_profile.support_density,
                "reinforcement_density_signal": validation_harness_profile.pedagogical_balance_signal,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "pacing_sustainability_signal": validation_harness_profile.pacing_sustainability_signal,
                "modulation_overlap": session_stability_profile.modulation_convergence_metric,
                "adaptive_overlap_signal": validation_harness_profile.adaptive_overlap_signal,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "resurfacing_effectiveness_signal": validation_harness_profile.resurfacing_effectiveness_signal,
                "retrieval_family": normalized_signal_profile.retrieval_family,
                "support_family": normalized_signal_profile.support_family,
                "continuity_family": normalized_signal_profile.continuity_family,
                "stabilization_family": normalized_signal_profile.stabilization_family,
                "overlap_family": normalized_signal_profile.overlap_family,
                "session_stability_state": session_stability_profile.session_stability_state,
                "validation_harness_state": validation_harness_profile.validation_harness_state,
                "behavioral_diff_state": behavioral_diff_profile.behavioral_diff_state,
                "session_snapshot_state": session_snapshot_profile.session_snapshot_state,
            }
        ]
    )


def _resolve_scientific_runtime_validation_profile(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
    validation_profile,
    normalized_signal_profile,
    behavioral_diff_profile,
    validation_dataset_awareness_profile,
):
    return resolve_scientific_runtime_validation(
        [
            {
                "type": block.type,
                "topic_id": block.topic_id,
                "retrieval_pressure_accumulation": session_stability_profile.retrieval_density_metric,
                "retrieval_density_metric": session_stability_profile.retrieval_density_metric,
                "scaffold_density": session_stability_profile.scaffold_load_metric,
                "scaffold_load_metric": session_stability_profile.scaffold_load_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "continuity_sustainability_signal": validation_harness_profile.continuity_sustainability_signal,
                "reconstruction_fragility": 1.0 - validation_harness_profile.reconstruction_sustainability_signal,
                "reconstruction_pressure_metric": session_stability_profile.reconstruction_pressure_metric,
                "reconstruction_sustainability_signal": validation_harness_profile.reconstruction_sustainability_signal,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "compression_safety_signal": validation_harness_profile.compression_safety_signal,
                "transfer_fragility": 1.0 - validation_harness_profile.transfer_stability_signal,
                "transfer_stability_signal": validation_harness_profile.transfer_stability_signal,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "stabilization_reliability_signal": validation_harness_profile.stabilization_reliability_signal,
                "support_density": session_stability_profile.support_density,
                "reinforcement_density_signal": validation_profile.reinforcement_density_signal,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "pacing_sustainability_signal": validation_harness_profile.pacing_sustainability_signal,
                "modulation_overlap": session_stability_profile.modulation_convergence_metric,
                "adaptive_overlap_signal": validation_harness_profile.adaptive_overlap_signal,
                "signal_overlap_density": validation_profile.adaptation_overlap_signal,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "false_fluency_risk": validation_profile.false_fluency_risk,
                "longitudinal_validation_signal": validation_profile.longitudinal_validation_signal,
                "retrieval_shift": behavioral_diff_profile.retrieval_shift,
                "scaffold_shift": behavioral_diff_profile.scaffold_shift,
                "continuity_shift": behavioral_diff_profile.continuity_shift,
                "overlap_shift": behavioral_diff_profile.overlap_shift,
                "runtime_behavior_delta": behavioral_diff_profile.runtime_behavior_delta,
                "retrieval_family": normalized_signal_profile.retrieval_family,
                "support_family": normalized_signal_profile.support_family,
                "continuity_family": normalized_signal_profile.continuity_family,
                "stabilization_family": normalized_signal_profile.stabilization_family,
                "overlap_family": normalized_signal_profile.overlap_family,
                "validation_dataset_state": validation_dataset_awareness_profile.validation_dataset_state,
                "pedagogical_scenario_family": validation_dataset_awareness_profile.pedagogical_scenario_family,
                "behavioral_diff_state": behavioral_diff_profile.behavioral_diff_state,
                "validation_harness_state": validation_harness_profile.validation_harness_state,
                "session_snapshot_state": behavioral_diff_profile.behavioral_diff_state,
            }
        ]
    )


def _resolve_comparative_session_analytics_profile(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
    session_export_snapshot,
    validation_dataset_awareness_profile,
    scientific_runtime_validation_profile,
):
    candidate_snapshot = {
        **session_export_snapshot.model_dump(mode="json"),
        "stability_snapshot": {
            **session_export_snapshot.stability_snapshot,
            "pacing_stability": session_stability_profile.pacing_stability_metric,
        },
        "validation_snapshot": {
            **session_export_snapshot.validation_snapshot,
            "validation_harness_state": validation_harness_profile.validation_harness_state,
            "validation_confidence": validation_harness_profile.validation_confidence,
        },
        "support_snapshot": {
            **session_export_snapshot.support_snapshot,
            "support_density": session_stability_profile.support_density,
        },
        "retrieval_snapshot": {
            **session_export_snapshot.retrieval_snapshot,
            "density": session_stability_profile.retrieval_density_metric,
        },
        "behavioral_diff_snapshot": {
            **session_export_snapshot.behavioral_diff_snapshot,
            "state": "behavior_stable",
            "delta": 0.0,
        },
    }
    baseline_snapshot = {
        **candidate_snapshot,
        "behavioral_diff_snapshot": {
            **candidate_snapshot["behavioral_diff_snapshot"],
            "state": "behavior_stable",
            "delta": 0.0,
        },
        "validation_snapshot": {
            **candidate_snapshot["validation_snapshot"],
            "validation_harness_state": validation_dataset_awareness_profile.validation_dataset_state,
        },
        "runtime_trace_snapshot": {
            **session_export_snapshot.runtime_trace_snapshot,
            "trace_summary": scientific_runtime_validation_profile.reproducibility_summary,
        },
    }
    _ = block
    return compare_session_analytics(baseline_snapshot, candidate_snapshot)


def _resolve_runtime_scenario_simulation_profile(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
    validation_profile,
    session_export_snapshot,
    validation_dataset_awareness_profile,
    scientific_runtime_validation_profile,
    comparative_session_analytics_profile,
):
    return simulate_runtime_scenario(
        [
            {
                "type": block.type,
                "topic_id": block.topic_id,
                "retrieval_density_metric": session_stability_profile.retrieval_density_metric,
                "scaffold_load_metric": session_stability_profile.scaffold_load_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "reconstruction_pressure_metric": session_stability_profile.reconstruction_pressure_metric,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "cognitive_balance_metric": session_stability_profile.cognitive_balance_metric,
                "support_density": session_stability_profile.support_density,
                "adaptive_overlap_signal": validation_harness_profile.adaptive_overlap_signal,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "false_fluency_risk": validation_profile.false_fluency_risk,
                "scaffold_dependency_signal": validation_profile.scaffold_dependency_signal,
                "resurfacing_effectiveness_signal": validation_harness_profile.resurfacing_effectiveness_signal,
                "transfer_stability_signal": validation_harness_profile.transfer_stability_signal,
                "compression_safety_signal": validation_harness_profile.compression_safety_signal,
                "scientific_validation_state": scientific_runtime_validation_profile.scientific_validation_state,
                "validation_dataset_state": validation_dataset_awareness_profile.validation_dataset_state,
                "comparative_session_state": comparative_session_analytics_profile.comparative_session_state,
                "pedagogical_regression_signal": comparative_session_analytics_profile.pedagogical_regression_signal,
                "session_export_state": session_export_snapshot.session_export_state,
            }
        ]
    )


def _resolve_empirical_validation_dataset_summary(
    block: StudyBlock,
    session_stability_profile,
    validation_harness_profile,
    validation_profile,
    validation_dataset_awareness_profile,
    scientific_runtime_validation_profile,
    comparative_session_analytics_profile,
):
    return evaluate_empirical_validation_dataset(
        [
            {
                "type": block.type,
                "topic_id": block.topic_id,
                "retrieval_density_metric": session_stability_profile.retrieval_density_metric,
                "scaffold_load_metric": session_stability_profile.scaffold_load_metric,
                "continuity_smoothness_metric": session_stability_profile.continuity_smoothness_metric,
                "reconstruction_pressure_metric": session_stability_profile.reconstruction_pressure_metric,
                "compression_safety_metric": session_stability_profile.compression_safety_metric,
                "stabilization_sustainability_metric": session_stability_profile.stabilization_sustainability_metric,
                "pacing_stability_metric": session_stability_profile.pacing_stability_metric,
                "cognitive_balance_metric": session_stability_profile.cognitive_balance_metric,
                "support_density": session_stability_profile.support_density,
                "adaptive_overlap_signal": validation_harness_profile.adaptive_overlap_signal,
                "validation_confidence": validation_harness_profile.validation_confidence,
                "false_fluency_risk": validation_profile.false_fluency_risk,
                "scaffold_dependency_signal": validation_profile.scaffold_dependency_signal,
                "resurfacing_effectiveness_signal": validation_harness_profile.resurfacing_effectiveness_signal,
                "transfer_stability_signal": validation_harness_profile.transfer_stability_signal,
                "compression_safety_signal": validation_harness_profile.compression_safety_signal,
                "scientific_validation_state": scientific_runtime_validation_profile.scientific_validation_state,
                "validation_dataset_state": validation_dataset_awareness_profile.validation_dataset_state,
                "comparative_session_state": comparative_session_analytics_profile.comparative_session_state,
                "pedagogical_regression_signal": comparative_session_analytics_profile.pedagogical_regression_signal,
            }
        ]
    )


def _resolve_pedagogical_benchmark_result(empirical_validation_dataset_summary):
    return run_pedagogical_benchmark(dataset_summary=empirical_validation_dataset_summary)


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


def _facet_metadata(profile) -> dict[str, object]:
    return {
        "cognitive_facets": [facet.model_dump(mode="json") for facet in profile.cognitive_facets],
        "dominant_facet": profile.dominant_facet,
        "facet_reasoning": profile.facet_reasoning,
        "cognitive_dimension": profile.cognitive_dimension,
        "retrieval_dimension": profile.retrieval_dimension,
        "conceptual_dimension": profile.conceptual_dimension,
        "transfer_signal": profile.transfer_signal,
        "reconstruction_signal": profile.reconstruction_signal,
        "recognition_signal": profile.recognition_signal,
        "why_this_facet_now": profile.why_this_facet_now,
        "facet_support_reason": profile.facet_support_reason,
    }


def _trajectory_metadata(profile) -> dict[str, object]:
    return {
        "cognitive_trajectory": profile.cognitive_trajectory,
        "trajectory_state": profile.trajectory_state,
        "trajectory_reasoning": profile.trajectory_reasoning,
        "consolidation_state": profile.consolidation_state,
        "stabilization_quality": profile.stabilization_quality,
        "false_fluency_signal": profile.false_fluency_signal,
        "reconstruction_fragility": profile.reconstruction_fragility,
        "transfer_fragility": profile.transfer_fragility,
        "longitudinal_consistency": profile.longitudinal_consistency,
        "why_this_trajectory_now": profile.why_this_trajectory_now,
        "trajectory_support_reason": profile.trajectory_support_reason,
    }


def _expression_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_expression_mode": profile.pedagogical_expression_mode,
        "expression_reasoning": profile.expression_reasoning,
        "readability_adjustment": profile.readability_adjustment,
        "pacing_adjustment": profile.pacing_adjustment,
        "continuity_support": profile.continuity_support,
        "retrieval_framing": profile.retrieval_framing,
        "explanation_density": profile.explanation_density,
        "cognitive_friction_reduction": profile.cognitive_friction_reduction,
        "transition_support_reason": profile.transition_support_reason,
        "why_this_expression_now": profile.why_this_expression_now,
    }


def _compression_metadata(profile) -> dict[str, object]:
    return {
        "cognitive_compression_mode": profile.cognitive_compression_mode,
        "compression_reasoning": profile.compression_reasoning,
        "informational_density": profile.informational_density,
        "contextual_support_level": profile.contextual_support_level,
        "retrieval_compaction": profile.retrieval_compaction,
        "explanatory_expansion": profile.explanatory_expansion,
        "redundancy_adjustment": profile.redundancy_adjustment,
        "prerequisite_support_signal": profile.prerequisite_support_signal,
        "compression_transition_reason": profile.compression_transition_reason,
        "why_this_compression_now": profile.why_this_compression_now,
    }


def _adaptive_signal_consolidation_metadata(profile) -> dict[str, object]:
    return {
        "adaptive_signal_state": profile.adaptive_signal_state,
        "consolidation_reasoning": profile.consolidation_reasoning,
        "modulation_overlap": profile.modulation_overlap,
        "reinforcement_convergence": profile.reinforcement_convergence,
        "retrieval_pressure_balance": profile.retrieval_pressure_balance,
        "reconstruction_support_balance": profile.reconstruction_support_balance,
        "pacing_consolidation": profile.pacing_consolidation,
        "stabilization_consolidation": profile.stabilization_consolidation,
        "cognitive_signal_alignment": profile.cognitive_signal_alignment,
        "why_this_consolidation_now": profile.why_this_consolidation_now,
    }


def _pedagogical_observability_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_observability_state": profile.pedagogical_observability_state,
        "observability_reasoning": profile.observability_reasoning,
        "signal_overlap_density": profile.signal_overlap_density,
        "retrieval_pressure_accumulation": profile.retrieval_pressure_accumulation,
        "compression_support_alignment": profile.compression_support_alignment,
        "scaffold_density": profile.scaffold_density,
        "continuity_stability": profile.continuity_stability,
        "modulation_redundancy": profile.modulation_redundancy,
        "expression_variation_balance": profile.expression_variation_balance,
        "intervention_repetition_signal": profile.intervention_repetition_signal,
        "trajectory_consistency": profile.trajectory_consistency,
        "adaptive_behavior_summary": profile.adaptive_behavior_summary,
        "signal_overlap_reason": profile.signal_overlap_reason,
        "support_density_reason": profile.support_density_reason,
        "retrieval_balance_reason": profile.retrieval_balance_reason,
        "modulation_consistency": profile.modulation_consistency,
        "continuity_observation": profile.continuity_observation,
        "stability_profile": profile.stability_profile,
        "why_this_observation_now": profile.why_this_observation_now,
    }


def _runtime_traceability_metadata(profile) -> dict[str, object]:
    return {
        "runtime_trace_state": profile.runtime_trace_state,
        "behavioral_trace": profile.behavioral_trace,
        "trace_reasoning": profile.trace_reasoning,
        "signal_contributors": profile.signal_contributors,
        "adaptation_stack": profile.adaptation_stack,
        "runtime_pressure_summary": profile.runtime_pressure_summary,
        "retrieval_density_trace": profile.retrieval_density_trace,
        "support_overlap_trace": profile.support_overlap_trace,
        "continuity_transition_trace": profile.continuity_transition_trace,
        "stabilization_trace": profile.stabilization_trace,
        "modulation_trace": profile.modulation_trace,
        "trace_alignment": profile.trace_alignment,
        "why_this_trace_now": profile.why_this_trace_now,
    }


def _pedagogical_validation_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_validation_state": profile.pedagogical_validation_state,
        "learning_effect_profile": profile.learning_effect_profile,
        "validation_reasoning": profile.validation_reasoning,
        "retrieval_effectiveness_signal": profile.retrieval_effectiveness_signal,
        "stabilization_quality_signal": profile.stabilization_quality_signal,
        "false_fluency_risk": profile.false_fluency_risk,
        "scaffold_dependency_signal": profile.scaffold_dependency_signal,
        "transfer_stability_signal": profile.transfer_stability_signal,
        "reconstruction_progress_signal": profile.reconstruction_progress_signal,
        "adaptation_overlap_signal": profile.adaptation_overlap_signal,
        "reinforcement_density_signal": profile.reinforcement_density_signal,
        "longitudinal_validation_signal": profile.longitudinal_validation_signal,
        "validation_alignment": profile.validation_alignment,
        "why_this_validation_now": profile.why_this_validation_now,
    }


def _runtime_signal_normalization_metadata(profile) -> dict[str, object]:
    return {
        "retrieval_family": profile.retrieval_family,
        "support_family": profile.support_family,
        "continuity_family": profile.continuity_family,
        "stabilization_family": profile.stabilization_family,
        "overlap_family": profile.overlap_family,
        "semantic_normalization_reasoning": profile.semantic_normalization_reasoning,
        "runtime_semantic_summary": profile.runtime_semantic_summary,
    }


def _session_stability_metrics_metadata(profile) -> dict[str, object]:
    return {
        "session_stability_state": profile.session_stability_state,
        "session_stability_reasoning": profile.session_stability_reasoning,
        "retrieval_density_metric": profile.retrieval_density_metric,
        "scaffold_load_metric": profile.scaffold_load_metric,
        "continuity_smoothness_metric": profile.continuity_smoothness_metric,
        "reconstruction_pressure_metric": profile.reconstruction_pressure_metric,
        "compression_safety_metric": profile.compression_safety_metric,
        "modulation_convergence_metric": profile.modulation_convergence_metric,
        "stabilization_sustainability_metric": profile.stabilization_sustainability_metric,
        "support_density": profile.support_density,
        "pacing_stability_metric": profile.pacing_stability_metric,
        "cognitive_balance_metric": profile.cognitive_balance_metric,
        "session_pressure_summary": profile.session_pressure_summary,
        "session_stability_summary": profile.session_stability_summary,
        "why_this_session_state": profile.why_this_session_state,
    }


def _pedagogical_tuning_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_tuning_state": profile.pedagogical_tuning_state,
        "tuning_profile_summary": profile.tuning_profile_summary,
        "tuning_reasoning": profile.tuning_reasoning,
        "retrieval_tolerance": profile.retrieval_tolerance,
        "scaffold_sensitivity": profile.scaffold_sensitivity,
        "continuity_smoothing_strength": profile.continuity_smoothing_strength,
        "compression_conservatism": profile.compression_conservatism,
        "reconstruction_support_level": profile.reconstruction_support_level,
        "pacing_relief_sensitivity": profile.pacing_relief_sensitivity,
        "overlap_tolerance": profile.overlap_tolerance,
        "stabilization_threshold": profile.stabilization_threshold,
        "modulation_density_tolerance": profile.modulation_density_tolerance,
        "intervention_rotation_sensitivity": profile.intervention_rotation_sensitivity,
        "why_this_tuning_profile": profile.why_this_tuning_profile,
    }


def _validation_harness_metadata(profile) -> dict[str, object]:
    return {
        "validation_harness_state": profile.validation_harness_state,
        "validation_harness_reasoning": profile.validation_harness_reasoning,
        "retrieval_sustainability_signal": profile.retrieval_sustainability_signal,
        "scaffold_dependency_signal": profile.scaffold_dependency_signal,
        "reconstruction_sustainability_signal": profile.reconstruction_sustainability_signal,
        "transfer_stability_signal": profile.transfer_stability_signal,
        "resurfacing_effectiveness_signal": profile.resurfacing_effectiveness_signal,
        "stabilization_reliability_signal": profile.stabilization_reliability_signal,
        "compression_safety_signal": profile.compression_safety_signal,
        "continuity_sustainability_signal": profile.continuity_sustainability_signal,
        "pacing_sustainability_signal": profile.pacing_sustainability_signal,
        "cognitive_friction_signal": profile.cognitive_friction_signal,
        "adaptive_overlap_signal": profile.adaptive_overlap_signal,
        "pedagogical_balance_signal": profile.pedagogical_balance_signal,
        "validation_confidence": profile.validation_confidence,
        "runtime_validation_summary": profile.runtime_validation_summary,
        "evidence_alignment": profile.evidence_alignment,
        "why_this_validation_state": profile.why_this_validation_state,
    }


def _session_snapshot_diff_metadata(snapshot_profile, diff_profile) -> dict[str, object]:
    return {
        "session_snapshot_state": snapshot_profile.session_snapshot_state,
        "session_snapshot_summary": snapshot_profile.session_snapshot_summary,
        "behavioral_diff_state": diff_profile.behavioral_diff_state,
        "behavioral_diff_reasoning": diff_profile.behavioral_diff_reasoning,
        "retrieval_shift": diff_profile.retrieval_shift,
        "scaffold_shift": diff_profile.scaffold_shift,
        "continuity_shift": diff_profile.continuity_shift,
        "pacing_shift": diff_profile.pacing_shift,
        "compression_shift": diff_profile.compression_shift,
        "stabilization_shift": diff_profile.stabilization_shift,
        "overlap_shift": diff_profile.overlap_shift,
        "modulation_shift": diff_profile.modulation_shift,
        "validation_shift": diff_profile.validation_shift,
        "convergence_summary": diff_profile.convergence_summary,
        "divergence_summary": diff_profile.divergence_summary,
        "runtime_behavior_delta": diff_profile.runtime_behavior_delta,
        "why_this_behavioral_diff": diff_profile.why_this_behavioral_diff,
    }


def _session_export_debug_metadata(profile) -> dict[str, object]:
    return {
        "session_export_state": profile.session_export_state,
        "runtime_export_summary": profile.runtime_export_summary,
        "pedagogical_runtime_snapshot": profile.pedagogical_runtime_snapshot,
        "validation_snapshot": profile.validation_snapshot,
        "behavioral_diff_snapshot": profile.behavioral_diff_snapshot,
        "runtime_trace_snapshot": profile.runtime_trace_snapshot,
        "stability_snapshot": profile.stability_snapshot,
        "tuning_snapshot": profile.tuning_snapshot,
        "compression_snapshot": profile.compression_snapshot,
        "continuity_snapshot": profile.continuity_snapshot,
        "support_snapshot": profile.support_snapshot,
        "retrieval_snapshot": profile.retrieval_snapshot,
        "reconstruction_snapshot": profile.reconstruction_snapshot,
        "export_reasoning": profile.export_reasoning,
        "export_alignment": profile.export_alignment,
        "export_trace_summary": profile.export_trace_summary,
    }


def _validation_dataset_awareness_metadata(profile) -> dict[str, object]:
    return {
        "validation_dataset_state": profile.validation_dataset_state,
        "validation_dataset_reasoning": profile.validation_dataset_reasoning,
        "pedagogical_scenario_family": profile.pedagogical_scenario_family,
        "retrieval_condition_profile": profile.retrieval_condition_profile,
        "scaffold_condition_profile": profile.scaffold_condition_profile,
        "continuity_condition_profile": profile.continuity_condition_profile,
        "reconstruction_condition_profile": profile.reconstruction_condition_profile,
        "compression_condition_profile": profile.compression_condition_profile,
        "transfer_condition_profile": profile.transfer_condition_profile,
        "stabilization_condition_profile": profile.stabilization_condition_profile,
        "overlap_condition_profile": profile.overlap_condition_profile,
        "pacing_condition_profile": profile.pacing_condition_profile,
        "reinforcement_condition_profile": profile.reinforcement_condition_profile,
        "runtime_validation_context": profile.runtime_validation_context,
        "comparative_validation_alignment": profile.comparative_validation_alignment,
        "dataset_awareness_summary": profile.dataset_awareness_summary,
        "why_this_validation_context": profile.why_this_validation_context,
    }


def _scientific_runtime_validation_metadata(profile) -> dict[str, object]:
    return {
        "scientific_validation_state": profile.scientific_validation_state,
        "scientific_validation_reasoning": profile.scientific_validation_reasoning,
        "runtime_benchmark_state": profile.runtime_benchmark_state,
        "regression_detection_state": profile.regression_detection_state,
        "sustainability_validation_state": profile.sustainability_validation_state,
        "cognitive_load_profile": profile.cognitive_load_profile,
        "retrieval_reliability_profile": profile.retrieval_reliability_profile,
        "scaffold_dependency_profile": profile.scaffold_dependency_profile,
        "compression_safety_profile": profile.compression_safety_profile,
        "overlap_inflation_profile": profile.overlap_inflation_profile,
        "stabilization_reliability_profile": profile.stabilization_reliability_profile,
        "continuity_reliability_profile": profile.continuity_reliability_profile,
        "reinforcement_redundancy_profile": profile.reinforcement_redundancy_profile,
        "pedagogical_regression_summary": profile.pedagogical_regression_summary,
        "runtime_benchmark_summary": profile.runtime_benchmark_summary,
        "empirical_validation_context": profile.empirical_validation_context,
        "comparative_runtime_alignment": profile.comparative_runtime_alignment,
        "reproducibility_summary": profile.reproducibility_summary,
        "why_this_validation_profile": profile.why_this_validation_profile,
    }


def _comparative_session_analytics_metadata(profile) -> dict[str, object]:
    return {
        "comparative_session_state": profile.comparative_session_state,
        "comparative_session_reasoning": profile.comparative_session_reasoning,
        "comparative_runtime_summary": profile.comparative_runtime_summary,
        "session_comparison_profile": profile.session_comparison_profile.model_dump(mode="json"),
        "baseline_session_signature": profile.baseline_session_signature,
        "candidate_session_signature": profile.candidate_session_signature,
        "retrieval_delta": profile.retrieval_delta,
        "scaffold_delta": profile.scaffold_delta,
        "compression_delta": profile.compression_delta,
        "continuity_delta": profile.continuity_delta,
        "reconstruction_delta": profile.reconstruction_delta,
        "pacing_delta": profile.pacing_delta,
        "validation_delta": profile.validation_delta,
        "sustainability_delta": profile.sustainability_delta,
        "behavioral_drift_signal": profile.behavioral_drift_signal,
        "pedagogical_regression_signal": profile.pedagogical_regression_signal,
        "comparative_validation_alignment": profile.comparative_validation_alignment,
        "why_this_comparison_state": profile.why_this_comparison_state,
    }


def _runtime_scenario_simulation_metadata(profile) -> dict[str, object]:
    return {
        "runtime_scenario_state": profile.runtime_scenario_state,
        "scenario_simulation_reasoning": profile.scenario_simulation_reasoning,
        "scenario_category": profile.scenario_category,
        "scenario_replay_snapshot": profile.scenario_replay_snapshot,
        "scenario_expected_states": profile.scenario_expected_states,
        "scenario_observed_states": profile.scenario_observed_states,
        "scenario_expectation_alignment": profile.scenario_expectation_alignment,
        "scenario_validation_outcome": profile.scenario_validation_outcome,
        "scenario_regression_signal": profile.scenario_regression_signal,
        "scenario_mismatch_reason": profile.scenario_mismatch_reason,
        "scenario_replay_summary": profile.scenario_replay_summary,
        "why_this_scenario_outcome": profile.why_this_scenario_outcome,
    }


def _empirical_validation_dataset_metadata(profile) -> dict[str, object]:
    return {
        "empirical_dataset_state": profile.empirical_dataset_state,
        "empirical_dataset_summary": profile.empirical_dataset_summary,
        "empirical_dataset_reasoning": profile.empirical_dataset_reasoning,
        "validation_case_results": [case.model_dump(mode="json") for case in profile.validation_case_results],
        "passed_cases": profile.passed_cases,
        "failed_cases": profile.failed_cases,
        "inconclusive_cases": profile.inconclusive_cases,
        "dataset_alignment_score": profile.dataset_alignment_score,
        "dataset_regression_flags": profile.dataset_regression_flags,
        "dataset_coverage_summary": profile.dataset_coverage_summary,
        "empirical_validation_context": profile.empirical_validation_context,
        "why_this_dataset_result": profile.why_this_dataset_result,
    }


def _pedagogical_benchmark_metadata(profile) -> dict[str, object]:
    return {
        "pedagogical_benchmark_state": profile.pedagogical_benchmark_state,
        "pedagogical_benchmark_summary": profile.pedagogical_benchmark_summary,
        "pedagogical_benchmark_reasoning": profile.pedagogical_benchmark_reasoning,
        "benchmark_case_reports": [case.model_dump(mode="json") for case in profile.benchmark_case_reports],
        "benchmark_total_cases": profile.benchmark_total_cases,
        "benchmark_passed_cases": profile.benchmark_passed_cases,
        "benchmark_failed_cases": profile.benchmark_failed_cases,
        "benchmark_inconclusive_cases": profile.benchmark_inconclusive_cases,
        "benchmark_regression_cases": profile.benchmark_regression_cases,
        "benchmark_regression_flags": profile.benchmark_regression_flags,
        "benchmark_regression_severity": profile.benchmark_regression_severity,
        "benchmark_readiness": profile.benchmark_readiness,
        "benchmark_alignment_score": profile.benchmark_alignment_score,
        "benchmark_coverage_summary": profile.benchmark_coverage_summary,
        "why_this_benchmark_result": profile.why_this_benchmark_result,
    }


def _micro_intervention_metadata(intervention) -> dict[str, object]:
    return {
        "micro_intervention": intervention.intervention_type,
        "micro_intervention_reason": intervention.intervention_reason,
        "cognitive_goal": intervention.cognitive_goal,
        "retrieval_support_reason": intervention.retrieval_support_reason,
        "conceptual_support_reason": intervention.conceptual_support_reason,
        "intervention_transition": intervention.intervention_transition,
        "why_this_intervention": intervention.why_this_intervention,
        "local_cognitive_strategy": intervention.local_cognitive_strategy,
        "intervention_signal": intervention.intervention_signal.model_dump(mode="json"),
    }


def _apply_intervention_to_summary(content: str, intervention, facet_profile) -> str:
    prefix = {
        "prerequisite_recall": "Ancora rapida: recupere a regra-base antes de prosseguir. ",
        "exception_alignment": "Alinhamento de excecao: compare a ressalva com a regra-base antes do detalhe. ",
        "confidence_check": "Cheque de confianca: confirme o nucleo sem reabrir explicacao longa. ",
        "guided_reconstruction": "Reconstrucao guiada: refaca o encadeamento antes de memorizar a conclusao. ",
        "lightweight_retrieval": "Recall leve: reative o ponto central com baixo custo cognitivo. ",
        "cumulative_bridge": "Ponte cumulativa: conecte este reaparecimento ao que ja foi consolidado. ",
        "semantic_reactivation": "Reativacao semantica: puxe a ideia central antes do detalhe. ",
        "contrast_reconciliation": "Reconcilie o contraste local antes de fixar a resposta. ",
        "rapid_anchor": "Ancora curta: fixe a palavra-chave antes da verificacao. ",
        "verification_step": "Verificacao leve: cheque o detalhe decisivo antes de seguir. ",
    }.get(intervention.intervention_type, "")
    facet_prefix = {
        "definition": "Foco definicional: organize primeiro o conceito-base. ",
        "rule": "Foco normativo: confirme a regra antes do detalhe. ",
        "exception": "Foco de ressalva: compare a excecao com a regra-base. ",
        "application": "Foco aplicado: leve a regra para o caso concreto. ",
        "interpretation": "Foco interpretativo: leia o contexto antes do julgamento. ",
        "recognition": "Foco de reconhecimento: identifique o marcador decisivo. ",
        "reconstruction": "Foco de reconstrucao: refaca a sequencia logica. ",
        "contextual_transfer": "Foco de transferencia: mova a regra entre contextos proximos. ",
    }.get(getattr(facet_profile, "dominant_facet", None), "")
    return prefix + facet_prefix + content


def _apply_intervention_to_question_statement(
    statement: str,
    intervention,
    facet_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    *,
    index: int,
) -> str:
    if index > 0:
        return _apply_signal_consolidation_to_question_statement(
            _apply_compression_to_question_statement(statement, compression_profile, index=index),
            consolidation_profile,
            index=index,
        )
    prefix = {
        "prerequisite_recall": "Ancora rapida: relembre a regra-base antes de julgar. ",
        "exception_alignment": "Antes de julgar, alinhe excecao e regra-base. ",
        "confidence_check": "Cheque de confianca: ",
        "guided_reconstruction": "Reconstrua o raciocinio: ",
        "lightweight_retrieval": "Recall leve: ",
        "cumulative_bridge": "Ponte cumulativa: ",
        "semantic_reactivation": "Reative a conexao central: ",
        "contrast_reconciliation": "Compare com o ponto anterior: ",
        "rapid_anchor": "Ancora curta: ",
        "verification_step": "Verificacao rapida: ",
    }.get(intervention.intervention_type, "")
    facet_prefix = {
        "recognition": "Reconheca o marcador-chave: ",
        "reconstruction": "Reconstrua a sequencia-base: ",
        "contextual_transfer": "Transfira a regra entre contextos: ",
    }.get(getattr(facet_profile, "dominant_facet", None), "")
    text = prefix + facet_prefix + statement
    return _apply_signal_consolidation_to_question_statement(
        _apply_compression_to_question_statement(
            _apply_expression_to_question_statement(text, expression_profile, index=index),
            compression_profile,
            index=index,
        ),
        consolidation_profile,
        index=index,
    )


def _apply_intervention_to_question_explanation(
    explanation: str,
    intervention,
    facet_profile,
    expression_profile,
    compression_profile,
    consolidation_profile,
    *,
    index: int,
) -> str:
    if index > 0:
        return _apply_signal_consolidation_to_question_explanation(
            _apply_compression_to_question_explanation(explanation, compression_profile, index=index),
            consolidation_profile,
            index=index,
        )
    suffix = {
        "prerequisite_recall": " A regra-base foi reativada para sustentar a aplicacao.",
        "exception_alignment": " A conciliacao entre regra e excecao foi mantida de forma explicita.",
        "confidence_check": " O objetivo aqui foi confirmar dominio com minima pressao adicional.",
        "guided_reconstruction": " A explicacao foi mantida em formato de reconstrucao guiada.",
        "lightweight_retrieval": " O bloco foi suavizado para preservar retencao com baixo atrito.",
        "cumulative_bridge": " O recall foi conectado ao historico cumulativo do conceito.",
        "semantic_reactivation": " A recuperacao buscou primeiro a ideia central do microtopico.",
        "contrast_reconciliation": " O contraste local foi mantido para reconciliar diferencas proximas.",
        "rapid_anchor": " Uma ancora curta foi usada para reduzir desorientacao conceitual.",
        "verification_step": " O foco foi checar rapidamente o detalhe mais decisivo.",
    }.get(intervention.intervention_type, "")
    facet_suffix = {
        "recognition": " A checagem privilegiou reconhecimento rapido do marcador correto.",
        "reconstruction": " A checagem privilegiou a reconstrucao do encadeamento principal.",
        "contextual_transfer": " A checagem privilegiou transferencia entre contextos proximos.",
    }.get(getattr(facet_profile, "dominant_facet", None), "")
    text = explanation + suffix + facet_suffix
    return _apply_signal_consolidation_to_question_explanation(
        _apply_compression_to_question_explanation(
            _apply_expression_to_question_explanation(text, expression_profile, index=index),
            compression_profile,
            index=index,
        ),
        consolidation_profile,
        index=index,
    )


def _apply_expression_to_summary(content: str, expression_profile) -> str:
    prefix = {
        "concise_reinforcement": "Ponto-chave: ",
        "progressive_anchor": "Passo atual: ",
        "contextual_bridge": "Ponte de contexto: ",
        "retrieval_softener": "Recupere com calma: ",
        "conceptual_clarifier": "Em termos diretos: ",
        "transition_smoother": "Antes de avancar: ",
        "pacing_relief": "Leitura leve: ",
        "focused_reconstruction": "Reconstrua em uma linha: ",
        "cumulative_reactivation": "Retome rapidamente: ",
        "stabilization_reassurance": "Confirmacao breve: ",
    }.get(expression_profile.pedagogical_expression_mode, "")
    if expression_profile.pedagogical_expression_mode in {"conceptual_clarifier", "pacing_relief"}:
        content = content.replace(" Exemplo de prova:", " Ponto de prova:")
    return prefix + content


def _apply_compression_to_summary(content: str, compression_profile) -> str:
    mode = compression_profile.cognitive_compression_mode
    prefix = {
        "prerequisite_supported": "Base visivel: ",
        "transfer_expanded": "Contexto de apoio: ",
        "reconstruction_scaffolded": "Sequencia guiada: ",
        "cumulative_lightweight": "Retomada leve: ",
        "retrieval_focused": "Nucleo de recall: ",
        "reinforcement_condensed": "Reforco enxuto: ",
    }.get(mode, "")
    if mode in {"stable_compressed", "reinforcement_condensed", "cumulative_lightweight", "guided_compact"}:
        content = content.replace("Resumo aprofundado de", "Resumo de")
        content = content.replace("Resumo estruturado de", "Resumo de")
    if mode == "retrieval_focused":
        content = content.replace("Compare a regra geral com a excecao aplicavel, destaque o contraste conceitual e observe o ponto que muda o julgamento. ", "")
        content = content.replace(" Priorize comparacoes entre cenarios e a condicao que muda a resposta.", "")
    if mode == "reconstruction_scaffolded":
        content += " Refaça primeiro a cadeia central antes de fixar o detalhe final."
    if mode == "transfer_expanded":
        content += " Mantenha o contexto comparativo visivel antes de transferir a regra."
    if mode == "prerequisite_supported":
        content += " Confirme a base normativa antes da aplicacao ou da excecao."
    return prefix + content


def _apply_signal_consolidation_to_summary(content: str, consolidation_profile) -> str:
    return _apply_signal_consolidation_to_text(content, consolidation_profile)


def _apply_expression_to_question_statement(statement: str, expression_profile, *, index: int) -> str:
    if index > 0:
        return statement
    prefix = {
        "retrieval_softener": "Sem pressa: ",
        "progressive_anchor": "Siga a trilha: ",
        "contextual_bridge": "Leve o contexto anterior: ",
        "focused_reconstruction": "Refaca a cadeia: ",
        "cumulative_reactivation": "Reative o ponto anterior: ",
        "stabilization_reassurance": "Cheque breve: ",
    }.get(expression_profile.pedagogical_expression_mode, "")
    return prefix + statement


def _apply_compression_to_question_statement(statement: str, compression_profile, *, index: int) -> str:
    if index > 0:
        return statement
    prefix = {
        "prerequisite_supported": "Base primeiro: ",
        "transfer_expanded": "Contexto visivel: ",
        "reconstruction_scaffolded": "Passo a passo: ",
        "cumulative_lightweight": "Revisita leve: ",
        "retrieval_focused": "Nucleo: ",
        "reinforcement_condensed": "Essencial: ",
    }.get(compression_profile.cognitive_compression_mode, "")
    return prefix + statement


def _apply_signal_consolidation_to_question_statement(
    statement: str,
    consolidation_profile,
    *,
    index: int,
) -> str:
    if index > 0:
        return statement
    return _apply_signal_consolidation_to_text(statement, consolidation_profile)


def _apply_expression_to_question_explanation(explanation: str, expression_profile, *, index: int) -> str:
    if index > 0:
        return explanation
    suffix = {
        "conceptual_clarifier": " A explicacao foi mantida mais direta para reduzir densidade.",
        "retrieval_softener": " A formulacao foi suavizada para manter recuperacao com menor atrito.",
        "contextual_bridge": " A explicacao preserva uma ponte curta com o contexto anterior.",
        "focused_reconstruction": " A formulacao manteve foco no encadeamento principal.",
        "cumulative_reactivation": " O reaparecimento foi mantido em framing leve e cumulativo.",
        "stabilization_reassurance": " O objetivo aqui foi confirmar estabilidade com formulacao enxuta.",
    }.get(expression_profile.pedagogical_expression_mode, "")
    return explanation + suffix


def _apply_compression_to_question_explanation(explanation: str, compression_profile, *, index: int) -> str:
    if index > 0:
        return explanation
    suffix = {
        "stable_compressed": " A explicacao foi compactada por estabilidade suficiente.",
        "retrieval_focused": " A explicacao foi mantida curta para preservar o recall.",
        "cumulative_lightweight": " A reapresentacao foi mantida leve por consolidacao previa.",
        "reconstruction_scaffolded": " A explicacao reteve apoio extra para sustentar a reconstrucao.",
        "transfer_expanded": " A explicacao reteve contexto extra para sustentar a transferencia.",
        "prerequisite_supported": " A explicacao preservou a base previa como apoio explicito.",
    }.get(compression_profile.cognitive_compression_mode, "")
    return explanation + suffix


def _apply_signal_consolidation_to_question_explanation(
    explanation: str,
    consolidation_profile,
    *,
    index: int,
) -> str:
    if index > 0:
        return explanation
    return _apply_signal_consolidation_to_text(explanation, consolidation_profile)


def _apply_signal_consolidation_to_text(text: str, consolidation_profile) -> str:
    if consolidation_profile.adaptive_signal_state not in {
        "retrieval_saturation",
        "compressed_stability",
        "reinforcement_overlap",
        "modulation_stable",
        "support_convergent",
    }:
        return text
    max_prefixes = 2 if consolidation_profile.modulation_overlap >= 0.5 else 3
    return _collapse_leading_prefixes(text, max_prefixes=max_prefixes)


def _collapse_leading_prefixes(text: str, *, max_prefixes: int) -> str:
    prefixes = [
        "Reforco enxuto: ",
        "Ponto-chave: ",
        "Base visivel: ",
        "Contexto de apoio: ",
        "Sequencia guiada: ",
        "Retomada leve: ",
        "Nucleo de recall: ",
        "Ancora rapida: ",
        "Cheque de confianca: ",
        "Recall leve: ",
        "Ponte cumulativa: ",
        "Reativacao semantica: ",
        "Verificacao leve: ",
        "Ancora curta: ",
        "Em termos diretos: ",
        "Antes de avancar: ",
        "Leitura leve: ",
        "Reconstrua em uma linha: ",
        "Retome rapidamente: ",
        "Confirmacao breve: ",
        "Sem pressa: ",
        "Siga a trilha: ",
        "Leve o contexto anterior: ",
        "Refaca a cadeia: ",
        "Reative o ponto anterior: ",
        "Cheque breve: ",
        "Base primeiro: ",
        "Contexto visivel: ",
        "Passo a passo: ",
        "Revisita leve: ",
        "Nucleo: ",
        "Essencial: ",
    ]
    remainder = text
    captured: list[str] = []
    while True:
        matched = next((prefix for prefix in prefixes if remainder.startswith(prefix)), None)
        if matched is None:
            break
        captured.append(matched)
        remainder = remainder[len(matched) :]
    if len(captured) <= max_prefixes:
        return text
    return "".join(captured[:max_prefixes]) + remainder


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
