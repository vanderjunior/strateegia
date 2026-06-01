import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


STRUCTURED_EDITAL = b"""# EDITAL DE QA

## 1. CONTEUDO PROGRAMATICO

Lingua Portuguesa:
1.1 Compreensao e interpretacao de textos.
1.2 Ortografia oficial.

Direito Administrativo:
2.1 Atos administrativos.
2.2 Poderes administrativos.

## 2. BIBLIOGRAFIA

MANUAL DE QA. Referencia simulada para teste interno. 2026.
"""


ALLOWED_RESPONSE_KEYS = {
    "blocks_status",
    "scope_status",
    "blocks_count",
    "estimated_minutes",
    "items",
    "source",
}

ALLOWED_NOT_READY_KEYS = {
    "blocks_status",
    "scope_status",
    "blocks_count",
    "estimated_minutes",
    "items",
    "message",
    "source",
}

ALLOWED_ITEM_KEYS = {
    "block_id",
    "title",
    "topic_id",
    "topic_label",
    "subtopic_id",
    "subtopic_label",
    "material_id",
    "material_title",
    "sections_count",
    "summary_status",
    "estimated_minutes",
    "status",
    "actions",
}

ALLOWED_ACTION_KEYS = {
    "label",
    "href",
}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-STUDY-BLOCK-SHOULD-NOT-LEAK",
    "OTHER-STUDY-BLOCK-SHOULD-NOT-LEAK",
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
    "evidence",
    "raw_reference",
    "progress",
    "correction",
    "worker",
    "job trace",
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


def prepare_study_material(client: TestClient, uploaded: dict[str, object]) -> str:
    document_id = uploaded["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return str(document_id)


def analyze_structured_edital(client: TestClient) -> dict[str, object]:
    uploaded = upload_material(
        client,
        filename="edital-qa.md",
        content=STRUCTURED_EDITAL,
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]
    analyzed = client.post(f"/api/materials/{document_id}/edital/analyze")
    assert analyzed.status_code == 200
    payload = analyzed.json()
    assert payload["analysis_status"] == "analyzed"
    return payload


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_action(action: dict[str, object]) -> None:
    assert set(action.keys()) == ALLOWED_ACTION_KEYS
    assert action["label"] == "Estudar bloco"
    assert isinstance(action["href"], str)
    assert action["href"].startswith("/study/blocks/")


def assert_bounded_study_blocks_payload(payload: dict[str, object]) -> None:
    allowed_keys = ALLOWED_NOT_READY_KEYS if payload["blocks_status"] == "not_ready" else ALLOWED_RESPONSE_KEYS
    assert set(payload.keys()) == allowed_keys
    assert payload["blocks_status"] in {"ready", "partial", "not_ready", "needs_review"}
    assert payload["scope_status"] in {"connected_to_edital", "material_only", "not_ready"}
    assert isinstance(payload["blocks_count"], int)
    assert isinstance(payload["estimated_minutes"], int)
    assert isinstance(payload["items"], list)
    assert payload["source"] == "user_scope"
    for item in payload["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert isinstance(item["block_id"], str)
        assert isinstance(item["title"], str)
        assert item["topic_id"] is None or isinstance(item["topic_id"], str)
        assert item["topic_label"] is None or isinstance(item["topic_label"], str)
        assert item["subtopic_id"] is None or isinstance(item["subtopic_id"], str)
        assert item["subtopic_label"] is None or isinstance(item["subtopic_label"], str)
        assert isinstance(item["material_id"], str)
        assert isinstance(item["material_title"], str)
        assert isinstance(item["sections_count"], int)
        assert item["summary_status"] in {"ready", "needs_review", "not_ready", "failed"}
        assert isinstance(item["estimated_minutes"], int)
        assert item["status"] in {"ready", "needs_review", "not_ready"}
        assert isinstance(item["actions"], list)
        for action in item["actions"]:
            assert_bounded_action(action)
    assert_no_forbidden_terms(payload)


def test_study_blocks_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/blocks")

    assert response.status_code == 401


def test_study_blocks_returns_not_ready_without_prepared_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_material(
        owner,
        filename="aula-nao-preparada.md",
        content=b"# Aula\n\nRAW-STUDY-BLOCK-SHOULD-NOT-LEAK",
    )

    response = owner.get("/api/study/blocks")
    payload = response.json()

    assert response.status_code == 200
    assert payload["blocks_status"] == "not_ready"
    assert payload["scope_status"] == "not_ready"
    assert payload["blocks_count"] == 0
    assert payload["items"] == []
    assert payload["message"] == "Envie e prepare um material de estudo para montar seus blocos."
    assert_bounded_study_blocks_payload(payload)


def test_study_blocks_returns_material_only_blocks_without_analyzed_edital(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-BLOCK-SHOULD-NOT-LEAK\n\n"
            b"## Poderes administrativos\n\n"
            b"Conteudo seguro."
        ),
    )
    document_id = prepare_study_material(owner, uploaded)

    response = owner.get("/api/study/blocks")
    payload = response.json()

    assert response.status_code == 200
    assert payload["blocks_status"] == "partial"
    assert payload["scope_status"] == "material_only"
    assert payload["blocks_count"] == 2
    assert payload["estimated_minutes"] >= 6
    assert [item["title"] for item in payload["items"]] == [
        "Atos administrativos",
        "Poderes administrativos",
    ]
    assert {item["material_id"] for item in payload["items"]} == {document_id}
    assert all(item["topic_id"] is None for item in payload["items"])
    assert all(item["status"] == "ready" for item in payload["items"])
    assert_bounded_study_blocks_payload(payload)


def test_study_blocks_connects_prepared_material_to_analyzed_edital(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    analyze_structured_edital(owner)
    uploaded = upload_material(
        owner,
        filename="atos-administrativos.md",
        content=b"# Atos administrativos\n\nRAW-STUDY-BLOCK-SHOULD-NOT-LEAK",
    )
    document_id = prepare_study_material(owner, uploaded)

    response = owner.get("/api/study/blocks")
    payload = response.json()

    assert response.status_code == 200
    assert payload["blocks_status"] == "ready"
    assert payload["scope_status"] == "connected_to_edital"
    assert payload["blocks_count"] == 1
    item = payload["items"][0]
    assert item["material_id"] == document_id
    assert item["topic_label"] == "Direito Administrativo"
    assert item["subtopic_label"] == "Atos administrativos"
    assert item["status"] == "ready"
    assert_bounded_study_blocks_payload(payload)


def test_study_blocks_ignores_non_study_materials_as_primary_blocks(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    upload_material(
        owner,
        filename="bibliografia.md",
        content=b"# Referencia\n\nOTHER-STUDY-BLOCK-SHOULD-NOT-LEAK",
        material_type="bibliography",
    )

    response = owner.get("/api/study/blocks")

    assert response.status_code == 200
    assert_bounded_study_blocks_payload(response.json())
    assert response.json()["blocks_status"] == "not_ready"


def test_study_blocks_are_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula privada\n\nOTHER-STUDY-BLOCK-SHOULD-NOT-LEAK",
    )
    prepare_study_material(owner, uploaded)

    response = other.get("/api/study/blocks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["blocks_status"] == "not_ready"
    assert_bounded_study_blocks_payload(payload)


def test_study_blocks_have_deterministic_ordering(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    older_needs_review = upload_material(
        owner,
        filename="aula-sem-estrutura.txt",
        content=b"Conteudo seguro sem cabecalho markdown.",
        content_type="text/plain",
    )
    newer_ready = upload_material(
        owner,
        filename="aula-pronta.md",
        content=b"# Aula pronta\n\nConteudo seguro.",
    )
    older_id = prepare_study_material(owner, older_needs_review)
    newer_id = prepare_study_material(owner, newer_ready)

    response = owner.get("/api/study/blocks")
    payload = response.json()

    assert response.status_code == 200
    assert [item["material_id"] for item in payload["items"]] == [newer_id, older_id]
    assert [item["status"] for item in payload["items"]] == ["ready", "needs_review"]
    assert_bounded_study_blocks_payload(payload)


def test_study_blocks_are_idempotent_and_do_not_mutate_progress(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "stable-owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula estavel\n\nConteudo seguro.",
    )
    document_id = prepare_study_material(owner, uploaded)
    section_count = len(repository.list_document_sections(document_id, user_id=user["user_id"]))
    chunk_count = len(repository.list_document_chunks(document_id, user_id=user["user_id"]))

    first = owner.get("/api/study/blocks")
    second = owner.get("/api/study/blocks")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_document_sections(document_id, user_id=user["user_id"])) == section_count
    assert len(repository.list_document_chunks(document_id, user_id=user["user_id"])) == chunk_count
    assert_bounded_study_blocks_payload(first.json())
