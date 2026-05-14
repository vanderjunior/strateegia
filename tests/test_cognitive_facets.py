from app.domain.models import MicroTopic
from app.services.cognitive_facets import extract_cognitive_facets, resolve_facet_profile


def microtopic(*, title: str, content: str) -> MicroTopic:
    return MicroTopic(
        id=f"micro-{title.lower()}",
        title=title,
        content=content,
        source_topic_title="Tema",
        difficulty_weight=1.0,
    )


def test_cognitive_facets_extract_deterministically():
    item = microtopic(
        title="Aplicacao",
        content="Aplicacao: compare os cenarios e reconheca a regra aplicavel no contexto.",
    )

    first = extract_cognitive_facets(item)
    second = extract_cognitive_facets(item)

    assert first == second


def test_cognitive_facets_keep_bounded_count():
    item = microtopic(
        title="Conceito",
        content=(
            "Conceito: definicao geral. Regra: deve observar o padrao. "
            "Excecao: porem ha ressalva. Aplicacao: compare contexto. Exemplo pratico."
        ),
    )

    facets = extract_cognitive_facets(item)

    assert 1 <= len(facets) <= 4


def test_cognitive_facets_distinguish_rule_and_exception():
    rule_item = microtopic(title="Regra", content="Regra: a embarcacao deve manter distancia obrigatoria.")
    exception_item = microtopic(title="Excecao", content="Excecao: exceto quando a via estiver restrita.")

    rule_facets = {facet.facet_type for facet in extract_cognitive_facets(rule_item)}
    exception_facets = {facet.facet_type for facet in extract_cognitive_facets(exception_item)}

    assert "rule" in rule_facets
    assert "exception" in exception_facets


def test_cognitive_facets_distinguish_definition_and_application():
    definition_item = microtopic(title="Conceito", content="Conceito: definicao da sinalizacao lateral.")
    application_item = microtopic(title="Aplicacao", content="Aplicacao: compare canal e baliza em situacao pratica.")

    definition_facets = {facet.facet_type for facet in extract_cognitive_facets(definition_item)}
    application_facets = {facet.facet_type for facet in extract_cognitive_facets(application_item)}

    assert "definition" in definition_facets
    assert "application" in application_facets


def test_cognitive_facets_distinguish_recognition_and_reconstruction():
    recognition_item = microtopic(title="Observacao", content="Observacao: reconheca o termo absoluto e a alternativa correta.")
    reconstruction_item = microtopic(title="Conceito", content="Conceito: reconstrua a sequencia logica da regra principal.")

    recognition_facets = {facet.facet_type for facet in extract_cognitive_facets(recognition_item)}
    reconstruction_facets = {facet.facet_type for facet in extract_cognitive_facets(reconstruction_item)}

    assert "recognition" in recognition_facets
    assert "reconstruction" in reconstruction_facets


def test_cognitive_facets_detect_contextual_transfer():
    item = microtopic(
        title="Aplicacao",
        content="Aplicacao: transfira a regra entre dois contextos distintos e compare cenarios.",
    )

    facets = {facet.facet_type for facet in extract_cognitive_facets(item)}

    assert "contextual_transfer" in facets


def test_cognitive_facets_tolerate_malformed_content():
    item = microtopic(title="Tema", content="### regra??\n\n:: aplicacao sem estrutura\n\ntexto solto")

    facets = extract_cognitive_facets(item)

    assert isinstance(facets, list)


def test_facet_profile_exposes_runtime_metadata():
    item = microtopic(
        title="Aplicacao",
        content="Aplicacao: compare o contexto, interprete a excecao e reconstrua a regra-base.",
    )

    profile = resolve_facet_profile(item)

    assert profile.cognitive_facets
    assert profile.dominant_facet
    assert profile.facet_reasoning
    assert 0.0 <= profile.transfer_signal <= 1.0
    assert 0.0 <= profile.reconstruction_signal <= 1.0
    assert 0.0 <= profile.recognition_signal <= 1.0


def test_facet_profile_supports_relationship_anchors():
    item = microtopic(
        title="Aplicacao",
        content="Aplicacao: compare os contextos e transfira a regra-base.",
    )

    profile = resolve_facet_profile(
        item,
        relationship_signal={
            "relationship_type": "applied_by",
            "conceptual_anchor": "Regra",
            "prerequisite_signal": 0.7,
        },
    )

    assert profile.dominant_facet in {"application", "contextual_transfer"}
    assert profile.facet_support_reason
