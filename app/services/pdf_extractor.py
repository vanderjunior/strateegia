from __future__ import annotations

from io import BytesIO

import fitz
import pdfplumber


class PdfTextExtractor:
    def extract(self, payload: bytes) -> str:
        text = self._extract_with_pymupdf(payload)
        if text.strip():
            return text
        return self._extract_with_pdfplumber(payload)

    def _extract_with_pymupdf(self, payload: bytes) -> str:
        with fitz.open(stream=payload, filetype="pdf") as document:
            pages = [page.get_text("text") for page in document]
        return "\n".join(pages).strip()

    def _extract_with_pdfplumber(self, payload: bytes) -> str:
        with pdfplumber.open(BytesIO(payload)) as document:
            pages = [(page.extract_text() or "") for page in document.pages]
        return "\n".join(pages).strip()
