import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_integrated_execution_correction import (
    SimuladoIntegratedExecutionCorrectionService,
)
from tests.fixtures.simulado_integrated_execution_corrections import (
    build_integrated_result,
    complete_chain_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_simulado_integrated_execution_correction_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = complete_chain_fixture(tmp_path, repository=repository)
    result = build_integrated_result(fixture)
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
    assert "study_cycle_update" not in dumped_keys
    assert "curriculum_graph_update" not in dumped_keys


def test_simulado_integrated_execution_correction_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = complete_chain_fixture(tmp_path, repository=repository)
    result = build_integrated_result(fixture)
    assert result is not None
    attempt_session = fixture.attempt_session
    answer_submission = fixture.answer_submission
    correction_shell = fixture.correction_shell
    answer_key_boundary = fixture.answer_key_boundary
    correction_result = fixture.correction_result
    score_result = fixture.score_result
    progress_guardrail = fixture.progress_guardrail
    assert attempt_session is not None
    assert answer_submission is not None
    assert correction_shell is not None
    assert answer_key_boundary is not None
    assert correction_result is not None
    assert score_result is not None
    assert progress_guardrail is not None
    service = SimuladoIntegratedExecutionCorrectionService(repository)

    before_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_submission = repository.get_simulado_answer_submission_by_id(
        answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_shell = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = repository.get_simulado_answer_key_boundary_by_id(
        answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_score = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = repository.get_simulado_progress_guardrail_by_id(
        progress_guardrail.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_integrated_result(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_integrated_result_by_id(
        result.integrated_result_id,
        user_id=fixture.context.user_id,
    )

    after_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_submission = repository.get_simulado_answer_submission_by_id(
        answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_shell = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = repository.get_simulado_answer_key_boundary_by_id(
        answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_score = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_progress_guardrail_by_id(
        progress_guardrail.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_attempt is not None
    assert before_submission is not None
    assert before_shell is not None
    assert before_boundary is not None
    assert before_correction is not None
    assert before_score is not None
    assert before_guardrail is not None
    assert loaded is not None
    assert by_id is not None
    assert after_attempt is not None
    assert after_submission is not None
    assert after_shell is not None
    assert after_boundary is not None
    assert after_correction is not None
    assert after_score is not None
    assert after_guardrail is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_attempt.model_dump(mode="json") == after_attempt.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction.model_dump(mode="json") == after_correction.model_dump(mode="json")
    assert before_score.model_dump(mode="json") == after_score.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
