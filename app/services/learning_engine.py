from __future__ import annotations

from datetime import datetime, timedelta
from math import exp

from app.domain.models import (
    ErrorType,
    ItemState,
    LearningPlan,
    LearningPlanEntry,
    StudyBlock,
    StudyStrategy,
    TopicNode,
    TopicLearningState,
    utc_now,
)
from app.services.curriculum_scheduler import CurriculumScheduler


ERROR_TYPE_WEIGHTS = {
    "conceptual": 1.0,
    "interpretation": 0.7,
    "memory": 0.5,
    "attention": 0.3,
}

MICROTOPIC_PRIORITY_WEIGHT = 0.25
MICROTOPIC_SCORE_CAP = 1.5
MICROTOPIC_TOP_SCORES = 3
MICROTOPIC_FULL_WEIGHT_MIN_COUNT = 2
MICROTOPIC_MAX_RELATIVE_DELTA = 0.25


def get_dominant_error_type(performance_data) -> str | None:
    distribution = dict(performance_data.get("error_distribution", {}) or {})
    for error_type in ERROR_TYPE_WEIGHTS:
        distribution.setdefault(error_type, 0)
    if not distribution or max(distribution.values(), default=0) <= 0:
        return None
    return max(distribution.items(), key=lambda item: item[1])[0]


def compute_dynamic_priority(topic_data: dict) -> float:
    total_questions = int(topic_data.get("total_questions", 0) or 0)
    correct_answers = int(topic_data.get("correct_answers", 0) or 0)
    recent_errors = int(topic_data.get("recent_errors", 0) or 0)
    error_distribution = dict(topic_data.get("error_distribution", {}) or {})

    accuracy = correct_answers / max(total_questions, 1)
    weighted_errors = sum(
        int(error_distribution.get(error_type, 0) or 0) * weight
        for error_type, weight in ERROR_TYPE_WEIGHTS.items()
    )
    priority = (
        (1 - accuracy) * 0.6
        + (recent_errors * 0.3)
        + (weighted_errors * 0.1)
        + (0.1 if total_questions == 0 else 0.0)
    )
    return float(priority)


def compute_microtopic_priority(microtopic_data: dict) -> float:
    total_questions = int(microtopic_data.get("total_questions", 0) or 0)
    correct_answers = int(microtopic_data.get("correct_answers", 0) or 0)
    recent_errors = int(microtopic_data.get("recent_errors", 0) or 0)
    error_distribution = dict(microtopic_data.get("error_distribution", {}) or {})

    accuracy = correct_answers / max(total_questions, 1)
    weighted_errors = sum(
        int(error_distribution.get(error_type, 0) or 0) * weight
        for error_type, weight in ERROR_TYPE_WEIGHTS.items()
    )
    priority = (
        (1 - accuracy) * 0.6
        + (recent_errors * 0.3)
        + (weighted_errors * 0.1)
        + (0.1 if total_questions == 0 else 0.0)
    )
    return float(priority)


def aggregate_topic_priority(topic_priority: float, microtopic_scores: list[float]) -> float:
    if not microtopic_scores:
        return float(topic_priority)

    ordered_scores = sorted(
        min(float(score), MICROTOPIC_SCORE_CAP)
        for score in microtopic_scores
        if score >= 0.0
    )
    if not ordered_scores:
        return float(topic_priority)

    strongest_scores = ordered_scores[-MICROTOPIC_TOP_SCORES:]
    strongest_score = strongest_scores[-1]
    average_score = sum(strongest_scores) / len(strongest_scores)
    microtopic_signal = strongest_score * 0.6 + average_score * 0.4
    sample_weight = min(
        len(strongest_scores) / MICROTOPIC_FULL_WEIGHT_MIN_COUNT,
        1.0,
    )
    effective_weight = MICROTOPIC_PRIORITY_WEIGHT * sample_weight
    blended_priority = (
        topic_priority * (1 - effective_weight)
        + microtopic_signal * effective_weight
    )
    lower_bound = topic_priority * (1 - MICROTOPIC_MAX_RELATIVE_DELTA)
    upper_bound = topic_priority * (1 + MICROTOPIC_MAX_RELATIVE_DELTA)
    return float(min(max(blended_priority, lower_bound), upper_bound))


def resolve_study_strategy(entry: LearningPlanEntry) -> StudyStrategy:
    error_type = entry.dominant_error_type
    if error_type == "conceptual":
        return StudyStrategy.THEORY_REVIEW
    if error_type == "interpretation":
        return StudyStrategy.QUESTIONS
    if error_type == "memory":
        return StudyStrategy.MIXED
    if error_type == "attention":
        return StudyStrategy.QUICK_REVIEW
    return StudyStrategy.MIXED


def _priority_intensity(priority_score: float) -> str:
    if priority_score > 0.7:
        return "high"
    if priority_score >= 0.4:
        return "normal"
    return "light"


def build_study_blocks(entry: LearningPlanEntry) -> list[StudyBlock]:
    strategy = entry.study_strategy or StudyStrategy.MIXED
    intensity = entry.review_intensity or _priority_intensity(entry.priority_score)
    normalized_intensity = {
        "high": "deep",
        "normal": "medium",
        "light": "light",
        "deep": "deep",
        "medium": "medium",
    }.get(intensity, "light")
    microtopic_performance = dict(entry.performance_data.get("microtopic_performance", {}) or {})
    topic_node = (
        TopicNode(title=entry.topic_title, level=2, content=entry.topic_content or "", children=[])
        if entry.topic_content
        else None
    )

    summary_depth = {
        "deep": "deep",
        "medium": "medium",
        "light": "light",
    }[normalized_intensity]
    question_quantity = {
        "deep": 5,
        "medium": 4,
        "light": 2,
    }[normalized_intensity]

    if strategy == StudyStrategy.THEORY_REVIEW:
        return [
            StudyBlock(
                type="summary",
                topic_id=entry.topic_id,
                depth=summary_depth,
                curriculum_role=entry.curriculum_role,
                review_intensity=entry.review_intensity,
                topic_node=topic_node,
                microtopic_performance=microtopic_performance,
            ),
            StudyBlock(
                type="questions",
                topic_id=entry.topic_id,
                quantity=question_quantity,
                curriculum_role=entry.curriculum_role,
                review_intensity=entry.review_intensity,
                topic_node=topic_node,
                microtopic_performance=microtopic_performance,
            ),
        ]
    if strategy == StudyStrategy.QUESTIONS:
        return [
            StudyBlock(
                type="questions",
                topic_id=entry.topic_id,
                quantity=question_quantity,
                curriculum_role=entry.curriculum_role,
                review_intensity=entry.review_intensity,
                topic_node=topic_node,
                microtopic_performance=microtopic_performance,
            ),
        ]
    if strategy == StudyStrategy.QUICK_REVIEW:
        if normalized_intensity == "light":
            return [
                StudyBlock(
                    type="summary",
                    topic_id=entry.topic_id,
                    depth="light",
                    curriculum_role=entry.curriculum_role,
                    review_intensity=entry.review_intensity,
                    topic_node=topic_node,
                    microtopic_performance=microtopic_performance,
                ),
            ]
        return [
            StudyBlock(
                type="questions",
                topic_id=entry.topic_id,
                quantity=question_quantity,
                curriculum_role=entry.curriculum_role,
                review_intensity=entry.review_intensity,
                topic_node=topic_node,
                microtopic_performance=microtopic_performance,
            ),
        ]
    return [
        StudyBlock(
            type="summary",
            topic_id=entry.topic_id,
            depth="light",
            curriculum_role=entry.curriculum_role,
            review_intensity=entry.review_intensity,
            topic_node=topic_node,
            microtopic_performance=microtopic_performance,
        ),
        StudyBlock(
            type="questions",
            topic_id=entry.topic_id,
            quantity=question_quantity,
            curriculum_role=entry.curriculum_role,
            review_intensity=entry.review_intensity,
            topic_node=topic_node,
            microtopic_performance=microtopic_performance,
        ),
    ]


class LearningDecisionEngine:
    SESSION_RELATIVE_SCORE_THRESHOLD = 0.30
    SESSION_MIN_NORMALIZED_PRIORITY = 0.15
    SESSION_CONSECUTIVE_DROP_FACTOR = 0.55
    SESSION_TOP_RAW_PRIORITY_FLOOR = 0.40
    SESSION_ABRUPT_DROP_FACTOR = 0.40
    SESSION_PREVIOUS_DROP_FACTOR = 0.50
    SESSION_ABRUPT_DROP_DELTA = 0.45

    def __init__(self, repository, now_provider=None):
        self.repository = repository
        self.now_provider = now_provider or utc_now

    def build_review_plan(
        self,
        *,
        title: str,
        max_questions: int = 5,
        candidate_documents: list | None = None,
    ) -> LearningPlan:
        documents = candidate_documents or self.repository.list_documents()
        if not documents:
            return LearningPlan(title=title)

        progress = self.repository.load_progress()
        now = self.now_provider()
        topic_candidates: list[dict] = []
        total_documents = len(documents)
        sorted_documents = sorted(documents, key=lambda item: item.created_at, reverse=True)

        for rank, document in enumerate(sorted_documents):
            for topic in document.topics:
                topic_state = progress.topic_learning_states.get(
                    topic.id, TopicLearningState(topic_id=topic.id)
                )
                recommended_difficulty = self._recommended_difficulty(topic_state)
                question_candidates = self._rank_question_candidates(
                    document=document,
                    topic_id=topic.id,
                    recommended_difficulty=recommended_difficulty,
                    item_states=progress.item_states,
                    now=now,
                )
                if not question_candidates:
                    continue

                raw_priority, reasons, score_breakdown = self._score_topic(
                    topic_state=topic_state,
                    rank=rank,
                    total_documents=total_documents,
                    now=now,
                )
                topic_candidates.append(
                    {
                        "document": document,
                        "topic": topic,
                        "recommended_difficulty": recommended_difficulty,
                        "question_candidates": question_candidates,
                        "raw_priority": raw_priority,
                        "reasons": reasons,
                        "score_breakdown": score_breakdown,
                        "performance_data": {
                            "total_questions": topic_state.total_questions,
                            "correct_answers": topic_state.correct_answers,
                            "recent_errors": topic_state.recent_errors,
                            "error_distribution": dict(topic_state.error_distribution),
                            "last_seen_at": (
                                topic_state.last_seen_at.isoformat()
                                if topic_state.last_seen_at
                                else None
                            ),
                        },
                        "microtopic_performance": [
                            {
                                "id": microtopic_id,
                                **state.model_dump(mode="json"),
                            }
                            for microtopic_id, state in progress.microtopic_performance.items()
                            if state.topic_id == topic.id
                        ],
                    }
                )

        self._apply_curriculum_schedule(topic_candidates)
        ranked_entries = self._build_ranked_entries(topic_candidates, now)
        ranked_entries.sort(
            key=lambda entry: (entry.priority_score, entry.recommended_difficulty),
            reverse=True,
        )
        selected_entries = self._trim_entries(ranked_entries, max_questions=max_questions)
        return LearningPlan(
            title=title,
            generated_at=now,
            entries=[
                entry.model_copy(update=self._build_entry_execution(entry))
                for entry in selected_entries
            ],
        )

    def _build_entry_execution(self, entry: LearningPlanEntry) -> dict[str, object]:
        strategy = resolve_study_strategy(entry).value
        enriched_entry = entry.model_copy(update={"study_strategy": strategy})
        return {
            "study_strategy": strategy,
            "study_blocks": build_study_blocks(enriched_entry),
        }

    def _apply_curriculum_schedule(self, topic_candidates: list[dict]) -> None:
        scheduler = CurriculumScheduler()
        snapshots = [
            {
                "topic_id": candidate["topic"].id,
                "created_at": candidate["document"].created_at,
                "performance_data": candidate.get("performance_data", {}),
                "dominant_error_type": get_dominant_error_type(candidate.get("performance_data", {})),
            }
            for candidate in topic_candidates
        ]
        assignments = scheduler.schedule(snapshots)
        for candidate in topic_candidates:
            assignment = assignments.get(candidate["topic"].id, {})
            candidate["curriculum_role"] = assignment.get("curriculum_role")
            candidate["review_intensity"] = assignment.get("review_intensity")
            candidate["curriculum_adjustment"] = assignment.get("priority_adjustment", 0.0)
            candidate["curriculum_reasoning"] = assignment.get("curriculum_reasoning", [])

    def _build_ranked_entries(self, topic_candidates: list[dict], now: datetime) -> list[LearningPlanEntry]:
        if not topic_candidates:
            return []

        scored_candidates: list[dict[str, object]] = []
        resolved_raw_scores: list[float] = []
        for candidate in topic_candidates:
            topic_dynamic_priority = (
                compute_dynamic_priority(candidate["performance_data"])
                if candidate.get("performance_data")
                else candidate["raw_priority"]
            )
            microtopic_scores = [
                compute_microtopic_priority(microtopic_data)
                for microtopic_data in candidate.get("microtopic_performance", [])
            ]
            microtopic_adjusted_priority = aggregate_topic_priority(
                topic_dynamic_priority,
                microtopic_scores,
            )
            final_priority = microtopic_adjusted_priority + float(
                candidate.get("curriculum_adjustment", 0.0) or 0.0
            )
            scored_candidates.append(
                {
                    "topic_dynamic_priority": topic_dynamic_priority,
                    "microtopic_scores": microtopic_scores,
                    "microtopic_adjusted_priority": microtopic_adjusted_priority,
                    "final_priority": final_priority,
                }
            )
            resolved_raw_scores.append(final_priority)
        min_score = min(resolved_raw_scores)
        max_score = max(resolved_raw_scores)

        ranked_entries: list[LearningPlanEntry] = []
        for candidate, scoring in zip(topic_candidates, scored_candidates, strict=False):
            resolved_raw_priority = scoring["final_priority"]
            topic_dynamic_priority = scoring["topic_dynamic_priority"]
            microtopic_scores = scoring["microtopic_scores"]
            microtopic_adjusted_priority = scoring["microtopic_adjusted_priority"]
            normalized_priority = self._normalize_score(
                resolved_raw_priority, min_score, max_score
            )
            score_breakdown = dict(candidate["score_breakdown"])
            score_breakdown["static_priority"] = round(candidate["raw_priority"], 4)
            score_breakdown["topic_dynamic_priority"] = round(topic_dynamic_priority, 4)
            score_breakdown["microtopic_adjusted_priority"] = round(microtopic_adjusted_priority, 4)
            score_breakdown["microtopic_adjustment"] = round(
                microtopic_adjusted_priority - topic_dynamic_priority, 4
            )
            score_breakdown["microtopic_count"] = len(microtopic_scores)
            score_breakdown["microtopic_signal"] = round(
                (sum(microtopic_scores) / len(microtopic_scores)) if microtopic_scores else 0.0,
                4,
            )
            score_breakdown["curriculum_adjustment"] = round(
                float(candidate.get("curriculum_adjustment", 0.0) or 0.0), 4
            )
            score_breakdown["dynamic_priority"] = round(resolved_raw_priority, 4)
            score_breakdown["raw_priority"] = round(resolved_raw_priority, 4)
            score_breakdown["normalized_priority"] = normalized_priority

            item_reasons = {
                question["id"]: question["reasons"]
                for question in candidate["question_candidates"]
            }
            ranked_entries.append(
                LearningPlanEntry(
                    document_id=candidate["document"].id,
                        document_title=candidate["document"].title,
                        topic_id=candidate["topic"].id,
                        topic_title=candidate["topic"].title,
                        topic_content=candidate["topic"].content,
                        question_ids=[question["id"] for question in candidate["question_candidates"]],
                        priority_score=normalized_priority,
                    recommended_difficulty=candidate["recommended_difficulty"],
                        reasons=candidate["reasons"] + candidate.get("curriculum_reasoning", []),
                        score_breakdown=score_breakdown,
                        item_reasons=item_reasons,
                        performance_data={
                            **candidate.get("performance_data", {}),
                            "microtopic_performance": {
                                microtopic_data.get("id", f"micro-{index}"): microtopic_data
                                for index, microtopic_data in enumerate(
                                    candidate.get("microtopic_performance", [])
                                )
                            },
                        },
                        dominant_error_type=get_dominant_error_type(
                            candidate.get("performance_data", {})
                        ),
                        curriculum_role=candidate.get("curriculum_role"),
                        review_intensity=candidate.get("review_intensity"),
                    )
            )
        return ranked_entries

    def _normalize_score(self, raw_score: float, min_score: float, max_score: float) -> float:
        if max_score <= 0:
            return 0.0
        normalized = raw_score / max_score
        return round(max(0.0, min(1.0, normalized)), 4)

    def _trim_entries(
        self, entries: list[LearningPlanEntry], *, max_questions: int
    ) -> list[LearningPlanEntry]:
        eligible_entries = self._eligible_entries_for_session(entries)
        if not eligible_entries:
            return []

        sequentially_eligible_entries: list[LearningPlanEntry] = []
        previous_selected_entry: LearningPlanEntry | None = None
        top_raw_priority = eligible_entries[0].score_breakdown.get(
            "raw_priority", eligible_entries[0].priority_score
        )
        for entry in eligible_entries:
            if previous_selected_entry is not None:
                previous_raw = previous_selected_entry.score_breakdown.get(
                    "raw_priority", previous_selected_entry.priority_score
                )
                current_raw = entry.score_breakdown.get(
                    "raw_priority", entry.priority_score
                )
                below_top_floor = (
                    current_raw
                    < top_raw_priority * self.SESSION_TOP_RAW_PRIORITY_FLOOR
                )
                if (
                    below_top_floor
                    and (
                        current_raw
                        < previous_raw * self.SESSION_CONSECUTIVE_DROP_FACTOR
                        or len(sequentially_eligible_entries) >= 2
                    )
                ):
                    break
            sequentially_eligible_entries.append(entry)
            previous_selected_entry = entry

        selected_map: dict[str, LearningPlanEntry] = {}
        used_similarity_groups: set[str] = set()
        selected_questions = 0

        # Primeira passada: no maximo um item por topico, para aumentar diversidade.
        for entry in sequentially_eligible_entries:
            if selected_questions >= max_questions:
                break
            chosen = self._pick_questions_for_entry(
                entry=entry,
                already_selected=[],
                remaining=1,
                used_similarity_groups=used_similarity_groups,
            )
            if not chosen:
                continue
            selected_map[entry.topic_id] = entry.model_copy(update={"question_ids": chosen})
            selected_questions += len(chosen)

        # Segunda passada: completar a sessao com itens adicionais, ainda evitando repeticao inutil.
        for entry in sequentially_eligible_entries:
            if selected_questions >= max_questions:
                break
            existing = selected_map.get(entry.topic_id)
            already_selected = existing.question_ids if existing else []
            remaining = min(2 - len(already_selected), max_questions - selected_questions)
            if remaining <= 0:
                continue
            extra = self._pick_questions_for_entry(
                entry=entry,
                already_selected=already_selected,
                remaining=remaining,
                used_similarity_groups=used_similarity_groups,
            )
            if not extra:
                continue
            updated_ids = already_selected + extra
            updated_entry = entry.model_copy(update={"question_ids": updated_ids})
            selected_map[entry.topic_id] = updated_entry
            selected_questions += len(extra)

        ordered_entries = [
            selected_map[entry.topic_id]
            for entry in sequentially_eligible_entries
            if entry.topic_id in selected_map
        ]
        return ordered_entries

    def _eligible_entries_for_session(
        self, entries: list[LearningPlanEntry]
    ) -> list[LearningPlanEntry]:
        if not entries:
            return []

        top_score = entries[0].score_breakdown.get("raw_priority", entries[0].priority_score)
        minimum_score = top_score * self.SESSION_RELATIVE_SCORE_THRESHOLD
        apply_normalized_floor = len(entries) >= 3
        eligible: list[LearningPlanEntry] = []
        previous_score = top_score

        for entry in entries:
            candidate_score = entry.score_breakdown.get("raw_priority", entry.priority_score)
            normalized_score = entry.score_breakdown.get(
                "normalized_priority", entry.priority_score
            )
            if candidate_score < minimum_score:
                break
            if (
                apply_normalized_floor
                and normalized_score < self.SESSION_MIN_NORMALIZED_PRIORITY
            ):
                break
            if self._has_abrupt_drop_from_top(
                candidate_score=candidate_score,
                top_score=top_score,
                previous_score=previous_score,
                already_selected=len(eligible),
            ):
                break
            eligible.append(entry)
            previous_score = candidate_score

        return eligible

    def _has_abrupt_drop_from_top(
        self,
        *,
        candidate_score: float,
        top_score: float,
        previous_score: float,
        already_selected: int,
    ) -> bool:
        if already_selected < 2:
            return False
        return (
            candidate_score < top_score * self.SESSION_ABRUPT_DROP_FACTOR
            and candidate_score < previous_score * self.SESSION_PREVIOUS_DROP_FACTOR
            and (top_score - candidate_score) > self.SESSION_ABRUPT_DROP_DELTA
        )

    def _pick_questions_for_entry(
        self,
        *,
        entry: LearningPlanEntry,
        already_selected: list[str],
        remaining: int,
        used_similarity_groups: set[str],
    ) -> list[str]:
        chosen: list[str] = []
        local_groups = set()
        for question_id in entry.question_ids:
            if question_id in already_selected or question_id in chosen:
                continue
            group = f"{entry.topic_id}:{question_id}"
            reasons = entry.item_reasons.get(question_id, [])
            for reason in reasons:
                if reason.startswith("similarity_group:"):
                    group = reason.split(":", maxsplit=1)[1]
                    break
            if group in used_similarity_groups or group in local_groups:
                continue
            chosen.append(question_id)
            local_groups.add(group)
            used_similarity_groups.add(group)
            if len(chosen) >= remaining:
                break
        return chosen

    def _recommended_difficulty(self, topic_state: TopicLearningState) -> int:
        if topic_state.attempts == 0:
            return 1

        if (
            topic_state.last_error_type in {ErrorType.INTERPRETATION, ErrorType.CONCEPT_CONFUSION}
            and topic_state.last_error_at
            and self.now_provider() - topic_state.last_error_at < timedelta(days=3)
        ):
            return 1

        consistency_bonus = self._consistency_bonus(topic_state)
        if consistency_bonus == 0:
            return 1
        return min(4, 1 + consistency_bonus)

    def _score_topic(
        self,
        *,
        topic_state: TopicLearningState,
        rank: int,
        total_documents: int,
        now: datetime,
    ) -> tuple[float, list[str], dict[str, float]]:
        error_rate = (
            topic_state.incorrect_attempts / topic_state.attempts
            if topic_state.attempts
            else 0.0
        )
        error_volume = 1 - exp(-topic_state.incorrect_attempts / 2) if topic_state.incorrect_attempts else 0.0
        error_pressure = min(1.0, error_rate * 0.6 + error_volume * 0.4)
        content_recency = max(0.05, 1 - (rank / max(total_documents - 1, 1)))
        review_gap = self._review_gap_score(topic_state.last_seen_at, now)
        novelty = 0.2 if topic_state.attempts == 0 else 0.0
        recent_error_bonus = (
            0.25
            if topic_state.last_error_at and now - topic_state.last_error_at < timedelta(days=2)
            else 0.0
        )
        repetition_penalty = (
            0.2
            if topic_state.last_seen_at and now - topic_state.last_seen_at < timedelta(hours=12)
            else 0.0
        )

        score = round(
            0.45 * error_pressure
            + 0.25 * content_recency
            + 0.15 * review_gap
            + 0.15 * novelty
            + recent_error_bonus
            - repetition_penalty,
            4,
        )

        reasons = []
        if topic_state.incorrect_attempts:
            reasons.append("Topico com pressao de erro acumulada.")
        if topic_state.last_error_at and now - topic_state.last_error_at < timedelta(days=2):
            reasons.append("Erro recente aumenta a prioridade de revisao.")
        if topic_state.attempts == 0:
            reasons.append("Topico novo ainda nao consolidado.")
        if topic_state.streak_correct >= 2:
            reasons.append("Bom desempenho recente permite elevar a dificuldade.")
        if not reasons:
            reasons.append("Topico priorizado por recencia e necessidade de manutencao.")
        score_breakdown = {
            "error_pressure": round(error_pressure, 4),
            "content_recency": round(content_recency, 4),
            "review_gap": round(review_gap, 4),
            "novelty": round(novelty, 4),
            "recent_error_bonus": round(recent_error_bonus, 4),
            "repetition_penalty": round(repetition_penalty, 4),
        }
        return score, reasons, score_breakdown

    def _consistency_bonus(self, topic_state: TopicLearningState) -> int:
        if topic_state.streak_correct < 3 or topic_state.correct_attempts < 3:
            return 0
        if topic_state.first_seen_at is None or topic_state.last_correct_at is None:
            return 0
        span_days = (topic_state.last_correct_at - topic_state.first_seen_at).total_seconds() / 86400
        accuracy = (
            topic_state.correct_attempts / topic_state.attempts
            if topic_state.attempts
            else 0.0
        )
        if span_days < 2 or accuracy < 0.7:
            return 0
        if topic_state.streak_correct >= 8 and accuracy >= 0.9 and span_days >= 10:
            return 3
        if topic_state.streak_correct >= 5 and accuracy >= 0.85 and span_days >= 5:
            return 2
        return 1

    def _review_gap_score(self, last_seen_at: datetime | None, now: datetime) -> float:
        if last_seen_at is None:
            return 0.6
        elapsed = now - last_seen_at
        days = elapsed.total_seconds() / 86400
        return min(1.0, days / 7)

    def _rank_question_candidates(
        self,
        *,
        document,
        topic_id: str,
        recommended_difficulty: int,
        item_states: dict[str, ItemState],
        now: datetime,
    ) -> list[dict]:
        questions = [question for question in document.questions if question.topic_id == topic_id]
        if not questions:
            return []

        ranked = []
        for question in questions:
            state = item_states.get(
                question.id,
                ItemState(
                    question_id=question.id,
                    topic_id=topic_id,
                    similarity_group=question.similarity_group,
                ),
            )
            item_score, reasons, breakdown = self._score_item(
                question=question,
                state=state,
                recommended_difficulty=recommended_difficulty,
                now=now,
            )
            similarity_group = question.similarity_group or f"{topic_id}:{question.id}"
            ranked.append(
                {
                    "id": question.id,
                    "score": item_score,
                    "reasons": reasons + [f"similarity_group:{similarity_group}"],
                    "breakdown": breakdown,
                    "similarity_group": similarity_group,
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked

    def _score_item(
        self,
        *,
        question,
        state: ItemState,
        recommended_difficulty: int,
        now: datetime,
    ) -> tuple[float, list[str], dict[str, float]]:
        novelty = 0.25 if state.seen_count == 0 else 0.0
        mistake_pressure = min(0.35, state.incorrect_count * 0.12)
        repetition_penalty = (
            0.45 if state.last_seen_at and now - state.last_seen_at < timedelta(hours=12) else 0.0
        )
        exposure_penalty = min(0.2, state.seen_count * 0.04)
        difficulty_match = max(
            0.0, 0.2 - (abs(question.difficulty_level - recommended_difficulty) * 0.08)
        )
        item_score = round(
            novelty + mistake_pressure + difficulty_match - repetition_penalty - exposure_penalty,
            4,
        )
        reasons = []
        if novelty:
            reasons.append("Item novo dentro do topico evita repeticao imediata.")
        if mistake_pressure:
            reasons.append("Item reforca um ponto com historico de erro.")
        if repetition_penalty:
            reasons.append("Item foi penalizado por repeticao muito recente.")
        if difficulty_match >= 0.12:
            reasons.append("Item alinhado ao nivel de dificuldade recomendado.")
        if not reasons:
            reasons.append("Item selecionado para manutencao equilibrada do topico.")
        breakdown = {
            "novelty": round(novelty, 4),
            "mistake_pressure": round(mistake_pressure, 4),
            "difficulty_match": round(difficulty_match, 4),
            "repetition_penalty": round(repetition_penalty, 4),
            "exposure_penalty": round(exposure_penalty, 4),
        }
        return item_score, reasons, breakdown
