from app.services.session_equilibrium import SessionEquilibriumLayer


def block(
    *,
    block_type: str,
    topic_id: str,
    pedagogical_mode: str = "reinforcement_check",
    explanation_depth: str = "light",
    retrieval_intensity: str = "low",
    curriculum_role: str = "active",
    review_intensity: str = "medium",
    question_index: int = 0,
    intervention_fatigue: float = 0.0,
    longitudinal_retention: float = 0.0,
) -> dict:
    payload = {
        "type": block_type,
        "topic_id": topic_id,
        "pedagogical_mode": pedagogical_mode,
        "explanation_depth": explanation_depth,
        "retrieval_intensity": retrieval_intensity,
        "curriculum_role": curriculum_role,
        "review_intensity": review_intensity,
        "intervention_fatigue": intervention_fatigue,
        "longitudinal_retention": longitudinal_retention,
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


def test_equilibrium_layer_is_deterministic():
    layer = SessionEquilibriumLayer()
    blocks = [
        block(block_type="summary", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep"),
        block(block_type="question", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep", retrieval_intensity="high", question_index=0),
        block(block_type="question", topic_id="t1", pedagogical_mode="active_recall", retrieval_intensity="high", question_index=1),
        block(block_type="question", topic_id="t2", pedagogical_mode="reinforcement_check", retrieval_intensity="low", question_index=1),
    ]

    first = layer.balance(blocks)
    second = layer.balance(blocks)

    assert first == second


def test_equilibrium_prevents_extended_heavy_question_streaks_when_light_block_exists():
    layer = SessionEquilibriumLayer()
    blocks = [
        block(block_type="summary", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep"),
        block(block_type="question", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep", retrieval_intensity="high", question_index=0),
        block(block_type="summary", topic_id="t2", pedagogical_mode="guided_explanation", explanation_depth="deep"),
        block(block_type="question", topic_id="t2", pedagogical_mode="guided_explanation", explanation_depth="deep", retrieval_intensity="high", question_index=0),
        block(block_type="question", topic_id="t1", pedagogical_mode="active_recall", retrieval_intensity="high", question_index=1),
        block(block_type="question", topic_id="t3", pedagogical_mode="reinforcement_check", retrieval_intensity="low", question_index=1),
    ]

    balanced = layer.balance(blocks)
    question_topics = [item["topic_id"] for item in balanced if item["type"] == "question"]

    assert question_topics[-2:] == ["t3", "t1"]


def test_equilibrium_preserves_summary_before_first_question():
    layer = SessionEquilibriumLayer()
    blocks = [
        block(block_type="summary", topic_id="t1"),
        block(block_type="question", topic_id="t1", question_index=0),
        block(block_type="summary", topic_id="t2"),
        block(block_type="question", topic_id="t2", question_index=0),
        block(block_type="question", topic_id="t1", question_index=1),
    ]

    balanced = layer.balance(blocks)
    first_summary = {}
    first_question = {}
    for index, item in enumerate(balanced):
        if item["type"] == "summary":
            first_summary.setdefault(item["topic_id"], index)
        if item["type"] == "question":
            first_question.setdefault(item["topic_id"], index)

    assert first_summary["t1"] < first_question["t1"]
    assert first_summary["t2"] < first_question["t2"]


def test_equilibrium_adds_explainable_metadata():
    layer = SessionEquilibriumLayer()
    balanced = layer.balance(
        [
            block(block_type="summary", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep"),
            block(block_type="question", topic_id="t1", pedagogical_mode="guided_explanation", explanation_depth="deep", retrieval_intensity="high", question_index=0),
        ]
    )

    assert "cognitive_load" in balanced[0]
    assert "equilibrium_reason" in balanced[0]
    assert "pacing_reason" in balanced[0]
    assert "intervention_rotation_reason" in balanced[0]
    assert "density_reason" in balanced[0]
    assert "fatigue_mitigation_reason" in balanced[0]
    assert "why_this_block_now" in balanced[0]


def test_equilibrium_handles_sparse_legacy_blocks():
    layer = SessionEquilibriumLayer()
    balanced = layer.balance(
        [
            {"type": "summary", "topic_id": "legacy", "_entry_index": 0, "_block_index": 0, "_question_index": 0},
            {"type": "question", "topic_id": "legacy", "question_id": "q1", "correct_answer": True, "explanation": "ok", "_entry_index": 0, "_block_index": 1, "_question_index": 0},
        ]
    )

    assert len(balanced) == 2
    assert all("cognitive_load" in item for item in balanced)


def test_equilibrium_moderates_cumulative_stable_blocks():
    layer = SessionEquilibriumLayer()
    balanced = layer.balance(
        [
            block(
                block_type="question",
                topic_id="cum-1",
                pedagogical_mode="active_recall",
                retrieval_intensity="medium",
                curriculum_role="cumulative",
                review_intensity="light",
                question_index=1,
                longitudinal_retention=0.85,
                intervention_fatigue=0.4,
            ),
            block(
                block_type="question",
                topic_id="cum-2",
                pedagogical_mode="active_recall",
                retrieval_intensity="medium",
                curriculum_role="cumulative",
                review_intensity="light",
                question_index=1,
                longitudinal_retention=0.8,
                intervention_fatigue=0.5,
            ),
        ]
    )

    assert all(item["cognitive_load_score"] <= 0.75 for item in balanced)
