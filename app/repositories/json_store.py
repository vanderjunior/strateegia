from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import (
    AlignmentWarning,
    AnswerSubmission,
    BibliographyAlignmentResult,
    BibliographyAlignmentState,
    CoverageGap,
    CoverageRedundancy,
    CurriculumGraph,
    CurriculumGraphState,
    Document,
    DocumentChunk,
    DocumentExtractionResult,
    EditalExtractionResult,
    EditalIngestionEvent,
    EditalIngestionState,
    ErrorType,
    ItemState,
    InterventionHistory,
    MicroTopicPerformance,
    PedagogicalMemory,
    PedagogicalOutcome,
    ProgressState,
    QuestionDraftSet,
    QuestionGenerationBlueprintSet,
    SimuladoBlueprint,
    SimuladoBlueprintState,
    StudyCyclePlan,
    StudyCyclePlanState,
    DocumentPipelineEvent,
    DocumentPipelineState,
    DocumentSection,
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

    def get_uploaded_material(self, document_id: str) -> UploadedMaterial | None:
        return self._repository.get_uploaded_material(document_id, user_id=self.user_id)

    def save_uploaded_material(self, material: UploadedMaterial) -> None:
        if self.user_id is None:
            raise ValueError("User-scoped material persistence requires a user_id.")
        self._repository.save_uploaded_material(material, user_id=self.user_id)

    def save_document_pipeline_state(self, state: DocumentPipelineState) -> None:
        self._repository.save_document_pipeline_state(state, user_id=self.user_id)

    def get_document_pipeline_state(self, document_id: str) -> DocumentPipelineState | None:
        return self._repository.get_document_pipeline_state(document_id, user_id=self.user_id)

    def save_document_extraction_result(self, result: DocumentExtractionResult) -> None:
        self._repository.save_document_extraction_result(result, user_id=self.user_id)

    def get_document_extraction_result(self, document_id: str) -> DocumentExtractionResult | None:
        return self._repository.get_document_extraction_result(document_id, user_id=self.user_id)

    def save_document_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        self._repository.save_document_chunks(document_id, chunks, user_id=self.user_id)

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        return self._repository.list_document_chunks(document_id, user_id=self.user_id)

    def save_document_sections(self, document_id: str, sections: list[DocumentSection]) -> None:
        self._repository.save_document_sections(document_id, sections, user_id=self.user_id)

    def list_document_sections(self, document_id: str) -> list[DocumentSection]:
        return self._repository.list_document_sections(document_id, user_id=self.user_id)

    def append_document_pipeline_event(self, event: DocumentPipelineEvent) -> None:
        self._repository.append_document_pipeline_event(event, user_id=self.user_id)

    def list_document_pipeline_events(self, document_id: str) -> list[DocumentPipelineEvent]:
        return self._repository.list_document_pipeline_events(document_id, user_id=self.user_id)

    def save_edital_ingestion_state(self, state: EditalIngestionState) -> None:
        self._repository.save_edital_ingestion_state(state, user_id=self.user_id)

    def get_edital_ingestion_state(self, document_id: str) -> EditalIngestionState | None:
        return self._repository.get_edital_ingestion_state(document_id, user_id=self.user_id)

    def save_edital_extraction_result(self, result: EditalExtractionResult) -> None:
        self._repository.save_edital_extraction_result(result, user_id=self.user_id)

    def get_edital_extraction_result(self, document_id: str) -> EditalExtractionResult | None:
        return self._repository.get_edital_extraction_result(document_id, user_id=self.user_id)

    def list_user_edital_extractions(self) -> list[EditalExtractionResult]:
        return self._repository.list_user_edital_extractions(user_id=self.user_id)

    def get_edital_extraction_by_id(self, edital_id: str) -> EditalExtractionResult | None:
        return self._repository.get_edital_extraction_by_id(edital_id, user_id=self.user_id)

    def append_edital_ingestion_event(self, event: EditalIngestionEvent) -> None:
        self._repository.append_edital_ingestion_event(event, user_id=self.user_id)

    def list_edital_ingestion_events(self, document_id: str) -> list[EditalIngestionEvent]:
        return self._repository.list_edital_ingestion_events(document_id, user_id=self.user_id)

    def save_bibliography_alignment_state(self, state: BibliographyAlignmentState) -> None:
        self._repository.save_bibliography_alignment_state(state, user_id=self.user_id)

    def get_bibliography_alignment_state(self, edital_id: str) -> BibliographyAlignmentState | None:
        return self._repository.get_bibliography_alignment_state(edital_id, user_id=self.user_id)

    def save_bibliography_alignment_result(self, result: BibliographyAlignmentResult) -> None:
        self._repository.save_bibliography_alignment_result(result, user_id=self.user_id)

    def get_bibliography_alignment_result(self, edital_id: str) -> BibliographyAlignmentResult | None:
        return self._repository.get_bibliography_alignment_result(edital_id, user_id=self.user_id)

    def list_user_bibliography_alignments(self) -> list[BibliographyAlignmentResult]:
        return self._repository.list_user_bibliography_alignments(user_id=self.user_id)

    def get_bibliography_alignment_by_id(self, alignment_id: str) -> BibliographyAlignmentResult | None:
        return self._repository.get_bibliography_alignment_by_id(alignment_id, user_id=self.user_id)

    def save_curriculum_graph_state(self, state: CurriculumGraphState) -> None:
        self._repository.save_curriculum_graph_state(state, user_id=self.user_id)

    def get_curriculum_graph_state(self, edital_id: str) -> CurriculumGraphState | None:
        return self._repository.get_curriculum_graph_state(edital_id, user_id=self.user_id)

    def save_curriculum_graph(self, graph: CurriculumGraph) -> None:
        self._repository.save_curriculum_graph(graph, user_id=self.user_id)

    def get_curriculum_graph(self, edital_id: str) -> CurriculumGraph | None:
        return self._repository.get_curriculum_graph(edital_id, user_id=self.user_id)

    def list_user_curriculum_graphs(self) -> list[CurriculumGraph]:
        return self._repository.list_user_curriculum_graphs(user_id=self.user_id)

    def get_curriculum_graph_by_id(self, graph_id: str) -> CurriculumGraph | None:
        return self._repository.get_curriculum_graph_by_id(graph_id, user_id=self.user_id)

    def save_study_cycle_plan_state(self, state: StudyCyclePlanState) -> None:
        self._repository.save_study_cycle_plan_state(state, user_id=self.user_id)

    def get_study_cycle_plan_state(self, graph_id: str) -> StudyCyclePlanState | None:
        return self._repository.get_study_cycle_plan_state(graph_id, user_id=self.user_id)

    def save_study_cycle_plan(self, plan: StudyCyclePlan) -> None:
        self._repository.save_study_cycle_plan(plan, user_id=self.user_id)

    def get_study_cycle_plan(self, graph_id: str) -> StudyCyclePlan | None:
        return self._repository.get_study_cycle_plan(graph_id, user_id=self.user_id)

    def list_user_study_cycle_plans(self) -> list[StudyCyclePlan]:
        return self._repository.list_user_study_cycle_plans(user_id=self.user_id)

    def get_study_cycle_plan_by_id(self, cycle_id: str) -> StudyCyclePlan | None:
        return self._repository.get_study_cycle_plan_by_id(cycle_id, user_id=self.user_id)

    def save_simulado_blueprint_state(self, state: SimuladoBlueprintState) -> None:
        self._repository.save_simulado_blueprint_state(state, user_id=self.user_id)

    def get_simulado_blueprint_state(self, cycle_id: str) -> SimuladoBlueprintState | None:
        return self._repository.get_simulado_blueprint_state(cycle_id, user_id=self.user_id)

    def save_simulado_blueprint(self, blueprint: SimuladoBlueprint) -> None:
        self._repository.save_simulado_blueprint(blueprint, user_id=self.user_id)

    def get_simulado_blueprint(self, cycle_id: str) -> SimuladoBlueprint | None:
        return self._repository.get_simulado_blueprint(cycle_id, user_id=self.user_id)

    def list_user_simulado_blueprints(self) -> list[SimuladoBlueprint]:
        return self._repository.list_user_simulado_blueprints(user_id=self.user_id)

    def get_simulado_blueprint_by_id(self, blueprint_id: str) -> SimuladoBlueprint | None:
        return self._repository.get_simulado_blueprint_by_id(blueprint_id, user_id=self.user_id)

    def save_question_generation_blueprint(self, blueprint_set: QuestionGenerationBlueprintSet) -> None:
        self._repository.save_question_generation_blueprint(blueprint_set, user_id=self.user_id)

    def get_question_generation_blueprint(self, source_simulado_blueprint_id: str) -> QuestionGenerationBlueprintSet | None:
        return self._repository.get_question_generation_blueprint(source_simulado_blueprint_id, user_id=self.user_id)

    def list_user_question_generation_blueprints(self) -> list[QuestionGenerationBlueprintSet]:
        return self._repository.list_user_question_generation_blueprints(user_id=self.user_id)

    def get_question_generation_blueprint_by_id(self, blueprint_set_id: str) -> QuestionGenerationBlueprintSet | None:
        return self._repository.get_question_generation_blueprint_by_id(blueprint_set_id, user_id=self.user_id)

    def save_question_draft_set(self, draft_set: QuestionDraftSet) -> None:
        self._repository.save_question_draft_set(draft_set, user_id=self.user_id)

    def get_question_draft_set(self, source_question_generation_blueprint_set_id: str) -> QuestionDraftSet | None:
        return self._repository.get_question_draft_set(
            source_question_generation_blueprint_set_id,
            user_id=self.user_id,
        )

    def list_user_question_draft_sets(self) -> list[QuestionDraftSet]:
        return self._repository.list_user_question_draft_sets(user_id=self.user_id)

    def get_question_draft_set_by_id(self, draft_set_id: str) -> QuestionDraftSet | None:
        return self._repository.get_question_draft_set_by_id(draft_set_id, user_id=self.user_id)


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
            "document_pipeline": {
                "states": {},
                "extraction_results": {},
                "chunks": {},
                "sections": {},
                "events": {},
            },
            "edital_ingestion": {
                "states": {},
                "results": {},
                "events": {},
            },
            "bibliography_alignment": {
                "states": {},
                "results": {},
            },
            "curriculum_graph": {
                "states": {},
                "results": {},
            },
            "study_cycle": {
                "states": {},
                "results": {},
            },
            "simulado_blueprint": {
                "states": {},
                "results": {},
            },
            "question_generation_blueprint": {
                "results": {},
            },
            "question_draft": {
                "results": {},
            },
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
            user_state["document_pipeline"] = self._normalize_document_pipeline_payload(
                user_state.get("document_pipeline")
            )
            user_state["edital_ingestion"] = self._normalize_edital_ingestion_payload(
                user_state.get("edital_ingestion")
            )
            user_state["bibliography_alignment"] = self._normalize_bibliography_alignment_payload(
                user_state.get("bibliography_alignment")
            )
            user_state["curriculum_graph"] = self._normalize_curriculum_graph_payload(
                user_state.get("curriculum_graph")
            )
            user_state["study_cycle"] = self._normalize_study_cycle_payload(
                user_state.get("study_cycle")
            )
            user_state["simulado_blueprint"] = self._normalize_simulado_blueprint_payload(
                user_state.get("simulado_blueprint")
            )
            user_state["question_generation_blueprint"] = self._normalize_question_generation_blueprint_payload(
                user_state.get("question_generation_blueprint")
            )
            user_state["question_draft"] = self._normalize_question_draft_payload(
                user_state.get("question_draft")
            )
            normalized_user_data[str(user_id)] = user_state
        normalized["user_data"] = normalized_user_data
        return normalized

    def _normalize_progress_payload(self, payload: object) -> dict[str, object]:
        normalized = self._default_progress_payload()
        if isinstance(payload, dict):
            normalized.update(payload)
        return normalized

    def _normalize_document_pipeline_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "extraction_results": {},
            "chunks": {},
            "sections": {},
            "events": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "extraction_results", "chunks", "sections", "events"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_edital_ingestion_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "results": {},
            "events": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "results", "events"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_bibliography_alignment_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "results"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_curriculum_graph_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "results"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_study_cycle_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "results"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_simulado_blueprint_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "states": {},
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        for key in ("states", "results"):
            if not isinstance(normalized.get(key), dict):
                normalized[key] = {}
        return normalized

    def _normalize_question_generation_blueprint_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        if not isinstance(normalized.get("results"), dict):
            normalized["results"] = {}
        return normalized

    def _normalize_question_draft_payload(self, payload: object) -> dict[str, object]:
        normalized = {
            "results": {},
        }
        if isinstance(payload, dict):
            normalized.update(payload)
        if not isinstance(normalized.get("results"), dict):
            normalized["results"] = {}
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
        state["document_pipeline"] = self._normalize_document_pipeline_payload(
            state.get("document_pipeline")
        )
        state["edital_ingestion"] = self._normalize_edital_ingestion_payload(
            state.get("edital_ingestion")
        )
        state["bibliography_alignment"] = self._normalize_bibliography_alignment_payload(
            state.get("bibliography_alignment")
        )
        state["curriculum_graph"] = self._normalize_curriculum_graph_payload(
            state.get("curriculum_graph")
        )
        state["study_cycle"] = self._normalize_study_cycle_payload(
            state.get("study_cycle")
        )
        state["simulado_blueprint"] = self._normalize_simulado_blueprint_payload(
            state.get("simulado_blueprint")
        )
        state["question_generation_blueprint"] = self._normalize_question_generation_blueprint_payload(
            state.get("question_generation_blueprint")
        )
        state["question_draft"] = self._normalize_question_draft_payload(
            state.get("question_draft")
        )
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

    def get_uploaded_material(self, document_id: str, *, user_id: str | None) -> UploadedMaterial | None:
        if user_id is None:
            return None
        for material in self.list_uploaded_materials(user_id=user_id):
            if material.metadata.document_id == document_id:
                return material
        return None

    def _pipeline_container(self, payload: dict[str, object], user_id: str | None) -> dict[str, object]:
        if user_id is None:
            return self._normalize_document_pipeline_payload({})
        return self._ensure_user_state(payload, user_id)["document_pipeline"]

    def _edital_container(self, payload: dict[str, object], user_id: str | None) -> dict[str, object]:
        if user_id is None:
            return self._normalize_edital_ingestion_payload({})
        return self._ensure_user_state(payload, user_id)["edital_ingestion"]

    def _bibliography_alignment_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_bibliography_alignment_payload({})
        return self._ensure_user_state(payload, user_id)["bibliography_alignment"]

    def _curriculum_graph_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_curriculum_graph_payload({})
        return self._ensure_user_state(payload, user_id)["curriculum_graph"]

    def _study_cycle_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_study_cycle_payload({})
        return self._ensure_user_state(payload, user_id)["study_cycle"]

    def _simulado_blueprint_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_simulado_blueprint_payload({})
        return self._ensure_user_state(payload, user_id)["simulado_blueprint"]

    def _question_generation_blueprint_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_question_generation_blueprint_payload({})
        return self._ensure_user_state(payload, user_id)["question_generation_blueprint"]

    def _question_draft_container(
        self,
        payload: dict[str, object],
        user_id: str | None,
    ) -> dict[str, object]:
        if user_id is None:
            return self._normalize_question_draft_payload({})
        return self._ensure_user_state(payload, user_id)["question_draft"]

    def save_document_pipeline_state(
        self,
        state: DocumentPipelineState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Document pipeline state requires user ownership.")
        payload = self._read()
        container = self._pipeline_container(payload, user_id)
        container["states"][state.document_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_document_pipeline_state(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> DocumentPipelineState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._pipeline_container(payload, user_id)["states"].get(document_id)
        if raw is None:
            return None
        return DocumentPipelineState.model_validate(raw)

    def save_document_extraction_result(
        self,
        result: DocumentExtractionResult,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Document extraction results require user ownership.")
        payload = self._read()
        container = self._pipeline_container(payload, user_id)
        container["extraction_results"][result.document_id] = result.model_dump(mode="json")
        self._write(payload)

    def get_document_extraction_result(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> DocumentExtractionResult | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._pipeline_container(payload, user_id)["extraction_results"].get(document_id)
        if raw is None:
            return None
        return DocumentExtractionResult.model_validate(raw)

    def save_document_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Document chunks require user ownership.")
        payload = self._read()
        container = self._pipeline_container(payload, user_id)
        container["chunks"][document_id] = [item.model_dump(mode="json") for item in chunks]
        self._write(payload)

    def list_document_chunks(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> list[DocumentChunk]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._pipeline_container(payload, user_id)["chunks"].get(document_id, [])
        return [DocumentChunk.model_validate(item) for item in raw]

    def save_document_sections(
        self,
        document_id: str,
        sections: list[DocumentSection],
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Document sections require user ownership.")
        payload = self._read()
        container = self._pipeline_container(payload, user_id)
        container["sections"][document_id] = [item.model_dump(mode="json") for item in sections]
        self._write(payload)

    def list_document_sections(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> list[DocumentSection]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._pipeline_container(payload, user_id)["sections"].get(document_id, [])
        return [DocumentSection.model_validate(item) for item in raw]

    def append_document_pipeline_event(
        self,
        event: DocumentPipelineEvent,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Document pipeline events require user ownership.")
        payload = self._read()
        container = self._pipeline_container(payload, user_id)
        existing = container["events"].get(event.document_id, [])
        filtered = [item for item in existing if item.get("event_id") != event.event_id]
        filtered.append(event.model_dump(mode="json"))
        filtered.sort(key=lambda item: item.get("created_at", ""))
        container["events"][event.document_id] = filtered
        self._write(payload)

    def list_document_pipeline_events(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> list[DocumentPipelineEvent]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._pipeline_container(payload, user_id)["events"].get(document_id, [])
        return [DocumentPipelineEvent.model_validate(item) for item in raw]

    def save_edital_ingestion_state(
        self,
        state: EditalIngestionState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Edital ingestion state requires user ownership.")
        payload = self._read()
        container = self._edital_container(payload, user_id)
        container["states"][state.document_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_edital_ingestion_state(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> EditalIngestionState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._edital_container(payload, user_id)["states"].get(document_id)
        if raw is None:
            return None
        return EditalIngestionState.model_validate(raw)

    def save_edital_extraction_result(
        self,
        result: EditalExtractionResult,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Edital extraction results require user ownership.")
        payload = self._read()
        container = self._edital_container(payload, user_id)
        container["results"][result.document_id] = result.model_dump(mode="json")
        self._write(payload)

    def get_edital_extraction_result(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> EditalExtractionResult | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._edital_container(payload, user_id)["results"].get(document_id)
        if raw is None:
            return None
        return EditalExtractionResult.model_validate(raw)

    def list_user_edital_extractions(
        self,
        *,
        user_id: str | None,
    ) -> list[EditalExtractionResult]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._edital_container(payload, user_id)["results"].values()
        items = [EditalExtractionResult.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.document_id)
        return items

    def get_edital_extraction_by_id(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> EditalExtractionResult | None:
        for item in self.list_user_edital_extractions(user_id=user_id):
            if item.edital_id == edital_id:
                return item
        return None

    def append_edital_ingestion_event(
        self,
        event: EditalIngestionEvent,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Edital ingestion events require user ownership.")
        payload = self._read()
        container = self._edital_container(payload, user_id)
        existing = container["events"].get(event.document_id, [])
        filtered = [item for item in existing if item.get("event_id") != event.event_id]
        filtered.append(event.model_dump(mode="json"))
        filtered.sort(key=lambda item: item.get("created_at", ""))
        container["events"][event.document_id] = filtered
        self._write(payload)

    def list_edital_ingestion_events(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> list[EditalIngestionEvent]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._edital_container(payload, user_id)["events"].get(document_id, [])
        return [EditalIngestionEvent.model_validate(item) for item in raw]

    def save_bibliography_alignment_state(
        self,
        state: BibliographyAlignmentState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Bibliography alignment state requires user ownership.")
        payload = self._read()
        container = self._bibliography_alignment_container(payload, user_id)
        container["states"][state.edital_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_bibliography_alignment_state(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> BibliographyAlignmentState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._bibliography_alignment_container(payload, user_id)["states"].get(edital_id)
        if raw is None:
            return None
        return BibliographyAlignmentState.model_validate(raw)

    def save_bibliography_alignment_result(
        self,
        result: BibliographyAlignmentResult,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Bibliography alignment result requires user ownership.")
        payload = self._read()
        container = self._bibliography_alignment_container(payload, user_id)
        container["results"][result.edital_id] = result.model_dump(mode="json")
        self._write(payload)

    def get_bibliography_alignment_result(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> BibliographyAlignmentResult | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._bibliography_alignment_container(payload, user_id)["results"].get(edital_id)
        if raw is None:
            return None
        return BibliographyAlignmentResult.model_validate(raw)

    def list_user_bibliography_alignments(
        self,
        *,
        user_id: str | None,
    ) -> list[BibliographyAlignmentResult]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._bibliography_alignment_container(payload, user_id)["results"].values()
        items = [BibliographyAlignmentResult.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.edital_id)
        return items

    def get_bibliography_alignment_by_id(
        self,
        alignment_id: str,
        *,
        user_id: str | None,
    ) -> BibliographyAlignmentResult | None:
        for item in self.list_user_bibliography_alignments(user_id=user_id):
            if item.alignment_id == alignment_id:
                return item
        return None

    def save_curriculum_graph_state(
        self,
        state: CurriculumGraphState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Curriculum graph state requires user ownership.")
        payload = self._read()
        container = self._curriculum_graph_container(payload, user_id)
        container["states"][state.edital_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_curriculum_graph_state(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> CurriculumGraphState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._curriculum_graph_container(payload, user_id)["states"].get(edital_id)
        if raw is None:
            return None
        return CurriculumGraphState.model_validate(raw)

    def save_curriculum_graph(
        self,
        graph: CurriculumGraph,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Curriculum graph requires user ownership.")
        payload = self._read()
        container = self._curriculum_graph_container(payload, user_id)
        container["results"][graph.edital_id] = graph.model_dump(mode="json")
        self._write(payload)

    def get_curriculum_graph(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> CurriculumGraph | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._curriculum_graph_container(payload, user_id)["results"].get(edital_id)
        if raw is None:
            return None
        return CurriculumGraph.model_validate(raw)

    def list_user_curriculum_graphs(
        self,
        *,
        user_id: str | None,
    ) -> list[CurriculumGraph]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._curriculum_graph_container(payload, user_id)["results"].values()
        items = [CurriculumGraph.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.edital_id)
        return items

    def get_curriculum_graph_by_id(
        self,
        graph_id: str,
        *,
        user_id: str | None,
    ) -> CurriculumGraph | None:
        for item in self.list_user_curriculum_graphs(user_id=user_id):
            if item.graph_id == graph_id:
                return item
        return None

    def save_study_cycle_plan_state(
        self,
        state: StudyCyclePlanState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Study cycle plan state requires user ownership.")
        payload = self._read()
        container = self._study_cycle_container(payload, user_id)
        container["states"][state.graph_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_study_cycle_plan_state(
        self,
        graph_id: str,
        *,
        user_id: str | None,
    ) -> StudyCyclePlanState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._study_cycle_container(payload, user_id)["states"].get(graph_id)
        if raw is None:
            return None
        return StudyCyclePlanState.model_validate(raw)

    def save_study_cycle_plan(
        self,
        plan: StudyCyclePlan,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Study cycle plan requires user ownership.")
        payload = self._read()
        container = self._study_cycle_container(payload, user_id)
        container["results"][plan.graph_id] = plan.model_dump(mode="json")
        self._write(payload)

    def get_study_cycle_plan(
        self,
        graph_id: str,
        *,
        user_id: str | None,
    ) -> StudyCyclePlan | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._study_cycle_container(payload, user_id)["results"].get(graph_id)
        if raw is None:
            return None
        return StudyCyclePlan.model_validate(raw)

    def list_user_study_cycle_plans(
        self,
        *,
        user_id: str | None,
    ) -> list[StudyCyclePlan]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._study_cycle_container(payload, user_id)["results"].values()
        items = [StudyCyclePlan.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.graph_id)
        return items

    def get_study_cycle_plan_by_id(
        self,
        cycle_id: str,
        *,
        user_id: str | None,
    ) -> StudyCyclePlan | None:
        for item in self.list_user_study_cycle_plans(user_id=user_id):
            if item.cycle_id == cycle_id:
                return item
        return None

    def save_simulado_blueprint_state(
        self,
        state: SimuladoBlueprintState,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Simulado blueprint state requires user ownership.")
        payload = self._read()
        container = self._simulado_blueprint_container(payload, user_id)
        container["states"][state.cycle_id] = state.model_dump(mode="json")
        self._write(payload)

    def get_simulado_blueprint_state(
        self,
        cycle_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoBlueprintState | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._simulado_blueprint_container(payload, user_id)["states"].get(cycle_id)
        if raw is None:
            return None
        return SimuladoBlueprintState.model_validate(raw)

    def save_simulado_blueprint(
        self,
        blueprint: SimuladoBlueprint,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Simulado blueprint requires user ownership.")
        payload = self._read()
        container = self._simulado_blueprint_container(payload, user_id)
        container["results"][blueprint.cycle_id] = blueprint.model_dump(mode="json")
        self._write(payload)

    def get_simulado_blueprint(
        self,
        cycle_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoBlueprint | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._simulado_blueprint_container(payload, user_id)["results"].get(cycle_id)
        if raw is None:
            return None
        return SimuladoBlueprint.model_validate(raw)

    def list_user_simulado_blueprints(
        self,
        *,
        user_id: str | None,
    ) -> list[SimuladoBlueprint]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._simulado_blueprint_container(payload, user_id)["results"].values()
        items = [SimuladoBlueprint.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.cycle_id)
        return items

    def get_simulado_blueprint_by_id(
        self,
        blueprint_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoBlueprint | None:
        for item in self.list_user_simulado_blueprints(user_id=user_id):
            if item.blueprint_id == blueprint_id:
                return item
        return None

    def save_question_generation_blueprint(
        self,
        blueprint_set: QuestionGenerationBlueprintSet,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Question generation blueprint requires user ownership.")
        payload = self._read()
        container = self._question_generation_blueprint_container(payload, user_id)
        container["results"][blueprint_set.source_simulado_blueprint_id] = blueprint_set.model_dump(mode="json")
        self._write(payload)

    def get_question_generation_blueprint(
        self,
        source_simulado_blueprint_id: str,
        *,
        user_id: str | None,
    ) -> QuestionGenerationBlueprintSet | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._question_generation_blueprint_container(payload, user_id)["results"].get(source_simulado_blueprint_id)
        if raw is None:
            return None
        return QuestionGenerationBlueprintSet.model_validate(raw)

    def list_user_question_generation_blueprints(
        self,
        *,
        user_id: str | None,
    ) -> list[QuestionGenerationBlueprintSet]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._question_generation_blueprint_container(payload, user_id)["results"].values()
        items = [QuestionGenerationBlueprintSet.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.source_simulado_blueprint_id)
        return items

    def get_question_generation_blueprint_by_id(
        self,
        blueprint_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionGenerationBlueprintSet | None:
        for item in self.list_user_question_generation_blueprints(user_id=user_id):
            if item.blueprint_set_id == blueprint_set_id:
                return item
        return None

    def save_question_draft_set(
        self,
        draft_set: QuestionDraftSet,
        *,
        user_id: str | None,
    ) -> None:
        if user_id is None:
            raise ValueError("Question draft set requires user ownership.")
        payload = self._read()
        container = self._question_draft_container(payload, user_id)
        container["results"][draft_set.source_question_generation_blueprint_set_id] = draft_set.model_dump(mode="json")
        self._write(payload)

    def get_question_draft_set(
        self,
        source_question_generation_blueprint_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionDraftSet | None:
        if user_id is None:
            return None
        payload = self._read()
        raw = self._question_draft_container(payload, user_id)["results"].get(
            source_question_generation_blueprint_set_id
        )
        if raw is None:
            return None
        return QuestionDraftSet.model_validate(raw)

    def list_user_question_draft_sets(
        self,
        *,
        user_id: str | None,
    ) -> list[QuestionDraftSet]:
        if user_id is None:
            return []
        payload = self._read()
        raw = self._question_draft_container(payload, user_id)["results"].values()
        items = [QuestionDraftSet.model_validate(item) for item in raw]
        items.sort(key=lambda item: item.source_question_generation_blueprint_set_id)
        return items

    def get_question_draft_set_by_id(
        self,
        draft_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionDraftSet | None:
        for item in self.list_user_question_draft_sets(user_id=user_id):
            if item.draft_set_id == draft_set_id:
                return item
        return None

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
