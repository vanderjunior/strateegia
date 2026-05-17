import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService


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


def test_user_scope_blocks_cross_user_bibliography_alignment_and_reads(tmp_path):
    repository, material_service, pipeline_service, edital_service, alignment_service = create_services(tmp_path)
    edital = material_service.register_upload(
        user_id="owner",
        original_filename="edital.md",
        content_type="text/markdown",
        payload=b"# Conteudo Programatico\n\n1. Arte Naval\n\n# Bibliografia\n\nSILVA, Joao. Navegacao Costeira. 2020.",
    )
    pipeline_service.process_document(edital.metadata.document_id, user_id="owner")
    edital_service.ingest_document(edital.metadata.document_id, user_id="owner")
    support = material_service.register_upload(
        user_id="owner",
        original_filename="silva_navegacao_costeira_2020.md",
        content_type="text/markdown",
        payload=b"# Navegacao Costeira\n\nArte Naval.",
    )
    pipeline_service.process_document(support.metadata.document_id, user_id="owner")

    owner_state = alignment_service.align_edital(f"edital:{edital.metadata.document_id}", user_id="owner")

    assert owner_state is not None
    assert alignment_service.align_edital(f"edital:{edital.metadata.document_id}", user_id="other") is None
    assert repository.get_bibliography_alignment_result(f"edital:{edital.metadata.document_id}", user_id="other") is None
    assert repository.get_bibliography_alignment_by_id(owner_state.alignment_id, user_id="other") is None
