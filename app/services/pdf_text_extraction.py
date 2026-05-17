from __future__ import annotations

from io import BytesIO
from pathlib import Path

import fitz
import pdfplumber

from app.domain.models import (
    DocumentIngestionStatus,
    DocumentProcessingError,
    PdfTextExtractionResult,
)


def normalize_pdf_text(text: str) -> str:
    normalized_lines: list[str] = []
    previous_blank = False
    for raw_line in text.replace("\x00", " ").splitlines():
        line = " ".join(raw_line.split())
        if not line:
            if not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False
    return "\n".join(normalized_lines).strip()


def is_pdf_textual_enough(text: str) -> bool:
    normalized = normalize_pdf_text(text)
    return bool(normalized and any(char.isalnum() for char in normalized))


def extract_text_from_pdf(file_path: Path) -> PdfTextExtractionResult:
    try:
        return _extract_with_pymupdf(file_path)
    except Exception:
        try:
            return _extract_with_pdfplumber(file_path)
        except Exception:
            error = DocumentProcessingError(
                code="pdf_text_extraction_failed",
                message="PDF text extraction failed for the current file.",
                stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                recoverable=True,
                metadata={},
            )
            return PdfTextExtractionResult(
                text=None,
                page_count=0,
                pages_extracted=0,
                extraction_method="pdf_text_extraction_failed",
                warnings=[],
                errors=[error],
                requires_ocr=False,
                extraction_status=DocumentIngestionStatus.FAILED.value,
            )


def _extract_with_pymupdf(file_path: Path) -> PdfTextExtractionResult:
    with fitz.open(file_path) as document:
        raw_pages = [page.get_text("text") or "" for page in document]
        page_count = document.page_count
    return _result_from_pages(
        raw_pages,
        page_count=page_count,
        extraction_method="pymupdf_text",
    )


def _extract_with_pdfplumber(file_path: Path) -> PdfTextExtractionResult:
    with pdfplumber.open(BytesIO(file_path.read_bytes())) as document:
        raw_pages = [(page.extract_text() or "") for page in document.pages]
        page_count = len(document.pages)
    return _result_from_pages(
        raw_pages,
        page_count=page_count,
        extraction_method="pdfplumber_text",
    )


def _result_from_pages(
    raw_pages: list[str],
    *,
    page_count: int,
    extraction_method: str,
) -> PdfTextExtractionResult:
    normalized_pages = [normalize_pdf_text(page) for page in raw_pages]
    text = "\n\n".join(page for page in normalized_pages if page).strip()
    if is_pdf_textual_enough(text):
        return PdfTextExtractionResult(
            text=text,
            page_count=page_count,
            pages_extracted=page_count,
            extraction_method=extraction_method,
            warnings=[],
            errors=[],
            requires_ocr=False,
            extraction_status=DocumentIngestionStatus.EXTRACTED.value,
        )
    return PdfTextExtractionResult(
        text=None,
        page_count=page_count,
        pages_extracted=page_count,
        extraction_method=extraction_method,
        warnings=["pdf_text_empty", "ocr_required"],
        errors=[],
        requires_ocr=True,
        extraction_status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
    )
