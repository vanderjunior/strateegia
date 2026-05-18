from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.learning_engine import LearningDecisionEngine
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from tests.fixtures.curriculum_graph_documents import basic_covered_graph_fixture
from tests.fixtures.ocr_documents import minimal_textless_pdf_bytes, minimal_textual_pdf_bytes
from tests.fixtures.simulado_blueprint_sources import persist_simulado_blueprint_fixture
from tests.fixtures.study_cycle_graphs import balanced_cycle_fixture


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
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
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    return registered.json()


def upload_material(client: TestClient, filename: str, content: bytes, content_type: str) -> dict[str, object]:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert response.status_code == 201
    return response.json()


def assert_sanitized_payload(payload: object, *, forbidden: list[str]) -> str:
    dumped = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    for fragment in forbidden:
        assert fragment not in dumped
    return dumped


def build_owner_surface(repository: JsonStudyRepository, *, user_id: str) -> dict[str, object]:
    edital_fixture = basic_covered_graph_fixture()
    edital = edital_fixture["edital"].model_copy(update={"user_id": user_id})
    alignment = edital_fixture["alignment"].model_copy(update={"user_id": user_id})
    repository.save_edital_extraction_result(edital, user_id=user_id)
    repository.save_bibliography_alignment_result(alignment, user_id=user_id)

    blueprint_bundle = persist_simulado_blueprint_fixture(
        repository,
        {"graph": balanced_cycle_fixture()["graph"], "profile_id": "exam-profile:fgv"},
        user_id=user_id,
    )
    graph = blueprint_bundle["graph"]
    blueprint = blueprint_bundle["blueprint"]
    cycle_state = blueprint_bundle["cycle_state"]

    return {
        "edital": edital,
        "alignment": alignment,
        "graph": graph,
        "cycle_id": cycle_state.cycle_id,
        "blueprint": blueprint,
    }


def test_product_server_readiness_smoke_and_response_sanitization(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")

    textual_upload = upload_material(
        owner,
        "../../owner study!!.txt",
        b"Conteudo textual do usuario.\n\nSem OCR no upload.",
        "text/plain",
    )
    assert ".." not in textual_upload["metadata"]["filename"]
    assert textual_upload["metadata"]["storage_path"].startswith(f"uploads/{user['user_id']}/")
    assert_sanitized_payload(
        textual_upload,
        forbidden=["password_hash", str(tmp_path), "/private/", "data:image"],
    )

    pdf_upload = upload_material(owner, "scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    pdf_textual_upload = upload_material(
        owner,
        "textual.pdf",
        minimal_textual_pdf_bytes("PDF textual suficiente para processamento sem OCR."),
        "application/pdf",
    )

    monkeypatch.setenv("ENABLE_OCR", "false")
    pdf_process = owner.post(f"/api/materials/{pdf_upload['metadata']['document_id']}/process")
    textual_process = owner.post(f"/api/materials/{textual_upload['metadata']['document_id']}/process")
    pdf_textual_process = owner.post(f"/api/materials/{pdf_textual_upload['metadata']['document_id']}/process")

    assert pdf_process.status_code == 200
    assert textual_process.status_code == 200
    assert pdf_textual_process.status_code == 200
    assert pdf_process.json()["current_stage"] == "extraction_pending"
    assert textual_process.json()["current_stage"] == "metadata_ready"
    assert pdf_textual_process.json()["current_stage"] == "metadata_ready"

    fixtures = build_owner_surface(repository, user_id=user["user_id"])
    responses = {
        "home": owner.get("/"),
        "dashboard_page": owner.get("/dashboard"),
        "dashboard_overview": owner.get("/api/dashboard/overview"),
        "pipeline": owner.get(f"/api/materials/{pdf_upload['metadata']['document_id']}/pipeline"),
        "chunks": owner.get(f"/api/materials/{textual_upload['metadata']['document_id']}/chunks"),
        "sections": owner.get(f"/api/materials/{textual_upload['metadata']['document_id']}/sections"),
        "edital": owner.get(f"/api/edital/{fixtures['edital'].edital_id}"),
        "alignment": owner.get(f"/api/alignment/{fixtures['alignment'].alignment_id}"),
        "graph": owner.get(f"/api/curriculum-graph/{fixtures['graph'].graph_id}"),
        "cycle": owner.get(f"/api/study-cycle/{fixtures['cycle_id']}"),
        "blueprint": owner.get(f"/api/simulado-blueprint/{fixtures['blueprint'].blueprint_id}"),
        "exam_profiles": owner.get("/api/exam-profiles"),
        "exam_profile": owner.get("/api/exam-profiles/exam-profile:fgv"),
        "exam_profile_suggestion": owner.get(f"/api/edital/{fixtures['edital'].edital_id}/exam-profile/suggestion"),
        "inspection": owner.get("/api/inspection/runtime"),
    }

    for name, response in responses.items():
        assert response.status_code == 200, name

    assert "Study Dashboard" in responses["dashboard_page"].text
    assert "Loading inspection payload" not in responses["dashboard_page"].text
    assert "Loading inspection payload" in owner.get("/inspection").text

    for key in ("dashboard_overview", "pipeline", "chunks", "sections", "edital", "alignment", "graph", "cycle", "blueprint", "exam_profiles", "exam_profile", "exam_profile_suggestion", "inspection"):
        assert_sanitized_payload(
            responses[key].json(),
            forbidden=[
                "password_hash",
                "studyflow_session",
                str(tmp_path),
                "/uploads/",
                "/private/",
                "data:image",
                "raw_runtime_block" if key == "dashboard_overview" else "<<<never>>>",
            ],
        )

    assert len(responses["chunks"].json()) >= 1
    assert len(responses["sections"].json()) >= 1
    assert responses["dashboard_overview"].json()["user"]["user_id"] == user["user_id"]


def test_product_server_readiness_user_scope_across_major_artifact_surfaces(tmp_path, monkeypatch):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user = register_and_login(owner, "owner")
    register_and_login(other, "other")
    fixtures = build_owner_surface(repository, user_id=owner_user["user_id"])
    uploaded = upload_material(owner, "owner-scan.pdf", minimal_textless_pdf_bytes(), "application/pdf")
    document_id = uploaded["metadata"]["document_id"]

    monkeypatch.setenv("ENABLE_OCR", "false")
    assert owner.post(f"/api/materials/{document_id}/process").status_code == 200

    assert anonymous.get("/api/dashboard/overview").status_code == 401
    assert other.post(f"/api/materials/{document_id}/process").status_code == 404
    assert other.get(f"/api/materials/{document_id}/pipeline").status_code == 404
    assert other.get(f"/api/materials/{document_id}/chunks").status_code == 404
    assert other.get(f"/api/materials/{document_id}/sections").status_code == 404
    assert other.get(f"/api/edital/{fixtures['edital'].edital_id}").status_code == 404
    assert other.get(f"/api/alignment/{fixtures['alignment'].alignment_id}").status_code == 404
    assert other.get(f"/api/curriculum-graph/{fixtures['graph'].graph_id}").status_code == 404
    assert other.get(f"/api/study-cycle/{fixtures['cycle_id']}").status_code == 404
    assert other.get(f"/api/simulado-blueprint/{fixtures['blueprint'].blueprint_id}").status_code == 404
    assert other.get(f"/api/edital/{fixtures['edital'].edital_id}/exam-profile/suggestion").status_code == 404

    owner_dashboard = owner.get("/api/dashboard/overview")
    other_dashboard = other.get("/api/dashboard/overview")
    assert owner_dashboard.status_code == 200
    assert other_dashboard.status_code == 200
    assert uploaded["metadata"]["filename"] in owner_dashboard.text
    assert uploaded["metadata"]["filename"] not in other_dashboard.text


def test_product_server_readiness_get_endpoints_are_read_only_and_idempotent(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    uploaded = upload_material(owner, "notes.txt", b"Conteudo reutilizavel do usuario.", "text/plain")
    process = owner.post(f"/api/materials/{uploaded['metadata']['document_id']}/process")
    assert process.status_code == 200
    fixtures = build_owner_surface(repository, user_id=user["user_id"])

    before_materials = len(repository.list_uploaded_materials(user_id=user["user_id"]))
    before_editais = len(repository.list_user_edital_extractions(user_id=user["user_id"]))
    before_graphs = len(repository.list_user_curriculum_graphs(user_id=user["user_id"]))
    before_cycles = len(repository.list_user_study_cycle_plans(user_id=user["user_id"]))
    before_blueprints = len(repository.list_user_simulado_blueprints(user_id=user["user_id"]))
    before_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    before_pipeline = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/pipeline").json()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("read-only readiness smoke should not invoke mutating builders/processors")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_called)
    monkeypatch.setattr(DocumentPipelineService, "process_document", fail_if_called)
    monkeypatch.setattr(EditalIngestionService, "ingest_document", fail_if_called)
    monkeypatch.setattr(BibliographyAlignmentService, "align_edital", fail_if_called)
    monkeypatch.setattr(CurriculumGraphBuilderService, "build_graph", fail_if_called)
    monkeypatch.setattr(StudyCycleOrchestratorService, "build_cycle", fail_if_called)
    monkeypatch.setattr(SimuladoBlueprintBuilderService, "build_blueprint", fail_if_called)
    monkeypatch.setattr(LearningDecisionEngine, "build_review_plan", fail_if_called)

    first_dashboard = owner.get("/api/dashboard/overview")
    second_dashboard = owner.get("/api/dashboard/overview")
    first_pipeline = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/pipeline")
    second_pipeline = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/pipeline")
    first_chunks = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/chunks")
    second_chunks = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/chunks")
    first_sections = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/sections")
    second_sections = owner.get(f"/api/materials/{uploaded['metadata']['document_id']}/sections")
    first_edital = owner.get(f"/api/edital/{fixtures['edital'].edital_id}")
    second_edital = owner.get(f"/api/edital/{fixtures['edital'].edital_id}")
    first_alignment = owner.get(f"/api/alignment/{fixtures['alignment'].alignment_id}")
    second_alignment = owner.get(f"/api/alignment/{fixtures['alignment'].alignment_id}")
    first_graph = owner.get(f"/api/curriculum-graph/{fixtures['graph'].graph_id}")
    second_graph = owner.get(f"/api/curriculum-graph/{fixtures['graph'].graph_id}")
    first_cycle = owner.get(f"/api/study-cycle/{fixtures['cycle_id']}")
    second_cycle = owner.get(f"/api/study-cycle/{fixtures['cycle_id']}")
    first_blueprint = owner.get(f"/api/simulado-blueprint/{fixtures['blueprint'].blueprint_id}")
    second_blueprint = owner.get(f"/api/simulado-blueprint/{fixtures['blueprint'].blueprint_id}")
    first_inspection = owner.get("/api/inspection/runtime")
    second_inspection = owner.get("/api/inspection/runtime")

    assert first_dashboard.status_code == 200
    assert second_dashboard.status_code == 200
    assert first_dashboard.json() == second_dashboard.json()
    assert first_pipeline.json() == before_pipeline
    assert second_pipeline.json() == before_pipeline
    assert first_chunks.json() == second_chunks.json()
    assert first_sections.json() == second_sections.json()
    assert first_edital.json() == second_edital.json()
    assert first_alignment.json() == second_alignment.json()
    assert first_graph.json() == second_graph.json()
    assert first_cycle.json() == second_cycle.json()
    assert first_blueprint.json() == second_blueprint.json()
    assert first_inspection.json() == second_inspection.json()
    assert len(repository.list_uploaded_materials(user_id=user["user_id"])) == before_materials
    assert len(repository.list_user_edital_extractions(user_id=user["user_id"])) == before_editais
    assert len(repository.list_user_curriculum_graphs(user_id=user["user_id"])) == before_graphs
    assert len(repository.list_user_study_cycle_plans(user_id=user["user_id"])) == before_cycles
    assert len(repository.list_user_simulado_blueprints(user_id=user["user_id"])) == before_blueprints
    assert repository.load_progress(user_id=user["user_id"]).model_dump(mode="json") == before_progress
