from __future__ import annotations

import re
from pathlib import Path

from app.domain.models import (
    DocumentChunk,
    DocumentExtractionResult,
    DocumentIngestionStatus,
    DocumentPipelineEvent,
    DocumentPipelineState,
    DocumentProcessingError,
    DocumentSection,
    UploadedMaterial,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.pdf_text_extraction import extract_text_from_pdf


PIPELINE_VERSION = "document-pipeline-v1"
DEFAULT_MAX_CHUNK_SIZE = 500
FINAL_PIPELINE_STAGES = {
    "metadata_ready",
    "extraction_pending",
    "unsupported",
    "failed",
}


class DocumentPipelineService:
    def __init__(
        self,
        repository: JsonStudyRepository,
        *,
        storage_root: Path,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    ):
        self.repository = repository
        self.storage_root = Path(storage_root)
        self.max_chunk_size = max_chunk_size

    def process_document(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> DocumentPipelineState:
        material = self.repository.get_uploaded_material(document_id, user_id=user_id)
        if material is None:
            raise ValueError("Document not found.")

        existing_state = self.repository.get_document_pipeline_state(document_id, user_id=user_id)
        if existing_state is not None and existing_state.current_stage in FINAL_PIPELINE_STAGES:
            return existing_state

        return self._process_material(material, user_id=user_id)

    def _process_material(
        self,
        material: UploadedMaterial,
        *,
        user_id: str | None,
    ) -> DocumentPipelineState:
        document_id = material.metadata.document_id
        created_at = utc_now()
        events: list[DocumentPipelineEvent] = []
        warnings: list[str] = []

        base_state = DocumentPipelineState(
            document_id=document_id,
            user_id=user_id,
            current_stage=DocumentIngestionStatus.TYPE_DETECTED.value,
            stages_completed=[
                DocumentIngestionStatus.UPLOADED.value,
                DocumentIngestionStatus.TYPE_DETECTED.value,
            ],
            extraction_status=DocumentIngestionStatus.TYPE_DETECTED.value,
            created_at=created_at,
            updated_at=created_at,
            pipeline_version=PIPELINE_VERSION,
        )
        events.append(
            self._event(
                material=material,
                stage=DocumentIngestionStatus.TYPE_DETECTED.value,
                status="ok",
                message="Document type detected.",
            )
        )

        suffix = str(material.metadata.metadata.get("extension") or Path(material.metadata.filename).suffix).lower()
        if suffix not in {".txt", ".md"}:
            if suffix == ".pdf":
                file_path = self._resolve_storage_path(material)
                if file_path is None or not file_path.exists():
                    error = DocumentProcessingError(
                        code="document_file_missing",
                        message="Stored document file could not be found.",
                        stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                        recoverable=True,
                        metadata={"document_id": document_id},
                    )
                    return self._finalize_failure(
                        material,
                        base_state,
                        stage=DocumentIngestionStatus.FAILED.value,
                        error=error,
                        warnings=warnings,
                        events=events,
                        user_id=user_id,
                    )
                return self._process_pdf_material(
                    material,
                    base_state,
                    file_path=file_path,
                    events=events,
                    user_id=user_id,
                )
            error = DocumentProcessingError(
                code="unsupported_material_type",
                message="Unsupported material type for the current document pipeline foundation.",
                stage=DocumentIngestionStatus.UNSUPPORTED.value,
                recoverable=True,
                metadata={"extension": suffix},
            )
            return self._finalize_failure(
                material,
                base_state,
                stage=DocumentIngestionStatus.UNSUPPORTED.value,
                error=error,
                warnings=warnings,
                events=events,
                user_id=user_id,
            )

        file_path = self._resolve_storage_path(material)
        if file_path is None or not file_path.exists():
            error = DocumentProcessingError(
                code="document_file_missing",
                message="Stored document file could not be found.",
                stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                recoverable=True,
                metadata={"document_id": document_id},
            )
            return self._finalize_failure(
                material,
                base_state,
                stage=DocumentIngestionStatus.FAILED.value,
                error=error,
                warnings=warnings,
                events=events,
                user_id=user_id,
            )

        events.append(
            self._event(
                material=material,
                stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                status="ok",
                message="Text extraction started.",
            )
        )
        try:
            raw_bytes = file_path.read_bytes()
        except OSError:
            error = DocumentProcessingError(
                code="document_read_failed",
                message="Stored document file could not be read.",
                stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                recoverable=True,
                metadata={"document_id": document_id},
            )
            return self._finalize_failure(
                material,
                base_state,
                stage=DocumentIngestionStatus.FAILED.value,
                error=error,
                warnings=warnings,
                events=events,
                user_id=user_id,
            )

        text = raw_bytes.decode("utf-8", errors="replace")
        if "\ufffd" in text:
            warnings.append("Input contained invalid UTF-8 bytes and was decoded with replacement characters.")

        return self._finalize_text_processing(
            material,
            base_state,
            text=text,
            extraction_method="markdown_text" if suffix == ".md" else "plain_text",
            page_count=0,
            pages_extracted=0,
            warnings=warnings,
            events=events,
            user_id=user_id,
            requires_ocr=False,
        )

    def _process_pdf_material(
        self,
        material: UploadedMaterial,
        base_state: DocumentPipelineState,
        *,
        file_path: Path,
        events: list[DocumentPipelineEvent],
        user_id: str | None,
    ) -> DocumentPipelineState:
        events.append(
            self._event(
                material=material,
                stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
                status="ok",
                message="PDF text extraction started.",
            )
        )
        pdf_result = extract_text_from_pdf(file_path)
        if pdf_result.extraction_status == DocumentIngestionStatus.EXTRACTED.value and pdf_result.text:
            return self._finalize_text_processing(
                material,
                base_state,
                text=pdf_result.text,
                extraction_method=pdf_result.extraction_method,
                page_count=pdf_result.page_count,
                pages_extracted=pdf_result.pages_extracted,
                warnings=pdf_result.warnings,
                events=events,
                user_id=user_id,
                requires_ocr=pdf_result.requires_ocr,
            )
        if pdf_result.requires_ocr:
            return self._finalize_pdf_pending(
                material,
                base_state,
                events=events,
                user_id=user_id,
                extraction_method=pdf_result.extraction_method,
                page_count=pdf_result.page_count,
                pages_extracted=pdf_result.pages_extracted,
                warnings=pdf_result.warnings,
            )
        error = pdf_result.errors[0] if pdf_result.errors else DocumentProcessingError(
            code="pdf_text_extraction_failed",
            message="PDF text extraction failed for the current file.",
            stage=DocumentIngestionStatus.EXTRACTION_STARTED.value,
            recoverable=True,
            metadata={},
        )
        return self._finalize_failure(
            material,
            base_state,
            stage=DocumentIngestionStatus.FAILED.value,
            error=error,
            warnings=pdf_result.warnings,
            events=events,
            user_id=user_id,
            extraction_method=pdf_result.extraction_method or "pdf_text_extraction_failed",
            page_count=pdf_result.page_count,
            pages_extracted=pdf_result.pages_extracted,
        )

    def _finalize_text_processing(
        self,
        material: UploadedMaterial,
        base_state: DocumentPipelineState,
        *,
        text: str,
        extraction_method: str,
        page_count: int,
        pages_extracted: int,
        warnings: list[str],
        events: list[DocumentPipelineEvent],
        user_id: str | None,
        requires_ocr: bool,
    ) -> DocumentPipelineState:
        document_id = material.metadata.document_id
        created_at = base_state.created_at
        section_payloads = self._build_sections(material, text, user_id=user_id)
        chunks = self._build_chunks(material, section_payloads, user_id=user_id)
        sections = [
            DocumentSection(
                section_id=str(item["section_id"]),
                document_id=material.metadata.document_id,
                user_id=user_id,
                title=str(item["title"]),
                level=int(item["level"]),
                order_index=int(item["order_index"]),
                start_chunk_index=int(item.get("start_chunk_index", 0)),
                end_chunk_index=int(item.get("end_chunk_index", 0)),
                metadata={"pipeline_version": PIPELINE_VERSION},
            )
            for item in section_payloads
        ]
        extraction = DocumentExtractionResult(
            document_id=document_id,
            user_id=user_id,
            source_type=material.metadata.source_type,
            text=text,
            text_length=len(text),
            page_count=page_count,
            extraction_method=extraction_method,
            extraction_status=DocumentIngestionStatus.EXTRACTED.value,
            warnings=warnings,
            errors=[],
            metadata={
                "filename": material.metadata.filename,
                "content_type": material.metadata.content_type,
                "pipeline_version": PIPELINE_VERSION,
                "pages_extracted": pages_extracted,
                "requires_ocr": requires_ocr,
            },
        )
        stages_completed = [
            DocumentIngestionStatus.UPLOADED.value,
            DocumentIngestionStatus.TYPE_DETECTED.value,
            DocumentIngestionStatus.EXTRACTION_STARTED.value,
            DocumentIngestionStatus.EXTRACTED.value,
            DocumentIngestionStatus.CHUNKED.value,
            DocumentIngestionStatus.SECTIONED.value,
            DocumentIngestionStatus.METADATA_READY.value,
        ]
        state = DocumentPipelineState(
            document_id=document_id,
            user_id=user_id,
            current_stage=DocumentIngestionStatus.METADATA_READY.value,
            stages_completed=stages_completed,
            extraction_status=DocumentIngestionStatus.EXTRACTED.value,
            chunking_status="completed",
            sectioning_status="completed",
            metadata_status="ready",
            error_count=0,
            last_error=None,
            created_at=created_at,
            updated_at=created_at,
            pipeline_version=PIPELINE_VERSION,
            text_length=len(text),
            chunk_count=len(chunks),
            section_count=len(sections),
        )
        events.extend(
            [
                self._event(
                    material=material,
                    stage=DocumentIngestionStatus.EXTRACTED.value,
                    status="ok",
                    message="Text extracted successfully.",
                    metadata={"text_length": len(text)},
                ),
                self._event(
                    material=material,
                    stage=DocumentIngestionStatus.CHUNKED.value,
                    status="ok",
                    message="Deterministic chunks created.",
                    metadata={"chunk_count": len(chunks)},
                ),
                self._event(
                    material=material,
                    stage=DocumentIngestionStatus.SECTIONED.value,
                    status="ok",
                    message="Sections detected.",
                    metadata={"section_count": len(sections)},
                ),
                self._event(
                    material=material,
                    stage=DocumentIngestionStatus.METADATA_READY.value,
                    status="ok",
                    message="Document metadata is ready for future processing stages.",
                ),
            ]
        )
        self.repository.save_document_extraction_result(extraction, user_id=user_id)
        self.repository.save_document_chunks(document_id, chunks, user_id=user_id)
        self.repository.save_document_sections(document_id, sections, user_id=user_id)
        self.repository.save_document_pipeline_state(state, user_id=user_id)
        self._save_material_update(
            material,
            user_id=user_id,
            status=DocumentIngestionStatus.METADATA_READY.value,
            extraction_status=DocumentIngestionStatus.EXTRACTED.value,
            metadata_updates={
                "pipeline_version": PIPELINE_VERSION,
                "text_length": len(text),
                "chunk_count": len(chunks),
                "section_count": len(sections),
                "page_count": page_count,
                "pages_extracted": pages_extracted,
                "requires_ocr": requires_ocr,
                "extraction_method": extraction_method,
                "processing_warnings": warnings,
            },
            error_message=None,
        )
        self._persist_events(events, user_id=user_id)
        return state

    def _finalize_pdf_pending(
        self,
        material: UploadedMaterial,
        base_state: DocumentPipelineState,
        *,
        events: list[DocumentPipelineEvent],
        user_id: str | None,
        extraction_method: str = "pending_pdf_extraction",
        page_count: int = 0,
        pages_extracted: int = 0,
        warnings: list[str] | None = None,
    ) -> DocumentPipelineState:
        extraction = DocumentExtractionResult(
            document_id=material.metadata.document_id,
            user_id=user_id,
            source_type=material.metadata.source_type,
            text=None,
            text_length=0,
            page_count=page_count,
            extraction_method=extraction_method,
            extraction_status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
            warnings=warnings or ["pdf_text_empty", "ocr_required"],
            errors=[],
            metadata={
                "filename": material.metadata.filename,
                "content_type": material.metadata.content_type,
                "pipeline_version": PIPELINE_VERSION,
                "pages_extracted": pages_extracted,
                "requires_ocr": True,
            },
        )
        state = base_state.model_copy(
            update={
                "current_stage": "extraction_pending",
                "stages_completed": [
                    *base_state.stages_completed,
                    "extraction_pending",
                ],
                "extraction_status": DocumentIngestionStatus.PENDING_EXTRACTION.value,
                "chunking_status": "not_started",
                "sectioning_status": "not_started",
                "metadata_status": "pending",
                "updated_at": base_state.created_at,
            }
        )
        events.append(
            self._event(
                material=material,
                stage=DocumentIngestionStatus.PENDING_EXTRACTION.value,
                status="pending",
                message="PDF registered for future extraction.",
            )
        )
        self.repository.save_document_extraction_result(extraction, user_id=user_id)
        self.repository.save_document_chunks(material.metadata.document_id, [], user_id=user_id)
        self.repository.save_document_sections(material.metadata.document_id, [], user_id=user_id)
        self.repository.save_document_pipeline_state(state, user_id=user_id)
        self._save_material_update(
            material,
            user_id=user_id,
            status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
            extraction_status=DocumentIngestionStatus.PENDING_EXTRACTION.value,
            metadata_updates={
                "pipeline_version": PIPELINE_VERSION,
                "page_count": page_count,
                "pages_extracted": pages_extracted,
                "requires_ocr": True,
                "extraction_method": extraction_method,
                "processing_warnings": warnings or ["pdf_text_empty", "ocr_required"],
            },
            error_message=None,
        )
        self._persist_events(events, user_id=user_id)
        return state

    def _finalize_failure(
        self,
        material: UploadedMaterial,
        base_state: DocumentPipelineState,
        *,
        stage: str,
        error: DocumentProcessingError,
        warnings: list[str],
        events: list[DocumentPipelineEvent],
        user_id: str | None,
        extraction_method: str = "none",
        page_count: int = 0,
        pages_extracted: int = 0,
    ) -> DocumentPipelineState:
        state = base_state.model_copy(
            update={
                "current_stage": stage,
                "stages_completed": [*base_state.stages_completed, stage],
                "extraction_status": stage,
                "chunking_status": "not_started",
                "sectioning_status": "not_started",
                "metadata_status": "error",
                "error_count": 1,
                "last_error": error,
                "updated_at": base_state.created_at,
            }
        )
        extraction = DocumentExtractionResult(
            document_id=material.metadata.document_id,
            user_id=user_id,
            source_type=material.metadata.source_type,
            text=None,
            text_length=0,
            page_count=page_count,
            extraction_method=extraction_method,
            extraction_status=stage,
            warnings=warnings,
            errors=[error],
            metadata={
                "filename": material.metadata.filename,
                "content_type": material.metadata.content_type,
                "pipeline_version": PIPELINE_VERSION,
                "pages_extracted": pages_extracted,
                "requires_ocr": False,
            },
        )
        events.append(
            self._event(
                material=material,
                stage=stage,
                status="error" if stage == DocumentIngestionStatus.FAILED.value else "unsupported",
                message=error.message,
                metadata={"error_code": error.code},
            )
        )
        self.repository.save_document_extraction_result(extraction, user_id=user_id)
        self.repository.save_document_chunks(material.metadata.document_id, [], user_id=user_id)
        self.repository.save_document_sections(material.metadata.document_id, [], user_id=user_id)
        self.repository.save_document_pipeline_state(state, user_id=user_id)
        self._save_material_update(
            material,
            user_id=user_id,
            status=stage,
            extraction_status=stage,
            metadata_updates={
                "pipeline_version": PIPELINE_VERSION,
                "page_count": page_count,
                "pages_extracted": pages_extracted,
                "requires_ocr": False,
                "extraction_method": extraction_method,
                "processing_warnings": warnings,
            },
            error_message=error.message,
        )
        self._persist_events(events, user_id=user_id)
        return state

    def _save_material_update(
        self,
        material: UploadedMaterial,
        *,
        user_id: str | None,
        status: str,
        extraction_status: str,
        metadata_updates: dict[str, object],
        error_message: str | None,
    ) -> None:
        updated = material.model_copy(deep=True)
        updated.metadata.status = status
        updated.metadata.extraction_status = extraction_status
        updated.metadata.updated_at = utc_now()
        updated.metadata.error_message = error_message
        updated.metadata.metadata.update(metadata_updates)
        self.repository.save_uploaded_material(updated, user_id=user_id or updated.metadata.user_id or "")

    def _persist_events(
        self,
        events: list[DocumentPipelineEvent],
        *,
        user_id: str | None,
    ) -> None:
        for event in events:
            self.repository.append_document_pipeline_event(event, user_id=user_id)

    def _build_sections(
        self,
        material: UploadedMaterial,
        text: str,
        *,
        user_id: str | None,
    ) -> list[dict[str, object]]:
        if material.metadata.filename.lower().endswith(".md"):
            sections = self._markdown_sections(text)
            if sections:
                return [
                    {
                        "section_id": f"{material.metadata.document_id}:section:{index}",
                        "title": title,
                        "level": level,
                        "order_index": index,
                        "text": section_text,
                        "user_id": user_id,
                    }
                    for index, (title, level, section_text) in enumerate(sections)
                ]
        return [
            {
                "section_id": f"{material.metadata.document_id}:section:0",
                "title": "Document",
                "level": 1,
                "order_index": 0,
                "text": text,
                "user_id": user_id,
            }
        ]

    def _build_chunks(
        self,
        material: UploadedMaterial,
        section_payloads: list[dict[str, object]],
        *,
        user_id: str | None,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for section_payload in section_payloads:
            section_id = str(section_payload["section_id"])
            text = str(section_payload.get("text") or "")
            for piece in self._split_text(text):
                chunk_index = len(chunks)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{material.metadata.document_id}:chunk:{chunk_index}",
                        document_id=material.metadata.document_id,
                        user_id=user_id,
                        chunk_index=chunk_index,
                        text=piece,
                        text_length=len(piece),
                        token_estimate=max(1, len(piece) // 4) if piece else 0,
                        section_id=section_id,
                        metadata={"pipeline_version": PIPELINE_VERSION},
                    )
                )
        sections_by_id = {str(item["section_id"]): item for item in section_payloads}
        for section_id, payload in sections_by_id.items():
            indexes = [chunk.chunk_index for chunk in chunks if chunk.section_id == section_id]
            payload["start_chunk_index"] = indexes[0] if indexes else 0
            payload["end_chunk_index"] = indexes[-1] if indexes else 0
        return chunks

    def _markdown_sections(self, text: str) -> list[tuple[str, int, str]]:
        sections: list[tuple[str, int, str]] = []
        current_title: str | None = None
        current_level = 1
        current_lines: list[str] = []
        for line in text.splitlines():
            match = re.match(r"^(#{1,3})\s+(.*\S)\s*$", line)
            if match:
                if current_title is not None:
                    sections.append((current_title, current_level, "\n".join(current_lines).strip()))
                current_title = match.group(2).strip()
                current_level = len(match.group(1))
                current_lines = []
                continue
            current_lines.append(line)
        if current_title is not None:
            sections.append((current_title, current_level, "\n".join(current_lines).strip()))
        return sections

    def _split_text(self, text: str) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            return []
        pieces: list[str] = []
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", cleaned) if item.strip()]
        for paragraph in paragraphs:
            if len(paragraph) <= self.max_chunk_size:
                pieces.append(paragraph)
                continue
            start = 0
            while start < len(paragraph):
                pieces.append(paragraph[start : start + self.max_chunk_size].strip())
                start += self.max_chunk_size
        return [piece for piece in pieces if piece]

    def _event(
        self,
        *,
        material: UploadedMaterial,
        stage: str,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> DocumentPipelineEvent:
        return DocumentPipelineEvent(
            event_id=f"{material.metadata.document_id}:{stage}:{status}",
            document_id=material.metadata.document_id,
            user_id=material.metadata.user_id,
            stage=stage,
            status=status,
            message=message,
            metadata=metadata or {},
        )

    def _resolve_storage_path(self, material: UploadedMaterial) -> Path | None:
        relative_path = material.metadata.storage_path
        if not relative_path:
            return None
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return None
        base_root = self.storage_root.parent.resolve()
        resolved = (base_root / candidate).resolve()
        try:
            resolved.relative_to(base_root)
        except ValueError:
            return None
        return resolved
