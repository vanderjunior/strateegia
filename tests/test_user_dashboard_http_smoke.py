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


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str = "text/markdown",
    process: bool = False,
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
    )
    assert uploaded.status_code == 201
    payload = uploaded.json()
    if process:
        processed = client.post(f"/api/materials/{payload['metadata']['document_id']}/process")
        assert processed.status_code == 200
    return payload


def test_dashboard_http_smoke_routes_assets_and_empty_contract(tmp_path):
    owner, anonymous, static_client, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    assert anonymous.get("/api/dashboard/overview").status_code == 401
    assert anonymous.get("/dashboard").status_code == 401

    dashboard_page = owner.get("/dashboard")
    overview_response = owner.get("/api/dashboard/overview")
    home_page = owner.get("/")
    inspection_page = owner.get("/inspection")
    static_html = static_client.get("/static/dashboard.html")
    static_js = static_client.get("/static/dashboard.js")
    static_css = static_client.get("/static/dashboard.css")

    assert dashboard_page.status_code == 200
    assert "Study Dashboard" in dashboard_page.text
    assert "read-only" in dashboard_page.text.lower()
    assert "Loading inspection payload" not in dashboard_page.text
    assert "<button" not in dashboard_page.text.lower()

    assert overview_response.status_code == 200
    payload = overview_response.json()
    expected_keys = {
        "dashboard_available",
        "dashboard_state",
        "dashboard_summary",
        "journey_stage",
        "pipeline_readiness",
        "study_readiness",
        "active_project",
        "user",
        "continuation",
        "materials",
        "document_pipeline",
        "edital",
        "alignment",
        "curriculum_graph",
        "study_cycle",
        "exam_profile",
        "simulado_blueprint",
        "progress",
        "retention",
        "pending_actions",
        "primary_next_step",
        "warnings",
        "generated_at",
        "dashboard_version",
        "metadata",
    }
    assert expected_keys.issubset(payload.keys())
    assert payload["dashboard_available"] is True
    assert payload["dashboard_state"] in {"getting_started", "no_data"}
    assert payload["pipeline_readiness"] == "no_data"
    assert payload["study_readiness"] == "not_ready"
    assert isinstance(payload["dashboard_summary"], str)
    assert len(payload["dashboard_summary"]) <= 200
    assert isinstance(payload["pending_actions"], list)
    assert len(payload["pending_actions"]) <= 20
    assert isinstance(payload["warnings"], list)
    assert len(payload["warnings"]) <= 20
    assert len(payload["materials"]["recent_materials"]) <= 10
    assert len(payload["document_pipeline"]["latest_pipeline_states"]) <= 10
    assert payload["pending_actions"][0]["action_type"] == "upload_material"
    assert payload["primary_next_step"]["action_type"] == "upload_material"
    pending_action_types = {item["action_type"] for item in payload["pending_actions"]}
    assert payload["primary_next_step"]["action_type"] in pending_action_types
    assert json.dumps(payload, ensure_ascii=True)

    assert home_page.status_code == 200
    assert "Study Dashboard" not in home_page.text
    assert inspection_page.status_code == 200
    assert "Loading inspection payload" in inspection_page.text
    assert dashboard_page.text != inspection_page.text

    assert static_html.status_code == 200
    assert "Study Dashboard" in static_html.text
    assert "Loading inspection payload" not in static_html.text
    assert "<details>" in static_html.text
    assert "<details open" not in static_html.text.lower()

    assert static_js.status_code == 200
    assert "/api/dashboard/overview" in static_js.text
    assert "/api/inspection/runtime" not in static_js.text
    assert "/api/inspection/runtime/export" not in static_js.text
    for forbidden in (
        "/process",
        "/edital/ingest",
        "/align-bibliography",
        "/curriculum-graph/build",
        "/study-cycle/build",
        "/simulado-blueprint/build",
    ):
        assert forbidden not in static_js.text

    assert static_css.status_code == 200
    assert ".dashboard-shell" in static_css.text


def test_dashboard_http_smoke_is_user_scoped_and_does_not_leak_material_data(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    upload_material(
        owner,
        filename="owner-secret-material.md",
        content=b"# Owner\n\nOWNER-SHOULD-NOT-LEAK",
        process=True,
    )
    upload_material(
        other,
        filename="other-secret-material.md",
        content=b"# Other\n\nOTHER-SHOULD-NOT-LEAK",
        process=True,
    )

    owner_payload = owner.get("/api/dashboard/overview")
    other_payload = other.get("/api/dashboard/overview")

    assert owner_payload.status_code == 200
    assert other_payload.status_code == 200

    owner_json = owner_payload.json()
    other_json = other_payload.json()
    owner_dump = json.dumps(owner_json, ensure_ascii=True)
    other_dump = json.dumps(other_json, ensure_ascii=True)

    assert owner_json["user"]["username"] == "owner"
    assert other_json["user"]["username"] == "other"
    assert owner_json["materials"]["total_materials"] == 1
    assert other_json["materials"]["total_materials"] == 1
    assert "owner-secret-material.md" in owner_dump
    assert "owner-secret-material.md" not in other_dump
    assert "other-secret-material.md" in other_dump
    assert "other-secret-material.md" not in owner_dump

    for dumped in (owner_dump, other_dump):
        assert "password_hash" not in dumped
        assert "studyflow_session" not in dumped
        assert "/uploads/" not in dumped
        assert "/private/" not in dumped
        assert "OWNER-SHOULD-NOT-LEAK" not in dumped
        assert "OTHER-SHOULD-NOT-LEAK" not in dumped
        assert "raw_runtime_block" not in dumped
        assert "manual_experiment_inspection" not in dumped
        assert "inspection_available" not in dumped


def test_dashboard_http_smoke_is_read_only_and_does_not_call_builders_or_inspection(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    upload_material(owner, filename="owner.md", content=b"# Owner\n\nConteudo.", process=True)

    before_materials = len(repository.list_uploaded_materials(user_id=user["user_id"]))
    before_editais = len(repository.list_user_edital_extractions(user_id=user["user_id"]))
    before_graphs = len(repository.list_user_curriculum_graphs(user_id=user["user_id"]))
    before_cycles = len(repository.list_user_study_cycle_plans(user_id=user["user_id"]))
    before_blueprints = len(repository.list_user_simulado_blueprints(user_id=user["user_id"]))
    before_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dashboard HTTP smoke expects a read-only overview route")

    monkeypatch.setattr(DocumentPipelineService, "process_document", fail_if_called)
    monkeypatch.setattr(EditalIngestionService, "ingest_document", fail_if_called)
    monkeypatch.setattr(BibliographyAlignmentService, "align_edital", fail_if_called)
    monkeypatch.setattr(CurriculumGraphBuilderService, "build_graph", fail_if_called)
    monkeypatch.setattr(StudyCycleOrchestratorService, "build_cycle", fail_if_called)
    monkeypatch.setattr(SimuladoBlueprintBuilderService, "build_blueprint", fail_if_called)
    monkeypatch.setattr(LearningDecisionEngine, "build_review_plan", fail_if_called)
    monkeypatch.setattr("app.api.routes._inspection_payload", fail_if_called)

    first = owner.get("/api/dashboard/overview")
    second = owner.get("/api/dashboard/overview")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_uploaded_materials(user_id=user["user_id"])) == before_materials
    assert len(repository.list_user_edital_extractions(user_id=user["user_id"])) == before_editais
    assert len(repository.list_user_curriculum_graphs(user_id=user["user_id"])) == before_graphs
    assert len(repository.list_user_study_cycle_plans(user_id=user["user_id"])) == before_cycles
    assert len(repository.list_user_simulado_blueprints(user_id=user["user_id"])) == before_blueprints
    assert repository.load_progress(user_id=user["user_id"]).model_dump(mode="json") == before_progress


def test_dashboard_http_smoke_bounds_and_primary_next_step_are_stable(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    for index in range(12):
        upload_material(
            owner,
            filename=f"material-{index}.md",
            content=f"# Material {index}\n\nConteudo {index}".encode("utf-8"),
            process=index % 3 == 0,
        )

    first = owner.get("/api/dashboard/overview")
    second = owner.get("/api/dashboard/overview")

    assert first.status_code == 200
    assert second.status_code == 200

    first_json = first.json()
    second_json = second.json()
    assert first_json == second_json

    assert len(first_json["materials"]["recent_materials"]) <= 10
    assert len(first_json["document_pipeline"]["latest_pipeline_states"]) <= 10
    assert len(first_json["pending_actions"]) <= 20
    assert len(first_json["warnings"]) <= 20
    assert isinstance(first_json["generated_at"], str)
    assert first_json["dashboard_version"]
    assert first_json["dashboard_summary"]
    assert len(first_json["dashboard_summary"]) <= 200

    primary = first_json["primary_next_step"]
    assert primary is None or primary["action_type"] in {
        item["action_type"] for item in first_json["pending_actions"]
    }
