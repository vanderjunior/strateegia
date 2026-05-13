from __future__ import annotations

from copy import deepcopy

from app.domain.models import SessionEquilibriumDecision


class SessionEquilibriumLayer:
    HEAVY_THRESHOLD = 0.72
    LIGHT_THRESHOLD = 0.5
    LOOKAHEAD_WINDOW = 3

    def balance(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        balanced = [deepcopy(block) for block in runtime_blocks]
        balanced = self._rebalance_local_order(balanced)
        return self._annotate_equilibrium_metadata(balanced)

    def _rebalance_local_order(self, blocks: list[dict]) -> list[dict]:
        rebalanced = list(blocks)
        for index, block in enumerate(rebalanced):
            if not self._is_movable_heavy_question(block):
                continue
            if self._recent_heavy_streak(rebalanced, index) < 2:
                continue

            swap_index = self._find_lighter_candidate(rebalanced, index)
            if swap_index is None:
                continue
            rebalanced[index], rebalanced[swap_index] = rebalanced[swap_index], rebalanced[index]
        return rebalanced

    def _annotate_equilibrium_metadata(self, blocks: list[dict]) -> list[dict]:
        annotated: list[dict] = []
        recent_loads: list[float] = []
        recent_modes: list[str] = []

        for block in blocks:
            load_score = self._cognitive_load_score(block)
            rotation_pressure = self._rotation_pressure(recent_modes, block)
            density = self._session_density(recent_loads, load_score)
            cumulative_fatigue = self._cumulative_fatigue_signal(block)
            equilibrium_pressure = self._clamp(
                max(0.0, density - 0.58) * 0.6
                + rotation_pressure * 0.25
                + cumulative_fatigue * 0.2
            )
            pacing_signal = self._clamp(
                max(0.0, load_score - 0.55) * 0.45
                + max(0.0, density - 0.6) * 0.25
            )

            adjusted_score = self._clamp(
                load_score - equilibrium_pressure * 0.12 - cumulative_fatigue * 0.08
            )
            decision = SessionEquilibriumDecision(
                cognitive_load=self._load_label(adjusted_score),
                cognitive_load_score=round(adjusted_score, 4),
                session_density=round(density, 4),
                intervention_rotation_pressure=round(rotation_pressure, 4),
                equilibrium_pressure=round(equilibrium_pressure, 4),
                pacing_signal=round(pacing_signal, 4),
                cumulative_fatigue_signal=round(cumulative_fatigue, 4),
                equilibrium_reason=self._equilibrium_reason(adjusted_score, equilibrium_pressure),
                pacing_reason=self._pacing_reason(density, pacing_signal),
                intervention_rotation_reason=self._rotation_reason(rotation_pressure, block),
                density_reason=self._density_reason(density),
                fatigue_mitigation_reason=self._fatigue_reason(cumulative_fatigue, block),
                why_this_block_now=self._why_this_block_now(block, adjusted_score, density),
            )

            annotated.append(
                {
                    **block,
                    **decision.model_dump(mode="json"),
                }
            )
            recent_loads.append(adjusted_score)
            recent_modes.append(str(block.get("pedagogical_mode") or ""))
            recent_loads = recent_loads[-3:]
            recent_modes = recent_modes[-3:]

        return annotated

    def _find_lighter_candidate(self, blocks: list[dict], index: int) -> int | None:
        current_score = self._cognitive_load_score(blocks[index])
        limit = min(len(blocks), index + 1 + self.LOOKAHEAD_WINDOW)
        for candidate_index in range(index + 1, limit):
            candidate = blocks[candidate_index]
            if not self._is_movable_light_candidate(candidate):
                continue
            if self._cognitive_load_score(candidate) <= current_score - 0.18:
                return candidate_index
        return None

    def _recent_heavy_streak(self, blocks: list[dict], index: int) -> int:
        streak = 0
        pointer = index - 1
        while pointer >= 0:
            candidate = blocks[pointer]
            if candidate.get("type") == "summary":
                pointer -= 1
                continue
            if self._cognitive_load_score(candidate) >= self.HEAVY_THRESHOLD:
                streak += 1
                pointer -= 1
                continue
            break
        return streak

    def _is_movable_heavy_question(self, block: dict) -> bool:
        return (
            block.get("type") == "question"
            and int(block.get("_question_index", 0) or 0) > 0
            and self._cognitive_load_score(block) >= self.HEAVY_THRESHOLD
        )

    def _is_movable_light_candidate(self, block: dict) -> bool:
        return (
            block.get("type") == "question"
            and int(block.get("_question_index", 0) or 0) > 0
            and self._cognitive_load_score(block) <= self.LIGHT_THRESHOLD
        )

    def _cognitive_load_score(self, block: dict) -> float:
        block_type = block.get("type")
        mode = str(block.get("pedagogical_mode") or "")
        depth = str(block.get("explanation_depth") or "light")
        retrieval = str(block.get("retrieval_intensity") or "low")
        curriculum_role = str(block.get("curriculum_role") or "active")
        review_intensity = str(block.get("review_intensity") or "light")
        retention = float(block.get("longitudinal_retention", 0.0) or 0.0)
        fatigue = float(block.get("intervention_fatigue", 0.0) or 0.0)

        base = 0.42 if block_type == "summary" else 0.36
        base += {
            "guided_explanation": 0.20,
            "conceptual_reinforcement": 0.16,
            "contextual_application": 0.13,
            "active_recall": 0.11,
            "rapid_review": 0.05,
            "reinforcement_check": 0.02,
        }.get(mode, 0.04)
        base += {"deep": 0.22, "medium": 0.12, "light": 0.04}.get(depth, 0.04)
        base += {"high": 0.22, "medium": 0.11, "low": 0.02}.get(retrieval, 0.02)
        base += {"deep": 0.06, "medium": 0.03, "light": 0.0}.get(review_intensity, 0.0)
        if curriculum_role == "cumulative":
            base -= 0.06
        base -= retention * 0.14
        base -= fatigue * 0.06
        return self._clamp(base)

    def _rotation_pressure(self, recent_modes: list[str], block: dict) -> float:
        mode = str(block.get("pedagogical_mode") or "")
        if not mode or not recent_modes:
            return 0.0
        consecutive = 0
        for recent_mode in reversed(recent_modes):
            if recent_mode == mode:
                consecutive += 1
            else:
                break
        return self._clamp(consecutive * 0.18)

    def _session_density(self, recent_loads: list[float], current_load: float) -> float:
        values = recent_loads[-2:] + [current_load]
        return self._clamp(sum(values) / len(values))

    def _cumulative_fatigue_signal(self, block: dict) -> float:
        if str(block.get("curriculum_role") or "") != "cumulative":
            return 0.0
        retention = float(block.get("longitudinal_retention", 0.0) or 0.0)
        fatigue = float(block.get("intervention_fatigue", 0.0) or 0.0)
        return self._clamp(retention * 0.35 + fatigue * 0.4)

    def _equilibrium_reason(self, load_score: float, equilibrium_pressure: float) -> str:
        if equilibrium_pressure >= 0.25:
            return "Pressao de equilibrio detectada; o bloco foi suavizado para preservar sustentabilidade cognitiva."
        if load_score >= self.HEAVY_THRESHOLD:
            return "Bloco mantido com carga alta por relevancia pedagogica, mas dentro de limite controlado."
        return "Bloco mantido em faixa equilibrada para continuidade da sessao."

    def _pacing_reason(self, density: float, pacing_signal: float) -> str:
        if pacing_signal >= 0.2:
            return f"Sequencia recente estava densa ({density:.2f}); o pacing foi levemente suavizado."
        return f"Pacing estavel com densidade controlada ({density:.2f})."

    def _rotation_reason(self, rotation_pressure: float, block: dict) -> str:
        if rotation_pressure >= 0.25:
            return f"Repeticao de {block.get('pedagogical_mode') or 'intervencao'} detectada; variacao leve priorizada."
        return "Rotacao de intervencao dentro do intervalo esperado."

    def _density_reason(self, density: float) -> str:
        if density >= 0.7:
            return "Densidade alta detectada; blocos leves receberam prioridade local quando disponiveis."
        if density <= 0.4:
            return "Densidade leve preservada para manter fluidez de revisao."
        return "Densidade moderada mantida para equilibrio entre explicacao e recuperacao."

    def _fatigue_reason(self, cumulative_fatigue: float, block: dict) -> str:
        if cumulative_fatigue >= 0.35:
            return "Conteudo cumulativo estavel recebeu mitigacao de fadiga para evitar sobrecarga repetitiva."
        if float(block.get("intervention_fatigue", 0.0) or 0.0) >= 0.35:
            return "Fadiga de intervencao monitorada; pressao mantida em nivel moderado."
        return "Sem mitigacao adicional de fadiga necessaria neste bloco."

    def _why_this_block_now(self, block: dict, load_score: float, density: float) -> str:
        reason = block.get("why_this_now")
        if isinstance(reason, list) and reason:
            prefix = reason[0]
        elif isinstance(reason, str) and reason:
            prefix = reason
        else:
            prefix = "Bloco mantido pela selecao adaptativa anterior."
        return f"{prefix} Equilibrio atual: carga {load_score:.2f}, densidade {density:.2f}."

    def _load_label(self, score: float) -> str:
        if score >= 0.72:
            return "high"
        if score >= 0.42:
            return "medium"
        return "low"

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(float(value), maximum))
