from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    CurriculumCoverageLink,
    CurriculumGapReference,
    CurriculumGraph,
    CurriculumGraphSummary,
    CurriculumSourceEvidence,
    CurriculumSubjectNode,
    CurriculumTopicNode,
    DocumentChunk,
    SimuladoBlueprint,
    SimuladoBlueprintRationale,
    SimuladoBlueprintWarning,
    SimuladoQuestionSlot,
    UploadedMaterial,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService
from app.services.question_generation_blueprint import QuestionGenerationBlueprintService
from tests.fixtures.study_cycle_graphs import (
    ambiguous_topic_cycle_fixture,
    missing_document_text_cycle_fixture,
    ocr_required_cycle_fixture,
    uncovered_topic_cycle_fixture,
)


@dataclass
class QuestionGenerationFixtureContext:
    repository: JsonStudyRepository
    material_service: MaterialService
    pipeline_service: DocumentPipelineService
    blueprint_service: QuestionGenerationBlueprintService
    user_id: str = "user-a"


@dataclass
class QuestionGenerationFixture:
    context: QuestionGenerationFixtureContext
    simulado_blueprint: SimuladoBlueprint
    graph: CurriculumGraph
    expected_slot_state: str | None = None
    expected_set_state: str | None = None
    uploaded_material: UploadedMaterial | None = None
    chunk: DocumentChunk | None = None


def create_context(tmp_path, *, user_id: str = "user-a") -> QuestionGenerationFixtureContext:
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    return QuestionGenerationFixtureContext(
        repository=repository,
        material_service=MaterialService(repository, storage_root=storage_root),
        pipeline_service=DocumentPipelineService(repository, storage_root=storage_root),
        blueprint_service=QuestionGenerationBlueprintService(repository),
        user_id=user_id,
    )


def upload_and_process_markdown(
    context: QuestionGenerationFixtureContext,
    *,
    filename: str,
    text: str,
) -> UploadedMaterial:
    uploaded = context.material_service.register_upload(
        user_id=context.user_id,
        original_filename=filename,
        content_type="text/markdown",
        payload=text.encode("utf-8"),
    )
    context.pipeline_service.process_document(uploaded.metadata.document_id, user_id=context.user_id)
    return uploaded


def collect_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(collect_keys(item))
        return keys
    return set()


def persist_graph(
    context: QuestionGenerationFixtureContext,
    graph: CurriculumGraph,
) -> CurriculumGraph:
    persisted = graph.model_copy(update={"user_id": context.user_id})
    context.repository.save_curriculum_graph(persisted, user_id=context.user_id)
    return persisted


def build_slot(
    *,
    topic_id: str,
    format_type: str,
    readiness_state: str,
    source_evidence_ids: list[str] | None = None,
    blocked_by_gap_ids: list[str] | None = None,
    order_index: int = 0,
) -> SimuladoQuestionSlot:
    return SimuladoQuestionSlot(
        slot_id=f"question-slot:{topic_id}:{order_index}",
        section_id="section:primary",
        order_index=order_index,
        target_subject_id="subject:navegacao",
        target_topic_id=topic_id,
        format_type=format_type,
        cognitive_demand="high",
        difficulty_hint="medium",
        generation_style="case_based",
        source_evidence_ids=source_evidence_ids or [],
        required_coverage_state="covered",
        blocked_by_gap_ids=blocked_by_gap_ids or [],
        readiness_state=readiness_state,
        confidence=0.8,
        reasoning="fixture slot",
    )


def persist_simulado(
    context: QuestionGenerationFixtureContext,
    *,
    graph_id: str,
    profile_id: str | None,
    format_type: str,
    question_slots: list[SimuladoQuestionSlot],
    warnings: list[SimuladoBlueprintWarning] | None = None,
    exam_board: str | None = None,
    exam_family: str | None = None,
    artifact_key: str | None = None,
) -> SimuladoBlueprint:
    suffix = artifact_key or profile_id or "unknown"
    simulado = SimuladoBlueprint(
        blueprint_id=f"simulado:{graph_id}:{suffix}",
        graph_id=graph_id,
        cycle_id=f"cycle:{graph_id}:{suffix}",
        exam_profile_id=profile_id,
        user_id=context.user_id,
        exam_board=exam_board,
        exam_family=exam_family,
        format_type=format_type,
        question_slots=question_slots,
        warnings=warnings or [],
        rationale=SimuladoBlueprintRationale(
            summary="fixture simulado blueprint",
            source_graph_id=graph_id,
            source_cycle_id=f"cycle:{graph_id}:{suffix}",
            source_exam_profile_id=profile_id,
            confidence=0.8,
        ),
        metadata={"fixture": True},
    )
    context.repository.save_simulado_blueprint(simulado, user_id=context.user_id)
    return simulado


def _covered_graph_with_material(
    context: QuestionGenerationFixtureContext,
    *,
    graph_id: str,
    topic_id: str,
    filename: str,
    text: str,
    evidence_id: str,
) -> tuple[CurriculumGraph, UploadedMaterial, DocumentChunk]:
    uploaded = upload_and_process_markdown(context, filename=filename, text=text)
    chunks = context.repository.list_document_chunks(uploaded.metadata.document_id, user_id=context.user_id)
    sections = context.repository.list_document_sections(uploaded.metadata.document_id, user_id=context.user_id)
    chunk = chunks[0]
    section = sections[0]
    evidence = CurriculumSourceEvidence(
        evidence_id=evidence_id,
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=uploaded.metadata.document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam", "navegacao", "governo"],
        confidence=0.92,
        reasoning="fixture source evidence",
    )
    topic = CurriculumTopicNode(
        topic_id=topic_id,
        title="RIPEAM",
        normalized_title="ripeam",
        subject_id="subject:navegacao",
        source_topic_candidate_id=topic_id,
        order_index=0,
        coverage_state="covered",
        review_state="ready_for_review",
        confidence=0.92,
        reasoning="fixture topic",
        evidence=[evidence],
    )
    graph = CurriculumGraph(
        graph_id=graph_id,
        edital_id=f"edital:{graph_id}",
        alignment_id=f"alignment:{graph_id}",
        user_id=context.user_id,
        subjects=[
            CurriculumSubjectNode(
                subject_id="subject:navegacao",
                title="Navegacao",
                normalized_title="navegacao",
                order_index=0,
                topic_ids=[topic.topic_id],
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.9,
                reasoning="fixture subject",
            )
        ],
        topics=[topic],
        coverage_links=[
            CurriculumCoverageLink(
                link_id=f"link:{topic_id}",
                target_type="topic",
                target_id=topic.topic_id,
                document_ids=[uploaded.metadata.document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="covered",
                confidence=0.92,
                reasoning="fixture link",
                evidence=[evidence],
            )
        ],
        summary=CurriculumGraphSummary(subject_count=1, topic_count=1, covered_topics_count=1),
        metadata={"fixture": True},
    )
    return persist_graph(context, graph), uploaded, chunk


def ready_source_grounded_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, uploaded, chunk = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-ready-fixture",
        topic_id="topic:ripeam-ready",
        filename="ripeam_ready.md",
        text=(
            "# RIPEAM\n\nAs regras de governo e rumo exigem leitura tecnica, cruzamento de definicoes "
            "e precisao terminologica para aplicacao segura em prova de navegacao."
        ),
        evidence_id="e:ripeam:ready",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-ready",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:ready"],
            )
        ],
        exam_board="FGV",
        artifact_key="ready-source-grounded",
    )
    return QuestionGenerationFixture(context, simulado, graph, "ready_for_draft", "ready_for_review", uploaded, chunk)


def missing_source_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(
        context,
        CurriculumGraph(
            graph_id="graph:qgb-missing-source",
            edital_id="edital:qgb-missing-source",
            alignment_id="alignment:qgb-missing-source",
            user_id=context.user_id,
            subjects=[
                CurriculumSubjectNode(
                    subject_id="subject:navegacao",
                    title="Navegacao",
                    normalized_title="navegacao",
                    topic_ids=["topic:missing-source"],
                    coverage_state="covered",
                    review_state="ready_for_review",
                    confidence=0.7,
                    reasoning="fixture subject",
                )
            ],
            topics=[
                CurriculumTopicNode(
                    topic_id="topic:missing-source",
                    title="Balizamento",
                    normalized_title="balizamento",
                    subject_id="subject:navegacao",
                    source_topic_candidate_id="topic:missing-source",
                    coverage_state="covered",
                    review_state="ready_for_review",
                    confidence=0.7,
                    reasoning="fixture topic",
                )
            ],
            summary=CurriculumGraphSummary(subject_count=1, topic_count=1, covered_topics_count=1),
        ),
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:missing-source",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
            )
        ],
        artifact_key="missing-source",
    )
    return QuestionGenerationFixture(context, simulado, graph, "blocked_by_missing_source", "blocked")


def ocr_required_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(context, ocr_required_cycle_fixture()["graph"])
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:marinha-pscpp",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:leg",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ocr",
                blocked_by_gap_ids=["graph-gap:ocr"],
            )
        ],
        exam_family="PSCPP",
        artifact_key="ocr-required",
    )
    return QuestionGenerationFixture(context, simulado, graph, "blocked_by_ocr", "blocked")


def material_gap_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(context, missing_document_text_cycle_fixture()["graph"])
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:navcost",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_material_gap",
                blocked_by_gap_ids=["graph-gap:missing-text"],
            )
        ],
        artifact_key="material-gap",
    )
    return QuestionGenerationFixture(context, simulado, graph, "blocked_by_material_gap", "blocked")


def missing_document_text_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    return material_gap_slot_fixture(tmp_path)


def insufficient_coverage_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(context, uncovered_topic_cycle_fixture()["graph"])
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:arte",
                format_type="multiple_choice_5",
                readiness_state="insufficient_source_evidence",
                blocked_by_gap_ids=["graph-gap:arte"],
            )
        ],
        artifact_key="insufficient-coverage",
    )
    return QuestionGenerationFixture(context, simulado, graph, "blocked_by_insufficient_coverage", "blocked")


def ambiguous_coverage_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(context, ambiguous_topic_cycle_fixture()["graph"])
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:amb",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ambiguity",
                source_evidence_ids=["e:amb"],
                blocked_by_gap_ids=["graph-gap:amb"],
            )
        ],
        artifact_key="ambiguous-coverage",
    )
    return QuestionGenerationFixture(context, simulado, graph, "needs_review", "needs_review")


def ambiguous_profile_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, _, _ = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-ambiguous-profile",
        topic_id="topic:ripeam-ambiguous-profile",
        filename="ripeam_ambiguous_profile.md",
        text="RIPEAM com base normativa e mapeamento tecnico suficiente para fixture controlada.",
        evidence_id="e:ripeam:ambiguous-profile",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-ambiguous-profile",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:ambiguous-profile"],
            )
        ],
        warnings=[SimuladoBlueprintWarning(code="format_requires_confirmation", message="fixture warning")],
        exam_board="FGV",
        artifact_key="ambiguous-profile",
    )
    return QuestionGenerationFixture(context, simulado, graph, "needs_review", "needs_review")


def unsupported_format_slot_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, _, _ = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-unsupported",
        topic_id="topic:ripeam-unsupported",
        filename="ripeam_unsupported.md",
        text="RIPEAM com evidencias suficientes, mas formato propositalmente nao suportado.",
        evidence_id="e:ripeam:unsupported",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="discursive",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-unsupported",
                format_type="discursive",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:unsupported"],
            )
        ],
        warnings=[SimuladoBlueprintWarning(code="format_requires_confirmation", message="fixture warning")],
        artifact_key="unsupported-format",
    )
    return QuestionGenerationFixture(context, simulado, graph, "blocked_by_unsupported_format", "blocked")


def cebraspe_true_false_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, uploaded, chunk = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-cebraspe",
        topic_id="topic:ripeam-cebraspe",
        filename="ripeam_cebraspe.md",
        text="RIPEAM e navegacao com foco em precisao terminologica para julgamento de afirmacoes tecnicas.",
        evidence_id="e:ripeam:cebraspe",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:cebraspe",
        format_type="true_false",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-cebraspe",
                format_type="true_false",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:cebraspe"],
            )
        ],
        exam_board="CEBRASPE",
        artifact_key="cebraspe-true-false",
    )
    return QuestionGenerationFixture(context, simulado, graph, "ready_for_draft", "ready_for_review", uploaded, chunk)


def fgv_multiple_choice_fixture(tmp_path) -> QuestionGenerationFixture:
    return ready_source_grounded_slot_fixture(tmp_path)


def pscpp_maritime_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, uploaded, chunk = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-pscpp",
        topic_id="topic:ripeam-pscpp",
        filename="ripeam_pscpp.md",
        text="RIPEAM, manobra, governo e termos tecnicos maritimos para contexto operacional de praticagem.",
        evidence_id="e:ripeam:pscpp",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:marinha-pscpp",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-pscpp",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:pscpp"],
            )
        ],
        exam_family="PSCPP",
        artifact_key="pscpp-maritime",
    )
    return QuestionGenerationFixture(context, simulado, graph, "ready_for_draft", "ready_for_review", uploaded, chunk)


def long_chunk_snippet_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph, uploaded, chunk = _covered_graph_with_material(
        context,
        graph_id="graph:qgb-long-snippet",
        topic_id="topic:ripeam-long-snippet",
        filename="ripeam_long_snippet.md",
        text=(
            "# RIPEAM\n\n"
            + " ".join(["conteudo-tecnico"] * 50)
            + " /Users/should/not/appear/in/snippet "
            + " ".join(["navegacao"] * 30)
        ),
        evidence_id="e:ripeam:long-snippet",
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam-long-snippet",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:long-snippet"],
            )
        ],
        artifact_key="long-snippet",
    )
    return QuestionGenerationFixture(context, simulado, graph, "ready_for_draft", "ready_for_review", uploaded, chunk)


def no_slots_blueprint_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    graph = persist_graph(
        context,
        CurriculumGraph(
            graph_id="graph:qgb-no-slots",
            edital_id="edital:qgb-no-slots",
            alignment_id="alignment:qgb-no-slots",
            user_id=context.user_id,
            summary=CurriculumGraphSummary(),
        ),
    )
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[],
        artifact_key="no-slots",
    )
    return QuestionGenerationFixture(context, simulado, graph, None, "no_slots")


def mixed_readiness_blueprint_fixture(tmp_path) -> QuestionGenerationFixture:
    context = create_context(tmp_path)
    uploaded = upload_and_process_markdown(
        context,
        filename="ripeam_mixed.md",
        text="RIPEAM e navegacao com texto suficiente para um slot pronto e contexto geral de cobertura.",
    )
    chunk = context.repository.list_document_chunks(uploaded.metadata.document_id, user_id=context.user_id)[0]
    section = context.repository.list_document_sections(uploaded.metadata.document_id, user_id=context.user_id)[0]
    ready_evidence = CurriculumSourceEvidence(
        evidence_id="e:mixed:ready",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=uploaded.metadata.document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam"],
        confidence=0.9,
    )
    amb_evidence = CurriculumSourceEvidence(
        evidence_id="e:mixed:amb",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=uploaded.metadata.document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["navegacao"],
        confidence=0.62,
    )
    graph = CurriculumGraph(
        graph_id="graph:qgb-mixed",
        edital_id="edital:qgb-mixed",
        alignment_id="alignment:qgb-mixed",
        user_id=context.user_id,
        subjects=[
            CurriculumSubjectNode(
                subject_id="subject:navegacao",
                title="Navegacao",
                normalized_title="navegacao",
                topic_ids=[
                    "topic:mixed-ready",
                    "topic:mixed-ocr",
                    "topic:mixed-missing",
                    "topic:mixed-ambiguous",
                ],
                coverage_state="partially_covered",
                review_state="candidate",
                confidence=0.7,
                reasoning="fixture subject",
            )
        ],
        topics=[
            CurriculumTopicNode(
                topic_id="topic:mixed-ready",
                title="RIPEAM",
                normalized_title="ripeam",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:mixed-ready",
                order_index=0,
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.9,
                evidence=[ready_evidence],
            ),
            CurriculumTopicNode(
                topic_id="topic:mixed-ocr",
                title="Legislacao Maritima",
                normalized_title="legislacao maritima",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:mixed-ocr",
                order_index=1,
                coverage_state="uncovered",
                review_state="ocr_required",
                confidence=0.25,
            ),
            CurriculumTopicNode(
                topic_id="topic:mixed-missing",
                title="Meteorologia",
                normalized_title="meteorologia",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:mixed-missing",
                order_index=2,
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.4,
            ),
            CurriculumTopicNode(
                topic_id="topic:mixed-ambiguous",
                title="Navegacao Costeira",
                normalized_title="navegacao costeira",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:mixed-ambiguous",
                order_index=3,
                coverage_state="partially_covered",
                review_state="ambiguous",
                confidence=0.62,
                evidence=[amb_evidence],
            ),
        ],
        coverage_links=[
            CurriculumCoverageLink(
                link_id="link:mixed-ready",
                target_type="topic",
                target_id="topic:mixed-ready",
                document_ids=[uploaded.metadata.document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="covered",
                confidence=0.9,
                evidence=[ready_evidence],
            ),
            CurriculumCoverageLink(
                link_id="link:mixed-amb",
                target_type="topic",
                target_id="topic:mixed-ambiguous",
                document_ids=[uploaded.metadata.document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="partially_covered",
                confidence=0.62,
                evidence=[amb_evidence],
            ),
        ],
        gaps=[
            CurriculumGapReference(
                gap_id="graph-gap:mixed-ocr",
                source_gap_id="mixed-ocr",
                gap_type="ocr_required",
                target_type="topic",
                target_id="topic:mixed-ocr",
                target_title="Legislacao Maritima",
                review_state="ocr_required",
            ),
            CurriculumGapReference(
                gap_id="graph-gap:mixed-missing",
                source_gap_id="mixed-missing",
                gap_type="missing_document_text",
                target_type="topic",
                target_id="topic:mixed-missing",
                target_title="Meteorologia",
                review_state="source_missing",
            ),
            CurriculumGapReference(
                gap_id="graph-gap:mixed-amb",
                source_gap_id="mixed-amb",
                gap_type="ambiguous_reference",
                target_type="topic",
                target_id="topic:mixed-ambiguous",
                target_title="Navegacao Costeira",
                review_state="ambiguous",
            ),
        ],
        summary=CurriculumGraphSummary(
            subject_count=1,
            topic_count=4,
            covered_topics_count=2,
            partially_covered_topics_count=1,
            uncovered_topics_count=1,
            ocr_required_count=1,
            needs_review_count=2,
            gap_count=3,
        ),
    )
    graph = persist_graph(context, graph)
    simulado = persist_simulado(
        context,
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:mixed-ready",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:mixed:ready"],
                order_index=0,
            ),
            build_slot(
                topic_id="topic:mixed-ocr",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ocr",
                blocked_by_gap_ids=["graph-gap:mixed-ocr"],
                order_index=1,
            ),
            build_slot(
                topic_id="topic:mixed-missing",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_material_gap",
                blocked_by_gap_ids=["graph-gap:mixed-missing"],
                order_index=2,
            ),
            build_slot(
                topic_id="topic:mixed-ambiguous",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ambiguity",
                source_evidence_ids=["e:mixed:amb"],
                blocked_by_gap_ids=["graph-gap:mixed-amb"],
                order_index=3,
            ),
        ],
        exam_board="FGV",
        artifact_key="mixed-readiness",
    )
    return QuestionGenerationFixture(context, simulado, graph, None, "partially_ready", uploaded, chunk)


def no_final_content_safety_fixture(tmp_path) -> QuestionGenerationFixture:
    return ready_source_grounded_slot_fixture(tmp_path)
