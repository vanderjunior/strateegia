from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    AnswerSubmission as FeedbackAnswerSubmission,
    SessionAnswerRequest,
    SessionStartRequest,
)
from app.domain.models import AnswerSubmission, BoardStyle, ProgressState
from app.repositories.json_store import JsonStudyRepository
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
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
from app.services.tuning_profile_benchmark_comparison import (
    compare_tuning_profiles_against_benchmark,
)


router = APIRouter(prefix="/api")


def get_repository(request: Request) -> JsonStudyRepository:
    return request.app.state.repository


def get_pipeline(request: Request) -> StudyPipeline:
    return request.app.state.pipeline


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def _inspection_defaults() -> dict[str, object]:
    registry = build_controlled_tuning_experiment_registry()
    comparison = compare_tuning_profiles_against_benchmark(registry=registry)
    return {
        "inspection_available": False,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {
            "session_id": None,
            "completed": None,
            "current_block_index": None,
            "total_blocks": 0,
            "current_block_type": None,
            "topic_id": None,
        },
        "benchmark_summary": {
            "pedagogical_benchmark_state": "not_available",
            "pedagogical_benchmark_summary": "No runtime data available.",
            "benchmark_readiness": "benchmark_insufficient",
            "benchmark_alignment_score": 0.0,
            "benchmark_regression_severity": "none",
            "benchmark_total_cases": 0,
            "benchmark_passed_cases": [],
            "benchmark_failed_cases": [],
            "benchmark_inconclusive_cases": [],
            "benchmark_regression_cases": [],
        },
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": registry.model_dump(mode="json"),
        "tuning_profile_benchmark_comparison": comparison.model_dump(mode="json"),
        "manual_experiment_inspection": build_manual_experiment_inspection(
            registry=registry,
            comparison=comparison,
        ).model_dump(mode="json"),
        "longitudinal_retention": observe_longitudinal_retention(
            progress=ProgressState(),
            runtime_block={},
        ).model_dump(mode="json"),
        "raw_runtime_block": {},
    }


def _inspection_payload(
    session_manager: SessionManager,
    repository: JsonStudyRepository,
) -> dict[str, object]:
    payload = _inspection_defaults()
    progress = repository.load_progress()
    context = session_manager.latest_inspection_context()
    if context is None:
        payload["longitudinal_retention"] = observe_longitudinal_retention(
            progress=progress,
            runtime_block={},
        ).model_dump(mode="json")
        return payload

    block = dict(context.get("block") or {})
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
        "pedagogical_benchmark_state": block.get("pedagogical_benchmark_state", "not_available"),
        "pedagogical_benchmark_summary": block.get("pedagogical_benchmark_summary", ""),
        "benchmark_readiness": block.get("benchmark_readiness", "benchmark_insufficient"),
        "benchmark_alignment_score": block.get("benchmark_alignment_score", 0.0),
        "benchmark_regression_severity": block.get("benchmark_regression_severity", "none"),
        "benchmark_total_cases": block.get("benchmark_total_cases", 0),
        "benchmark_passed_cases": block.get("benchmark_passed_cases", []),
        "benchmark_failed_cases": block.get("benchmark_failed_cases", []),
        "benchmark_inconclusive_cases": block.get("benchmark_inconclusive_cases", []),
        "benchmark_regression_cases": block.get("benchmark_regression_cases", []),
    }
    payload["benchmark_case_reports"] = list(block.get("benchmark_case_reports") or [])
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
        "retrieval_delta": block.get("retrieval_delta", 0.0),
        "scaffold_delta": block.get("scaffold_delta", 0.0),
        "compression_delta": block.get("compression_delta", 0.0),
        "continuity_delta": block.get("continuity_delta", 0.0),
        "reconstruction_delta": block.get("reconstruction_delta", 0.0),
        "pacing_delta": block.get("pacing_delta", 0.0),
        "validation_delta": block.get("validation_delta", 0.0),
        "sustainability_delta": block.get("sustainability_delta", 0.0),
        "pedagogical_regression_signal": block.get("pedagogical_regression_signal", ""),
    }
    payload["session_export_debug"] = {
        "session_export_state": block.get("session_export_state", ""),
        "runtime_export_summary": block.get("runtime_export_summary", ""),
        "behavioral_diff_snapshot": block.get("behavioral_diff_snapshot", {}),
        "runtime_trace_snapshot": block.get("runtime_trace_snapshot", {}),
        "stability_snapshot": block.get("stability_snapshot", {}),
        "tuning_snapshot": block.get("tuning_snapshot", {}),
        "compression_snapshot": block.get("compression_snapshot", {}),
        "continuity_snapshot": block.get("continuity_snapshot", {}),
        "support_snapshot": block.get("support_snapshot", {}),
        "retrieval_snapshot": block.get("retrieval_snapshot", {}),
        "reconstruction_snapshot": block.get("reconstruction_snapshot", {}),
    }
    payload["stability_metrics"] = {
        "session_stability_state": block.get("session_stability_state", ""),
        "retrieval_density_metric": block.get("retrieval_density_metric", 0.0),
        "scaffold_load_metric": block.get("scaffold_load_metric", 0.0),
        "continuity_smoothness_metric": block.get("continuity_smoothness_metric", 0.0),
        "reconstruction_pressure_metric": block.get("reconstruction_pressure_metric", 0.0),
        "compression_safety_metric": block.get("compression_safety_metric", 0.0),
        "pacing_stability_metric": block.get("pacing_stability_metric", 0.0),
        "cognitive_balance_metric": block.get("cognitive_balance_metric", 0.0),
    }
    payload["validation_dataset_awareness"] = {
        "validation_dataset_state": block.get("validation_dataset_state", ""),
        "pedagogical_scenario_family": block.get("pedagogical_scenario_family", ""),
        "runtime_validation_context": block.get("runtime_validation_context", ""),
        "comparative_validation_alignment": block.get("comparative_validation_alignment", 0.0),
        "dataset_awareness_summary": block.get("dataset_awareness_summary", ""),
    }
    registry = build_controlled_tuning_experiment_registry()
    payload["controlled_tuning_registry"] = registry.model_dump(mode="json")
    comparison = compare_tuning_profiles_against_benchmark(
        registry=registry,
        benchmark_result={"benchmark_case_reports": block.get("benchmark_case_reports", [])},
    )
    payload["tuning_profile_benchmark_comparison"] = comparison.model_dump(mode="json")
    payload["manual_experiment_inspection"] = build_manual_experiment_inspection(
        registry=registry,
        comparison=comparison,
    ).model_dump(mode="json")
    payload["longitudinal_retention"] = observe_longitudinal_retention(
        progress=progress,
        runtime_block=block,
    ).model_dump(mode="json")
    payload["raw_runtime_block"] = block
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
    get_repository(request).save_document(document)
    return document


@router.get("/documents")
def list_documents(request: Request):
    return get_repository(request).list_documents()


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request):
    document = get_repository(request).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento nao encontrado.")
    return document


@router.post("/questions/{question_id}/answer")
def submit_answer(question_id: str, submission: AnswerSubmission, request: Request):
    if submission.question_id != question_id:
        raise HTTPException(status_code=400, detail="Question ID inconsistente.")
    get_repository(request).record_answer(submission)
    return {"status": "recorded"}


@router.post("/answers/submit")
def submit_feedback_answer(submission: FeedbackAnswerSubmission, request: Request):
    is_correct = _record_feedback_answer(get_repository(request), submission)
    return {
        "correct": is_correct,
        "message": "Answer recorded",
    }


@router.post("/session/start")
def start_session(
    request: Request,
    payload: SessionStartRequest = Body(default_factory=SessionStartRequest),
):
    repository = get_repository(request)
    plan = LearningDecisionEngine(repository).build_review_plan(
        title=payload.title,
        max_questions=payload.max_questions,
    )
    session = get_session_manager(request).create_session(plan)
    return {
        "session_id": session.session_id,
        "first_block": get_session_manager(request).current_block(session.session_id),
    }


@router.get("/session/{session_id}/current")
def get_current_session_block(session_id: str, request: Request):
    session = get_session_manager(request).get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    current_block = get_session_manager(request).current_block(session_id)
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
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_block = session_manager.current_block(session_id)
    if current_block is None:
        return {"completed": True}

    if current_block["type"] == "summary":
        session_manager.advance(session_id)
        next_block = session_manager.current_block(session_id)
        return {"completed": next_block is None, "next_block": next_block}

    if submission is None:
        raise HTTPException(status_code=400, detail="Answer payload is required.")
    if submission.question_id != current_block["question_id"]:
        raise HTTPException(status_code=400, detail="Question ID inconsistente.")
    if submission.user_answer is None or submission.correct_answer is None:
        raise HTTPException(status_code=400, detail="Incomplete answer payload.")

    is_correct = _record_feedback_answer(
        get_repository(request),
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
    session_manager.advance(session_id)
    next_block = session_manager.current_block(session_id)
    if next_block is None:
        return {"correct": is_correct, "completed": True}
    return {
        "correct": is_correct,
        "completed": False,
        "next_block": next_block,
    }


@router.get("/progress")
def get_progress(request: Request):
    return get_repository(request).load_progress()


@router.get("/reviews/daily")
def get_daily_review(request: Request):
    return ReviewService(get_repository(request)).build_daily_review()


@router.get("/reviews/blocks/latest")
def get_latest_block_review(request: Request):
    review = ReviewService(get_repository(request)).build_latest_block_review()
    if review is None:
        raise HTTPException(status_code=404, detail="Ainda nao existem 3 PDFs processados.")
    return review


@router.get("/inspection/runtime")
def get_runtime_inspection(request: Request):
    return _inspection_payload(get_session_manager(request), get_repository(request))


def ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "index.html"


def inspection_ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "inspection.html"


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(ui_path())
