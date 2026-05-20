import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    blank_submission_fixture,
    build_answer_submission,
    selected_option_submission_fixture,
    short_text_submission_fixture,
    true_false_submission_fixture,
    unknown_item_fixture,
    unsupported_answer_kind_fixture,
)


FORBIDDEN_BOUNDARY_KEYS = {
    "correction_result",
    "correction_status",
    "corrected_answer",
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key",
    "final_answer_key_content",
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


def build_answer_key_boundary_from_submission_fixture(fixture):
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
    return boundary, submission, correction_shell


def test_simulado_answer_key_boundary_handles_missing_correction_shell_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoAnswerKeyBoundaryService(repository)

    assert service.build_answer_key_boundary("simulado-correction-shell:missing", user_id="user-a") is None
    assert repository.list_user_simulado_answer_key_boundaries(user_id="user-a") == []


def test_simulado_answer_key_boundary_keeps_selected_option_and_true_false_structural_and_private(tmp_path):
    selected, _, _ = build_answer_key_boundary_from_submission_fixture(
        selected_option_submission_fixture(tmp_path / "selected")
    )
    true_false, _, _ = build_answer_key_boundary_from_submission_fixture(
        true_false_submission_fixture(tmp_path / "true-false")
    )

    for result in (selected, true_false):
        assert result.correction_enabled is False
        assert result.scoring_enabled is False
        assert result.progress_mutation_enabled is False
        assert result.answer_key_publicly_exposed is False
        assert result.gabarito_publicly_exposed is False
        assert result.no_correction_result_created is True
        assert result.no_score_created is True
        assert result.no_progress_mutation is True
        assert result.total_answer_records == 1
        assert result.supported_answer_record_count == 1
        assert result.blocked_answer_record_count == 1
        assert result.internal_answer_key_reference_count == 0
        assert result.correction_input_contract.contract_available is True
        assert result.correction_input_contract.internal_only is True
        assert result.correction_input_contract.public_exposure_allowed is False
        assert result.correction_input_contract.correction_allowed_now is False
        assert result.correction_input_contract.scoring_allowed_now is False
        assert result.correction_input_contract.requires_final_answer_key is True
        assert result.correction_input_contract.requires_correction_rule is True
        assert result.correction_input_contract.requires_score_rule is True
        blocker_codes = {item.code for item in result.blockers}
        assert "blocked_by_missing_internal_answer_key_reference" in blocker_codes
        assert "blocked_by_missing_correction_rule" in blocker_codes
        assert "blocked_by_missing_score_rule" in blocker_codes

    selected_record = selected.answer_records[0]
    assert selected_record.answer_kind == "selected_option"
    assert selected_record.boundary_readiness_state == "answer_blocked_by_missing_internal_answer_key_reference"
    assert selected_record.has_internal_answer_key_reference is False
    assert selected_record.has_public_answer_key_content is False
    assert selected_record.answer_key_publicly_exposed is False
    assert selected_record.future_correction_supported is True
    assert selected_record.correction_allowed_now is False
    assert selected_record.scoring_allowed_now is False

    true_false_record = true_false.answer_records[0]
    assert true_false_record.answer_kind == "true_false_value"
    assert true_false_record.boundary_readiness_state == "answer_blocked_by_missing_internal_answer_key_reference"
    assert true_false_record.future_correction_supported is True
    assert "true_false_value" in true_false.correction_input_contract.supported_answer_kinds


def test_simulado_answer_key_boundary_handles_blank_short_text_unsupported_and_invalid_submission_conservatively(
    tmp_path,
):
    blank, _, _ = build_answer_key_boundary_from_submission_fixture(blank_submission_fixture(tmp_path / "blank"))
    short_text, _, _ = build_answer_key_boundary_from_submission_fixture(
        short_text_submission_fixture(tmp_path / "short-text")
    )
    unsupported, _, _ = build_answer_key_boundary_from_submission_fixture(
        unsupported_answer_kind_fixture(tmp_path / "unsupported")
    )
    invalid, _, _ = build_answer_key_boundary_from_submission_fixture(unknown_item_fixture(tmp_path / "invalid"))

    blank_record = blank.answer_records[0]
    assert blank_record.boundary_readiness_state == "answer_blank_not_corrected"
    assert blank_record.future_correction_supported is False
    assert blank_record.correction_allowed_now is False
    assert blank_record.scoring_allowed_now is False

    short_text_record = short_text.answer_records[0]
    assert short_text_record.answer_kind == "short_text"
    assert short_text_record.boundary_readiness_state == "answer_blocked_by_missing_internal_answer_key_reference"
    assert short_text_record.future_correction_supported is True
    assert "short_text" in short_text.correction_input_contract.supported_answer_kinds

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind"

    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert invalid.total_answer_records == 0
    assert invalid.readiness_state == "blocked_by_no_answer_records"
    assert "unknown_session_item" in invalid_codes or "blocked_by_no_answer_records" in invalid_codes


def test_simulado_answer_key_boundary_redacts_internal_references_and_exposes_no_public_answer_key_content(
    tmp_path,
):
    result, _, _ = build_answer_key_boundary_from_submission_fixture(selected_option_submission_fixture(tmp_path))
    dumped = result.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    if result.internal_answer_key_references:
        for reference in result.internal_answer_key_references:
            assert reference.answer_key_reference_available is False
            assert reference.answer_key_value_stored is False
            assert reference.answer_key_value_publicly_exposed is False
            assert reference.answer_key_value_redacted is True
            assert reference.answer_key_value_hash is None
            assert reference.allowed_values == []

    for key in FORBIDDEN_BOUNDARY_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_simulado_answer_key_boundary_is_idempotent_and_does_not_mutate_source_artifacts(tmp_path):
    fixture = selected_option_submission_fixture(tmp_path)
    submission = build_answer_submission(fixture)
    assert submission is not None
    correction_service = SimuladoCorrectionShellService(fixture.context.repository)
    correction_shell = correction_service.build_correction_shell(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    assert correction_shell is not None
    service = SimuladoAnswerKeyBoundaryService(fixture.context.repository)

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

    first = service.build_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    second = service.build_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        first.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_answer_key_boundaries(
        user_id=fixture.context.user_id
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
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert before_correction_shell is not None and after_correction_shell is not None
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
