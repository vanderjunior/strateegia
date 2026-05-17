import json

import fitz

from app.services.pdf_text_extraction import extract_text_from_pdf


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def test_textual_pdf_extraction_returns_text_and_page_metadata(tmp_path):
    pdf_path = tmp_path / "texto.pdf"
    pdf_path.write_bytes(build_pdf_bytes("Competencia tributaria.", "Fiscalizacao aduaneira."))

    result = extract_text_from_pdf(pdf_path)

    assert result.extraction_status == "extracted"
    assert result.extraction_method in {"pymupdf_text", "pdfplumber_text"}
    assert "Competencia tributaria" in (result.text or "")
    assert result.page_count == 2
    assert result.pages_extracted == 2
    assert result.requires_ocr is False
    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)


def test_textless_pdf_returns_safe_ocr_required_result(tmp_path):
    pdf_path = tmp_path / "vazio.pdf"
    pdf_path.write_bytes(build_pdf_bytes(""))

    result = extract_text_from_pdf(pdf_path)

    assert result.extraction_status == "pending_extraction"
    assert result.requires_ocr is True
    assert "ocr_required" in result.warnings
    assert "pdf_text_empty" in result.warnings
    assert result.text in {None, ""}


def test_invalid_pdf_returns_safe_failure_without_path_leakage(tmp_path):
    pdf_path = tmp_path / "quebrado.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 quebrado sem estrutura valida")

    result = extract_text_from_pdf(pdf_path)
    serialized = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)

    assert result.extraction_status == "failed"
    assert result.errors
    assert str(tmp_path) not in serialized
    assert "quebrado.pdf" not in serialized

