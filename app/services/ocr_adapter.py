from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import parse_bool_env
from app.domain.models import (
    DocumentIngestionStatus,
    DocumentProcessingError,
    OcrExtractionResult,
)
from app.services.pdf_text_extraction import normalize_pdf_text


DEFAULT_OCR_ENGINE = "tesseract"
DEFAULT_OCR_LANGUAGE = "por+eng"
DEFAULT_OCR_MAX_PAGES = 5
DEFAULT_OCR_RENDER_DPI = 150
OCR_MAX_PAGES_HARD_LIMIT = 20
OCR_RENDER_DPI_HARD_LIMIT = 300
MIN_USEFUL_OCR_TEXT_LENGTH = 50
MIN_USEFUL_OCR_TOKENS = 10


class OcrAdapterConfig(BaseModel):
    enabled: bool = False
    engine: str = DEFAULT_OCR_ENGINE
    language: str = DEFAULT_OCR_LANGUAGE
    max_pages: int = DEFAULT_OCR_MAX_PAGES
    render_dpi: int = DEFAULT_OCR_RENDER_DPI


class OcrAdapterAvailability(BaseModel):
    enabled: bool = False
    available: bool = False
    engine: str = DEFAULT_OCR_ENGINE
    language: str = DEFAULT_OCR_LANGUAGE
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


def _parse_int_env(name: str, default: int, hard_limit: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        value = default
    else:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            value = default
    if value <= 0:
        value = default
    return min(value, hard_limit)


def load_ocr_config(
    *,
    enabled: bool | None = None,
    engine: str | None = None,
    language: str | None = None,
    max_pages: int | None = None,
    dpi: int | None = None,
) -> OcrAdapterConfig:
    return OcrAdapterConfig(
        enabled=parse_bool_env("ENABLE_OCR", False) if enabled is None else bool(enabled),
        engine=(engine or os.getenv("OCR_ENGINE") or DEFAULT_OCR_ENGINE).strip() or DEFAULT_OCR_ENGINE,
        language=(language or os.getenv("OCR_LANGUAGE") or DEFAULT_OCR_LANGUAGE).strip() or DEFAULT_OCR_LANGUAGE,
        max_pages=min(
            max_pages if isinstance(max_pages, int) and max_pages > 0 else _parse_int_env("OCR_MAX_PAGES", DEFAULT_OCR_MAX_PAGES, OCR_MAX_PAGES_HARD_LIMIT),
            OCR_MAX_PAGES_HARD_LIMIT,
        ),
        render_dpi=min(
            dpi if isinstance(dpi, int) and dpi > 0 else _parse_int_env("OCR_RENDER_DPI", DEFAULT_OCR_RENDER_DPI, OCR_RENDER_DPI_HARD_LIMIT),
            OCR_RENDER_DPI_HARD_LIMIT,
        ),
    )


def is_ocr_text_useful(
    text: str | None,
    *,
    min_chars: int = MIN_USEFUL_OCR_TEXT_LENGTH,
    min_tokens: int = MIN_USEFUL_OCR_TOKENS,
) -> bool:
    normalized = normalize_pdf_text(text or "")
    if not normalized:
        return False
    if len(normalized) >= min_chars:
        return True
    tokens = [item for item in normalized.split() if item.strip()]
    return len(tokens) >= min_tokens


def should_attempt_ocr(pdf_text_result, config: OcrAdapterConfig | None = None) -> bool:
    resolved = config or load_ocr_config()
    return bool(resolved.enabled and getattr(pdf_text_result, "requires_ocr", False))


def check_ocr_availability(config: OcrAdapterConfig | None = None) -> OcrAdapterAvailability:
    resolved = config or load_ocr_config()
    if not resolved.enabled:
        return OcrAdapterAvailability(
            enabled=False,
            available=False,
            engine=resolved.engine,
            language=resolved.language,
            warnings=["ocr_disabled"],
        )

    try:
        importlib.import_module("fitz")
    except ImportError:
        return OcrAdapterAvailability(
            enabled=True,
            available=False,
            engine=resolved.engine,
            language=resolved.language,
            warnings=["pdf_renderer_unavailable"],
        )

    if resolved.engine != DEFAULT_OCR_ENGINE:
        return OcrAdapterAvailability(
            enabled=True,
            available=False,
            engine=resolved.engine,
            language=resolved.language,
            warnings=["ocr_dependency_missing"],
            errors=[
                DocumentProcessingError(
                    code="ocr_engine_error",
                    message="The configured OCR engine is not supported by the current foundation.",
                    stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                    recoverable=True,
                    metadata={"ocr_engine": resolved.engine},
                )
            ],
        )

    try:
        pytesseract = importlib.import_module("pytesseract")
    except ImportError:
        return OcrAdapterAvailability(
            enabled=True,
            available=False,
            engine=resolved.engine,
            language=resolved.language,
            warnings=["ocr_dependency_missing"],
        )

    try:
        version = pytesseract.get_tesseract_version()
    except (FileNotFoundError, OSError, RuntimeError):
        return OcrAdapterAvailability(
            enabled=True,
            available=False,
            engine=resolved.engine,
            language=resolved.language,
            warnings=["ocr_binary_missing"],
        )

    return OcrAdapterAvailability(
        enabled=True,
        available=True,
        engine=resolved.engine,
        language=resolved.language,
        metadata={"engine_version": str(version)},
    )


def extract_text_with_ocr(
    pdf_path: Path,
    *,
    max_pages: int | None = None,
    language: str | None = None,
    dpi: int | None = None,
    enabled: bool | None = None,
) -> OcrExtractionResult:
    config = load_ocr_config(
        enabled=enabled,
        language=language,
        max_pages=max_pages,
        dpi=dpi,
    )
    availability = check_ocr_availability(config)
    if not availability.enabled:
        return OcrExtractionResult(
            text=None,
            requires_ocr=True,
            ocr_attempted=False,
            ocr_available=False,
            ocr_enabled=False,
            ocr_engine=config.engine,
            ocr_language=config.language,
            extraction_method="ocr_disabled",
            extraction_status="ocr_disabled",
            warnings=["ocr_disabled"],
            errors=availability.errors,
            metadata=_base_metadata(config, text_useful=False),
        )
    if not availability.available:
        return OcrExtractionResult(
            text=None,
            requires_ocr=True,
            ocr_attempted=False,
            ocr_available=False,
            ocr_enabled=True,
            ocr_engine=config.engine,
            ocr_language=config.language,
            extraction_method="ocr_unavailable",
            extraction_status="ocr_unavailable",
            warnings=availability.warnings,
            errors=availability.errors,
            metadata=_base_metadata(config, text_useful=False),
        )

    fitz = importlib.import_module("fitz")
    pytesseract = importlib.import_module("pytesseract")
    warnings: list[str] = []
    errors: list[DocumentProcessingError] = []
    page_texts: list[str] = []

    try:
        with fitz.open(pdf_path) as document:
            page_count = int(getattr(document, "page_count", 0) or 0)
            pages_attempted = min(page_count, config.max_pages)
            if page_count > pages_attempted:
                warnings.append("ocr_max_pages_reached")

            pages_succeeded = 0
            pages_failed = 0
            for page_index, page in enumerate(document):
                if page_index >= pages_attempted:
                    break
                try:
                    pixmap = page.get_pixmap(dpi=config.render_dpi, alpha=False)
                    with tempfile.NamedTemporaryFile(suffix=".png") as rendered_page:
                        rendered_page.write(pixmap.tobytes("png"))
                        rendered_page.flush()
                        page_text = normalize_pdf_text(
                            pytesseract.image_to_string(rendered_page.name, lang=config.language)
                        )
                    if page_text:
                        page_texts.append(page_text)
                    pages_succeeded += 1
                except Exception:
                    pages_failed += 1
                    warnings.append("ocr_page_failed")
                    errors.append(
                        DocumentProcessingError(
                            code="ocr_engine_error",
                            message="OCR failed for one rendered page.",
                            stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                            recoverable=True,
                            metadata={"page_index": page_index},
                        )
                    )
    except Exception:
        return OcrExtractionResult(
            text=None,
            requires_ocr=True,
            ocr_attempted=True,
            ocr_available=True,
            ocr_enabled=True,
            ocr_engine=config.engine,
            ocr_language=config.language,
            extraction_method="ocr_invalid_pdf",
            extraction_status="invalid_pdf",
            warnings=[],
            errors=[
                DocumentProcessingError(
                    code="invalid_pdf",
                    message="The PDF could not be rendered safely for OCR.",
                    stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                    recoverable=True,
                    metadata={},
                )
            ],
            metadata=_base_metadata(config, text_useful=False),
        )

    combined_text = normalize_pdf_text("\n\n".join(page_texts))
    useful = is_ocr_text_useful(combined_text)

    if useful:
        status = "ocr_partial" if errors else "ocr_completed"
        if status == "ocr_partial" and "ocr_partial_result" not in warnings:
            warnings.append("ocr_partial_result")
        return OcrExtractionResult(
            text=combined_text,
            page_count=page_count,
            pages_attempted=pages_attempted,
            pages_succeeded=pages_succeeded,
            pages_failed=pages_failed,
            requires_ocr=False,
            ocr_attempted=True,
            ocr_available=True,
            ocr_enabled=True,
            ocr_engine=config.engine,
            ocr_language=config.language,
            extraction_method="ocr_tesseract",
            extraction_status=status,
            warnings=warnings,
            errors=errors,
            metadata=_base_metadata(config, text_useful=True),
        )

    if combined_text:
        warnings.append("ocr_text_insufficient")
    else:
        warnings.append("ocr_text_empty")

    failure_status = "ocr_failed" if pages_succeeded == 0 and pages_failed == pages_attempted else "ocr_required"
    return OcrExtractionResult(
        text=None,
        page_count=page_count,
        pages_attempted=pages_attempted,
        pages_succeeded=pages_succeeded,
        pages_failed=pages_failed,
        requires_ocr=True,
        ocr_attempted=True,
        ocr_available=True,
        ocr_enabled=True,
        ocr_engine=config.engine,
        ocr_language=config.language,
        extraction_method="ocr_tesseract",
        extraction_status=failure_status,
        warnings=warnings,
        errors=errors,
        metadata=_base_metadata(config, text_useful=False),
    )


def _base_metadata(config: OcrAdapterConfig, *, text_useful: bool) -> dict[str, object]:
    return {
        "ocr_engine": config.engine,
        "ocr_language": config.language,
        "ocr_max_pages": config.max_pages,
        "ocr_render_dpi": config.render_dpi,
        "ocr_usefulness_threshold": {
            "min_chars": MIN_USEFUL_OCR_TEXT_LENGTH,
            "min_tokens": MIN_USEFUL_OCR_TOKENS,
        },
        "ocr_text_useful": text_useful,
    }
