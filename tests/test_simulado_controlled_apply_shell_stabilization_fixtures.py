import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_apply_shell import (
    SimuladoControlledRuntimeApplyShellService,
)
from tests.fixtures.simulado_controlled_apply_shells import (
    api_readonly_fixture,
    application_already_applied_fixture,
    application_not_planned_only_fixture,
    audit_confirmation_missing_fixture,
    audit_requirements_shape_fixture,
    audit_trail_fixture,
    build_controlled_apply_shell,
    explicit_apply_approval_missing_fixture,
    idempotency_fixture,
    intent_decision_shape_fixture,
    intents_not_apply_allowed_fixture,
    missing_runtime_policy_fixture,
    missing_runtime_progress_application_fixture,
    mixed_shell_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_only_source_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_plan_missing_fixture,
    runtime_application_disabled_fixture,
    surface_decision_shape_fixture,
    surfaces_not_apply_allowed_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_APPLY_SHELL_KEYS = {
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


def _requirement(shell, requirement_type: str):
    return next(item for item in shell.audit_requirements if item.requirement_type == requirement_type)


def _create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


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


def _prepare_application(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    application = fixture.runtime_progress_application
    assert application is not None
    return application


def test_controlled_apply_shell_stabilization_fixtures_are_json_safe_and_deterministic(tmp_path):
    fixture = idempotency_fixture(tmp_path / "idempotent")
    first = build_controlled_apply_shell(fixture)
    second = build_controlled_apply_shell(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    dumped_payload = first.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    assert first.metadata["llm_used"] is False
    assert first.metadata["external_calls_used"] is False
    assert "data:image" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert len(dumped) < 100000


def test_controlled_apply_shell_stabilization_covers_source_application_shapes(tmp_path):
    missing = missing_runtime_progress_application_fixture(tmp_path / "missing")
    planned_only = build_controlled_apply_shell(planned_only_source_fixture(tmp_path / "planned-only"))
    not_planned = build_controlled_apply_shell(application_not_planned_only_fixture(tmp_path / "not-planned"))
    already_applied = build_controlled_apply_shell(
        application_already_applied_fixture(tmp_path / "already-applied")
    )

    assert build_controlled_apply_shell(missing) is None
    assert missing.context.repository.list_user_simulado_controlled_apply_shells(
        user_id=missing.context.user_id
    ) == []

    assert planned_only is not None
    assert planned_only.precondition_summary.source_application_planned_only is True
    assert planned_only.precondition_summary.source_application_not_applied is True
    assert planned_only.apply_shell_created is True
    assert planned_only.apply_request_accepted is False
    assert planned_only.runtime_application_applied is False

    assert not_planned is not None
    assert not_planned.readiness_state == "blocked_by_application_not_planned_only"
    assert not_planned.runtime_application_applied is False

    assert already_applied is not None
    assert already_applied.readiness_state == "blocked_by_application_already_applied"
    assert already_applied.runtime_application_applied is False


def test_controlled_apply_shell_stabilization_covers_policy_approval_audit_and_rollback_requirements(tmp_path):
    policy = build_controlled_apply_shell(missing_runtime_policy_fixture(tmp_path / "policy"))
    explicit = build_controlled_apply_shell(explicit_apply_approval_missing_fixture(tmp_path / "explicit"))
    audit = build_controlled_apply_shell(audit_confirmation_missing_fixture(tmp_path / "audit"))
    rollback = build_controlled_apply_shell(rollback_plan_missing_fixture(tmp_path / "rollback"))

    assert policy is not None
    assert policy.readiness_state == "blocked_by_runtime_policy_missing"
    assert _requirement(policy, "runtime_policy_confirmation").required is True
    assert _requirement(policy, "runtime_policy_confirmation").satisfied is False

    assert explicit is not None
    assert explicit.readiness_state == "blocked_by_explicit_apply_approval_missing"
    assert _requirement(explicit, "explicit_apply_approval").required is True
    assert _requirement(explicit, "explicit_apply_approval").satisfied is False

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_confirmation_missing"
    assert _requirement(audit, "audit_confirmation").required is True
    assert _requirement(audit, "audit_confirmation").satisfied is False

    assert rollback is not None
    assert rollback.apply_request_accepted is False
    assert rollback.apply_preconditions_satisfied is False
    assert _requirement(rollback, "rollback_plan_confirmation").required is True
    assert _requirement(rollback, "rollback_plan_confirmation").satisfied is False


def test_controlled_apply_shell_stabilization_covers_intent_and_surface_decisions(tmp_path):
    intents = build_controlled_apply_shell(intents_not_apply_allowed_fixture(tmp_path / "intents"))
    intent_shape = build_controlled_apply_shell(intent_decision_shape_fixture(tmp_path / "intent-shape"))
    surfaces = build_controlled_apply_shell(surfaces_not_apply_allowed_fixture(tmp_path / "surfaces"))
    surface_shape = build_controlled_apply_shell(surface_decision_shape_fixture(tmp_path / "surface-shape"))

    assert intents is not None
    assert intents.readiness_state == "blocked_by_intents_not_apply_allowed"
    for decision in intents.intent_decisions:
        assert decision.apply_decision == "intent_rejected_pre_apply"
        assert decision.applied is False
        assert "intent_blocked_by_apply_not_allowed" in decision.blockers

    assert intent_shape is not None
    for decision in intent_shape.intent_decisions:
        assert decision.intent_type in {
            "progress_update_candidate",
            "ranking_update_candidate",
            "retention_update_candidate",
            "scheduler_update_candidate",
            "study_cycle_update_candidate",
            "curriculum_graph_update_candidate",
            "unknown",
        }
        assert decision.proposed_surface in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert decision.applied is False

    assert surfaces is not None
    assert surfaces.readiness_state == "blocked_by_surfaces_not_apply_allowed"
    for decision in surfaces.surface_decisions:
        assert decision.apply_decision == "surface_rejected_pre_apply"
        assert decision.applied is False
        assert "surface_blocked_by_apply_not_allowed" in decision.blockers

    assert surface_shape is not None
    for decision in surface_shape.surface_decisions:
        assert decision.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert decision.applied is False


def test_controlled_apply_shell_stabilization_covers_runtime_disabled_public_exposure_audit_and_mixed(tmp_path):
    runtime_disabled = build_controlled_apply_shell(runtime_application_disabled_fixture(tmp_path / "disabled"))
    public_exposure = build_controlled_apply_shell(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "public-exposure")
    )
    requirements = build_controlled_apply_shell(audit_requirements_shape_fixture(tmp_path / "requirements"))
    audit = build_controlled_apply_shell(audit_trail_fixture(tmp_path / "audit"))
    mixed = build_controlled_apply_shell(mixed_shell_fixture(tmp_path / "mixed"))

    assert runtime_disabled is not None
    assert runtime_disabled.readiness_state == "blocked_by_runtime_application_disabled"
    assert runtime_disabled.runtime_application_enabled is False
    assert runtime_disabled.runtime_application_applied is False
    assert runtime_disabled.progress_mutation_enabled is False
    assert runtime_disabled.progress_mutation_applied is False
    assert runtime_disabled.ranking_update_enabled is False
    assert runtime_disabled.ranking_update_applied is False
    assert runtime_disabled.retention_update_enabled is False
    assert runtime_disabled.retention_update_applied is False
    assert runtime_disabled.scheduler_update_enabled is False
    assert runtime_disabled.scheduler_update_applied is False
    assert runtime_disabled.study_cycle_update_enabled is False
    assert runtime_disabled.study_cycle_update_applied is False
    assert runtime_disabled.curriculum_graph_update_enabled is False
    assert runtime_disabled.curriculum_graph_update_applied is False
    assert runtime_disabled.adaptive_tuning_enabled is False
    assert runtime_disabled.adaptive_tuning_applied is False
    assert runtime_disabled.no_runtime_application is True
    assert runtime_disabled.no_progress_mutation is True
    assert runtime_disabled.no_ranking_update is True
    assert runtime_disabled.no_retention_update is True
    assert runtime_disabled.no_scheduler_update is True
    assert runtime_disabled.no_study_cycle_update is True
    assert runtime_disabled.no_curriculum_graph_update is True
    assert runtime_disabled.no_adaptive_tuning_update is True

    assert public_exposure is not None
    assert public_exposure.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    dumped_payload = public_exposure.model_dump(mode="json")
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_APPLY_SHELL_KEYS:
        assert key not in dumped_keys

    assert requirements is not None
    assert {item.requirement_type for item in requirements.audit_requirements} == {
        "runtime_policy_confirmation",
        "explicit_apply_approval",
        "audit_confirmation",
        "public_answer_key_absence_confirmation",
        "rollback_plan_confirmation",
        "human_review_confirmation",
    }
    assert all(item.required is True for item in requirements.audit_requirements)
    assert all(item.satisfied is False for item in requirements.audit_requirements)

    assert audit is not None
    event_types = {item.event_type for item in audit.audit_trail}
    assert "apply_shell_created" in event_types
    assert "apply_blocked" in event_types
    assert "runtime_policy_missing" in event_types
    assert "no_runtime_application" in event_types

    assert mixed is not None
    blocker_codes = {item.code for item in mixed.blockers}
    assert {
        "blocked_by_runtime_policy_missing",
        "blocked_by_explicit_apply_approval_missing",
        "blocked_by_audit_confirmation_missing",
        "blocked_by_intents_not_apply_allowed",
        "blocked_by_surfaces_not_apply_allowed",
    }.issubset(blocker_codes)
    assert mixed.runtime_application_applied is False


def test_controlled_apply_shell_stabilization_preserves_no_runtime_application_mutation_and_no_leakage(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    application_fixture = no_runtime_application_fixture(tmp_path / "application", repository=repository)
    mutation_fixture = no_runtime_mutation_fixture(tmp_path / "mutation", repository=repository)
    application = build_controlled_apply_shell(application_fixture)
    mutation = build_controlled_apply_shell(mutation_fixture)

    assert application is not None
    assert application.application_mode in {"pre_apply_shell", "controlled_apply_shell"}
    assert application.apply_status in {
        "apply_shell_created_not_applied",
        "apply_blocked",
        "apply_needs_review",
    }
    assert application.apply_request_accepted is False
    assert application.apply_preconditions_satisfied is False
    assert application.runtime_application_enabled is False
    assert application.runtime_application_applied is False
    assert application.no_runtime_application is True

    assert mutation is not None
    dumped_payload = mutation.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert mutation.no_progress_mutation is True
    assert mutation.no_ranking_update is True
    assert mutation.no_retention_update is True
    assert mutation.no_scheduler_update is True
    assert mutation.no_study_cycle_update is True
    assert mutation.no_curriculum_graph_update is True
    assert mutation.no_adaptive_tuning_update is True
    assert mutation.answer_key_publicly_exposed is False
    assert mutation.gabarito_publicly_exposed is False
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    for key in FORBIDDEN_APPLY_SHELL_KEYS:
        assert key not in dumped_keys


def test_controlled_apply_shell_stabilization_preserves_persistence_runtime_state_and_api_scope(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotency", repository=repository)
    result = build_controlled_apply_shell(fixture)
    assert result is not None
    application = fixture.runtime_progress_application
    assert application is not None
    service = SimuladoControlledRuntimeApplyShellService(repository)

    before_application = repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    before_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_integrated = repository.get_simulado_integrated_result_by_id(
        application.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_apply_shell(application.application_id, user_id=fixture.context.user_id)
    second = service.build_apply_shell(application.application_id, user_id=fixture.context.user_id)
    loaded = service.get_apply_shell(application.application_id, user_id=fixture.context.user_id)
    by_id = service.get_apply_shell_by_id(result.apply_shell_id, user_id=fixture.context.user_id)
    listed = repository.list_user_simulado_controlled_apply_shells(user_id=fixture.context.user_id)

    after_application = repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    after_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_integrated = repository.get_simulado_integrated_result_by_id(
        application.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_application is not None and after_application is not None
    assert before_runtime_guardrail is not None and after_runtime_guardrail is not None
    assert before_integrated is not None and after_integrated is not None
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")

    owner, other, anonymous, api_repository = _create_clients(tmp_path / "api")
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    api_application = _prepare_application(api_repository, tmp_path / "api-owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell"
    )
    first_build = owner.post(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell/build"
    )
    second_build = owner.post(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell/build"
    )
    loaded_once = owner.get(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell"
    )
    loaded_twice = owner.get(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell"
    )
    apply_shell_id = first_build.json()["apply_shell_id"]
    before_api_application = api_repository.get_simulado_runtime_progress_application_by_id(
        api_application.application_id,
        user_id=owner_user_id,
    )
    by_id_response = owner.get(f"/api/simulado-controlled-apply-shell/{apply_shell_id}")
    after_api_application = api_repository.get_simulado_runtime_progress_application_by_id(
        api_application.application_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert loaded_once.status_code == 200
    assert loaded_twice.status_code == 200
    assert by_id_response.status_code == 200
    assert first_build.json() == second_build.json()
    assert loaded_once.json() == loaded_twice.json()
    assert before_api_application is not None and after_api_application is not None
    assert before_api_application.model_dump(mode="json") == after_api_application.model_dump(mode="json")
    assert anonymous.post(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-controlled-apply-shell/{apply_shell_id}").status_code == 401
    assert other.post(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-progress-application/{api_application.application_id}/controlled-apply-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-controlled-apply-shell/{apply_shell_id}").status_code == 404
