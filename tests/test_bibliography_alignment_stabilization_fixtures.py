import json

import fitz

from app.repositories.json_store import JsonStudyRepository
from app.services.bibliography_alignment import BibliographyAlignmentService
from app.services.document_pipeline import DocumentPipelineService
from app.services.edital_ingestion import EditalIngestionService
from app.services.material_service import MaterialService
from tests.fixtures.bibliography_alignment_documents import (
    ALL_BIBLIOGRAPHY_ALIGNMENT_FIXTURES,
    ambiguous_duplicate_material_fixture,
    exact_bibliography_match_fixture,
    generic_year_overlap_fixture,
    maritime_praticagem_alignment_fixture,
    mixed_alignment_fixture,
    multiple_documents_same_topic_redundancy_fixture,
    no_materials_alignment_fixture,
    ocr_required_material_gap_fixture,
    partial_author_title_match_fixture,
    topic_covered_by_chunk_fixture,
    topic_covered_by_section_fixture,
    unmatched_bibliography_fixture,
    unprocessed_material_fixture,
    weak_generic_overlap_fixture,
)


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


def register_material(
    material_service: MaterialService,
    *,
    user_id: str,
    filename: str,
    content_type: str,
    text: str | None = None,
    pdf_pages: list[str] | None = None,
):
    if content_type == "application/pdf":
        payload = build_pdf_bytes(*(pdf_pages or [""]))
    else:
        payload = (text or "").encode("utf-8")
    return material_service.register_upload(
        user_id=user_id,
        original_filename=filename,
        content_type=content_type,
        payload=payload,
    )


def run_alignment_fixture(tmp_path, fixture: dict[str, object], *, user_id: str = "user-a") -> dict[str, object]:
    repository, material_service, pipeline_service, edital_service, alignment_service = create_services(tmp_path)
    edital = register_material(
        material_service,
        user_id=user_id,
        filename="edital.md",
        content_type="text/markdown",
        text=str(fixture["edital_text"]),
    )
    pipeline_service.process_document(edital.metadata.document_id, user_id=user_id)
    edital_service.ingest_document(edital.metadata.document_id, user_id=user_id)

    material_ids: dict[str, str] = {}
    for spec in fixture["materials"]:
        uploaded = register_material(
            material_service,
            user_id=user_id,
            filename=spec["filename"],
            content_type=spec["content_type"],
            text=spec.get("text"),
            pdf_pages=spec.get("pdf_pages"),
        )
        material_ids[spec["alias"]] = uploaded.metadata.document_id
        if spec.get("process", True):
            pipeline_service.process_document(uploaded.metadata.document_id, user_id=user_id)

    edital_id = f"edital:{edital.metadata.document_id}"
    state = alignment_service.align_edital(edital_id, user_id=user_id)
    result = repository.get_bibliography_alignment_result(edital_id, user_id=user_id)
    return {
        "repository": repository,
        "state": state,
        "result": result,
        "edital_id": edital_id,
        "material_ids": material_ids,
    }


def assert_alignment_json_safe(payload) -> None:
    dumped = json.dumps(payload.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def assert_candidate_metadata(result) -> None:
    for item in result.bibliography_alignments:
        assert 0.0 <= item.confidence <= 1.0
        assert item.reasoning
        for evidence in item.evidence:
            assert len(evidence.excerpt) <= 160
    for item in result.topic_coverage:
        assert 0.0 <= item.confidence <= 1.0
        assert item.reasoning
        for evidence in item.evidence:
            assert len(evidence.excerpt) <= 160


def topic_by_title(result, title: str):
    return next(item for item in result.topic_coverage if item.topic_title == title)


def bibliography_by_text(result, snippet: str):
    return next(item for item in result.bibliography_alignments if snippet in item.raw_reference)


def test_alignment_fixture_sanity_is_deterministic_and_json_safe():
    for builder in ALL_BIBLIOGRAPHY_ALIGNMENT_FIXTURES:
        first = builder()
        second = builder()
        assert first == second
        assert isinstance(first["edital_text"], str)
        assert len(first["edital_text"]) < 6000
        json.dumps(first, ensure_ascii=True)
        if builder is not no_materials_alignment_fixture:
            assert first["edital_text"].strip()


def test_exact_and_partial_bibliography_matches_remain_conservative(tmp_path):
    exact_context = run_alignment_fixture(tmp_path / "exact", exact_bibliography_match_fixture())
    partial_context = run_alignment_fixture(tmp_path / "partial", partial_author_title_match_fixture())
    exact_result = exact_context["result"]
    partial_result = partial_context["result"]

    exact_alignment = exact_result.bibliography_alignments[0]
    partial_alignment = partial_result.bibliography_alignments[0]

    assert exact_alignment.match_state == "matched"
    assert exact_context["material_ids"]["nav_exact"] in exact_alignment.matched_document_ids
    assert exact_alignment.evidence
    assert exact_alignment.evidence[0].matched_terms
    assert partial_alignment.match_state in {"matched", "partially_matched"}
    assert partial_alignment.confidence <= exact_alignment.confidence
    assert partial_alignment.reasoning
    assert_alignment_json_safe(exact_result)
    assert_alignment_json_safe(partial_result)


def test_generic_overlap_does_not_create_high_confidence_false_positive_and_unmatched_creates_gap(tmp_path):
    generic_context = run_alignment_fixture(tmp_path / "generic", generic_year_overlap_fixture())
    unmatched_context = run_alignment_fixture(tmp_path / "unmatched", unmatched_bibliography_fixture())
    generic_result = generic_context["result"]
    unmatched_result = unmatched_context["result"]

    generic_alignment = generic_result.bibliography_alignments[0]
    unmatched_alignment = unmatched_result.bibliography_alignments[0]

    assert generic_alignment.match_state in {"unmatched", "partially_matched"}
    assert generic_alignment.confidence < 0.65
    assert unmatched_alignment.match_state == "unmatched"
    assert any(gap.gap_type == "missing_bibliography_material" for gap in unmatched_result.gaps)
    assert unmatched_alignment.reasoning
    assert_alignment_json_safe(generic_result)
    assert_alignment_json_safe(unmatched_result)


def test_ambiguous_duplicate_materials_and_mixed_alignment_emit_redundancy_and_gaps(tmp_path):
    ambiguous_context = run_alignment_fixture(tmp_path / "ambiguous", ambiguous_duplicate_material_fixture())
    mixed_context = run_alignment_fixture(tmp_path / "mixed", mixed_alignment_fixture())
    ambiguous_result = ambiguous_context["result"]
    mixed_result = mixed_context["result"]

    ambiguous_alignment = ambiguous_result.bibliography_alignments[0]
    assert ambiguous_alignment.match_state == "ambiguous"
    assert len(ambiguous_alignment.candidate_matches) >= 2
    assert any(item.redundancy_type == "duplicate_bibliography_match" for item in ambiguous_result.redundancies)

    match_states = {item.match_state for item in mixed_result.bibliography_alignments}
    coverage_states = {item.coverage_state for item in mixed_result.topic_coverage}
    gap_types = {item.gap_type for item in mixed_result.gaps}
    redundancy_types = {item.redundancy_type for item in mixed_result.redundancies}

    assert "matched" in match_states
    assert "unmatched" in match_states or "ambiguous" in match_states
    assert "covered" in coverage_states or "partially_covered" in coverage_states
    assert "weakly_covered" in coverage_states or "uncovered" in coverage_states
    assert "missing_bibliography_material" in gap_types or "uncovered_topic" in gap_types
    assert "duplicate_bibliography_match" in redundancy_types or "overlapping_topic_coverage" in redundancy_types
    assert_candidate_metadata(ambiguous_result)
    assert_candidate_metadata(mixed_result)


def test_no_materials_returns_safe_insufficient_state_without_fake_coverage(tmp_path):
    context = run_alignment_fixture(tmp_path, no_materials_alignment_fixture())
    state = context["state"]
    result = context["result"]

    assert state.status == "insufficient_materials"
    assert result.bibliography_alignments == []
    assert result.topic_coverage == []
    assert "no_candidate_materials_available" in state.warnings
    assert_alignment_json_safe(result)


def test_topic_coverage_detects_chunk_and_section_evidence_and_keeps_weak_overlap_conservative(tmp_path):
    chunk_context = run_alignment_fixture(tmp_path / "chunk", topic_covered_by_chunk_fixture())
    section_context = run_alignment_fixture(tmp_path / "section", topic_covered_by_section_fixture())
    weak_context = run_alignment_fixture(tmp_path / "weak", weak_generic_overlap_fixture())

    chunk_topic = topic_by_title(chunk_context["result"], "Meteorologia")
    section_topic = topic_by_title(section_context["result"], "RIPEAM")
    weak_topic = topic_by_title(weak_context["result"], "Legislacao Maritima Especial")

    assert chunk_topic.coverage_state in {"covered", "partially_covered"}
    assert chunk_topic.matched_chunk_ids
    assert chunk_topic.evidence and chunk_topic.evidence[0].matched_terms
    assert section_topic.coverage_state in {"covered", "partially_covered"}
    assert section_topic.matched_section_ids
    assert section_topic.reasoning
    assert weak_topic.coverage_state in {"weakly_covered", "uncovered"}
    assert weak_topic.confidence < 0.65


def test_ocr_required_and_unprocessed_materials_emit_safe_gaps_without_fake_coverage(tmp_path):
    ocr_context = run_alignment_fixture(tmp_path / "ocr", ocr_required_material_gap_fixture())
    unprocessed_context = run_alignment_fixture(tmp_path / "unprocessed", unprocessed_material_fixture())
    ocr_result = ocr_context["result"]
    unprocessed_result = unprocessed_context["result"]

    ocr_topic = topic_by_title(ocr_result, "Autoridade Maritima Aplicada")
    unprocessed_topic = topic_by_title(unprocessed_result, "Navegacao Costeira")

    assert ocr_topic.coverage_state == "uncovered"
    assert any(gap.gap_type == "ocr_required" for gap in ocr_result.gaps)
    assert any(warning.code == "ocr_required_material_present" for warning in ocr_result.warnings)
    assert unprocessed_topic.coverage_state == "uncovered"
    assert any(gap.gap_type == "missing_document_text" for gap in unprocessed_result.gaps)
    assert not unprocessed_topic.matched_document_ids


def test_multiple_documents_same_topic_and_maritime_fixture_produce_redundancy_and_expected_gaps(tmp_path):
    redundancy_context = run_alignment_fixture(tmp_path / "redundancy", multiple_documents_same_topic_redundancy_fixture())
    maritime_context = run_alignment_fixture(tmp_path / "maritime", maritime_praticagem_alignment_fixture())
    redundancy_result = redundancy_context["result"]
    maritime_result = maritime_context["result"]

    meteorologia = topic_by_title(redundancy_result, "Meteorologia")
    assert meteorologia.coverage_state in {"covered", "partially_covered"}
    assert any(item.redundancy_type == "overlapping_topic_coverage" for item in redundancy_result.redundancies)
    assert len(meteorologia.matched_document_ids) >= 2

    ripeam = topic_by_title(maritime_result, "RIPEAM")
    meteorologia_mar = topic_by_title(maritime_result, "Meteorologia")
    arte_naval = topic_by_title(maritime_result, "Arte Naval")
    assert ripeam.coverage_state in {"covered", "partially_covered"}
    assert meteorologia_mar.coverage_state in {"covered", "partially_covered"}
    assert arte_naval.coverage_state in {"weakly_covered", "uncovered"}
    assert any(gap.target_title == "Arte Naval" for gap in maritime_result.gaps)


def test_alignment_results_are_deterministic_and_idempotent(tmp_path):
    fixture = mixed_alignment_fixture()
    first_context = run_alignment_fixture(tmp_path / "first", fixture)
    second_context = run_alignment_fixture(tmp_path / "second", fixture)
    repeated_state = first_context["repository"].get_bibliography_alignment_state(first_context["edital_id"], user_id="user-a")
    repeated_again = first_context["repository"].get_bibliography_alignment_result(first_context["edital_id"], user_id="user-a")

    rerun_state = BibliographyAlignmentService(first_context["repository"]).align_edital(first_context["edital_id"], user_id="user-a")
    rerun_result = first_context["repository"].get_bibliography_alignment_result(first_context["edital_id"], user_id="user-a")

    assert [item.match_state for item in first_context["result"].bibliography_alignments] == [
        item.match_state for item in second_context["result"].bibliography_alignments
    ]
    assert [item.coverage_state for item in first_context["result"].topic_coverage] == [
        item.coverage_state for item in second_context["result"].topic_coverage
    ]
    assert [item.raw_reference for item in first_context["result"].bibliography_alignments] == [
        item.raw_reference for item in second_context["result"].bibliography_alignments
    ]
    assert [item.topic_title for item in first_context["result"].topic_coverage] == [
        item.topic_title for item in second_context["result"].topic_coverage
    ]
    assert repeated_state.model_dump(mode="json") == rerun_state.model_dump(mode="json")
    assert repeated_again.model_dump(mode="json") == rerun_result.model_dump(mode="json")
    assert_alignment_json_safe(first_context["result"])


def test_alignment_respects_user_scope_when_running_fixture_flow(tmp_path):
    fixture = exact_bibliography_match_fixture()
    owner_context = run_alignment_fixture(tmp_path / "owner", fixture, user_id="owner")
    other_context = run_alignment_fixture(tmp_path / "other", no_materials_alignment_fixture(), user_id="other")

    owner_result = owner_context["result"]
    other_result = other_context["result"]
    owner_repo = owner_context["repository"]

    assert owner_result.bibliography_alignments[0].matched_document_ids
    assert other_result.bibliography_alignments == []
    assert owner_repo.get_bibliography_alignment_result(owner_context["edital_id"], user_id="other") is None
    assert owner_repo.get_bibliography_alignment_state(owner_context["edital_id"], user_id="other") is None
