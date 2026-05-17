import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService


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
    return repository, material_service, pipeline_service, edital_service, alignment_service, graph_service


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


def prepare_graph_context(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service, graph_service = create_services(tmp_path)
    edital = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="edital.md",
        content_type="text/markdown",
        payload=EDITAL_TEXT,
    )
    edital_service.ingest_document(edital.metadata.document_id, user_id="user-a")
    silva = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="silva_navegacao_costeira_2020.md",
        content_type="text/markdown",
        payload=b"# Navegacao Costeira\n\nArte Naval aplicada a navegacao costeira.",
    )
    ripeam_a = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="ripeam_comentado_2021.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nRIPEAM comentado com regras de navegacao.",
    )
    ripeam_b = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="ripeam_resumo_2021.md",
        content_type="text/markdown",
        payload=b"# RIPEAM\n\nResumo de RIPEAM e regras de governo e rumo.",
    )
    meteorologia = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="meteorologia_cartas_sinoticas.md",
        content_type="text/markdown",
        payload=b"# Meteorologia\n\nVentos e cartas sinoticas para navegacao.",
    )
    ocr_pdf = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="autoridade_maritima_aplicada.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    edital_id = f"edital:{edital.metadata.document_id}"
    alignment_service.align_edital(edital_id, user_id="user-a")
    return {
        "repository": repository,
        "graph_service": graph_service,
        "edital_id": edital_id,
        "material_ids": {
            "silva": silva.metadata.document_id,
            "ripeam_a": ripeam_a.metadata.document_id,
            "ripeam_b": ripeam_b.metadata.document_id,
            "meteorologia": meteorologia.metadata.document_id,
            "ocr_pdf": ocr_pdf.metadata.document_id,
        },
    }


def test_graph_builder_handles_missing_edital_and_missing_alignment_safely(tmp_path):
    repository, material_service, pipeline_service, edital_service, _, graph_service = create_services(tmp_path)

    missing_edital_state = graph_service.build_graph("edital:missing", user_id="user-a")
    assert missing_edital_state is not None
    assert missing_edital_state.status == "insufficient_edital"

    edital = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="edital.md",
        content_type="text/markdown",
        payload=EDITAL_TEXT,
    )
    edital_service.ingest_document(edital.metadata.document_id, user_id="user-a")
    edital_id = f"edital:{edital.metadata.document_id}"

    state = graph_service.build_graph(edital_id, user_id="user-a")
    graph = repository.get_curriculum_graph(edital_id, user_id="user-a")

    assert state is not None
    assert state.status == "insufficient_alignment"
    assert graph is not None
    assert graph.subjects
    assert graph.topics
    assert graph.coverage_links == []
    assert any(item.code == "missing_bibliography_alignment" for item in graph.warnings)


def test_graph_builder_creates_candidate_subject_topic_and_subtopic_graph(tmp_path):
    context = prepare_graph_context(tmp_path)
    repository = context["repository"]
    graph_service = context["graph_service"]
    edital_id = context["edital_id"]

    state = graph_service.build_graph(edital_id, user_id="user-a")
    graph = repository.get_curriculum_graph(edital_id, user_id="user-a")

    assert state is not None
    assert state.status == "ready_for_review"
    assert state.subject_count >= 1
    assert state.topic_count >= 4
    assert state.subtopic_count >= 2
    assert graph is not None
    assert graph.subjects
    assert graph.topics
    assert graph.subtopics
    assert graph.coverage_links
    assert graph.summary.topic_count == len(graph.topics)
    assert graph.summary.subtopic_count == len(graph.subtopics)
    assert graph.summary.gap_count == len(graph.gaps)
    assert graph.summary.redundancy_count == len(graph.redundancies)

    topic_titles = [item.title for item in graph.topics]
    assert topic_titles[:4] == ["Arte Naval", "Meteorologia", "RIPEAM", "Autoridade Maritima"]
    meteorologia = next(item for item in graph.topics if item.title == "Meteorologia")
    ripeam = next(item for item in graph.topics if item.title == "RIPEAM")
    autoridade = next(item for item in graph.topics if item.title == "Autoridade Maritima")

    assert meteorologia.coverage_state in {"covered", "partially_covered"}
    assert meteorologia.review_state in {"candidate", "ready_for_review"}
    assert ripeam.coverage_state in {"covered", "partially_covered"}
    assert autoridade.review_state in {"ocr_required", "needs_review", "source_missing"}
    assert all(0.0 <= item.confidence <= 1.0 for item in graph.topics)
    assert all(item.reasoning for item in graph.topics)
    assert all(len(item.excerpt) <= 160 for link in graph.coverage_links for item in link.evidence)
    json.dumps(graph.model_dump(mode="json"), ensure_ascii=True)


def test_graph_preserves_gaps_redundancies_and_summary_counts(tmp_path):
    context = prepare_graph_context(tmp_path)
    repository = context["repository"]
    graph_service = context["graph_service"]
    edital_id = context["edital_id"]

    graph_service.build_graph(edital_id, user_id="user-a")
    graph = repository.get_curriculum_graph(edital_id, user_id="user-a")

    assert graph is not None
    gap_types = {item.gap_type for item in graph.gaps}
    redundancy_types = {item.redundancy_type for item in graph.redundancies}

    assert "ocr_required" in gap_types
    assert "missing_bibliography_material" in gap_types or "uncovered_topic" in gap_types
    assert "duplicate_bibliography_match" in redundancy_types or "overlapping_topic_coverage" in redundancy_types
    assert graph.summary.ocr_required_count >= 1
    assert graph.summary.needs_review_count >= 1


def test_graph_repository_round_trip_and_determinism_are_json_safe(tmp_path):
    context = prepare_graph_context(tmp_path)
    repository = context["repository"]
    graph_service = context["graph_service"]
    edital_id = context["edital_id"]

    first = graph_service.build_graph(edital_id, user_id="user-a")
    second = graph_service.build_graph(edital_id, user_id="user-a")
    graph = repository.get_curriculum_graph(edital_id, user_id="user-a")
    listed = repository.list_user_curriculum_graphs(user_id="user-a")

    assert first is not None and second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert graph is not None
    assert len(listed) == 1
    assert listed[0].graph_id == graph.graph_id
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(graph.model_dump(mode="json"), ensure_ascii=True)
