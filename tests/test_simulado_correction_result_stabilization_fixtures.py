import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_correction_results import (
    api_readonly_fixture,
    blank_answer_correction_result_fixture,
    build_correction_result,
    empty_answer_key_boundary_fixture,
    idempotency_fixture,
    invalid_submission_fixture,
    missing_answer_key_boundary_fixture,
    missing_correction_rule_fixture,
    missing_internal_answer_key_reference_fixture,
    mixed_correction_result_fixture,
    no_progress_mutation_fixture,
    no_public_key_gabarito_safety_fixture,
    no_scoring_safety_fixture,
    selected_option_correction_result_fixture,
    short_text_correction_result_fixture,
    true_false_correction_result_fixture,
    unsupported_answer_kind_fixture,
    user_scope_fixture,
)


FORBIDDEN_CORRECTION_RESULT_KEYS = {
    "score",
    "grade",
    "points_awarded",
    "weighted_score",
    "percent_correct",
    "final_score",
    "simulado_result",
    "final_simulado_result",
    "passed",
    "failed",
    "answer_key",
    "answer_key_value",
    "correct_answer",
    "correct_option",
    "gabarito",
    "gabarito_final",
    "final_answer_key",
    "final_answer_key_content",
    "final_question_content",
    "final_explanation_content",
    "result_id",
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


def assert_disabled_flags(result) -> None:
    assert result.scoring_enabled is False
    assert result.progress_mutation_enabled is False
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    assert result.no_score_created is True
    assert result.no_progress_mutation is True
    assert result.no_final_simulado_result_created is True


def assert_no_leakage(dumped_text: str, dumped_keys: set[str]) -> None:
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "/uploads/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text
    for key in FORBIDDEN_CORRECTION_RESULT_KEYS:
        assert key not in dumped_keys


def test_correction_result_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = selected_option_correction_result_fixture(tmp_path / "first")
    second = selected_option_correction_result_fixture(tmp_path / "second")

    assert first.answer_key_boundary is not None
    assert second.answer_key_boundary is not None
    assert first.answer_key_boundary.answer_key_boundary_id == second.answer_key_boundary.answer_key_boundary_id

    built = build_correction_result(first)
    assert built is not None
    dumped = built.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    assert len(dumped_text) < 40000
    json.dumps(dumped, ensure_ascii=True)


def test_missing_empty_selected_true_false_blank_and_short_text_correction_result_scenarios_are_stable(tmp_path):
    missing = missing_answer_key_boundary_fixture(tmp_path / "missing")
    assert build_correction_result(missing) is None
    assert missing.context.repository.list_user_simulado_correction_results(user_id=missing.context.user_id) == []

    empty = build_correction_result(empty_answer_key_boundary_fixture(tmp_path / "empty"))
    selected = build_correction_result(selected_option_correction_result_fixture(tmp_path / "selected"))
    true_false = build_correction_result(true_false_correction_result_fixture(tmp_path / "true-false"))
    blank = build_correction_result(blank_answer_correction_result_fixture(tmp_path / "blank"))
    short_text = build_correction_result(short_text_correction_result_fixture(tmp_path / "short-text"))

    assert empty is not None
    assert selected is not None
    assert true_false is not None
    assert blank is not None
    assert short_text is not None

    assert empty.readiness_state in {"correction_result_needs_review", "blocked_by_invalid_submission"}
    assert_disabled_flags(empty)

    for result in (selected, true_false, short_text):
        assert result.total_answer_records == 1
        assert result.corrected_answer_count == 0
        assert result.blocked_answer_count == 1
        assert result.answer_records[0].scoreable is False
        assert result.answer_records[0].scoring_enabled is False
        assert result.answer_records[0].candidate_result is None
        assert_disabled_flags(result)

    assert selected.answer_records[0].answer_kind == "selected_option"
    assert selected.answer_records[0].correction_state == "answer_blocked_by_missing_internal_answer_key_reference"

    assert true_false.answer_records[0].answer_kind == "true_false_value"
    assert true_false.answer_records[0].correction_state == "answer_blocked_by_missing_internal_answer_key_reference"

    assert blank.blank_answer_count == 1
    assert blank.answer_records[0].student_answer_blank is True
    assert blank.answer_records[0].correction_state == "answer_blank_not_scored"
    assert_disabled_flags(blank)

    assert short_text.answer_records[0].answer_kind == "short_text"
    assert short_text.answer_records[0].correction_state == "answer_blocked_by_missing_internal_answer_key_reference"


def test_unsupported_invalid_missing_key_missing_rule_and_mixed_correction_result_counts_are_stable(tmp_path):
    unsupported = build_correction_result(unsupported_answer_kind_fixture(tmp_path / "unsupported"))
    invalid = build_correction_result(invalid_submission_fixture(tmp_path / "invalid"))
    missing_key = build_correction_result(
        missing_internal_answer_key_reference_fixture(tmp_path / "missing-key")
    )
    missing_rule = build_correction_result(missing_correction_rule_fixture(tmp_path / "missing-rule"))
    mixed = build_correction_result(mixed_correction_result_fixture(tmp_path / "mixed"))

    assert unsupported is not None
    assert invalid is not None
    assert missing_key is not None
    assert missing_rule is not None
    assert mixed is not None

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].correction_state == "answer_blocked_by_unsupported_answer_kind"
    assert unsupported.unsupported_answer_count == 1
    assert_disabled_flags(unsupported)

    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert invalid.total_answer_records == 0
    assert invalid.readiness_state == "blocked_by_invalid_submission"
    assert "unknown_session_item" in invalid_codes or "blocked_by_invalid_submission" in invalid_codes
    assert_disabled_flags(invalid)

    for result in (missing_key, missing_rule):
        blocker_codes = {item.code for item in result.blockers}
        assert "blocked_by_missing_internal_answer_key_reference" in blocker_codes
        assert "blocked_by_missing_correction_rule" in blocker_codes
        assert result.answer_records[0].correction_state == "answer_blocked_by_missing_internal_answer_key_reference"
        assert result.answer_records[0].scoreable is False
        assert_disabled_flags(result)

    assert mixed.total_answer_records == 4
    assert mixed.corrected_answer_count == 0
    assert mixed.blocked_answer_count == 4
    assert mixed.needs_review_answer_count == 0
    assert mixed.blank_answer_count == 1
    assert mixed.unsupported_answer_count == 1
    assert all(record.scoreable is False for record in mixed.answer_records)
    assert_disabled_flags(mixed)


def test_public_answer_key_scoring_and_progress_safeguards_hold(tmp_path):
    public_safety = build_correction_result(no_public_key_gabarito_safety_fixture(tmp_path / "public-safety"))
    no_score = build_correction_result(no_scoring_safety_fixture(tmp_path / "score-safety"))
    progress_fixture = no_progress_mutation_fixture(tmp_path / "progress")

    before_boundary = progress_fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        progress_fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=progress_fixture.context.user_id,
    )
    assert before_boundary is not None
    before_correction_shell = progress_fixture.context.repository.get_simulado_correction_shell_by_id(
        progress_fixture.answer_key_boundary.source_correction_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    before_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.answer_key_boundary.source_answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    before_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.answer_key_boundary.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    before_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        before_submission.source_execution_shell_id if before_submission is not None else "",
        user_id=progress_fixture.context.user_id,
    )
    before_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)

    no_progress = build_correction_result(progress_fixture)
    loaded = progress_fixture.context.service.get_correction_result(
        progress_fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=progress_fixture.context.user_id,
    )
    by_id = progress_fixture.context.service.get_correction_result_by_id(
        no_progress.correction_result_id if no_progress is not None else "",
        user_id=progress_fixture.context.user_id,
    )

    after_boundary = progress_fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        progress_fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=progress_fixture.context.user_id,
    )
    after_correction_shell = progress_fixture.context.repository.get_simulado_correction_shell_by_id(
        progress_fixture.answer_key_boundary.source_correction_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    after_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.answer_key_boundary.source_answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    after_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.answer_key_boundary.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    after_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        after_submission.source_execution_shell_id if after_submission is not None else "",
        user_id=progress_fixture.context.user_id,
    )
    after_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)

    assert public_safety is not None
    assert no_score is not None
    assert no_progress is not None
    assert loaded is not None
    assert by_id is not None

    for result in (public_safety, no_score, no_progress):
        dumped = result.model_dump(mode="json")
        dumped_keys = collect_json_keys(dumped)
        dumped_text = json.dumps(dumped, ensure_ascii=True)
        assert_no_leakage(dumped_text, dumped_keys)
        assert_disabled_flags(result)

    assert before_correction_shell is not None and after_correction_shell is not None
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_correction_result_persistence_api_scope_and_read_only_behavior_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path / "idempotency")
    first = build_correction_result(fixture)
    second = build_correction_result(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_correction_result(
        fixture.answer_key_boundary.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_correction_result_by_id(
        first.correction_result_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_correction_results(
        user_id=fixture.context.user_id
    )

    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    owner, other = user_scope_fixture(tmp_path / "scope")
    owner_result = build_correction_result(owner)
    other_result = build_correction_result(other)
    assert owner_result is not None
    assert other_result is not None
    owner_listed = owner.context.repository.list_user_simulado_correction_results(user_id=owner.context.user_id)
    other_listed = other.context.repository.list_user_simulado_correction_results(user_id=other.context.user_id)
    assert len(owner_listed) == 1
    assert len(other_listed) == 1
    assert owner_listed[0].user_id == owner.context.user_id
    assert other_listed[0].user_id == other.context.user_id

    readonly = api_readonly_fixture(tmp_path / "readonly")
    before_boundary = readonly.context.repository.get_simulado_answer_key_boundary_by_id(
        readonly.answer_key_boundary.answer_key_boundary_id,
        user_id=readonly.context.user_id,
    )
    assert before_boundary is not None
    missing = readonly.context.service.get_correction_result(
        readonly.answer_key_boundary.answer_key_boundary_id,
        user_id=readonly.context.user_id,
    )
    built = build_correction_result(readonly)
    loaded = readonly.context.service.get_correction_result(
        readonly.answer_key_boundary.answer_key_boundary_id,
        user_id=readonly.context.user_id,
    )
    after_boundary = readonly.context.repository.get_simulado_answer_key_boundary_by_id(
        readonly.answer_key_boundary.answer_key_boundary_id,
        user_id=readonly.context.user_id,
    )

    assert missing is None
    assert built is not None
    assert loaded is not None
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")


def test_correction_result_api_endpoints_are_owner_only_and_read_only(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    fixture = selected_option_correction_result_fixture(
        tmp_path / "owner-data",
        user_id=owner_user_id,
        repository=repository,
    )
    boundary = fixture.answer_key_boundary
    assert boundary is not None

    missing = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    build = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    loaded = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    correction_result_id = build.json()["correction_result_id"]
    by_id = owner.get(f"/api/simulado-correction-result/{correction_result_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_answer_key_boundary_id"] == boundary.answer_key_boundary_id
    assert loaded.json()["scoring_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-correction-result/{correction_result_id}").status_code == 401

    assert other.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result"
    ).status_code == 404
    assert other.get(f"/api/simulado-correction-result/{correction_result_id}").status_code == 404
