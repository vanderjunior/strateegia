import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_execution_shell import SimuladoExecutionShellService
from tests.fixtures.simulado_final_approvals import (
    blocked_guardrail_fixture,
    build_approval_artifact,
    explicit_approve_for_future_execution_review_fixture,
    no_decision_payload_fixture,
    single_decision_payload,
)


FORBIDDEN_EXECUTION_SHELL_KEYS = {
    "real_student_attempt",
    "student_attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "active_execution_session",
    "executable_question",
    "executable_simulado",
    "final_question_content",
    "final_answer_key_content",
    "final_explanation_content",
    "correction_rule",
    "score_rule",
    "gabarito_final",
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


def build_execution_shell_from_fixture(fixture, *, decision_payload=None):
    approval_artifact = build_approval_artifact(fixture, decision_payload=decision_payload)
    assert approval_artifact is not None
    return SimuladoExecutionShellService(fixture.context.repository).build_execution_shell(
        approval_artifact.approval_artifact_id,
        user_id=fixture.context.user_id,
    )


def test_simulado_execution_shell_handles_missing_final_approval_artifact_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoExecutionShellService(repository)

    assert service.build_execution_shell("simulado-final-approval:missing", user_id="user-a") is None
    assert repository.list_user_simulado_execution_shells(user_id="user-a") == []


def test_simulado_execution_shell_blocks_when_no_approved_candidates_exist(tmp_path):
    fixture = no_decision_payload_fixture(tmp_path)
    result = build_execution_shell_from_fixture(fixture)
    assert result is not None

    assert result.status in {"execution_shell_blocked", "execution_shell_needs_review"}
    assert result.approved_candidate_count == 0
    assert result.executable_candidate_count == 0
    assert result.execution_shell_active is False
    assert result.execution_started is False
    assert result.attempt_created is False
    assert result.readiness_state in {
        "blocked_by_no_approved_candidates",
        "needs_future_activation_review",
    }


def test_simulado_execution_shell_keeps_approved_candidates_non_executable(tmp_path):
    fixture = explicit_approve_for_future_execution_review_fixture(tmp_path)
    decision_payload = single_decision_payload(
        fixture,
        decision_type="approve_for_future_execution_review",
        reason="Approved for future execution review only.",
    )
    result = build_execution_shell_from_fixture(fixture, decision_payload=decision_payload)
    assert result is not None

    assert result.approved_candidate_count > 0
    assert result.executable_candidate_count == 0
    assert result.execution_shell_active is False
    assert result.student_submission_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    approved_record = next(
        item for item in result.candidate_records if item.approval_state == "candidate_approved_for_future_execution_review"
    )
    assert approved_record.execution_readiness_state == "candidate_ready_for_future_activation_review"
    assert approved_record.can_be_presented_to_student is False
    assert approved_record.can_accept_answer is False
    assert approved_record.can_be_corrected is False
    assert approved_record.can_be_scored is False


def test_simulado_execution_shell_adds_missing_final_content_blockers_and_false_readiness_flags(tmp_path):
    fixture = explicit_approve_for_future_execution_review_fixture(tmp_path)
    decision_payload = single_decision_payload(
        fixture,
        decision_type="approve_for_future_execution_review",
        reason="Approved for future execution review only.",
    )
    result = build_execution_shell_from_fixture(fixture, decision_payload=decision_payload)
    assert result is not None

    blocker_codes = {item.code for item in result.blockers}
    assert "blocked_by_missing_final_questions" in blocker_codes
    assert "blocked_by_missing_final_answer_keys" in blocker_codes
    assert "blocked_by_missing_final_explanations" in blocker_codes
    assert all(item.has_final_question is False for item in result.candidate_records)
    assert all(item.has_final_answer_key is False for item in result.candidate_records)
    assert all(item.has_final_explanation is False for item in result.candidate_records)


def test_simulado_execution_shell_assigns_stable_candidate_ordering_metadata(tmp_path):
    fixture = explicit_approve_for_future_execution_review_fixture(tmp_path)
    decision_payload = single_decision_payload(
        fixture,
        decision_type="approve_for_future_execution_review",
        reason="Approved for future execution review only.",
    )
    service = SimuladoExecutionShellService(fixture.context.repository)
    approval_artifact = build_approval_artifact(fixture, decision_payload=decision_payload)
    assert approval_artifact is not None

    first = service.build_execution_shell(
        approval_artifact.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    second = service.build_execution_shell(
        approval_artifact.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    assert first is not None
    assert second is not None

    first_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in first.candidate_records]
    second_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in second.candidate_records]

    assert first_pairs == second_pairs
    assert first_pairs == sorted(first_pairs, key=lambda item: (item[1], item[2], item[0] or ""))
    assert [item[1] for item in first_pairs] == list(range(len(first_pairs)))
    assert [item[2] for item in first_pairs] == list(range(1, len(first_pairs) + 1))
    assert first.operational_summary.candidate_ordering_strategy


def test_simulado_execution_shell_preserves_disabled_flags_and_no_execution_leakage(tmp_path):
    fixture = blocked_guardrail_fixture(tmp_path)
    result = build_execution_shell_from_fixture(fixture)
    assert result is not None

    dumped = result.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert result.execution_shell_active is False
    assert result.execution_started is False
    assert result.attempt_created is False
    assert result.student_submission_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.no_student_attempt_created is True
    assert result.no_answer_submission_created is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    for key in FORBIDDEN_EXECUTION_SHELL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text

