from copy import deepcopy
from datetime import datetime, timedelta, timezone

from app.domain.models import MicroTopicPerformance, PedagogicalMemory, ProgressState
from app.repositories.json_store import JsonStudyRepository
from app.services.longitudinal_retention_observability import (
    observe_longitudinal_retention,
)


def build_performance(**overrides) -> MicroTopicPerformance:
    base = MicroTopicPerformance(
        topic_id="topic-1",
        total_questions=0,
        correct_answers=0,
        recent_errors=0,
        consecutive_correct=0,
        consecutive_incorrect=0,
        last_seen_at=None,
        last_reviewed_at=None,
        last_correct_at=None,
        last_incorrect_at=None,
    )
    return base.model_copy(update=overrides)


def build_memory(**overrides) -> PedagogicalMemory:
    base = PedagogicalMemory(
        microtopic_id="micro-1",
        topic_id="topic-1",
        stabilization_level=0.0,
        escalation_level=0.0,
        retrieval_success_trend=0.5,
        resurfacing_cycles=0,
        successful_resurfacing_cycles=0,
        fatigue_exposure=0.0,
        recovery_count=0,
        last_stabilized_at=None,
    )
    return base.model_copy(update=overrides)


def build_progress(
    *,
    microtopic_id: str = "micro-1",
    performance: MicroTopicPerformance | None = None,
    memory: PedagogicalMemory | None = None,
) -> ProgressState:
    performance = performance or build_performance()
    memory = memory or build_memory(microtopic_id=microtopic_id)
    return ProgressState(
        microtopic_performance={microtopic_id: performance},
        pedagogical_memory={microtopic_id: memory},
    )


def build_runtime_block(**overrides) -> dict[str, object]:
    base = {
        "microtopic_id": "micro-1",
        "retention_confidence": 0.5,
        "pedagogical_stability_score": 0.5,
        "stabilization_stage": "stabilizing",
        "intervention_fatigue": 0.2,
        "reinforcement_signal": 0.3,
        "forgetting_signal": 0.2,
        "longitudinal_consistency": 0.5,
        "recovery_signal": 0.3,
        "cognitive_trajectory": "balanced",
        "trajectory_state": "stabilizing",
        "consolidation_state": "emerging",
        "false_fluency_signal": 0.1,
        "false_fluency_risk": 0.1,
        "reconstruction_fragility": 0.2,
        "transfer_fragility": 0.2,
        "resurfacing_effectiveness_signal": 0.5,
        "stabilization_quality_signal": 0.55,
        "longitudinal_validation_signal": 0.55,
        "validation_confidence": 0.55,
        "transfer_stability_signal": 0.55,
        "reconstruction_progress_signal": 0.55,
    }
    base.update(overrides)
    return base


def test_longitudinal_retention_profile_is_deterministic():
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    progress = build_progress(
        performance=build_performance(
            total_questions=10,
            correct_answers=8,
            consecutive_correct=3,
            last_reviewed_at=now,
            last_correct_at=now,
        ),
        memory=build_memory(
            stabilization_level=0.7,
            retrieval_success_trend=0.78,
            resurfacing_cycles=3,
            successful_resurfacing_cycles=2,
            recovery_count=1,
        ),
    )
    block = build_runtime_block()

    first = observe_longitudinal_retention(progress=progress, runtime_block=block)
    second = observe_longitudinal_retention(progress=progress, runtime_block=block)

    assert first == second


def test_insufficient_evidence_fallback():
    profile = observe_longitudinal_retention(progress=ProgressState(), runtime_block={})

    assert profile.longitudinal_retention_state == "retention_insufficient_evidence"
    assert "insufficient_longitudinal_evidence" in profile.retention_risk_flags


def test_durable_retention_detection():
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(
                total_questions=18,
                correct_answers=16,
                consecutive_correct=5,
                last_reviewed_at=now,
                last_correct_at=now,
            ),
            memory=build_memory(
                stabilization_level=0.84,
                retrieval_success_trend=0.88,
                resurfacing_cycles=5,
                successful_resurfacing_cycles=4,
                recovery_count=2,
                last_stabilized_at=now - timedelta(days=5),
            ),
        ),
        runtime_block=build_runtime_block(
            retention_confidence=0.84,
            pedagogical_stability_score=0.82,
            stabilization_stage="consolidated",
            longitudinal_consistency=0.8,
            recovery_signal=0.64,
            resurfacing_effectiveness_signal=0.82,
            stabilization_quality_signal=0.8,
            validation_confidence=0.78,
            reconstruction_fragility=0.12,
            transfer_fragility=0.1,
            transfer_stability_signal=0.8,
            reconstruction_progress_signal=0.78,
        ),
    )

    assert profile.longitudinal_retention_state == "retention_sustainable"
    assert profile.retention_durability_state == "durable"


def test_superficial_retention_detection():
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(
                total_questions=5,
                correct_answers=5,
                consecutive_correct=4,
                last_reviewed_at=now,
                last_correct_at=now,
            ),
            memory=build_memory(
                stabilization_level=0.62,
                retrieval_success_trend=0.86,
                resurfacing_cycles=1,
                successful_resurfacing_cycles=0,
            ),
        ),
        runtime_block=build_runtime_block(
            retention_confidence=0.76,
            pedagogical_stability_score=0.72,
            stabilization_stage="stabilizing",
            longitudinal_consistency=0.36,
            false_fluency_signal=0.72,
            false_fluency_risk=0.7,
            reconstruction_fragility=0.7,
            transfer_fragility=0.66,
            resurfacing_effectiveness_signal=0.22,
            validation_confidence=0.4,
            transfer_stability_signal=0.34,
            reconstruction_progress_signal=0.3,
        ),
    )

    assert profile.longitudinal_retention_state == "retention_superficial"
    assert profile.false_fluency_retention_risk >= 0.55


def test_resurfacing_effective_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=12, correct_answers=10, consecutive_correct=3),
            memory=build_memory(
                resurfacing_cycles=4,
                successful_resurfacing_cycles=4,
                retrieval_success_trend=0.82,
            ),
        ),
        runtime_block=build_runtime_block(resurfacing_effectiveness_signal=0.84),
    )

    assert profile.resurfacing_effectiveness_state == "effective"


def test_resurfacing_ineffective_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(
                total_questions=10,
                correct_answers=4,
                recent_errors=3,
                consecutive_incorrect=2,
            ),
            memory=build_memory(
                resurfacing_cycles=4,
                successful_resurfacing_cycles=1,
                retrieval_success_trend=0.35,
            ),
        ),
        runtime_block=build_runtime_block(
            resurfacing_effectiveness_signal=0.2,
            validation_confidence=0.28,
        ),
    )

    assert profile.resurfacing_effectiveness_state == "ineffective"


def test_recovery_improving_detection():
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(
                total_questions=11,
                correct_answers=8,
                recent_errors=1,
                consecutive_correct=3,
                last_incorrect_at=now - timedelta(days=3),
                last_correct_at=now,
            ),
            memory=build_memory(recovery_count=2, resurfacing_cycles=3, successful_resurfacing_cycles=2),
        ),
        runtime_block=build_runtime_block(recovery_signal=0.68, longitudinal_consistency=0.72),
    )

    assert profile.recovery_state == "recovery_improving"


def test_recovery_unstable_detection():
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(
                total_questions=9,
                correct_answers=4,
                recent_errors=3,
                consecutive_incorrect=2,
                last_incorrect_at=now,
                last_correct_at=now - timedelta(days=4),
            ),
            memory=build_memory(recovery_count=0, resurfacing_cycles=2, successful_resurfacing_cycles=0),
        ),
        runtime_block=build_runtime_block(recovery_signal=0.18, longitudinal_consistency=0.34),
    )

    assert profile.recovery_state == "recovery_unstable"


def test_reconstruction_fragile_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=8, correct_answers=4, recent_errors=2),
            memory=build_memory(resurfacing_cycles=3, successful_resurfacing_cycles=1),
        ),
        runtime_block=build_runtime_block(
            reconstruction_fragility=0.82,
            reconstruction_progress_signal=0.24,
        ),
    )

    assert profile.reconstruction_retention_state == "reconstruction_fragile"


def test_reconstruction_durable_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=16, correct_answers=14, consecutive_correct=4),
            memory=build_memory(
                stabilization_level=0.78,
                resurfacing_cycles=4,
                successful_resurfacing_cycles=4,
            ),
        ),
        runtime_block=build_runtime_block(
            reconstruction_fragility=0.12,
            reconstruction_progress_signal=0.82,
            validation_confidence=0.78,
        ),
    )

    assert profile.reconstruction_retention_state == "reconstruction_durable"


def test_transfer_fragile_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=10, correct_answers=6, recent_errors=2),
            memory=build_memory(resurfacing_cycles=3, successful_resurfacing_cycles=1),
        ),
        runtime_block=build_runtime_block(
            transfer_fragility=0.78,
            transfer_stability_signal=0.26,
        ),
    )

    assert profile.transfer_retention_state == "transfer_fragile"


def test_transfer_durable_detection():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=15, correct_answers=13, consecutive_correct=4),
            memory=build_memory(
                stabilization_level=0.74,
                retrieval_success_trend=0.8,
                resurfacing_cycles=4,
                successful_resurfacing_cycles=3,
            ),
        ),
        runtime_block=build_runtime_block(
            transfer_fragility=0.14,
            transfer_stability_signal=0.8,
            validation_confidence=0.76,
        ),
    )

    assert profile.transfer_retention_state == "transfer_durable"


def test_retention_risk_flags_are_exposed():
    profile = observe_longitudinal_retention(
        progress=build_progress(
            performance=build_performance(total_questions=6, correct_answers=3, recent_errors=2),
            memory=build_memory(resurfacing_cycles=2, successful_resurfacing_cycles=0),
        ),
        runtime_block=build_runtime_block(
            false_fluency_signal=0.72,
            false_fluency_risk=0.7,
            reconstruction_fragility=0.7,
            transfer_fragility=0.68,
            resurfacing_effectiveness_signal=0.18,
            recovery_signal=0.2,
        ),
    )

    assert "false_fluency_risk" in profile.retention_risk_flags
    assert "reconstruction_decay_risk" in profile.retention_risk_flags
    assert "transfer_decay_risk" in profile.retention_risk_flags


def test_compatibility_with_missing_legacy_fields(tmp_path):
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
            "microtopic_performance": {
              "micro-old": {
                "topic_id": "topic-1",
                "total_questions": 2,
                "correct_answers": 1
              }
            },
            "pedagogical_memory": {
              "micro-old": {
                "microtopic_id": "micro-old",
                "topic_id": "topic-1"
              }
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(repository_path)
    progress = repository.load_progress()
    profile = observe_longitudinal_retention(progress=progress, runtime_block={"microtopic_id": "micro-old"})

    assert profile.longitudinal_retention_state in {
        "retention_inconclusive",
        "retention_insufficient_evidence",
        "retention_emerging",
    }


def test_longitudinal_retention_is_read_only_and_does_not_mutate_inputs():
    progress = build_progress(
        performance=build_performance(total_questions=9, correct_answers=7, consecutive_correct=2),
        memory=build_memory(resurfacing_cycles=3, successful_resurfacing_cycles=2),
    )
    block = build_runtime_block()
    progress_snapshot = deepcopy(progress)
    block_snapshot = deepcopy(block)

    observe_longitudinal_retention(progress=progress, runtime_block=block)

    assert progress == progress_snapshot
    assert block == block_snapshot
