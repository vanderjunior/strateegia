from __future__ import annotations

from app.domain.models import LearningPlanEntry, StudyBlock


def execute_study_block(block: StudyBlock) -> dict:
    if block.type == "summary":
        depth = block.depth or "light"
        return {
            "type": "summary",
            "topic_id": block.topic_id,
            "depth": depth,
            "content": _generate_summary_content(block.topic_id, depth),
        }
    if block.type == "questions":
        quantity = max(1, int(block.quantity or 1))
        return {
            "type": "questions",
            "topic_id": block.topic_id,
            "questions": _generate_questions(block.topic_id, quantity),
        }
    raise ValueError(f"Unsupported study block type: {block.type}")


def execute_learning_plan(plan: list[LearningPlanEntry]) -> list[dict]:
    executed_session: list[dict] = []
    for entry in plan:
        for block in entry.study_blocks:
            executed_session.append(execute_study_block(block))
    return executed_session


def _generate_summary_content(topic_id: str, depth: str) -> str:
    topic_name = _humanize_topic_id(topic_id)
    if depth == "deep":
        return (
            f"Resumo aprofundado de {topic_name}: conceito central, requisitos, excecoes e "
            f"comparacoes cobradas em prova. Exemplo: a banca pode inverter a regra geral, "
            f"trocar o sujeito competente ou explorar uma excecao aparente para induzir erro."
        )
    if depth == "medium":
        return (
            f"Resumo estruturado de {topic_name}: pontos de prova, regra principal, excecoes "
            f"relevantes e alerta para termos absolutos ou comparacoes proximas."
        )
    return (
        f"Visao rapida de {topic_name}: regra central, palavra-chave e ponto de maior risco em prova."
    )


def _generate_questions(topic_id: str, quantity: int) -> list[dict]:
    topic_name = _humanize_topic_id(topic_id)
    templates = [
        (
            f"Em {topic_name}, a regra geral pode ser aplicada sem analisar excecoes normativas especificas.",
            False,
            f"Errado. Em {topic_name}, a banca costuma cobrar justamente as excecoes e limitacoes da regra geral.",
        ),
        (
            f"No tema {topic_name}, a identificacao do conceito correto depende de diferenciar institutos proximos e efeitos juridicos distintos.",
            True,
            f"Certo. A cobranca costuma exigir distincao tecnica entre conceitos parecidos dentro de {topic_name}.",
        ),
        (
            f"Em {topic_name}, termos absolutos como sempre ou nunca tendem a tornar o item mais seguro quando a materia e tecnica.",
            False,
            f"Errado. Termos absolutos costumam ser indicio de pegadinha em itens tecnicos sobre {topic_name}.",
        ),
        (
            f"No estudo de {topic_name}, um detalhe acessorio pode alterar a conclusao do item mesmo quando a regra principal parece conhecida.",
            True,
            f"Certo. A banca frequentemente desloca a resposta correta com um detalhe normativo ou uma condicao adicional em {topic_name}.",
        ),
    ]

    questions: list[dict] = []
    for index in range(quantity):
        statement, answer, explanation = templates[index % len(templates)]
        questions.append(
            {
                "statement": statement,
                "answer": answer,
                "explanation": explanation,
            }
        )
    return questions


def _humanize_topic_id(topic_id: str) -> str:
    cleaned = topic_id.replace("_", " ").replace("-", " ").strip()
    return " ".join(token.capitalize() for token in cleaned.split()) or "Tema"
