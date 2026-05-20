import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
from app.services.simulado_correction_result import SimuladoCorrectionResultService
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    blank_submission_fixture,
    build_answer_submission,
    selected_option_submission_fixture,
    true_false_submission_fixture,
    unknown_item_fixture,
    unsupported_answer_kind_fixture,
)


FORBIDDEN_CORRECTION_RESULT_KEYS = {
    "score",
    "grade",
    "simulado_result",
    "points_awarded",
    "weighted_score",
    "percent_correct",
    "final_score",
    "passed",
    "failed",
    "answer_key",
    "answer_key_value",
    "correct_answer",
    "correct_option",
    "gabarito",
    "gabarito_final",
    "final_answer_key_content",
    "final_question_content",
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


def build_correction_result_from_submission_fixture(fixture):
    submission = build_answer_submission(fixture)
    assert submission is not None
    correction_shell = SimuladoCorrectionShellService(fixture.context.repository).build_correction_shell(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    assert correction_shell is not None
    boundary = SimuladoAnswerKeyBoundaryService(fixture.context.repository).build_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    assert boundary is not None
    result = SimuladoCorrectionResultService(fixture.context.repository).build_correction_result(
        boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None
    return result, boundary, correction_shell, submission


def test_simulado_correction_result_handles_missing_answer_key_boundary_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoCorrectionResultService(repository)

    assert service.build_correction_result("simulado-answer-key-boundary:missing", user_id="user-a") is None
    assert repository.list_user_simulado_correction_results(user_id="user-a") == []


def test_simulado_correction_result_keeps_selected_option_and_true_false_non_scoreable_and_private(tmp_path):
    selected, _, _, _ = build_correction_result_from_submission_fixture(
        selected_option_submission_fixture(tmp_path / "selected")
    )
    true_false, _, _, _ = build_correction_result_from_submission_fixture(
        true_false_submission_fixture(tmp_path / "true-false")
    )

    for result in (selected, true_false):
        assert result.scoring_enabled is False
        assert result.progress_mutation_enabled is False
        assert result.answer_key_publicly_exposed is False
        assert result.gabarito_publicly_exposed is False
        assert result.no_score_created is True
        assert result.no_progress_mutation is True
        assert result.no_final_simulado_result_created is True
        assert result.total_answer_records == 1
        assert result.corrected_answer_count == 0
        assert result.blocked_answer_count == 1
        assert result.blank_answer_count == 0
        assert result.unsupported_answer_count == 0
        assert result.summary.correction_result_available is True
        assert result.summary.scoring_available is False
        assert result.summary.progress_mutation_available is False
        assert result.summary.public_answer_key_exposure_allowed is False
        assert result.summary.public_gabarito_exposure_allowed is False
        assert result.summary.correction_completed_for_all_answers is False
        assert result.summary.has_unresolved_blockers is True

    selected_record = selected.answer_records[0]
    assert selected_record.answer_kind == "selected_option"
    assert selected_record.correction_state == "answer_blocked_by_missing_internal_answer_key_reference"
    assert selected_record.correction_input_available is False
    assert selected_record.has_internal_answer_key_reference is False
    assert selected_record.has_public_answer_key_content is False
    assert selected_record.answer_key_publicly_exposed is False
    assert selected_record.student_answer_recorded is True
    assert selected_record.student_answer_blank is False
    assert selected_record.candidate_result is None
    assert selected_record.requires_review is False
    assert selected_record.scoreable is False
    assert selected_record.scoring_enabled is False

    true_false_record = true_false.answer_records[0]
    assert true_false_record.answer_kind == "true_false_value"
    assert true_false_record.correction_state == "answer_blocked_by_missing_internal_answer_key_reference"
    assert true_false_record.candidate_result is None
    assert true_false_record.scoreable is False


def test_simulado_correction_result_handles_blank_unsupported_and_invalid_answers_conservatively(tmp_path):
    blank, _, _, _ = build_correction_result_from_submission_fixture(blank_submission_fixture(tmp_path / "blank"))
    unsupported, _, _, _ = build_correction_result_from_submission_fixture(
        unsupported_answer_kind_fixture(tmp_path / "unsupported")
    )
    invalid, _, _, _ = build_correction_result_from_submission_fixture(unknown_item_fixture(tmp_path / "invalid"))

    blank_record = blank.answer_records[0]
    assert blank_record.correction_state == "answer_blank_not_scored"
    assert blank_record.student_answer_blank is True
    assert blank_record.candidate_result is None
    assert blank_record.scoreable is False
    assert blank.blank_answer_count == 1

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].correction_state == "answer_blocked_by_unsupported_answer_kind"
    assert unsupported.unsupported_answer_count == 1

    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert invalid.total_answer_records == 0
    assert invalid.readiness_state == "blocked_by_invalid_submission"
    assert "unknown_session_item" in invalid_codes or "blocked_by_invalid_submission" in invalid_codes
    assert invalid.needs_review_answer_count >= 0


def test_simulado_correction_result_preserves_missing_key_and_rule_blockers_without_public_exposure(tmp_path):
    result, _, _, _ = build_correction_result_from_submission_fixture(selected_option_submission_fixture(tmp_path))
    dumped = result.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    blocker_codes = {item.code for item in result.blockers}

    assert "blocked_by_missing_internal_answer_key_reference" in blocker_codes
    assert "blocked_by_missing_correction_rule" in blocker_codes
    assert result.readiness_state == "blocked_by_missing_internal_answer_key_reference"
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    for key in FORBIDDEN_CORRECTION_RESULT_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_simulado_correction_result_is_idempotent_and_does_not_mutate_source_artifacts(tmp_path):
    fixture = selected_option_submission_fixture(tmp_path)
    result, boundary, correction_shell, submission = build_correction_result_from_submission_fixture(fixture)
    service = SimuladoCorrectionResultService(fixture.context.repository)

    before_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
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

    first = service.build_correction_result(boundary.answer_key_boundary_id, user_id=fixture.context.user_id)
    second = service.build_correction_result(boundary.answer_key_boundary_id, user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_correction_result(
        boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_correction_result_by_id(
        result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_correction_results(
        user_id=fixture.context.user_id
    )

    after_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
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
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_boundary is not None and after_boundary is not None
    assert before_correction_shell is not None and after_correction_shell is not None
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
