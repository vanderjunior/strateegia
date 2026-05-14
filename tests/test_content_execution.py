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
    TopicNode,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.microtopic_extractor import MicroTopicExtractor
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


def build_topic_node(*, title: str, content: str) -> TopicNode:
    return TopicNode(title=title, level=2, content=content, children=[])


def build_microtopic_performance(**overrides):
    base = {
        "total_questions": 0,
        "correct_answers": 0,
        "recent_errors": 0,
        "error_distribution": {
            "conceptual": 0,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        },
        "last_seen_at": None,
    }
    base.update(overrides)
    return base


def build_pedagogical_memory(**overrides):
    base = {
        "last_pedagogical_mode": None,
        "recent_effectiveness": "neutral",
        "consecutive_successes": 0,
        "consecutive_failures": 0,
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


def test_execute_study_block_summary_respects_depth():
    light = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="light"))
    medium = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="medium"))
    deep = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="deep"))

    assert light["type"] == "summary"
    assert light["depth"] == "light"
    assert "visao rapida" in light["content"].lower()
    assert "pontos de prova" in medium["content"].lower()
    assert "exemplo" in deep["content"].lower()


def test_execute_study_block_summary_uses_microtopics():
    topic_node = build_topic_node(
        title="Luzes de Navegacao",
        content=(
            "Conceito: luzes de navegacao identificam situacoes e posicoes da embarcacao.\n\n"
            "Excecao: embarcacoes de pequeno porte podem cumprir sinalizacao reduzida.\n\n"
            "Aplicacao: em prova, compare luzes de alcançado e de bordo."
        ),
    )

    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="luzes-de-navegacao",
            depth="deep",
            topic_node=topic_node,
        )
    )

    assert payload["type"] == "summary"
    assert "excecao" in payload["content"].lower()
    assert "aplicacao" in payload["content"].lower()
    assert "sinalizacao reduzida" in payload["content"].lower()
    assert payload["selected_microtopics"]
    assert payload["review_intensity"] == "deep"


def test_execute_study_block_questions_respects_quantity():
    payload = execute_study_block(StudyBlock(type="questions", topic_id="lancamento", quantity=3))

    assert payload["type"] == "questions"
    assert payload["topic_id"] == "lancamento"
    assert len(payload["questions"]) == 3


def test_execute_study_block_questions_use_microtopics():
    topic_node = build_topic_node(
        title="RIPAM",
        content=(
            "Conceito: as regras disciplinam manobras e luzes.\n\n"
            "Excecao: a regra nao se aplica do mesmo modo em situacoes especiais.\n\n"
            "Observacao: a banca explora termos absolutos."
        ),
    )

    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="ripam",
            quantity=2,
            topic_node=topic_node,
        )
    )

    statements = " ".join(question["statement"] for question in payload["questions"]).lower()
    explanations = " ".join(question["explanation"] for question in payload["questions"]).lower()

    assert "excecao" in statements or "observacao" in statements
    assert "manobras e luzes" in explanations or "termos absolutos" in explanations
    assert payload["selected_microtopics"]


def test_execute_study_block_summary_supports_prerequisite_before_application():
    topic_node = build_topic_node(
        title="RIPAM",
        content=(
            "Conceito: a regra define prioridade de passagem.\n\n"
            "Aplicacao: em cruzamento, compare embarcacao a motor e a vela."
        ),
    )
    extracted = MicroTopicExtractor().extract(topic_node)
    application = next(microtopic for microtopic in extracted if microtopic.title == "Aplicacao")

    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="ripam",
            depth="deep",
            topic_node=topic_node,
            selected_microtopic_ids=[application.id],
        )
    )

    titles = [item["title"] for item in payload["selected_microtopics"]]

    assert titles[:2] == ["Conceito", "Aplicacao"]
    assert payload["relationship_type"] == "applied_by"
    assert payload["prerequisite_signal"] > 0.0


def test_execute_study_block_question_format_is_correct():
    payload = execute_study_block(StudyBlock(type="questions", topic_id="competencia", quantity=2))

    assert payload["questions"]
    for question in payload["questions"]:
        assert set(question) == {"statement", "answer", "explanation", "microtopic_id"}
        assert isinstance(question["statement"], str)
        assert isinstance(question["answer"], bool)
        assert isinstance(question["explanation"], str)
        assert isinstance(question["microtopic_id"], str)


def test_execute_study_block_exposes_adaptive_debug_metadata():
    topic_node = build_topic_node(
        title="Balizas",
        content=(
            "Conceito: sinalizam canal seguro.\n\n"
            "Excecao: em area especial, a interpretacao pode mudar.\n\n"
            "Observacao: a banca explora diferencas sutis."
        ),
    )

    payload = execute_study_block(
        StudyBlock(type="summary", topic_id="balizas", depth="medium", topic_node=topic_node)
    )

    assert set(payload).issuperset(
        {
            "type",
            "topic_id",
            "content",
            "selected_microtopics",
            "resurfaced_microtopics",
            "weak_microtopics",
            "review_intensity",
            "adaptive_reasoning",
            "pedagogical_mode",
            "intervention_reason",
            "cognitive_load",
            "pedagogical_reasoning",
            "pedagogical_breakdown",
            "intervention_transition_reason",
            "pedagogical_confidence",
            "intervention_effectiveness",
            "pedagogical_stability",
            "intervention_history_summary",
            "why_this_now",
            "stabilization_stage",
            "longitudinal_retention",
            "intervention_fatigue",
            "reinforcement_reason",
            "fatigue_reason",
            "stabilization_reasoning",
            "retention_reasoning",
            "recovery_signal",
        }
    )


def test_execute_study_block_difficulty_weighting_affects_selection():
    topic_node = build_topic_node(
        title="Luzes",
        content=(
            "Conceito: as luzes identificam a embarcacao.\n\n"
            "Excecao: rebocadores pequenos podem exibir combinacoes reduzidas."
        ),
    )

    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="luzes",
            quantity=1,
            topic_node=topic_node,
        )
    )

    question = payload["questions"][0]
    combined_text = f'{question["statement"]} {question["explanation"]}'.lower()

    assert "excecao" in combined_text
    assert "combinacoes reduzidas" in combined_text
    assert question["microtopic_id"]


def test_execute_study_block_prioritizes_weak_microtopics_but_keeps_resurfacing():
    topic_node = build_topic_node(
        title="Luzes",
        content=(
            "Conceito: identifica a embarcacao.\n\n"
            "Excecao: rebocadores pequenos exibem combinacoes reduzidas.\n\n"
            "Observacao: termos absolutos tendem a induzir erro."
        ),
    )
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="luzes",
            depth="deep",
            topic_node=topic_node,
            microtopic_performance={
                "micro-fake-conceito": build_microtopic_performance(),
            },
        )
    )

    assert payload["selected_microtopics"]
    assert any(item["title"] == "Excecao" for item in payload["selected_microtopics"])


def test_execute_study_block_mastered_microtopics_periodically_resurface():
    topic_node = build_topic_node(
        title="RIPAM",
        content=(
            "Conceito: manobras e prioridades de passagem.\n\n"
            "Excecao: situacoes especiais alteram a regra.\n\n"
            "Aplicacao: compare navio a vela e embarcacao a motor."
        ),
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="ripam", depth="deep", topic_node=topic_node)
    )
    microtopic_ids = {item["title"]: item["id"] for item in probe["selected_microtopics"]}
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="ripam",
            depth="medium",
            topic_node=topic_node,
            microtopic_performance={
                microtopic_ids["Conceito"]: build_microtopic_performance(
                    total_questions=5,
                    correct_answers=5,
                    recent_errors=0,
                    last_seen_at="2026-04-01T10:00:00+00:00",
                ),
                microtopic_ids["Excecao"]: build_microtopic_performance(
                    total_questions=4,
                    correct_answers=2,
                    recent_errors=1,
                    error_distribution={"conceptual": 1},
                    last_seen_at="2026-05-10T10:00:00+00:00",
                ),
            },
        )
    )

    assert payload["resurfaced_microtopics"]
    resurfaced_titles = {item["title"] for item in payload["resurfaced_microtopics"]}
    assert "Conceito" in resurfaced_titles


def test_execute_study_block_temporal_inactivity_resurfaces_old_microtopic():
    topic_node = build_topic_node(
        title="Aparelhos Sonoros",
        content=(
            "Conceito: sinais curtos indicam manobras objetivas.\n\n"
            "Aplicacao: compare cruzamento e ultrapassagem."
        ),
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="aparelhos", depth="deep", topic_node=topic_node)
    )
    ids = {item["title"]: item["id"] for item in probe["selected_microtopics"]}
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="aparelhos",
            quantity=2,
            topic_node=topic_node,
            microtopic_performance={
                ids["Conceito"]: build_microtopic_performance(
                    total_questions=6,
                    correct_answers=6,
                    recent_errors=0,
                    last_reviewed_at="2026-01-01T10:00:00+00:00",
                    last_correct_at="2026-01-01T10:00:00+00:00",
                    consecutive_correct=4,
                )
            },
        )
    )

    assert any(item["title"] == "Conceito" for item in payload["resurfaced_microtopics"])


def test_execute_study_block_uses_pedagogical_memory_to_escalate_ineffective_recall():
    topic_node = build_topic_node(
        title="Canal Estreito",
        content="Conceito: manobra restrita.\n\nAplicacao: prioridade de passagem.",
    )
    probe = execute_study_block(
        StudyBlock(type="questions", topic_id="canal-estreito", quantity=1, topic_node=topic_node)
    )
    target_id = probe["questions"][0]["microtopic_id"]

    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="canal-estreito",
            quantity=1,
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            microtopic_performance={
                target_id: build_microtopic_performance(
                    recent_errors=2,
                    error_distribution={"memory": 2},
                    consecutive_incorrect=2,
                )
            },
            pedagogical_memory={
                target_id: build_pedagogical_memory(
                    last_pedagogical_mode="active_recall",
                    recent_effectiveness="ineffective",
                    consecutive_failures=2,
                    escalation_level=0.8,
                    intervention_history={
                        "active_recall": {
                            "pedagogical_mode": "active_recall",
                            "total_attempts": 3,
                            "successful_attempts": 0,
                            "failed_attempts": 3,
                            "consecutive_failures": 2,
                            "confidence": 0.15,
                        }
                    },
                )
            },
            curriculum_role="active",
            review_intensity="medium",
        )
    )

    assert payload["pedagogical_mode"] == "guided_explanation"
    assert payload["intervention_transition_reason"]


def test_execute_study_block_temporal_reinforcement_resurfaces_stable_old_microtopic_lightly():
    topic_node = build_topic_node(
        title="Balizamento",
        content="Conceito: define referencia lateral.\n\nObservacao: prova confunde top marks.",
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="balizamento", depth="light", topic_node=topic_node)
    )
    target_id = probe["selected_microtopics"][0]["id"]
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="balizamento",
            depth="light",
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            pedagogical_memory={
                target_id: build_pedagogical_memory(
                    last_pedagogical_mode="reinforcement_check",
                    recent_effectiveness="effective",
                    last_intervention_at="2026-01-01T10:00:00+00:00",
                    stabilization_level=0.75,
                    retrieval_success_trend=0.85,
                )
            },
            curriculum_role="cumulative",
            review_intensity="light",
        )
    )

    assert payload["pedagogical_mode"] in {"reinforcement_check", "active_recall", "rapid_review"}
    assert payload["why_this_now"]


def test_execute_study_block_exposes_longitudinal_stability_metadata():
    topic_node = build_topic_node(
        title="Farol",
        content="Conceito: referencia visual.\n\nObservacao: prova explora confusoes com alcance.",
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="farol", depth="light", topic_node=topic_node)
    )
    target_id = probe["selected_microtopics"][0]["id"]
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="farol",
            depth="light",
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            pedagogical_memory={
                target_id: build_pedagogical_memory(
                    last_pedagogical_mode="reinforcement_check",
                    recent_effectiveness="effective",
                    stabilization_level=0.82,
                    retrieval_success_trend=0.9,
                    fatigue_exposure=0.3,
                    resurfacing_cycles=4,
                    successful_resurfacing_cycles=4,
                    recovery_count=1,
                )
            },
            curriculum_role="cumulative",
            review_intensity="light",
        )
    )

    assert payload["stabilization_stage"] in {"stabilizing", "consolidated", "resilient"}
    assert payload["longitudinal_retention"] >= 0.5
    assert payload["retention_reasoning"]


def test_execute_study_block_consecutive_success_stabilizes_repetition_pressure():
    topic_node = build_topic_node(
        title="Marcas Cardeais",
        content=(
            "Conceito: indicam quadrantes de perigo.\n\n"
            "Excecao: top marks exigem leitura precisa."
        ),
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="cardeais", depth="deep", topic_node=topic_node)
    )
    ids = {item["title"]: item["id"] for item in probe["selected_microtopics"]}
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="cardeais",
            quantity=2,
            topic_node=topic_node,
            microtopic_performance={
                ids["Excecao"]: build_microtopic_performance(
                    total_questions=7,
                    correct_answers=7,
                    recent_errors=0,
                    last_reviewed_at="2026-05-10T10:00:00+00:00",
                    last_correct_at="2026-05-10T10:00:00+00:00",
                    consecutive_correct=5,
                )
            },
        )
    )

    weak_titles = {item["title"] for item in payload["weak_microtopics"]}
    assert "Excecao" not in weak_titles


def test_execute_study_block_guided_explanation_mode_for_conceptual_weakness():
    topic_node = build_topic_node(
        title="Canal Restrito",
        content="Conceito: limites de manobra.\n\nExcecao: situacoes especiais ampliam restricoes.",
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="canal", depth="deep", topic_node=topic_node)
    )
    target_id = probe["selected_microtopics"][0]["id"]
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="canal",
            depth="deep",
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            microtopic_performance={
                target_id: build_microtopic_performance(
                    recent_errors=2,
                    error_distribution={"conceptual": 2},
                    consecutive_incorrect=2,
                )
            },
            curriculum_role="active",
            review_intensity="deep",
        )
    )

    assert payload["pedagogical_mode"] in {"guided_explanation", "conceptual_reinforcement"}
    assert payload["explanation_depth"] == "deep"


def test_execute_study_block_contextual_application_mode_for_interpretation_weakness():
    topic_node = build_topic_node(
        title="Prioridade de Passagem",
        content="Conceito: regras de cruzamento.\n\nAplicacao: compare motor e vela.",
    )
    probe = execute_study_block(
        StudyBlock(type="questions", topic_id="prioridade", quantity=1, topic_node=topic_node)
    )
    target_id = probe["questions"][0]["microtopic_id"]
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="prioridade",
            quantity=1,
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            microtopic_performance={
                target_id: build_microtopic_performance(error_distribution={"interpretation": 2})
            },
            curriculum_role="active",
            review_intensity="medium",
        )
    )

    assert payload["pedagogical_mode"] == "contextual_application"


def test_execute_study_block_active_recall_mode_for_memory_weakness():
    topic_node = build_topic_node(
        title="Apitos",
        content="Conceito: sinais curtos.\n\nRegra: sinais longos.",
    )
    probe = execute_study_block(
        StudyBlock(type="questions", topic_id="apitos", quantity=1, topic_node=topic_node)
    )
    target_id = probe["questions"][0]["microtopic_id"]
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="apitos",
            quantity=1,
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            microtopic_performance={
                target_id: build_microtopic_performance(error_distribution={"memory": 2})
            },
            curriculum_role="cumulative",
            review_intensity="light",
        )
    )

    assert payload["pedagogical_mode"] == "active_recall"


def test_execute_study_block_stable_cumulative_topic_uses_lighter_reinforcement():
    topic_node = build_topic_node(
        title="Balizas",
        content="Conceito: orientam o canal.\n\nAplicacao: identifique a lateral.",
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="balizas", depth="light", topic_node=topic_node)
    )
    target_id = probe["selected_microtopics"][0]["id"]
    payload = execute_study_block(
        StudyBlock(
            type="summary",
            topic_id="balizas",
            depth="light",
            topic_node=topic_node,
            selected_microtopic_ids=[target_id],
            microtopic_performance={
                target_id: build_microtopic_performance(consecutive_correct=4)
            },
            curriculum_role="cumulative",
            review_intensity="light",
        )
    )

    assert payload["pedagogical_mode"] in {"reinforcement_check", "rapid_review"}
    assert payload["retrieval_intensity"] in {"low", "medium"}


def test_execute_study_block_cumulative_review_balances_weak_and_mastered_questions():
    topic_node = build_topic_node(
        title="Sinalizacao",
        content=(
            "Conceito: boias laterais delimitam canal.\n\n"
            "Excecao: marcas especiais fogem ao padrao lateral.\n\n"
            "Observacao: cores e top marks confundem candidatos."
        ),
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="sinalizacao", depth="deep", topic_node=topic_node)
    )
    ids = {item["title"]: item["id"] for item in probe["selected_microtopics"]}
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="sinalizacao",
            quantity=3,
            topic_node=topic_node,
            microtopic_performance={
                ids["Conceito"]: build_microtopic_performance(
                    total_questions=6,
                    correct_answers=6,
                    recent_errors=0,
                    last_seen_at="2026-04-15T10:00:00+00:00",
                ),
                ids["Excecao"]: build_microtopic_performance(
                    total_questions=4,
                    correct_answers=1,
                    recent_errors=2,
                    error_distribution={"conceptual": 2},
                    last_seen_at="2026-05-11T09:00:00+00:00",
                ),
            },
        )
    )

    microtopic_ids = [question["microtopic_id"] for question in payload["questions"]]
    assert ids["Excecao"] in microtopic_ids
    assert ids["Conceito"] in microtopic_ids


def test_execute_study_block_layered_review_intensity_changes_selection_pressure():
    topic_node = build_topic_node(
        title="Boreste e Bombordo",
        content=(
            "Conceito: lados da embarcacao.\n\n"
            "Excecao: referencias em manobras podem confundir.\n\n"
            "Observacao: a prova troca referencial do observador."
        ),
    )

    deep_payload = execute_study_block(
        StudyBlock(type="summary", topic_id="bordos", depth="deep", topic_node=topic_node)
    )
    light_payload = execute_study_block(
        StudyBlock(type="summary", topic_id="bordos", depth="light", topic_node=topic_node)
    )

    assert deep_payload["review_intensity"] == "deep"
    assert light_payload["review_intensity"] == "light"
    assert len(deep_payload["selected_microtopics"]) > len(light_payload["selected_microtopics"])


def test_execute_study_block_selection_is_deterministic_with_balanced_distribution():
    topic_node = build_topic_node(
        title="Apitos",
        content=(
            "Conceito: sinais sonoros informam manobras.\n\n"
            "Regra: apitos curtos e longos possuem significados tecnicos.\n\n"
            "Aplicacao: compare ultrapassagem e cruzamento."
        ),
    )
    block = StudyBlock(type="questions", topic_id="apitos", quantity=3, topic_node=topic_node)

    first = execute_study_block(block)
    second = execute_study_block(block)

    assert first["selected_microtopics"] == second["selected_microtopics"]
    assert first["questions"] == second["questions"]


def test_execute_study_block_does_not_overfocus_only_on_recent_errors():
    topic_node = build_topic_node(
        title="Prioridades",
        content=(
            "Conceito: prioridade de passagem segue criterios normativos.\n\n"
            "Excecao: capacidade de manobra altera a preferencia.\n\n"
            "Aplicacao: compare pesca, vela e motor."
        ),
    )
    probe = execute_study_block(
        StudyBlock(type="summary", topic_id="prioridades", depth="deep", topic_node=topic_node)
    )
    ids = {item["title"]: item["id"] for item in probe["selected_microtopics"]}
    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="prioridades",
            quantity=3,
            topic_node=topic_node,
            microtopic_performance={
                ids["Excecao"]: build_microtopic_performance(
                    total_questions=3,
                    correct_answers=0,
                    recent_errors=3,
                    error_distribution={"conceptual": 3},
                    last_seen_at="2026-05-11T09:30:00+00:00",
                ),
                ids["Conceito"]: build_microtopic_performance(
                    total_questions=6,
                    correct_answers=6,
                    recent_errors=0,
                    last_seen_at="2026-03-01T09:30:00+00:00",
                ),
            },
        )
    )

    selected_ids = {item["id"] for item in payload["selected_microtopics"]}
    assert ids["Excecao"] in selected_ids
    assert ids["Conceito"] in selected_ids


def test_execute_study_block_falls_back_when_no_microtopics_exist():
    payload = execute_study_block(StudyBlock(type="summary", topic_id="imunidades", depth="medium"))

    assert payload["type"] == "summary"
    assert payload["content"]
    assert "imunidades" in payload["content"].lower()


def test_execute_study_block_questions_fall_back_with_stable_microtopic_id():
    payload = execute_study_block(StudyBlock(type="questions", topic_id="imunidades", quantity=1))

    assert payload["questions"][0]["microtopic_id"] == "fallback-imunidades"


def test_execute_study_block_tolerates_malformed_topic_content():
    topic_node = build_topic_node(
        title="Balizamento",
        content="### sinalizacao\n- item solto\n\nConceito sem dois pontos\n\n1. regra incompleta",
    )

    payload = execute_study_block(
        StudyBlock(
            type="questions",
            topic_id="balizamento",
            quantity=2,
            topic_node=topic_node,
        )
    )

    assert len(payload["questions"]) == 2
    assert payload["selected_microtopics"]


def test_execute_study_block_is_deterministic_for_same_microtopics():
    topic_node = build_topic_node(
        title="Farolete",
        content=(
            "Conceito: indica sinalizacao principal.\n\n"
            "Observacao: em prova, atencao a termos absolutos."
        ),
    )

    block = StudyBlock(type="summary", topic_id="farolete", depth="deep", topic_node=topic_node)

    first = execute_study_block(block)
    second = execute_study_block(block)

    assert first == second


def test_execute_learning_plan_builds_structured_session():
    topic_node = build_topic_node(
        title="Obrigacao Tributaria",
        content=(
            "Conceito: nasce com a ocorrencia do fato gerador.\n\n"
            "Excecao: a acessoria pode subsistir sem obrigacao principal exigivel."
        ),
    )
    plan_entries = [
        build_entry(
            topic_id="obrigacao",
            priority_score=0.8,
            study_blocks=[
                StudyBlock(type="summary", topic_id="obrigacao", depth="deep", topic_node=topic_node),
                StudyBlock(type="questions", topic_id="obrigacao", quantity=2, topic_node=topic_node),
            ],
        )
    ]

    session = execute_learning_plan(plan_entries)

    assert len(session) == 2
    assert session[0]["type"] == "summary"
    assert session[1]["type"] == "questions"
    assert "excecao" in session[0]["content"].lower()
    assert "obrigacao principal" in session[1]["questions"][0]["explanation"].lower()
    assert session[1]["questions"][0]["microtopic_id"]


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


def test_execute_learning_plan_with_microtopics_keeps_existing_block_contract():
    topic_node = build_topic_node(
        title="NORMAM",
        content=(
            "Conceito: a norma orienta a inspeção naval.\n\n"
            "Observacao: a prova cobra excecoes e limites operacionais."
        ),
    )
    entry = build_entry(
        topic_id="normam",
        priority_score=0.9,
        study_blocks=[
            StudyBlock(type="summary", topic_id="normam", depth="medium", topic_node=topic_node),
            StudyBlock(type="questions", topic_id="normam", quantity=1, topic_node=topic_node),
        ],
    )

    session = execute_learning_plan([entry])

    assert len(session) == 2
    assert session[0]["type"] == "summary"
    assert session[1]["type"] == "questions"
    assert "observacao" in session[0]["content"].lower() or "conceito" in session[0]["content"].lower()
    assert (
        "norma orienta" in session[1]["questions"][0]["explanation"].lower()
        or "limites operacionais" in session[1]["questions"][0]["explanation"].lower()
    )
