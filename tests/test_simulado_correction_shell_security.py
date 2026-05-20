import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    blank_submission_fixture,
    build_answer_submission,
    selected_option_submission_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_simulado_correction_shell_does_not_leak_sensitive_or_final_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    submission_fixture = selected_option_submission_fixture(tmp_path, repository=repository)
    submission = build_answer_submission(submission_fixture)
    assert submission is not None

    result = SimuladoCorrectionShellService(repository).build_correction_shell(
        submission.answer_submission_id,
        user_id=submission_fixture.context.user_id,
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
    assert "correct_answer" not in dumped_keys
    assert "correct_option" not in dumped_keys
    assert "answer_key" not in dumped_keys
    assert "gabarito" not in dumped_keys
    assert "score" not in dumped_keys
    assert "points_awarded" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def test_simulado_correction_shell_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    submission_fixture = blank_submission_fixture(tmp_path, repository=repository)
    submission = build_answer_submission(submission_fixture)
    assert submission is not None
    service = SimuladoCorrectionShellService(repository)

    before_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=submission_fixture.context.user_id,
    )
    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=submission_fixture.context.user_id,
    )
    before_execution_shell = repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=submission_fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=submission_fixture.context.user_id)

    built = service.build_correction_shell(
        submission.answer_submission_id,
        user_id=submission_fixture.context.user_id,
    )
    assert built is not None
    loaded = service.get_correction_shell(
        submission.answer_submission_id,
        user_id=submission_fixture.context.user_id,
    )
    by_id = service.get_correction_shell_by_id(
        built.correction_shell_id,
        user_id=submission_fixture.context.user_id,
    )

    after_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=submission_fixture.context.user_id,
    )
    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=submission_fixture.context.user_id,
    )
    after_execution_shell = repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=submission_fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=submission_fixture.context.user_id)

    assert before_submission is not None
    assert before_attempt_session is not None
    assert before_execution_shell is not None
    assert loaded is not None
    assert by_id is not None
    assert after_submission is not None
    assert after_attempt_session is not None
    assert after_execution_shell is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
