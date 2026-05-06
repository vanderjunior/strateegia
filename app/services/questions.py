from __future__ import annotations

import re
from uuid import uuid4

from app.domain.models import BoardStyle, GeneratedQuestion, Topic


class QuestionGenerator:
    def generate(
        self,
        *,
        document_id: str,
        topic: Topic,
        board: BoardStyle,
        count: int = 2,
    ) -> list[GeneratedQuestion]:
        facts = self._extract_facts(topic.content)
        if not facts:
            return []

        questions: list[GeneratedQuestion] = []
        for index in range(count):
            fact = facts[index % len(facts)]
            if board == BoardStyle.CEBRASPE:
                questions.append(self._build_cebraspe_question(document_id, topic, fact))
            else:
                questions.append(self._build_fgv_question(index, document_id, topic, fact))
        return questions

    def _extract_facts(self, content: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        facts = [sentence.strip() for sentence in sentences if len(sentence.strip()) > 30]
        return facts[:4]

    def _build_fgv_question(
        self,
        index: int,
        document_id: str,
        topic: Topic,
        fact: str,
    ) -> GeneratedQuestion:
        distractors = self._build_distractors(fact)
        options = distractors[:]
        correct_index = index % 4
        options.insert(correct_index, fact)
        options = options[:4]
        answer_letter = "ABCD"[correct_index]
        return GeneratedQuestion(
            id=str(uuid4()),
            document_id=document_id,
            topic_id=topic.id,
            style="multiple_choice",
            stem=f"No tema {topic.title}, assinale a alternativa correta.",
            options=options,
            correct_answer=answer_letter,
            explanation=(
                f"A alternativa correta reproduz a ideia central do topico {topic.title}. "
                f"Pegadinha principal: {topic.trap_points[0] if topic.trap_points else 'evite termos absolutos.'}"
            ),
        )

    def _build_cebraspe_question(
        self,
        document_id: str,
        topic: Topic,
        fact: str,
    ) -> GeneratedQuestion:
        return GeneratedQuestion(
            id=str(uuid4()),
            document_id=document_id,
            topic_id=topic.id,
            style="certo_errado",
            stem=f"Julgue o item a seguir sobre {topic.title}: {fact}",
            options=["Certo", "Errado"],
            correct_answer="Certo",
            explanation=(
                f"O item esta correto porque preserva a formulacao extraida do material base. "
                f"Atencao especial: {topic.trap_points[0] if topic.trap_points else 'a banca costuma trocar conceitos proximos.'}"
            ),
        )

    def _build_distractors(self, fact: str) -> list[str]:
        base = fact.rstrip(".")
        mutations = [
            base.replace(" nao ", " ").replace(" indelegavel", " delegavel"),
            f"{base} apenas em hipoteses residuais previstas em decreto.",
            f"{base} sem necessidade de observar excecoes ou comparacoes conceituais.",
            f"{base} exclusivamente por ato administrativo infralegal.",
        ]
        unique: list[str] = []
        for item in mutations:
            candidate = item.strip()
            if candidate and candidate != fact and candidate not in unique:
                unique.append(candidate)
        while len(unique) < 3:
            unique.append(f"{base} de forma livre e irrestrita.")
        return unique[:3]
