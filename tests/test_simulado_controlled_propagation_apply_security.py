import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_propagation_apply import (
    SimuladoControlledPropagationApplyService,
)
from tests.fixtures.simulado_controlled_propagation_applies import (
    build_controlled_propagation_apply,
    capture_controlled_propagation_apply_source_snapshot,
    safe_source_guardrail_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_controlled_propagation_apply_does_not_leak_sensitive_or_answer_key_content(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = safe_source_guardrail_fixture(tmp_path, repository=repository)
    result = build_controlled_propagation_apply(fixture)
    assert result is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "correct_answer" not in dumped_keys
    assert "correct_option" not in dumped_keys
    assert "answer_key" not in dumped_keys
    assert "answer_key_value" not in dumped_keys
    assert "gabarito" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "ranking_update_payload" not in dumped_keys
    assert "scheduler_update_payload" not in dumped_keys
    assert "retention_update_payload" not in dumped_keys
    assert "study_cycle_update_payload" not in dumped_keys
    assert "curriculum_graph_update_payload" not in dumped_keys
    assert "adaptive_tuning_payload" not in dumped_keys


def test_controlled_propagation_apply_build_and_get_do_not_mutate_source_artifacts(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = safe_source_guardrail_fixture(tmp_path, repository=repository)
    result = build_controlled_propagation_apply(fixture)
    assert result is not None
    service = SimuladoControlledPropagationApplyService(repository)

    before = capture_controlled_propagation_apply_source_snapshot(fixture)
    loaded = service.get_controlled_propagation_apply(
        result.source_propagation_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_controlled_propagation_apply_by_id(
        result.controlled_propagation_apply_id,
        user_id=fixture.context.user_id,
    )
    after = capture_controlled_propagation_apply_source_snapshot(fixture)

    assert loaded is not None
    assert by_id is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(
        mode="json"
    )
    assert before.propagation_guardrail == after.propagation_guardrail
    assert before.applied_event_ledger == after.applied_event_ledger
    assert before.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == after.final_event
    assert before.controlled_execution == after.controlled_execution
    assert before.execution_plan == after.execution_plan
    assert before.progress == after.progress
