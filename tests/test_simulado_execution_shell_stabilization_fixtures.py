import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_execution_shells import (
    approved_candidates_not_executable_fixture,
    assembly_json_keys,
    bounded_summary_fixture,
    build_execution_shell,
    disabled_flags_fixture,
    idempotency_fixture,
    missing_final_answer_keys_fixture,
    missing_final_approval_fixture,
    missing_final_explanations_fixture,
    missing_final_questions_fixture,
    mixed_approval_states_fixture,
    no_approved_candidates_fixture,
    no_attempt_submission_score_safety_fixture,
    ordering_fixture,
    user_scope_fixture,
)


FORBIDDEN_EXECUTION_SHELL_KEYS = {
    "real_student_attempt",
    "student_attempt",
    "attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "active_execution_session",
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


def assert_disabled_flags(shell) -> None:
    assert shell.execution_shell_active is False
    assert shell.execution_started is False
    assert shell.attempt_created is False
    assert shell.student_submission_enabled is False
    assert shell.correction_enabled is False
    assert shell.scoring_enabled is False
    assert shell.progress_mutation_enabled is False
    assert shell.no_student_attempt_created is True
    assert shell.no_answer_submission_created is True
    assert shell.no_correction_result_created is True
    assert shell.no_score_created is True


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_execution_shell_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = no_approved_candidates_fixture(tmp_path / "first")
    second = no_approved_candidates_fixture(tmp_path / "second")

    assert first.final_approval_artifact is not None
    assert second.final_approval_artifact is not None
    assert (
        first.final_approval_artifact.approval_artifact_id
        == second.final_approval_artifact.approval_artifact_id
    )
    json.dumps(first.final_approval_artifact.model_dump(mode="json"), ensure_ascii=True)
    shell = build_execution_shell(first)
    assert shell is not None
    json.dumps(shell.model_dump(mode="json"), ensure_ascii=True)


def test_missing_final_approval_fixture_is_safe_and_creates_no_shell(tmp_path):
    fixture = missing_final_approval_fixture(tmp_path)
    result = build_execution_shell(fixture)

    assert result is None
    assert fixture.context.repository.list_user_simulado_execution_shells(user_id=fixture.context.user_id) == []


def test_no_approved_candidates_and_approved_but_not_executable_scenarios_stay_non_active(tmp_path):
    no_approved = build_execution_shell(no_approved_candidates_fixture(tmp_path / "no-approved"))
    approved = build_execution_shell(
        approved_candidates_not_executable_fixture(tmp_path / "approved-not-executable")
    )

    assert no_approved is not None
    assert approved is not None

    assert no_approved.approved_candidate_count == 0
    assert no_approved.executable_candidate_count == 0
    assert no_approved.readiness_state in {
        "blocked_by_no_approved_candidates",
        "needs_future_activation_review",
    }
    assert "blocked_by_no_approved_candidates" in {item.code for item in no_approved.blockers}
    assert_disabled_flags(no_approved)

    assert approved.approved_candidate_count > 0
    assert approved.executable_candidate_count == 0
    assert all(item.can_be_presented_to_student is False for item in approved.candidate_records)
    assert all(item.can_accept_answer is False for item in approved.candidate_records)
    assert all(item.can_be_corrected is False for item in approved.candidate_records)
    assert all(item.can_be_scored is False for item in approved.candidate_records)
    assert_disabled_flags(approved)


def test_missing_final_content_blockers_and_mixed_approval_states_remain_conservative(tmp_path):
    missing_questions = build_execution_shell(missing_final_questions_fixture(tmp_path / "questions"))
    missing_answer_keys = build_execution_shell(
        missing_final_answer_keys_fixture(tmp_path / "answer-keys")
    )
    missing_explanations = build_execution_shell(
        missing_final_explanations_fixture(tmp_path / "explanations")
    )
    mixed = build_execution_shell(mixed_approval_states_fixture(tmp_path / "mixed"))

    assert missing_questions is not None
    assert missing_answer_keys is not None
    assert missing_explanations is not None
    assert mixed is not None

    assert "blocked_by_missing_final_questions" in {item.code for item in missing_questions.blockers}
    assert all(item.has_final_question is False for item in missing_questions.candidate_records)

    assert "blocked_by_missing_final_answer_keys" in {item.code for item in missing_answer_keys.blockers}
    assert all(item.has_final_answer_key is False for item in missing_answer_keys.candidate_records)
    assert missing_answer_keys.correction_enabled is False
    assert missing_answer_keys.scoring_enabled is False

    assert "blocked_by_missing_final_explanations" in {item.code for item in missing_explanations.blockers}
    assert all(item.has_final_explanation is False for item in missing_explanations.candidate_records)

    assert mixed.approved_candidate_count >= 1
    assert mixed.blocked_candidate_count >= 1
    assert mixed.needs_review_candidate_count >= 1
    assert mixed.executable_candidate_count == 0
    assert_disabled_flags(mixed)


def test_candidate_ordering_and_disabled_flags_are_stable(tmp_path):
    ordering = ordering_fixture(tmp_path / "ordering")
    first = build_execution_shell(ordering)
    second = build_execution_shell(ordering)
    disabled = build_execution_shell(disabled_flags_fixture(tmp_path / "disabled"))

    assert first is not None
    assert second is not None
    assert disabled is not None

    first_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in first.candidate_records]
    second_pairs = [(item.source_candidate_id, item.order_index, item.display_position) for item in second.candidate_records]

    assert first_pairs == second_pairs
    assert [item[1] for item in first_pairs] == list(range(len(first_pairs)))
    assert [item[2] for item in first_pairs] == list(range(1, len(first_pairs) + 1))
    assert first.operational_summary.candidate_ordering_strategy
    assert_disabled_flags(disabled)


def test_no_attempt_submission_score_fixture_and_no_leakage_assertions_hold(tmp_path):
    shell = build_execution_shell(no_attempt_submission_score_safety_fixture(tmp_path / "safety"))
    bounded = build_execution_shell(bounded_summary_fixture(tmp_path / "bounded"))

    assert shell is not None
    assert bounded is not None

    dumped_payload = shell.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    json.dumps(bounded.model_dump(mode="json"), ensure_ascii=True)
    for key in FORBIDDEN_EXECUTION_SHELL_KEYS:
        assert key not in dumped_keys
    assert_no_leakage(dumped)


def test_persistence_idempotency_api_scope_and_read_only_behavior(tmp_path):
    fixture = idempotency_fixture(tmp_path / "repo")
    first = build_execution_shell(fixture)
    second = build_execution_shell(fixture)

    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_execution_shell(
        fixture.final_approval_artifact.approval_artifact_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_execution_shell_by_id(
        first.execution_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_execution_shells(
        user_id=fixture.context.user_id
    )

    assert by_source is not None
    assert by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    owner, other, anonymous, repository = create_clients(tmp_path / "api")
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture = idempotency_fixture(
        tmp_path / "api-owner",
        user_id=owner_user_id,
        repository=repository,
    )
    owner_artifact = owner_fixture.final_approval_artifact
    assert owner_artifact is not None

    missing = owner.get(f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell")
    before_approval = repository.get_simulado_final_approval_artifact_by_id(
        owner_artifact.approval_artifact_id,
        user_id=owner_user_id,
    )
    build = owner.post(f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell/build")
    loaded = owner.get(f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell")
    execution_shell_id = build.json()["execution_shell_id"]
    by_shell_id = owner.get(f"/api/simulado-execution-shell/{execution_shell_id}")
    after_approval = repository.get_simulado_final_approval_artifact_by_id(
        owner_artifact.approval_artifact_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_shell_id.status_code == 200
    assert before_approval is not None
    assert after_approval is not None
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert build.json() == loaded.json() == by_shell_id.json()

    assert anonymous.post(
        f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-execution-shell/{execution_shell_id}").status_code == 401

    assert other.post(
        f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-approval/{owner_artifact.approval_artifact_id}/execution-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-execution-shell/{execution_shell_id}").status_code == 404


def test_user_scope_fixture_preserves_owner_only_visibility(tmp_path):
    owner_fixture, other_fixture = user_scope_fixture(tmp_path)
    owner_shell = build_execution_shell(owner_fixture)
    other_shell = build_execution_shell(other_fixture)

    assert owner_shell is not None
    assert other_shell is not None
    assert owner_shell.user_id != other_shell.user_id
    assert (
        owner_fixture.context.repository.get_simulado_execution_shell(
            owner_fixture.final_approval_artifact.approval_artifact_id,
            user_id=owner_fixture.context.user_id,
        )
        is not None
    )
    assert (
        owner_fixture.context.repository.get_simulado_execution_shell(
            other_fixture.final_approval_artifact.approval_artifact_id,
            user_id=other_fixture.context.user_id,
        )
        is not None
    )
    assert owner_shell.source_final_approval_artifact_id == owner_fixture.final_approval_artifact.approval_artifact_id
    assert other_shell.source_final_approval_artifact_id == other_fixture.final_approval_artifact.approval_artifact_id
