from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.config import get_studyflow_data_file, is_production
from app.domain.models import (
    DocumentChunk,
    DocumentExtractionResult,
    DocumentMetadata,
    DocumentPipelineState,
    DocumentSection,
    EditalExtractionResult,
    EditalIngestionState,
    EditalSectionCandidate,
    EditalSubtopicCandidate,
    EditalTopicCandidate,
    UploadedMaterial,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.user_service import LocalUserService


QA_REVIEW_USERNAME = "compose-qa-seed"
QA_REVIEW_DISPLAY_NAME = "Compose QA Seed"
QA_REVIEW_PASSWORD_ENV = "QA_REVIEW_PASSWORD"
QA_REVIEW_DEFAULT_PASSWORD = "local-qa-seed-12345"
QA_REVIEW_FIXTURE_TAG = "review-progress-browser-qa"
QA_REVIEW_EDITAL_DOCUMENT_ID = "8f5e6f21-0d1a-4d11-9f1d-a7c2a0000001"
QA_REVIEW_MATERIAL_IDS = [
    "8f5e6f21-0d1a-4d11-9f1d-a7c2a0000101",
    "8f5e6f21-0d1a-4d11-9f1d-a7c2a0000102",
    "8f5e6f21-0d1a-4d11-9f1d-a7c2a0000103",
]


@dataclass(frozen=True)
class ReviewProgressSeedResult:
    user_id: str
    username: str
    edital_document_id: str
    edital_id: str
    material_ids: list[str]
    block_ids: list[str]
    progress_event_ids: list[str]
    studied_materials_count: int
    review_basis: str

    def safe_payload(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "edital_document_id": self.edital_document_id,
            "edital_id": self.edital_id,
            "material_ids": self.material_ids,
            "block_ids": self.block_ids,
            "progress_event_ids": self.progress_event_ids,
            "studied_materials_count": self.studied_materials_count,
            "review_basis": self.review_basis,
            "source": "development_fixture",
        }


QA_TOPICS = [
    {
        "slug": "atos-administrativos",
        "title": "Atos administrativos",
        "message": "Conceitos, atributos e classificação dos atos administrativos.",
    },
    {
        "slug": "navegacao-costeira",
        "title": "Navegação costeira",
        "message": "Marcação, posição e leitura de referências costeiras.",
    },
    {
        "slug": "seguranca-operacional",
        "title": "Segurança operacional",
        "message": "Procedimentos de segurança, prevenção e resposta operacional.",
    },
]


def seed_review_progress_browser_qa(
    repository: JsonStudyRepository,
    *,
    username: str = QA_REVIEW_USERNAME,
    password: str | None = None,
    display_name: str = QA_REVIEW_DISPLAY_NAME,
) -> ReviewProgressSeedResult:
    """Seed a deterministic development-only fixture for studied-material review QA."""
    if is_production():
        raise RuntimeError("Review progress browser QA fixture is disabled in production.")

    password = password or os.getenv(QA_REVIEW_PASSWORD_ENV) or QA_REVIEW_DEFAULT_PASSWORD
    user = _ensure_user(repository, username=username, password=password, display_name=display_name)
    material_ids = list(QA_REVIEW_MATERIAL_IDS)
    block_ids = _expected_block_ids(material_ids)
    _cleanup_legacy_fixture_state(
        repository,
        user_id=user.user_id,
        keep_document_ids={_edital_document_id(), *material_ids},
        keep_block_ids=set(block_ids),
    )
    _seed_analyzed_edital(repository, user_id=user.user_id)
    material_ids = _seed_prepared_study_materials(repository, user_id=user.user_id)
    progress_event_ids = [
        str(
            repository.record_study_progress_event(
                user_id=user.user_id,
                event_type="block_marked_studied",
                target_type="block",
                target_id=block_id,
                idempotency_key=f"qa-fixture:block_marked_studied:{block_id}",
            )["event_id"]
        )
        for block_id in block_ids
    ]
    studied_materials_count = _derived_studied_materials_count(repository, user.user_id, material_ids, block_ids)
    review_basis = "studied_materials" if studied_materials_count >= 3 else "prepared_materials"

    return ReviewProgressSeedResult(
        user_id=user.user_id,
        username=user.username,
        edital_document_id=_edital_document_id(),
        edital_id=_edital_id(),
        material_ids=material_ids,
        block_ids=block_ids,
        progress_event_ids=progress_event_ids,
        studied_materials_count=studied_materials_count,
        review_basis=review_basis,
    )


def _ensure_user(repository: JsonStudyRepository, *, username: str, password: str, display_name: str):
    existing = repository.get_user_by_username(username)
    if existing is not None:
        return existing
    return LocalUserService(repository).register_user(
        username=username,
        password=password,
        display_name=display_name,
        email=f"{username}@example.com",
    )


def _edital_document_id() -> str:
    return QA_REVIEW_EDITAL_DOCUMENT_ID


def _edital_id() -> str:
    return f"edital:{_edital_document_id()}"


def _seed_analyzed_edital(repository: JsonStudyRepository, *, user_id: str) -> None:
    document_id = _edital_document_id()
    now = utc_now()
    repository.save_uploaded_material(
        UploadedMaterial(
            metadata=DocumentMetadata(
                document_id=document_id,
                user_id=user_id,
                filename="qa-review-progress-edital.md",
                original_filename="qa-review-progress-edital.md",
                content_type="text/markdown",
                size_bytes=256,
                storage_path="",
                status="metadata_ready",
                extraction_status="metadata_ready",
                material_type="edital",
                created_at=now,
                updated_at=now,
                metadata={
                    "material_type": "edital",
                    "extension": ".md",
                    "qa_fixture": QA_REVIEW_FIXTURE_TAG,
                },
            ),
            extracted_text=None,
        ),
        user_id=user_id,
    )
    repository.save_edital_ingestion_state(
        EditalIngestionState(
            edital_id=_edital_id(),
            document_id=document_id,
            user_id=user_id,
            current_stage="ready_for_review",
            status="ready_for_review",
            sections_detected=1,
            topics_detected=len(QA_TOPICS),
            subtopics_detected=len(QA_TOPICS),
            created_at=now,
            updated_at=now,
        ),
        user_id=user_id,
    )
    repository.save_edital_extraction_result(
        EditalExtractionResult(
            edital_id=_edital_id(),
            document_id=document_id,
            user_id=user_id,
            source_text_length=256,
            sections=[
                EditalSectionCandidate(
                    section_id="qa-section-conteudo-programatico",
                    title="Conteúdo programático",
                    normalized_title="conteudo programatico",
                    section_type="program_content",
                    order_index=0,
                    confidence=0.95,
                    reasoning="Synthetic QA fixture section.",
                )
            ],
            topics=[
                EditalTopicCandidate(
                    topic_id=f"qa-topic-{topic['slug']}",
                    title=topic["title"],
                    normalized_title=topic["title"].lower(),
                    parent_section_id="qa-section-conteudo-programatico",
                    order_index=index,
                    confidence=0.95,
                    reasoning="Synthetic QA fixture topic.",
                )
                for index, topic in enumerate(QA_TOPICS)
            ],
            subtopics=[
                EditalSubtopicCandidate(
                    subtopic_id=f"qa-subtopic-{topic['slug']}",
                    parent_topic_id=f"qa-topic-{topic['slug']}",
                    title=topic["title"],
                    normalized_title=topic["title"].lower(),
                    order_index=index,
                    confidence=0.95,
                    reasoning="Synthetic QA fixture subtopic.",
                )
                for index, topic in enumerate(QA_TOPICS)
            ],
            confidence_summary={"fixture": QA_REVIEW_FIXTURE_TAG, "review_state": "ready_for_review"},
            metadata={"qa_fixture": QA_REVIEW_FIXTURE_TAG},
        ),
        user_id=user_id,
    )


def _seed_prepared_study_materials(repository: JsonStudyRepository, *, user_id: str) -> list[str]:
    material_ids: list[str] = []
    now = utc_now()
    for index, topic in enumerate(QA_TOPICS):
        document_id = QA_REVIEW_MATERIAL_IDS[index]
        material_ids.append(document_id)
        title = str(topic["title"])
        text = f"# {title}\n\n{topic['message']}\n\nFixture de estudo para validação de revisão acumulada."
        section_id = f"qa-section-{topic['slug']}"
        chunk_id = f"qa-chunk-{topic['slug']}-0"
        repository.save_uploaded_material(
            UploadedMaterial(
                metadata=DocumentMetadata(
                    document_id=document_id,
                    user_id=user_id,
                    filename=f"qa-review-progress-{topic['slug']}.md",
                    original_filename=f"{title}.md",
                    content_type="text/markdown",
                    size_bytes=len(text.encode("utf-8")),
                    storage_path="",
                    status="metadata_ready",
                    extraction_status="metadata_ready",
                    material_type="study_material",
                    created_at=now,
                    updated_at=now,
                    metadata={
                        "material_type": "study_material",
                        "extension": ".md",
                        "qa_fixture": QA_REVIEW_FIXTURE_TAG,
                    },
                ),
                extracted_text=None,
            ),
            user_id=user_id,
        )
        repository.save_document_extraction_result(
            DocumentExtractionResult(
                document_id=document_id,
                user_id=user_id,
                text=text,
                text_length=len(text),
                page_count=1,
                extraction_method="qa_fixture_text",
                extraction_status="metadata_ready",
                metadata={"qa_fixture": QA_REVIEW_FIXTURE_TAG},
            ),
            user_id=user_id,
        )
        repository.save_document_sections(
            document_id,
            [
                DocumentSection(
                    section_id=section_id,
                    document_id=document_id,
                    user_id=user_id,
                    title=title,
                    level=1,
                    order_index=0,
                    start_chunk_index=0,
                    end_chunk_index=0,
                    metadata={"qa_fixture": QA_REVIEW_FIXTURE_TAG},
                )
            ],
            user_id=user_id,
        )
        repository.save_document_chunks(
            document_id,
            [
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    user_id=user_id,
                    chunk_index=0,
                    text=text,
                    text_length=len(text),
                    token_estimate=max(1, len(text.split())),
                    section_id=section_id,
                    metadata={"qa_fixture": QA_REVIEW_FIXTURE_TAG},
                )
            ],
            user_id=user_id,
        )
        repository.save_document_pipeline_state(
            DocumentPipelineState(
                document_id=document_id,
                user_id=user_id,
                current_stage="metadata_ready",
                stages_completed=["uploaded", "extracted", "chunked", "sectioned", "metadata_ready"],
                extraction_status="metadata_ready",
                chunking_status="chunked",
                sectioning_status="sectioned",
                metadata_status="ready",
                created_at=now,
                updated_at=now,
                text_length=len(text),
                chunk_count=1,
                section_count=1,
            ),
            user_id=user_id,
        )
    return material_ids


def _expected_block_ids(material_ids: list[str]) -> list[str]:
    return [
        f"study-block:qa-subtopic-{topic['slug']}:{document_id}:0"
        for topic, document_id in zip(QA_TOPICS, material_ids, strict=True)
    ]


def _cleanup_legacy_fixture_state(
    repository: JsonStudyRepository,
    *,
    user_id: str,
    keep_document_ids: set[str],
    keep_block_ids: set[str],
) -> None:
    """Remove older versions of this fixture while leaving unrelated QA data untouched."""
    payload = repository._read()
    user_state = repository._ensure_user_state(payload, user_id)

    legacy_document_ids: set[str] = set()
    materials = []
    for item in user_state.get("materials", []):
        if not isinstance(item, dict):
            materials.append(item)
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            materials.append(item)
            continue
        document_id = str(metadata.get("document_id", ""))
        custom_metadata = metadata.get("metadata")
        is_fixture = (
            custom_metadata.get("qa_fixture") == QA_REVIEW_FIXTURE_TAG
            if isinstance(custom_metadata, dict)
            else False
        )
        if is_fixture and document_id not in keep_document_ids:
            legacy_document_ids.add(document_id)
            continue
        materials.append(item)
    user_state["materials"] = materials

    pipeline = repository._normalize_document_pipeline_payload(user_state.get("document_pipeline"))
    for key in ("states", "extraction_results", "chunks", "sections", "events"):
        container = pipeline.get(key)
        if isinstance(container, dict):
            for document_id in legacy_document_ids:
                container.pop(document_id, None)
    user_state["document_pipeline"] = pipeline

    edital = repository._normalize_edital_ingestion_payload(user_state.get("edital_ingestion"))
    for key in ("states", "results", "events"):
        container = edital.get(key)
        if not isinstance(container, dict):
            continue
        for entry_key, value in list(container.items()):
            if entry_key == _edital_id():
                continue
            document_id = value.get("document_id") if isinstance(value, dict) else None
            metadata = value.get("metadata") if isinstance(value, dict) else None
            is_fixture = isinstance(metadata, dict) and metadata.get("qa_fixture") == QA_REVIEW_FIXTURE_TAG
            if document_id in legacy_document_ids or is_fixture:
                container.pop(entry_key, None)
    user_state["edital_ingestion"] = edital

    progress_events = repository._normalize_study_progress_events_payload(user_state.get("study_progress_events"))
    events = progress_events.get("events")
    idempotency = progress_events.get("idempotency")
    removed_event_ids: set[str] = set()
    if isinstance(events, dict):
        for event_id, event in list(events.items()):
            if not isinstance(event, dict):
                continue
            key = str(event.get("idempotency_key", ""))
            target_id = str(event.get("target_id", ""))
            is_fixture_event = key.startswith("qa-fixture:block_marked_studied:")
            if is_fixture_event and target_id not in keep_block_ids:
                removed_event_ids.add(str(event_id))
                events.pop(event_id, None)
    if isinstance(idempotency, dict):
        for key, event_id in list(idempotency.items()):
            is_fixture_key = str(key).startswith("qa-fixture:block_marked_studied:")
            target_id = str(key).removeprefix("qa-fixture:block_marked_studied:")
            if is_fixture_key and (event_id in removed_event_ids or target_id not in keep_block_ids):
                idempotency.pop(key, None)
    user_state["study_progress_events"] = progress_events

    repository._write(payload)


def _derived_studied_materials_count(
    repository: JsonStudyRepository,
    user_id: str,
    material_ids: list[str],
    block_ids: list[str],
) -> int:
    studied_blocks = {
        str(event.get("target_id"))
        for event in repository.list_study_progress_events(user_id=user_id)
        if event.get("event_type") == "block_marked_studied" and event.get("target_type") == "block"
    }
    return sum(1 for _material_id, block_id in zip(material_ids, block_ids, strict=True) if block_id in studied_blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the development-only review progress browser QA fixture.")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=get_studyflow_data_file(),
        help="Path to the StudyFlow JSON data file. Defaults to STUDYFLOW_DATA_FILE.",
    )
    parser.add_argument("--username", default=QA_REVIEW_USERNAME)
    parser.add_argument("--display-name", default=QA_REVIEW_DISPLAY_NAME)
    args = parser.parse_args(argv)

    repository = JsonStudyRepository(args.data_file)
    result = seed_review_progress_browser_qa(
        repository,
        username=args.username,
        display_name=args.display_name,
    )
    print(json.dumps(result.safe_payload(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
