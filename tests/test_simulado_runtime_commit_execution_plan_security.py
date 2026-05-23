import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_commit_execution_plan import (
    SimuladoRuntimeCommitExecutionPlanService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_commit_execution_plans import (
    api_readonly_fixture,
    build_runtime_commit_execution_plan,
)


def test_runtime_commit_execution_plan_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_runtime_commit_execution_plan(fixture)
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


def test_runtime_commit_execution_plan_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path, repository=repository)
    result = build_runtime_commit_execution_plan(fixture)
    assert result is not None
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    service = SimuladoRuntimeCommitExecutionPlanService(repository)

    before_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_approval.execution_approval_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_approval.source_execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        execution_approval.source_commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    before_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        execution_approval.source_explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    before_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        execution_approval.source_commit_shell_id,
        user_id=fixture.context.user_id,
    )
    before_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        execution_approval.source_mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    before_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        execution_approval.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    before_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        execution_approval.source_apply_shell_id,
        user_id=fixture.context.user_id,
    )
    before_application = repository.get_simulado_runtime_progress_application_by_id(
        execution_approval.source_application_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_execution_plan(
        execution_approval.execution_approval_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_execution_plan_by_id(
        result.execution_plan_id,
        user_id=fixture.context.user_id,
    )

    after_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_approval.execution_approval_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_approval.source_execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        execution_approval.source_commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        execution_approval.source_explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    after_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        execution_approval.source_commit_shell_id,
        user_id=fixture.context.user_id,
    )
    after_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        execution_approval.source_mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        execution_approval.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    after_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        execution_approval.source_apply_shell_id,
        user_id=fixture.context.user_id,
    )
    after_application = repository.get_simulado_runtime_progress_application_by_id(
        execution_approval.source_application_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_approval is not None
    assert before_guardrail is not None
    assert before_transaction is not None
    assert before_explicit_commit is not None
    assert before_shell is not None
    assert before_mutation_transaction is not None
    assert before_explicit_apply is not None
    assert before_apply_shell is not None
    assert before_application is not None
    assert loaded is not None
    assert by_id is not None
    assert after_approval is not None
    assert after_guardrail is not None
    assert after_transaction is not None
    assert after_explicit_commit is not None
    assert after_shell is not None
    assert after_mutation_transaction is not None
    assert after_explicit_apply is not None
    assert after_apply_shell is not None
    assert after_application is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")
    assert before_explicit_commit.model_dump(mode="json") == after_explicit_commit.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert (
        before_mutation_transaction.model_dump(mode="json")
        == after_mutation_transaction.model_dump(mode="json")
    )
    assert before_explicit_apply.model_dump(mode="json") == after_explicit_apply.model_dump(mode="json")
    assert before_apply_shell.model_dump(mode="json") == after_apply_shell.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
