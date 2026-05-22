import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_mutation_commit_transaction import (
    SimuladoRuntimeMutationCommitTransactionService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_mutation_commit_transactions import (
    api_readonly_fixture,
    approved_for_future_only_fixture,
    audit_trail_fixture,
    build_runtime_mutation_commit_transaction,
    commit_execution_disabled_fixture,
    commit_shell_not_pre_commit_only_fixture,
    commit_transaction_mode_status_fixture,
    confirmations_incomplete_fixture,
    delta_approvals_not_ready_fixture,
    explicit_commit_not_approved_fixture,
    idempotency_fixture,
    missing_explicit_commit_fixture,
    missing_rollback_execution_plan_fixture,
    missing_source_mutation_transaction_fixture,
    mixed_commit_transaction_fixture,
    no_commit_execution_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_progress_commits_shape_fixture,
    planned_surface_commits_shape_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_execution_plan_shape_fixture,
    rollback_unavailable_fixture,
    rollback_unverified_fixture,
    surface_approvals_not_ready_fixture,
    user_scope_fixture,
)


FORBIDDEN_COMMIT_TRANSACTION_KEYS = {
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
    assert result.commit_transaction_created is True
    assert result.commit_transaction_mode in {"commit_plan_only", "dry_run_commit_transaction"}
    assert result.commit_transaction_status != "committed"
    assert result.commit_transaction_valid_for_execution is False
    assert result.commit_execution_ready is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.no_commit_execution is True
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
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(result) -> None:
    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_COMMIT_TRANSACTION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped


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


def _prepare_explicit_commit(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    return explicit_commit


def test_runtime_mutation_commit_transaction_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_explicit_commit_fixture(tmp_path / "missing")
    future_only = approved_for_future_only_fixture(tmp_path / "future-only")
    mode_status = commit_transaction_mode_status_fixture(tmp_path / "mode-status")
    mixed = mixed_commit_transaction_fixture(tmp_path / "mixed")

    assert missing.missing_explicit_commit_id == "simulado-explicit-commit:missing"
    assert future_only.explicit_commit is not None
    assert mode_status.explicit_commit is not None
    assert mixed.explicit_commit is not None
    assert json.dumps({"fixture": "runtime-mutation-commit-transaction"}, ensure_ascii=True)


def test_runtime_mutation_commit_transaction_stabilization_covers_source_scenarios_and_blockers(tmp_path):
    missing = build_runtime_mutation_commit_transaction(missing_explicit_commit_fixture(tmp_path / "missing"))
    not_approved = build_runtime_mutation_commit_transaction(
        explicit_commit_not_approved_fixture(tmp_path / "not-approved")
    )
    future_only = build_runtime_mutation_commit_transaction(
        approved_for_future_only_fixture(tmp_path / "future-only")
    )
    confirmations = build_runtime_mutation_commit_transaction(
        confirmations_incomplete_fixture(tmp_path / "confirmations")
    )
    shell = build_runtime_mutation_commit_transaction(
        commit_shell_not_pre_commit_only_fixture(tmp_path / "shell")
    )
    source = build_runtime_mutation_commit_transaction(
        missing_source_mutation_transaction_fixture(tmp_path / "source")
    )
    missing_rollback = build_runtime_mutation_commit_transaction(
        missing_rollback_execution_plan_fixture(tmp_path / "missing-rollback")
    )
    unavailable = build_runtime_mutation_commit_transaction(
        rollback_unavailable_fixture(tmp_path / "rollback-unavailable")
    )
    unverified = build_runtime_mutation_commit_transaction(
        rollback_unverified_fixture(tmp_path / "rollback-unverified")
    )
    deltas = build_runtime_mutation_commit_transaction(
        delta_approvals_not_ready_fixture(tmp_path / "deltas")
    )
    surfaces = build_runtime_mutation_commit_transaction(
        surface_approvals_not_ready_fixture(tmp_path / "surfaces")
    )
    disabled = build_runtime_mutation_commit_transaction(
        commit_execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_runtime_mutation_commit_transaction(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_explicit_commit_not_approved"
    _assert_no_runtime_mutation_flags(not_approved)

    assert future_only is not None
    assert future_only.validation_summary.explicit_commit_approved is True
    assert future_only.validation_summary.approved_for_commit_now is False
    assert future_only.readiness_state == "blocked_by_commit_now_not_allowed"
    _assert_no_runtime_mutation_flags(future_only)

    assert confirmations is not None
    assert "blocked_by_confirmations_incomplete" in {item.code for item in confirmations.blockers}
    _assert_no_runtime_mutation_flags(confirmations)

    assert shell is not None
    assert shell.readiness_state == "blocked_by_commit_shell_not_pre_commit_only"
    _assert_no_runtime_mutation_flags(shell)

    assert source is not None
    assert source.readiness_state == "blocked_by_missing_source_mutation_transaction"
    _assert_no_runtime_mutation_flags(source)

    assert missing_rollback is not None
    assert "blocked_by_missing_rollback_execution_plan" in {item.code for item in missing_rollback.blockers}
    _assert_no_runtime_mutation_flags(missing_rollback)

    assert unavailable is not None
    assert "blocked_by_rollback_not_available" in {item.code for item in unavailable.blockers}
    assert unavailable.rollback_execution_plan.rollback_execution_ready is False
    _assert_no_runtime_mutation_flags(unavailable)

    assert unverified is not None
    assert "blocked_by_rollback_not_verified" in {item.code for item in unverified.blockers}
    assert unverified.rollback_execution_plan.rollback_execution_ready is False
    _assert_no_runtime_mutation_flags(unverified)

    assert deltas is not None
    assert "blocked_by_delta_approvals_not_ready" in {item.code for item in deltas.blockers}
    _assert_no_runtime_mutation_flags(deltas)

    assert surfaces is not None
    assert "blocked_by_surface_approvals_not_ready" in {item.code for item in surfaces.blockers}
    _assert_no_runtime_mutation_flags(surfaces)

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_commit_execution_disabled"
    _assert_no_runtime_mutation_flags(disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_mutation_flags(unsafe)


def test_runtime_mutation_commit_transaction_stabilization_covers_planned_shapes_and_audit(tmp_path):
    progress = build_runtime_mutation_commit_transaction(
        planned_progress_commits_shape_fixture(tmp_path / "progress")
    )
    surfaces = build_runtime_mutation_commit_transaction(
        planned_surface_commits_shape_fixture(tmp_path / "surfaces")
    )
    rollback = build_runtime_mutation_commit_transaction(
        rollback_execution_plan_shape_fixture(tmp_path / "rollback")
    )
    audit = build_runtime_mutation_commit_transaction(
        audit_trail_fixture(tmp_path / "audit")
    )
    mode_status = build_runtime_mutation_commit_transaction(
        commit_transaction_mode_status_fixture(tmp_path / "mode-status")
    )
    mixed = build_runtime_mutation_commit_transaction(
        mixed_commit_transaction_fixture(tmp_path / "mixed")
    )

    assert progress is not None
    for item in progress.planned_progress_commits:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.committed is False
        assert item.execution_allowed is False
        assert item.proposed_before_summary == {"available": False}
        assert item.proposed_after_summary == {"available": False}

    assert surfaces is not None
    for item in surfaces.planned_surface_commits:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.committed is False
        assert item.execution_allowed is False
        assert item.proposed_before_summary == {"available": False}
        assert item.proposed_after_summary == {"available": False}

    assert rollback is not None
    assert rollback.rollback_execution_plan.rollback_required is True
    assert rollback.rollback_execution_plan.rollback_available is False
    assert rollback.rollback_execution_plan.rollback_verified is False
    assert rollback.rollback_execution_plan.rollback_execution_ready is False
    assert rollback.rollback_execution_plan.rollback_execution_performed is False
    assert rollback.rollback_execution_plan.rollback_steps_count >= 0

    assert audit is not None
    events = {item.event_type for item in audit.audit_trail}
    assert "commit_transaction_created" in events
    assert "commit_transaction_blocked" in events
    assert "commit_plan_created" in events
    assert "commit_now_not_allowed" in events
    assert "rollback_not_available" in events
    assert "rollback_not_verified" in events
    assert "no_commit_execution" in events
    assert "no_mutation_commit" in events
    assert "no_runtime_application" in events
    assert "no_progress_mutation" in events
    assert "no_final_pedagogical_update_event" in events

    assert mode_status is not None
    assert mode_status.commit_transaction_mode in {"commit_plan_only", "dry_run_commit_transaction"}
    assert mode_status.commit_transaction_status != "committed"
    _assert_no_runtime_mutation_flags(mode_status)

    assert mixed is not None
    assert mixed.blockers
    assert mixed.warnings
    _assert_no_runtime_mutation_flags(mixed)


def test_runtime_mutation_commit_transaction_stabilization_preserves_no_leakage_and_no_execution(tmp_path):
    safe = build_runtime_mutation_commit_transaction(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_commit = build_runtime_mutation_commit_transaction(
        no_commit_execution_fixture(tmp_path / "no-commit")
    )
    no_runtime_application = build_runtime_mutation_commit_transaction(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    mutation = build_runtime_mutation_commit_transaction(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    _assert_no_leakage(safe)

    assert no_commit is not None
    assert no_commit.commit_executed is False
    assert no_commit.no_commit_execution is True
    assert no_commit.mutation_committed is False
    assert no_commit.no_mutation_commit is True
    assert no_commit.no_mutation_commit_event_created is True
    _assert_no_runtime_mutation_flags(no_commit)

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    assert no_runtime_application.no_runtime_application is True
    _assert_no_runtime_mutation_flags(no_runtime_application)

    assert mutation is not None
    _assert_no_runtime_mutation_flags(mutation)
    _assert_no_leakage(mutation)


def test_runtime_mutation_commit_transaction_stabilization_is_idempotent_owner_only_and_read_only(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotent", repository=repository)
    source_explicit_commit = fixture.explicit_commit
    assert source_explicit_commit is not None
    first = build_runtime_mutation_commit_transaction(fixture)
    second = build_runtime_mutation_commit_transaction(fixture)
    service = SimuladoRuntimeMutationCommitTransactionService(repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_commit_transaction(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert service.get_commit_transaction_by_id(
        first.commit_transaction_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert len(
        repository.list_user_simulado_runtime_mutation_commit_transactions(user_id=fixture.context.user_id)
    ) == 1

    before_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    loaded = service.get_commit_transaction(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    after_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    assert loaded is not None
    assert before_explicit is not None
    assert after_explicit is not None
    assert before_explicit.model_dump(mode="json") == after_explicit.model_dump(mode="json")

    owner = TestClient(create_app(repository=repository))
    other = TestClient(create_app(repository=repository))
    anonymous = TestClient(create_app(repository=repository))
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    explicit_commit = _prepare_explicit_commit(repository, tmp_path / "owner-scope", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction")
    build = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    loaded_owner = owner.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    )
    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded_owner.status_code == 200

    transaction_id = build.json()["commit_transaction_id"]
    assert other.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    ).status_code == 404
    assert other.get(f"/api/simulado-commit-transaction/{transaction_id}").status_code == 404
    assert anonymous.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-commit-transaction/{transaction_id}").status_code == 401

    before_owner_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        explicit_commit.explicit_commit_id,
        user_id=owner_user_id,
    )
    reread = owner.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    )
    after_owner_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        explicit_commit.explicit_commit_id,
        user_id=owner_user_id,
    )
    assert reread.status_code == 200
    assert before_owner_explicit is not None
    assert after_owner_explicit is not None
    assert before_owner_explicit.model_dump(mode="json") == after_owner_explicit.model_dump(mode="json")
