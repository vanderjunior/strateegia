import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
from tests.fixtures.simulado_attempt_sessions import (
    build_attempt_session,
    idempotency_fixture,
    no_progress_mutation_fixture,
    prepared_items_non_submittable_fixture,
)


FORBIDDEN_SUBMISSION_KEYS = {
    "correction_result",
    "correct_answer",
    "correct_option",
    "gabarito",
    "score",
    "grade",
    "simulado_result",
    "score_rule",
    "correction_rule",
    "is_correct",
    "points_awarded",
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


def build_submission_from_fixture(fixture, payload):
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    return SimuladoAnswerSubmissionService(fixture.context.repository).build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload=payload,
    )


def first_session_item_id(fixture):
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    return attempt_session.items[0].item_id


def test_simulado_answer_submission_handles_missing_attempt_session_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoAnswerSubmissionService(repository)

    assert service.build_answer_submission(
        "simulado-attempt-session:missing",
        user_id="user-a",
        submission_payload={"answers": []},
    ) is None
    assert repository.list_user_simulado_answer_submissions(user_id="user-a") == []


def test_simulado_answer_submission_records_structural_selected_option_and_true_false_without_correction(tmp_path):
    fixture = prepared_items_non_submittable_fixture(tmp_path)
    item_id = first_session_item_id(fixture)

    selected = build_submission_from_fixture(
        fixture,
        {
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    assert selected is not None
    assert selected.submission_recorded is True
    assert selected.correction_enabled is False
    assert selected.scoring_enabled is False
    assert selected.progress_mutation_enabled is False
    assert selected.no_correction_result_created is True
    assert selected.no_score_created is True
    assert selected.no_progress_mutation is True
    assert selected.submitted_answer_count == 1
    answer = selected.submitted_answers[0]
    assert answer.answer_kind == "selected_option"
    assert answer.submitted_value == "A"
    assert answer.validation_state == "structurally_valid"

    true_false = build_submission_from_fixture(
        fixture,
        {
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "true_false_value",
                    "submitted_value": "C",
                }
            ]
        },
    )
    assert true_false is not None
    assert true_false.submitted_answers[0].answer_kind == "true_false_value"
    assert true_false.submitted_answers[0].submitted_value == "C"
    assert true_false.submitted_answers[0].validation_state == "structurally_valid"


def test_simulado_answer_submission_handles_blank_short_text_unknown_duplicate_and_unsupported_answers_deterministically(tmp_path):
    fixture = prepared_items_non_submittable_fixture(tmp_path)
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    item_id = attempt_session.items[0].item_id

    blank = build_submission_from_fixture(
        fixture,
        {
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "blank",
                }
            ]
        },
    )
    assert blank is not None
    assert blank.submitted_answers[0].is_blank is True
    assert blank.submitted_answers[0].validation_state == "blank_answer"

    long_text = "x" * 1300
    short_text = build_submission_from_fixture(
        fixture,
        {
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "short_text",
                    "submitted_value": long_text,
                }
            ]
        },
    )
    assert short_text is not None
    assert short_text.submitted_answers[0].answer_kind == "short_text"
    assert short_text.submitted_answers[0].submitted_value is not None
    assert len(short_text.submitted_answers[0].submitted_value) <= 1000
    assert short_text.submitted_answers[0].validation_state == "structurally_valid"

    mixed = build_submission_from_fixture(
        fixture,
        {
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "B",
                },
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "C",
                },
                {
                    "source_session_item_id": "unknown-item",
                    "answer_kind": "selected_option",
                    "submitted_value": "D",
                },
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "unsupported_kind",
                    "submitted_value": "Z",
                },
            ]
        },
    )
    assert mixed is not None
    assert mixed.duplicate_answer_count == 1
    assert mixed.invalid_answer_count >= 2
    warning_codes = {item.code for item in mixed.warnings}
    finding_codes = {item.code for item in mixed.validation_findings}
    assert "duplicate_answer" in warning_codes or "duplicate_answer" in finding_codes
    assert "unknown_session_item" in finding_codes
    assert "unsupported_answer_kind" in finding_codes


def test_simulado_answer_submission_preserves_no_progress_mutation_no_correction_no_score_and_idempotency(tmp_path):
    fixture = no_progress_mutation_fixture(tmp_path)
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    item_id = attempt_session.items[0].item_id
    service = SimuladoAnswerSubmissionService(fixture.context.repository)
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    first = service.build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload=payload,
    )
    second = service.build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload=payload,
    )
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_answer_submission_by_id(
        first.answer_submission_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_answer_submissions(
        user_id=fixture.context.user_id
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
    for key in FORBIDDEN_SUBMISSION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_simulado_answer_submission_handles_different_payloads_deterministically(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    attempt_session = build_attempt_session(fixture)
    assert attempt_session is not None
    item_id = attempt_session.items[0].item_id
    service = SimuladoAnswerSubmissionService(fixture.context.repository)

    first = service.build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    second = service.build_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
        submission_payload={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "B",
                }
            ]
        },
    )
    latest = service.get_answer_submission(
        attempt_session.attempt_session_id,
        user_id=fixture.context.user_id,
    )

    assert first is not None
    assert second is not None
    assert latest is not None
    assert first.model_dump(mode="json") != second.model_dump(mode="json")
    assert latest.model_dump(mode="json") == second.model_dump(mode="json")
