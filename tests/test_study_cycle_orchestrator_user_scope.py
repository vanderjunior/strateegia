import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService


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


def test_user_scope_blocks_cross_user_study_cycle_build_and_reads(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service, graph_service, cycle_service = create_services(tmp_path)
    edital = material_service.register_upload(
        user_id="owner",
        original_filename="edital.md",
        content_type="text/markdown",
        payload=b"# Conteudo Programatico\n\n1. RIPEAM\n\n# Bibliografia\n\nBRASIL. RIPEAM Comentado. 2021.",
    )
    pipeline_service.process_document(edital.metadata.document_id, user_id="owner")
    edital_service.ingest_document(edital.metadata.document_id, user_id="owner")
    support = material_service.register_upload(
        user_id="owner",
        original_filename="ripeam_comentado_2021.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nRegras de governo e rumo.",
    )
    pipeline_service.process_document(support.metadata.document_id, user_id="owner")
    support_pdf = material_service.register_upload(
        user_id="owner",
        original_filename="autoridade_maritima_aplicada.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    pipeline_service.process_document(support_pdf.metadata.document_id, user_id="owner")

    edital_id = f"edital:{edital.metadata.document_id}"
    alignment_service.align_edital(edital_id, user_id="owner")
    graph_service.build_graph(edital_id, user_id="owner")
    graph = repository.get_curriculum_graph(edital_id, user_id="owner")
    owner_state = cycle_service.build_cycle(graph.graph_id, user_id="owner")

    assert owner_state is not None
    assert owner_state.status == "ready_for_review"
    assert repository.get_study_cycle_plan(graph.graph_id, user_id="owner") is not None
    assert cycle_service.build_cycle(graph.graph_id, user_id="other").status == "insufficient_graph"
    assert repository.get_study_cycle_plan(graph.graph_id, user_id="other") is None
    assert repository.get_study_cycle_plan_by_id(owner_state.cycle_id, user_id="other") is None
