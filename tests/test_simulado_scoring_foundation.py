import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_scoring import SimuladoScoringService
from tests.fixtures.simulado_correction_results import build_correction_result
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_scoring_results import (
    blank_answer_score_fixture,
    build_score_result,
    empty_correction_result_fixture,
    invalid_submission_fixture,
    mixed_score_fixture,
    missing_correction_result_fixture,
    missing_correction_rule_fixture,
    missing_internal_answer_key_reference_fixture,
    selected_option_score_fixture,
    short_text_score_fixture,
    true_false_score_fixture,
    unsupported_answer_kind_fixture,
)


FORBIDDEN_SCORE_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "final_question_content",
    "final_explanation_content",
    "progress_applied",
    "ranking_applied",
    "retention_applied",
    "scheduler_applied",
    "final_result_applied",
    "passed",
    "failed",
}


def test_simulado_scoring_handles_missing_correction_result_safely(tmp_path):
    fixture = missing_correction_result_fixture(tmp_path)

    assert build_score_result(fixture) is None
    assert fixture.context.repository.list_user_simulado_score_results(user_id=fixture.context.user_id) == []


def test_simulado_scoring_blocks_when_no_scoreable_records_or_policy_are_available(tmp_path):
    empty = build_score_result(empty_correction_result_fixture(tmp_path / "empty"))
    selected = build_score_result(selected_option_score_fixture(tmp_path / "selected"))
    true_false = build_score_result(true_false_score_fixture(tmp_path / "true-false"))
    short_text = build_score_result(short_text_score_fixture(tmp_path / "short-text"))

    for result in (empty, selected, true_false, short_text):
        assert result is not None
        assert result.status == "score_result_blocked"
        assert result.readiness_state == "blocked_by_no_scoreable_correction_records"
        assert result.scoreable_item_count == 0
        assert result.scored_item_count == 0
        assert result.score_summary.raw_score == 0.0
        assert result.score_summary.max_score == 0.0
        assert result.score_summary.percentage_score is None
        assert result.score_summary.score_computable is False
        assert result.score_summary.score_complete is False
        assert result.score_summary.no_scoreable_items is True
        assert result.score_policy.policy_available is False
        assert result.score_policy.negative_marking_enabled is False
        assert result.score_policy.blank_penalty_enabled is False
        assert result.score_policy.unsupported_items_scoreable is False
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
        assert result.answer_key_publicly_exposed is False
        assert result.gabarito_publicly_exposed is False

    assert selected.item_records[0].answer_kind == "selected_option"
    assert selected.item_records[0].score_state == "item_blocked_by_missing_correction_state"
    assert selected.item_records[0].scoreable is False
    assert selected.item_records[0].scored is False
    assert selected.item_records[0].points_awarded == 0.0
    assert selected.item_records[0].max_points == 0.0

    assert true_false.item_records[0].answer_kind == "true_false_value"
    assert true_false.item_records[0].score_state == "item_blocked_by_missing_correction_state"
    assert short_text.item_records[0].answer_kind == "short_text"
    assert short_text.item_records[0].score_state == "item_blocked_by_missing_correction_state"


def test_simulado_scoring_handles_blank_unsupported_invalid_and_missing_key_rule_conservatively(tmp_path):
    blank = build_score_result(blank_answer_score_fixture(tmp_path / "blank"))
    unsupported = build_score_result(unsupported_answer_kind_fixture(tmp_path / "unsupported"))
    invalid = build_score_result(invalid_submission_fixture(tmp_path / "invalid"))
    missing_key = build_score_result(missing_internal_answer_key_reference_fixture(tmp_path / "missing-key"))
    missing_rule = build_score_result(missing_correction_rule_fixture(tmp_path / "missing-rule"))

    assert blank is not None
    assert blank.item_records[0].score_state == "item_blank_not_scored"
    assert blank.item_records[0].scoreable is False
    assert blank.item_records[0].scored is False
    assert blank.item_records[0].points_awarded == 0.0
    assert blank.blank_item_count == 1

    assert unsupported is not None
    assert unsupported.item_records[0].score_state == "item_blocked_by_unsupported_answer_kind"
    assert unsupported.unsupported_item_count == 1

    assert invalid is not None
    assert invalid.total_answer_records == 0
    assert invalid.scoreable_item_count == 0
    assert invalid.scored_item_count == 0
    invalid_codes = {item.code for item in invalid.blockers} | {item.code for item in invalid.validation_findings}
    assert "blocked_by_invalid_submission" in invalid_codes or "unknown_session_item" in invalid_codes

    assert missing_key is not None
    assert missing_key.item_records[0].score_state == "item_blocked_by_missing_correction_state"
    assert "blocked_by_no_scoreable_correction_records" in {item.code for item in missing_key.blockers}

    assert missing_rule is not None
    assert missing_rule.item_records[0].score_state == "item_blocked_by_missing_correction_state"
    assert "blocked_by_missing_score_policy" in {item.code for item in missing_rule.blockers}


def test_simulado_scoring_preserves_no_public_answer_key_and_no_runtime_mutation_guarantees(tmp_path):
    result = build_score_result(mixed_score_fixture(tmp_path))
    assert result is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert result.blocked_item_count == result.total_answer_records
    assert result.scoreable_item_count == 0
    assert result.scored_item_count == 0
    assert result.needs_review_item_count >= 0
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    for key in FORBIDDEN_SCORE_KEYS:
        assert key not in dumped_keys


def test_simulado_scoring_is_idempotent_and_does_not_mutate_source_artifacts(tmp_path):
    fixture = selected_option_score_fixture(tmp_path)
    result = build_score_result(fixture)
    assert result is not None

    correction_result = fixture.correction_result
    assert correction_result is not None
    boundary_id = correction_result.source_answer_key_boundary_id
    correction_shell_id = correction_result.source_correction_shell_id
    submission_id = correction_result.source_answer_submission_id
    attempt_session_id = correction_result.source_attempt_session_id
    service = SimuladoScoringService(fixture.context.repository)

    before_correction_result = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    before_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary_id,
        user_id=fixture.context.user_id,
    )
    before_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell_id,
        user_id=fixture.context.user_id,
    )
    before_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission_id,
        user_id=fixture.context.user_id,
    )
    before_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_score_result(correction_result.correction_result_id, user_id=fixture.context.user_id)
    second = service.build_score_result(correction_result.correction_result_id, user_id=fixture.context.user_id)

    by_source = fixture.context.repository.get_simulado_score_result(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_score_result_by_id(
        result.score_result_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_score_results(user_id=fixture.context.user_id)

    after_correction_result = fixture.context.repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=fixture.context.user_id,
    )
    after_boundary = fixture.context.repository.get_simulado_answer_key_boundary_by_id(
        boundary_id,
        user_id=fixture.context.user_id,
    )
    after_correction_shell = fixture.context.repository.get_simulado_correction_shell_by_id(
        correction_shell_id,
        user_id=fixture.context.user_id,
    )
    after_submission = fixture.context.repository.get_simulado_answer_submission_by_id(
        submission_id,
        user_id=fixture.context.user_id,
    )
    after_attempt_session = fixture.context.repository.get_simulado_attempt_session_by_id(
        attempt_session_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_correction_result is not None and after_correction_result is not None
    assert before_boundary is not None and after_boundary is not None
    assert before_correction_shell is not None and after_correction_shell is not None
    assert before_submission is not None and after_submission is not None
    assert before_attempt_session is not None and after_attempt_session is not None
    assert before_correction_result.model_dump(mode="json") == after_correction_result.model_dump(mode="json")
    assert before_boundary.model_dump(mode="json") == after_boundary.model_dump(mode="json")
    assert before_correction_shell.model_dump(mode="json") == after_correction_shell.model_dump(mode="json")
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
