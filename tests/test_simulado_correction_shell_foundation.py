import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    blank_submission_fixture,
    build_answer_submission,
    empty_submission_fixture,
    selected_option_submission_fixture,
    true_false_submission_fixture,
    unknown_item_fixture,
    unsupported_answer_kind_fixture,
)


FORBIDDEN_CORRECTION_SHELL_KEYS = {
    "correction_result",
    "correction_status",
    "corrected_answer",
    "correct_answer",
    "correct_option",
    "answer_key",
    "gabarito",
    "gabarito_final",
    "score",
    "grade",
    "simulado_result",
    "score_rule",
    "correction_rule",
    "correctness",
    "is_correct",
    "points_awarded",
    "final_question_content",
    "final_answer_key_content",
    "final_explanation_content",
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


def build_correction_shell_from_submission_fixture(fixture):
    submission = build_answer_submission(fixture)
    assert submission is not None
    return SimuladoCorrectionShellService(fixture.context.repository).build_correction_shell(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )


def test_simulado_correction_shell_handles_missing_answer_submission_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoCorrectionShellService(repository)

    assert service.build_correction_shell("simulado-answer-submission:missing", user_id="user-a") is None
    assert repository.list_user_simulado_correction_shells(user_id="user-a") == []


def test_simulado_correction_shell_keeps_selected_option_and_true_false_readiness_structural_only(tmp_path):
    selected = build_correction_shell_from_submission_fixture(selected_option_submission_fixture(tmp_path / "selected"))
    true_false = build_correction_shell_from_submission_fixture(true_false_submission_fixture(tmp_path / "true-false"))

    assert selected is not None
    assert true_false is not None

    for result in (selected, true_false):
        assert result.correction_enabled is False
        assert result.scoring_enabled is False
        assert result.progress_mutation_enabled is False
        assert result.no_correction_result_created is True
        assert result.no_score_created is True
        assert result.no_progress_mutation is True
        assert result.total_submitted_answers == 1
        assert result.correction_ready_answer_count == 0
        assert result.blocked_answer_count == 1
        assert result.readiness_state in {
            "blocked_by_missing_final_answer_keys",
            "blocked_by_missing_correction_rules",
            "blocked_by_missing_score_rules",
            "needs_future_correction_review",
        }

    selected_record = selected.answer_records[0]
    assert selected_record.answer_kind == "selected_option"
    assert selected_record.submission_validation_state == "structurally_valid"
    assert selected_record.correction_readiness_state == "answer_blocked_by_missing_final_answer_key"
    assert selected_record.has_final_answer_key is False
    assert selected_record.has_correction_rule is False
    assert selected_record.can_be_corrected is False
    assert selected_record.can_be_scored is False

    true_false_record = true_false.answer_records[0]
    assert true_false_record.answer_kind == "true_false_value"
    assert true_false_record.submission_validation_state == "structurally_valid"
    assert true_false_record.can_be_corrected is False
    assert true_false_record.can_be_scored is False


def test_simulado_correction_shell_handles_blank_unsupported_unknown_and_empty_submissions_conservatively(tmp_path):
    blank = build_correction_shell_from_submission_fixture(blank_submission_fixture(tmp_path / "blank"))
    unsupported = build_correction_shell_from_submission_fixture(
        unsupported_answer_kind_fixture(tmp_path / "unsupported")
    )
    unknown = build_correction_shell_from_submission_fixture(unknown_item_fixture(tmp_path / "unknown"))
    empty = build_correction_shell_from_submission_fixture(empty_submission_fixture(tmp_path / "empty"))

    assert blank is not None
    assert unsupported is not None
    assert unknown is not None
    assert empty is not None

    blank_record = blank.answer_records[0]
    assert blank_record.is_blank is True
    assert blank_record.correction_readiness_state == "answer_blank_not_corrected"
    assert blank_record.can_be_corrected is False
    assert blank_record.can_be_scored is False

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].correction_readiness_state == "answer_blocked_by_unsupported_answer_kind"

    unknown_codes = {item.code for item in unknown.blockers} | {item.code for item in unknown.validation_findings}
    assert "unknown_session_item" in unknown_codes
    assert unknown.total_submitted_answers == 0
    assert unknown.invalid_answer_count >= 1
    assert unknown.readiness_state in {"blocked_by_invalid_submission", "blocked_by_no_submitted_answers"}

    empty_codes = {item.code for item in empty.blockers}
    assert empty.total_submitted_answers == 0
    assert empty.readiness_state == "blocked_by_no_submitted_answers"
    assert "blocked_by_no_submitted_answers" in empty_codes


def test_simulado_correction_shell_adds_missing_answer_key_rule_and_score_rule_blockers_without_exposing_them(tmp_path):
    result = build_correction_shell_from_submission_fixture(selected_option_submission_fixture(tmp_path))
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    dumped = result.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert "blocked_by_missing_final_answer_keys" in blocker_codes
    assert "blocked_by_missing_correction_rules" in blocker_codes
    assert "blocked_by_missing_score_rules" in blocker_codes
    assert result.readiness_summary.has_final_answer_keys is False
    assert result.readiness_summary.has_correction_rules is False
    assert result.readiness_summary.has_score_rules is False
    for key in FORBIDDEN_CORRECTION_SHELL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_simulado_correction_shell_is_idempotent_and_does_not_mutate_source_artifacts(tmp_path):
    fixture = selected_option_submission_fixture(tmp_path)
    submission = build_answer_submission(fixture)
    assert submission is not None
    service = SimuladoCorrectionShellService(fixture.context.repository)

    before_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_execution_shell = fixture.context.repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_correction_shell(submission.answer_submission_id, user_id=fixture.context.user_id)
    second = service.build_correction_shell(submission.answer_submission_id, user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_correction_shell(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_correction_shell_by_id(
        first.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_correction_shells(user_id=fixture.context.user_id)

    after_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_execution_shell = fixture.context.repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
