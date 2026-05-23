import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_pedagogical_update_event import (
    SimuladoFinalPedagogicalUpdateEventService,
)
from tests.fixtures.simulado_final_pedagogical_update_events import (
    api_readonly_fixture,
    build_final_pedagogical_update_event,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_final_pedagogical_update_event_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_final_pedagogical_update_event(fixture)
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
    assert "commit_execution_event" not in dumped_keys
    assert "mutation_commit_event" not in dumped_keys
    assert "runtime_application_event" not in dumped_keys
    assert "applied_final_pedagogical_update_event" not in dumped_keys


def test_final_pedagogical_update_event_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_final_pedagogical_update_event(fixture)
    assert result is not None
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    service = SimuladoFinalPedagogicalUpdateEventService(repository)

    before_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    before_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        controlled_execution.source_execution_plan_id,
        user_id=fixture.context.user_id,
    )
    before_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        controlled_execution.source_execution_approval_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        controlled_execution.source_execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_final_event(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_final_event_by_id(
        result.final_event_id,
        user_id=fixture.context.user_id,
    )

    after_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    after_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        controlled_execution.source_execution_plan_id,
        user_id=fixture.context.user_id,
    )
    after_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        controlled_execution.source_execution_approval_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        controlled_execution.source_execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_controlled is not None
    assert before_plan is not None
    assert before_approval is not None
    assert before_guardrail is not None
    assert loaded is not None
    assert by_id is not None
    assert after_controlled is not None
    assert after_plan is not None
    assert after_approval is not None
    assert after_guardrail is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_controlled.model_dump(mode="json") == after_controlled.model_dump(mode="json")
    assert before_plan.model_dump(mode="json") == after_plan.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
