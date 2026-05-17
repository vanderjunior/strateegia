import json

from app.repositories.json_store import JsonStudyRepository
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from tests.fixtures.study_cycle_graphs import (
    ALL_STUDY_CYCLE_FIXTURES,
    ambiguous_topic_cycle_fixture,
    balanced_cycle_fixture,
    covered_topic_cycle_fixture,
    empty_or_insufficient_graph_fixture,
    gap_heavy_cycle_fixture,
    maritime_praticagem_cycle_fixture,
    material_blocked_cycle_fixture,
    missing_document_text_cycle_fixture,
    mixed_complex_cycle_fixture,
    multi_subject_rotation_fixture,
    ocr_required_cycle_fixture,
    partial_topic_cycle_fixture,
    redundancy_cycle_fixture,
    review_heavy_cycle_fixture,
    uncovered_topic_cycle_fixture,
    weak_topic_cycle_fixture,
)


def run_study_cycle_fixture(tmp_path, fixture: dict[str, object], *, user_id: str = "user-a") -> dict[str, object]:
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = StudyCycleOrchestratorService(repository)
    graph = fixture["graph"].model_copy(update={"user_id": user_id})
    repository.save_curriculum_graph(graph, user_id=user_id)
    state = service.build_cycle(graph.graph_id, user_id=user_id)
    plan = repository.get_study_cycle_plan(graph.graph_id, user_id=user_id)
    return {
        "repository": repository,
        "service": service,
        "graph": graph,
        "state": state,
        "plan": plan,
    }


def topic_slot_by_title(plan, title: str):
    return next(item for item in plan.topic_slots if item.topic_title == title)


def review_slot_by_title(plan, title: str):
    return next(item for item in plan.review_slots if item.topic_title == title)


def rotation_by_title(plan, title: str):
    return next(item for item in plan.subject_rotations if item.subject_title == title)


def gap_slot_by_title(plan, title: str):
    return next(item for item in plan.gap_slots if item.target_title == title)


def assert_json_safe(model) -> None:
    dumped = json.dumps(model.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def test_study_cycle_fixture_sanity_is_deterministic_and_json_safe():
    for builder in ALL_STUDY_CYCLE_FIXTURES:
        first = builder()
        second = builder()
        assert first["graph"].model_dump(mode="json") == second["graph"].model_dump(mode="json")
        json.dumps(first["graph"].model_dump(mode="json"), ensure_ascii=True)


def test_covered_partial_and_weak_fixtures_generate_conservative_slots(tmp_path):
    covered = run_study_cycle_fixture(tmp_path / "covered", covered_topic_cycle_fixture())
    partial = run_study_cycle_fixture(tmp_path / "partial", partial_topic_cycle_fixture())
    weak = run_study_cycle_fixture(tmp_path / "weak", weak_topic_cycle_fixture())

    covered_slot = topic_slot_by_title(covered["plan"], "RIPEAM")
    partial_slot = topic_slot_by_title(partial["plan"], "Meteorologia")
    weak_slot = topic_slot_by_title(weak["plan"], "Comunicacoes")

    assert covered_slot.slot_type == "reinforce"
    assert covered_slot.suggested_action == "reinforce_with_existing_material"
    assert covered_slot.intensity_level in {"light", "moderate"}
    assert covered["plan"].gap_slots == []
    assert covered["plan"].review_slots == []
    assert covered_slot.source_evidence_ids

    assert partial_slot.slot_type in {"review_needed", "reinforce"}
    assert partial_slot.intensity_level == "moderate"
    assert partial_slot.coverage_state == "partially_covered"
    assert covered_slot.slot_type != partial_slot.slot_type or partial["plan"].review_slots
    assert review_slot_by_title(partial["plan"], "Meteorologia").review_trigger == "partial_coverage"

    assert weak_slot.slot_type == "weak_topic_resurfacing"
    assert weak_slot.intensity_level in {"moderate", "high"}
    assert review_slot_by_title(weak["plan"], "Comunicacoes").review_trigger == "weak_coverage"
    assert any("Weak" in item or "weak" in item for item in weak["plan"].rationale.reasons)


def test_uncovered_ocr_missing_text_and_ambiguous_fixtures_remain_safe(tmp_path):
    uncovered = run_study_cycle_fixture(tmp_path / "uncovered", uncovered_topic_cycle_fixture())
    ocr = run_study_cycle_fixture(tmp_path / "ocr", ocr_required_cycle_fixture())
    missing_text = run_study_cycle_fixture(tmp_path / "missing-text", missing_document_text_cycle_fixture())
    ambiguous = run_study_cycle_fixture(tmp_path / "ambiguous", ambiguous_topic_cycle_fixture())

    uncovered_slot = topic_slot_by_title(uncovered["plan"], "Arte Naval")
    assert uncovered_slot.slot_type in {"gap_blocked", "learn"}
    assert uncovered_slot.slot_type != "reinforce"
    assert uncovered_slot.suggested_action in {"resolve_material_gap", "study_now_candidate"}
    assert gap_slot_by_title(uncovered["plan"], "Arte Naval").gap_type == "uncovered_topic"

    ocr_slot = topic_slot_by_title(ocr["plan"], "Legislacao Maritima")
    assert ocr_slot.slot_type == "ocr_blocked"
    assert ocr_slot.suggested_action in {"process_ocr_material", "defer_until_material_available"}
    assert gap_slot_by_title(ocr["plan"], "Legislacao Maritima").suggested_resolution == "run_ocr_future"
    assert ocr["plan"].balance_summary.ocr_blocked_slot_count >= 1

    missing_text_slot = topic_slot_by_title(missing_text["plan"], "Navegacao Costeira")
    assert missing_text_slot.slot_type == "gap_blocked"
    assert missing_text_slot.suggested_action == "resolve_material_gap"
    assert gap_slot_by_title(missing_text["plan"], "Navegacao Costeira").suggested_resolution == "process_existing_material"

    ambiguous_slot = topic_slot_by_title(ambiguous["plan"], "Navegacao Costeira")
    assert ambiguous_slot.slot_type == "ambiguous_review"
    assert ambiguous_slot.suggested_action == "manual_review_required"
    assert review_slot_by_title(ambiguous["plan"], "Navegacao Costeira").review_trigger == "ambiguity"


def test_redundancy_gap_heavy_review_heavy_and_material_blocked_are_preserved(tmp_path):
    redundancy = run_study_cycle_fixture(tmp_path / "redundancy", redundancy_cycle_fixture())
    gap_heavy = run_study_cycle_fixture(tmp_path / "gap-heavy", gap_heavy_cycle_fixture())
    review_heavy = run_study_cycle_fixture(tmp_path / "review-heavy", review_heavy_cycle_fixture())
    material_blocked = run_study_cycle_fixture(tmp_path / "material-blocked", material_blocked_cycle_fixture())

    redundancy_slot = topic_slot_by_title(redundancy["plan"], "Meteorologia")
    assert redundancy_slot.slot_type == "ambiguous_review"
    assert redundancy_slot.redundancy_ids
    assert review_slot_by_title(redundancy["plan"], "Meteorologia").metadata["redundancy_ids"]

    assert len(gap_heavy["plan"].gap_slots) >= 4
    assert gap_heavy["plan"].balance_summary.balance_state in {"gap_heavy", "material_blocked"}
    assert gap_heavy["plan"].fatigue_profile.fatigue_risk_level in {"moderate", "high", "unknown"}
    assert any("gap" in item.lower() or "ocr" in item.lower() for item in gap_heavy["plan"].rationale.reasons)

    assert len(review_heavy["plan"].review_slots) >= 3
    assert review_heavy["plan"].balance_summary.balance_state in {"review_heavy", "balanced_candidate"}
    assert {item.slot_type for item in review_heavy["plan"].topic_slots} >= {"review_needed", "weak_topic_resurfacing", "ambiguous_review"}

    assert material_blocked["plan"].balance_summary.balance_state in {"material_blocked", "gap_heavy"}
    assert material_blocked["plan"].balance_summary.gap_blocked_slot_count + material_blocked["plan"].balance_summary.ocr_blocked_slot_count >= 2
    assert all(
        item.suggested_action in {"resolve_material_gap", "process_ocr_material"}
        for item in material_blocked["plan"].topic_slots
    )


def test_balanced_and_multi_subject_fixtures_keep_rotation_and_summary_stable(tmp_path):
    balanced = run_study_cycle_fixture(tmp_path / "balanced", balanced_cycle_fixture())
    multi = run_study_cycle_fixture(tmp_path / "multi", multi_subject_rotation_fixture())

    assert balanced["plan"].balance_summary.balance_state in {"balanced_candidate", "coverage_heavy"}
    assert len(balanced["plan"].gap_slots) == 0
    assert balanced["plan"].fatigue_profile.fatigue_risk_level in {"low", "moderate"}
    assert [item.topic_title for item in balanced["plan"].topic_slots] == [
        "RIPEAM",
        "Meteorologia",
        "Comunicacoes",
        "Cartas Nauticas",
    ]

    assert [item.subject_title for item in multi["plan"].subject_rotations] == [
        "Navegacao",
        "Meteorologia",
        "Legislacao",
    ]
    assert [item.rotation_id for item in multi["plan"].subject_rotations] == [
        "rotation:subject:nav",
        "rotation:subject:meteo",
        "rotation:subject:leg",
    ]
    assert rotation_by_title(multi["plan"], "Navegacao").suggested_frequency == "low"
    assert rotation_by_title(multi["plan"], "Meteorologia").suggested_frequency in {"medium", "high"}
    assert rotation_by_title(multi["plan"], "Legislacao").suggested_frequency == "unavailable"


def test_maritime_and_mixed_complex_fixtures_cover_expected_cycle_states(tmp_path):
    maritime = run_study_cycle_fixture(tmp_path / "maritime", maritime_praticagem_cycle_fixture())
    mixed = run_study_cycle_fixture(tmp_path / "mixed", mixed_complex_cycle_fixture())

    maritime_titles = [item.topic_title for item in maritime["plan"].topic_slots]
    assert maritime_titles == [
        "Arte Naval",
        "RIPEAM",
        "Manobra",
        "Meteorologia",
        "Legislacao Maritima",
    ]
    assert topic_slot_by_title(maritime["plan"], "RIPEAM").slot_type == "reinforce"
    assert topic_slot_by_title(maritime["plan"], "Meteorologia").slot_type == "reinforce"
    assert topic_slot_by_title(maritime["plan"], "Manobra").slot_type == "weak_topic_resurfacing"
    assert topic_slot_by_title(maritime["plan"], "Arte Naval").slot_type == "gap_blocked"
    assert topic_slot_by_title(maritime["plan"], "Legislacao Maritima").slot_type == "ocr_blocked"

    mixed_slot_types = {item.slot_type for item in mixed["plan"].topic_slots}
    assert {"reinforce", "review_needed", "weak_topic_resurfacing", "ocr_blocked", "ambiguous_review"} <= mixed_slot_types
    assert mixed["plan"].review_slots
    assert mixed["plan"].gap_slots
    assert mixed["plan"].balance_summary.balance_state in {"gap_heavy", "review_heavy", "material_blocked", "balanced_candidate"}
    assert mixed["plan"].rationale.summary
    assert mixed["plan"].rationale.limitations


def test_empty_or_insufficient_graph_fixture_is_safe_and_does_not_fake_slots(tmp_path):
    context = run_study_cycle_fixture(tmp_path / "empty", empty_or_insufficient_graph_fixture())
    repository = JsonStudyRepository(tmp_path / "missing" / "study_data.json")
    service = StudyCycleOrchestratorService(repository)
    missing_state = service.build_cycle("graph:missing", user_id="user-a")

    assert context["state"].status == "insufficient_graph"
    assert context["plan"].topic_slots == []
    assert context["plan"].review_slots == []
    assert context["plan"].gap_slots == []
    assert any(item.code == "insufficient_curriculum_graph" for item in context["plan"].warnings)
    assert missing_state.status == "insufficient_graph"
    assert_json_safe(context["state"])
    assert_json_safe(context["plan"])


def test_cycle_outputs_are_json_safe_and_preserve_confidence_reasoning_and_rationale(tmp_path):
    context = run_study_cycle_fixture(tmp_path, mixed_complex_cycle_fixture())
    state = context["state"]
    plan = context["plan"]

    assert_json_safe(state)
    assert_json_safe(plan)
    assert all(0.0 <= item.confidence <= 1.0 for item in plan.subject_rotations)
    assert all(item.reasoning for item in plan.subject_rotations)
    assert all(0.0 <= item.confidence <= 1.0 for item in plan.topic_slots)
    assert all(item.reasoning for item in plan.topic_slots)
    assert all(0.0 <= item.confidence <= 1.0 for item in plan.review_slots)
    assert all(item.reasoning for item in plan.review_slots)
    assert 0.0 <= plan.rationale.confidence <= 1.0
    assert plan.rationale.summary
    assert plan.rationale.limitations
    assert plan.rationale.source_graph_id == context["graph"].graph_id


def test_study_cycle_fixture_flow_is_deterministic_and_idempotent(tmp_path):
    fixture = mixed_complex_cycle_fixture()
    first = run_study_cycle_fixture(tmp_path / "first", fixture)
    second = run_study_cycle_fixture(tmp_path / "second", fixture)
    rerun_state = first["service"].build_cycle(first["graph"].graph_id, user_id="user-a")
    rerun_plan = first["repository"].get_study_cycle_plan(first["graph"].graph_id, user_id="user-a")

    assert first["state"].cycle_id == second["state"].cycle_id
    assert [item.topic_title for item in first["plan"].topic_slots] == [item.topic_title for item in second["plan"].topic_slots]
    assert [item.slot_type for item in first["plan"].topic_slots] == [item.slot_type for item in second["plan"].topic_slots]
    assert first["state"].model_dump(mode="json") == rerun_state.model_dump(mode="json")
    assert first["plan"].model_dump(mode="json") == rerun_plan.model_dump(mode="json")
    json.dumps(first["state"].model_dump(mode="json"), ensure_ascii=True)
    json.dumps(first["plan"].model_dump(mode="json"), ensure_ascii=True)


def test_study_cycle_fixture_flow_respects_user_scope(tmp_path):
    owner = run_study_cycle_fixture(tmp_path / "owner", covered_topic_cycle_fixture(), user_id="owner")
    other = run_study_cycle_fixture(tmp_path / "other", empty_or_insufficient_graph_fixture(), user_id="other")

    assert owner["plan"].topic_slots
    assert other["state"].status == "insufficient_graph"
    assert owner["repository"].get_study_cycle_plan(owner["graph"].graph_id, user_id="other") is None
    assert owner["repository"].get_study_cycle_plan_by_id(owner["state"].cycle_id, user_id="other") is None
