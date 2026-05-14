from __future__ import annotations

from copy import deepcopy

from app.domain.models import (
    CognitiveMomentumSignal,
    CognitiveMomentumState,
    MomentumTrend,
    SessionCognitiveSnapshot,
)


class CognitiveMomentumLayer:
    WINDOW_SIZE = 3

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        recent_blocks: list[dict] = []
        for block in [deepcopy(item) for item in runtime_blocks]:
            state = self._build_state(recent_blocks, block)
            annotated_block = {
                **block,
                "cognitive_momentum": state.cognitive_momentum,
                "momentum_signal": state.momentum_signal.model_dump(mode="json"),
                "conceptual_density_reason": state.conceptual_density_reason,
                "retrieval_fatigue_reason": state.retrieval_fatigue_reason,
                "continuity_pressure_reason": state.continuity_pressure_reason,
                "stabilization_balance_reason": state.stabilization_balance_reason,
                "pacing_relief_reason": state.pacing_relief_reason,
                "why_this_relief_now": state.why_this_relief_now,
                "cognitive_session_state": state.cognitive_session_state.model_dump(mode="json"),
                "local_momentum_reasoning": state.local_momentum_reasoning,
            }
            annotated.append(annotated_block)
            recent_blocks.append(annotated_block)
            recent_blocks = recent_blocks[-self.WINDOW_SIZE :]
        return annotated

    def _build_state(self, recent_blocks: list[dict], current_block: dict) -> CognitiveMomentumState:
        window = recent_blocks[-(self.WINDOW_SIZE - 1) :] + [current_block]
        conceptual_density = self._average(self._conceptual_weight(block) for block in window)
        abstraction_load = self._average(self._abstraction_weight(block) for block in window)
        retrieval_fatigue = self._average(self._retrieval_weight(block) for block in window)
        intervention_fatigue = self._intervention_fatigue(window)
        continuity_stability = self._continuity_stability(window)
        stabilization_balance = self._average(self._stabilization_weight(block) for block in window)
        resurfacing_balance = self._average(self._resurfacing_weight(block) for block in window)
        cognitive_pressure = self._clamp(
            conceptual_density * 0.28
            + abstraction_load * 0.22
            + retrieval_fatigue * 0.18
            + intervention_fatigue * 0.16
            + max(0.0, 0.5 - continuity_stability) * 0.24
            + max(0.0, 0.42 - resurfacing_balance) * 0.12
            - stabilization_balance * 0.12
        )

        signal = CognitiveMomentumSignal(
            conceptual_density=round(conceptual_density, 4),
            abstraction_load=round(abstraction_load, 4),
            retrieval_fatigue=round(retrieval_fatigue, 4),
            intervention_fatigue=round(intervention_fatigue, 4),
            continuity_stability=round(continuity_stability, 4),
            stabilization_balance=round(stabilization_balance, 4),
            cognitive_pressure=round(cognitive_pressure, 4),
            resurfacing_balance=round(resurfacing_balance, 4),
        )
        trend = self._trend(signal)
        snapshot = SessionCognitiveSnapshot(
            state_label=trend.value,
            window_size=len(window),
            heavy_block_count=sum(1 for block in window if self._load_score(block) >= 0.72),
            retrieval_heavy_count=sum(1 for block in window if self._retrieval_weight(block) >= 0.68),
            continuity_average=round(continuity_stability, 4),
        )
        return CognitiveMomentumState(
            cognitive_momentum=trend.value,
            momentum_signal=signal,
            conceptual_density_reason=self._conceptual_density_reason(signal),
            retrieval_fatigue_reason=self._retrieval_reason(signal),
            continuity_pressure_reason=self._continuity_reason(signal),
            stabilization_balance_reason=self._stabilization_reason(signal),
            pacing_relief_reason=self._pacing_relief_reason(signal),
            why_this_relief_now=self._why_this_relief_now(signal, current_block, trend),
            cognitive_session_state=snapshot,
            local_momentum_reasoning=self._momentum_reasoning(signal, trend),
        )

    def _conceptual_weight(self, block: dict) -> float:
        mode = str(block.get("pedagogical_mode") or "")
        depth = str(block.get("explanation_depth") or "light")
        relationship_type = str(block.get("relationship_type") or "")
        weight = {
            "guided_explanation": 0.78,
            "conceptual_reinforcement": 0.72,
            "contextual_application": 0.52,
            "active_recall": 0.34,
            "rapid_review": 0.18,
            "reinforcement_check": 0.12,
        }.get(mode, 0.2)
        weight += {"deep": 0.14, "medium": 0.07, "light": 0.02}.get(depth, 0.02)
        if relationship_type in {"prerequisite", "exception_of", "applied_by"}:
            weight += 0.08
        return self._clamp(weight)

    def _abstraction_weight(self, block: dict) -> float:
        block_type = str(block.get("type") or "")
        depth = str(block.get("explanation_depth") or "light")
        narrative_relation = str(block.get("narrative_relation") or "")
        weight = 0.18 if block_type == "summary" else 0.08
        weight += {"deep": 0.24, "medium": 0.12, "light": 0.03}.get(depth, 0.03)
        if narrative_relation in {"contrast", "application", "escalation"}:
            weight += 0.08
        return self._clamp(weight)

    def _retrieval_weight(self, block: dict) -> float:
        retrieval = str(block.get("retrieval_intensity") or "low")
        mode = str(block.get("pedagogical_mode") or "")
        micro_intervention = str(block.get("micro_intervention") or "")
        weight = {"high": 0.82, "medium": 0.5, "low": 0.18}.get(retrieval, 0.18)
        if mode == "active_recall":
            weight += 0.08
        if micro_intervention in {"semantic_reactivation", "prerequisite_recall"}:
            weight += 0.06
        return self._clamp(weight)

    def _intervention_fatigue(self, window: list[dict]) -> float:
        interventions = [str(block.get("micro_intervention") or "") for block in window if block.get("micro_intervention")]
        if not interventions:
            return 0.0
        last = interventions[-1]
        consecutive = 0
        for intervention in reversed(interventions):
            if intervention == last:
                consecutive += 1
            else:
                break
        fatigue = max(0.0, (consecutive - 1) * 0.22)
        return self._clamp(fatigue + self._average(float(block.get("intervention_fatigue", 0.0) or 0.0) for block in window) * 0.4)

    def _continuity_stability(self, window: list[dict]) -> float:
        raw = [float(block.get("continuity_signal", 0.55) or 0.55) for block in window]
        stability = self._average(raw)
        contrast_penalty = sum(
            0.08 for block in window if str(block.get("narrative_relation") or "") == "contrast"
        )
        return self._clamp(stability - contrast_penalty)

    def _stabilization_weight(self, block: dict) -> float:
        retention = float(block.get("longitudinal_retention", 0.0) or 0.0)
        stage = str(block.get("stabilization_stage") or "")
        mode = str(block.get("micro_intervention") or "")
        weight = retention * 0.72
        weight += {
            "resilient": 0.22,
            "consolidated": 0.16,
            "stabilizing": 0.1,
        }.get(stage, 0.0)
        if mode in {"confidence_check", "lightweight_retrieval"}:
            weight += 0.08
        return self._clamp(weight)

    def _resurfacing_weight(self, block: dict) -> float:
        narrative_relation = str(block.get("narrative_relation") or "")
        curriculum_role = str(block.get("curriculum_role") or "")
        weight = 0.0
        if curriculum_role == "cumulative":
            weight += 0.24
        if narrative_relation in {"cumulative_resurfacing", "contextual_recall", "recall"}:
            weight += 0.36
        if str(block.get("micro_intervention") or "") in {"cumulative_bridge", "confidence_check", "lightweight_retrieval"}:
            weight += 0.16
        return self._clamp(weight)

    def _trend(self, signal: CognitiveMomentumSignal) -> MomentumTrend:
        if signal.cognitive_pressure >= 0.68:
            return MomentumTrend.PRESSURED
        if signal.retrieval_fatigue >= 0.55:
            return MomentumTrend.RETRIEVAL_HEAVY
        if signal.conceptual_density >= 0.66:
            return MomentumTrend.CONCEPTUALLY_DENSE
        if signal.continuity_stability <= 0.32:
            return MomentumTrend.CONTINUITY_FRAGILE
        if signal.stabilization_balance >= 0.58 and signal.cognitive_pressure <= 0.42:
            return MomentumTrend.BALANCED
        return MomentumTrend.STABLE

    def _conceptual_density_reason(self, signal: CognitiveMomentumSignal) -> str:
        if signal.conceptual_density >= 0.66:
            return "A sessao acumulou densidade conceitual alta em janela curta."
        if signal.conceptual_density <= 0.32:
            return "A densidade conceitual permaneceu leve e sustentavel."
        return "A densidade conceitual permaneceu em faixa moderada."

    def _retrieval_reason(self, signal: CognitiveMomentumSignal) -> str:
        if signal.retrieval_fatigue >= 0.55:
            return "A recuperacao recente ficou intensa e pode pedir alivio local."
        if signal.retrieval_fatigue <= 0.24:
            return "A recuperacao recente permaneceu controlada."
        return "A recuperacao manteve pressao moderada."

    def _continuity_reason(self, signal: CognitiveMomentumSignal) -> str:
        if signal.continuity_stability <= 0.32:
            return "A continuidade local perdeu estabilidade e pede ancoragem adicional."
        if signal.continuity_stability >= 0.62:
            return "A continuidade local permaneceu bem sustentada."
        return "A continuidade local ficou aceitavel, sem ruptura forte."

    def _stabilization_reason(self, signal: CognitiveMomentumSignal) -> str:
        if signal.stabilization_balance >= 0.58:
            return "A janela recente mostrou bom equilibrio entre consolidacao e reaparecimento."
        if signal.stabilization_balance <= 0.25:
            return "Ainda ha pouca estabilizacao acumulada na janela recente."
        return "A estabilizacao recente ficou em faixa intermediaria."

    def _pacing_relief_reason(self, signal: CognitiveMomentumSignal) -> str:
        if signal.cognitive_pressure >= 0.68:
            return "Pressao cognitiva elevada detectada; alivio local passa a ser desejavel."
        if signal.intervention_fatigue >= 0.32:
            return "Repeticao de micro-intervencao sugere alivio de ritmo."
        if signal.retrieval_fatigue >= 0.55:
            return "Carga de recuperacao elevada sugere pequenas pausas de densidade."
        return "Nao houve necessidade de alivio adicional relevante nesta janela."

    def _why_this_relief_now(
        self,
        signal: CognitiveMomentumSignal,
        current_block: dict,
        trend: MomentumTrend,
    ) -> str:
        if trend == MomentumTrend.PRESSURED:
            return "A janela recente concentrou carga demais; este bloco deve ser lido com alivio local em mente."
        if trend == MomentumTrend.RETRIEVAL_HEAVY:
            return "A sessao entrou em fase de recuperacao intensa e pede moderacao local."
        if trend == MomentumTrend.CONCEPTUALLY_DENSE:
            return "A sequencia recente acumulou abstração; este ponto se beneficia de ancoragem mais clara."
        if trend == MomentumTrend.CONTINUITY_FRAGILE:
            return "A continuidade recente enfraqueceu; este bloco pede apoio de contexto."
        if trend == MomentumTrend.BALANCED:
            return "A sessao manteve bom equilibrio recente; este bloco pode seguir com baixa friccao."
        return (
            f"A sessao segue estavel; o bloco atual ({current_block.get('topic_id') or 'conteudo atual'}) "
            "nao exige alivio adicional."
        )

    def _momentum_reasoning(
        self,
        signal: CognitiveMomentumSignal,
        trend: MomentumTrend,
    ) -> list[str]:
        reasoning = [f"Tendencia local identificada: {trend.value}."]
        if signal.conceptual_density >= 0.6:
            reasoning.append("A densidade conceitual recente elevou a pressao da janela.")
        if signal.retrieval_fatigue >= 0.45:
            reasoning.append("A recuperacao recente ficou suficientemente repetida para gerar fadiga local.")
        if signal.continuity_stability <= 0.35:
            reasoning.append("A continuidade recente ficou fragil e merece suporte adicional.")
        if signal.stabilization_balance >= 0.5:
            reasoning.append("A sessao ainda preserva boa base de estabilizacao.")
        return reasoning

    def _load_score(self, block: dict) -> float:
        return self._clamp(float(block.get("cognitive_load_score", 0.5) or 0.5))

    def _average(self, values) -> float:
        collected = list(values)
        if not collected:
            return 0.0
        return self._clamp(sum(float(value) for value in collected) / len(collected))

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(float(value), maximum))
