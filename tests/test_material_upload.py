from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
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


def test_upload_txt_material_creates_metadata_and_user_scoped_storage(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "material-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("../../meu resumo final!!.txt", BytesIO(b"linha 1\nlinha 2"), "text/plain")},
    )

    payload = response.json()
    stored = repository.list_uploaded_materials(user_id=user["user_id"])

    assert response.status_code == 201
    assert payload["metadata"]["user_id"] == user["user_id"]
    assert payload["metadata"]["original_filename"] == "../../meu resumo final!!.txt"
    assert ".." not in payload["metadata"]["filename"]
    assert ".." not in payload["metadata"]["storage_path"]
    assert payload["metadata"]["storage_path"].startswith(f"uploads/{user['user_id']}/")
    assert payload["extracted_text"].startswith("linha 1")
    assert len(stored) == 1


def test_upload_persists_normalized_material_type(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "intent-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("edital.txt", BytesIO(b"conteudo"), "text/plain")},
        data={"material_type": "edital"},
    )

    payload = response.json()
    stored = repository.list_uploaded_materials(user_id=user["user_id"])

    assert response.status_code == 201
    assert payload["metadata"]["metadata"]["material_type"] == "edital"
    assert stored[0].metadata.metadata["material_type"] == "edital"


def test_upload_defaults_missing_material_type_to_unknown(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "unknown-intent-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("material.txt", BytesIO(b"conteudo"), "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["metadata"]["metadata"]["material_type"] == "unknown"


def test_upload_rejects_invalid_material_type(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "bad-intent-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("material.txt", BytesIO(b"conteudo"), "text/plain")},
        data={"material_type": "auto_ingest_now"},
    )

    assert response.status_code == 422
    assert "material_type" in response.json()["detail"]


def test_upload_pdf_material_is_pending_extraction(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "pdf-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("material.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["metadata"]["status"] == "pending_extraction"


def test_upload_rejects_unsupported_extension(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "unsupported-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("material.exe", BytesIO(b"binario"), "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_oversized_payload(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "large-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("grande.txt", BytesIO(b"a" * (5 * 1024 * 1024 + 1)), "text/plain")},
    )

    assert response.status_code == 413
    assert "size" in response.json()["detail"].lower()
