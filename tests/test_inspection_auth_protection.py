import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura normativa e comparacoes tecnicas.",
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


def register_and_login(client: TestClient, username: str):
    register = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return register.json()


def test_test_environment_keeps_inspection_routes_available_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ENABLE_INSPECTION", raising=False)
    monkeypatch.delenv("REQUIRE_AUTH_FOR_INSPECTION", raising=False)
    monkeypatch.delenv("INSPECTION_ALLOWED_IN_PRODUCTION", raising=False)
    client, _ = create_client(tmp_path)

    inspection = client.get("/inspection")
    runtime = client.get("/api/inspection/runtime")
    exported = client.get("/api/inspection/runtime/export")

    assert inspection.status_code == 200
    assert runtime.status_code == 200
    assert exported.status_code == 200


def test_explicit_disable_blocks_inspection_consistently_without_mutation(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_INSPECTION", "false")
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 17, 16, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Bloqueio",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2}).json()
    progress_before = repository.load_progress().model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current").json()

    inspection = client.get("/inspection")
    runtime = client.get("/api/inspection/runtime")
    exported = client.get("/api/inspection/runtime/export")

    progress_after = repository.load_progress().model_dump(mode="json")
    current_after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert inspection.status_code == 404
    assert runtime.status_code == 404
    assert exported.status_code == 404
    assert progress_before == progress_after
    assert current_before == current_after


def test_production_blocks_inspection_by_default_but_keeps_normal_routes_available(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_INSPECTION", raising=False)
    monkeypatch.delenv("INSPECTION_ALLOWED_IN_PRODUCTION", raising=False)
    monkeypatch.delenv("REQUIRE_AUTH_FOR_INSPECTION", raising=False)
    client, _ = create_client(tmp_path)

    home = client.get("/")
    register = client.post(
        "/api/auth/register",
        json={
            "username": "produser",
            "password": "senha-segura-123",
            "display_name": "Prod User",
            "email": "produser@example.com",
        },
    )
    inspection = client.get("/inspection")
    runtime = client.get("/api/inspection/runtime")

    assert home.status_code == 200
    assert register.status_code == 201
    assert inspection.status_code == 404
    assert runtime.status_code == 404


def test_production_explicit_enable_requires_auth_and_allows_authenticated_access(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_INSPECTION", "true")
    monkeypatch.setenv("INSPECTION_ALLOWED_IN_PRODUCTION", "true")
    monkeypatch.setenv("REQUIRE_AUTH_FOR_INSPECTION", "true")
    client, repository = create_client(tmp_path)
    authed = TestClient(client.app)
    now = datetime(2026, 5, 17, 16, 30, tzinfo=timezone.utc)
    register_and_login(authed, "guardado")
    repository.save_document(
        build_document(
            title="Inspecao Protegida",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    unauth_page = client.get("/inspection")
    unauth_runtime = client.get("/api/inspection/runtime")
    unauth_export = client.get("/api/inspection/runtime/export")
    auth_page = authed.get("/inspection")
    auth_runtime = authed.get("/api/inspection/runtime")
    auth_export = authed.get("/api/inspection/runtime/export")

    assert unauth_page.status_code == 401
    assert unauth_runtime.status_code == 401
    assert unauth_export.status_code == 401
    assert auth_page.status_code == 200
    assert auth_runtime.status_code == 200
    assert auth_export.status_code == 200


def test_development_auth_required_mode_blocks_unauthenticated_and_preserves_auth_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REQUIRE_AUTH_FOR_INSPECTION", "yes")
    monkeypatch.delenv("ENABLE_INSPECTION", raising=False)
    monkeypatch.delenv("INSPECTION_ALLOWED_IN_PRODUCTION", raising=False)
    client, _ = create_client(tmp_path)
    authed = TestClient(client.app)
    register_and_login(authed, "devauth")

    unauth = client.get("/api/inspection/runtime")
    me = authed.get("/api/auth/me")
    auth = authed.get("/api/inspection/runtime")

    assert unauth.status_code == 401
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert auth.status_code == 200


def test_inspection_payload_and_blocked_responses_do_not_leak_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_INSPECTION", "true")
    monkeypatch.setenv("INSPECTION_ALLOWED_IN_PRODUCTION", "true")
    monkeypatch.setenv("REQUIRE_AUTH_FOR_INSPECTION", "true")
    client, _ = create_client(tmp_path)
    authed = TestClient(client.app)
    register_and_login(authed, "sigilo")

    blocked = client.get("/api/inspection/runtime")
    allowed = authed.get("/api/inspection/runtime")
    auth_me = authed.get("/api/auth/me")

    assert blocked.status_code == 401
    assert "password_hash" not in json.dumps(blocked.json(), ensure_ascii=True)
    assert "password_hash" not in json.dumps(allowed.json(), ensure_ascii=True)
    assert "password_hash" not in json.dumps(auth_me.json(), ensure_ascii=True)
    assert "Users" not in blocked.text


def test_readme_documents_inspection_server_mode_configuration():
    readme = Path("README.md").read_text(encoding="utf-8").lower()

    for snippet in [
        "app_env",
        "enable_inspection",
        "require_auth_for_inspection",
        "inspection_allowed_in_production",
        "internal",
        "debug",
        "producao",
    ]:
        assert snippet in readme
