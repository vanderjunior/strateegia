import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_session import SimuladoAttemptSessionService
from tests.fixtures.simulado_execution_shells import (
    approved_candidates_not_executable_fixture,
    build_execution_shell,
    no_approved_candidates_fixture,
)


FORBIDDEN_ATTEMPT_SESSION_KEYS = {
    "answer_submission",
    "submitted_answers",
    "selected_option",
    "typed_answer",
    "submission_id",
    "correction_result",
    "correct_answer",
    "gabarito",
    "score",
    "grade",
    "simulado_result",
    "final_question_content",
    "final_answer_key_content",
    "final_explanation_content",
    "correction_rule",
    "score_rule",
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


def build_attempt_session_from_fixture(fixture):
    execution_shell = build_execution_shell(fixture)
    assert execution_shell is not None
    return SimuladoAttemptSessionService(fixture.context.repository).build_attempt_session(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )


def test_simulado_attempt_session_handles_missing_execution_shell_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoAttemptSessionService(repository)

    assert service.build_attempt_session("simulado-execution-shell:missing", user_id="user-a") is None
    assert repository.list_user_simulado_attempt_sessions(user_id="user-a") == []


def test_simulado_attempt_session_stays_prepared_non_submittable_and_inactive(tmp_path):
    fixture = approved_candidates_not_executable_fixture(tmp_path)
    result = build_attempt_session_from_fixture(fixture)
    assert result is not None

    assert result.status in {"attempt_session_blocked", "attempt_session_needs_review", "attempt_session_prepared"}
    assert result.session_prepared is True
    assert result.session_active is False
    assert result.session_submitted is False
    assert result.session_completed is False
    assert result.answer_submission_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.no_answer_submission_created is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    assert result.no_progress_mutation is True
    assert result.readiness_state in {
        "blocked_by_no_executable_items",
        "needs_future_submission_foundation",
        "prepared_non_submittable",
    }


def test_simulado_attempt_session_preserves_non_displayable_non_submittable_items_and_timing_placeholders(tmp_path):
    fixture = approved_candidates_not_executable_fixture(tmp_path)
    result = build_attempt_session_from_fixture(fixture)
    assert result is not None

    assert result.total_items == len(result.items)
    assert result.prepared_item_count == len(result.items)
    assert result.blocked_item_count >= 1
    assert all(item.can_be_displayed is False for item in result.items)
    assert all(item.can_accept_answer is False for item in result.items)
    assert all(item.has_submitted_answer is False for item in result.items)
    assert all(item.can_be_corrected is False for item in result.items)
    assert all(item.can_be_scored is False for item in result.items)
    assert result.timing_plan.timing_available is False
    assert result.timing_plan.timer_active is False
    assert result.timing_plan.timer_started_at is None
    assert result.timing_plan.timer_completed_at is None


def test_simulado_attempt_session_blocks_when_execution_shell_has_no_executable_candidates(tmp_path):
    fixture = no_approved_candidates_fixture(tmp_path)
    result = build_attempt_session_from_fixture(fixture)
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    assert result.status in {"attempt_session_blocked", "attempt_session_needs_review"}
    assert result.readiness_state in {"blocked_by_no_executable_items", "needs_future_submission_foundation"}
    assert "blocked_by_no_executable_items" in blocker_codes
    assert "blocked_by_submission_disabled" in blocker_codes
    assert "blocked_by_correction_disabled" in blocker_codes
    assert "blocked_by_scoring_disabled" in blocker_codes


def test_simulado_attempt_session_preserves_no_submission_no_correction_no_score_leakage_and_idempotency(tmp_path):
    fixture = approved_candidates_not_executable_fixture(tmp_path)
    execution_shell = build_execution_shell(fixture)
    assert execution_shell is not None
    service = SimuladoAttemptSessionService(fixture.context.repository)

    first = service.build_attempt_session(execution_shell.execution_shell_id, user_id=fixture.context.user_id)
    second = service.build_attempt_session(execution_shell.execution_shell_id, user_id=fixture.context.user_id)
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_attempt_session(
        execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_attempt_session_by_id(
        first.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_attempt_sessions(user_id=fixture.context.user_id)
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1
    for key in FORBIDDEN_ATTEMPT_SESSION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
