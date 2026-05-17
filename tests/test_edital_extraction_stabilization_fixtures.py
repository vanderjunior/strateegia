from __future__ import annotations

import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService
from tests.fixtures.edital_documents import (
    basic_numbered_program_edital_text,
    bibliography_block_edital_text,
    cebraspe_style_edital_text,
    colon_subtopics_program_edital_text,
    exam_structure_with_weights_edital_text,
    exclusions_block_edital_text,
    fgv_style_edital_text,
    low_text_edital_text,
    marinha_pscpp_style_edital_text,
    mixed_sections_edital_text,
    noisy_mixed_format_edital_text,
    semicolon_inline_program_edital_text,
)


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


def ingest_markdown_fixture(tmp_path, text: str, *, user_id: str = "user-a"):
    repository, material_service, pipeline_service, edital_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id=user_id,
        original_filename="edital.md",
        content_type="text/markdown",
        payload=text.encode("utf-8"),
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id=user_id)
    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id=user_id)
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id=user_id)
    return repository, uploaded, state, result, edital_service


def ingest_ocr_required_fixture(tmp_path):
    repository, material_service, pipeline_service, edital_service = create_services(tmp_path)
    uploaded = material_service.register_upload(
        user_id="user-a",
        original_filename="edital.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes(""),
    )
    pipeline_service.process_document(uploaded.metadata.document_id, user_id="user-a")
    state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")
    return repository, uploaded, state, result


def test_fixture_sanity_and_json_safety():
    fixtures = [
        basic_numbered_program_edital_text(),
        colon_subtopics_program_edital_text(),
        semicolon_inline_program_edital_text(),
        bibliography_block_edital_text(),
        exclusions_block_edital_text(),
        exam_structure_with_weights_edital_text(),
        mixed_sections_edital_text(),
        marinha_pscpp_style_edital_text(),
        cebraspe_style_edital_text(),
        fgv_style_edital_text(),
        low_text_edital_text(),
        noisy_mixed_format_edital_text(),
    ]

    assert all(isinstance(item, str) for item in fixtures)
    assert all(item == item for item in fixtures)
    assert all(item.strip() for item in fixtures[:-1] + [fixtures[-1]])
    assert low_text_edital_text().strip() == "OK"
    json.dumps(fixtures, ensure_ascii=True)


def test_basic_numbered_program_fixture_extracts_expected_topics_in_stable_order(tmp_path):
    _, _, state, result, _ = ingest_markdown_fixture(tmp_path, basic_numbered_program_edital_text())

    assert state.status == "ready_for_review"
    assert result is not None
    assert any(section.section_type == "content_program" for section in result.sections)
    assert [topic.title for topic in result.topics[:4]] == [
        "Arte Naval",
        "RIPEAM",
        "Meteorologia",
        "Legislacao Maritima",
    ]
    assert all(0.0 <= topic.confidence <= 1.0 for topic in result.topics)
    assert all(topic.reasoning for topic in result.topics)
    assert all(len(topic.source_excerpt) <= 160 for topic in result.topics)


def test_colon_subtopics_fixture_preserves_parent_relationship_and_order(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, colon_subtopics_program_edital_text())

    assert result is not None
    assert [topic.title for topic in result.topics] == ["Meteorologia", "Legislacao Maritima"]
    meteorologia = result.topics[0]
    subs = [item.title for item in result.subtopics if item.parent_topic_id == meteorologia.topic_id]
    assert subs == ["ventos", "pressao atmosferica", "frentes frias", "cartas sinoticas"]


def test_semicolon_inline_fixture_extracts_conservative_candidates_without_crashing(tmp_path):
    _, _, state, result, _ = ingest_markdown_fixture(tmp_path, semicolon_inline_program_edital_text())

    assert state.status == "ready_for_review"
    assert result is not None
    assert len(result.topics) >= 1
    assert len(result.subtopics) >= 3
    assert all(item.reasoning for item in result.subtopics)


def test_bibliography_block_fixture_extracts_reference_candidates(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, bibliography_block_edital_text())

    assert result is not None
    assert any(section.section_type == "bibliography" for section in result.sections)
    assert len(result.bibliography) >= 2
    assert all(item.raw_reference for item in result.bibliography)
    assert all(item.reasoning for item in result.bibliography)


def test_exclusions_block_fixture_extracts_exclusion_candidates(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, exclusions_block_edital_text())

    assert result is not None
    assert len(result.exclusions) >= 2
    assert all(item.reasoning for item in result.exclusions)
    assert all(len(item.source_excerpt) <= 160 for item in result.exclusions)


def test_exam_structure_fixture_extracts_weight_hints_only_as_hints(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, exam_structure_with_weights_edital_text())

    assert result is not None
    assert any(section.section_type == "exam_structure" for section in result.sections)
    weight_types = {item.weight_type for item in result.weight_hints}
    assert "question_count" in weight_types
    assert "explicit_points" in weight_types or "percentage" in weight_types
    assert all(item.reasoning for item in result.weight_hints)


def test_mixed_sections_fixture_detects_multiple_candidate_groups(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, mixed_sections_edital_text())

    assert result is not None
    section_types = {section.section_type for section in result.sections}
    assert {"content_program", "bibliography", "exclusions", "exam_structure"} <= section_types
    assert result.topics
    assert result.bibliography
    assert result.exclusions
    assert result.weight_hints


def test_marinha_style_fixture_extracts_maritime_topics_without_profile_behavior(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, marinha_pscpp_style_edital_text())

    assert result is not None
    titles = [topic.title for topic in result.topics]
    for expected in ["Arte Naval", "RIPEAM", "Manobra", "Meteorologia", "Legislacao Maritima"]:
        assert expected in titles
    assert result.metadata.get("source_section_count", 0) >= 1


def test_cebraspe_style_fixture_detects_exam_structure_and_question_hint(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, cebraspe_style_edital_text())

    assert result is not None
    assert any(section.section_type == "exam_structure" for section in result.sections)
    assert any(item.weight_type == "question_count" for item in result.weight_hints)
    assert len(result.topics) >= 3


def test_fgv_style_fixture_detects_exam_structure_and_topics(tmp_path):
    _, _, _, result, _ = ingest_markdown_fixture(tmp_path, fgv_style_edital_text())

    assert result is not None
    assert any(section.section_type == "exam_structure" for section in result.sections)
    assert len(result.topics) >= 3


def test_low_text_fixture_returns_safe_insufficient_text_state(tmp_path):
    _, _, state, result, _ = ingest_markdown_fixture(tmp_path, low_text_edital_text())

    assert state.status == "insufficient_text"
    assert result is not None
    assert result.topics == []
    assert "insufficient_text_for_edital_ingestion" in state.warnings


def test_ocr_required_fixture_returns_safe_warning_without_fake_topics(tmp_path):
    _, _, state, result = ingest_ocr_required_fixture(tmp_path)

    assert state.status == "insufficient_text"
    assert result is not None
    assert result.topics == []
    assert "ocr_required_before_edital_ingestion" in state.warnings


def test_noisy_mixed_format_fixture_stays_conservative_and_does_not_crash(tmp_path):
    _, _, state, result, _ = ingest_markdown_fixture(tmp_path, noisy_mixed_format_edital_text())

    assert state.status == "ready_for_review"
    assert result is not None
    assert any(topic.title == "Arte Naval" for topic in result.topics)
    assert any(topic.title == "Meteorologia" for topic in result.topics)
    assert len(result.topics) <= 6


def test_fixture_ingestion_is_idempotent_deterministic_and_json_safe(tmp_path):
    repository, uploaded, first_state, first_result, edital_service = ingest_markdown_fixture(
        tmp_path,
        mixed_sections_edital_text(),
    )

    second_state = edital_service.ingest_document(uploaded.metadata.document_id, user_id="user-a")
    second_result = repository.get_edital_extraction_result(uploaded.metadata.document_id, user_id="user-a")

    assert second_state is not None
    assert first_state.model_dump(mode="json") == second_state.model_dump(mode="json")
    assert first_result is not None and second_result is not None
    assert first_result.model_dump(mode="json") == second_result.model_dump(mode="json")
    assert [item.topic_id for item in first_result.topics] == [item.topic_id for item in second_result.topics]
    json.dumps(second_result.model_dump(mode="json"), ensure_ascii=True)
