from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.domain.models import (
    DocumentIngestionStatus,
    OcrExtractionResult,
    PdfTextExtractionResult,
)
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService


def minimal_textual_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("Texto PDF textual suficiente para bypass do OCR.",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def minimal_textless_pdf_bytes(page_count: int = 1) -> bytes:
    document = fitz.open()
    for _ in range(max(page_count, 1)):
        document.new_page()
    payload = document.tobytes()
    document.close()
    return payload


def malformed_pdf_bytes() -> bytes:
    return b"%PDF-1.4 broken synthetic fixture"


def fake_ocr_page_texts_success() -> list[str]:
    return [
        "Primeira pagina OCR com conteudo suficientemente longo para ser util.",
        "Segunda pagina OCR com vocabulario adicional para completar o threshold.",
    ]


def fake_ocr_page_texts_partial() -> list[object]:
    return [
        "Pagina OCR parcial com detalhes tecnicos suficientes para ainda ser util.",
        RuntimeError("synthetic ocr page failure"),
    ]


def fake_ocr_page_texts_empty() -> list[str]:
    return ["", ""]


def fake_ocr_page_texts_insufficient() -> list[object]:
    return ["ruido", RuntimeError("synthetic ocr page failure")]


def fake_ocr_long_pdf_page_count() -> int:
    return 25


def ocr_required_pdf_result(page_count: int = 2) -> PdfTextExtractionResult:
    return PdfTextExtractionResult(
        text=None,
        page_count=page_count,
        pages_extracted=page_count,
        extraction_method="pymupdf_text",
        warnings=["pdf_text_empty", "ocr_required"],
        errors=[],
        requires_ocr=True,
        extraction_status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
    )


def ocr_success_result(
    *,
    status: str = "ocr_completed",
    text: str | None = None,
    warnings: list[str] | None = None,
    pages_attempted: int = 2,
    pages_succeeded: int | None = None,
    pages_failed: int | None = None,
) -> OcrExtractionResult:
    resolved_succeeded = pages_succeeded if pages_succeeded is not None else (pages_attempted if status == "ocr_completed" else max(pages_attempted - 1, 1))
    resolved_failed = pages_failed if pages_failed is not None else (0 if status == "ocr_completed" else max(pages_attempted - resolved_succeeded, 1))
    return OcrExtractionResult(
        text=text or "Texto OCR suficientemente longo para alimentar chunking e sectioning com seguranca.",
        page_count=pages_attempted,
        pages_attempted=pages_attempted,
        pages_succeeded=resolved_succeeded,
        pages_failed=resolved_failed,
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


def ocr_unavailable_result(*, warning_code: str) -> OcrExtractionResult:
    return OcrExtractionResult(
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
        warnings=[warning_code],
        errors=[],
        metadata={"ocr_text_useful": False},
    )


def ocr_insufficient_result() -> OcrExtractionResult:
    return OcrExtractionResult(
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
    )


class FakePixmap:
    def __init__(self, page_index: int):
        self.page_index = page_index

    def tobytes(self, fmt: str) -> bytes:
        assert fmt == "png"
        return f"fake-page-{self.page_index}".encode("utf-8")


class FakePage:
    def __init__(self, page_index: int):
        self.page_index = page_index

    def get_pixmap(self, *, dpi: int, alpha: bool):
        assert dpi > 0
        assert alpha is False
        return FakePixmap(self.page_index)


class FakeDocument:
    def __init__(self, page_count: int):
        self.page_count = page_count
        self._pages = [FakePage(index) for index in range(page_count)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def __iter__(self):
        return iter(self._pages)


class FakeFitz:
    def __init__(self, page_count: int):
        self.page_count = page_count

    def open(self, _path):
        return FakeDocument(self.page_count)


class BrokenFitz:
    def open(self, _path):
        raise RuntimeError("synthetic broken renderer")


class FakePytesseract:
    def __init__(self, page_texts: list[object], *, binary_missing: bool = False):
        self.page_texts = list(page_texts)
        self.binary_missing = binary_missing
        self.calls: list[dict[str, object]] = []

    def get_tesseract_version(self):
        if self.binary_missing:
            raise FileNotFoundError("tesseract not found")
        return "5.0.0"

    def image_to_string(self, image_path, *, lang: str):
        self.calls.append({"image_path": str(image_path), "lang": lang})
        result = self.page_texts[len(self.calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result


def monkeypatch_ocr_success(monkeypatch, ocr_module, *, page_count: int = 2, page_texts: list[object] | None = None) -> FakePytesseract:
    fake_tesseract = FakePytesseract(page_texts or fake_ocr_page_texts_success())

    def fake_import(name: str):
        if name == "fitz":
            return FakeFitz(page_count)
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_module.importlib, "import_module", fake_import)
    return fake_tesseract


def monkeypatch_ocr_unavailable(monkeypatch, ocr_module, *, reason: str):
    def fake_import(name: str):
        if reason == "renderer" and name == "fitz":
            raise ImportError("missing fitz")
        if name == "fitz":
            return FakeFitz(1)
        if reason == "dependency" and name == "pytesseract":
            raise ImportError("missing pytesseract")
        if name == "pytesseract":
            return FakePytesseract(fake_ocr_page_texts_success(), binary_missing=(reason == "binary"))
        raise AssertionError(name)

    monkeypatch.setattr(ocr_module.importlib, "import_module", fake_import)


def monkeypatch_ocr_failure(monkeypatch, ocr_module, *, page_count: int = 2):
    return monkeypatch_ocr_success(
        monkeypatch,
        ocr_module,
        page_count=page_count,
        page_texts=[RuntimeError("synthetic ocr engine failure") for _ in range(page_count)],
    )


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


def build_ocr_required_pdf_material(material_service: MaterialService, *, user_id: str, filename: str = "scan.pdf"):
    return upload_material(
        material_service,
        user_id=user_id,
        filename=filename,
        content_type="application/pdf",
        payload=minimal_textless_pdf_bytes(),
    )


def build_textual_pdf_material(material_service: MaterialService, *, user_id: str, filename: str = "textual.pdf"):
    return upload_material(
        material_service,
        user_id=user_id,
        filename=filename,
        content_type="application/pdf",
        payload=minimal_textual_pdf_bytes(),
    )


def assert_json_safe(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)
