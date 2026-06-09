from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StudyProgressEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    target_type: str
    target_id: str
    idempotency_key: str | None = None


class StudyBlockAnswerReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    answer_format: str


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


class UserRegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    email: str | None = None


class UserLoginRequest(BaseModel):
    username: str
    password: str
