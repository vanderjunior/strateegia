from __future__ import annotations

import json

from tests.fixtures.study_cycle_profiles import (
    non_pscpp_behavior_fixture,
    pscpp_historical_evidence_fixture,
    pscpp_integration_metadata_fixture,
    pscpp_no_leakage_fixture,
    pscpp_no_runtime_mutation_fixture,
    pscpp_no_scheduler_mutation_fixture,
    pscpp_notebook_system_fixture,
    pscpp_phase_plan_fixture,
    pscpp_priority_blocks_fixture,
    pscpp_question_style_bridge_fixture,
    pscpp_question_training_progression_fixture,
    pscpp_rotating_12_session_cycle_fixture,
    pscpp_scaled_weekly_distribution_fixture,
    pscpp_session_structure_fixture,
    pscpp_study_cycle_blueprint_metadata_fixture,
    pscpp_study_cycle_guidance_fixture,
    pscpp_study_cycle_profile_fixture,
    pscpp_study_cycle_profile_payload_fixture,
    pscpp_user_override_fixture,
    pscpp_weekly_distribution_fixture,
    stabilization_fixture_builders,
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


def test_fixture_builders_are_deterministic_json_safe_and_guidance_only():
    builders = stabilization_fixture_builders()
    first = pscpp_study_cycle_profile_payload_fixture()
    second = pscpp_study_cycle_profile_payload_fixture()

    assert "pscpp_study_cycle_profile" in builders
    assert "pscpp_scaled_weekly_distribution" in builders
    assert first == second

    dumped = {
        "profile": first,
        "guidance": pscpp_study_cycle_guidance_fixture(),
        "metadata": pscpp_study_cycle_blueprint_metadata_fixture(),
    }
    serialized = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = _collect_keys(dumped)
    assert '"external_calls_used": false' in serialized
    assert '"llm_used": false' in serialized
    assert "ocr" not in serialized.lower()
    assert "rag" not in serialized.lower()
    assert "vector_store" not in dumped_keys
    assert "vector_search" not in dumped_keys
    assert "calendar_event" not in serialized
    assert "study_session" not in serialized


def test_profile_retrieval_identity_and_guidance_flags_are_stable():
    profile = pscpp_study_cycle_profile_fixture()
    user_override = pscpp_user_override_fixture()
    no_scheduler = pscpp_no_scheduler_mutation_fixture()

    assert profile["profile_id"] == "marinha_dpc_pscpp_praticagem_study_cycle"
    assert profile["exam_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert profile["profile_type"] == "flexible_study_cycle_guidance"
    assert profile["guidance_mode"] == "editable_recommendation"
    assert profile["not_fixed_schedule"] is True
    assert profile["user_override_allowed"] is True
    assert profile["profile_is_guidance_not_mandate"] is True
    assert profile["automatic_scheduler_mutation_allowed"] is False
    assert profile["requires_current_edital_alignment"] is True
    assert user_override == {
        "not_fixed_schedule": True,
        "user_override_allowed": True,
        "profile_is_guidance_not_mandate": True,
    }
    assert no_scheduler["automatic_scheduler_mutation_allowed"] is False


def test_historical_evidence_and_strategic_reading_remain_non_current_scope():
    profile = pscpp_study_cycle_profile_fixture()
    evidence = pscpp_historical_evidence_fixture()
    strategic = profile["strategic_reading"]

    assert "PSCPP/2011" in evidence["exams"]
    assert "PSCPP/2012 Prova Rosa" in evidence["exams"]
    assert evidence["use_as"] == "strategy_and_style_reference"
    assert evidence["do_not_use_as_current_content_scope"] is True
    assert evidence["requires_current_edital_alignment"] is True
    assert any("technical decision-making" in item for item in strategic)
    assert any("not be treated as legislation-only" in item for item in strategic)
    assert any("COLREG" in item and "NORMAM" in item for item in strategic)


def test_priority_blocks_and_phase_plan_are_complete_and_guidance_only():
    blocks = pscpp_priority_blocks_fixture()
    phases = pscpp_phase_plan_fixture()

    assert [item["block_id"] for item in blocks] == [
        "manoeuvrability_shiphandling_tugs_restricted_waters",
        "colreg_lights_marks_sound_signals",
        "restricted_navigation_radar_ecdis_tides_passage_planning",
        "arte_naval_foundations",
        "legislation_meteorology_communications_general_knowledge",
    ]
    for expected, block in enumerate(blocks, start=1):
        assert block["priority"] == expected
        assert block["rationale"]
        assert isinstance(block["includes"], list)
        assert len(block["includes"]) > 0

    assert [item["phase_id"] for item in phases] == [
        "phase_1_base_technical_vocabulary",
        "phase_2_scenario_consolidation",
        "phase_3_deepening_and_new_question_production",
        "phase_4_post_edital_alignment",
    ]
    for phase in phases:
        assert phase["objective"]
        assert phase.get("focus") or phase.get("scenario_examples") or phase.get("recommended_mix")
        assert phase.get("output_products") or phase.get("cadence_hints") or phase.get("question_generation_emphasis")


def test_weekly_distribution_and_scaled_variants_preserve_proportions():
    base = pscpp_weekly_distribution_fixture()
    scaled_12 = pscpp_scaled_weekly_distribution_fixture(weekly_hours=12)
    scaled_18 = pscpp_scaled_weekly_distribution_fixture(weekly_hours=18)
    scaled_30 = pscpp_scaled_weekly_distribution_fixture(weekly_hours=30)

    assert base == {
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
    for expected_total, scaled in ((12.0, scaled_12), (18.0, scaled_18), (30.0, scaled_30)):
        assert scaled["total_hours"] == expected_total
        assert set(scaled) == {
            "total_hours",
            "scaling_ratio",
            "manoeuvrability_shiphandling_tugs",
            "colreg_lights_marks_cis",
            "restricted_navigation_radar_ecdis_tides",
            "arte_naval",
            "legislation_normam_tribunal_praticagem",
            "meteorology_oceanography",
            "communications_smcp_gmdss",
            "cumulative_review_error_notebook",
        }
        assert scaled["manoeuvrability_shiphandling_tugs"] > scaled["meteorology_oceanography"] > scaled["communications_smcp_gmdss"]
    assert pscpp_study_cycle_guidance_fixture(weekly_hours=18)["user_override_allowed"] is True


def test_rotating_cycle_session_structure_progression_and_notebooks_are_stable():
    sessions = pscpp_rotating_12_session_cycle_fixture()
    structure = pscpp_session_structure_fixture()
    progression = pscpp_question_training_progression_fixture()
    notebooks = pscpp_notebook_system_fixture()

    assert len(sessions) == 12
    assert sessions[0]["theme"] == "Manoeuvrability: forces, resistance, propulsion"
    assert sessions[1]["theme"] == "COLREG: steering and sailing rules"
    assert sessions[2]["theme"] == "Arte Naval: nomenclature, geometry, stability"
    assert sessions[3]["theme"] == "Navigation: headings, bearings, compass, LDP"
    assert sessions[4]["theme"] == "Manoeuvrability: rudder, turning circle, zig-zag, stopping"
    assert sessions[5]["theme"] == "Legislation: NORMAM, LESTA/RLESTA, praticagem"
    assert sessions[6]["theme"] == "Shiphandling: berthing, unberthing, anchoring"
    assert sessions[7]["theme"] == "COLREG: lights, marks, sound signals"
    assert sessions[8]["theme"] == "Restricted navigation: radar, ECDIS, AIS, passage planning"
    assert sessions[9]["theme"] == "Tugs, interaction, bollard pull, escort"
    assert sessions[10]["theme"] == "Meteorology, oceanography, tides, METAREA"
    assert sessions[11]["theme"] == "Short simulado + error review"
    assert structure == {
        "active_review_minutes": 20,
        "directed_theory_minutes": "60_to_90",
        "questions_or_question_creation_minutes": 40,
        "error_notebook_flashcards_minutes": 20,
    }
    assert progression["jan_mar_2027"] == "20 questions per week by topic"
    assert progression["apr_jun_2027"] == "40 questions per week plus own question creation"
    assert progression["jul_aug_2027"] == "1 partial simulado per week"
    assert progression["sep_2027"] == "1 complete simulado every 15 days"
    assert progression["oct_2027"] == "1 complete simulado per week"
    assert progression["nov_2027"] == "review by errors, not long reading"
    assert progression["guidance_only"] is True
    assert [item["notebook_id"] for item in notebooks] == [
        "concepts_the_banca_confuses",
        "fatal_numbers_and_rules",
        "scenario_notebook",
    ]
    scenario = next(item for item in notebooks if item["notebook_id"] == "scenario_notebook")
    assert scenario["fields"] == [
        "situation",
        "applicable_rule",
        "correct_conduct",
        "likely_trap",
        "possible_variation",
    ]


def test_question_style_bridge_and_integration_metadata_are_complete():
    bridge = pscpp_question_style_bridge_fixture()
    metadata = pscpp_study_cycle_blueprint_metadata_fixture()
    integration = pscpp_integration_metadata_fixture()

    assert bridge["question_generation_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert bridge["use_pscpp_question_style_profile"] is True
    assert bridge["prefer_source_grounded_questions"] is True
    assert bridge["prefer_scenario_rich_questions"] is True
    assert bridge["prefer_technically_plausible_distractors"] is True
    assert bridge["do_not_generate_answer_key_without_source_validation"] is True
    assert bridge["require_human_review_for_answer_key"] is True
    assert metadata["study_cycle_profile_id"] == "marinha_dpc_pscpp_praticagem_study_cycle"
    assert metadata["priority_blocks"]
    assert metadata["phase_plan"]
    assert metadata["rotating_12_session_cycle"]
    assert metadata["weekly_distribution_hint_24h"]["total_hours"] == 24
    assert metadata["scaled_weekly_distribution"]["total_hours"] == 24.0
    assert integration["scheduler_mutation_disabled"] is True
    assert integration["study_cycle_runtime_mutation_disabled"] is True
    assert integration["question_style_profile_id"] == "marinha_dpc_pscpp_praticagem"


def test_non_pscpp_behavior_no_runtime_mutation_and_no_leakage_are_preserved():
    non_pscpp = non_pscpp_behavior_fixture()
    runtime = pscpp_no_runtime_mutation_fixture()
    leakage = pscpp_no_leakage_fixture()
    serialized = json.dumps(leakage, ensure_ascii=True)
    dumped_keys = _collect_keys(leakage)

    assert non_pscpp["guidance"] == {"existing": True}
    assert non_pscpp["blueprint"] == {"existing": True}
    assert runtime["automatic_scheduler_mutation_allowed"] is False
    assert runtime["integration_metadata"]["scheduler_mutation_disabled"] is True
    assert runtime["integration_metadata"]["study_cycle_runtime_mutation_disabled"] is True
    assert runtime["metadata"]["runtime_mutation_performed"] is False
    assert runtime["metadata"]["scheduler_mutation_performed"] is False
    assert runtime["metadata"]["calendar_mutation_performed"] is False
    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key",
        "final_answer_key_content",
        "gabarito",
        "gabarito_final",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in (
        "/Users/",
        "/private/",
        "OCR/base64",
        "raw_runtime_block",
        "raw document body",
        "storage_root",
    ):
        assert forbidden not in serialized
