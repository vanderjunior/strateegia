import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_READY_KEYS = {
    "review_status",
    "review_id",
    "basis",
    "materials_count",
    "blocks_count",
    "estimated_minutes",
    "title",
    "summary",
    "questions",
    "reinforcement",
    "actions",
    "source",
}

ALLOWED_NOT_READY_KEYS = ALLOWED_READY_KEYS | {"message"}

ALLOWED_SUMMARY_KEYS = {"status", "items"}
ALLOWED_SUMMARY_ITEM_KEYS = {"title", "message", "topic_label", "subtopic_label"}
ALLOWED_QUESTIONS_KEYS = {"status", "items_count"}
ALLOWED_REINFORCEMENT_KEYS = {"status", "weak_topics_count", "items"}
ALLOWED_REINFORCEMENT_ITEM_KEYS = {"topic_label", "subtopic_label", "message"}
ALLOWED_ACTION_KEYS = {"label", "href"}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-REVIEW-BLOCK-SHOULD-NOT-LEAK",
    "OTHER-REVIEW-BLOCK-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "raw_ocr",
    "ocr_dump",
    "base64",
    "storage_path",
    "/Users/",
    "C:\\",
    "token",
    "cookie",
    "studyflow_session",
    "session token",
    "password_hash",
    "answer_key",
    "gabarito",
    "correct_answer",
    "correct_alternative",
    "score",
    "pontuação",
    "correction",
    "progress payload",
    "attempt payload",
    "worker",
    "job trace",
    "internal trace",
)

FORBIDDEN_WORDING = (
    "completed",
    "progresso atualizado",
    "concluído",
    "concluídos",
    "você concluiu",
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


def upload_and_prepare_study_material(client: TestClient, index: int) -> str:
    uploaded = upload_material(
        client,
        filename=f"aula-{index}.md",
        content=(
            f"# Tema {index}\n\n"
            "RAW-REVIEW-BLOCK-SHOULD-NOT-LEAK\n\n"
            "Conteudo seguro para estudo."
        ).encode("utf-8"),
    )
    return prepare_study_material(client, uploaded)


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped
    for term in FORBIDDEN_WORDING:
        assert term not in dumped.lower()


def assert_bounded_review_payload(payload: dict[str, object]) -> None:
    allowed_keys = ALLOWED_NOT_READY_KEYS if payload["review_status"] == "not_ready" else ALLOWED_READY_KEYS
    assert set(payload.keys()) == allowed_keys
    assert payload["review_status"] in {"ready", "partial", "not_ready", "needs_review"}
    assert payload["review_id"] is None or isinstance(payload["review_id"], str)
    assert payload["basis"] in {"prepared_materials", "study_blocks", "studied_materials"}
    assert isinstance(payload["materials_count"], int)
    assert isinstance(payload["blocks_count"], int)
    assert isinstance(payload["estimated_minutes"], int)
    assert payload["title"] == "Revisão acumulada"
    assert set(payload["summary"].keys()) == ALLOWED_SUMMARY_KEYS
    assert payload["summary"]["status"] in {"ready", "needs_review", "not_ready"}
    assert isinstance(payload["summary"]["items"], list)
    for item in payload["summary"]["items"]:
        assert set(item.keys()) == ALLOWED_SUMMARY_ITEM_KEYS
        assert isinstance(item["title"], str)
        assert isinstance(item["message"], str)
        assert item["topic_label"] is None or isinstance(item["topic_label"], str)
        assert item["subtopic_label"] is None or isinstance(item["subtopic_label"], str)
    assert set(payload["questions"].keys()) == ALLOWED_QUESTIONS_KEYS
    assert payload["questions"]["status"] in {"ready", "needs_review", "not_ready"}
    assert isinstance(payload["questions"]["items_count"], int)
    assert set(payload["reinforcement"].keys()) == ALLOWED_REINFORCEMENT_KEYS
    assert payload["reinforcement"]["status"] in {"ready", "needs_review", "not_ready"}
    assert isinstance(payload["reinforcement"]["weak_topics_count"], int)
    assert isinstance(payload["reinforcement"]["items"], list)
    for item in payload["reinforcement"]["items"]:
        assert set(item.keys()) == ALLOWED_REINFORCEMENT_ITEM_KEYS
        assert item["topic_label"] is None or isinstance(item["topic_label"], str)
        assert item["subtopic_label"] is None or isinstance(item["subtopic_label"], str)
        assert isinstance(item["message"], str)
    assert isinstance(payload["actions"], list)
    for action in payload["actions"]:
        assert set(action.keys()) == ALLOWED_ACTION_KEYS
        assert action["label"] == "Abrir revisão"
        assert isinstance(action["href"], str)
        assert action["href"].startswith("/study/review/")
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_next_review_requires_auth(tmp_path):
    _, _, anonymous, _, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/review/next")

    assert response.status_code == 401


def test_next_review_not_ready_without_prepared_study_materials(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_material(
        owner,
        filename="aula-nao-preparada.md",
        content=b"# Aula\n\nRAW-REVIEW-BLOCK-SHOULD-NOT-LEAK",
    )

    response = owner.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "not_ready"
    assert payload["review_id"] is None
    assert payload["materials_count"] == 0
    assert payload["blocks_count"] == 0
    assert payload["actions"] == []
    assert payload["message"] == "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada."
    assert_bounded_review_payload(payload)


def test_next_review_partial_until_three_prepared_materials(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_and_prepare_study_material(owner, 1)
    upload_and_prepare_study_material(owner, 2)

    response = owner.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "not_ready"
    assert payload["materials_count"] == 2
    assert payload["blocks_count"] >= 2
    assert payload["actions"] == []
    assert_bounded_review_payload(payload)


def test_next_review_ready_for_three_prepared_study_materials(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    for index in range(1, 4):
        upload_and_prepare_study_material(owner, index)

    response = owner.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] in {"ready", "needs_review"}
    assert payload["basis"] == "prepared_materials"
    assert payload["materials_count"] == 3
    assert payload["blocks_count"] >= 3
    assert payload["estimated_minutes"] > 0
    assert payload["review_id"].startswith("review:prepared_materials:")
    assert payload["summary"]["items"]
    assert payload["questions"]["items_count"] >= 1
    assert payload["reinforcement"]["weak_topics_count"] == 0
    assert payload["actions"] == [
        {
            "label": "Abrir revisão",
            "href": f"/study/review/{payload['review_id']}",
        }
    ]
    assert_bounded_review_payload(payload)


def test_next_review_ignores_non_study_materials_as_primary_review_materials(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_and_prepare_study_material(owner, 1)
    upload_and_prepare_study_material(owner, 2)
    for material_type in ("edital", "bibliography", "previous_exam", "note", "other", "unknown"):
        upload_material(
            owner,
            filename=f"{material_type}.md",
            content=b"# Arquivo de apoio\n\nOTHER-REVIEW-BLOCK-SHOULD-NOT-LEAK",
            material_type=material_type,
        )

    response = owner.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "not_ready"
    assert payload["materials_count"] == 2
    assert payload["actions"] == []
    assert_bounded_review_payload(payload)


def test_next_review_is_user_scoped(tmp_path):
    owner, other, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    for index in range(1, 4):
        upload_and_prepare_study_material(owner, index)

    response = other.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review_status"] == "not_ready"
    assert payload["materials_count"] == 0
    assert payload["blocks_count"] == 0
    assert_bounded_review_payload(payload)


def test_next_review_is_idempotent_and_read_only(tmp_path):
    owner, _, _, repository, data_path = create_clients(tmp_path)
    user = register_and_login(owner, "stable-owner")
    document_ids = [upload_and_prepare_study_material(owner, index) for index in range(1, 4)]
    before_progress = repository.load_progress(user_id=user["user_id"]).model_dump(mode="json")
    before_sections = {
        document_id: len(repository.list_document_sections(document_id, user_id=user["user_id"]))
        for document_id in document_ids
    }
    before_chunks = {
        document_id: len(repository.list_document_chunks(document_id, user_id=user["user_id"]))
        for document_id in document_ids
    }
    before_file = data_path.read_text(encoding="utf-8")

    first = owner.get("/api/study/review/next")
    second = owner.get("/api/study/review/next")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert repository.load_progress(user_id=user["user_id"]).model_dump(mode="json") == before_progress
    assert data_path.read_text(encoding="utf-8") == before_file
    assert {
        document_id: len(repository.list_document_sections(document_id, user_id=user["user_id"]))
        for document_id in document_ids
    } == before_sections
    assert {
        document_id: len(repository.list_document_chunks(document_id, user_id=user["user_id"]))
        for document_id in document_ids
    } == before_chunks
    assert_bounded_review_payload(first.json())


def test_next_review_does_not_leak_raw_content_or_forbidden_wording(tmp_path):
    owner, _, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "safe-owner")
    for index in range(1, 4):
        upload_and_prepare_study_material(owner, index)

    response = owner.get("/api/study/review/next")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_review_payload(payload)
