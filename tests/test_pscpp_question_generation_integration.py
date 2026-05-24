from __future__ import annotations

from tests.fixtures.question_style_profiles import (
    pscpp_archetype_slot_fixture,
    pscpp_direct_metadata_fixture,
    pscpp_draft_fixture,
    pscpp_ready_blueprint_fixture,
)


def test_pscpp_simulado_blueprint_includes_extended_generation_metadata(tmp_path):
    fixture = pscpp_ready_blueprint_fixture(tmp_path)
    result = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    slot = result.slot_blueprints[0]

    assert slot.metadata["exam_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert slot.metadata["question_style_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert slot.metadata["format"] == "multiple_choice"
    assert slot.metadata["options_count"] == 5
    assert slot.metadata["answer_labels"] == ["a", "b", "c", "d", "e"]
    assert slot.metadata["source_required"] is True
    assert slot.metadata["bibliography_anchor_required"] is True
    assert slot.metadata["source_title_should_be_visible_in_blueprint"] is True
    assert slot.metadata["current_edital_alignment_required"] is True
    assert slot.metadata["selected_question_archetype"] == "technical_operational_scenario"
    assert slot.metadata["recommended_question_archetype"] == "technical_operational_scenario"
    assert slot.metadata["distractor_policy"]["must_be_technically_plausible"] is True
    assert slot.metadata["scoring_behavior"]["do_not_assume_default_weight"] is True
    assert slot.metadata["historical_exam_evidence"]["do_not_use_as_current_content_scope"] is True


def test_pscpp_fixation_review_and_summary_metadata_are_consistently_enriched():
    fixation = pscpp_direct_metadata_fixture(context="fixation")
    review = pscpp_direct_metadata_fixture(
        context="review",
        requested_archetype="statement_combination",
        per_statement_source_support=True,
    )
    summary = pscpp_direct_metadata_fixture(
        context="summary_reading",
        requested_archetype="incorrect_alternative",
        negative_command=True,
    )

    assert fixation["selected_question_archetype"] == "statement_combination"
    assert review["selected_question_archetype"] == "statement_combination"
    assert summary["selected_question_archetype"] == "incorrect_alternative"
    for payload in (fixation, review, summary):
        assert payload["question_style_profile_id"] == "marinha_dpc_pscpp_praticagem"
        assert payload["source_required"] is True
        assert payload["human_review_required_for_answer_key"] is True
        assert payload["allowed_archetypes"]
        assert payload["preferred_templates"]


def test_pscpp_archetype_selection_and_draft_propagation_are_deterministic(tmp_path):
    fixture = pscpp_archetype_slot_fixture(
        tmp_path,
        requested_archetype="statement_combination",
        slot_metadata={"per_statement_source_support": True},
    )
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    draft_set = pscpp_draft_fixture(tmp_path / "draft-propagation")
    slot = blueprint_set.slot_blueprints[0]
    draft = draft_set.drafts[0]

    assert slot.metadata["selected_question_archetype"] == "statement_combination"
    assert slot.metadata["question_style_validation"]["archetype_requirements"]["statement_count_min"] == 4
    assert draft.metadata["selected_question_archetype"] == "technical_operational_scenario"
    assert draft.metadata["question_style_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert draft.metadata["human_review_required_for_answer_key"] is True
