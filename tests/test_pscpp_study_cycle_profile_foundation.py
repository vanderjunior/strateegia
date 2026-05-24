from __future__ import annotations

import json

from app.services.study_cycle_profiles import PSCPP_STUDY_CYCLE_PROFILE_ID, get_study_cycle_profile
from tests.fixtures.study_cycle_profiles import (
    pscpp_study_cycle_guidance_fixture,
    pscpp_study_cycle_profile_fixture,
)


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


def test_pscpp_study_cycle_profile_retrieval_is_deterministic_and_guidance_only():
    first = pscpp_study_cycle_profile_fixture()
    second = get_study_cycle_profile(PSCPP_STUDY_CYCLE_PROFILE_ID)

    assert first == second
    assert first["profile_id"] == PSCPP_STUDY_CYCLE_PROFILE_ID
    assert first["exam_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert first["profile_type"] == "flexible_study_cycle_guidance"
    assert first["not_fixed_schedule"] is True
    assert first["user_override_allowed"] is True
    assert first["automatic_scheduler_mutation_allowed"] is False


def test_pscpp_study_cycle_historical_evidence_priority_blocks_and_phases_are_present():
    profile = pscpp_study_cycle_profile_fixture()
    blocks = profile["priority_blocks"]
    phases = profile["phase_plan"]

    assert profile["historical_exam_evidence"]["exams"] == ["PSCPP/2011", "PSCPP/2012 Prova Rosa"]
    assert profile["historical_exam_evidence"]["use_as"] == "strategy_and_style_reference"
    assert profile["historical_exam_evidence"]["do_not_use_as_current_content_scope"] is True
    assert profile["historical_exam_evidence"]["requires_current_edital_alignment"] is True
    assert [item["block_id"] for item in blocks] == [
        "manoeuvrability_shiphandling_tugs_restricted_waters",
        "colreg_lights_marks_sound_signals",
        "restricted_navigation_radar_ecdis_tides_passage_planning",
        "arte_naval_foundations",
        "legislation_meteorology_communications_general_knowledge",
    ]
    assert [item["priority"] for item in blocks] == [1, 2, 3, 4, 5]
    assert [item["phase_id"] for item in phases] == [
        "phase_1_base_technical_vocabulary",
        "phase_2_scenario_consolidation",
        "phase_3_deepening_and_new_question_production",
        "phase_4_post_edital_alignment",
    ]


def test_pscpp_study_cycle_weekly_distribution_rotation_and_session_structure_are_stable():
    profile = pscpp_study_cycle_profile_fixture()
    weekly = profile["weekly_distribution_hint_24h"]
    sessions = profile["rotating_12_session_cycle"]
    structure = profile["session_structure"]

    assert weekly == {
        "total_hours": 24,
        "manoeuvrability_shiphandling_tugs": 6,
        "colreg_lights_marks_cis": 4,
        "restricted_navigation_radar_ecdis_tides": 4,
        "arte_naval": 3,
        "legislation_normam_tribunal_praticagem": 3,
        "meteorology_oceanography": 2,
        "communications_smcp_gmdss": 1,
        "cumulative_review_error_notebook": 1,
    }
    assert len(sessions) == 12
    assert sessions[0]["theme"] == "Manoeuvrability: forces, resistance, propulsion"
    assert sessions[-1]["theme"] == "Short simulado + error review"
    assert structure["active_review_minutes"] == 20
    assert structure["directed_theory_minutes"] == "60_to_90"
    assert structure["questions_or_question_creation_minutes"] == 40
    assert structure["error_notebook_flashcards_minutes"] == 20


def test_pscpp_study_cycle_guidance_carries_training_notebooks_and_question_linkage():
    profile = pscpp_study_cycle_profile_fixture()

    assert profile["question_training_progression"]["guidance_only"] is True
    assert profile["study_products_per_topic"] == [
        "operational_summary",
        "trap_map",
        "flashcards",
        "original_questions",
    ]
    assert [item["notebook_id"] for item in profile["notebook_system"]] == [
        "concepts_the_banca_confuses",
        "fatal_numbers_and_rules",
        "scenario_notebook",
    ]
    guidance = profile["question_generation_guidance"]
    assert guidance["question_generation_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert guidance["use_pscpp_question_style_profile"] is True
    assert guidance["prefer_source_grounded_questions"] is True
    assert guidance["prefer_scenario_rich_questions"] is True
    assert guidance["prefer_technically_plausible_distractors"] is True
    assert guidance["do_not_generate_answer_key_without_source_validation"] is True
    assert guidance["require_human_review_for_answer_key"] is True


def test_pscpp_study_cycle_profile_is_json_safe_and_has_no_runtime_mutation():
    profile = pscpp_study_cycle_profile_fixture()
    guidance = pscpp_study_cycle_guidance_fixture()
    dumped = {"profile": profile, "guidance": guidance}
    serialized = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = _collect_keys(dumped)

    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key",
        "final_answer_key_content",
        "gabarito",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("/Users/", "/private/", "raw document body", "OCR/base64", "storage_root"):
        assert forbidden not in serialized
    assert profile["metadata"]["runtime_mutation_performed"] is False
    assert profile["metadata"]["scheduler_mutation_performed"] is False
    assert profile["metadata"]["calendar_mutation_performed"] is False
