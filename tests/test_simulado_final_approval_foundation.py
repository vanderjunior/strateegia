import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_approval import SimuladoFinalApprovalService
from tests.fixtures.simulado_finalization_guardrails import (
    build_finalization_guardrail,
    idempotency_fixture,
    non_final_assembly_fixture,
    ready_candidates_not_finalizable_fixture,
)


FORBIDDEN_APPROVAL_KEYS = {
    "approved_simulado",
    "finalized_simulado",
    "approval_record",
    "finalization_record",
    "real_student_attempt",
    "student_attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "execution_session",
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


def test_simulado_final_approval_handles_missing_guardrail_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoFinalApprovalService(repository)

    assert service.build_approval_artifact("simulado-finalization-guardrail:missing", user_id="user-a") is None
    assert repository.list_user_simulado_final_approval_artifacts(user_id="user-a") == []


def test_simulado_final_approval_does_not_auto_approve_without_manual_decisions(tmp_path):
    fixture = ready_candidates_not_finalizable_fixture(tmp_path)
    finalization_guardrail = build_finalization_guardrail(fixture)
    assert finalization_guardrail is not None

    result = SimuladoFinalApprovalService(fixture.context.repository).build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None

    assert result.approval_recorded is False
    assert result.human_approved is False
    assert result.human_review_required is True
    assert result.execution_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.student_submission_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.no_student_attempt_created is True
    assert result.no_answer_submission_enabled is True
    assert result.no_correction_result_created is True
    assert result.no_score_created is True
    assert result.approved_candidate_count == 0
    assert result.not_reviewed_candidate_count > 0
    assert all(item.approval_state == "candidate_not_reviewed" for item in result.candidate_records)
    assert result.audit_trail


def test_simulado_final_approval_records_conservative_manual_decisions_without_enabling_execution(tmp_path):
    fixture = ready_candidates_not_finalizable_fixture(tmp_path)
    finalization_guardrail = build_finalization_guardrail(fixture)
    assert finalization_guardrail is not None
    candidate_id = finalization_guardrail.candidate_summaries[0].source_question_candidate_id
    assert candidate_id is not None

    result = SimuladoFinalApprovalService(fixture.context.repository).build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {
                    "source_candidate_id": candidate_id,
                    "decision_type": "approve_for_future_execution_review",
                    "reason": "Manual review completed for future execution review only.",
                }
            ]
        },
    )
    assert result is not None

    decision = result.decisions[0]
    record = next(item for item in result.candidate_records if item.source_candidate_id == candidate_id)

    assert result.approval_recorded is True
    assert result.human_approved is True
    assert result.human_reviewer_id == fixture.context.user_id
    assert result.execution_enabled is False
    assert result.correction_enabled is False
    assert result.scoring_enabled is False
    assert result.student_submission_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.approved_candidate_count == 1
    assert decision.decision_type == "approve_for_future_execution_review"
    assert decision.decision_state == "decision_recorded"
    assert record.approval_state == "candidate_approved_for_future_execution_review"
    assert record.final_question_ready is False
    assert record.final_answer_key_ready is False
    assert record.final_explanation_ready is False
    assert result.audit_trail


def test_simulado_final_approval_records_rejected_revision_and_blocked_decisions(tmp_path):
    fixture = ready_candidates_not_finalizable_fixture(tmp_path)
    finalization_guardrail = build_finalization_guardrail(fixture)
    assert finalization_guardrail is not None
    candidate_id = finalization_guardrail.candidate_summaries[0].source_question_candidate_id
    assert candidate_id is not None

    service = SimuladoFinalApprovalService(fixture.context.repository)

    rejected = service.build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {"source_candidate_id": candidate_id, "decision_type": "reject", "reason": "Rejected in manual review."}
            ]
        },
    )
    assert rejected is not None
    assert rejected.rejected_candidate_count == 1
    assert any(item.approval_state == "candidate_rejected" for item in rejected.candidate_records)

    revision = service.build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {
                    "source_candidate_id": candidate_id,
                    "decision_type": "request_revision",
                    "reason": "Needs revision before any future review.",
                }
            ]
        },
    )
    assert revision is not None
    assert revision.needs_review_candidate_count == 1
    assert any(item.approval_state == "candidate_needs_revision" for item in revision.candidate_records)

    blocked = service.build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload={
            "decisions": [
                {"source_candidate_id": candidate_id, "decision_type": "block", "reason": "Blocked by manual review."}
            ]
        },
    )
    assert blocked is not None
    assert blocked.blocked_candidate_count >= 1
    assert any(item.approval_state == "candidate_blocked" for item in blocked.candidate_records)
    assert blocked.execution_enabled is False


def test_simulado_final_approval_preserves_no_execution_no_final_content_and_idempotency(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    finalization_guardrail = build_finalization_guardrail(fixture)
    assert finalization_guardrail is not None
    service = SimuladoFinalApprovalService(fixture.context.repository)

    decision_payload = {
        "decisions": [
            {
                "source_candidate_id": finalization_guardrail.candidate_summaries[0].source_question_candidate_id,
                "decision_type": "mark_not_reviewed",
                "reason": "Pending additional human review.",
            }
        ]
    }
    first = service.build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload=decision_payload,
    )
    second = service.build_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload=decision_payload,
    )
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_final_approval_artifact(
        finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_final_approval_artifact_by_id(
        first.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_final_approval_artifacts(
        user_id=fixture.context.user_id
    )
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1
    for key in FORBIDDEN_APPROVAL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text

