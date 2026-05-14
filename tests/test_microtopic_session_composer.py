from app.domain.models import LearningPlanEntry
from app.services.microtopic_session_composer import MicrotopicSessionComposer


def build_entry(
    *,
    topic_id: str,
    topic_title: str,
    topic_content: str,
    curriculum_role: str,
    review_intensity: str,
    microtopic_performance: dict[str, dict[str, object]] | None = None,
    pedagogical_memory: dict[str, dict[str, object]] | None = None,
    priority_score: float = 0.5,
) -> LearningPlanEntry:
    return LearningPlanEntry(
        document_id=f"doc-{topic_id}",
        document_title=f"Doc {topic_id}",
        topic_id=topic_id,
        topic_title=topic_title,
        topic_content=topic_content,
        question_ids=[f"{topic_id}-q1"],
        priority_score=priority_score,
        curriculum_role=curriculum_role,
        review_intensity=review_intensity,
        performance_data={
            "microtopic_performance": microtopic_performance or {},
            "pedagogical_memory": pedagogical_memory or {},
        },
    )


def test_composer_is_deterministic_for_same_entries():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="ripam",
            topic_title="RIPAM",
            topic_content="Conceito: manobras.\n\nExcecao: situacoes especiais.\n\nAplicacao: cruzamento.",
            curriculum_role="active",
            review_intensity="deep",
        )
    ]

    first = composer.compose(entries)
    second = composer.compose(entries)

    assert [candidate.microtopic_id for candidate in first] == [candidate.microtopic_id for candidate in second]


def test_composer_preserves_curriculum_coherence_with_active_before_cumulative():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="active-topic",
            topic_title="Active",
            topic_content="Conceito: ativo.\n\nAplicacao: detalhe.",
            curriculum_role="active",
            review_intensity="deep",
        ),
        build_entry(
            topic_id="cumulative-topic",
            topic_title="Cumulative",
            topic_content="Conceito: cumulativo.\n\nAplicacao: recall.",
            curriculum_role="cumulative",
            review_intensity="light",
        ),
    ]

    candidates = composer.compose(entries)

    assert candidates[0].topic_id == "active-topic"


def test_composer_active_topics_receive_more_slots_than_cumulative():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="active-topic",
            topic_title="Active",
            topic_content="Conceito: um.\n\nExcecao: dois.\n\nAplicacao: tres.",
            curriculum_role="active",
            review_intensity="deep",
        ),
        build_entry(
            topic_id="cumulative-topic",
            topic_title="Cumulative",
            topic_content="Conceito: um.\n\nAplicacao: dois.\n\nObservacao: tres.",
            curriculum_role="cumulative",
            review_intensity="light",
        ),
    ]

    candidates = composer.compose(entries)
    active_count = sum(1 for candidate in candidates if candidate.topic_id == "active-topic")
    cumulative_count = sum(1 for candidate in candidates if candidate.topic_id == "cumulative-topic")

    assert active_count > cumulative_count


def test_composer_prioritizes_weak_microtopics_without_monopolization():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="ripam",
            topic_title="RIPAM",
            topic_content="Conceito: manobras.\n\nExcecao: situacoes especiais.\n\nAplicacao: cruzamento.",
            curriculum_role="active",
            review_intensity="deep",
            microtopic_performance={
                "micro-a": {
                    "total_questions": 4,
                    "correct_answers": 0,
                    "recent_errors": 3,
                    "error_distribution": {"conceptual": 3},
                }
            },
        )
    ]

    candidates = composer.compose(entries)

    assert candidates
    assert len(candidates) <= 3


def test_composer_keeps_resurfacing_candidate_for_cumulative_topic():
    composer = MicrotopicSessionComposer()
    base_entry = build_entry(
        topic_id="normam",
        topic_title="NORMAM",
        topic_content="Conceito: regra.\n\nAplicacao: inspeção.\n\nObservacao: excecoes.",
        curriculum_role="cumulative",
        review_intensity="light",
    )
    probe_ids = [candidate.microtopic_id for candidate in composer.compose([base_entry])]
    entries = [
        build_entry(
            topic_id="normam",
            topic_title="NORMAM",
            topic_content="Conceito: regra.\n\nAplicacao: inspeção.\n\nObservacao: excecoes.",
            curriculum_role="cumulative",
            review_intensity="light",
            microtopic_performance={
                probe_ids[0]: {
                    "total_questions": 6,
                    "correct_answers": 6,
                    "recent_errors": 0,
                    "last_reviewed_at": "2026-01-01T10:00:00+00:00",
                    "consecutive_correct": 4,
                }
            },
        )
    ]

    candidates = composer.compose(entries)

    assert any(candidate.selection_reason == "cumulative_resurfacing" for candidate in candidates)


def test_composer_produces_bounded_and_explainable_scores():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="topic-1",
            topic_title="Topic 1",
            topic_content="Conceito: regra.\n\nExcecao: detalhe.",
            curriculum_role="active",
            review_intensity="deep",
        )
    ]

    candidate = composer.compose(entries)[0]

    assert 0.0 <= candidate.composition_score <= 1.0
    assert set(candidate.composition_breakdown).issuperset(
        {
            "weakness",
            "resurfacing",
            "difficulty",
            "curriculum",
            "temporal",
            "stabilization_discount",
            "exposure_discount",
            "pedagogical_discount",
        }
    )


def test_composer_handles_sparse_legacy_data_safely():
    composer = MicrotopicSessionComposer()
    entries = [
        build_entry(
            topic_id="topic-legacy",
            topic_title="Legacy",
            topic_content="Conceito: regra.\n\nAplicacao: manutencao.",
            curriculum_role="cumulative",
            review_intensity="light",
            microtopic_performance={"legacy": {"total_questions": 1}},
        )
    ]

    candidates = composer.compose(entries)

    assert candidates
    assert all(candidate.curriculum_role == "cumulative" for candidate in candidates)


def test_composer_temporal_pedagogical_memory_resurfaces_stale_microtopic_deterministically():
    composer = MicrotopicSessionComposer()
    base_entry = build_entry(
        topic_id="topic-time",
        topic_title="Topic Time",
        topic_content="Conceito: regra base.\n\nAplicacao: caso pratico.\n\nObservacao: detalhe cumulativo.",
        curriculum_role="cumulative",
        review_intensity="light",
    )
    probe = composer.compose([base_entry])
    stale_id = probe[0].microtopic_id

    entries = [
        build_entry(
            topic_id="topic-time",
            topic_title="Topic Time",
            topic_content="Conceito: regra base.\n\nAplicacao: caso pratico.\n\nObservacao: detalhe cumulativo.",
            curriculum_role="cumulative",
            review_intensity="light",
            pedagogical_memory={
                stale_id: {
                    "microtopic_id": stale_id,
                    "topic_id": "topic-time",
                    "last_pedagogical_mode": "reinforcement_check",
                    "recent_effectiveness": "neutral",
                    "last_intervention_at": "2026-01-01T10:00:00+00:00",
                    "stabilization_level": 0.6,
                    "escalation_level": 0.0,
                    "retrieval_success_trend": 0.4,
                }
            },
        )
    ]

    candidates = composer.compose(entries)

    assert candidates[0].microtopic_id == stale_id
    assert "temporal" in candidates[0].composition_breakdown


def test_composer_prevents_pedagogical_memory_monopolization():
    composer = MicrotopicSessionComposer()
    base_entry = build_entry(
        topic_id="topic-balance",
        topic_title="Topic Balance",
        topic_content="Conceito: regra.\n\nExcecao: detalhe.\n\nAplicacao: comparacao.",
        curriculum_role="active",
        review_intensity="deep",
    )
    probe = composer.compose([base_entry])
    target_id = probe[0].microtopic_id

    candidates = composer.compose(
        [
            build_entry(
                topic_id="topic-balance",
                topic_title="Topic Balance",
                topic_content="Conceito: regra.\n\nExcecao: detalhe.\n\nAplicacao: comparacao.",
                curriculum_role="active",
                review_intensity="deep",
                pedagogical_memory={
                    target_id: {
                        "microtopic_id": target_id,
                        "topic_id": "topic-balance",
                        "last_pedagogical_mode": "active_recall",
                        "recent_effectiveness": "ineffective",
                        "stabilization_level": 0.0,
                        "escalation_level": 1.0,
                        "retrieval_success_trend": 0.0,
                    }
                },
            )
        ]
    )

    assert len(candidates) <= 3
    assert all(0.0 <= candidate.composition_score <= 1.0 for candidate in candidates)


def test_composer_considers_stability_and_fatigue_in_breakdown():
    composer = MicrotopicSessionComposer()
    probe = composer.compose(
        [
            build_entry(
                topic_id="topic-stability",
                topic_title="Topic Stability",
                topic_content="Conceito: regra.\n\nExcecao: detalhe.\n\nAplicacao: comparacao.",
                curriculum_role="cumulative",
                review_intensity="light",
            )
        ]
    )
    target_id = probe[0].microtopic_id

    candidates = composer.compose(
        [
            build_entry(
                topic_id="topic-stability",
                topic_title="Topic Stability",
                topic_content="Conceito: regra.\n\nExcecao: detalhe.\n\nAplicacao: comparacao.",
                curriculum_role="cumulative",
                review_intensity="light",
                pedagogical_memory={
                    target_id: {
                        "microtopic_id": target_id,
                        "topic_id": "topic-stability",
                        "stabilization_level": 0.85,
                        "retrieval_success_trend": 0.9,
                        "fatigue_exposure": 0.7,
                        "resurfacing_cycles": 5,
                        "successful_resurfacing_cycles": 5,
                    }
                },
            )
        ]
    )

    candidate = candidates[0]
    assert "stability" in candidate.composition_breakdown
    assert "fatigue" in candidate.composition_breakdown


def test_composer_lightly_boosts_rule_before_weak_exception():
    composer = MicrotopicSessionComposer()
    probe = composer.compose(
        [
            build_entry(
                topic_id="topic-relationship",
                topic_title="Topic Relationship",
                topic_content="Regra: base normativa.\n\nExcecao: ressalva restritiva.\n\nAplicacao: caso pratico.",
                curriculum_role="active",
                review_intensity="deep",
            )
        ]
    )
    ids_by_title = {candidate.microtopic_title: candidate.microtopic_id for candidate in probe}

    candidates = composer.compose(
        [
            build_entry(
                topic_id="topic-relationship",
                topic_title="Topic Relationship",
                topic_content="Regra: base normativa.\n\nExcecao: ressalva restritiva.\n\nAplicacao: caso pratico.",
                curriculum_role="active",
                review_intensity="deep",
                microtopic_performance={
                    ids_by_title["Excecao"]: {
                        "total_questions": 4,
                        "correct_answers": 1,
                        "recent_errors": 2,
                        "error_distribution": {"conceptual": 2},
                    }
                },
            )
        ]
    )

    titles = [candidate.microtopic_title for candidate in candidates]
    regra = next(candidate for candidate in candidates if candidate.microtopic_title == "Regra")

    assert titles.index("Regra") < titles.index("Excecao")
    assert "relationship" in regra.composition_breakdown
