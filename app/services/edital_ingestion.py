from __future__ import annotations

import re
import unicodedata

from app.domain.models import (
    DocumentChunk,
    DocumentExtractionResult,
    DocumentProcessingError,
    DocumentSection,
    EditalBibliographyCandidate,
    EditalExclusionCandidate,
    EditalExtractionResult,
    EditalExtractionWarning,
    EditalIngestionEvent,
    EditalIngestionState,
    EditalSectionCandidate,
    EditalSubtopicCandidate,
    EditalTopicCandidate,
    EditalWeightHint,
    UploadedMaterial,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository


EDITAL_INGESTION_VERSION = "edital-ingestion-v1"
FINAL_EDITAL_STATUSES = {"ready_for_review", "insufficient_text", "failed"}
MIN_EDITAL_TEXT_LENGTH = 20


class EditalIngestionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def ingest_document(
        self,
        document_id: str,
        *,
        user_id: str | None,
    ) -> EditalIngestionState | None:
        material = self.repository.get_uploaded_material(document_id, user_id=user_id)
        if material is None:
            return None

        existing_state = self.repository.get_edital_ingestion_state(document_id, user_id=user_id)
        if existing_state is not None and existing_state.status in FINAL_EDITAL_STATUSES:
            return existing_state

        extraction = self.repository.get_document_extraction_result(document_id, user_id=user_id)
        chunks = self.repository.list_document_chunks(document_id, user_id=user_id)
        sections = self.repository.list_document_sections(document_id, user_id=user_id)
        return self._ingest_from_pipeline_artifacts(
            material,
            extraction=extraction,
            chunks=chunks,
            sections=sections,
            user_id=user_id,
        )

    def _ingest_from_pipeline_artifacts(
        self,
        material: UploadedMaterial,
        *,
        extraction: DocumentExtractionResult | None,
        chunks: list[DocumentChunk],
        sections: list[DocumentSection],
        user_id: str | None,
    ) -> EditalIngestionState:
        document_id = material.metadata.document_id
        edital_id = f"edital:{document_id}"
        created_at = utc_now()
        normalized_source_text = " ".join((extraction.text or "").split()) if extraction is not None else ""

        if extraction is None or len(normalized_source_text) < MIN_EDITAL_TEXT_LENGTH:
            warning_codes = ["insufficient_text_for_edital_ingestion"]
            if extraction is not None and (
                extraction.metadata.get("requires_ocr") is True or "ocr_required" in extraction.warnings
            ):
                warning_codes = ["ocr_required_before_edital_ingestion", "insufficient_text_for_edital_ingestion"]
            result = EditalExtractionResult(
                edital_id=edital_id,
                document_id=document_id,
                user_id=user_id,
                source_text_length=0,
                sections=[],
                topics=[],
                subtopics=[],
                bibliography=[],
                exclusions=[],
                weight_hints=[],
                warnings=[
                    EditalExtractionWarning(code=code, message=code.replace("_", " "))
                    for code in warning_codes
                ],
                confidence_summary={"review_required": True, "candidate_only": True},
                metadata={"document_status": material.metadata.status},
            )
            state = EditalIngestionState(
                edital_id=edital_id,
                document_id=document_id,
                user_id=user_id,
                current_stage="insufficient_text",
                status="insufficient_text",
                warnings=warning_codes,
                created_at=created_at,
                updated_at=created_at,
                ingestion_version=EDITAL_INGESTION_VERSION,
            )
            self.repository.save_edital_extraction_result(result, user_id=user_id)
            self.repository.save_edital_ingestion_state(state, user_id=user_id)
            self.repository.append_edital_ingestion_event(
                self._event(
                    edital_id=edital_id,
                    document_id=document_id,
                    user_id=user_id,
                    stage="insufficient_text",
                    status="warning",
                    message="Insufficient text for edital ingestion.",
                ),
                user_id=user_id,
            )
            return state

        section_candidates = self._section_candidates(sections, chunks, extraction.text)
        topic_candidates, subtopic_candidates = self._topic_candidates(section_candidates)
        bibliography_candidates = self._bibliography_candidates(section_candidates)
        exclusion_candidates = self._exclusion_candidates(section_candidates)
        weight_hints = self._weight_hints(section_candidates)
        warnings = self._warnings_for_candidates(section_candidates, topic_candidates)

        result = EditalExtractionResult(
            edital_id=edital_id,
            document_id=document_id,
            user_id=user_id,
            source_text_length=len(extraction.text),
            sections=section_candidates,
            topics=topic_candidates,
            subtopics=subtopic_candidates,
            bibliography=bibliography_candidates,
            exclusions=exclusion_candidates,
            weight_hints=weight_hints,
            warnings=warnings,
            confidence_summary={
                "review_required": True,
                "candidate_only": True,
                "sections_detected": len(section_candidates),
                "topics_detected": len(topic_candidates),
                "subtopics_detected": len(subtopic_candidates),
            },
            extraction_method="heuristic_edital_ingestion",
            ingestion_version=EDITAL_INGESTION_VERSION,
            metadata={"source_chunk_count": len(chunks), "source_section_count": len(sections)},
        )
        state = EditalIngestionState(
            edital_id=edital_id,
            document_id=document_id,
            user_id=user_id,
            current_stage="ready_for_review",
            status="ready_for_review",
            sections_detected=len(section_candidates),
            topics_detected=len(topic_candidates),
            subtopics_detected=len(subtopic_candidates),
            bibliography_items_detected=len(bibliography_candidates),
            exclusions_detected=len(exclusion_candidates),
            weight_hints_detected=len(weight_hints),
            warnings=[item.code for item in warnings],
            errors=[],
            created_at=created_at,
            updated_at=created_at,
            ingestion_version=EDITAL_INGESTION_VERSION,
        )
        self.repository.save_edital_extraction_result(result, user_id=user_id)
        self.repository.save_edital_ingestion_state(state, user_id=user_id)
        self.repository.append_edital_ingestion_event(
            self._event(
                edital_id=edital_id,
                document_id=document_id,
                user_id=user_id,
                stage="ready_for_review",
                status="ok",
                message="Edital candidate extraction completed.",
            ),
            user_id=user_id,
        )
        return state

    def _section_candidates(
        self,
        sections: list[DocumentSection],
        chunks: list[DocumentChunk],
        fallback_text: str,
    ) -> list[EditalSectionCandidate]:
        chunk_map: dict[str | None, list[DocumentChunk]] = {}
        for chunk in chunks:
            chunk_map.setdefault(chunk.section_id, []).append(chunk)
        if not sections:
            sections = [
                DocumentSection(
                    section_id="document:section:0",
                    document_id="",
                    title="Document",
                    level=1,
                    order_index=0,
                    start_chunk_index=0,
                    end_chunk_index=0,
                )
            ]
        candidates: list[EditalSectionCandidate] = []
        for index, section in enumerate(sorted(sections, key=lambda item: item.order_index)):
            section_chunks = sorted(chunk_map.get(section.section_id, []), key=lambda item: item.chunk_index)
            text = "\n".join(chunk.text for chunk in section_chunks).strip() or fallback_text.strip()
            normalized_title = self._normalize_text(section.title)
            section_type, confidence, reasoning = self._classify_section(section.title)
            candidates.append(
                EditalSectionCandidate(
                    section_id=section.section_id,
                    title=section.title,
                    normalized_title=normalized_title,
                    section_type=section_type,
                    order_index=index,
                    source_chunk_ids=[chunk.chunk_id for chunk in section_chunks],
                    text_excerpt=self._excerpt(text),
                    confidence=confidence,
                    reasoning=reasoning,
                    metadata={"text": text},
                )
            )
        return candidates

    def _classify_section(self, title: str) -> tuple[str, float, str]:
        normalized = self._normalize_text(title)
        keyword_map = {
            "content_program": ["conteudo programatico", "programa", "conhecimentos", "disciplinas", "materias"],
            "bibliography": ["bibliografia", "referencias"],
            "exclusions": ["exclusoes", "nao sera cobrado", "nao serao objeto", "exclui"],
            "exam_structure": ["estrutura da prova", "distribuicao", "prova objetiva"],
            "evaluation_criteria": ["avaliacao", "criterios"],
            "general_rules": ["regras gerais", "disposicoes gerais"],
        }
        for section_type, keywords in keyword_map.items():
            if any(keyword in normalized for keyword in keywords):
                return section_type, 0.95, f"section title matched edital keyword for {section_type}"
        if re.match(r"^\d+[\.\)]", title.strip()):
            return "content_program", 0.6, "numbered heading suggests content program section"
        return "unknown", 0.35, "no strong edital section keyword detected"

    def _topic_candidates(
        self,
        sections: list[EditalSectionCandidate],
    ) -> tuple[list[EditalTopicCandidate], list[EditalSubtopicCandidate]]:
        topics: list[EditalTopicCandidate] = []
        subtopics: list[EditalSubtopicCandidate] = []
        topic_order = 0
        subtopic_order = 0
        for section in sections:
            if section.section_type != "content_program":
                continue
            section_text = str(section.metadata.get("text") or "")
            for raw_line in self._meaningful_lines(section_text):
                topic_match = re.match(r"^(?:\d+[\.\)]\s+|[-*]\s+)(.+)$", raw_line)
                colon_match = re.match(r"^([^:]{3,120}):\s+(.+)$", raw_line)
                candidate_text = None
                trailing_text = None
                reasoning = ""
                confidence = 0.0
                if topic_match:
                    candidate_text = topic_match.group(1).strip()
                    reasoning = "numbered or bulleted line inside content section"
                    confidence = 0.88
                elif colon_match:
                    candidate_text = colon_match.group(1).strip()
                    trailing_text = colon_match.group(2).strip()
                    reasoning = "colon-separated topic line inside content section"
                    confidence = 0.82
                if candidate_text is None:
                    continue
                topic_title = candidate_text
                if ":" in topic_title:
                    topic_title = topic_title.split(":", 1)[0].strip()
                if trailing_text is None and ":" in candidate_text:
                    topic_title, trailing_text = [part.strip() for part in candidate_text.split(":", 1)]
                topic_id = f"{section.section_id}:topic:{topic_order}"
                topics.append(
                    EditalTopicCandidate(
                        topic_id=topic_id,
                        title=topic_title,
                        normalized_title=self._normalize_text(topic_title),
                        subject_hint=section.title,
                        parent_section_id=section.section_id,
                        order_index=topic_order,
                        source_chunk_ids=section.source_chunk_ids,
                        source_excerpt=self._excerpt(raw_line),
                        confidence=confidence,
                        reasoning=reasoning,
                    )
                )
                if trailing_text:
                    for piece in self._split_inline_items(trailing_text):
                        subtopics.append(
                            EditalSubtopicCandidate(
                                subtopic_id=f"{topic_id}:subtopic:{subtopic_order}",
                                parent_topic_id=topic_id,
                                title=piece,
                                normalized_title=self._normalize_text(piece),
                                order_index=subtopic_order,
                                source_chunk_ids=section.source_chunk_ids,
                                source_excerpt=self._excerpt(raw_line),
                                confidence=0.76,
                                reasoning="inline list after colon in topic candidate",
                            )
                        )
                        subtopic_order += 1
                topic_order += 1
        return topics, subtopics

    def _bibliography_candidates(
        self,
        sections: list[EditalSectionCandidate],
    ) -> list[EditalBibliographyCandidate]:
        candidates: list[EditalBibliographyCandidate] = []
        order_index = 0
        for section in sections:
            if section.section_type != "bibliography":
                continue
            for line in self._meaningful_lines(str(section.metadata.get("text") or "")):
                if len(line) < 8:
                    continue
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                edition_match = re.search(r"\b(\d+\.\s*ed\.)\b", line, flags=re.IGNORECASE)
                parts = [part.strip() for part in line.split(".") if part.strip()]
                authors = [parts[0]] if parts else []
                title = parts[1] if len(parts) > 1 else line[:80]
                confidence = 0.82 if year_match else 0.58
                candidates.append(
                    EditalBibliographyCandidate(
                        bibliography_id=f"{section.section_id}:bibliography:{order_index}",
                        title=title,
                        authors=authors,
                        publisher=parts[2] if len(parts) > 2 else None,
                        edition=edition_match.group(1) if edition_match else None,
                        year=year_match.group(0) if year_match else None,
                        raw_reference=line,
                        source_section_id=section.section_id,
                        confidence=confidence,
                        reasoning="reference-like line inside bibliography section",
                    )
                )
                order_index += 1
        return candidates

    def _exclusion_candidates(
        self,
        sections: list[EditalSectionCandidate],
    ) -> list[EditalExclusionCandidate]:
        patterns = ["nao sera cobrado", "nao serao objeto", "exclui", "ficam excluidos", "nao integra o programa"]
        candidates: list[EditalExclusionCandidate] = []
        order_index = 0
        for section in sections:
            if section.section_type not in {"exclusions", "content_program", "general_rules"}:
                continue
            for line in self._meaningful_lines(str(section.metadata.get("text") or "")):
                normalized = self._normalize_text(line)
                if any(pattern in normalized for pattern in patterns):
                    candidates.append(
                        EditalExclusionCandidate(
                            exclusion_id=f"{section.section_id}:exclusion:{order_index}",
                            text=line,
                            normalized_text=normalized,
                            source_section_id=section.section_id,
                            source_excerpt=self._excerpt(line),
                            confidence=0.9 if section.section_type == "exclusions" else 0.7,
                            reasoning="explicit exclusion phrase detected",
                        )
                    )
                    order_index += 1
        return candidates

    def _weight_hints(
        self,
        sections: list[EditalSectionCandidate],
    ) -> list[EditalWeightHint]:
        hints: list[EditalWeightHint] = []
        order_index = 0
        for section in sections:
            if section.section_type not in {"exam_structure", "evaluation_criteria"}:
                continue
            for line in self._meaningful_lines(str(section.metadata.get("text") or "")):
                for match in re.finditer(r"(\d+)\s+quest(?:ao|oes)", line, flags=re.IGNORECASE):
                    hints.append(self._build_weight_hint(section, order_index, "question_count", float(match.group(1)), line))
                    order_index += 1
                for match in re.finditer(r"(\d+)\s+pontos?", line, flags=re.IGNORECASE):
                    hints.append(self._build_weight_hint(section, order_index, "explicit_points", float(match.group(1)), line))
                    order_index += 1
                for match in re.finditer(r"(\d+)\s*%", line):
                    hints.append(self._build_weight_hint(section, order_index, "percentage", float(match.group(1)), line))
                    order_index += 1
        return hints

    def _build_weight_hint(
        self,
        section: EditalSectionCandidate,
        order_index: int,
        weight_type: str,
        value: float,
        raw_text: str,
    ) -> EditalWeightHint:
        return EditalWeightHint(
            weight_id=f"{section.section_id}:weight:{order_index}",
            target_type="section",
            target_id=section.section_id,
            target_title=section.title,
            weight_type=weight_type,
            value=value,
            raw_text=self._excerpt(raw_text, limit=200),
            confidence=0.84,
            reasoning="explicit numeric hint detected in exam structure section",
        )

    def _warnings_for_candidates(
        self,
        sections: list[EditalSectionCandidate],
        topics: list[EditalTopicCandidate],
    ) -> list[EditalExtractionWarning]:
        warnings: list[EditalExtractionWarning] = []
        if not any(section.section_type == "content_program" for section in sections):
            warnings.append(
                EditalExtractionWarning(
                    code="content_program_section_not_found",
                    message="No strong content program section was detected.",
                    severity="warning",
                )
            )
        if not topics:
            warnings.append(
                EditalExtractionWarning(
                    code="no_topic_candidates_detected",
                    message="No topic candidates were extracted from the current source.",
                    severity="warning",
                )
            )
        return warnings

    def _event(
        self,
        *,
        edital_id: str,
        document_id: str,
        user_id: str | None,
        stage: str,
        status: str,
        message: str,
    ) -> EditalIngestionEvent:
        return EditalIngestionEvent(
            event_id=f"{edital_id}:{stage}:{status}",
            edital_id=edital_id,
            document_id=document_id,
            user_id=user_id,
            stage=stage,
            status=status,
            message=message,
        )

    def _meaningful_lines(self, text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _split_inline_items(self, text: str) -> list[str]:
        parts = [item.strip(" -\t.") for item in re.split(r"[;,]", text) if item.strip(" -\t.")]
        return [item for item in parts if len(item) >= 2]

    def _excerpt(self, text: str, *, limit: int = 160) -> str:
        clean = " ".join(text.split())
        return clean[:limit]

    def _normalize_text(self, text: str) -> str:
        lowered = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        lowered = lowered.lower()
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip(" .:-")
