import json

from app.domain.models import DocumentIngestionStatus
from app.services.document_ingestion import ingest_uploaded_material


def test_txt_and_markdown_are_extracted_with_metadata(tmp_path):
    txt = ingest_uploaded_material(
        user_id="user-a",
        original_filename="resumo final.txt",
        content_type="text/plain",
        payload=b"linha 1\nlinha 2",
        storage_root=tmp_path / "uploads",
    )
    md = ingest_uploaded_material(
        user_id="user-a",
        original_filename="anotacoes.md",
        content_type="text/markdown",
        payload=b"# Titulo\n\nConteudo",
        storage_root=tmp_path / "uploads",
    )

    assert txt.metadata.extraction_status == DocumentIngestionStatus.EXTRACTED.value
    assert "linha 1" in (txt.extracted_text or "")
    assert md.metadata.extraction_status == DocumentIngestionStatus.EXTRACTED.value
    assert "Titulo" in (md.extracted_text or "")
    json.dumps(txt.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(md.model_dump(mode="json"), ensure_ascii=True)


def test_pdf_is_registered_as_pending_extraction(tmp_path):
    uploaded = ingest_uploaded_material(
        user_id="user-a",
        original_filename="material.pdf",
        content_type="application/pdf",
        payload=b"%PDF-1.4 test",
        storage_root=tmp_path / "uploads",
    )

    assert uploaded.metadata.status == DocumentIngestionStatus.PENDING_EXTRACTION.value
    assert uploaded.metadata.extraction_status == DocumentIngestionStatus.PENDING_EXTRACTION.value
    assert uploaded.extracted_text is None


def test_unsupported_file_is_marked_without_crashing(tmp_path):
    uploaded = ingest_uploaded_material(
        user_id="user-a",
        original_filename="planilha.csv",
        content_type="text/csv",
        payload=b"a,b,c",
        storage_root=tmp_path / "uploads",
    )

    assert uploaded.metadata.status == DocumentIngestionStatus.UNSUPPORTED.value
    assert uploaded.metadata.error_message
    assert uploaded.extracted_text is None


def test_ingestion_preserves_safe_metadata_and_prevents_path_traversal(tmp_path):
    uploaded = ingest_uploaded_material(
        user_id="user-a",
        original_filename="../../segredo final!!.txt",
        content_type="text/plain",
        payload=b"conteudo",
        storage_root=tmp_path / "uploads",
    )

    assert ".." not in uploaded.metadata.filename
    assert ".." not in uploaded.metadata.storage_path
    assert uploaded.metadata.user_id == "user-a"
    assert uploaded.metadata.size_bytes == len(b"conteudo")
