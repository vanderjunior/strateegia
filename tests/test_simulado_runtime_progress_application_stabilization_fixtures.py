import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_progress_application import (
    SimuladoRuntimeProgressApplicationService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_progress_applications import (
    api_readonly_fixture,
    audit_confirmation_missing_fixture,
    audit_trail_fixture,
    build_runtime_progress_application,
    explicit_apply_blocked_fixture,
    guardrail_not_eligible_fixture,
    idempotency_fixture,
    incomplete_guardrail_fixture,
    missing_runtime_guardrail_fixture,
    missing_runtime_policy_fixture,
    mixed_application_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_mutation_intents_fixture,
    proposed_surface_diffs_fixture,
    runtime_application_disabled_fixture,
)


FORBIDDEN_APPLICATION_KEYS = {
    "password_hash",
    "studyflow_session",
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
    "raw_runtime_block",
    "final_question_content",
    "final_explanation_content",
    "runtime_application_event",
    "final_pedagogical_update_event",
    "application_completed",
}

ALLOWED_INTENT_TYPES = {
    "progress_update_candidate",
    "ranking_update_candidate",
    "retention_update_candidate",
    "scheduler_update_candidate",
    "study_cycle_update_candidate",
    "curriculum_graph_update_candidate",
    "unknown",
}

ALLOWED_SURFACES = {
    "progress",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
    "unknown",
}

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


def test_runtime_progress_application_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    fixtures = [
        missing_runtime_guardrail_fixture(tmp_path / "missing"),
        guardrail_not_eligible_fixture(tmp_path / "not-eligible"),
        incomplete_guardrail_fixture(tmp_path / "incomplete"),
        missing_runtime_policy_fixture(tmp_path / "missing-policy"),
        runtime_application_disabled_fixture(tmp_path / "disabled"),
        explicit_apply_blocked_fixture(tmp_path / "explicit"),
        audit_confirmation_missing_fixture(tmp_path / "audit-missing"),
        mixed_application_fixture(tmp_path / "mixed"),
    ]

    results = [build_runtime_progress_application(fixture) for fixture in fixtures]
    assert results[0] is None
    for result in results[1:]:
        assert result is not None
        dumped = result.model_dump(mode="json")
        dumped_text = json.dumps(dumped, ensure_ascii=True)
        assert dumped["metadata"]["build_method"] == "heuristic_simulado_runtime_progress_application_builder"
        assert dumped["metadata"]["llm_used"] is False
        assert dumped["metadata"]["external_calls_used"] is False
        assert "data:image" not in dumped_text
        assert "http://" not in dumped_text
        assert "https://" not in dumped_text
        assert "/Users/" not in dumped_text
        assert "/private/" not in dumped_text


def test_runtime_progress_application_stabilization_covers_missing_and_blocked_states(tmp_path):
    missing = missing_runtime_guardrail_fixture(tmp_path / "missing")
    not_eligible = build_runtime_progress_application(guardrail_not_eligible_fixture(tmp_path / "not-eligible"))
    incomplete = build_runtime_progress_application(incomplete_guardrail_fixture(tmp_path / "incomplete"))
    missing_policy = build_runtime_progress_application(missing_runtime_policy_fixture(tmp_path / "missing-policy"))
    disabled = build_runtime_progress_application(runtime_application_disabled_fixture(tmp_path / "disabled"))
    explicit = build_runtime_progress_application(explicit_apply_blocked_fixture(tmp_path / "explicit"))
    audit_missing = build_runtime_progress_application(audit_confirmation_missing_fixture(tmp_path / "audit-missing"))

    assert build_runtime_progress_application(missing) is None

    assert not_eligible is not None
    assert not_eligible.application_status == "application_blocked"
    assert not_eligible.readiness_state == "blocked_by_guardrail_not_eligible"
    assert not_eligible.plan.can_apply_now is False
    assert "blocked_by_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}

    assert incomplete is not None
    assert incomplete.readiness_state == "blocked_by_incomplete_guardrail"
    assert "blocked_by_incomplete_guardrail" in {item.code for item in incomplete.blockers}

    assert missing_policy is not None
    assert missing_policy.readiness_state == "blocked_by_runtime_policy_missing"
    assert missing_policy.plan.requires_runtime_policy is True
    assert "blocked_by_runtime_policy_missing" in {item.code for item in missing_policy.blockers}

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_runtime_application_disabled"
    assert "blocked_by_runtime_application_disabled" in {item.code for item in disabled.blockers}

    assert explicit is not None
    assert explicit.readiness_state == "blocked_by_explicit_apply_not_allowed"
    assert "blocked_by_explicit_apply_not_allowed" in {item.code for item in explicit.blockers}

    assert audit_missing is not None
    assert audit_missing.readiness_state == "blocked_by_audit_confirmation_missing"
    assert "blocked_by_audit_confirmation_missing" in {item.code for item in audit_missing.blockers}


def test_runtime_progress_application_stabilization_preserves_planned_intents_and_surface_diffs(tmp_path):
    intents = build_runtime_progress_application(planned_mutation_intents_fixture(tmp_path / "intents"))
    diffs = build_runtime_progress_application(proposed_surface_diffs_fixture(tmp_path / "diffs"))

    assert intents is not None
    assert intents.planned_mutation_intents
    for item in intents.planned_mutation_intents:
        assert item.intent_type in ALLOWED_INTENT_TYPES
        assert item.proposed_surface in ALLOWED_SURFACES
        assert item.planned is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert diffs is not None
    assert diffs.proposed_surface_diffs
    for diff in diffs.proposed_surface_diffs:
        assert diff.surface_type in ALLOWED_SURFACES
        assert diff.applied is False
        assert diff.apply_allowed is False
        assert diff.diff_status in {"diff_planned_not_applied", "diff_blocked", "diff_needs_review"}
        assert isinstance(diff.before_summary, dict)
        assert isinstance(diff.proposed_after_summary, dict)


def test_runtime_progress_application_stabilization_preserves_audit_trail_and_plan_requirements(tmp_path):
    audit = build_runtime_progress_application(audit_trail_fixture(tmp_path / "audit"))
    assert audit is not None

    assert audit.plan.requires_runtime_policy in {False, True}
    assert audit.plan.requires_explicit_final_approval is True
    assert audit.plan.requires_audit_confirmation is True

    event_types = {item.event_type for item in audit.audit_trail}
    assert "application_plan_created" in event_types
    assert "no_runtime_application" in event_types
    assert any(code in event_types for code in {"application_blocked", "runtime_policy_missing"})


def test_runtime_progress_application_stabilization_preserves_mixed_blockers_and_no_public_exposure(tmp_path):
    mixed = build_runtime_progress_application(mixed_application_fixture(tmp_path / "mixed"))
    safe = build_runtime_progress_application(no_public_key_gabarito_safety_fixture(tmp_path / "safe"))

    assert mixed is not None
    blocker_codes = {item.code for item in mixed.blockers}
    assert "blocked_by_runtime_policy_missing" in blocker_codes
    assert "blocked_by_runtime_application_disabled" in blocker_codes
    assert len(mixed.warnings) >= 1

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped_text = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert safe.answer_key_publicly_exposed is False
    assert safe.gabarito_publicly_exposed is False
    for key in FORBIDDEN_APPLICATION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text


def test_runtime_progress_application_stabilization_preserves_no_runtime_application_and_no_mutation(tmp_path):
    application = build_runtime_progress_application(no_runtime_application_fixture(tmp_path / "application"))
    mutation = build_runtime_progress_application(no_runtime_mutation_fixture(tmp_path / "mutation"))

    assert application is not None
    assert application.application_mode in {"dry_run", "planned_only"}
    assert application.application_status != "applied"
    assert application.runtime_application_enabled is False
    assert application.runtime_application_applied is False
    assert application.no_runtime_application is True

    assert mutation is not None
    assert mutation.progress_mutation_enabled is False
    assert mutation.progress_mutation_applied is False
    assert mutation.ranking_update_enabled is False
    assert mutation.ranking_update_applied is False
    assert mutation.retention_update_enabled is False
    assert mutation.retention_update_applied is False
    assert mutation.scheduler_update_enabled is False
    assert mutation.scheduler_update_applied is False
    assert mutation.study_cycle_update_enabled is False
    assert mutation.study_cycle_update_applied is False
    assert mutation.curriculum_graph_update_enabled is False
    assert mutation.curriculum_graph_update_applied is False
    assert mutation.adaptive_tuning_enabled is False
    assert mutation.adaptive_tuning_applied is False
    assert mutation.no_progress_mutation is True
    assert mutation.no_ranking_update is True
    assert mutation.no_retention_update is True
    assert mutation.no_scheduler_update is True
    assert mutation.no_study_cycle_update is True
    assert mutation.no_curriculum_graph_update is True
    assert mutation.no_adaptive_tuning_update is True


def test_runtime_progress_application_stabilization_is_persistent_idempotent_and_non_mutating(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    repository = fixture.context.repository
    service = SimuladoRuntimeProgressApplicationService(repository)
    result = build_runtime_progress_application(fixture)
    assert result is not None
    runtime_guardrail = fixture.runtime_guardrail
    assert runtime_guardrail is not None

    before_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_integrated = repository.get_simulado_integrated_result_by_id(
        runtime_guardrail.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_application(runtime_guardrail.runtime_guardrail_id, user_id=fixture.context.user_id)
    second = service.build_application(runtime_guardrail.runtime_guardrail_id, user_id=fixture.context.user_id)
    by_source = repository.get_simulado_runtime_progress_application(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_runtime_progress_application_by_id(
        result.application_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_runtime_progress_applications(user_id=fixture.context.user_id)

    after_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_integrated = repository.get_simulado_integrated_result_by_id(
        runtime_guardrail.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_runtime_guardrail is not None and after_runtime_guardrail is not None
    assert before_integrated is not None and after_integrated is not None
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_runtime_progress_application_stabilization_api_owner_only_and_read_only_behaviour(tmp_path):
    owner_client, other_client, anonymous_client, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner_client, "owner")
    _register_and_login(other_client, "other")

    owner_fixture = api_readonly_fixture(tmp_path / "owner-fixture", user_id=owner_user_id, repository=repository)
    runtime_guardrail = owner_fixture.runtime_guardrail
    assert runtime_guardrail is not None

    missing_get = owner_client.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    )
    before = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=owner_user_id,
    )
    build = owner_client.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    loaded = owner_client.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    )
    application_id = build.json()["application_id"]
    by_id = owner_client.get(f"/api/simulado-progress-application/{application_id}")
    after = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=owner_user_id,
    )

    assert missing_get.status_code == 404
    assert before is not None and after is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
    assert anonymous_client.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    ).status_code == 401
    assert anonymous_client.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    ).status_code == 401
    assert other_client.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    ).status_code == 404
    assert other_client.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    ).status_code == 404
    assert other_client.get(f"/api/simulado-progress-application/{application_id}").status_code == 404
