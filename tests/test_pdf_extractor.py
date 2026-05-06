from pathlib import Path

import fitz

from app.services.pdf_extractor import PdfTextExtractor


def test_pdf_extractor_reads_pdf_text(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Competencia tributaria e fiscalizacao.")
    document.save(pdf_path)
    document.close()

    extractor = PdfTextExtractor()

    text = extractor.extract(pdf_path.read_bytes())

    assert "Competencia tributaria" in text
