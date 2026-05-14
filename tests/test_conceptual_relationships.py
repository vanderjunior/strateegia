from app.domain.models import TopicNode
from app.services.conceptual_relationships import (
    ConceptualRelationshipsLayer,
    build_relationship_signals,
)
from app.services.microtopic_extractor import MicroTopicExtractor


def build_topic_node(title: str, content: str) -> TopicNode:
    return TopicNode(title=title, level=2, content=content, children=[])


def test_relationship_extraction_detects_rule_exception_and_application():
    topic_node = build_topic_node(
        "Luzes de Navegacao",
        (
            "Regra: as luzes identificam a posicao da embarcacao.\n\n"
            "Excecao: embarcacoes pequenas admitem sinalizacao reduzida.\n\n"
            "Aplicacao: compare luzes de bordo e de alcançado."
        ),
    )
    microtopics = MicroTopicExtractor().extract(topic_node)

    relationships = ConceptualRelationshipsLayer().extract(topic_node, microtopics)

    relationship_types = {relationship.relationship_type for relationship in relationships}
    assert "exception_of" in relationship_types
    assert "applied_by" in relationship_types


def test_relationship_signal_marks_prerequisite_and_anchor():
    topic_node = build_topic_node(
        "RIPAM",
        (
            "Conceito: a regra define prioridade de passagem.\n\n"
            "Aplicacao: em cruzamento, compare embarcacao a motor e a vela."
        ),
    )
    microtopics = MicroTopicExtractor().extract(topic_node)
    relationships = ConceptualRelationshipsLayer().extract(topic_node, microtopics)

    signals = build_relationship_signals(microtopics, relationships)
    application = next(microtopic for microtopic in microtopics if microtopic.title == "Aplicacao")

    assert signals[application.id].relationship_type == "applied_by"
    assert signals[application.id].prerequisite_signal > 0.0
    assert signals[application.id].conceptual_anchor is not None


def test_relationship_extraction_tolerates_malformed_markdown():
    topic_node = build_topic_node(
        "Canal Restrito",
        "### regra sem estrutura clara\n\naplicacao sem marcador consistente\n\n- item solto",
    )
    microtopics = MicroTopicExtractor().extract(topic_node)

    relationships = ConceptualRelationshipsLayer().extract(topic_node, microtopics)

    assert isinstance(relationships, list)

