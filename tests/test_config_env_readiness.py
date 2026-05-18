from __future__ import annotations

from pathlib import Path

from app import config
from app.services import ocr_adapter


def test_config_defaults_and_invalid_values_remain_secure_by_default(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENABLE_INSPECTION", raising=False)
    monkeypatch.delenv("REQUIRE_AUTH_FOR_INSPECTION", raising=False)
    monkeypatch.delenv("INSPECTION_ALLOWED_IN_PRODUCTION", raising=False)

    assert config.get_app_env() == "development"
    assert config.inspection_enabled() is True
    assert config.inspection_requires_auth() is False

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_INSPECTION", "talvez")
    monkeypatch.setenv("INSPECTION_ALLOWED_IN_PRODUCTION", "talvez")
    monkeypatch.setenv("REQUIRE_AUTH_FOR_INSPECTION", "talvez")

    assert config.get_app_env() == "production"
    assert config.inspection_enabled() is False
    assert config.inspection_requires_auth() is True

    monkeypatch.setenv("APP_ENV", "desconhecido")
    assert config.get_app_env() == "development"

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_INSPECTION", "true")
    monkeypatch.setenv("INSPECTION_ALLOWED_IN_PRODUCTION", "true")
    monkeypatch.delenv("REQUIRE_AUTH_FOR_INSPECTION", raising=False)
    assert config.inspection_enabled() is True
    assert config.inspection_requires_auth() is True


def test_ocr_config_readiness_defaults_and_bounds_remain_optional(monkeypatch):
    monkeypatch.delenv("ENABLE_OCR", raising=False)
    monkeypatch.delenv("OCR_ENGINE", raising=False)
    monkeypatch.delenv("OCR_LANGUAGE", raising=False)
    monkeypatch.delenv("OCR_MAX_PAGES", raising=False)
    monkeypatch.delenv("OCR_RENDER_DPI", raising=False)

    defaults = ocr_adapter.load_ocr_config()
    assert defaults.enabled is False
    assert defaults.engine == "tesseract"
    assert defaults.language == "por+eng"
    assert defaults.max_pages == ocr_adapter.DEFAULT_OCR_MAX_PAGES
    assert defaults.render_dpi == ocr_adapter.DEFAULT_OCR_RENDER_DPI

    monkeypatch.setenv("ENABLE_OCR", "sim")
    monkeypatch.setenv("OCR_MAX_PAGES", "999")
    monkeypatch.setenv("OCR_RENDER_DPI", "999")
    invalid = ocr_adapter.load_ocr_config()
    assert invalid.enabled is False
    assert invalid.max_pages == ocr_adapter.OCR_MAX_PAGES_HARD_LIMIT
    assert invalid.render_dpi == ocr_adapter.OCR_RENDER_DPI_HARD_LIMIT

    monkeypatch.setenv("ENABLE_OCR", "true")
    monkeypatch.setenv("OCR_MAX_PAGES", "-10")
    monkeypatch.setenv("OCR_RENDER_DPI", "abc")
    fallback = ocr_adapter.load_ocr_config()
    assert fallback.enabled is True
    assert fallback.max_pages == ocr_adapter.DEFAULT_OCR_MAX_PAGES
    assert fallback.render_dpi == ocr_adapter.DEFAULT_OCR_RENDER_DPI


def test_readme_and_requirements_reflect_current_product_server_surface():
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()

    for snippet in [
        "/dashboard",
        "/inspection",
        "/api/dashboard/overview",
        "/api/inspection/runtime",
        "ocr e desabilitado por padrao",
        "tesseract",
        "nao roda no upload",
        "nao chama, encapsula ou reaproveita `/api/inspection/runtime`".lower(),
        "candidate-based",
        "study cycle candidato",
        "simulado blueprint",
        "sem geracao final de questoes",
        "sem execucao/correcao de simulados",
    ]:
        assert snippet in readme

    assert "pytesseract" not in requirements
    assert "pillow" not in requirements
