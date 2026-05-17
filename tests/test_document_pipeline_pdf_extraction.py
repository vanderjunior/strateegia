import json
from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    return repository, material_service, pipeline_service


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


def upload_material(client: TestClient, filename: str, content: bytes, content_type: str) -> dict[str, object]:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert response.status_code == 201
    return response.json()


def test_textual_pdf_processes_into_pipeline_chunks_and_sections(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="manual.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes("Primeira pagina de texto.", "Segunda pagina relevante."),
    )

    first = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    second = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")
    events = repository.list_document_pipeline_events(uploaded.metadata.document_id, user_id="user-a")

    assert first.current_stage == "metadata_ready"
    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    assert extraction is not None
    assert extraction.extraction_status == "extracted"
    assert extraction.page_count == 2
    assert extraction.metadata["requires_ocr"] is False
    assert len(chunks) >= 1
    assert len(sections) == 1
    assert sections[0].title == "Document"
    assert first.chunk_count == len(chunks)
    assert first.section_count == len(sections)
    assert events
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)


def test_textless_pdf_stays_pending_with_ocr_warning_and_no_chunks(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="escaneado.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "extraction_pending"
    assert extraction is not None
    assert "ocr_required" in extraction.warnings
    assert chunks == []
    assert sections == []


def test_invalid_pdf_fails_safely_without_path_leakage(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="invalido.pdf",
        content_type="application/pdf",
        payload=b"%PDF-1.4 quebrado sem estrutura valida",
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    serialized = json.dumps((extraction or state).model_dump(mode="json"), ensure_ascii=True)

    assert state.current_stage == "failed"
    assert state.last_error is not None
    assert extraction is not None
    assert extraction.errors
    assert str(tmp_path) not in serialized


def test_pdf_process_endpoint_succeeds_for_textual_pdf_owner(tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "pdf-owner")
    uploaded = upload_material(
        client,
        "manual.pdf",
        build_pdf_bytes("Texto util do PDF."),
        "application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    process = client.post(f"/api/materials/{document_id}/process")
    pipeline = client.get(f"/api/materials/{document_id}/pipeline")
    chunks = client.get(f"/api/materials/{document_id}/chunks")
    sections = client.get(f"/api/materials/{document_id}/sections")

    assert process.status_code == 200
    assert process.json()["current_stage"] == "metadata_ready"
    assert pipeline.status_code == 200
    assert chunks.status_code == 200
    assert sections.status_code == 200
    assert len(chunks.json()) >= 1
    assert len(sections.json()) == 1
