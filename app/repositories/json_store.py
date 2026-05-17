from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import (
    AnswerSubmission,
    Document,
    ErrorType,
    ItemState,
    InterventionHistory,
    MicroTopicPerformance,
    PedagogicalMemory,
    PedagogicalOutcome,
    ProgressState,
    TopicLearningState,
    UploadedMaterial,
    User,
    utc_now,
)


class UserScopedStudyRepository:
    def __init__(self, repository: JsonStudyRepository, user_id: str | None):
        self._repository = repository
        self.user_id = user_id

    def save_document(self, document: Document) -> None:
        self._repository.save_document(document, user_id=self.user_id)

    def list_documents(self) -> list[Document]:
        return self._repository.list_documents(user_id=self.user_id)

    def get_document(self, document_id: str) -> Document | None:
        return self._repository.get_document(document_id, user_id=self.user_id)

    def register_answer(
        self,
        *,
        topic_id: str,
        question_id: str,
        microtopic_id: str | None = None,
        pedagogical_mode: str | None = None,
        is_correct: bool,
        error_type: str | ErrorType | None = None,
    ) -> None:
        self._repository.register_answer(
            topic_id=topic_id,
            question_id=question_id,
            microtopic_id=microtopic_id,
            pedagogical_mode=pedagogical_mode,
            is_correct=is_correct,
            error_type=error_type,
            user_id=self.user_id,
        )

    def record_answer(self, submission: AnswerSubmission) -> None:
        self._repository.record_answer(submission, user_id=self.user_id)

    def load_progress(self) -> ProgressState:
        return self._repository.load_progress(user_id=self.user_id)


class JsonStudyRepository:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._default_payload())

    def _default_payload(self) -> dict[str, object]:
        return {
            "documents": [],
            "answers": [],
            "progress": self._default_progress_payload(),
            "users": [],
            "user_data": {},
        }

    def _default_progress_payload(self) -> dict[str, object]:
        return {
            "total_errors": 0,
            "weak_topics": {},
            "error_buckets": {},
            "topic_learning_states": {},
            "item_states": {},
            "microtopic_performance": {},
            "pedagogical_memory": {},
        }

    def _default_user_payload(self) -> dict[str, object]:
        return {
            "documents": [],
            "answers": [],
            "progress": self._default_progress_payload(),
            "materials": [],
        }

    def _read(self) -> dict[str, object]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return self._normalize_storage_payload(payload)

    def _write(self, payload: dict[str, object]) -> None:
        self.path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _normalize_storage_payload(self, payload: dict[str, object] | None) -> dict[str, object]:
        normalized = self._default_payload()
        if isinstance(payload, dict):
            normalized.update(payload)
        normalized["documents"] = list(normalized.get("documents", []) or [])
        normalized["answers"] = list(normalized.get("answers", []) or [])
        normalized["users"] = list(normalized.get("users", []) or [])
        normalized["progress"] = self._normalize_progress_payload(normalized.get("progress"))
        user_data = normalized.get("user_data")
        if not isinstance(user_data, dict):
            user_data = {}
        normalized_user_data: dict[str, dict[str, object]] = {}
        for user_id, state in user_data.items():
            if not isinstance(state, dict):
                state = {}
            user_state = self._default_user_payload()
            user_state.update(state)
            user_state["documents"] = list(user_state.get("documents", []) or [])
            user_state["answers"] = list(user_state.get("answers", []) or [])
            user_state["materials"] = list(user_state.get("materials", []) or [])
            user_state["progress"] = self._normalize_progress_payload(user_state.get("progress"))
            normalized_user_data[str(user_id)] = user_state
        normalized["user_data"] = normalized_user_data
        return normalized

    def _normalize_progress_payload(self, payload: object) -> dict[str, object]:
        normalized = self._default_progress_payload()
        if isinstance(payload, dict):
            normalized.update(payload)
        return normalized

    def _progress_container(self, payload: dict[str, object], user_id: str | None) -> dict[str, object]:
        if user_id is None:
            progress = payload.get("progress")
            if not isinstance(progress, dict):
                progress = self._default_progress_payload()
                payload["progress"] = progress
            return progress
        user_state = self._ensure_user_state(payload, user_id)
        progress = user_state.get("progress")
        if not isinstance(progress, dict):
            progress = self._default_progress_payload()
            user_state["progress"] = progress
        return progress

    def _documents_container(self, payload: dict[str, object], user_id: str | None) -> list[dict[str, object]]:
        if user_id is None:
            documents = payload.get("documents")
            if not isinstance(documents, list):
                documents = []
                payload["documents"] = documents
            return documents
        user_state = self._ensure_user_state(payload, user_id)
        documents = user_state.get("documents")
        if not isinstance(documents, list):
            documents = []
            user_state["documents"] = documents
        return documents

    def _answers_container(self, payload: dict[str, object], user_id: str | None) -> list[dict[str, object]]:
        if user_id is None:
            answers = payload.get("answers")
            if not isinstance(answers, list):
                answers = []
                payload["answers"] = answers
            return answers
        user_state = self._ensure_user_state(payload, user_id)
        answers = user_state.get("answers")
        if not isinstance(answers, list):
            answers = []
            user_state["answers"] = answers
        return answers

    def _materials_container(self, payload: dict[str, object], user_id: str) -> list[dict[str, object]]:
        user_state = self._ensure_user_state(payload, user_id)
        materials = user_state.get("materials")
        if not isinstance(materials, list):
            materials = []
            user_state["materials"] = materials
        return materials

    def _ensure_user_state(self, payload: dict[str, object], user_id: str) -> dict[str, object]:
        user_data = payload.setdefault("user_data", {})
        if not isinstance(user_data, dict):
            user_data = {}
            payload["user_data"] = user_data
        state = user_data.get(user_id)
        if not isinstance(state, dict):
            state = self._default_user_payload()
            user_data[user_id] = state
        if "progress" not in state or not isinstance(state.get("progress"), dict):
            state["progress"] = self._default_progress_payload()
        if "documents" not in state or not isinstance(state.get("documents"), list):
            state["documents"] = []
        if "answers" not in state or not isinstance(state.get("answers"), list):
            state["answers"] = []
        if "materials" not in state or not isinstance(state.get("materials"), list):
            state["materials"] = []
        return state

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

    def _normalize_intervention_history(self, mode: str, state: dict | None = None) -> dict:
        normalized = InterventionHistory(pedagogical_mode=mode).model_dump(mode="json")
        if state:
            normalized.update(state)
        normalized["confidence"] = self._clamp(normalized.get("confidence", 0.5), 0.0, 1.0)
        return normalized

    def _normalize_pedagogical_memory(
        self,
        microtopic_id: str,
        topic_id: str | None,
        state: dict | None = None,
    ) -> dict:
        normalized = PedagogicalMemory(
            microtopic_id=microtopic_id,
            topic_id=topic_id,
        ).model_dump(mode="json")
        if state:
            normalized.update(state)
        normalized["microtopic_id"] = microtopic_id
        normalized["topic_id"] = topic_id or normalized.get("topic_id")
        histories = {}
        for mode, history in (normalized.get("intervention_history", {}) or {}).items():
            histories[mode] = self._normalize_intervention_history(mode, history)
        normalized["intervention_history"] = histories
        normalized["stabilization_level"] = self._clamp(
            normalized.get("stabilization_level", 0.0), 0.0, 1.0
        )
        normalized["escalation_level"] = self._clamp(
            normalized.get("escalation_level", 0.0), 0.0, 1.0
        )
        normalized["retrieval_success_trend"] = self._clamp(
            normalized.get("retrieval_success_trend", 0.5), 0.0, 1.0
        )
        normalized["resurfacing_cycles"] = int(normalized.get("resurfacing_cycles", 0) or 0)
        normalized["successful_resurfacing_cycles"] = int(
            normalized.get("successful_resurfacing_cycles", 0) or 0
        )
        normalized["fatigue_exposure"] = self._clamp(
            normalized.get("fatigue_exposure", 0.0), 0.0, 1.0
        )
        normalized["recovery_count"] = int(normalized.get("recovery_count", 0) or 0)
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

    def for_user(self, user_id: str | None) -> UserScopedStudyRepository:
        return UserScopedStudyRepository(self, user_id)

    def create_user(self, user: User) -> User:
        payload = self._read()
        users = payload.setdefault("users", [])
        for existing in users:
            if existing.get("username", "").lower() == user.username.lower():
                raise ValueError("User already exists.")
            email = existing.get("email")
            if user.email and email and str(email).lower() == user.email.lower():
                raise ValueError("User already exists.")
        users.append(user.model_dump(mode="json"))
        users.sort(key=lambda item: item.get("created_at", ""))
        self._ensure_user_state(payload, user.user_id)
        self._write(payload)
        return user

    def get_user(self, user_id: str) -> User | None:
        payload = self._read()
        for item in payload.get("users", []):
            if item.get("user_id") == user_id:
                return User.model_validate(item)
        return None

    def get_user_by_username(self, username: str) -> User | None:
        payload = self._read()
        lookup = username.lower()
        for item in payload.get("users", []):
            if str(item.get("username", "")).lower() == lookup:
                return User.model_validate(item)
        return None

    def update_user(self, user: User) -> User:
        payload = self._read()
        users = [item for item in payload.get("users", []) if item.get("user_id") != user.user_id]
        users.append(user.model_dump(mode="json"))
        users.sort(key=lambda item: item.get("created_at", ""))
        payload["users"] = users
        self._write(payload)
        return user

    def save_uploaded_material(self, material: UploadedMaterial, *, user_id: str) -> None:
        payload = self._read()
        materials = [item for item in self._materials_container(payload, user_id) if item.get("metadata", {}).get("document_id") != material.metadata.document_id]
        materials.append(material.model_dump(mode="json"))
        materials.sort(key=lambda item: item.get("metadata", {}).get("created_at", ""))
        self._ensure_user_state(payload, user_id)["materials"] = materials
        self._write(payload)

    def list_uploaded_materials(self, *, user_id: str) -> list[UploadedMaterial]:
        payload = self._read()
        return [
            UploadedMaterial.model_validate(item)
            for item in self._materials_container(payload, user_id)
        ]

    def save_document(self, document: Document, user_id: str | None = None) -> None:
        payload = self._read()
        documents = [
            item for item in self._documents_container(payload, user_id) if item["id"] != document.id
        ]
        documents.append(document.model_dump(mode="json"))
        documents.sort(key=lambda item: item["created_at"])
        if user_id is None:
            payload["documents"] = documents
        else:
            self._ensure_user_state(payload, user_id)["documents"] = documents
        self._write(payload)

    def list_documents(self, user_id: str | None = None) -> list[Document]:
        payload = self._read()
        return [Document.model_validate(item) for item in self._documents_container(payload, user_id)]

    def get_document(self, document_id: str, user_id: str | None = None) -> Document | None:
        for document in self.list_documents(user_id=user_id):
            if document.id == document_id:
                return document
        return None

    def _resolve_document_id(
        self,
        payload: dict[str, object],
        *,
        question_id: str,
        topic_id: str,
        user_id: str | None,
    ) -> str:
        documents = self._documents_container(payload, user_id)
        for document in documents:
            if any(question.get("id") == question_id for question in document.get("questions", [])):
                return document.get("id", "")
        for document in documents:
            if any(topic.get("id") == topic_id for topic in document.get("topics", [])):
                return document.get("id", "")
        return ""

    def register_answer(
        self,
        *,
        topic_id: str,
        question_id: str,
        microtopic_id: str | None = None,
        pedagogical_mode: str | None = None,
        is_correct: bool,
        error_type: str | ErrorType | None = None,
        user_id: str | None = None,
    ) -> None:
        payload = self._read()
        document_id = self._resolve_document_id(
            payload,
            question_id=question_id,
            topic_id=topic_id,
            user_id=user_id,
        )
        self.record_answer(
            AnswerSubmission(
                question_id=question_id,
                document_id=document_id,
                topic_id=topic_id,
                microtopic_id=microtopic_id,
                pedagogical_mode=pedagogical_mode,
                selected_answer="true" if is_correct else "false",
                is_correct=is_correct,
                error_type=error_type,
                created_at=utc_now(),
            ),
            user_id=user_id,
        )

    def record_answer(self, submission: AnswerSubmission, user_id: str | None = None) -> None:
        payload = self._read()
        self._answers_container(payload, user_id).append(submission.model_dump(mode="json"))
        progress = self._progress_container(payload, user_id)
        topic_states = progress.setdefault("topic_learning_states", {})
        item_states = progress.setdefault("item_states", {})
        microtopic_states = progress.setdefault("microtopic_performance", {})
        pedagogical_memories = progress.setdefault("pedagogical_memory", {})
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
        pedagogical_memory = None
        if submission.microtopic_id:
            pedagogical_memory = self._normalize_pedagogical_memory(
                submission.microtopic_id,
                submission.topic_id,
                pedagogical_memories.get(submission.microtopic_id),
            )

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
            progress["total_errors"] = int(progress.get("total_errors", 0) or 0) + 1
            weak_topics = progress.setdefault("weak_topics", {})
            weak_topics[submission.topic_id] = weak_topics.get(submission.topic_id, 0) + 1
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
                error_buckets = progress.setdefault("error_buckets", {})
                error_buckets[bucket_key] = error_buckets.get(bucket_key, 0) + 1
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
        if (
            submission.microtopic_id
            and submission.pedagogical_mode
            and pedagogical_memory is not None
        ):
            self._update_pedagogical_memory(
                pedagogical_memory=pedagogical_memory,
                pedagogical_mode=submission.pedagogical_mode,
                is_correct=submission.is_correct,
                created_at=submission.created_at.isoformat(),
            )
            pedagogical_memories[submission.microtopic_id] = pedagogical_memory
        self._write(payload)

    def load_progress(self, user_id: str | None = None) -> ProgressState:
        payload = self._progress_container(self._read(), user_id)
        bucket_map = {
            ErrorType(key): value for key, value in payload.get("error_buckets", {}).items()
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
        pedagogical_memory = {
            microtopic_id: PedagogicalMemory.model_validate(
                self._normalize_pedagogical_memory(
                    microtopic_id,
                    (state or {}).get("topic_id"),
                    state,
                )
            )
            for microtopic_id, state in payload.get("pedagogical_memory", {}).items()
        }
        return ProgressState(
            total_errors=payload.get("total_errors", 0),
            weak_topics=payload.get("weak_topics", {}),
            error_buckets=bucket_map,
            topic_learning_states=topic_states,
            item_states=item_states,
            microtopic_performance=microtopic_performance,
            pedagogical_memory=pedagogical_memory,
        )

    def _update_pedagogical_memory(
        self,
        *,
        pedagogical_memory: dict,
        pedagogical_mode: str,
        is_correct: bool,
        created_at: str,
    ) -> None:
        previous_failures = int(pedagogical_memory.get("consecutive_failures", 0) or 0)
        history = self._normalize_intervention_history(
            pedagogical_mode,
            pedagogical_memory.get("intervention_history", {}).get(pedagogical_mode),
        )
        history["total_attempts"] += 1
        history["last_intervention_at"] = created_at
        if is_correct:
            history["successful_attempts"] += 1
            history["consecutive_successes"] += 1
            history["consecutive_failures"] = 0
        else:
            history["failed_attempts"] += 1
            history["consecutive_failures"] += 1
            history["consecutive_successes"] = 0
        history["last_outcome"] = (
            PedagogicalOutcome.EFFECTIVE.value
            if is_correct
            else PedagogicalOutcome.INEFFECTIVE.value
        )

        success_rate = history["successful_attempts"] / max(history["total_attempts"], 1)
        history["confidence"] = self._clamp(
            0.5
            + (success_rate - 0.5) * 0.6
            + min(history["consecutive_successes"] * 0.05, 0.2)
            - min(history["consecutive_failures"] * 0.08, 0.24),
            0.0,
            1.0,
        )

        pedagogical_memory["last_pedagogical_mode"] = pedagogical_mode
        pedagogical_memory["last_intervention_at"] = created_at
        pedagogical_memory["resurfacing_cycles"] = pedagogical_memory.get("resurfacing_cycles", 0) + 1
        pedagogical_memory["consecutive_successes"] = history["consecutive_successes"]
        pedagogical_memory["consecutive_failures"] = history["consecutive_failures"]
        pedagogical_memory["recent_effectiveness"] = self._derive_effectiveness(history)
        pedagogical_memory["retrieval_success_trend"] = self._clamp(success_rate, 0.0, 1.0)
        if is_correct:
            pedagogical_memory["successful_resurfacing_cycles"] = (
                pedagogical_memory.get("successful_resurfacing_cycles", 0) + 1
            )
        if is_correct and previous_failures >= 2:
            pedagogical_memory["recovery_count"] = pedagogical_memory.get("recovery_count", 0) + 1
        pedagogical_memory["stabilization_level"] = self._clamp(
            success_rate * 0.5
            + min(history["consecutive_successes"] * 0.1, 0.3)
            - min(history["consecutive_failures"] * 0.06, 0.18),
            0.0,
            1.0,
        )
        pedagogical_memory["escalation_level"] = self._clamp(
            (1.0 - success_rate) * 0.35
            + min(history["consecutive_failures"] * 0.15, 0.45)
            - min(history["consecutive_successes"] * 0.05, 0.15),
            0.0,
            1.0,
        )
        pedagogical_memory["fatigue_exposure"] = self._clamp(
            pedagogical_memory.get("fatigue_exposure", 0.0)
            + (
                0.08
                if history["consecutive_successes"] >= 2 and pedagogical_memory["last_pedagogical_mode"] == pedagogical_mode
                else -0.05
            ),
            0.0,
            1.0,
        )
        if pedagogical_memory["stabilization_level"] >= 0.7 and is_correct:
            pedagogical_memory["last_stabilized_at"] = created_at
        pedagogical_memory.setdefault("intervention_history", {})[pedagogical_mode] = history

    def _derive_effectiveness(self, history: dict) -> str:
        attempts = history.get("total_attempts", 0)
        success_rate = history.get("successful_attempts", 0) / max(attempts, 1)
        if history.get("consecutive_failures", 0) >= 2 or (attempts >= 3 and success_rate <= 0.35):
            return PedagogicalOutcome.INEFFECTIVE.value
        if history.get("consecutive_successes", 0) >= 2 or (attempts >= 3 and success_rate >= 0.65):
            return PedagogicalOutcome.EFFECTIVE.value
        return PedagogicalOutcome.NEUTRAL.value

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(float(value), maximum))
