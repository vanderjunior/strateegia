import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> None:
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


def test_exam_profile_endpoints_are_available_and_json_safe(tmp_path):
    client, _, _, _ = create_clients(tmp_path)

    listed = client.get("/api/exam-profiles")
    cebraspe = client.get("/api/exam-profiles/exam-profile:cebraspe")
    missing = client.get("/api/exam-profiles/exam-profile:unknown")

    assert listed.status_code == 200
    assert cebraspe.status_code == 200
    assert missing.status_code == 404
    assert [item["profile_id"] for item in listed.json()] == [
        "exam-profile:cebraspe",
        "exam-profile:fgv",
        "exam-profile:marinha-pscpp",
    ]
    assert cebraspe.json()["exam_board"] == "CEBRASPE"
    json.dumps(listed.json(), ensure_ascii=True)
    dumped = json.dumps(cebraspe.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def test_exam_profile_suggestion_endpoint_requires_owner_and_is_json_safe(tmp_path):
    owner, other, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    uploaded = upload_and_process_material(
        owner,
        "edital.md",
        b"# Estrutura da Prova\n\nBanca CEBRASPE.\nJulgue os itens seguintes em CERTO ou ERRADO.\n120 questoes objetivas.",
    )
    document_id = uploaded["metadata"]["document_id"]
    ingest = owner.post(f"/api/materials/{document_id}/edital/ingest")
    assert ingest.status_code == 200
    edital_id = ingest.json()["edital_id"]

    suggested = owner.post(f"/api/edital/{edital_id}/exam-profile/suggest")
    loaded = owner.get(f"/api/edital/{edital_id}/exam-profile/suggestion")

    assert suggested.status_code == 200
    assert loaded.status_code == 200
    assert suggested.json()["profile_id"] == "exam-profile:cebraspe"
    assert loaded.json()["profile_id"] == "exam-profile:cebraspe"
    assert loaded.json()["profile_name"]
    json.dumps(loaded.json(), ensure_ascii=True)

    assert anonymous.post(f"/api/edital/{edital_id}/exam-profile/suggest").status_code == 401
    assert other.post(f"/api/edital/{edital_id}/exam-profile/suggest").status_code == 404
    assert other.get(f"/api/edital/{edital_id}/exam-profile/suggestion").status_code == 404
