import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_mutation_commit import (
    SimuladoControlledRuntimeMutationCommitService,
)
from tests.fixtures.simulado_controlled_mutation_commit_shells import (
    api_readonly_fixture,
    audit_confirmation_missing_fixture,
    audit_requirements_shape_fixture,
    audit_trail_fixture,
    build_controlled_mutation_commit_shell,
    commit_mode_status_fixture,
    commit_policy_missing_fixture,
    delta_commit_decision_shape_fixture,
    deltas_not_commit_allowed_fixture,
    explicit_apply_not_approved_fixture,
    explicit_commit_approval_missing_fixture,
    idempotency_fixture,
    missing_mutation_transaction_fixture,
    mixed_commit_shell_fixture,
    mutation_commit_not_ready_fixture,
    mutation_not_valid_for_commit_fixture,
    no_mutation_commit_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_not_available_fixture,
    rollback_not_verified_fixture,
    rollback_readiness_shape_fixture,
    runtime_mutation_disabled_fixture,
    surface_commit_decision_shape_fixture,
    surfaces_not_commit_allowed_fixture,
    transaction_already_committed_fixture,
    transaction_not_proposal_only_fixture,
    transaction_proposal_only_fixture,
    user_scope_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_COMMIT_SHELL_KEYS = {
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

REQUIRED_AUDIT_REQUIREMENTS = {
    "commit_policy_confirmation",
    "explicit_commit_approval",
    "audit_confirmation",
    "rollback_verification_confirmation",
    "public_answer_key_absence_confirmation",
    "human_review_confirmation",
}


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.commit_shell_created is True
    assert result.commit_request_accepted is False
    assert result.commit_preconditions_satisfied is False
    assert result.commit_ready_for_execution is False
    assert result.commit_mode in {"pre_commit_shell", "controlled_commit_shell"}
    assert result.commit_status != "committed"
    assert result.mutation_valid_for_commit is False
    assert result.mutation_commit_ready is False
    assert result.mutation_committed is False
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
    for key in FORBIDDEN_COMMIT_SHELL_KEYS:
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


def _prepare_mutation_transaction(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    return transaction


def test_controlled_mutation_commit_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_mutation_transaction_fixture(tmp_path / "missing")
    proposal = transaction_proposal_only_fixture(tmp_path / "proposal")
    mixed = mixed_commit_shell_fixture(tmp_path / "mixed")

    assert missing.missing_mutation_transaction_id == "simulado-progress-mutation:missing"
    assert proposal.mutation_transaction is not None
    assert mixed.mutation_transaction is not None
    assert json.dumps({"fixture": "controlled-mutation-commit"}, ensure_ascii=True)


def test_controlled_mutation_commit_stabilization_covers_source_scenarios_and_blockers(tmp_path):
    missing = build_controlled_mutation_commit_shell(
        missing_mutation_transaction_fixture(tmp_path / "missing")
    )
    proposal = build_controlled_mutation_commit_shell(
        transaction_proposal_only_fixture(tmp_path / "proposal")
    )
    not_proposal = build_controlled_mutation_commit_shell(
        transaction_not_proposal_only_fixture(tmp_path / "not-proposal")
    )
    already_committed = build_controlled_mutation_commit_shell(
        transaction_already_committed_fixture(tmp_path / "already-committed")
    )
    mutation_invalid = build_controlled_mutation_commit_shell(
        mutation_not_valid_for_commit_fixture(tmp_path / "invalid")
    )
    mutation_not_ready = build_controlled_mutation_commit_shell(
        mutation_commit_not_ready_fixture(tmp_path / "not-ready")
    )
    rollback_unavailable = build_controlled_mutation_commit_shell(
        rollback_not_available_fixture(tmp_path / "rollback-unavailable")
    )
    rollback_unverified = build_controlled_mutation_commit_shell(
        rollback_not_verified_fixture(tmp_path / "rollback-unverified")
    )
    deltas = build_controlled_mutation_commit_shell(
        deltas_not_commit_allowed_fixture(tmp_path / "deltas")
    )
    surfaces = build_controlled_mutation_commit_shell(
        surfaces_not_commit_allowed_fixture(tmp_path / "surfaces")
    )
    commit_policy = build_controlled_mutation_commit_shell(
        commit_policy_missing_fixture(tmp_path / "commit-policy")
    )
    explicit_commit = build_controlled_mutation_commit_shell(
        explicit_commit_approval_missing_fixture(tmp_path / "explicit-commit")
    )
    audit = build_controlled_mutation_commit_shell(
        audit_confirmation_missing_fixture(tmp_path / "audit")
    )
    runtime_disabled = build_controlled_mutation_commit_shell(
        runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled")
    )
    unsafe = build_controlled_mutation_commit_shell(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )
    explicit_not_approved = build_controlled_mutation_commit_shell(
        explicit_apply_not_approved_fixture(tmp_path / "explicit-not-approved")
    )

    assert missing is None

    assert proposal is not None
    _assert_no_runtime_mutation_flags(proposal)

    assert not_proposal is not None
    assert not_proposal.readiness_state == "blocked_by_transaction_not_proposal_only"
    _assert_no_runtime_mutation_flags(not_proposal)

    assert already_committed is not None
    assert already_committed.readiness_state == "blocked_by_transaction_already_committed"
    _assert_no_runtime_mutation_flags(already_committed)

    assert mutation_invalid is not None
    assert mutation_invalid.readiness_state == "blocked_by_mutation_not_valid_for_commit"
    _assert_no_runtime_mutation_flags(mutation_invalid)

    assert mutation_not_ready is not None
    assert mutation_not_ready.readiness_state == "blocked_by_mutation_commit_not_ready"
    _assert_no_runtime_mutation_flags(mutation_not_ready)

    assert rollback_unavailable is not None
    assert rollback_unavailable.readiness_state == "blocked_by_rollback_not_available"
    assert rollback_unavailable.rollback_readiness.rollback_ready_for_commit is False
    _assert_no_runtime_mutation_flags(rollback_unavailable)

    assert rollback_unverified is not None
    assert rollback_unverified.readiness_state == "blocked_by_rollback_not_verified"
    assert rollback_unverified.rollback_readiness.rollback_ready_for_commit is False
    _assert_no_runtime_mutation_flags(rollback_unverified)

    assert deltas is not None
    assert deltas.readiness_state == "blocked_by_deltas_not_commit_allowed"
    assert all(item.commit_decision == "delta_rejected_pre_commit" for item in deltas.delta_commit_decisions)
    _assert_no_runtime_mutation_flags(deltas)

    assert surfaces is not None
    assert surfaces.readiness_state == "blocked_by_surfaces_not_commit_allowed"
    assert all(
        item.commit_decision == "surface_rejected_pre_commit"
        for item in surfaces.surface_commit_decisions
    )
    _assert_no_runtime_mutation_flags(surfaces)

    assert commit_policy is not None
    assert commit_policy.readiness_state == "blocked_by_commit_policy_missing"
    _assert_no_runtime_mutation_flags(commit_policy)

    assert explicit_commit is not None
    assert explicit_commit.readiness_state == "blocked_by_explicit_commit_approval_missing"
    _assert_no_runtime_mutation_flags(explicit_commit)

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_confirmation_missing"
    _assert_no_runtime_mutation_flags(audit)

    assert runtime_disabled is not None
    assert runtime_disabled.readiness_state == "blocked_by_runtime_mutation_disabled"
    _assert_no_runtime_mutation_flags(runtime_disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_leakage(unsafe)
    _assert_no_runtime_mutation_flags(unsafe)

    assert explicit_not_approved is not None
    assert explicit_not_approved.readiness_state == "blocked_by_mutation_not_valid_for_commit"
    _assert_no_runtime_mutation_flags(explicit_not_approved)


def test_controlled_mutation_commit_stabilization_covers_decision_rollback_audit_and_mode_shapes(tmp_path):
    deltas = build_controlled_mutation_commit_shell(
        delta_commit_decision_shape_fixture(tmp_path / "deltas")
    )
    surfaces = build_controlled_mutation_commit_shell(
        surface_commit_decision_shape_fixture(tmp_path / "surfaces")
    )
    rollback = build_controlled_mutation_commit_shell(
        rollback_readiness_shape_fixture(tmp_path / "rollback")
    )
    requirements = build_controlled_mutation_commit_shell(
        audit_requirements_shape_fixture(tmp_path / "requirements")
    )
    audit = build_controlled_mutation_commit_shell(
        audit_trail_fixture(tmp_path / "audit")
    )
    status = build_controlled_mutation_commit_shell(
        commit_mode_status_fixture(tmp_path / "status")
    )

    assert deltas is not None
    for item in deltas.delta_commit_decisions:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.committed is False
        assert item.commit_decision == "delta_rejected_pre_commit"

    assert surfaces is not None
    for item in surfaces.surface_commit_decisions:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.committed is False
        assert item.commit_decision == "surface_rejected_pre_commit"

    assert rollback is not None
    assert rollback.rollback_readiness.rollback_required is True
    assert rollback.rollback_readiness.rollback_available is False
    assert rollback.rollback_readiness.rollback_verified is False
    assert rollback.rollback_readiness.rollback_ready_for_commit is False

    assert requirements is not None
    assert {item.requirement_type for item in requirements.audit_requirements} == REQUIRED_AUDIT_REQUIREMENTS
    for item in requirements.audit_requirements:
        assert item.required is True
        assert item.satisfied is False

    assert audit is not None
    audit_events = {item.event_type for item in audit.audit_trail}
    assert "commit_shell_created" in audit_events
    assert "commit_blocked" in audit_events
    assert "mutation_not_valid_for_commit" in audit_events
    assert "mutation_commit_not_ready" in audit_events
    assert "rollback_not_available" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert status is not None
    _assert_no_runtime_mutation_flags(status)


def test_controlled_mutation_commit_stabilization_preserves_no_leakage_and_no_commit_behavior(tmp_path):
    safe = build_controlled_mutation_commit_shell(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_commit = build_controlled_mutation_commit_shell(
        no_mutation_commit_fixture(tmp_path / "no-commit")
    )
    mutation = build_controlled_mutation_commit_shell(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    mixed = build_controlled_mutation_commit_shell(
        mixed_commit_shell_fixture(tmp_path / "mixed")
    )

    assert safe is not None
    _assert_no_leakage(safe)
    _assert_no_runtime_mutation_flags(safe)

    assert no_commit is not None
    assert no_commit.mutation_committed is False
    _assert_no_runtime_mutation_flags(no_commit)

    assert mutation is not None
    _assert_no_runtime_mutation_flags(mutation)

    assert mixed is not None
    assert mixed.blockers
    _assert_no_runtime_mutation_flags(mixed)


def test_controlled_mutation_commit_stabilization_preserves_persistence_and_idempotency(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    source_transaction = fixture.mutation_transaction
    assert source_transaction is not None

    first = build_controlled_mutation_commit_shell(fixture)
    second = build_controlled_mutation_commit_shell(fixture)
    service = SimuladoControlledRuntimeMutationCommitService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_commit_shell(
        source_transaction.mutation_transaction_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert service.get_commit_shell_by_id(
        first.commit_shell_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert len(
        fixture.context.repository.list_user_simulado_controlled_mutation_commit_shells(
            user_id=fixture.context.user_id
        )
    ) == 1


def test_controlled_mutation_commit_stabilization_api_owner_scope_and_read_only_behavior(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    transaction = _prepare_mutation_transaction(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell"
    )
    before_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        transaction.mutation_transaction_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell/build"
    )
    loaded = owner.get(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell"
    )
    commit_shell_id = build.json()["commit_shell_id"]
    by_id = owner.get(f"/api/simulado-mutation-commit-shell/{commit_shell_id}")
    after_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        transaction.mutation_transaction_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json() == by_id.json()
    assert before_transaction is not None
    assert after_transaction is not None
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-mutation-commit-shell/{commit_shell_id}").status_code == 401

    assert other.post(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-progress-mutation/{transaction.mutation_transaction_id}/commit-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-mutation-commit-shell/{commit_shell_id}").status_code == 404
