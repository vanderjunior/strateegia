import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_final_approvals import (
    assembly_json_keys,
    block_decision_fixture,
    blocked_guardrail_fixture,
    bounded_audit_reason_fixture,
    build_approval_artifact,
    explicit_approve_for_future_execution_review_fixture,
    final_readiness_flags_false_fixture,
    first_candidate_id,
    idempotency_fixture,
    mark_not_reviewed_decision_fixture,
    mixed_decision_payload,
    mixed_decision_payload_fixture,
    no_decision_payload_fixture,
    no_execution_submission_score_safety_fixture,
    reject_decision_fixture,
    request_revision_decision_fixture,
    single_decision_payload,
    user_scope_fixture,
)


FORBIDDEN_APPROVAL_KEYS = {
    "real_student_attempt",
    "student_attempt",
    "attempt",
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
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "started_at",
    "submitted_at",
    "completed_at",
    "attempt_id",
    "submission_id",
    "result_id",
}


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["user"]["user_id"]


def assert_disabled_flags(artifact) -> None:
    assert artifact.execution_enabled is False
    assert artifact.correction_enabled is False
    assert artifact.scoring_enabled is False
    assert artifact.student_submission_enabled is False
    assert artifact.progress_mutation_enabled is False
    assert artifact.no_student_attempt_created is True
    assert artifact.no_answer_submission_enabled is True
    assert artifact.no_correction_result_created is True
    assert artifact.no_score_created is True


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_final_approval_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = no_decision_payload_fixture(tmp_path / "first")
    second = no_decision_payload_fixture(tmp_path / "second")

    assert (
        first.finalization_guardrail.finalization_guardrail_id
        == second.finalization_guardrail.finalization_guardrail_id
    )
    json.dumps(first.finalization_guardrail.model_dump(mode="json"), ensure_ascii=True)
    artifact = build_approval_artifact(first)
    assert artifact is not None
    json.dumps(artifact.model_dump(mode="json"), ensure_ascii=True)


def test_no_automatic_approval_and_explicit_manual_decisions_remain_non_executable(tmp_path):
    no_decision_fixture = no_decision_payload_fixture(tmp_path / "no-decision")
    no_decision = build_approval_artifact(no_decision_fixture)

    approve_fixture = explicit_approve_for_future_execution_review_fixture(tmp_path / "approve")
    approve = build_approval_artifact(
        approve_fixture,
        decision_payload=single_decision_payload(
            approve_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Approved only for future execution review.",
        ),
    )

    reject_fixture = reject_decision_fixture(tmp_path / "reject")
    reject = build_approval_artifact(
        reject_fixture,
        decision_payload=single_decision_payload(
            reject_fixture,
            decision_type="reject",
            reason="Rejected in deterministic fixture review.",
        ),
    )

    revision_fixture = request_revision_decision_fixture(tmp_path / "revision")
    revision = build_approval_artifact(
        revision_fixture,
        decision_payload=single_decision_payload(
            revision_fixture,
            decision_type="request_revision",
            reason="Needs revision before any future review stage.",
        ),
    )

    blocked_fixture = block_decision_fixture(tmp_path / "blocked")
    blocked = build_approval_artifact(
        blocked_fixture,
        decision_payload=single_decision_payload(
            blocked_fixture,
            decision_type="block",
            reason="Blocked in deterministic fixture review.",
        ),
    )

    not_reviewed_fixture = mark_not_reviewed_decision_fixture(tmp_path / "not-reviewed")
    not_reviewed = build_approval_artifact(
        not_reviewed_fixture,
        decision_payload=single_decision_payload(
            not_reviewed_fixture,
            decision_type="mark_not_reviewed",
            reason="Explicitly marked not reviewed.",
        ),
    )

    assert no_decision is not None
    assert approve is not None
    assert reject is not None
    assert revision is not None
    assert blocked is not None
    assert not_reviewed is not None

    assert no_decision.approval_recorded is False
    assert no_decision.human_approved is False
    assert all(item.approval_state == "candidate_not_reviewed" for item in no_decision.candidate_records)
    assert_disabled_flags(no_decision)

    assert approve.approval_recorded is True
    assert approve.human_approved is True
    assert approve.approved_candidate_count == 1
    assert any(
        item.approval_state == "candidate_approved_for_future_execution_review"
        for item in approve.candidate_records
    )
    assert approve.decisions[0].decision_state == "decision_recorded"
    assert_disabled_flags(approve)

    assert reject.rejected_candidate_count == 1
    assert any(item.approval_state == "candidate_rejected" for item in reject.candidate_records)
    assert reject.decisions[0].decision_state == "decision_recorded"
    assert_disabled_flags(reject)

    assert revision.needs_review_candidate_count == 1
    assert any(item.approval_state == "candidate_needs_revision" for item in revision.candidate_records)
    assert revision.decisions[0].decision_state in {"decision_needs_revision", "decision_recorded"}
    assert_disabled_flags(revision)

    assert blocked.blocked_candidate_count >= 1
    assert any(item.approval_state == "candidate_blocked" for item in blocked.candidate_records)
    assert blocked.decisions[0].decision_state in {"decision_blocked", "decision_recorded"}
    assert_disabled_flags(blocked)

    assert not_reviewed.not_reviewed_candidate_count >= 1
    assert any(item.approval_state == "candidate_not_reviewed" for item in not_reviewed.candidate_records)
    assert_disabled_flags(not_reviewed)


def test_mixed_decisions_blocked_guardrails_and_final_readiness_flags_stay_conservative(tmp_path):
    mixed_fixture = mixed_decision_payload_fixture(tmp_path / "mixed")
    mixed = build_approval_artifact(
        mixed_fixture,
        decision_payload=mixed_decision_payload(mixed_fixture),
    )

    blocked_fixture = blocked_guardrail_fixture(tmp_path / "blocked-guardrail")
    blocked_guardrail = build_approval_artifact(
        blocked_fixture,
        decision_payload=single_decision_payload(
            blocked_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Even explicit approval must remain blocked here.",
        ),
    )

    readiness_fixture = final_readiness_flags_false_fixture(tmp_path / "readiness")
    readiness = build_approval_artifact(
        readiness_fixture,
        decision_payload=single_decision_payload(
            readiness_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Approved for future review only.",
        ),
    )

    assert mixed is not None
    assert blocked_guardrail is not None
    assert readiness is not None

    assert mixed.total_candidates >= 3
    assert mixed.approved_candidate_count >= 1
    assert mixed.rejected_candidate_count >= 0
    assert mixed.needs_review_candidate_count >= 0
    assert mixed.blocked_candidate_count >= 0
    assert mixed.not_reviewed_candidate_count >= 0
    assert len(mixed.decisions) >= 3
    assert len(mixed.audit_trail) == len(mixed.decisions) + 1
    assert_disabled_flags(mixed)

    assert blocked_guardrail.status in {"approval_blocked", "approval_needs_review", "approval_partially_recorded"}
    assert blocked_guardrail.execution_enabled is False
    assert blocked_guardrail.correction_enabled is False
    assert blocked_guardrail.scoring_enabled is False
    assert blocked_guardrail.student_submission_enabled is False

    assert all(item.final_question_ready is False for item in readiness.candidate_records)
    assert all(item.final_answer_key_ready is False for item in readiness.candidate_records)
    assert all(item.final_explanation_ready is False for item in readiness.candidate_records)
    assert_disabled_flags(readiness)


def test_no_execution_submission_score_safety_and_bounded_audit_hold(tmp_path):
    safety_fixture = no_execution_submission_score_safety_fixture(tmp_path / "safety")
    safety = build_approval_artifact(
        safety_fixture,
        decision_payload=single_decision_payload(
            safety_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Safe audit-only approval record.",
        ),
    )

    bounded_fixture = bounded_audit_reason_fixture(tmp_path / "bounded")
    bounded = build_approval_artifact(
        bounded_fixture,
        decision_payload=single_decision_payload(
            bounded_fixture,
            decision_type="approve_for_future_execution_review",
            reason="A" * 600,
        ),
    )

    assert safety is not None
    assert bounded is not None

    dumped = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped)

    assert_disabled_flags(safety)
    for key in FORBIDDEN_APPROVAL_KEYS:
        assert key not in dumped_keys
    assert_no_leakage(dumped_text)

    assert bounded.decisions
    assert bounded.audit_trail
    assert len(bounded.decisions[0].reason or "") <= 240
    assert all(len(item.message) <= 240 for item in bounded.audit_trail)
    assert_no_leakage(json.dumps(bounded.model_dump(mode="json"), ensure_ascii=True))


def test_final_approval_persistence_idempotency_and_different_payload_behavior_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    mark_not_reviewed_payload = single_decision_payload(
        fixture,
        decision_type="mark_not_reviewed",
        reason="Pending additional human review.",
    )
    approve_payload = single_decision_payload(
        fixture,
        decision_type="approve_for_future_execution_review",
        reason="Approved for future execution review only.",
    )

    first = build_approval_artifact(fixture, decision_payload=mark_not_reviewed_payload)
    second = build_approval_artifact(fixture, decision_payload=mark_not_reviewed_payload)
    changed = build_approval_artifact(fixture, decision_payload=approve_payload)

    assert first is not None
    assert second is not None
    assert changed is not None

    by_source = fixture.context.repository.get_simulado_final_approval_artifact(
        fixture.finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_final_approval_artifact_by_id(
        changed.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_final_approval_artifacts(
        user_id=fixture.context.user_id
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert changed.model_dump(mode="json") != first.model_dump(mode="json")
    assert changed.approved_candidate_count == 1
    assert first.approved_candidate_count == 0
    assert by_source is not None
    assert by_id is not None
    assert by_source.model_dump(mode="json") == changed.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == changed.model_dump(mode="json")
    assert len(listed) == 1


def test_final_approval_api_owner_only_read_only_and_user_scope_are_preserved(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture, _ = user_scope_fixture(tmp_path / "scope", repository=repository)
    owner_fixture = no_decision_payload_fixture(
        tmp_path / "owner-api",
        user_id=owner_user_id,
        repository=repository,
    )
    guardrail_id = owner_fixture.finalization_guardrail.finalization_guardrail_id
    candidate_id = first_candidate_id(owner_fixture)
    assert candidate_id is not None

    missing = owner.get(f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval")
    before_list = repository.list_user_simulado_final_approval_artifacts(user_id=owner_user_id)
    payload = {
        "decisions": [
            {
                "source_candidate_id": candidate_id,
                "decision_type": "approve_for_future_execution_review",
                "reason": "Owner-only approval record.",
            }
        ]
    }
    build = owner.post(
        f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval/build",
        json=payload,
    )
    approval_artifact_id = build.json()["approval_artifact_id"]
    after_build_list = repository.list_user_simulado_final_approval_artifacts(user_id=owner_user_id)
    loaded = owner.get(f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval")
    by_id = owner.get(f"/api/simulado-final-approval/{approval_artifact_id}")
    after_get_list = repository.list_user_simulado_final_approval_artifacts(user_id=owner_user_id)
    dumped = json.dumps(by_id.json(), ensure_ascii=True)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert (
        owner.post(
            f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval/build",
            json=payload,
        ).json()
        == build.json()
    )
    assert anonymous.post(
        f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-final-approval/{approval_artifact_id}").status_code == 401
    assert other.post(
        f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-finalization-guardrail/{guardrail_id}/final-approval"
    ).status_code == 404
    assert other.get(f"/api/simulado-final-approval/{approval_artifact_id}").status_code == 404
    assert_no_leakage(dumped)


def test_final_approval_build_and_get_do_not_mutate_source_finalization_guardrail(tmp_path):
    fixture = no_decision_payload_fixture(tmp_path)
    before_guardrail = fixture.context.repository.get_simulado_finalization_guardrail_by_id(
        fixture.finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )

    payload = single_decision_payload(
        fixture,
        decision_type="mark_not_reviewed",
        reason="Read-only mutation safety check.",
    )
    built = build_approval_artifact(fixture, decision_payload=payload)
    assert built is not None
    loaded = fixture.context.service.get_approval_artifact(
        fixture.finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.service.get_approval_artifact_by_id(
        built.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = fixture.context.repository.get_simulado_finalization_guardrail_by_id(
        fixture.finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )

    assert before_guardrail is not None
    assert loaded is not None
    assert by_id is not None
    assert after_guardrail is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
