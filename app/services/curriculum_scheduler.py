from __future__ import annotations

from datetime import datetime
from math import ceil

from app.domain.models import CurriculumPhase, CurriculumProgress, CurriculumWindow


class CurriculumScheduler:
    ACTIVE_WINDOW_SIZE = 3
    CUMULATIVE_LIGHT_REVIEW = True
    ACTIVE_DEEP_COUNT = 1
    ACTIVE_DEEP_BOOST = 0.14
    ACTIVE_MEDIUM_BOOST = 0.09
    CUMULATIVE_LIGHT_BOOST = 0.05
    CUMULATIVE_MEDIUM_BOOST = 0.1
    CUMULATIVE_DEEP_BOOST = 0.13

    def __init__(self, *, active_window_size: int | None = None):
        self.active_window_size = active_window_size or self.ACTIVE_WINDOW_SIZE

    def build_phase(self, topic_snapshots: list[dict]) -> CurriculumPhase:
        ordered = self._ordered_snapshots(topic_snapshots)
        active_ids = [snapshot["topic_id"] for snapshot in ordered[: self.active_window_size]]
        cumulative_ids = [snapshot["topic_id"] for snapshot in ordered[self.active_window_size :]]
        total_topics = len(ordered)
        phase_number = max(1, ceil(total_topics / max(self.active_window_size, 1))) if total_topics else 1
        return CurriculumPhase(
            phase_number=phase_number,
            active_window=CurriculumWindow(role="active", topic_ids=active_ids),
            cumulative_window=CurriculumWindow(role="cumulative", topic_ids=cumulative_ids),
        )

    def build_progress(self, topic_snapshots: list[dict]) -> CurriculumProgress:
        phase = self.build_phase(topic_snapshots)
        return CurriculumProgress(
            total_topics=len(topic_snapshots),
            active_window_size=self.active_window_size,
            active_topic_ids=phase.active_window.topic_ids,
            cumulative_topic_ids=phase.cumulative_window.topic_ids,
        )

    def schedule(self, topic_snapshots: list[dict]) -> dict[str, dict[str, object]]:
        phase = self.build_phase(topic_snapshots)
        ordered = self._ordered_snapshots(topic_snapshots)
        assignments: dict[str, dict[str, object]] = {}

        for recency_index, snapshot in enumerate(ordered):
            topic_id = snapshot["topic_id"]
            role = "active" if topic_id in phase.active_window.topic_ids else "cumulative"
            intensity = self._review_intensity(
                snapshot=snapshot,
                role=role,
                recency_index=recency_index,
            )
            adjustment = self._priority_adjustment(role=role, intensity=intensity)
            assignments[topic_id] = {
                "curriculum_role": role,
                "review_intensity": intensity,
                "priority_adjustment": adjustment,
                "phase_number": phase.phase_number,
                "recency_index": recency_index,
                "curriculum_reasoning": self._reasoning(role=role, intensity=intensity),
            }

        return assignments

    def _ordered_snapshots(self, topic_snapshots: list[dict]) -> list[dict]:
        return sorted(
            topic_snapshots,
            key=lambda snapshot: (
                -self._timestamp(snapshot.get("created_at")),
                str(snapshot.get("topic_id", "")),
            ),
        )

    def _review_intensity(
        self,
        *,
        snapshot: dict,
        role: str,
        recency_index: int,
    ) -> str:
        performance = dict(snapshot.get("performance_data", {}) or {})
        recent_errors = int(performance.get("recent_errors", 0) or 0)
        conceptual_errors = int(
            (performance.get("error_distribution", {}) or {}).get("conceptual", 0) or 0
        )
        weakness = recent_errors + conceptual_errors

        if role == "active":
            if recency_index < self.ACTIVE_DEEP_COUNT or weakness >= 2:
                return "deep"
            return "medium"

        if weakness >= 4:
            return "deep"
        if weakness >= 2:
            return "medium"
        return "light"

    def _priority_adjustment(self, *, role: str, intensity: str) -> float:
        if role == "active":
            return self.ACTIVE_DEEP_BOOST if intensity == "deep" else self.ACTIVE_MEDIUM_BOOST
        if intensity == "deep":
            return self.CUMULATIVE_DEEP_BOOST
        if intensity == "medium":
            return self.CUMULATIVE_MEDIUM_BOOST
        return self.CUMULATIVE_LIGHT_BOOST

    def _reasoning(self, *, role: str, intensity: str) -> list[str]:
        reasons = [f"Papel curricular definido como {role}."]
        if role == "active":
            reasons.append("Janela ativa recebe maior carga cognitiva e consolidacao progressiva.")
        else:
            reasons.append("Janela cumulativa mantem resurfacing amplo e retencao de longo prazo.")
        reasons.append(f"Intensidade de revisao definida como {intensity}.")
        return reasons

    def _timestamp(self, value: object) -> float:
        if isinstance(value, datetime):
            return value.timestamp()
        return 0.0
