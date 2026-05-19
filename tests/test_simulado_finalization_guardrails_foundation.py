import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_shell import SimuladoAttemptShellService
from app.services.simulado_finalization_guardrails import SimuladoFinalizationGuardrailsService
from tests.fixtures.simulado_attempt_shells import (
    build_attempt_shell,
    idempotency_fixture,
    non_executable_assembly_fixture,
    ready_candidates_not_executable_fixture,
    zero_candidates_assembly_fixture,
)


FORBIDDEN_FINALIZATION_KEYS = {
    "approved_simulado",
    "finalized_simulado",
    "executable_simulado",
    "real_student_attempt",
    "student_attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "executable_question",
    "final_question_content",
    "final_answer_key_content",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation_content",
    "correction_rule",
    "auto_correction",
    "score_rule",
    "scoring_result",
    "exam_session",
}


def collect_json_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(collect_json_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(collect_json_keys(item))
        return keys
    return set()


def test_simulado_finalization_guardrail_handles_missing_attempt_shell_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoFinalizationGuardrailsService(repository)

    assert service.build_guardrail("simulado-attempt-shell:missing", user_id="user-a") is None
    assert repository.list_user_simulado_finalization_guardrails(user_id="user-a") == []


def test_simulado_finalization_guardrail_blocks_non_final_attempt_shell_and_assembly(tmp_path):
    fixture = non_executable_assembly_fixture(tmp_path)
    shell = build_attempt_shell(fixture)
    assert shell is not None

    result = SimuladoFinalizationGuardrailsService(fixture.context.repository).build_guardrail(
        shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    finding_codes = {item.code for item in result.validation_findings}

    assert result.readiness_state in {
        "blocked_by_non_final_assembly",
        "blocked_by_attempt_shell_not_executable",
        "blocked_by_human_review_required",
        "needs_human_approval_review",
    }
    assert result.finalizable_candidates_count == 0
    assert result.approved_candidates_count == 0
    assert result.approval_required is True
    assert result.human_review_required is True
    assert result.execution_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.student_submission_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.no_student_attempt_created is True
    assert result.no_answer_submission_enabled is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    assert "blocked_by_non_final_assembly" in blocker_codes
    assert "blocked_by_attempt_shell_not_executable" in blocker_codes
    assert "blocked_by_missing_final_questions" in blocker_codes
    assert "blocked_by_missing_final_answer_keys" in blocker_codes
    assert "blocked_by_missing_final_explanations" in blocker_codes
    assert "approval_required" in finding_codes
    assert "execution_disabled" in finding_codes
    assert "correction_disabled" in finding_codes
    assert "scoring_disabled" in finding_codes
    assert "student_submission_disabled" in finding_codes


def test_candidate_ready_for_review_still_does_not_mean_finalizable(tmp_path):
    fixture = ready_candidates_not_executable_fixture(tmp_path)
    shell = build_attempt_shell(fixture)
    assert shell is not None

    result = SimuladoFinalizationGuardrailsService(fixture.context.repository).build_guardrail(
        shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    assert result.review_ready_candidates > 0
    assert result.finalizable_candidates_count == 0
    assert result.execution_enabled is False
    assert result.human_review_required is True
    assert result.missing_final_questions_count == result.total_candidates
    assert result.missing_final_answer_keys_count == result.total_candidates
    assert result.missing_final_explanations_count == result.total_candidates
    assert result.candidate_summaries
    assert all(item.has_final_question is False for item in result.candidate_summaries)
    assert all(item.has_final_answer_key is False for item in result.candidate_summaries)
    assert all(item.has_final_explanation is False for item in result.candidate_summaries)
    assert all(item.approval_state == "approval_required" for item in result.candidate_summaries)


def test_finalization_guardrail_preserves_no_approval_no_execution_and_idempotency(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    shell = build_attempt_shell(fixture)
    assert shell is not None
    service = SimuladoFinalizationGuardrailsService(fixture.context.repository)

    first = service.build_guardrail(shell.attempt_shell_id, user_id=fixture.context.user_id)
    second = service.build_guardrail(shell.attempt_shell_id, user_id=fixture.context.user_id)
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_finalization_guardrail(
        shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_finalization_guardrail_by_id(
        first.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_finalization_guardrails(
        user_id=fixture.context.user_id
    )
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1
    for key in FORBIDDEN_FINALIZATION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_finalization_guardrail_handles_zero_candidate_shells_conservatively(tmp_path):
    fixture = zero_candidates_assembly_fixture(tmp_path)
    shell = build_attempt_shell(fixture)
    assert shell is not None

    result = SimuladoFinalizationGuardrailsService(fixture.context.repository).build_guardrail(
        shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    assert result.total_candidates == 0
    assert result.review_ready_candidates == 0
    assert result.finalizable_candidates_count == 0
    assert result.readiness_state in {
        "blocked_by_insufficient_candidates",
        "blocked_by_missing_final_questions",
        "blocked_by_non_final_assembly",
    }
    assert "blocked_by_insufficient_candidates" in blocker_codes
