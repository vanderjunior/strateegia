from __future__ import annotations

from app.domain.models import (
    CurriculumGapReference,
    CurriculumGraph,
    CurriculumGraphSummary,
    CurriculumRedundancyReference,
    CurriculumSourceEvidence,
    CurriculumSubjectNode,
    CurriculumTopicNode,
)


def build_evidence(
    *,
    evidence_id: str,
    source_id: str,
    excerpt: str,
    matched_terms: list[str],
    confidence: float = 0.8,
    source_type: str = "document",
) -> CurriculumSourceEvidence:
    return CurriculumSourceEvidence(
        evidence_id=evidence_id,
        source_type=source_type,
        source_id=source_id,
        document_id=source_id if source_type == "document" else None,
        excerpt=excerpt,
        matched_terms=matched_terms,
        confidence=confidence,
        reasoning="fixture evidence",
    )


def build_subject(
    *,
    subject_id: str,
    title: str,
    order_index: int,
    topic_ids: list[str],
    coverage_state: str = "covered",
    review_state: str = "ready_for_review",
    confidence: float = 0.8,
) -> CurriculumSubjectNode:
    return CurriculumSubjectNode(
        subject_id=subject_id,
        title=title,
        normalized_title=title.lower(),
        order_index=order_index,
        topic_ids=topic_ids,
        coverage_state=coverage_state,
        review_state=review_state,
        confidence=confidence,
        reasoning="fixture subject",
    )


def build_topic(
    *,
    topic_id: str,
    title: str,
    subject_id: str,
    order_index: int,
    coverage_state: str,
    review_state: str,
    confidence: float = 0.7,
    evidence: list[CurriculumSourceEvidence] | None = None,
) -> CurriculumTopicNode:
    return CurriculumTopicNode(
        topic_id=topic_id,
        title=title,
        normalized_title=title.lower(),
        subject_id=subject_id,
        source_topic_candidate_id=topic_id,
        order_index=order_index,
        coverage_state=coverage_state,
        review_state=review_state,
        confidence=confidence,
        reasoning="fixture topic",
        evidence=evidence or [],
    )


def build_gap(
    *,
    gap_id: str,
    gap_type: str,
    target_id: str,
    target_title: str,
    severity: str = "medium",
    review_state: str = "needs_review",
) -> CurriculumGapReference:
    return CurriculumGapReference(
        gap_id=gap_id,
        source_gap_id=gap_id.replace("graph-gap:", ""),
        gap_type=gap_type,
        target_type="topic",
        target_id=target_id,
        target_title=target_title,
        severity=severity,
        reason="fixture gap",
        review_state=review_state,
    )


def build_redundancy(
    *,
    redundancy_id: str,
    redundancy_type: str,
    target_id: str,
    target_title: str,
    overlapping_document_ids: list[str],
    review_state: str = "ambiguous",
) -> CurriculumRedundancyReference:
    return CurriculumRedundancyReference(
        redundancy_id=redundancy_id,
        source_redundancy_id=redundancy_id.replace("graph-redundancy:", ""),
        redundancy_type=redundancy_type,
        target_type="topic",
        target_id=target_id,
        target_title=target_title,
        overlapping_document_ids=overlapping_document_ids,
        reason="fixture redundancy",
        review_state=review_state,
    )


def build_graph(
    *,
    graph_id: str,
    subjects: list[CurriculumSubjectNode],
    topics: list[CurriculumTopicNode],
    gaps: list[CurriculumGapReference] | None = None,
    redundancies: list[CurriculumRedundancyReference] | None = None,
    summary: CurriculumGraphSummary | None = None,
) -> CurriculumGraph:
    gaps = gaps or []
    redundancies = redundancies or []
    if summary is None:
        summary = CurriculumGraphSummary(
            subject_count=len(subjects),
            topic_count=len(topics),
            covered_topics_count=sum(1 for item in topics if item.coverage_state == "covered"),
            partially_covered_topics_count=sum(1 for item in topics if item.coverage_state == "partially_covered"),
            weakly_covered_topics_count=sum(1 for item in topics if item.coverage_state == "weakly_covered"),
            uncovered_topics_count=sum(1 for item in topics if item.coverage_state == "uncovered"),
            ambiguous_topics_count=sum(1 for item in topics if item.coverage_state == "ambiguous"),
            gap_count=len(gaps),
            redundancy_count=len(redundancies),
            ocr_required_count=sum(1 for item in gaps if item.gap_type == "ocr_required"),
            needs_review_count=sum(1 for item in topics if item.review_state in {"needs_review", "source_missing", "ocr_required", "ambiguous"}),
        )
    return CurriculumGraph(
        graph_id=graph_id,
        edital_id=f"edital:{graph_id}",
        alignment_id=f"alignment:edital:{graph_id}",
        user_id="user-a",
        subjects=subjects,
        topics=topics,
        subtopics=[],
        coverage_links=[],
        gaps=gaps,
        redundancies=redundancies,
        summary=summary,
        metadata={"fixture": True},
    )


def covered_topic_cycle_fixture() -> dict[str, object]:
    evidence = [build_evidence(evidence_id="e:covered", source_id="doc:ripeam", excerpt="RIPEAM com regras de governo.", matched_terms=["ripeam"], confidence=0.9)]
    topic = build_topic(topic_id="topic:ripeam", title="RIPEAM", subject_id="subject:nav", order_index=0, coverage_state="covered", review_state="ready_for_review", confidence=0.9, evidence=evidence)
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id])
    return {"graph": build_graph(graph_id="graph:covered", subjects=[subject], topics=[topic])}


def partial_topic_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:meteo", title="Meteorologia", subject_id="subject:nav", order_index=0, coverage_state="partially_covered", review_state="candidate", confidence=0.58, evidence=[build_evidence(evidence_id="e:partial", source_id="doc:meteo", excerpt="Ventos e cartas sinoticas.", matched_terms=["ventos"], confidence=0.58)])
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="partially_covered", review_state="candidate", confidence=0.58)
    return {"graph": build_graph(graph_id="graph:partial", subjects=[subject], topics=[topic])}


def weak_topic_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:weak", title="Comunicacoes", subject_id="subject:nav", order_index=0, coverage_state="weakly_covered", review_state="needs_review", confidence=0.31, evidence=[build_evidence(evidence_id="e:weak", source_id="doc:generic", excerpt="Comunicacao geral.", matched_terms=["comunicacao"], confidence=0.31)])
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="weakly_covered", review_state="needs_review", confidence=0.31)
    return {"graph": build_graph(graph_id="graph:weak", subjects=[subject], topics=[topic])}


def uncovered_topic_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:arte", title="Arte Naval", subject_id="subject:nav", order_index=0, coverage_state="uncovered", review_state="source_missing", confidence=0.2)
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="uncovered", review_state="source_missing", confidence=0.2)
    gap = build_gap(gap_id="graph-gap:arte", gap_type="uncovered_topic", target_id=topic.topic_id, target_title=topic.title, severity="high", review_state="source_missing")
    return {"graph": build_graph(graph_id="graph:uncovered", subjects=[subject], topics=[topic], gaps=[gap])}


def ocr_required_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:leg", title="Legislacao Maritima", subject_id="subject:nav", order_index=0, coverage_state="uncovered", review_state="ocr_required", confidence=0.25)
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="uncovered", review_state="ocr_required", confidence=0.25)
    gap = build_gap(gap_id="graph-gap:ocr", gap_type="ocr_required", target_id=topic.topic_id, target_title=topic.title, review_state="ocr_required")
    summary = CurriculumGraphSummary(subject_count=1, topic_count=1, uncovered_topics_count=1, gap_count=1, ocr_required_count=1, needs_review_count=1)
    return {"graph": build_graph(graph_id="graph:ocr", subjects=[subject], topics=[topic], gaps=[gap], summary=summary)}


def missing_document_text_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:navcost", title="Navegacao Costeira", subject_id="subject:nav", order_index=0, coverage_state="uncovered", review_state="source_missing", confidence=0.22)
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="uncovered", review_state="source_missing", confidence=0.22)
    gap = build_gap(gap_id="graph-gap:missing-text", gap_type="missing_document_text", target_id=topic.topic_id, target_title=topic.title, review_state="source_missing")
    return {"graph": build_graph(graph_id="graph:missing-text", subjects=[subject], topics=[topic], gaps=[gap])}


def ambiguous_topic_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:amb", title="Navegacao Costeira", subject_id="subject:nav", order_index=0, coverage_state="partially_covered", review_state="ambiguous", confidence=0.61, evidence=[build_evidence(evidence_id="e:amb", source_id="doc:nav-a", excerpt="Navegacao costeira e derrota.", matched_terms=["navegacao"], confidence=0.61)])
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="partially_covered", review_state="ambiguous", confidence=0.61)
    gap = build_gap(gap_id="graph-gap:amb", gap_type="ambiguous_reference", target_id=topic.topic_id, target_title=topic.title, review_state="ambiguous")
    return {"graph": build_graph(graph_id="graph:ambiguous", subjects=[subject], topics=[topic], gaps=[gap])}


def redundancy_cycle_fixture() -> dict[str, object]:
    topic = build_topic(topic_id="topic:red", title="Meteorologia", subject_id="subject:nav", order_index=0, coverage_state="covered", review_state="ambiguous", confidence=0.82, evidence=[build_evidence(evidence_id="e:red", source_id="doc:met-a", excerpt="Ventos e frentes.", matched_terms=["ventos", "frentes"], confidence=0.82)])
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[topic.topic_id], coverage_state="covered", review_state="ambiguous", confidence=0.82)
    redundancy = build_redundancy(redundancy_id="graph-redundancy:topic", redundancy_type="overlapping_topic_coverage", target_id=topic.topic_id, target_title=topic.title, overlapping_document_ids=["doc:met-a", "doc:met-b"])
    return {"graph": build_graph(graph_id="graph:redundancy", subjects=[subject], topics=[topic], redundancies=[redundancy])}


def gap_heavy_cycle_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:a", title="Arte Naval", subject_id="subject:nav", order_index=0, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
        build_topic(topic_id="topic:b", title="Meteorologia", subject_id="subject:nav", order_index=1, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
        build_topic(topic_id="topic:c", title="Legislacao Maritima", subject_id="subject:nav", order_index=2, coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
        build_topic(topic_id="topic:d", title="Navegacao Costeira", subject_id="subject:nav", order_index=3, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
    ]
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[item.topic_id for item in topics], coverage_state="uncovered", review_state="source_missing", confidence=0.2)
    gaps = [
        build_gap(gap_id="graph-gap:a", gap_type="missing_bibliography_material", target_id="topic:a", target_title="Arte Naval", review_state="source_missing"),
        build_gap(gap_id="graph-gap:b", gap_type="uncovered_topic", target_id="topic:b", target_title="Meteorologia", review_state="source_missing"),
        build_gap(gap_id="graph-gap:c", gap_type="ocr_required", target_id="topic:c", target_title="Legislacao Maritima", review_state="ocr_required"),
        build_gap(gap_id="graph-gap:d", gap_type="missing_document_text", target_id="topic:d", target_title="Navegacao Costeira", review_state="source_missing"),
    ]
    summary = CurriculumGraphSummary(subject_count=1, topic_count=4, uncovered_topics_count=4, gap_count=4, ocr_required_count=1, needs_review_count=4)
    return {"graph": build_graph(graph_id="graph:gap-heavy", subjects=[subject], topics=topics, gaps=gaps, summary=summary)}


def review_heavy_cycle_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:a", title="Meteorologia", subject_id="subject:nav", order_index=0, coverage_state="partially_covered", review_state="candidate", confidence=0.56),
        build_topic(topic_id="topic:b", title="Comunicacoes", subject_id="subject:nav", order_index=1, coverage_state="weakly_covered", review_state="needs_review", confidence=0.31),
        build_topic(topic_id="topic:c", title="Navegacao Costeira", subject_id="subject:nav", order_index=2, coverage_state="partially_covered", review_state="ambiguous", confidence=0.6),
    ]
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[item.topic_id for item in topics], coverage_state="partially_covered", review_state="candidate", confidence=0.5)
    gap = build_gap(gap_id="graph-gap:amb", gap_type="ambiguous_reference", target_id="topic:c", target_title="Navegacao Costeira", review_state="ambiguous")
    return {"graph": build_graph(graph_id="graph:review-heavy", subjects=[subject], topics=topics, gaps=[gap])}


def balanced_cycle_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:a", title="RIPEAM", subject_id="subject:nav", order_index=0, coverage_state="covered", review_state="ready_for_review", confidence=0.9),
        build_topic(topic_id="topic:b", title="Meteorologia", subject_id="subject:nav", order_index=1, coverage_state="covered", review_state="ready_for_review", confidence=0.84),
        build_topic(topic_id="topic:c", title="Comunicacoes", subject_id="subject:nav", order_index=2, coverage_state="partially_covered", review_state="candidate", confidence=0.55),
        build_topic(topic_id="topic:d", title="Cartas Nauticas", subject_id="subject:nav", order_index=3, coverage_state="covered", review_state="ready_for_review", confidence=0.82),
    ]
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[item.topic_id for item in topics], coverage_state="covered", review_state="ready_for_review", confidence=0.76)
    return {"graph": build_graph(graph_id="graph:balanced", subjects=[subject], topics=topics)}


def material_blocked_cycle_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:a", title="Arte Naval", subject_id="subject:nav", order_index=0, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
        build_topic(topic_id="topic:b", title="Legislacao Maritima", subject_id="subject:nav", order_index=1, coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
        build_topic(topic_id="topic:c", title="Manobra", subject_id="subject:nav", order_index=2, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
    ]
    subject = build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=[item.topic_id for item in topics], coverage_state="uncovered", review_state="source_missing", confidence=0.2)
    gaps = [
        build_gap(gap_id="graph-gap:a", gap_type="missing_bibliography_material", target_id="topic:a", target_title="Arte Naval", review_state="source_missing"),
        build_gap(gap_id="graph-gap:b", gap_type="ocr_required", target_id="topic:b", target_title="Legislacao Maritima", review_state="ocr_required"),
        build_gap(gap_id="graph-gap:c", gap_type="missing_document_text", target_id="topic:c", target_title="Manobra", review_state="source_missing"),
    ]
    summary = CurriculumGraphSummary(subject_count=1, topic_count=3, uncovered_topics_count=3, gap_count=3, ocr_required_count=1, needs_review_count=3)
    return {"graph": build_graph(graph_id="graph:material-blocked", subjects=[subject], topics=topics, gaps=gaps, summary=summary)}


def multi_subject_rotation_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:ripeam", title="RIPEAM", subject_id="subject:nav", order_index=0, coverage_state="covered", review_state="ready_for_review", confidence=0.9),
        build_topic(topic_id="topic:meteo", title="Meteorologia", subject_id="subject:meteo", order_index=1, coverage_state="partially_covered", review_state="candidate", confidence=0.56),
        build_topic(topic_id="topic:leg", title="Legislacao Maritima", subject_id="subject:leg", order_index=2, coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
    ]
    subjects = [
        build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=["topic:ripeam"], coverage_state="covered", review_state="ready_for_review", confidence=0.9),
        build_subject(subject_id="subject:meteo", title="Meteorologia", order_index=1, topic_ids=["topic:meteo"], coverage_state="partially_covered", review_state="candidate", confidence=0.56),
        build_subject(subject_id="subject:leg", title="Legislacao", order_index=2, topic_ids=["topic:leg"], coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
    ]
    gaps = [build_gap(gap_id="graph-gap:leg", gap_type="ocr_required", target_id="topic:leg", target_title="Legislacao Maritima", review_state="ocr_required")]
    summary = CurriculumGraphSummary(subject_count=3, topic_count=3, covered_topics_count=1, partially_covered_topics_count=1, uncovered_topics_count=1, gap_count=1, ocr_required_count=1, needs_review_count=2)
    return {"graph": build_graph(graph_id="graph:multi-subject", subjects=subjects, topics=topics, gaps=gaps, summary=summary)}


def maritime_praticagem_cycle_fixture() -> dict[str, object]:
    topics = [
        build_topic(topic_id="topic:arte", title="Arte Naval", subject_id="subject:praticagem", order_index=0, coverage_state="uncovered", review_state="source_missing", confidence=0.2),
        build_topic(topic_id="topic:ripeam", title="RIPEAM", subject_id="subject:praticagem", order_index=1, coverage_state="covered", review_state="ready_for_review", confidence=0.88),
        build_topic(topic_id="topic:manobra", title="Manobra", subject_id="subject:praticagem", order_index=2, coverage_state="weakly_covered", review_state="needs_review", confidence=0.33),
        build_topic(topic_id="topic:meteo", title="Meteorologia", subject_id="subject:praticagem", order_index=3, coverage_state="covered", review_state="ready_for_review", confidence=0.84),
        build_topic(topic_id="topic:leg", title="Legislacao Maritima", subject_id="subject:praticagem", order_index=4, coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
    ]
    subject = build_subject(subject_id="subject:praticagem", title="Praticagem", order_index=0, topic_ids=[item.topic_id for item in topics], coverage_state="partially_covered", review_state="candidate", confidence=0.49)
    gaps = [
        build_gap(gap_id="graph-gap:arte", gap_type="uncovered_topic", target_id="topic:arte", target_title="Arte Naval", review_state="source_missing"),
        build_gap(gap_id="graph-gap:leg", gap_type="ocr_required", target_id="topic:leg", target_title="Legislacao Maritima", review_state="ocr_required"),
    ]
    summary = CurriculumGraphSummary(subject_count=1, topic_count=5, covered_topics_count=2, weakly_covered_topics_count=1, uncovered_topics_count=2, gap_count=2, ocr_required_count=1, needs_review_count=3)
    return {"graph": build_graph(graph_id="graph:maritime-cycle", subjects=[subject], topics=topics, gaps=gaps, summary=summary)}


def mixed_complex_cycle_fixture() -> dict[str, object]:
    subjects = [
        build_subject(subject_id="subject:nav", title="Navegacao", order_index=0, topic_ids=["topic:ripeam", "topic:meteo", "topic:comms"], coverage_state="partially_covered", review_state="candidate", confidence=0.58),
        build_subject(subject_id="subject:leg", title="Legislacao", order_index=1, topic_ids=["topic:leg", "topic:nav"], coverage_state="uncovered", review_state="ambiguous", confidence=0.4),
    ]
    topics = [
        build_topic(topic_id="topic:ripeam", title="RIPEAM", subject_id="subject:nav", order_index=0, coverage_state="covered", review_state="ready_for_review", confidence=0.9),
        build_topic(topic_id="topic:meteo", title="Meteorologia", subject_id="subject:nav", order_index=1, coverage_state="partially_covered", review_state="candidate", confidence=0.56),
        build_topic(topic_id="topic:comms", title="Comunicacoes", subject_id="subject:nav", order_index=2, coverage_state="weakly_covered", review_state="needs_review", confidence=0.31),
        build_topic(topic_id="topic:leg", title="Legislacao Maritima", subject_id="subject:leg", order_index=3, coverage_state="uncovered", review_state="ocr_required", confidence=0.2),
        build_topic(topic_id="topic:nav", title="Navegacao Costeira", subject_id="subject:leg", order_index=4, coverage_state="partially_covered", review_state="ambiguous", confidence=0.61),
    ]
    gaps = [
        build_gap(gap_id="graph-gap:ocr", gap_type="ocr_required", target_id="topic:leg", target_title="Legislacao Maritima", review_state="ocr_required"),
        build_gap(gap_id="graph-gap:amb", gap_type="ambiguous_reference", target_id="topic:nav", target_title="Navegacao Costeira", review_state="ambiguous"),
        build_gap(gap_id="graph-gap:uncovered", gap_type="uncovered_topic", target_id="topic:comms", target_title="Comunicacoes", review_state="needs_review"),
    ]
    redundancies = [build_redundancy(redundancy_id="graph-redundancy:nav", redundancy_type="overlapping_topic_coverage", target_id="topic:nav", target_title="Navegacao Costeira", overlapping_document_ids=["doc:nav-a", "doc:nav-b"])]
    summary = CurriculumGraphSummary(subject_count=2, topic_count=5, covered_topics_count=1, partially_covered_topics_count=2, weakly_covered_topics_count=1, uncovered_topics_count=1, gap_count=3, redundancy_count=1, ocr_required_count=1, needs_review_count=4)
    return {"graph": build_graph(graph_id="graph:mixed-complex", subjects=subjects, topics=topics, gaps=gaps, redundancies=redundancies, summary=summary)}


def empty_or_insufficient_graph_fixture() -> dict[str, object]:
    return {"graph": build_graph(graph_id="graph:empty", subjects=[], topics=[])}


ALL_STUDY_CYCLE_FIXTURES = [
    covered_topic_cycle_fixture,
    partial_topic_cycle_fixture,
    weak_topic_cycle_fixture,
    uncovered_topic_cycle_fixture,
    ocr_required_cycle_fixture,
    missing_document_text_cycle_fixture,
    ambiguous_topic_cycle_fixture,
    redundancy_cycle_fixture,
    gap_heavy_cycle_fixture,
    review_heavy_cycle_fixture,
    balanced_cycle_fixture,
    material_blocked_cycle_fixture,
    multi_subject_rotation_fixture,
    maritime_praticagem_cycle_fixture,
    mixed_complex_cycle_fixture,
    empty_or_insufficient_graph_fixture,
]
