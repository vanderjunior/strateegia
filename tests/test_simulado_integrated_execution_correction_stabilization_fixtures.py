import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_integrated_execution_correction import (
    SimuladoIntegratedExecutionCorrectionService,
)
from tests.fixtures.simulado_integrated_execution_corrections import (
    api_readonly_fixture,
    build_integrated_result,
    chain_summary_shape_fixture,
    complete_chain_readonly_fixture,
    correction_summary_shape_fixture,
    execution_summary_shape_fixture,
    idempotency_fixture,
    incomplete_correction_fixture,
    incomplete_score_fixture,
    missing_answer_key_boundary_fixture,
    missing_answer_submission_fixture,
    missing_attempt_session_fixture,
    missing_correction_result_fixture,
    missing_correction_shell_fixture,
    missing_progress_guardrail_fixture,
    missing_score_result_fixture,
    mixed_blockers_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    no_scoreable_items_fixture,
    progress_guardrail_not_eligible_fixture,
    progress_guardrail_summary_shape_fixture,
    runtime_mutation_disabled_fixture,
    score_summary_shape_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_INTEGRATED_KEYS = {
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
    "runtime_progress_application",
    "pedagogical_update_event",
    "final_pedagogical_update_event",
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


def test_simulado_integrated_execution_correction_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    fixtures = [
        missing_attempt_session_fixture(tmp_path / "missing-attempt"),
        missing_answer_submission_fixture(tmp_path / "missing-submission"),
        missing_correction_shell_fixture(tmp_path / "missing-shell"),
        missing_answer_key_boundary_fixture(tmp_path / "missing-boundary"),
        missing_correction_result_fixture(tmp_path / "missing-correction"),
        missing_score_result_fixture(tmp_path / "missing-score"),
        missing_progress_guardrail_fixture(tmp_path / "missing-guardrail"),
        complete_chain_readonly_fixture(tmp_path / "complete"),
        no_scoreable_items_fixture(tmp_path / "no-scoreable"),
        mixed_blockers_fixture(tmp_path / "mixed"),
    ]

    results = [build_integrated_result(fixture) for fixture in fixtures]
    assert results[0] is None
    for result in results[1:]:
        assert result is not None
        dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
        assert isinstance(dumped, str)
        assert "data:image" not in dumped
        assert "http://" not in dumped
        assert "https://" not in dumped


def test_simulado_integrated_execution_correction_stabilization_covers_missing_chain_stages(tmp_path):
    expectations = [
        (
            build_integrated_result(missing_answer_submission_fixture(tmp_path / "submission")),
            "answer_submission_available",
            "blocked_by_missing_answer_submission",
        ),
        (
            build_integrated_result(missing_correction_shell_fixture(tmp_path / "shell")),
            "correction_shell_available",
            "blocked_by_missing_correction_shell",
        ),
        (
            build_integrated_result(missing_answer_key_boundary_fixture(tmp_path / "boundary")),
            "answer_key_boundary_available",
            "blocked_by_missing_answer_key_boundary",
        ),
        (
            build_integrated_result(missing_correction_result_fixture(tmp_path / "correction")),
            "correction_result_available",
            "blocked_by_missing_correction_result",
        ),
        (
            build_integrated_result(missing_score_result_fixture(tmp_path / "score")),
            "score_result_available",
            "blocked_by_missing_score_result",
        ),
        (
            build_integrated_result(missing_progress_guardrail_fixture(tmp_path / "guardrail")),
            "progress_guardrail_available",
            "blocked_by_missing_progress_guardrail",
        ),
    ]

    for result, availability_field, blocker_code in expectations:
        assert result is not None
        assert getattr(result.chain_summary, availability_field) is False
        assert result.chain_summary.chain_complete is False
        assert blocker_code in {item.code for item in result.blockers}
        assert result.progress_mutation_applied is False
        assert result.ranking_update_applied is False
        assert result.retention_update_applied is False
        assert result.scheduler_update_applied is False
        assert result.study_cycle_update_applied is False
        assert result.curriculum_graph_update_applied is False
        assert result.adaptive_tuning_applied is False


def test_simulado_integrated_execution_correction_stabilization_covers_complete_chain_incomplete_states_and_runtime_disabled(
    tmp_path,
):
    complete = build_integrated_result(complete_chain_readonly_fixture(tmp_path / "complete"))
    incomplete_correction = build_integrated_result(incomplete_correction_fixture(tmp_path / "incomplete-correction"))
    incomplete_score = build_integrated_result(incomplete_score_fixture(tmp_path / "incomplete-score"))
    not_eligible = build_integrated_result(progress_guardrail_not_eligible_fixture(tmp_path / "not-eligible"))
    runtime_disabled = build_integrated_result(runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled"))

    assert complete is not None
    assert complete.chain_summary.chain_complete is True
    assert complete.progress_mutation_applied is False
    assert complete.ranking_update_applied is False
    assert complete.retention_update_applied is False
    assert complete.scheduler_update_applied is False
    assert complete.study_cycle_update_applied is False
    assert complete.curriculum_graph_update_applied is False
    assert complete.adaptive_tuning_applied is False

    assert incomplete_correction is not None
    assert incomplete_correction.correction_summary.correction_complete is False
    assert "blocked_by_incomplete_correction" in {item.code for item in incomplete_correction.blockers}

    assert incomplete_score is not None
    assert incomplete_score.score_summary.score_complete is False
    assert "blocked_by_incomplete_score" in {item.code for item in incomplete_score.blockers}

    assert not_eligible is not None
    assert not_eligible.progress_guardrail_summary.mutation_blocked is True
    assert "blocked_by_progress_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}

    assert runtime_disabled is not None
    assert "blocked_by_runtime_mutation_disabled" in {item.code for item in runtime_disabled.blockers}
    assert runtime_disabled.progress_mutation_enabled is False
    assert runtime_disabled.ranking_mutation_enabled is False
    assert runtime_disabled.retention_mutation_enabled is False
    assert runtime_disabled.scheduler_mutation_enabled is False
    assert runtime_disabled.study_cycle_mutation_enabled is False
    assert runtime_disabled.curriculum_graph_mutation_enabled is False
    assert runtime_disabled.adaptive_tuning_enabled is False
    assert runtime_disabled.no_progress_mutation is True
    assert runtime_disabled.no_ranking_update is True
    assert runtime_disabled.no_retention_update is True
    assert runtime_disabled.no_scheduler_update is True
    assert runtime_disabled.no_study_cycle_update is True
    assert runtime_disabled.no_curriculum_graph_update is True
    assert runtime_disabled.no_adaptive_tuning_update is True


def test_simulado_integrated_execution_correction_stabilization_preserves_summary_shapes(tmp_path):
    chain = build_integrated_result(chain_summary_shape_fixture(tmp_path / "chain"))
    execution = build_integrated_result(execution_summary_shape_fixture(tmp_path / "execution"))
    correction = build_integrated_result(correction_summary_shape_fixture(tmp_path / "correction"))
    score = build_integrated_result(score_summary_shape_fixture(tmp_path / "score"))
    guardrail = build_integrated_result(progress_guardrail_summary_shape_fixture(tmp_path / "guardrail"))

    assert chain is not None
    assert chain.chain_summary.attempt_session_available is True
    assert isinstance(chain.chain_summary.missing_artifacts, list)
    assert isinstance(chain.chain_summary.chain_complete, bool)

    assert execution is not None
    assert isinstance(execution.execution_summary.session_prepared, bool)
    assert isinstance(execution.execution_summary.session_active, bool)
    assert isinstance(execution.execution_summary.session_submitted, bool)
    assert isinstance(execution.execution_summary.session_completed, bool)
    assert execution.execution_summary.submitted_answer_count >= 0

    assert correction is not None
    assert correction.correction_summary.total_answer_records >= 0
    assert correction.correction_summary.blocked_answer_count >= 0
    assert correction.correction_summary.needs_review_answer_count >= 0

    assert score is not None
    assert score.score_summary.raw_score >= 0.0
    assert score.score_summary.max_score >= 0.0
    assert score.score_summary.scoreable_item_count >= 0
    assert score.score_summary.scored_item_count >= 0

    assert guardrail is not None
    assert guardrail.progress_guardrail_summary.candidate_target_count >= 0
    assert guardrail.progress_guardrail_summary.update_applied_count == 0
    assert isinstance(guardrail.progress_guardrail_summary.mutation_blocked, bool)


def test_simulado_integrated_execution_correction_stabilization_preserves_mixed_blockers_and_no_public_exposure(
    tmp_path,
):
    mixed = build_integrated_result(mixed_blockers_fixture(tmp_path / "mixed"))
    safe = build_integrated_result(no_public_key_gabarito_safety_fixture(tmp_path / "safe"))
    assert mixed is not None
    assert safe is not None

    mixed_codes = {item.code for item in mixed.blockers}
    assert "blocked_by_runtime_mutation_disabled" in mixed_codes
    assert "blocked_by_progress_guardrail_not_eligible" in mixed_codes
    assert len(mixed.warnings) >= 1

    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert safe.answer_key_publicly_exposed is False
    assert safe.gabarito_publicly_exposed is False
    for key in FORBIDDEN_INTEGRATED_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "raw_runtime_block" not in dumped


def test_simulado_integrated_execution_correction_stabilization_is_persistent_idempotent_and_non_mutating(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    repository = fixture.context.repository
    service = SimuladoIntegratedExecutionCorrectionService(repository)
    result = build_integrated_result(fixture)
    assert result is not None
    attempt_session = fixture.attempt_session
    assert attempt_session is not None

    before_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_submission = repository.get_simulado_answer_submission_by_id(
        fixture.answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    before_shell = repository.get_simulado_correction_shell_by_id(
        fixture.correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = repository.get_simulado_answer_key_boundary_by_id(
        fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction = repository.get_simulado_correction_result_by_id(
        fixture.correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_score = repository.get_simulado_score_result_by_id(
        fixture.score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = repository.get_simulado_progress_guardrail_by_id(
        fixture.progress_guardrail.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_integrated_result(attempt_session.attempt_session_id, user_id=fixture.context.user_id)
    second = service.build_integrated_result(attempt_session.attempt_session_id, user_id=fixture.context.user_id)
    by_source = repository.get_simulado_integrated_result(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_integrated_result_by_id(
        result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_integrated_results(user_id=fixture.context.user_id)

    after_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_submission = repository.get_simulado_answer_submission_by_id(
        fixture.answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    after_shell = repository.get_simulado_correction_shell_by_id(
        fixture.correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = repository.get_simulado_answer_key_boundary_by_id(
        fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction = repository.get_simulado_correction_result_by_id(
        fixture.correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_score = repository.get_simulado_score_result_by_id(
        fixture.score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_progress_guardrail_by_id(
        fixture.progress_guardrail.progress_guardrail_id,
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
    assert before_attempt is not None and after_attempt is not None
    assert before_submission is not None and after_submission is not None
    assert before_shell is not None and after_shell is not None
    assert before_boundary is not None and after_boundary is not None
    assert before_correction is not None and after_correction is not None
    assert before_score is not None and after_score is not None
    assert before_guardrail is not None and after_guardrail is not None
    assert before_attempt.model_dump(mode="json") == after_attempt.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction.model_dump(mode="json") == after_correction.model_dump(mode="json")
    assert before_score.model_dump(mode="json") == after_score.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_simulado_integrated_execution_correction_stabilization_api_owner_only_and_read_only(tmp_path):
    owner, other, anonymous, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    fixture = api_readonly_fixture(tmp_path / "owner", user_id=owner_user_id, repository=repository)
    attempt_session = fixture.attempt_session
    assert attempt_session is not None

    missing = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    build = owner.post(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build")
    loaded = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    integrated_result_id = build.json()["integrated_result_id"]
    by_id = owner.get(f"/api/simulado-integrated-result/{integrated_result_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert anonymous.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-integrated-result/{integrated_result_id}").status_code == 401
    assert other.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result"
    ).status_code == 404
    assert other.get(f"/api/simulado-integrated-result/{integrated_result_id}").status_code == 404

    before_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )
    loaded_again = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    after_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )
    assert loaded_again.status_code == 200
    assert before_attempt is not None and after_attempt is not None
    assert before_attempt.model_dump(mode="json") == after_attempt.model_dump(mode="json")


def test_simulado_integrated_execution_correction_stabilization_runtime_preservation_and_no_leakage(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_mutation_fixture(tmp_path, repository=repository)
    result = build_integrated_result(fixture)
    assert result is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert result.metadata.get("llm_used") is False
    assert result.metadata.get("external_calls_used") is False
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "runtime_progress_application" not in dumped_keys
    assert "pedagogical_update_event" not in dumped_keys
    assert "final_pedagogical_update_event" not in dumped_keys

