from app.domain.models import TopicNode
from app.services.microtopic_extractor import MicroTopicExtractor


def test_microtopic_extractor_splits_paragraphs_into_units():
    topic = TopicNode(
        title="Luzes de Navegacao",
        level=1,
        content="Paragrafo um.\n\nParagrafo dois.\n\nParagrafo tres.",
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)

    assert len(extracted) == 3
    assert extracted[0].content == "Paragrafo um."
    assert extracted[1].content == "Paragrafo dois."
    assert extracted[2].content == "Paragrafo tres."


def test_microtopic_extractor_extracts_bullet_lists_as_microtopics():
    topic = TopicNode(
        title="Sinais",
        level=2,
        content="- Luz de topo\n- Luz de alcance\n- Luz de borda",
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)

    assert len(extracted) == 3
    assert extracted[0].title == "Luz de topo"
    assert extracted[1].title == "Luz de alcance"
    assert extracted[2].title == "Luz de borda"


def test_microtopic_extractor_detects_conceptual_markers():
    topic = TopicNode(
        title="Luzes de Navegacao",
        level=1,
        content=(
            "Conceito: luzes indicam posicao e movimento.\n\n"
            "Excecao: embarcacoes fundeadas seguem regime proprio.\n\n"
            "Aplicacao: em canais estreitos a interpretacao deve ser cautelosa."
        ),
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)

    assert [item.title for item in extracted] == ["Conceito", "Excecao", "Aplicacao"]
    assert "luzes indicam posicao" in extracted[0].content
    assert "embarcacoes fundeadas" in extracted[1].content


def test_microtopic_extractor_generates_stable_ids():
    topic = TopicNode(
        title="Balizamento",
        level=1,
        content="Observacao: sinais laterais exigem leitura contextual.",
        children=[],
    )

    first = MicroTopicExtractor().extract(topic)
    second = MicroTopicExtractor().extract(topic)

    assert first[0].id == second[0].id


def test_microtopic_extractor_tolerates_malformed_content():
    topic = TopicNode(
        title="Malformado",
        level=3,
        content="### texto solto\n\n- item sem estrutura clara\n\n2) numero estranho",
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)

    assert extracted
    assert any("item sem estrutura clara" in item.content for item in extracted)


def test_microtopic_extractor_handles_empty_content():
    topic = TopicNode(
        title="Vazio",
        level=2,
        content="",
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)

    assert extracted == []


def test_microtopic_extractor_applies_difficulty_weights():
    topic = TopicNode(
        title="Regras",
        level=1,
        content=(
            "Conceito: regra base.\n\n"
            "Observacao: detalhe relevante.\n\n"
            "Excecao: altera a conclusao esperada."
        ),
        children=[],
    )

    extracted = MicroTopicExtractor().extract(topic)
    weights = {item.title: item.difficulty_weight for item in extracted}

    assert weights["Conceito"] == 1.0
    assert weights["Observacao"] == 1.2
    assert weights["Excecao"] == 1.4
