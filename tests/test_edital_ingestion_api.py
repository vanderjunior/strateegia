import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


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


def test_edital_ingestion_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_and_process_material(
        owner,
        "edital.md",
        b"# Conteudo Programatico\n\n1. Arte Naval\n\n# Estrutura da Prova\n\n20 questoes, 40 pontos.",
    )
    document_id = uploaded["metadata"]["document_id"]

    ingest = owner.post(f"/api/materials/{document_id}/edital/ingest")
    loaded = owner.get(f"/api/materials/{document_id}/edital")
    edital_id = loaded.json()["edital_id"]
    by_id = owner.get(f"/api/edital/{edital_id}")

    assert ingest.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["document_id"] == document_id
    json.dumps(loaded.json(), ensure_ascii=True)
    json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in json.dumps(by_id.json(), ensure_ascii=True)

    unauth = anonymous.post(f"/api/materials/{document_id}/edital/ingest")
    assert unauth.status_code == 401


def test_non_owner_cannot_access_other_user_edital_extraction(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_and_process_material(
        owner,
        "edital.md",
        b"# Conteudo Programatico\n\n1. Arte Naval",
    )
    document_id = uploaded["metadata"]["document_id"]

    ingest = owner.post(f"/api/materials/{document_id}/edital/ingest")
    assert ingest.status_code == 200
    edital_id = ingest.json()["edital_id"]

    assert other.post(f"/api/materials/{document_id}/edital/ingest").status_code == 404
    assert other.get(f"/api/materials/{document_id}/edital").status_code == 404
    assert other.get(f"/api/edital/{edital_id}").status_code == 404
