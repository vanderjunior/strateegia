from __future__ import annotations

from pydantic import BaseModel


class AnswerSubmission(BaseModel):
    topic_id: str
    question_id: str
    microtopic_id: str | None = None
    pedagogical_mode: str | None = None
    user_answer: bool
    correct_answer: bool
    error_type: str | None = None


class SessionStartRequest(BaseModel):
    title: str = "Study Session"
    max_questions: int = 5


class SessionAnswerRequest(BaseModel):
    question_id: str | None = None
    user_answer: bool | None = None
    correct_answer: bool | None = None
    error_type: str | None = None
    pedagogical_mode: str | None = None
