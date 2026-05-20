import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_progress_guardrails import SimuladoProgressGuardrailsService
from tests.fixtures.simulado_progress_guardrails import (
    blank_score_fixture,
    blocked_score_fixture,
    build_progress_guardrail,
    empty_score_result_fixture,
    invalid_score_fixture,
    missing_score_policy_fixture,
    missing_score_result_fixture,
    mixed_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    no_scoreable_items_fixture,
    safe_policy_snapshot_fixture,
    score_summary_fixture,
    unsupported_score_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_PROGRESS_GUARDRAIL_KEYS = {
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
    "final_result_applied",
}


def test_simulado_progress_guardrails_handles_missing_score_result_safely(tmp_path):
    fixture = missing_score_result_fixture(tmp_path)

    assert build_progress_guardrail(fixture) is None
    assert fixture.context.repository.list_user_simulado_progress_guardrails(user_id=fixture.context.user_id) == []


def test_simulado_progress_guardrails_blocks_when_score_is_incomplete_or_has_no_scoreable_items(tmp_path):
    empty = build_progress_guardrail(empty_score_result_fixture(tmp_path / "empty"))
    no_scoreable = build_progress_guardrail(no_scoreable_items_fixture(tmp_path / "no-scoreable"))

    for result in (empty, no_scoreable):
        assert result is not None
        assert result.status == "progress_guardrail_blocked"
        assert result.readiness_state == "blocked_by_no_scoreable_items"
        assert result.eligibility.eligible_for_future_progress_mutation is False
        assert result.eligibility.eligible_for_future_ranking_update is False
        assert result.eligibility.eligible_for_future_retention_update is False
        assert result.eligibility.eligible_for_future_scheduler_update is False
        assert result.eligibility.eligible_for_future_study_cycle_update is False
        assert result.eligibility.eligible_for_future_curriculum_graph_update is False
        assert result.eligibility.eligibility_state == "not_eligible"
        assert result.score_completeness.score_complete is False
        assert result.score_completeness.score_blocked is True
        assert result.score_completeness.enough_data_for_progress_update is False
        assert result.progress_mutation_enabled is False
        assert result.ranking_mutation_enabled is False
        assert result.retention_mutation_enabled is False
        assert result.scheduler_mutation_enabled is False
        assert result.study_cycle_mutation_enabled is False
        assert result.curriculum_graph_mutation_enabled is False
        assert result.adaptive_tuning_enabled is False
        assert result.no_progress_mutation is True
        assert result.no_ranking_update is True
        assert result.no_retention_update is True
        assert result.no_scheduler_update is True
        assert result.no_study_cycle_update is True
        assert result.no_curriculum_graph_update is True
        assert result.no_adaptive_tuning_update is True


def test_simulado_progress_guardrails_cover_blocked_blank_unsupported_invalid_and_policy_confirmation(tmp_path):
    blocked = build_progress_guardrail(blocked_score_fixture(tmp_path / "blocked"))
    blank = build_progress_guardrail(blank_score_fixture(tmp_path / "blank"))
    unsupported = build_progress_guardrail(unsupported_score_fixture(tmp_path / "unsupported"))
    invalid = build_progress_guardrail(invalid_score_fixture(tmp_path / "invalid"))
    missing_policy = build_progress_guardrail(missing_score_policy_fixture(tmp_path / "missing-policy"))

    assert blocked is not None
    assert blocked.readiness_state == "blocked_by_no_scoreable_items"
    assert "blocked_by_missing_policy_confirmation" in {item.code for item in blocked.blockers}

    assert blank is not None
    assert blank.score_completeness.blank_items == 1
    assert blank.score_completeness.enough_data_for_progress_update is False

    assert unsupported is not None
    assert unsupported.score_completeness.unsupported_items == 1
    target_blockers = {code for target in unsupported.candidate_progress_targets for code in target.blockers}
    assert "target_blocked_by_missing_mapping" in target_blockers

    assert invalid is not None
    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert "blocked_by_invalid_submission" in invalid_codes or "unknown_session_item" in invalid_codes

    assert missing_policy is not None
    assert missing_policy.eligibility.requires_policy_confirmation is True
    assert "blocked_by_missing_policy_confirmation" in {item.code for item in missing_policy.blockers}


def test_simulado_progress_guardrails_preserve_candidate_targets_and_score_completeness_safely(tmp_path):
    mixed = build_progress_guardrail(mixed_guardrail_fixture(tmp_path / "mixed"))
    summary = build_progress_guardrail(score_summary_fixture(tmp_path / "summary"))
    policy = build_progress_guardrail(safe_policy_snapshot_fixture(tmp_path / "policy"))

    assert mixed is not None
    assert len(mixed.candidate_progress_targets) == mixed.score_completeness.total_items
    assert mixed.candidate_progress_targets
    for target in mixed.candidate_progress_targets:
        assert target.update_applied is False
        assert target.future_update_allowed is False
        assert target.target_available is False
        assert target.mapping_confidence == 0.0
        assert target.proposed_update_kind == "no_update_applied"

    assert summary is not None
    assert summary.score_completeness.raw_score == 0.0
    assert summary.score_completeness.max_score == 0.0
    assert summary.score_completeness.percentage_score is None
    assert summary.score_completeness.score_partial is False
    assert summary.score_completeness.score_complete is False

    assert policy is not None
    assert policy.eligibility.requires_policy_confirmation is True
    assert policy.eligibility.requires_topic_mapping is True
    assert policy.eligibility.requires_complete_score is True


def test_simulado_progress_guardrails_preserve_no_public_answer_key_and_no_runtime_mutation_guarantees(tmp_path):
    result = build_progress_guardrail(no_public_key_gabarito_safety_fixture(tmp_path))
    runtime = build_progress_guardrail(no_runtime_mutation_fixture(tmp_path / "runtime"))
    assert result is not None
    assert runtime is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    assert runtime.progress_mutation_enabled is False
    assert runtime.ranking_mutation_enabled is False
    assert runtime.retention_mutation_enabled is False
    assert runtime.scheduler_mutation_enabled is False
    assert runtime.study_cycle_mutation_enabled is False
    assert runtime.curriculum_graph_mutation_enabled is False
    assert runtime.adaptive_tuning_enabled is False
    for key in FORBIDDEN_PROGRESS_GUARDRAIL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped


def test_simulado_progress_guardrails_is_idempotent_and_does_not_mutate_source_artifacts(tmp_path):
    fixture = no_scoreable_items_fixture(tmp_path)
    result = build_progress_guardrail(fixture)
    assert result is not None

    score_result = fixture.score_result
    assert score_result is not None
    correction_result_id = score_result.source_correction_result_id
    boundary_id = score_result.source_answer_key_boundary_id
    correction_shell_id = score_result.source_correction_shell_id
    submission_id = score_result.source_answer_submission_id
    attempt_session_id = score_result.source_attempt_session_id
    service = SimuladoProgressGuardrailsService(fixture.context.repository)

    before_score_result = fixture.context.repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    before_correction_result = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_progress_guardrail(score_result.score_result_id, user_id=fixture.context.user_id)
    second = service.build_progress_guardrail(score_result.score_result_id, user_id=fixture.context.user_id)

    by_source = fixture.context.repository.get_simulado_progress_guardrail(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_progress_guardrail_by_id(
        result.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_progress_guardrails(user_id=fixture.context.user_id)

    after_score_result = fixture.context.repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    after_correction_result = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_score_result is not None and after_score_result is not None
    assert before_correction_result is not None and after_correction_result is not None
    assert before_boundary is not None and after_boundary is not None
    assert before_correction_shell is not None and after_correction_shell is not None
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_score_result.model_dump(mode="json") == after_score_result.model_dump(mode="json")
    assert before_correction_result.model_dump(mode="json") == after_correction_result.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
