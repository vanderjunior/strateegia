import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_scoring_results import (
    api_readonly_fixture,
    blank_answer_score_fixture,
    blocked_records_fixture,
    build_score_result,
    empty_correction_result_fixture,
    invalid_submission_fixture,
    missing_correction_result_fixture,
    missing_score_policy_fixture,
    mixed_score_result_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    no_scoreable_records_fixture,
    safe_policy_snapshot_fixture,
    score_summary_fixture,
    unsupported_answer_kind_fixture,
    user_scope_fixture,
)


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
    "progress_update",
    "ranking_update",
    "retention_update",
    "scheduler_update",
    "final_result_applied",
}


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


def test_scoring_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    result = build_score_result(no_scoreable_records_fixture(tmp_path / "first"))
    assert result is not None

    dumped = result.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert isinstance(dumped, dict)
    assert dumped["metadata"]["build_method"] == "heuristic_simulado_scoring_builder"
    assert dumped["metadata"]["llm_used"] is False
    assert dumped["metadata"]["external_calls_used"] is False
    assert "data:image" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text


def test_scoring_stabilization_covers_missing_empty_and_no_scoreable_records(tmp_path):
    missing = missing_correction_result_fixture(tmp_path / "missing")
    empty = build_score_result(empty_correction_result_fixture(tmp_path / "empty"))
    no_scoreable = build_score_result(no_scoreable_records_fixture(tmp_path / "no-scoreable"))

    assert build_score_result(missing) is None

    for result in (empty, no_scoreable):
        assert result is not None
        assert result.status == "score_result_blocked"
        assert result.readiness_state == "blocked_by_no_scoreable_correction_records"
        assert result.scoreable_item_count == 0
        assert result.scored_item_count == 0
        assert result.score_summary.percentage_score is None
        assert result.score_summary.no_scoreable_items is True
        assert result.progress_mutation_enabled is False
        assert result.ranking_mutation_enabled is False
        assert result.retention_mutation_enabled is False
        assert result.scheduler_mutation_enabled is False
        assert result.study_cycle_mutation_enabled is False
        assert result.curriculum_graph_mutation_enabled is False
        assert result.no_progress_mutation is True
        assert result.no_ranking_update is True
        assert result.no_retention_update is True
        assert result.no_scheduler_update is True
        assert result.no_study_cycle_update is True
        assert result.no_curriculum_graph_update is True


def test_scoring_stabilization_covers_blocked_blank_unsupported_and_invalid_records(tmp_path):
    blocked = build_score_result(blocked_records_fixture(tmp_path / "blocked"))
    blank = build_score_result(blank_answer_score_fixture(tmp_path / "blank"))
    unsupported = build_score_result(unsupported_answer_kind_fixture(tmp_path / "unsupported"))
    invalid = build_score_result(invalid_submission_fixture(tmp_path / "invalid"))

    assert blocked is not None
    assert blocked.item_records[0].score_state == "item_blocked_by_missing_correction_state"
    assert blocked.item_records[0].scoreable is False
    assert blocked.item_records[0].scored is False
    assert blocked.item_records[0].points_awarded == 0.0

    assert blank is not None
    assert blank.item_records[0].score_state == "item_blank_not_scored"
    assert blank.item_records[0].scoreable is False
    assert blank.item_records[0].points_awarded == 0.0
    assert blank.score_policy.blank_penalty_enabled is False

    assert unsupported is not None
    assert unsupported.item_records[0].score_state == "item_blocked_by_unsupported_answer_kind"
    assert unsupported.unsupported_item_count == 1

    assert invalid is not None
    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert invalid.total_answer_records == 0
    assert "blocked_by_invalid_submission" in invalid_codes or "unknown_session_item" in invalid_codes


def test_scoring_stabilization_covers_missing_policy_snapshot_and_summary_behaviour(tmp_path):
    missing_policy = build_score_result(missing_score_policy_fixture(tmp_path / "missing-policy"))
    safe_policy = build_score_result(safe_policy_snapshot_fixture(tmp_path / "policy"))
    summary = build_score_result(score_summary_fixture(tmp_path / "summary"))

    assert missing_policy is not None
    assert "blocked_by_missing_score_policy" in {item.code for item in missing_policy.blockers}
    assert missing_policy.score_policy.policy_available is False
    assert missing_policy.score_policy.negative_marking_enabled is False
    assert missing_policy.score_policy.blank_penalty_enabled is False

    assert safe_policy is not None
    assert safe_policy.score_policy.policy_available is False
    assert safe_policy.score_policy.policy_source is None
    assert safe_policy.score_policy.negative_marking_enabled is False
    assert safe_policy.score_policy.blank_penalty_enabled is False
    assert safe_policy.score_policy.unsupported_items_scoreable is False

    assert summary is not None
    assert summary.score_summary.raw_score == 0.0
    assert summary.score_summary.max_score == 0.0
    assert summary.score_summary.percentage_score is None
    assert summary.score_summary.score_computable is False
    assert summary.score_summary.score_complete is False
    assert summary.score_summary.score_partial is False
    assert "passed" not in assembly_json_keys(summary.model_dump(mode="json"))
    assert "failed" not in assembly_json_keys(summary.model_dump(mode="json"))


def test_scoring_stabilization_covers_mixed_result_safety_and_runtime_isolation(tmp_path):
    mixed = build_score_result(mixed_score_result_fixture(tmp_path / "mixed"))
    safety = build_score_result(no_public_key_gabarito_safety_fixture(tmp_path / "safety"))
    runtime = build_score_result(no_runtime_mutation_fixture(tmp_path / "runtime"))

    assert mixed is not None
    assert mixed.total_answer_records >= 1
    assert mixed.scoreable_item_count == 0
    assert mixed.scored_item_count == 0
    assert mixed.blocked_item_count == mixed.total_answer_records
    assert mixed.needs_review_item_count >= 0
    assert mixed.blank_item_count >= 0
    assert mixed.unsupported_item_count >= 0

    assert runtime is not None
    assert runtime.progress_mutation_enabled is False
    assert runtime.ranking_mutation_enabled is False
    assert runtime.retention_mutation_enabled is False
    assert runtime.scheduler_mutation_enabled is False
    assert runtime.study_cycle_mutation_enabled is False
    assert runtime.curriculum_graph_mutation_enabled is False
    assert runtime.no_progress_mutation is True
    assert runtime.no_ranking_update is True
    assert runtime.no_retention_update is True
    assert runtime.no_scheduler_update is True
    assert runtime.no_study_cycle_update is True
    assert runtime.no_curriculum_graph_update is True

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


def test_scoring_stabilization_preserves_persistence_and_idempotency(tmp_path):
    fixture = no_scoreable_records_fixture(tmp_path)
    result = build_score_result(fixture)
    assert result is not None

    correction_result = fixture.correction_result
    assert correction_result is not None
    repository = fixture.context.repository

    again = build_score_result(fixture)
    by_source = repository.get_simulado_score_result(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_score_result_by_id(
        result.score_result_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_score_results(user_id=fixture.context.user_id)

    assert again is not None
    assert by_source is not None
    assert by_id is not None
    assert result.model_dump(mode="json") == again.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert len(listed) == 1


def test_scoring_stabilization_api_owner_only_and_read_only_behaviour(tmp_path):
    owner_client, other_client, anonymous_client, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner_client, "owner")
    _register_and_login(other_client, "other")

    owner_fixture = api_readonly_fixture(tmp_path / "owner-fixture", user_id=owner_user_id, repository=repository)
    correction_result = owner_fixture.correction_result
    assert correction_result is not None

    missing_get = owner_client.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    before = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=owner_user_id,
    )
    build = owner_client.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    loaded = owner_client.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    score_result_id = build.json()["score_result_id"]
    by_id = owner_client.get(f"/api/simulado-score-result/{score_result_id}")
    after = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=owner_user_id,
    )

    assert missing_get.status_code == 404
    assert before is not None and after is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
    assert anonymous_client.post(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build"
    ).status_code == 401
    assert anonymous_client.get(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score"
    ).status_code == 401
    assert other_client.post(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build"
    ).status_code == 404
    assert other_client.get(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score"
    ).status_code == 404
    assert other_client.get(f"/api/simulado-score-result/{score_result_id}").status_code == 404
