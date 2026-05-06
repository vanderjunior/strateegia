from io import BytesIO

from fastapi.testclient import TestClient

from app.domain.models import (
    AnswerSubmission,
    BoardStyle,
    Document,
    ErrorType,
    GeneratedQuestion,
    Topic,
)
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


class FakePipeline:
    def process_pdf(self, *, filename, payload, board, exam_context):
        topic = Topic(
            id="topic-1",
            title="Competencia Tributaria",
            content="A competencia tributaria e indelegavel e decorre da Constituicao.",
            key_points=["Competencia e indelegavel."],
            trap_points=["Nao confundir competencia com capacidade tributaria ativa."],
            relevance_score=0.95,
            source_pages=[1],
        )
        question = GeneratedQuestion(
            id="q1",
            document_id="doc-1",
            topic_id="topic-1",
            style="multiple_choice",
            stem="Sobre competencia tributaria, assinale a alternativa correta.",
            options=[
                "Pode ser delegada por lei ordinaria.",
                "Decorre apenas de decreto regulamentar.",
                "E indelegavel e decorre da Constituicao.",
                "Se confunde com capacidade ativa.",
            ],
            correct_answer="C",
            explanation="A competencia tributaria e prevista na Constituicao e nao pode ser delegada.",
        )
        return Document.create(
            title="PDF Processado",
            source_filename=filename,
            board=board,
            exam_context=exam_context,
            source_excerpt="Trecho original sintetico",
            topics=[topic],
            summaries=[],
            questions=[question],
        )


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository, pipeline=FakePipeline())
    return TestClient(app), repository


def test_upload_pdf_returns_processed_document(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("aula.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")},
        data={"board": "fgv", "exam_context": "Receita Federal"},
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["title"] == "PDF Processado"
    assert payload["topics"][0]["title"] == "Competencia Tributaria"


def test_upload_pdf_rejects_invalid_extension(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("aula.txt", BytesIO(b"texto"), "text/plain")},
        data={"board": "fgv", "exam_context": "Receita Federal"},
    )

    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


def test_answer_submission_updates_progress(tmp_path):
    client, repository = create_client(tmp_path)
    document = FakePipeline().process_pdf(
        filename="aula.pdf",
        payload=b"",
        board=BoardStyle.FGV,
        exam_context="Receita Federal",
    )
    repository.save_document(document)

    response = client.post(
        "/api/questions/q1/answer",
        json=AnswerSubmission(
            question_id="q1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="A",
            is_correct=False,
            error_type=ErrorType.INTERPRETATION,
        ).model_dump(mode="json"),
    )

    progress = repository.load_progress()

    assert response.status_code == 200
    assert progress.total_errors == 1
    assert progress.error_buckets[ErrorType.INTERPRETATION] == 1


def test_daily_review_returns_recent_content(tmp_path):
    client, repository = create_client(tmp_path)

    for index in range(2):
        document = FakePipeline().process_pdf(
            filename=f"aula_{index}.pdf",
            payload=b"",
            board=BoardStyle.FGV,
            exam_context="Receita Federal",
        )
        repository.save_document(document)

    response = client.get("/api/reviews/daily")

    payload = response.json()

    assert response.status_code == 200
    assert 3 <= len(payload["questions"]) <= 5
    assert payload["documents_considered"]
