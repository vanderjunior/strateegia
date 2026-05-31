import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService


EDITAL_MARKDOWN = b"""# Conteudo Programatico

1. Arte Naval
2. Meteorologia: ventos; pressao; frentes; cartas sinoticas
3. Legislacao Maritima: autoridade maritima, infracoes

# Bibliografia

SILVA, Joao. Navegacao Costeira. 3. ed. Atlas, 2020.
BRASIL. Regulamento Internacional Para Evitar Abalroamento no Mar. 2018.

# Exclusoes

Nao sera cobrado: sistemas militares sigilosos.

# Estrutura da Prova

Prova objetiva: 20 questoes, 40 pontos, 50%.
"""

STRUCTURED_TOPIC_SUBTOPIC_EDITAL = b"""# Conteudo Programatico

Lingua Portuguesa:
1.1 Compreensao e interpretacao de textos.
1.2 Ortografia oficial.
1.3 Pontuacao.

Informatica:
2.1 Redes de computadores.
2.2 Seguranca da informacao.
2.3 Banco de dados.

Direito Administrativo:
- Atos administrativos.
- Poderes administrativos.
- Responsabilidade civil do Estado.

# Bibliografia

BRASIL. Constituicao da Republica Federativa do Brasil. 1988.
MANUAL DE QA. Referencia simulada para teste interno. 2026.
"""


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    edital_service = EditalIngestionService(repository)
    return repository, material_service, pipeline_service, edital_service


def build_pdf_bytes(*pages: str) -> bytes:
    document = fitz.open()
    for page_text in pages or ("",):
        page = document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


def prepare_processed_material(tmp_path, *, user_id: str = "user-a", filename: str = "edital.md", payload: bytes = EDITAL_MARKDOWN):
    repository, material_service, pipeline_service, edital_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type="text/markdown",
        payload=payload,
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id=user_id)
    return repository, uploaded, edital_service


def test_edital_ingestion_extracts_candidate_sections_topics_subtopics_bibliography_and_weights(tmp_path):
    repository, uploaded, edital_service = prepare_processed_material(tmp_path)

    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    events = repository.list_edital_ingestion_events(uploaded.metadata.document_id, user_id="user-a")

    assert state.status == "ready_for_review"
    assert state.sections_detected >= 4
    assert state.topics_detected >= 3
    assert state.subtopics_detected >= 4
    assert state.bibliography_items_detected >= 2
    assert state.exclusions_detected >= 1
    assert state.weight_hints_detected >= 3
    assert result is not None
    assert {section.section_type for section in result.sections} >= {
        "content_program",
        "bibliography",
        "exclusions",
        "exam_structure",
    }
    assert [topic.title for topic in result.topics[:2]] == ["Arte Naval", "Meteorologia"]
    assert any(subtopic.title == "ventos" for subtopic in result.subtopics)
    assert any("Navegacao Costeira" in item.raw_reference for item in result.bibliography)
    assert any("Nao sera cobrado" in item.text for item in result.exclusions)
    assert {hint.weight_type for hint in result.weight_hints} >= {"question_count", "explicit_points", "percentage"}
    assert all(0.0 <= item.confidence <= 1.0 for item in result.sections)
    assert all(topic.reasoning for topic in result.topics)
    assert events
    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)


def test_edital_ingestion_preserves_subjects_and_bounded_subtopics_separately(tmp_path):
    repository, uploaded, edital_service = prepare_processed_material(
        tmp_path,
        filename="edital-estruturado.md",
        payload=STRUCTURED_TOPIC_SUBTOPIC_EDITAL,
    )

    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.status == "ready_for_review"
    assert state.topics_detected == 3
    assert state.subtopics_detected == 9
    assert state.bibliography_items_detected == 2
    assert result is not None
    assert [topic.title for topic in result.topics] == [
        "Lingua Portuguesa",
        "Informatica",
        "Direito Administrativo",
    ]
    assert [subtopic.title for subtopic in result.subtopics] == [
        "Compreensao e interpretacao de textos",
        "Ortografia oficial",
        "Pontuacao",
        "Redes de computadores",
        "Seguranca da informacao",
        "Banco de dados",
        "Atos administrativos",
        "Poderes administrativos",
        "Responsabilidade civil do Estado",
    ]
    assert all("Constituicao" not in topic.title for topic in result.topics)
    assert all("Constituicao" not in subtopic.title for subtopic in result.subtopics)


def test_ocr_required_source_returns_insufficient_text_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    edital_service = EditalIngestionService(repository)

    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="escaneado.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")

    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert state.status == "insufficient_text"
    assert "ocr_required_before_edital_ingestion" in state.warnings
    assert result is not None
    assert result.sections == []
    assert result.topics == []


def test_repeated_ingestion_is_deterministic_and_repository_round_trip_is_safe(tmp_path):
    repository, uploaded, edital_service = prepare_processed_material(tmp_path)

    first = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    second = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    listed = repository.list_user_edital_extractions(user_id="user-a")
    events = repository.list_edital_ingestion_events(uploaded.metadata.document_id, user_id="user-a")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert result is not None
    assert len(listed) == 1
    assert listed[0].edital_id == result.edital_id
    assert len(events) >= 1
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)
