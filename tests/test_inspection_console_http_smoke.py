import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


EXPECTED_TOP_LEVEL_KEYS = {
    "inspection_available",
    "inspection_label",
    "session",
    "benchmark_summary",
    "benchmark_case_reports",
    "scientific_runtime_validation",
    "comparative_session_analytics",
    "session_export_debug",
    "stability_metrics",
    "validation_dataset_awareness",
    "controlled_tuning_registry",
    "tuning_profile_benchmark_comparison",
    "manual_experiment_inspection",
    "longitudinal_retention",
    "aggregate_retention",
    "raw_runtime_block",
}


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura normativa, excecoes e comparacoes tecnicas.",
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


def test_get_inspection_returns_200_with_read_only_label(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/inspection")

    assert response.status_code == 200
    assert "Internal Runtime Inspection Console" in response.text
    assert "Read Only" in response.text


def test_get_api_inspection_runtime_returns_json_with_stable_keys(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/api/inspection/runtime")
    payload = response.json()

    assert response.status_code == 200
    assert set(payload.keys()) == EXPECTED_TOP_LEVEL_KEYS
    json.dumps(payload, ensure_ascii=True)


def test_no_session_fallback_is_safe_and_serializable(tmp_path):
    client, _ = create_client(tmp_path)

    response = client.get("/api/inspection/runtime")
    payload = response.json()

    assert response.status_code == 200
    assert payload["inspection_available"] is False
    assert payload["session"]["session_id"] is None
    assert payload["benchmark_case_reports"] == []
    assert isinstance(payload["controlled_tuning_registry"], dict)
    assert isinstance(payload["manual_experiment_inspection"], dict)
    assert isinstance(payload["longitudinal_retention"], dict)
    assert isinstance(payload["aggregate_retention"], dict)
    json.dumps(payload, ensure_ascii=True)


def test_inspection_static_assets_are_reachable(tmp_path):
    client, _ = create_client(tmp_path)

    html_response = client.get("/static/inspection.html")
    js_response = client.get("/static/inspection.js")
    css_response = client.get("/static/inspection.css")

    assert html_response.status_code == 200
    assert js_response.status_code == 200
    assert css_response.status_code == 200
    assert "text/html" in html_response.headers.get("content-type", "")
    assert "javascript" in js_response.headers.get("content-type", "")
    assert "text/css" in css_response.headers.get("content-type", "")


def test_main_study_page_remains_distinct_from_inspection(tmp_path):
    client, _ = create_client(tmp_path)

    study = client.get("/")
    inspection = client.get("/inspection")

    assert study.status_code == 200
    assert inspection.status_code == 200
    assert "Start Session" in study.text
    assert "Internal Runtime Inspection Console" not in study.text
    assert "Internal Runtime Inspection Console" in inspection.text


def test_inspection_routes_do_not_call_answer_submission_or_review_plan(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 15, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Autoridade Maritima",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = start_basic_session(client)

    calls = {"record_feedback": 0, "review_plan": 0}

    def forbidden_record_feedback(*args, **kwargs):
        calls["record_feedback"] += 1
        raise AssertionError("Inspection routes must not submit answers.")

    def forbidden_build_review_plan(*args, **kwargs):
        calls["review_plan"] += 1
        raise AssertionError("Inspection routes must not create review plans.")

    monkeypatch.setattr("app.api.routes._record_feedback_answer", forbidden_record_feedback)
    monkeypatch.setattr(
        "app.api.routes.LearningDecisionEngine.build_review_plan",
        forbidden_build_review_plan,
    )

    progress_before = repository.load_progress().model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current")
    assert current_before.status_code == 200

    inspection_page = client.get("/inspection")
    inspection_api = client.get("/api/inspection/runtime")

    progress_after = repository.load_progress().model_dump(mode="json")

    assert inspection_page.status_code == 200
    assert inspection_api.status_code == 200
    assert calls == {"record_feedback": 0, "review_plan": 0}
    assert progress_before == progress_after


def test_inspection_api_does_not_advance_existing_session(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 15, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Auxilios a Navegacao",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = start_basic_session(client)
    before = client.get(f"/api/session/{started['session_id']}/current").json()

    response = client.get("/api/inspection/runtime")
    after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert response.status_code == 200
    assert before == after
