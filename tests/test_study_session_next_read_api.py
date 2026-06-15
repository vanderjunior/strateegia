import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_READY_KEYS = {
    "session_status",
    "session_id",
    "document_id",
    "material_title",
    "material_type",
    "summary_status",
    "estimated_minutes",
    "sections_count",
    "items",
    "next_actions",
    "message",
    "source",
}

ALLOWED_NOT_READY_KEYS = {
    "session_status",
    "message",
    "next_actions",
    "source",
}

ALLOWED_ITEM_KEYS = {
    "section_id",
    "title",
    "summary",
    "key_points",
    "estimated_minutes",
    "status",
    "source_material_id",
    "source_section_id",
    "source_anchors",
    "content_fingerprint",
    "generator_version",
    "generation_method",
}

ALLOWED_ACTION_KEYS = {
    "label",
    "href",
}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-STUDY-SESSION-SHOULD-NOT-LEAK",
    "OTHER-STUDY-SESSION-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "raw_ocr",
    "ocr_dump",
    "base64",
    "storage_path",
    "/Users/",
    "C:\\",
    "password_hash",
    "studyflow_session",
    "session token",
    "answer_key",
    "gabarito",
    "correctness",
    "is_correct",
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


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


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_action(action: dict[str, object]) -> None:
    assert set(action.keys()) == ALLOWED_ACTION_KEYS
    assert isinstance(action["label"], str)
    assert isinstance(action["href"], str)
    assert action["href"].startswith("/")


def assert_bounded_not_ready_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_NOT_READY_KEYS
    assert payload["session_status"] == "not_ready"
    assert isinstance(payload["message"], str)
    assert isinstance(payload["next_actions"], list)
    assert payload["source"] == "user_scope"
    for action in payload["next_actions"]:
        assert_bounded_action(action)
    assert_no_forbidden_terms(payload)


def assert_bounded_ready_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_READY_KEYS
    assert payload["session_status"] in {"ready", "needs_review"}
    assert str(payload["session_id"]).startswith("study-session:")
    assert isinstance(payload["document_id"], str)
    assert payload["material_type"] == "study_material"
    assert payload["summary_status"] in {"ready", "needs_review"}
    assert isinstance(payload["material_title"], str)
    assert isinstance(payload["estimated_minutes"], int)
    assert isinstance(payload["sections_count"], int)
    assert isinstance(payload["items"], list)
    assert isinstance(payload["next_actions"], list)
    assert isinstance(payload["message"], str)
    assert payload["source"] == "user_scope"
    for item in payload["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert isinstance(item["section_id"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["summary"], str)
        assert isinstance(item["key_points"], list)
        assert isinstance(item["estimated_minutes"], int)
        assert item["status"] in {"ready", "needs_review"}
        assert item["source_material_id"] == payload["document_id"]
        assert item["source_section_id"] == item["section_id"]
        assert isinstance(item["source_anchors"], list)
        assert isinstance(item["content_fingerprint"], str)
        assert item["generator_version"] == "grounded-summary-v1"
        assert item["generation_method"] == "deterministic_extractive"
    for action in payload["next_actions"]:
        assert_bounded_action(action)
    assert_no_forbidden_terms(payload)


def test_next_study_session_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/session/next")

    assert response.status_code == 401


def test_next_study_session_returns_not_ready_without_prepared_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/study/session/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["message"] == "Envie e prepare um material de estudo para começar."
    assert_bounded_not_ready_payload(payload)


def test_next_study_session_ignores_non_study_materials(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_material(
        owner,
        filename="edital.md",
        content=b"# Edital\n\nOTHER-STUDY-SESSION-SHOULD-NOT-LEAK",
        material_type="edital",
    )

    response = owner.get("/api/study/session/next")

    assert response.status_code == 200
    assert_bounded_not_ready_payload(response.json())


def test_next_study_session_returns_prepared_material_summary(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-SESSION-SHOULD-NOT-LEAK\n\n"
            b"## Poder de policia\n\n"
            b"Conteudo seguro para estudo."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    prepared = owner.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200

    response = owner.get("/api/study/session/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["session_status"] == "ready"
    assert payload["session_id"] == f"study-session:{document_id}"
    assert payload["document_id"] == document_id
    assert payload["material_title"] == "aula.md"
    assert payload["summary_status"] == "ready"
    assert payload["sections_count"] == 2
    assert payload["estimated_minutes"] >= 6
    assert [item["title"] for item in payload["items"]] == [
        "Atos administrativos",
        "Poder de policia",
    ]
    assert payload["next_actions"][0] == {
        "label": "Abrir material",
        "href": f"/materials/{document_id}",
    }
    assert payload["message"] == "Este estudo ainda não está conectado completamente ao edital."
    assert_bounded_ready_payload(payload)


def test_next_study_session_prefers_ready_then_oldest_prepared_candidate(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    needs_review = upload_material(
        owner,
        filename="aula-sem-estrutura.txt",
        content=b"Conteudo sem cabecalho markdown.",
        content_type="text/plain",
    )
    ready = upload_material(
        owner,
        filename="aula-pronta.md",
        content=b"# Aula pronta\n\nConteudo seguro.",
    )
    needs_review_id = needs_review["metadata"]["document_id"]
    ready_id = ready["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{needs_review_id}/study/prepare").status_code == 200
    assert owner.post(f"/api/materials/{ready_id}/study/prepare").status_code == 200

    response = owner.get("/api/study/session/next")
    payload = response.json()

    assert response.status_code == 200
    assert payload["document_id"] == ready_id
    assert payload["session_status"] == "ready"
    assert_bounded_ready_payload(payload)


def test_next_study_session_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula\n\nOTHER-STUDY-SESSION-SHOULD-NOT-LEAK",
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    response = other.get("/api/study/session/next")

    assert response.status_code == 200
    assert_bounded_not_ready_payload(response.json())


def test_next_study_session_is_idempotent_and_does_not_mutate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula estavel\n\nConteudo seguro.",
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200
    section_count = len(repository.list_document_sections(document_id, user_id=user["user_id"]))
    chunk_count = len(repository.list_document_chunks(document_id, user_id=user["user_id"]))

    first = owner.get("/api/study/session/next")
    second = owner.get("/api/study/session/next")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_document_sections(document_id, user_id=user["user_id"])) == section_count
    assert len(repository.list_document_chunks(document_id, user_id=user["user_id"])) == chunk_count
    assert_bounded_ready_payload(first.json())
