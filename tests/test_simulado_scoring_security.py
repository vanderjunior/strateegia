import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_scoring import SimuladoScoringService
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_scoring_results import build_score_result, selected_option_score_fixture


def test_simulado_scoring_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = selected_option_score_fixture(tmp_path, repository=repository)
    result = build_score_result(fixture)
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
    assert "answer_key_value" not in dumped_keys
    assert "gabarito" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "progress_update" not in dumped_keys
    assert "ranking_update" not in dumped_keys
    assert "retention_update" not in dumped_keys
    assert "scheduler_update" not in dumped_keys


def test_simulado_scoring_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = selected_option_score_fixture(tmp_path, repository=repository)
    result = build_score_result(fixture)
    assert result is not None
    correction_result = fixture.correction_result
    assert correction_result is not None
    service = SimuladoScoringService(repository)

    before_correction_result = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = repository.get_simulado_answer_key_boundary_by_id(
        correction_result.source_answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction_shell = repository.get_simulado_correction_shell_by_id(
        correction_result.source_correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_submission = repository.get_simulado_answer_submission_by_id(
        correction_result.source_answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        correction_result.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_score_result(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_score_result_by_id(
        result.score_result_id,
        user_id=fixture.context.user_id,
    )

    after_correction_result = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = repository.get_simulado_answer_key_boundary_by_id(
        correction_result.source_answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction_shell = repository.get_simulado_correction_shell_by_id(
        correction_result.source_correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_submission = repository.get_simulado_answer_submission_by_id(
        correction_result.source_answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        correction_result.source_attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_correction_result is not None
    assert before_boundary is not None
    assert before_correction_shell is not None
    assert before_submission is not None
    assert before_attempt_session is not None
    assert loaded is not None
    assert by_id is not None
    assert after_correction_result is not None
    assert after_boundary is not None
    assert after_correction_shell is not None
    assert after_submission is not None
    assert after_attempt_session is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_correction_result.model_dump(mode="json") == after_correction_result.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
