import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_explicit_mutation_commit import (
    SimuladoExplicitRuntimeMutationCommitService,
)
from tests.fixtures.simulado_explicit_mutation_commits import (
    api_readonly_fixture,
    approve_all_payload,
    approve_payload,
    approve_with_all_confirmations_fixture,
    approve_without_confirmations_fixture,
    block_decision_fixture,
    block_payload,
    build_explicit_mutation_commit,
    confirmation_summary_shape_fixture,
    delta_approvals_shape_fixture,
    deny_decision_fixture,
    deny_payload,
    different_payload_behavior_fixture,
    mark_not_reviewed_decision_fixture,
    mark_not_reviewed_payload,
    missing_controlled_commit_shell_fixture,
    mixed_decision_fixture,
    no_decision_payload_fixture,
    no_mutation_commit_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    payload_idempotency_fixture,
    request_revision_decision_fixture,
    request_revision_payload,
    surface_approvals_shape_fixture,
    unsafe_source_fixture,
    user_scope_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_EXPLICIT_COMMIT_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "mutation_commit_event",
    "runtime_application_event",
    "final_pedagogical_update_event",
}

ALLOWED_TARGET_TYPES = {
    "user_progress",
    "topic_progress",
    "subtopic_progress",
    "microtopic_progress",
    "subject_progress",
    "unknown",
}

ALLOWED_DELTA_KINDS = {
    "mastery_delta",
    "completion_delta",
    "accuracy_delta",
    "review_signal_delta",
    "confidence_delta",
    "unknown",
}

ALLOWED_SURFACE_TYPES = {
    "progress",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
    "unknown",
}

ALLOWED_UPDATE_KINDS = {
    "progress_delta",
    "ranking_signal",
    "retention_signal",
    "scheduler_signal",
    "study_cycle_signal",
    "curriculum_graph_signal",
    "adaptive_tuning_signal",
    "unknown",
}


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.approved_for_commit_now is False
    assert result.commit_request_accepted is False
    assert result.commit_ready_for_execution is False
    assert result.mutation_valid_for_commit is False
    assert result.mutation_commit_ready is False
    assert result.mutation_committed is False
    assert result.no_mutation_commit is True
    assert result.no_mutation_commit_event_created is True
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False
    assert result.progress_mutation_enabled is False
    assert result.progress_mutation_applied is False
    assert result.ranking_update_enabled is False
    assert result.ranking_update_applied is False
    assert result.retention_update_enabled is False
    assert result.retention_update_applied is False
    assert result.scheduler_update_enabled is False
    assert result.scheduler_update_applied is False
    assert result.study_cycle_update_enabled is False
    assert result.study_cycle_update_applied is False
    assert result.curriculum_graph_update_enabled is False
    assert result.curriculum_graph_update_applied is False
    assert result.adaptive_tuning_enabled is False
    assert result.adaptive_tuning_applied is False
    assert result.no_runtime_application is True
    assert result.no_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.no_final_pedagogical_update_event is True


def _assert_no_leakage(result) -> None:
    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_EXPLICIT_COMMIT_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _register_and_login(client: TestClient, username: str) -> str:
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


def _prepare_commit_shell(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    commit_shell = fixture.controlled_commit_shell
    assert commit_shell is not None
    return commit_shell


def test_explicit_mutation_commit_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_controlled_commit_shell_fixture(tmp_path / "missing")
    no_payload = no_decision_payload_fixture(tmp_path / "no-payload")
    approve_all = approve_with_all_confirmations_fixture(tmp_path / "approve-all")
    mixed = mixed_decision_fixture(tmp_path / "mixed")

    assert missing.missing_commit_shell_id == "simulado-mutation-commit-shell:missing"
    assert no_payload.controlled_commit_shell is not None
    assert approve_all.controlled_commit_shell is not None
    assert mixed.controlled_commit_shell is not None
    assert json.dumps(approve_payload(), ensure_ascii=True)
    assert json.dumps(approve_all_payload(), ensure_ascii=True)


def test_explicit_mutation_commit_stabilization_covers_missing_and_decision_payload_scenarios(tmp_path):
    missing = build_explicit_mutation_commit(missing_controlled_commit_shell_fixture(tmp_path / "missing"))
    no_payload = build_explicit_mutation_commit(no_decision_payload_fixture(tmp_path / "no-payload"))
    approve_missing = build_explicit_mutation_commit(
        approve_without_confirmations_fixture(tmp_path / "approve-missing"),
        decision_payload=approve_payload(),
    )
    approve_all = build_explicit_mutation_commit(
        approve_with_all_confirmations_fixture(tmp_path / "approve-all"),
        decision_payload=approve_all_payload(),
    )
    denied = build_explicit_mutation_commit(
        deny_decision_fixture(tmp_path / "deny"),
        decision_payload=deny_payload(),
    )
    revision = build_explicit_mutation_commit(
        request_revision_decision_fixture(tmp_path / "revision"),
        decision_payload=request_revision_payload(),
    )
    blocked = build_explicit_mutation_commit(
        block_decision_fixture(tmp_path / "block"),
        decision_payload=block_payload(),
    )
    not_reviewed = build_explicit_mutation_commit(
        mark_not_reviewed_decision_fixture(tmp_path / "not-reviewed"),
        decision_payload=mark_not_reviewed_payload(),
    )

    assert missing is None

    assert no_payload is not None
    assert no_payload.explicit_commit_recorded is False
    assert no_payload.explicit_commit_approved is False
    assert no_payload.decision_status in {"explicit_commit_not_reviewed", "explicit_commit_blocked"}
    _assert_no_runtime_mutation_flags(no_payload)

    assert approve_missing is not None
    assert approve_missing.explicit_commit_recorded is True
    assert approve_missing.explicit_commit_approved is False
    assert {
        "blocked_by_commit_policy_not_confirmed",
        "blocked_by_explicit_commit_approval_not_confirmed",
        "blocked_by_audit_not_confirmed",
        "blocked_by_rollback_not_verified",
        "blocked_by_human_review_not_confirmed",
    }.issubset({item.code for item in approve_missing.blockers})
    _assert_no_runtime_mutation_flags(approve_missing)

    assert approve_all is not None
    assert approve_all.explicit_commit_recorded is True
    assert approve_all.explicit_commit_approved is True
    assert approve_all.approved_for_future_mutation_commit_review is True
    assert approve_all.approved_for_commit_now is False
    assert approve_all.decision_status == "explicit_commit_approved_for_future_mutation_commit_review"
    assert approve_all.commit_ready_for_execution is False
    assert approve_all.mutation_committed is False
    _assert_no_runtime_mutation_flags(approve_all)

    assert denied is not None
    assert denied.decision_summary.denied is True
    assert denied.explicit_commit_approved is False
    _assert_no_runtime_mutation_flags(denied)

    assert revision is not None
    assert revision.decision_summary.revision_requested is True
    assert revision.explicit_commit_approved is False
    _assert_no_runtime_mutation_flags(revision)

    assert blocked is not None
    assert blocked.decision_summary.blocked is True
    assert blocked.explicit_commit_approved is False
    _assert_no_runtime_mutation_flags(blocked)

    assert not_reviewed is not None
    assert not_reviewed.explicit_commit_recorded is True
    assert not_reviewed.explicit_commit_approved is False
    assert not_reviewed.decision_status == "explicit_commit_not_reviewed"
    _assert_no_runtime_mutation_flags(not_reviewed)


def test_explicit_mutation_commit_stabilization_confirms_shapes_and_audit(tmp_path):
    default_result = build_explicit_mutation_commit(
        confirmation_summary_shape_fixture(tmp_path / "default"),
        decision_payload=approve_payload(),
    )
    approved_result = build_explicit_mutation_commit(
        delta_approvals_shape_fixture(tmp_path / "approved"),
        decision_payload=approve_all_payload(),
    )
    surface_result = build_explicit_mutation_commit(
        surface_approvals_shape_fixture(tmp_path / "surface"),
        decision_payload=approve_all_payload(),
    )

    assert default_result is not None
    assert default_result.confirmation_summary.commit_policy_confirmed is False
    assert default_result.confirmation_summary.explicit_commit_approval_confirmed is False
    assert default_result.confirmation_summary.audit_confirmed is False
    assert default_result.confirmation_summary.rollback_verified_confirmed is False
    assert default_result.confirmation_summary.human_review_confirmed is False
    assert default_result.confirmation_summary.public_answer_key_absence_confirmed is False
    assert default_result.confirmation_summary.all_confirmations_satisfied is False
    assert "confirmations_missing" in {item.event_type for item in default_result.audit_trail}

    assert approved_result is not None
    assert approved_result.confirmation_summary.all_confirmations_satisfied is True
    for approval in approved_result.delta_approvals:
        assert approval.target_type in ALLOWED_TARGET_TYPES
        assert approval.delta_kind in ALLOWED_DELTA_KINDS
        assert approval.committed is False
        assert approval.approved_for_commit_now is False
        assert approval.approved_for_future_mutation_commit_review is True
        assert approval.approval_state == "delta_approved_for_future_mutation_commit_review"
    audit_events = {item.event_type for item in approved_result.audit_trail}
    assert "explicit_commit_created" in audit_events
    assert "explicit_commit_decision_recorded" in audit_events
    assert "explicit_commit_approved_for_future_mutation_commit_review" in audit_events
    assert "no_mutation_commit" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert surface_result is not None
    for approval in surface_result.surface_approvals:
        assert approval.surface_type in ALLOWED_SURFACE_TYPES
        assert approval.update_kind in ALLOWED_UPDATE_KINDS
        assert approval.committed is False
        assert approval.approved_for_commit_now is False
        assert approval.approved_for_future_mutation_commit_review is True
        assert approval.approval_state == "surface_approved_for_future_mutation_commit_review"


def test_explicit_mutation_commit_stabilization_preserves_blocked_source_no_leakage_and_no_commit(tmp_path):
    mixed = build_explicit_mutation_commit(
        mixed_decision_fixture(tmp_path / "mixed"),
        decision_payload=approve_payload(),
    )
    safe = build_explicit_mutation_commit(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe"),
        decision_payload=approve_all_payload(),
    )
    unsafe = build_explicit_mutation_commit(
        unsafe_source_fixture(tmp_path / "unsafe"),
        decision_payload=approve_all_payload(),
    )
    no_commit = build_explicit_mutation_commit(
        no_mutation_commit_fixture(tmp_path / "no-commit"),
        decision_payload=approve_all_payload(),
    )
    runtime = build_explicit_mutation_commit(
        no_runtime_application_fixture(tmp_path / "runtime"),
        decision_payload=approve_all_payload(),
    )
    mutation = build_explicit_mutation_commit(
        no_runtime_mutation_fixture(tmp_path / "mutation"),
        decision_payload=approve_all_payload(),
    )

    assert mixed is not None
    assert mixed.blockers
    _assert_no_runtime_mutation_flags(mixed)

    assert safe is not None
    _assert_no_leakage(safe)
    _assert_no_runtime_mutation_flags(safe)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_leakage(unsafe)
    _assert_no_runtime_mutation_flags(unsafe)

    assert no_commit is not None
    assert no_commit.mutation_committed is False
    assert no_commit.no_mutation_commit is True
    assert no_commit.no_mutation_commit_event_created is True
    _assert_no_runtime_mutation_flags(no_commit)

    assert runtime is not None
    assert runtime.runtime_application_enabled is False
    assert runtime.runtime_application_applied is False
    assert runtime.no_runtime_application is True
    _assert_no_runtime_mutation_flags(runtime)

    assert mutation is not None
    _assert_no_runtime_mutation_flags(mutation)


def test_explicit_mutation_commit_stabilization_preserves_persistence_idempotency_and_payload_replacement(tmp_path):
    fixture = payload_idempotency_fixture(tmp_path / "idempotent")
    source_commit_shell = fixture.controlled_commit_shell
    assert source_commit_shell is not None

    first = build_explicit_mutation_commit(fixture, decision_payload=approve_all_payload())
    second = build_explicit_mutation_commit(fixture, decision_payload=approve_all_payload())
    service = SimuladoExplicitRuntimeMutationCommitService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_explicit_commit(
        source_commit_shell.commit_shell_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert service.get_explicit_commit_by_id(
        first.explicit_commit_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert len(
        fixture.context.repository.list_user_simulado_explicit_mutation_commits(
            user_id=fixture.context.user_id
        )
    ) == 1

    different = different_payload_behavior_fixture(tmp_path / "different")
    different_source = different.controlled_commit_shell
    assert different_source is not None
    approved = build_explicit_mutation_commit(different, decision_payload=approve_all_payload())
    denied = build_explicit_mutation_commit(different, decision_payload=deny_payload())

    assert approved is not None
    assert denied is not None
    assert approved.explicit_commit_id != denied.explicit_commit_id
    latest = different.context.service.get_explicit_commit(
        different_source.commit_shell_id,
        user_id=different.context.user_id,
    )
    assert latest is not None
    assert latest.model_dump(mode="json") == denied.model_dump(mode="json")


def test_explicit_mutation_commit_stabilization_api_owner_scope_and_read_only_behavior(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    commit_shell = _prepare_commit_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit")
    before_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        commit_shell.commit_shell_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit/build",
        json=approve_all_payload(),
    )
    loaded = owner.get(f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit")
    explicit_commit_id = build.json()["explicit_commit_id"]
    by_id = owner.get(f"/api/simulado-explicit-commit/{explicit_commit_id}")
    after_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        commit_shell.commit_shell_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json() == by_id.json()
    assert before_shell is not None
    assert after_shell is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit/build",
        json=approve_all_payload(),
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-explicit-commit/{explicit_commit_id}").status_code == 401

    assert other.post(
        f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit/build",
        json=approve_all_payload(),
    ).status_code == 404
    assert other.get(
        f"/api/simulado-mutation-commit-shell/{commit_shell.commit_shell_id}/explicit-commit"
    ).status_code == 404
    assert other.get(f"/api/simulado-explicit-commit/{explicit_commit_id}").status_code == 404
