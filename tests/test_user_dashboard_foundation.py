import json

import fitz

from app.domain.models import User
from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from app.services.user_dashboard import UserDashboardService


def create_user(repository: JsonStudyRepository, *, user_id: str = "user-a", username: str = "owner") -> User:
    user = User(
        user_id=user_id,
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        password_hash="hash-test",
    )
    repository.create_user(user)
    return user


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def prepare_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    edital_service = EditalIngestionService(repository)
    alignment_service = BibliographyAlignmentService(repository)
    graph_service = CurriculumGraphBuilderService(repository)
    cycle_service = StudyCycleOrchestratorService(repository)
    blueprint_service = SimuladoBlueprintBuilderService(repository)
    dashboard_service = UserDashboardService(repository)
    return (
        repository,
        material_service,
        pipeline_service,
        edital_service,
        alignment_service,
        graph_service,
        cycle_service,
        blueprint_service,
        dashboard_service,
    )


def register_upload(material_service, *, user_id: str, filename: str, content_type: str, payload: bytes):
    return material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        payload=payload,
    )


def build_full_user_context(tmp_path, *, user_id: str = "user-a"):
    (
        repository,
        material_service,
        pipeline_service,
        edital_service,
        alignment_service,
        graph_service,
        cycle_service,
        blueprint_service,
        dashboard_service,
    ) = prepare_services(tmp_path)
    create_user(repository, user_id=user_id, username=user_id)

    edital = register_upload(
        material_service,
        user_id=user_id,
        filename="edital.md",
        content_type="text/markdown",
        payload=(
            b"# Estrutura da Prova\n\nFGV. Prova objetiva com cinco alternativas A, B, C, D e E. 80 questoes."
            b"\n\n# Conteudo Programatico\n\n1. RIPEAM\n2. Meteorologia\n\n# Bibliografia\n\nBRASIL. RIPEAM Comentado. 2021."
        ),
    )
    pipeline_service.process_document(edital.metadata.document_id, user_id=user_id)
    edital_state = edital_service.ingest_document(edital.metadata.document_id, user_id=user_id)

    ripeam = register_upload(
        material_service,
        user_id=user_id,
        filename="ripeam.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nRegras de governo e rumo.",
    )
    pipeline_service.process_document(ripeam.metadata.document_id, user_id=user_id)

    meteo = register_upload(
        material_service,
        user_id=user_id,
        filename="meteorologia.md",
        content_type="text/markdown",
        payload=b"# Meteorologia\n\nVentos e cartas sinoticas.",
    )
    pipeline_service.process_document(meteo.metadata.document_id, user_id=user_id)

    pdf = register_upload(
        material_service,
        user_id=user_id,
        filename="legislacao.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    pipeline_service.process_document(pdf.metadata.document_id, user_id=user_id)

    edital_id = edital_state.edital_id
    alignment_service.align_edital(edital_id, user_id=user_id)
    graph_service.build_graph(edital_id, user_id=user_id)
    graph = repository.get_curriculum_graph(edital_id, user_id=user_id)
    cycle_service.build_cycle(graph.graph_id, user_id=user_id)
    cycle = repository.get_study_cycle_plan(graph.graph_id, user_id=user_id)
    blueprint_service.build_blueprint(cycle.cycle_id, user_id=user_id)

    return {
        "repository": repository,
        "dashboard_service": dashboard_service,
        "user_id": user_id,
        "edital_id": edital_id,
        "graph_id": graph.graph_id,
        "cycle_id": cycle.cycle_id,
    }


def test_user_dashboard_empty_authenticated_user_is_safe_and_useful(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    user = create_user(repository)
    overview = UserDashboardService(repository).build_overview(user.user_id)

    assert overview.dashboard_available is True
    assert overview.dashboard_state in {"getting_started", "no_data"}
    assert overview.pipeline_readiness == "no_data"
    assert overview.study_readiness == "not_ready"
    assert overview.pending_actions
    assert overview.pending_actions[0].action_type == "upload_material"
    assert overview.primary_next_step is not None
    assert overview.primary_next_step.action_type == "upload_material"
    assert overview.active_project.project_available is False
    assert overview.materials.total_materials == 0
    assert overview.edital.edital_available is False
    assert overview.alignment.alignment_available is False
    assert overview.curriculum_graph.graph_available is False
    assert overview.study_cycle.cycle_available is False
    assert overview.simulado_blueprint.blueprint_available is False
    dumped = json.dumps(overview.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def test_user_dashboard_summarizes_materials_pipeline_and_pending_actions_without_mutation(tmp_path):
    (
        repository,
        material_service,
        pipeline_service,
        _,
        _,
        _,
        _,
        _,
        dashboard_service,
    ) = prepare_services(tmp_path)
    user = create_user(repository)

    for index in range(11):
        register_upload(
            material_service,
            user_id=user.user_id,
            filename=f"material-{index}.md",
            content_type="text/markdown",
            payload=f"# Documento {index}\n\nConteudo {index}".encode("utf-8"),
        )
    txt = register_upload(
        material_service,
        user_id=user.user_id,
        filename="processado.txt",
        content_type="text/plain",
        payload=b"introducao\n\ndetalhe\n\nfim",
    )
    pipeline_service.process_document(txt.metadata.document_id, user_id=user.user_id)
    pdf = register_upload(
        material_service,
        user_id=user.user_id,
        filename="ocr.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    pipeline_service.process_document(pdf.metadata.document_id, user_id=user.user_id)

    before_materials = len(repository.list_uploaded_materials(user_id=user.user_id))
    before_editals = len(repository.list_user_edital_extractions(user_id=user.user_id))
    overview = dashboard_service.build_overview(user.user_id)
    after_materials = len(repository.list_uploaded_materials(user_id=user.user_id))
    after_editals = len(repository.list_user_edital_extractions(user_id=user.user_id))

    assert before_materials == after_materials
    assert before_editals == after_editals
    assert overview.materials.total_materials == 13
    assert overview.materials.processed_count >= 1
    assert overview.materials.pending_count >= 1
    assert overview.materials.ocr_required_count >= 1
    assert len(overview.materials.recent_materials) == 10
    assert overview.document_pipeline.total_documents == 13
    assert overview.document_pipeline.ocr_required_count >= 1
    assert len(overview.document_pipeline.latest_pipeline_states) == 10
    action_types = {item.action_type for item in overview.pending_actions}
    assert "process_material" in action_types
    assert "run_ocr_future" in action_types
    assert "ingest_edital" in action_types
    assert len(overview.pending_actions) <= 20
    dumped = json.dumps(overview.model_dump(mode="json"), ensure_ascii=True)
    assert "storage_path" not in dumped
    assert "extracted_text" not in dumped


def test_user_dashboard_aggregates_existing_artifacts_and_derives_primary_next_step(tmp_path):
    context = build_full_user_context(tmp_path)
    overview = context["dashboard_service"].build_overview(context["user_id"])

    assert overview.dashboard_available is True
    assert overview.dashboard_state in {
        "blocked_by_ocr",
        "needs_manual_review",
        "simulado_blueprint_ready",
        "study_cycle_ready",
    }
    assert overview.pipeline_readiness in {"blueprint_ready", "blocked", "cycle_ready"}
    assert overview.study_readiness in {"ready_for_simulado", "ready_for_review", "blocked"}
    assert overview.edital.edital_available is True
    assert overview.alignment.alignment_available is True
    assert overview.curriculum_graph.graph_available is True
    assert overview.study_cycle.cycle_available is True
    assert overview.exam_profile.profile_available is True
    assert overview.simulado_blueprint.blueprint_available is True
    assert overview.simulado_blueprint.no_question_generation_confirmed is True
    assert overview.curriculum_graph.topic_count >= 2
    assert overview.study_cycle.topic_slot_count >= 2
    assert overview.simulado_blueprint.question_slot_count >= 2
    assert overview.primary_next_step is not None
    assert overview.primary_next_step.action_type in {
        "run_ocr_future",
        "manual_review",
        "resolve_material_gap",
        "confirm_exam_profile",
    }
    assert overview.dashboard_summary
    assert overview.user.user_id == context["user_id"]
    assert overview.continuation.continuation_available is False
    assert overview.retention.retention_available is False

