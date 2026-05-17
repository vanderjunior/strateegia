from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from app.domain.models import (
    AlignmentEvidence,
    AlignmentWarning,
    BibliographyAlignmentResult,
    BibliographyAlignmentState,
    BibliographyItemAlignment,
    CoverageGap,
    CoverageRedundancy,
    DocumentCoverageCandidate,
    EditalExtractionResult,
    EditalSubtopicCandidate,
    TopicCoverageCandidate,
    SectionCoverageCandidate,
    UploadedMaterial,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository


ALIGNMENT_VERSION = "bibliography-alignment-v1"
FINAL_ALIGNMENT_STATUSES = {"ready_for_review", "insufficient_materials", "failed"}
STOPWORDS = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "a",
    "o",
    "as",
    "os",
    "para",
    "com",
    "no",
    "na",
    "em",
    "por",
    "um",
    "uma",
    "the",
}


@dataclass
class _MaterialContext:
    material: UploadedMaterial
    extraction: object | None
    chunks: list[object]
    sections: list[object]
    searchable_text: str
    processed_text: str
    title_hint: str
    filename_tokens: set[str]
    text_tokens: set[str]
    processed_text_tokens: set[str]
    ocr_required: bool
    has_processed_text: bool


class BibliographyAlignmentService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def align_edital(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> BibliographyAlignmentState | None:
        edital = self.repository.get_edital_extraction_by_id(edital_id, user_id=user_id)
        if edital is None:
            return None

        existing = self.repository.get_bibliography_alignment_state(edital_id, user_id=user_id)
        if existing is not None and existing.status in FINAL_ALIGNMENT_STATUSES:
            return existing

        return self._align(edital, user_id=user_id)

    def _align(
        self,
        edital: EditalExtractionResult,
        *,
        user_id: str | None,
    ) -> BibliographyAlignmentState:
        created_at = utc_now()
        alignment_id = f"alignment:{edital.edital_id}"
        materials = [
            item
            for item in self.repository.list_uploaded_materials(user_id=user_id or "")
            if item.metadata.document_id != edital.document_id
        ] if user_id is not None else []

        if not materials:
            result = BibliographyAlignmentResult(
                alignment_id=alignment_id,
                edital_id=edital.edital_id,
                user_id=user_id,
                warnings=[
                    AlignmentWarning(
                        code="no_candidate_materials_available",
                        message="No processed user materials are available for alignment.",
                        severity="warning",
                    )
                ],
                confidence_summary={"review_required": True, "candidate_only": True},
                alignment_version=ALIGNMENT_VERSION,
                metadata={"materials_considered": 0},
            )
            state = BibliographyAlignmentState(
                alignment_id=alignment_id,
                edital_id=edital.edital_id,
                user_id=user_id,
                current_stage="insufficient_materials",
                status="insufficient_materials",
                bibliography_items_total=len(edital.bibliography),
                topics_total=len(edital.topics),
                warnings=["no_candidate_materials_available"],
                created_at=created_at,
                updated_at=created_at,
                alignment_version=ALIGNMENT_VERSION,
            )
            self.repository.save_bibliography_alignment_result(result, user_id=user_id)
            self.repository.save_bibliography_alignment_state(state, user_id=user_id)
            return state

        contexts = [self._material_context(item, user_id=user_id) for item in materials]
        bibliography_alignments, bibliography_gaps, bibliography_redundancies = self._align_bibliography(
            edital,
            contexts,
        )
        topic_coverage, section_coverage, topic_gaps, topic_redundancies = self._align_topics(
            edital,
            contexts,
        )
        document_coverage = self._document_coverage(contexts, bibliography_alignments, topic_coverage, section_coverage)

        warnings = list(self._warnings_from_contexts(contexts, topic_coverage))
        gaps = bibliography_gaps + topic_gaps
        redundancies = bibliography_redundancies + topic_redundancies

        result = BibliographyAlignmentResult(
            alignment_id=alignment_id,
            edital_id=edital.edital_id,
            user_id=user_id,
            bibliography_alignments=bibliography_alignments,
            topic_coverage=topic_coverage,
            document_coverage=document_coverage,
            section_coverage=section_coverage,
            gaps=gaps,
            redundancies=redundancies,
            warnings=warnings,
            confidence_summary={
                "review_required": True,
                "candidate_only": True,
                "materials_considered": len(contexts),
                "bibliography_items_matched": sum(1 for item in bibliography_alignments if item.match_state in {"matched", "partially_matched"}),
                "topics_with_coverage": sum(1 for item in topic_coverage if item.coverage_state in {"covered", "partially_covered", "weakly_covered"}),
            },
            alignment_method="heuristic_bibliography_alignment",
            alignment_version=ALIGNMENT_VERSION,
            metadata={"materials_considered": len(contexts)},
        )
        state = BibliographyAlignmentState(
            alignment_id=alignment_id,
            edital_id=edital.edital_id,
            user_id=user_id,
            current_stage="ready_for_review",
            status="ready_for_review",
            bibliography_items_total=len(edital.bibliography),
            bibliography_items_matched=sum(1 for item in bibliography_alignments if item.match_state in {"matched", "partially_matched"}),
            topics_total=len(edital.topics),
            topics_with_coverage=sum(1 for item in topic_coverage if item.coverage_state in {"covered", "partially_covered", "weakly_covered"}),
            gaps_detected=len(gaps),
            redundancies_detected=len(redundancies),
            warnings=[item.code for item in warnings],
            errors=[],
            created_at=created_at,
            updated_at=created_at,
            alignment_version=ALIGNMENT_VERSION,
        )
        self.repository.save_bibliography_alignment_result(result, user_id=user_id)
        self.repository.save_bibliography_alignment_state(state, user_id=user_id)
        return state

    def _material_context(self, material: UploadedMaterial, *, user_id: str | None) -> _MaterialContext:
        extraction = self.repository.get_document_extraction_result(material.metadata.document_id, user_id=user_id)
        chunks = self.repository.list_document_chunks(material.metadata.document_id, user_id=user_id)
        sections = self.repository.list_document_sections(material.metadata.document_id, user_id=user_id)
        title_hint = sections[0].title if sections else self._filename_stem(material.metadata.filename)
        text_parts = [self._filename_stem(material.metadata.filename), title_hint]
        processed_parts = [section.title for section in sections[:5] if section.title]
        if extraction is not None and extraction.text:
            text_parts.append(extraction.text[:1200])
            processed_parts.append(extraction.text[:1200])
        searchable_text = " ".join(part for part in text_parts if part)
        processed_text = " ".join(part for part in processed_parts if part)
        requires_ocr = False
        if extraction is not None:
            requires_ocr = bool(extraction.metadata.get("requires_ocr")) or "ocr_required" in extraction.warnings
        return _MaterialContext(
            material=material,
            extraction=extraction,
            chunks=chunks,
            sections=sections,
            searchable_text=searchable_text,
            processed_text=processed_text,
            title_hint=title_hint,
            filename_tokens=self._tokens(material.metadata.filename),
            text_tokens=self._tokens(searchable_text),
            processed_text_tokens=self._tokens(processed_text),
            ocr_required=requires_ocr,
            has_processed_text=bool(processed_text.strip() or chunks),
        )

    def _align_bibliography(
        self,
        edital: EditalExtractionResult,
        contexts: list[_MaterialContext],
    ) -> tuple[list[BibliographyItemAlignment], list[CoverageGap], list[CoverageRedundancy]]:
        alignments: list[BibliographyItemAlignment] = []
        gaps: list[CoverageGap] = []
        redundancies: list[CoverageRedundancy] = []
        for item in edital.bibliography:
            ref_tokens = self._tokens(" ".join([item.title, " ".join(item.authors), item.raw_reference, item.year or ""]))
            candidates: list[tuple[float, _MaterialContext, list[str]]] = []
            for context in contexts:
                matched_terms = sorted(ref_tokens & context.text_tokens)
                if not matched_terms:
                    continue
                score = self._overlap_score(ref_tokens, context.text_tokens)
                if item.year and item.year in context.searchable_text:
                    score += 0.1
                if self._normalize_text(item.title) and self._normalize_text(item.title) in self._normalize_text(context.searchable_text):
                    score += 0.2
                score = min(score, 1.0)
                candidates.append((score, context, matched_terms))
            candidates.sort(key=lambda entry: (-entry[0], entry[1].material.metadata.document_id))
            strong = [entry for entry in candidates if entry[0] >= 0.65]
            partial = [entry for entry in candidates if entry[0] >= 0.3]
            if not candidates:
                alignments.append(
                    BibliographyItemAlignment(
                        bibliography_id=item.bibliography_id,
                        raw_reference=item.raw_reference,
                        match_state="unmatched",
                        confidence=0.0,
                        reasoning="no meaningful overlap found between bibliography candidate and available materials",
                        evidence=[],
                    )
                )
                gaps.append(
                    CoverageGap(
                        gap_id=f"{item.bibliography_id}:gap",
                        gap_type="missing_bibliography_material",
                        target_id=item.bibliography_id,
                        target_title=item.title or item.raw_reference[:80],
                        reason="No uploaded material matched this bibliography candidate.",
                        severity="high",
                    )
                )
                continue
            state = "partially_matched"
            selected = partial[:3]
            confidence = partial[0][0] if partial else 0.0
            reasoning = "partial bibliography overlap detected in candidate materials"
            if len(strong) == 1:
                state = "matched"
                selected = strong[:1]
                confidence = strong[0][0]
                reasoning = "strong title/author/reference overlap matched a single material"
            elif len(strong) > 1:
                state = "ambiguous"
                selected = strong[:3]
                confidence = strong[0][0]
                reasoning = "multiple materials strongly overlap this bibliography candidate"
                redundancies.append(
                    CoverageRedundancy(
                        redundancy_id=f"{item.bibliography_id}:redundancy",
                        redundancy_type="duplicate_bibliography_match",
                        target_id=item.bibliography_id,
                        target_title=item.title or item.raw_reference[:80],
                        overlapping_document_ids=[entry[1].material.metadata.document_id for entry in strong[:3]],
                        reason="Multiple materials appear to match the same bibliography candidate.",
                        severity="medium",
                        evidence=[
                            AlignmentEvidence(
                                source_type="document",
                                source_id=entry[1].material.metadata.document_id,
                                excerpt=self._excerpt(entry[1].searchable_text),
                                matched_terms=entry[2][:6],
                                reasoning="strong overlap with bibliography candidate",
                                confidence=entry[0],
                            )
                            for entry in strong[:2]
                        ],
                    )
                )
                gaps.append(
                    CoverageGap(
                        gap_id=f"{item.bibliography_id}:ambiguous-gap",
                        gap_type="ambiguous_reference",
                        target_id=item.bibliography_id,
                        target_title=item.title or item.raw_reference[:80],
                        reason="Multiple materials may correspond to the same bibliography candidate.",
                        severity="medium",
                    )
                )
            evidence = [
                AlignmentEvidence(
                    source_type="document",
                    source_id=entry[1].material.metadata.document_id,
                    excerpt=self._excerpt(entry[1].searchable_text),
                    matched_terms=entry[2][:8],
                    reasoning="reference token overlap with material metadata/text",
                    confidence=entry[0],
                )
                for entry in selected
            ]
            alignments.append(
                BibliographyItemAlignment(
                    bibliography_id=item.bibliography_id,
                    raw_reference=item.raw_reference,
                    matched_document_ids=[entry[1].material.metadata.document_id for entry in selected if entry[0] >= 0.3],
                    candidate_matches=[entry[1].material.metadata.document_id for entry in candidates[:5]],
                    match_state=state,
                    confidence=round(confidence, 4),
                    reasoning=reasoning,
                    evidence=evidence,
                )
            )
        return alignments, gaps, redundancies

    def _align_topics(
        self,
        edital: EditalExtractionResult,
        contexts: list[_MaterialContext],
    ) -> tuple[list[TopicCoverageCandidate], list[SectionCoverageCandidate], list[CoverageGap], list[CoverageRedundancy]]:
        subtopics_by_topic: dict[str, list[EditalSubtopicCandidate]] = defaultdict(list)
        for subtopic in edital.subtopics:
            subtopics_by_topic[subtopic.parent_topic_id].append(subtopic)

        topic_coverage: list[TopicCoverageCandidate] = []
        section_coverage: list[SectionCoverageCandidate] = []
        gaps: list[CoverageGap] = []
        redundancies: list[CoverageRedundancy] = []
        for topic in edital.topics:
            base_terms = self._tokens(topic.title)
            subtopic_terms: set[str] = set()
            for subtopic in subtopics_by_topic.get(topic.topic_id, []):
                subtopic_terms.update(self._tokens(subtopic.title))
            all_terms = base_terms | subtopic_terms
            matches: list[tuple[float, _MaterialContext, list[str], list[str], list[str]]] = []
            ocr_overlap: list[_MaterialContext] = []
            missing_text_overlap: list[_MaterialContext] = []
            for context in contexts:
                if context.ocr_required:
                    if all_terms & context.filename_tokens:
                        ocr_overlap.append(context)
                    continue
                if not context.has_processed_text:
                    if all_terms & context.filename_tokens:
                        missing_text_overlap.append(context)
                    continue
                if not context.processed_text_tokens:
                    continue
                matched_terms = sorted(all_terms & context.processed_text_tokens)
                if not matched_terms:
                    continue
                section_ids: list[str] = []
                chunk_ids: list[str] = []
                best_section_score = 0.0
                for section in context.sections:
                    section_tokens = self._tokens(section.title)
                    overlap = self._overlap_score(all_terms, section_tokens)
                    if overlap > 0:
                        section_ids.append(section.section_id)
                        best_section_score = max(best_section_score, overlap)
                best_chunk_score = 0.0
                for chunk in context.chunks:
                    chunk_tokens = self._tokens(chunk.text)
                    overlap = self._overlap_score(all_terms, chunk_tokens)
                    if overlap >= 0.2:
                        chunk_ids.append(chunk.chunk_id)
                        best_chunk_score = max(best_chunk_score, overlap)
                score = max(
                    self._overlap_score(all_terms, context.processed_text_tokens),
                    best_section_score + 0.15,
                    best_chunk_score + 0.1,
                )
                score = min(score, 1.0)
                matches.append((score, context, matched_terms, sorted(set(section_ids)), sorted(set(chunk_ids))))
            matches.sort(key=lambda entry: (-entry[0], entry[1].material.metadata.document_id))
            strong = [entry for entry in matches if entry[0] >= 0.6]
            partial = [entry for entry in matches if entry[0] >= 0.35]
            if strong:
                coverage_state = "covered"
                selected = strong[:3]
                confidence = strong[0][0]
                reasoning = "topic terms were found strongly in processed material text and sections"
            elif partial:
                coverage_state = "partially_covered" if partial[0][0] >= 0.45 else "weakly_covered"
                selected = partial[:3]
                confidence = partial[0][0]
                reasoning = "topic terms were found with limited but meaningful overlap in processed materials"
            else:
                coverage_state = "uncovered"
                selected = []
                confidence = 0.0
                reasoning = "no meaningful processed material coverage was found for this topic"
            evidence = [
                AlignmentEvidence(
                    source_type="document",
                    source_id=entry[1].material.metadata.document_id,
                    excerpt=self._excerpt(entry[1].searchable_text),
                    matched_terms=entry[2][:8],
                    reasoning="topic/subtopic term overlap with processed material",
                    confidence=entry[0],
                )
                for entry in selected
            ]
            matched_document_ids = [entry[1].material.metadata.document_id for entry in selected]
            matched_section_ids = sorted({sid for entry in selected for sid in entry[3]})
            matched_chunk_ids = sorted({cid for entry in selected for cid in entry[4]})
            topic_coverage.append(
                TopicCoverageCandidate(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    matched_document_ids=matched_document_ids,
                    matched_chunk_ids=matched_chunk_ids,
                    matched_section_ids=matched_section_ids,
                    coverage_state=coverage_state,
                    confidence=round(confidence, 4),
                    reasoning=reasoning,
                    evidence=evidence,
                )
            )
            for entry in selected:
                for section_id in entry[3][:2]:
                    section_title = next((section.title for section in entry[1].sections if section.section_id == section_id), "")
                    section_coverage.append(
                        SectionCoverageCandidate(
                            section_id=section_id,
                            section_title=section_title,
                            document_id=entry[1].material.metadata.document_id,
                            matched_topic_ids=[topic.topic_id],
                            matched_terms=entry[2][:8],
                            confidence=round(entry[0], 4),
                            reasoning="document section title/content overlaps with edital topic terms",
                            evidence=[
                                AlignmentEvidence(
                                    source_type="document_section",
                                    source_id=section_id,
                                    excerpt=self._excerpt(section_title or entry[1].searchable_text),
                                    matched_terms=entry[2][:8],
                                    reasoning="section matched edital topic",
                                    confidence=entry[0],
                                )
                            ],
                        )
                    )
            if coverage_state == "uncovered":
                gaps.append(
                    CoverageGap(
                        gap_id=f"{topic.topic_id}:gap",
                        gap_type="uncovered_topic",
                        target_id=topic.topic_id,
                        target_title=topic.title,
                        reason="No processed material showed meaningful coverage for this topic.",
                        severity="high",
                    )
                )
            elif coverage_state == "weakly_covered":
                gaps.append(
                    CoverageGap(
                        gap_id=f"{topic.topic_id}:weak-gap",
                        gap_type="weak_topic_coverage",
                        target_id=topic.topic_id,
                        target_title=topic.title,
                        reason="Coverage exists but is weak and should be reviewed.",
                        severity="medium",
                        evidence=evidence[:1],
                    )
                )
            if ocr_overlap:
                gaps.append(
                    CoverageGap(
                        gap_id=f"{topic.topic_id}:ocr-gap",
                        gap_type="ocr_required",
                        target_id=topic.topic_id,
                        target_title=topic.title,
                        reason="Potentially relevant material requires OCR before coverage can be confirmed.",
                        severity="medium",
                        evidence=[
                            AlignmentEvidence(
                                source_type="material_filename",
                                source_id=context.material.metadata.document_id,
                                excerpt=self._excerpt(context.material.metadata.filename),
                                matched_terms=sorted(all_terms & context.filename_tokens)[:8],
                                reasoning="topic terms overlap with an OCR-required material filename",
                                confidence=0.4,
                            )
                            for context in ocr_overlap[:2]
                        ],
                    )
                )
            if missing_text_overlap:
                gaps.append(
                    CoverageGap(
                        gap_id=f"{topic.topic_id}:missing-text-gap",
                        gap_type="missing_document_text",
                        target_id=topic.topic_id,
                        target_title=topic.title,
                        reason="Potentially relevant material exists but has not produced processed text yet.",
                        severity="medium",
                        evidence=[
                            AlignmentEvidence(
                                source_type="material_filename",
                                source_id=context.material.metadata.document_id,
                                excerpt=self._excerpt(context.material.metadata.filename),
                                matched_terms=sorted(all_terms & context.filename_tokens)[:8],
                                reasoning="topic terms overlap with an uploaded material that lacks processed text",
                                confidence=0.35,
                            )
                            for context in missing_text_overlap[:2]
                        ],
                    )
                )
            if len(matched_document_ids) > 1:
                redundancies.append(
                    CoverageRedundancy(
                        redundancy_id=f"{topic.topic_id}:redundancy",
                        redundancy_type="overlapping_topic_coverage",
                        target_id=topic.topic_id,
                        target_title=topic.title,
                        overlapping_document_ids=matched_document_ids,
                        reason="Multiple materials strongly cover the same edital topic.",
                        severity="low",
                        evidence=evidence[:2],
                    )
                )
        return topic_coverage, section_coverage, gaps, redundancies

    def _document_coverage(
        self,
        contexts: list[_MaterialContext],
        bibliography_alignments: list[BibliographyItemAlignment],
        topic_coverage: list[TopicCoverageCandidate],
        section_coverage: list[SectionCoverageCandidate],
    ) -> list[DocumentCoverageCandidate]:
        bibliography_by_doc: dict[str, list[str]] = defaultdict(list)
        for item in bibliography_alignments:
            for document_id in item.matched_document_ids:
                bibliography_by_doc[document_id].append(item.bibliography_id)
        topics_by_doc: dict[str, list[str]] = defaultdict(list)
        for item in topic_coverage:
            for document_id in item.matched_document_ids:
                topics_by_doc[document_id].append(item.topic_id)
        sections_by_doc: dict[str, list[str]] = defaultdict(list)
        for item in section_coverage:
            sections_by_doc[item.document_id].append(item.section_id)
        results: list[DocumentCoverageCandidate] = []
        for context in contexts:
            doc_id = context.material.metadata.document_id
            evidences: list[AlignmentEvidence] = []
            if bibliography_by_doc[doc_id]:
                evidences.append(
                    AlignmentEvidence(
                        source_type="bibliography_match",
                        source_id=doc_id,
                        excerpt=self._excerpt(context.searchable_text),
                        matched_terms=sorted(context.filename_tokens)[:8],
                        reasoning="document matched at least one bibliography candidate",
                        confidence=0.8,
                    )
                )
            results.append(
                DocumentCoverageCandidate(
                    document_id=doc_id,
                    material_id=doc_id,
                    filename=context.material.metadata.filename,
                    title_hint=context.title_hint,
                    matched_bibliography_ids=sorted(set(bibliography_by_doc[doc_id])),
                    covered_topic_ids=sorted(set(topics_by_doc[doc_id])),
                    covered_subtopic_ids=[],
                    matched_section_ids=sorted(set(sections_by_doc[doc_id])),
                    confidence=0.8 if bibliography_by_doc[doc_id] or topics_by_doc[doc_id] else 0.2,
                    reasoning="document coverage summary derived from bibliography and topic matches",
                    evidence=evidences,
                    metadata={"ocr_required": context.ocr_required},
                )
            )
        return results

    def _warnings_from_contexts(
        self,
        contexts: list[_MaterialContext],
        topic_coverage: list[TopicCoverageCandidate],
    ) -> list[AlignmentWarning]:
        warnings: list[AlignmentWarning] = []
        if any(context.ocr_required for context in contexts):
            warnings.append(
                AlignmentWarning(
                    code="ocr_required_material_present",
                    message="At least one candidate material requires OCR before full coverage can be confirmed.",
                    severity="warning",
                )
            )
        if not any(item.coverage_state in {"covered", "partially_covered"} for item in topic_coverage):
            warnings.append(
                AlignmentWarning(
                    code="low_topic_coverage_confidence",
                    message="No topic achieved strong coverage confidence against available materials.",
                    severity="warning",
                )
            )
        return warnings

    def _overlap_score(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        overlap = left & right
        if not overlap:
            return 0.0
        return len(overlap) / max(1, min(len(left), len(right)))

    def _tokens(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        return {
            token
            for token in re.findall(r"[a-z0-9]+", normalized)
            if len(token) >= 3 and token not in STOPWORDS
        }

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _filename_stem(self, filename: str) -> str:
        if "." in filename:
            filename = filename.rsplit(".", 1)[0]
        return filename.replace("_", " ").replace("-", " ").strip()

    def _excerpt(self, text: str, *, limit: int = 160) -> str:
        return " ".join(text.split())[:limit]
