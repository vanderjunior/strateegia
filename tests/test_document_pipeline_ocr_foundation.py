import json
from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.domain.models import (
    DocumentIngestionStatus,
    DocumentProcessingError,
    OcrExtractionResult,
    PdfTextExtractionResult,
)
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService


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


def upload_material(material_service: MaterialService, *, user_id: str, filename: str, content_type: str, payload: bytes):
    return material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        payload=payload,
    )


def upload_material_via_api(client: TestClient, filename: str, content: bytes, content_type: str) -> dict[str, object]:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert response.status_code == 201
    return response.json()


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def ocr_required_pdf_result() -> PdfTextExtractionResult:
    return PdfTextExtractionResult(
        text=None,
        page_count=2,
        pages_extracted=2,
        extraction_method="pymupdf_text",
        warnings=["pdf_text_empty", "ocr_required"],
        errors=[],
        requires_ocr=True,
        extraction_status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
    )


def ocr_success_result(*, status: str = "ocr_completed", text: str | None = None, warnings: list[str] | None = None) -> OcrExtractionResult:
    return OcrExtractionResult(
        text=text or "Texto OCR suficientemente longo para alimentar chunking e sectioning com seguranca.",
        page_count=2,
        pages_attempted=2,
        pages_succeeded=2 if status == "ocr_completed" else 1,
        pages_failed=0 if status == "ocr_completed" else 1,
        requires_ocr=False,
        ocr_attempted=True,
        ocr_available=True,
        ocr_enabled=True,
        ocr_engine="tesseract",
        ocr_language="por+eng",
        extraction_method="ocr_tesseract",
        extraction_status=status,
        warnings=warnings or ([] if status == "ocr_completed" else ["ocr_page_failed", "ocr_partial_result"]),
        errors=[],
        metadata={"ocr_text_useful": True},
    )


def test_document_pipeline_preserves_safe_pending_state_when_ocr_is_disabled(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="scan.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    monkeypatch.setenv("ENABLE_OCR", "false")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "extraction_pending"
    assert extraction is not None
    assert extraction.metadata["requires_ocr"] is True
    assert extraction.metadata["ocr_enabled"] is False
    assert extraction.metadata["ocr_attempted"] is False
    assert "ocr_disabled" in extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a") == []
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a") == []


def test_document_pipeline_handles_ocr_unavailable_without_500(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="scan.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: OcrExtractionResult(
            text=None,
            page_count=2,
            pages_attempted=0,
            pages_succeeded=0,
            pages_failed=0,
            requires_ocr=True,
            ocr_attempted=False,
            ocr_available=False,
            ocr_enabled=True,
            ocr_engine="tesseract",
            ocr_language="por+eng",
            extraction_method="ocr_unavailable",
            extraction_status="ocr_unavailable",
            warnings=["ocr_dependency_missing"],
            errors=[],
            metadata={"ocr_text_useful": False},
        ),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "extraction_pending"
    assert extraction is not None
    assert extraction.metadata["ocr_attempted"] is False
    assert extraction.metadata["ocr_available"] is False
    assert "ocr_dependency_missing" in extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a") == []
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a") == []


def test_document_pipeline_uses_ocr_text_when_useful(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="scan.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_success_result())

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "metadata_ready"
    assert extraction is not None
    assert extraction.extraction_method == "ocr_tesseract"
    assert extraction.metadata["ocr_attempted"] is True
    assert extraction.metadata["ocr_text_useful"] is True
    assert extraction.metadata["requires_ocr"] is False
    assert len(chunks) >= 1
    assert len(sections) == 1
    assert "Texto OCR" in (extraction.text or "")


def test_document_pipeline_handles_partial_ocr_result_with_useful_text(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="scan.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: ocr_success_result(status="ocr_partial", warnings=["ocr_page_failed", "ocr_partial_result"]),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "metadata_ready"
    assert extraction is not None
    assert extraction.extraction_status == "ocr_partial"
    assert "ocr_partial_result" in extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")


def test_document_pipeline_keeps_insufficient_ocr_text_pending_without_chunks(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="scan.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: OcrExtractionResult(
            text=None,
            page_count=2,
            pages_attempted=2,
            pages_succeeded=1,
            pages_failed=1,
            requires_ocr=True,
            ocr_attempted=True,
            ocr_available=True,
            ocr_enabled=True,
            ocr_engine="tesseract",
            ocr_language="por+eng",
            extraction_method="ocr_tesseract",
            extraction_status="ocr_required",
            warnings=["ocr_text_insufficient", "ocr_page_failed"],
            errors=[],
            metadata={"ocr_text_useful": False},
        ),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "extraction_pending"
    assert extraction is not None
    assert extraction.metadata["ocr_attempted"] is True
    assert extraction.metadata["ocr_text_useful"] is False
    assert "ocr_text_insufficient" in extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a") == []
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a") == []


def test_textual_pdf_and_txt_md_paths_do_not_call_ocr_even_when_enabled(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    monkeypatch.setenv("ENABLE_OCR", "true")
    uploaded_pdf = upload_material(
        material_service,
        user_id="user-a",
        filename="textual.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes("Texto util dentro do PDF."),
    )
    uploaded_txt = upload_material(
        material_service,
        user_id="user-a",
        filename="notes.txt",
        content_type="text/plain",
        payload=b"Texto normal.\n\nContinua aqui.",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("OCR should not run for textual PDF or TXT/MD documents")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    pipeline_service.process_document(uploaded_pdf.metadata.document_id, user_id="user-a")
    pipeline_service.process_document(uploaded_txt.metadata.document_id, user_id="user-a")

    pdf_extraction = repository.get_document_extraction_result(uploaded_pdf.metadata.document_id, user_id="user-a")
    txt_extraction = repository.get_document_extraction_result(uploaded_txt.metadata.document_id, user_id="user-a")
    assert pdf_extraction is not None and pdf_extraction.metadata["requires_ocr"] is False
    assert txt_extraction is not None and txt_extraction.extraction_method == "plain_text"


def test_get_endpoints_dashboard_and_inspection_do_not_trigger_ocr(monkeypatch, tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", build_pdf_bytes(""), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setenv("ENABLE_OCR", "false")
    process = client.post(f"/api/materials/{document_id}/process")
    assert process.status_code == 200

    def fail_if_called(*args, **kwargs):
        raise AssertionError("OCR should not run from GET-only surfaces")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    assert client.get(f"/api/materials/{document_id}/pipeline").status_code == 200
    assert client.get(f"/api/materials/{document_id}/chunks").status_code == 200
    assert client.get(f"/api/materials/{document_id}/sections").status_code == 200
    assert client.get("/api/dashboard/overview").status_code == 200
    assert client.get("/inspection").status_code == 200

    progress_before = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    progress_after = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    assert progress_before == progress_after
    json.dumps(client.get("/api/dashboard/overview").json(), ensure_ascii=True)


def test_process_endpoint_handles_ocr_disabled_unavailable_and_success_safely(monkeypatch, tmp_path):
    client, _ = create_client(tmp_path)
    register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", build_pdf_bytes(""), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())

    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled = client.post(f"/api/materials/{document_id}/process")
    assert disabled.status_code == 200
    assert disabled.json()["current_stage"] == "extraction_pending"

    client, _ = create_client(tmp_path / "unavailable")
    register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", build_pdf_bytes(""), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: OcrExtractionResult(
            text=None,
            page_count=1,
            pages_attempted=0,
            pages_succeeded=0,
            pages_failed=0,
            requires_ocr=True,
            ocr_attempted=False,
            ocr_available=False,
            ocr_enabled=True,
            ocr_engine="tesseract",
            ocr_language="por+eng",
            extraction_method="ocr_unavailable",
            extraction_status="ocr_unavailable",
            warnings=["ocr_binary_missing"],
            errors=[],
            metadata={"ocr_text_useful": False},
        ),
    )
    unavailable = client.post(f"/api/materials/{document_id}/process")
    assert unavailable.status_code == 200
    assert unavailable.json()["current_stage"] == "extraction_pending"

    client, _ = create_client(tmp_path / "success")
    register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", build_pdf_bytes(""), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_success_result())
    success = client.post(f"/api/materials/{document_id}/process")
    assert success.status_code == 200
    assert success.json()["current_stage"] == "metadata_ready"
    json.dumps(success.json(), ensure_ascii=True)
