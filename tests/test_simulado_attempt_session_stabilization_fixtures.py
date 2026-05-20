import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_attempt_sessions import (
    assembly_json_keys,
    bounded_summary_fixture,
    build_attempt_session,
    disabled_flags_fixture,
    idempotency_fixture,
    inactive_execution_shell_fixture,
    missing_execution_shell_fixture,
    no_answer_submission_safety_fixture,
    no_correction_scoring_safety_fixture,
    no_executable_candidates_fixture,
    no_progress_mutation_fixture,
    ordering_stability_fixture,
    prepared_items_non_submittable_fixture,
    timing_placeholders_fixture,
    user_scope_fixture,
)


FORBIDDEN_ATTEMPT_SESSION_KEYS = {
    "answer_submission",
    "submitted_answers",
    "selected_option",
    "typed_answer",
    "answer_payload",
    "answer_received_at",
    "submission_id",
    "submitted_at",
    "correction_result",
    "correction_status",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "score",
    "grade",
    "simulado_result",
    "score_rule",
    "correction_rule",
    "result_id",
    "final_question_content",
    "final_answer_key_content",
    "final_explanation_content",
    "completed_at",
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


def assert_disabled_flags(session) -> None:
    assert session.session_prepared is True
    assert session.session_active is False
    assert session.session_submitted is False
    assert session.session_completed is False
    assert session.answer_submission_enabled is False
    assert session.correction_enabled is False
    assert session.scoring_enabled is False
    assert session.progress_mutation_enabled is False
    assert session.no_answer_submission_created is True
    assert session.no_correction_result_created is True
    assert session.no_score_created is True
    assert session.no_progress_mutation is True


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_attempt_session_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = inactive_execution_shell_fixture(tmp_path / "first")
    second = inactive_execution_shell_fixture(tmp_path / "second")

    assert first.execution_shell is not None
    assert second.execution_shell is not None
    assert first.execution_shell.execution_shell_id == second.execution_shell.execution_shell_id
    json.dumps(first.execution_shell.model_dump(mode="json"), ensure_ascii=True)
    session = build_attempt_session(first)
    assert session is not None
    json.dumps(session.model_dump(mode="json"), ensure_ascii=True)


def test_missing_execution_shell_fixture_is_safe_and_creates_no_session(tmp_path):
    fixture = missing_execution_shell_fixture(tmp_path)
    result = build_attempt_session(fixture)

    assert result is None
    assert fixture.context.repository.list_user_simulado_attempt_sessions(user_id=fixture.context.user_id) == []


def test_inactive_and_no_executable_attempt_session_scenarios_stay_non_submittable(tmp_path):
    inactive = build_attempt_session(inactive_execution_shell_fixture(tmp_path / "inactive"))
    no_executable = build_attempt_session(no_executable_candidates_fixture(tmp_path / "no-executable"))

    assert inactive is not None
    assert no_executable is not None

    assert inactive.session_active is False
    assert inactive.answer_submission_enabled is False
    assert inactive.correction_enabled is False
    assert inactive.scoring_enabled is False
    assert_disabled_flags(inactive)

    assert no_executable.readiness_state in {
        "blocked_by_no_executable_items",
        "needs_future_submission_foundation",
    }
    assert no_executable.status in {"attempt_session_blocked", "attempt_session_needs_review"}
    assert all(item.can_accept_answer is False for item in no_executable.items)


def test_prepared_items_and_timing_placeholders_remain_inactive(tmp_path):
    prepared = build_attempt_session(prepared_items_non_submittable_fixture(tmp_path / "prepared"))
    timing = build_attempt_session(timing_placeholders_fixture(tmp_path / "timing"))

    assert prepared is not None
    assert timing is not None

    assert prepared.items
    assert all(item.can_accept_answer is False for item in prepared.items)
    assert all(item.has_submitted_answer is False for item in prepared.items)
    assert all(item.can_be_corrected is False for item in prepared.items)
    assert all(item.can_be_scored is False for item in prepared.items)

    assert timing.timing_plan is not None
    assert timing.timing_plan.timer_active is False
    assert timing.timing_plan.timer_started_at is None
    assert timing.timing_plan.timer_completed_at is None


def test_disabled_flags_submission_safety_correction_safety_and_no_progress_mutation_hold(tmp_path):
    disabled = build_attempt_session(disabled_flags_fixture(tmp_path / "disabled"))
    no_answers = build_attempt_session(no_answer_submission_safety_fixture(tmp_path / "no-answers"))
    no_correction = build_attempt_session(no_correction_scoring_safety_fixture(tmp_path / "no-correction"))

    fixture = no_progress_mutation_fixture(tmp_path / "no-progress")
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)
    before_shell = fixture.context.repository.get_simulado_execution_shell_by_id(
        fixture.execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    no_progress = build_attempt_session(fixture)
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)
    after_shell = fixture.context.repository.get_simulado_execution_shell_by_id(
        fixture.execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )

    assert disabled is not None
    assert no_answers is not None
    assert no_correction is not None
    assert no_progress is not None

    assert_disabled_flags(disabled)
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
    assert before_shell is not None
    assert after_shell is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")

    for session in (no_answers, no_correction):
        dumped_payload = session.model_dump(mode="json")
        dumped = json.dumps(dumped_payload, ensure_ascii=True)
        dumped_keys = assembly_json_keys(dumped_payload)
        for key in FORBIDDEN_ATTEMPT_SESSION_KEYS:
            assert key not in dumped_keys
        assert_no_leakage(dumped)


def test_ordering_idempotency_api_scope_and_read_only_behavior(tmp_path):
    ordering = ordering_stability_fixture(tmp_path / "ordering")
    first = build_attempt_session(ordering)
    second = build_attempt_session(ordering)

    assert first is not None
    assert second is not None

    first_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in first.items]
    second_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in second.items]
    assert first_pairs == second_pairs

    fixture = idempotency_fixture(tmp_path / "repo")
    repo_first = build_attempt_session(fixture)
    repo_second = build_attempt_session(fixture)
    assert repo_first is not None
    assert repo_second is not None

    by_source = fixture.context.repository.get_simulado_attempt_session(
        fixture.execution_shell.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_attempt_session_by_id(
        repo_first.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_attempt_sessions(user_id=fixture.context.user_id)

    assert by_source is not None
    assert by_id is not None
    assert repo_first.model_dump(mode="json") == repo_second.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == repo_first.model_dump(mode="json")
    assert len(listed) == 1

    owner, other, anonymous, repository = create_clients(tmp_path / "api")
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture = idempotency_fixture(
        tmp_path / "api-owner",
        user_id=owner_user_id,
        repository=repository,
    )
    owner_shell = owner_fixture.execution_shell
    assert owner_shell is not None

    missing = owner.get(f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session")
    before_shell = repository.get_simulado_execution_shell_by_id(
        owner_shell.execution_shell_id,
        user_id=owner_user_id,
    )
    build = owner.post(f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session/build")
    loaded = owner.get(f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session")
    attempt_session_id = build.json()["attempt_session_id"]
    by_session_id = owner.get(f"/api/simulado-attempt-session/{attempt_session_id}")
    after_shell = repository.get_simulado_execution_shell_by_id(
        owner_shell.execution_shell_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_session_id.status_code == 200
    assert before_shell is not None
    assert after_shell is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert build.json() == loaded.json() == by_session_id.json()

    assert anonymous.post(
        f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-attempt-session/{attempt_session_id}").status_code == 401

    assert other.post(
        f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-execution-shell/{owner_shell.execution_shell_id}/attempt-session"
    ).status_code == 404
    assert other.get(f"/api/simulado-attempt-session/{attempt_session_id}").status_code == 404


def test_user_scope_fixture_preserves_owner_only_visibility(tmp_path):
    owner_fixture, other_fixture = user_scope_fixture(tmp_path)
    owner_session = build_attempt_session(owner_fixture)
    other_session = build_attempt_session(other_fixture)

    assert owner_session is not None
    assert other_session is not None
    assert owner_session.user_id != other_session.user_id
    assert (
        owner_fixture.context.repository.get_simulado_attempt_session(
            owner_fixture.execution_shell.execution_shell_id,
            user_id=owner_fixture.context.user_id,
        )
        is not None
    )
    assert (
        other_fixture.context.repository.get_simulado_attempt_session(
            other_fixture.execution_shell.execution_shell_id,
            user_id=other_fixture.context.user_id,
        )
        is not None
    )
