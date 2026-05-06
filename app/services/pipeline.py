from __future__ import annotations

from app.domain.models import BoardStyle, Document
from app.services.pdf_extractor import PdfTextExtractor
from app.services.questions import QuestionGenerator
from app.services.structuring import ContentStructurer
from app.services.summaries import SummaryGenerator


class StudyPipeline:
    def __init__(
        self,
        extractor: PdfTextExtractor | None = None,
        structurer: ContentStructurer | None = None,
        summary_generator: SummaryGenerator | None = None,
        question_generator: QuestionGenerator | None = None,
    ):
        self.extractor = extractor or PdfTextExtractor()
        self.structurer = structurer or ContentStructurer()
        self.summary_generator = summary_generator or SummaryGenerator()
        self.question_generator = question_generator or QuestionGenerator()

    def process_pdf(
        self,
        *,
        filename: str,
        payload: bytes,
        board: BoardStyle,
        exam_context: str,
    ) -> Document:
        raw_text = self.extractor.extract(payload)
        topics = self.structurer.structure(raw_text)
        summaries = [self.summary_generator.generate(topic) for topic in topics]

        base_document = Document.create(
            title=self._derive_title(filename, topics),
            source_filename=filename,
            board=board,
            exam_context=exam_context,
            source_excerpt=raw_text[:1200],
            topics=topics,
            summaries=summaries,
            questions=[],
        )

        questions = []
        for topic in topics:
            questions.extend(
                self.question_generator.generate(
                    document_id=base_document.id,
                    topic=topic,
                    board=board,
                    count=2,
                )
            )
        base_document.questions = questions
        return base_document

    def _derive_title(self, filename: str, topics) -> str:
        if topics:
            return topics[0].title
        return filename.rsplit(".", maxsplit=1)[0].replace("_", " ").title()
