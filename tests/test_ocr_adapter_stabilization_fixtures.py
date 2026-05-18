from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services import ocr_adapter
from tests.fixtures.ocr_documents import (
    BrokenFitz,
    FakePytesseract,
    assert_json_safe,
    build_ocr_required_pdf_material,
    build_textual_pdf_material,
    create_client,
    create_services,
    fake_ocr_long_pdf_page_count,
    fake_ocr_page_texts_empty,
    fake_ocr_page_texts_insufficient,
    fake_ocr_page_texts_partial,
    fake_ocr_page_texts_success,
    malformed_pdf_bytes,
    minimal_textless_pdf_bytes,
    minimal_textual_pdf_bytes,
    monkeypatch_ocr_failure,
    monkeypatch_ocr_success,
    monkeypatch_ocr_unavailable,
    ocr_insufficient_result,
    ocr_required_pdf_result,
    ocr_success_result,
    ocr_unavailable_result,
    register_and_login,
    upload_material_via_api,
)


def test_ocr_fixture_helpers_are_deterministic_small_and_json_safe():
    textual = minimal_textual_pdf_bytes()
    textless = minimal_textless_pdf_bytes()
    malformed = malformed_pdf_bytes()
    payload = {
        "success": fake_ocr_page_texts_success(),
        "partial": [str(item) for item in fake_ocr_page_texts_partial()],
        "empty": fake_ocr_page_texts_empty(),
        "insufficient": [str(item) for item in fake_ocr_page_texts_insufficient()],
        "long_count": fake_ocr_long_pdf_page_count(),
    }

    assert textual.startswith(b"%PDF")
    assert textless.startswith(b"%PDF")
    assert abs(len(minimal_textual_pdf_bytes()) - len(textual)) < 128
    assert abs(len(minimal_textless_pdf_bytes()) - len(textless)) < 128
    assert len(textual) < 20_000
    assert len(textless) < 20_000
    assert len(malformed) < 1_000
    assert_json_safe(payload)


def test_ocr_disabled_fixture_returns_safe_result(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes())
    monkeypatch.setenv("ENABLE_OCR", "false")

    result = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped = assert_json_safe(result.model_dump(mode="json"))

    assert result.extraction_status == "ocr_disabled"
    assert result.ocr_attempted is False
    assert result.ocr_enabled is False
    assert "ocr_disabled" in result.warnings
    assert str(tmp_path) not in dumped


@pytest.mark.parametrize(
    ("reason", "warning_code"),
    [
        ("dependency", "ocr_dependency_missing"),
        ("binary", "ocr_binary_missing"),
        ("renderer", "pdf_renderer_unavailable"),
    ],
)
def test_ocr_unavailable_fixtures_are_safe(monkeypatch, tmp_path, reason: str, warning_code: str):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes())
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch_ocr_unavailable(monkeypatch, ocr_adapter, reason=reason)

    result = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped = assert_json_safe(result.model_dump(mode="json"))

    assert result.extraction_status == "ocr_unavailable"
    assert result.ocr_attempted is False
    assert warning_code in result.warnings
    assert str(tmp_path) not in dumped
    assert "scan.pdf" not in dumped


def test_ocr_success_fixture_counts_pages_and_avoids_image_data(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes(page_count=2))
    monkeypatch.setenv("ENABLE_OCR", "true")
    fake_tesseract = monkeypatch_ocr_success(monkeypatch, ocr_adapter, page_count=2)

    result = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped = assert_json_safe(result.model_dump(mode="json"))

    assert result.extraction_status == "ocr_completed"
    assert result.pages_attempted == 2
    assert result.pages_succeeded == 2
    assert result.pages_failed == 0
    assert result.text
    assert len(fake_tesseract.calls) == 2
    assert "fake-page" not in dumped
    assert "image_data" not in dumped


def test_ocr_partial_useful_and_insufficient_fixtures_are_conservative(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes(page_count=2))
    monkeypatch.setenv("ENABLE_OCR", "true")

    monkeypatch_ocr_success(monkeypatch, ocr_adapter, page_count=2, page_texts=fake_ocr_page_texts_partial())
    partial = ocr_adapter.extract_text_with_ocr(pdf_path)
    assert partial.extraction_status == "ocr_partial"
    assert partial.pages_succeeded == 1
    assert partial.pages_failed == 1
    assert "ocr_page_failed" in partial.warnings
    assert "ocr_partial_result" in partial.warnings

    monkeypatch_ocr_success(monkeypatch, ocr_adapter, page_count=2, page_texts=fake_ocr_page_texts_insufficient())
    insufficient = ocr_adapter.extract_text_with_ocr(pdf_path)
    assert insufficient.extraction_status in {"ocr_required", "ocr_failed"}
    assert insufficient.text in {None, ""}
    assert "ocr_text_insufficient" in insufficient.warnings or "ocr_text_empty" in insufficient.warnings


def test_ocr_empty_engine_failure_and_invalid_pdf_fixtures_are_safe(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes(page_count=2))
    monkeypatch.setenv("ENABLE_OCR", "true")

    monkeypatch_ocr_success(monkeypatch, ocr_adapter, page_count=2, page_texts=fake_ocr_page_texts_empty())
    empty = ocr_adapter.extract_text_with_ocr(pdf_path)
    assert empty.extraction_status in {"ocr_failed", "ocr_required"}
    assert "ocr_text_empty" in empty.warnings

    monkeypatch_ocr_failure(monkeypatch, ocr_adapter, page_count=2)
    failed = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped_failed = assert_json_safe(failed.model_dump(mode="json"))
    assert failed.extraction_status in {"ocr_failed", "ocr_required"}
    assert any(error.code == "ocr_engine_error" for error in failed.errors)
    assert str(tmp_path) not in dumped_failed

    invalid_pdf_path = tmp_path / "invalid.pdf"
    invalid_pdf_path.write_bytes(malformed_pdf_bytes())
    fake_tesseract = FakePytesseract(fake_ocr_page_texts_success())

    def fake_import_invalid(name: str):
        if name == "fitz":
            return BrokenFitz()
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import_invalid)
    invalid = ocr_adapter.extract_text_with_ocr(invalid_pdf_path)
    dumped_invalid = assert_json_safe(invalid.model_dump(mode="json"))
    assert invalid.extraction_status in {"invalid_pdf", "ocr_failed"}
    assert any(error.code in {"invalid_pdf", "ocr_render_error"} for error in invalid.errors)
    assert str(tmp_path) not in dumped_invalid
    assert "invalid.pdf" not in dumped_invalid


def test_ocr_page_limit_fixture_respects_configured_and_hard_caps(monkeypatch, tmp_path):
    pdf_path = tmp_path / "long.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes(page_count=1))
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_MAX_PAGES", "999")
    page_count = fake_ocr_long_pdf_page_count()
    page_texts = ["Texto OCR util para pagina longa e controlada pelo limite."] * page_count
    fake_tesseract = monkeypatch_ocr_success(monkeypatch, ocr_adapter, page_count=page_count, page_texts=page_texts)

    result = ocr_adapter.extract_text_with_ocr(pdf_path)

    assert result.pages_attempted == ocr_adapter.OCR_MAX_PAGES_HARD_LIMIT
    assert result.pages_succeeded == ocr_adapter.OCR_MAX_PAGES_HARD_LIMIT
    assert "ocr_max_pages_reached" in result.warnings
    assert len(fake_tesseract.calls) == ocr_adapter.OCR_MAX_PAGES_HARD_LIMIT


def test_ocr_config_is_read_at_call_time_and_invalid_values_fall_back(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(minimal_textless_pdf_bytes())

    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled = ocr_adapter.extract_text_with_ocr(pdf_path)
    assert disabled.extraction_status == "ocr_disabled"

    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_MAX_PAGES", "abc")
    monkeypatch.setenv("OCR_RENDER_DPI", "999")
    monkeypatch_ocr_unavailable(monkeypatch, ocr_adapter, reason="dependency")
    enabled = ocr_adapter.extract_text_with_ocr(pdf_path)
    config = ocr_adapter.load_ocr_config()

    assert enabled.extraction_status == "ocr_unavailable"
    assert config.enabled is True
    assert config.max_pages == ocr_adapter.DEFAULT_OCR_MAX_PAGES
    assert config.render_dpi == ocr_adapter.OCR_RENDER_DPI_HARD_LIMIT


def test_ocr_text_usefulness_threshold_fixture_is_deterministic():
    assert ocr_adapter.is_ocr_text_useful("") is False
    assert ocr_adapter.is_ocr_text_useful("x y z") is False
    assert ocr_adapter.is_ocr_text_useful("um dois tres quatro cinco seis sete oito nove") is False
    assert ocr_adapter.is_ocr_text_useful("um dois tres quatro cinco seis sete oito nove dez") is True
    assert ocr_adapter.is_ocr_text_useful("Texto suficientemente longo para passar do threshold de cinquenta caracteres.") is True


def test_document_pipeline_textual_pdf_first_preserves_ocr_bypass(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = build_textual_pdf_material(material_service, user_id="user-a")
    monkeypatch.setenv("ENABLE_OCR", "true")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run for textual PDFs")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "metadata_ready"
    assert extraction is not None
    assert extraction.metadata["requires_ocr"] is False


def test_document_pipeline_ocr_disabled_and_unavailable_fixtures_preserve_pending_state(monkeypatch, tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = build_ocr_required_pdf_material(material_service, user_id="user-a")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())

    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled_state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    disabled_extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    assert disabled_state.current_stage == "extraction_pending"
    assert disabled_extraction is not None
    assert disabled_extraction.metadata["ocr_enabled"] is False
    assert disabled_extraction.metadata["ocr_attempted"] is False
    assert "ocr_disabled" in disabled_extraction.warnings

    repository, material_service, pipeline_service = create_services(tmp_path / "unavailable")
    uploaded = build_ocr_required_pdf_material(material_service, user_id="user-a")
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: ocr_unavailable_result(warning_code="ocr_dependency_missing"),
    )
    unavailable_state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    unavailable_extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    assert unavailable_state.current_stage == "extraction_pending"
    assert unavailable_extraction is not None
    assert unavailable_extraction.metadata["ocr_available"] is False
    assert "ocr_dependency_missing" in unavailable_extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a") == []
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a") == []


def test_document_pipeline_ocr_success_partial_and_insufficient_fixtures(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")

    repository, material_service, pipeline_service = create_services(tmp_path / "success")
    uploaded = build_ocr_required_pdf_material(material_service, user_id="user-a")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_success_result())
    success_state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    success_extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    assert success_state.current_stage == "metadata_ready"
    assert success_extraction is not None
    assert success_extraction.extraction_method == "ocr_tesseract"
    assert success_extraction.metadata["ocr_attempted"] is True
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")

    repository, material_service, pipeline_service = create_services(tmp_path / "partial")
    uploaded = build_ocr_required_pdf_material(material_service, user_id="user-a")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: ocr_success_result(status="ocr_partial", warnings=["ocr_page_failed", "ocr_partial_result"]),
    )
    partial_state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    partial_extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    assert partial_state.current_stage == "metadata_ready"
    assert partial_extraction is not None
    assert partial_extraction.extraction_status == "ocr_partial"
    assert "ocr_partial_result" in partial_extraction.warnings

    repository, material_service, pipeline_service = create_services(tmp_path / "insufficient")
    uploaded = build_ocr_required_pdf_material(material_service, user_id="user-a")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_insufficient_result())
    insufficient_state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    insufficient_extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    assert insufficient_state.current_stage == "extraction_pending"
    assert insufficient_extraction is not None
    assert "ocr_text_insufficient" in insufficient_extraction.warnings
    assert repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a") == []
    assert repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a") == []


def test_get_dashboard_and_inspection_surfaces_do_not_trigger_ocr(monkeypatch, tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setenv("ENABLE_OCR", "false")
    assert client.post(f"/api/materials/{document_id}/process").status_code == 200

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run from GET/dashboard/inspection surfaces")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    assert client.get(f"/api/materials/{document_id}/pipeline").status_code == 200
    assert client.get(f"/api/materials/{document_id}/chunks").status_code == 200
    assert client.get(f"/api/materials/{document_id}/sections").status_code == 200
    overview = client.get("/api/dashboard/overview")
    inspection = client.get("/inspection")
    assert overview.status_code == 200
    assert inspection.status_code == 200
    progress_before = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    progress_after = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    assert progress_before == progress_after


def test_user_scope_txt_md_and_process_endpoint_ocr_paths_remain_safe(monkeypatch, tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)

    register_and_login(owner, "owner")
    register_and_login(other, "other")

    uploaded = upload_material_via_api(owner, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())

    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled = owner.post(f"/api/materials/{document_id}/process")
    assert disabled.status_code == 200
    disabled_dumped = assert_json_safe(disabled.json())
    assert "password_hash" not in disabled_dumped
    assert str(tmp_path) not in disabled_dumped

    assert other.post(f"/api/materials/{document_id}/process").status_code == 404
    assert other.get(f"/api/materials/{document_id}/pipeline").status_code == 404
    assert other.get(f"/api/materials/{document_id}/chunks").status_code == 404
    assert other.get(f"/api/materials/{document_id}/sections").status_code == 404
    assert "scan.pdf" not in other.get("/api/dashboard/overview").text

    uploaded_txt = upload_material_via_api(owner, "notes.txt", b"Texto normal.\n\nContinua aqui.", "text/plain")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run for TXT/MD documents")

    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    txt_processed = owner.post(f"/api/materials/{uploaded_txt['metadata']['document_id']}/process")
    assert txt_processed.status_code == 200

    success_root = tmp_path / "success-api"
    success_client, _ = create_client(success_root)
    register_and_login(success_client, "owner")
    uploaded_success = upload_material_via_api(success_client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_success_result())
    success = success_client.post(f"/api/materials/{uploaded_success['metadata']['document_id']}/process")
    assert success.status_code == 200
    success_dumped = assert_json_safe(success.json())
    assert "password_hash" not in success_dumped
    assert str(success_root) not in success_dumped
