from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    AnswerSubmission as FeedbackAnswerSubmission,
    SessionAnswerRequest,
    SessionStartRequest,
)
from app.domain.models import AnswerSubmission, BoardStyle
from app.repositories.json_store import JsonStudyRepository
from app.services.learning_engine import LearningDecisionEngine
from app.services.pipeline import StudyPipeline
from app.services.reviews import ReviewService
from app.services.session_flow import SessionManager


router = APIRouter(prefix="/api")


def get_repository(request: Request) -> JsonStudyRepository:
    return request.app.state.repository


def get_pipeline(request: Request) -> StudyPipeline:
    return request.app.state.pipeline


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


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


def ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "index.html"


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(ui_path())
