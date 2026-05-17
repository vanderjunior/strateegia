import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    return repository, material_service, pipeline_service


def upload_material(material_service: MaterialService, *, user_id: str, filename: str, content_type: str, payload: bytes):
    return material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        payload=payload,
    )


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def test_txt_pipeline_creates_extraction_chunks_sections_and_metadata(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="resumo.txt",
        content_type="text/plain",
        payload=b"Introducao geral.\n\nDetalhe importante.\n\nConclusao final.",
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")
    events = repository.list_document_pipeline_events(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "metadata_ready"
    assert state.stages_completed[-1] == "metadata_ready"
    assert extraction is not None
    assert extraction.text_length > 0
    assert extraction.extraction_status == "extracted"
    assert len(chunks) >= 1
    assert len(sections) == 1
    assert sections[0].title == "Document"
    assert state.metadata_status == "ready"
    assert state.chunk_count == len(chunks)
    assert state.section_count == len(sections)
    assert events
    json.dumps(state.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(extraction.model_dump(mode="json"), ensure_ascii=True)


def test_markdown_pipeline_detects_headings_and_preserves_chunk_order(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="anotacoes.md",
        content_type="text/markdown",
        payload=(
            b"# Introducao\n\nTexto inicial.\n\n## Detalhes\n\nTexto detalhado.\n\n### Fechamento\n\nFim."
        ),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "metadata_ready"
    assert [section.title for section in sections] == ["Introducao", "Detalhes", "Fechamento"]
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.text_length <= pipeline_service.max_chunk_size for chunk in chunks)


def test_pdf_pipeline_is_marked_pending_without_chunks_or_ocr(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="material.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )

    state = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    extraction = repository.get_document_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")

    assert state.current_stage == "extraction_pending"
    assert state.extraction_status == "pending_extraction"
    assert extraction is not None
    assert extraction.extraction_method in {"pymupdf_text", "pdfplumber_text", "pending_pdf_extraction"}
    assert chunks == []
    assert sections == []


def test_missing_file_and_unsupported_material_are_handled_safely(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    unsupported = upload_material(
        material_service,
        user_id="user-a",
        filename="dados.bin",
        content_type="application/octet-stream",
        payload=b"binario",
    )
    missing = upload_material(
        material_service,
        user_id="user-a",
        filename="faltante.txt",
        content_type="text/plain",
        payload=b"conteudo temporario",
    )
    (tmp_path / "uploads" / "user-a" / missing.metadata.storage_path.split("/")[-1]).unlink()

    unsupported_state = pipeline_service.process_document(unsupported.metadata.document_id, user_id="user-a")
    missing_state = pipeline_service.process_document(missing.metadata.document_id, user_id="user-a")

    assert unsupported_state.current_stage in {"unsupported", "failed"}
    assert unsupported_state.last_error is not None
    assert missing_state.current_stage == "failed"
    assert missing_state.last_error is not None


def test_reprocessing_is_deterministic_and_does_not_duplicate_artifacts(tmp_path):
    repository, material_service, pipeline_service = create_services(tmp_path)
    uploaded = upload_material(
        material_service,
        user_id="user-a",
        filename="deterministico.txt",
        content_type="text/plain",
        payload=b"Primeiro bloco.\n\nSegundo bloco.\n\nTerceiro bloco.",
    )

    first = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    first_chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    first_events = repository.list_document_pipeline_events(uploaded.metadata.document_id, user_id="user-a")
    second = pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    second_chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    second_events = repository.list_document_pipeline_events(uploaded.metadata.document_id, user_id="user-a")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [chunk.chunk_id for chunk in first_chunks] == [chunk.chunk_id for chunk in second_chunks]
    assert len(first_events) == len(second_events)
    json.dumps(second.model_dump(mode="json"), ensure_ascii=True)
