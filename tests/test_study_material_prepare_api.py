import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.domain.models import DocumentIngestionStatus
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.ocr_documents import minimal_textual_pdf_bytes, ocr_required_pdf_result


ALLOWED_PREPARE_KEYS = {
    "document_id",
    "preparation_status",
    "material_type",
    "section_count",
    "chunk_count",
    "warnings_count",
    "ready_for_study",
    "source",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-STUDY-MATERIAL-SHOULD-NOT-LEAK",
    "OTHER-STUDY-MATERIAL-SHOULD-NOT-LEAK",
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
    material_type: str = "study_material",
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_prepare_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_PREPARE_KEYS
    assert payload["preparation_status"] in {"ready_for_study", "needs_review", "not_ready", "failed"}
    assert payload["material_type"] == "study_material"
    assert isinstance(payload["section_count"], int)
    assert isinstance(payload["chunk_count"], int)
    assert isinstance(payload["warnings_count"], int)
    assert isinstance(payload["ready_for_study"], bool)
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_prepare_study_material_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.post("/api/materials/doc-unknown/study/prepare")

    assert response.status_code == 401


def test_prepare_study_material_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.post("/api/materials/doc-unknown/study/prepare")

    assert response.status_code == 404


def test_prepare_study_material_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula\n\nOTHER-STUDY-MATERIAL-SHOULD-NOT-LEAK",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = other.post(f"/api/materials/{document_id}/study/prepare")

    assert response.status_code == 404


def test_prepare_study_material_rejects_non_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="edital.md",
        content=b"# Edital\n\nConteudo seguro.",
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/study/prepare")

    assert response.status_code == 422
    assert "study material" in response.json()["detail"].lower()


def test_prepare_fresh_txt_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "txt-owner")
    uploaded = upload_material(
        owner,
        filename="aula.txt",
        content=b"Conteudo de estudo seguro para preparacao.\nCom segunda linha.",
        content_type="text/plain",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/study/prepare")
    payload = response.json()

    assert response.status_code == 200
    assert payload["document_id"] == document_id
    assert payload["preparation_status"] == "ready_for_study"
    assert payload["ready_for_study"] is True
    assert payload["section_count"] >= 1
    assert payload["chunk_count"] >= 1
    assert_bounded_prepare_payload(payload)


def test_prepare_fresh_md_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "md-owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=b"# Tema principal\n\nRAW-STUDY-MATERIAL-SHOULD-NOT-LEAK\n\n## Subtema\n\nConteudo seguro.",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/study/prepare")
    payload = response.json()

    assert response.status_code == 200
    assert payload["preparation_status"] == "ready_for_study"
    assert payload["section_count"] >= 1
    assert payload["chunk_count"] >= 1
    assert_bounded_prepare_payload(payload)


def test_prepare_textual_pdf_study_material_without_ocr(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "pdf-owner")
    uploaded = upload_material(
        owner,
        filename="aula-textual.pdf",
        content=minimal_textual_pdf_bytes("Conteudo textual suficiente para preparar material de estudo."),
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    def fail_ocr(*_args, **_kwargs):
        raise AssertionError("OCR should not be called for controlled study material preparation.")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_ocr)

    response = owner.post(f"/api/materials/{document_id}/study/prepare")
    payload = response.json()

    assert response.status_code == 200
    assert payload["preparation_status"] == "ready_for_study"
    assert payload["ready_for_study"] is True
    assert payload["section_count"] >= 1
    assert payload["chunk_count"] >= 1
    assert_bounded_prepare_payload(payload)


def test_prepare_ocr_required_pdf_returns_not_ready_without_ocr(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "ocr-owner")
    uploaded = upload_material(
        owner,
        filename="aula-escaneada.pdf",
        content=b"%PDF-1.4 synthetic",
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_from_pdf",
        lambda _path: ocr_required_pdf_result(),
    )

    def fail_ocr(*_args, **_kwargs):
        raise AssertionError("OCR should not be called for controlled study material preparation.")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_ocr)

    response = owner.post(f"/api/materials/{document_id}/study/prepare")
    payload = response.json()
    extraction = repository.get_document_extraction_result(document_id, user_id=user["user_id"])

    assert response.status_code == 200
    assert payload["preparation_status"] == "not_ready"
    assert payload["ready_for_study"] is False
    assert payload["section_count"] == 0
    assert payload["chunk_count"] == 0
    assert extraction is None or extraction.extraction_status == DocumentIngestionStatus.PENDING_EXTRACTION.value
    assert_bounded_prepare_payload(payload)


def test_prepare_study_material_is_idempotent(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula\n\nConteudo de estudo seguro e estavel.",
    )
    document_id = uploaded["metadata"]["document_id"]

    first = owner.post(f"/api/materials/{document_id}/study/prepare").json()
    second = owner.post(f"/api/materials/{document_id}/study/prepare").json()

    assert first == second
    assert first["preparation_status"] == "ready_for_study"
    assert_bounded_prepare_payload(first)
