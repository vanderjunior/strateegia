from __future__ import annotations

from app.domain.models import (
    AlignmentEvidence,
    AlignmentWarning,
    BibliographyAlignmentResult,
    CoverageGap,
    CoverageRedundancy,
    EditalExtractionResult,
    EditalSectionCandidate,
    EditalSubtopicCandidate,
    EditalTopicCandidate,
)


def build_section_candidate(
    *,
    section_id: str,
    title: str,
    section_type: str = "content_program",
    order_index: int = 0,
    text_excerpt: str = "",
) -> EditalSectionCandidate:
    return EditalSectionCandidate(
        section_id=section_id,
        title=title,
        normalized_title=title.lower(),
        section_type=section_type,
        order_index=order_index,
        text_excerpt=text_excerpt or title,
        confidence=0.9 if section_type == "content_program" else 0.5,
        reasoning=f"fixture section classified as {section_type}",
        metadata={"text": text_excerpt or title},
    )


def build_topic_candidate(
    *,
    topic_id: str,
    title: str,
    order_index: int = 0,
    parent_section_id: str | None = "section:content",
    source_excerpt: str = "",
) -> EditalTopicCandidate:
    return EditalTopicCandidate(
        topic_id=topic_id,
        title=title,
        normalized_title=title.lower(),
        parent_section_id=parent_section_id,
        order_index=order_index,
        source_excerpt=source_excerpt or title,
        confidence=0.8,
        reasoning="fixture topic candidate",
        source_chunk_ids=[f"chunk:{topic_id}:0"],
    )


def build_subtopic_candidate(
    *,
    subtopic_id: str,
    parent_topic_id: str,
    title: str,
    order_index: int = 0,
    source_excerpt: str = "",
) -> EditalSubtopicCandidate:
    return EditalSubtopicCandidate(
        subtopic_id=subtopic_id,
        parent_topic_id=parent_topic_id,
        title=title,
        normalized_title=title.lower(),
        order_index=order_index,
        source_excerpt=source_excerpt or title,
        confidence=0.75,
        reasoning="fixture subtopic candidate",
        source_chunk_ids=[f"chunk:{subtopic_id}:0"],
    )


def build_alignment_evidence(
    *,
    source_type: str = "document",
    source_id: str,
    excerpt: str,
    matched_terms: list[str],
    confidence: float = 0.8,
    reasoning: str = "fixture evidence",
) -> AlignmentEvidence:
    return AlignmentEvidence(
        source_type=source_type,
        source_id=source_id,
        excerpt=excerpt,
        matched_terms=matched_terms,
        confidence=confidence,
        reasoning=reasoning,
    )


def build_topic_coverage(
    *,
    topic_id: str,
    topic_title: str,
    coverage_state: str,
    confidence: float,
    matched_document_ids: list[str] | None = None,
    matched_chunk_ids: list[str] | None = None,
    matched_section_ids: list[str] | None = None,
    evidence: list[AlignmentEvidence] | None = None,
    reasoning: str = "fixture topic coverage",
) -> dict[str, object]:
    return {
        "topic_id": topic_id,
        "topic_title": topic_title,
        "matched_document_ids": matched_document_ids or [],
        "matched_chunk_ids": matched_chunk_ids or [],
        "matched_section_ids": matched_section_ids or [],
        "coverage_state": coverage_state,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": evidence or [],
    }


def build_gap(
    *,
    gap_id: str,
    gap_type: str,
    target_id: str,
    target_title: str,
    severity: str = "medium",
    reason: str = "fixture gap",
    evidence: list[AlignmentEvidence] | None = None,
) -> CoverageGap:
    return CoverageGap(
        gap_id=gap_id,
        gap_type=gap_type,
        target_id=target_id,
        target_title=target_title,
        severity=severity,
        reason=reason,
        evidence=evidence or [],
    )


def build_redundancy(
    *,
    redundancy_id: str,
    redundancy_type: str,
    target_id: str,
    target_title: str,
    overlapping_document_ids: list[str],
    severity: str = "low",
    reason: str = "fixture redundancy",
    evidence: list[AlignmentEvidence] | None = None,
) -> CoverageRedundancy:
    return CoverageRedundancy(
        redundancy_id=redundancy_id,
        redundancy_type=redundancy_type,
        target_id=target_id,
        target_title=target_title,
        overlapping_document_ids=overlapping_document_ids,
        severity=severity,
        reason=reason,
        evidence=evidence or [],
    )


def build_edital_result(
    *,
    edital_id: str,
    document_id: str,
    sections: list[EditalSectionCandidate] | None = None,
    topics: list[EditalTopicCandidate] | None = None,
    subtopics: list[EditalSubtopicCandidate] | None = None,
) -> EditalExtractionResult:
    return EditalExtractionResult(
        edital_id=edital_id,
        document_id=document_id,
        user_id="user-a",
        source_text_length=400,
        sections=sections or [],
        topics=topics or [],
        subtopics=subtopics or [],
        warnings=[],
        confidence_summary={"candidate_only": True},
        metadata={"fixture": True},
    )


def build_alignment_result(
    *,
    edital_id: str,
    topic_coverage: list[dict[str, object]] | None = None,
    gaps: list[CoverageGap] | None = None,
    redundancies: list[CoverageRedundancy] | None = None,
    warnings: list[AlignmentWarning] | None = None,
) -> BibliographyAlignmentResult:
    return BibliographyAlignmentResult(
        alignment_id=f"alignment:{edital_id}",
        edital_id=edital_id,
        user_id="user-a",
        topic_coverage=topic_coverage or [],
        gaps=gaps or [],
        redundancies=redundancies or [],
        warnings=warnings or [],
        confidence_summary={"candidate_only": True},
        metadata={"fixture": True},
    )


def basic_covered_graph_fixture() -> dict[str, object]:
    edital_id = "edital:basic-covered"
    topic = build_topic_candidate(topic_id="topic:ripeam", title="RIPEAM")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:basic-covered",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="covered",
                    confidence=0.9,
                    matched_document_ids=["doc:ripeam"],
                    matched_chunk_ids=["chunk:ripeam:1"],
                    matched_section_ids=["section:ripeam"],
                    evidence=[
                        build_alignment_evidence(
                            source_type="document",
                            source_id="doc:ripeam",
                            excerpt="RIPEAM com regras de governo e navegacao.",
                            matched_terms=["ripeam", "regras"],
                            confidence=0.9,
                        ),
                        build_alignment_evidence(
                            source_type="document_section",
                            source_id="section:ripeam",
                            excerpt="RIPEAM - Regras de Governo e Navegacao",
                            matched_terms=["ripeam"],
                            confidence=0.85,
                        ),
                    ],
                    reasoning="strong overlap in processed material",
                )
            ],
        ),
    }


def partial_coverage_graph_fixture() -> dict[str, object]:
    edital_id = "edital:partial-coverage"
    topic = build_topic_candidate(topic_id="topic:meteorologia", title="Meteorologia")
    subtopics = [
        build_subtopic_candidate(subtopic_id="subtopic:ventos", parent_topic_id=topic.topic_id, title="Ventos", order_index=0),
        build_subtopic_candidate(subtopic_id="subtopic:frentes", parent_topic_id=topic.topic_id, title="Frentes", order_index=1),
    ]
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:partial-coverage",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
            subtopics=subtopics,
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="partially_covered",
                    confidence=0.58,
                    matched_document_ids=["doc:meteorologia"],
                    matched_chunk_ids=["chunk:meteorologia:0"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:meteorologia",
                            excerpt="Ventos e cartas sinoticas para navegacao.",
                            matched_terms=["ventos", "meteorologia"],
                            confidence=0.58,
                        )
                    ],
                    reasoning="partial overlap with only part of the expected subtopic space",
                )
            ],
        ),
    }


def weak_coverage_graph_fixture() -> dict[str, object]:
    edital_id = "edital:weak-coverage"
    topic = build_topic_candidate(topic_id="topic:leg-mar", title="Legislacao Maritima Especial")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:weak-coverage",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="weakly_covered",
                    confidence=0.32,
                    matched_document_ids=["doc:generic"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:generic",
                            excerpt="Normas gerais e conteudo administrativo.",
                            matched_terms=["normas"],
                            confidence=0.32,
                        )
                    ],
                    reasoning="generic overlap only",
                )
            ],
        ),
    }


def uncovered_topic_graph_fixture() -> dict[str, object]:
    edital_id = "edital:uncovered"
    topic = build_topic_candidate(topic_id="topic:arte-naval", title="Arte Naval")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:uncovered",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            gaps=[
                build_gap(
                    gap_id="gap:arte-naval",
                    gap_type="uncovered_topic",
                    target_id=topic.topic_id,
                    target_title=topic.title,
                    severity="high",
                    reason="No processed material showed meaningful coverage.",
                )
            ],
        ),
    }


def ocr_required_graph_fixture() -> dict[str, object]:
    edital_id = "edital:ocr-required"
    topic = build_topic_candidate(topic_id="topic:autoridade", title="Autoridade Maritima Aplicada")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:ocr-required",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            gaps=[
                build_gap(
                    gap_id="gap:ocr",
                    gap_type="ocr_required",
                    target_id=topic.topic_id,
                    target_title=topic.title,
                    reason="Relevant material requires OCR.",
                    evidence=[
                        build_alignment_evidence(
                            source_type="material_filename",
                            source_id="doc:autoridade-pdf",
                            excerpt="autoridade_maritima_aplicada.pdf",
                            matched_terms=["autoridade", "maritima"],
                            confidence=0.4,
                        )
                    ],
                )
            ],
            warnings=[
                AlignmentWarning(
                    code="ocr_required_material_present",
                    message="At least one material requires OCR.",
                    severity="warning",
                )
            ],
        ),
    }


def missing_document_text_graph_fixture() -> dict[str, object]:
    edital_id = "edital:missing-text"
    topic = build_topic_candidate(topic_id="topic:navegacao", title="Navegacao Costeira")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:missing-text",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            gaps=[
                build_gap(
                    gap_id="gap:missing-text",
                    gap_type="missing_document_text",
                    target_id=topic.topic_id,
                    target_title=topic.title,
                    reason="Potentially relevant material lacks processed text.",
                    evidence=[
                        build_alignment_evidence(
                            source_type="material_filename",
                            source_id="doc:navegacao-upload",
                            excerpt="navegacao_costeira_manual.pdf",
                            matched_terms=["navegacao", "costeira"],
                            confidence=0.35,
                        )
                    ],
                )
            ],
        ),
    }


def ambiguous_reference_graph_fixture() -> dict[str, object]:
    edital_id = "edital:ambiguous"
    topic = build_topic_candidate(topic_id="topic:ripeam", title="RIPEAM")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:ambiguous",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="partially_covered",
                    confidence=0.62,
                    matched_document_ids=["doc:ripeam-a", "doc:ripeam-b"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:ripeam-a",
                            excerpt="RIPEAM comentado com regras de governo.",
                            matched_terms=["ripeam"],
                            confidence=0.62,
                        )
                    ],
                    reasoning="multiple candidate materials overlap the same topic",
                )
            ],
            gaps=[
                build_gap(
                    gap_id="gap:ambiguous-ref",
                    gap_type="ambiguous_reference",
                    target_id=topic.topic_id,
                    target_title=topic.title,
                    reason="Multiple references may map to this topic.",
                )
            ],
        ),
    }


def redundancy_graph_fixture() -> dict[str, object]:
    edital_id = "edital:redundancy"
    topic = build_topic_candidate(topic_id="topic:meteorologia", title="Meteorologia")
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:redundancy",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="covered",
                    confidence=0.82,
                    matched_document_ids=["doc:meteo-a", "doc:meteo-b"],
                    matched_chunk_ids=["chunk:meteo-a:0", "chunk:meteo-b:0"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:meteo-a",
                            excerpt="Ventos, frentes e cartas sinoticas.",
                            matched_terms=["ventos", "frentes"],
                            confidence=0.82,
                        )
                    ],
                )
            ],
            redundancies=[
                build_redundancy(
                    redundancy_id="redundancy:topic",
                    redundancy_type="overlapping_topic_coverage",
                    target_id=topic.topic_id,
                    target_title=topic.title,
                    overlapping_document_ids=["doc:meteo-a", "doc:meteo-b"],
                ),
                build_redundancy(
                    redundancy_id="redundancy:biblio",
                    redundancy_type="duplicate_bibliography_match",
                    target_id="biblio:ripeam",
                    target_title="RIPEAM Comentado",
                    overlapping_document_ids=["doc:ripeam-a", "doc:ripeam-b"],
                ),
            ],
        ),
    }


def subject_fallback_graph_fixture() -> dict[str, object]:
    edital_id = "edital:fallback-subject"
    topic = build_topic_candidate(topic_id="topic:comunicacoes", title="Comunicacoes", parent_section_id=None)
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:fallback-subject",
            sections=[build_section_candidate(section_id="section:unknown", title="Avisos Gerais", section_type="unknown")],
            topics=[topic],
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="covered",
                    confidence=0.74,
                    matched_document_ids=["doc:comunicacoes"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:comunicacoes",
                            excerpt="Comunicacoes de bordo e fraseologia.",
                            matched_terms=["comunicacoes"],
                            confidence=0.74,
                        )
                    ],
                )
            ],
        ),
    }


def subtopic_hierarchy_graph_fixture() -> dict[str, object]:
    edital_id = "edital:subtopic-hierarchy"
    topic = build_topic_candidate(topic_id="topic:meteorologia", title="Meteorologia")
    subtopics = [
        build_subtopic_candidate(subtopic_id="subtopic:ventos", parent_topic_id=topic.topic_id, title="Ventos", order_index=0),
        build_subtopic_candidate(subtopic_id="subtopic:frentes", parent_topic_id=topic.topic_id, title="Frentes Frias", order_index=1),
        build_subtopic_candidate(subtopic_id="subtopic:cartas", parent_topic_id=topic.topic_id, title="Cartas Sinoticas", order_index=2),
    ]
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:subtopic-hierarchy",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[topic],
            subtopics=subtopics,
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id=topic.topic_id,
                    topic_title=topic.title,
                    coverage_state="partially_covered",
                    confidence=0.57,
                    matched_document_ids=["doc:meteo"],
                    matched_chunk_ids=["chunk:meteo:0"],
                    evidence=[
                        build_alignment_evidence(
                            source_id="doc:meteo",
                            excerpt="Ventos e cartas sinoticas para navegacao costeira.",
                            matched_terms=["ventos", "cartas"],
                            confidence=0.57,
                        )
                    ],
                )
            ],
        ),
    }


def maritime_praticagem_curriculum_graph_fixture() -> dict[str, object]:
    edital_id = "edital:maritime"
    topics = [
        build_topic_candidate(topic_id="topic:arte-naval", title="Arte Naval", order_index=0),
        build_topic_candidate(topic_id="topic:ripeam", title="RIPEAM", order_index=1),
        build_topic_candidate(topic_id="topic:manobra", title="Manobra", order_index=2),
        build_topic_candidate(topic_id="topic:meteorologia", title="Meteorologia", order_index=3),
        build_topic_candidate(topic_id="topic:leg-mar", title="Legislacao Maritima", order_index=4),
    ]
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:maritime",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=topics,
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(
                    topic_id="topic:ripeam",
                    topic_title="RIPEAM",
                    coverage_state="covered",
                    confidence=0.88,
                    matched_document_ids=["doc:ripeam"],
                    evidence=[build_alignment_evidence(source_id="doc:ripeam", excerpt="RIPEAM e regras de governo.", matched_terms=["ripeam"], confidence=0.88)],
                ),
                build_topic_coverage(
                    topic_id="topic:meteorologia",
                    topic_title="Meteorologia",
                    coverage_state="covered",
                    confidence=0.84,
                    matched_document_ids=["doc:meteo"],
                    evidence=[build_alignment_evidence(source_id="doc:meteo", excerpt="Ventos, pressao e frentes.", matched_terms=["ventos", "frentes"], confidence=0.84)],
                ),
                build_topic_coverage(
                    topic_id="topic:manobra",
                    topic_title="Manobra",
                    coverage_state="weakly_covered",
                    confidence=0.33,
                    matched_document_ids=["doc:ripeam"],
                    evidence=[build_alignment_evidence(source_id="doc:ripeam", excerpt="Manobras preventivas breves.", matched_terms=["manobra"], confidence=0.33)],
                ),
            ],
            gaps=[
                build_gap(gap_id="gap:arte", gap_type="uncovered_topic", target_id="topic:arte-naval", target_title="Arte Naval", severity="high"),
                build_gap(gap_id="gap:ocr-leg", gap_type="ocr_required", target_id="topic:leg-mar", target_title="Legislacao Maritima"),
            ],
        ),
    }


def mixed_review_needed_graph_fixture() -> dict[str, object]:
    edital_id = "edital:mixed-review"
    topics = [
        build_topic_candidate(topic_id="topic:covered", title="RIPEAM", order_index=0),
        build_topic_candidate(topic_id="topic:partial", title="Meteorologia", order_index=1),
        build_topic_candidate(topic_id="topic:weak", title="Comunicacoes", order_index=2),
        build_topic_candidate(topic_id="topic:uncovered", title="Arte Naval", order_index=3),
        build_topic_candidate(topic_id="topic:ocr", title="Legislacao Maritima", order_index=4),
        build_topic_candidate(topic_id="topic:ambiguous", title="Navegacao Costeira", order_index=5),
    ]
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:mixed-review",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=topics,
        ),
        "alignment": build_alignment_result(
            edital_id=edital_id,
            topic_coverage=[
                build_topic_coverage(topic_id="topic:covered", topic_title="RIPEAM", coverage_state="covered", confidence=0.9, matched_document_ids=["doc:ripeam"], evidence=[build_alignment_evidence(source_id="doc:ripeam", excerpt="RIPEAM completo.", matched_terms=["ripeam"], confidence=0.9)]),
                build_topic_coverage(topic_id="topic:partial", topic_title="Meteorologia", coverage_state="partially_covered", confidence=0.55, matched_document_ids=["doc:meteo"], evidence=[build_alignment_evidence(source_id="doc:meteo", excerpt="Ventos e cartas.", matched_terms=["ventos"], confidence=0.55)]),
                build_topic_coverage(topic_id="topic:weak", topic_title="Comunicacoes", coverage_state="weakly_covered", confidence=0.31, matched_document_ids=["doc:generic"], evidence=[build_alignment_evidence(source_id="doc:generic", excerpt="Comunicacao geral.", matched_terms=["comunicacao"], confidence=0.31)]),
                build_topic_coverage(topic_id="topic:ambiguous", topic_title="Navegacao Costeira", coverage_state="partially_covered", confidence=0.61, matched_document_ids=["doc:nav-a", "doc:nav-b"], evidence=[build_alignment_evidence(source_id="doc:nav-a", excerpt="Navegacao costeira e derrota.", matched_terms=["navegacao"], confidence=0.61)]),
            ],
            gaps=[
                build_gap(gap_id="gap:uncovered", gap_type="uncovered_topic", target_id="topic:uncovered", target_title="Arte Naval", severity="high"),
                build_gap(gap_id="gap:ocr", gap_type="ocr_required", target_id="topic:ocr", target_title="Legislacao Maritima"),
                build_gap(gap_id="gap:ambiguous", gap_type="ambiguous_reference", target_id="topic:ambiguous", target_title="Navegacao Costeira"),
            ],
            redundancies=[
                build_redundancy(redundancy_id="redundancy:nav", redundancy_type="overlapping_topic_coverage", target_id="topic:ambiguous", target_title="Navegacao Costeira", overlapping_document_ids=["doc:nav-a", "doc:nav-b"]),
            ],
        ),
    }


def no_alignment_graph_fixture() -> dict[str, object]:
    edital_id = "edital:no-alignment"
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:no-alignment",
            sections=[build_section_candidate(section_id="section:content", title="Conteudo Programatico")],
            topics=[build_topic_candidate(topic_id="topic:ripeam", title="RIPEAM")],
        ),
        "alignment": None,
    }


def low_edital_graph_fixture() -> dict[str, object]:
    edital_id = "edital:low-edital"
    return {
        "edital": build_edital_result(
            edital_id=edital_id,
            document_id="doc:low-edital",
            sections=[],
            topics=[],
            subtopics=[],
        ),
        "alignment": None,
    }


ALL_CURRICULUM_GRAPH_FIXTURES = [
    basic_covered_graph_fixture,
    partial_coverage_graph_fixture,
    weak_coverage_graph_fixture,
    uncovered_topic_graph_fixture,
    ocr_required_graph_fixture,
    missing_document_text_graph_fixture,
    ambiguous_reference_graph_fixture,
    redundancy_graph_fixture,
    subject_fallback_graph_fixture,
    subtopic_hierarchy_graph_fixture,
    maritime_praticagem_curriculum_graph_fixture,
    mixed_review_needed_graph_fixture,
    no_alignment_graph_fixture,
    low_edital_graph_fixture,
]
