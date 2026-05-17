from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from app.domain.models import (
    AlignmentEvidence,
    AlignmentWarning,
    BibliographyAlignmentResult,
    CoverageGap,
    CoverageRedundancy,
    CurriculumCoverageLink,
    CurriculumGapReference,
    CurriculumGraph,
    CurriculumGraphState,
    CurriculumGraphSummary,
    CurriculumGraphWarning,
    CurriculumRedundancyReference,
    CurriculumSourceEvidence,
    CurriculumSubjectNode,
    CurriculumSubtopicNode,
    CurriculumTopicNode,
    EditalExtractionResult,
    EditalSectionCandidate,
    EditalSubtopicCandidate,
    EditalTopicCandidate,
    TopicCoverageCandidate,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository


GRAPH_VERSION = "curriculum-graph-v1"
FINAL_GRAPH_STATUSES = {"ready_for_review", "insufficient_alignment"}


class CurriculumGraphBuilderService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_graph(
        self,
        edital_id: str,
        *,
        user_id: str | None,
    ) -> CurriculumGraphState | None:
        edital = self.repository.get_edital_extraction_by_id(edital_id, user_id=user_id)
        if edital is None:
            return CurriculumGraphState(
                graph_id=f"graph:{edital_id}",
                edital_id=edital_id,
                user_id=user_id,
                current_stage="insufficient_edital",
                status="insufficient_edital",
                warnings=["missing_edital_extraction"],
                created_at=utc_now(),
                updated_at=utc_now(),
                graph_version=GRAPH_VERSION,
            )

        existing = self.repository.get_curriculum_graph_state(edital_id, user_id=user_id)
        if existing is not None and existing.status in FINAL_GRAPH_STATUSES:
            return existing

        alignment = self.repository.get_bibliography_alignment_result(edital_id, user_id=user_id)
        return self._build(edital, alignment=alignment, user_id=user_id)

    def _build(
        self,
        edital: EditalExtractionResult,
        *,
        alignment: BibliographyAlignmentResult | None,
        user_id: str | None,
    ) -> CurriculumGraphState:
        created_at = utc_now()
        graph_id = f"graph:{edital.edital_id}"
        subjects, topic_subject_map = self._subject_nodes(edital)
        topics = self._topic_nodes(edital, topic_subject_map)
        subtopics = self._subtopic_nodes(edital, topics)
        topic_by_id = {item.topic_id: item for item in topics}
        subject_by_id = {item.subject_id: item for item in subjects}
        for topic in topics:
            subject = subject_by_id.get(topic.subject_id)
            if subject is not None:
                subject.topic_ids.append(topic.topic_id)

        warnings: list[CurriculumGraphWarning] = []
        coverage_links: list[CurriculumCoverageLink] = []
        gap_refs: list[CurriculumGapReference] = []
        redundancy_refs: list[CurriculumRedundancyReference] = []
        alignment_id: str | None = None
        status = "ready_for_review"
        current_stage = "ready_for_review"

        if alignment is None:
            status = "insufficient_alignment"
            current_stage = "insufficient_alignment"
            warnings.append(
                CurriculumGraphWarning(
                    code="missing_bibliography_alignment",
                    message="Bibliography alignment has not been built for this edital yet.",
                    severity="warning",
                )
            )
            for topic in topics:
                topic.coverage_state = "insufficient_evidence"
                topic.review_state = "needs_review"
                topic.reasoning = "topic exists in edital extraction but alignment evidence is missing"
                topic.confidence = min(topic.confidence, 0.35)
            for subtopic in subtopics:
                subtopic.coverage_state = "insufficient_evidence"
                subtopic.review_state = "needs_review"
                subtopic.reasoning = "subtopic exists in edital extraction but alignment evidence is missing"
                subtopic.confidence = min(subtopic.confidence, 0.3)
        else:
            alignment_id = alignment.alignment_id
            topic_coverage_map = {item.topic_id: item for item in alignment.topic_coverage}
            topic_gap_map: dict[str, list[CoverageGap]] = defaultdict(list)
            for gap in alignment.gaps:
                topic_gap_map[gap.target_id].append(gap)
            topic_redundancy_map: dict[str, list[CoverageRedundancy]] = defaultdict(list)
            for redundancy in alignment.redundancies:
                topic_redundancy_map[redundancy.target_id].append(redundancy)

            for topic in topics:
                coverage = topic_coverage_map.get(topic.source_topic_candidate_id)
                topic_gaps = topic_gap_map.get(topic.source_topic_candidate_id, [])
                topic_redundancies = topic_redundancy_map.get(topic.source_topic_candidate_id, [])
                if coverage is not None:
                    topic.coverage_state = coverage.coverage_state
                    topic.review_state = self._review_state_for_topic(coverage.coverage_state, topic_gaps, topic_redundancies)
                    topic.confidence = coverage.confidence
                    topic.reasoning = coverage.reasoning
                    topic.evidence = self._convert_evidence(
                        coverage.evidence,
                        target_kind="topic",
                        target_id=topic.topic_id,
                    )
                    coverage_links.append(self._topic_coverage_link(topic, coverage))
                else:
                    topic.coverage_state = self._coverage_state_from_gaps(topic_gaps)
                    topic.review_state = self._review_state_for_topic(topic.coverage_state, topic_gaps, topic_redundancies)
                    topic.reasoning = (
                        "topic state was derived conservatively from alignment gaps because no direct topic coverage record was available"
                        if topic_gaps
                        else "no topic coverage record was available in the alignment result"
                    )
                    topic.confidence = min(topic.confidence, 0.3)
                for gap in topic_gaps:
                    gap_refs.append(self._gap_reference(gap, target_type="topic"))
                for redundancy in topic_redundancies:
                    redundancy_refs.append(self._redundancy_reference(redundancy, target_type="topic"))

            for subtopic in subtopics:
                parent = topic_by_id.get(subtopic.parent_topic_id)
                if parent is not None:
                    subtopic.coverage_state = parent.coverage_state
                    subtopic.review_state = parent.review_state
                    subtopic.confidence = round(min(parent.confidence, subtopic.confidence + 0.1), 4)
                    subtopic.reasoning = "subtopic inherits candidate coverage from parent topic alignment"
                    subtopic.evidence = parent.evidence[:2]
                    coverage_links.append(
                        CurriculumCoverageLink(
                            link_id=f"coverage:subtopic:{subtopic.subtopic_id}",
                            target_type="subtopic",
                            target_id=subtopic.subtopic_id,
                            document_ids=self._document_ids_from_evidence(subtopic.evidence),
                            chunk_ids=self._chunk_ids_from_evidence(subtopic.evidence),
                            section_ids=self._section_ids_from_evidence(subtopic.evidence),
                            coverage_state=subtopic.coverage_state,
                            confidence=subtopic.confidence,
                            reasoning=subtopic.reasoning,
                            evidence=subtopic.evidence,
                            metadata={"source_subtopic_candidate_id": subtopic.source_subtopic_candidate_id},
                        )
                    )

            for gap in alignment.gaps:
                if gap.target_id not in topic_by_id:
                    gap_refs.append(self._gap_reference(gap, target_type="bibliography"))
            for redundancy in alignment.redundancies:
                if redundancy.target_id not in topic_by_id:
                    redundancy_refs.append(self._redundancy_reference(redundancy, target_type="bibliography"))
            warnings.extend(self._convert_warnings(alignment.warnings))

        for subject in subjects:
            related_topics = [topic_by_id[topic_id] for topic_id in subject.topic_ids if topic_id in topic_by_id]
            subject.coverage_state = self._aggregate_coverage_state([item.coverage_state for item in related_topics])
            subject.review_state = self._aggregate_review_state([item.review_state for item in related_topics])
            subject.confidence = round(sum(item.confidence for item in related_topics) / len(related_topics), 4) if related_topics else 0.0
            subject.reasoning = "subject node aggregates candidate topic coverage from its child topics"
            subject.evidence = [evidence for item in related_topics for evidence in item.evidence][:3]
            if alignment is not None:
                coverage_links.append(
                    CurriculumCoverageLink(
                        link_id=f"coverage:subject:{subject.subject_id}",
                        target_type="subject",
                        target_id=subject.subject_id,
                        document_ids=self._document_ids_from_evidence(subject.evidence),
                        chunk_ids=self._chunk_ids_from_evidence(subject.evidence),
                        section_ids=self._section_ids_from_evidence(subject.evidence) or subject.source_section_ids,
                        coverage_state=subject.coverage_state,
                        confidence=subject.confidence,
                        reasoning=subject.reasoning,
                        evidence=subject.evidence,
                        metadata={"topic_ids": subject.topic_ids},
                    )
                )

        graph = CurriculumGraph(
            graph_id=graph_id,
            edital_id=edital.edital_id,
            alignment_id=alignment_id,
            user_id=user_id,
            subjects=subjects,
            topics=topics,
            subtopics=subtopics,
            coverage_links=coverage_links,
            gaps=gap_refs,
            redundancies=redundancy_refs,
            warnings=warnings,
            summary=self._summary(subjects, topics, subtopics, gap_refs, redundancy_refs, warnings),
            graph_version=GRAPH_VERSION,
            metadata={
                "edital_sections_detected": len(edital.sections),
                "alignment_available": alignment is not None,
            },
        )
        state = CurriculumGraphState(
            graph_id=graph_id,
            edital_id=edital.edital_id,
            alignment_id=alignment_id,
            user_id=user_id,
            current_stage=current_stage,
            status=status,
            subject_count=len(subjects),
            topic_count=len(topics),
            subtopic_count=len(subtopics),
            coverage_links_count=len(coverage_links),
            gaps_count=len(gap_refs),
            redundancies_count=len(redundancy_refs),
            warnings=[item.code for item in warnings],
            created_at=created_at,
            updated_at=created_at,
            graph_version=GRAPH_VERSION,
        )
        self.repository.save_curriculum_graph(graph, user_id=user_id)
        self.repository.save_curriculum_graph_state(state, user_id=user_id)
        return state

    def _subject_nodes(
        self,
        edital: EditalExtractionResult,
    ) -> tuple[list[CurriculumSubjectNode], dict[str, str]]:
        subjects: list[CurriculumSubjectNode] = []
        topic_subject_map: dict[str, str] = {}
        content_sections = [section for section in edital.sections if section.section_type == "content_program"]
        if content_sections:
            for index, section in enumerate(sorted(content_sections, key=lambda item: item.order_index)):
                subject_id = f"subject:{section.section_id}"
                subjects.append(
                    CurriculumSubjectNode(
                        subject_id=subject_id,
                        title=section.title,
                        normalized_title=section.normalized_title,
                        order_index=index,
                        source_section_ids=[section.section_id],
                        confidence=section.confidence,
                        reasoning=section.reasoning,
                        evidence=[
                            CurriculumSourceEvidence(
                                evidence_id=f"evidence:subject:{subject_id}",
                                source_type="edital_section",
                                source_id=section.section_id,
                                section_id=section.section_id,
                                excerpt=section.text_excerpt[:160],
                                confidence=section.confidence,
                                reasoning=section.reasoning,
                                metadata={"section_type": section.section_type},
                            )
                        ],
                    )
                )
                for topic in edital.topics:
                    if topic.parent_section_id == section.section_id:
                        topic_subject_map[topic.topic_id] = subject_id
        if not subjects:
            subject_id = "subject:conteudo-programatico"
            subjects.append(
                CurriculumSubjectNode(
                    subject_id=subject_id,
                    title="Conteudo Programatico",
                    normalized_title="conteudo programatico",
                    order_index=0,
                    confidence=0.5,
                    reasoning="fallback subject created because no explicit content-program section was available",
                )
            )
        for topic in edital.topics:
            if topic.topic_id not in topic_subject_map:
                topic_subject_map[topic.topic_id] = subjects[0].subject_id
        return subjects, topic_subject_map

    def _topic_nodes(
        self,
        edital: EditalExtractionResult,
        topic_subject_map: dict[str, str],
    ) -> list[CurriculumTopicNode]:
        topics: list[CurriculumTopicNode] = []
        for topic in sorted(edital.topics, key=lambda item: item.order_index):
            topics.append(
                CurriculumTopicNode(
                    topic_id=topic.topic_id,
                    title=topic.title,
                    normalized_title=topic.normalized_title,
                    subject_id=topic_subject_map[topic.topic_id],
                    source_topic_candidate_id=topic.topic_id,
                    order_index=topic.order_index,
                    confidence=topic.confidence,
                    reasoning=topic.reasoning,
                    evidence=[
                        CurriculumSourceEvidence(
                            evidence_id=f"evidence:topic:{topic.topic_id}",
                            source_type="edital_topic",
                            source_id=topic.topic_id,
                            excerpt=topic.source_excerpt[:160],
                            matched_terms=self._tokens(topic.title),
                            confidence=topic.confidence,
                            reasoning=topic.reasoning,
                        )
                    ] if topic.source_excerpt or topic.reasoning else [],
                    metadata={"source_chunk_ids": topic.source_chunk_ids},
                )
            )
        topic_ids_by_subject: dict[str, list[str]] = defaultdict(list)
        for topic in topics:
            topic_ids_by_subject[topic.subject_id].append(topic.topic_id)
        return topics

    def _subtopic_nodes(
        self,
        edital: EditalExtractionResult,
        topics: list[CurriculumTopicNode],
    ) -> list[CurriculumSubtopicNode]:
        topic_map = {item.topic_id: item for item in topics}
        subtopics: list[CurriculumSubtopicNode] = []
        for subtopic in sorted(edital.subtopics, key=lambda item: item.order_index):
            subtopics.append(
                CurriculumSubtopicNode(
                    subtopic_id=subtopic.subtopic_id,
                    title=subtopic.title,
                    normalized_title=subtopic.normalized_title,
                    parent_topic_id=subtopic.parent_topic_id,
                    source_subtopic_candidate_id=subtopic.subtopic_id,
                    order_index=subtopic.order_index,
                    confidence=subtopic.confidence,
                    reasoning=subtopic.reasoning,
                    evidence=[
                        CurriculumSourceEvidence(
                            evidence_id=f"evidence:subtopic:{subtopic.subtopic_id}",
                            source_type="edital_subtopic",
                            source_id=subtopic.subtopic_id,
                            excerpt=subtopic.source_excerpt[:160],
                            matched_terms=self._tokens(subtopic.title),
                            confidence=subtopic.confidence,
                            reasoning=subtopic.reasoning,
                        )
                    ] if subtopic.source_excerpt or subtopic.reasoning else [],
                    metadata={"source_chunk_ids": subtopic.source_chunk_ids},
                )
            )
            parent = topic_map.get(subtopic.parent_topic_id)
            if parent is not None:
                parent.subtopic_ids.append(subtopic.subtopic_id)
        return subtopics

    def _topic_coverage_link(
        self,
        topic: CurriculumTopicNode,
        coverage: TopicCoverageCandidate,
    ) -> CurriculumCoverageLink:
        evidence = self._convert_evidence(coverage.evidence, target_kind="topic", target_id=topic.topic_id)
        return CurriculumCoverageLink(
            link_id=f"coverage:topic:{topic.topic_id}",
            target_type="topic",
            target_id=topic.topic_id,
            document_ids=coverage.matched_document_ids,
            chunk_ids=coverage.matched_chunk_ids,
            section_ids=coverage.matched_section_ids,
            coverage_state=coverage.coverage_state,
            confidence=coverage.confidence,
            reasoning=coverage.reasoning,
            evidence=evidence,
            metadata={"source_topic_candidate_id": topic.source_topic_candidate_id},
        )

    def _convert_evidence(
        self,
        evidence: list[AlignmentEvidence],
        *,
        target_kind: str,
        target_id: str,
    ) -> list[CurriculumSourceEvidence]:
        items: list[CurriculumSourceEvidence] = []
        for index, item in enumerate(evidence):
            source_id = item.source_id
            items.append(
                CurriculumSourceEvidence(
                    evidence_id=f"evidence:{target_kind}:{target_id}:{index}",
                    source_type=item.source_type,
                    source_id=source_id,
                    document_id=source_id if item.source_type in {"document", "bibliography_match", "material_filename"} else None,
                    chunk_id=source_id if item.source_type == "document_chunk" else None,
                    section_id=source_id if item.source_type == "document_section" else None,
                    excerpt=item.excerpt[:160],
                    matched_terms=item.matched_terms[:8],
                    confidence=item.confidence,
                    reasoning=item.reasoning,
                )
            )
        return items

    def _gap_reference(self, gap: CoverageGap, *, target_type: str) -> CurriculumGapReference:
        return CurriculumGapReference(
            gap_id=f"graph-gap:{gap.gap_id}",
            source_gap_id=gap.gap_id,
            gap_type=gap.gap_type,
            target_type=target_type,
            target_id=gap.target_id,
            target_title=gap.target_title,
            severity=gap.severity,
            reason=gap.reason,
            evidence=self._convert_evidence(gap.evidence, target_kind="gap", target_id=gap.target_id),
            review_state="ocr_required" if gap.gap_type == "ocr_required" else "needs_review",
            metadata=gap.metadata,
        )

    def _redundancy_reference(
        self,
        redundancy: CoverageRedundancy,
        *,
        target_type: str,
    ) -> CurriculumRedundancyReference:
        return CurriculumRedundancyReference(
            redundancy_id=f"graph-redundancy:{redundancy.redundancy_id}",
            source_redundancy_id=redundancy.redundancy_id,
            redundancy_type=redundancy.redundancy_type,
            target_type=target_type,
            target_id=redundancy.target_id,
            target_title=redundancy.target_title,
            overlapping_document_ids=redundancy.overlapping_document_ids,
            severity=redundancy.severity,
            reason=redundancy.reason,
            evidence=self._convert_evidence(
                redundancy.evidence,
                target_kind="redundancy",
                target_id=redundancy.target_id,
            ),
            review_state="ambiguous",
            metadata=redundancy.metadata,
        )

    def _convert_warnings(self, warnings: list[AlignmentWarning]) -> list[CurriculumGraphWarning]:
        return [
            CurriculumGraphWarning(
                code=item.code,
                message=item.message,
                severity=item.severity,
                target_id=item.target_id,
                metadata=item.metadata,
            )
            for item in warnings
        ]

    def _review_state_for_topic(
        self,
        coverage_state: str,
        gaps: list[CoverageGap],
        redundancies: list[CoverageRedundancy],
    ) -> str:
        gap_types = {item.gap_type for item in gaps}
        if "ocr_required" in gap_types:
            return "ocr_required"
        if "missing_document_text" in gap_types or "missing_bibliography_material" in gap_types:
            return "source_missing"
        if redundancies or "ambiguous_reference" in gap_types:
            return "ambiguous"
        if coverage_state in {"weakly_covered", "uncovered", "insufficient_evidence"}:
            return "needs_review"
        if coverage_state == "partially_covered":
            return "candidate"
        return "ready_for_review"

    def _coverage_state_from_gaps(self, gaps: list[CoverageGap]) -> str:
        gap_types = {item.gap_type for item in gaps}
        if "ambiguous_reference" in gap_types:
            return "ambiguous"
        if "weak_topic_coverage" in gap_types:
            return "weakly_covered"
        if gap_types & {"uncovered_topic", "ocr_required", "missing_document_text", "missing_bibliography_material"}:
            return "uncovered"
        return "insufficient_evidence"

    def _aggregate_coverage_state(self, coverage_states: list[str]) -> str:
        if not coverage_states:
            return "insufficient_evidence"
        if any(state == "covered" for state in coverage_states):
            if all(state == "covered" for state in coverage_states):
                return "covered"
            return "partially_covered"
        if any(state == "partially_covered" for state in coverage_states):
            return "partially_covered"
        if any(state == "weakly_covered" for state in coverage_states):
            return "weakly_covered"
        if any(state == "ambiguous" for state in coverage_states):
            return "ambiguous"
        if all(state == "insufficient_evidence" for state in coverage_states):
            return "insufficient_evidence"
        return "uncovered"

    def _aggregate_review_state(self, review_states: list[str]) -> str:
        if not review_states:
            return "needs_review"
        if "ocr_required" in review_states:
            return "ocr_required"
        if "source_missing" in review_states:
            return "source_missing"
        if "ambiguous" in review_states:
            return "ambiguous"
        if "needs_review" in review_states:
            return "needs_review"
        if "candidate" in review_states:
            return "candidate"
        return "ready_for_review"

    def _summary(
        self,
        subjects: list[CurriculumSubjectNode],
        topics: list[CurriculumTopicNode],
        subtopics: list[CurriculumSubtopicNode],
        gaps: list[CurriculumGapReference],
        redundancies: list[CurriculumRedundancyReference],
        warnings: list[CurriculumGraphWarning],
    ) -> CurriculumGraphSummary:
        coverage_states = [item.coverage_state for item in topics]
        review_states = [item.review_state for item in subjects + topics + subtopics]
        avg_confidence = round(sum(item.confidence for item in topics) / len(topics), 4) if topics else 0.0
        return CurriculumGraphSummary(
            subject_count=len(subjects),
            topic_count=len(topics),
            subtopic_count=len(subtopics),
            covered_topics_count=sum(1 for item in coverage_states if item == "covered"),
            partially_covered_topics_count=sum(1 for item in coverage_states if item == "partially_covered"),
            weakly_covered_topics_count=sum(1 for item in coverage_states if item == "weakly_covered"),
            uncovered_topics_count=sum(1 for item in coverage_states if item == "uncovered"),
            ambiguous_topics_count=sum(1 for item in coverage_states if item == "ambiguous"),
            gap_count=len(gaps),
            redundancy_count=len(redundancies),
            ocr_required_count=sum(1 for item in gaps if item.gap_type == "ocr_required"),
            needs_review_count=sum(1 for item in review_states if item in {"needs_review", "source_missing", "ocr_required", "ambiguous"}),
            confidence_summary={"average_topic_confidence": avg_confidence, "warnings": len(warnings)},
            coverage_summary={"topic_states": {state: coverage_states.count(state) for state in sorted(set(coverage_states))}},
        )

    def _document_ids_from_evidence(self, evidence: list[CurriculumSourceEvidence]) -> list[str]:
        return sorted({item.document_id for item in evidence if item.document_id})

    def _chunk_ids_from_evidence(self, evidence: list[CurriculumSourceEvidence]) -> list[str]:
        return sorted({item.chunk_id for item in evidence if item.chunk_id})

    def _section_ids_from_evidence(self, evidence: list[CurriculumSourceEvidence]) -> list[str]:
        return sorted({item.section_id for item in evidence if item.section_id})

    def _tokens(self, text: str) -> list[str]:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return [token for token in normalized.split(" ") if token]
