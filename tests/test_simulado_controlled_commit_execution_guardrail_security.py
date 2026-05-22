import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_commit_execution_guardrail import (
    SimuladoControlledRuntimeCommitExecutionGuardrailService,
)
from tests.fixtures.simulado_controlled_commit_execution_guardrails import (
    api_readonly_fixture,
    build_controlled_commit_execution_guardrail,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_controlled_commit_execution_guardrail_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_controlled_commit_execution_guardrail(fixture)
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
    assert "final_pedagogical_update_event" not in dumped_keys


def test_controlled_commit_execution_guardrail_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_controlled_commit_execution_guardrail(fixture)
    assert result is not None
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    service = SimuladoControlledRuntimeCommitExecutionGuardrailService(repository)

    before_commit_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        commit_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    before_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        commit_transaction.source_explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    before_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        commit_transaction.source_commit_shell_id,
        user_id=fixture.context.user_id,
    )
    before_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        commit_transaction.source_mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    before_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        commit_transaction.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    before_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        commit_transaction.source_apply_shell_id,
        user_id=fixture.context.user_id,
    )
    before_application = repository.get_simulado_runtime_progress_application_by_id(
        commit_transaction.source_application_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_execution_guardrail(
        commit_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_execution_guardrail_by_id(
        result.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )

    after_commit_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        commit_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        commit_transaction.source_explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    after_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        commit_transaction.source_commit_shell_id,
        user_id=fixture.context.user_id,
    )
    after_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        commit_transaction.source_mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        commit_transaction.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    after_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        commit_transaction.source_apply_shell_id,
        user_id=fixture.context.user_id,
    )
    after_application = repository.get_simulado_runtime_progress_application_by_id(
        commit_transaction.source_application_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_commit_transaction is not None
    assert before_explicit_commit is not None
    assert before_shell is not None
    assert before_mutation_transaction is not None
    assert before_explicit_apply is not None
    assert before_apply_shell is not None
    assert before_application is not None
    assert loaded is not None
    assert by_id is not None
    assert after_commit_transaction is not None
    assert after_explicit_commit is not None
    assert after_shell is not None
    assert after_mutation_transaction is not None
    assert after_explicit_apply is not None
    assert after_apply_shell is not None
    assert after_application is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_commit_transaction.model_dump(mode="json") == after_commit_transaction.model_dump(mode="json")
    assert before_explicit_commit.model_dump(mode="json") == after_explicit_commit.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_mutation_transaction.model_dump(mode="json") == after_mutation_transaction.model_dump(mode="json")
    assert before_explicit_apply.model_dump(mode="json") == after_explicit_apply.model_dump(mode="json")
    assert before_apply_shell.model_dump(mode="json") == after_apply_shell.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
