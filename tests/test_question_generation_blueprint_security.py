import json
from io import BytesIO

from fastapi.testclient import TestClient

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
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService
from app.services.question_generation_blueprint import QuestionGenerationBlueprintService


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    return (
        repository,
        MaterialService(repository, storage_root=storage_root),
        DocumentPipelineService(repository, storage_root=storage_root),
        QuestionGenerationBlueprintService(repository),
    )


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
    assert client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    ).status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return login.json()["user"]["user_id"]


def upload_markdown(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(text.encode("utf-8")), "text/markdown")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["metadata"]["document_id"]
    processed = client.post(f"/api/materials/{document_id}/process")
    assert processed.status_code == 200
    return document_id


def persist_ready_fixture(repository, material_service, pipeline_service):
    long_text = (
        "# RIPEAM\n\n"
        + " ".join(["conteudo-tecnico"] * 40)
        + " /Users/should/not/appear/in/snippet "
        + " ".join(["navegacao"] * 20)
    )
    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="ripeam_longo.md",
        content_type="text/markdown",
        payload=long_text.encode("utf-8"),
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    chunk = repository.list_document_chunks(uploaded.metadata.document_id, user_id="user-a")[0]
    section = repository.list_document_sections(uploaded.metadata.document_id, user_id="user-a")[0]
    evidence = CurriculumSourceEvidence(
        evidence_id="e:qgb:secure",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=uploaded.metadata.document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam"],
        confidence=0.91,
    )
    graph = CurriculumGraph(
        graph_id="graph:qgb-security",
        edital_id="edital:qgb-security",
        alignment_id="alignment:qgb-security",
        user_id="user-a",
        subjects=[
            CurriculumSubjectNode(
                subject_id="subject:navegacao",
                title="Navegacao",
                normalized_title="navegacao",
                order_index=0,
                topic_ids=["topic:ripeam"],
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.9,
                reasoning="fixture",
            )
        ],
        topics=[
            CurriculumTopicNode(
                topic_id="topic:ripeam",
                title="RIPEAM",
                normalized_title="ripeam",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:ripeam",
                order_index=0,
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.91,
                evidence=[evidence],
            )
        ],
        coverage_links=[
            CurriculumCoverageLink(
                link_id="link:qgb:secure",
                target_type="topic",
                target_id="topic:ripeam",
                document_ids=[uploaded.metadata.document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="covered",
                confidence=0.91,
                evidence=[evidence],
            )
        ],
        summary=CurriculumGraphSummary(subject_count=1, topic_count=1, covered_topics_count=1),
    )
    repository.save_curriculum_graph(graph, user_id="user-a")
    simulado = SimuladoBlueprint(
        blueprint_id="simulado:graph:qgb-security:exam-profile:fgv",
        graph_id=graph.graph_id,
        cycle_id="cycle:graph:qgb-security",
        exam_profile_id="exam-profile:fgv",
        user_id="user-a",
        exam_board="FGV",
        format_type="multiple_choice_5",
        question_slots=[
            SimuladoQuestionSlot(
                slot_id="question-slot:topic:ripeam",
                section_id="section:primary",
                target_subject_id="subject:navegacao",
                target_topic_id="topic:ripeam",
                format_type="multiple_choice_5",
                cognitive_demand="high",
                difficulty_hint="medium",
                generation_style="case_based",
                source_evidence_ids=["e:qgb:secure"],
                required_coverage_state="covered",
                readiness_state="ready_for_generation",
                confidence=0.8,
            )
        ],
        rationale=SimuladoBlueprintRationale(
            summary="fixture",
            source_graph_id=graph.graph_id,
            source_cycle_id="cycle:graph:qgb-security",
            source_exam_profile_id="exam-profile:fgv",
            confidence=0.8,
        ),
    )
    repository.save_simulado_blueprint(simulado, user_id="user-a")
    return simulado.blueprint_id, long_text


def test_question_generation_blueprint_snippets_are_bounded_and_sanitized(tmp_path):
    repository, material_service, pipeline_service, service = create_services(tmp_path)
    blueprint_id, long_text = persist_ready_fixture(repository, material_service, pipeline_service)

    result = service.build_blueprint_set(blueprint_id, user_id="user-a")
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    snippet = result.slot_blueprints[0].source_evidence[0].safe_snippet

    assert snippet is not None
    assert len(snippet) <= 240
    assert "/Users/" not in snippet
    assert long_text not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "password_hash" not in dumped


def test_question_generation_blueprint_api_does_not_leak_paths_or_raw_document_body(tmp_path):
    client, repository = create_client(tmp_path)
    user_id = register_and_login(client, "owner")
    document_id = upload_markdown(
        client,
        "ripeam.md",
        "# RIPEAM\n\n" + " ".join(["texto-seguro"] * 80),
    )
    chunk = repository.list_document_chunks(document_id, user_id=user_id)[0]
    section = repository.list_document_sections(document_id, user_id=user_id)[0]
    evidence = CurriculumSourceEvidence(
        evidence_id="e:api",
        source_type="document_chunk",
        source_id=chunk.chunk_id,
        document_id=document_id,
        chunk_id=chunk.chunk_id,
        section_id=section.section_id,
        excerpt=chunk.text,
        matched_terms=["ripeam"],
        confidence=0.88,
    )
    graph = CurriculumGraph(
        graph_id="graph:qgb-api",
        edital_id="edital:qgb-api",
        alignment_id="alignment:qgb-api",
        user_id=user_id,
        subjects=[
            CurriculumSubjectNode(
                subject_id="subject:navegacao",
                title="Navegacao",
                normalized_title="navegacao",
                topic_ids=["topic:ripeam"],
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.88,
                reasoning="fixture",
            )
        ],
        topics=[
            CurriculumTopicNode(
                topic_id="topic:ripeam",
                title="RIPEAM",
                normalized_title="ripeam",
                subject_id="subject:navegacao",
                source_topic_candidate_id="topic:ripeam",
                coverage_state="covered",
                review_state="ready_for_review",
                confidence=0.88,
                evidence=[evidence],
            )
        ],
        coverage_links=[
            CurriculumCoverageLink(
                link_id="link:api",
                target_type="topic",
                target_id="topic:ripeam",
                document_ids=[document_id],
                chunk_ids=[chunk.chunk_id],
                section_ids=[section.section_id],
                coverage_state="covered",
                confidence=0.88,
                evidence=[evidence],
            )
        ],
        summary=CurriculumGraphSummary(subject_count=1, topic_count=1, covered_topics_count=1),
    )
    repository.save_curriculum_graph(graph, user_id=user_id)
    repository.save_simulado_blueprint(
        SimuladoBlueprint(
            blueprint_id="simulado:graph:qgb-api:exam-profile:fgv",
            graph_id=graph.graph_id,
            cycle_id="cycle:graph:qgb-api",
            exam_profile_id="exam-profile:fgv",
            user_id=user_id,
            exam_board="FGV",
            format_type="multiple_choice_5",
            question_slots=[
                SimuladoQuestionSlot(
                    slot_id="question-slot:topic:ripeam",
                    section_id="section:primary",
                    target_subject_id="subject:navegacao",
                    target_topic_id="topic:ripeam",
                    format_type="multiple_choice_5",
                    cognitive_demand="high",
                    difficulty_hint="medium",
                    generation_style="case_based",
                    source_evidence_ids=["e:api"],
                    required_coverage_state="covered",
                    readiness_state="ready_for_generation",
                )
            ],
            rationale=SimuladoBlueprintRationale(
                summary="fixture",
                source_graph_id=graph.graph_id,
                source_cycle_id="cycle:graph:qgb-api",
                source_exam_profile_id="exam-profile:fgv",
            ),
        ),
        user_id=user_id,
    )

    response = client.post(
        "/api/simulado-blueprint/simulado:graph:qgb-api:exam-profile:fgv/question-generation-blueprint/build"
    )
    dumped = json.dumps(response.json(), ensure_ascii=True)

    assert response.status_code == 200
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert chunk.text not in dumped
