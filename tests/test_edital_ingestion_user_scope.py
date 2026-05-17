from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    material_service = MaterialService(repository, storage_root=storage_root)
    pipeline_service = DocumentPipelineService(repository, storage_root=storage_root)
    edital_service = EditalIngestionService(repository)
    return repository, material_service, pipeline_service, edital_service


def test_user_scope_blocks_cross_user_edital_ingestion_and_reads(tmp_path):
    repository, material_service, pipeline_service, edital_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id="owner",
        original_filename="edital.md",
        content_type="text/markdown",
        payload=b"# Conteudo Programatico\n\n1. Arte Naval",
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id="owner")

    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="owner")

    assert state.status == "ready_for_review"
    assert edital_service.ingest_document(uploaded.metadata.document_id, user_id="other") is None
    assert repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="other") is None
    assert repository.get_edital_ingestion_state(uploaded.metadata.document_id, user_id="other") is None

