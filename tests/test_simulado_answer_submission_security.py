import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
from tests.fixtures.simulado_attempt_sessions import (
    bounded_summary_fixture,
    build_attempt_session,
    prepared_items_non_submittable_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_simulado_answer_submission_does_not_leak_sensitive_or_final_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = bounded_summary_fixture(tmp_path, repository=repository)
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    item_id = attempt_session.items[0].item_id

    result = SimuladoAnswerSubmissionService(repository).build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "short_text",
                    "submitted_value": "<script>alert('x')</script>",
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
    assert "correct_answer" not in dumped_keys
    assert "correct_option" not in dumped_keys
    assert "gabarito" not in dumped_keys
    assert "score" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "<script>" not in dumped


def test_simulado_answer_submission_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = prepared_items_non_submittable_fixture(tmp_path, repository=repository)
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    item_id = attempt_session.items[0].item_id
    service = SimuladoAnswerSubmissionService(repository)

    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_execution_shell = repository.get_simulado_execution_shell_by_id(
        attempt_session.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    before_approval = repository.get_simulado_final_approval_artifact_by_id(
        attempt_session.source_final_approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    built = service.build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    assert built is not None
    loaded = service.get_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_answer_submission_by_id(
        built.answer_submission_id,
        user_id=fixture.context.user_id,
    )

    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_execution_shell = repository.get_simulado_execution_shell_by_id(
        attempt_session.source_execution_shell_id,
        user_id=fixture.context.user_id,
    )
    after_approval = repository.get_simulado_final_approval_artifact_by_id(
        attempt_session.source_final_approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_attempt_session is not None
    assert before_execution_shell is not None
    assert before_approval is not None
    assert loaded is not None
    assert by_id is not None
    assert after_attempt_session is not None
    assert after_execution_shell is not None
    assert after_approval is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
