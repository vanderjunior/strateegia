import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService


EDITAL_TEXT = b"""# Conteudo Programatico

1. Arte Naval
2. Meteorologia: ventos; cartas sinoticas
3. RIPEAM
4. Autoridade Maritima

# Bibliografia

SILVA, Joao. Navegacao Costeira. 2. ed. Rio de Janeiro: Editora Naval, 2020.
BRASIL. RIPEAM Comentado. Brasilia, 2021.
PEREIRA, Ana. Autoridade Maritima Aplicada. 2022.
"""


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    edital_service = EditalIngestionService(repository)
    alignment_service = BibliographyAlignmentService(repository)
    graph_service = CurriculumGraphBuilderService(repository)
    cycle_service = StudyCycleOrchestratorService(repository)
    return repository, material_service, pipeline_service, edital_service, alignment_service, graph_service, cycle_service


def register_processed_material(
    material_service: MaterialService,
    pipeline_service: DocumentPipelineService,
    *,
    user_id: str,
    filename: str,
    content_type: str,
    payload: bytes,
):
    uploaded = material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        payload=payload,
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id=user_id)
    return uploaded


def prepare_cycle_context(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service, graph_service, cycle_service = create_services(tmp_path)
    edital = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="edital.md",
        content_type="text/markdown",
        payload=EDITAL_TEXT,
    )
    edital_service.ingest_document(edital.metadata.document_id, user_id="user-a")
    register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="silva_navegacao_costeira_2020.md",
        content_type="text/markdown",
        payload=b"# Navegacao Costeira\n\nArte Naval aplicada a navegacao costeira.",
    )
    register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="ripeam_comentado_2021.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nRIPEAM comentado com regras de navegacao.",
    )
    register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="ripeam_resumo_2021.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nResumo de RIPEAM e regras de governo e rumo.",
    )
    register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="meteorologia_cartas_sinoticas.md",
        content_type="text/markdown",
        payload=b"# Meteorologia\n\nVentos e cartas sinoticas para navegacao.",
    )
    register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="autoridade_maritima_aplicada.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    edital_id = f"edital:{edital.metadata.document_id}"
    alignment_service.align_edital(edital_id, user_id="user-a")
    graph_service.build_graph(edital_id, user_id="user-a")
    graph = repository.get_curriculum_graph(edital_id, user_id="user-a")
    return {
        "repository": repository,
        "cycle_service": cycle_service,
        "graph_id": graph.graph_id,
    }


def test_study_cycle_handles_missing_graph_and_partial_graph_safely(tmp_path):
    repository, _, _, _, _, _, cycle_service = create_services(tmp_path)

    missing_state = cycle_service.build_cycle("graph:missing", user_id="user-a")
    assert missing_state is not None
    assert missing_state.status == "insufficient_graph"

    from app.domain.models import CurriculumGraph

    graph = CurriculumGraph(
        graph_id="graph:empty",
        edital_id="edital:empty",
        user_id="user-a",
        subjects=[],
        topics=[],
        subtopics=[],
    )
    repository.save_curriculum_graph(graph, user_id="user-a")
    state = cycle_service.build_cycle("graph:empty", user_id="user-a")
    plan = repository.get_study_cycle_plan("graph:empty", user_id="user-a")

    assert state is not None
    assert state.status == "insufficient_graph"
    assert plan is not None
    assert plan.topic_slots == []
    assert any(item.code == "insufficient_curriculum_graph" for item in plan.warnings)


def test_study_cycle_creates_subject_rotations_topic_slots_review_slots_and_gap_slots(tmp_path):
    context = prepare_cycle_context(tmp_path)
    repository = context["repository"]
    cycle_service = context["cycle_service"]
    graph_id = context["graph_id"]

    state = cycle_service.build_cycle(graph_id, user_id="user-a")
    plan = repository.get_study_cycle_plan(graph_id, user_id="user-a")

    assert state is not None
    assert state.status == "ready_for_review"
    assert state.subject_count >= 1
    assert state.topic_slot_count >= 4
    assert state.review_slot_count >= 2
    assert state.gap_slot_count >= 1
    assert plan is not None
    assert plan.subject_rotations
    assert plan.topic_slots
    assert plan.review_slots
    assert plan.gap_slots

    slot_types = {item.slot_type for item in plan.topic_slots}
    actions = {item.suggested_action for item in plan.topic_slots}
    assert "reinforce" in slot_types
    assert "review_needed" in slot_types or "weak_topic_resurfacing" in slot_types or "ambiguous_review" in slot_types
    assert "ocr_blocked" in slot_types or "gap_blocked" in slot_types
    assert "reinforce_with_existing_material" in actions
    assert "process_ocr_material" in actions or "resolve_material_gap" in actions


def test_study_cycle_computes_fatigue_balance_and_rationale_conservatively(tmp_path):
    context = prepare_cycle_context(tmp_path)
    repository = context["repository"]
    cycle_service = context["cycle_service"]
    graph_id = context["graph_id"]

    cycle_service.build_cycle(graph_id, user_id="user-a")
    plan = repository.get_study_cycle_plan(graph_id, user_id="user-a")

    assert plan is not None
    assert plan.fatigue_profile.fatigue_risk_level in {"low", "moderate", "high", "unknown"}
    assert plan.fatigue_profile.high_intensity_topic_count >= 0
    assert plan.balance_summary.balance_state in {
        "balanced_candidate",
        "coverage_heavy",
        "gap_heavy",
        "review_heavy",
        "material_blocked",
        "insufficient_graph",
    }
    assert plan.rationale.summary
    assert plan.rationale.reasons
    assert plan.rationale.limitations
    assert plan.rationale.source_graph_id == graph_id
    assert 0.0 <= plan.rationale.confidence <= 1.0


def test_study_cycle_repository_round_trip_and_determinism_are_json_safe(tmp_path):
    context = prepare_cycle_context(tmp_path)
    repository = context["repository"]
    cycle_service = context["cycle_service"]
    graph_id = context["graph_id"]

    first = cycle_service.build_cycle(graph_id, user_id="user-a")
    second = cycle_service.build_cycle(graph_id, user_id="user-a")
    plan = repository.get_study_cycle_plan(graph_id, user_id="user-a")
    listed = repository.list_user_study_cycle_plans(user_id="user-a")

    assert first is not None and second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert plan is not None
    assert len(listed) == 1
    assert listed[0].cycle_id == plan.cycle_id
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(plan.model_dump(mode="json"), ensure_ascii=True)
