from __future__ import annotations

import json

from app.services.exam_profiles import ExamProfileService
from app.services.question_style_profiles import (
    PSCPP_QUESTION_STYLE_PROFILE_ID,
    get_pscpp_question_style_profile,
    get_question_style_profile,
)
from tests.fixtures.question_style_profiles import pscpp_profile_fixture


def _collect_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def test_pscpp_profile_retrieval_is_deterministic_and_json_safe():
    first = pscpp_profile_fixture()
    second = get_pscpp_question_style_profile()
    third = get_question_style_profile(PSCPP_QUESTION_STYLE_PROFILE_ID)
    alias = get_question_style_profile("exam-profile:marinha-pscpp")

    assert first == second == third == alias
    assert first["profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert first["profile_name"] == "Marinha/DPC PSCPP Praticagem"
    assert first["options"]["options_count"] == 5
    assert first["options"]["answer_labels"] == ["a", "b", "c", "d", "e"]
    assert first["source_grounding"]["source_required"] is True
    assert first["source_grounding"]["bibliography_anchor_required"] is True
    assert first["source_grounding"]["source_title_should_be_visible_in_blueprint"] is True
    assert first["historical_exam_evidence"]["exam"] == "PSCPP/2012 Prova Rosa"
    assert first["historical_exam_evidence"]["do_not_use_as_current_content_scope"] is True

    dumped = json.dumps(first, ensure_ascii=True)
    dumped_keys = _collect_keys(first)
    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key_content",
        "gabarito",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    assert "file://" not in dumped
    assert "/Users/" not in dumped


def test_pscpp_profile_encodes_archetypes_scoring_and_distractor_policy():
    profile = get_pscpp_question_style_profile()
    archetypes = {item["archetype_id"] for item in profile["question_archetypes"]}

    assert archetypes == {
        "statement_combination",
        "true_false_sequence_multiple_choice",
        "incorrect_alternative",
        "applied_calculation",
        "technical_operational_scenario",
        "technical_gap_fill_multiple_choice",
        "normative_case_application",
    }
    assert profile["scoring_behavior"]["uniform_weight"] is False
    assert profile["scoring_behavior"]["observed_weights"] == [0.8, 1.0, 1.2, 1.3, 1.6, 2.0]
    assert profile["scoring_behavior"]["do_not_assume_default_weight"] is True
    assert profile["distractor_policy"]["must_be_technically_plausible"] is True
    assert "squat_vs_bank_effect" in profile["distractor_policy"]["common_confusions"]
    assert "rumo_verdadeiro_vs_rumo_magnetico_vs_rumo_da_agulha" in profile["distractor_policy"]["common_confusions"]


def test_pscpp_profile_exposes_template_and_safety_metadata():
    profile = get_pscpp_question_style_profile()
    templates = {item["template_id"] for item in profile["templates"]}

    assert templates == {
        "bibliography_statements",
        "operational_scenario",
        "applied_calculation",
        "incorrect_alternative",
        "technical_gap_fill",
    }
    assert profile["safety_rules"]["do_not_generate_without_source"] is True
    assert profile["safety_rules"]["do_not_generate_numeric_answer_without_explicit_source_or_formula"] is True
    assert profile["safety_rules"]["require_human_review_for_answer_key"] is True
    assert profile["safety_rules"]["final_answer_key_should_not_be_generated_without_source_validation"] is True
    assert "simulado" in profile["applicable_generation_flows"]
    assert "fixation" in profile["applicable_generation_flows"]
    assert "review" in profile["applicable_generation_flows"]
    assert "summary_reading" in profile["applicable_generation_flows"]


def test_exam_profile_references_pscpp_style_profile_without_treating_2012_as_current_scope():
    profile = ExamProfileService().get_exam_profile("exam-profile:marinha-pscpp")

    assert profile is not None
    assert profile.metadata["canonical_question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert profile.question_style_profile.metadata["question_style_profile_id"] == PSCPP_QUESTION_STYLE_PROFILE_ID
    assert profile.question_style_profile.metadata["historical_exam_evidence"]["exam"] == "PSCPP/2012 Prova Rosa"
    assert profile.question_style_profile.metadata["historical_exam_evidence"]["do_not_use_as_current_content_scope"] is True
