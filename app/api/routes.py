from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    AnswerSubmission as FeedbackAnswerSubmission,
    SessionAnswerRequest,
    UserLoginRequest,
    UserRegisterRequest,
    SessionStartRequest,
)
from app.config import inspection_enabled, inspection_requires_auth
from app.domain.models import AnswerSubmission, BoardStyle, ProgressState
from app.repositories.json_store import JsonStudyRepository
from app.services.document_ingestion import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES
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
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
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
from app.services.user_service import LocalUserService


router = APIRouter(prefix="/api")
SESSION_COOKIE_NAME = "studyflow_session"


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


@router.post("/materials/upload", status_code=201)
async def upload_material(request: Request, file: UploadFile = File(...)):
    user_id = _require_authenticated_user_id(request)
    original_name = file.filename or "material"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported material type.")
    payload = await file.read()
    if len(payload) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Upload size exceeds the supported limit.")
    material = get_material_service(request).register_upload(
        user_id=user_id,
        original_filename=original_name,
        content_type=file.content_type or "",
        payload=payload,
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
