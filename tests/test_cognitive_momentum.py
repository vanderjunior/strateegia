from app.services.cognitive_momentum import CognitiveMomentumLayer


def block(
    *,
    block_id: str,
    block_type: str = "question",
    topic_id: str = "topic-a",
    pedagogical_mode: str = "reinforcement_check",
    explanation_depth: str = "light",
    retrieval_intensity: str = "low",
    curriculum_role: str = "active",
    review_intensity: str = "medium",
    micro_intervention: str = "verification_step",
    continuity_signal: float = 0.6,
    narrative_relation: str = "continuation",
    cognitive_load_score: float = 0.42,
    longitudinal_retention: float = 0.0,
    intervention_fatigue: float = 0.0,
    question_index: int = 0,
) -> dict:
    payload = {
        "id": block_id,
        "type": block_type,
        "topic_id": topic_id,
        "pedagogical_mode": pedagogical_mode,
        "explanation_depth": explanation_depth,
        "retrieval_intensity": retrieval_intensity,
        "curriculum_role": curriculum_role,
        "review_intensity": review_intensity,
        "micro_intervention": micro_intervention,
        "continuity_signal": continuity_signal,
        "narrative_relation": narrative_relation,
        "cognitive_load_score": cognitive_load_score,
        "longitudinal_retention": longitudinal_retention,
        "intervention_fatigue": intervention_fatigue,
        "_entry_index": 0,
        "_block_index": 0,
        "_question_index": question_index,
    }
    if block_type == "summary":
        payload["content"] = "Resumo"
    else:
        payload["statement"] = "Pergunta"
        payload["correct_answer"] = True
        payload["explanation"] = "Explicacao"
        payload["question_id"] = f"{topic_id}-{question_index}"
    return payload


def test_cognitive_momentum_detects_conceptual_saturation():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            block(
                block_id="b1",
                block_type="summary",
                pedagogical_mode="guided_explanation",
                explanation_depth="deep",
                cognitive_load_score=0.82,
            ),
            block(
                block_id="b2",
                pedagogical_mode="conceptual_reinforcement",
                explanation_depth="deep",
                cognitive_load_score=0.8,
                question_index=1,
            ),
            block(
                block_id="b3",
                pedagogical_mode="guided_explanation",
                explanation_depth="deep",
                cognitive_load_score=0.84,
                question_index=2,
            ),
        ]
    )

    assert annotated[-1]["cognitive_momentum"] in {"conceptually_dense", "pressured"}
    assert annotated[-1]["momentum_signal"]["conceptual_density"] >= 0.6
    assert annotated[-1]["conceptual_density_reason"]


def test_cognitive_momentum_detects_retrieval_fatigue():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            block(
                block_id="q1",
                pedagogical_mode="active_recall",
                retrieval_intensity="high",
                micro_intervention="semantic_reactivation",
                cognitive_load_score=0.64,
                question_index=1,
            ),
            block(
                block_id="q2",
                pedagogical_mode="active_recall",
                retrieval_intensity="high",
                micro_intervention="semantic_reactivation",
                cognitive_load_score=0.67,
                question_index=2,
            ),
            block(
                block_id="q3",
                pedagogical_mode="active_recall",
                retrieval_intensity="high",
                micro_intervention="semantic_reactivation",
                cognitive_load_score=0.69,
                question_index=3,
            ),
        ]
    )

    assert annotated[-1]["momentum_signal"]["retrieval_fatigue"] >= 0.45
    assert annotated[-1]["retrieval_fatigue_reason"]


def test_cognitive_momentum_detects_intervention_fatigue():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            block(block_id="q1", micro_intervention="guided_reconstruction", question_index=1),
            block(block_id="q2", micro_intervention="guided_reconstruction", question_index=2),
            block(block_id="q3", micro_intervention="guided_reconstruction", question_index=3),
        ]
    )

    assert annotated[-1]["momentum_signal"]["intervention_fatigue"] >= 0.3
    assert annotated[-1]["pacing_relief_reason"]


def test_cognitive_momentum_detects_continuity_instability():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            block(block_id="a", continuity_signal=0.22, narrative_relation="contrast", question_index=1),
            block(block_id="b", continuity_signal=0.18, narrative_relation="contrast", question_index=2),
            block(block_id="c", continuity_signal=0.2, narrative_relation="contrast", question_index=3),
        ]
    )

    assert annotated[-1]["momentum_signal"]["continuity_stability"] <= 0.35
    assert annotated[-1]["continuity_pressure_reason"]


def test_cognitive_momentum_balances_stabilized_resurfacing():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            block(
                block_id="c1",
                curriculum_role="cumulative",
                review_intensity="light",
                narrative_relation="cumulative_resurfacing",
                longitudinal_retention=0.82,
                intervention_fatigue=0.24,
                micro_intervention="confidence_check",
                question_index=1,
            ),
            block(
                block_id="c2",
                curriculum_role="cumulative",
                review_intensity="light",
                narrative_relation="cumulative_resurfacing",
                longitudinal_retention=0.78,
                intervention_fatigue=0.28,
                micro_intervention="confidence_check",
                question_index=2,
            ),
        ]
    )

    assert annotated[-1]["momentum_signal"]["stabilization_balance"] >= 0.45
    assert annotated[-1]["momentum_signal"]["resurfacing_balance"] >= 0.35
    assert annotated[-1]["stabilization_balance_reason"]


def test_cognitive_momentum_is_deterministic_and_bounded():
    layer = CognitiveMomentumLayer()
    blocks = [
        block(block_id="s1", block_type="summary", pedagogical_mode="guided_explanation", explanation_depth="deep"),
        block(block_id="q1", pedagogical_mode="active_recall", retrieval_intensity="high", question_index=1),
    ]

    first = layer.annotate(blocks)
    second = layer.annotate(blocks)

    assert first == second
    for item in first:
        for value in item["momentum_signal"].values():
            assert 0.0 <= value <= 1.0


def test_cognitive_momentum_handles_sparse_legacy_blocks():
    layer = CognitiveMomentumLayer()
    annotated = layer.annotate(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {
                "type": "question",
                "topic_id": "legacy",
                "question_id": "q1",
                "correct_answer": True,
                "explanation": "ok",
                "_entry_index": 0,
                "_block_index": 1,
                "_question_index": 0,
            },
        ]
    )

    assert len(annotated) == 2
    assert all("cognitive_momentum" in item for item in annotated)
