import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_progress_mutation import (
    SimuladoRuntimeProgressMutationService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_progress_mutations import (
    api_readonly_fixture,
    approved_for_future_only_fixture,
    audit_trail_fixture,
    build_runtime_progress_mutation_transaction,
    confirmations_incomplete_fixture,
    explicit_apply_not_approved_fixture,
    idempotency_fixture,
    intents_not_approved_fixture,
    missing_explicit_apply_fixture,
    missing_rollback_plan_fixture,
    mixed_mutation_fixture,
    mutation_mode_status_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    proposed_progress_deltas_shape_fixture,
    proposed_surface_updates_shape_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_plan_shape_fixture,
    runtime_mutation_disabled_fixture,
    surfaces_not_approved_fixture,
    user_scope_fixture,
)


FORBIDDEN_MUTATION_KEYS = {
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
    assert result.mutation_transaction_created is True
    assert result.mutation_mode in {"proposal_only", "dry_run_transaction"}
    assert result.mutation_status != "committed"
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
    for key in FORBIDDEN_MUTATION_KEYS:
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


def _prepare_explicit_apply(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    return explicit_apply


def test_runtime_progress_mutation_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_explicit_apply_fixture(tmp_path / "missing")
    future_only = approved_for_future_only_fixture(tmp_path / "future-only")
    mixed = mixed_mutation_fixture(tmp_path / "mixed")

    assert missing.missing_explicit_apply_id == "simulado-explicit-apply:missing"
    assert future_only.explicit_apply is not None
    assert mixed.explicit_apply is not None
    assert json.dumps({"fixture": "runtime-mutation"}, ensure_ascii=True)


def test_runtime_progress_mutation_stabilization_covers_source_scenarios_and_blockers(tmp_path):
    missing = build_runtime_progress_mutation_transaction(missing_explicit_apply_fixture(tmp_path / "missing"))
    not_approved = build_runtime_progress_mutation_transaction(
        explicit_apply_not_approved_fixture(tmp_path / "not-approved")
    )
    future_only = build_runtime_progress_mutation_transaction(
        approved_for_future_only_fixture(tmp_path / "future-only")
    )
    incomplete = build_runtime_progress_mutation_transaction(
        confirmations_incomplete_fixture(tmp_path / "incomplete")
    )
    rollback_missing = build_runtime_progress_mutation_transaction(
        missing_rollback_plan_fixture(tmp_path / "rollback-missing")
    )
    disabled = build_runtime_progress_mutation_transaction(
        runtime_mutation_disabled_fixture(tmp_path / "disabled")
    )

    assert missing is None

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_explicit_apply_not_approved"
    _assert_no_runtime_mutation_flags(not_approved)

    assert future_only is not None
    assert future_only.validation_summary.explicit_apply_approved is True
    assert future_only.validation_summary.approved_for_apply_now is False
    assert future_only.readiness_state == "blocked_by_apply_now_not_allowed"
    _assert_no_runtime_mutation_flags(future_only)

    assert incomplete is not None
    assert "blocked_by_confirmations_incomplete" in {item.code for item in incomplete.blockers}
    _assert_no_runtime_mutation_flags(incomplete)

    assert rollback_missing is not None
    assert "blocked_by_missing_rollback_plan" in {item.code for item in rollback_missing.blockers}
    assert rollback_missing.rollback_plan.rollback_required is True
    assert rollback_missing.rollback_plan.rollback_available is False
    assert rollback_missing.rollback_plan.rollback_verified is False
    _assert_no_runtime_mutation_flags(rollback_missing)

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_runtime_mutation_disabled"
    _assert_no_runtime_mutation_flags(disabled)


def test_runtime_progress_mutation_stabilization_covers_intents_surfaces_mixed_and_unsafe_sources(tmp_path):
    intents = build_runtime_progress_mutation_transaction(
        intents_not_approved_fixture(tmp_path / "intents")
    )
    surfaces = build_runtime_progress_mutation_transaction(
        surfaces_not_approved_fixture(tmp_path / "surfaces")
    )
    mixed = build_runtime_progress_mutation_transaction(
        mixed_mutation_fixture(tmp_path / "mixed")
    )
    unsafe = build_runtime_progress_mutation_transaction(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert intents is not None
    assert "blocked_by_intents_not_approved" in {item.code for item in intents.blockers}
    assert all("delta_blocked_by_unapproved_intent" in item.blockers for item in intents.proposed_progress_deltas)
    _assert_no_runtime_mutation_flags(intents)

    assert surfaces is not None
    assert "blocked_by_surfaces_not_approved" in {item.code for item in surfaces.blockers}
    assert all("surface_update_blocked_by_unapproved_surface" in item.blockers for item in surfaces.proposed_surface_updates)
    _assert_no_runtime_mutation_flags(surfaces)

    assert mixed is not None
    assert mixed.blockers
    _assert_no_runtime_mutation_flags(mixed)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_leakage(unsafe)
    _assert_no_runtime_mutation_flags(unsafe)


def test_runtime_progress_mutation_stabilization_covers_delta_surface_rollback_audit_and_mode_shapes(tmp_path):
    deltas = build_runtime_progress_mutation_transaction(
        proposed_progress_deltas_shape_fixture(tmp_path / "deltas")
    )
    surfaces = build_runtime_progress_mutation_transaction(
        proposed_surface_updates_shape_fixture(tmp_path / "surface-updates")
    )
    rollback = build_runtime_progress_mutation_transaction(
        rollback_plan_shape_fixture(tmp_path / "rollback")
    )
    audit = build_runtime_progress_mutation_transaction(
        audit_trail_fixture(tmp_path / "audit")
    )
    status = build_runtime_progress_mutation_transaction(
        mutation_mode_status_fixture(tmp_path / "status")
    )

    assert deltas is not None
    for item in deltas.proposed_progress_deltas:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.applied is False
        assert item.commit_allowed is False
        assert item.proposed_before_summary == {"available": False}
        assert item.proposed_after_summary == {"available": False}

    assert surfaces is not None
    for item in surfaces.proposed_surface_updates:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.applied is False
        assert item.commit_allowed is False
        assert item.proposed_before_summary == {"available": False}
        assert item.proposed_after_summary == {"available": False}

    assert rollback is not None
    assert rollback.rollback_plan.rollback_required is True
    assert rollback.rollback_plan.rollback_available is False
    assert rollback.rollback_plan.rollback_verified is False
    assert rollback.rollback_plan.rollback_steps_count == 0

    assert audit is not None
    audit_events = {item.event_type for item in audit.audit_trail}
    assert "mutation_transaction_created" in audit_events
    assert "mutation_transaction_blocked" in audit_events
    assert "mutation_proposal_created" in audit_events
    assert "rollback_plan_missing" in audit_events
    assert "apply_now_not_allowed" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert status is not None
    _assert_no_runtime_mutation_flags(status)


def test_runtime_progress_mutation_stabilization_preserves_no_leakage_and_runtime_artifacts(tmp_path):
    safe = build_runtime_progress_mutation_transaction(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    runtime = build_runtime_progress_mutation_transaction(
        no_runtime_application_fixture(tmp_path / "runtime")
    )
    mutation = build_runtime_progress_mutation_transaction(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    _assert_no_leakage(safe)
    _assert_no_runtime_mutation_flags(safe)

    assert runtime is not None
    assert runtime.runtime_application_enabled is False
    assert runtime.runtime_application_applied is False
    assert runtime.no_runtime_application is True

    assert mutation is not None
    _assert_no_runtime_mutation_flags(mutation)


def test_runtime_progress_mutation_stabilization_preserves_persistence_and_idempotency(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    source_explicit_apply = fixture.explicit_apply
    assert source_explicit_apply is not None

    first = build_runtime_progress_mutation_transaction(fixture)
    second = build_runtime_progress_mutation_transaction(fixture)
    service = SimuladoRuntimeProgressMutationService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_mutation_transaction(
        source_explicit_apply.explicit_apply_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert service.get_mutation_transaction_by_id(
        first.mutation_transaction_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert len(
        fixture.context.repository.list_user_simulado_runtime_progress_mutation_transactions(
            user_id=fixture.context.user_id
        )
    ) == 1


def test_runtime_progress_mutation_stabilization_api_owner_scope_and_read_only_behavior(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    explicit_apply = _prepare_explicit_apply(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    before_explicit = repository.get_simulado_explicit_runtime_apply_by_id(
        explicit_apply.explicit_apply_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    )
    loaded = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    mutation_id = build.json()["mutation_transaction_id"]
    by_id = owner.get(f"/api/simulado-progress-mutation/{mutation_id}")
    after_explicit = repository.get_simulado_explicit_runtime_apply_by_id(
        explicit_apply.explicit_apply_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json() == by_id.json()
    assert before_explicit is not None
    assert after_explicit is not None
    assert before_explicit.model_dump(mode="json") == after_explicit.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-progress-mutation/{mutation_id}").status_code == 401

    assert other.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation"
    ).status_code == 404
    assert other.get(f"/api/simulado-progress-mutation/{mutation_id}").status_code == 404
