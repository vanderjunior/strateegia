import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_SUMMARY_KEYS = {
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
    "summary",
    "source",
}


ALLOWED_NESTED_SUMMARY_KEYS = {
    "has_topics",
    "has_bibliography",
    "has_gaps",
    "needs_review",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-EDITAL-SUMMARY-SHOULD-NOT-LEAK",
    "RAW-DOCUMENT-SUMMARY-SHOULD-NOT-LEAK",
    "OTHER-EDITAL-SUMMARY-SHOULD-NOT-LEAK",
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
            b"RAW-EDITAL-SUMMARY-SHOULD-NOT-LEAK"
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


def test_edital_summary_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/editais/edital:missing/summary")

    assert response.status_code == 401


def test_edital_summary_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/editais/edital:missing/summary")

    assert response.status_code == 404


def test_edital_summary_returns_own_bounded_summary(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = ingest_edital(owner)

    response = owner.get(f"/api/editais/{edital['edital_id']}/summary")
    payload = response.json()

    assert response.status_code == 200
    assert set(payload.keys()) == ALLOWED_SUMMARY_KEYS
    assert set(payload["summary"].keys()) == ALLOWED_NESTED_SUMMARY_KEYS
    assert payload["edital_id"] == edital["edital_id"]
    assert payload["document_id"] == edital["document_id"]
    assert payload["title"] == "Edital analisado da sessão"
    assert payload["source"] == "user_scope"
    assert payload["analysis_status"] in {"analyzed", "needs_review", "failed", "not_ready"}
    assert payload["topics_count"] >= 1
    assert payload["bibliography_count"] >= 0
    assert payload["gaps_count"] == 0
    assert isinstance(payload["warnings_count"], int)
    assert isinstance(payload["summary"]["has_topics"], bool)
    assert isinstance(payload["summary"]["has_bibliography"], bool)
    assert isinstance(payload["summary"]["has_gaps"], bool)
    assert isinstance(payload["summary"]["needs_review"], bool)
    assert_no_forbidden_terms(payload)


def test_edital_summary_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_edital = ingest_edital(owner, filename="owner-edital.md")
    other_edital = ingest_edital(other, filename="other-edital.md")

    owner_edital_id = owner_edital["edital_id"]
    other_edital_id = other_edital["edital_id"]

    assert other.get(f"/api/editais/{owner_edital_id}/summary").status_code == 404
    other_response = other.get(f"/api/editais/{other_edital_id}/summary")
    owner_response = owner.get(f"/api/editais/{owner_edital_id}/summary")

    assert other_response.status_code == 200
    assert owner_response.status_code == 200
    assert other_response.json()["edital_id"] == other_edital_id
    assert owner_response.json()["edital_id"] == owner_edital_id
    assert_no_forbidden_terms(other_response.json())
    assert_no_forbidden_terms(owner_response.json())


def test_edital_summary_includes_bounded_alignment_counts(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = ingest_edital(owner)

    alignment = owner.post(f"/api/edital/{edital['edital_id']}/align-bibliography")
    assert alignment.status_code == 200
    response = owner.get(f"/api/editais/{edital['edital_id']}/summary")
    payload = response.json()

    assert payload["edital_id"] == edital["edital_id"]
    assert isinstance(payload["gaps_count"], int)
    assert payload["summary"]["has_gaps"] is (payload["gaps_count"] > 0)
    assert payload["alignment_status"] in {"aligned", "partial", "needs_review", "not_available", "unknown"}
    assert_no_forbidden_terms(payload)


def test_edital_summary_shape_is_deterministic_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-user")
    edital = ingest_edital(owner)

    first = owner.get(f"/api/editais/{edital['edital_id']}/summary").json()
    second = owner.get(f"/api/editais/{edital['edital_id']}/summary").json()

    assert first == second
    assert set(first.keys()) == ALLOWED_SUMMARY_KEYS
    assert set(first["summary"].keys()) == ALLOWED_NESTED_SUMMARY_KEYS
    assert isinstance(first["topics_count"], int)
    assert isinstance(first["bibliography_count"], int)
    assert isinstance(first["gaps_count"], int)
    assert_no_forbidden_terms(first)
