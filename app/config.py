from __future__ import annotations

import os
from pathlib import Path


TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}
VALID_APP_ENVS = {"development", "test", "production"}
DEFAULT_STUDYFLOW_DATA_FILE = Path("data") / "study_data.json"
DEFAULT_STUDYFLOW_UPLOAD_ROOT = Path("data") / "uploads"


def get_app_env() -> str:
    value = str(os.getenv("APP_ENV", "development") or "development").strip().lower()
    if value in VALID_APP_ENVS:
        return value
    return "development"


def is_production() -> bool:
    return get_app_env() == "production"


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    return default


def get_path_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return Path(str(raw).strip()).expanduser()


def get_studyflow_data_file() -> Path:
    return get_path_env("STUDYFLOW_DATA_FILE", DEFAULT_STUDYFLOW_DATA_FILE)


def get_studyflow_upload_root(default: Path | None = None) -> Path:
    return get_path_env("STUDYFLOW_UPLOAD_ROOT", default or DEFAULT_STUDYFLOW_UPLOAD_ROOT)


def inspection_allowed_in_production() -> bool:
    return parse_bool_env("INSPECTION_ALLOWED_IN_PRODUCTION", False)


def inspection_enabled() -> bool:
    if is_production():
        if not inspection_allowed_in_production():
            return False
        return parse_bool_env("ENABLE_INSPECTION", False)
    return parse_bool_env("ENABLE_INSPECTION", True)


def inspection_requires_auth() -> bool:
    default = True if is_production() else False
    return parse_bool_env("REQUIRE_AUTH_FOR_INSPECTION", default)
