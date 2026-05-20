import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_progress_guardrails import (
    api_readonly_fixture,
    build_progress_guardrail,
    candidate_progress_target_shape_fixture,
    incomplete_score_fixture,
    missing_policy_confirmation_fixture,
    missing_score_result_fixture,
    missing_topic_mapping_fixture,
    mixed_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    no_scoreable_items_fixture,
    runtime_mutation_disabled_fixture,
    score_completeness_assessment_fixture,
    score_needs_review_fixture,
    user_scope_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_STABILIZATION_KEYS = {
    "password_hash",
    "studyflow_session",
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "raw_runtime_block",
    "final_question_content",
    "final_explanation_content",
    "progress_applied",
    "ranking_applied",
    "retention_applied",
    "scheduler_applied",
    "study_cycle_applied",
    "curriculum_graph_applied",
    "adaptive_tuning_applied",
    "final_result_applied",
}

ALLOWED_TARGET_TYPES = {"topic", "subtopic", "microtopic", "subject", "simulado", "unknown"}


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


def _create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def test_progress_guardrail_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    result = build_progress_guardrail(no_scoreable_items_fixture(tmp_path / "fixture-sanity"))
    assert result is not None

    dumped = result.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert isinstance(dumped, dict)
    assert dumped["metadata"]["build_method"] == "heuristic_simulado_progress_guardrail_builder"
    assert dumped["metadata"]["llm_used"] is False
    assert dumped["metadata"]["external_calls_used"] is False
    assert "data:image" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_progress_guardrail_stabilization_covers_missing_no_scoreable_and_incomplete_score(tmp_path):
    missing = missing_score_result_fixture(tmp_path / "missing")
    no_scoreable = build_progress_guardrail(no_scoreable_items_fixture(tmp_path / "no-scoreable"))
    incomplete = build_progress_guardrail(incomplete_score_fixture(tmp_path / "incomplete"))

    assert build_progress_guardrail(missing) is None

    assert no_scoreable is not None
    assert no_scoreable.status == "progress_guardrail_blocked"
    assert no_scoreable.readiness_state == "blocked_by_no_scoreable_items"
    assert no_scoreable.eligibility.eligible_for_future_progress_mutation is False
    assert no_scoreable.score_completeness.enough_data_for_progress_update is False

    assert incomplete is not None
    incomplete_codes = {item.code for item in incomplete.blockers}
    assert "blocked_by_incomplete_score" in incomplete_codes
    assert incomplete.score_completeness.score_complete is False
    assert incomplete.score_completeness.enough_data_for_progress_update is False


def test_progress_guardrail_stabilization_covers_needs_review_missing_mapping_and_policy_confirmation(tmp_path):
    needs_review = build_progress_guardrail(score_needs_review_fixture(tmp_path / "needs-review"))
    missing_mapping = build_progress_guardrail(missing_topic_mapping_fixture(tmp_path / "missing-mapping"))
    missing_policy = build_progress_guardrail(
        missing_policy_confirmation_fixture(tmp_path / "missing-policy-confirmation")
    )

    assert needs_review is not None
    assert needs_review.status in {"progress_guardrail_blocked", "progress_guardrail_needs_review"}
    assert needs_review.readiness_state in {
        "blocked_by_no_scoreable_items",
        "blocked_by_incomplete_score",
        "blocked_by_score_needs_review",
    }
    assert needs_review.eligibility.requires_human_review in {False, True}
    assert needs_review.progress_mutation_enabled is False

    assert missing_mapping is not None
    assert missing_mapping.candidate_progress_targets
    for target in missing_mapping.candidate_progress_targets:
        assert "target_blocked_by_missing_mapping" in target.blockers
        assert target.target_available is False
        assert target.update_applied is False

    assert missing_policy is not None
    assert missing_policy.eligibility.requires_policy_confirmation is True
    assert "blocked_by_missing_policy_confirmation" in {item.code for item in missing_policy.blockers}


def test_progress_guardrail_stabilization_covers_runtime_mutation_disabled_and_candidate_shape(tmp_path):
    runtime_disabled = build_progress_guardrail(runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled"))
    target_shape = build_progress_guardrail(candidate_progress_target_shape_fixture(tmp_path / "target-shape"))

    assert runtime_disabled is not None
    runtime_codes = {item.code for item in runtime_disabled.blockers}
    assert "blocked_by_runtime_mutation_disabled" in runtime_codes
    assert runtime_disabled.progress_mutation_enabled is False
    assert runtime_disabled.ranking_mutation_enabled is False
    assert runtime_disabled.retention_mutation_enabled is False
    assert runtime_disabled.scheduler_mutation_enabled is False
    assert runtime_disabled.study_cycle_mutation_enabled is False
    assert runtime_disabled.curriculum_graph_mutation_enabled is False
    assert runtime_disabled.adaptive_tuning_enabled is False
    assert runtime_disabled.no_progress_mutation is True
    assert runtime_disabled.no_ranking_update is True
    assert runtime_disabled.no_retention_update is True
    assert runtime_disabled.no_scheduler_update is True
    assert runtime_disabled.no_study_cycle_update is True
    assert runtime_disabled.no_curriculum_graph_update is True
    assert runtime_disabled.no_adaptive_tuning_update is True

    assert target_shape is not None
    assert target_shape.candidate_progress_targets
    for target in target_shape.candidate_progress_targets:
        assert target.target_type in ALLOWED_TARGET_TYPES
        assert target.future_update_allowed is False
        assert target.update_applied is False
        assert target.proposed_update_kind == "no_update_applied"


def test_progress_guardrail_stabilization_covers_score_completeness_mixed_counts_and_safety(tmp_path):
    completeness = build_progress_guardrail(score_completeness_assessment_fixture(tmp_path / "completeness"))
    mixed = build_progress_guardrail(mixed_guardrail_fixture(tmp_path / "mixed"))
    safety = build_progress_guardrail(no_public_key_gabarito_safety_fixture(tmp_path / "safety"))

    assert completeness is not None
    assert completeness.score_completeness.total_items >= 0
    assert completeness.score_completeness.scored_items >= 0
    assert completeness.score_completeness.scoreable_items >= 0
    assert completeness.score_completeness.blocked_items >= 0
    assert completeness.score_completeness.blank_items >= 0
    assert completeness.score_completeness.unsupported_items >= 0
    assert completeness.score_completeness.raw_score == 0.0
    assert completeness.score_completeness.max_score == 0.0
    assert completeness.score_completeness.percentage_score is None
    assert completeness.score_completeness.enough_data_for_progress_update is False

    assert mixed is not None
    assert len(mixed.candidate_progress_targets) == mixed.score_completeness.total_items
    assert mixed.score_completeness.total_items >= mixed.score_completeness.unsupported_items
    assert mixed.score_completeness.total_items >= mixed.score_completeness.blank_items

    assert safety is not None
    dumped_payload = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert safety.answer_key_publicly_exposed is False
    assert safety.gabarito_publicly_exposed is False
    for key in FORBIDDEN_STABILIZATION_KEYS:
        assert key not in dumped_keys
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "data:image" not in dumped_text


def test_progress_guardrail_stabilization_preserves_persistence_and_idempotency(tmp_path):
    fixture = no_scoreable_items_fixture(tmp_path)
    result = build_progress_guardrail(fixture)
    assert result is not None

    score_result = fixture.score_result
    assert score_result is not None
    repository = fixture.context.repository

    again = build_progress_guardrail(fixture)
    by_source = repository.get_simulado_progress_guardrail(
        score_result.score_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_progress_guardrail_by_id(
        result.progress_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_progress_guardrails(user_id=fixture.context.user_id)

    assert again is not None
    assert by_source is not None
    assert by_id is not None
    assert result.model_dump(mode="json") == again.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert len(listed) == 1


def test_progress_guardrail_stabilization_api_owner_only_and_read_only_behaviour(tmp_path):
    owner_client, other_client, anonymous_client, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner_client, "owner")
    _register_and_login(other_client, "other")

    owner_fixture = api_readonly_fixture(tmp_path / "owner-fixture", user_id=owner_user_id, repository=repository)
    score_result = owner_fixture.score_result
    assert score_result is not None

    missing_get = owner_client.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    before = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=owner_user_id,
    )
    build = owner_client.post(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build")
    loaded = owner_client.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    progress_guardrail_id = build.json()["progress_guardrail_id"]
    by_id = owner_client.get(f"/api/simulado-progress-guardrail/{progress_guardrail_id}")
    after = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=owner_user_id,
    )

    assert missing_get.status_code == 404
    assert before is not None and after is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
    assert anonymous_client.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    ).status_code == 401
    assert anonymous_client.get(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail"
    ).status_code == 401
    assert other_client.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    ).status_code == 404
    assert other_client.get(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail"
    ).status_code == 404
    assert other_client.get(f"/api/simulado-progress-guardrail/{progress_guardrail_id}").status_code == 404
