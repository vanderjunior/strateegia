from __future__ import annotations

from app.domain.models import BlockReview, ReviewPayload
from app.services.learning_engine import LearningDecisionEngine
from app.services.questions import QuestionGenerator


class ReviewService:
    def __init__(
        self,
        repository,
        question_generator: QuestionGenerator | None = None,
        now_provider=None,
    ):
        self.repository = repository
        self.question_generator = question_generator or QuestionGenerator()
        self.learning_engine = LearningDecisionEngine(
            repository, now_provider=now_provider
        )

    def build_daily_review(self) -> ReviewPayload:
        documents = self.repository.list_documents()
        plan = self.learning_engine.build_review_plan(
            title="Revisao diaria",
            max_questions=5,
        )
        document_map = {document.id: document for document in documents}
        summaries = self._summaries_from_plan(plan.entries, document_map)
        questions = self._questions_from_plan(plan.entries, document_map)
        questions = self._top_up_questions(
            questions=questions,
            documents=documents,
            minimum=3,
            maximum=5,
        )
        document_titles = self._document_titles_from_plan(plan.entries)
        if not document_titles:
            document_titles = [document.title for document in documents[-3:]]

        return ReviewPayload(
            title="Revisao diaria",
            documents_considered=document_titles,
            summaries=summaries[:4],
            questions=questions[:5] if len(questions) >= 5 else questions[: max(3, len(questions))],
        )

    def build_latest_block_review(self) -> BlockReview | None:
        documents = self.repository.list_documents()
        if len(documents) < 3:
            return None

        block = documents[-3:]
        document_map = {document.id: document for document in documents}
        plan = self.learning_engine.build_review_plan(
            title=f"Simulado do bloco ate {block[-1].title}",
            max_questions=8,
            candidate_documents=block,
        )
        summaries = self._summaries_from_plan(plan.entries, document_map)
        questions = self._questions_from_plan(plan.entries, document_map)
        questions = self._top_up_questions(
            questions=questions,
            documents=block,
            minimum=3,
            maximum=8,
        )

        return BlockReview(
            title=f"Simulado do bloco ate {block[-1].title}",
            document_ids=[document.id for document in block],
            summaries=summaries[:5],
            questions=questions[:8],
        )

    def _document_titles_from_plan(self, entries) -> list[str]:
        titles = []
        for entry in entries:
            if entry.document_title not in titles:
                titles.append(entry.document_title)
        return titles

    def _summaries_from_plan(self, entries, document_map) -> list[str]:
        summaries: list[str] = []
        for entry in entries:
            document = document_map.get(entry.document_id)
            if not document:
                continue
            summary = self._summary_for_topic(document, entry.topic_id)
            if summary and summary not in summaries:
                summaries.append(summary)
        return summaries

    def _summary_for_topic(self, document, topic_id: str) -> str:
        for summary in document.summaries:
            if summary.topic_id == topic_id:
                return summary.structured_summary
        for topic in document.topics:
            if topic.id == topic_id:
                return topic.key_points[0] if topic.key_points else topic.content[:140]
        return ""

    def _questions_from_plan(self, entries, document_map) -> list:
        selected = []
        for entry in entries:
            document = document_map.get(entry.document_id)
            if not document:
                continue
            question_map = {question.id: question for question in document.questions}
            for question_id in entry.question_ids:
                question = question_map.get(question_id)
                if question is not None:
                    selected.append(question)
        return selected

    def _top_up_questions(self, *, questions: list, documents: list, minimum: int, maximum: int) -> list:
        selected = list(questions)
        seen_ids = {question.id for question in selected}
        if len(selected) >= minimum:
            return selected[:maximum]

        for document in reversed(documents):
            for topic in document.topics:
                generated = self.question_generator.generate(
                    document_id=document.id,
                    topic=topic,
                    board=document.board,
                    count=1,
                )
                for question in generated:
                    if question.id in seen_ids:
                        continue
                    selected.append(question)
                    seen_ids.add(question.id)
                    if len(selected) >= minimum:
                        return selected[:maximum]
        return selected[:maximum]
