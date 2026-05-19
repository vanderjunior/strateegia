import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.domain.models import (
    CurriculumCoverageLink,
    CurriculumGraph,
    CurriculumGraphSummary,
    CurriculumSourceEvidence,
    CurriculumSubjectNode,
    CurriculumTopicNode,
    SimuladoBlueprint,
    SimuladoBlueprintRationale,
    SimuladoQuestionSlot,
)
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.question_generation_blueprints import (
    ambiguous_coverage_slot_fixture,
    ambiguous_profile_slot_fixture,
    cebraspe_true_false_fixture,
    collect_keys,
    fgv_multiple_choice_fixture,
    insufficient_coverage_slot_fixture,
    long_chunk_snippet_fixture,
    material_gap_slot_fixture,
    missing_document_text_slot_fixture,
    missing_source_slot_fixture,
    mixed_readiness_blueprint_fixture,
    no_final_content_safety_fixture,
    no_slots_blueprint_fixture,
    ocr_required_slot_fixture,
    pscpp_maritime_fixture,
    ready_source_grounded_slot_fixture,
    unsupported_format_slot_fixture,
)


FORBIDDEN_FINAL_KEYS = {
    "question_text",
    "final_question_text",
    "stem",
    "final_stem",
    "statement",
    "final_statement",
    "options",
    "alternatives",
    "distractors",
    "answer",
    "answer_key",
    "correct_answer",
    "gabarito",
    "explanation",
    "final_explanation",
    "correction",
    "scoring_result",
}


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return login.json()["user"]["user_id"]


def assert_no_leakage(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/uploads/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped


def upload_and_process_markdown(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(text.encode("utf-8")), "text/markdown")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["metadata"]["document_id"]
    processed = client.post(f"/api/materials/{document_id}/process")
    assert processed.status_code == 200
    return document_id


def test_question_generation_blueprint_fixture_sanity(tmp_path):
    fixtures = [
        ready_source_grounded_slot_fixture(tmp_path / "ready"),
        missing_source_slot_fixture(tmp_path / "missing"),
        ocr_required_slot_fixture(tmp_path / "ocr"),
        material_gap_slot_fixture(tmp_path / "gap"),
        insufficient_coverage_slot_fixture(tmp_path / "coverage"),
        ambiguous_coverage_slot_fixture(tmp_path / "amb"),
        ambiguous_profile_slot_fixture(tmp_path / "profile"),
        unsupported_format_slot_fixture(tmp_path / "unsupported"),
        no_slots_blueprint_fixture(tmp_path / "no-slots"),
    ]

    first = fixtures[0].context.blueprint_service.build_blueprint_set(
        fixtures[0].simulado_blueprint.blueprint_id,
        user_id=fixtures[0].context.user_id,
    )
    second = fixtures[0].context.blueprint_service.build_blueprint_set(
        fixtures[0].simulado_blueprint.blueprint_id,
        user_id=fixtures[0].context.user_id,
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)


def test_question_generation_blueprint_ready_source_grounded_fixture(tmp_path):
    fixture = ready_source_grounded_slot_fixture(tmp_path)
    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    slot = result.slot_blueprints[0]

    assert result.readiness_state == "ready_for_review"
    assert result.ready_slots == 1
    assert slot.readiness_state == "ready_for_draft"
    assert slot.source_evidence
    assert slot.source_evidence[0].document_id == fixture.uploaded_material.metadata.document_id
    assert slot.source_evidence[0].chunk_id == fixture.chunk.chunk_id
    assert any(item.constraint_type == "must_use_source_evidence" for item in slot.constraints)
    assert slot.source_evidence[0].safe_snippet is not None
    assert len(slot.source_evidence[0].safe_snippet) <= 240


def test_question_generation_blueprint_blocker_fixtures_are_conservative(tmp_path):
    scenarios = [
        (missing_source_slot_fixture(tmp_path / "missing"), "blocked_by_missing_source", "blocked"),
        (ocr_required_slot_fixture(tmp_path / "ocr"), "blocked_by_ocr", "blocked"),
        (material_gap_slot_fixture(tmp_path / "gap"), "blocked_by_material_gap", "blocked"),
        (missing_document_text_slot_fixture(tmp_path / "missing-text"), "blocked_by_material_gap", "blocked"),
        (insufficient_coverage_slot_fixture(tmp_path / "coverage"), "blocked_by_insufficient_coverage", "blocked"),
        (ambiguous_coverage_slot_fixture(tmp_path / "amb"), "needs_review", "needs_review"),
        (ambiguous_profile_slot_fixture(tmp_path / "profile"), "needs_review", "needs_review"),
        (unsupported_format_slot_fixture(tmp_path / "unsupported"), "blocked_by_unsupported_format", "blocked"),
    ]

    for fixture, expected_slot_state, expected_set_state in scenarios:
        result = fixture.context.blueprint_service.build_blueprint_set(
            fixture.simulado_blueprint.blueprint_id,
            user_id=fixture.context.user_id,
        )
        slot = result.slot_blueprints[0]
        assert slot.readiness_state == expected_slot_state
        assert result.readiness_state == expected_set_state
        assert result.ready_slots == 0
        if expected_slot_state.startswith("blocked_by_"):
            assert result.blocked_slots == 1
        if expected_slot_state == "needs_review":
            assert result.needs_review_slots == 1


def test_question_generation_blueprint_exam_profile_style_fixtures(tmp_path):
    cebraspe = cebraspe_true_false_fixture(tmp_path / "cebraspe")
    fgv = fgv_multiple_choice_fixture(tmp_path / "fgv")
    pscpp = pscpp_maritime_fixture(tmp_path / "pscpp")

    cebraspe_result = cebraspe.context.blueprint_service.build_blueprint_set(
        cebraspe.simulado_blueprint.blueprint_id,
        user_id=cebraspe.context.user_id,
    )
    fgv_result = fgv.context.blueprint_service.build_blueprint_set(
        fgv.simulado_blueprint.blueprint_id,
        user_id=fgv.context.user_id,
    )
    pscpp_result = pscpp.context.blueprint_service.build_blueprint_set(
        pscpp.simulado_blueprint.blueprint_id,
        user_id=pscpp.context.user_id,
    )

    assert cebraspe_result.slot_blueprints[0].question_kind == "assertion_judgement"
    assert "single_assertion" in cebraspe_result.slot_blueprints[0].style_hints
    assert "technical_precision" in cebraspe_result.slot_blueprints[0].style_hints
    assert "source_grounded_assertion_required" in cebraspe_result.slot_blueprints[0].style_hints

    assert fgv_result.slot_blueprints[0].question_kind == "case_based_multiple_choice"
    assert "contextualized_command" in fgv_result.slot_blueprints[0].style_hints
    assert "plausible_distractors_future" in fgv_result.slot_blueprints[0].style_hints
    assert "single_best_answer" in fgv_result.slot_blueprints[0].style_hints

    assert pscpp_result.slot_blueprints[0].question_kind == "technical_maritime_scenario"
    assert "technical_operational_context" in pscpp_result.slot_blueprints[0].style_hints
    assert "allow_english_maritime_terms" in pscpp_result.slot_blueprints[0].style_hints
    assert "prioritize_bibliography_evidence" in pscpp_result.slot_blueprints[0].style_hints
    assert any(
        item.constraint_type == "must_preserve_technical_maritime_context"
        for item in pscpp_result.slot_blueprints[0].constraints
    )


def test_question_generation_blueprint_safe_snippet_and_no_leakage_assertions(tmp_path):
    fixture = long_chunk_snippet_fixture(tmp_path)
    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    snippet = result.slot_blueprints[0].source_evidence[0].safe_snippet
    dumped = result.model_dump(mode="json")

    assert snippet is not None
    assert len(snippet) <= 240
    assert "/Users/" not in snippet
    assert fixture.chunk.text not in json.dumps(dumped, ensure_ascii=True)
    assert_no_leakage(dumped)


def test_question_generation_blueprint_no_slots_and_mixed_readiness_fixtures(tmp_path):
    no_slots = no_slots_blueprint_fixture(tmp_path / "no-slots")
    mixed = mixed_readiness_blueprint_fixture(tmp_path / "mixed")

    no_slots_result = no_slots.context.blueprint_service.build_blueprint_set(
        no_slots.simulado_blueprint.blueprint_id,
        user_id=no_slots.context.user_id,
    )
    mixed_result = mixed.context.blueprint_service.build_blueprint_set(
        mixed.simulado_blueprint.blueprint_id,
        user_id=mixed.context.user_id,
    )

    assert no_slots_result.readiness_state == "no_slots"
    assert no_slots_result.total_slots == 0
    assert no_slots_result.ready_slots == 0
    assert no_slots_result.blocked_slots == 0
    assert no_slots_result.needs_review_slots == 0

    assert mixed_result.readiness_state == "partially_ready"
    assert mixed_result.total_slots == 4
    assert mixed_result.ready_slots == 1
    assert mixed_result.blocked_slots == 2
    assert mixed_result.needs_review_slots == 1
    assert all(item.readiness_state != "ready_for_draft" for item in mixed_result.slot_blueprints[1:])


def test_question_generation_blueprint_no_final_content_safeguards(tmp_path):
    fixture = no_final_content_safety_fixture(tmp_path)
    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    dumped = result.model_dump(mode="json")
    keys = collect_keys(dumped)

    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in keys
    assert result.no_question_text_generated is True
    assert result.no_alternatives_generated is True
    assert result.no_distractors_generated is True
    assert result.no_answer_key_generated is True
    assert result.no_explanations_generated is True
    json.dumps(dumped, ensure_ascii=True)


def test_question_generation_blueprint_persistence_and_idempotency_fixture(tmp_path):
    fixture = ready_source_grounded_slot_fixture(tmp_path)
    service = fixture.context.blueprint_service
    repository = fixture.context.repository

    first = service.build_blueprint_set(fixture.simulado_blueprint.blueprint_id, user_id=fixture.context.user_id)
    second = service.build_blueprint_set(fixture.simulado_blueprint.blueprint_id, user_id=fixture.context.user_id)
    by_source = repository.get_question_generation_blueprint(fixture.simulado_blueprint.blueprint_id, user_id=fixture.context.user_id)
    by_id = repository.get_question_generation_blueprint_by_id(first.blueprint_set_id, user_id=fixture.context.user_id)
    listed = repository.list_user_question_generation_blueprints(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1


def test_question_generation_blueprint_api_owner_only_and_get_read_only(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    document_id = upload_and_process_markdown(
        owner,
        "ripeam_owner_api.md",
        "# RIPEAM\n\nRegras de governo e rumo com base normativa e tecnicidade suficiente para fixture API.",
    )
    chunk = repository.list_document_chunks(document_id, user_id=owner_id)[0]
    section = repository.list_document_sections(document_id, user_id=owner_id)[0]
    evidence = CurriculumSourceEvidence(
        evidence_id="e:owner-api",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam", "governo"],
        confidence=0.9,
    )
    graph = CurriculumGraph(
        graph_id="graph:qgb-owner-api",
        edital_id="edital:qgb-owner-api",
        alignment_id="alignment:qgb-owner-api",
        user_id=owner_id,
        subjects=[
            CurriculumSubjectNode(
                subject_id="subject:navegacao",
                title="Navegacao",
                normalized_title="navegacao",
                topic_ids=["topic:owner-api"],
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.9,
                reasoning="fixture",
            )
        ],
        topics=[
            CurriculumTopicNode(
                topic_id="topic:owner-api",
                title="RIPEAM",
                normalized_title="ripeam",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:owner-api",
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.9,
                evidence=[evidence],
            )
        ],
        coverage_links=[
            CurriculumCoverageLink(
                link_id="link:owner-api",
                target_type="topic",
                target_id="topic:owner-api",
                document_ids=[document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="covered",
                confidence=0.9,
                evidence=[evidence],
            )
        ],
        summary=CurriculumGraphSummary(subject_count=1, topic_count=1, covered_topics_count=1),
    )
    repository.save_curriculum_graph(graph, user_id=owner_id)
    fixture_simulado = SimuladoBlueprint(
        blueprint_id="simulado:owner-api:exam-profile:fgv",
        graph_id=graph.graph_id,
        cycle_id="cycle:owner-api:exam-profile:fgv",
        exam_profile_id="exam-profile:fgv",
        user_id=owner_id,
        exam_board="FGV",
        format_type="multiple_choice_5",
        question_slots=[
            SimuladoQuestionSlot(
                slot_id="question-slot:topic:owner-api",
                section_id="section:primary",
                target_subject_id="subject:navegacao",
                target_topic_id="topic:owner-api",
                format_type="multiple_choice_5",
                cognitive_demand="high",
                difficulty_hint="medium",
                generation_style="case_based",
                source_evidence_ids=["e:owner-api"],
                required_coverage_state="covered",
                readiness_state="ready_for_generation",
            )
        ],
        rationale=SimuladoBlueprintRationale(
            summary="fixture",
            source_graph_id=graph.graph_id,
            source_cycle_id="cycle:owner-api:exam-profile:fgv",
            source_exam_profile_id="exam-profile:fgv",
            confidence=0.8,
        ),
    )
    repository.save_simulado_blueprint(fixture_simulado, user_id=owner_id)

    before = repository.list_user_question_generation_blueprints(user_id=owner_id)
    missing = owner.get(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint")
    after_missing = repository.list_user_question_generation_blueprints(user_id=owner_id)
    built = owner.post(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint/build")
    loaded = owner.get(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint")
    blueprint_set_id = built.json()["blueprint_set_id"]
    by_id = owner.get(f"/api/question-generation-blueprint/{blueprint_set_id}")
    after_get = repository.list_user_question_generation_blueprints(user_id=owner_id)

    assert before == []
    assert missing.status_code == 404
    assert after_missing == []
    assert built.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert after_get and len(after_get) == 1
    assert loaded.json() == by_id.json()
    assert other.post(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint/build").status_code == 404
    assert other.get(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint").status_code == 404
    assert other.get(f"/api/question-generation-blueprint/{blueprint_set_id}").status_code == 404
    assert anonymous.post(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint/build").status_code == 401
    assert anonymous.get(f"/api/simulado-blueprint/{fixture_simulado.blueprint_id}/question-generation-blueprint").status_code == 401
    assert anonymous.get(f"/api/question-generation-blueprint/{blueprint_set_id}").status_code == 401
    assert_no_leakage(loaded.json())


def test_question_generation_blueprint_runtime_preservation_fixture(tmp_path):
    fixture = ready_source_grounded_slot_fixture(tmp_path)
    repository = fixture.context.repository
    before_graph = repository.get_curriculum_graph_by_id(fixture.graph.graph_id, user_id=fixture.context.user_id)
    before_simulado = repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    after_graph = repository.get_curriculum_graph_by_id(fixture.graph.graph_id, user_id=fixture.context.user_id)
    after_simulado = repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    assert before_graph.model_dump(mode="json") == after_graph.model_dump(mode="json")
    assert before_simulado.model_dump(mode="json") == after_simulado.model_dump(mode="json")
