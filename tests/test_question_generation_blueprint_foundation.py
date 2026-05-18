import json

from app.domain.models import (
    CurriculumCoverageLink,
    CurriculumGraph,
    CurriculumGraphSummary,
    CurriculumSourceEvidence,
    CurriculumSubjectNode,
    CurriculumTopicNode,
    QuestionGenerationBlueprintSet,
    SimuladoBlueprint,
    SimuladoBlueprintRationale,
    SimuladoQuestionSlot,
    SimuladoBlueprintWarning,
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


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    blueprint_service = QuestionGenerationBlueprintService(repository)
    return repository, material_service, pipeline_service, blueprint_service


def upload_and_process_markdown(
    material_service: MaterialService,
    pipeline_service: DocumentPipelineService,
    *,
    user_id: str,
    filename: str,
    text: str,
):
    uploaded = material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type="text/markdown",
        payload=text.encode("utf-8"),
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id=user_id)
    return uploaded


def persist_graph(repository: JsonStudyRepository, graph: CurriculumGraph, *, user_id: str) -> CurriculumGraph:
    persisted = graph.model_copy(update={"user_id": user_id})
    repository.save_curriculum_graph(persisted, user_id=user_id)
    return persisted


def persist_simulado(
    repository: JsonStudyRepository,
    *,
    user_id: str,
    graph_id: str,
    profile_id: str | None,
    format_type: str,
    question_slots: list[SimuladoQuestionSlot],
    warnings: list[SimuladoBlueprintWarning] | None = None,
    exam_board: str | None = None,
    exam_family: str | None = None,
    artifact_key: str | None = None,
) -> SimuladoBlueprint:
    profile_suffix = artifact_key or profile_id or "unknown"
    blueprint = SimuladoBlueprint(
        blueprint_id=f"simulado:{graph_id}:{profile_suffix}",
        graph_id=graph_id,
        cycle_id=f"cycle:{graph_id}:{profile_suffix}",
        exam_profile_id=profile_id,
        user_id=user_id,
        exam_board=exam_board,
        exam_family=exam_family,
        format_type=format_type,
        question_slots=question_slots,
        warnings=warnings or [],
        rationale=SimuladoBlueprintRationale(
            summary="fixture simulado blueprint",
            source_graph_id=graph_id,
            source_cycle_id=f"cycle:{graph_id}",
            source_exam_profile_id=profile_id,
            confidence=0.8,
        ),
        metadata={"fixture": True},
    )
    repository.save_simulado_blueprint(blueprint, user_id=user_id)
    return blueprint


def ready_graph_fixture(repository: JsonStudyRepository, material_service: MaterialService, pipeline_service: DocumentPipelineService):
    uploaded = upload_and_process_markdown(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="ripeam.md",
        text=(
            "# RIPEAM\n\n"
            "As regras de governo e rumo exigem leitura tecnica, cruzamento de definicoes e "
            "precisao terminologica para aplicacao em prova de navegacao."
        ),
    )
    chunks = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")
    sections = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")
    assert chunks
    assert sections
    chunk = chunks[0]
    section = sections[0]
    evidence = CurriculumSourceEvidence(
        evidence_id="e:ripeam:chunk",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=uploaded.metadata.document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam", "governo", "rumo"],
        confidence=0.92,
        reasoning="fixture source evidence",
    )
    topic = CurriculumTopicNode(
        topic_id="topic:ripeam",
        title="RIPEAM",
        normalized_title="ripeam",
        subject_id="subject:navegacao",
        source_topic_candidate_id="topic:ripeam",
        order_index=0,
        coverage_state="covered",
        review_state="ready_for_review",
        confidence=0.92,
        reasoning="fixture topic",
        evidence=[evidence],
    )
    graph = CurriculumGraph(
        graph_id="graph:qgb-ready",
        edital_id="edital:qgb-ready",
        alignment_id="alignment:qgb-ready",
        user_id="user-a",
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
                link_id="link:ripeam",
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
        summary=CurriculumGraphSummary(
            subject_count=1,
            topic_count=1,
            covered_topics_count=1,
        ),
        metadata={"fixture": True},
    )
    return persist_graph(repository, graph, user_id="user-a"), uploaded, chunk


def build_slot(
    *,
    topic_id: str,
    format_type: str,
    readiness_state: str,
    source_evidence_ids: list[str] | None = None,
    blocked_by_gap_ids: list[str] | None = None,
) -> SimuladoQuestionSlot:
    return SimuladoQuestionSlot(
        slot_id=f"question-slot:{topic_id}",
        section_id="section:primary",
        order_index=0,
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


def test_question_generation_blueprint_handles_missing_simulado_and_no_slots(tmp_path):
    repository, _, _, service = create_services(tmp_path)

    assert service.build_blueprint_set("simulado:missing", user_id="user-a") is None
    assert repository.list_user_question_generation_blueprints(user_id="user-a") == []

    empty_graph = persist_graph(
        repository,
        CurriculumGraph(
            graph_id="graph:qgb-empty",
            edital_id="edital:qgb-empty",
            alignment_id="alignment:qgb-empty",
            subjects=[],
            topics=[],
            summary=CurriculumGraphSummary(),
        ),
        user_id="user-a",
    )
    simulado = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=empty_graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[],
        exam_board="FGV",
    )

    result = service.build_blueprint_set(simulado.blueprint_id, user_id="user-a")

    assert isinstance(result, QuestionGenerationBlueprintSet)
    assert result.readiness_state == "no_slots"
    assert result.total_slots == 0
    assert result.ready_slots == 0
    assert result.no_question_text_generated is True


def test_question_generation_blueprint_maps_ready_slot_with_source_evidence_and_cebraspe_hints(tmp_path):
    repository, material_service, pipeline_service, service = create_services(tmp_path)
    graph, _, chunk = ready_graph_fixture(repository, material_service, pipeline_service)
    simulado = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=graph.graph_id,
        profile_id="exam-profile:cebraspe",
        format_type="true_false",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam",
                format_type="true_false",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:chunk"],
            )
        ],
        exam_board="CEBRASPE",
    )

    result = service.build_blueprint_set(simulado.blueprint_id, user_id="user-a")
    slot = result.slot_blueprints[0]
    dumped = result.model_dump(mode="json")
    dumped_json = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = collect_keys(dumped)

    assert result.readiness_state == "ready_for_review"
    assert result.ready_slots == 1
    assert slot.readiness_state == "ready_for_draft"
    assert slot.question_kind == "assertion_judgement"
    assert "single_assertion" in slot.style_hints
    assert slot.source_evidence
    assert slot.source_evidence[0].document_id == chunk.document_id
    assert slot.source_evidence[0].chunk_id == chunk.chunk_id
    assert slot.source_evidence[0].safe_snippet is not None
    assert len(slot.source_evidence[0].safe_snippet) <= 240
    assert any(item.constraint_type == "must_use_source_evidence" for item in slot.constraints)
    assert result.no_question_text_generated is True
    assert result.no_alternatives_generated is True
    assert result.no_distractors_generated is True
    assert result.no_answer_key_generated is True
    assert result.no_explanations_generated is True
    for forbidden in (
        "question_text",
        "final_question_text",
        "stem",
        "statement",
        "options",
        "alternatives",
        "distractors",
        "answer",
        "answer_key",
        "correct_answer",
        "gabarito",
        "explanation",
        "correction",
    ):
        assert forbidden not in dumped_keys
    assert "no_final_question_text_in_this_pass" in dumped_json


def test_question_generation_blueprint_marks_blockers_and_review_states_conservatively(tmp_path):
    repository, _, _, service = create_services(tmp_path)
    scenarios = [
        (
            ocr_required_cycle_fixture()["graph"],
            build_slot(
                topic_id="topic:leg",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ocr",
                blocked_by_gap_ids=["graph-gap:ocr"],
            ),
            "exam-profile:marinha-pscpp",
            "blocked_by_ocr",
        ),
        (
            missing_document_text_cycle_fixture()["graph"],
            build_slot(
                topic_id="topic:navcost",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_material_gap",
                blocked_by_gap_ids=["graph-gap:missing-text"],
            ),
            "exam-profile:fgv",
            "blocked_by_material_gap",
        ),
        (
            uncovered_topic_cycle_fixture()["graph"],
            build_slot(
                topic_id="topic:arte",
                format_type="multiple_choice_5",
                readiness_state="insufficient_source_evidence",
                blocked_by_gap_ids=["graph-gap:arte"],
            ),
            "exam-profile:fgv",
            "blocked_by_insufficient_coverage",
        ),
        (
            ambiguous_topic_cycle_fixture()["graph"],
            build_slot(
                topic_id="topic:amb",
                format_type="multiple_choice_5",
                readiness_state="blocked_by_ambiguity",
                source_evidence_ids=["e:amb"],
                blocked_by_gap_ids=["graph-gap:amb"],
            ),
            "exam-profile:fgv",
            "needs_review",
        ),
    ]

    for graph, slot, profile_id, expected in scenarios:
        persisted_graph = persist_graph(repository, graph, user_id="user-a")
        simulado = persist_simulado(
            repository,
            user_id="user-a",
            graph_id=persisted_graph.graph_id,
            profile_id=profile_id,
            format_type=slot.format_type,
            question_slots=[slot],
            exam_family="PSCPP" if profile_id == "exam-profile:marinha-pscpp" else None,
            artifact_key=f"{profile_id}:{slot.target_topic_id}",
        )
        result = service.build_blueprint_set(simulado.blueprint_id, user_id="user-a")
        assert result.slot_blueprints[0].readiness_state == expected


def test_question_generation_blueprint_uses_style_hints_for_fgv_pscpp_and_unsupported_formats(tmp_path):
    repository, material_service, pipeline_service, service = create_services(tmp_path)
    graph, _, _ = ready_graph_fixture(repository, material_service, pipeline_service)

    fgv = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:chunk"],
            )
        ],
        exam_board="FGV",
        artifact_key="fgv-ready",
    )
    pscpp = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=graph.graph_id,
        profile_id="exam-profile:marinha-pscpp",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:chunk"],
            )
        ],
        exam_family="PSCPP",
        artifact_key="pscpp-ready",
    )
    unsupported = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="discursive",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam",
                format_type="discursive",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:chunk"],
            )
        ],
        warnings=[SimuladoBlueprintWarning(code="format_requires_confirmation", message="fixture warning")],
        artifact_key="fgv-unsupported",
    )

    fgv_result = service.build_blueprint_set(fgv.blueprint_id, user_id="user-a")
    pscpp_result = service.build_blueprint_set(pscpp.blueprint_id, user_id="user-a")
    unsupported_result = service.build_blueprint_set(unsupported.blueprint_id, user_id="user-a")

    assert fgv_result.slot_blueprints[0].question_kind == "case_based_multiple_choice"
    assert "contextualized_command" in fgv_result.slot_blueprints[0].style_hints
    assert pscpp_result.slot_blueprints[0].question_kind == "technical_maritime_scenario"
    assert "allow_english_maritime_terms" in pscpp_result.slot_blueprints[0].style_hints
    assert unsupported_result.slot_blueprints[0].readiness_state == "blocked_by_unsupported_format"


def test_question_generation_blueprint_persistence_is_user_scoped_and_idempotent(tmp_path):
    repository, material_service, pipeline_service, service = create_services(tmp_path)
    graph, _, _ = ready_graph_fixture(repository, material_service, pipeline_service)
    simulado = persist_simulado(
        repository,
        user_id="user-a",
        graph_id=graph.graph_id,
        profile_id="exam-profile:fgv",
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:ripeam",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
                source_evidence_ids=["e:ripeam:chunk"],
            )
        ],
        exam_board="FGV",
    )

    first = service.build_blueprint_set(simulado.blueprint_id, user_id="user-a")
    second = service.build_blueprint_set(simulado.blueprint_id, user_id="user-a")
    by_source = repository.get_question_generation_blueprint(simulado.blueprint_id, user_id="user-a")
    by_id = repository.get_question_generation_blueprint_by_id(first.blueprint_set_id, user_id="user-a")
    listed = repository.list_user_question_generation_blueprints(user_id="user-a")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert repository.get_question_generation_blueprint(simulado.blueprint_id, user_id="user-b") is None
