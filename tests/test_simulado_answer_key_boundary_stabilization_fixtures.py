import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_answer_key_boundaries import (
    api_readonly_fixture,
    blank_answer_boundary_fixture,
    build_answer_key_boundary,
    empty_correction_shell_fixture,
    idempotency_fixture,
    internal_reference_redacted_fixture,
    invalid_submission_boundary_fixture,
    missing_correction_rule_fixture,
    missing_correction_shell_fixture,
    missing_internal_answer_key_reference_fixture,
    missing_score_rule_fixture,
    mixed_boundary_fixture,
    no_correction_scoring_safety_fixture,
    no_progress_mutation_fixture,
    no_public_key_gabarito_safety_fixture,
    selected_option_boundary_fixture,
    short_text_boundary_fixture,
    true_false_boundary_fixture,
    unsupported_answer_kind_boundary_fixture,
    user_scope_fixture,
)


FORBIDDEN_BOUNDARY_KEYS = {
    "correction_result",
    "correction_status",
    "corrected_answer",
    "correct_option",
    "correct_answer",
    "answer_key",
    "answer_key_value",
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


def assert_disabled_flags(boundary) -> None:
    assert boundary.answer_key_publicly_exposed is False
    assert boundary.gabarito_publicly_exposed is False
    assert boundary.correction_enabled is False
    assert boundary.scoring_enabled is False
    assert boundary.progress_mutation_enabled is False
    assert boundary.no_correction_result_created is True
    assert boundary.no_score_created is True
    assert boundary.no_progress_mutation is True


def assert_no_leakage(dumped_text: str, dumped_keys: set[str]) -> None:
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "/uploads/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text
    for key in FORBIDDEN_BOUNDARY_KEYS:
        assert key not in dumped_keys


def test_answer_key_boundary_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = selected_option_boundary_fixture(tmp_path / "first")
    second = selected_option_boundary_fixture(tmp_path / "second")

    assert first.correction_shell is not None
    assert second.correction_shell is not None
    assert first.correction_shell.correction_shell_id == second.correction_shell.correction_shell_id

    built = build_answer_key_boundary(first)
    assert built is not None
    dumped = built.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    assert len(dumped_text) < 40000
    json.dumps(dumped, ensure_ascii=True)


def test_missing_empty_selected_true_false_blank_and_short_text_boundary_scenarios_are_stable(tmp_path):
    missing = missing_correction_shell_fixture(tmp_path / "missing")
    assert build_answer_key_boundary(missing) is None
    assert missing.context.repository.list_user_simulado_answer_key_boundaries(user_id=missing.context.user_id) == []

    empty = build_answer_key_boundary(empty_correction_shell_fixture(tmp_path / "empty"))
    selected = build_answer_key_boundary(selected_option_boundary_fixture(tmp_path / "selected"))
    true_false = build_answer_key_boundary(true_false_boundary_fixture(tmp_path / "true-false"))
    blank = build_answer_key_boundary(blank_answer_boundary_fixture(tmp_path / "blank"))
    short_text = build_answer_key_boundary(short_text_boundary_fixture(tmp_path / "short-text"))

    assert empty is not None
    assert selected is not None
    assert true_false is not None
    assert blank is not None
    assert short_text is not None

    assert empty.readiness_state == "blocked_by_no_answer_records"
    assert_disabled_flags(empty)

    for boundary in (selected, true_false, short_text):
        assert boundary.total_answer_records == 1
        assert boundary.supported_answer_record_count == 1
        assert boundary.blocked_answer_record_count == 1
        assert boundary.answer_records[0].has_public_answer_key_content is False
        assert boundary.answer_records[0].answer_key_publicly_exposed is False
        assert boundary.answer_records[0].correction_allowed_now is False
        assert boundary.answer_records[0].scoring_allowed_now is False
        assert_disabled_flags(boundary)

    assert selected.answer_records[0].answer_kind == "selected_option"
    assert selected.answer_records[0].boundary_readiness_state == "answer_blocked_by_missing_internal_answer_key_reference"

    assert true_false.answer_records[0].answer_kind == "true_false_value"
    assert true_false.answer_records[0].boundary_readiness_state == "answer_blocked_by_missing_internal_answer_key_reference"

    assert blank.answer_records[0].boundary_readiness_state == "answer_blank_not_corrected"
    assert blank.answer_records[0].future_correction_supported is False
    assert_disabled_flags(blank)

    assert short_text.answer_records[0].answer_kind == "short_text"
    assert short_text.answer_records[0].future_correction_supported is True


def test_unsupported_invalid_missing_rules_redaction_and_mixed_counts_are_stable(tmp_path):
    unsupported = build_answer_key_boundary(unsupported_answer_kind_boundary_fixture(tmp_path / "unsupported"))
    invalid = build_answer_key_boundary(invalid_submission_boundary_fixture(tmp_path / "invalid"))
    missing_key = build_answer_key_boundary(
        missing_internal_answer_key_reference_fixture(tmp_path / "missing-key")
    )
    missing_correction_rule = build_answer_key_boundary(
        missing_correction_rule_fixture(tmp_path / "missing-correction-rule")
    )
    missing_score_rule = build_answer_key_boundary(
        missing_score_rule_fixture(tmp_path / "missing-score-rule")
    )
    redacted = build_answer_key_boundary(internal_reference_redacted_fixture(tmp_path / "redacted"))
    mixed = build_answer_key_boundary(mixed_boundary_fixture(tmp_path / "mixed"))

    assert unsupported is not None
    assert invalid is not None
    assert missing_key is not None
    assert missing_correction_rule is not None
    assert missing_score_rule is not None
    assert redacted is not None
    assert mixed is not None

    unsupported_codes = {item.code for item in unsupported.blockers} | {
        item.code for item in unsupported.validation_findings
    }
    assert "blocked_by_unsupported_answer_kind" in unsupported_codes or "unsupported_answer_kind" in unsupported_codes
    assert unsupported.answer_records[0].boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind"
    assert_disabled_flags(unsupported)

    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert invalid.total_answer_records == 0
    assert invalid.readiness_state == "blocked_by_no_answer_records"
    assert "unknown_session_item" in invalid_codes or "blocked_by_no_answer_records" in invalid_codes
    assert_disabled_flags(invalid)

    for boundary in (missing_key, missing_correction_rule, missing_score_rule):
        blocker_codes = {item.code for item in boundary.blockers}
        assert "blocked_by_missing_internal_answer_key_reference" in blocker_codes
        assert "blocked_by_missing_correction_rule" in blocker_codes
        assert "blocked_by_missing_score_rule" in blocker_codes
        assert boundary.correction_input_contract.correction_allowed_now is False
        assert boundary.correction_input_contract.scoring_allowed_now is False
        assert_disabled_flags(boundary)

    for reference in redacted.internal_answer_key_references:
        assert reference.answer_key_reference_available is False
        assert reference.answer_key_value_stored is False
        assert reference.answer_key_value_publicly_exposed is False
        assert reference.answer_key_value_redacted is True
        assert reference.answer_key_value_hash is None
        assert reference.allowed_values == []
    assert_disabled_flags(redacted)

    assert mixed.total_answer_records == 4
    assert mixed.supported_answer_record_count == 2
    assert mixed.blocked_answer_record_count == 4
    assert mixed.internal_answer_key_reference_count == 0
    assert all(record.correction_allowed_now is False for record in mixed.answer_records)
    assert all(record.scoring_allowed_now is False for record in mixed.answer_records)
    assert_disabled_flags(mixed)


def test_public_exposure_correction_scoring_and_progress_safeguards_hold(tmp_path):
    public_safety = build_answer_key_boundary(no_public_key_gabarito_safety_fixture(tmp_path / "public-safety"))
    no_score = build_answer_key_boundary(no_correction_scoring_safety_fixture(tmp_path / "score-safety"))
    progress_fixture = no_progress_mutation_fixture(tmp_path / "progress")

    before_correction_shell = progress_fixture.context.repository.get_simulado_correction_shell_by_id(
        progress_fixture.correction_shell.correction_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    assert before_correction_shell is not None
    before_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.correction_shell.source_answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    before_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.correction_shell.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    before_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.correction_shell.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    before_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)

    no_progress = build_answer_key_boundary(progress_fixture)
    loaded = progress_fixture.context.service.get_answer_key_boundary(
        progress_fixture.correction_shell.correction_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    by_id = progress_fixture.context.service.get_answer_key_boundary_by_id(
        no_progress.answer_key_boundary_id if no_progress is not None else "",
        user_id=progress_fixture.context.user_id,
    )

    after_correction_shell = progress_fixture.context.repository.get_simulado_correction_shell_by_id(
        progress_fixture.correction_shell.correction_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    after_submission = progress_fixture.context.repository.get_simulado_answer_submission_by_id(
        progress_fixture.correction_shell.source_answer_submission_id,
        user_id=progress_fixture.context.user_id,
    )
    after_attempt_session = progress_fixture.context.repository.get_simulado_attempt_session_by_id(
        progress_fixture.correction_shell.source_attempt_session_id,
        user_id=progress_fixture.context.user_id,
    )
    after_execution_shell = progress_fixture.context.repository.get_simulado_execution_shell_by_id(
        progress_fixture.correction_shell.source_execution_shell_id,
        user_id=progress_fixture.context.user_id,
    )
    after_progress = progress_fixture.context.repository.load_progress(user_id=progress_fixture.context.user_id)

    assert public_safety is not None
    assert no_score is not None
    assert no_progress is not None
    assert loaded is not None
    assert by_id is not None

    for boundary in (public_safety, no_score, no_progress):
        dumped = boundary.model_dump(mode="json")
        dumped_keys = collect_json_keys(dumped)
        dumped_text = json.dumps(dumped, ensure_ascii=True)
        assert_no_leakage(dumped_text, dumped_keys)
        assert_disabled_flags(boundary)

    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_execution_shell is not None and after_execution_shell is not None
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_execution_shell.model_dump(mode="json") == after_execution_shell.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_answer_key_boundary_persistence_api_scope_and_read_only_behavior_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path / "idempotency")
    first = build_answer_key_boundary(fixture)
    second = build_answer_key_boundary(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = fixture.context.repository.get_simulado_answer_key_boundary(
        fixture.correction_shell.correction_shell_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        first.answer_key_boundary_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_answer_key_boundaries(
        user_id=fixture.context.user_id
    )

    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    owner, other = user_scope_fixture(tmp_path / "scope")
    owner_boundary = build_answer_key_boundary(owner)
    other_boundary = build_answer_key_boundary(other)
    assert owner_boundary is not None
    assert other_boundary is not None
    owner_listed = owner.context.repository.list_user_simulado_answer_key_boundaries(
        user_id=owner.context.user_id
    )
    other_listed = other.context.repository.list_user_simulado_answer_key_boundaries(
        user_id=other.context.user_id
    )
    assert len(owner_listed) == 1
    assert len(other_listed) == 1
    assert owner_listed[0].user_id == owner.context.user_id
    assert other_listed[0].user_id == other.context.user_id

    readonly = api_readonly_fixture(tmp_path / "readonly")
    before_shell = readonly.context.repository.get_simulado_correction_shell_by_id(
        readonly.correction_shell.correction_shell_id,
        user_id=readonly.context.user_id,
    )
    assert before_shell is not None
    missing = readonly.context.service.get_answer_key_boundary(
        readonly.correction_shell.correction_shell_id,
        user_id=readonly.context.user_id,
    )
    built = build_answer_key_boundary(readonly)
    loaded = readonly.context.service.get_answer_key_boundary(
        readonly.correction_shell.correction_shell_id,
        user_id=readonly.context.user_id,
    )
    after_shell = readonly.context.repository.get_simulado_correction_shell_by_id(
        readonly.correction_shell.correction_shell_id,
        user_id=readonly.context.user_id,
    )

    assert missing is None
    assert built is not None
    assert loaded is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")


def test_answer_key_boundary_api_endpoints_are_owner_only_and_read_only(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    fixture = selected_option_boundary_fixture(tmp_path / "owner-data", user_id=owner_user_id, repository=repository)
    correction_shell = fixture.correction_shell
    assert correction_shell is not None

    missing = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    build = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    loaded = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    boundary_id = build.json()["answer_key_boundary_id"]
    by_id = owner.get(f"/api/simulado-answer-key-boundary/{boundary_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_correction_shell_id"] == correction_shell.correction_shell_id
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-answer-key-boundary/{boundary_id}").status_code == 401

    assert other.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary"
    ).status_code == 404
    assert other.get(f"/api/simulado-answer-key-boundary/{boundary_id}").status_code == 404
