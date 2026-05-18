import json
from pathlib import Path

import fitz

from app.domain.models import DocumentProcessingError
from app.services import ocr_adapter


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def write_pdf(tmp_path, name: str, *pages: str) -> Path:
    pdf_path = tmp_path / name
    pdf_path.write_bytes(build_pdf_bytes(*pages))
    return pdf_path


class _FakePixmap:
    def __init__(self, page_index: int):
        self.page_index = page_index

    def tobytes(self, fmt: str) -> bytes:
        assert fmt == "png"
        return f"fake-page-{self.page_index}".encode("utf-8")


class _FakePage:
    def __init__(self, page_index: int):
        self.page_index = page_index

    def get_pixmap(self, *, dpi: int, alpha: bool):
        assert dpi > 0
        assert alpha is False
        return _FakePixmap(self.page_index)


class _FakeDocument:
    def __init__(self, page_count: int):
        self.page_count = page_count
        self._pages = [_FakePage(index) for index in range(page_count)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def __iter__(self):
        return iter(self._pages)


class _FakeFitz:
    def __init__(self, page_count: int):
        self.page_count = page_count

    def open(self, _path):
        return _FakeDocument(self.page_count)


class _FakePytesseract:
    def __init__(self, page_texts, *, binary_missing: bool = False):
        self.page_texts = list(page_texts)
        self.binary_missing = binary_missing
        self.calls = []

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


def test_default_ocr_config_is_disabled_and_safe(monkeypatch):
    monkeypatch.delenv("ENABLE_OCR", raising=False)
    monkeypatch.delenv("OCR_MAX_PAGES", raising=False)
    monkeypatch.delenv("OCR_RENDER_DPI", raising=False)

    config = ocr_adapter.load_ocr_config()

    assert config.enabled is False
    assert config.engine == "tesseract"
    assert config.language == "por+eng"
    assert config.max_pages == 5
    assert config.render_dpi == 150
    json.dumps(config.model_dump(mode="json"), ensure_ascii=True)


def test_invalid_ocr_env_values_fall_back_and_hard_caps_are_applied(monkeypatch):
    monkeypatch.setenv("ENABLE_OCR", "talvez")
    monkeypatch.setenv("OCR_MAX_PAGES", "999")
    monkeypatch.setenv("OCR_RENDER_DPI", "999")

    config = ocr_adapter.load_ocr_config()

    assert config.enabled is False
    assert config.max_pages == ocr_adapter.OCR_MAX_PAGES_HARD_LIMIT
    assert config.render_dpi == ocr_adapter.OCR_RENDER_DPI_HARD_LIMIT

    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_MAX_PAGES", "-1")
    monkeypatch.setenv("OCR_RENDER_DPI", "abc")
    config = ocr_adapter.load_ocr_config()

    assert config.enabled is True
    assert config.max_pages == ocr_adapter.DEFAULT_OCR_MAX_PAGES
    assert config.render_dpi == ocr_adapter.DEFAULT_OCR_RENDER_DPI


def test_ocr_availability_reports_disabled_and_missing_dependencies_safely(monkeypatch):
    monkeypatch.setenv("ENABLE_OCR", "false")
    disabled = ocr_adapter.check_ocr_availability()
    assert disabled.enabled is False
    assert disabled.available is False
    assert "ocr_disabled" in disabled.warnings

    monkeypatch.setenv("ENABLE_OCR", "true")

    def missing_renderer(name: str):
        if name == "fitz":
            raise ImportError("missing fitz")
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", missing_renderer)
    no_renderer = ocr_adapter.check_ocr_availability()
    assert no_renderer.available is False
    assert "pdf_renderer_unavailable" in no_renderer.warnings

    def missing_tesseract(name: str):
        if name == "fitz":
            return _FakeFitz(1)
        if name == "pytesseract":
            raise ImportError("missing pytesseract")
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", missing_tesseract)
    no_dependency = ocr_adapter.check_ocr_availability()
    assert no_dependency.available is False
    assert "ocr_dependency_missing" in no_dependency.warnings
    json.dumps(no_dependency.model_dump(mode="json"), ensure_ascii=True)


def test_ocr_binary_missing_and_renderer_unavailable_degrade_without_crash(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")
    pdf_path = write_pdf(tmp_path, "scan.pdf", "")

    fake_tesseract = _FakePytesseract(["texto"], binary_missing=True)

    def fake_import(name: str):
        if name == "fitz":
            return _FakeFitz(1)
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import)
    result = ocr_adapter.extract_text_with_ocr(pdf_path)

    assert result.extraction_status == "ocr_unavailable"
    assert result.ocr_attempted is False
    assert "ocr_binary_missing" in result.warnings
    assert result.text in {None, ""}


def test_ocr_text_usefulness_threshold_is_deterministic():
    assert ocr_adapter.is_ocr_text_useful("Texto longo o suficiente para ser util em OCR com varias palavras claras.") is True
    assert ocr_adapter.is_ocr_text_useful("") is False
    assert ocr_adapter.is_ocr_text_useful("x y z") is False
    assert ocr_adapter.is_ocr_text_useful("um dois tres quatro cinco seis sete oito nove") is False
    assert ocr_adapter.is_ocr_text_useful("um dois tres quatro cinco seis sete oito nove dez") is True


def test_ocr_adapter_success_counts_pages_and_avoids_image_data(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")
    pdf_path = write_pdf(tmp_path, "scan.pdf", "", "")
    fake_tesseract = _FakePytesseract(
        [
            "Primeira pagina OCR suficientemente detalhada para ser util.",
            "Segunda pagina OCR com texto adicional para formar um resultado util.",
        ]
    )

    def fake_import(name: str):
        if name == "fitz":
            return _FakeFitz(2)
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import)
    result = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)

    assert result.extraction_status == "ocr_completed"
    assert result.pages_attempted == 2
    assert result.pages_succeeded == 2
    assert result.pages_failed == 0
    assert result.ocr_attempted is True
    assert result.ocr_available is True
    assert result.text
    assert "Primeira pagina OCR" in result.text
    assert "image_data" not in dumped
    assert "fake-page" not in dumped


def test_ocr_adapter_partial_result_and_page_limits_are_bounded(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_MAX_PAGES", "1")
    pdf_path = write_pdf(tmp_path, "scan.pdf", "", "", "")
    fake_tesseract = _FakePytesseract(
        ["Texto OCR parcial mas suficientemente grande para permitir chunking posterior."]
    )

    def fake_import(name: str):
        if name == "fitz":
            return _FakeFitz(3)
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import)
    result = ocr_adapter.extract_text_with_ocr(pdf_path)

    assert result.extraction_status == "ocr_completed"
    assert result.pages_attempted == 1
    assert result.pages_succeeded == 1
    assert result.pages_failed == 0
    assert "ocr_max_pages_reached" in result.warnings


def test_ocr_adapter_partial_and_insufficient_results_are_conservative(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")
    useful_pdf = write_pdf(tmp_path, "partial.pdf", "", "")

    partial_tesseract = _FakePytesseract(
        [
            "Texto OCR parcial com detalhe suficiente para passar pelo threshold util.",
            RuntimeError("ocr engine failed"),
        ]
    )

    def fake_import_partial(name: str):
        if name == "fitz":
            return _FakeFitz(2)
        if name == "pytesseract":
            return partial_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import_partial)
    partial = ocr_adapter.extract_text_with_ocr(useful_pdf)

    assert partial.extraction_status == "ocr_partial"
    assert partial.pages_attempted == 2
    assert partial.pages_succeeded == 1
    assert partial.pages_failed == 1
    assert "ocr_page_failed" in partial.warnings
    assert "ocr_partial_result" in partial.warnings

    insufficient_tesseract = _FakePytesseract(["ruido", RuntimeError("ocr engine failed")])

    def fake_import_insufficient(name: str):
        if name == "fitz":
            return _FakeFitz(2)
        if name == "pytesseract":
            return insufficient_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import_insufficient)
    insufficient = ocr_adapter.extract_text_with_ocr(useful_pdf)

    assert insufficient.extraction_status in {"ocr_required", "ocr_failed"}
    assert insufficient.text in {None, ""}
    assert "ocr_text_insufficient" in insufficient.warnings or "ocr_text_empty" in insufficient.warnings


def test_ocr_adapter_handles_invalid_pdf_without_path_leakage(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_OCR", "true")
    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 quebrado")
    fake_tesseract = _FakePytesseract(["texto suficiente"])

    class BrokenFitz:
        def open(self, _path):
            raise RuntimeError("broken renderer")

    def fake_import(name: str):
        if name == "fitz":
            return BrokenFitz()
        if name == "pytesseract":
            return fake_tesseract
        raise AssertionError(name)

    monkeypatch.setattr(ocr_adapter.importlib, "import_module", fake_import)
    result = ocr_adapter.extract_text_with_ocr(pdf_path)
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)

    assert result.extraction_status in {"invalid_pdf", "ocr_failed"}
    assert result.errors
    assert str(tmp_path) not in dumped
    assert "invalid.pdf" not in dumped
