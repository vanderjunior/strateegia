import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_SUMMARY_KEYS = {
    "document_id",
    "status",
    "steps",
    "steps_count",
    "has_ocr_warning",
    "ready_for_review",
    "section_count",
    "chunk_count",
    "warnings_count",
    "source",
}


ALLOWED_STEP_KEYS = {
    "key",
    "label",
    "state",
    "warnings_count",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-PIPELINE-SHOULD-NOT-LEAK",
    "OTHER-PIPELINE-SHOULD-NOT-LEAK",
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
    "worker",
    "job trace",
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


def assert_bounded_pipeline_summary(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_SUMMARY_KEYS
    assert payload["source"] == "user_scope"
    assert payload["status"] in {
        "uploaded",
        "text_extracted",
        "segmented",
        "ocr_required",
        "ready_for_review",
        "pending",
        "unknown",
    }
    assert isinstance(payload["steps"], list)
    assert payload["steps_count"] == len(payload["steps"])
    assert isinstance(payload["has_ocr_warning"], bool)
    assert isinstance(payload["ready_for_review"], bool)
    assert isinstance(payload["section_count"], int)
    assert isinstance(payload["chunk_count"], int)
    assert isinstance(payload["warnings_count"], int)
    for step in payload["steps"]:
        assert set(step.keys()) == ALLOWED_STEP_KEYS
        assert step["key"] in {"uploaded", "text_extracted", "segmented", "ready_for_review"}
        assert step["state"] in {"done", "pending", "needs_review", "unknown"}
        assert isinstance(step["warnings_count"], int)


def test_pipeline_summary_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/materials/doc-unknown/pipeline/summary")

    assert response.status_code == 401


def test_pipeline_summary_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/materials/doc-unknown/pipeline/summary")

    assert response.status_code == 404


def test_pipeline_summary_returns_own_bounded_status(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="../../pipeline-summary.md",
        content=b"# Roteiro\n\nRAW-PIPELINE-SHOULD-NOT-LEAK",
        process=True,
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.get(f"/api/materials/{document_id}/pipeline/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["document_id"] == document_id
    assert payload["status"] in {"segmented", "ready_for_review", "text_extracted"}
    assert payload["chunk_count"] >= 1
    assert payload["section_count"] >= 0
    assert_bounded_pipeline_summary(payload)
    assert_no_forbidden_terms(payload)


def test_pipeline_summary_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_upload = upload_material(
        owner,
        filename="owner-pipeline.md",
        content=b"# Owner\n\nRAW-PIPELINE-SHOULD-NOT-LEAK",
        process=True,
    )
    other_upload = upload_material(
        other,
        filename="other-pipeline.md",
        content=b"# Other\n\nOTHER-PIPELINE-SHOULD-NOT-LEAK",
        process=True,
    )

    owner_document_id = owner_upload["metadata"]["document_id"]
    other_document_id = other_upload["metadata"]["document_id"]

    assert other.get(f"/api/materials/{owner_document_id}/pipeline/summary").status_code == 404
    other_response = other.get(f"/api/materials/{other_document_id}/pipeline/summary")
    owner_response = owner.get(f"/api/materials/{owner_document_id}/pipeline/summary")

    assert other_response.status_code == 200
    assert owner_response.status_code == 200
    assert other_response.json()["document_id"] == other_document_id
    assert owner_response.json()["document_id"] == owner_document_id
    assert_no_forbidden_terms(other_response.json())
    assert_no_forbidden_terms(owner_response.json())


def test_pipeline_summary_pending_material_is_stable(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "pending-user")
    uploaded = upload_material(
        owner,
        filename="pending.txt",
        content=b"linha 1",
        content_type="text/plain",
        process=False,
    )
    document_id = uploaded["metadata"]["document_id"]

    first = owner.get(f"/api/materials/{document_id}/pipeline/summary").json()
    second = owner.get(f"/api/materials/{document_id}/pipeline/summary").json()

    assert first == second
    assert first["document_id"] == document_id
    assert first["status"] in {"pending", "uploaded", "text_extracted"}
    assert first["steps_count"] == 4
    assert first["chunk_count"] == 0
    assert first["section_count"] == 0
    assert first["ready_for_review"] is False
    assert_bounded_pipeline_summary(first)
    assert_no_forbidden_terms(first)


def test_pipeline_summary_shape_is_deterministic_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-user")
    uploaded = upload_material(
        owner,
        filename="stable-pipeline.md",
        content=b"# Estavel\n\nconteudo seguro",
        process=True,
    )
    document_id = uploaded["metadata"]["document_id"]

    first = owner.get(f"/api/materials/{document_id}/pipeline/summary").json()
    second = owner.get(f"/api/materials/{document_id}/pipeline/summary").json()

    assert first == second
    assert_bounded_pipeline_summary(first)
    assert_no_forbidden_terms(first)
