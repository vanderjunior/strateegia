import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_correction_shells import (
    api_readonly_fixture,
    blank_answer_correction_readiness_fixture,
    build_correction_shell,
    empty_answer_submission_fixture,
    idempotency_fixture,
    invalid_submission_fixture,
    missing_answer_submission_fixture,
    missing_correction_rule_fixture,
    missing_final_answer_key_fixture,
    missing_score_rule_fixture,
    mixed_submission_readiness_fixture,
    no_answer_key_gabarito_safety_fixture,
    no_correction_scoring_safety_fixture,
    no_progress_mutation_fixture,
    selected_option_correction_readiness_fixture,
    short_text_correction_readiness_fixture,
    true_false_correction_readiness_fixture,
    unsupported_answer_kind_fixture,
    user_scope_fixture,
)


FORBIDDEN_CORRECTION_KEYS = {
    "correction_result",
    "correction_status",
    "corrected_answer",
    "correct_option",
    "correct_answer",
    "answer_key",
    "final_answer_key",
    "final_answer_key_content",
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


def assert_disabled_flags(shell) -> None:
    assert shell.correction_enabled is False
    assert shell.scoring_enabled is False
    assert shell.progress_mutation_enabled is False
    assert shell.no_correction_result_created is True
    assert shell.no_score_created is True
    assert shell.no_progress_mutation is True


def assert_no_leakage(dumped_text: str, dumped_keys: set[str]) -> None:
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "/uploads/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text
    for key in FORBIDDEN_CORRECTION_KEYS:
        assert key not in dumped_keys


def test_correction_shell_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = selected_option_correction_readiness_fixture(tmp_path / "first")
    second = selected_option_correction_readiness_fixture(tmp_path / "second")

    assert first.answer_submission is not None
    assert second.answer_submission is not None
    assert first.answer_submission.answer_submission_id == second.answer_submission.answer_submission_id

    built = build_correction_shell(first)
    assert built is not None
    dumped = built.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    assert len(dumped_text) < 30000
    json.dumps(dumped, ensure_ascii=True)


def test_missing_empty_selected_true_false_blank_and_short_text_correction_shell_scenarios_are_stable(tmp_path):
    missing = missing_answer_submission_fixture(tmp_path / "missing")
    assert build_correction_shell(missing) is None
    assert missing.context.repository.list_user_simulado_correction_shells(user_id=missing.context.user_id) == []

    empty = build_correction_shell(empty_answer_submission_fixture(tmp_path / "empty"))
    selected = build_correction_shell(selected_option_correction_readiness_fixture(tmp_path / "selected"))
    true_false = build_correction_shell(true_false_correction_readiness_fixture(tmp_path / "true-false"))
    blank = build_correction_shell(blank_answer_correction_readiness_fixture(tmp_path / "blank"))
    short_text = build_correction_shell(short_text_correction_readiness_fixture(tmp_path / "short-text"))

    assert empty is not None
    assert selected is not None
    assert true_false is not None
    assert blank is not None
    assert short_text is not None

    assert empty.readiness_state == "blocked_by_no_submitted_answers"
    assert_disabled_flags(empty)

    for shell in (selected, true_false, short_text):
        assert shell.total_submitted_answers == 1
        assert shell.structurally_valid_answer_count == 1
        assert shell.correction_ready_answer_count == 0
        assert shell.answer_records[0].can_be_corrected is False
        assert shell.answer_records[0].can_be_scored is False
        assert_disabled_flags(shell)

    assert selected.answer_records[0].answer_kind == "selected_option"
    assert selected.answer_records[0].submission_validation_state == "structurally_valid"
    assert selected.answer_records[0].correction_readiness_state == "answer_blocked_by_missing_final_answer_key"

    assert true_false.answer_records[0].answer_kind == "true_false_value"
    assert true_false.answer_records[0].submission_validation_state == "structurally_valid"

    assert blank.blank_answer_count == 1
    assert blank.answer_records[0].is_blank is True
    assert blank.answer_records[0].correction_readiness_state == "answer_blank_not_corrected"
    assert_disabled_flags(blank)

    assert short_text.answer_records[0].answer_kind == "short_text"
    assert short_text.answer_records[0].submission_validation_state == "structurally_valid"


def test_unsupported_invalid_missing_rules_and_mixed_readiness_counts_are_stable(tmp_path):
    unsupported = build_correction_shell(unsupported_answer_kind_fixture(tmp_path / "unsupported"))
    invalid = build_correction_shell(invalid_submission_fixture(tmp_path / "invalid"))
    missing_key = build_correction_shell(missing_final_answer_key_fixture(tmp_path / "missing-key"))
    missing_correction_rule = build_correction_shell(
        missing_correction_rule_fixture(tmp_path / "missing-correction-rule")
    )
    missing_score_rule = build_correction_shell(missing_score_rule_fixture(tmp_path / "missing-score-rule"))
    mixed = build_correction_shell(mixed_submission_readiness_fixture(tmp_path / "mixed"))

    assert unsupported is not None
    assert invalid is not None
    assert missing_key is not None
    assert missing_correction_rule is not None
    assert missing_score_rule is not None
    assert mixed is not None

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].correction_readiness_state == "answer_blocked_by_unsupported_answer_kind"
    assert_disabled_flags(unsupported)

    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert "unknown_session_item" in invalid_codes
    assert invalid.invalid_answer_count >= 1
    assert invalid.total_submitted_answers == 0
    assert invalid.readiness_state in {"blocked_by_invalid_submission", "blocked_by_no_submitted_answers"}
    assert_disabled_flags(invalid)

    for shell in (missing_key, missing_correction_rule, missing_score_rule):
        blocker_codes = {item.code for item in shell.blockers}
        assert "blocked_by_missing_final_answer_keys" in blocker_codes
        assert "blocked_by_missing_correction_rules" in blocker_codes
        assert "blocked_by_missing_score_rules" in blocker_codes
        assert shell.readiness_summary.has_final_answer_keys is False
        assert shell.readiness_summary.has_correction_rules is False
        assert shell.readiness_summary.has_score_rules is False
        assert_disabled_flags(shell)

    assert mixed.total_submitted_answers == 4
    assert mixed.structurally_valid_answer_count == 2
    assert mixed.blank_answer_count == 1
    assert mixed.invalid_answer_count >= 1
    assert mixed.blocked_answer_count == 4
    assert all(record.can_be_corrected is False for record in mixed.answer_records)
    assert all(record.can_be_scored is False for record in mixed.answer_records)
    assert_disabled_flags(mixed)


def test_answer_key_gabarito_correction_scoring_and_progress_safeguards_hold(tmp_path):
    safety = build_correction_shell(no_answer_key_gabarito_safety_fixture(tmp_path / "key-safety"))
    no_score = build_correction_shell(no_correction_scoring_safety_fixture(tmp_path / "score-safety"))
    progress_fixture = no_progress_mutation_fixture(tmp_path / "progress")

    before_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.answer_submission.answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    before_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.answer_submission.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    before_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.answer_submission.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    before_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)
    no_progress = build_correction_shell(progress_fixture)
    loaded = progress_fixture.context.service.get_correction_shell(
        progress_fixture.answer_submission.answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    by_id = progress_fixture.context.service.get_correction_shell_by_id(
        no_progress.correction_shell_id if no_progress is not None else "",
        user_id=progress_fixture.context.user_id,
    )
    after_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.answer_submission.answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    after_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.answer_submission.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    after_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.answer_submission.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    after_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)

    assert safety is not None
    assert no_score is not None
    assert no_progress is not None
    assert loaded is not None
    assert by_id is not None

    for shell in (safety, no_score, no_progress):
        dumped = shell.model_dump(mode="json")
        dumped_keys = collect_json_keys(dumped)
        dumped_text = json.dumps(dumped, ensure_ascii=True)
        assert_no_leakage(dumped_text, dumped_keys)
        assert_disabled_flags(shell)

    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == by_id.model_dump(mode="json") == no_progress.model_dump(mode="json")


def test_correction_shell_persistence_idempotency_api_owner_only_and_get_read_only_hold(tmp_path):
    fixture = idempotency_fixture(tmp_path / "idempotency")
    first = build_correction_shell(fixture)
    second = build_correction_shell(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_correction_shell(
        fixture.answer_submission.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_correction_shell_by_id(
        first.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_correction_shells(user_id=fixture.context.user_id)
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    owner, other, anonymous, repository = create_clients(tmp_path / "api")
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    api_fixture = api_readonly_fixture(tmp_path / "api-fixture", user_id=owner_user_id, repository=repository)
    assert api_fixture.answer_submission is not None

    missing = owner.get(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell"
    )
    before_submission = repository.get_simulado_answer_submission_by_id(
        api_fixture.answer_submission.answer_submission_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell/build"
    )
    loaded = owner.get(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell"
    )
    correction_shell_id = build.json()["correction_shell_id"]
    by_id_response = owner.get(f"/api/simulado-correction-shell/{correction_shell_id}")
    repeated = owner.post(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell/build"
    )
    after_submission = repository.get_simulado_answer_submission_by_id(
        api_fixture.answer_submission.answer_submission_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_submission is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id_response.status_code == 200
    assert repeated.status_code == 200
    assert build.json() == loaded.json() == by_id_response.json() == repeated.json()
    assert after_submission is not None
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-correction-shell/{correction_shell_id}").status_code == 401

    assert other.post(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-answer-submission/{api_fixture.answer_submission.answer_submission_id}/correction-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-correction-shell/{correction_shell_id}").status_code == 404


def test_user_scope_fixture_remains_user_scoped_and_json_safe(tmp_path):
    owner_fixture, other_fixture = user_scope_fixture(tmp_path / "scope")
    owner_shell = build_correction_shell(owner_fixture)
    other_shell = build_correction_shell(other_fixture)

    assert owner_shell is not None
    assert other_shell is not None
    assert owner_shell.user_id != other_shell.user_id
    assert owner_fixture.context.repository.get_simulado_correction_shell(
        owner_shell.source_answer_submission_id,
        user_id=owner_fixture.context.user_id,
    ) is not None
    assert other_fixture.context.repository.get_simulado_correction_shell(
        other_shell.source_answer_submission_id,
        user_id=other_fixture.context.user_id,
    ) is not None

    dumped = json.dumps(owner_shell.model_dump(mode="json"), ensure_ascii=True)
    dumped_keys = collect_json_keys(owner_shell.model_dump(mode="json"))
    assert_no_leakage(dumped, dumped_keys)
