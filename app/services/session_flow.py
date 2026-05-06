from __future__ import annotations

from uuid import uuid4

from app.domain.models import LearningPlan, LearningPlanEntry, StudySession
from app.services.content_execution import execute_study_block


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
        runtime_blocks: list[dict] = []
        for entry_index, entry in enumerate(entries):
            for block_index, block in enumerate(entry.study_blocks):
                executed = execute_study_block(block)
                if executed["type"] == "summary":
                    runtime_blocks.append(
                        {
                            **executed,
                            "_entry_index": entry_index,
                            "_block_index": block_index,
                            "_question_index": 0,
                        }
                    )
                    continue

                questions = executed.get("questions", [])
                for question_index, question in enumerate(questions):
                    runtime_blocks.append(
                        {
                            "type": "question",
                            "topic_id": entry.topic_id,
                            "question_id": self._runtime_question_id(
                                entry,
                                block_index=block_index,
                                question_index=question_index,
                            ),
                            "statement": question["statement"],
                            "correct_answer": question["answer"],
                            "explanation": question["explanation"],
                            "_entry_index": entry_index,
                            "_block_index": block_index,
                            "_question_index": question_index,
                        }
                    )
        return runtime_blocks

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
