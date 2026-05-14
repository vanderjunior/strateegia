from __future__ import annotations

from app.domain.models import (
    ConceptualRelationship,
    MicroTopic,
    RelationshipSignal,
    RelationshipType,
    TopicNode,
)


class ConceptualRelationshipsLayer:
    BASE_TITLES = {"conceito", "definicao", "regra"}
    EXCEPTION_TITLES = {"excecao"}
    APPLICATION_TITLES = {"aplicacao"}
    OBSERVATION_TITLES = {"observacao"}
    REQUIRES_MARKERS = ("depende", "requer", "exige", "pressupoe")
    CONTRAST_MARKERS = ("porem", "porém", "diferente de", "ao contrario", "entretanto", "however")

    def extract(
        self,
        topic_node: TopicNode | None,
        microtopics: list[MicroTopic],
    ) -> list[ConceptualRelationship]:
        if not microtopics:
            return []

        relationships: list[ConceptualRelationship] = []
        seen: set[tuple[str, str, str]] = set()

        for index, current in enumerate(microtopics):
            previous = microtopics[index - 1] if index > 0 else None
            if previous is None:
                continue

            previous_kind = self._kind(previous)
            current_kind = self._kind(current)
            normalized_content = self._normalize(current.content)
            nearest_base = self._nearest_base(microtopics, index)

            if previous_kind == "base" and current_kind == "exception":
                self._push(
                    relationships,
                    seen,
                    previous,
                    current,
                    RelationshipType.EXCEPTION_OF.value,
                    "A excecao depende da regra geral imediatamente anterior.",
                    0.72,
                )
            if nearest_base is not None and current_kind == "application":
                self._push(
                    relationships,
                    seen,
                    nearest_base,
                    current,
                    RelationshipType.APPLIED_BY.value,
                    "A aplicacao usa a base conceitual apresentada logo antes.",
                    0.76,
                )
            if previous_kind in {"base", "exception"} and any(
                marker in normalized_content for marker in self.REQUIRES_MARKERS
            ):
                self._push(
                    relationships,
                    seen,
                    previous,
                    current,
                    RelationshipType.PREREQUISITE.value,
                    "O bloco atual explicita dependencia conceitual do ponto anterior.",
                    0.68,
                )
            if previous_kind in {"base", "exception", "application"} and current_kind == "observation":
                self._push(
                    relationships,
                    seen,
                    previous,
                    current,
                    RelationshipType.REINFORCES.value,
                    "A observacao reforca o ponto imediatamente anterior.",
                    0.46,
                )
            if any(marker in normalized_content for marker in self.CONTRAST_MARKERS):
                self._push(
                    relationships,
                    seen,
                    previous,
                    current,
                    RelationshipType.CONTRASTS_WITH.value,
                    "O bloco atual introduz contraste local em relacao ao anterior.",
                    0.52,
                )

        return relationships

    def _nearest_base(self, microtopics: list[MicroTopic], index: int) -> MicroTopic | None:
        for pointer in range(index - 1, -1, -1):
            candidate = microtopics[pointer]
            if self._kind(candidate) == "base":
                return candidate
        return None

    def _push(
        self,
        relationships: list[ConceptualRelationship],
        seen: set[tuple[str, str, str]],
        source: MicroTopic,
        target: MicroTopic,
        relationship_type: str,
        reason: str,
        strength: float,
    ) -> None:
        key = (source.id, target.id, relationship_type)
        if key in seen:
            return
        seen.add(key)
        relationships.append(
            ConceptualRelationship(
                source_microtopic_id=source.id,
                target_microtopic_id=target.id,
                relationship_type=relationship_type,
                reason=reason,
                strength=strength,
            )
        )

    def _kind(self, microtopic: MicroTopic) -> str:
        title = self._normalize(microtopic.title)
        if title in self.BASE_TITLES:
            return "base"
        if title in self.EXCEPTION_TITLES:
            return "exception"
        if title in self.APPLICATION_TITLES:
            return "application"
        if title in self.OBSERVATION_TITLES:
            return "observation"
        return "generic"

    def _normalize(self, value: str) -> str:
        normalized = value.strip().lower()
        replacements = str.maketrans(
            {
                "á": "a",
                "à": "a",
                "â": "a",
                "ã": "a",
                "é": "e",
                "ê": "e",
                "í": "i",
                "ó": "o",
                "ô": "o",
                "õ": "o",
                "ú": "u",
                "ç": "c",
            }
        )
        return normalized.translate(replacements)


def build_relationship_signals(
    microtopics: list[MicroTopic],
    relationships: list[ConceptualRelationship],
) -> dict[str, RelationshipSignal]:
    by_id = {microtopic.id: microtopic for microtopic in microtopics}
    signals = {microtopic.id: RelationshipSignal() for microtopic in microtopics}

    for relationship in relationships:
        source = by_id.get(relationship.source_microtopic_id)
        target = by_id.get(relationship.target_microtopic_id)
        if source is None or target is None:
            continue

        source_signal = signals[source.id]
        target_signal = signals[target.id]

        prerequisite_weight = relationship.strength * 0.7 if relationship.relationship_type in {
            RelationshipType.PREREQUISITE.value,
            RelationshipType.EXCEPTION_OF.value,
            RelationshipType.APPLIED_BY.value,
        } else 0.0

        target_signal.relationship_type = relationship.relationship_type
        target_signal.relationship_reason = relationship.reason
        target_signal.conceptual_anchor = source.title
        target_signal.anchor_microtopic_id = source.id
        target_signal.prerequisite_signal = _clamp(
            max(target_signal.prerequisite_signal, prerequisite_weight)
        )
        target_signal.conceptual_transition = _transition_label(relationship.relationship_type)
        target_signal.semantic_continuity_reason = _continuity_reason(
            source.title,
            target.title,
            relationship.relationship_type,
        )
        target_signal.why_this_before_that = (
            f"{source.title} deve aparecer antes de {target.title} para sustentar o encadeamento conceitual."
        )
        if relationship.relationship_type == RelationshipType.EXCEPTION_OF.value:
            target_signal.reinforcement_reason = f"A excecao se apoia na regra base {source.title}."
        elif relationship.relationship_type == RelationshipType.APPLIED_BY.value:
            target_signal.reinforcement_reason = f"A aplicacao depende da base {source.title}."

        source_signal.support_signal = _clamp(
            source_signal.support_signal + min(0.22, relationship.strength * 0.28)
        )
        if source_signal.relationship_reason is None:
            source_signal.relationship_reason = f"{source.title} sustenta {target.title}."
        if source_signal.conceptual_anchor is None:
            source_signal.conceptual_anchor = source.title

    return signals


def _transition_label(relationship_type: str) -> str:
    return {
        RelationshipType.PREREQUISITE.value: "prerequisite_support",
        RelationshipType.EXCEPTION_OF.value: "rule_before_exception",
        RelationshipType.APPLIED_BY.value: "foundation_before_application",
        RelationshipType.REINFORCES.value: "local_reinforcement",
        RelationshipType.CONTRASTS_WITH.value: "contrast_transition",
        RelationshipType.CUMULATIVE_EXTENSION.value: "cumulative_extension",
    }.get(relationship_type, "local_continuity")


def _continuity_reason(source_title: str, target_title: str, relationship_type: str) -> str:
    reasons = {
        RelationshipType.PREREQUISITE.value: f"{source_title} fornece base necessaria para {target_title}.",
        RelationshipType.EXCEPTION_OF.value: f"{target_title} deve ser lido como ressalva de {source_title}.",
        RelationshipType.APPLIED_BY.value: f"{target_title} contextualiza a base apresentada em {source_title}.",
        RelationshipType.REINFORCES.value: f"{target_title} reforca o que foi apresentado em {source_title}.",
        RelationshipType.CONTRASTS_WITH.value: f"{target_title} contrasta localmente com {source_title}.",
        RelationshipType.CUMULATIVE_EXTENSION.value: f"{target_title} estende gradualmente {source_title}.",
    }
    return reasons.get(relationship_type, f"{target_title} se conecta localmente a {source_title}.")


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))
