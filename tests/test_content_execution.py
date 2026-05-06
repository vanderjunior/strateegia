from datetime import datetime, timedelta, timezone

import pytest

from app.domain.models import (
    AnswerSubmission,
    BoardStyle,
    Document,
    GeneratedQuestion,
    LearningPlanEntry,
    StudyBlock,
    Topic,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.content_execution import execute_learning_plan, execute_study_block
from app.services.learning_engine import LearningDecisionEngine


def build_entry(
    *,
    topic_id: str,
    priority_score: float,
    study_blocks: list[StudyBlock],
) -> LearningPlanEntry:
    return LearningPlanEntry(
        document_id=f"doc-{topic_id}",
        document_title=f"Documento {topic_id}",
        topic_id=topic_id,
        topic_title=f"Topico {topic_id}",
        question_ids=[f"{topic_id}-q1"],
        priority_score=priority_score,
        recommended_difficulty=1,
        reasons=[],
        score_breakdown={"raw_priority": priority_score, "normalized_priority": priority_score},
        item_reasons={f"{topic_id}-q1": []},
        study_strategy="mixed",
        study_blocks=study_blocks,
    )


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=(
            f"{title} exige precisao normativa, leitura cuidadosa e atencao a excecoes. "
            f"Em prova, {title} costuma aparecer em itens tecnicos com comparacoes e pegadinhas."
        ),
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.8,
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
                stem=f"Julgue item sobre {title}",
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


def test_execute_study_block_summary_respects_depth():
    light = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="light"))
    medium = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="medium"))
    deep = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="deep"))

    assert light["type"] == "summary"
    assert light["depth"] == "light"
    assert "visao rapida" in light["content"].lower()
    assert "pontos de prova" in medium["content"].lower()
    assert "exemplo" in deep["content"].lower()


def test_execute_study_block_questions_respects_quantity():
    payload = execute_study_block(StudyBlock(type="questions", topic_id="lancamento", quantity=3))

    assert payload["type"] == "questions"
    assert payload["topic_id"] == "lancamento"
    assert len(payload["questions"]) == 3


def test_execute_study_block_question_format_is_correct():
    payload = execute_study_block(StudyBlock(type="questions", topic_id="competencia", quantity=2))

    assert payload["questions"]
    for question in payload["questions"]:
        assert set(question) == {"statement", "answer", "explanation"}
        assert isinstance(question["statement"], str)
        assert isinstance(question["answer"], bool)
        assert isinstance(question["explanation"], str)


def test_execute_learning_plan_builds_structured_session():
    plan_entries = [
        build_entry(
            topic_id="obrigacao",
            priority_score=0.8,
            study_blocks=[
                StudyBlock(type="summary", topic_id="obrigacao", depth="deep"),
                StudyBlock(type="questions", topic_id="obrigacao", quantity=2),
            ],
        )
    ]

    session = execute_learning_plan(plan_entries)

    assert len(session) == 2
    assert session[0]["type"] == "summary"
    assert session[1]["type"] == "questions"


def test_execute_learning_plan_handles_empty_and_invalid_blocks():
    assert execute_learning_plan([]) == []

    with pytest.raises(ValueError):
        execute_study_block(StudyBlock(type="invalid", topic_id="tema"))


def test_full_plan_executes_into_real_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Imunidades Tributarias",
        topic_id="topic-imunidades",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-imunidades",
            selected_answer="B",
            is_correct=False,
            error_type="conceptual",
            created_at=now - timedelta(hours=2),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Sessao executavel",
        max_questions=3,
    )

    executed = execute_learning_plan(plan.entries)

    assert executed
    assert any(block["type"] == "summary" for block in executed)
    assert any(block["type"] == "questions" for block in executed)
