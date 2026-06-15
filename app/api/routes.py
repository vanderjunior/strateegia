from __future__ import annotations

import re
import hashlib
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    AnswerSubmission as FeedbackAnswerSubmission,
    SessionAnswerRequest,
    StudyBlockAnswerReviewRequest,
    StudyProgressEventRequest,
    UserLoginRequest,
    UserRegisterRequest,
    SessionStartRequest,
)
from app.config import inspection_enabled, inspection_requires_auth
from app.domain.models import AnswerSubmission, BoardStyle, ProgressState
from app.repositories.json_store import JsonStudyRepository
from app.services.document_ingestion import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES, normalize_material_type
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
from app.services.aggregate_retention_observability import observe_aggregate_retention
from app.services.learning_engine import LearningDecisionEngine
from app.services.longitudinal_retention_observability import (
    observe_longitudinal_retention,
)
from app.services.manual_experiment_inspection import (
    build_manual_experiment_inspection,
)
from app.services.pipeline import StudyPipeline
from app.services.reviews import ReviewService
from app.services.session_flow import SessionManager
from app.services.material_service import MaterialService
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from app.services.exam_profiles import ExamProfileService
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from app.services.question_draft_generation import QuestionDraftGenerationService
from app.services.question_generation_blueprint import QuestionGenerationBlueprintService
from app.services.simulado_attempt_shell import SimuladoAttemptShellService
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
from app.services.simulado_attempt_session import SimuladoAttemptSessionService
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
from app.services.simulado_correction_result import SimuladoCorrectionResultService
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from app.services.simulado_execution_shell import SimuladoExecutionShellService
from app.services.simulado_final_approval import SimuladoFinalApprovalService
from app.services.simulado_finalization_guardrails import SimuladoFinalizationGuardrailsService
from app.services.simulado_question_assembly import SimuladoQuestionAssemblyService
from app.services.simulado_progress_guardrails import SimuladoProgressGuardrailsService
from app.services.simulado_scoring import SimuladoScoringService
from app.services.simulado_integrated_execution_correction import (
    SimuladoIntegratedExecutionCorrectionService,
)
from app.services.simulado_runtime_application_guardrails import (
    SimuladoRuntimeApplicationGuardrailsService,
)
from app.services.simulado_runtime_progress_application import (
    SimuladoRuntimeProgressApplicationService,
)
from app.services.simulado_controlled_apply_shell import (
    SimuladoControlledRuntimeApplyShellService,
)
from app.services.simulado_explicit_runtime_apply import (
    SimuladoExplicitRuntimeProgressApplyService,
)
from app.services.simulado_runtime_progress_mutation import (
    SimuladoRuntimeProgressMutationService,
)
from app.services.simulado_controlled_mutation_commit import (
    SimuladoControlledRuntimeMutationCommitService,
)
from app.services.simulado_explicit_mutation_commit import (
    SimuladoExplicitRuntimeMutationCommitService,
)
from app.services.simulado_runtime_mutation_commit_transaction import (
    SimuladoRuntimeMutationCommitTransactionService,
)
from app.services.simulado_controlled_commit_execution_guardrail import (
    SimuladoControlledRuntimeCommitExecutionGuardrailService,
)
from app.services.simulado_explicit_commit_execution_approval import (
    SimuladoExplicitRuntimeCommitExecutionApprovalService,
)
from app.services.simulado_runtime_commit_execution_plan import (
    SimuladoRuntimeCommitExecutionPlanService,
)
from app.services.simulado_controlled_runtime_commit_execution import (
    SimuladoControlledRuntimeCommitExecutionService,
)
from app.services.simulado_final_pedagogical_update_event import (
    SimuladoFinalPedagogicalUpdateEventService,
)
from app.services.simulado_runtime_apply_policy import SimuladoRuntimeApplyPolicyService
from app.services.simulado_minimal_progress_ledger_apply import (
    SimuladoMinimalProgressLedgerApplyService,
)
from app.services.simulado_applied_event_ledger import (
    SimuladoAppliedEventLedgerService,
)
from app.services.simulado_propagation_guardrail import (
    SimuladoPropagationGuardrailService,
)
from app.services.simulado_controlled_propagation_apply import (
    SimuladoControlledPropagationApplyService,
)
from app.services.snapshot_offline_io import export_inspection_snapshot
from app.services.scientific_tooling_contracts import (
    json_safe_profile,
    normalize_availability_state,
    safe_dict,
    safe_float,
    safe_list,
    scientific_payload_defaults,
)
from app.services.tuning_profile_benchmark_comparison import (
    compare_tuning_profiles_against_benchmark,
)
from app.services.user_dashboard import UserDashboardService
from app.services.user_service import LocalUserService


router = APIRouter(prefix="/api")

PERSONAL_STUDY_MVP_VERSION = "personal-study-mvp-v1"
GROUNDED_SUMMARY_GENERATOR_VERSION = "grounded-summary-v1"
GROUNDED_SUMMARY_GENERATION_METHOD = "deterministic_extractive"
GROUNDED_SUMMARY_MAX_SENTENCES = 5
GROUNDED_SUMMARY_MAX_CHARS = 960
GROUNDED_SUMMARY_MAX_KEY_POINTS = 7
GROUNDED_SUMMARY_MAX_SOURCE_ANCHORS = 5
GROUNDED_QUESTION_GENERATOR_VERSION = "grounded-question-v1"
GROUNDED_QUESTION_GENERATION_METHOD = "deterministic_source_transformation"
GROUNDED_QUESTION_MAX_ITEMS = 5
GROUNDED_QUESTION_MAX_PROMPT_CHARS = 240
GROUNDED_QUESTION_MAX_ALTERNATIVE_CHARS = 320
SESSION_COOKIE_NAME = "studyflow_session"
STUDY_PROGRESS_EVENT_TYPES = {
    "block_opened",
    "block_marked_studied",
    "question_reviewed",
    "review_opened",
    "review_completed",
}
STUDY_PROGRESS_TARGET_TYPES = {"block", "question", "review", "material"}
STUDY_PROGRESS_EVENT_TARGETS = {
    "block_opened": {"block"},
    "block_marked_studied": {"block"},
    "question_reviewed": {"question"},
    "review_opened": {"review"},
    "review_completed": {"review"},
}


def get_repository(request: Request) -> JsonStudyRepository:
    return request.app.state.repository


def get_pipeline(request: Request) -> StudyPipeline:
    return request.app.state.pipeline


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def get_user_service(request: Request) -> LocalUserService:
    return LocalUserService(get_repository(request))


def get_material_service(request: Request) -> MaterialService:
    return MaterialService(
        get_repository(request),
        storage_root=request.app.state.storage_root,
    )


def get_document_pipeline_service(request: Request) -> DocumentPipelineService:
    return DocumentPipelineService(
        get_repository(request),
        storage_root=request.app.state.storage_root,
    )


def get_edital_ingestion_service(request: Request) -> EditalIngestionService:
    return EditalIngestionService(get_repository(request))


def get_bibliography_alignment_service(request: Request) -> BibliographyAlignmentService:
    return BibliographyAlignmentService(get_repository(request))


def get_curriculum_graph_builder_service(request: Request) -> CurriculumGraphBuilderService:
    return CurriculumGraphBuilderService(get_repository(request))


def get_study_cycle_orchestrator_service(request: Request) -> StudyCycleOrchestratorService:
    return StudyCycleOrchestratorService(get_repository(request))


def get_exam_profile_service(request: Request) -> ExamProfileService:
    return ExamProfileService(get_repository(request))


def get_simulado_blueprint_builder_service(request: Request) -> SimuladoBlueprintBuilderService:
    return SimuladoBlueprintBuilderService(get_repository(request))


def get_user_dashboard_service(request: Request) -> UserDashboardService:
    return UserDashboardService(get_repository(request))


def get_question_generation_blueprint_service(request: Request) -> QuestionGenerationBlueprintService:
    return QuestionGenerationBlueprintService(get_repository(request))


def get_question_draft_generation_service(request: Request) -> QuestionDraftGenerationService:
    return QuestionDraftGenerationService(get_repository(request))


def get_answer_explanation_guardrail_service(request: Request) -> AnswerExplanationGuardrailService:
    return AnswerExplanationGuardrailService(get_repository(request))


def get_simulado_question_assembly_service(request: Request) -> SimuladoQuestionAssemblyService:
    return SimuladoQuestionAssemblyService(get_repository(request))


def get_simulado_attempt_shell_service(request: Request) -> SimuladoAttemptShellService:
    return SimuladoAttemptShellService(get_repository(request))


def get_simulado_finalization_guardrails_service(
    request: Request,
) -> SimuladoFinalizationGuardrailsService:
    return SimuladoFinalizationGuardrailsService(get_repository(request))


def get_simulado_final_approval_service(request: Request) -> SimuladoFinalApprovalService:
    return SimuladoFinalApprovalService(get_repository(request))


def get_simulado_execution_shell_service(request: Request) -> SimuladoExecutionShellService:
    return SimuladoExecutionShellService(get_repository(request))


def get_simulado_attempt_session_service(request: Request) -> SimuladoAttemptSessionService:
    return SimuladoAttemptSessionService(get_repository(request))


def get_simulado_answer_submission_service(request: Request) -> SimuladoAnswerSubmissionService:
    return SimuladoAnswerSubmissionService(get_repository(request))


def get_simulado_correction_shell_service(request: Request) -> SimuladoCorrectionShellService:
    return SimuladoCorrectionShellService(get_repository(request))


def get_simulado_answer_key_boundary_service(request: Request) -> SimuladoAnswerKeyBoundaryService:
    return SimuladoAnswerKeyBoundaryService(get_repository(request))


def get_simulado_correction_result_service(request: Request) -> SimuladoCorrectionResultService:
    return SimuladoCorrectionResultService(get_repository(request))


def get_simulado_scoring_service(request: Request) -> SimuladoScoringService:
    return SimuladoScoringService(get_repository(request))


def get_simulado_progress_guardrails_service(request: Request) -> SimuladoProgressGuardrailsService:
    return SimuladoProgressGuardrailsService(get_repository(request))


def get_simulado_integrated_execution_correction_service(
    request: Request,
) -> SimuladoIntegratedExecutionCorrectionService:
    return SimuladoIntegratedExecutionCorrectionService(get_repository(request))


def get_simulado_runtime_application_guardrails_service(
    request: Request,
) -> SimuladoRuntimeApplicationGuardrailsService:
    return SimuladoRuntimeApplicationGuardrailsService(get_repository(request))


def get_simulado_runtime_progress_application_service(
    request: Request,
) -> SimuladoRuntimeProgressApplicationService:
    return SimuladoRuntimeProgressApplicationService(get_repository(request))


def get_simulado_controlled_apply_shell_service(
    request: Request,
) -> SimuladoControlledRuntimeApplyShellService:
    return SimuladoControlledRuntimeApplyShellService(get_repository(request))


def get_simulado_explicit_runtime_apply_service(
    request: Request,
) -> SimuladoExplicitRuntimeProgressApplyService:
    return SimuladoExplicitRuntimeProgressApplyService(get_repository(request))


def get_simulado_runtime_progress_mutation_service(
    request: Request,
) -> SimuladoRuntimeProgressMutationService:
    return SimuladoRuntimeProgressMutationService(get_repository(request))


def get_simulado_controlled_mutation_commit_service(
    request: Request,
) -> SimuladoControlledRuntimeMutationCommitService:
    return SimuladoControlledRuntimeMutationCommitService(get_repository(request))


def get_simulado_explicit_mutation_commit_service(
    request: Request,
) -> SimuladoExplicitRuntimeMutationCommitService:
    return SimuladoExplicitRuntimeMutationCommitService(get_repository(request))


def get_simulado_runtime_mutation_commit_transaction_service(
    request: Request,
) -> SimuladoRuntimeMutationCommitTransactionService:
    return SimuladoRuntimeMutationCommitTransactionService(get_repository(request))


def get_simulado_controlled_commit_execution_guardrail_service(
    request: Request,
) -> SimuladoControlledRuntimeCommitExecutionGuardrailService:
    return SimuladoControlledRuntimeCommitExecutionGuardrailService(get_repository(request))


def get_simulado_explicit_commit_execution_approval_service(
    request: Request,
) -> SimuladoExplicitRuntimeCommitExecutionApprovalService:
    return SimuladoExplicitRuntimeCommitExecutionApprovalService(get_repository(request))


def get_simulado_runtime_commit_execution_plan_service(
    request: Request,
) -> SimuladoRuntimeCommitExecutionPlanService:
    return SimuladoRuntimeCommitExecutionPlanService(get_repository(request))


def get_simulado_controlled_runtime_commit_execution_service(
    request: Request,
) -> SimuladoControlledRuntimeCommitExecutionService:
    return SimuladoControlledRuntimeCommitExecutionService(get_repository(request))


def get_simulado_final_pedagogical_update_event_service(
    request: Request,
) -> SimuladoFinalPedagogicalUpdateEventService:
    return SimuladoFinalPedagogicalUpdateEventService(get_repository(request))


def get_simulado_runtime_apply_policy_service(
    request: Request,
) -> SimuladoRuntimeApplyPolicyService:
    return SimuladoRuntimeApplyPolicyService(get_repository(request))


def get_simulado_minimal_progress_ledger_apply_service(
    request: Request,
) -> SimuladoMinimalProgressLedgerApplyService:
    return SimuladoMinimalProgressLedgerApplyService(get_repository(request))


def get_simulado_applied_event_ledger_service(
    request: Request,
) -> SimuladoAppliedEventLedgerService:
    return SimuladoAppliedEventLedgerService(get_repository(request))


def get_simulado_propagation_guardrail_service(
    request: Request,
) -> SimuladoPropagationGuardrailService:
    return SimuladoPropagationGuardrailService(get_repository(request))


def get_simulado_controlled_propagation_apply_service(
    request: Request,
) -> SimuladoControlledPropagationApplyService:
    return SimuladoControlledPropagationApplyService(get_repository(request))


def _auth_sessions(request: Request) -> dict[str, str]:
    return request.app.state.auth_sessions


def _current_user_id(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return _auth_sessions(request).get(token)


def _scoped_repository(request: Request):
    return get_repository(request).for_user(_current_user_id(request))


def _require_authenticated_user_id(request: Request) -> str:
    user_id = _current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user_id


def _public_user_payload(user) -> dict[str, object]:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "is_active": user.is_active,
    }


def require_inspection_access(request: Request) -> None:
    if not inspection_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    if inspection_requires_auth() and _current_user_id(request) is None:
        raise HTTPException(status_code=401, detail="Authentication required.")


def _inspection_defaults() -> dict[str, object]:
    registry = build_controlled_tuning_experiment_registry()
    comparison = compare_tuning_profiles_against_benchmark(registry=registry)
    manual = build_manual_experiment_inspection(
        registry=registry,
        comparison=comparison,
    )
    retention = observe_longitudinal_retention(
        progress=ProgressState(),
        runtime_block={},
    )
    aggregate_retention = observe_aggregate_retention(
        progress=ProgressState(),
        runtime_block={},
    )
    return scientific_payload_defaults(
        controlled_tuning_registry=registry,
        tuning_profile_benchmark_comparison=comparison,
        manual_experiment_inspection=manual,
        longitudinal_retention=retention,
        aggregate_retention=aggregate_retention,
    )


def _inspection_payload(
    session_manager: SessionManager,
    repository: JsonStudyRepository,
    *,
    user_id: str | None = None,
) -> dict[str, object]:
    payload = _inspection_defaults()
    progress = repository.load_progress(user_id=user_id)
    context = session_manager.latest_inspection_context(user_id=user_id)
    if context is None:
        payload["longitudinal_retention"] = json_safe_profile(
            observe_longitudinal_retention(
                progress=progress,
                runtime_block={},
            )
        )
        payload["aggregate_retention"] = json_safe_profile(
            observe_aggregate_retention(
                progress=progress,
                runtime_block={},
            )
        )
        return payload

    block = safe_dict(context.get("block"))
    payload["inspection_available"] = True
    payload["session"] = {
        "session_id": context.get("session_id"),
        "completed": context.get("completed"),
        "current_block_index": context.get("current_block_index"),
        "total_blocks": context.get("total_blocks", 0),
        "current_block_type": block.get("type"),
        "topic_id": block.get("topic_id"),
    }
    payload["benchmark_summary"] = {
        "pedagogical_benchmark_state": normalize_availability_state(
            block.get("pedagogical_benchmark_state"),
            "not_available",
        ),
        "pedagogical_benchmark_summary": block.get("pedagogical_benchmark_summary", ""),
        "benchmark_readiness": block.get("benchmark_readiness", "benchmark_insufficient"),
        "benchmark_alignment_score": safe_float(block.get("benchmark_alignment_score"), 0.0),
        "benchmark_regression_severity": normalize_availability_state(
            block.get("benchmark_regression_severity"),
            "none",
        ),
        "benchmark_total_cases": block.get("benchmark_total_cases", 0),
        "benchmark_passed_cases": safe_list(block.get("benchmark_passed_cases")),
        "benchmark_failed_cases": safe_list(block.get("benchmark_failed_cases")),
        "benchmark_inconclusive_cases": safe_list(block.get("benchmark_inconclusive_cases")),
        "benchmark_regression_cases": safe_list(block.get("benchmark_regression_cases")),
    }
    payload["benchmark_case_reports"] = safe_list(block.get("benchmark_case_reports"))
    payload["scientific_runtime_validation"] = {
        "scientific_validation_state": block.get("scientific_validation_state", ""),
        "runtime_benchmark_state": block.get("runtime_benchmark_state", ""),
        "regression_detection_state": block.get("regression_detection_state", ""),
        "sustainability_validation_state": block.get("sustainability_validation_state", ""),
        "cognitive_load_profile": block.get("cognitive_load_profile", ""),
        "retrieval_reliability_profile": block.get("retrieval_reliability_profile", ""),
        "scaffold_dependency_profile": block.get("scaffold_dependency_profile", ""),
        "compression_safety_profile": block.get("compression_safety_profile", ""),
        "stabilization_reliability_profile": block.get("stabilization_reliability_profile", ""),
        "continuity_reliability_profile": block.get("continuity_reliability_profile", ""),
    }
    payload["comparative_session_analytics"] = {
        "comparative_session_state": block.get("comparative_session_state", ""),
        "comparative_runtime_summary": block.get("comparative_runtime_summary", ""),
        "retrieval_delta": safe_float(block.get("retrieval_delta"), 0.0),
        "scaffold_delta": safe_float(block.get("scaffold_delta"), 0.0),
        "compression_delta": safe_float(block.get("compression_delta"), 0.0),
        "continuity_delta": safe_float(block.get("continuity_delta"), 0.0),
        "reconstruction_delta": safe_float(block.get("reconstruction_delta"), 0.0),
        "pacing_delta": safe_float(block.get("pacing_delta"), 0.0),
        "validation_delta": safe_float(block.get("validation_delta"), 0.0),
        "sustainability_delta": safe_float(block.get("sustainability_delta"), 0.0),
        "pedagogical_regression_signal": block.get("pedagogical_regression_signal", ""),
    }
    payload["session_export_debug"] = {
        "session_export_state": block.get("session_export_state", ""),
        "runtime_export_summary": block.get("runtime_export_summary", ""),
        "behavioral_diff_snapshot": safe_dict(block.get("behavioral_diff_snapshot")),
        "runtime_trace_snapshot": safe_dict(block.get("runtime_trace_snapshot")),
        "stability_snapshot": safe_dict(block.get("stability_snapshot")),
        "tuning_snapshot": safe_dict(block.get("tuning_snapshot")),
        "compression_snapshot": safe_dict(block.get("compression_snapshot")),
        "continuity_snapshot": safe_dict(block.get("continuity_snapshot")),
        "support_snapshot": safe_dict(block.get("support_snapshot")),
        "retrieval_snapshot": safe_dict(block.get("retrieval_snapshot")),
        "reconstruction_snapshot": safe_dict(block.get("reconstruction_snapshot")),
    }
    payload["stability_metrics"] = {
        "session_stability_state": block.get("session_stability_state", ""),
        "retrieval_density_metric": safe_float(block.get("retrieval_density_metric"), 0.0),
        "scaffold_load_metric": safe_float(block.get("scaffold_load_metric"), 0.0),
        "continuity_smoothness_metric": safe_float(block.get("continuity_smoothness_metric"), 0.0),
        "reconstruction_pressure_metric": safe_float(block.get("reconstruction_pressure_metric"), 0.0),
        "compression_safety_metric": safe_float(block.get("compression_safety_metric"), 0.0),
        "pacing_stability_metric": safe_float(block.get("pacing_stability_metric"), 0.0),
        "cognitive_balance_metric": safe_float(block.get("cognitive_balance_metric"), 0.0),
    }
    payload["validation_dataset_awareness"] = {
        "validation_dataset_state": block.get("validation_dataset_state", ""),
        "pedagogical_scenario_family": block.get("pedagogical_scenario_family", ""),
        "runtime_validation_context": block.get("runtime_validation_context", ""),
        "comparative_validation_alignment": safe_float(
            block.get("comparative_validation_alignment"),
            0.0,
        ),
        "dataset_awareness_summary": block.get("dataset_awareness_summary", ""),
    }
    registry = build_controlled_tuning_experiment_registry()
    payload["controlled_tuning_registry"] = json_safe_profile(registry)
    comparison = compare_tuning_profiles_against_benchmark(
        registry=registry,
        benchmark_result={"benchmark_case_reports": safe_list(block.get("benchmark_case_reports"))},
    )
    payload["tuning_profile_benchmark_comparison"] = json_safe_profile(comparison)
    payload["manual_experiment_inspection"] = json_safe_profile(
        build_manual_experiment_inspection(
            registry=registry,
            comparison=comparison,
        )
    )
    payload["longitudinal_retention"] = json_safe_profile(
        observe_longitudinal_retention(
            progress=progress,
            runtime_block=block,
        )
    )
    payload["aggregate_retention"] = json_safe_profile(
        observe_aggregate_retention(
            progress=progress,
            runtime_block=block,
        )
    )
    payload["raw_runtime_block"] = json_safe_profile(block)
    return payload


def _record_feedback_answer(
    repository: JsonStudyRepository,
    submission: FeedbackAnswerSubmission,
) -> bool:
    is_correct = submission.user_answer == submission.correct_answer
    if not is_correct and submission.error_type is None:
        raise HTTPException(
            status_code=400,
            detail="error_type is required for incorrect answers.",
        )
    repository.register_answer(
        topic_id=submission.topic_id,
        question_id=submission.question_id,
        microtopic_id=submission.microtopic_id,
        pedagogical_mode=submission.pedagogical_mode,
        is_correct=is_correct,
        error_type=submission.error_type if not is_correct else None,
    )
    return is_correct


@router.post("/documents/upload", status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    board: BoardStyle = Form(...),
    exam_context: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="O arquivo enviado precisa ser um PDF.")

    payload = await file.read()
    document = get_pipeline(request).process_pdf(
        filename=file.filename,
        payload=payload,
        board=board,
        exam_context=exam_context,
    )
    _scoped_repository(request).save_document(document)
    return document


@router.get("/documents")
def list_documents(request: Request):
    return _scoped_repository(request).list_documents()


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request):
    document = _scoped_repository(request).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento nao encontrado.")
    return document


@router.post("/questions/{question_id}/answer")
def submit_answer(question_id: str, submission: AnswerSubmission, request: Request):
    if submission.question_id != question_id:
        raise HTTPException(status_code=400, detail="Question ID inconsistente.")
    _scoped_repository(request).record_answer(submission)
    return {"status": "recorded"}


@router.post("/answers/submit")
def submit_feedback_answer(submission: FeedbackAnswerSubmission, request: Request):
    is_correct = _record_feedback_answer(_scoped_repository(request), submission)
    return {
        "correct": is_correct,
        "message": "Answer recorded",
    }


@router.post("/auth/register", status_code=201)
def register_user(payload: UserRegisterRequest, request: Request):
    try:
        user = get_user_service(request).register_user(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _public_user_payload(user)


@router.post("/auth/login")
def login_user(payload: UserLoginRequest, request: Request, response: Response):
    user = get_user_service(request).authenticate(
        username=payload.username,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = user.user_id + "." + user.username
    _auth_sessions(request)[token] = user.user_id
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
    )
    return {"authenticated": True, "user": _public_user_payload(user)}


@router.post("/auth/logout")
def logout_user(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        _auth_sessions(request).pop(token, None)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"authenticated": False, "user": None}


@router.get("/auth/me")
def current_user(request: Request):
    user_id = _current_user_id(request)
    if user_id is None:
        return {"authenticated": False, "user": None}
    user = get_repository(request).get_user(user_id)
    if user is None or not user.is_active:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": _public_user_payload(user)}


def _material_content_type_label(content_type: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    normalized = content_type.lower()
    if "pdf" in normalized or suffix == ".pdf":
        return "pdf"
    if "markdown" in normalized or suffix == ".md":
        return "md"
    if "text/plain" in normalized or suffix == ".txt":
        return "txt"
    return "unknown"


def _material_display_filename(original_filename: str, stored_filename: str) -> str:
    candidate = original_filename or stored_filename
    normalized = candidate.replace("\\", "/").split("/")[-1].strip()
    if not normalized or normalized in {".", ".."}:
        return stored_filename
    return normalized


def _material_requires_ocr(extraction, pipeline_state) -> bool:
    if extraction is not None and (
        bool(extraction.metadata.get("requires_ocr")) or "ocr_required" in extraction.warnings
    ):
        return True
    if pipeline_state is not None and "ocr" in pipeline_state.extraction_status.lower():
        return True
    return False


def _material_type_from_metadata(metadata) -> str:
    candidates = [
        metadata.metadata.get("material_type"),
        getattr(metadata, "material_type", None),
        metadata.metadata.get("upload_intent"),
    ]
    for candidate in candidates:
        try:
            normalized = normalize_material_type(str(candidate or ""))
        except ValueError:
            continue
        if normalized != "unknown":
            return normalized
    return "unknown"


def _bounded_material_item(material, repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    metadata = material.metadata
    document_id = metadata.document_id
    pipeline_state = repository.get_document_pipeline_state(document_id, user_id=user_id)
    extraction = repository.get_document_extraction_result(document_id, user_id=user_id)
    requires_ocr = _material_requires_ocr(extraction, pipeline_state)
    current_stage = pipeline_state.current_stage if pipeline_state is not None else metadata.status
    extraction_status = pipeline_state.extraction_status if pipeline_state is not None else metadata.extraction_status
    metadata_status = pipeline_state.metadata_status if pipeline_state is not None else "not_ready"
    chunk_count = pipeline_state.chunk_count if pipeline_state is not None else 0
    section_count = pipeline_state.section_count if pipeline_state is not None else 0
    material_type = _material_type_from_metadata(metadata)

    if requires_ocr:
        processing_status = "ocr_required"
        safe_extraction_status = "ocr_required"
        review_state = "needs_review"
    elif metadata_status in {"ready", "metadata_ready"} or current_stage == "metadata_ready":
        processing_status = "ready_for_review"
        safe_extraction_status = "extracted"
        review_state = "ready_for_review"
    elif extraction_status in {"extracted", "chunked", "sectioned", "metadata_ready"}:
        processing_status = "text_extracted"
        safe_extraction_status = (
            "textual_pdf"
            if _material_content_type_label(metadata.content_type, metadata.filename) == "pdf"
            else "extracted"
        )
        review_state = "needs_review"
    elif extraction_status in {"pending_extraction", "extraction_pending"} or current_stage in {
        "uploaded",
        "pending_extraction",
        "extraction_pending",
        "extraction_started",
    }:
        processing_status = "extraction_pending"
        safe_extraction_status = "pending"
        review_state = "pending"
    elif metadata.status == "uploaded":
        processing_status = "uploaded"
        safe_extraction_status = "pending"
        review_state = "pending"
    else:
        processing_status = "unknown"
        safe_extraction_status = "unknown"
        review_state = "unknown"

    warnings_count = 0
    if extraction is not None:
        warnings_count += len(extraction.warnings)
    if pipeline_state is not None:
        warnings_count += pipeline_state.error_count
    if metadata.error_message:
        warnings_count += 1

    return {
        "document_id": document_id,
        "display_filename": _material_display_filename(metadata.original_filename, metadata.filename),
        "content_type": _material_content_type_label(metadata.content_type, metadata.filename),
        "material_type": material_type,
        "created_at": metadata.created_at,
        "updated_at": metadata.updated_at,
        "processing_status": processing_status,
        "extraction_status": safe_extraction_status,
        "chunk_count": chunk_count,
        "section_count": section_count,
        "review_state": review_state,
        "warnings_count": warnings_count,
        "latest_pipeline_status": current_stage or None,
    }


@router.get("/materials")
def list_materials(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    items = [
        _bounded_material_item(material, repository, user_id)
        for material in repository.list_uploaded_materials(user_id=user_id)
    ]
    items.sort(
        key=lambda item: (
            item["updated_at"] or item["created_at"],
            item["display_filename"],
            item["document_id"],
        ),
        reverse=True,
    )
    return {
        "items": items,
        "count": len(items),
        "source": "user_scope",
    }


@router.post("/materials/upload", status_code=201)
async def upload_material(
    request: Request,
    file: UploadFile = File(...),
    material_type: str | None = Form(default=None),
):
    user_id = _require_authenticated_user_id(request)
    original_name = file.filename or "material"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported material type.")
    payload = await file.read()
    if len(payload) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Upload size exceeds the supported limit.")
    try:
        normalized_material_type = normalize_material_type(material_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    material = get_material_service(request).register_upload(
        user_id=user_id,
        original_filename=original_name,
        content_type=file.content_type or "",
        payload=payload,
        material_type=normalized_material_type,
    )
    return material


@router.post("/materials/{document_id}/process")
def process_material(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    try:
        return get_document_pipeline_service(request).process_document(document_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Material not found.") from exc


def _bounded_material_pipeline_summary(material, repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    document_id = material.metadata.document_id
    pipeline_state = repository.get_document_pipeline_state(document_id, user_id=user_id)
    extraction = repository.get_document_extraction_result(document_id, user_id=user_id)
    has_ocr_warning = _material_requires_ocr(extraction, pipeline_state)
    status = pipeline_state.current_stage if pipeline_state is not None else material.metadata.status
    ready_for_review = False
    if pipeline_state is not None:
        ready_for_review = (
            pipeline_state.current_stage == "metadata_ready"
            or pipeline_state.metadata_status in {"ready", "metadata_ready"}
        )

    return {
        "status": status or None,
        "steps_count": len(pipeline_state.stages_completed) if pipeline_state is not None else 0,
        "has_ocr_warning": has_ocr_warning,
        "ready_for_review": ready_for_review,
    }


def _bounded_material_pipeline_status(
    material_summary: dict[str, object],
    pipeline_summary: dict[str, object],
) -> str:
    if pipeline_summary["has_ocr_warning"] or material_summary["extraction_status"] == "ocr_required":
        return "ocr_required"
    if pipeline_summary["ready_for_review"] or material_summary["review_state"] == "ready_for_review":
        return "ready_for_review"
    if material_summary["section_count"] > 0 or material_summary["chunk_count"] > 0:
        return "segmented"
    if material_summary["processing_status"] == "text_extracted" or material_summary["extraction_status"] in {
        "textual_pdf",
        "extracted",
    }:
        return "text_extracted"
    if material_summary["processing_status"] in {"uploaded", "extraction_pending"}:
        return "pending"
    return "unknown"


def _bounded_material_pipeline_step(
    *,
    key: str,
    label: str,
    state: str,
    warnings_count: int = 0,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "state": state,
        "warnings_count": warnings_count,
    }


def _bounded_material_pipeline_steps(
    material_summary: dict[str, object],
    pipeline_summary: dict[str, object],
) -> list[dict[str, object]]:
    has_ocr_warning = bool(pipeline_summary["has_ocr_warning"])
    ready_for_review = bool(pipeline_summary["ready_for_review"])
    chunk_count = int(material_summary["chunk_count"])
    section_count = int(material_summary["section_count"])
    warnings_count = int(material_summary["warnings_count"])
    extraction_status = str(material_summary["extraction_status"])
    processing_status = str(material_summary["processing_status"])

    has_extracted_text = extraction_status in {"textual_pdf", "extracted"} or processing_status in {
        "text_extracted",
        "ready_for_review",
    }
    has_segments = chunk_count > 0 or section_count > 0

    return [
        _bounded_material_pipeline_step(
            key="uploaded",
            label="Enviado",
            state="done",
        ),
        _bounded_material_pipeline_step(
            key="text_extracted",
            label="Texto extraído",
            state="needs_review" if has_ocr_warning else "done" if has_extracted_text else "pending",
            warnings_count=warnings_count if has_ocr_warning else 0,
        ),
        _bounded_material_pipeline_step(
            key="segmented",
            label="Segmentado",
            state="done" if has_segments else "pending",
        ),
        _bounded_material_pipeline_step(
            key="ready_for_review",
            label="Pronto para revisão",
            state="done" if ready_for_review else "needs_review" if has_ocr_warning else "pending",
            warnings_count=warnings_count if not ready_for_review else 0,
        ),
    ]


@router.get("/materials/{document_id}/summary")
def get_material_summary(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    material = repository.get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    summary = _bounded_material_item(material, repository, user_id)
    return {
        **summary,
        "pipeline": _bounded_material_pipeline_summary(material, repository, user_id),
        "source": "user_scope",
    }


@router.get("/materials/{document_id}/pipeline/summary")
def get_material_pipeline_summary(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    material = repository.get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    material_summary = _bounded_material_item(material, repository, user_id)
    pipeline_summary = _bounded_material_pipeline_summary(material, repository, user_id)
    steps = _bounded_material_pipeline_steps(material_summary, pipeline_summary)
    return {
        "document_id": document_id,
        "status": _bounded_material_pipeline_status(material_summary, pipeline_summary),
        "steps": steps,
        "steps_count": len(steps),
        "has_ocr_warning": pipeline_summary["has_ocr_warning"],
        "ready_for_review": pipeline_summary["ready_for_review"],
        "section_count": material_summary["section_count"],
        "chunk_count": material_summary["chunk_count"],
        "warnings_count": material_summary["warnings_count"],
        "source": "user_scope",
    }


@router.get("/materials/{document_id}/pipeline")
def get_material_pipeline(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    state = get_repository(request).get_document_pipeline_state(document_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Pipeline state not found.")
    return state


@router.get("/materials/{document_id}/chunks")
def get_material_chunks(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return get_repository(request).list_document_chunks(document_id, user_id=user_id)


@router.get("/materials/{document_id}/sections")
def get_material_sections(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return get_repository(request).list_document_sections(document_id, user_id=user_id)


def _uploaded_material_type(material) -> str:
    return _material_type_from_metadata(material.metadata)


def _bounded_edital_analysis_status(edital, ingestion_state, review_state: str) -> str:
    if ingestion_state is not None:
        if ingestion_state.status == "insufficient_text":
            return "not_ready"
        if ingestion_state.status == "failed":
            return "failed"
        if ingestion_state.status in {"pending", "started"}:
            return "not_ready"
    if review_state == "ready_for_review":
        return "analyzed"
    if review_state == "needs_review":
        return "needs_review"
    return "not_ready"


def _bounded_edital_analysis_response(edital, repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    summary = _bounded_edital_item(edital, repository, user_id)
    return {
        "edital_id": summary["edital_id"],
        "document_id": summary["document_id"],
        "analysis_status": summary["analysis_status"],
        "review_state": summary["review_state"],
        "topics_count": summary["topics_count"],
        "subtopics_count": summary["subtopics_count"],
        "bibliography_count": summary["bibliography_count"],
        "gaps_count": summary["gaps_count"],
        "warnings_count": summary["warnings_count"],
        "source": "user_scope",
    }


def _can_prepare_edital_material_without_ocr(material) -> bool:
    suffix = str(
        material.metadata.metadata.get("extension") or Path(material.metadata.filename).suffix
    ).lower()
    return suffix in {".txt", ".md", ".pdf"}


def _bounded_study_material_preparation_response(
    material,
    repository: JsonStudyRepository,
    user_id: str,
) -> dict[str, object]:
    document_id = material.metadata.document_id
    summary = _bounded_material_item(material, repository, user_id)
    pipeline_summary = _bounded_material_pipeline_summary(material, repository, user_id)
    extraction = repository.get_document_extraction_result(document_id, user_id=user_id)

    section_count = int(summary["section_count"])
    chunk_count = int(summary["chunk_count"])
    warnings_count = int(summary["warnings_count"])
    pipeline_status = str(pipeline_summary["status"] or "")
    has_safe_text = extraction is not None and bool((extraction.text or "").strip())

    if pipeline_status in {"failed", "unsupported"} or str(summary["processing_status"]) == "unknown":
        preparation_status = "failed"
    elif bool(pipeline_summary["has_ocr_warning"]) or str(summary["extraction_status"]) == "ocr_required":
        preparation_status = "not_ready"
    elif has_safe_text and section_count > 0 and chunk_count > 0:
        preparation_status = "ready_for_study"
    elif has_safe_text:
        preparation_status = "needs_review"
    else:
        preparation_status = "not_ready"

    return {
        "document_id": document_id,
        "preparation_status": preparation_status,
        "material_type": "study_material",
        "section_count": section_count,
        "chunk_count": chunk_count,
        "warnings_count": warnings_count,
        "ready_for_study": preparation_status == "ready_for_study",
        "source": "user_scope",
    }


def _bounded_study_summary_title(value: object, fallback: str = "Material de estudo") -> str:
    title = " ".join(str(value or "").split())
    unsafe_markers = ("storage_path", "/Users/", "C:\\", "password_hash", "studyflow_session")
    if any(marker.lower() in title.lower() for marker in unsafe_markers):
        return fallback
    if not title:
        return fallback
    return title[:120]


SOURCE_LEAK_MARKERS = (
    "should-not-leak",
    "raw-",
    "raw text",
    "extracted_text",
    "chunk body",
    "section body",
    "storage_path",
    "answer_key",
    "correct_answer",
    "correct_alternative",
    "gabarito",
    "is_correct",
    "solution",
    "rationale",
    "correction",
    "score",
    "token",
    "cookie",
    "password_hash",
    "studyflow_session",
    "session token",
    "/users/",
    "c:\\",
)

SUMMARY_ALWAYS_NOISE_MARKERS = (
    "todos os direitos reservados",
    "all rights reserved",
    "copyright",
    "www.",
    "http://",
    "https://",
)

SUMMARY_SHORT_NOISE_PREFIXES = (
    "sumario",
    "sumário",
    "indice",
    "índice",
    "pagina",
    "página",
)

SUMMARY_DANGLING_REFERENCE_MARKERS = (
    "conforme acima",
    "como visto acima",
    "conforme mencionado anteriormente",
    "como visto anteriormente",
)


def _safe_source_sentence(value: object, *, limit: int = 360) -> str | None:
    sentence = " ".join(str(value or "").split())
    if len(sentence) < 12:
        return None
    lowered = sentence.lower()
    if any(marker in lowered for marker in SOURCE_LEAK_MARKERS):
        return None
    return sentence[:limit]


def _split_source_sentences(text: str) -> list[str]:
    normalized = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    pieces = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    sentences: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        sentence = _safe_source_sentence(piece)
        if sentence is None:
            continue
        key = _normalize_study_text(sentence)
        if key in seen:
            continue
        seen.add(key)
        sentences.append(sentence)
    return sentences


def _normalize_study_text(value: object) -> str:
    lowered = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    lowered = lowered.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _study_term_tokens(*values: object) -> set[str]:
    ignored = {
        "para",
        "como",
        "este",
        "esta",
        "esse",
        "essa",
        "material",
        "estudo",
        "aula",
        "secao",
        "seção",
        "document",
        "conteudo",
        "conteúdo",
    }
    tokens: set[str] = set()
    for value in values:
        for token in _normalize_study_text(value).split():
            if len(token) >= 4 and token not in ignored:
                tokens.add(token)
    return tokens


def _sentence_score(sentence: str, terms: set[str]) -> int:
    normalized = _normalize_study_text(sentence)
    score = sum(3 for term in terms if term in normalized)
    pedagogical_markers = (
        "define",
        "consiste",
        "deve",
        "podera",
        "poderá",
        "quando",
        "exceto",
        "salvo",
        "inclui",
        "classifica",
        "objetivo",
        "regra",
        "condicao",
        "condição",
        "causa",
        "efeito",
    )
    score += sum(1 for marker in pedagogical_markers if marker in normalized)
    if 60 <= len(sentence) <= 260:
        score += 2
    return score


def _summary_source_fingerprint(
    *,
    material_id: str,
    section_id: str,
    title: str,
    chunks: list[object],
) -> str:
    source_text = "\n".join(
        _normalize_study_text(getattr(chunk, "text", ""))
        for chunk in sorted(chunks, key=lambda item: getattr(item, "chunk_index", 0))
    )
    identity = "|".join(
        (
            material_id,
            section_id,
            _normalize_study_text(title),
            source_text,
            GROUNDED_SUMMARY_GENERATOR_VERSION,
            str(GROUNDED_SUMMARY_MAX_SENTENCES),
            str(GROUNDED_SUMMARY_MAX_CHARS),
            str(GROUNDED_SUMMARY_MAX_KEY_POINTS),
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _is_summary_noise(sentence: str, *, title: str) -> bool:
    normalized = _normalize_study_text(sentence)
    if not normalized or normalized == _normalize_study_text(title):
        return True
    if len(normalized) < 12 or len(normalized.split()) < 2:
        return True
    if re.fullmatch(r"(?:pagina\s*)?\d+(?:\s+de\s+\d+)?", normalized):
        return True
    if any(marker in normalized for marker in SUMMARY_ALWAYS_NOISE_MARKERS):
        return True
    if len(normalized) <= 80 and normalized.startswith(SUMMARY_SHORT_NOISE_PREFIXES):
        return True
    if any(marker in normalized for marker in SUMMARY_DANGLING_REFERENCE_MARKERS) and len(normalized) < 120:
        return True
    return False


def _summary_statement_candidates(
    *,
    title: str,
    chunks: list[object],
    terms: set[str],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    seen: set[str] = set()
    for chunk in sorted(chunks, key=lambda item: getattr(item, "chunk_index", 0)):
        raw_text = str(getattr(chunk, "text", "") or "")
        pieces = re.split(r"(?<=[.!?])\s+|\n+", raw_text)
        for sentence_index, piece in enumerate(pieces):
            cleaned = re.sub(r"^\s*(?:[-*•]|\d+[\.\)])\s+", "", piece).strip()
            sentence = _safe_source_sentence(cleaned, limit=1000)
            if sentence is None or len(sentence) > 320 or _is_summary_noise(sentence, title=title):
                continue
            normalized = _normalize_study_text(sentence)
            if normalized in seen:
                continue
            seen.add(normalized)
            score = _sentence_score(sentence, terms)
            if re.match(r"^\s*(?:[-*•]|\d+[\.\)])\s+", piece):
                score += 2
            candidates.append(
                {
                    "text": sentence,
                    "score": score,
                    "source_order": (int(getattr(chunk, "chunk_index", 0)), sentence_index),
                    "anchor": {
                        "chunk_id": str(getattr(chunk, "chunk_id", "")),
                        "chunk_index": int(getattr(chunk, "chunk_index", 0)),
                        "sentence_index": sentence_index,
                        "excerpt_fingerprint": hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16],
                        "page_start": getattr(chunk, "page_start", None),
                        "page_end": getattr(chunk, "page_end", None),
                    },
                }
            )
    return candidates


def _select_summary_statements(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            -int(item["score"]),
            item["source_order"],
            str(item["text"]),
        ),
    )
    selected: list[dict[str, object]] = []
    current_length = 0
    for candidate in ranked:
        sentence = str(candidate["text"])
        added_length = len(sentence) + (1 if selected else 0)
        if current_length + added_length > GROUNDED_SUMMARY_MAX_CHARS:
            continue
        selected.append(candidate)
        current_length += added_length
        if len(selected) >= GROUNDED_SUMMARY_MAX_SENTENCES:
            break
    return sorted(selected, key=lambda item: item["source_order"])


def _extractive_study_summary(
    *,
    material_id: str,
    section_id: str,
    title: str,
    chunks: list[object],
    topic_label: object | None = None,
    subtopic_label: object | None = None,
) -> dict[str, object]:
    content_fingerprint = _summary_source_fingerprint(
        material_id=material_id,
        section_id=section_id,
        title=title,
        chunks=chunks,
    )
    terms = _study_term_tokens(title, topic_label, subtopic_label)
    candidates = _summary_statement_candidates(title=title, chunks=chunks, terms=terms)
    selected = _select_summary_statements(candidates)
    if not selected:
        return {
            "summary": "Conteúdo insuficiente para montar um resumo confiável desta seção.",
            "key_points": [],
            "status": "needs_review",
            "source_anchors": [],
            "content_fingerprint": content_fingerprint,
        }
    selected_sentences = [str(item["text"]) for item in selected]
    key_points = selected_sentences[:GROUNDED_SUMMARY_MAX_KEY_POINTS]
    return {
        "summary": " ".join(selected_sentences),
        "key_points": key_points,
        "status": "ready",
        "source_anchors": [
            dict(item["anchor"])
            for item in selected[:GROUNDED_SUMMARY_MAX_SOURCE_ANCHORS]
        ],
        "content_fingerprint": content_fingerprint,
    }


def _bounded_study_summary_item(
    section,
    chunks: list[object],
    *,
    material_id: str,
    topic_label: object | None = None,
    subtopic_label: object | None = None,
) -> dict[str, object]:
    title = _bounded_study_summary_title(section.title, fallback="Seção sem título")
    has_specific_title = title.lower() not in {"document", "seção sem título", "section"}
    estimated_minutes = max(3, min(20, max(1, len(chunks)) * 5))
    grounded = _extractive_study_summary(
        material_id=material_id,
        section_id=str(section.section_id),
        title=title,
        chunks=chunks,
        topic_label=topic_label,
        subtopic_label=subtopic_label,
    )
    status = "ready" if has_specific_title and grounded["status"] == "ready" else "needs_review"
    return {
        "section_id": section.section_id,
        "title": title,
        "summary": str(grounded["summary"]),
        "key_points": list(grounded["key_points"]) if has_specific_title else [],
        "estimated_minutes": estimated_minutes,
        "status": status,
        "source_material_id": material_id,
        "source_section_id": str(section.section_id),
        "source_anchors": list(grounded["source_anchors"]) if has_specific_title else [],
        "content_fingerprint": str(grounded["content_fingerprint"]),
        "generator_version": GROUNDED_SUMMARY_GENERATOR_VERSION,
        "generation_method": GROUNDED_SUMMARY_GENERATION_METHOD,
    }


def _bounded_study_material_summary_response(
    material,
    repository: JsonStudyRepository,
    user_id: str,
) -> dict[str, object]:
    document_id = material.metadata.document_id
    preparation = _bounded_study_material_preparation_response(material, repository, user_id)
    warnings_count = int(preparation["warnings_count"])
    sections = sorted(
        repository.list_document_sections(document_id, user_id=user_id),
        key=lambda section: (section.order_index, section.section_id),
    )
    chunks = repository.list_document_chunks(document_id, user_id=user_id)
    chunks_by_section: dict[str, list[object]] = {}
    for chunk in chunks:
        if chunk.section_id:
            chunks_by_section.setdefault(chunk.section_id, []).append(chunk)

    if preparation["preparation_status"] in {"not_ready", "failed"} or not sections:
        summary_status = "not_ready" if preparation["preparation_status"] != "failed" else "failed"
        items: list[dict[str, object]] = []
    else:
        items = [
            _bounded_study_summary_item(
                section,
                sorted(
                    chunks_by_section.get(section.section_id, []),
                    key=lambda chunk: getattr(chunk, "chunk_index", 0),
                ),
                material_id=document_id,
            )
            for section in sections
        ]
        has_ready_item = any(item["status"] == "ready" for item in items)
        summary_status = "ready" if has_ready_item and warnings_count == 0 else "needs_review"

    return {
        "document_id": document_id,
        "summary_status": summary_status,
        "material_type": "study_material",
        "title": _bounded_study_summary_title(
            _material_display_filename(material.metadata.original_filename, material.metadata.filename),
            fallback="Material de estudo",
        ),
        "sections_count": len(sections),
        "items": items,
        "warnings_count": warnings_count,
        "source": "user_scope",
    }


def _bounded_study_session_action(label: str, href: str) -> dict[str, object]:
    return {
        "label": label,
        "href": href,
    }


def _has_analyzed_edital_for_study(repository: JsonStudyRepository, user_id: str) -> bool:
    for edital in repository.list_user_edital_extractions(user_id=user_id):
        summary = _bounded_edital_item(edital, repository, user_id)
        if summary["analysis_status"] == "analyzed" and summary["review_state"] == "ready_for_review":
            return True
    return False


def _not_ready_study_session_response() -> dict[str, object]:
    return {
        "session_status": "not_ready",
        "message": "Envie e prepare um material de estudo para começar.",
        "next_actions": [
            _bounded_study_session_action("Enviar material", "/materials/upload"),
            _bounded_study_session_action("Ver materiais", "/materials"),
        ],
        "source": "user_scope",
    }


def _bounded_next_study_session_response(
    summary: dict[str, object],
    repository: JsonStudyRepository,
    user_id: str,
) -> dict[str, object]:
    document_id = str(summary["document_id"])
    items = list(summary["items"])
    estimated_minutes = sum(int(item["estimated_minutes"]) for item in items)
    session_status = "ready" if summary["summary_status"] == "ready" else "needs_review"
    has_analyzed_edital = _has_analyzed_edital_for_study(repository, user_id)
    message = (
        "Comece por este material preparado."
        if has_analyzed_edital
        else "Este estudo ainda não está conectado completamente ao edital."
    )

    return {
        "session_status": session_status,
        "session_id": f"study-session:{document_id}",
        "document_id": document_id,
        "material_title": summary["title"],
        "material_type": "study_material",
        "summary_status": summary["summary_status"],
        "estimated_minutes": estimated_minutes,
        "sections_count": int(summary["sections_count"]),
        "items": items,
        "next_actions": [
            _bounded_study_session_action("Abrir material", f"/materials/{document_id}"),
            _bounded_study_session_action("Ver materiais", "/materials"),
        ],
        "message": message,
        "source": "user_scope",
    }


def _not_ready_study_blocks_response() -> dict[str, object]:
    return {
        "blocks_status": "not_ready",
        "scope_status": "not_ready",
        "blocks_count": 0,
        "estimated_minutes": 0,
        "items": [],
        "message": "Envie e prepare um material de estudo para montar seus blocos.",
        "source": "user_scope",
    }


def _study_blocks_candidate_edital(repository: JsonStudyRepository, user_id: str):
    candidates = []
    for edital in repository.list_user_edital_extractions(user_id=user_id):
        summary = _bounded_edital_item(edital, repository, user_id)
        if summary["analysis_status"] not in {"analyzed", "needs_review"}:
            continue
        if not edital.topics and not edital.subtopics:
            continue
        status_rank = 0 if summary["analysis_status"] == "analyzed" else 1
        review_rank = 0 if summary["review_state"] == "ready_for_review" else 1
        candidates.append((status_rank, review_rank, edital.document_id, edital))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0][3]


def _study_blocks_match_edital_scope(edital, value: str) -> dict[str, object] | None:
    value_tokens = _coverage_tokens(value)
    if not value_tokens:
        return None

    topics = sorted(edital.topics, key=lambda item: (item.order_index, item.topic_id))
    subtopics_by_topic: dict[str, list[object]] = {}
    for subtopic in edital.subtopics:
        subtopics_by_topic.setdefault(subtopic.parent_topic_id, []).append(subtopic)

    best: tuple[int, int, int, object, object | None] | None = None
    for topic in topics:
        topic_tokens = _coverage_tokens(topic.title)
        subtopics = sorted(
            subtopics_by_topic.get(topic.topic_id, []),
            key=lambda item: (item.order_index, item.subtopic_id),
        )
        if not subtopics:
            score = len(value_tokens & topic_tokens)
            if score:
                candidate = (score, topic.order_index, 0, topic, None)
                if best is None or (score, -topic.order_index, 0) > (best[0], -best[1], -best[2]):
                    best = candidate
            continue
        for subtopic in subtopics:
            subtopic_tokens = _coverage_tokens(subtopic.title)
            score = len(value_tokens & topic_tokens) + (len(value_tokens & subtopic_tokens) * 2)
            if not score:
                continue
            candidate = (score, topic.order_index, subtopic.order_index, topic, subtopic)
            if best is None or (score, -topic.order_index, -subtopic.order_index) > (best[0], -best[1], -best[2]):
                best = candidate

    if best is None:
        return None

    _, topic_order, subtopic_order, topic, subtopic = best
    return {
        "topic_id": topic.topic_id,
        "topic_label": _bounded_study_summary_title(topic.title, fallback="Tópico do edital"),
        "topic_order": topic_order,
        "subtopic_id": subtopic.subtopic_id if subtopic is not None else None,
        "subtopic_label": (
            _bounded_study_summary_title(subtopic.title, fallback="Subtópico do edital")
            if subtopic is not None
            else None
        ),
        "subtopic_order": subtopic_order,
    }


def _bounded_study_block_item(
    *,
    summary: dict[str, object],
    material,
    section_item: dict[str, object],
    section_index: int,
    edital_scope: dict[str, object] | None,
    edital_available: bool,
) -> tuple[tuple[int, int, int, int, str, str, int], dict[str, object]]:
    document_id = str(summary["document_id"])
    material_title = str(summary["title"])
    section_title = str(section_item["title"])
    connected = edital_scope is not None
    scope_key = (
        str(edital_scope["subtopic_id"] or edital_scope["topic_id"])
        if edital_scope is not None
        else "material"
    )
    block_id = f"study-block:{scope_key}:{document_id}:{section_index}"
    summary_status = str(summary["summary_status"])
    has_specific_section = section_title.lower() not in {"document", "seção sem título", "section"}
    status = (
        "ready"
        if has_specific_section and summary_status != "failed" and (connected or not edital_available)
        else "needs_review"
    )
    title = (
        str(edital_scope["subtopic_label"] or edital_scope["topic_label"])
        if edital_scope is not None
        else section_title
    )
    created_at = material.metadata.created_at.isoformat()
    sort_key = (
        0 if connected else 1,
        int(edital_scope["topic_order"]) if edital_scope is not None else 10_000,
        int(edital_scope["subtopic_order"]) if edital_scope is not None else 10_000,
        0 if status == "ready" else 1,
        created_at,
        document_id,
        section_index,
    )

    return (
        sort_key,
        {
            "block_id": block_id,
            "title": title,
            "topic_id": edital_scope["topic_id"] if edital_scope is not None else None,
            "topic_label": edital_scope["topic_label"] if edital_scope is not None else None,
            "subtopic_id": edital_scope["subtopic_id"] if edital_scope is not None else None,
            "subtopic_label": edital_scope["subtopic_label"] if edital_scope is not None else None,
            "material_id": document_id,
            "material_title": material_title,
            "sections_count": 1,
            "summary_status": summary_status,
            "estimated_minutes": int(section_item["estimated_minutes"]),
            "status": status if summary_status != "failed" else "not_ready",
            "actions": [
                _bounded_study_session_action("Estudar bloco", f"/study/blocks/{block_id}"),
            ],
        },
    )


def _bounded_study_blocks_response(repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    prepared_summaries: list[tuple[object, dict[str, object]]] = []
    for material in repository.list_uploaded_materials(user_id=user_id):
        if _uploaded_material_type(material) != "study_material":
            continue
        summary = _bounded_study_material_summary_response(material, repository, user_id)
        if summary["summary_status"] not in {"ready", "needs_review"} or not summary["items"]:
            continue
        prepared_summaries.append((material, summary))

    if not prepared_summaries:
        return _not_ready_study_blocks_response()

    edital = _study_blocks_candidate_edital(repository, user_id)
    rows: list[tuple[tuple[int, int, int, int, str, str, int], dict[str, object]]] = []
    connected_count = 0
    for material, summary in prepared_summaries:
        material_title = str(summary["title"])
        for section_index, section_item in enumerate(list(summary["items"])):
            match_value = " ".join([material_title, str(section_item["title"])])
            edital_scope = _study_blocks_match_edital_scope(edital, match_value) if edital is not None else None
            if edital_scope is not None:
                connected_count += 1
            rows.append(
                _bounded_study_block_item(
                    summary=summary,
                    material=material,
                    section_item=section_item,
                    section_index=section_index,
                    edital_scope=edital_scope,
                    edital_available=edital is not None,
                )
            )

    rows.sort(key=lambda row: row[0])
    items = [item for _, item in rows]
    estimated_minutes = sum(int(item["estimated_minutes"]) for item in items)
    if edital is None:
        blocks_status = "partial"
        scope_status = "material_only"
    elif connected_count == len(items) and all(item["status"] == "ready" for item in items):
        blocks_status = "ready"
        scope_status = "connected_to_edital"
    else:
        blocks_status = "needs_review"
        scope_status = "connected_to_edital" if connected_count else "material_only"

    return {
        "blocks_status": blocks_status,
        "scope_status": scope_status,
        "blocks_count": len(items),
        "estimated_minutes": estimated_minutes,
        "items": items,
        "source": "user_scope",
    }


def _prepared_review_material_summaries(
    repository: JsonStudyRepository,
    user_id: str,
) -> list[tuple[object, dict[str, object]]]:
    prepared_summaries: list[tuple[object, dict[str, object]]] = []
    for material in repository.list_uploaded_materials(user_id=user_id):
        if _uploaded_material_type(material) != "study_material":
            continue
        summary = _bounded_study_material_summary_response(material, repository, user_id)
        if summary["summary_status"] not in {"ready", "needs_review"} or not summary["items"]:
            continue
        prepared_summaries.append((material, summary))
    return prepared_summaries


def _explicitly_studied_block_ids(repository: JsonStudyRepository, user_id: str) -> set[str]:
    return {
        str(event.get("target_id"))
        for event in repository.list_study_progress_events(user_id=user_id)
        if event.get("event_type") == "block_marked_studied" and event.get("target_type") == "block"
    }


def _studied_material_ids_from_blocks(
    prepared_summaries: list[tuple[object, dict[str, object]]],
    block_items: list[dict[str, object]],
    studied_block_ids: set[str],
) -> set[str]:
    prepared_material_ids = {
        str(summary["document_id"])
        for _, summary in prepared_summaries
        if isinstance(summary.get("document_id"), str)
    }
    block_ids_by_material: dict[str, set[str]] = {
        document_id: set()
        for document_id in prepared_material_ids
    }

    for block in block_items:
        material_id = block.get("material_id")
        block_id = block.get("block_id")
        if not isinstance(material_id, str) or not isinstance(block_id, str):
            continue
        if material_id not in block_ids_by_material:
            continue
        block_ids_by_material[material_id].add(block_id)

    return {
        material_id
        for material_id, block_ids in block_ids_by_material.items()
        if block_ids and block_ids.issubset(studied_block_ids)
    }


def _not_ready_review_block_response(materials_count: int = 0, blocks_count: int = 0) -> dict[str, object]:
    return {
        "review_status": "not_ready",
        "review_id": None,
        "basis": "prepared_materials",
        "materials_count": materials_count,
        "blocks_count": blocks_count,
        "estimated_minutes": 0,
        "title": "Revisão acumulada",
        "summary": {
            "status": "not_ready",
            "items": [],
        },
        "questions": {
            "status": "not_ready",
            "items_count": 0,
        },
        "reinforcement": {
            "status": "not_ready",
            "weak_topics_count": 0,
            "items": [],
        },
        "actions": [],
        "message": "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.",
        "source": "user_scope",
    }


def _bounded_review_summary_item(block: dict[str, object]) -> dict[str, object]:
    title = _bounded_study_summary_title(block.get("title"), fallback="Ponto para revisar")
    material_title = _bounded_study_summary_title(block.get("material_title"), fallback="material preparado")
    topic_label = block["topic_label"] if isinstance(block.get("topic_label"), str) else None
    subtopic_label = block["subtopic_label"] if isinstance(block.get("subtopic_label"), str) else None
    return {
        "title": title,
        "message": f"Revise {title} no material {material_title}.",
        "topic_label": topic_label,
        "subtopic_label": subtopic_label,
    }


def _bounded_review_reinforcement_item(
    block: dict[str, object],
    weak_topic_signals: dict[str, int] | None = None,
) -> dict[str, object]:
    topic_label = block["topic_label"] if isinstance(block.get("topic_label"), str) else None
    subtopic_label = block["subtopic_label"] if isinstance(block.get("subtopic_label"), str) else None
    topic_id = block["topic_id"] if isinstance(block.get("topic_id"), str) else None
    subtopic_id = block["subtopic_id"] if isinstance(block.get("subtopic_id"), str) else None
    focus_label = subtopic_label or topic_label or _bounded_study_summary_title(
        block.get("title"),
        fallback="os pontos principais",
    )
    weak_topic_signals = weak_topic_signals or {}
    weak_count = max(
        int(weak_topic_signals.get(str(subtopic_id), 0) or 0) if subtopic_id else 0,
        int(weak_topic_signals.get(str(topic_id), 0) or 0) if topic_id else 0,
        int(weak_topic_signals.get(str(focus_label), 0) or 0),
    )
    message = (
        f"Priorize {focus_label}: há tentativa incorreta registrada neste ponto."
        if weak_count > 0
        else f"Revise {focus_label} com calma antes de avançar para novos pontos."
    )
    return {
        "topic_label": topic_label,
        "subtopic_label": subtopic_label,
        "message": message,
    }


def _bounded_next_review_block_response(repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    prepared_summaries = _prepared_review_material_summaries(repository, user_id)
    prepared_materials_count = len(prepared_summaries)
    blocks = _bounded_study_blocks_response(repository, user_id)
    block_items = [item for item in blocks.get("items", []) if isinstance(item, dict)]
    all_blocks_count = len(block_items)
    studied_material_ids = _studied_material_ids_from_blocks(
        prepared_summaries,
        block_items,
        _explicitly_studied_block_ids(repository, user_id),
    )
    studied_materials_count = len(studied_material_ids)

    if studied_materials_count >= 3:
        basis = "studied_materials"
        review_blocks = [
            block
            for block in block_items
            if isinstance(block.get("material_id"), str) and str(block["material_id"]) in studied_material_ids
        ]
        materials_count = studied_materials_count
        blocks_count = len(review_blocks)
    else:
        basis = "prepared_materials" if prepared_materials_count >= 3 else "study_blocks"
        review_blocks = block_items
        materials_count = prepared_materials_count
        blocks_count = all_blocks_count

    if materials_count < 3 and blocks_count < 3:
        return _not_ready_review_block_response(materials_count, blocks_count)

    weak_topic_signals = repository.list_study_weak_topic_signals(user_id=user_id)

    def review_block_priority(block: dict[str, object]) -> tuple[int, str]:
        identifiers = [
            block.get("subtopic_id"),
            block.get("topic_id"),
            block.get("subtopic_label"),
            block.get("topic_label"),
            block.get("title"),
        ]
        has_weak_signal = any(str(identifier) in weak_topic_signals for identifier in identifiers if identifier)
        return (0 if has_weak_signal else 1, str(block.get("block_id") or ""))

    selected_blocks = sorted(review_blocks, key=review_block_priority)[: min(5, len(review_blocks))]
    estimated_minutes = sum(int(block.get("estimated_minutes", 0) or 0) for block in selected_blocks)
    if estimated_minutes <= 0:
        estimated_minutes = max(5, min(30, blocks_count * 5))

    questions_count = 0
    for block in selected_blocks[:3]:
        questions = _bounded_fixation_questions_response(repository, user_id, str(block["block_id"]))
        questions_count += len([item for item in questions.get("items", []) if isinstance(item, dict)])

    all_blocks_ready = all(str(block.get("status")) == "ready" for block in selected_blocks)
    all_summaries_ready = all(str(block.get("summary_status")) == "ready" for block in selected_blocks)
    review_status = "ready" if all_blocks_ready and all_summaries_ready and questions_count > 0 else "needs_review"
    review_id = f"review:{basis}:{materials_count}:{blocks_count}"
    summary_status = "ready" if all_summaries_ready else "needs_review"
    questions_status = "ready" if questions_count > 0 and review_status == "ready" else "needs_review"

    return {
        "review_status": review_status,
        "review_id": review_id,
        "basis": basis,
        "materials_count": materials_count,
        "blocks_count": blocks_count,
        "estimated_minutes": estimated_minutes,
        "title": "Revisão acumulada",
        "summary": {
            "status": summary_status,
            "items": [_bounded_review_summary_item(block) for block in selected_blocks],
        },
        "questions": {
            "status": questions_status,
            "items_count": questions_count,
        },
        "reinforcement": {
            "status": "ready" if weak_topic_signals else "needs_review",
            "weak_topics_count": len(weak_topic_signals),
            "items": [
                _bounded_review_reinforcement_item(block, weak_topic_signals)
                for block in selected_blocks[:3]
            ],
        },
        "actions": [
            _bounded_study_session_action("Abrir revisão", f"/study/review/{review_id}"),
        ],
        "source": "user_scope",
    }


def _validate_study_progress_event_request(payload: StudyProgressEventRequest) -> None:
    if payload.event_type not in STUDY_PROGRESS_EVENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported progress event type.")
    if payload.target_type not in STUDY_PROGRESS_TARGET_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported progress target type.")
    if payload.target_type not in STUDY_PROGRESS_EVENT_TARGETS[payload.event_type]:
        raise HTTPException(status_code=422, detail="Unsupported progress event target.")
    if not payload.target_id.strip() or len(payload.target_id) > 240:
        raise HTTPException(status_code=422, detail="Invalid progress target id.")
    if payload.idempotency_key is not None and (
        not payload.idempotency_key.strip() or len(payload.idempotency_key) > 160
    ):
        raise HTTPException(status_code=422, detail="Invalid progress idempotency key.")


def _bounded_study_progress_event_response(event: dict[str, object]) -> dict[str, object]:
    return {
        "event_id": str(event["event_id"]),
        "event_type": str(event["event_type"]),
        "target_type": str(event["target_type"]),
        "target_id": str(event["target_id"]),
        "created_at": str(event["created_at"]),
        "source": "user_scope",
    }


def _bounded_study_progress_summary_response(repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    events = repository.list_study_progress_events(user_id=user_id)
    opened_blocks = {
        str(event.get("target_id"))
        for event in events
        if event.get("event_type") == "block_opened" and event.get("target_type") == "block"
    }
    studied_blocks = {
        str(event.get("target_id"))
        for event in events
        if event.get("event_type") == "block_marked_studied" and event.get("target_type") == "block"
    }
    reviewed_question_ids = {
        str(event.get("target_id"))
        for event in events
        if event.get("event_type") == "question_reviewed" and event.get("target_type") == "question"
    }
    reviewed_question_ids.update(
        str(attempt.get("question_id"))
        for attempt in repository.list_study_question_attempts(user_id=user_id)
        if isinstance(attempt.get("question_id"), str)
    )
    reviewed_questions_count = len(reviewed_question_ids)
    weak_topics_count = len(repository.list_study_weak_topic_signals(user_id=user_id))
    prepared_summaries = _prepared_review_material_summaries(repository, user_id)
    prepared_materials_count = len(prepared_summaries)
    blocks = _bounded_study_blocks_response(repository, user_id)
    block_items = [item for item in blocks.get("items", []) if isinstance(item, dict)]
    studied_materials_count = len(
        _studied_material_ids_from_blocks(prepared_summaries, block_items, studied_blocks)
    )
    review_due = studied_materials_count >= 3 or prepared_materials_count >= 3
    review_basis = (
        "studied_materials"
        if studied_materials_count >= 3
        else "prepared_materials"
        if prepared_materials_count >= 3
        else "none"
    )
    progress_status = "ready" if events or prepared_materials_count else "not_ready"

    return {
        "progress_status": progress_status,
        "opened_blocks_count": len(opened_blocks),
        "studied_blocks_count": len(studied_blocks),
        "prepared_materials_count": prepared_materials_count,
        "studied_materials_count": studied_materials_count,
        "review_due": review_due,
        "review_basis": review_basis,
        "reviewed_questions_count": reviewed_questions_count,
        "weak_topics_count": weak_topics_count,
        "source": "user_scope",
    }


def _study_block_section_index(block_id: str) -> int | None:
    try:
        return int(block_id.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return None


def _bounded_study_block_detail_response(
    repository: JsonStudyRepository,
    user_id: str,
    block_id: str,
) -> dict[str, object]:
    blocks = _bounded_study_blocks_response(repository, user_id)
    block = next(
        (
            item
            for item in blocks.get("items", [])
            if isinstance(item, dict) and item.get("block_id") == block_id
        ),
        None,
    )
    if block is None:
        raise HTTPException(status_code=404, detail="Study block not found")

    material_id = str(block["material_id"])
    material = repository.get_uploaded_material(material_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Study block not found")

    summary = _bounded_study_material_summary_response(material, repository, user_id)
    summary_items = list(summary["items"])
    section_index = _study_block_section_index(block_id)
    if section_index is None:
        raise HTTPException(status_code=404, detail="Study block not found")

    if 0 <= section_index < len(summary_items):
        sections = [summary_items[section_index]]
    else:
        sections = []

    summary_status = str(summary["summary_status"])
    if summary_status not in {"ready", "needs_review", "not_ready"}:
        summary_status = "not_ready"

    if not sections:
        detail_status = "not_ready"
    elif str(block["status"]) == "ready" and summary_status == "ready":
        detail_status = "ready"
    else:
        detail_status = "needs_review"

    estimated_minutes = sum(int(section["estimated_minutes"]) for section in sections)
    if estimated_minutes == 0:
        estimated_minutes = int(block["estimated_minutes"])

    return {
        "block_id": str(block["block_id"]),
        "detail_status": detail_status,
        "title": str(block["title"]),
        "topic_id": block["topic_id"],
        "topic_label": block["topic_label"],
        "subtopic_id": block["subtopic_id"],
        "subtopic_label": block["subtopic_label"],
        "material_id": material_id,
        "material_title": str(block["material_title"]),
        "summary_status": summary_status,
        "estimated_minutes": estimated_minutes,
        "sections": sections,
        "actions": [
            _bounded_study_session_action("Abrir material", f"/materials/{material_id}"),
            _bounded_study_session_action("Voltar ao caminho de estudo", "/study"),
        ],
        "source": "user_scope",
    }


def _safe_fixation_question_label(value: object) -> str | None:
    label = _bounded_study_summary_title(value, fallback="")
    if not label:
        return None
    if label.strip().lower() in {"document", "section", "seção sem título", "material de estudo"}:
        return None
    return label


def _deduplicate_fixation_labels(values: list[str | None]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = _safe_fixation_question_label(value)
        if label is None:
            continue
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def _fixation_labels_from_detail(detail: dict[str, object]) -> list[str]:
    values: list[str | None] = []
    if isinstance(detail.get("subtopic_label"), str):
        values.append(str(detail["subtopic_label"]))
    if isinstance(detail.get("topic_label"), str):
        values.append(str(detail["topic_label"]))
    if isinstance(detail.get("title"), str):
        values.append(str(detail["title"]))
    for section in detail["sections"]:
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("title"), str):
            values.append(str(section["title"]))
        key_points = section.get("key_points")
        if isinstance(key_points, list):
            values.extend(str(item) for item in key_points if isinstance(item, str))
    return _deduplicate_fixation_labels(values)


def _resolve_fixation_question_profile(detail: dict[str, object]) -> str:
    return "multiple_choice_ae"


def _question_fingerprint(*parts: object) -> str:
    normalized = "|".join(_normalize_study_text(part) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def _public_question_payload(question: dict[str, object]) -> dict[str, object]:
    return {
        "question_id": str(question["question_id"]),
        "type": str(question["type"]),
        "prompt": str(question["prompt"]),
        "alternatives": list(question.get("alternatives", [])),
        "topic_label": question.get("topic_label") if isinstance(question.get("topic_label"), str) else None,
        "subtopic_label": question.get("subtopic_label") if isinstance(question.get("subtopic_label"), str) else None,
        "difficulty": str(question.get("difficulty") or "basic"),
        "status": str(question.get("status") or "needs_review"),
    }


def _section_chunks_for_detail(
    repository: JsonStudyRepository,
    user_id: str,
    detail: dict[str, object],
) -> list[object]:
    material_id = str(detail.get("material_id") or "")
    section_ids = {
        str(section.get("section_id"))
        for section in detail.get("sections", [])
        if isinstance(section, dict) and isinstance(section.get("section_id"), str)
    }
    chunks = repository.list_document_chunks(material_id, user_id=user_id)
    return [
        chunk
        for chunk in sorted(chunks, key=lambda item: item.chunk_index)
        if chunk.section_id in section_ids
    ]


QUESTION_AMBIGUITY_MARKERS = (
    " pode ser ",
    " podem ser ",
    " em geral ",
    " normalmente ",
    " possivelmente ",
    " talvez ",
    " ou ",
)

QUESTION_FALSE_TRANSFORMATIONS = (
    (r"\bconsiste em\b", "não consiste em"),
    (r"\bdeve\b", "não deve"),
    (r"\bdevem\b", "não devem"),
    (r"\bpode\b", "não pode"),
    (r"\bpodem\b", "não podem"),
    (r"\bexige\b", "não exige"),
    (r"\binclui\b", "não inclui"),
    (r"\bpermite\b", "não permite"),
    (r"\bimpede\b", "não impede"),
    (r"\blimitar\b", "ampliar"),
    (r"\blimita\b", "amplia"),
    (r"\bimediatos\b", "posteriores"),
    (r"\bimediato\b", "posterior"),
    (r"\bfinalidade publica\b", "finalidade privada"),
    (r"\bfinalidade pública\b", "finalidade privada"),
    (r"\batividade administrativa\b", "atividade privada"),
    (r"\befeitos juridicos\b", "efeitos sem natureza jurídica"),
    (r"\befeitos jurídicos\b", "efeitos sem natureza jurídica"),
    (r"\bobrigatoria\b", "facultativa"),
    (r"\bobrigatória\b", "facultativa"),
    (r"\bantes\b", "depois"),
)


def _question_strategy(sentence: str) -> str | None:
    normalized = f" {_normalize_study_text(sentence)} "
    if any(marker in normalized for marker in QUESTION_AMBIGUITY_MARKERS):
        return None
    if any(marker in normalized for marker in (" consiste ", " define ", " significa ")):
        return "definition"
    if any(marker in normalized for marker in (" exceto ", " salvo ", " excecao ", " exceção ")):
        return "exception"
    if any(marker in normalized for marker in (" deve ", " devem ", " exige ", " quando ", " se ")):
        return "rule_condition"
    if any(marker in normalized for marker in (" classifica ", " classificam ", " inclui ", " compreende ")):
        return "classification"
    if any(
        marker in normalized
        for marker in (
            " indica ",
            " apresenta ",
            " representa ",
            " organiza ",
            " produz ",
            " corresponde ",
            " possui ",
        )
    ):
        return "factual_relation"
    if re.search(r"\b\d+(?:[.,]\d+)?\b", normalized):
        return "explicit_fact"
    return None


def _grounded_question_evidence(
    repository: JsonStudyRepository,
    user_id: str,
    detail: dict[str, object],
) -> list[dict[str, object]]:
    chunks = _section_chunks_for_detail(repository, user_id, detail)
    terms = _study_term_tokens(
        detail.get("title"),
        detail.get("topic_label"),
        detail.get("subtopic_label"),
    )
    candidates = _summary_statement_candidates(
        title=str(detail.get("title") or ""),
        chunks=chunks,
        terms=terms,
    )
    evidence: list[dict[str, object]] = []
    for candidate in candidates:
        sentence = str(candidate["text"])
        strategy = _question_strategy(sentence)
        if strategy is None or len(sentence) > GROUNDED_QUESTION_MAX_ALTERNATIVE_CHARS:
            continue
        evidence.append(
            {
                "text": sentence,
                "strategy": strategy,
                "score": int(candidate["score"]),
                "source_order": candidate["source_order"],
                "anchor": dict(candidate["anchor"]),
            }
        )
    return sorted(
        evidence,
        key=lambda item: (-int(item["score"]), item["source_order"], str(item["text"])),
    )


def _controlled_false_variants(sentence: str, source_sentences: set[str]) -> list[str]:
    variants: list[str] = []
    seen = {_normalize_study_text(sentence)}
    for pattern, replacement in QUESTION_FALSE_TRANSFORMATIONS:
        if re.search(pattern, sentence, flags=re.IGNORECASE) is None:
            continue
        variant = re.sub(pattern, replacement, sentence, count=1, flags=re.IGNORECASE)
        normalized = _normalize_study_text(variant)
        if not normalized or normalized in seen or normalized in source_sentences:
            continue
        seen.add(normalized)
        variants.append(variant)
    return variants


def _relation_parts(sentence: str) -> tuple[str, str] | None:
    match = re.search(
        r"\b(?:consiste|define|significa|deve|devem|exige|indica|apresenta|representa|organiza|produz|corresponde|possui)\b",
        sentence,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    subject = sentence[: match.start()].strip(" ,:;-")
    predicate = sentence[match.start() :].strip()
    if len(subject.split()) < 2 or len(predicate.split()) < 3:
        return None
    return subject, predicate


def _relation_false_variants(
    sentence: str,
    evidence_items: list[dict[str, object]],
    source_sentences: set[str],
) -> list[str]:
    current = _relation_parts(sentence)
    if current is None:
        return []
    subject, predicate = current
    variants: list[str] = []
    seen = {_normalize_study_text(sentence)}
    for item in evidence_items:
        other_sentence = str(item["text"])
        if _normalize_study_text(other_sentence) == _normalize_study_text(sentence):
            continue
        other = _relation_parts(other_sentence)
        if other is None:
            continue
        other_subject, other_predicate = other
        for variant in (f"{subject} {other_predicate}", f"{other_subject} {predicate}"):
            normalized = _normalize_study_text(variant)
            if not normalized or normalized in seen or normalized in source_sentences:
                continue
            seen.add(normalized)
            variants.append(variant)
    return variants


def _question_focus(sentence: str, fallback: str) -> str:
    normalized = " ".join(sentence.split())
    marker_match = re.search(
        r"\b(?:consiste|define|significa|deve|devem|exige|indica|apresenta|representa|organiza|produz)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    focus = normalized[: marker_match.start()].strip(" ,:;-") if marker_match else fallback
    return focus[:80] or fallback[:80]


def _grounded_question_prompt(*, strategy: str, sentence: str, fallback: str) -> str:
    focus = _question_focus(sentence, fallback)
    if focus and not focus.isupper():
        focus = f"{focus[0].lower()}{focus[1:]}"
    if strategy == "definition":
        prompt = f"Segundo o material, qual afirmação define corretamente {focus}?"
    elif strategy == "exception":
        prompt = f"Qual afirmação preserva corretamente a exceção apresentada sobre {focus}?"
    elif strategy == "classification":
        prompt = f"Qual classificação sobre {focus} está expressamente apoiada pelo material?"
    elif strategy == "explicit_fact":
        prompt = f"Qual informação objetiva sobre {focus} está expressamente apoiada pelo material?"
    else:
        prompt = f"Qual afirmação sobre {focus} está expressamente apoiada pelo material?"
    return " ".join(prompt.split())[:GROUNDED_QUESTION_MAX_PROMPT_CHARS]


def _multiple_choice_alternatives(
    *,
    correct_text: str,
    false_variants: list[str],
    ordering_fingerprint: str,
    option_count: int = 5,
) -> tuple[list[dict[str, str]], str]:
    option_ids = list("ABCDE")[:option_count]
    texts = [correct_text, *false_variants[: option_count - 1]]
    correct_index = int(ordering_fingerprint[:2], 16) % option_count
    ordered: list[str] = []
    distractor_index = 1
    for index in range(option_count):
        if index == correct_index:
            ordered.append(texts[0])
        else:
            ordered.append(texts[distractor_index])
            distractor_index += 1
    alternatives = [
        {"id": option_id, "text": " ".join(text.split())[:GROUNDED_QUESTION_MAX_ALTERNATIVE_CHARS]}
        for option_id, text in zip(option_ids, ordered)
    ]
    return alternatives, option_ids[correct_index]


def _true_false_alternatives() -> list[dict[str, str]]:
    return [
        {"id": "C", "text": "Certo"},
        {"id": "E", "text": "Errado"},
    ]


def _append_fixation_candidate(
    candidates: list[dict[str, object]],
    seen_questions: set[str],
    *,
    block_id: str,
    material_id: str,
    prompt: str,
    topic_label: str | None,
    subtopic_label: str | None,
    status: str,
    question_type: str = "short_answer",
    alternatives: list[dict[str, str]] | None = None,
    correct_answer: str | None = None,
    evidence: str | None = None,
    source_anchor: dict[str, object] | None = None,
    rationale: str | None = None,
    strategy: str | None = None,
    validation_state: str = "needs_review",
    fingerprint: str | None = None,
) -> None:
    safe_prompt = " ".join(prompt.split())[:GROUNDED_QUESTION_MAX_PROMPT_CHARS]
    if not safe_prompt:
        return
    public_alternatives = alternatives or []
    question_key = _question_fingerprint(
        safe_prompt,
        [(item.get("id"), item.get("text")) for item in public_alternatives],
        block_id,
        question_type,
        GROUNDED_QUESTION_GENERATOR_VERSION,
    )
    if question_key in seen_questions or len(candidates) >= GROUNDED_QUESTION_MAX_ITEMS:
        return
    seen_questions.add(question_key)
    question_fingerprint = fingerprint or question_key
    candidates.append(
        {
            "question_id": f"question:{block_id}:{question_fingerprint}",
            "type": question_type,
            "prompt": safe_prompt,
            "alternatives": public_alternatives,
            "topic_label": topic_label,
            "subtopic_label": subtopic_label,
            "difficulty": "basic",
            "status": status,
            "_correct_answer": correct_answer,
            "_evidence": evidence,
            "_source_anchor": dict(source_anchor or {}),
            "_rationale": rationale,
            "_material_id": material_id,
            "_block_id": block_id,
            "_strategy": strategy,
            "_generator_method": GROUNDED_QUESTION_GENERATION_METHOD,
            "_generator_version": GROUNDED_QUESTION_GENERATOR_VERSION,
            "_validation_state": validation_state,
            "_fingerprint": question_fingerprint,
            "_version": GROUNDED_QUESTION_GENERATOR_VERSION,
        }
    )


def _internal_fixation_question_candidates(
    repository: JsonStudyRepository,
    user_id: str,
    block_id: str,
) -> tuple[dict[str, object], str, list[dict[str, object]]]:
    detail = _bounded_study_block_detail_response(repository, user_id, block_id)
    if detail["detail_status"] == "not_ready":
        return detail, "not_ready", []

    topic_label = detail["topic_label"] if isinstance(detail["topic_label"], str) else None
    subtopic_label = detail["subtopic_label"] if isinstance(detail["subtopic_label"], str) else None
    candidates: list[dict[str, object]] = []
    seen_questions: set[str] = set()
    profile = _resolve_fixation_question_profile(detail)
    if profile not in {"multiple_choice_ae", "multiple_choice_ad", "cebraspe_true_false"}:
        return detail, "unsupported", []
    evidence_items = _grounded_question_evidence(repository, user_id, detail)
    source_sentences = {_normalize_study_text(str(item["text"])) for item in evidence_items}
    focus_label = subtopic_label or topic_label or str(detail.get("title") or "este ponto")
    item_status = "candidate" if detail["detail_status"] == "ready" else "needs_review"

    if profile in {"multiple_choice_ae", "multiple_choice_ad"}:
        option_count = 4 if profile == "multiple_choice_ad" else 5
        for evidence in evidence_items:
            sentence = str(evidence["text"])
            false_variants = _controlled_false_variants(sentence, source_sentences)
            false_variants.extend(
                variant
                for variant in _relation_false_variants(sentence, evidence_items, source_sentences)
                if _normalize_study_text(variant)
                not in {_normalize_study_text(item) for item in false_variants}
            )
            if len(false_variants) < option_count - 1:
                continue
            prompt = _grounded_question_prompt(
                strategy=str(evidence["strategy"]),
                sentence=sentence,
                fallback=focus_label,
            )
            ordering_fingerprint = _question_fingerprint(
                detail["block_id"],
                sentence,
                profile,
                GROUNDED_QUESTION_GENERATOR_VERSION,
            )
            alternatives, correct_answer = _multiple_choice_alternatives(
                correct_text=sentence,
                false_variants=false_variants,
                ordering_fingerprint=ordering_fingerprint,
                option_count=option_count,
            )
            fingerprint = _question_fingerprint(
                prompt,
                [(item["id"], item["text"]) for item in alternatives],
                detail["block_id"],
                profile,
                GROUNDED_QUESTION_GENERATOR_VERSION,
            )
            _append_fixation_candidate(
                candidates,
                seen_questions,
                block_id=str(detail["block_id"]),
                material_id=str(detail["material_id"]),
                prompt=prompt,
                topic_label=topic_label,
                subtopic_label=subtopic_label,
                status=item_status,
                question_type="multiple_choice",
                alternatives=alternatives,
                correct_answer=correct_answer,
                evidence=sentence,
                source_anchor=dict(evidence["anchor"]),
                rationale="A alternativa correta reproduz a proposição explícita do material; as demais alteram um elemento factual.",
                strategy=str(evidence["strategy"]),
                validation_state="validated",
                fingerprint=fingerprint,
            )

    if profile == "cebraspe_true_false":
        alternatives = _true_false_alternatives()
        for evidence in evidence_items:
            sentence = str(evidence["text"])
            true_prompt = f"Julgue o item: {sentence}"
            if len(true_prompt) > GROUNDED_QUESTION_MAX_PROMPT_CHARS:
                continue
            true_fingerprint = _question_fingerprint(
                true_prompt,
                alternatives,
                detail["block_id"],
                profile,
                GROUNDED_QUESTION_GENERATOR_VERSION,
            )
            _append_fixation_candidate(
                candidates,
                seen_questions,
                block_id=str(detail["block_id"]),
                material_id=str(detail["material_id"]),
                prompt=true_prompt,
                topic_label=topic_label,
                subtopic_label=subtopic_label,
                status=item_status,
                question_type="true_false",
                alternatives=alternatives,
                correct_answer="C",
                evidence=sentence,
                source_anchor=dict(evidence["anchor"]),
                rationale="A afirmação reproduz uma proposição explícita do material.",
                strategy=str(evidence["strategy"]),
                validation_state="validated",
                fingerprint=true_fingerprint,
            )
            false_variants = _controlled_false_variants(sentence, source_sentences)
            if not false_variants:
                continue
            false_prompt = f"Julgue o item: {false_variants[0]}"
            if len(false_prompt) > GROUNDED_QUESTION_MAX_PROMPT_CHARS:
                continue
            false_fingerprint = _question_fingerprint(
                false_prompt,
                alternatives,
                detail["block_id"],
                profile,
                GROUNDED_QUESTION_GENERATOR_VERSION,
            )
            _append_fixation_candidate(
                candidates,
                seen_questions,
                block_id=str(detail["block_id"]),
                material_id=str(detail["material_id"]),
                prompt=false_prompt,
                topic_label=topic_label,
                subtopic_label=subtopic_label,
                status=item_status,
                question_type="true_false",
                alternatives=alternatives,
                correct_answer="E",
                evidence=sentence,
                source_anchor=dict(evidence["anchor"]),
                rationale="A afirmação altera um elemento da proposição explícita do material.",
                strategy=str(evidence["strategy"]),
                validation_state="validated",
                fingerprint=false_fingerprint,
            )

    if not candidates:
        return detail, "needs_review", []
    question_status = "ready" if detail["detail_status"] == "ready" else "needs_review"
    return detail, question_status, candidates


def _bounded_fixation_questions_response(
    repository: JsonStudyRepository,
    user_id: str,
    block_id: str,
) -> dict[str, object]:
    detail, question_status, candidates = _internal_fixation_question_candidates(
        repository,
        user_id,
        block_id,
    )
    if question_status == "not_ready":
        return {
            "block_id": str(detail["block_id"]),
            "question_status": "not_ready",
            "mode": "review_only",
            "items": [],
            "warnings_count": 0,
            "source": "user_scope",
        }

    return {
        "block_id": str(detail["block_id"]),
        "question_status": question_status,
        "mode": "review_only",
        "items": [_public_question_payload(item) for item in candidates],
        "warnings_count": 1 if question_status == "needs_review" else 0,
        "source": "user_scope",
    }


ANSWER_REVIEW_FORMATS = {"text", "choice", "true_false"}
MAX_ANSWER_REVIEW_LENGTH = 2000


def _validate_answer_review_request(payload: StudyBlockAnswerReviewRequest) -> tuple[str, str, str | None]:
    answer = payload.answer.strip()
    answer_format = payload.answer_format.strip()
    if not answer:
        raise HTTPException(status_code=422, detail="answer is required.")
    if len(answer) > MAX_ANSWER_REVIEW_LENGTH:
        raise HTTPException(status_code=422, detail="answer is too long.")
    if answer_format not in ANSWER_REVIEW_FORMATS:
        raise HTTPException(status_code=422, detail="answer_format is invalid.")
    idempotency_key = payload.idempotency_key.strip() if payload.idempotency_key else None
    if idempotency_key is not None and (not idempotency_key or len(idempotency_key) > 160):
        raise HTTPException(status_code=422, detail="idempotency_key is invalid.")
    return answer, answer_format, idempotency_key


def _bounded_answer_review_response(
    repository: JsonStudyRepository,
    user_id: str,
    block_id: str,
    question_id: str,
    payload: StudyBlockAnswerReviewRequest,
) -> dict[str, object]:
    answer, answer_format, _idempotency_key = _validate_answer_review_request(payload)
    detail, _question_status, candidates = _internal_fixation_question_candidates(repository, user_id, block_id)
    question = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("question_id") == question_id
        ),
        None,
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Study block question not found.")

    topic_label = question["topic_label"] if isinstance(question.get("topic_label"), str) else None
    subtopic_label = question["subtopic_label"] if isinstance(question.get("subtopic_label"), str) else None
    focus_label = subtopic_label or topic_label
    if focus_label:
        reinforcement_message = (
            f"Revise o resumo do bloco e compare sua resposta com os pontos principais de {focus_label}."
        )
    else:
        reinforcement_message = "Revise o resumo do bloco e compare sua resposta com os pontos principais."

    question_type = str(question.get("type") or "")
    expected_format = "true_false" if question_type == "true_false" else "choice" if question_type == "multiple_choice" else "text"
    if answer_format != expected_format:
        raise HTTPException(status_code=422, detail="answer_format does not match question type.")
    allowed_answers = {
        str(alternative.get("id"))
        for alternative in question.get("alternatives", [])
        if isinstance(alternative, dict) and isinstance(alternative.get("id"), str)
    }
    if question_type in {"multiple_choice", "true_false"} and answer not in allowed_answers:
        raise HTTPException(status_code=422, detail="answer is not an alternative for this question.")

    validation_state = str(question.get("_validation_state") or "needs_review")
    correct_answer = question.get("_correct_answer") if isinstance(question.get("_correct_answer"), str) else None
    evidence = question.get("_evidence") if isinstance(question.get("_evidence"), str) else None
    if validation_state == "validated" and correct_answer:
        review_status = "reviewed"
        result = "correct" if answer == correct_answer else "incorrect"
        if result == "correct":
            feedback = (
                f"Sua escolha está alinhada com o material: {evidence}"
                if evidence
                else "Sua escolha está alinhada com a evidência do material."
            )
            suggested_action = "review_summary"
        else:
            feedback = "Sua escolha não corresponde à evidência usada para esta questão. Revise o trecho indicado."
            suggested_action = "retry_question"
            if evidence:
                reinforcement_message = f"Revise este ponto no resumo: {evidence[:220]}"
    else:
        review_status = "reviewed" if question_type == "short_answer" and answer_format == "text" else "needs_review"
        result = "ungraded"
        feedback = "Esta escolha foi recebida, mas a questão ainda não tem validação suficiente para avaliar certo ou errado."
        suggested_action = "review_summary" if question_type == "short_answer" else "revisit_block"

    return {
        "block_id": str(detail["block_id"]),
        "question_id": question_id,
        "review_status": review_status,
        "result": result,
        "feedback": feedback,
        "reinforcement": {
            "topic_label": topic_label,
            "subtopic_label": subtopic_label,
            "message": reinforcement_message,
            "suggested_action": suggested_action,
        },
        "source": "user_scope",
    }


@router.get("/study/blocks")
def get_study_blocks(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_study_blocks_response(repository, user_id)


@router.get("/study/review/next")
def get_next_study_review(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_next_review_block_response(repository, user_id)


@router.post("/study/progress/events")
def create_study_progress_event(payload: StudyProgressEventRequest, request: Request):
    user_id = _require_authenticated_user_id(request)
    _validate_study_progress_event_request(payload)
    repository = get_repository(request)
    event = repository.record_study_progress_event(
        user_id=user_id,
        event_type=payload.event_type,
        target_type=payload.target_type,
        target_id=payload.target_id.strip(),
        idempotency_key=payload.idempotency_key.strip() if payload.idempotency_key else None,
    )
    return _bounded_study_progress_event_response(event)


@router.get("/study/progress/summary")
def get_study_progress_summary(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_study_progress_summary_response(repository, user_id)


@router.get("/study/blocks/{block_id}/questions")
def get_study_block_questions(block_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_fixation_questions_response(repository, user_id, block_id)


@router.post("/study/blocks/{block_id}/questions/{question_id}/answer/review")
def review_study_block_answer(
    block_id: str,
    question_id: str,
    payload: StudyBlockAnswerReviewRequest,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_answer_review_response(repository, user_id, block_id, question_id, payload)


@router.get("/study/blocks/{block_id}")
def get_study_block_detail(block_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    return _bounded_study_block_detail_response(repository, user_id, block_id)


@router.get("/study/session/next")
def get_next_study_session(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    candidates: list[tuple[int, str, str, object, dict[str, object]]] = []
    for material in repository.list_uploaded_materials(user_id=user_id):
        if _uploaded_material_type(material) != "study_material":
            continue
        summary = _bounded_study_material_summary_response(material, repository, user_id)
        if summary["summary_status"] not in {"ready", "needs_review"} or not summary["items"]:
            continue
        created_at = material.metadata.created_at.isoformat()
        status_rank = 0 if summary["summary_status"] == "ready" else 1
        candidates.append((status_rank, created_at, material.metadata.document_id, material, summary))

    if not candidates:
        return _not_ready_study_session_response()

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    _, _, _, _, selected_summary = candidates[0]
    return _bounded_next_study_session_response(selected_summary, repository, user_id)


@router.post("/materials/{document_id}/study/prepare")
def prepare_study_material(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    material = repository.get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    if _uploaded_material_type(material) != "study_material":
        raise HTTPException(status_code=422, detail="Material is not classified as study material.")

    if (
        repository.get_document_extraction_result(document_id, user_id=user_id) is None
        and _can_prepare_edital_material_without_ocr(material)
    ):
        try:
            get_document_pipeline_service(request).prepare_document_without_ocr(document_id, user_id=user_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Material not found.") from exc

    refreshed_material = repository.get_uploaded_material(document_id, user_id=user_id)
    if refreshed_material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return _bounded_study_material_preparation_response(refreshed_material, repository, user_id)


@router.get("/materials/{document_id}/study/summary")
def get_study_material_summary(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    material = repository.get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    if _uploaded_material_type(material) != "study_material":
        raise HTTPException(status_code=422, detail="Material is not classified as study material.")
    return _bounded_study_material_summary_response(material, repository, user_id)


@router.post("/materials/{document_id}/edital/analyze")
def analyze_edital(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    material = repository.get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    if _uploaded_material_type(material) != "edital":
        raise HTTPException(status_code=422, detail="Material is not classified as edital.")

    if (
        repository.get_document_extraction_result(document_id, user_id=user_id) is None
        and _can_prepare_edital_material_without_ocr(material)
    ):
        get_document_pipeline_service(request).prepare_document_without_ocr(document_id, user_id=user_id)

    state = get_edital_ingestion_service(request).ingest_document(document_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    result = repository.get_edital_extraction_result(document_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    return _bounded_edital_analysis_response(result, repository, user_id)


@router.post("/materials/{document_id}/edital/ingest")
def ingest_edital(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    state = get_edital_ingestion_service(request).ingest_document(document_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    result = get_repository(request).get_edital_extraction_result(document_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    return result


@router.get("/materials/{document_id}/edital")
def get_material_edital(document_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    material = get_repository(request).get_uploaded_material(document_id, user_id=user_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    result = get_repository(request).get_edital_extraction_result(document_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    return result


def _bounded_edital_review_state(edital, ingestion_state, alignment_result) -> str:
    if ingestion_state is not None and ingestion_state.status in {"pending", "started"}:
        return "pending"
    if edital.warnings:
        return "needs_review"
    if alignment_result is not None and (alignment_result.gaps or alignment_result.warnings):
        return "needs_review"
    if ingestion_state is not None and ingestion_state.status in {"ready_for_review", "available", "ready", "completed"}:
        return "ready_for_review"
    return "unknown"


def _bounded_edital_coverage_status(alignment_result) -> str:
    if alignment_result is None:
        return "unknown"
    if alignment_result.gaps:
        gap_types = {gap.gap_type for gap in alignment_result.gaps}
        if gap_types & {"missing_bibliography_material", "missing_document_text", "uncovered_topic"}:
            return "needs_material"
        return "gap_found"
    uncovered = [item for item in alignment_result.topic_coverage if item.coverage_state == "uncovered"]
    partial = [
        item
        for item in alignment_result.topic_coverage
        if item.coverage_state in {"partially_covered", "weakly_covered"}
    ]
    if uncovered:
        return "gap_found"
    if partial:
        return "partial"
    if alignment_result.topic_coverage or alignment_result.bibliography_alignments:
        return "good"
    return "unknown"


def _bounded_edital_alignment_status(alignment_state, alignment_result) -> str:
    if alignment_state is None and alignment_result is None:
        return "not_available"
    if alignment_state is not None and alignment_state.status in {"pending", "started"}:
        return "unknown"
    if alignment_result is not None and (alignment_result.gaps or alignment_result.warnings):
        return "needs_review"
    if alignment_state is not None and alignment_state.status in {"ready_for_review", "available", "ready", "completed"}:
        return "aligned"
    if alignment_result is not None:
        return "partial"
    return "unknown"


def _bounded_edital_item(edital, repository: JsonStudyRepository, user_id: str) -> dict[str, object]:
    ingestion_state = repository.get_edital_ingestion_state(edital.document_id, user_id=user_id)
    alignment_state = repository.get_bibliography_alignment_state(edital.edital_id, user_id=user_id)
    alignment_result = repository.get_bibliography_alignment_result(edital.edital_id, user_id=user_id)
    warnings_count = len(edital.warnings)
    if ingestion_state is not None:
        warnings_count += len(ingestion_state.warnings) + len(ingestion_state.errors)
    if alignment_result is not None:
        warnings_count += len(alignment_result.warnings)
    if alignment_state is not None:
        warnings_count += len(alignment_state.warnings) + len(alignment_state.errors)

    updated_at = None
    if alignment_state is not None:
        updated_at = alignment_state.updated_at
    elif ingestion_state is not None:
        updated_at = ingestion_state.updated_at

    review_state = _bounded_edital_review_state(edital, ingestion_state, alignment_result)

    return {
        "edital_id": edital.edital_id,
        "document_id": edital.document_id,
        "title": "Edital analisado da sessão",
        "created_at": ingestion_state.created_at if ingestion_state is not None else None,
        "updated_at": updated_at,
        "analysis_status": _bounded_edital_analysis_status(edital, ingestion_state, review_state),
        "topics_count": len(edital.topics),
        "subtopics_count": len(edital.subtopics),
        "bibliography_count": len(edital.bibliography),
        "gaps_count": len(alignment_result.gaps) if alignment_result is not None else 0,
        "review_state": review_state,
        "coverage_status": _bounded_edital_coverage_status(alignment_result),
        "alignment_status": _bounded_edital_alignment_status(alignment_state, alignment_result),
        "warnings_count": warnings_count,
    }


@router.get("/editais")
def list_editais(request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    items = [
        _bounded_edital_item(edital, repository, user_id)
        for edital in repository.list_user_edital_extractions(user_id=user_id)
    ]
    items.sort(
        key=lambda item: (
            item["updated_at"] or item["created_at"],
            item["title"],
            item["edital_id"],
        ),
        reverse=True,
    )
    return {
        "items": items,
        "count": len(items),
        "source": "user_scope",
    }


def _bounded_edital_summary_flags(summary: dict[str, object]) -> dict[str, object]:
    needs_review = summary["review_state"] != "ready_for_review"
    return {
        "has_topics": summary["topics_count"] > 0,
        "has_subtopics": summary["subtopics_count"] > 0,
        "has_bibliography": summary["bibliography_count"] > 0,
        "has_gaps": summary["gaps_count"] > 0,
        "needs_review": needs_review,
    }


def _coverage_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalized.lower())
        if len(token) >= 3
    }


def _coverage_material_contexts(
    repository: JsonStudyRepository,
    *,
    user_id: str,
    source_document_id: str,
) -> tuple[list[dict[str, object]], int]:
    contexts: list[dict[str, object]] = []
    out_of_scope_count = 0
    for material in repository.list_uploaded_materials(user_id=user_id):
        document_id = material.metadata.document_id
        if document_id == source_document_id:
            continue
        material_type = _uploaded_material_type(material)
        if material_type not in {"study_material", "bibliography", "previous_exam"}:
            out_of_scope_count += 1
            continue

        display_filename = _material_display_filename(
            material.metadata.original_filename,
            material.metadata.filename,
        )
        section_titles = [
            section.title
            for section in repository.list_document_sections(document_id, user_id=user_id)
            if section.title
        ]
        tokens = _coverage_tokens(" ".join([display_filename, material_type, *section_titles]))
        if not tokens:
            out_of_scope_count += 1
            continue
        contexts.append(
            {
                "document_id": document_id,
                "material_type": material_type,
                "tokens": tokens,
            }
        )
    return contexts, out_of_scope_count


def _coverage_match_state(
    *,
    topic_tokens: set[str],
    subtopic_tokens: set[str],
    contexts: list[dict[str, object]],
) -> str:
    if not subtopic_tokens and not topic_tokens:
        return "uncovered"

    target_tokens = subtopic_tokens or topic_tokens
    for context in contexts:
        context_tokens = context["tokens"]
        if not isinstance(context_tokens, set):
            continue
        subtopic_overlap = target_tokens & context_tokens
        topic_overlap = topic_tokens & context_tokens
        material_type = context["material_type"]
        if material_type == "study_material" and (
            len(subtopic_overlap) >= min(2, len(target_tokens))
            or (len(target_tokens) == 1 and bool(subtopic_overlap))
        ):
            return "covered"
        if subtopic_overlap or topic_overlap:
            return "partial"
    return "uncovered"


def _bounded_edital_coverage_response(
    edital,
    repository: JsonStudyRepository,
    user_id: str,
) -> dict[str, object]:
    summary = _bounded_edital_item(edital, repository, user_id)
    analysis_status = str(summary["analysis_status"])
    empty_response = {
        "edital_id": edital.edital_id,
        "analysis_status": analysis_status,
        "coverage_status": "not_ready" if analysis_status == "not_ready" else "unknown",
        "topics_count": len(edital.topics),
        "subtopics_count": len(edital.subtopics),
        "covered_subtopics_count": 0,
        "partial_subtopics_count": 0,
        "uncovered_subtopics_count": 0,
        "out_of_scope_materials_count": 0,
        "materials_considered_count": 0,
        "items": [],
        "source": "user_scope",
    }
    if analysis_status in {"not_ready", "failed", "unknown"}:
        return empty_response

    contexts, out_of_scope_count = _coverage_material_contexts(
        repository,
        user_id=user_id,
        source_document_id=edital.document_id,
    )
    subtopics_by_topic: dict[str, list[object]] = {}
    for subtopic in edital.subtopics:
        subtopics_by_topic.setdefault(subtopic.parent_topic_id, []).append(subtopic)

    items: list[dict[str, object]] = []
    covered_total = 0
    partial_total = 0
    uncovered_total = 0
    for topic in sorted(edital.topics, key=lambda item: item.order_index):
        topic_tokens = _coverage_tokens(topic.title)
        topic_subtopics = sorted(
            subtopics_by_topic.get(topic.topic_id, []),
            key=lambda item: item.order_index,
        )
        covered_count = 0
        partial_count = 0
        uncovered_count = 0
        for subtopic in topic_subtopics:
            state = _coverage_match_state(
                topic_tokens=topic_tokens,
                subtopic_tokens=_coverage_tokens(subtopic.title),
                contexts=contexts,
            )
            if state == "covered":
                covered_count += 1
            elif state == "partial":
                partial_count += 1
            else:
                uncovered_count += 1

        if topic_subtopics and covered_count == len(topic_subtopics):
            topic_status = "covered"
        elif covered_count or partial_count:
            topic_status = "partial"
        elif topic_subtopics:
            topic_status = "uncovered"
        else:
            topic_status = "needs_review"

        covered_total += covered_count
        partial_total += partial_count
        uncovered_total += uncovered_count
        items.append(
            {
                "topic_id": topic.topic_id,
                "label": topic.title,
                "subtopics_count": len(topic_subtopics),
                "covered_count": covered_count,
                "partial_count": partial_count,
                "uncovered_count": uncovered_count,
                "status": topic_status,
            }
        )

    if not edital.subtopics:
        coverage_status = "needs_review"
    elif covered_total == len(edital.subtopics):
        coverage_status = "ready_for_review"
    elif covered_total or partial_total:
        coverage_status = "partial"
    else:
        coverage_status = "needs_review"

    return {
        "edital_id": edital.edital_id,
        "analysis_status": analysis_status,
        "coverage_status": coverage_status,
        "topics_count": len(edital.topics),
        "subtopics_count": len(edital.subtopics),
        "covered_subtopics_count": covered_total,
        "partial_subtopics_count": partial_total,
        "uncovered_subtopics_count": uncovered_total,
        "out_of_scope_materials_count": out_of_scope_count,
        "materials_considered_count": len(contexts),
        "items": items,
        "source": "user_scope",
    }


@router.get("/editais/{edital_id}/summary")
def get_edital_summary(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    edital = repository.get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    summary = _bounded_edital_item(edital, repository, user_id)
    return {
        **summary,
        "summary": _bounded_edital_summary_flags(summary),
        "source": "user_scope",
    }


@router.get("/editais/{edital_id}/coverage")
def get_edital_coverage(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    repository = get_repository(request)
    edital = repository.get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    return _bounded_edital_coverage_response(edital, repository, user_id)


@router.get("/edital/{edital_id}")
def get_edital_by_id(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    return result


@router.post("/edital/{edital_id}/align-bibliography")
def align_edital_bibliography(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    state = get_bibliography_alignment_service(request).align_edital(edital_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    result = get_repository(request).get_bibliography_alignment_result(edital_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Bibliography alignment not found.")
    return result


@router.get("/edital/{edital_id}/alignment")
def get_edital_alignment(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    result = get_repository(request).get_bibliography_alignment_result(edital_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Bibliography alignment not found.")
    return result


@router.get("/alignment/{alignment_id}")
def get_alignment_by_id(alignment_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_repository(request).get_bibliography_alignment_by_id(alignment_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Bibliography alignment not found.")
    return result


@router.post("/edital/{edital_id}/curriculum-graph/build")
def build_curriculum_graph(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    state = get_curriculum_graph_builder_service(request).build_graph(edital_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Curriculum graph could not be built.")
    result = get_repository(request).get_curriculum_graph(edital_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Curriculum graph not found.")
    return result


@router.get("/edital/{edital_id}/curriculum-graph")
def get_curriculum_graph_for_edital(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    result = get_repository(request).get_curriculum_graph(edital_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Curriculum graph not found.")
    return result


@router.get("/curriculum-graph/{graph_id}")
def get_curriculum_graph_by_id(graph_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_repository(request).get_curriculum_graph_by_id(graph_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Curriculum graph not found.")
    return result


@router.post("/curriculum-graph/{graph_id}/study-cycle/build")
def build_study_cycle(graph_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    graph = get_repository(request).get_curriculum_graph_by_id(graph_id, user_id=user_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Curriculum graph not found.")
    state = get_study_cycle_orchestrator_service(request).build_cycle(graph_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Study cycle could not be built.")
    result = get_repository(request).get_study_cycle_plan(graph_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study cycle plan not found.")
    return result


@router.get("/curriculum-graph/{graph_id}/study-cycle")
def get_study_cycle_for_graph(graph_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    graph = get_repository(request).get_curriculum_graph_by_id(graph_id, user_id=user_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Curriculum graph not found.")
    result = get_repository(request).get_study_cycle_plan(graph_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study cycle plan not found.")
    return result


@router.get("/study-cycle/{cycle_id}")
def get_study_cycle_by_id(cycle_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_repository(request).get_study_cycle_plan_by_id(cycle_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study cycle plan not found.")
    return result


@router.post("/study-cycle/{cycle_id}/simulado-blueprint/build")
def build_simulado_blueprint(
    cycle_id: str,
    request: Request,
    payload: dict[str, object] = Body(default_factory=dict),
):
    user_id = _require_authenticated_user_id(request)
    cycle = get_repository(request).get_study_cycle_plan_by_id(cycle_id, user_id=user_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Study cycle plan not found.")
    profile_id = payload.get("profile_id")
    if profile_id is not None:
        profile_id = str(profile_id)
    state = get_simulado_blueprint_builder_service(request).build_blueprint(
        cycle_id,
        user_id=user_id,
        profile_id=profile_id,
    )
    if state is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint could not be built.")
    result = get_repository(request).get_simulado_blueprint(cycle_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    return result


@router.get("/study-cycle/{cycle_id}/simulado-blueprint")
def get_simulado_blueprint_for_cycle(cycle_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    cycle = get_repository(request).get_study_cycle_plan_by_id(cycle_id, user_id=user_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Study cycle plan not found.")
    result = get_repository(request).get_simulado_blueprint(cycle_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    return result


@router.get("/simulado-blueprint/{blueprint_id}")
def get_simulado_blueprint_by_id(blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_repository(request).get_simulado_blueprint_by_id(blueprint_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    return result


@router.post("/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build")
def build_question_generation_blueprint(blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint = get_repository(request).get_simulado_blueprint_by_id(blueprint_id, user_id=user_id)
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    result = get_question_generation_blueprint_service(request).build_blueprint_set(
        blueprint_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question generation blueprint could not be built.")
    return result


@router.get("/simulado-blueprint/{blueprint_id}/question-generation-blueprint")
def get_question_generation_blueprint_for_simulado(blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint = get_repository(request).get_simulado_blueprint_by_id(blueprint_id, user_id=user_id)
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    result = get_question_generation_blueprint_service(request).get_blueprint_set(
        blueprint_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question generation blueprint not found.")
    return result


@router.get("/question-generation-blueprint/{question_generation_blueprint_id}")
def get_question_generation_blueprint_by_id(question_generation_blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_question_generation_blueprint_service(request).get_blueprint_set_by_id(
        question_generation_blueprint_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question generation blueprint not found.")
    return result


@router.post("/question-generation-blueprint/{blueprint_set_id}/question-drafts/build")
def build_question_drafts(blueprint_set_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint_set = get_question_generation_blueprint_service(request).get_blueprint_set_by_id(
        blueprint_set_id,
        user_id=user_id,
    )
    if blueprint_set is None:
        raise HTTPException(status_code=404, detail="Question generation blueprint not found.")
    result = get_question_draft_generation_service(request).build_draft_set(
        blueprint_set_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question draft set could not be built.")
    return result


@router.get("/question-generation-blueprint/{blueprint_set_id}/question-drafts")
def get_question_drafts_for_blueprint(blueprint_set_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint_set = get_question_generation_blueprint_service(request).get_blueprint_set_by_id(
        blueprint_set_id,
        user_id=user_id,
    )
    if blueprint_set is None:
        raise HTTPException(status_code=404, detail="Question generation blueprint not found.")
    result = get_question_draft_generation_service(request).get_draft_set(
        blueprint_set_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question draft set not found.")
    return result


@router.get("/question-draft-set/{draft_set_id}")
def get_question_draft_set_by_id(draft_set_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_question_draft_generation_service(request).get_draft_set_by_id(
        draft_set_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Question draft set not found.")
    return result


@router.post("/question-drafts/{draft_id}/answer-explanation-guardrail/build")
def build_answer_explanation_guardrail(draft_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_answer_explanation_guardrail_service(request).build_guardrail(
        draft_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Answer explanation guardrail could not be built.")
    return result


@router.get("/question-drafts/{draft_id}/answer-explanation-guardrail")
def get_answer_explanation_guardrail_for_draft(draft_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_answer_explanation_guardrail_service(request).get_guardrail(
        draft_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Answer explanation guardrail not found.")
    return result


@router.get("/answer-explanation-guardrail/{guardrail_id}")
def get_answer_explanation_guardrail_by_id(guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_answer_explanation_guardrail_service(request).get_guardrail_by_id(
        guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Answer explanation guardrail not found.")
    return result


@router.post("/simulado-blueprint/{blueprint_id}/question-assembly/build")
def build_simulado_question_assembly(blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint = get_repository(request).get_simulado_blueprint_by_id(
        blueprint_id,
        user_id=user_id,
    )
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    result = get_simulado_question_assembly_service(request).build_assembly(
        blueprint_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado question assembly could not be built.")
    return result


@router.get("/simulado-blueprint/{blueprint_id}/question-assembly")
def get_simulado_question_assembly_for_blueprint(blueprint_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    blueprint = get_repository(request).get_simulado_blueprint_by_id(
        blueprint_id,
        user_id=user_id,
    )
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Simulado blueprint not found.")
    result = get_simulado_question_assembly_service(request).get_assembly(
        blueprint_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado question assembly not found.")
    return result


@router.get("/simulado-question-assembly/{assembly_id}")
def get_simulado_question_assembly_by_id(assembly_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_question_assembly_service(request).get_assembly_by_id(
        assembly_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado question assembly not found.")
    return result


@router.post("/simulado-question-assembly/{assembly_id}/attempt-shell/build")
def build_simulado_attempt_shell(assembly_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    assembly = get_simulado_question_assembly_service(request).get_assembly_by_id(
        assembly_id,
        user_id=user_id,
    )
    if assembly is None:
        raise HTTPException(status_code=404, detail="Simulado question assembly not found.")
    result = get_simulado_attempt_shell_service(request).build_attempt_shell(
        assembly_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt shell could not be built.")
    return result


@router.get("/simulado-question-assembly/{assembly_id}/attempt-shell")
def get_simulado_attempt_shell_for_assembly(assembly_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    assembly = get_simulado_question_assembly_service(request).get_assembly_by_id(
        assembly_id,
        user_id=user_id,
    )
    if assembly is None:
        raise HTTPException(status_code=404, detail="Simulado question assembly not found.")
    result = get_simulado_attempt_shell_service(request).get_attempt_shell(
        assembly_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt shell not found.")
    return result


@router.get("/simulado-attempt-shell/{attempt_shell_id}")
def get_simulado_attempt_shell_by_id(attempt_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_attempt_shell_service(request).get_attempt_shell_by_id(
        attempt_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt shell not found.")
    return result


@router.post("/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
def build_simulado_finalization_guardrail(attempt_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    attempt_shell = get_simulado_attempt_shell_service(request).get_attempt_shell_by_id(
        attempt_shell_id,
        user_id=user_id,
    )
    if attempt_shell is None:
        raise HTTPException(status_code=404, detail="Simulado attempt shell not found.")
    result = get_simulado_finalization_guardrails_service(request).build_guardrail(
        attempt_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado finalization guardrail could not be built.")
    return result


@router.get("/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail")
def get_simulado_finalization_guardrail_for_attempt_shell(attempt_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    attempt_shell = get_simulado_attempt_shell_service(request).get_attempt_shell_by_id(
        attempt_shell_id,
        user_id=user_id,
    )
    if attempt_shell is None:
        raise HTTPException(status_code=404, detail="Simulado attempt shell not found.")
    result = get_simulado_finalization_guardrails_service(request).get_guardrail(
        attempt_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado finalization guardrail not found.")
    return result


@router.get("/simulado-finalization-guardrail/{finalization_guardrail_id}")
def get_simulado_finalization_guardrail_by_id(finalization_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_finalization_guardrails_service(request).get_guardrail_by_id(
        finalization_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado finalization guardrail not found.")
    return result


@router.post("/simulado-finalization-guardrail/{finalization_guardrail_id}/final-approval/build")
def build_simulado_final_approval_artifact(
    finalization_guardrail_id: str,
    request: Request,
    payload: dict[str, object] | None = Body(default=None),
):
    user_id = _require_authenticated_user_id(request)
    guardrail = get_simulado_finalization_guardrails_service(request).get_guardrail_by_id(
        finalization_guardrail_id,
        user_id=user_id,
    )
    if guardrail is None:
        raise HTTPException(status_code=404, detail="Simulado finalization guardrail not found.")
    result = get_simulado_final_approval_service(request).build_approval_artifact(
        finalization_guardrail_id,
        user_id=user_id,
        decision_payload=payload,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado final approval artifact could not be built.")
    return result


@router.get("/simulado-finalization-guardrail/{finalization_guardrail_id}/final-approval")
def get_simulado_final_approval_artifact_for_guardrail(finalization_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    guardrail = get_simulado_finalization_guardrails_service(request).get_guardrail_by_id(
        finalization_guardrail_id,
        user_id=user_id,
    )
    if guardrail is None:
        raise HTTPException(status_code=404, detail="Simulado finalization guardrail not found.")
    result = get_simulado_final_approval_service(request).get_approval_artifact(
        finalization_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado final approval artifact not found.")
    return result


@router.get("/simulado-final-approval/{approval_artifact_id}")
def get_simulado_final_approval_artifact_by_id(approval_artifact_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_final_approval_service(request).get_approval_artifact_by_id(
        approval_artifact_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado final approval artifact not found.")
    return result


@router.post("/simulado-final-approval/{approval_artifact_id}/execution-shell/build")
def build_simulado_execution_shell(approval_artifact_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    approval_artifact = get_simulado_final_approval_service(request).get_approval_artifact_by_id(
        approval_artifact_id,
        user_id=user_id,
    )
    if approval_artifact is None:
        raise HTTPException(status_code=404, detail="Simulado final approval artifact not found.")
    result = get_simulado_execution_shell_service(request).build_execution_shell(
        approval_artifact_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado execution shell could not be built.")
    return result


@router.get("/simulado-final-approval/{approval_artifact_id}/execution-shell")
def get_simulado_execution_shell_for_approval(approval_artifact_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    approval_artifact = get_simulado_final_approval_service(request).get_approval_artifact_by_id(
        approval_artifact_id,
        user_id=user_id,
    )
    if approval_artifact is None:
        raise HTTPException(status_code=404, detail="Simulado final approval artifact not found.")
    result = get_simulado_execution_shell_service(request).get_execution_shell(
        approval_artifact_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado execution shell not found.")
    return result


@router.get("/simulado-execution-shell/{execution_shell_id}")
def get_simulado_execution_shell_by_id(execution_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_execution_shell_service(request).get_execution_shell_by_id(
        execution_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado execution shell not found.")
    return result


@router.post("/simulado-execution-shell/{execution_shell_id}/attempt-session/build")
def build_simulado_attempt_session(execution_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    execution_shell = get_simulado_execution_shell_service(request).get_execution_shell_by_id(
        execution_shell_id,
        user_id=user_id,
    )
    if execution_shell is None:
        raise HTTPException(status_code=404, detail="Simulado execution shell not found.")
    result = get_simulado_attempt_session_service(request).build_attempt_session(
        execution_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session could not be built.")
    return result


@router.get("/simulado-execution-shell/{execution_shell_id}/attempt-session")
def get_simulado_attempt_session_for_execution_shell(execution_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    execution_shell = get_simulado_execution_shell_service(request).get_execution_shell_by_id(
        execution_shell_id,
        user_id=user_id,
    )
    if execution_shell is None:
        raise HTTPException(status_code=404, detail="Simulado execution shell not found.")
    result = get_simulado_attempt_session_service(request).get_attempt_session(
        execution_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    return result


@router.get("/simulado-attempt-session/{attempt_session_id}")
def get_simulado_attempt_session_by_id(attempt_session_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_attempt_session_service(request).get_attempt_session_by_id(
        attempt_session_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    return result


@router.post("/simulado-attempt-session/{attempt_session_id}/answer-submission/build")
def build_simulado_answer_submission_for_attempt_session(
    attempt_session_id: str,
    request: Request,
    payload: dict[str, object] | None = Body(default=None),
):
    user_id = _require_authenticated_user_id(request)
    attempt_session = get_simulado_attempt_session_service(request).get_attempt_session_by_id(
        attempt_session_id,
        user_id=user_id,
    )
    if attempt_session is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    result = get_simulado_answer_submission_service(request).build_answer_submission(
        attempt_session_id,
        user_id=user_id,
        submission_payload=payload,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer submission could not be built.")
    return result


@router.get("/simulado-attempt-session/{attempt_session_id}/answer-submission")
def get_simulado_answer_submission_for_attempt_session(attempt_session_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    attempt_session = get_simulado_attempt_session_service(request).get_attempt_session_by_id(
        attempt_session_id,
        user_id=user_id,
    )
    if attempt_session is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    result = get_simulado_answer_submission_service(request).get_answer_submission(
        attempt_session_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer submission not found.")
    return result


@router.get("/simulado-answer-submission/{answer_submission_id}")
def get_simulado_answer_submission_by_id(answer_submission_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_answer_submission_service(request).get_answer_submission_by_id(
        answer_submission_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer submission not found.")
    return result


@router.post("/simulado-answer-submission/{answer_submission_id}/correction-shell/build")
def build_simulado_correction_shell_for_answer_submission(answer_submission_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    answer_submission = get_simulado_answer_submission_service(request).get_answer_submission_by_id(
        answer_submission_id,
        user_id=user_id,
    )
    if answer_submission is None:
        raise HTTPException(status_code=404, detail="Simulado answer submission not found.")
    result = get_simulado_correction_shell_service(request).build_correction_shell(
        answer_submission_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction shell could not be built.")
    return result


@router.get("/simulado-answer-submission/{answer_submission_id}/correction-shell")
def get_simulado_correction_shell_for_answer_submission(answer_submission_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    answer_submission = get_simulado_answer_submission_service(request).get_answer_submission_by_id(
        answer_submission_id,
        user_id=user_id,
    )
    if answer_submission is None:
        raise HTTPException(status_code=404, detail="Simulado answer submission not found.")
    result = get_simulado_correction_shell_service(request).get_correction_shell(
        answer_submission_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction shell not found.")
    return result


@router.get("/simulado-correction-shell/{correction_shell_id}")
def get_simulado_correction_shell_by_id(correction_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_correction_shell_service(request).get_correction_shell_by_id(
        correction_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction shell not found.")
    return result


@router.post("/simulado-correction-shell/{correction_shell_id}/answer-key-boundary/build")
def build_simulado_answer_key_boundary_for_correction_shell(correction_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    correction_shell = get_simulado_correction_shell_service(request).get_correction_shell_by_id(
        correction_shell_id,
        user_id=user_id,
    )
    if correction_shell is None:
        raise HTTPException(status_code=404, detail="Simulado correction shell not found.")
    result = get_simulado_answer_key_boundary_service(request).build_answer_key_boundary(
        correction_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer key boundary could not be built.")
    return result


@router.get("/simulado-correction-shell/{correction_shell_id}/answer-key-boundary")
def get_simulado_answer_key_boundary_for_correction_shell(correction_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    correction_shell = get_simulado_correction_shell_service(request).get_correction_shell_by_id(
        correction_shell_id,
        user_id=user_id,
    )
    if correction_shell is None:
        raise HTTPException(status_code=404, detail="Simulado correction shell not found.")
    result = get_simulado_answer_key_boundary_service(request).get_answer_key_boundary(
        correction_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer key boundary not found.")
    return result


@router.get("/simulado-answer-key-boundary/{answer_key_boundary_id}")
def get_simulado_answer_key_boundary_by_id(answer_key_boundary_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_answer_key_boundary_service(request).get_answer_key_boundary_by_id(
        answer_key_boundary_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado answer key boundary not found.")
    return result


@router.post("/simulado-answer-key-boundary/{answer_key_boundary_id}/correction-result/build")
def build_simulado_correction_result_for_answer_key_boundary(answer_key_boundary_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    boundary = get_simulado_answer_key_boundary_service(request).get_answer_key_boundary_by_id(
        answer_key_boundary_id,
        user_id=user_id,
    )
    if boundary is None:
        raise HTTPException(status_code=404, detail="Simulado answer key boundary not found.")
    result = get_simulado_correction_result_service(request).build_correction_result(
        answer_key_boundary_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction result could not be built.")
    return result


@router.get("/simulado-answer-key-boundary/{answer_key_boundary_id}/correction-result")
def get_simulado_correction_result_for_answer_key_boundary(answer_key_boundary_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    boundary = get_simulado_answer_key_boundary_service(request).get_answer_key_boundary_by_id(
        answer_key_boundary_id,
        user_id=user_id,
    )
    if boundary is None:
        raise HTTPException(status_code=404, detail="Simulado answer key boundary not found.")
    result = get_simulado_correction_result_service(request).get_correction_result(
        answer_key_boundary_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction result not found.")
    return result


@router.get("/simulado-correction-result/{correction_result_id}")
def get_simulado_correction_result_by_id(correction_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_correction_result_service(request).get_correction_result_by_id(
        correction_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado correction result not found.")
    return result


@router.post("/simulado-correction-result/{correction_result_id}/score/build")
def build_simulado_score_result_for_correction_result(correction_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    correction_result = get_simulado_correction_result_service(request).get_correction_result_by_id(
        correction_result_id,
        user_id=user_id,
    )
    if correction_result is None:
        raise HTTPException(status_code=404, detail="Simulado correction result not found.")
    result = get_simulado_scoring_service(request).build_score_result(
        correction_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado score result could not be built.")
    return result


@router.get("/simulado-correction-result/{correction_result_id}/score")
def get_simulado_score_result_for_correction_result(correction_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    correction_result = get_simulado_correction_result_service(request).get_correction_result_by_id(
        correction_result_id,
        user_id=user_id,
    )
    if correction_result is None:
        raise HTTPException(status_code=404, detail="Simulado correction result not found.")
    result = get_simulado_scoring_service(request).get_score_result(
        correction_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado score result not found.")
    return result


@router.get("/simulado-score-result/{score_result_id}")
def get_simulado_score_result_by_id(score_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_scoring_service(request).get_score_result_by_id(
        score_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado score result not found.")
    return result


@router.post("/simulado-score-result/{score_result_id}/progress-guardrail/build")
def build_simulado_progress_guardrail_for_score_result(score_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    score_result = get_simulado_scoring_service(request).get_score_result_by_id(
        score_result_id,
        user_id=user_id,
    )
    if score_result is None:
        raise HTTPException(status_code=404, detail="Simulado score result not found.")
    result = get_simulado_progress_guardrails_service(request).build_progress_guardrail(
        score_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado progress guardrail could not be built.")
    return result


@router.get("/simulado-score-result/{score_result_id}/progress-guardrail")
def get_simulado_progress_guardrail_for_score_result(score_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    score_result = get_simulado_scoring_service(request).get_score_result_by_id(
        score_result_id,
        user_id=user_id,
    )
    if score_result is None:
        raise HTTPException(status_code=404, detail="Simulado score result not found.")
    result = get_simulado_progress_guardrails_service(request).get_progress_guardrail(
        score_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado progress guardrail not found.")
    return result


@router.get("/simulado-progress-guardrail/{progress_guardrail_id}")
def get_simulado_progress_guardrail_by_id(progress_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_progress_guardrails_service(request).get_progress_guardrail_by_id(
        progress_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado progress guardrail not found.")
    return result


@router.post("/simulado-attempt-session/{attempt_session_id}/integrated-result/build")
def build_simulado_integrated_execution_correction_for_attempt_session(
    attempt_session_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    attempt_session = get_simulado_attempt_session_service(request).get_attempt_session_by_id(
        attempt_session_id,
        user_id=user_id,
    )
    if attempt_session is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    result = get_simulado_integrated_execution_correction_service(request).build_integrated_result(
        attempt_session_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado integrated execution/correction could not be built.")
    return result


@router.get("/simulado-attempt-session/{attempt_session_id}/integrated-result")
def get_simulado_integrated_execution_correction_for_attempt_session(attempt_session_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    attempt_session = get_simulado_attempt_session_service(request).get_attempt_session_by_id(
        attempt_session_id,
        user_id=user_id,
    )
    if attempt_session is None:
        raise HTTPException(status_code=404, detail="Simulado attempt session not found.")
    result = get_simulado_integrated_execution_correction_service(request).get_integrated_result(
        attempt_session_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado integrated execution/correction not found.")
    return result


@router.get("/simulado-integrated-result/{integrated_result_id}")
def get_simulado_integrated_execution_correction_by_id(integrated_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_integrated_execution_correction_service(request).get_integrated_result_by_id(
        integrated_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado integrated execution/correction not found.")
    return result


@router.post("/simulado-integrated-result/{integrated_result_id}/runtime-guardrail/build")
def build_simulado_runtime_application_guardrail_for_integrated_result(
    integrated_result_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    integrated_result = get_simulado_integrated_execution_correction_service(request).get_integrated_result_by_id(
        integrated_result_id,
        user_id=user_id,
    )
    if integrated_result is None:
        raise HTTPException(status_code=404, detail="Simulado integrated execution/correction not found.")
    result = get_simulado_runtime_application_guardrails_service(request).build_runtime_guardrail(
        integrated_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime application guardrail could not be built.")
    return result


@router.get("/simulado-integrated-result/{integrated_result_id}/runtime-guardrail")
def get_simulado_runtime_application_guardrail_for_integrated_result(integrated_result_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    integrated_result = get_simulado_integrated_execution_correction_service(request).get_integrated_result_by_id(
        integrated_result_id,
        user_id=user_id,
    )
    if integrated_result is None:
        raise HTTPException(status_code=404, detail="Simulado integrated execution/correction not found.")
    result = get_simulado_runtime_application_guardrails_service(request).get_runtime_guardrail(
        integrated_result_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime application guardrail not found.")
    return result


@router.get("/simulado-runtime-guardrail/{runtime_guardrail_id}")
def get_simulado_runtime_application_guardrail_by_id(runtime_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_application_guardrails_service(request).get_runtime_guardrail_by_id(
        runtime_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime application guardrail not found.")
    return result


@router.post("/simulado-runtime-guardrail/{runtime_guardrail_id}/progress-application/build")
def build_simulado_runtime_progress_application_for_runtime_guardrail(
    runtime_guardrail_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    runtime_guardrail = get_simulado_runtime_application_guardrails_service(request).get_runtime_guardrail_by_id(
        runtime_guardrail_id,
        user_id=user_id,
    )
    if runtime_guardrail is None:
        raise HTTPException(status_code=404, detail="Simulado runtime application guardrail not found.")
    result = get_simulado_runtime_progress_application_service(request).build_application(
        runtime_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress application could not be built.")
    return result


@router.get("/simulado-runtime-guardrail/{runtime_guardrail_id}/progress-application")
def get_simulado_runtime_progress_application_for_runtime_guardrail(runtime_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    runtime_guardrail = get_simulado_runtime_application_guardrails_service(request).get_runtime_guardrail_by_id(
        runtime_guardrail_id,
        user_id=user_id,
    )
    if runtime_guardrail is None:
        raise HTTPException(status_code=404, detail="Simulado runtime application guardrail not found.")
    result = get_simulado_runtime_progress_application_service(request).get_application(
        runtime_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress application not found.")
    return result


@router.get("/simulado-progress-application/{application_id}")
def get_simulado_runtime_progress_application_by_id(application_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_progress_application_service(request).get_application_by_id(
        application_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress application not found.")
    return result


@router.post("/simulado-progress-application/{application_id}/controlled-apply-shell/build")
def build_simulado_controlled_apply_shell_for_progress_application(
    application_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    application = get_simulado_runtime_progress_application_service(request).get_application_by_id(
        application_id,
        user_id=user_id,
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress application not found.")
    result = get_simulado_controlled_apply_shell_service(request).build_apply_shell(
        application_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled apply shell could not be built.")
    return result


@router.get("/simulado-progress-application/{application_id}/controlled-apply-shell")
def get_simulado_controlled_apply_shell_for_progress_application(application_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    application = get_simulado_runtime_progress_application_service(request).get_application_by_id(
        application_id,
        user_id=user_id,
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress application not found.")
    result = get_simulado_controlled_apply_shell_service(request).get_apply_shell(
        application_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled apply shell not found.")
    return result


@router.get("/simulado-controlled-apply-shell/{apply_shell_id}")
def get_simulado_controlled_apply_shell_by_id(apply_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_controlled_apply_shell_service(request).get_apply_shell_by_id(
        apply_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled apply shell not found.")
    return result


@router.post("/simulado-controlled-apply-shell/{apply_shell_id}/explicit-apply/build")
def build_simulado_explicit_runtime_apply_for_controlled_apply_shell(
    apply_shell_id: str,
    request: Request,
    decision_payload: dict[str, object] | None = Body(default=None),
):
    user_id = _require_authenticated_user_id(request)
    shell = get_simulado_controlled_apply_shell_service(request).get_apply_shell_by_id(
        apply_shell_id,
        user_id=user_id,
    )
    if shell is None:
        raise HTTPException(status_code=404, detail="Simulado controlled apply shell not found.")
    result = get_simulado_explicit_runtime_apply_service(request).build_explicit_apply(
        apply_shell_id,
        decision_payload=decision_payload,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime apply could not be built.")
    return result


@router.get("/simulado-controlled-apply-shell/{apply_shell_id}/explicit-apply")
def get_simulado_explicit_runtime_apply_for_controlled_apply_shell(apply_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    shell = get_simulado_controlled_apply_shell_service(request).get_apply_shell_by_id(
        apply_shell_id,
        user_id=user_id,
    )
    if shell is None:
        raise HTTPException(status_code=404, detail="Simulado controlled apply shell not found.")
    result = get_simulado_explicit_runtime_apply_service(request).get_explicit_apply(
        apply_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime apply not found.")
    return result


@router.get("/simulado-explicit-apply/{explicit_apply_id}")
def get_simulado_explicit_runtime_apply_by_id(explicit_apply_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_explicit_runtime_apply_service(request).get_explicit_apply_by_id(
        explicit_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime apply not found.")
    return result


@router.post("/simulado-explicit-apply/{explicit_apply_id}/progress-mutation/build")
def build_simulado_runtime_progress_mutation_for_explicit_apply(
    explicit_apply_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    explicit_apply = get_simulado_explicit_runtime_apply_service(request).get_explicit_apply_by_id(
        explicit_apply_id,
        user_id=user_id,
    )
    if explicit_apply is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime apply not found.")
    result = get_simulado_runtime_progress_mutation_service(request).build_mutation_transaction(
        explicit_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime progress mutation transaction could not be built.",
        )
    return result


@router.get("/simulado-explicit-apply/{explicit_apply_id}/progress-mutation")
def get_simulado_runtime_progress_mutation_for_explicit_apply(explicit_apply_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    explicit_apply = get_simulado_explicit_runtime_apply_service(request).get_explicit_apply_by_id(
        explicit_apply_id,
        user_id=user_id,
    )
    if explicit_apply is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime apply not found.")
    result = get_simulado_runtime_progress_mutation_service(request).get_mutation_transaction(
        explicit_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress mutation transaction not found.")
    return result


@router.get("/simulado-progress-mutation/{mutation_transaction_id}")
def get_simulado_runtime_progress_mutation_by_id(mutation_transaction_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_progress_mutation_service(request).get_mutation_transaction_by_id(
        mutation_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress mutation transaction not found.")
    return result


@router.post("/simulado-progress-mutation/{mutation_transaction_id}/commit-shell/build")
def build_simulado_controlled_mutation_commit_shell_for_mutation_transaction(
    mutation_transaction_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    transaction = get_simulado_runtime_progress_mutation_service(request).get_mutation_transaction_by_id(
        mutation_transaction_id,
        user_id=user_id,
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress mutation transaction not found.")
    result = get_simulado_controlled_mutation_commit_service(request).build_commit_shell(
        mutation_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled mutation commit shell could not be built.",
        )
    return result


@router.get("/simulado-progress-mutation/{mutation_transaction_id}/commit-shell")
def get_simulado_controlled_mutation_commit_shell_for_mutation_transaction(
    mutation_transaction_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    transaction = get_simulado_runtime_progress_mutation_service(request).get_mutation_transaction_by_id(
        mutation_transaction_id,
        user_id=user_id,
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Simulado runtime progress mutation transaction not found.")
    result = get_simulado_controlled_mutation_commit_service(request).get_commit_shell(
        mutation_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled mutation commit shell not found.")
    return result


@router.get("/simulado-mutation-commit-shell/{commit_shell_id}")
def get_simulado_controlled_mutation_commit_shell_by_id(commit_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_controlled_mutation_commit_service(request).get_commit_shell_by_id(
        commit_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled mutation commit shell not found.")
    return result


@router.post("/simulado-mutation-commit-shell/{commit_shell_id}/explicit-commit/build")
def build_simulado_explicit_mutation_commit_for_controlled_commit_shell(
    commit_shell_id: str,
    request: Request,
    decision_payload: dict[str, object] | None = Body(default=None),
):
    user_id = _require_authenticated_user_id(request)
    commit_shell = get_simulado_controlled_mutation_commit_service(request).get_commit_shell_by_id(
        commit_shell_id,
        user_id=user_id,
    )
    if commit_shell is None:
        raise HTTPException(status_code=404, detail="Simulado controlled mutation commit shell not found.")
    result = get_simulado_explicit_mutation_commit_service(request).build_explicit_commit(
        commit_shell_id,
        decision_payload=decision_payload,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime mutation commit could not be built.")
    return result


@router.get("/simulado-mutation-commit-shell/{commit_shell_id}/explicit-commit")
def get_simulado_explicit_mutation_commit_for_controlled_commit_shell(commit_shell_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    commit_shell = get_simulado_controlled_mutation_commit_service(request).get_commit_shell_by_id(
        commit_shell_id,
        user_id=user_id,
    )
    if commit_shell is None:
        raise HTTPException(status_code=404, detail="Simulado controlled mutation commit shell not found.")
    result = get_simulado_explicit_mutation_commit_service(request).get_explicit_commit(
        commit_shell_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime mutation commit not found.")
    return result


@router.get("/simulado-explicit-commit/{explicit_commit_id}")
def get_simulado_explicit_mutation_commit_by_id(explicit_commit_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_explicit_mutation_commit_service(request).get_explicit_commit_by_id(
        explicit_commit_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime mutation commit not found.")
    return result


@router.post("/simulado-explicit-commit/{explicit_commit_id}/commit-transaction/build")
def build_simulado_runtime_mutation_commit_transaction_for_explicit_commit(
    explicit_commit_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    explicit_commit = get_simulado_explicit_mutation_commit_service(request).get_explicit_commit_by_id(
        explicit_commit_id,
        user_id=user_id,
    )
    if explicit_commit is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime mutation commit not found.")
    result = get_simulado_runtime_mutation_commit_transaction_service(request).build_commit_transaction(
        explicit_commit_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime mutation commit transaction could not be built.",
        )
    return result


@router.get("/simulado-explicit-commit/{explicit_commit_id}/commit-transaction")
def get_simulado_runtime_mutation_commit_transaction_for_explicit_commit(
    explicit_commit_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    explicit_commit = get_simulado_explicit_mutation_commit_service(request).get_explicit_commit_by_id(
        explicit_commit_id,
        user_id=user_id,
    )
    if explicit_commit is None:
        raise HTTPException(status_code=404, detail="Simulado explicit runtime mutation commit not found.")
    result = get_simulado_runtime_mutation_commit_transaction_service(request).get_commit_transaction(
        explicit_commit_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime mutation commit transaction not found.")
    return result


@router.get("/simulado-commit-transaction/{commit_transaction_id}")
def get_simulado_runtime_mutation_commit_transaction_by_id(commit_transaction_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_mutation_commit_transaction_service(
        request
    ).get_commit_transaction_by_id(
        commit_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado runtime mutation commit transaction not found.")
    return result


@router.post("/simulado-commit-transaction/{commit_transaction_id}/execution-guardrail/build")
def build_simulado_controlled_commit_execution_guardrail_for_commit_transaction(
    commit_transaction_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    transaction = get_simulado_runtime_mutation_commit_transaction_service(
        request
    ).get_commit_transaction_by_id(
        commit_transaction_id,
        user_id=user_id,
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Simulado runtime mutation commit transaction not found.")
    result = get_simulado_controlled_commit_execution_guardrail_service(request).build_execution_guardrail(
        commit_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution guardrail could not be built.",
        )
    return result


@router.get("/simulado-commit-transaction/{commit_transaction_id}/execution-guardrail")
def get_simulado_controlled_commit_execution_guardrail_for_commit_transaction(
    commit_transaction_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    transaction = get_simulado_runtime_mutation_commit_transaction_service(
        request
    ).get_commit_transaction_by_id(
        commit_transaction_id,
        user_id=user_id,
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Simulado runtime mutation commit transaction not found.")
    result = get_simulado_controlled_commit_execution_guardrail_service(request).get_execution_guardrail(
        commit_transaction_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled runtime commit execution guardrail not found.")
    return result


@router.get("/simulado-commit-execution-guardrail/{execution_guardrail_id}")
def get_simulado_controlled_commit_execution_guardrail_by_id(execution_guardrail_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_controlled_commit_execution_guardrail_service(
        request
    ).get_execution_guardrail_by_id(
        execution_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulado controlled runtime commit execution guardrail not found.")
    return result


@router.post("/simulado-commit-execution-guardrail/{execution_guardrail_id}/explicit-execution-approval/build")
def build_simulado_explicit_commit_execution_approval_for_execution_guardrail(
    execution_guardrail_id: str,
    request: Request,
    decision_payload: dict[str, object] | None = Body(default=None),
):
    user_id = _require_authenticated_user_id(request)
    guardrail = get_simulado_controlled_commit_execution_guardrail_service(
        request
    ).get_execution_guardrail_by_id(
        execution_guardrail_id,
        user_id=user_id,
    )
    if guardrail is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution guardrail not found.",
        )
    result = get_simulado_explicit_commit_execution_approval_service(
        request
    ).build_execution_approval(
        execution_guardrail_id,
        decision_payload=decision_payload,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado explicit runtime commit execution approval could not be built.",
        )
    return result


@router.get("/simulado-commit-execution-guardrail/{execution_guardrail_id}/explicit-execution-approval")
def get_simulado_explicit_commit_execution_approval_for_execution_guardrail(
    execution_guardrail_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    guardrail = get_simulado_controlled_commit_execution_guardrail_service(
        request
    ).get_execution_guardrail_by_id(
        execution_guardrail_id,
        user_id=user_id,
    )
    if guardrail is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution guardrail not found.",
        )
    result = get_simulado_explicit_commit_execution_approval_service(
        request
    ).get_execution_approval(
        execution_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado explicit runtime commit execution approval not found.",
        )
    return result


@router.get("/simulado-explicit-execution-approval/{execution_approval_id}")
def get_simulado_explicit_commit_execution_approval_by_id(execution_approval_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_explicit_commit_execution_approval_service(
        request
    ).get_execution_approval_by_id(
        execution_approval_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado explicit runtime commit execution approval not found.",
        )
    return result


@router.post("/simulado-explicit-execution-approval/{execution_approval_id}/execution-plan/build")
def build_simulado_runtime_commit_execution_plan_for_execution_approval(
    execution_approval_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    approval = get_simulado_explicit_commit_execution_approval_service(
        request
    ).get_execution_approval_by_id(
        execution_approval_id,
        user_id=user_id,
    )
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado explicit runtime commit execution approval not found.",
        )
    result = get_simulado_runtime_commit_execution_plan_service(request).build_execution_plan(
        execution_approval_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime commit execution plan could not be built.",
        )
    return result


@router.get("/simulado-explicit-execution-approval/{execution_approval_id}/execution-plan")
def get_simulado_runtime_commit_execution_plan_for_execution_approval(
    execution_approval_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    approval = get_simulado_explicit_commit_execution_approval_service(
        request
    ).get_execution_approval_by_id(
        execution_approval_id,
        user_id=user_id,
    )
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado explicit runtime commit execution approval not found.",
        )
    result = get_simulado_runtime_commit_execution_plan_service(request).get_execution_plan(
        execution_approval_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime commit execution plan not found.",
        )
    return result


@router.get("/simulado-execution-plan/{execution_plan_id}")
def get_simulado_runtime_commit_execution_plan_by_id(execution_plan_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_commit_execution_plan_service(request).get_execution_plan_by_id(
        execution_plan_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime commit execution plan not found.",
        )
    return result


@router.post("/simulado-execution-plan/{execution_plan_id}/controlled-execution/build")
def build_simulado_controlled_runtime_commit_execution_for_execution_plan(
    execution_plan_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    execution_plan = get_simulado_runtime_commit_execution_plan_service(
        request
    ).get_execution_plan_by_id(
        execution_plan_id,
        user_id=user_id,
    )
    if execution_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime commit execution plan not found.",
        )
    result = get_simulado_controlled_runtime_commit_execution_service(
        request
    ).build_controlled_execution(
        execution_plan_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution could not be built.",
        )
    return result


@router.get("/simulado-execution-plan/{execution_plan_id}/controlled-execution")
def get_simulado_controlled_runtime_commit_execution_for_execution_plan(
    execution_plan_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    execution_plan = get_simulado_runtime_commit_execution_plan_service(
        request
    ).get_execution_plan_by_id(
        execution_plan_id,
        user_id=user_id,
    )
    if execution_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime commit execution plan not found.",
        )
    result = get_simulado_controlled_runtime_commit_execution_service(
        request
    ).get_controlled_execution(
        execution_plan_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution not found.",
        )
    return result


@router.get("/simulado-controlled-execution/{controlled_execution_id}")
def get_simulado_controlled_runtime_commit_execution_by_id(
    controlled_execution_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_controlled_runtime_commit_execution_service(
        request
    ).get_controlled_execution_by_id(
        controlled_execution_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution not found.",
        )
    return result


@router.post("/simulado-controlled-execution/{controlled_execution_id}/final-pedagogical-event/build")
def build_simulado_final_pedagogical_update_event_for_controlled_execution(
    controlled_execution_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    controlled_execution = get_simulado_controlled_runtime_commit_execution_service(
        request
    ).get_controlled_execution_by_id(
        controlled_execution_id,
        user_id=user_id,
    )
    if controlled_execution is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution not found.",
        )
    result = get_simulado_final_pedagogical_update_event_service(
        request
    ).build_final_event(
        controlled_execution_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado final pedagogical update event could not be built.",
        )
    return result


@router.get("/simulado-controlled-execution/{controlled_execution_id}/final-pedagogical-event")
def get_simulado_final_pedagogical_update_event_for_controlled_execution(
    controlled_execution_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    controlled_execution = get_simulado_controlled_runtime_commit_execution_service(
        request
    ).get_controlled_execution_by_id(
        controlled_execution_id,
        user_id=user_id,
    )
    if controlled_execution is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled runtime commit execution not found.",
        )
    result = get_simulado_final_pedagogical_update_event_service(
        request
    ).get_final_event(
        controlled_execution_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado final pedagogical update event not found.",
        )
    return result


@router.get("/simulado-final-pedagogical-event/{final_event_id}")
def get_simulado_final_pedagogical_update_event_by_id(
    final_event_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_final_pedagogical_update_event_service(
        request
    ).get_final_event_by_id(
        final_event_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado final pedagogical update event not found.",
        )
    return result


@router.post("/simulado-final-pedagogical-event/{final_event_id}/runtime-apply-policy/build")
def build_simulado_runtime_apply_policy_for_final_event(
    final_event_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    final_event = get_simulado_final_pedagogical_update_event_service(request).get_final_event_by_id(
        final_event_id,
        user_id=user_id,
    )
    if final_event is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado final pedagogical update event not found.",
        )
    result = get_simulado_runtime_apply_policy_service(request).build_runtime_apply_policy(
        final_event_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime apply policy could not be built.",
        )
    return result


@router.get("/simulado-final-pedagogical-event/{final_event_id}/runtime-apply-policy")
def get_simulado_runtime_apply_policy_for_final_event(
    final_event_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    final_event = get_simulado_final_pedagogical_update_event_service(request).get_final_event_by_id(
        final_event_id,
        user_id=user_id,
    )
    if final_event is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado final pedagogical update event not found.",
        )
    result = get_simulado_runtime_apply_policy_service(request).get_runtime_apply_policy(
        final_event_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime apply policy not found.",
        )
    return result


@router.get("/simulado-runtime-apply-policy/{runtime_apply_policy_id}")
def get_simulado_runtime_apply_policy_by_id(
    runtime_apply_policy_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_runtime_apply_policy_service(request).get_runtime_apply_policy_by_id(
        runtime_apply_policy_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime apply policy not found.",
        )
    return result


@router.post(
    "/simulado-runtime-apply-policy/{runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
)
def build_simulado_minimal_progress_ledger_apply_for_policy(
    runtime_apply_policy_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    policy = get_simulado_runtime_apply_policy_service(request).get_runtime_apply_policy_by_id(
        runtime_apply_policy_id,
        user_id=user_id,
    )
    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime apply policy not found.",
        )
    result = get_simulado_minimal_progress_ledger_apply_service(
        request
    ).build_minimal_progress_ledger_apply(
        runtime_apply_policy_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado minimal progress ledger apply could not be built.",
        )
    return result


@router.get("/simulado-runtime-apply-policy/{runtime_apply_policy_id}/minimal-progress-ledger-apply")
def get_simulado_minimal_progress_ledger_apply_for_policy(
    runtime_apply_policy_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    policy = get_simulado_runtime_apply_policy_service(request).get_runtime_apply_policy_by_id(
        runtime_apply_policy_id,
        user_id=user_id,
    )
    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado runtime apply policy not found.",
        )
    result = get_simulado_minimal_progress_ledger_apply_service(
        request
    ).get_minimal_progress_ledger_apply(
        runtime_apply_policy_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado minimal progress ledger apply not found.",
        )
    return result


@router.get("/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}")
def get_simulado_minimal_progress_ledger_apply_by_id(
    minimal_progress_ledger_apply_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_minimal_progress_ledger_apply_service(
        request
    ).get_minimal_progress_ledger_apply_by_id(
        minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado minimal progress ledger apply not found.",
        )
    return result


@router.post(
    "/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}/applied-event-ledger/build"
)
def build_simulado_applied_event_ledger_for_minimal_apply(
    minimal_progress_ledger_apply_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_apply = get_simulado_minimal_progress_ledger_apply_service(
        request
    ).get_minimal_progress_ledger_apply_by_id(
        minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    if source_apply is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado minimal progress ledger apply not found.",
        )
    result = get_simulado_applied_event_ledger_service(request).build_applied_event_ledger(
        minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado applied event ledger could not be built.",
        )
    return result


@router.get(
    "/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}/applied-event-ledger"
)
def get_simulado_applied_event_ledger_for_minimal_apply(
    minimal_progress_ledger_apply_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_apply = get_simulado_minimal_progress_ledger_apply_service(
        request
    ).get_minimal_progress_ledger_apply_by_id(
        minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    if source_apply is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado minimal progress ledger apply not found.",
        )
    result = get_simulado_applied_event_ledger_service(request).get_applied_event_ledger(
        minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado applied event ledger not found.",
        )
    return result


@router.get("/simulado-applied-event-ledger/{applied_event_ledger_id}")
def get_simulado_applied_event_ledger_by_id(
    applied_event_ledger_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_applied_event_ledger_service(
        request
    ).get_applied_event_ledger_by_id(
        applied_event_ledger_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado applied event ledger not found.",
        )
    return result


@router.post(
    "/simulado-applied-event-ledger/{applied_event_ledger_id}/propagation-guardrail/build"
)
def build_simulado_propagation_guardrail_for_applied_event_ledger(
    applied_event_ledger_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_ledger = get_simulado_applied_event_ledger_service(request).get_applied_event_ledger_by_id(
        applied_event_ledger_id,
        user_id=user_id,
    )
    if source_ledger is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado applied event ledger not found.",
        )
    result = get_simulado_propagation_guardrail_service(request).build_propagation_guardrail(
        applied_event_ledger_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado propagation guardrail could not be built.",
        )
    return result


@router.get("/simulado-applied-event-ledger/{applied_event_ledger_id}/propagation-guardrail")
def get_simulado_propagation_guardrail_for_applied_event_ledger(
    applied_event_ledger_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_ledger = get_simulado_applied_event_ledger_service(request).get_applied_event_ledger_by_id(
        applied_event_ledger_id,
        user_id=user_id,
    )
    if source_ledger is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado applied event ledger not found.",
        )
    result = get_simulado_propagation_guardrail_service(request).get_propagation_guardrail(
        applied_event_ledger_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado propagation guardrail not found.",
        )
    return result


@router.get("/simulado-propagation-guardrail/{propagation_guardrail_id}")
def get_simulado_propagation_guardrail_by_id(
    propagation_guardrail_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_propagation_guardrail_service(request).get_propagation_guardrail_by_id(
        propagation_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado propagation guardrail not found.",
        )
    return result


@router.post(
    "/simulado-propagation-guardrail/{propagation_guardrail_id}/controlled-propagation-apply/build"
)
def build_simulado_controlled_propagation_apply_for_guardrail(
    propagation_guardrail_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_guardrail = get_simulado_propagation_guardrail_service(
        request
    ).get_propagation_guardrail_by_id(
        propagation_guardrail_id,
        user_id=user_id,
    )
    if source_guardrail is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado propagation guardrail not found.",
        )
    result = get_simulado_controlled_propagation_apply_service(
        request
    ).build_controlled_propagation_apply(
        propagation_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled propagation apply could not be built.",
        )
    return result


@router.get(
    "/simulado-propagation-guardrail/{propagation_guardrail_id}/controlled-propagation-apply"
)
def get_simulado_controlled_propagation_apply_for_guardrail(
    propagation_guardrail_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    source_guardrail = get_simulado_propagation_guardrail_service(
        request
    ).get_propagation_guardrail_by_id(
        propagation_guardrail_id,
        user_id=user_id,
    )
    if source_guardrail is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado propagation guardrail not found.",
        )
    result = get_simulado_controlled_propagation_apply_service(
        request
    ).get_controlled_propagation_apply(
        propagation_guardrail_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled propagation apply not found.",
        )
    return result


@router.get("/simulado-controlled-propagation-apply/{controlled_propagation_apply_id}")
def get_simulado_controlled_propagation_apply_by_id(
    controlled_propagation_apply_id: str,
    request: Request,
):
    user_id = _require_authenticated_user_id(request)
    result = get_simulado_controlled_propagation_apply_service(
        request
    ).get_controlled_propagation_apply_by_id(
        controlled_propagation_apply_id,
        user_id=user_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Simulado controlled propagation apply not found.",
        )
    return result


@router.get("/dashboard/overview")
def get_dashboard_overview(request: Request):
    user_id = _require_authenticated_user_id(request)
    return get_user_dashboard_service(request).build_overview(user_id)


@router.get("/exam-profiles")
def list_exam_profiles(request: Request):
    return get_exam_profile_service(request).list_exam_profiles()


@router.get("/exam-profiles/{profile_id}")
def get_exam_profile(profile_id: str, request: Request):
    profile = get_exam_profile_service(request).get_exam_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Exam profile not found.")
    return profile


@router.post("/edital/{edital_id}/exam-profile/suggest")
def suggest_exam_profile(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    suggestion = get_exam_profile_service(request).suggest_exam_profile_from_edital(edital)
    if suggestion is None:
        return {
            "profile_id": None,
            "board_id": None,
            "exam_board": None,
            "profile_name": None,
            "exam_family": None,
            "format_type": "unknown",
            "confidence": 0.0,
            "heuristic_confidence": 0.0,
            "format_confidence": 0.0,
            "board_confidence": 0.0,
            "family_confidence": 0.0,
            "scoring_confidence": 0.0,
            "reasoning": ["No stable exam board, family or format signal was found."],
            "selection_reasoning": ["No stable exam board, family or format signal was found."],
            "format_evidence": [],
            "scoring_evidence": [],
            "family_evidence": [],
            "board_evidence": [],
            "warnings": [],
            "metadata": {"edital_id": edital_id, "negative_marking_confirmed": False},
        }
    return suggestion


@router.get("/edital/{edital_id}/exam-profile/suggestion")
def get_exam_profile_suggestion(edital_id: str, request: Request):
    user_id = _require_authenticated_user_id(request)
    edital = get_repository(request).get_edital_extraction_by_id(edital_id, user_id=user_id)
    if edital is None:
        raise HTTPException(status_code=404, detail="Edital extraction not found.")
    suggestion = get_exam_profile_service(request).suggest_exam_profile_from_edital(edital)
    if suggestion is None:
        return {
            "profile_id": None,
            "board_id": None,
            "exam_board": None,
            "profile_name": None,
            "exam_family": None,
            "format_type": "unknown",
            "confidence": 0.0,
            "heuristic_confidence": 0.0,
            "format_confidence": 0.0,
            "board_confidence": 0.0,
            "family_confidence": 0.0,
            "scoring_confidence": 0.0,
            "reasoning": ["No stable exam board, family or format signal was found."],
            "selection_reasoning": ["No stable exam board, family or format signal was found."],
            "format_evidence": [],
            "scoring_evidence": [],
            "family_evidence": [],
            "board_evidence": [],
            "warnings": [],
            "metadata": {"edital_id": edital_id, "negative_marking_confirmed": False},
        }
    return suggestion


@router.post("/session/start")
def start_session(
    request: Request,
    payload: SessionStartRequest = Body(default_factory=SessionStartRequest),
):
    repository = _scoped_repository(request)
    plan = LearningDecisionEngine(repository).build_review_plan(
        title=payload.title,
        max_questions=payload.max_questions,
    )
    session = get_session_manager(request).create_session(
        plan,
        user_id=_current_user_id(request),
    )
    return {
        "session_id": session.session_id,
        "first_block": get_session_manager(request).current_block(
            session.session_id,
            user_id=_current_user_id(request),
        ),
    }


@router.get("/session/{session_id}/current")
def get_current_session_block(session_id: str, request: Request):
    user_id = _current_user_id(request)
    session = get_session_manager(request).get_session(session_id, user_id=user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    current_block = get_session_manager(request).current_block(session_id, user_id=user_id)
    if current_block is None:
        return {"completed": True}
    return current_block


@router.post("/session/{session_id}/answer")
def submit_session_answer(
    session_id: str,
    request: Request,
    submission: SessionAnswerRequest | None = None,
):
    session_manager = get_session_manager(request)
    user_id = _current_user_id(request)
    session = session_manager.get_session(session_id, user_id=user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_block = session_manager.current_block(session_id, user_id=user_id)
    if current_block is None:
        return {"completed": True}

    if current_block["type"] == "summary":
        session_manager.advance(session_id, user_id=user_id)
        next_block = session_manager.current_block(session_id, user_id=user_id)
        return {"completed": next_block is None, "next_block": next_block}

    if submission is None:
        raise HTTPException(status_code=400, detail="Answer payload is required.")
    if submission.question_id != current_block["question_id"]:
        raise HTTPException(status_code=400, detail="Question ID inconsistente.")
    if submission.user_answer is None or submission.correct_answer is None:
        raise HTTPException(status_code=400, detail="Incomplete answer payload.")

    is_correct = _record_feedback_answer(
        _scoped_repository(request),
        FeedbackAnswerSubmission(
            topic_id=current_block["topic_id"],
            question_id=submission.question_id,
            microtopic_id=current_block.get("microtopic_id"),
            pedagogical_mode=current_block.get("pedagogical_mode") or submission.pedagogical_mode,
            user_answer=submission.user_answer,
            correct_answer=submission.correct_answer,
            error_type=submission.error_type,
        ),
    )
    session_manager.advance(session_id, user_id=user_id)
    next_block = session_manager.current_block(session_id, user_id=user_id)
    if next_block is None:
        return {"correct": is_correct, "completed": True}
    return {
        "correct": is_correct,
        "completed": False,
        "next_block": next_block,
    }


@router.get("/progress")
def get_progress(request: Request):
    return _scoped_repository(request).load_progress()


@router.get("/reviews/daily")
def get_daily_review(request: Request):
    return ReviewService(_scoped_repository(request)).build_daily_review()


@router.get("/reviews/blocks/latest")
def get_latest_block_review(request: Request):
    review = ReviewService(_scoped_repository(request)).build_latest_block_review()
    if review is None:
        raise HTTPException(status_code=404, detail="Ainda nao existem 3 PDFs processados.")
    return review


@router.get("/inspection/runtime")
def get_runtime_inspection(request: Request):
    require_inspection_access(request)
    return _inspection_payload(
        get_session_manager(request),
        get_repository(request),
        user_id=_current_user_id(request),
    )


@router.get("/inspection/runtime/export")
def export_runtime_inspection_snapshot(request: Request):
    require_inspection_access(request)
    payload = _inspection_payload(
        get_session_manager(request),
        get_repository(request),
        user_id=_current_user_id(request),
    )
    return export_inspection_snapshot(payload).snapshot_envelope.model_dump(mode="json")


def ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "index.html"


def inspection_ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "inspection.html"


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(ui_path())
