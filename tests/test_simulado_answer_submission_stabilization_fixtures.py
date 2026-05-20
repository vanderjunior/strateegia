import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_answer_submissions import (
    api_readonly_fixture,
    blank_submission_fixture,
    build_answer_submission,
    different_payload_fixture,
    empty_submission_fixture,
    first_session_item_id,
    long_short_text_fixture,
    missing_attempt_session_fixture,
    no_correction_scoring_safety_fixture,
    no_progress_mutation_fixture,
    partial_submission_fixture,
    same_payload_idempotency_fixture,
    selected_option_submission_fixture,
    short_text_submission_fixture,
    true_false_submission_fixture,
    unknown_item_fixture,
    duplicate_answer_fixture,
    unsupported_answer_kind_fixture,
    user_scope_fixture,
)


FORBIDDEN_SUBMISSION_KEYS = {
    "correction_result",
    "correction_status",
    "correct_option",
    "correct_answer",
    "answer_key",
    "gabarito",
    "gabarito_final",
    "score",
    "grade",
    "simulado_result",
    "score_rule",
    "correction_rule",
    "correctness",
    "is_correct",
    "points_awarded",
    "result_id",
    "final_question_content",
    "final_answer_key_content",
    "final_explanation_content",
}


def collect_json_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(collect_json_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(collect_json_keys(item))
        return keys
    return set()


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
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return login.json()["user"]["user_id"]


def assert_disabled_flags(submission) -> None:
    assert submission.correction_enabled is False
    assert submission.scoring_enabled is False
    assert submission.progress_mutation_enabled is False
    assert submission.no_correction_result_created is True
    assert submission.no_score_created is True
    assert submission.no_progress_mutation is True


def assert_no_leakage(dumped_text: str, dumped_keys: set[str]) -> None:
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "/uploads/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text
    for key in FORBIDDEN_SUBMISSION_KEYS:
        assert key not in dumped_keys


def test_answer_submission_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = selected_option_submission_fixture(tmp_path / "first")
    second = selected_option_submission_fixture(tmp_path / "second")

    assert first.attempt_session is not None
    assert second.attempt_session is not None
    assert first.attempt_session.attempt_session_id == second.attempt_session.attempt_session_id
    assert first.submission_payload == second.submission_payload

    built = build_answer_submission(first)
    assert built is not None
    dumped = built.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    assert len(dumped_text) < 20000
    json.dumps(dumped, ensure_ascii=True)


def test_selected_true_false_blank_short_text_and_long_text_fixtures_remain_structural_only(tmp_path):
    selected = build_answer_submission(selected_option_submission_fixture(tmp_path / "selected"))
    true_false = build_answer_submission(true_false_submission_fixture(tmp_path / "true-false"))
    blank = build_answer_submission(blank_submission_fixture(tmp_path / "blank"))
    short_text = build_answer_submission(short_text_submission_fixture(tmp_path / "short-text"))
    long_text = build_answer_submission(long_short_text_fixture(tmp_path / "long-text"))

    assert selected is not None
    assert true_false is not None
    assert blank is not None
    assert short_text is not None
    assert long_text is not None

    assert selected.submitted_answers[0].answer_kind == "selected_option"
    assert selected.submitted_answers[0].submitted_value == "A"
    assert selected.submitted_answers[0].validation_state == "structurally_valid"
    assert selected.readiness_state in {"submission_recorded_not_corrected", "partial_submission_recorded_not_corrected"}
    assert_disabled_flags(selected)

    assert true_false.submitted_answers[0].answer_kind == "true_false_value"
    assert true_false.submitted_answers[0].submitted_value == "C"
    assert true_false.submitted_answers[0].validation_state == "structurally_valid"
    assert_disabled_flags(true_false)

    assert blank.submitted_answers[0].is_blank is True
    assert blank.submitted_answers[0].validation_state == "blank_answer"
    assert_disabled_flags(blank)

    assert short_text.submitted_answers[0].answer_kind == "short_text"
    assert short_text.submitted_answers[0].validation_state == "structurally_valid"
    assert "<seguro>" not in short_text.submitted_answers[0].submitted_value
    assert "&lt;" in short_text.submitted_answers[0].submitted_value or "&amp;lt;" in short_text.submitted_answers[0].submitted_value
    assert_disabled_flags(short_text)

    assert len(long_text.submitted_answers[0].submitted_value or "") <= 1000
    assert "<script>" not in (long_text.submitted_answers[0].submitted_value or "")
    assert "&lt;" in (long_text.submitted_answers[0].submitted_value or "") or "&amp;lt;" in (
        long_text.submitted_answers[0].submitted_value or ""
    )
    assert_disabled_flags(long_text)


def test_unknown_duplicate_unsupported_partial_and_empty_submissions_are_handled_deterministically(tmp_path):
    unknown = build_answer_submission(unknown_item_fixture(tmp_path / "unknown"))
    duplicate = build_answer_submission(duplicate_answer_fixture(tmp_path / "duplicate"))
    unsupported = build_answer_submission(unsupported_answer_kind_fixture(tmp_path / "unsupported"))
    partial_fixture = partial_submission_fixture(tmp_path / "partial")
    partial = build_answer_submission(partial_fixture)
    empty = build_answer_submission(empty_submission_fixture(tmp_path / "empty"))

    assert unknown is not None
    assert duplicate is not None
    assert unsupported is not None
    assert partial is not None
    assert empty is not None

    unknown_codes = {finding.code for finding in unknown.validation_findings}
    assert "unknown_session_item" in unknown_codes
    assert unknown.submitted_answer_count == 0
    assert_disabled_flags(unknown)

    duplicate_codes = {warning.code for warning in duplicate.warnings} | {
        finding.code for finding in duplicate.validation_findings
    }
    assert duplicate.duplicate_answer_count == 1
    assert "duplicate_answer" in duplicate_codes
    assert duplicate.submitted_answer_count == 1
    assert duplicate.submitted_answers[0].submitted_value == "B"
    assert_disabled_flags(duplicate)

    unsupported_codes = {finding.code for finding in unsupported.validation_findings}
    assert "unsupported_answer_kind" in unsupported_codes
    assert unsupported.invalid_answer_count >= 1
    assert unsupported.submitted_answers[0].validation_state == "unsupported_answer_kind"
    assert_disabled_flags(unsupported)

    assert partial.total_items > 1
    assert partial.submitted_answer_count == 1
    assert partial.missing_answer_count == partial.total_items - 1
    assert partial.status == "answer_submission_partial"
    assert partial.readiness_state == "partial_submission_recorded_not_corrected"
    assert_disabled_flags(partial)

    assert empty.submitted_answer_count == 0
    assert empty.invalid_answer_count == 0
    assert empty.status == "answer_submission_blocked"
    assert empty.readiness_state == "blocked_by_no_session_items"
    assert_disabled_flags(empty)


def test_same_payload_idempotency_and_different_payload_behavior_are_stable(tmp_path):
    same_payload = same_payload_idempotency_fixture(tmp_path / "same")
    first = build_answer_submission(same_payload)
    second = build_answer_submission(same_payload)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = same_payload.context.repository.get_simulado_answer_submission(
        first.source_attempt_session_id,
        user_id=same_payload.context.user_id,
    )
    by_id = same_payload.context.repository.get_simulado_answer_submission_by_id(
        first.answer_submission_id,
        user_id=same_payload.context.user_id,
    )
    listed = same_payload.context.repository.list_user_simulado_answer_submissions(
        user_id=same_payload.context.user_id
    )
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    different = different_payload_fixture(tmp_path / "different")
    first_variant = build_answer_submission(different)
    second_variant = build_answer_submission(different, different.alternate_submission_payload)
    latest = different.context.service.get_answer_submission(
        different.attempt_session.attempt_session_id,
        user_id=different.context.user_id,
    )

    assert first_variant is not None
    assert second_variant is not None
    assert latest is not None
    assert first_variant.model_dump(mode="json") != second_variant.model_dump(mode="json")
    assert latest.model_dump(mode="json") == second_variant.model_dump(mode="json")


def test_no_correction_scoring_no_progress_mutation_and_no_leakage_safeguards_hold(tmp_path):
    safety = build_answer_submission(no_correction_scoring_safety_fixture(tmp_path / "safety"))
    progress_fixture = no_progress_mutation_fixture(tmp_path / "progress")
    before_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)
    before_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.attempt_session.attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    before_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.attempt_session.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    before_approval = progress_fixture.context.repository.get_simulado_final_approval_artifact_by_id(
        progress_fixture.attempt_session.source_final_approval_artifact_id,
        user_id=progress_fixture.context.user_id,
    )
    no_progress = build_answer_submission(progress_fixture)
    loaded = progress_fixture.context.service.get_answer_submission(
        progress_fixture.attempt_session.attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    by_id = progress_fixture.context.service.get_answer_submission_by_id(
        no_progress.answer_submission_id if no_progress is not None else "",
        user_id=progress_fixture.context.user_id,
    )
    after_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)
    after_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.attempt_session.attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    after_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.attempt_session.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    after_approval = progress_fixture.context.repository.get_simulado_final_approval_artifact_by_id(
        progress_fixture.attempt_session.source_final_approval_artifact_id,
        user_id=progress_fixture.context.user_id,
    )

    assert safety is not None
    assert no_progress is not None
    assert loaded is not None
    assert by_id is not None
    assert_disabled_flags(safety)
    assert_disabled_flags(no_progress)

    dumped_payload = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = collect_json_keys(dumped_payload)
    assert_no_leakage(dumped_text, dumped_keys)

    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_approval is not None and after_approval is not None
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == by_id.model_dump(mode="json") == no_progress.model_dump(mode="json")


def test_missing_attempt_session_and_api_owner_only_read_only_behavior(tmp_path):
    missing = missing_attempt_session_fixture(tmp_path / "missing")
    assert build_answer_submission(missing) is None
    assert missing.context.repository.list_user_simulado_answer_submissions(user_id=missing.context.user_id) == []

    owner, other, anonymous, repository = create_clients(tmp_path / "api")
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    api_fixture = api_readonly_fixture(tmp_path / "api-fixture", user_id=owner_user_id, repository=repository)
    assert api_fixture.attempt_session is not None
    item_id = first_session_item_id(api_fixture)

    missing_get = owner.get(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission"
    )
    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        api_fixture.attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission/build",
        json={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    loaded = owner.get(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission"
    )
    answer_submission_id = build.json()["answer_submission_id"]
    by_id = owner.get(f"/api/simulado-answer-submission/{answer_submission_id}")
    repeated = owner.post(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission/build",
        json={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        api_fixture.attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )

    assert missing_get.status_code == 404
    assert before_attempt_session is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert repeated.status_code == 200
    assert build.json() == repeated.json() == loaded.json() == by_id.json()
    assert after_attempt_session is not None
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-answer-submission/{answer_submission_id}").status_code == 401

    assert other.post(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission/build",
        json={"answers": []},
    ).status_code == 404
    assert other.get(
        f"/api/simulado-attempt-session/{api_fixture.attempt_session.attempt_session_id}/answer-submission"
    ).status_code == 404
    assert other.get(f"/api/simulado-answer-submission/{answer_submission_id}").status_code == 404


def test_user_scope_fixture_and_api_payloads_remain_bounded_and_json_safe(tmp_path):
    owner_fixture, other_fixture = user_scope_fixture(tmp_path / "scope")
    owner_submission = build_answer_submission(owner_fixture)
    other_submission = build_answer_submission(other_fixture)

    assert owner_submission is not None
    assert other_submission is not None
    assert owner_submission.user_id != other_submission.user_id
    assert owner_fixture.context.repository.get_simulado_answer_submission(
        owner_submission.source_attempt_session_id,
        user_id=owner_fixture.context.user_id,
    ) is not None
    assert other_fixture.context.repository.get_simulado_answer_submission(
        other_submission.source_attempt_session_id,
        user_id=other_fixture.context.user_id,
    ) is not None

    dumped = json.dumps(owner_submission.model_dump(mode="json"), ensure_ascii=True)
    dumped_keys = collect_json_keys(owner_submission.model_dump(mode="json"))
    assert_no_leakage(dumped, dumped_keys)
