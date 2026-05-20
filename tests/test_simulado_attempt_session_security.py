import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_session import SimuladoAttemptSessionService
from tests.fixtures.simulado_execution_shells import (
    approved_candidates_not_executable_fixture,
    bounded_summary_fixture,
    build_execution_shell,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_simulado_attempt_session_does_not_leak_sensitive_or_final_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = bounded_summary_fixture(tmp_path, repository=repository)
    execution_shell = build_execution_shell(fixture)
    assert execution_shell is not None

    result = SimuladoAttemptSessionService(repository).build_attempt_session(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
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
    assert "answer_submission" not in dumped_keys
    assert "submitted_answers" not in dumped_keys
    assert "correction_result" not in dumped_keys
    assert "score" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def test_simulado_attempt_session_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = approved_candidates_not_executable_fixture(tmp_path, repository=repository)
    execution_shell = build_execution_shell(fixture)
    assert execution_shell is not None
    service = SimuladoAttemptSessionService(repository)

    before_execution_shell = repository.get_simulado_execution_shell_by_id(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    before_approval = repository.get_simulado_final_approval_artifact_by_id(
        execution_shell.source_final_approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = repository.get_simulado_finalization_guardrail_by_id(
        execution_shell.source_finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_shell = repository.get_simulado_attempt_shell_by_id(
        execution_shell.source_attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    before_assembly = repository.get_simulado_question_assembly_by_id(
        execution_shell.source_assembly_id,
        user_id=fixture.context.user_id,
    )

    built = service.build_attempt_session(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    assert built is not None
    loaded = service.get_attempt_session(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_attempt_session_by_id(
        built.attempt_session_id,
        user_id=fixture.context.user_id,
    )

    after_execution_shell = repository.get_simulado_execution_shell_by_id(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    after_approval = repository.get_simulado_final_approval_artifact_by_id(
        execution_shell.source_final_approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_finalization_guardrail_by_id(
        execution_shell.source_finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_shell = repository.get_simulado_attempt_shell_by_id(
        execution_shell.source_attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    after_assembly = repository.get_simulado_question_assembly_by_id(
        execution_shell.source_assembly_id,
        user_id=fixture.context.user_id,
    )

    assert before_execution_shell is not None
    assert before_approval is not None
    assert before_guardrail is not None
    assert before_attempt_shell is not None
    assert before_assembly is not None
    assert loaded is not None
    assert by_id is not None
    assert after_execution_shell is not None
    assert after_approval is not None
    assert after_guardrail is not None
    assert after_attempt_shell is not None
    assert after_assembly is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_attempt_shell.model_dump(mode="json") == after_attempt_shell.model_dump(mode="json")
    assert before_assembly.model_dump(mode="json") == after_assembly.model_dump(mode="json")
