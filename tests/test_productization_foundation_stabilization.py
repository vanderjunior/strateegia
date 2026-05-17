import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.user_service import LocalUserService


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura cuidadosa, comparacoes e precisao normativa.",
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.84,
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


def register_and_login(client: TestClient, username: str, password: str = "senha-segura-123") -> dict[str, object]:
    register = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert register.status_code == 201
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return register.json()


def test_user_persistence_survives_reload_and_inactive_users_cannot_authenticate(tmp_path):
    path = tmp_path / "study_data.json"
    repository = JsonStudyRepository(path)
    service = LocalUserService(repository)

    created = service.register_user(
        username="persistente",
        password="senha-segura-123",
        display_name="Persistente",
        email="persistente@example.com",
    )
    reloaded = JsonStudyRepository(path)
    loaded = reloaded.get_user_by_username("persistente")
    assert loaded is not None
    assert loaded.user_id == created.user_id
    assert loaded.password_hash != "senha-segura-123"

    loaded.is_active = False
    reloaded.update_user(loaded)
    inactive_service = LocalUserService(JsonStudyRepository(path))
    assert inactive_service.authenticate(username="persistente", password="senha-segura-123") is None


def test_login_failure_cookie_safety_and_auth_responses_do_not_expose_password_hash(tmp_path):
    client, _ = create_client(tmp_path)
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "seguro",
            "password": "senha-segura-123",
            "display_name": "Seguro",
            "email": "seguro@example.com",
        },
    )
    failed_login = client.post(
        "/api/auth/login",
        json={"username": "seguro", "password": "senha-incorreta"},
    )
    successful_login = client.post(
        "/api/auth/login",
        json={"username": "seguro", "password": "senha-segura-123"},
    )
    me = client.get("/api/auth/me")
    logout = client.post("/api/auth/logout")

    assert register_response.status_code == 201
    assert "password_hash" not in json.dumps(register_response.json(), ensure_ascii=True)
    assert failed_login.status_code == 401
    assert failed_login.json()["detail"] == "Invalid credentials."
    assert "password_hash" not in json.dumps(successful_login.json(), ensure_ascii=True)
    assert "httponly" in successful_login.headers.get("set-cookie", "").lower()
    assert me.status_code == 200
    assert "password_hash" not in json.dumps(me.json(), ensure_ascii=True)
    assert "studyflow_session=" in logout.headers.get("set-cookie", "").lower()


def test_repository_loads_legacy_or_partial_store_shapes_safely(tmp_path):
    path = tmp_path / "study_data.json"
    path.write_text(
        json.dumps(
            {
                "documents": [],
                "answers": [],
                "progress": {
                    "total_errors": 2,
                    "weak_topics": {"topic-legacy": 2},
                    "error_buckets": {"concept_confusion": 2},
                    "topic_learning_states": {},
                    "item_states": {},
                    "microtopic_performance": {},
                    "pedagogical_memory": {},
                },
                "user_data": {
                    "user-a": {
                        "progress": {
                            "total_errors": 0,
                            "weak_topics": {},
                            "error_buckets": {},
                            "topic_learning_states": {},
                            "item_states": {},
                            "microtopic_performance": {},
                            "pedagogical_memory": {},
                        }
                    }
                },
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(path)
    legacy = repository.load_progress()
    user_a = repository.load_progress(user_id="user-a")

    assert legacy.total_errors == 2
    assert legacy.weak_topics["topic-legacy"] == 2
    assert user_a.total_errors == 0
    assert repository.list_documents(user_id="user-a") == []
    assert repository.list_uploaded_materials(user_id="user-a") == []


def test_materials_are_isolated_per_user_and_duplicate_names_do_not_collide(tmp_path):
    client_a, repository = create_client(tmp_path)
    app = client_a.app
    client_b = TestClient(app)
    user_a = register_and_login(client_a, "usera")
    user_b = register_and_login(client_b, "userb")

    first = client_a.post(
        "/api/materials/upload",
        files={"file": ("resumo.md", BytesIO(b"# A"), "text/markdown")},
    )
    second = client_a.post(
        "/api/materials/upload",
        files={"file": ("resumo.md", BytesIO(b"# B"), "text/markdown")},
    )
    other = client_b.post(
        "/api/materials/upload",
        files={"file": ("resumo.md", BytesIO(b"# C"), "text/markdown")},
    )

    materials_a = repository.list_uploaded_materials(user_id=user_a["user_id"])
    materials_b = repository.list_uploaded_materials(user_id=user_b["user_id"])

    assert first.status_code == 201
    assert second.status_code == 201
    assert other.status_code == 201
    assert len(materials_a) == 2
    assert len(materials_b) == 1
    assert materials_a[0].metadata.storage_path != materials_a[1].metadata.storage_path
    assert all(item.metadata.storage_path.startswith(f"uploads/{user_a['user_id']}/") for item in materials_a)
    assert materials_b[0].metadata.storage_path.startswith(f"uploads/{user_b['user_id']}/")


def test_legacy_mode_and_user_mode_both_preserve_runtime_behavior(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 17, 13, 0, tzinfo=timezone.utc)
    legacy_document = build_document(
        title="Legado",
        topic_id="topic-legacy",
        question_id="q-legacy",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(legacy_document)

    legacy_started = client.post("/api/session/start", json={"title": "Sessao Legada", "max_questions": 2})
    assert legacy_started.status_code == 200
    assert legacy_started.json()["first_block"]["topic_id"] == "topic-legacy"

    user = register_and_login(client, "runtime-user")
    repository.save_document(
        build_document(
            title="Usuario",
            topic_id="topic-user",
            question_id="q-user",
            created_at=now - timedelta(days=1),
        ),
        user_id=user["user_id"],
    )
    started = client.post("/api/session/start", json={"title": "Sessao Usuario", "max_questions": 2})
    question = client.post(f"/api/session/{started.json()['session_id']}/answer").json()["next_block"]
    answered = client.post(
        f"/api/session/{started.json()['session_id']}/answer",
        json={
            "question_id": question["question_id"],
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )

    assert started.status_code == 200
    assert started.json()["first_block"]["topic_id"] == "topic-user"
    assert answered.status_code == 200
    assert repository.load_progress(user_id=user["user_id"]).total_errors == 1
    assert repository.load_progress().total_errors == 0


def test_inspection_remains_json_safe_read_only_and_does_not_leak_password_data(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "inspecao")
    now = datetime(2026, 5, 17, 14, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Inspecao",
            topic_id="topic-inspecao",
            question_id="q-inspecao",
            created_at=now - timedelta(days=1),
        ),
        user_id=user["user_id"],
    )
    started = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2}).json()

    progress_before = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current").json()
    inspection = client.get("/api/inspection/runtime")
    exported = client.get("/api/inspection/runtime/export")
    progress_after = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    current_after = client.get(f"/api/session/{started['session_id']}/current").json()
    serialized_payload = json.dumps(inspection.json(), ensure_ascii=True)
    serialized_export = json.dumps(exported.json(), ensure_ascii=True)

    assert inspection.status_code == 200
    assert exported.status_code == 200
    assert progress_before == progress_after
    assert current_before == current_after
    assert "password_hash" not in serialized_payload
    assert "password_hash" not in serialized_export


def test_readme_and_requirements_document_server_foundation_limitations():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    readme = Path("README.md").read_text(encoding="utf-8").lower()

    for dependency in ["fastapi", "uvicorn", "pytest", "python-multipart", "pdfplumber", "pymupdf"]:
        assert dependency in requirements
    for absent in ["pytesseract", "easyocr", "opencv", "sqlalchemy"]:
        assert absent not in requirements

    for snippet in [
        "inspection",
        "producao",
        "json",
        "sql",
        "ocr",
        "edital",
        "simulados",
        "roadmap",
    ]:
        assert snippet in readme
