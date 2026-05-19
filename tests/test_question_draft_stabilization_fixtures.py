import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.question_draft_generation import (
    MAX_COMMAND_LENGTH,
    MAX_OPTION_PLACEHOLDER_LENGTH,
    MAX_SAFE_SNIPPET_LENGTH,
    MAX_SCENARIO_LENGTH,
    MAX_STATEMENT_LENGTH,
    MAX_STEM_LENGTH,
    QuestionDraftGenerationService,
)
from tests.fixtures.question_drafts import (
    long_snippet_bounds_fixture,
    mixed_draft_set_fixture,
    missing_source_evidence_fixture,
    no_final_content_safety_fixture,
    no_ready_blueprints_fixture,
    non_ready_blueprint_fixture,
    ready_cebraspe_assertion_blueprint_fixture,
    ready_direct_multiple_choice_blueprint_fixture,
    ready_fgv_case_mcq_blueprint_fixture,
    ready_pscpp_maritime_blueprint_fixture,
    source_review_needed_fixture,
    unsupported_question_kind_fixture,
)
from tests.fixtures.question_generation_blueprints import collect_keys


FORBIDDEN_FINAL_KEYS = {
    "final_question_text",
    "final_stem",
    "final_statement",
    "final_options",
    "alternatives",
    "final_alternatives",
    "distractors",
    "answer",
    "answer_key",
    "correct_answer",
    "gabarito",
    "explanation",
    "final_explanation",
    "correction",
    "scoring_result",
}


def _build(fixture):
    return fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )


def _assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def _assert_no_final_content(payload: dict[str, object]) -> None:
    keys = collect_keys(payload)
    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in keys


def _create_clients(tmp_path: Path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def _register_and_login(client: TestClient, username: str) -> str:
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


def test_question_draft_fixtures_are_deterministic_and_json_safe(tmp_path):
    fixture_a = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "first")
    fixture_b = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "second")

    assert fixture_a.blueprint_set.blueprint_set_id == fixture_b.blueprint_set.blueprint_set_id
    assert fixture_a.blueprint_set.slot_blueprints[0].blueprint_id == fixture_b.blueprint_set.slot_blueprints[0].blueprint_id
    json.dumps(fixture_a.blueprint_set.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(mixed_draft_set_fixture(tmp_path / "mixed").blueprint_set.model_dump(mode="json"), ensure_ascii=True)


def test_cebraspe_fgv_pscpp_and_direct_draft_fixtures_create_review_required_drafts(tmp_path):
    cebraspe = _build(ready_cebraspe_assertion_blueprint_fixture(tmp_path / "cebraspe"))
    fgv = _build(ready_fgv_case_mcq_blueprint_fixture(tmp_path / "fgv"))
    pscpp = _build(ready_pscpp_maritime_blueprint_fixture(tmp_path / "pscpp"))
    direct = _build(ready_direct_multiple_choice_blueprint_fixture(tmp_path / "direct"))

    assertion_draft = cebraspe.drafts[0]
    assert assertion_draft.question_kind == "assertion_judgement"
    assert assertion_draft.draft_stem
    assert assertion_draft.draft_command
    assert assertion_draft.draft_statement
    assert assertion_draft.source_references
    assert assertion_draft.review_required is True
    assert assertion_draft.finalization_blocked is True
    assert assertion_draft.validation_summary.source_grounded is True
    assert "Correto" not in (assertion_draft.draft_statement or "")
    assert "Errado" not in (assertion_draft.draft_statement or "")

    fgv_draft = fgv.drafts[0]
    assert fgv_draft.question_kind == "case_based_multiple_choice"
    assert fgv_draft.draft_scenario
    assert len(fgv_draft.draft_option_placeholders) == 5
    assert all(item.startswith("Placeholder ") for item in fgv_draft.draft_option_placeholders)
    assert all("alternativa futura" in item for item in fgv_draft.draft_option_placeholders)
    assert all(len(item) <= MAX_OPTION_PLACEHOLDER_LENGTH for item in fgv_draft.draft_option_placeholders)

    pscpp_draft = pscpp.drafts[0]
    assert pscpp_draft.question_kind == "technical_maritime_scenario"
    assert pscpp_draft.draft_scenario
    assert "tecnico-maritimo" in pscpp_draft.draft_scenario.lower()
    assert any(item.code == "maritime_draft_requires_review" for item in pscpp_draft.warnings)

    direct_draft = direct.drafts[0]
    assert direct_draft.question_kind == "direct_multiple_choice"
    assert direct_draft.draft_stem
    assert direct_draft.draft_command
    assert direct_draft.draft_option_placeholders
    assert direct_draft.draft_statement is None


def test_question_draft_stabilization_blocks_unsupported_non_ready_and_missing_source_inputs(tmp_path):
    unsupported = _build(unsupported_question_kind_fixture(tmp_path / "unsupported"))
    non_ready = _build(non_ready_blueprint_fixture(tmp_path / "non-ready"))
    missing_source = _build(missing_source_evidence_fixture(tmp_path / "missing-source"))

    assert unsupported.draft_count == 0
    assert unsupported.blocked_count == 1
    assert unsupported.skipped_blueprint_ids

    assert non_ready.draft_count == 0
    assert non_ready.readiness_state in {"needs_review", "no_ready_blueprints"}
    assert non_ready.needs_review_count == 1
    assert non_ready.skipped_blueprint_ids

    assert missing_source.draft_count == 0
    assert missing_source.blocked_count == 1
    assert missing_source.readiness_state in {"blocked", "no_ready_blueprints"}
    assert missing_source.skipped_blueprint_ids


def test_question_draft_source_review_fixture_stays_conservative(tmp_path):
    result = _build(source_review_needed_fixture(tmp_path))
    draft = result.drafts[0]

    assert result.draft_count == 1
    assert draft.draft_status == "needs_review"
    assert draft.draft_readiness == "needs_source_review"
    assert draft.source_references
    assert draft.source_references[0].safe_snippet is None
    assert any(item.code == "safe_snippet_missing" for item in draft.warnings)


def test_question_draft_mixed_and_no_ready_sets_have_stable_counts(tmp_path):
    mixed = _build(mixed_draft_set_fixture(tmp_path / "mixed"))
    no_ready = _build(no_ready_blueprints_fixture(tmp_path / "no-ready"))

    assert mixed.readiness_state == "partially_created"
    assert mixed.total_blueprint_slots == 6
    assert mixed.draft_count == 3
    assert mixed.blocked_count == 2
    assert mixed.needs_review_count == 1
    assert len(mixed.skipped_blueprint_ids) == 3

    assert no_ready.readiness_state == "no_ready_blueprints"
    assert no_ready.total_blueprint_slots == 2
    assert no_ready.draft_count == 0
    assert no_ready.skipped_blueprint_ids


def test_question_draft_bounds_and_source_grounding_are_enforced(tmp_path):
    result = _build(long_snippet_bounds_fixture(tmp_path))
    draft = result.drafts[0]
    serialized = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)

    assert len(draft.draft_stem or "") <= MAX_STEM_LENGTH
    assert len(draft.draft_command or "") <= MAX_COMMAND_LENGTH
    assert len(draft.draft_scenario or "") <= MAX_SCENARIO_LENGTH
    assert all(len(item) <= MAX_OPTION_PLACEHOLDER_LENGTH for item in draft.draft_option_placeholders)
    assert draft.validation_summary.source_grounded is True
    assert draft.validation_summary.has_required_source_evidence is True
    assert draft.provenance.source_evidence_count > 0
    assert draft.source_references[0].safe_snippet is not None
    assert len(draft.source_references[0].safe_snippet) <= MAX_SAFE_SNIPPET_LENGTH
    assert "conteudo conteudo conteudo conteudo conteudo conteudo conteudo conteudo conteudo conteudo" not in serialized
    _assert_no_leakage(serialized)


def test_question_draft_payloads_keep_no_final_content_guarantees(tmp_path):
    result = _build(no_final_content_safety_fixture(tmp_path))
    dumped = result.model_dump(mode="json")
    serialized = json.dumps(dumped, ensure_ascii=True)

    assert result.no_final_question_generated is True
    assert result.no_answer_key_generated is True
    assert result.no_final_alternatives_generated is True
    assert result.no_distractors_generated is True
    assert result.no_final_explanations_generated is True
    assert all(item.review_required is True for item in result.drafts)
    assert all(item.finalization_blocked is True for item in result.drafts)
    _assert_no_final_content(dumped)
    _assert_no_leakage(serialized)


def test_question_draft_persistence_and_idempotency_are_stable(tmp_path):
    fixture = mixed_draft_set_fixture(tmp_path)
    first = _build(fixture)
    second = _build(fixture)
    by_source = fixture.context.repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_question_draft_set_by_id(
        first.draft_set_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_question_draft_sets(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1


def test_question_draft_api_owner_only_and_get_read_only_behavior(tmp_path):
    owner, other, anonymous, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    fixture = ready_fgv_case_mcq_blueprint_fixture(
        tmp_path / "api-owner",
        user_id=owner_user_id,
        repository=repository,
    )
    blueprint_set_id = fixture.blueprint_set.blueprint_set_id

    missing = owner.get(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts")
    before_list = repository.list_user_question_draft_sets(user_id=owner_user_id)
    build = owner.post(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts/build")
    draft_set_id = build.json()["draft_set_id"]
    after_build_list = repository.list_user_question_draft_sets(user_id=owner_user_id)
    loaded = owner.get(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts")
    by_id = owner.get(f"/api/question-draft-set/{draft_set_id}")
    after_get_list = repository.list_user_question_draft_sets(user_id=owner_user_id)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert owner.post(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts/build").json() == build.json()
    assert anonymous.post(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts/build").status_code == 401
    assert anonymous.get(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts").status_code == 401
    assert anonymous.get(f"/api/question-draft-set/{draft_set_id}").status_code == 401
    assert other.post(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts/build").status_code == 404
    assert other.get(f"/api/question-generation-blueprint/{blueprint_set_id}/question-drafts").status_code == 404
    assert other.get(f"/api/question-draft-set/{draft_set_id}").status_code == 404


def test_question_draft_api_responses_are_json_safe_and_do_not_mutate_sources(tmp_path):
    owner, _, _, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner, "owner")
    fixture = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "api-security",
        user_id=owner_user_id,
        repository=repository,
    )
    service = QuestionDraftGenerationService(repository)
    before_blueprint = repository.get_question_generation_blueprint_by_id(
        fixture.blueprint_set.blueprint_set_id,
        user_id=owner_user_id,
    )

    built = owner.post(
        f"/api/question-generation-blueprint/{fixture.blueprint_set.blueprint_set_id}/question-drafts/build"
    )
    loaded = owner.get(
        f"/api/question-generation-blueprint/{fixture.blueprint_set.blueprint_set_id}/question-drafts"
    )
    after_blueprint = repository.get_question_generation_blueprint_by_id(
        fixture.blueprint_set.blueprint_set_id,
        user_id=owner_user_id,
    )
    direct_load = service.get_draft_set(fixture.blueprint_set.blueprint_set_id, user_id=owner_user_id)
    dumped = built.json()
    serialized = json.dumps(dumped, ensure_ascii=True)

    assert built.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json() == dumped
    assert direct_load is not None
    assert before_blueprint.model_dump(mode="json") == after_blueprint.model_dump(mode="json")
    _assert_no_final_content(dumped)
    _assert_no_leakage(serialized)
