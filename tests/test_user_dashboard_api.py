import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.learning_engine import LearningDecisionEngine


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    return registered.json()


def upload_and_process_material(client: TestClient, filename: str, content: bytes) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), "text/markdown")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["metadata"]["document_id"]
    processed = client.post(f"/api/materials/{document_id}/process")
    assert processed.status_code == 200
    return uploaded.json()


def test_dashboard_overview_requires_auth_and_is_user_scoped(tmp_path):
    owner, other, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    upload_and_process_material(owner, "owner.md", b"# Owner\n\nConteudo.")
    upload_and_process_material(other, "other.md", b"# Other\n\nConteudo.")

    assert anonymous.get("/api/dashboard/overview").status_code == 401

    owner_payload = owner.get("/api/dashboard/overview")
    other_payload = other.get("/api/dashboard/overview")

    assert owner_payload.status_code == 200
    assert other_payload.status_code == 200
    assert owner_payload.json()["user"]["username"] == "owner"
    assert other_payload.json()["user"]["username"] == "other"
    assert owner_payload.json()["materials"]["total_materials"] == 1
    assert other_payload.json()["materials"]["total_materials"] == 1
    dumped = json.dumps(owner_payload.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert "inspection_available" not in dumped
    assert "manual_experiment_inspection" not in dumped


def test_dashboard_overview_is_read_only_and_safe_to_call_repeatedly(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    upload_and_process_material(owner, "owner.md", b"# Owner\n\nConteudo.")

    before_materials = len(repository.list_uploaded_materials(user_id=user["user_id"]))
    before_editais = len(repository.list_user_edital_extractions(user_id=user["user_id"]))
    before_graphs = len(repository.list_user_curriculum_graphs(user_id=user["user_id"]))
    before_cycles = len(repository.list_user_study_cycle_plans(user_id=user["user_id"]))
    before_blueprints = len(repository.list_user_simulado_blueprints(user_id=user["user_id"]))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dashboard overview must remain read-only")

    monkeypatch.setattr(LearningDecisionEngine, "build_review_plan", fail_if_called)

    first = owner.get("/api/dashboard/overview")
    second = owner.get("/api/dashboard/overview")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_uploaded_materials(user_id=user["user_id"])) == before_materials
    assert len(repository.list_user_edital_extractions(user_id=user["user_id"])) == before_editais
    assert len(repository.list_user_curriculum_graphs(user_id=user["user_id"])) == before_graphs
    assert len(repository.list_user_study_cycle_plans(user_id=user["user_id"])) == before_cycles
    assert len(repository.list_user_simulado_blueprints(user_id=user["user_id"])) == before_blueprints

