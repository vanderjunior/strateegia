from datetime import datetime, timedelta, timezone

from app.services.curriculum_scheduler import CurriculumScheduler


def build_snapshot(
    *,
    topic_id: str,
    created_at: datetime,
    recent_errors: int = 0,
    conceptual_errors: int = 0,
    attempts: int = 0,
) -> dict:
    return {
        "topic_id": topic_id,
        "created_at": created_at,
        "performance_data": {
            "total_questions": attempts,
            "correct_answers": max(0, attempts - recent_errors),
            "recent_errors": recent_errors,
            "error_distribution": {
                "conceptual": conceptual_errors,
                "attention": 0,
                "interpretation": 0,
                "memory": 0,
            },
        },
        "dominant_error_type": "conceptual" if conceptual_errors else None,
    }


def test_scheduler_selects_active_window_from_newest_topics():
    now = datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=6 - index))
        for index in range(6)
    ]

    phase = scheduler.build_phase(snapshots)

    assert phase.active_window.topic_ids == ["topic-5", "topic-4", "topic-3"]


def test_scheduler_generates_cumulative_window_for_previous_topics():
    now = datetime(2026, 5, 12, 10, 30, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=6 - index))
        for index in range(6)
    ]

    phase = scheduler.build_phase(snapshots)

    assert phase.cumulative_window.topic_ids == ["topic-2", "topic-1", "topic-0"]


def test_scheduler_progressive_advancement_moves_active_window_forward():
    now = datetime(2026, 5, 12, 11, 0, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    phase_one = scheduler.build_phase(
        [
            build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=2 - index))
            for index in range(3)
        ]
    )
    phase_two = scheduler.build_phase(
        [
            build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=5 - index))
            for index in range(6)
        ]
    )

    assert phase_one.phase_number == 1
    assert phase_two.phase_number == 2
    assert phase_two.active_window.topic_ids == ["topic-5", "topic-4", "topic-3"]


def test_scheduler_marks_older_topics_for_light_review():
    now = datetime(2026, 5, 12, 11, 30, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=6 - index))
        for index in range(6)
    ]

    assignment = scheduler.schedule(snapshots)["topic-1"]

    assert assignment["curriculum_role"] == "cumulative"
    assert assignment["review_intensity"] == "light"


def test_scheduler_marks_recent_topics_for_deeper_review():
    now = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=6 - index))
        for index in range(6)
    ]

    latest = scheduler.schedule(snapshots)["topic-5"]

    assert latest["curriculum_role"] == "active"
    assert latest["review_intensity"] == "deep"


def test_scheduler_temporarily_intensifies_weak_cumulative_topic():
    now = datetime(2026, 5, 12, 12, 30, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=6 - index))
        for index in range(6)
    ]
    snapshots[1] = build_snapshot(
        topic_id="topic-1",
        created_at=now - timedelta(days=5),
        recent_errors=2,
        conceptual_errors=2,
        attempts=4,
    )

    assignment = scheduler.schedule(snapshots)["topic-1"]

    assert assignment["curriculum_role"] == "cumulative"
    assert assignment["review_intensity"] in {"medium", "deep"}


def test_scheduler_keeps_cumulative_topics_present_after_active_window():
    now = datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id=f"topic-{index}", created_at=now - timedelta(days=8 - index))
        for index in range(9)
    ]

    progress = scheduler.build_progress(snapshots)

    assert progress.cumulative_topic_ids
    assert "topic-0" in progress.cumulative_topic_ids


def test_scheduler_integration_with_adaptive_review_increases_cumulative_pressure():
    now = datetime(2026, 5, 12, 13, 30, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    calm = build_snapshot(
        topic_id="topic-calm",
        created_at=now - timedelta(days=5),
        recent_errors=0,
        attempts=4,
    )
    weak = build_snapshot(
        topic_id="topic-weak",
        created_at=now - timedelta(days=4),
        recent_errors=2,
        conceptual_errors=2,
        attempts=4,
    )
    assignments = scheduler.schedule(
        [
            build_snapshot(topic_id="topic-5", created_at=now),
            build_snapshot(topic_id="topic-4", created_at=now - timedelta(days=1)),
            build_snapshot(topic_id="topic-3", created_at=now - timedelta(days=2)),
            weak,
            calm,
        ]
    )

    assert assignments["topic-weak"]["priority_adjustment"] > assignments["topic-calm"]["priority_adjustment"]


def test_scheduler_ordering_is_deterministic():
    now = datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)
    snapshots = [
        build_snapshot(topic_id="topic-b", created_at=now - timedelta(days=1)),
        build_snapshot(topic_id="topic-a", created_at=now - timedelta(days=1)),
        build_snapshot(topic_id="topic-c", created_at=now),
    ]

    phase = scheduler.build_phase(snapshots)

    assert phase.active_window.topic_ids == ["topic-c", "topic-a", "topic-b"]


def test_scheduler_handles_sparse_data_with_safe_defaults():
    now = datetime(2026, 5, 12, 14, 30, tzinfo=timezone.utc)
    scheduler = CurriculumScheduler(active_window_size=3)

    assignment = scheduler.schedule(
        [
            {"topic_id": "topic-1", "created_at": now},
            {"topic_id": "topic-2", "created_at": now - timedelta(days=1)},
            {"topic_id": "topic-3", "created_at": now - timedelta(days=2)},
            {"topic_id": "topic-4", "created_at": now - timedelta(days=3)},
        ]
    )["topic-4"]

    assert assignment["curriculum_role"] == "cumulative"
    assert assignment["review_intensity"] == "light"
