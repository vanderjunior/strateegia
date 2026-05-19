import json

from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService
from app.services.question_draft_generation import QuestionDraftGenerationService
from tests.fixtures.question_generation_blueprints import (
    ambiguous_coverage_slot_fixture,
    cebraspe_true_false_fixture,
    collect_keys,
    fgv_multiple_choice_fixture,
    no_slots_blueprint_fixture,
    pscpp_maritime_fixture,
    ready_source_grounded_slot_fixture,
    unsupported_format_slot_fixture,
)


FORBIDDEN_FINAL_KEYS = {
    "final_question_text",
    "final_stem",
    "final_statement",
    "final_options",
    "alternatives",
    "final_alternatives",
    "distractors",
    "answer",
    "answer_key",
    "correct_answer",
    "gabarito",
    "explanation",
    "final_explanation",
    "correction",
    "scoring_result",
}


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    return (
        repository,
        MaterialService(repository, storage_root=storage_root),
        DocumentPipelineService(repository, storage_root=storage_root),
        QuestionDraftGenerationService(repository),
    )


def build_blueprint_set(fixture):
    return fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )


def test_question_draft_generation_handles_missing_source_and_no_ready_blueprints(tmp_path):
    repository, _, _, service = create_services(tmp_path)

    assert service.build_draft_set("question-generation:missing", user_id="user-a") is None
    assert repository.list_user_question_draft_sets(user_id="user-a") == []

    no_slots_fixture = no_slots_blueprint_fixture(tmp_path / "no-slots")
    blocked_fixture = ambiguous_coverage_slot_fixture(tmp_path / "needs-review")
    no_slots_service = QuestionDraftGenerationService(no_slots_fixture.context.repository)
    blocked_service = QuestionDraftGenerationService(blocked_fixture.context.repository)
    no_slots_blueprint = build_blueprint_set(no_slots_fixture)
    blocked_blueprint = build_blueprint_set(blocked_fixture)

    no_slots_result = no_slots_service.build_draft_set(no_slots_blueprint.blueprint_set_id, user_id="user-a")
    blocked_result = blocked_service.build_draft_set(blocked_blueprint.blueprint_set_id, user_id="user-a")

    assert no_slots_result.readiness_state == "no_ready_blueprints"
    assert no_slots_result.total_blueprint_slots == 0
    assert no_slots_result.draft_count == 0
    assert blocked_result.readiness_state in {"no_ready_blueprints", "blocked", "needs_review"}
    assert blocked_result.draft_count == 0
    assert blocked_result.skipped_count + blocked_result.blocked_count + blocked_result.needs_review_count >= 1


def test_question_draft_generation_creates_ready_assertion_judgement_draft(tmp_path):
    fixture = cebraspe_true_false_fixture(tmp_path)
    service = QuestionDraftGenerationService(fixture.context.repository)
    blueprint_set = build_blueprint_set(fixture)

    result = service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    draft = result.drafts[0]

    assert result.readiness_state == "drafts_created"
    assert result.draft_count == 1
    assert draft.draft_status == "draft_created"
    assert draft.draft_readiness == "draft_for_review"
    assert draft.question_kind == "assertion_judgement"
    assert draft.draft_stem
    assert draft.draft_command
    assert draft.draft_statement
    assert draft.source_references
    assert draft.review_required is True
    assert draft.finalization_blocked is True
    assert draft.validation_summary.source_grounded is True
    assert draft.validation_summary.final_answer_absent is True
    assert draft.validation_summary.final_explanation_absent is True
    assert draft.draft_command.startswith("Julgue")


def test_question_draft_generation_creates_fgv_and_pscpp_review_required_drafts(tmp_path):
    fgv_fixture = fgv_multiple_choice_fixture(tmp_path / "fgv")
    pscpp_fixture = pscpp_maritime_fixture(tmp_path / "pscpp")
    fgv_service = QuestionDraftGenerationService(fgv_fixture.context.repository)
    pscpp_service = QuestionDraftGenerationService(pscpp_fixture.context.repository)

    fgv_result = fgv_service.build_draft_set(
        build_blueprint_set(fgv_fixture).blueprint_set_id,
        user_id=fgv_fixture.context.user_id,
    )
    pscpp_result = pscpp_service.build_draft_set(
        build_blueprint_set(pscpp_fixture).blueprint_set_id,
        user_id=pscpp_fixture.context.user_id,
    )

    fgv_draft = fgv_result.drafts[0]
    pscpp_draft = pscpp_result.drafts[0]

    assert fgv_draft.question_kind == "case_based_multiple_choice"
    assert fgv_draft.draft_scenario
    assert len(fgv_draft.draft_option_placeholders) == 5
    assert all(item.startswith("Placeholder") for item in fgv_draft.draft_option_placeholders)
    assert all(len(item) <= 160 for item in fgv_draft.draft_option_placeholders)
    assert fgv_draft.review_required is True

    assert pscpp_draft.question_kind == "technical_maritime_scenario"
    assert pscpp_draft.draft_scenario
    assert pscpp_draft.review_required is True
    assert any(item.code == "maritime_draft_requires_review" for item in pscpp_draft.warnings)


def test_question_draft_generation_skips_unsupported_blueprints_and_preserves_bounds(tmp_path):
    unsupported_fixture = unsupported_format_slot_fixture(tmp_path / "unsupported")
    ready_fixture = ready_source_grounded_slot_fixture(tmp_path / "ready")
    unsupported_service = QuestionDraftGenerationService(unsupported_fixture.context.repository)
    ready_service = QuestionDraftGenerationService(ready_fixture.context.repository)
    unsupported_blueprint = build_blueprint_set(unsupported_fixture)
    ready_blueprint = build_blueprint_set(ready_fixture)

    unsupported_result = unsupported_service.build_draft_set(
        unsupported_blueprint.blueprint_set_id,
        user_id=unsupported_fixture.context.user_id,
    )
    ready_result = ready_service.build_draft_set(
        ready_blueprint.blueprint_set_id,
        user_id=ready_fixture.context.user_id,
    )
    draft = ready_result.drafts[0]

    assert unsupported_result.draft_count == 0
    assert unsupported_result.skipped_count + unsupported_result.blocked_count >= 1
    assert draft.draft_stem is not None and len(draft.draft_stem) <= 800
    if draft.draft_command is not None:
        assert len(draft.draft_command) <= 240
    if draft.draft_statement is not None:
        assert len(draft.draft_statement) <= 600
    if draft.draft_scenario is not None:
        assert len(draft.draft_scenario) <= 800
    for source in draft.source_references:
        assert source.safe_snippet is None or len(source.safe_snippet) <= 240


def test_question_draft_generation_no_final_content_and_idempotency(tmp_path):
    repository, _, _, service = create_services(tmp_path)
    fixture = fgv_multiple_choice_fixture(tmp_path)
    blueprint_set = build_blueprint_set(fixture)

    first = service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    second = service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    by_source = repository.get_question_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    by_id = repository.get_question_draft_set_by_id(first.draft_set_id, user_id=fixture.context.user_id)
    listed = repository.list_user_question_draft_sets(user_id=fixture.context.user_id)
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_keys(dumped)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert first.no_final_question_generated is True
    assert first.no_answer_key_generated is True
    assert first.no_final_alternatives_generated is True
    assert first.no_distractors_generated is True
    assert first.no_final_explanations_generated is True
    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in dumped_keys
    json.dumps(dumped, ensure_ascii=True)
