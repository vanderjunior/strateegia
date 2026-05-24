from __future__ import annotations

from app.services.question_style_profiles import build_question_style_validation
from tests.fixtures.question_style_profiles import pscpp_archetype_slot_fixture, pscpp_direct_metadata_fixture


def test_pscpp_source_validation_marks_missing_anchor_and_alignment_for_review():
    missing_anchor = pscpp_direct_metadata_fixture(
        context="fixation",
        bibliography_anchor_present=False,
    )
    missing_alignment = pscpp_direct_metadata_fixture(
        context="review",
        current_edital_alignment_present=False,
    )

    assert missing_anchor["question_style_validation"]["state"] == "needs_review"
    assert "bibliography_anchor_missing" in missing_anchor["question_style_validation"]["warnings"]
    assert missing_anchor["bibliography_anchor_validation_state"] == "needs_review"
    assert missing_alignment["question_style_validation"]["state"] == "needs_review"
    assert "current_edital_alignment_missing" in missing_alignment["question_style_validation"]["warnings"]
    assert missing_alignment["current_edital_alignment_validation_state"] == "needs_review"


def test_pscpp_archetype_validation_accepts_valid_archetypes_and_warns_invalid():
    valid = build_question_style_validation(
        exam_profile_id="marinha_dpc_pscpp_praticagem",
        requested_archetype="technical_gap_fill_multiple_choice",
        source_present=True,
        bibliography_anchor_present=True,
        source_title_visible=True,
        current_edital_alignment_present=True,
        formula_supported=False,
        per_statement_source_support=False,
        negative_command=False,
        exact_source_value_present=False,
        scenario_present=False,
        normative_source_present=False,
        units_present=False,
        delivery_context="summary_reading",
    )
    invalid = build_question_style_validation(
        exam_profile_id="marinha_dpc_pscpp_praticagem",
        requested_archetype="essay_discursive",
        source_present=True,
        bibliography_anchor_present=True,
        source_title_visible=True,
        current_edital_alignment_present=True,
        formula_supported=False,
        per_statement_source_support=False,
        negative_command=False,
        exact_source_value_present=False,
        scenario_present=False,
        normative_source_present=False,
        units_present=False,
        delivery_context="summary_reading",
    )

    assert valid["selected_archetype"] == "technical_gap_fill_multiple_choice"
    assert valid["state"] == "needs_review"
    assert "exact_source_value_required" in valid["warnings"]
    assert valid["archetype_requirements"]["requires_exact_source_value"] is True
    assert invalid["invalid_requested_archetype"] is True
    assert invalid["recommended_archetype"] == "incorrect_alternative"
    assert invalid["selected_archetype"] == "incorrect_alternative"
    assert "invalid_pscpp_archetype_requested" in invalid["warnings"]


def test_pscpp_archetype_specific_rules_are_attached_in_simulado_blueprints(tmp_path):
    calc_fixture = pscpp_archetype_slot_fixture(
        tmp_path / "calc",
        requested_archetype="applied_calculation",
    )
    stmt_fixture = pscpp_archetype_slot_fixture(
        tmp_path / "stmt",
        requested_archetype="statement_combination",
    )
    gap_fixture = pscpp_archetype_slot_fixture(
        tmp_path / "gap",
        requested_archetype="technical_gap_fill_multiple_choice",
    )

    calc_slot = calc_fixture.context.blueprint_service.build_blueprint_set(
        calc_fixture.simulado_blueprint.blueprint_id,
        user_id=calc_fixture.context.user_id,
    ).slot_blueprints[0]
    stmt_slot = stmt_fixture.context.blueprint_service.build_blueprint_set(
        stmt_fixture.simulado_blueprint.blueprint_id,
        user_id=stmt_fixture.context.user_id,
    ).slot_blueprints[0]
    gap_slot = gap_fixture.context.blueprint_service.build_blueprint_set(
        gap_fixture.simulado_blueprint.blueprint_id,
        user_id=gap_fixture.context.user_id,
    ).slot_blueprints[0]

    assert "numeric_source_or_formula_validation_required" in calc_slot.metadata["question_style_validation"]["warnings"]
    assert "calculation_units_required" in calc_slot.metadata["question_style_validation"]["warnings"]
    assert stmt_slot.metadata["question_style_validation"]["archetype_requirements"]["source_support_per_statement_required"] is True
    assert "source_support_per_statement_required" in stmt_slot.metadata["question_style_validation"]["warnings"]
    assert "exact_source_value_required" in gap_slot.metadata["question_style_validation"]["warnings"]


def test_pscpp_negative_command_and_normative_case_rules_are_marked_for_review():
    negative = pscpp_direct_metadata_fixture(
        context="summary_reading",
        requested_archetype="incorrect_alternative",
        negative_command=True,
    )
    normative = pscpp_direct_metadata_fixture(
        context="review",
        requested_archetype="normative_case_application",
        normative_source_present=False,
    )

    assert "negative_command_review_marker_required" in negative["question_style_validation"]["warnings"]
    assert normative["question_style_validation"]["archetype_requirements"]["normative_reference_required"] is True
    assert "normative_reference_required" in normative["question_style_validation"]["warnings"]
