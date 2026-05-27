import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_SUMMARY_KEYS = {
    "document_id",
    "display_filename",
    "content_type",
    "created_at",
    "updated_at",
    "processing_status",
    "extraction_status",
    "chunk_count",
    "section_count",
    "review_state",
    "warnings_count",
    "latest_pipeline_status",
    "pipeline",
    "source",
}


ALLOWED_PIPELINE_KEYS = {
    "status",
    "steps_count",
    "has_ocr_warning",
    "ready_for_review",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-MATERIAL-SUMMARY-SHOULD-NOT-LEAK",
    "OTHER-SUMMARY-SHOULD-NOT-LEAK",
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


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str = "text/markdown",
    process: bool = False,
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert uploaded.status_code == 201
    payload = uploaded.json()
    if process:
        processed = client.post(f"/api/materials/{payload['metadata']['document_id']}/process")
        assert processed.status_code == 200
    return payload


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def test_material_summary_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/materials/doc-unknown/summary")

    assert response.status_code == 401


def test_material_summary_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/materials/doc-unknown/summary")

    assert response.status_code == 404


def test_material_summary_returns_own_bounded_material_summary(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="../../roteiro-summary.md",
        content=b"# Roteiro\n\nRAW-MATERIAL-SUMMARY-SHOULD-NOT-LEAK",
        process=True,
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.get(f"/api/materials/{document_id}/summary")
    payload = response.json()

    assert response.status_code == 200
    assert set(payload.keys()) == ALLOWED_SUMMARY_KEYS
    assert set(payload["pipeline"].keys()) == ALLOWED_PIPELINE_KEYS
    assert payload["document_id"] == document_id
    assert payload["display_filename"] == "roteiro-summary.md"
    assert payload["content_type"] == "md"
    assert payload["source"] == "user_scope"
    assert payload["chunk_count"] >= 1
    assert payload["section_count"] >= 0
    assert isinstance(payload["warnings_count"], int)
    assert isinstance(payload["pipeline"]["steps_count"], int)
    assert isinstance(payload["pipeline"]["has_ocr_warning"], bool)
    assert isinstance(payload["pipeline"]["ready_for_review"], bool)
    assert_no_forbidden_terms(payload)


def test_material_summary_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_upload = upload_material(
        owner,
        filename="owner-summary.md",
        content=b"# Owner\n\nRAW-MATERIAL-SUMMARY-SHOULD-NOT-LEAK",
        process=True,
    )
    other_upload = upload_material(
        other,
        filename="other-summary.md",
        content=b"# Other\n\nOTHER-SUMMARY-SHOULD-NOT-LEAK",
        process=True,
    )

    owner_document_id = owner_upload["metadata"]["document_id"]
    other_document_id = other_upload["metadata"]["document_id"]

    assert other.get(f"/api/materials/{owner_document_id}/summary").status_code == 404
    other_response = other.get(f"/api/materials/{other_document_id}/summary")
    owner_response = owner.get(f"/api/materials/{owner_document_id}/summary")

    assert other_response.status_code == 200
    assert owner_response.status_code == 200
    assert other_response.json()["document_id"] == other_document_id
    assert owner_response.json()["document_id"] == owner_document_id
    assert_no_forbidden_terms(other_response.json())
    assert_no_forbidden_terms(owner_response.json())


def test_material_summary_shape_is_deterministic_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-user")
    uploaded = upload_material(
        owner,
        filename="stable.txt",
        content=b"linha 1",
        content_type="text/plain",
        process=False,
    )
    document_id = uploaded["metadata"]["document_id"]

    first = owner.get(f"/api/materials/{document_id}/summary").json()
    second = owner.get(f"/api/materials/{document_id}/summary").json()

    assert first == second
    assert set(first.keys()) == ALLOWED_SUMMARY_KEYS
    assert set(first["pipeline"].keys()) == ALLOWED_PIPELINE_KEYS
    assert first["content_type"] in {"pdf", "txt", "md", "unknown"}
    assert isinstance(first["chunk_count"], int)
    assert isinstance(first["section_count"], int)
    assert_no_forbidden_terms(first)
