from datetime import datetime, timezone

from app.repositories.json_store import JsonStudyRepository
from app.services.pedagogical_stability import analyze_pedagogical_stability


def build_performance(**overrides):
    base = {
        "total_questions": 0,
        "correct_answers": 0,
        "recent_errors": 0,
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "last_seen_at": None,
        "last_reviewed_at": None,
        "last_correct_at": None,
        "last_incorrect_at": None,
    }
    base.update(overrides)
    return base


def build_memory(**overrides):
    base = {
        "last_pedagogical_mode": None,
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "consecutive_failures": 0,
        "last_intervention_at": None,
        "stabilization_level": 0.0,
        "escalation_level": 0.0,
        "retrieval_success_trend": 0.5,
        "intervention_history": {},
        "resurfacing_cycles": 0,
        "successful_resurfacing_cycles": 0,
        "fatigue_exposure": 0.0,
        "recovery_count": 0,
        "last_stabilized_at": None,
    }
    base.update(overrides)
    return base


def test_longitudinal_stability_distinguishes_shallow_from_durable_retention():
    shallow = analyze_pedagogical_stability(
        performance=build_performance(consecutive_correct=2, total_questions=2, correct_answers=2),
        pedagogical_memory=build_memory(stabilization_level=0.2, resurfacing_cycles=0),
        resurfacing_signal=0.2,
    )
    durable = analyze_pedagogical_stability(
        performance=build_performance(consecutive_correct=6, total_questions=18, correct_answers=16),
        pedagogical_memory=build_memory(
            stabilization_level=0.8,
            retrieval_success_trend=0.9,
            resurfacing_cycles=5,
            successful_resurfacing_cycles=4,
            last_stabilized_at="2026-04-01T10:00:00+00:00",
        ),
        resurfacing_signal=0.45,
    )

    assert shallow["stabilization_stage"] in {"unstable", "emerging", "stabilizing"}
    assert durable["stabilization_stage"] in {"consolidated", "resilient"}
    assert durable["retention_confidence"] > shallow["retention_confidence"]


def test_fatigue_accumulates_with_repeated_same_intervention():
    result = analyze_pedagogical_stability(
        performance=build_performance(consecutive_correct=5),
        pedagogical_memory=build_memory(
            last_pedagogical_mode="guided_explanation",
            stabilization_level=0.7,
            fatigue_exposure=0.8,
            intervention_history={
                "guided_explanation": {
                    "pedagogical_mode": "guided_explanation",
                    "total_attempts": 8,
                    "successful_attempts": 7,
                    "failed_attempts": 1,
                    "consecutive_successes": 5,
                    "confidence": 0.9,
                }
            },
        ),
        resurfacing_signal=0.15,
    )

    assert result["intervention_fatigue"] > 0.0
    assert result["fatigue_reason"]


def test_recovery_detection_recognizes_prior_failure_then_stability():
    result = analyze_pedagogical_stability(
        performance=build_performance(consecutive_correct=4, total_questions=10, correct_answers=7),
        pedagogical_memory=build_memory(
            recent_effectiveness="effective",
            consecutive_successes=4,
            consecutive_failures=0,
            recovery_count=1,
            escalation_level=0.2,
            stabilization_level=0.65,
            successful_resurfacing_cycles=2,
            resurfacing_cycles=3,
        ),
        resurfacing_signal=0.4,
    )

    assert result["recovery_signal"] > 0.0
    assert result["reinforcement_reason"]


def test_forgetting_signal_rises_after_inactivity_and_failed_recall():
    result = analyze_pedagogical_stability(
        performance=build_performance(
            recent_errors=2,
            consecutive_incorrect=2,
            last_reviewed_at="2026-01-01T10:00:00+00:00",
        ),
        pedagogical_memory=build_memory(
            stabilization_level=0.7,
            retrieval_success_trend=0.2,
            last_intervention_at="2026-01-01T10:00:00+00:00",
        ),
        resurfacing_signal=0.85,
    )

    assert result["forgetting_signal"] >= 0.5
    assert result["reinforcement_signal"] >= 0.3


def test_stability_analysis_is_deterministic_and_bounded():
    kwargs = dict(
        performance=build_performance(consecutive_correct=3, total_questions=7, correct_answers=6),
        pedagogical_memory=build_memory(
            stabilization_level=0.5,
            retrieval_success_trend=0.7,
            fatigue_exposure=0.2,
            successful_resurfacing_cycles=2,
            resurfacing_cycles=3,
        ),
        resurfacing_signal=0.35,
    )

    first = analyze_pedagogical_stability(**kwargs)
    second = analyze_pedagogical_stability(**kwargs)

    assert first == second
    assert all(
        0.0 <= first[key] <= 1.0
        for key in [
            "pedagogical_stability_score",
            "retention_confidence",
            "intervention_fatigue",
            "reinforcement_signal",
            "forgetting_signal",
            "longitudinal_consistency",
            "recovery_signal",
        ]
    )


def test_repository_loads_legacy_pedagogical_memory_without_longitudinal_fields(tmp_path):
    repository_path = tmp_path / "study_data.json"
    repository_path.write_text(
        """
        {
          "documents": [],
          "answers": [],
          "progress": {
            "total_errors": 0,
            "weak_topics": {},
            "error_buckets": {},
            "topic_learning_states": {},
            "item_states": {},
            "microtopic_performance": {},
            "pedagogical_memory": {
              "micro-old": {
                "microtopic_id": "micro-old",
                "topic_id": "topic-1",
                "last_pedagogical_mode": "active_recall",
                "recent_effectiveness": "neutral"
              }
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(repository_path)
    memory = repository.load_progress().pedagogical_memory["micro-old"]

    assert memory.resurfacing_cycles == 0
    assert memory.successful_resurfacing_cycles == 0
    assert memory.fatigue_exposure == 0.0
    assert memory.recovery_count == 0
    assert memory.last_stabilized_at is None
