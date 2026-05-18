from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.ocr_documents import (
    create_client,
    minimal_textless_pdf_bytes,
    minimal_textual_pdf_bytes,
    ocr_insufficient_result,
    ocr_required_pdf_result,
    ocr_success_result,
    ocr_unavailable_result,
    register_and_login,
    upload_material_via_api,
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def assert_no_http_leakage(payload: object, *, forbidden_fragments: list[str]):
    dumped = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    for fragment in forbidden_fragments:
        assert fragment not in dumped
    return dumped


def test_process_endpoint_http_smoke_handles_ocr_disabled_and_unavailable_without_chunks(tmp_path, monkeypatch):
    owner, anonymous, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material_via_api(owner, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())

    assert anonymous.post(f"/api/materials/{document_id}/process").status_code == 401
    assert anonymous.get(f"/api/materials/{document_id}/pipeline").status_code == 401
    assert anonymous.get(f"/api/materials/{document_id}/chunks").status_code == 401
    assert anonymous.get(f"/api/materials/{document_id}/sections").status_code == 401

    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled_process = owner.post(f"/api/materials/{document_id}/process")
    assert disabled_process.status_code == 200
    disabled_payload = disabled_process.json()
    assert disabled_payload["current_stage"] == "extraction_pending"
    assert disabled_payload["chunk_count"] == 0
    assert disabled_payload["section_count"] == 0
    assert_no_http_leakage(
        disabled_payload,
        forbidden_fragments=["password_hash", str(tmp_path), "/uploads/", "/private/", "data:image", "fake-page"],
    )
    assert owner.get(f"/api/materials/{document_id}/chunks").json() == []
    assert owner.get(f"/api/materials/{document_id}/sections").json() == []

    unavailable_client, _ = create_client(tmp_path / "unavailable")
    register_and_login(unavailable_client, "owner")
    uploaded = upload_material_via_api(unavailable_client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr(
        "app.services.document_pipeline.extract_text_with_ocr",
        lambda *_args, **_kwargs: ocr_unavailable_result(warning_code="ocr_dependency_missing"),
    )

    unavailable_process = unavailable_client.post(f"/api/materials/{document_id}/process")
    assert unavailable_process.status_code == 200
    unavailable_payload = unavailable_process.json()
    assert unavailable_payload["current_stage"] == "extraction_pending"
    assert unavailable_payload["chunk_count"] == 0
    assert unavailable_payload["section_count"] == 0
    assert_no_http_leakage(
        unavailable_payload,
        forbidden_fragments=["password_hash", str(tmp_path / "unavailable"), "/uploads/", "/private/", "data:image", "fake-page"],
    )
    assert unavailable_client.get(f"/api/materials/{document_id}/chunks").json() == []
    assert unavailable_client.get(f"/api/materials/{document_id}/sections").json() == []


def test_process_endpoint_http_smoke_handles_fake_ocr_success_and_insufficient_cases(tmp_path, monkeypatch):
    success_client, _ = create_client(tmp_path / "success")
    register_and_login(success_client, "owner")
    uploaded = upload_material_via_api(success_client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_success_result())

    success_process = success_client.post(f"/api/materials/{document_id}/process")
    assert success_process.status_code == 200
    success_payload = success_process.json()
    assert success_payload["current_stage"] == "metadata_ready"
    assert success_payload["chunk_count"] >= 1
    assert success_payload["section_count"] >= 1
    assert json.dumps(success_payload, ensure_ascii=True)
    success_chunks = success_client.get(f"/api/materials/{document_id}/chunks")
    success_sections = success_client.get(f"/api/materials/{document_id}/sections")
    assert success_chunks.status_code == 200
    assert success_sections.status_code == 200
    assert len(success_chunks.json()) >= 1
    assert len(success_sections.json()) >= 1
    assert_no_http_leakage(
        success_chunks.json(),
        forbidden_fragments=["password_hash", str(tmp_path / "success"), "/uploads/", "/private/", "data:image", "fake-page"],
    )

    insufficient_client, _ = create_client(tmp_path / "insufficient")
    register_and_login(insufficient_client, "owner")
    uploaded = upload_material_via_api(insufficient_client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", lambda *_args, **_kwargs: ocr_insufficient_result())

    insufficient_process = insufficient_client.post(f"/api/materials/{document_id}/process")
    assert insufficient_process.status_code == 200
    insufficient_payload = insufficient_process.json()
    assert insufficient_payload["current_stage"] == "extraction_pending"
    assert insufficient_payload["chunk_count"] == 0
    assert insufficient_payload["section_count"] == 0
    assert insufficient_client.get(f"/api/materials/{document_id}/chunks").json() == []
    assert insufficient_client.get(f"/api/materials/{document_id}/sections").json() == []


def test_textual_pdf_and_txt_md_http_processing_bypass_ocr_even_when_enabled(tmp_path, monkeypatch):
    client, _ = create_client(tmp_path)
    register_and_login(client, "owner")
    textual_pdf = upload_material_via_api(
        client,
        "textual.pdf",
        minimal_textual_pdf_bytes("Texto embutido suficientemente claro para bypass do OCR."),
        "application/pdf",
    )
    txt_file = upload_material_via_api(
        client,
        "notes.txt",
        b"Texto normal.\n\nContinua aqui com material textual.",
        "text/plain",
    )

    monkeypatch.setenv("ENABLE_OCR", "true")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run for textual PDF or TXT/MD process flows")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)

    textual_response = client.post(f"/api/materials/{textual_pdf['metadata']['document_id']}/process")
    txt_response = client.post(f"/api/materials/{txt_file['metadata']['document_id']}/process")

    assert textual_response.status_code == 200
    assert txt_response.status_code == 200
    assert textual_response.json()["current_stage"] == "metadata_ready"
    assert txt_response.json()["current_stage"] == "metadata_ready"
    assert len(client.get(f"/api/materials/{textual_pdf['metadata']['document_id']}/chunks").json()) >= 1
    assert len(client.get(f"/api/materials/{txt_file['metadata']['document_id']}/chunks").json()) >= 1


def test_get_endpoints_dashboard_and_inspection_http_smoke_do_not_trigger_ocr_and_are_idempotent(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    user = register_and_login(client, "owner")
    uploaded = upload_material_via_api(client, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]
    monkeypatch.setenv("ENABLE_OCR", "false")
    process = client.post(f"/api/materials/{document_id}/process")
    assert process.status_code == 200

    before_state = client.get(f"/api/materials/{document_id}/pipeline").json()
    before_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run from GET-only surfaces")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)

    pipeline_first = client.get(f"/api/materials/{document_id}/pipeline")
    chunks_first = client.get(f"/api/materials/{document_id}/chunks")
    sections_first = client.get(f"/api/materials/{document_id}/sections")
    dashboard_first = client.get("/api/dashboard/overview")
    inspection_page = client.get("/inspection")
    inspection_runtime = client.get("/api/inspection/runtime")
    pipeline_second = client.get(f"/api/materials/{document_id}/pipeline")
    dashboard_second = client.get("/api/dashboard/overview")

    assert pipeline_first.status_code == 200
    assert chunks_first.status_code == 200
    assert sections_first.status_code == 200
    assert dashboard_first.status_code == 200
    assert inspection_page.status_code == 200
    assert inspection_runtime.status_code == 200
    assert pipeline_first.json() == before_state
    assert pipeline_second.json() == before_state
    assert dashboard_first.json() == dashboard_second.json()
    assert repository.load_progress(user_id=user["user_id"]).model_dump(mode="json") == before_progress
    assert_no_http_leakage(
        dashboard_first.json(),
        forbidden_fragments=["password_hash", str(tmp_path), "/uploads/", "/private/", "data:image", "fake-page", "raw_runtime_block"],
    )


def test_ocr_http_endpoints_remain_owner_only_and_do_not_cross_leak_between_users(tmp_path, monkeypatch):
    owner, other, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material_via_api(owner, "owner-scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setenv("ENABLE_OCR", "false")
    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    assert owner.post(f"/api/materials/{document_id}/process").status_code == 200

    assert anonymous.get("/api/dashboard/overview").status_code == 401
    assert other.post(f"/api/materials/{document_id}/process").status_code == 404
    assert other.get(f"/api/materials/{document_id}/pipeline").status_code == 404
    assert other.get(f"/api/materials/{document_id}/chunks").status_code == 404
    assert other.get(f"/api/materials/{document_id}/sections").status_code == 404

    owner_dashboard = owner.get("/api/dashboard/overview")
    other_dashboard = other.get("/api/dashboard/overview")
    assert owner_dashboard.status_code == 200
    assert other_dashboard.status_code == 200
    assert "owner-scan.pdf" in owner_dashboard.text
    assert "owner-scan.pdf" not in other_dashboard.text
