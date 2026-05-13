from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import LearningPlanEntry, MicrotopicSessionCandidate, TopicNode
from app.services.learning_engine import compute_microtopic_priority
from app.services.microtopic_extractor import MicroTopicExtractor
from app.services.pedagogical_stability import analyze_pedagogical_stability


class MicrotopicSessionComposer:
    ACTIVE_QUOTAS = {
        "deep": 3,
        "medium": 2,
        "light": 1,
    }
    CUMULATIVE_QUOTAS = {
        "deep": 2,
        "medium": 2,
        "light": 1,
    }
    MAX_TOPIC_QUOTA = 3
    WEAK_BONUS_CAP = 1

    def compose(self, entries: list[LearningPlanEntry]) -> list[MicrotopicSessionCandidate]:
        topic_candidate_groups: list[list[MicrotopicSessionCandidate]] = []
        for topic_position, entry in enumerate(entries):
            topic_candidate_groups.append(
                self._build_candidates_for_entry(entry, topic_position=topic_position)
            )
        return self._interleave(topic_candidate_groups, entries)

    def _build_candidates_for_entry(
        self,
        entry: LearningPlanEntry,
        *,
        topic_position: int,
    ) -> list[MicrotopicSessionCandidate]:
        microtopics = self._extract_microtopics(entry)
        performance_map = dict(entry.performance_data.get("microtopic_performance", {}) or {})
        pedagogical_memory_map = dict(entry.performance_data.get("pedagogical_memory", {}) or {})
        curriculum_role = entry.curriculum_role or "active"
        review_intensity = entry.review_intensity or "light"

        candidates: list[MicrotopicSessionCandidate] = []
        for microtopic in microtopics:
            performance = self._normalize_microtopic_performance(performance_map.get(microtopic.id))
            pedagogical_memory = self._normalize_pedagogical_memory(
                pedagogical_memory_map.get(microtopic.id)
            )
            weakness_signal = min(compute_microtopic_priority(performance) / 1.5, 1.0)
            resurfacing_signal = self._resurfacing_signal(
                performance.get("last_reviewed_at") or performance.get("last_seen_at")
            )
            difficulty_signal = min(max(microtopic.difficulty_weight - 1.0, 0.0) / 0.4, 1.0)
            curriculum_signal = self._curriculum_signal(curriculum_role, review_intensity)
            stabilization_discount = self._stabilization_discount(performance)
            exposure_discount = self._exposure_discount(performance)
            temporal_signal = self._temporal_signal(
                resurfacing_signal=resurfacing_signal,
                pedagogical_memory=pedagogical_memory,
            )
            stability = analyze_pedagogical_stability(
                performance=performance,
                pedagogical_memory=pedagogical_memory,
                resurfacing_signal=max(resurfacing_signal, temporal_signal),
            )
            pedagogical_discount = min(
                float(stability["retention_confidence"]) * 0.06
                + float(stability["intervention_fatigue"]) * 0.05,
                0.08,
            )
            composition_score = max(
                0.0,
                min(
                    1.0,
                    weakness_signal * 0.30
                    + resurfacing_signal * 0.20
                    + difficulty_signal * 0.15
                    + curriculum_signal * 0.25
                    + temporal_signal
                    + min(float(stability["reinforcement_signal"]) * 0.08, 0.08)
                    - stabilization_discount
                    - exposure_discount,
                )
                - pedagogical_discount,
            )
            selection_reason = self._selection_reason(
                weakness_signal=weakness_signal,
                resurfacing_signal=max(resurfacing_signal, temporal_signal * 4),
                curriculum_role=curriculum_role,
                temporal_signal=temporal_signal,
            )
            candidates.append(
                MicrotopicSessionCandidate(
                    microtopic_id=microtopic.id,
                    microtopic_title=microtopic.title,
                    microtopic_content=microtopic.content,
                    topic_id=entry.topic_id,
                    topic_title=entry.topic_title,
                    curriculum_role=curriculum_role,
                    review_intensity=review_intensity,
                    microtopic_priority=round(weakness_signal, 4),
                    selection_reason=selection_reason,
                    difficulty_weight=microtopic.difficulty_weight,
                    resurfacing_signal=round(resurfacing_signal, 4),
                    weakness_signal=round(weakness_signal, 4),
                    composition_score=round(composition_score, 4),
                    composition_breakdown={
                        "weakness": round(weakness_signal, 4),
                        "resurfacing": round(resurfacing_signal, 4),
                        "difficulty": round(difficulty_signal, 4),
                        "curriculum": round(curriculum_signal, 4),
                        "temporal": round(temporal_signal, 4),
                        "stability": round(float(stability["pedagogical_stability_score"]), 4),
                        "fatigue": round(float(stability["intervention_fatigue"]), 4),
                        "stabilization_discount": round(stabilization_discount, 4),
                        "exposure_discount": round(exposure_discount, 4),
                        "pedagogical_discount": round(pedagogical_discount, 4),
                    },
                    topic_position=topic_position,
                )
            )

        ordered = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.composition_score,
                -candidate.weakness_signal,
                -candidate.resurfacing_signal,
                candidate.microtopic_title,
                candidate.microtopic_id,
            ),
        )
        selected = self._apply_quota(ordered, curriculum_role=curriculum_role, review_intensity=review_intensity)
        for candidate_position, candidate in enumerate(selected):
            candidate.candidate_position = candidate_position
        return selected

    def _apply_quota(
        self,
        ordered: list[MicrotopicSessionCandidate],
        *,
        curriculum_role: str,
        review_intensity: str,
    ) -> list[MicrotopicSessionCandidate]:
        if not ordered:
            return []

        quota_map = self.ACTIVE_QUOTAS if curriculum_role == "active" else self.CUMULATIVE_QUOTAS
        quota = quota_map.get(review_intensity, 1)
        weak_count = sum(1 for candidate in ordered if candidate.weakness_signal >= 0.55)
        quota = min(self.MAX_TOPIC_QUOTA, quota + min(self.WEAK_BONUS_CAP, weak_count))

        selected = ordered[:quota]
        if curriculum_role == "cumulative" and not any(candidate.resurfacing_signal >= 0.5 for candidate in selected):
            resurfaced = next((candidate for candidate in ordered if candidate.resurfacing_signal >= 0.5), None)
            if resurfaced and resurfaced not in selected:
                if len(selected) < quota:
                    selected.append(resurfaced)
                else:
                    selected[-1] = resurfaced
        return selected

    def _interleave(
        self,
        topic_candidate_groups: list[list[MicrotopicSessionCandidate]],
        entries: list[LearningPlanEntry],
    ) -> list[MicrotopicSessionCandidate]:
        active_groups = []
        cumulative_groups = []
        by_topic_order = {entry.topic_id: index for index, entry in enumerate(entries)}

        for group in topic_candidate_groups:
            if not group:
                continue
            target = active_groups if group[0].curriculum_role == "active" else cumulative_groups
            target.append(group)

        active_groups.sort(key=lambda group: by_topic_order[group[0].topic_id])
        cumulative_groups.sort(key=lambda group: by_topic_order[group[0].topic_id])

        ordered_candidates: list[MicrotopicSessionCandidate] = []
        max_rounds = max((len(group) for group in active_groups + cumulative_groups), default=0)
        for round_index in range(max_rounds):
            for group in active_groups:
                if round_index < len(group):
                    ordered_candidates.append(group[round_index])
            for group in cumulative_groups:
                if round_index < len(group):
                    ordered_candidates.append(group[round_index])
        return ordered_candidates

    def _extract_microtopics(self, entry: LearningPlanEntry):
        topic_node = TopicNode(
            title=entry.topic_title,
            level=2,
            content=entry.topic_content or entry.topic_title,
            children=[],
        )
        extracted = MicroTopicExtractor().extract(topic_node)
        return extracted or MicroTopicExtractor().extract(
            TopicNode(title=entry.topic_title, level=2, content=entry.topic_title, children=[])
        )

    def _normalize_microtopic_performance(self, raw_performance: dict[str, object] | None) -> dict[str, object]:
        normalized = {
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
            return normalized
        normalized.update(raw_performance)
        distribution = dict(normalized["error_distribution"])
        distribution.update(raw_performance.get("error_distribution", {}) or {})
        normalized["error_distribution"] = distribution
        return normalized

    def _normalize_pedagogical_memory(self, raw_memory: dict[str, object] | None) -> dict[str, object]:
        normalized = {
            "last_pedagogical_mode": None,
            "recent_effectiveness": "neutral",
            "consecutive_successes": 0,
            "consecutive_failures": 0,
            "last_intervention_at": None,
            "stabilization_level": 0.0,
            "escalation_level": 0.0,
            "retrieval_success_trend": 0.5,
        }
        if not raw_memory:
            return normalized
        normalized.update(raw_memory)
        normalized["stabilization_level"] = min(
            max(float(normalized.get("stabilization_level", 0.0) or 0.0), 0.0),
            1.0,
        )
        normalized["escalation_level"] = min(
            max(float(normalized.get("escalation_level", 0.0) or 0.0), 0.0),
            1.0,
        )
        normalized["retrieval_success_trend"] = min(
            max(float(normalized.get("retrieval_success_trend", 0.5) or 0.5), 0.0),
            1.0,
        )
        return normalized

    def _resurfacing_signal(self, last_reviewed_at: object) -> float:
        if not last_reviewed_at:
            return 0.45
        parsed = self._parse_datetime(last_reviewed_at)
        if parsed is None:
            return 0.25
        elapsed_days = max((datetime.now(timezone.utc) - parsed).total_seconds() / 86400, 0.0)
        return min(elapsed_days / 21.0, 1.0)

    def _curriculum_signal(self, curriculum_role: str, review_intensity: str) -> float:
        base = 0.65 if curriculum_role == "active" else 0.35
        bonus = {
            "deep": 0.20,
            "medium": 0.12,
            "light": 0.04,
        }.get(review_intensity, 0.04)
        return min(base + bonus, 1.0)

    def _temporal_signal(
        self,
        *,
        resurfacing_signal: float,
        pedagogical_memory: dict[str, object],
    ) -> float:
        memory_resurfacing = self._resurfacing_signal(pedagogical_memory.get("last_intervention_at"))
        retrieval_decay = max(
            0.0,
            0.55 - float(pedagogical_memory.get("retrieval_success_trend", 0.5) or 0.5),
        )
        escalation = float(pedagogical_memory.get("escalation_level", 0.0) or 0.0)
        stabilization = float(pedagogical_memory.get("stabilization_level", 0.0) or 0.0)
        return min(
            max(
                max(resurfacing_signal, memory_resurfacing) * 0.10
                + retrieval_decay * 0.08
                + escalation * 0.08
                - stabilization * 0.04,
                0.0,
            ),
            0.18,
        )

    def _stabilization_discount(self, performance: dict[str, object]) -> float:
        consecutive_correct = int(performance.get("consecutive_correct", 0) or 0)
        return min(consecutive_correct * 0.04, 0.18)

    def _exposure_discount(self, performance: dict[str, object]) -> float:
        total_questions = int(performance.get("total_questions", 0) or 0)
        last_reviewed_at = performance.get("last_reviewed_at")
        if total_questions == 0:
            return 0.0
        recent_penalty = 0.05 if self._resurfacing_signal(last_reviewed_at) < 0.1 else 0.0
        return min(total_questions * 0.01, 0.08) + recent_penalty

    def _selection_reason(
        self,
        *,
        weakness_signal: float,
        resurfacing_signal: float,
        curriculum_role: str,
        temporal_signal: float,
    ) -> str:
        if weakness_signal >= 0.55:
            return "weakness_reinforcement"
        if resurfacing_signal >= 0.5:
            return "cumulative_resurfacing"
        if temporal_signal >= 0.10:
            return "temporal_resurfacing"
        if curriculum_role == "active":
            return "active_progression"
        return "light_cumulative_recall"

    def _parse_datetime(self, raw_value: object) -> datetime | None:
        if isinstance(raw_value, datetime):
            return raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)
        if not isinstance(raw_value, str):
            return None
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
