from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=(
            f"{title} exige precisao normativa e comparacoes tecnicas. "
            f"{title} aparece em prova com excecoes, pegadinhas e termos absolutos."
        ),
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.85,
        source_pages=[1],
    )
    document = Document.create(
        title=title,
        source_filename=f"{title}.pdf",
        board=BoardStyle.CEBRASPE,
        exam_context="Marinha",
        source_excerpt=f"Trecho de {title}",
        topics=[topic],
        summaries=[],
        questions=[
            GeneratedQuestion(
                id=question_id,
                document_id="placeholder",
                topic_id=topic_id,
                style="certo_errado",
                stem=f"Julgue item sobre {title}.",
                options=["Certo", "Errado"],
                correct_answer="Certo",
                explanation=f"Explicacao de {title}",
                difficulty_level=1,
            )
        ],
    )
    document.created_at = created_at
    document.questions[0].document_id = document.id
    return document


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def start_basic_session(client: TestClient):
    response = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2})
    assert response.status_code == 200
    return response.json()


def test_inspection_endpoint_returns_fallback_when_no_runtime_exists(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/api/inspection/runtime")

    payload = response.json()

    assert response.status_code == 200
    assert payload["inspection_available"] is False
    assert payload["benchmark_summary"]["pedagogical_benchmark_state"] == "not_available"
    assert payload["benchmark_case_reports"] == []
    assert payload["controlled_tuning_registry"]["tuning_experiment_registry_state"] in {
        "registry_ready",
        "registry_empty",
    }


def test_inspection_page_is_served_successfully(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/inspection")

    assert response.status_code == 200
    assert "Internal Runtime Inspection Console" in response.text
    assert "/static/inspection.js" in response.text


def test_inspection_page_does_not_replace_main_study_ui(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "Start Session" in response.text
    assert "Internal Runtime Inspection Console" not in response.text


def test_inspection_endpoint_returns_benchmark_and_validation_payload(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Canal Restrito",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    start_basic_session(client)
    response = client.get("/api/inspection/runtime")

    payload = response.json()

    assert response.status_code == 200
    assert payload["inspection_available"] is True
    assert payload["benchmark_summary"]["pedagogical_benchmark_state"]
    assert payload["benchmark_summary"]["benchmark_readiness"]
    assert payload["benchmark_case_reports"]
    assert payload["scientific_runtime_validation"]["scientific_validation_state"]
    assert payload["stability_metrics"]["session_stability_state"]
    assert payload["validation_dataset_awareness"]["validation_dataset_state"]
    assert payload["controlled_tuning_registry"]["total_experiments"] >= 1


def test_inspection_endpoint_is_deterministic_for_same_runtime_state(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="RIPAM",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    start_basic_session(client)

    first = client.get("/api/inspection/runtime").json()
    second = client.get("/api/inspection/runtime").json()

    assert first == second


def test_inspection_endpoint_is_read_only_and_does_not_advance_session(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 15, 15, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Obrigacao",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    started = start_basic_session(client)
    before = client.get(f"/api/session/{started['session_id']}/current").json()

    inspection = client.get("/api/inspection/runtime")
    after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert inspection.status_code == 200
    assert before == after


def test_inspection_endpoint_does_not_record_answers_or_mutate_progress(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 15, 15, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Competencia",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    start_basic_session(client)
    before = repository.load_progress().model_dump(mode="json")

    response = client.get("/api/inspection/runtime")
    after = repository.load_progress().model_dump(mode="json")

    assert response.status_code == 200
    assert before == after
