import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_approval import SimuladoFinalApprovalService
from tests.fixtures.simulado_finalization_guardrails import (
    build_finalization_guardrail,
    bounded_summary_fixture,
    non_final_assembly_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_simulado_final_approval_does_not_leak_sensitive_or_final_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = bounded_summary_fixture(tmp_path, repository=repository)
    guardrail = build_finalization_guardrail(fixture)
    assert guardrail is not None
    result = SimuladoFinalApprovalService(repository).build_approval_artifact(
        guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {
                    "source_candidate_id": guardrail.candidate_summaries[0].source_question_candidate_id,
                    "decision_type": "approve_for_future_execution_review",
                    "reason": "Safe bounded approval record only.",
                }
            ]
        },
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
    assert "approved_simulado" not in dumped_keys
    assert "finalized_simulado" not in dumped_keys
    assert "student_attempt" not in dumped_keys
    assert "answer_submission" not in dumped_keys
    assert "correction_result" not in dumped_keys
    assert "scoring_result" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def test_simulado_final_approval_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = non_final_assembly_fixture(tmp_path, repository=repository)
    guardrail = build_finalization_guardrail(fixture)
    assert guardrail is not None
    service = SimuladoFinalApprovalService(repository)

    before_guardrail = repository.get_simulado_finalization_guardrail_by_id(
        guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_shell = repository.get_simulado_attempt_shell_by_id(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    before_assembly = repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    built = service.build_approval_artifact(
        guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {
                    "source_candidate_id": guardrail.candidate_summaries[0].source_question_candidate_id,
                    "decision_type": "mark_not_reviewed",
                    "reason": "No mutation expected.",
                }
            ]
        },
    )
    assert built is not None
    loaded = service.get_approval_artifact(
        guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_approval_artifact_by_id(
        built.approval_artifact_id,
        user_id=fixture.context.user_id,
    )

    after_guardrail = repository.get_simulado_finalization_guardrail_by_id(
        guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_shell = repository.get_simulado_attempt_shell_by_id(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    after_assembly = repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    assert before_guardrail is not None
    assert before_shell is not None
    assert before_assembly is not None
    assert loaded is not None
    assert by_id is not None
    assert after_guardrail is not None
    assert after_shell is not None
    assert after_assembly is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_assembly.model_dump(mode="json") == after_assembly.model_dump(mode="json")

