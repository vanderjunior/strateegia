from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.domain.models import (
    DocumentIngestionStatus,
    DocumentMetadata,
    MaterialSourceType,
    UploadedMaterial,
    utc_now,
)


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_MATERIAL_TYPES = {
    "edital",
    "study_material",
    "previous_exam",
    "bibliography",
    "note",
    "other",
    "unknown",
}


def normalize_material_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return "unknown"
    if normalized not in ALLOWED_MATERIAL_TYPES:
        raise ValueError("Unsupported material_type.")
    return normalized


def sanitize_filename(filename: str) -> str:
    base = Path(filename or "material").name.strip()
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    base = re.sub(r"_+", "_", base).strip("._")
    if not base:
        return "material"
    return base


def ingest_uploaded_material(
    *,
    user_id: str,
    original_filename: str,
    content_type: str,
    payload: bytes,
    storage_root: Path,
    material_type: str | None = None,
) -> UploadedMaterial:
    document_id = str(uuid4())
    safe_name = sanitize_filename(original_filename)
    suffix = Path(safe_name).suffix.lower()
    created_at = utc_now()
    user_dir = Path(storage_root) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{document_id}_{safe_name or 'material'}"
    file_path = user_dir / storage_name
    file_path.write_bytes(payload)
    relative_storage = Path("uploads") / user_id / storage_name

    normalized_material_type = normalize_material_type(material_type)
    metadata = DocumentMetadata(
        document_id=document_id,
        user_id=user_id,
        filename=safe_name or "material",
        original_filename=original_filename,
        content_type=content_type or "",
        size_bytes=len(payload),
        storage_path=relative_storage.as_posix(),
        source_type=MaterialSourceType.USER_UPLOAD.value,
        status=DocumentIngestionStatus.UPLOADED.value,
        created_at=created_at,
        updated_at=created_at,
        extraction_status=DocumentIngestionStatus.UPLOADED.value,
        metadata={"extension": suffix, "material_type": normalized_material_type},
    )

    if suffix == ".pdf":
        metadata.status = DocumentIngestionStatus.PENDING_EXTRACTION.value
        metadata.extraction_status = DocumentIngestionStatus.PENDING_EXTRACTION.value
        return UploadedMaterial(metadata=metadata, extracted_text=None)

    if suffix in {".txt", ".md"}:
        extracted = payload.decode("utf-8", errors="replace")
        metadata.status = DocumentIngestionStatus.EXTRACTED.value
        metadata.extraction_status = DocumentIngestionStatus.EXTRACTED.value
        metadata.metadata["text_length"] = len(extracted)
        return UploadedMaterial(metadata=metadata, extracted_text=extracted)

    metadata.status = DocumentIngestionStatus.UNSUPPORTED.value
    metadata.extraction_status = DocumentIngestionStatus.UNSUPPORTED.value
    metadata.error_message = "Unsupported material type for the current ingestion foundation."
    return UploadedMaterial(metadata=metadata, extracted_text=None)
