from __future__ import annotations

from datetime import datetime
from typing import Iterable

from pydantic import BaseModel, Field

from app.domain.models import (
    BibliographyAlignmentResult,
    CurriculumGraph,
    EditalExtractionResult,
    ProgressState,
    SimuladoBlueprint,
    StudyCyclePlan,
    UploadedMaterial,
    User,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.exam_profiles import ExamProfileService


DASHBOARD_VERSION = "user-dashboard-v1"
MAX_RECENT_ITEMS = 10
MAX_PENDING_ACTIONS = 20
MAX_WARNINGS = 20


class DashboardUserSummary(BaseModel):
    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    authenticated: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardActiveProjectSummary(BaseModel):
    project_available: bool = False
    project_id: str | None = None
    title: str | None = None
    exam_target: str | None = None
    board_or_profile: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardContinuationSummary(BaseModel):
    continuation_available: bool = False
    last_subject_id: str | None = None
    last_topic_id: str | None = None
    last_microtopic_id: str | None = None
    last_activity_at: datetime | None = None
    recommended_resume_label: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardRecentMaterialItem(BaseModel):
    document_id: str
    display_filename: str
    content_type: str = ""
    status: str = ""
    uploaded_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardMaterialSummary(BaseModel):
    total_materials: int = 0
    materials_by_type: dict[str, int] = Field(default_factory=dict)
    recent_materials: list[DashboardRecentMaterialItem] = Field(default_factory=list)
    uploaded_count: int = 0
    processed_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    ocr_required_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardPipelineStateItem(BaseModel):
    document_id: str
    display_filename: str
    current_stage: str = ""
    extraction_status: str = ""
    metadata_status: str = ""
    updated_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardDocumentPipelineSummary(BaseModel):
    total_documents: int = 0
    extracted_count: int = 0
    chunked_count: int = 0
    sectioned_count: int = 0
    metadata_ready_count: int = 0
    extraction_pending_count: int = 0
    failed_count: int = 0
    unsupported_count: int = 0
    ocr_required_count: int = 0
    latest_pipeline_states: list[DashboardPipelineStateItem] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardEditalSummary(BaseModel):
    edital_available: bool = False
    latest_edital_id: str | None = None
    latest_document_id: str | None = None
    status: str = "unavailable"
    topics_detected: int = 0
    subtopics_detected: int = 0
    bibliography_items_detected: int = 0
    exclusions_detected: int = 0
    weight_hints_detected: int = 0
    warnings_count: int = 0
    needs_review: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardAlignmentSummary(BaseModel):
    alignment_available: bool = False
    latest_alignment_id: str | None = None
    status: str = "unavailable"
    bibliography_items_total: int = 0
    bibliography_items_matched: int = 0
    topics_total: int = 0
    topics_with_coverage: int = 0
    gaps_detected: int = 0
    redundancies_detected: int = 0
    ocr_required_gaps: int = 0
    missing_material_gaps: int = 0
    ambiguous_gaps: int = 0
    needs_review: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardCurriculumGraphSummary(BaseModel):
    graph_available: bool = False
    latest_graph_id: str | None = None
    status: str = "unavailable"
    subject_count: int = 0
    topic_count: int = 0
    subtopic_count: int = 0
    coverage_links_count: int = 0
    covered_topics_count: int = 0
    partially_covered_topics_count: int = 0
    weakly_covered_topics_count: int = 0
    uncovered_topics_count: int = 0
    gaps_count: int = 0
    redundancies_count: int = 0
    ocr_required_count: int = 0
    needs_review_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardStudyCycleSummary(BaseModel):
    cycle_available: bool = False
    latest_cycle_id: str | None = None
    status: str = "unavailable"
    subject_count: int = 0
    topic_slot_count: int = 0
    review_slot_count: int = 0
    gap_slot_count: int = 0
    balance_state: str = "unavailable"
    fatigue_risk_level: str = "unknown"
    material_blocked: bool = False
    ocr_blocked: bool = False
    needs_review: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardExamProfileSummary(BaseModel):
    profile_available: bool = False
    suggested_profile_id: str | None = None
    board_id: str | None = None
    exam_family: str | None = None
    format_type: str = "unknown"
    heuristic_confidence: float = 0.0
    format_confidence: float = 0.0
    scoring_confidence: float = 0.0
    needs_confirmation: bool = False
    warnings_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardSimuladoBlueprintSummary(BaseModel):
    blueprint_available: bool = False
    latest_blueprint_id: str | None = None
    status: str = "unavailable"
    readiness_state: str = "unavailable"
    section_count: int = 0
    question_slot_count: int = 0
    ready_slot_count: int = 0
    blocked_slot_count: int = 0
    review_needed_slot_count: int = 0
    ocr_blocked_count: int = 0
    material_gap_count: int = 0
    ambiguity_count: int = 0
    format_type: str = "unknown"
    scoring_source: str = "unknown"
    question_count_source: str = "unknown"
    no_question_generation_confirmed: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardProgressSummary(BaseModel):
    progress_available: bool = False
    total_attempts: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    accuracy: float = 0.0
    studied_topics_count: int = 0
    weak_topics_count: int = 0
    last_activity_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardRetentionSummary(BaseModel):
    retention_available: bool = False
    aggregate_retention_state: str = "unavailable"
    durable_microtopics_count: int = 0
    fragile_microtopics_count: int = 0
    superficial_microtopics_count: int = 0
    insufficient_evidence_count: int = 0
    false_fluency_count: int = 0
    evidence_coverage_ratio: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardPendingAction(BaseModel):
    action_id: str
    action_type: str
    title: str
    description: str
    severity: str = "info"
    priority: int = 100
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    suggested_next_step: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardPrimaryNextStep(BaseModel):
    action_type: str
    title: str
    description: str
    severity: str = "info"
    priority: int = 100
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    metadata: dict[str, object] = Field(default_factory=dict)


class UserDashboardOverview(BaseModel):
    dashboard_available: bool = True
    dashboard_state: str = "no_data"
    dashboard_summary: str = ""
    journey_stage: str = "unknown"
    pipeline_readiness: str = "no_data"
    study_readiness: str = "not_ready"
    active_project: DashboardActiveProjectSummary = Field(default_factory=DashboardActiveProjectSummary)
    user: DashboardUserSummary = Field(default_factory=DashboardUserSummary)
    continuation: DashboardContinuationSummary = Field(default_factory=DashboardContinuationSummary)
    materials: DashboardMaterialSummary = Field(default_factory=DashboardMaterialSummary)
    document_pipeline: DashboardDocumentPipelineSummary = Field(default_factory=DashboardDocumentPipelineSummary)
    edital: DashboardEditalSummary = Field(default_factory=DashboardEditalSummary)
    alignment: DashboardAlignmentSummary = Field(default_factory=DashboardAlignmentSummary)
    curriculum_graph: DashboardCurriculumGraphSummary = Field(default_factory=DashboardCurriculumGraphSummary)
    study_cycle: DashboardStudyCycleSummary = Field(default_factory=DashboardStudyCycleSummary)
    exam_profile: DashboardExamProfileSummary = Field(default_factory=DashboardExamProfileSummary)
    simulado_blueprint: DashboardSimuladoBlueprintSummary = Field(default_factory=DashboardSimuladoBlueprintSummary)
    progress: DashboardProgressSummary = Field(default_factory=DashboardProgressSummary)
    retention: DashboardRetentionSummary = Field(default_factory=DashboardRetentionSummary)
    pending_actions: list[DashboardPendingAction] = Field(default_factory=list)
    primary_next_step: DashboardPrimaryNextStep | None = None
    warnings: list[DashboardWarning] = Field(default_factory=list)
    generated_at: datetime | None = None
    dashboard_version: str = DASHBOARD_VERSION
    metadata: dict[str, object] = Field(default_factory=dict)


class UserDashboardService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository
        self.exam_profiles = ExamProfileService(repository)

    def build_overview(self, user_id: str | None) -> UserDashboardOverview:
        user = self.repository.get_user(user_id) if user_id else None
        materials = self.repository.list_uploaded_materials(user_id=user_id) if user_id else []
        material_map = {item.metadata.document_id: item for item in materials}
        pipeline_states = []
        extraction_results = {}
        if user_id:
            for material in materials:
                document_id = material.metadata.document_id
                state = self.repository.get_document_pipeline_state(document_id, user_id=user_id)
                if state is not None:
                    pipeline_states.append(state)
                extraction = self.repository.get_document_extraction_result(document_id, user_id=user_id)
                if extraction is not None:
                    extraction_results[document_id] = extraction
        editais = self.repository.list_user_edital_extractions(user_id=user_id) if user_id else []
        alignments = self.repository.list_user_bibliography_alignments(user_id=user_id) if user_id else []
        graphs = self.repository.list_user_curriculum_graphs(user_id=user_id) if user_id else []
        cycles = self.repository.list_user_study_cycle_plans(user_id=user_id) if user_id else []
        blueprints = self.repository.list_user_simulado_blueprints(user_id=user_id) if user_id else []
        progress = self.repository.load_progress(user_id=user_id) if user_id else ProgressState()

        latest_edital = editais[-1] if editais else None
        latest_alignment = alignments[-1] if alignments else None
        latest_graph = graphs[-1] if graphs else None
        latest_cycle = cycles[-1] if cycles else None
        latest_blueprint = blueprints[-1] if blueprints else None

        user_summary = self._user_summary(user, user_id)
        materials_summary = self._materials_summary(materials, extraction_results)
        pipeline_summary = self._document_pipeline_summary(materials, pipeline_states, extraction_results)
        edital_summary = self._edital_summary(latest_edital, user_id=user_id)
        alignment_summary = self._alignment_summary(latest_alignment, user_id=user_id)
        graph_summary = self._graph_summary(latest_graph, user_id=user_id)
        cycle_summary = self._cycle_summary(latest_cycle, user_id=user_id)
        exam_profile_summary = self._exam_profile_summary(latest_edital)
        blueprint_summary = self._simulado_blueprint_summary(latest_blueprint, user_id=user_id)
        progress_summary = self._progress_summary(progress)
        continuation_summary = self._continuation_summary(progress, latest_graph)
        retention_summary = DashboardRetentionSummary(
            retention_available=False,
            aggregate_retention_state="unavailable",
            metadata={"reason": "aggregate_retention_not_persisted_for_dashboard"},
        )

        pending_actions = self._pending_actions(
            user=user_summary,
            materials=materials_summary,
            pipeline=pipeline_summary,
            edital=edital_summary,
            alignment=alignment_summary,
            graph=graph_summary,
            cycle=cycle_summary,
            exam_profile=exam_profile_summary,
            blueprint=blueprint_summary,
        )
        primary_next_step = self._primary_next_step(pending_actions)
        warnings = self._warnings(
            materials=materials_summary,
            alignment=alignment_summary,
            graph=graph_summary,
            cycle=cycle_summary,
            exam_profile=exam_profile_summary,
            blueprint=blueprint_summary,
        )
        dashboard_state = self._dashboard_state(
            materials=materials_summary,
            pipeline=pipeline_summary,
            edital=edital_summary,
            alignment=alignment_summary,
            graph=graph_summary,
            cycle=cycle_summary,
            blueprint=blueprint_summary,
            exam_profile=exam_profile_summary,
            pending_actions=pending_actions,
        )
        pipeline_readiness = self._pipeline_readiness(
            materials=materials_summary,
            pipeline=pipeline_summary,
            edital=edital_summary,
            alignment=alignment_summary,
            graph=graph_summary,
            cycle=cycle_summary,
            blueprint=blueprint_summary,
        )
        study_readiness = self._study_readiness(
            cycle=cycle_summary,
            blueprint=blueprint_summary,
            exam_profile=exam_profile_summary,
            continuation=continuation_summary,
            pending_actions=pending_actions,
        )
        journey_stage = self._journey_stage(dashboard_state)
        generated_at = self._generated_at(
            user,
            materials,
            pipeline_states,
            latest_edital,
            latest_alignment,
            latest_graph,
            latest_cycle,
            latest_blueprint,
            progress_summary.last_activity_at,
        )
        return UserDashboardOverview(
            dashboard_available=True,
            dashboard_state=dashboard_state,
            dashboard_summary=self._dashboard_summary(
                materials=materials_summary,
                edital=edital_summary,
                alignment=alignment_summary,
                cycle=cycle_summary,
                blueprint=blueprint_summary,
                dashboard_state=dashboard_state,
            ),
            journey_stage=journey_stage,
            pipeline_readiness=pipeline_readiness,
            study_readiness=study_readiness,
            active_project=DashboardActiveProjectSummary(),
            user=user_summary,
            continuation=continuation_summary,
            materials=materials_summary,
            document_pipeline=pipeline_summary,
            edital=edital_summary,
            alignment=alignment_summary,
            curriculum_graph=graph_summary,
            study_cycle=cycle_summary,
            exam_profile=exam_profile_summary,
            simulado_blueprint=blueprint_summary,
            progress=progress_summary,
            retention=retention_summary,
            pending_actions=pending_actions[:MAX_PENDING_ACTIONS],
            primary_next_step=primary_next_step,
            warnings=warnings[:MAX_WARNINGS],
            generated_at=generated_at,
            metadata={
                "material_document_ids": sorted(material_map.keys())[:MAX_RECENT_ITEMS],
                "pending_action_count": len(pending_actions[:MAX_PENDING_ACTIONS]),
            },
        )

    def _user_summary(self, user: User | None, user_id: str | None) -> DashboardUserSummary:
        return DashboardUserSummary(
            user_id=user.user_id if user else user_id,
            username=user.username if user else None,
            email=user.email if user else None,
            display_name=user.display_name if user else None,
            authenticated=bool(user_id),
        )

    def _materials_summary(
        self,
        materials: list[UploadedMaterial],
        extraction_results: dict[str, object],
    ) -> DashboardMaterialSummary:
        by_type: dict[str, int] = {}
        processed = 0
        pending = 0
        failed = 0
        ocr_required = 0
        for material in materials:
            content_type = material.metadata.content_type or "unknown"
            by_type[content_type] = by_type.get(content_type, 0) + 1
            status = material.metadata.status or material.metadata.extraction_status
            if status in {"failed", "unsupported"}:
                failed += 1
            elif status in {"metadata_ready", "sectioned", "chunked", "extracted"} or material.metadata.extraction_status in {
                "metadata_ready",
                "sectioned",
                "chunked",
                "extracted",
            }:
                processed += 1
            else:
                pending += 1
            extraction = extraction_results.get(material.metadata.document_id)
            if extraction is not None and (
                bool(extraction.metadata.get("requires_ocr")) or "ocr_required" in extraction.warnings
            ):
                ocr_required += 1
        recent = sorted(
            materials,
            key=lambda item: (item.metadata.created_at or datetime.min, item.metadata.document_id),
            reverse=True,
        )[:MAX_RECENT_ITEMS]
        return DashboardMaterialSummary(
            total_materials=len(materials),
            materials_by_type=by_type,
            recent_materials=[
                DashboardRecentMaterialItem(
                    document_id=item.metadata.document_id,
                    display_filename=item.metadata.original_filename or item.metadata.filename,
                    content_type=item.metadata.content_type,
                    status=item.metadata.status or item.metadata.extraction_status,
                    uploaded_at=item.metadata.created_at,
                )
                for item in recent
            ],
            uploaded_count=len(materials),
            processed_count=processed,
            pending_count=pending,
            failed_count=failed,
            ocr_required_count=ocr_required,
        )

    def _document_pipeline_summary(self, materials, states, extraction_results) -> DashboardDocumentPipelineSummary:
        extracted = 0
        chunked = 0
        sectioned = 0
        metadata_ready = 0
        pending = 0
        failed = 0
        unsupported = 0
        ocr_required = 0
        state_items = []
        material_by_id = {item.metadata.document_id: item for item in materials}
        seen_document_ids: set[str] = set()
        for state in states:
            seen_document_ids.add(state.document_id)
            if state.extraction_status in {"extracted", "chunked", "sectioned", "metadata_ready"}:
                extracted += 1
            if state.current_stage in {"chunked", "sectioned", "metadata_ready"} or state.chunk_count > 0:
                chunked += 1
            if state.current_stage in {"sectioned", "metadata_ready"} or state.section_count > 0:
                sectioned += 1
            if state.current_stage == "metadata_ready" or state.metadata_status == "ready":
                metadata_ready += 1
            if state.current_stage in {"failed"}:
                failed += 1
            if state.current_stage in {"unsupported"}:
                unsupported += 1
            if state.extraction_status in {"pending_extraction"} or state.current_stage in {"extraction_pending", "pending_extraction", "extraction_started"}:
                pending += 1
            extraction = extraction_results.get(state.document_id)
            if extraction is not None and (
                bool(extraction.metadata.get("requires_ocr")) or "ocr_required" in extraction.warnings
            ):
                ocr_required += 1
            material = material_by_id.get(state.document_id)
            state_items.append(
                DashboardPipelineStateItem(
                    document_id=state.document_id,
                    display_filename=(material.metadata.original_filename if material else state.document_id),
                    current_stage=state.current_stage,
                    extraction_status=state.extraction_status,
                    metadata_status=state.metadata_status,
                    updated_at=state.updated_at,
                    metadata={"chunk_count": state.chunk_count, "section_count": state.section_count},
                )
            )
        for material in materials:
            if material.metadata.document_id in seen_document_ids:
                continue
            pending += 1
            state_items.append(
                DashboardPipelineStateItem(
                    document_id=material.metadata.document_id,
                    display_filename=material.metadata.original_filename or material.metadata.filename,
                    current_stage=material.metadata.status or "uploaded",
                    extraction_status=material.metadata.extraction_status or "uploaded",
                    metadata_status="not_ready",
                    updated_at=material.metadata.updated_at or material.metadata.created_at,
                    metadata={"pipeline_state_missing": True},
                )
            )
        latest = sorted(
            state_items,
            key=lambda item: (item.updated_at or datetime.min, item.document_id),
            reverse=True,
        )[:MAX_RECENT_ITEMS]
        return DashboardDocumentPipelineSummary(
            total_documents=len(materials),
            extracted_count=extracted,
            chunked_count=chunked,
            sectioned_count=sectioned,
            metadata_ready_count=metadata_ready,
            extraction_pending_count=pending,
            failed_count=failed,
            unsupported_count=unsupported,
            ocr_required_count=ocr_required,
            latest_pipeline_states=latest,
        )

    def _edital_summary(self, edital: EditalExtractionResult | None, *, user_id: str | None) -> DashboardEditalSummary:
        if edital is None:
            return DashboardEditalSummary()
        state = self.repository.get_edital_ingestion_state(edital.document_id, user_id=user_id)
        warnings_count = len(edital.warnings) + (len(state.warnings) if state else 0)
        status = state.status if state else "available"
        return DashboardEditalSummary(
            edital_available=True,
            latest_edital_id=edital.edital_id,
            latest_document_id=edital.document_id,
            status=status,
            topics_detected=len(edital.topics),
            subtopics_detected=len(edital.subtopics),
            bibliography_items_detected=len(edital.bibliography),
            exclusions_detected=len(edital.exclusions),
            weight_hints_detected=len(edital.weight_hints),
            warnings_count=warnings_count,
            needs_review=warnings_count > 0 or status not in {"available", "ready", "completed"},
        )

    def _alignment_summary(
        self,
        alignment: BibliographyAlignmentResult | None,
        *,
        user_id: str | None,
    ) -> DashboardAlignmentSummary:
        if alignment is None:
            return DashboardAlignmentSummary()
        state = self.repository.get_bibliography_alignment_state(alignment.edital_id, user_id=user_id)
        gap_types = [item.gap_type for item in alignment.gaps]
        return DashboardAlignmentSummary(
            alignment_available=True,
            latest_alignment_id=alignment.alignment_id,
            status=state.status if state else "available",
            bibliography_items_total=len(alignment.bibliography_alignments),
            bibliography_items_matched=sum(1 for item in alignment.bibliography_alignments if item.match_state != "unmatched"),
            topics_total=len(alignment.topic_coverage),
            topics_with_coverage=sum(1 for item in alignment.topic_coverage if item.coverage_state != "uncovered"),
            gaps_detected=len(alignment.gaps),
            redundancies_detected=len(alignment.redundancies),
            ocr_required_gaps=gap_types.count("ocr_required"),
            missing_material_gaps=sum(1 for item in gap_types if item in {"missing_bibliography_material", "missing_document_text", "uncovered_topic"}),
            ambiguous_gaps=gap_types.count("ambiguous_reference"),
            needs_review=bool(alignment.gaps or alignment.redundancies or alignment.warnings),
        )

    def _graph_summary(self, graph: CurriculumGraph | None, *, user_id: str | None) -> DashboardCurriculumGraphSummary:
        if graph is None:
            return DashboardCurriculumGraphSummary()
        state = self.repository.get_curriculum_graph_state(graph.edital_id, user_id=user_id)
        return DashboardCurriculumGraphSummary(
            graph_available=True,
            latest_graph_id=graph.graph_id,
            status=state.status if state else "available",
            subject_count=graph.summary.subject_count or len(graph.subjects),
            topic_count=graph.summary.topic_count or len(graph.topics),
            subtopic_count=graph.summary.subtopic_count or len(graph.subtopics),
            coverage_links_count=state.coverage_links_count if state else len(graph.coverage_links),
            covered_topics_count=graph.summary.covered_topics_count,
            partially_covered_topics_count=graph.summary.partially_covered_topics_count,
            weakly_covered_topics_count=graph.summary.weakly_covered_topics_count,
            uncovered_topics_count=graph.summary.uncovered_topics_count,
            gaps_count=graph.summary.gap_count or len(graph.gaps),
            redundancies_count=graph.summary.redundancy_count or len(graph.redundancies),
            ocr_required_count=graph.summary.ocr_required_count,
            needs_review_count=graph.summary.needs_review_count,
        )

    def _cycle_summary(self, cycle: StudyCyclePlan | None, *, user_id: str | None) -> DashboardStudyCycleSummary:
        if cycle is None:
            return DashboardStudyCycleSummary()
        state = self.repository.get_study_cycle_plan_state(cycle.graph_id, user_id=user_id)
        return DashboardStudyCycleSummary(
            cycle_available=True,
            latest_cycle_id=cycle.cycle_id,
            status=state.status if state else "available",
            subject_count=state.subject_count if state else len(cycle.subject_rotations),
            topic_slot_count=state.topic_slot_count if state else len(cycle.topic_slots),
            review_slot_count=state.review_slot_count if state else len(cycle.review_slots),
            gap_slot_count=state.gap_slot_count if state else len(cycle.gap_slots),
            balance_state=cycle.balance_summary.balance_state,
            fatigue_risk_level=cycle.fatigue_profile.fatigue_risk_level,
            material_blocked=cycle.balance_summary.balance_state == "material_blocked" or cycle.balance_summary.gap_blocked_slot_count > 0,
            ocr_blocked=cycle.balance_summary.ocr_blocked_slot_count > 0,
            needs_review=cycle.balance_summary.review_needed_slot_count > 0 or bool(cycle.warnings),
        )

    def _exam_profile_summary(self, edital: EditalExtractionResult | None) -> DashboardExamProfileSummary:
        suggestion = self.exam_profiles.suggest_exam_profile_from_edital(edital) if edital is not None else None
        if suggestion is None:
            return DashboardExamProfileSummary()
        needs_confirmation = (
            bool(suggestion.metadata.get("format_requires_confirmation"))
            or suggestion.scoring_confidence < 0.8
            or bool(suggestion.warnings)
        )
        return DashboardExamProfileSummary(
            profile_available=bool(suggestion.profile_id or suggestion.board_id or suggestion.format_type != "unknown"),
            suggested_profile_id=suggestion.profile_id,
            board_id=suggestion.board_id,
            exam_family=suggestion.exam_family,
            format_type=suggestion.format_type or "unknown",
            heuristic_confidence=suggestion.heuristic_confidence,
            format_confidence=suggestion.format_confidence,
            scoring_confidence=suggestion.scoring_confidence,
            needs_confirmation=needs_confirmation,
            warnings_count=len(suggestion.warnings),
            metadata={"negative_marking_confirmed": bool(suggestion.metadata.get("negative_marking_confirmed"))},
        )

    def _simulado_blueprint_summary(self, blueprint: SimuladoBlueprint | None, *, user_id: str | None) -> DashboardSimuladoBlueprintSummary:
        if blueprint is None:
            return DashboardSimuladoBlueprintSummary()
        state = self.repository.get_simulado_blueprint_state(blueprint.cycle_id, user_id=user_id)
        return DashboardSimuladoBlueprintSummary(
            blueprint_available=True,
            latest_blueprint_id=blueprint.blueprint_id,
            status=state.status if state else "available",
            readiness_state=blueprint.readiness_profile.readiness_state,
            section_count=len(blueprint.sections),
            question_slot_count=len(blueprint.question_slots),
            ready_slot_count=blueprint.readiness_profile.ready_slot_count,
            blocked_slot_count=blueprint.readiness_profile.blocked_slot_count,
            review_needed_slot_count=blueprint.readiness_profile.review_needed_slot_count,
            ocr_blocked_count=blueprint.readiness_profile.ocr_blocked_count,
            material_gap_count=blueprint.readiness_profile.material_gap_count,
            ambiguity_count=blueprint.readiness_profile.ambiguity_count,
            format_type=blueprint.format_type,
            scoring_source=blueprint.scoring_plan.scoring_source,
            question_count_source=blueprint.distribution_plan.question_count_source,
            no_question_generation_confirmed=any(
                item.constraint_type == "no_question_generation_in_this_pass"
                for item in blueprint.generation_constraints
            ),
        )

    def _progress_summary(self, progress: ProgressState) -> DashboardProgressSummary:
        topic_states = list(progress.topic_learning_states.values())
        total_attempts = sum(max(item.attempts, item.total_questions) for item in topic_states)
        correct_count = sum(max(item.correct_answers, item.correct_attempts) for item in topic_states)
        incorrect_count = sum(item.incorrect_attempts for item in topic_states)
        activity_candidates: list[datetime] = []
        for item in topic_states:
            if item.last_seen_at:
                activity_candidates.append(item.last_seen_at)
        for item in progress.item_states.values():
            if item.last_seen_at:
                activity_candidates.append(item.last_seen_at)
        for item in progress.microtopic_performance.values():
            if item.last_seen_at:
                activity_candidates.append(item.last_seen_at)
        for item in progress.pedagogical_memory.values():
            if item.last_intervention_at:
                activity_candidates.append(item.last_intervention_at)
        last_activity = max(activity_candidates) if activity_candidates else None
        denominator = correct_count + incorrect_count
        return DashboardProgressSummary(
            progress_available=bool(total_attempts or correct_count or incorrect_count or progress.weak_topics),
            total_attempts=total_attempts,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            accuracy=round(correct_count / denominator, 4) if denominator else 0.0,
            studied_topics_count=sum(1 for item in topic_states if max(item.attempts, item.total_questions) > 0),
            weak_topics_count=len(progress.weak_topics),
            last_activity_at=last_activity,
        )

    def _continuation_summary(
        self,
        progress: ProgressState,
        graph: CurriculumGraph | None,
    ) -> DashboardContinuationSummary:
        latest_topic_id = None
        latest_activity = None
        for topic_id, state in progress.topic_learning_states.items():
            if state.last_seen_at and (latest_activity is None or state.last_seen_at > latest_activity):
                latest_activity = state.last_seen_at
                latest_topic_id = topic_id
        latest_microtopic_id = None
        for microtopic_id, state in progress.pedagogical_memory.items():
            if state.last_intervention_at and (latest_activity is None or state.last_intervention_at > latest_activity):
                latest_activity = state.last_intervention_at
                latest_topic_id = state.topic_id
                latest_microtopic_id = microtopic_id
        if latest_activity is None or latest_topic_id is None:
            return DashboardContinuationSummary()
        last_subject_id = None
        if graph is not None:
            for topic in graph.topics:
                if topic.topic_id == latest_topic_id:
                    last_subject_id = topic.subject_id
                    break
        return DashboardContinuationSummary(
            continuation_available=True,
            last_subject_id=last_subject_id,
            last_topic_id=latest_topic_id,
            last_microtopic_id=latest_microtopic_id,
            last_activity_at=latest_activity,
            recommended_resume_label=f"Resume from topic {latest_topic_id}.",
        )

    def _pending_actions(
        self,
        *,
        user: DashboardUserSummary,
        materials: DashboardMaterialSummary,
        pipeline: DashboardDocumentPipelineSummary,
        edital: DashboardEditalSummary,
        alignment: DashboardAlignmentSummary,
        graph: DashboardCurriculumGraphSummary,
        cycle: DashboardStudyCycleSummary,
        exam_profile: DashboardExamProfileSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
    ) -> list[DashboardPendingAction]:
        actions: list[DashboardPendingAction] = []
        if not user.authenticated:
            return actions
        if materials.total_materials == 0:
            actions.append(
                DashboardPendingAction(
                    action_id="action:upload-material",
                    action_type="upload_material",
                    title="Upload your first material",
                    description="Add at least one study material to start the pipeline.",
                    severity="warning",
                    priority=10,
                    suggested_next_step="Upload a file through the materials area.",
                )
            )
        if materials.pending_count > 0:
            actions.append(
                DashboardPendingAction(
                    action_id="action:process-material",
                    action_type="process_material",
                    title="Process uploaded materials",
                    description=f"{materials.pending_count} uploaded materials still need document processing.",
                    severity="warning",
                    priority=20,
                    related_artifact_type="materials",
                    suggested_next_step="Process pending uploads before expecting downstream artifacts.",
                )
            )
        if materials.ocr_required_count > 0 or pipeline.ocr_required_count > 0 or alignment.ocr_required_gaps > 0 or graph.ocr_required_count > 0 or cycle.ocr_blocked or blueprint.ocr_blocked_count > 0:
            actions.append(
                DashboardPendingAction(
                    action_id="action:run-ocr-future",
                    action_type="run_ocr_future",
                    title="OCR-required materials are blocking coverage",
                    description="Some uploaded PDFs are textless or require OCR before they can support the study pipeline.",
                    severity="blocked",
                    priority=5,
                    related_artifact_type="document_pipeline",
                    suggested_next_step="Keep these materials flagged for future OCR support.",
                )
            )
        if materials.total_materials > 0 and not edital.edital_available:
            actions.append(
                DashboardPendingAction(
                    action_id="action:ingest-edital",
                    action_type="ingest_edital",
                    title="Map your edital",
                    description="Materials exist, but there is no edital extraction yet.",
                    severity="warning",
                    priority=30,
                    related_artifact_type="edital",
                    suggested_next_step="Ingest the edital after the source document is ready.",
                )
            )
        if edital.edital_available and not alignment.alignment_available:
            actions.append(
                DashboardPendingAction(
                    action_id="action:align-bibliography",
                    action_type="align_bibliography",
                    title="Align bibliography coverage",
                    description="The edital exists, but bibliography alignment is still missing.",
                    severity="warning",
                    priority=40,
                    related_artifact_type="alignment",
                    related_artifact_id=edital.latest_edital_id,
                    suggested_next_step="Run bibliography alignment to map materials to edital topics.",
                )
            )
        if alignment.alignment_available and not graph.graph_available:
            actions.append(
                DashboardPendingAction(
                    action_id="action:build-graph",
                    action_type="build_curriculum_graph",
                    title="Build the curriculum graph",
                    description="Coverage mapping exists, but the curriculum graph has not been built yet.",
                    severity="warning",
                    priority=50,
                    related_artifact_type="curriculum_graph",
                    suggested_next_step="Build the curriculum graph from existing alignment evidence.",
                )
            )
        if graph.graph_available and not cycle.cycle_available:
            actions.append(
                DashboardPendingAction(
                    action_id="action:build-cycle",
                    action_type="build_study_cycle",
                    title="Build the study cycle",
                    description="The curriculum graph is available, but the study cycle has not been created yet.",
                    severity="warning",
                    priority=60,
                    related_artifact_type="study_cycle",
                    related_artifact_id=graph.latest_graph_id,
                    suggested_next_step="Create the study cycle candidate from the existing graph.",
                )
            )
        if cycle.cycle_available and exam_profile.needs_confirmation:
            actions.append(
                DashboardPendingAction(
                    action_id="action:confirm-profile",
                    action_type="confirm_exam_profile",
                    title="Confirm exam profile details",
                    description="Exam format or scoring still needs confirmation from the edital.",
                    severity="warning",
                    priority=70,
                    related_artifact_type="exam_profile",
                    related_artifact_id=exam_profile.suggested_profile_id,
                    suggested_next_step="Review the suggested exam profile before trusting blueprint assumptions.",
                )
            )
        if cycle.cycle_available and exam_profile.profile_available and not blueprint.blueprint_available:
            actions.append(
                DashboardPendingAction(
                    action_id="action:build-blueprint",
                    action_type="build_simulado_blueprint",
                    title="Prepare a simulado blueprint",
                    description="Study cycle and exam profile are available, but no simulado blueprint exists yet.",
                    severity="info",
                    priority=80,
                    related_artifact_type="simulado_blueprint",
                    related_artifact_id=cycle.latest_cycle_id,
                    suggested_next_step="Build the read-only simulado blueprint candidate from the cycle.",
                )
            )
        if alignment.missing_material_gaps or graph.gaps_count or cycle.gap_slot_count or blueprint.material_gap_count:
            actions.append(
                DashboardPendingAction(
                    action_id="action:resolve-material-gap",
                    action_type="resolve_material_gap",
                    title="Resolve material gaps",
                    description="Coverage still depends on missing material, missing text or uncovered topics.",
                    severity="blocked" if alignment.missing_material_gaps or blueprint.material_gap_count else "warning",
                    priority=15,
                    related_artifact_type="alignment",
                    related_artifact_id=alignment.latest_alignment_id or graph.latest_graph_id,
                    suggested_next_step="Review missing materials before trusting blocked areas.",
                )
            )
        if alignment.ambiguous_gaps or graph.needs_review_count or cycle.needs_review or blueprint.ambiguity_count:
            actions.append(
                DashboardPendingAction(
                    action_id="action:manual-review",
                    action_type="manual_review",
                    title="Review ambiguous areas",
                    description="Some artifacts still need manual review because coverage or format remains ambiguous.",
                    severity="warning",
                    priority=25,
                    related_artifact_type="review",
                    suggested_next_step="Inspect the ambiguous topics, profile hints or blocked slots before proceeding.",
                )
            )
        actions.sort(key=self._pending_action_sort_key)
        return actions[:MAX_PENDING_ACTIONS]

    def _warnings(
        self,
        *,
        materials: DashboardMaterialSummary,
        alignment: DashboardAlignmentSummary,
        graph: DashboardCurriculumGraphSummary,
        cycle: DashboardStudyCycleSummary,
        exam_profile: DashboardExamProfileSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
    ) -> list[DashboardWarning]:
        warnings: list[DashboardWarning] = []
        if materials.ocr_required_count:
            warnings.append(DashboardWarning(code="ocr_required", message="Some materials require OCR before they can be used fully.", severity="warning"))
        if alignment.missing_material_gaps or blueprint.material_gap_count:
            warnings.append(DashboardWarning(code="material_gaps", message="Material gaps still block parts of the learning pipeline.", severity="warning"))
        if alignment.ambiguous_gaps or blueprint.ambiguity_count:
            warnings.append(DashboardWarning(code="manual_review_needed", message="Ambiguous coverage or format still needs manual review.", severity="warning"))
        if exam_profile.needs_confirmation:
            warnings.append(DashboardWarning(code="exam_profile_confirmation_needed", message="Exam format or scoring still needs confirmation.", severity="warning"))
        if graph.needs_review_count or cycle.needs_review:
            warnings.append(DashboardWarning(code="review_needed", message="Some candidate curriculum or cycle artifacts remain review-oriented.", severity="info"))
        return warnings[:MAX_WARNINGS]

    def _primary_next_step(self, actions: list[DashboardPendingAction]) -> DashboardPrimaryNextStep | None:
        if not actions:
            return None
        selected = sorted(actions, key=self._pending_action_sort_key)[0]
        return DashboardPrimaryNextStep(
            action_type=selected.action_type,
            title=selected.title,
            description=selected.description,
            severity=selected.severity,
            priority=selected.priority,
            related_artifact_type=selected.related_artifact_type,
            related_artifact_id=selected.related_artifact_id,
            metadata=selected.metadata,
        )

    def _dashboard_state(
        self,
        *,
        materials: DashboardMaterialSummary,
        pipeline: DashboardDocumentPipelineSummary,
        edital: DashboardEditalSummary,
        alignment: DashboardAlignmentSummary,
        graph: DashboardCurriculumGraphSummary,
        cycle: DashboardStudyCycleSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
        exam_profile: DashboardExamProfileSummary,
        pending_actions: list[DashboardPendingAction],
    ) -> str:
        action_types = {item.action_type for item in pending_actions}
        if "run_ocr_future" in action_types:
            return "blocked_by_ocr"
        if "resolve_material_gap" in action_types:
            return "blocked_by_materials"
        if "manual_review" in action_types or exam_profile.needs_confirmation:
            return "needs_manual_review"
        if blueprint.blueprint_available:
            return "simulado_blueprint_ready"
        if cycle.cycle_available:
            return "study_cycle_ready"
        if graph.graph_available:
            return "graph_ready"
        if alignment.alignment_available:
            return "alignment_ready"
        if edital.edital_available:
            return "edital_ready"
        if pipeline.total_documents and (pipeline.extraction_pending_count or pipeline.metadata_ready_count < pipeline.total_documents):
            return "documents_processing"
        if materials.total_materials:
            return "materials_uploaded"
        return "getting_started"

    def _pipeline_readiness(
        self,
        *,
        materials: DashboardMaterialSummary,
        pipeline: DashboardDocumentPipelineSummary,
        edital: DashboardEditalSummary,
        alignment: DashboardAlignmentSummary,
        graph: DashboardCurriculumGraphSummary,
        cycle: DashboardStudyCycleSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
    ) -> str:
        if materials.total_materials == 0:
            return "no_data"
        if pipeline.ocr_required_count or alignment.ocr_required_gaps or graph.ocr_required_count or cycle.ocr_blocked or blueprint.ocr_blocked_count:
            return "blocked"
        if blueprint.blueprint_available:
            return "blueprint_ready"
        if cycle.cycle_available:
            return "cycle_ready"
        if graph.graph_available:
            return "graph_ready"
        if alignment.alignment_available:
            return "alignment_ready"
        if edital.edital_available:
            return "edital_ready"
        if pipeline.metadata_ready_count == pipeline.total_documents and pipeline.total_documents > 0:
            return "documents_ready"
        if pipeline.total_documents:
            return "documents_processing"
        return "materials_ready"

    def _study_readiness(
        self,
        *,
        cycle: DashboardStudyCycleSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
        exam_profile: DashboardExamProfileSummary,
        continuation: DashboardContinuationSummary,
        pending_actions: list[DashboardPendingAction],
    ) -> str:
        action_types = {item.action_type for item in pending_actions}
        if {"run_ocr_future", "resolve_material_gap"} & action_types:
            return "blocked"
        if blueprint.blueprint_available and blueprint.ready_slot_count > 0:
            return "ready_for_simulado"
        if cycle.cycle_available:
            return "ready_for_review"
        if continuation.continuation_available:
            return "ready_to_continue"
        if exam_profile.profile_available:
            return "ready_for_review"
        return "not_ready"

    def _journey_stage(self, dashboard_state: str) -> str:
        mapping = {
            "getting_started": "uploading_materials",
            "materials_uploaded": "processing_documents",
            "documents_processing": "processing_documents",
            "edital_ready": "edital_mapping",
            "alignment_ready": "coverage_mapping",
            "graph_ready": "curriculum_graph",
            "study_cycle_ready": "study_cycle",
            "simulado_blueprint_ready": "simulado_preparation",
            "blocked_by_ocr": "blocked",
            "blocked_by_materials": "blocked",
            "needs_manual_review": "blocked",
        }
        return mapping.get(dashboard_state, "unknown")

    def _dashboard_summary(
        self,
        *,
        materials: DashboardMaterialSummary,
        edital: DashboardEditalSummary,
        alignment: DashboardAlignmentSummary,
        cycle: DashboardStudyCycleSummary,
        blueprint: DashboardSimuladoBlueprintSummary,
        dashboard_state: str,
    ) -> str:
        if materials.total_materials == 0:
            return "No materials uploaded yet."
        if dashboard_state == "blocked_by_ocr":
            return "Some materials still require OCR before the study pipeline can advance safely."
        if dashboard_state == "blocked_by_materials":
            return "Material gaps are still blocking parts of the study pipeline."
        if blueprint.blueprint_available:
            return "Study cycle and simulado blueprint are available for review."
        if cycle.cycle_available:
            return "Study cycle is available, but the simulado blueprint still needs attention."
        if alignment.alignment_available:
            return (
                f"You have {materials.total_materials} uploaded materials and bibliography alignment is available, "
                "but later planning artifacts are still missing."
            )
        if edital.edital_available:
            return "Edital mapping is available, but bibliography alignment is still missing."
        return f"You have {materials.total_materials} uploaded materials and document processing is still in progress."

    def _generated_at(
        self,
        user: User | None,
        materials: list[UploadedMaterial],
        pipeline_states: Iterable[object],
        edital: EditalExtractionResult | None,
        alignment: BibliographyAlignmentResult | None,
        graph: CurriculumGraph | None,
        cycle: StudyCyclePlan | None,
        blueprint: SimuladoBlueprint | None,
        progress_last_activity: datetime | None,
    ) -> datetime | None:
        timestamps: list[datetime] = []
        if user is not None:
            if user.created_at:
                timestamps.append(user.created_at)
            if user.last_login_at:
                timestamps.append(user.last_login_at)
        for material in materials:
            if material.metadata.updated_at:
                timestamps.append(material.metadata.updated_at)
            elif material.metadata.created_at:
                timestamps.append(material.metadata.created_at)
        for state in pipeline_states:
            if getattr(state, "updated_at", None):
                timestamps.append(state.updated_at)
        for item in [edital, alignment, graph, cycle, blueprint]:
            if item is None:
                continue
            for attribute in ("updated_at", "created_at"):
                value = getattr(item, attribute, None)
                if isinstance(value, datetime):
                    timestamps.append(value)
        if progress_last_activity:
            timestamps.append(progress_last_activity)
        return max(timestamps) if timestamps else None

    def _pending_action_sort_key(self, action: DashboardPendingAction) -> tuple[int, int, str]:
        severity_rank = {"blocked": 0, "error": 1, "warning": 2, "info": 3}
        return (severity_rank.get(action.severity, 4), action.priority, action.action_id)
