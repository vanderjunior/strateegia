import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_integrated_execution_correction import (
    SimuladoIntegratedExecutionCorrectionService,
)
from tests.fixtures.simulado_integrated_execution_corrections import (
    build_integrated_result,
    complete_chain_fixture,
    idempotency_fixture,
    incomplete_correction_fixture,
    incomplete_score_fixture,
    missing_answer_key_boundary_fixture,
    missing_answer_submission_fixture,
    missing_attempt_session_fixture,
    missing_correction_result_fixture,
    missing_correction_shell_fixture,
    missing_progress_guardrail_fixture,
    missing_score_result_fixture,
    mixed_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    no_scoreable_items_fixture,
    progress_guardrail_not_eligible_fixture,
    runtime_mutation_disabled_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_INTEGRATED_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "progress_applied",
    "ranking_applied",
    "retention_applied",
    "scheduler_applied",
    "study_cycle_applied",
    "curriculum_graph_applied",
    "adaptive_tuning_applied_runtime",
    "final_result_applied",
}


def test_simulado_integrated_execution_correction_handles_missing_attempt_session_safely(tmp_path):
    fixture = missing_attempt_session_fixture(tmp_path)

    assert build_integrated_result(fixture) is None
    assert fixture.context.repository.list_user_simulado_integrated_results(user_id=fixture.context.user_id) == []


def test_simulado_integrated_execution_correction_blocks_when_chain_artifacts_are_missing(tmp_path):
    missing_submission = build_integrated_result(missing_answer_submission_fixture(tmp_path / "submission"))
    missing_shell = build_integrated_result(missing_correction_shell_fixture(tmp_path / "shell"))
    missing_boundary = build_integrated_result(missing_answer_key_boundary_fixture(tmp_path / "boundary"))
    missing_correction = build_integrated_result(missing_correction_result_fixture(tmp_path / "correction"))
    missing_score = build_integrated_result(missing_score_result_fixture(tmp_path / "score"))
    missing_guardrail = build_integrated_result(missing_progress_guardrail_fixture(tmp_path / "guardrail"))

    assert missing_submission is not None
    assert missing_submission.chain_summary.answer_submission_available is False
    assert missing_submission.chain_summary.chain_complete is False
    assert "blocked_by_missing_answer_submission" in {item.code for item in missing_submission.blockers}

    assert missing_shell is not None
    assert missing_shell.chain_summary.correction_shell_available is False
    assert "blocked_by_missing_correction_shell" in {item.code for item in missing_shell.blockers}

    assert missing_boundary is not None
    assert missing_boundary.chain_summary.answer_key_boundary_available is False
    assert "blocked_by_missing_answer_key_boundary" in {item.code for item in missing_boundary.blockers}

    assert missing_correction is not None
    assert missing_correction.chain_summary.correction_result_available is False
    assert "blocked_by_missing_correction_result" in {item.code for item in missing_correction.blockers}

    assert missing_score is not None
    assert missing_score.chain_summary.score_result_available is False
    assert "blocked_by_missing_score_result" in {item.code for item in missing_score.blockers}

    assert missing_guardrail is not None
    assert missing_guardrail.chain_summary.progress_guardrail_available is False
    assert "blocked_by_missing_progress_guardrail" in {item.code for item in missing_guardrail.blockers}


def test_simulado_integrated_execution_correction_creates_complete_chain_summary_but_remains_read_only(tmp_path):
    result = build_integrated_result(complete_chain_fixture(tmp_path))
    assert result is not None

    assert result.chain_summary.attempt_session_available is True
    assert result.chain_summary.answer_submission_available is True
    assert result.chain_summary.correction_shell_available is True
    assert result.chain_summary.answer_key_boundary_available is True
    assert result.chain_summary.correction_result_available is True
    assert result.chain_summary.score_result_available is True
    assert result.chain_summary.progress_guardrail_available is True
    assert result.chain_summary.chain_complete is True
    assert result.progress_mutation_applied is False
    assert result.ranking_update_applied is False
    assert result.retention_update_applied is False
    assert result.scheduler_update_applied is False
    assert result.study_cycle_update_applied is False
    assert result.curriculum_graph_update_applied is False
    assert result.adaptive_tuning_applied is False


def test_simulado_integrated_execution_correction_carries_incomplete_correction_score_and_guardrail_blockers(tmp_path):
    correction = build_integrated_result(incomplete_correction_fixture(tmp_path / "correction"))
    score = build_integrated_result(incomplete_score_fixture(tmp_path / "score"))
    not_eligible = build_integrated_result(progress_guardrail_not_eligible_fixture(tmp_path / "guardrail"))
    no_scoreable = build_integrated_result(no_scoreable_items_fixture(tmp_path / "no-scoreable"))

    assert correction is not None
    assert correction.correction_summary.correction_complete is False
    assert "blocked_by_incomplete_correction" in {item.code for item in correction.blockers}

    assert score is not None
    assert score.score_summary.score_complete is False
    assert "blocked_by_incomplete_score" in {item.code for item in score.blockers}

    assert not_eligible is not None
    assert not_eligible.progress_guardrail_summary.mutation_blocked is True
    assert "blocked_by_progress_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}

    assert no_scoreable is not None
    assert no_scoreable.score_summary.scoreable_item_count == 0
    assert no_scoreable.progress_guardrail_summary.eligible_for_future_progress_mutation is False


def test_simulado_integrated_execution_correction_preserves_candidate_counts_and_runtime_flags(tmp_path):
    mixed = build_integrated_result(mixed_guardrail_fixture(tmp_path / "mixed"))
    runtime = build_integrated_result(runtime_mutation_disabled_fixture(tmp_path / "runtime"))
    assert mixed is not None
    assert runtime is not None

    assert mixed.execution_summary.answer_submission_present is True
    assert mixed.correction_summary.total_answer_records >= 0
    assert mixed.score_summary.scoreable_item_count >= 0
    assert mixed.progress_guardrail_summary.candidate_target_count >= 0

    assert runtime.progress_mutation_enabled is False
    assert runtime.ranking_mutation_enabled is False
    assert runtime.retention_mutation_enabled is False
    assert runtime.scheduler_mutation_enabled is False
    assert runtime.study_cycle_mutation_enabled is False
    assert runtime.curriculum_graph_mutation_enabled is False
    assert runtime.adaptive_tuning_enabled is False
    assert runtime.no_progress_mutation is True
    assert runtime.no_ranking_update is True
    assert runtime.no_retention_update is True
    assert runtime.no_scheduler_update is True
    assert runtime.no_study_cycle_update is True
    assert runtime.no_curriculum_graph_update is True
    assert runtime.no_adaptive_tuning_update is True
    assert "blocked_by_runtime_mutation_disabled" in {item.code for item in runtime.blockers}


def test_simulado_integrated_execution_correction_preserves_no_public_answer_key_and_bounded_payload(tmp_path):
    result = build_integrated_result(no_public_key_gabarito_safety_fixture(tmp_path))
    assert result is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    for key in FORBIDDEN_INTEGRATED_KEYS:
        assert key not in dumped_keys


def test_simulado_integrated_execution_correction_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_integrated_result(fixture)
    assert result is not None

    service = SimuladoIntegratedExecutionCorrectionService(fixture.context.repository)
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

    before_attempt = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_score = fixture.context.repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = fixture.context.repository.get_simulado_progress_guardrail_by_id(
        progress_guardrail.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_integrated_result(attempt_session.attempt_session_id, user_id=fixture.context.user_id)
    second = service.build_integrated_result(attempt_session.attempt_session_id, user_id=fixture.context.user_id)
    by_source = fixture.context.repository.get_simulado_integrated_result(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_integrated_result_by_id(
        result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_integrated_results(user_id=fixture.context.user_id)

    after_attempt = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_score = fixture.context.repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = fixture.context.repository.get_simulado_progress_guardrail_by_id(
        progress_guardrail.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert result.model_dump(mode="json") == by_source.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_attempt is not None and after_attempt is not None
    assert before_submission is not None and after_submission is not None
    assert before_shell is not None and after_shell is not None
    assert before_boundary is not None and after_boundary is not None
    assert before_correction is not None and after_correction is not None
    assert before_score is not None and after_score is not None
    assert before_guardrail is not None and after_guardrail is not None
    assert before_attempt.model_dump(mode="json") == after_attempt.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction.model_dump(mode="json") == after_correction.model_dump(mode="json")
    assert before_score.model_dump(mode="json") == after_score.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_simulado_integrated_execution_correction_fixture_runtime_safety_baseline(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    result = build_integrated_result(no_runtime_mutation_fixture(tmp_path, repository=repository))
    assert result is not None
    assert result.metadata.get("llm_used") is False
    assert result.metadata.get("external_calls_used") is False
