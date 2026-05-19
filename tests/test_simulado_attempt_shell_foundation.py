import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_shell import SimuladoAttemptShellService
from tests.fixtures.simulado_question_assemblies import (
    build_assembly,
    idempotency_fixture,
    no_candidates_fixture,
    ready_for_review_candidate_fixture,
)


FORBIDDEN_EXECUTION_KEYS = {
    "real_student_attempt",
    "student_attempt",
    "attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "executable_question",
    "executable_simulado",
    "final_question",
    "final_answer_key",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation",
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


def test_simulado_attempt_shell_handles_missing_assembly_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoAttemptShellService(repository)

    assert service.build_attempt_shell("simulado-question-assembly:missing", user_id="user-a") is None
    assert repository.list_user_simulado_attempt_shells(user_id="user-a") == []


def test_simulado_attempt_shell_disables_execution_even_with_review_ready_candidates(tmp_path):
    fixture = ready_for_review_candidate_fixture(tmp_path)
    assembly = build_assembly(fixture)
    assert assembly is not None

    result = SimuladoAttemptShellService(fixture.context.repository).build_attempt_shell(
        assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    finding_codes = {item.code for item in result.validation_findings}

    assert result.total_candidates == 1
    assert result.review_ready_candidates == 1
    assert result.blocked_candidates == 0
    assert result.needs_review_candidates == 0
    assert result.executable_questions_count == 0
    assert result.execution_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.student_submission_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.requires_human_finalization is True
    assert result.no_student_attempt_created is True
    assert result.no_answer_submission_enabled is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    assert result.readiness_state in {
        "blocked_by_non_final_assembly",
        "blocked_by_review_required",
        "needs_human_finalization",
    }
    assert "blocked_by_non_final_assembly" in blocker_codes
    assert "blocked_by_unfinalized_questions" in blocker_codes
    assert "blocked_by_missing_final_answer_keys" in blocker_codes
    assert "blocked_by_missing_final_explanations" in blocker_codes
    assert "blocked_by_review_required" in blocker_codes or result.readiness_state == "needs_human_finalization"
    assert "execution_disabled" in finding_codes
    assert "correction_disabled" in finding_codes
    assert "scoring_disabled" in finding_codes
    assert "student_submission_disabled" in finding_codes
    assert "progress_mutation_disabled" in finding_codes


def test_simulado_attempt_shell_blocks_no_candidates_and_preserves_no_attempt_no_score_safeguards(tmp_path):
    fixture = no_candidates_fixture(tmp_path)
    assembly = build_assembly(fixture)
    assert assembly is not None

    result = SimuladoAttemptShellService(fixture.context.repository).build_attempt_shell(
        assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    dumped = result.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert result.total_candidates == 0
    assert result.review_ready_candidates == 0
    assert result.blocked_candidates == 0
    assert result.needs_review_candidates == 0
    assert result.executable_questions_count == 0
    assert result.status == "execution_readiness_blocked"
    assert result.readiness_state == "blocked_by_insufficient_question_count"
    assert result.execution_enabled is False
    assert result.student_submission_enabled is False
    assert result.no_student_attempt_created is True
    assert result.no_answer_submission_enabled is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    for key in FORBIDDEN_EXECUTION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_simulado_attempt_shell_persistence_and_idempotency_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    assembly = build_assembly(fixture)
    assert assembly is not None
    service = SimuladoAttemptShellService(fixture.context.repository)

    first = service.build_attempt_shell(assembly.assembly_id, user_id=fixture.context.user_id)
    second = service.build_attempt_shell(assembly.assembly_id, user_id=fixture.context.user_id)
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_attempt_shell(
        assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_attempt_shell_by_id(
        first.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_attempt_shells(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1
