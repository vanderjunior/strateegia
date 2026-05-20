from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAnswerSubmission, SimuladoAttemptSession
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
from tests.fixtures.simulado_attempt_sessions import (
    SimuladoAttemptSessionFixture,
    bounded_summary_fixture as _bounded_summary_fixture,
    build_attempt_session,
    idempotency_fixture as _idempotency_fixture,
    no_correction_scoring_safety_fixture as _no_correction_scoring_safety_fixture,
    no_progress_mutation_fixture as _no_progress_mutation_fixture,
    ordering_stability_fixture as _ordering_stability_fixture,
    prepared_items_non_submittable_fixture as _prepared_items_non_submittable_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoAnswerSubmissionFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoAnswerSubmissionService
    user_id: str


@dataclass
class SimuladoAnswerSubmissionFixture:
    context: SimuladoAnswerSubmissionFixtureContext
    attempt_session_fixture: SimuladoAttemptSessionFixture | None
    attempt_session: SimuladoAttemptSession | None
    submission_payload: dict[str, object] | None = None
    missing_attempt_session_id: str | None = None
    alternate_submission_payload: dict[str, object] | None = None


def _wrap_fixture(
    attempt_session_fixture: SimuladoAttemptSessionFixture,
    *,
    submission_payload: dict[str, object] | None = None,
    alternate_submission_payload: dict[str, object] | None = None,
) -> SimuladoAnswerSubmissionFixture:
    attempt_session = build_attempt_session(attempt_session_fixture)
    assert attempt_session is not None
    return SimuladoAnswerSubmissionFixture(
        context=SimuladoAnswerSubmissionFixtureContext(
            repository=attempt_session_fixture.context.repository,
            service=SimuladoAnswerSubmissionService(attempt_session_fixture.context.repository),
            user_id=attempt_session_fixture.context.user_id,
        ),
        attempt_session_fixture=attempt_session_fixture,
        attempt_session=attempt_session,
        submission_payload=submission_payload,
        alternate_submission_payload=alternate_submission_payload,
    )


def build_answer_submission(
    fixture: SimuladoAnswerSubmissionFixture,
    payload: dict[str, object] | None = None,
) -> SimuladoAnswerSubmission | None:
    source_id = fixture.missing_attempt_session_id
    if fixture.attempt_session is not None:
        source_id = fixture.attempt_session.attempt_session_id
    assert source_id is not None
    return fixture.context.service.build_answer_submission(
        source_id,
        user_id=fixture.context.user_id,
        submission_payload=payload if payload is not None else fixture.submission_payload,
    )


def first_session_item_id(fixture: SimuladoAnswerSubmissionFixture) -> str:
    assert fixture.attempt_session is not None
    return fixture.attempt_session.items[0].item_id


def second_session_item_id(fixture: SimuladoAnswerSubmissionFixture) -> str:
    assert fixture.attempt_session is not None
    assert len(fixture.attempt_session.items) > 1
    return fixture.attempt_session.items[1].item_id


def missing_attempt_session_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    repository = repository or JsonStudyRepository(tmp_path / "study_data.json")
    return SimuladoAnswerSubmissionFixture(
        context=SimuladoAnswerSubmissionFixtureContext(
            repository=repository,
            service=SimuladoAnswerSubmissionService(repository),
            user_id=user_id,
        ),
        attempt_session_fixture=None,
        attempt_session=None,
        submission_payload={"answers": []},
        missing_attempt_session_id="simulado-attempt-session:missing",
    )


def selected_option_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return wrapped


def true_false_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "true_false_value",
                "submitted_value": "C",
            }
        ]
    }
    return wrapped


def blank_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "blank",
            }
        ]
    }
    return wrapped


def short_text_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "short_text",
                "submitted_value": "Texto <seguro> e objetivo.",
            }
        ]
    }
    return wrapped


def long_short_text_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _bounded_summary_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "short_text",
                "submitted_value": "<script>alert('x')</script>" + ("x" * 1300),
            }
        ]
    }
    return wrapped


def unknown_item_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": "unknown-item",
                "answer_kind": "selected_option",
                "submitted_value": "D",
            }
        ]
    }
    return wrapped


def duplicate_answer_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
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
        ]
    }
    return wrapped


def unsupported_answer_kind_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "unsupported_kind",
                "submitted_value": "Z",
            }
        ]
    }
    return wrapped


def partial_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _ordering_stability_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return wrapped


def empty_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    return _wrap_fixture(
        _ordering_stability_fixture(tmp_path, user_id=user_id, repository=repository),
        submission_payload={"answers": []},
    )


def same_payload_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _idempotency_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return wrapped


def different_payload_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _idempotency_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    wrapped.alternate_submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "B",
            }
        ]
    }
    return wrapped


def no_correction_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _no_correction_scoring_safety_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "short_text",
                "submitted_value": "<script>alert('x')</script>",
            }
        ]
    }
    return wrapped


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _no_progress_mutation_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return wrapped


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoAnswerSubmissionFixture, SimuladoAnswerSubmissionFixture]:
    owner_fixture, other_fixture = _user_scope_fixture(tmp_path, repository=repository)
    owner = _wrap_fixture(owner_fixture)
    other = _wrap_fixture(other_fixture)
    item_id = first_session_item_id(owner)
    owner.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    other.submission_payload = {
        "answers": [
            {
                "source_session_item_id": first_session_item_id(other),
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return owner, other


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerSubmissionFixture:
    wrapped = _wrap_fixture(
        _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository),
    )
    item_id = first_session_item_id(wrapped)
    wrapped.submission_payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    return wrapped
