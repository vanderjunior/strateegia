import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
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
    return repository, material_service, pipeline_service, edital_service, alignment_service


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


def prepare_alignment_context(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service = create_services(tmp_path)
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
    return {
        "repository": repository,
        "alignment_service": alignment_service,
        "edital_document_id": edital.metadata.document_id,
        "material_ids": {
            "silva": silva.metadata.document_id,
            "ripeam_a": ripeam_a.metadata.document_id,
            "ripeam_b": ripeam_b.metadata.document_id,
            "meteorologia": meteorologia.metadata.document_id,
            "ocr_pdf": ocr_pdf.metadata.document_id,
        },
    }


def test_alignment_handles_missing_materials_safely(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service = create_services(tmp_path)
    edital = register_processed_material(
        material_service,
        pipeline_service,
        user_id="user-a",
        filename="edital.md",
        content_type="text/markdown",
        payload=EDITAL_TEXT,
    )
    edital_service.ingest_document(edital.metadata.document_id, user_id="user-a")

    state = alignment_service.align_edital(f"edital:{edital.metadata.document_id}", user_id="user-a")
    result = repository.get_bibliography_alignment_result(f"edital:{edital.metadata.document_id}", user_id="user-a")

    assert state is not None
    assert state.status == "insufficient_materials"
    assert "no_candidate_materials_available" in state.warnings
    assert result is not None
    assert result.bibliography_alignments == []
    assert result.topic_coverage == []


def test_alignment_matches_bibliography_estimates_topic_coverage_and_detects_gaps_and_redundancy(tmp_path):
    context = prepare_alignment_context(tmp_path)
    repository = context["repository"]
    alignment_service = context["alignment_service"]
    edital_id = f"edital:{context['edital_document_id']}"

    state = alignment_service.align_edital(edital_id, user_id="user-a")
    result = repository.get_bibliography_alignment_result(edital_id, user_id="user-a")

    assert state is not None
    assert state.status == "ready_for_review"
    assert state.bibliography_items_total >= 3
    assert state.bibliography_items_matched >= 2
    assert state.topics_total >= 4
    assert state.topics_with_coverage >= 3
    assert result is not None
    assert result.bibliography_alignments
    assert result.topic_coverage
    assert result.document_coverage
    assert all(0.0 <= item.confidence <= 1.0 for item in result.bibliography_alignments)
    assert all(item.reasoning for item in result.bibliography_alignments)
    assert all(item.evidence for item in result.bibliography_alignments)
    assert all(len(evidence.excerpt) <= 160 for item in result.bibliography_alignments for evidence in item.evidence)

    nav_alignment = next(item for item in result.bibliography_alignments if "Navegacao Costeira" in item.raw_reference)
    assert nav_alignment.match_state == "matched"
    assert context["material_ids"]["silva"] in nav_alignment.matched_document_ids

    ripeam_alignment = next(item for item in result.bibliography_alignments if "RIPEAM Comentado" in item.raw_reference)
    assert ripeam_alignment.match_state in {"matched", "ambiguous"}
    assert len(ripeam_alignment.candidate_matches) >= 1

    meteorologia_topic = next(item for item in result.topic_coverage if item.topic_title == "Meteorologia")
    assert meteorologia_topic.coverage_state in {"covered", "partially_covered"}
    assert context["material_ids"]["meteorologia"] in meteorologia_topic.matched_document_ids

    autoridade_topic = next(item for item in result.topic_coverage if item.topic_title == "Autoridade Maritima")
    assert autoridade_topic.coverage_state in {"weakly_covered", "uncovered"}

    gap_types = {gap.gap_type for gap in result.gaps}
    assert "ocr_required" in gap_types
    assert "missing_bibliography_material" in gap_types or "uncovered_topic" in gap_types

    redundancy_types = {item.redundancy_type for item in result.redundancies}
    assert "overlapping_topic_coverage" in redundancy_types or "duplicate_bibliography_match" in redundancy_types

    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)


def test_alignment_is_deterministic_and_repository_round_trip_is_json_safe(tmp_path):
    context = prepare_alignment_context(tmp_path)
    repository = context["repository"]
    alignment_service = context["alignment_service"]
    edital_id = f"edital:{context['edital_document_id']}"

    first = alignment_service.align_edital(edital_id, user_id="user-a")
    second = alignment_service.align_edital(edital_id, user_id="user-a")
    result = repository.get_bibliography_alignment_result(edital_id, user_id="user-a")
    listed = repository.list_user_bibliography_alignments(user_id="user-a")

    assert first is not None and second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert result is not None
    assert len(listed) == 1
    assert listed[0].alignment_id == result.alignment_id
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
