import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from tests.fixtures.simulado_blueprint_sources import (
    ALL_SIMULADO_BLUEPRINT_FIXTURES,
    ambiguous_topic_blueprint_fixture,
    cebraspe_multiple_choice_5_blueprint_fixture,
    cebraspe_true_false_confirmed_scoring_blueprint_fixture,
    cebraspe_true_false_unconfirmed_scoring_blueprint_fixture,
    conflicting_format_blueprint_fixture,
    edital_weight_hint_distribution_blueprint_fixture,
    fgv_mixed_discursive_hint_blueprint_fixture,
    fgv_multiple_choice_5_blueprint_fixture,
    insufficient_sources_blueprint_fixture,
    material_blocked_blueprint_fixture,
    multi_subject_balanced_blueprint_fixture,
    no_question_generation_safety_fixture,
    no_ready_topics_blueprint_fixture,
    ocr_blocked_blueprint_fixture,
    profile_hint_distribution_blueprint_fixture,
    pscpp_technical_maritime_blueprint_fixture,
    pscpp_with_ocr_and_material_gaps_blueprint_fixture,
    run_simulado_blueprint_fixture,
    unknown_format_blueprint_fixture,
    weak_topic_allocation_blueprint_fixture,
    mixed_ready_blocked_blueprint_fixture,
)


FORBIDDEN_SLOT_FIELDS = {
    "question_text",
    "stem",
    "statement",
    "options",
    "answer",
    "correct_answer",
    "distractors",
    "explanation",
    "gabarito",
}


def assert_json_safe(model) -> None:
    dumped = json.dumps(model.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def slot_by_topic(blueprint, title: str):
    return next(item for item in blueprint.question_slots if item.target_topic_id.endswith(title) or item.metadata.get("topic_title") == title)


def test_simulado_blueprint_fixture_sanity_is_deterministic_and_json_safe():
    for builder in ALL_SIMULADO_BLUEPRINT_FIXTURES:
        first = builder()
        second = builder()
        assert first["graph"].model_dump(mode="json") == second["graph"].model_dump(mode="json")
        if first.get("edital_result") is not None:
            assert first["edital_result"].model_dump(mode="json") == second["edital_result"].model_dump(mode="json")
            json.dumps(first["edital_result"].model_dump(mode="json"), ensure_ascii=True)
        assert len(json.dumps(first["graph"].model_dump(mode="json"), ensure_ascii=True)) < 16000


def test_cebraspe_and_fgv_fixtures_respect_format_and_scoring_rules(tmp_path):
    ce_confirmed = run_simulado_blueprint_fixture(tmp_path / "ce-confirmed", cebraspe_true_false_confirmed_scoring_blueprint_fixture())
    ce_unconfirmed = run_simulado_blueprint_fixture(tmp_path / "ce-unconfirmed", cebraspe_true_false_unconfirmed_scoring_blueprint_fixture())
    ce_ae = run_simulado_blueprint_fixture(tmp_path / "ce-ae", cebraspe_multiple_choice_5_blueprint_fixture())
    fgv = run_simulado_blueprint_fixture(tmp_path / "fgv", fgv_multiple_choice_5_blueprint_fixture())
    fgv_mixed = run_simulado_blueprint_fixture(tmp_path / "fgv-mixed", fgv_mixed_discursive_hint_blueprint_fixture())

    assert ce_confirmed["blueprint"].sections[0].section_type == "true_false_block"
    assert ce_confirmed["blueprint"].format_type == "true_false"
    assert all(slot.format_type == "true_false" for slot in ce_confirmed["blueprint"].question_slots)
    assert ce_confirmed["blueprint"].scoring_plan.negative_marking is True
    assert ce_confirmed["blueprint"].scoring_plan.scoring_source == "explicit_edital"
    assert all(slot.generation_style == "assertion_based" for slot in ce_confirmed["blueprint"].question_slots)

    assert ce_unconfirmed["blueprint"].sections[0].section_type == "true_false_block"
    assert ce_unconfirmed["blueprint"].scoring_plan.negative_marking is False
    assert ce_unconfirmed["blueprint"].scoring_plan.scoring_source == "exam_profile_hint"
    assert "scoring_requires_confirmation" in {item.code for item in ce_unconfirmed["blueprint"].warnings}
    assert any(item.constraint_type == "scoring_requires_confirmation" for item in ce_unconfirmed["blueprint"].generation_constraints)

    assert ce_ae["blueprint"].sections[0].section_type == "multiple_choice_block"
    assert ce_ae["blueprint"].format_type == "multiple_choice_5"
    assert all(slot.format_type == "multiple_choice_5" for slot in ce_ae["blueprint"].question_slots)

    assert fgv["blueprint"].sections[0].section_type == "multiple_choice_block"
    assert all(slot.format_type == "multiple_choice_5" for slot in fgv["blueprint"].question_slots)
    assert all(slot.generation_style in {"interpretive", "case_based", "applied_problem_solving"} for slot in fgv["blueprint"].question_slots)
    assert fgv["blueprint"].scoring_plan.negative_marking is False

    assert any(section.section_type == "discursive_hint" for section in fgv_mixed["blueprint"].sections)
    assert any("discursive" in section.format_type for section in fgv_mixed["blueprint"].sections if section.section_type == "discursive_hint")
    assert any("question" not in item.description.lower() for item in fgv_mixed["blueprint"].generation_constraints)


def test_pscpp_and_blocked_source_fixtures_preserve_family_and_constraints(tmp_path):
    pscpp = run_simulado_blueprint_fixture(tmp_path / "pscpp", pscpp_technical_maritime_blueprint_fixture())
    pscpp_blocked = run_simulado_blueprint_fixture(tmp_path / "pscpp-blocked", pscpp_with_ocr_and_material_gaps_blueprint_fixture())
    material_blocked = run_simulado_blueprint_fixture(tmp_path / "material-blocked", material_blocked_blueprint_fixture())
    ocr_blocked = run_simulado_blueprint_fixture(tmp_path / "ocr-blocked", ocr_blocked_blueprint_fixture())

    assert pscpp["blueprint"].exam_family == "PSCPP"
    assert pscpp["blueprint"].sections[0].section_type == "technical_maritime_block"
    assert all(slot.generation_style == "technical_maritime" for slot in pscpp["blueprint"].question_slots)
    assert pscpp["blueprint"].metadata["allow_english_terms"] is True
    assert pscpp["blueprint"].metadata["bibliography_driven"] is True
    assert any(item.constraint_type == "require_source_topic_mapping" for item in pscpp["blueprint"].generation_constraints)

    assert pscpp_blocked["blueprint"].readiness_profile.readiness_state in {
        "blueprint_partially_ready",
        "blueprint_ocr_blocked",
        "blueprint_material_blocked",
    }
    assert any(slot.readiness_state == "blocked_by_ocr" for slot in pscpp_blocked["blueprint"].question_slots)
    assert any(slot.readiness_state == "blocked_by_material_gap" for slot in pscpp_blocked["blueprint"].question_slots)
    assert any("blocked" in text.lower() or "ocr" in text.lower() for text in pscpp_blocked["blueprint"].rationale.reasoning)

    assert material_blocked["blueprint"].readiness_profile.readiness_state in {
        "blueprint_material_blocked",
        "blueprint_ocr_blocked",
        "blueprint_not_ready",
    }
    assert material_blocked["blueprint"].readiness_profile.ready_slot_count == 0
    assert any(item.constraint_type == "avoid_uncovered_topic" for item in material_blocked["blueprint"].generation_constraints)

    assert ocr_blocked["blueprint"].readiness_profile.ocr_blocked_count >= 1
    assert any(item.constraint_type == "avoid_ocr_blocked_topic" for item in ocr_blocked["blueprint"].generation_constraints)
    assert all(slot.readiness_state != "ready_for_generation" for slot in ocr_blocked["blueprint"].question_slots)


def test_unknown_conflicting_ambiguous_and_mixed_fixtures_stay_conservative(tmp_path):
    unknown = run_simulado_blueprint_fixture(tmp_path / "unknown", unknown_format_blueprint_fixture())
    conflicting = run_simulado_blueprint_fixture(tmp_path / "conflicting", conflicting_format_blueprint_fixture())
    ambiguous = run_simulado_blueprint_fixture(tmp_path / "ambiguous", ambiguous_topic_blueprint_fixture())
    mixed = run_simulado_blueprint_fixture(tmp_path / "mixed", mixed_ready_blocked_blueprint_fixture())
    weak = run_simulado_blueprint_fixture(tmp_path / "weak", weak_topic_allocation_blueprint_fixture())

    assert unknown["blueprint"].format_type == "unknown"
    assert unknown["blueprint"].readiness_profile.readiness_state in {"blueprint_ambiguous", "blueprint_partially_ready"}
    assert any(item.constraint_type == "format_requires_confirmation" for item in unknown["blueprint"].generation_constraints)

    assert conflicting["blueprint"].readiness_profile.readiness_state in {"blueprint_ambiguous", "blueprint_partially_ready"}
    assert any(item.code in {"format_requires_confirmation", "ambiguous_format_signals", "conflicting_format_signals"} for item in conflicting["blueprint"].warnings)
    assert conflicting["blueprint"].format_type in {"unknown", "mixed", "multiple_choice_5", "true_false"}

    assert ambiguous["blueprint"].readiness_profile.readiness_state in {"blueprint_ambiguous", "blueprint_partially_ready"}
    assert any(slot.readiness_state == "blocked_by_ambiguity" for slot in ambiguous["blueprint"].question_slots)
    assert any(item.constraint_type == "require_manual_review" for item in ambiguous["blueprint"].generation_constraints)

    readiness_states = {slot.readiness_state for slot in mixed["blueprint"].question_slots}
    assert {"ready_for_generation", "needs_review", "blocked_by_ocr", "blocked_by_ambiguity"} <= readiness_states
    assert mixed["blueprint"].coverage_plan.covered_topic_slots >= 1
    assert mixed["blueprint"].coverage_plan.ambiguous_slots >= 1
    assert mixed["blueprint"].readiness_profile.readiness_state in {"blueprint_partially_ready", "blueprint_material_blocked", "blueprint_ambiguous"}
    assert mixed["blueprint"].rationale.priorities
    assert mixed["blueprint"].rationale.limitations

    assert weak["blueprint"].distribution_plan.weak_topic_allocation
    assert weak["blueprint"].readiness_profile.ready_slot_count == 0
    assert weak["blueprint"].readiness_profile.review_needed_slot_count >= 1


def test_distribution_timing_and_source_selection_fixtures_are_stable(tmp_path):
    explicit_distribution = run_simulado_blueprint_fixture(
        tmp_path / "explicit-distribution",
        edital_weight_hint_distribution_blueprint_fixture(),
    )
    profile_distribution = run_simulado_blueprint_fixture(
        tmp_path / "profile-distribution",
        profile_hint_distribution_blueprint_fixture(),
    )
    multi_subject = run_simulado_blueprint_fixture(
        tmp_path / "multi-subject",
        multi_subject_balanced_blueprint_fixture(),
    )

    assert explicit_distribution["blueprint"].distribution_plan.question_count_source == "explicit_edital"
    assert explicit_distribution["blueprint"].distribution_plan.total_question_count == 80
    assert explicit_distribution["blueprint"].timing_plan.duration_source in {"explicit_edital", "exam_profile_hint", "default_candidate"}

    assert profile_distribution["blueprint"].distribution_plan.question_count_source == "exam_profile_hint"
    assert profile_distribution["blueprint"].distribution_plan.total_question_count > 0
    assert any(item.constraint_type == "question_count_requires_confirmation" for item in profile_distribution["blueprint"].generation_constraints)

    assert multi_subject["blueprint"].timing_plan.duration_source in {"explicit_edital", "exam_profile_hint", "default_candidate"}
    assert multi_subject["blueprint"].timing_plan.estimated_minutes_per_question > 0
    assert multi_subject["blueprint"].timing_plan.timing_pressure in {"low", "moderate", "high", "unknown"}
    assert [slot.target_subject_id for slot in multi_subject["blueprint"].question_slots] == [
        "subject:nav",
        "subject:meteo",
        "subject:leg",
    ]
    assert list(multi_subject["blueprint"].distribution_plan.subject_distribution.keys()) == [
        "subject:nav",
        "subject:meteo",
        "subject:leg",
    ]


def test_insufficient_sources_no_ready_topics_and_no_question_generation_safety(tmp_path):
    repository = JsonStudyRepository(tmp_path / "insufficient" / "study_data.json")
    builder = SimuladoBlueprintBuilderService(repository)
    missing_state = builder.build_blueprint("cycle:missing", user_id="user-a")
    insufficient = run_simulado_blueprint_fixture(tmp_path / "insufficient-fixture", insufficient_sources_blueprint_fixture())
    no_ready = run_simulado_blueprint_fixture(tmp_path / "no-ready", no_ready_topics_blueprint_fixture())
    safety = run_simulado_blueprint_fixture(tmp_path / "safety", no_question_generation_safety_fixture())

    assert missing_state.status == "insufficient_cycle"
    assert insufficient["blueprint_state"].status in {"insufficient_profile", "insufficient_sources"}
    assert insufficient["blueprint"].question_slots == []

    assert no_ready["blueprint"].readiness_profile.ready_slot_count == 0
    assert no_ready["blueprint"].readiness_profile.readiness_state in {
        "blueprint_material_blocked",
        "blueprint_ocr_blocked",
        "blueprint_not_ready",
        "blueprint_ambiguous",
    }

    assert any(item.constraint_type == "no_question_generation_in_this_pass" for item in safety["blueprint"].generation_constraints)
    for slot in safety["blueprint"].question_slots:
        payload = slot.model_dump(mode="json")
        assert FORBIDDEN_SLOT_FIELDS.isdisjoint(payload.keys())


def test_simulado_blueprint_outputs_are_json_safe_deterministic_and_user_scoped(tmp_path):
    first = run_simulado_blueprint_fixture(tmp_path / "first", no_question_generation_safety_fixture())
    second = run_simulado_blueprint_fixture(tmp_path / "second", no_question_generation_safety_fixture())
    rerun_state = SimuladoBlueprintBuilderService(first["repository"]).build_blueprint(
        first["blueprint"].cycle_id,
        user_id="user-a",
    )
    rerun_blueprint = first["repository"].get_simulado_blueprint(first["blueprint"].cycle_id, user_id="user-a")
    owner = run_simulado_blueprint_fixture(tmp_path / "owner", fgv_multiple_choice_5_blueprint_fixture(), user_id="owner")
    other = run_simulado_blueprint_fixture(tmp_path / "other", unknown_format_blueprint_fixture(), user_id="other")

    assert first["blueprint_state"].blueprint_id == second["blueprint_state"].blueprint_id
    assert first["blueprint_state"].model_dump(mode="json") == rerun_state.model_dump(mode="json")
    assert first["blueprint"].model_dump(mode="json") == rerun_blueprint.model_dump(mode="json")
    assert_json_safe(first["blueprint_state"])
    assert_json_safe(first["blueprint"])
    assert all(0.0 <= slot.confidence <= 1.0 for slot in first["blueprint"].question_slots)
    assert all(slot.reasoning for slot in first["blueprint"].question_slots)
    assert 0.0 <= first["blueprint"].rationale.confidence <= 1.0
    assert owner["repository"].get_simulado_blueprint(owner["blueprint"].cycle_id, user_id="other") is None
    assert owner["repository"].get_simulado_blueprint_by_id(owner["blueprint"].blueprint_id, user_id="other") is None
    assert other["blueprint_state"].status in {"ready_for_review", "insufficient_profile"}
