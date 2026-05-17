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


def test_bibliography_alignment_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = upload_and_process_material(
        owner,
        "edital.md",
        b"# Conteudo Programatico\n\n1. Arte Naval\n\n# Bibliografia\n\nSILVA, Joao. Navegacao Costeira. 2020.",
    )
    owner.post(f"/api/materials/{edital['metadata']['document_id']}/edital/ingest")
    upload_and_process_material(
        owner,
        "silva_navegacao_costeira_2020.md",
        b"# Navegacao Costeira\n\nArte Naval aplicada.",
    )
    edital_id = f"edital:{edital['metadata']['document_id']}"

    align = owner.post(f"/api/edital/{edital_id}/align-bibliography")
    loaded = owner.get(f"/api/edital/{edital_id}/alignment")
    alignment_id = loaded.json()["alignment_id"]
    by_id = owner.get(f"/api/alignment/{alignment_id}")

    assert align.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["alignment_id"] == alignment_id
    assert "password_hash" not in json.dumps(by_id.json(), ensure_ascii=True)
    json.dumps(loaded.json(), ensure_ascii=True)
    json.dumps(by_id.json(), ensure_ascii=True)

    unauth = anonymous.post(f"/api/edital/{edital_id}/align-bibliography")
    assert unauth.status_code == 401


def test_non_owner_cannot_access_other_user_alignment(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    edital = upload_and_process_material(
        owner,
        "edital.md",
        b"# Conteudo Programatico\n\n1. RIPEAM\n\n# Bibliografia\n\nBRASIL. RIPEAM Comentado. 2021.",
    )
    owner.post(f"/api/materials/{edital['metadata']['document_id']}/edital/ingest")
    upload_and_process_material(
        owner,
        "ripeam_comentado_2021.md",
        b"# RIPEAM\n\nRegras de governo e rumo.",
    )
    edital_id = f"edital:{edital['metadata']['document_id']}"
    align = owner.post(f"/api/edital/{edital_id}/align-bibliography")
    assert align.status_code == 200
    alignment_id = align.json()["alignment_id"]

    assert other.post(f"/api/edital/{edital_id}/align-bibliography").status_code == 404
    assert other.get(f"/api/edital/{edital_id}/alignment").status_code == 404
    assert other.get(f"/api/alignment/{alignment_id}").status_code == 404
