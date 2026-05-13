from __future__ import annotations

from copy import deepcopy

from app.domain.models import SessionNarrativeDecision


class SessionNarrativeLayer:
    HEAVY_THRESHOLD = 0.74
    LIGHT_THRESHOLD = 0.38
    LOOKAHEAD_WINDOW = 2

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        narrated = [deepcopy(block) for block in runtime_blocks]
        narrated = self._soften_local_heavy_streaks(narrated)
        return self._annotate_transitions(narrated)

    def _soften_local_heavy_streaks(self, blocks: list[dict]) -> list[dict]:
        softened = list(blocks)
        for index in range(1, len(softened) - 1):
            previous = softened[index - 1]
            current = softened[index]
            if not self._is_softenable_heavy_followup(previous, current):
                continue

            swap_index = self._find_light_bridge_candidate(softened, index)
            if swap_index is None:
                continue
            softened[index], softened[swap_index] = softened[swap_index], softened[index]
        return softened

    def _annotate_transitions(self, blocks: list[dict]) -> list[dict]:
        annotated: list[dict] = []
        previous: dict | None = None
        for block in blocks:
            decision = self._build_decision(previous, block)
            annotated.append({**block, **decision.model_dump(mode="json")})
            previous = annotated[-1]
        return annotated

    def _build_decision(self, previous: dict | None, current: dict) -> SessionNarrativeDecision:
        if previous is None:
            anchor = self._anchor_label(current)
            return SessionNarrativeDecision(
                narrative_relation="session_opening",
                narrative_role="session_anchor",
                continuity_signal=0.3,
                contextual_anchor=anchor,
                transition_reason="Bloco inicial mantido para abrir a progressao curricular da sessao.",
                progression_reason="A sessao comeca pelo primeiro ponto priorizado na trilha atual.",
                why_this_after_previous=f"Este bloco abre a sessao e ancora o contexto em {anchor}.",
            )

        relation = self._relation(previous, current)
        role = self._role_for_relation(relation)
        continuity = self._continuity_signal(previous, current, relation)
        anchor = self._contextual_anchor(previous, current)
        return SessionNarrativeDecision(
            narrative_relation=relation,
            narrative_role=role,
            continuity_signal=continuity,
            contextual_anchor=anchor,
            transition_reason=self._transition_reason(previous, current, relation),
            comparison_reason=self._comparison_reason(previous, current, relation),
            recall_reason=self._recall_reason(previous, current, relation),
            progression_reason=self._progression_reason(previous, current, relation),
            why_this_after_previous=self._why_this_after_previous(previous, current, relation, anchor),
        )

    def _relation(self, previous: dict, current: dict) -> str:
        same_topic = previous.get("topic_id") == current.get("topic_id")
        current_mode = str(current.get("pedagogical_mode") or "")
        current_role = str(current.get("curriculum_role") or "")
        current_intensity = str(current.get("review_intensity") or "")
        previous_score = self._cognitive_load(previous)
        current_score = self._cognitive_load(current)
        stabilization_stage = str(current.get("stabilization_stage") or "")

        if current_role == "cumulative" and current_intensity == "light":
            return "cumulative_resurfacing"
        if current_mode in {"rapid_review", "reinforcement_check", "active_recall"} and (
            float(current.get("longitudinal_retention", 0.0) or 0.0) >= 0.55
        ):
            return "contextual_recall"
        if same_topic and previous.get("type") == "summary" and current_mode == "contextual_application":
            return "application"
        if same_topic and stabilization_stage in {"consolidated", "resilient"} and current_mode in {
            "rapid_review",
            "reinforcement_check",
        }:
            return "stabilization"
        if same_topic and current_mode in {"guided_explanation", "conceptual_reinforcement"}:
            return "reinforcement"
        if same_topic and current_score > previous_score + 0.12:
            return "escalation"
        if same_topic:
            return "continuation"
        if current_score <= previous_score - 0.18 and current_mode in {
            "active_recall",
            "rapid_review",
            "reinforcement_check",
        }:
            return "recall"
        return "contrast"

    def _role_for_relation(self, relation: str) -> str:
        return {
            "session_opening": "session_anchor",
            "reinforcement": "same_topic_progression",
            "application": "same_topic_progression",
            "continuation": "same_topic_progression",
            "escalation": "same_topic_progression",
            "stabilization": "stability_check",
            "recall": "retrieval_bridge",
            "contextual_recall": "retrieval_bridge",
            "cumulative_resurfacing": "cumulative_bridge",
            "contrast": "cross_topic_bridge",
        }.get(relation, "cross_topic_bridge")

    def _continuity_signal(self, previous: dict, current: dict, relation: str) -> float:
        signal = 0.14
        if previous.get("topic_id") == current.get("topic_id"):
            signal += 0.34
        if previous.get("curriculum_role") == current.get("curriculum_role"):
            signal += 0.1
        if relation in {"reinforcement", "application", "continuation", "escalation"}:
            signal += 0.18
        if relation in {"contextual_recall", "cumulative_resurfacing", "stabilization", "recall"}:
            signal += 0.12
        if self._mode_family(previous) == self._mode_family(current):
            signal += 0.08
        if abs(self._cognitive_load(current) - self._cognitive_load(previous)) <= 0.24:
            signal += 0.05
        return round(self._clamp(signal), 4)

    def _transition_reason(self, previous: dict, current: dict, relation: str) -> str:
        reasons = {
            "reinforcement": "O bloco atual reforca o mesmo topico logo apos a base explicativa anterior.",
            "application": "O bloco atual contextualiza a explicacao anterior com foco aplicado no mesmo topico.",
            "continuation": "O bloco atual continua o desenvolvimento do mesmo topico com carga controlada.",
            "escalation": "O bloco atual aprofunda o mesmo topico com pressao cognitiva levemente maior.",
            "stabilization": "O bloco atual revisita o mesmo topico em modo de estabilizacao e manutencao.",
            "recall": "O bloco atual reduz a densidade para recuperar um ponto de forma mais leve.",
            "contextual_recall": "O bloco atual faz recall contextual de um conceito que ja mostrou retencao parcial.",
            "cumulative_resurfacing": "O bloco atual resurfaz um conceito cumulativo para manter retencao ampla.",
            "contrast": "O bloco atual alterna para outro topico sem romper a coerencia do fluxo.",
        }
        default_reason = "O bloco atual preserva a progressao local da sessao."
        return reasons.get(relation, default_reason)

    def _comparison_reason(self, previous: dict, current: dict, relation: str) -> str | None:
        if relation != "contrast":
            return None
        return (
            f"O topico {current.get('topic_title') or current.get('topic_id')} "
            f"entra agora para contrastar com {previous.get('topic_title') or previous.get('topic_id')} "
            "sem quebrar a progressao curricular."
        )

    def _recall_reason(self, previous: dict, current: dict, relation: str) -> str | None:
        if relation == "contextual_recall":
            return "Este bloco reapresenta um ponto relevante em formato de recuperacao contextual."
        if relation == "cumulative_resurfacing":
            return "Este bloco traz de volta um conceito cumulativo em formato mais leve e sustentavel."
        if relation == "recall":
            return "Este bloco reduz a carga para manter o fluxo de recuperacao sem sobrecarga."
        return None

    def _progression_reason(self, previous: dict, current: dict, relation: str) -> str | None:
        if relation == "application":
            return "A aplicacao vem logo depois da explicacao para consolidar transferencia de contexto."
        if relation == "reinforcement":
            return "O reforco imediato preserva continuidade conceitual antes de mudar o foco."
        if relation == "escalation":
            return "A escalada foi mantida porque o mesmo topico ainda exige aprofundamento."
        if relation == "continuation":
            return "A continuidade local evita quebra brusca do raciocinio no mesmo topico."
        if relation == "session_opening":
            return "A sessao abre com um bloco ancora definido pela progressao curricular."
        return None

    def _why_this_after_previous(
        self,
        previous: dict,
        current: dict,
        relation: str,
        anchor: str | None,
    ) -> str:
        if relation == "application":
            return f"Este bloco contextualiza o que acabou de ser explicado em {anchor or self._anchor_label(previous)}."
        if relation == "cumulative_resurfacing":
            return f"Este bloco reaparece agora para manter vivo um conceito cumulativo ligado a {anchor or self._anchor_label(current)}."
        if relation == "contextual_recall":
            return f"Este bloco revisita {anchor or self._anchor_label(current)} em formato de recall contextual."
        if relation == "reinforcement":
            return f"Este bloco reforca {anchor or self._anchor_label(current)} antes de ampliar o contexto."
        if relation == "stabilization":
            return f"Este bloco confirma estabilidade recente em {anchor or self._anchor_label(current)} com pressao reduzida."
        if relation == "recall":
            return "Este bloco reduz a pressao local para preservar ritmo e recuperacao."
        if relation == "escalation":
            return f"Este bloco aprofunda {anchor or self._anchor_label(current)} logo apos a base anterior."
        if relation == "continuation":
            return f"Este bloco continua a trilha local de {anchor or self._anchor_label(current)}."
        return (
            f"Este bloco alterna para {self._anchor_label(current)} mantendo a progressao curricular apos "
            f"{self._anchor_label(previous)}."
        )

    def _contextual_anchor(self, previous: dict, current: dict) -> str:
        if previous.get("topic_id") == current.get("topic_id"):
            return str(current.get("topic_title") or current.get("topic_id") or "")
        return str(previous.get("topic_title") or previous.get("topic_id") or "")

    def _anchor_label(self, block: dict) -> str:
        return str(block.get("topic_title") or block.get("topic_id") or "conteudo atual")

    def _mode_family(self, block: dict) -> str:
        mode = str(block.get("pedagogical_mode") or "")
        if mode in {"guided_explanation", "conceptual_reinforcement"}:
            return "explanation"
        if mode == "contextual_application":
            return "application"
        if mode in {"active_recall", "rapid_review", "reinforcement_check"}:
            return "recall"
        return "generic"

    def _is_softenable_heavy_followup(self, previous: dict, current: dict) -> bool:
        return (
            current.get("type") == "question"
            and int(current.get("_question_index", 0) or 0) > 0
            and self._cognitive_load(current) >= self.HEAVY_THRESHOLD
            and self._cognitive_load(previous) >= self.HEAVY_THRESHOLD - 0.02
        )

    def _find_light_bridge_candidate(self, blocks: list[dict], index: int) -> int | None:
        current_score = self._cognitive_load(blocks[index])
        limit = min(len(blocks), index + 1 + self.LOOKAHEAD_WINDOW)
        for candidate_index in range(index + 1, limit):
            candidate = blocks[candidate_index]
            if not self._is_light_bridge_candidate(candidate):
                continue
            if self._cognitive_load(candidate) <= current_score - 0.18:
                return candidate_index
        return None

    def _is_light_bridge_candidate(self, block: dict) -> bool:
        return (
            block.get("type") == "question"
            and int(block.get("_question_index", 0) or 0) > 0
            and self._cognitive_load(block) <= self.LIGHT_THRESHOLD
            and (
                str(block.get("curriculum_role") or "") == "cumulative"
                or str(block.get("pedagogical_mode") or "") in {"reinforcement_check", "rapid_review", "active_recall"}
            )
        )

    def _cognitive_load(self, block: dict) -> float:
        return self._clamp(float(block.get("cognitive_load_score", 0.5) or 0.5))

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(float(value), maximum))
