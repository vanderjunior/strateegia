from __future__ import annotations

from uuid import uuid4

from app.domain.models import LearningPlan, LearningPlanEntry, StudySession
from app.services.content_execution import execute_study_block
from app.services.microtopic_session_composer import MicrotopicSessionComposer
from app.services.session_equilibrium import SessionEquilibriumLayer


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, StudySession] = {}
        self._runtime_blocks: dict[str, list[dict]] = {}

    def create_session(self, plan: LearningPlan) -> StudySession:
        session_id = str(uuid4())
        runtime_blocks = self._build_runtime_blocks(plan.entries)
        session = StudySession(
            session_id=session_id,
            entries=plan.entries,
            completed=not runtime_blocks,
        )
        if runtime_blocks:
            self._sync_position(session, runtime_blocks[0])
        self._sessions[session_id] = session
        self._runtime_blocks[session_id] = runtime_blocks
        return session

    def get_session(self, session_id: str) -> StudySession | None:
        return self._sessions.get(session_id)

    def current_block(self, session_id: str) -> dict | None:
        session = self.get_session(session_id)
        if session is None or session.completed:
            return None
        runtime_blocks = self._runtime_blocks.get(session_id, [])
        if not runtime_blocks:
            return None
        index = self._current_runtime_index(session_id)
        if index >= len(runtime_blocks):
            return None
        block = dict(runtime_blocks[index])
        block.pop("_entry_index", None)
        block.pop("_block_index", None)
        block.pop("_question_index", None)
        return block

    def advance(self, session_id: str) -> StudySession | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        if session.completed:
            return session

        runtime_blocks = self._runtime_blocks.get(session_id, [])
        next_index = self._current_runtime_index(session_id) + 1
        if next_index >= len(runtime_blocks):
            session.completed = True
            return session

        self._sync_position(session, runtime_blocks[next_index])
        return session

    def _current_runtime_index(self, session_id: str) -> int:
        session = self._sessions[session_id]
        runtime_blocks = self._runtime_blocks.get(session_id, [])
        for index, block in enumerate(runtime_blocks):
            if (
                block["_entry_index"] == session.current_entry_index
                and block["_block_index"] == session.current_block_index
                and block["_question_index"] == session.current_question_index
            ):
                return index
        return len(runtime_blocks)

    def _sync_position(self, session: StudySession, runtime_block: dict) -> None:
        session.current_entry_index = runtime_block["_entry_index"]
        session.current_block_index = runtime_block["_block_index"]
        session.current_question_index = runtime_block["_question_index"]
        session.completed = False

    def _build_runtime_blocks(self, entries: list[LearningPlanEntry]) -> list[dict]:
        composer = MicrotopicSessionComposer()
        equilibrium = SessionEquilibriumLayer()
        candidates = composer.compose(entries)
        entry_index_by_topic = {entry.topic_id: index for index, entry in enumerate(entries)}
        summary_emitted: set[str] = set()
        question_count_by_topic: dict[str, int] = {}
        runtime_blocks: list[dict] = []

        for candidate in candidates:
            entry_index = entry_index_by_topic[candidate.topic_id]
            entry = entries[entry_index]
            if candidate.topic_id not in summary_emitted:
                summary_block = self._summary_block_for_topic(entry, candidate, entry_index=entry_index)
                if summary_block is not None:
                    runtime_blocks.append(summary_block)
                summary_emitted.add(candidate.topic_id)

            runtime_blocks.append(
                self._question_block_for_candidate(
                    entry,
                    candidate,
                    entry_index=entry_index,
                    question_index=question_count_by_topic.get(candidate.topic_id, 0),
                )
            )
            question_count_by_topic[candidate.topic_id] = question_count_by_topic.get(candidate.topic_id, 0) + 1

        return equilibrium.balance(runtime_blocks)

    def _summary_block_for_topic(
        self,
        entry: LearningPlanEntry,
        candidate,
        *,
        entry_index: int,
    ) -> dict | None:
        summary_index = next(
            (index for index, block in enumerate(entry.study_blocks) if block.type == "summary"),
            None,
        )
        if summary_index is None:
            return None
        block = entry.study_blocks[summary_index].model_copy(
            update={"selected_microtopic_ids": [candidate.microtopic_id]}
        )
        executed = execute_study_block(block)
        return {
            **executed,
            "topic_title": entry.topic_title,
            "curriculum_role": entry.curriculum_role,
            "review_intensity": entry.review_intensity,
            "_entry_index": entry_index,
            "_block_index": summary_index,
            "_question_index": 0,
        }

    def _question_block_for_candidate(
        self,
        entry: LearningPlanEntry,
        candidate,
        *,
        entry_index: int,
        question_index: int,
    ) -> dict:
        question_block_index = next(
            (index for index, block in enumerate(entry.study_blocks) if block.type == "questions"),
            0,
        )
        question_block = entry.study_blocks[question_block_index].model_copy(
            update={"quantity": 1, "selected_microtopic_ids": [candidate.microtopic_id]}
        )
        executed = execute_study_block(question_block)
        question = executed["questions"][0]
        return {
            "type": "question",
            "topic_id": entry.topic_id,
            "topic_title": entry.topic_title,
            "curriculum_role": entry.curriculum_role,
            "review_intensity": entry.review_intensity,
            "question_id": self._runtime_question_id(
                entry,
                block_index=question_block_index,
                question_index=question_index,
            ),
            "microtopic_id": question.get("microtopic_id"),
            "statement": question["statement"],
            "correct_answer": question["answer"],
            "explanation": question["explanation"],
            "pedagogical_mode": executed.get("pedagogical_mode"),
            "intervention_reason": executed.get("intervention_reason"),
            "explanation_depth": executed.get("explanation_depth"),
            "retrieval_intensity": executed.get("retrieval_intensity"),
            "pedagogical_reasoning": executed.get("pedagogical_reasoning"),
            "pedagogical_breakdown": executed.get("pedagogical_breakdown"),
            "adaptation_reasoning": executed.get("adaptation_reasoning"),
            "intervention_transition_reason": executed.get("intervention_transition_reason"),
            "pedagogical_confidence": executed.get("pedagogical_confidence"),
            "intervention_effectiveness": executed.get("intervention_effectiveness"),
            "pedagogical_stability": executed.get("pedagogical_stability"),
            "stabilization_stage": executed.get("stabilization_stage"),
            "longitudinal_retention": executed.get("longitudinal_retention"),
            "intervention_fatigue": executed.get("intervention_fatigue"),
            "reinforcement_reason": executed.get("reinforcement_reason"),
            "fatigue_reason": executed.get("fatigue_reason"),
            "stabilization_reasoning": executed.get("stabilization_reasoning"),
            "retention_reasoning": executed.get("retention_reasoning"),
            "recovery_signal": executed.get("recovery_signal"),
            "intervention_history_summary": executed.get("intervention_history_summary"),
            "why_this_now": executed.get("why_this_now"),
            "_entry_index": entry_index,
            "_block_index": question_block_index,
            "_question_index": question_index,
        }

    def _runtime_question_id(
        self,
        entry: LearningPlanEntry,
        *,
        block_index: int,
        question_index: int,
    ) -> str:
        if not entry.question_ids:
            return f"{entry.topic_id}:{block_index}:{question_index}"
        base = entry.question_ids[min(question_index, len(entry.question_ids) - 1)]
        if question_index < len(entry.question_ids):
            return base
        return f"{base}:{block_index}:{question_index}"
