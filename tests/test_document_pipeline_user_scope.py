from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), repository


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


def upload_material(client: TestClient, filename: str, content: bytes, content_type: str) -> dict[str, object]:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert response.status_code == 201
    return response.json()


def test_owner_can_process_and_read_pipeline_artifacts(tmp_path):
    owner, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(owner, "material.md", b"# Titulo\n\nConteudo", "text/markdown")
    document_id = uploaded["metadata"]["document_id"]

    process = owner.post(f"/api/materials/{document_id}/process")
    pipeline = owner.get(f"/api/materials/{document_id}/pipeline")
    chunks = owner.get(f"/api/materials/{document_id}/chunks")
    sections = owner.get(f"/api/materials/{document_id}/sections")

    assert process.status_code == 200
    assert pipeline.status_code == 200
    assert chunks.status_code == 200
    assert sections.status_code == 200
    assert pipeline.json()["document_id"] == document_id
    assert len(chunks.json()) >= 1
    assert len(sections.json()) >= 1


def test_user_cannot_process_or_read_other_user_pipeline_artifacts(tmp_path):
    owner, other, _ = create_clients(tmp_path)
    owner_user = register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(owner, "material.txt", b"Conteudo privado", "text/plain")
    document_id = uploaded["metadata"]["document_id"]

    assert owner_user["user_id"] == uploaded["metadata"]["user_id"]

    process_other = other.post(f"/api/materials/{document_id}/process")
    pipeline_other = other.get(f"/api/materials/{document_id}/pipeline")
    chunks_other = other.get(f"/api/materials/{document_id}/chunks")
    sections_other = other.get(f"/api/materials/{document_id}/sections")

    assert process_other.status_code == 404
    assert pipeline_other.status_code == 404
    assert chunks_other.status_code == 404
    assert sections_other.status_code == 404


def test_pipeline_endpoints_require_auth_and_legacy_progress_mode_still_works(tmp_path):
    owner, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(owner, "material.txt", b"Conteudo legado", "text/plain")
    document_id = uploaded["metadata"]["document_id"]

    unauth_process = anonymous.post(f"/api/materials/{document_id}/process")
    unauth_pipeline = anonymous.get(f"/api/materials/{document_id}/pipeline")
    legacy_progress = anonymous.get("/api/progress")

    assert unauth_process.status_code == 401
    assert unauth_pipeline.status_code == 401
    assert legacy_progress.status_code == 200
