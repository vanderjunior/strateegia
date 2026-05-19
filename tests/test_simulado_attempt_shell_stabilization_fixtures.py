import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_attempt_shells import (
    all_blocked_candidates_assembly_fixture,
    assembly_json_keys,
    bounded_summary_fixture,
    build_attempt_shell,
    idempotency_fixture,
    mixed_ready_blocked_review_assembly_fixture,
    missing_final_answer_keys_fixture,
    missing_final_explanations_fixture,
    missing_final_questions_fixture,
    no_attempt_submission_score_safety_fixture,
    non_executable_assembly_fixture,
    ready_candidates_not_executable_fixture,
    review_required_assembly_fixture,
    unsupported_candidate_assembly_fixture,
    user_scope_fixture,
    zero_candidates_assembly_fixture,
)


FORBIDDEN_EXECUTION_KEYS = {
    "real_student_attempt",
    "student_attempt",
    "attempt",
    "answer_submission",
    "submitted_answers",
    "correction_result",
    "score",
    "grade",
    "simulado_result",
    "executable_question",
    "executable_simulado",
    "final_question",
    "final_answer_key",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation",
    "correction_rule",
    "auto_correction",
    "score_rule",
    "scoring_result",
    "exam_session",
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


def assert_disabled_flags(shell):
    assert shell.execution_enabled is False
    assert shell.correction_enabled is False
    assert shell.scoring_enabled is False
    assert shell.student_submission_enabled is False
    assert shell.progress_mutation_enabled is False
    assert shell.no_student_attempt_created is True
    assert shell.no_answer_submission_enabled is True
    assert shell.no_correction_result_created is True
    assert shell.no_score_created is True
    assert shell.requires_human_finalization is True


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_simulado_attempt_shell_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = non_executable_assembly_fixture(tmp_path / "first")
    second = non_executable_assembly_fixture(tmp_path / "second")

    assert first.assembly.assembly_id == second.assembly.assembly_id
    assert first.assembly.source_simulado_blueprint_id == second.assembly.source_simulado_blueprint_id
    json.dumps(first.assembly.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(build_attempt_shell(first).model_dump(mode="json"), ensure_ascii=True)


def test_non_executable_review_required_and_ready_candidates_fixtures_remain_non_executable(tmp_path):
    non_exec = build_attempt_shell(non_executable_assembly_fixture(tmp_path / "non-exec"))
    ready = build_attempt_shell(ready_candidates_not_executable_fixture(tmp_path / "ready"))
    review = build_attempt_shell(review_required_assembly_fixture(tmp_path / "review"))

    assert non_exec is not None
    assert ready is not None
    assert review is not None

    non_exec_blockers = {item.code for item in non_exec.blockers}
    review_blockers = {item.code for item in review.blockers}

    assert_disabled_flags(non_exec)
    assert non_exec.readiness_state in {
        "blocked_by_non_final_assembly",
        "blocked_by_review_required",
        "needs_human_finalization",
    }
    assert "blocked_by_non_final_assembly" in non_exec_blockers

    assert ready.review_ready_candidates > 0
    assert ready.executable_questions_count == 0
    assert_disabled_flags(ready)

    assert review.requires_human_finalization is True
    assert review.readiness_state in {"blocked_by_review_required", "needs_human_finalization"}
    assert "blocked_by_review_required" in review_blockers or review.readiness_state == "needs_human_finalization"


def test_missing_final_content_and_zero_or_blocked_candidate_fixtures_preserve_blockers(tmp_path):
    missing_questions = build_attempt_shell(missing_final_questions_fixture(tmp_path / "questions"))
    missing_answers = build_attempt_shell(missing_final_answer_keys_fixture(tmp_path / "answers"))
    missing_explanations = build_attempt_shell(missing_final_explanations_fixture(tmp_path / "explanations"))
    zero = build_attempt_shell(zero_candidates_assembly_fixture(tmp_path / "zero"))
    all_blocked = build_attempt_shell(all_blocked_candidates_assembly_fixture(tmp_path / "blocked"))

    assert missing_questions is not None
    assert missing_answers is not None
    assert missing_explanations is not None
    assert zero is not None
    assert all_blocked is not None

    assert "blocked_by_unfinalized_questions" in {item.code for item in missing_questions.blockers}
    assert "blocked_by_missing_final_answer_keys" in {item.code for item in missing_answers.blockers}
    assert missing_answers.correction_enabled is False
    assert missing_answers.scoring_enabled is False
    assert "blocked_by_missing_final_explanations" in {item.code for item in missing_explanations.blockers}

    assert zero.readiness_state == "blocked_by_insufficient_question_count"
    assert zero.executable_questions_count == 0

    assert all_blocked.review_ready_candidates == 0
    assert all_blocked.blocked_candidates > 0
    assert all_blocked.execution_enabled is False


def test_mixed_and_unsupported_fixtures_keep_counts_stable_without_execution(tmp_path):
    mixed = build_attempt_shell(mixed_ready_blocked_review_assembly_fixture(tmp_path / "mixed"))
    unsupported = build_attempt_shell(unsupported_candidate_assembly_fixture(tmp_path / "unsupported"))

    assert mixed is not None
    assert unsupported is not None

    assert mixed.total_candidates >= 3
    assert mixed.review_ready_candidates > 0
    assert mixed.blocked_candidates > 0
    assert mixed.needs_review_candidates > 0
    assert mixed.executable_questions_count == 0
    assert_disabled_flags(mixed)

    unsupported_codes = {item.code for item in unsupported.blockers}
    assert unsupported.execution_enabled is False
    assert "blocked_by_unsupported_format" in unsupported_codes or unsupported.readiness_state in {
        "blocked_by_unsupported_format",
        "blocked_by_insufficient_question_count",
    }


def test_no_attempt_submission_score_and_bounded_summary_safeguards_hold(tmp_path):
    safety = build_attempt_shell(no_attempt_submission_score_safety_fixture(tmp_path / "safety"))
    bounded = build_attempt_shell(bounded_summary_fixture(tmp_path / "bounded"))

    assert safety is not None
    assert bounded is not None

    dumped = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped)

    assert_disabled_flags(safety)
    for key in FORBIDDEN_EXECUTION_KEYS:
        assert key not in dumped_keys
    assert_no_leakage(dumped_text)

    bounded_text = json.dumps(bounded.model_dump(mode="json"), ensure_ascii=True)
    assert_no_leakage(bounded_text)


def test_attempt_shell_persistence_and_idempotency_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    first = build_attempt_shell(fixture)
    second = build_attempt_shell(fixture)
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_attempt_shell(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_attempt_shell_by_id(
        first.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_attempt_shells(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1


def test_attempt_shell_api_owner_only_read_only_and_user_scope_are_preserved(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture, _ = user_scope_fixture(tmp_path / "scope", repository=repository)
    owner_fixture = non_executable_assembly_fixture(
        tmp_path / "owner-api",
        user_id=owner_user_id,
        repository=repository,
    )
    assembly_id = owner_fixture.assembly.assembly_id

    missing = owner.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell")
    before_list = repository.list_user_simulado_attempt_shells(user_id=owner_user_id)
    build = owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build")
    attempt_shell_id = build.json()["attempt_shell_id"]
    after_build_list = repository.list_user_simulado_attempt_shells(user_id=owner_user_id)
    loaded = owner.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell")
    by_id = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}")
    after_get_list = repository.list_user_simulado_attempt_shells(user_id=owner_user_id)
    dumped = json.dumps(by_id.json(), ensure_ascii=True)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build").json() == build.json()
    assert anonymous.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build").status_code == 401
    assert anonymous.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell").status_code == 401
    assert anonymous.get(f"/api/simulado-attempt-shell/{attempt_shell_id}").status_code == 401
    assert other.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build").status_code == 404
    assert other.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell").status_code == 404
    assert other.get(f"/api/simulado-attempt-shell/{attempt_shell_id}").status_code == 404
    assert_no_leakage(dumped)


def test_attempt_shell_build_and_get_do_not_mutate_source_assembly(tmp_path):
    fixture = non_executable_assembly_fixture(tmp_path)
    before = fixture.context.repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    built = build_attempt_shell(fixture)
    assert built is not None
    loaded = fixture.context.service.get_attempt_shell(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.service.get_attempt_shell_by_id(
        built.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    after = fixture.context.repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    assert before is not None
    assert loaded is not None
    assert by_id is not None
    assert after is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
