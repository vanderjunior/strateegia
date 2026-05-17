from __future__ import annotations

from pathlib import Path

from app.domain.models import UploadedMaterial
from app.repositories.json_store import JsonStudyRepository
from app.services.document_ingestion import ingest_uploaded_material


class MaterialService:
    def __init__(self, repository: JsonStudyRepository, storage_root: Path):
        self.repository = repository
        self.storage_root = Path(storage_root)

    def register_upload(
        self,
        *,
        user_id: str,
        original_filename: str,
        content_type: str,
        payload: bytes,
    ) -> UploadedMaterial:
        material = ingest_uploaded_material(
            user_id=user_id,
            original_filename=original_filename,
            content_type=content_type,
            payload=payload,
            storage_root=self.storage_root,
        )
        self.repository.save_uploaded_material(material, user_id=user_id)
        return material
