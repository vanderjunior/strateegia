from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import (
    BoardStyle,
    Document,
    GeneratedQuestion,
    MicroTopicPerformance,
    PedagogicalMemory,
    ProgressState,
    Topic,
)
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.aggregate_retention_observability import observe_aggregate_retention
from app.services.snapshot_offline_io import export_inspection_snapshot, import_inspection_snapshot


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura normativa, excecoes e comparacoes tecnicas.",
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.85,
        source_pages=[1],
    )
    document = Document.create(
        title=title,
        source_filename=f"{title}.pdf",
        board=BoardStyle.CEBRASPE,
        exam_context="Marinha",
        source_excerpt=f"Trecho de {title}",
        topics=[topic],
        summaries=[],
        questions=[
            GeneratedQuestion(
                id=question_id,
                document_id="placeholder",
                topic_id=topic_id,
                style="certo_errado",
                stem=f"Julgue item sobre {title}.",
                options=["Certo", "Errado"],
                correct_answer="Certo",
                explanation=f"Explicacao de {title}",
                difficulty_level=1,
            )
        ],
    )
    document.created_at = created_at
    document.questions[0].document_id = document.id
    return document


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def start_basic_session(client: TestClient):
    response = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2})
    assert response.status_code == 200
    return response.json()


def build_performance(**overrides) -> MicroTopicPerformance:
    base = MicroTopicPerformance(
        topic_id="topic-a",
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
        microtopic_id="micro-a",
        topic_id="topic-a",
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


def build_runtime_block(**overrides) -> dict[str, object]:
    base = {
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


def build_progress() -> ProgressState:
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    return ProgressState(
        microtopic_performance={
            "micro-durable": build_performance(
                topic_id="topic-a",
                total_questions=18,
                correct_answers=16,
                consecutive_correct=5,
                last_reviewed_at=now,
                last_correct_at=now,
            ),
            "micro-fragile": build_performance(
                topic_id="topic-a",
                total_questions=10,
                correct_answers=4,
                recent_errors=3,
                consecutive_incorrect=2,
                last_reviewed_at=now - timedelta(days=1),
                last_incorrect_at=now,
            ),
            "micro-superficial": build_performance(
                topic_id="topic-b",
                total_questions=5,
                correct_answers=5,
                consecutive_correct=4,
                last_reviewed_at=now,
                last_correct_at=now,
            ),
            "micro-insufficient": build_performance(
                topic_id=None,
                total_questions=0,
                correct_answers=0,
            ),
        },
        pedagogical_memory={
            "micro-durable": build_memory(
                microtopic_id="micro-durable",
                topic_id="topic-a",
                stabilization_level=0.84,
                retrieval_success_trend=0.88,
                resurfacing_cycles=5,
                successful_resurfacing_cycles=4,
                recovery_count=2,
                last_stabilized_at=now - timedelta(days=5),
            ),
            "micro-fragile": build_memory(
                microtopic_id="micro-fragile",
                topic_id="topic-a",
                stabilization_level=0.28,
                retrieval_success_trend=0.34,
                resurfacing_cycles=4,
                successful_resurfacing_cycles=1,
                recovery_count=1,
            ),
            "micro-superficial": build_memory(
                microtopic_id="micro-superficial",
                topic_id="topic-b",
                stabilization_level=0.62,
                retrieval_success_trend=0.86,
                resurfacing_cycles=1,
                successful_resurfacing_cycles=0,
            ),
            "micro-insufficient": build_memory(
                microtopic_id="micro-insufficient",
                topic_id=None,
            ),
        },
    )


def build_runtime_blocks() -> dict[str, dict[str, object]]:
    return {
        "micro-durable": build_runtime_block(
            microtopic_id="micro-durable",
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
        "micro-fragile": build_runtime_block(
            microtopic_id="micro-fragile",
            retention_confidence=0.28,
            pedagogical_stability_score=0.3,
            stabilization_stage="unstable",
            longitudinal_consistency=0.24,
            recovery_signal=0.25,
            resurfacing_effectiveness_signal=0.18,
            validation_confidence=0.24,
            reconstruction_fragility=0.82,
            transfer_fragility=0.78,
            transfer_stability_signal=0.2,
            reconstruction_progress_signal=0.22,
            forgetting_signal=0.7,
        ),
        "micro-superficial": build_runtime_block(
            microtopic_id="micro-superficial",
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
    }


def test_aggregate_population_summary_and_ratios_are_deterministic():
    progress = build_progress()
    runtime_blocks = build_runtime_blocks()

    first = observe_aggregate_retention(
        progress=progress,
        runtime_blocks_by_microtopic=runtime_blocks,
    )
    second = observe_aggregate_retention(
        progress=progress,
        runtime_blocks_by_microtopic=runtime_blocks,
    )

    assert first == second
    assert first.total_microtopics_observed == 4
    assert first.durable_microtopics_count == 1
    assert first.fragile_microtopics_count == 1
    assert first.superficial_microtopics_count == 1
    assert first.insufficient_evidence_count == 1
    assert first.false_fluency_count == 1
    assert 0.0 <= first.durable_ratio <= 1.0
    assert 0.0 <= first.fragile_ratio <= 1.0
    assert 0.0 <= first.superficial_ratio <= 1.0


def test_aggregate_retention_state_and_evidence_summary_are_bounded():
    profile = observe_aggregate_retention(
        progress=build_progress(),
        runtime_blocks_by_microtopic=build_runtime_blocks(),
    )

    assert profile.aggregate_retention_state == "aggregate_retention_mixed"
    assert profile.aggregate_retention_evidence_summary.aggregate_retention_evidence_state in {
        "evidence_sufficient",
        "evidence_partial",
    }
    assert 0.0 <= profile.evidence_coverage_ratio <= 1.0


def test_topic_level_risk_summary_groups_by_topic_and_handles_missing_topic_id():
    profile = observe_aggregate_retention(
        progress=build_progress(),
        runtime_blocks_by_microtopic=build_runtime_blocks(),
    )

    by_topic = {item.topic_id: item for item in profile.topic_retention_risk_summary}

    assert "topic-a" in by_topic
    assert by_topic["topic-a"].fragile_count >= 1
    assert by_topic["topic-a"].observed_microtopics >= 2
    assert "topic-b" in by_topic
    assert by_topic["topic-b"].false_fluency_count >= 1
    assert "unknown_topic" in by_topic
    assert by_topic["unknown_topic"].topic_retention_state == "topic_retention_insufficient_evidence"


def test_resurfacing_recovery_reconstruction_and_transfer_aggregation():
    profile = observe_aggregate_retention(
        progress=build_progress(),
        runtime_blocks_by_microtopic=build_runtime_blocks(),
    )

    assert profile.aggregate_resurfacing_state == "aggregate_resurfacing_mixed"
    assert profile.aggregate_recovery_state in {
        "aggregate_recovery_mixed",
        "aggregate_recovery_improving",
    }
    assert profile.aggregate_reconstruction_state == "aggregate_reconstruction_mixed"
    assert profile.aggregate_transfer_state == "aggregate_transfer_mixed"
    assert profile.retention_population_summary.reconstruction_fragile_count >= 1
    assert profile.retention_population_summary.transfer_fragile_count >= 1


def test_aggregate_risk_flags_and_fallback_behavior():
    populated = observe_aggregate_retention(
        progress=build_progress(),
        runtime_blocks_by_microtopic=build_runtime_blocks(),
    )
    empty = observe_aggregate_retention(progress=ProgressState(), runtime_blocks_by_microtopic={})

    assert "aggregate_false_fluency_risk" in populated.aggregate_retention_risk_flags
    assert "aggregate_topic_risk_concentration" in populated.aggregate_retention_risk_flags
    assert empty.aggregate_retention_state == "aggregate_retention_insufficient_evidence"
    assert empty.aggregate_retention_evidence_summary.aggregate_retention_evidence_state == "evidence_insufficient"
    assert empty.topic_retention_risk_summary == []


def test_aggregate_retention_is_read_only_and_json_safe():
    progress = build_progress()
    runtime_blocks = build_runtime_blocks()
    progress_before = progress.model_dump(mode="json")
    runtime_before = deepcopy(runtime_blocks)

    profile = observe_aggregate_retention(
        progress=progress,
        runtime_blocks_by_microtopic=runtime_blocks,
    )

    assert progress.model_dump(mode="json") == progress_before
    assert runtime_blocks == runtime_before
    assert profile.aggregate_retention_reasoning


def test_inspection_payload_and_snapshot_include_aggregate_retention(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 15, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Balizamento",
            topic_id="topic-a",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    start_basic_session(client)

    response = client.get("/api/inspection/runtime")
    payload = response.json()
    exported = export_inspection_snapshot(payload)
    imported = import_inspection_snapshot(exported.snapshot_envelope.model_dump(mode="json"))

    assert response.status_code == 200
    assert "aggregate_retention" in payload
    assert payload["aggregate_retention"]["aggregate_retention_state"]
    assert exported.snapshot_envelope.snapshot_payload["aggregate_retention"]["aggregate_retention_state"]
    assert imported.imported_payload["aggregate_retention"]["aggregate_retention_state"]
