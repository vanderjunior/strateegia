from __future__ import annotations

from copy import deepcopy

from app.domain.models import SessionCoherenceDecision
from app.services.pedagogical_expression import expression_family


class SessionCoherenceLayer:
    WINDOW_SIZE = 3

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        recent: list[dict] = []
        for block in [deepcopy(item) for item in runtime_blocks]:
            decision = self._build_decision(recent, block)
            annotated_block = {
                **block,
                **decision.model_dump(mode="json"),
                "pacing_adjustment": round(
                    self._clamp(
                        float(block.get("pacing_adjustment", 0.0) or 0.0)
                        + (0.08 if decision.session_coherence_state in {"retrieval_transition", "cumulative_relief"} else 0.0)
                        + (0.06 if decision.session_coherence_state == "pacing_fragile" else 0.0)
                    ),
                    4,
                ),
                "continuity_support": round(
                    self._clamp(
                        float(block.get("continuity_support", 0.0) or 0.0)
                        + (0.08 if decision.session_coherence_state in {"stable_progression", "continuity_stable", "contextual_shift_softened"} else 0.0)
                        + (0.06 if decision.session_coherence_state == "reinforcement_chain" else 0.0)
                    ),
                    4,
                ),
            }
            annotated.append(annotated_block)
            recent.append(annotated_block)
            recent = recent[-self.WINDOW_SIZE :]
        return annotated

    def _build_decision(self, recent: list[dict], current: dict) -> SessionCoherenceDecision:
        previous = recent[-1] if recent else None
        progression_continuity = self._progression_continuity(previous, current)
        framing_stability = self._framing_stability(recent, current)
        cognitive_rhythm = self._cognitive_rhythm(recent, current)
        state = self._state(
            previous=previous,
            current=current,
            progression_continuity=progression_continuity,
            framing_stability=framing_stability,
            cognitive_rhythm=cognitive_rhythm,
            recent=recent,
        )
        return SessionCoherenceDecision(
            session_coherence_state=state,
            coherence_reasoning=self._coherence_reasoning(
                state=state,
                progression_continuity=progression_continuity,
                framing_stability=framing_stability,
                cognitive_rhythm=cognitive_rhythm,
            ),
            pacing_transition_reason=self._pacing_transition_reason(state, previous, current, cognitive_rhythm),
            progression_continuity=round(progression_continuity, 4),
            coherence_support_reason=self._support_reason(state),
            framing_stability=round(framing_stability, 4),
            cognitive_rhythm=round(cognitive_rhythm, 4),
            continuity_smoothing_reason=self._smoothing_reason(state),
            why_this_transition_now=self._why_now(state, current),
        )

    def _state(
        self,
        *,
        previous: dict | None,
        current: dict,
        progression_continuity: float,
        framing_stability: float,
        cognitive_rhythm: float,
        recent: list[dict],
    ) -> str:
        if self._is_reconstruction_cluster(recent, current):
            return "reconstruction_cluster"
        if self._is_retrieval_transition(previous, current):
            return "retrieval_transition"
        if (
            str(current.get("curriculum_role") or "") == "cumulative"
            and str(current.get("narrative_relation") or "") in {"cumulative_resurfacing", "contextual_recall", "recall"}
            and float(current.get("cognitive_load_score", 0.5) or 0.5) <= 0.4
        ):
            return "cumulative_relief"
        if progression_continuity >= 0.72 and framing_stability >= 0.62 and cognitive_rhythm >= 0.55:
            if str(current.get("pedagogical_mode") or "") in {"guided_explanation", "conceptual_reinforcement"}:
                return "conceptually_progressive"
            return "stable_progression"
        if progression_continuity >= 0.62 and framing_stability >= 0.58:
            return "continuity_stable"
        if self._is_reinforcement_chain(recent, current):
            return "reinforcement_chain"
        if progression_continuity <= 0.42 or framing_stability <= 0.38 or cognitive_rhythm <= 0.32:
            return "pacing_fragile"
        if previous and previous.get("topic_id") != current.get("topic_id") and framing_stability >= 0.5:
            return "contextual_shift_softened"
        return "stable_progression"

    def _progression_continuity(self, previous: dict | None, current: dict) -> float:
        if previous is None:
            return 0.52
        signal = float(current.get("continuity_signal", 0.55) or 0.55) * 0.55
        if previous.get("topic_id") == current.get("topic_id"):
            signal += 0.18
        if previous.get("curriculum_role") == current.get("curriculum_role"):
            signal += 0.08
        if abs(self._load(previous) - self._load(current)) <= 0.24:
            signal += 0.08
        if str(previous.get("narrative_relation") or "") == str(current.get("narrative_relation") or ""):
            signal += 0.06
        return self._clamp(signal)

    def _framing_stability(self, recent: list[dict], current: dict) -> float:
        if not recent:
            return 0.56
        previous = recent[-1]
        stability = 0.3
        if expression_family(previous.get("pedagogical_expression_mode")) == expression_family(
            current.get("pedagogical_expression_mode")
        ):
            stability += 0.22
        if self._mode_family(previous) == self._mode_family(current):
            stability += 0.18
        if str(previous.get("micro_intervention") or "") == str(current.get("micro_intervention") or ""):
            stability += 0.08
        if self._compression_family(previous) == self._compression_family(current):
            stability += 0.08
        if abs(self._load(previous) - self._load(current)) <= 0.24:
            stability += 0.1
        return self._clamp(stability)

    def _cognitive_rhythm(self, recent: list[dict], current: dict) -> float:
        window = recent[-2:] + [current]
        loads = [self._load(block) for block in window]
        if len(loads) == 1:
            return 0.58
        deltas = [abs(loads[index] - loads[index - 1]) for index in range(1, len(loads))]
        average_delta = sum(deltas) / len(deltas)
        return self._clamp(0.82 - average_delta * 1.25)

    def _is_reconstruction_cluster(self, recent: list[dict], current: dict) -> bool:
        relevant = recent[-1:] + [current]
        if len(relevant) < 2:
            return False
        return all(
            str(block.get("pedagogical_expression_mode") or "") == "focused_reconstruction"
            or str(block.get("micro_intervention") or "") == "guided_reconstruction"
            for block in relevant
        )

    def _is_retrieval_transition(self, previous: dict | None, current: dict) -> bool:
        if previous is None:
            return False
        previous_retrieval = str(previous.get("retrieval_intensity") or "")
        current_retrieval = str(current.get("retrieval_intensity") or "")
        return (
            previous_retrieval == "high"
            and current_retrieval in {"medium", "low"}
            and str(current.get("pedagogical_expression_mode") or "") == "retrieval_softener"
        )

    def _is_reinforcement_chain(self, recent: list[dict], current: dict) -> bool:
        chain = recent[-1:] + [current]
        if len(chain) < 2:
            return False
        return all(
            str(block.get("narrative_relation") or "") in {"reinforcement", "continuation", "application"}
            and block.get("topic_id") == current.get("topic_id")
            for block in chain
        )

    def _coherence_reasoning(
        self,
        *,
        state: str,
        progression_continuity: float,
        framing_stability: float,
        cognitive_rhythm: float,
    ) -> list[str]:
        return [
            f"Estado de coerencia: {state}.",
            f"Continuidade progressiva: {progression_continuity:.2f}.",
            f"Estabilidade de framing: {framing_stability:.2f}.",
            f"Ritmo cognitivo local: {cognitive_rhythm:.2f}.",
        ]

    def _pacing_transition_reason(
        self,
        state: str,
        previous: dict | None,
        current: dict,
        cognitive_rhythm: float,
    ) -> str:
        if state == "retrieval_transition":
            return "A transicao atual reduziu a pressao de recuperacao para preservar ritmo."
        if state == "reconstruction_cluster":
            return "A sessao concentrou reconstrucao em janela curta e manteve esse cluster de forma explicita."
        if state == "cumulative_relief":
            return "A reapresentacao cumulativa entrou em faixa mais leve para aliviar a sessao."
        if state == "pacing_fragile":
            return "A mudanca local de framing ficou mais brusca e recebeu suporte de coerencia."
        if previous and previous.get("topic_id") != current.get("topic_id"):
            return f"A transicao entre {previous.get('topic_id')} e {current.get('topic_id')} foi mantida com troca controlada."
        return f"Ritmo local mantido em faixa estavel ({cognitive_rhythm:.2f})."

    def _support_reason(self, state: str) -> str | None:
        return {
            "reconstruction_cluster": "A coerencia local preservou um bloco curto de reconstrucao antes de aliviar a sessao.",
            "retrieval_transition": "A coerencia local suavizou a passagem de recall intenso para verificacao mais leve.",
            "cumulative_relief": "A coerencia local sustentou resurfacing com menor atrito cognitivo.",
            "pacing_fragile": "A coerencia local tentou reduzir a sensacao de quebra abrupta.",
            "reinforcement_chain": "A coerencia local preservou uma cadeia curta de reforco antes da troca de foco.",
        }.get(state)

    def _smoothing_reason(self, state: str) -> str | None:
        return {
            "stable_progression": "A progressao local permaneceu suave e previsivel.",
            "conceptually_progressive": "A sessao manteve aprofundamento conceitual com legibilidade suficiente.",
            "continuity_stable": "A continuidade entre blocos permaneceu bem sustentada.",
            "contextual_shift_softened": "A troca de contexto foi suavizada por framing local compativel.",
            "pacing_fragile": "A camada de coerencia sinalizou fragilidade de pacing para reduzir friccao percebida.",
        }.get(state)

    def _why_now(self, state: str, current: dict) -> str:
        if state == "reconstruction_cluster":
            return "Este bloco aparece agora dentro de um cluster curto de reconstrucao ainda coeso."
        if state == "retrieval_transition":
            return "Este bloco aparece agora para aliviar uma sequencia de recuperacao mais intensa."
        if state == "cumulative_relief":
            return "Este bloco aparece agora como alivio cumulativo sem perder a trilha de revisao."
        if state == "pacing_fragile":
            return "Este bloco aparece agora com suporte de coerencia porque a janela recente ficou irregular."
        if state == "contextual_shift_softened":
            return "Este bloco aparece agora com troca de contexto suavizada para manter progressao legivel."
        return f"Este bloco aparece agora dentro de uma progressao local coerente em {current.get('topic_id') or 'conteudo atual'}."

    def _mode_family(self, block: dict) -> str:
        mode = str(block.get("pedagogical_mode") or "")
        if mode in {"guided_explanation", "conceptual_reinforcement"}:
            return "explanation"
        if mode == "contextual_application":
            return "application"
        if mode in {"active_recall", "rapid_review", "reinforcement_check"}:
            return "recall"
        return "generic"

    def _compression_family(self, block: dict) -> str:
        mode = str(block.get("cognitive_compression_mode") or "")
        if mode in {"guided_compact", "stable_compressed", "reinforcement_condensed", "cumulative_lightweight"}:
            return "compact"
        if mode in {"prerequisite_supported", "transfer_expanded", "context_supported"}:
            return "supported"
        if mode in {"retrieval_focused", "reconstruction_scaffolded"}:
            return "retrieval"
        return "neutral"

    def _load(self, block: dict) -> float:
        return self._clamp(float(block.get("cognitive_load_score", 0.5) or 0.5))

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(float(value), maximum))
