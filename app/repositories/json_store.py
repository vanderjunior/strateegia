from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import (
    AnswerSubmission,
    Document,
    ErrorType,
    ItemState,
    MicroTopicPerformance,
    ProgressState,
    TopicLearningState,
    utc_now,
)


class JsonStudyRepository:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(
                {
                    "documents": [],
                    "answers": [],
                    "progress": {
                        "total_errors": 0,
                    "weak_topics": {},
                    "error_buckets": {},
                    "topic_learning_states": {},
                    "item_states": {},
                    "microtopic_performance": {},
                },
            }
        )

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict) -> None:
        self.path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _default_error_distribution(self) -> dict[str, int]:
        return {
            "conceptual": 0,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        }

    def _normalize_topic_state(self, topic_id: str, state: dict | None = None) -> dict:
        normalized = TopicLearningState(topic_id=topic_id).model_dump(mode="json")
        if state:
            normalized.update(state)
        distribution = dict(self._default_error_distribution())
        distribution.update(normalized.get("error_distribution", {}) or {})
        normalized["error_distribution"] = distribution
        return normalized

    def _normalize_microtopic_state(self, state: dict | None = None) -> dict:
        normalized = MicroTopicPerformance().model_dump(mode="json")
        if state:
            normalized.update(state)
        distribution = dict(self._default_error_distribution())
        distribution.update(normalized.get("error_distribution", {}) or {})
        normalized["error_distribution"] = distribution
        return normalized

    def _normalize_error_type(self, error_type: str | ErrorType | None) -> str | None:
        if error_type is None:
            return None
        raw = error_type.value if isinstance(error_type, ErrorType) else str(error_type)
        mapping = {
            "conceptual": "conceptual",
            ErrorType.CONCEPT_CONFUSION.value: "conceptual",
            ErrorType.KNOWLEDGE_GAP.value: "conceptual",
            "attention": "attention",
            ErrorType.DISTRACTION.value: "attention",
            "interpretation": "interpretation",
            ErrorType.INTERPRETATION.value: "interpretation",
            "memory": "memory",
            ErrorType.MEMORIZATION.value: "memory",
        }
        return mapping.get(raw)

    def _legacy_error_bucket_key(self, error_type: str | ErrorType | None) -> str | None:
        if error_type is None:
            return None
        raw = error_type.value if isinstance(error_type, ErrorType) else str(error_type)
        try:
            return ErrorType(raw).value
        except ValueError:
            return None

    def save_document(self, document: Document) -> None:
        payload = self._read()
        documents = [
            item for item in payload["documents"] if item["id"] != document.id
        ]
        documents.append(document.model_dump(mode="json"))
        documents.sort(key=lambda item: item["created_at"])
        payload["documents"] = documents
        self._write(payload)

    def list_documents(self) -> list[Document]:
        payload = self._read()
        return [Document.model_validate(item) for item in payload["documents"]]

    def get_document(self, document_id: str) -> Document | None:
        for document in self.list_documents():
            if document.id == document_id:
                return document
        return None

    def _resolve_document_id(self, payload: dict, *, question_id: str, topic_id: str) -> str:
        for document in payload.get("documents", []):
            if any(question.get("id") == question_id for question in document.get("questions", [])):
                return document.get("id", "")
        for document in payload.get("documents", []):
            if any(topic.get("id") == topic_id for topic in document.get("topics", [])):
                return document.get("id", "")
        return ""

    def register_answer(
        self,
        *,
        topic_id: str,
        question_id: str,
        microtopic_id: str | None = None,
        is_correct: bool,
        error_type: str | ErrorType | None = None,
    ) -> None:
        payload = self._read()
        document_id = self._resolve_document_id(
            payload,
            question_id=question_id,
            topic_id=topic_id,
        )
        self.record_answer(
            AnswerSubmission(
                question_id=question_id,
                document_id=document_id,
                topic_id=topic_id,
                microtopic_id=microtopic_id,
                selected_answer="true" if is_correct else "false",
                is_correct=is_correct,
                error_type=error_type,
                created_at=utc_now(),
            )
        )

    def record_answer(self, submission: AnswerSubmission) -> None:
        payload = self._read()
        payload["answers"].append(submission.model_dump(mode="json"))
        progress = payload["progress"]
        topic_states = progress.setdefault("topic_learning_states", {})
        item_states = progress.setdefault("item_states", {})
        microtopic_states = progress.setdefault("microtopic_performance", {})
        topic_state = self._normalize_topic_state(
            submission.topic_id, topic_states.get(submission.topic_id)
        )
        item_state = item_states.get(submission.question_id) or ItemState(
            question_id=submission.question_id,
            topic_id=submission.topic_id,
        ).model_dump(mode="json")
        microtopic_state = None
        if submission.microtopic_id:
            microtopic_state = self._normalize_microtopic_state(
                microtopic_states.get(submission.microtopic_id)
            )
            microtopic_state["topic_id"] = submission.topic_id

        topic_state["attempts"] += 1
        topic_state["total_questions"] = topic_state.get("total_questions", 0) + 1
        if not topic_state.get("first_seen_at"):
            topic_state["first_seen_at"] = submission.created_at.isoformat()
        topic_state["last_seen_at"] = submission.created_at.isoformat()
        item_state["seen_count"] += 1
        item_state["last_seen_at"] = submission.created_at.isoformat()
        if microtopic_state is not None:
            microtopic_state["total_questions"] = microtopic_state.get("total_questions", 0) + 1
            microtopic_state["last_seen_at"] = submission.created_at.isoformat()
            microtopic_state["last_reviewed_at"] = submission.created_at.isoformat()

        if not submission.is_correct:
            progress["total_errors"] += 1
            progress["weak_topics"][submission.topic_id] = (
                progress["weak_topics"].get(submission.topic_id, 0) + 1
            )
            topic_state["incorrect_attempts"] += 1
            topic_state["recent_errors"] = topic_state.get("recent_errors", 0) + 1
            normalized_error_type = self._normalize_error_type(submission.error_type)
            if normalized_error_type:
                distribution = topic_state.get("error_distribution") or self._default_error_distribution()
                distribution[normalized_error_type] = distribution.get(normalized_error_type, 0) + 1
                topic_state["error_distribution"] = distribution
            topic_state["streak_correct"] = 0
            topic_state["last_error_at"] = submission.created_at.isoformat()
            topic_state["last_error_type"] = (
                submission.error_type.value if isinstance(submission.error_type, ErrorType) else submission.error_type
            )
            topic_state["current_difficulty"] = max(
                1, topic_state.get("current_difficulty", 1) - 1
            )
            item_state["incorrect_count"] += 1
            item_state["last_result"] = "incorrect"
            item_state["last_error_type"] = (
                submission.error_type.value if isinstance(submission.error_type, ErrorType) else submission.error_type
            )
            if microtopic_state is not None:
                microtopic_state["recent_errors"] = microtopic_state.get("recent_errors", 0) + 1
                microtopic_state["last_incorrect_at"] = submission.created_at.isoformat()
                microtopic_state["consecutive_incorrect"] = (
                    microtopic_state.get("consecutive_incorrect", 0) + 1
                )
                microtopic_state["consecutive_correct"] = 0
                normalized_error_type = self._normalize_error_type(submission.error_type)
                if normalized_error_type:
                    distribution = microtopic_state.get("error_distribution") or self._default_error_distribution()
                    distribution[normalized_error_type] = distribution.get(normalized_error_type, 0) + 1
                    microtopic_state["error_distribution"] = distribution
            bucket_key = self._legacy_error_bucket_key(submission.error_type)
            if bucket_key:
                progress["error_buckets"][bucket_key] = (
                    progress["error_buckets"].get(bucket_key, 0) + 1
                )
        else:
            topic_state["correct_attempts"] += 1
            topic_state["correct_answers"] = topic_state.get("correct_answers", 0) + 1
            topic_state["recent_errors"] = max(0, topic_state.get("recent_errors", 0) - 1)
            topic_state["streak_correct"] += 1
            topic_state["last_correct_at"] = submission.created_at.isoformat()
            topic_state["current_difficulty"] = min(
                4,
                max(
                    topic_state.get("current_difficulty", 1),
                    1 + topic_state["streak_correct"] // 2,
                ),
            )
            item_state["correct_count"] += 1
            item_state["last_result"] = "correct"
            item_state["difficulty_level"] = min(
                4, 1 + item_state["correct_count"] // 2
            )
            if microtopic_state is not None:
                microtopic_state["correct_answers"] = microtopic_state.get("correct_answers", 0) + 1
                microtopic_state["recent_errors"] = max(
                    0, microtopic_state.get("recent_errors", 0) - 1
                )
                microtopic_state["last_correct_at"] = submission.created_at.isoformat()
                microtopic_state["consecutive_correct"] = (
                    microtopic_state.get("consecutive_correct", 0) + 1
                )
                microtopic_state["consecutive_incorrect"] = 0

        topic_states[submission.topic_id] = topic_state
        item_states[submission.question_id] = item_state
        if submission.microtopic_id and microtopic_state is not None:
            microtopic_states[submission.microtopic_id] = microtopic_state
        self._write(payload)

    def load_progress(self) -> ProgressState:
        payload = self._read()["progress"]
        bucket_map = {
            ErrorType(key): value for key, value in payload["error_buckets"].items()
        }
        topic_states = {
            topic_id: TopicLearningState.model_validate(
                self._normalize_topic_state(topic_id, state)
            )
            for topic_id, state in payload.get("topic_learning_states", {}).items()
        }
        item_states = {
            question_id: ItemState.model_validate(state)
            for question_id, state in payload.get("item_states", {}).items()
        }
        microtopic_performance = {
            microtopic_id: MicroTopicPerformance.model_validate(
                self._normalize_microtopic_state(state)
            )
            for microtopic_id, state in payload.get("microtopic_performance", {}).items()
        }
        return ProgressState(
            total_errors=payload["total_errors"],
            weak_topics=payload["weak_topics"],
            error_buckets=bucket_map,
            topic_learning_states=topic_states,
            item_states=item_states,
            microtopic_performance=microtopic_performance,
        )
