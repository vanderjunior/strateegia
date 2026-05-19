import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_finalization_guardrails import (
    all_blocked_candidates_fixture,
    assembly_json_keys,
    attempt_shell_not_executable_fixture,
    bounded_summary_fixture,
    build_finalization_guardrail,
    human_review_required_fixture,
    idempotency_fixture,
    missing_final_answer_keys_fixture,
    missing_final_explanations_fixture,
    missing_final_questions_fixture,
    mixed_ready_blocked_review_fixture,
    no_approval_finalization_execution_safety_fixture,
    non_final_assembly_fixture,
    ready_candidates_not_finalizable_fixture,
    unsupported_format_fixture,
    user_scope_fixture,
    zero_candidates_fixture,
)


FORBIDDEN_FINALIZATION_KEYS = {
    "approved_simulado",
    "finalized_simulado",
    "approval_record",
    "finalization_record",
    "executable_simulado",
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
    "final_question_content",
    "final_answer_key_content",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation_content",
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


def assert_disabled_flags(guardrail) -> None:
    assert guardrail.approval_required is True
    assert guardrail.human_review_required is True
    assert guardrail.execution_enabled is False
    assert guardrail.correction_enabled is False
    assert guardrail.scoring_enabled is False
    assert guardrail.student_submission_enabled is False
    assert guardrail.progress_mutation_enabled is False
    assert guardrail.no_student_attempt_created is True
    assert guardrail.no_answer_submission_enabled is True
    assert guardrail.no_correction_result_created is True
    assert guardrail.no_score_created is True


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_finalization_guardrail_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = non_final_assembly_fixture(tmp_path / "first")
    second = non_final_assembly_fixture(tmp_path / "second")

    assert first.assembly.assembly_id == second.assembly.assembly_id
    assert first.attempt_shell.attempt_shell_id == second.attempt_shell.attempt_shell_id
    json.dumps(first.assembly.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(first.attempt_shell.model_dump(mode="json"), ensure_ascii=True)
    guardrail = build_finalization_guardrail(first)
    assert guardrail is not None
    json.dumps(guardrail.model_dump(mode="json"), ensure_ascii=True)


def test_missing_attempt_shell_and_non_final_or_not_executable_fixtures_remain_blocked(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    assert build_finalization_guardrail(
        non_final_assembly_fixture(tmp_path / "seed", repository=repository)
    ) is not None

    from app.services.simulado_finalization_guardrails import SimuladoFinalizationGuardrailsService

    service = SimuladoFinalizationGuardrailsService(repository)
    assert service.build_guardrail("simulado-attempt-shell:missing", user_id="user-a") is None

    non_final = build_finalization_guardrail(non_final_assembly_fixture(tmp_path / "non-final"))
    not_executable = build_finalization_guardrail(
        attempt_shell_not_executable_fixture(tmp_path / "not-executable")
    )

    assert non_final is not None
    assert not_executable is not None

    non_final_codes = {item.code for item in non_final.blockers}
    not_executable_codes = {item.code for item in not_executable.blockers}

    assert_disabled_flags(non_final)
    assert "blocked_by_non_final_assembly" in non_final_codes
    assert "blocked_by_attempt_shell_not_executable" in non_final_codes
    assert non_final.readiness_state in {
        "blocked_by_attempt_shell_not_executable",
        "blocked_by_non_final_assembly",
        "needs_human_approval_review",
    }

    assert_disabled_flags(not_executable)
    assert "blocked_by_attempt_shell_not_executable" in not_executable_codes
    assert not_executable.finalizable_candidates_count == 0
    assert not_executable.approved_candidates_count == 0


def test_ready_candidates_missing_final_content_and_human_review_fixtures_preserve_non_finalizable_state(tmp_path):
    ready = build_finalization_guardrail(ready_candidates_not_finalizable_fixture(tmp_path / "ready"))
    missing_questions = build_finalization_guardrail(missing_final_questions_fixture(tmp_path / "questions"))
    missing_answers = build_finalization_guardrail(missing_final_answer_keys_fixture(tmp_path / "answers"))
    missing_explanations = build_finalization_guardrail(
        missing_final_explanations_fixture(tmp_path / "explanations")
    )
    human_review = build_finalization_guardrail(human_review_required_fixture(tmp_path / "review"))

    assert ready is not None
    assert missing_questions is not None
    assert missing_answers is not None
    assert missing_explanations is not None
    assert human_review is not None

    assert ready.review_ready_candidates > 0
    assert ready.finalizable_candidates_count == 0
    assert ready.approved_candidates_count == 0
    assert all(item.approval_state == "approval_required" for item in ready.candidate_summaries)
    assert all(item.has_final_question is False for item in ready.candidate_summaries)
    assert all(item.has_final_answer_key is False for item in ready.candidate_summaries)
    assert all(item.has_final_explanation is False for item in ready.candidate_summaries)

    assert "blocked_by_missing_final_questions" in {item.code for item in missing_questions.blockers}
    assert missing_questions.finalizable_candidates_count == 0
    assert missing_questions.missing_final_questions_count > 0

    assert "blocked_by_missing_final_answer_keys" in {item.code for item in missing_answers.blockers}
    assert missing_answers.correction_enabled is False
    assert missing_answers.scoring_enabled is False

    assert "blocked_by_missing_final_explanations" in {item.code for item in missing_explanations.blockers}

    human_review_codes = {item.code for item in human_review.blockers}
    assert human_review.human_review_required is True
    assert "blocked_by_human_review_required" in human_review_codes or human_review.readiness_state in {
        "needs_human_approval_review",
        "blocked_by_attempt_shell_not_executable",
    }


def test_zero_all_blocked_mixed_and_unsupported_fixtures_keep_counts_stable(tmp_path):
    zero = build_finalization_guardrail(zero_candidates_fixture(tmp_path / "zero"))
    all_blocked = build_finalization_guardrail(all_blocked_candidates_fixture(tmp_path / "blocked"))
    mixed = build_finalization_guardrail(mixed_ready_blocked_review_fixture(tmp_path / "mixed"))
    unsupported = build_finalization_guardrail(unsupported_format_fixture(tmp_path / "unsupported"))

    assert zero is not None
    assert all_blocked is not None
    assert mixed is not None
    assert unsupported is not None

    assert zero.readiness_state == "blocked_by_insufficient_candidates"
    assert zero.finalizable_candidates_count == 0

    assert all_blocked.finalizable_candidates_count == 0
    assert all_blocked.blocked_candidates > 0
    assert all_blocked.status in {"finalization_blocked", "finalization_not_available"}

    assert mixed.review_ready_candidates > 0
    assert mixed.blocked_candidates > 0
    assert mixed.needs_review_candidates > 0
    assert mixed.finalizable_candidates_count == 0
    assert_disabled_flags(mixed)

    unsupported_codes = {item.code for item in unsupported.blockers}
    assert unsupported.execution_enabled is False
    assert "blocked_by_unsupported_format" in unsupported_codes or unsupported.readiness_state in {
        "blocked_by_insufficient_candidates",
        "blocked_by_unsupported_format",
    }


def test_disabled_flags_and_no_approval_finalization_execution_safeguards_hold(tmp_path):
    safety = build_finalization_guardrail(
        no_approval_finalization_execution_safety_fixture(tmp_path / "safety")
    )
    bounded = build_finalization_guardrail(bounded_summary_fixture(tmp_path / "bounded"))

    assert safety is not None
    assert bounded is not None

    dumped = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped)
    finding_codes = {item.code for item in safety.validation_findings}

    assert_disabled_flags(safety)
    assert "approval_required" in finding_codes
    assert "human_review_required" in finding_codes
    assert "execution_disabled" in finding_codes
    assert "correction_disabled" in finding_codes
    assert "scoring_disabled" in finding_codes
    assert "student_submission_disabled" in finding_codes
    assert "progress_mutation_disabled" in finding_codes
    for key in FORBIDDEN_FINALIZATION_KEYS:
        assert key not in dumped_keys
    assert_no_leakage(dumped_text)
    assert_no_leakage(json.dumps(bounded.model_dump(mode="json"), ensure_ascii=True))


def test_finalization_guardrail_persistence_and_idempotency_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    first = build_finalization_guardrail(fixture)
    second = build_finalization_guardrail(fixture)

    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_finalization_guardrail(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_finalization_guardrail_by_id(
        first.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_finalization_guardrails(
        user_id=fixture.context.user_id
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1


def test_finalization_guardrail_api_owner_only_read_only_and_user_scope_are_preserved(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture, _ = user_scope_fixture(tmp_path / "scope", repository=repository)
    owner_fixture = non_final_assembly_fixture(
        tmp_path / "owner-api",
        user_id=owner_user_id,
        repository=repository,
    )
    attempt_shell_id = owner_fixture.attempt_shell.attempt_shell_id

    missing = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail")
    before_list = repository.list_user_simulado_finalization_guardrails(user_id=owner_user_id)
    build = owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
    finalization_guardrail_id = build.json()["finalization_guardrail_id"]
    after_build_list = repository.list_user_simulado_finalization_guardrails(user_id=owner_user_id)
    loaded = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail")
    by_id = owner.get(f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}")
    after_get_list = repository.list_user_simulado_finalization_guardrails(user_id=owner_user_id)
    dumped = json.dumps(by_id.json(), ensure_ascii=True)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert (
        owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build").json()
        == build.json()
    )
    assert anonymous.post(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}"
    ).status_code == 401
    assert other.post(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}"
    ).status_code == 404
    assert_no_leakage(dumped)


def test_finalization_guardrail_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    fixture = non_final_assembly_fixture(tmp_path)
    before_shell = fixture.context.repository.get_simulado_attempt_shell_by_id(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    before_assembly = fixture.context.repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    built = build_finalization_guardrail(fixture)
    assert built is not None
    loaded = fixture.context.service.get_guardrail(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.service.get_guardrail_by_id(
        built.finalization_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_shell = fixture.context.repository.get_simulado_attempt_shell_by_id(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    after_assembly = fixture.context.repository.get_simulado_question_assembly_by_id(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )

    assert before_shell is not None
    assert before_assembly is not None
    assert loaded is not None
    assert by_id is not None
    assert after_shell is not None
    assert after_assembly is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_assembly.model_dump(mode="json") == after_assembly.model_dump(mode="json")
