import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_ITEM_KEYS = {
    "edital_id",
    "document_id",
    "title",
    "created_at",
    "updated_at",
    "analysis_status",
    "topics_count",
    "bibliography_count",
    "gaps_count",
    "review_state",
    "coverage_status",
    "alignment_status",
    "warnings_count",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-EDITAL-BODY-SHOULD-NOT-LEAK",
    "RAW-DOCUMENT-BODY-SHOULD-NOT-LEAK",
    "OTHER-EDITAL-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "raw_ocr",
    "ocr_dump",
    "base64",
    "storage_path",
    "/Users/",
    "C:\\",
    "password_hash",
    "studyflow_session",
    "session token",
    "answer_key",
    "gabarito",
    "correctness",
    "is_correct",
    "evidence",
    "raw_reference",
)


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


def ingest_edital(client: TestClient, *, filename: str = "edital.md") -> dict[str, object]:
    uploaded = upload_and_process_material(
        client,
        filename,
        (
            b"# Conteudo Programatico\n\n"
            b"1. Arte Naval\n\n"
            b"2. Navegacao\n\n"
            b"# Bibliografia\n\n"
            b"Normas da Autoridade Maritima\n\n"
            b"RAW-EDITAL-BODY-SHOULD-NOT-LEAK"
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    ingested = client.post(f"/api/materials/{document_id}/edital/ingest")
    assert ingested.status_code == 200
    return ingested.json()


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def test_editais_list_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/editais")

    assert response.status_code == 401


def test_editais_list_empty_for_authenticated_user(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "empty-user")

    response = owner.get("/api/editais")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0, "source": "user_scope"}


def test_editais_list_returns_own_bounded_edital(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = ingest_edital(owner)

    response = owner.get("/api/editais")
    payload = response.json()

    assert response.status_code == 200
    assert payload["source"] == "user_scope"
    assert payload["count"] == 1
    assert len(payload["items"]) == payload["count"]
    item = payload["items"][0]
    assert set(item.keys()) == ALLOWED_ITEM_KEYS
    assert item["edital_id"] == edital["edital_id"]
    assert item["document_id"] == edital["document_id"]
    assert item["title"] == "Edital analisado da sessão"
    assert item["topics_count"] >= 1
    assert item["bibliography_count"] >= 0
    assert item["gaps_count"] == 0
    assert item["analysis_status"] in {"analyzed", "needs_review", "failed", "not_ready"}
    assert item["review_state"] in {"ready_for_review", "needs_review", "pending", "unknown"}
    assert item["coverage_status"] in {"good", "partial", "gap_found", "needs_material", "unknown"}
    assert item["alignment_status"] in {"aligned", "partial", "needs_review", "not_available", "unknown"}
    assert_no_forbidden_terms(payload)


def test_editais_list_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_edital = ingest_edital(owner, filename="owner-edital.md")
    other_edital = ingest_edital(other, filename="other-edital.md")

    owner_payload = owner.get("/api/editais").json()
    other_payload = other.get("/api/editais").json()

    owner_ids = {item["edital_id"] for item in owner_payload["items"]}
    other_ids = {item["edital_id"] for item in other_payload["items"]}
    assert owner_edital["edital_id"] in owner_ids
    assert other_edital["edital_id"] not in owner_ids
    assert other_edital["edital_id"] in other_ids
    assert owner_edital["edital_id"] not in other_ids
    assert_no_forbidden_terms(owner_payload)
    assert_no_forbidden_terms(other_payload)


def test_editais_list_includes_bounded_alignment_counts(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = ingest_edital(owner)

    alignment = owner.post(f"/api/edital/{edital['edital_id']}/align-bibliography")
    assert alignment.status_code == 200
    response = owner.get("/api/editais")
    payload = response.json()

    item = payload["items"][0]
    assert item["edital_id"] == edital["edital_id"]
    assert isinstance(item["gaps_count"], int)
    assert item["alignment_status"] in {"aligned", "partial", "needs_review", "not_available", "unknown"}
    assert_no_forbidden_terms(payload)


def test_editais_list_shape_is_deterministic_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-user")
    ingest_edital(owner, filename="a-edital.md")
    ingest_edital(owner, filename="b-edital.md")

    first = owner.get("/api/editais").json()
    second = owner.get("/api/editais").json()

    assert first == second
    assert first["count"] == len(first["items"])
    for item in first["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert isinstance(item["topics_count"], int)
        assert isinstance(item["bibliography_count"], int)
        assert isinstance(item["gaps_count"], int)
        assert isinstance(item["warnings_count"], int)
    assert_no_forbidden_terms(first)
