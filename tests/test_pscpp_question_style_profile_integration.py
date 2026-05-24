from __future__ import annotations

from app.services.question_style_profiles import (
    PSCPP_EXAM_PROFILE_ID,
    PSCPP_QUESTION_STYLE_PROFILE_ID,
    build_question_style_validation,
    enrich_question_generation_blueprint_with_style_profile,
)
from tests.fixtures.question_generation_blueprints import fgv_multiple_choice_fixture
from tests.fixtures.question_style_profiles import (
    pscpp_draft_fixture,
    pscpp_fixation_metadata_fixture,
    pscpp_missing_source_blueprint_fixture,
    pscpp_ready_blueprint_fixture,
    pscpp_review_metadata_fixture,
    pscpp_summary_reading_metadata_fixture,
)


def test_pscpp_simulado_blueprint_integration_enriches_metadata(tmp_path):
    fixture = pscpp_ready_blueprint_fixture(tmp_path)

    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    slot = result.slot_blueprints[0]

    assert slot.readiness_state == "ready_for_draft"
    assert slot.metadata["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert slot.metadata["source_required"] is True
    assert slot.metadata["bibliography_anchor_required"] is True
    assert slot.metadata["human_review_required_for_answer_key"] is True
    assert "statement_combination" in slot.metadata["allowed_archetypes"]
    assert "technical_operational_scenario" in slot.metadata["allowed_archetypes"]
    assert slot.metadata["scoring_behavior"]["uniform_weight"] is False
    assert slot.metadata["question_style_validation"]["state"] == "style_profile_ready"
    assert slot.metadata["visible_source_titles"]


def test_pscpp_blueprint_without_source_is_blocked_and_marked_invalid(tmp_path):
    fixture = pscpp_missing_source_blueprint_fixture(tmp_path)

    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    slot = result.slot_blueprints[0]

    assert slot.readiness_state == "blocked_by_missing_source"
    assert slot.metadata["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert slot.metadata["question_style_validation"]["state"] == "blocked_by_missing_source"
    assert slot.metadata["question_style_validation"]["blockers"] == ["blocked_by_missing_source"]
    assert slot.metadata["source_required"] is True


def test_pscpp_style_helper_supports_fixation_review_and_summary_metadata():
    fixation = pscpp_fixation_metadata_fixture()
    review = pscpp_review_metadata_fixture()
    summary = pscpp_summary_reading_metadata_fixture()

    for payload in (fixation, review, summary):
        assert payload["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
        assert payload["source_required"] is True
        assert payload["bibliography_anchor_required"] is True
        assert payload["human_review_required_for_answer_key"] is True
        assert "technical_operational_scenario" in payload["allowed_archetypes"]
        assert payload["preferred_templates"]

    assert fixation["delivery_context"] == "fixation"
    assert review["delivery_context"] == "review"
    assert summary["delivery_context"] == "summary_reading"
    assert "negative_command_review_marker_required" in summary["question_style_validation"]["warnings"]


def test_pscpp_style_validation_marks_calculation_and_multistatement_items_for_review():
    calculation = build_question_style_validation(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        requested_archetype="applied_calculation",
        source_present=True,
        formula_supported=False,
        per_statement_source_support=False,
        negative_command=False,
    )
    multi_statement = build_question_style_validation(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        requested_archetype="statement_combination",
        source_present=True,
        formula_supported=False,
        per_statement_source_support=False,
        negative_command=False,
    )

    assert calculation["state"] == "needs_review"
    assert "numeric_source_or_formula_validation_required" in calculation["warnings"]
    assert multi_statement["state"] == "needs_review"
    assert "source_support_per_statement_required" in multi_statement["warnings"]


def test_pscpp_draft_metadata_carries_style_constraints_without_answer_key_leakage(tmp_path):
    draft_set = pscpp_draft_fixture(tmp_path)
    draft = draft_set.drafts[0]

    assert draft.metadata["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert draft.metadata["source_required"] is True
    assert draft.metadata["human_review_required_for_answer_key"] is True
    assert draft.validation_summary.metadata["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert draft.metadata["question_style_validation"]["state"] == "style_profile_ready"
    assert draft.metadata["no_answer_key_generated"] is True


def test_non_pscpp_behavior_remains_unchanged(tmp_path):
    fixture = fgv_multiple_choice_fixture(tmp_path)
    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    slot = result.slot_blueprints[0]
    direct = enrich_question_generation_blueprint_with_style_profile(
        exam_profile_id="exam-profile:fgv",
        blueprint_metadata={"existing": True},
        source_titles=["FGV source"],
        source_present=True,
    )

    assert "question_style_profile_id" not in slot.metadata
    assert direct == {"existing": True}
