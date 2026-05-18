import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
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
    return logged_in.json()["user"]["user_id"]


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


def prepare_simulado_blueprint(client: TestClient) -> str:
    edital = upload_and_process_material(
        client,
        "edital.md",
        (
            b"# Estrutura da Prova\n\nFGV. Prova objetiva com cinco alternativas A, B, C, D e E, apenas uma correta.\n\n"
            b"# Conteudo Programatico\n\n1. RIPEAM\n2. Meteorologia\n\n# Bibliografia\n\nBRASIL. RIPEAM Comentado. 2021."
        ),
    )
    document_id = edital["metadata"]["document_id"]
    ingest = client.post(f"/api/materials/{document_id}/edital/ingest")
    assert ingest.status_code == 200
    edital_id = ingest.json()["edital_id"]
    upload_and_process_material(
        client,
        "ripeam_comentado_2021.md",
        b"# RIPEAM\n\nRegras de governo e rumo com base normativa e tecnicidade.",
    )
    upload_and_process_material(
        client,
        "meteorologia.md",
        b"# Meteorologia\n\nVentos, cartas sinoticas e leitura aplicada.",
    )
    assert client.post(f"/api/edital/{edital_id}/align-bibliography").status_code == 200
    assert client.post(f"/api/edital/{edital_id}/curriculum-graph/build").status_code == 200
    graph_id = client.get(f"/api/edital/{edital_id}/curriculum-graph").json()["graph_id"]
    assert client.post(f"/api/curriculum-graph/{graph_id}/study-cycle/build").status_code == 200
    cycle_id = client.get(f"/api/curriculum-graph/{graph_id}/study-cycle").json()["cycle_id"]
    build = client.post(f"/api/study-cycle/{cycle_id}/simulado-blueprint/build")
    assert build.status_code == 200
    return build.json()["blueprint_id"]


def test_question_generation_blueprint_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    blueprint_id = prepare_simulado_blueprint(owner)

    missing = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint")
    build = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build")
    loaded = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint")
    blueprint_set_id = build.json()["blueprint_set_id"]
    by_id = owner.get(f"/api/question-generation-blueprint/{blueprint_set_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_simulado_blueprint_id"] == blueprint_id
    assert loaded.json()["no_question_text_generated"] is True
    assert loaded.json()["slot_blueprints"]
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build").status_code == 401
    assert anonymous.get(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint").status_code == 401
    assert anonymous.get(f"/api/question-generation-blueprint/{blueprint_set_id}").status_code == 401


def test_question_generation_blueprint_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    blueprint_id = prepare_simulado_blueprint(owner)

    first = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build")
    second = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build")
    listed = repository.list_user_question_generation_blueprints(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_question_generation_blueprint(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    blueprint_id = prepare_simulado_blueprint(owner)
    build = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build")
    assert build.status_code == 200
    blueprint_set_id = build.json()["blueprint_set_id"]

    assert other.post(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build").status_code == 404
    assert other.get(f"/api/simulado-blueprint/{blueprint_id}/question-generation-blueprint").status_code == 404
    assert other.get(f"/api/question-generation-blueprint/{blueprint_set_id}").status_code == 404
