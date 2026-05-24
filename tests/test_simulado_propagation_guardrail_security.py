import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_propagation_guardrail import SimuladoPropagationGuardrailService
from tests.fixtures.simulado_propagation_guardrails import (
    build_propagation_guardrail,
    capture_propagation_guardrail_source_snapshot,
    successful_source_ledger_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_propagation_guardrail_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = successful_source_ledger_fixture(tmp_path, repository=repository)
    result = build_propagation_guardrail(fixture)
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


def test_propagation_guardrail_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = successful_source_ledger_fixture(tmp_path, repository=repository)
    result = build_propagation_guardrail(fixture)
    assert result is not None
    service = SimuladoPropagationGuardrailService(repository)

    before = capture_propagation_guardrail_source_snapshot(fixture)
    loaded = service.get_propagation_guardrail(
        result.source_applied_event_ledger_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_propagation_guardrail_by_id(
        result.propagation_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after = capture_propagation_guardrail_source_snapshot(fixture)

    assert loaded is not None
    assert by_id is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(
        mode="json"
    )
    assert before.applied_event_ledger == after.applied_event_ledger
    assert before.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == after.final_event
    assert before.controlled_execution == after.controlled_execution
    assert before.execution_plan == after.execution_plan
    assert before.progress == after.progress
