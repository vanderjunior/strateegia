from app.domain.models import AnswerSubmission, BoardStyle, Document, ErrorType, Topic
from app.repositories.json_store import JsonStudyRepository
from app.services.questions import QuestionGenerator
from app.services.reviews import ReviewService
from app.services.structuring import ContentStructurer
from app.services.summaries import SummaryGenerator


def test_content_structurer_detects_headings_and_scores_relevance():
    raw_text = """
    DIREITO TRIBUTARIO
    Competencia tributaria e principios limitadores ao poder de tributar.
    IMUNIDADES
    As imunidades tributarias sao excecoes constitucionais relevantes.
    FISCALIZACAO
    A fiscalizacao pode exigir documentos e identificar obrigacoes acessorias.
    """

    structurer = ContentStructurer()

    topics = structurer.structure(raw_text)

    assert len(topics) == 3
    assert topics[0].title == "Direito Tributario"
    assert topics[1].relevance_score >= topics[2].relevance_score
    assert "imunidades tributarias" in topics[1].content.lower()


def test_content_structurer_falls_back_to_chunks_when_no_headings():
    raw_text = (
        "Linha um sobre administracao tributaria. "
        "Linha dois com detalhes de fiscalizacao. "
        "Linha tres com excecoes relevantes. "
        "Linha quatro com obrigacoes acessorias. "
    )

    structurer = ContentStructurer(chunk_size=90)

    topics = structurer.structure(raw_text)

    assert len(topics) >= 2
    assert all(topic.title.startswith("Topico") for topic in topics)


def test_summary_generator_builds_structured_summary():
    topic = Topic(
        id="t1",
        title="Imunidades",
        content=(
            "Imunidades tributarias impedem a incidencia do tributo em situacoes previstas "
            "na Constituicao. Sao cobradas em prova por meio de excecoes e comparacoes com isencao."
        ),
        key_points=[],
        trap_points=[],
        relevance_score=0.9,
        source_pages=[1, 2],
    )

    summary = SummaryGenerator().generate(topic)

    assert summary.topic_id == "t1"
    assert summary.structured_summary
    assert len(summary.key_points) >= 2
    assert any("exce" in trap.lower() for trap in summary.trap_points)


def test_question_generator_creates_explanations_and_options():
    topic = Topic(
        id="t1",
        title="Obrigacao Tributaria",
        content=(
            "A obrigacao principal surge com o fato gerador e tem por objeto o pagamento de tributo "
            "ou penalidade pecuniaria. A obrigacao acessoria decorre da legislacao tributaria e envolve "
            "prestacoes positivas ou negativas."
        ),
        key_points=["Obrigacao principal depende do fato gerador."],
        trap_points=["Nao confundir obrigacao principal com acessoria."],
        relevance_score=0.8,
        source_pages=[3],
    )

    questions = QuestionGenerator().generate(
        document_id="doc-1",
        topic=topic,
        board=BoardStyle.FGV,
        count=2,
    )

    assert len(questions) == 2
    assert all(question.explanation for question in questions)
    assert all(len(question.options) == 4 for question in questions)


def test_review_service_creates_block_review_every_three_documents(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")

    for index in range(3):
        document = Document.create(
            title=f"PDF {index + 1}",
            source_filename=f"pdf_{index + 1}.pdf",
            board=BoardStyle.CEBRASPE,
            exam_context="Receita Federal",
            source_excerpt="Trecho original",
            topics=[
                Topic(
                    id=f"topic-{index}",
                    title=f"Topico {index}",
                    content="Conteudo essencial e excecoes cobradas.",
                    key_points=["Ponto essencial"],
                    trap_points=["Pegadinha"],
                    relevance_score=0.7,
                    source_pages=[1],
                )
            ],
            summaries=[],
            questions=[],
        )
        repository.save_document(document)

    review = ReviewService(repository).build_latest_block_review()

    assert review is not None
    assert len(review.document_ids) == 3
    assert len(review.questions) >= 3
    assert "PDF 3" in review.title


def test_repository_updates_errors_and_weak_topics(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")

    document = Document.create(
        title="PDF Unico",
        source_filename="unico.pdf",
        board=BoardStyle.FGV,
        exam_context="ISS Niteroi",
        source_excerpt="Trecho original",
        topics=[
            Topic(
                id="topic-1",
                title="Lancamento",
                content="Lancamento por homologacao depende de atividade posterior da autoridade.",
                key_points=["Lancamento por homologacao"],
                trap_points=["Nao confundir com lancamento de oficio."],
                relevance_score=0.9,
                source_pages=[1],
            )
        ],
        summaries=[],
        questions=[],
    )
    repository.save_document(document)

    repository.record_answer(
        AnswerSubmission(
            question_id="q1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
        )
    )

    progress = repository.load_progress()

    assert progress.total_errors == 1
    assert progress.weak_topics["topic-1"] == 1
    assert progress.error_buckets[ErrorType.CONCEPT_CONFUSION] == 1
