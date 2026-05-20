import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    build_answer_submission,
    short_text_submission_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def build_boundary_from_fixture(fixture):
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


def test_simulado_answer_key_boundary_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = short_text_submission_fixture(tmp_path, repository=repository)
    result, _, _ = build_boundary_from_fixture(fixture)
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
    assert "score" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def test_simulado_answer_key_boundary_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = short_text_submission_fixture(tmp_path, repository=repository)
    submission = build_answer_submission(fixture)
    assert submission is not None
    correction_service = SimuladoCorrectionShellService(repository)
    correction_shell = correction_service.build_correction_shell(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    assert correction_shell is not None
    service = SimuladoAnswerKeyBoundaryService(repository)

    before_correction_shell = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_execution_shell = repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)
    before_approval = None
    if before_attempt_session is not None:
        before_approval = repository.get_simulado_final_approval_artifact_by_id(
            before_attempt_session.source_final_approval_artifact_id,
            user_id=fixture.context.user_id,
        )

    built = service.build_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    assert built is not None
    loaded = service.get_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_answer_key_boundary_by_id(
        built.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )

    after_correction_shell = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_execution_shell = repository.get_simulado_execution_shell_by_id(
        submission.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)
    after_approval = None
    if after_attempt_session is not None:
        after_approval = repository.get_simulado_final_approval_artifact_by_id(
            after_attempt_session.source_final_approval_artifact_id,
            user_id=fixture.context.user_id,
        )

    assert before_correction_shell is not None
    assert before_submission is not None
    assert before_attempt_session is not None
    assert before_execution_shell is not None
    assert loaded is not None
    assert by_id is not None
    assert after_correction_shell is not None
    assert after_submission is not None
    assert after_attempt_session is not None
    assert after_execution_shell is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    if before_approval is not None and after_approval is not None:
        assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
