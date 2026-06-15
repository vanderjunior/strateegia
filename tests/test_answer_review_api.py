import json
from io import BytesIO
from urllib.parse import quote

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


STRUCTURED_EDITAL = b"""# EDITAL DE QA

## 1. CONTEUDO PROGRAMATICO

Direito Administrativo:
2.1 Atos administrativos.
2.2 Poderes administrativos.
"""

GROUNDED_QUESTION_SOURCE = (
    b"O poder de policia consiste em atividade administrativa que deve limitar direitos "
    b"para proteger a finalidade publica e produzir efeitos imediatos."
)


ALLOWED_RESPONSE_KEYS = {
    "block_id",
    "question_id",
    "review_status",
    "result",
    "feedback",
    "reinforcement",
    "source",
}

ALLOWED_REINFORCEMENT_KEYS = {
    "topic_label",
    "subtopic_label",
    "message",
    "suggested_action",
}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-ANSWER-REVIEW-SHOULD-NOT-LEAK",
    "OTHER-ANSWER-REVIEW-SHOULD-NOT-LEAK",
    "answer_key",
    "correct_answer",
    "correct_alternative",
    "gabarito",
    "is_correct",
    "solution",
    "score",
    "correction",
    "rationale",
    "raw text",
    "extracted_text",
    "chunk body",
    "section body",
    "storage_path",
    "/Users/",
    "C:\\",
    "token",
    "cookie",
    "studyflow_session",
    "password_hash",
    "progress payload",
    "internal trace",
)


def create_clients(tmp_path):
    data_path = tmp_path / "study_data.json"
    repository = JsonStudyRepository(data_path)
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository, data_path


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    return registered.json()


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str = "text/markdown",
    material_type: str = "study_material",
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def prepare_study_material(client: TestClient, uploaded: dict[str, object]) -> str:
    document_id = uploaded["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return str(document_id)


def analyze_structured_edital(client: TestClient) -> None:
    uploaded = upload_material(
        client,
        filename="edital-qa.md",
        content=STRUCTURED_EDITAL,
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]
    analyzed = client.post(f"/api/materials/{document_id}/edital/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["analysis_status"] == "analyzed"


def encoded_questions_path(block_id: str) -> str:
    return f"/api/study/blocks/{quote(block_id, safe='')}/questions"


def encoded_review_path(block_id: str, question_id: str) -> str:
    return (
        f"/api/study/blocks/{quote(block_id, safe='')}"
        f"/questions/{quote(question_id, safe='')}/answer/review"
    )


def first_block(client: TestClient) -> dict[str, object]:
    response = client.get("/api/study/blocks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    return payload["items"][0]


def first_question(client: TestClient, block_id: str) -> dict[str, object]:
    response = client.get(encoded_questions_path(block_id))
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    return payload["items"][0]


def prepare_ready_question(client: TestClient) -> tuple[str, dict[str, object]]:
    uploaded = upload_material(
        client,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-ANSWER-REVIEW-SHOULD-NOT-LEAK\n\n"
            + GROUNDED_QUESTION_SOURCE
        ),
    )
    prepare_study_material(client, uploaded)
    block = first_block(client)
    question = first_question(client, str(block["block_id"]))
    return str(block["block_id"]), question


def post_review(
    client: TestClient,
    block_id: str,
    question_id: str,
    *,
    answer: str = "Minha resposta sobre atos administrativos.",
    answer_format: str = "text",
):
    return client.post(
        encoded_review_path(block_id, question_id),
        json={"answer": answer, "answer_format": answer_format},
    )


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_answer_review_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_RESPONSE_KEYS
    assert isinstance(payload["block_id"], str)
    assert isinstance(payload["question_id"], str)
    assert payload["review_status"] in {"reviewed", "needs_review", "not_ready", "unsupported"}
    assert payload["result"] in {"correct", "incorrect", "partial", "ungraded", "needs_review"}
    assert isinstance(payload["feedback"], str)
    assert payload["feedback"]
    assert set(payload["reinforcement"].keys()) == ALLOWED_REINFORCEMENT_KEYS
    assert payload["reinforcement"]["topic_label"] is None or isinstance(payload["reinforcement"]["topic_label"], str)
    assert payload["reinforcement"]["subtopic_label"] is None or isinstance(
        payload["reinforcement"]["subtopic_label"], str
    )
    assert isinstance(payload["reinforcement"]["message"], str)
    assert payload["reinforcement"]["suggested_action"] in {
        "review_summary",
        "retry_question",
        "revisit_block",
    }
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_answer_review_requires_auth(tmp_path):
    _, _, anonymous, _, _ = create_clients(tmp_path)

    response = anonymous.post(
        "/api/study/blocks/study-block%3Amissing%3Adoc%3A0/questions/question%3Amissing/answer/review",
        json={"answer": "Resposta", "answer_format": "text"},
    )

    assert response.status_code == 401


def test_answer_review_returns_404_for_missing_block(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.post(
        "/api/study/blocks/study-block%3Amissing%3Adoc%3A0/questions/question%3Amissing/answer/review",
        json={"answer": "Resposta", "answer_format": "text"},
    )

    assert response.status_code == 404


def test_answer_review_returns_404_for_question_not_in_block(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    block_id, _ = prepare_ready_question(owner)

    response = post_review(owner, block_id, "question:fake")

    assert response.status_code == 404


def test_answer_review_rejects_invalid_body(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    block_id, question = prepare_ready_question(owner)
    path = encoded_review_path(block_id, str(question["question_id"]))

    cases = [
        {},
        {"answer_format": "text"},
        {"answer": "", "answer_format": "text"},
        {"answer": "   ", "answer_format": "text"},
        {"answer": "Resposta", "answer_format": "unsupported"},
        {"answer": "x" * 2001, "answer_format": "text"},
        {"answer": "Resposta", "answer_format": "text", "answer_key": "SHOULD-NOT-BE-ACCEPTED"},
    ]

    for body in cases:
        response = owner.post(path, json=body)
        assert response.status_code == 422


def test_answer_review_returns_404_when_profile_has_no_supported_objective_question(tmp_path, monkeypatch):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "short_answer")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=b"# Atos administrativos\n\n" + GROUNDED_QUESTION_SOURCE,
    )
    prepare_study_material(owner, uploaded)
    block_id = str(first_block(owner)["block_id"])

    response = post_review(owner, block_id, "question:unsupported")

    assert response.status_code == 404


def test_answer_review_grades_validated_choice_without_persisting_attempt(tmp_path):
    owner, _, _, repository, _ = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    block_id, question = prepare_ready_question(owner)

    assert question["type"] == "multiple_choice"
    response = post_review(
        owner,
        block_id,
        str(question["question_id"]),
        answer="A",
        answer_format="choice",
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "reviewed"
    assert payload["result"] in {"correct", "incorrect"}
    assert repository.list_study_question_attempts(user_id=user["user_id"]) == []
    assert_bounded_answer_review_payload(payload)


def test_answer_review_grades_validated_true_false(tmp_path, monkeypatch):
    owner, _, _, repository, _ = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "cebraspe_true_false")
    block_id, question = prepare_ready_question(owner)

    assert question["type"] == "true_false"
    response = post_review(
        owner,
        block_id,
        str(question["question_id"]),
        answer="C",
        answer_format="true_false",
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "reviewed"
    assert payload["result"] == "correct"
    assert repository.list_study_question_attempts(user_id=user["user_id"]) == []
    assert_bounded_answer_review_payload(payload)


def test_answer_review_reinforcement_includes_connected_edital_labels(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    analyze_structured_edital(owner)
    uploaded = upload_material(
        owner,
        filename="atos-administrativos.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-ANSWER-REVIEW-SHOULD-NOT-LEAK\n\n"
            b"Atos administrativos produzem efeitos juridicos imediatos e devem observar finalidade publica."
        ),
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    question = first_question(owner, str(block["block_id"]))

    response = post_review(owner, str(block["block_id"]), str(question["question_id"]), answer="A", answer_format="choice")
    payload = response.json()

    assert response.status_code == 200
    assert payload["reinforcement"]["topic_label"] == "Direito Administrativo"
    assert payload["reinforcement"]["subtopic_label"] == "Atos administrativos"
    assert "Atos administrativos" in payload["reinforcement"]["message"]
    assert_bounded_answer_review_payload(payload)


def test_answer_review_is_idempotent_and_read_only_for_same_choice(tmp_path):
    owner, _, _, repository, data_path = create_clients(tmp_path)
    user = register_and_login(owner, "stable-owner")
    block_id, question = prepare_ready_question(owner)
    before_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    before_file = data_path.read_text(encoding="utf-8")

    first = post_review(owner, block_id, str(question["question_id"]), answer="A", answer_format="choice")
    second = post_review(owner, block_id, str(question["question_id"]), answer="A", answer_format="choice")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    after_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    assert after_progress == before_progress
    assert data_path.read_text(encoding="utf-8") == before_file
    assert repository.list_study_question_attempts(user_id=user["user_id"]) == []


def test_answer_review_is_user_scoped(tmp_path):
    owner, other, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    block_id, question = prepare_ready_question(owner)

    response = post_review(other, block_id, str(question["question_id"]))

    assert response.status_code == 404


def test_answer_review_does_not_leak_answer_keys_or_raw_content(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    block_id, question = prepare_ready_question(owner)

    response = post_review(owner, block_id, str(question["question_id"]), answer="A", answer_format="choice")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_answer_review_payload(payload)
