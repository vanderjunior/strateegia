from __future__ import annotations

from app.domain.models import CognitiveFacet, CognitiveFacetProfile, FacetSignal, FacetType, MicroTopic


FACET_ORDER = [
    FacetType.DEFINITION.value,
    FacetType.RULE.value,
    FacetType.EXCEPTION.value,
    FacetType.APPLICATION.value,
    FacetType.INTERPRETATION.value,
    FacetType.RECOGNITION.value,
    FacetType.RECONSTRUCTION.value,
    FacetType.CONTEXTUAL_TRANSFER.value,
]
TITLE_MARKERS = {
    FacetType.DEFINITION.value: ("conceito", "definicao", "definição"),
    FacetType.RULE.value: ("regra",),
    FacetType.EXCEPTION.value: ("excecao", "exceção"),
    FacetType.APPLICATION.value: ("aplicacao", "aplicação", "exemplo"),
    FacetType.INTERPRETATION.value: ("interpretacao", "interpretação", "observacao", "observação"),
}
CONTENT_MARKERS = {
    FacetType.DEFINITION.value: ("conceito", "definicao", "definição", "significa"),
    FacetType.RULE.value: ("regra", "deve", "obrigatorio", "obrigatório", "vedado"),
    FacetType.EXCEPTION.value: ("excecao", "exceção", "exceto", "porem", "porém", "ressalva"),
    FacetType.APPLICATION.value: ("aplicacao", "aplicação", "exemplo", "caso", "situacao", "situação", "cenario", "cenário"),
    FacetType.INTERPRETATION.value: ("interprete", "compare", "distinga", "leitura", "contextualize"),
    FacetType.RECOGNITION.value: ("reconheca", "reconheça", "identifique", "assinale", "alternativa correta"),
    FacetType.RECONSTRUCTION.value: ("reconstrua", "refaca", "refaça", "encadeamento", "sequencia logica", "sequência lógica"),
    FacetType.CONTEXTUAL_TRANSFER.value: ("transfira", "transfer", "contexto", "contextual", "cenarios", "cenários"),
}
FACET_LIMIT = 4


def extract_cognitive_facets(
    microtopic: MicroTopic,
    *,
    relationship_signal: dict[str, object] | None = None,
) -> list[CognitiveFacet]:
    normalized_title = _normalize_text(microtopic.title)
    normalized_content = _normalize_text(microtopic.content)
    relationship_type = str((relationship_signal or {}).get("relationship_type") or "")
    scores = {facet: 0.0 for facet in FACET_ORDER}
    reasons: dict[str, list[str]] = {facet: [] for facet in FACET_ORDER}

    for facet, markers in TITLE_MARKERS.items():
        if any(marker in normalized_title for marker in markers):
            scores[facet] += 0.62
            reasons[facet].append("marcador no titulo")

    for facet, markers in CONTENT_MARKERS.items():
        matches = sum(1 for marker in markers if marker in normalized_content)
        if matches:
            scores[facet] += min(0.24 + matches * 0.12, 0.46)
            reasons[facet].append("marcadores no conteudo")

    if relationship_type == "applied_by":
        scores[FacetType.APPLICATION.value] += 0.18
        scores[FacetType.CONTEXTUAL_TRANSFER.value] += 0.24
        reasons[FacetType.APPLICATION.value].append("relacao aplicada")
        reasons[FacetType.CONTEXTUAL_TRANSFER.value].append("transferencia contextual implicita")
    elif relationship_type == "exception_of":
        scores[FacetType.EXCEPTION.value] += 0.22
        scores[FacetType.RULE.value] += 0.1
        reasons[FacetType.EXCEPTION.value].append("relacao de excecao")
    elif relationship_type == "prerequisite":
        scores[FacetType.RULE.value] += 0.16
        scores[FacetType.DEFINITION.value] += 0.08
        reasons[FacetType.RULE.value].append("apoio prerequisito")

    if "compare" in normalized_content and "contexto" in normalized_content:
        scores[FacetType.CONTEXTUAL_TRANSFER.value] += 0.16
        reasons[FacetType.CONTEXTUAL_TRANSFER.value].append("comparacao entre contextos")

    selected: list[CognitiveFacet] = []
    for facet, score in sorted(
        scores.items(),
        key=lambda item: (-item[1], FACET_ORDER.index(item[0])),
    ):
        if score <= 0.0:
            continue
        selected.append(
            CognitiveFacet(
                facet_type=facet,
                strength=round(_clamp(score), 4),
                reason=_build_reason(facet, reasons[facet]),
            )
        )
        if len(selected) >= FACET_LIMIT:
            break

    if not selected:
        selected.append(
            CognitiveFacet(
                facet_type=FacetType.DEFINITION.value,
                strength=0.2,
                reason="fallback estrutural por ausencia de marcadores fortes.",
            )
        )

    return selected


def resolve_facet_profile(
    microtopic: MicroTopic,
    *,
    relationship_signal: dict[str, object] | None = None,
    pedagogical_profile: dict[str, object] | object | None = None,
    micro_intervention: dict[str, object] | object | None = None,
) -> CognitiveFacetProfile:
    facets = extract_cognitive_facets(microtopic, relationship_signal=relationship_signal)
    pedagogical = _normalize_object(pedagogical_profile)
    intervention = _normalize_object(micro_intervention)
    dominant = facets[0].facet_type if facets else FacetType.DEFINITION.value
    transfer_signal = _facet_strength(facets, FacetType.CONTEXTUAL_TRANSFER.value)
    if dominant in {FacetType.APPLICATION.value, FacetType.INTERPRETATION.value}:
        transfer_signal = _clamp(max(transfer_signal, _facet_strength(facets, dominant) * 0.72))
    reconstruction_signal = _facet_strength(facets, FacetType.RECONSTRUCTION.value)
    recognition_signal = _facet_strength(facets, FacetType.RECOGNITION.value)

    if str(pedagogical.get("pedagogical_mode") or "") == "guided_explanation":
        reconstruction_signal = _clamp(max(reconstruction_signal, 0.42))
    if str(intervention.get("intervention_type") or "") in {"guided_reconstruction", "semantic_reactivation"}:
        reconstruction_signal = _clamp(max(reconstruction_signal, 0.5))
    if str(pedagogical.get("pedagogical_mode") or "") in {"rapid_review", "reinforcement_check"}:
        recognition_signal = _clamp(max(recognition_signal, 0.38))

    profile = CognitiveFacetProfile(
        cognitive_facets=facets,
        dominant_facet=dominant,
        facet_reasoning=_facet_reasoning(facets),
        cognitive_dimension=_cognitive_dimension(dominant),
        retrieval_dimension=_retrieval_dimension(recognition_signal, reconstruction_signal),
        conceptual_dimension=_conceptual_dimension(facets),
        transfer_signal=round(_clamp(transfer_signal), 4),
        reconstruction_signal=round(_clamp(reconstruction_signal), 4),
        recognition_signal=round(_clamp(recognition_signal), 4),
        why_this_facet_now=_why_this_facet_now(dominant),
        facet_support_reason=_facet_support_reason(dominant, relationship_signal),
    )
    profile.facet_signal = FacetSignal(
        transfer_signal=profile.transfer_signal,
        reconstruction_signal=profile.reconstruction_signal,
        recognition_signal=profile.recognition_signal,
    )
    return profile


def _facet_strength(facets: list[CognitiveFacet], facet_type: str) -> float:
    for facet in facets:
        if facet.facet_type == facet_type:
            return _clamp(float(facet.strength))
    return 0.0


def _facet_reasoning(facets: list[CognitiveFacet]) -> list[str]:
    reasoning = [f"Faceta dominante: {facets[0].facet_type}."]
    if len(facets) > 1:
        reasoning.append(
            "Facetas de apoio: " + ", ".join(facet.facet_type for facet in facets[1:]) + "."
        )
    reasoning.extend(facet.reason.capitalize() for facet in facets[:2])
    return reasoning


def _cognitive_dimension(dominant_facet: str) -> str:
    if dominant_facet in {FacetType.DEFINITION.value, FacetType.RULE.value, FacetType.EXCEPTION.value}:
        return "conceptual_foundation"
    if dominant_facet in {FacetType.APPLICATION.value, FacetType.INTERPRETATION.value, FacetType.CONTEXTUAL_TRANSFER.value}:
        return "contextual_processing"
    return "retrieval_processing"


def _retrieval_dimension(recognition_signal: float, reconstruction_signal: float) -> str:
    if reconstruction_signal >= max(0.45, recognition_signal + 0.08):
        return "reconstruction"
    if recognition_signal >= 0.35:
        return "recognition"
    return "balanced"


def _conceptual_dimension(facets: list[CognitiveFacet]) -> str:
    types = {facet.facet_type for facet in facets}
    if FacetType.RULE.value in types and FacetType.EXCEPTION.value in types:
        return "rule_exception"
    if FacetType.DEFINITION.value in types and FacetType.APPLICATION.value in types:
        return "definition_application"
    if FacetType.CONTEXTUAL_TRANSFER.value in types:
        return "context_transfer"
    return "single_focus"


def _why_this_facet_now(dominant_facet: str) -> str:
    mapping = {
        FacetType.DEFINITION.value: "A base definicional precisa orientar o bloco atual.",
        FacetType.RULE.value: "A regra central organiza o julgamento deste momento.",
        FacetType.EXCEPTION.value: "A ressalva local precisa aparecer sem perder a regra-base.",
        FacetType.APPLICATION.value: "O bloco atual pede transferencia do conceito para um caso concreto.",
        FacetType.INTERPRETATION.value: "A leitura fina do contexto precisa ganhar destaque agora.",
        FacetType.RECOGNITION.value: "O momento atual depende de reconhecer rapidamente o sinal correto.",
        FacetType.RECONSTRUCTION.value: "O bloco atual pede reconstruir o encadeamento do conceito.",
        FacetType.CONTEXTUAL_TRANSFER.value: "O momento atual exige mover a regra entre contextos proximos.",
    }
    return mapping.get(dominant_facet, "A faceta local ajuda a manter precisao cognitiva neste ponto.")


def _facet_support_reason(
    dominant_facet: str,
    relationship_signal: dict[str, object] | None,
) -> str | None:
    relationship_type = str((relationship_signal or {}).get("relationship_type") or "")
    anchor = str((relationship_signal or {}).get("conceptual_anchor") or "")
    if dominant_facet in {FacetType.APPLICATION.value, FacetType.CONTEXTUAL_TRANSFER.value} and relationship_type == "applied_by":
        return f"A aplicacao permanece apoiada pela ancora conceitual {anchor or 'anterior'}."
    if dominant_facet == FacetType.EXCEPTION.value and relationship_type == "exception_of":
        return f"A excecao continua amarrada a {anchor or 'sua regra-base'}."
    if dominant_facet == FacetType.RULE.value and relationship_type == "prerequisite":
        return f"A regra atua como prerequisito local antes do proximo passo."
    return None


def _build_reason(facet: str, parts: list[str]) -> str:
    if parts:
        return f"{facet} detectada por " + ", ".join(parts) + "."
    return f"{facet} detectada por padrao estrutural local."


def _normalize_object(value: dict[str, object] | object | None) -> dict[str, object]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    return {}


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace(":", " ").replace("\n", " ").split())


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
