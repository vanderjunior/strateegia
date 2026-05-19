import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import (
    MAX_EXPLANATION_OUTLINE_LENGTH,
    MAX_SAFE_SNIPPET_LENGTH,
)
from tests.fixtures.answer_explanation_guardrails import (
    ambiguous_source_draft_fixture,
    cebraspe_assertion_draft_fixture,
    direct_multiple_choice_placeholder_fixture,
    explanation_outline_fixture,
    fgv_placeholder_mcq_draft_fixture,
    guardrail_json_keys,
    idempotency_fixture,
    long_safe_snippet_fixture,
    missing_source_draft_fixture,
    mixed_guardrail_set_fixture,
    no_final_content_safety_fixture,
    non_ready_draft_fixture,
    pscpp_technical_maritime_draft_fixture,
    unsupported_format_draft_fixture,
    user_scope_fixture,
    weak_source_draft_fixture,
)


FORBIDDEN_FINAL_KEYS = {
    "final_answer_key",
    "final_explanation",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "correction_rule",
    "auto_correction",
    "score_rule",
    "scoring_result",
    "executable_question",
    "simulado_ready_question",
    "approved_answer",
    "validated_answer",
    "final_score",
    "grading_key",
}


def build_guardrail(fixture):
    return fixture.context.service.build_guardrail(
        fixture.draft.draft_id,
        user_id=fixture.context.user_id,
    )


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


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_answer_explanation_guardrail_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = cebraspe_assertion_draft_fixture(tmp_path / "first")
    second = cebraspe_assertion_draft_fixture(tmp_path / "second")

    assert first.draft.draft_id == second.draft.draft_id
    assert first.draft_set.draft_set_id == second.draft_set.draft_set_id
    json.dumps(first.draft_set.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(build_guardrail(first).model_dump(mode="json"), ensure_ascii=True)


def test_cebraspe_fgv_pscpp_and_direct_guardrail_fixtures_cover_expected_formats(tmp_path):
    cebraspe = build_guardrail(cebraspe_assertion_draft_fixture(tmp_path / "cebraspe"))
    fgv = build_guardrail(fgv_placeholder_mcq_draft_fixture(tmp_path / "fgv"))
    pscpp = build_guardrail(pscpp_technical_maritime_draft_fixture(tmp_path / "pscpp"))
    direct = build_guardrail(direct_multiple_choice_placeholder_fixture(tmp_path / "direct"))

    assert cebraspe.candidate_answer_key.allowed_values == ["C", "E"]
    assert cebraspe.candidate_answer_key.candidate_value is None
    assert cebraspe.review_required is True
    assert cebraspe.finalization_blocked is True
    assert cebraspe.source_support_assessment.primary_source_available is True

    assert fgv.answer_key_state == "answer_key_blocked_by_ambiguous_draft"
    assert fgv.candidate_answer_key.candidate_value is None
    assert fgv.candidate_explanation.explanation_outline is not None
    assert "correct_answer" not in guardrail_json_keys(fgv.model_dump(mode="json"))

    pscpp_codes = {item.code for item in pscpp.validation_findings} | {item.code for item in pscpp.warnings}
    assert "technical_term_review_required" in pscpp_codes
    assert "source_topic_mapping_required" in pscpp_codes
    assert pscpp.candidate_answer_key.candidate_value is None
    assert pscpp.review_required is True

    assert direct.answer_key_state == "answer_key_blocked_by_ambiguous_draft"
    assert direct.candidate_answer_key.candidate_value is None
    assert direct.candidate_explanation.explanation_outline is not None


def test_guardrail_fixtures_cover_non_ready_missing_weak_ambiguous_and_unsupported_cases(tmp_path):
    non_ready = build_guardrail(non_ready_draft_fixture(tmp_path / "non-ready"))
    missing = build_guardrail(missing_source_draft_fixture(tmp_path / "missing"))
    weak = build_guardrail(weak_source_draft_fixture(tmp_path / "weak"))
    ambiguous = build_guardrail(ambiguous_source_draft_fixture(tmp_path / "ambiguous"))
    unsupported = build_guardrail(unsupported_format_draft_fixture(tmp_path / "unsupported"))

    assert non_ready.status == "blocked"
    assert non_ready.answer_key_state == "answer_key_blocked_by_non_ready_draft"
    assert non_ready.explanation_state == "explanation_blocked_by_non_ready_draft"

    assert missing.status == "blocked"
    assert missing.answer_key_state == "answer_key_blocked_by_missing_source"
    assert missing.explanation_state == "explanation_blocked_by_missing_source"
    assert missing.source_support_assessment.missing_source is True

    assert weak.answer_key_state in {
        "answer_key_needs_human_review",
        "answer_key_blocked_by_insufficient_evidence",
    }
    assert weak.explanation_state in {
        "explanation_needs_human_review",
        "explanation_blocked_by_insufficient_evidence",
    }
    assert weak.source_support_assessment.ambiguous_support is True

    assert ambiguous.status == "needs_review"
    assert ambiguous.source_support_assessment.ambiguous_support is True
    assert ambiguous.candidate_answer_key.candidate_value is None

    assert unsupported.status in {"unsupported", "blocked"}
    assert unsupported.answer_key_state == "answer_key_blocked_by_unsupported_format"
    assert unsupported.explanation_state == "explanation_blocked_by_unsupported_format"


def test_guardrail_source_support_and_explanation_outline_assertions_are_bounded(tmp_path):
    explanation_fixture = explanation_outline_fixture(tmp_path / "explanation")
    long_fixture = long_safe_snippet_fixture(tmp_path / "long")
    explanation_guardrail = build_guardrail(explanation_fixture)
    long_guardrail = build_guardrail(long_fixture)
    serialized = json.dumps(long_guardrail.model_dump(mode="json"), ensure_ascii=True)

    assert explanation_guardrail.candidate_explanation.explanation_outline is not None
    assert len(explanation_guardrail.candidate_explanation.explanation_outline) <= MAX_EXPLANATION_OUTLINE_LENGTH
    assert explanation_guardrail.candidate_explanation.source_anchor_ids
    assert explanation_guardrail.candidate_answer_key.candidate_value is None

    assert long_guardrail.source_support_assessment.safe_snippets
    assert all(len(item) <= MAX_SAFE_SNIPPET_LENGTH for item in long_guardrail.source_support_assessment.safe_snippets)
    assert long_guardrail.source_support_assessment.safe_snippets[0].endswith("…")
    assert_no_leakage(serialized)


def test_mixed_guardrail_fixture_and_no_final_content_safeguards_are_stable(tmp_path):
    mixed = mixed_guardrail_set_fixture(tmp_path / "mixed")
    guardrails = [build_guardrail(item) for item in mixed]
    payload = no_final_content_safety_fixture(tmp_path / "safety")
    dumped = build_guardrail(payload).model_dump(mode="json")

    states = {item.answer_key_state for item in guardrails}
    statuses = {item.status for item in guardrails}

    assert "answer_key_candidate_ready_for_review" in states
    assert "answer_key_blocked_by_ambiguous_draft" in states
    assert "answer_key_needs_human_review" in states
    assert "answer_key_blocked_by_missing_source" in states
    assert "answer_key_blocked_by_unsupported_format" in states
    assert "ready_for_review" in statuses
    assert "needs_review" in statuses
    assert "blocked" in statuses or "unsupported" in statuses
    assert dumped["review_required"] is True
    assert dumped["finalization_blocked"] is True
    assert dumped["no_final_answer_key_generated"] is True
    assert dumped["no_final_explanation_generated"] is True
    assert dumped["no_simulado_execution_enabled"] is True
    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in guardrail_json_keys(dumped)
    json.dumps(dumped, ensure_ascii=True)


def test_guardrail_persistence_and_idempotency_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    first = build_guardrail(fixture)
    second = build_guardrail(fixture)
    by_source = fixture.context.repository.get_answer_explanation_guardrail(
        fixture.draft.draft_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_answer_explanation_guardrail_by_id(
        first.guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_answer_explanation_guardrails(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1


def test_guardrail_api_owner_only_read_only_and_user_scope_are_preserved(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture, _ = user_scope_fixture(tmp_path / "scope", repository=repository)
    owner_fixture = cebraspe_assertion_draft_fixture(
        tmp_path / "owner-api",
        user_id=owner_user_id,
        repository=repository,
    )
    draft_id = owner_fixture.draft.draft_id

    missing = owner.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail")
    before_list = repository.list_user_answer_explanation_guardrails(user_id=owner_user_id)
    build = owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build")
    guardrail_id = build.json()["guardrail_id"]
    after_build_list = repository.list_user_answer_explanation_guardrails(user_id=owner_user_id)
    loaded = owner.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail")
    by_id = owner.get(f"/api/answer-explanation-guardrail/{guardrail_id}")
    after_get_list = repository.list_user_answer_explanation_guardrails(user_id=owner_user_id)
    dumped = json.dumps(by_id.json(), ensure_ascii=True)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build").json() == build.json()
    assert anonymous.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build").status_code == 401
    assert anonymous.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail").status_code == 401
    assert anonymous.get(f"/api/answer-explanation-guardrail/{guardrail_id}").status_code == 401
    assert other.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build").status_code == 404
    assert other.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail").status_code == 404
    assert other.get(f"/api/answer-explanation-guardrail/{guardrail_id}").status_code == 404
    assert_no_leakage(dumped)


def test_guardrail_build_and_get_do_not_mutate_source_drafts(tmp_path):
    fixture = cebraspe_assertion_draft_fixture(tmp_path)
    before = fixture.context.repository.get_question_draft_set(
        fixture.draft_set.source_question_generation_blueprint_set_id,
        user_id=fixture.context.user_id,
    )

    built = build_guardrail(fixture)
    loaded = fixture.context.service.get_guardrail(
        fixture.draft.draft_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.service.get_guardrail_by_id(
        built.guardrail_id,
        user_id=fixture.context.user_id,
    )
    after = fixture.context.repository.get_question_draft_set(
        fixture.draft_set.source_question_generation_blueprint_set_id,
        user_id=fixture.context.user_id,
    )

    assert loaded is not None
    assert by_id is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
