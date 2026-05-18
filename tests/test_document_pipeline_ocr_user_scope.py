from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


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


def upload_pdf(client: TestClient, filename: str) -> dict[str, object]:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(build_pdf_bytes("")), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_ocr_related_process_and_read_endpoints_remain_user_scoped(tmp_path, monkeypatch):
    owner, other, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    uploaded = upload_pdf(owner, "owner-scan.pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setenv("ENABLE_OCR", "false")

    assert other.post(f"/api/materials/{document_id}/process").status_code == 404
    assert other.get(f"/api/materials/{document_id}/pipeline").status_code == 404
    assert other.get(f"/api/materials/{document_id}/chunks").status_code == 404
    assert other.get(f"/api/materials/{document_id}/sections").status_code == 404

    assert owner.post(f"/api/materials/{document_id}/process").status_code == 200
    assert owner.get(f"/api/materials/{document_id}/pipeline").status_code == 200
