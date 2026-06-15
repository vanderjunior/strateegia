import json
from io import BytesIO
from urllib.parse import quote

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


ALLOWED_DETAIL_KEYS = {
    "block_id",
    "detail_status",
    "title",
    "topic_id",
    "topic_label",
    "subtopic_id",
    "subtopic_label",
    "material_id",
    "material_title",
    "summary_status",
    "estimated_minutes",
    "sections",
    "actions",
    "source",
}

ALLOWED_SECTION_KEYS = {
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
    "RAW-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK",
    "OTHER-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "raw text",
    "raw_ocr",
    "ocr_dump",
    "base64",
    "storage_path",
    "/Users/",
    "C:\\",
    "password_hash",
    "studyflow_session",
    "session token",
    "cookie",
    "answer_key",
    "gabarito",
    "correctness",
    "is_correct",
    "progress",
    "correction",
    "worker",
    "job trace",
    "internal trace",
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


def encoded_block_path(block_id: str) -> str:
    return f"/api/study/blocks/{quote(block_id, safe='')}"


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_action(action: dict[str, object]) -> None:
    assert set(action.keys()) == ALLOWED_ACTION_KEYS
    assert isinstance(action["label"], str)
    assert isinstance(action["href"], str)
    assert action["href"].startswith("/")


def assert_bounded_detail_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_DETAIL_KEYS
    assert isinstance(payload["block_id"], str)
    assert payload["detail_status"] in {"ready", "needs_review", "not_ready"}
    assert isinstance(payload["title"], str)
    assert payload["topic_id"] is None or isinstance(payload["topic_id"], str)
    assert payload["topic_label"] is None or isinstance(payload["topic_label"], str)
    assert payload["subtopic_id"] is None or isinstance(payload["subtopic_id"], str)
    assert payload["subtopic_label"] is None or isinstance(payload["subtopic_label"], str)
    assert isinstance(payload["material_id"], str)
    assert isinstance(payload["material_title"], str)
    assert payload["summary_status"] in {"ready", "needs_review", "not_ready"}
    assert isinstance(payload["estimated_minutes"], int)
    assert isinstance(payload["sections"], list)
    assert isinstance(payload["actions"], list)
    assert payload["source"] == "user_scope"
    for section in payload["sections"]:
        assert set(section.keys()) == ALLOWED_SECTION_KEYS
        assert isinstance(section["section_id"], str)
        assert isinstance(section["title"], str)
        assert isinstance(section["summary"], str)
        assert isinstance(section["key_points"], list)
        assert all(isinstance(point, str) for point in section["key_points"])
        assert isinstance(section["estimated_minutes"], int)
        assert section["status"] in {"ready", "needs_review"}
        assert section["source_material_id"] == payload["material_id"]
        assert section["source_section_id"] == section["section_id"]
        assert isinstance(section["source_anchors"], list)
        assert isinstance(section["content_fingerprint"], str)
        assert section["generator_version"] == "grounded-summary-v1"
        assert section["generation_method"] == "deterministic_extractive"
    for action in payload["actions"]:
        assert_bounded_action(action)
    assert_no_forbidden_terms(payload)


def first_block(client: TestClient) -> dict[str, object]:
    response = client.get("/api/study/blocks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    return payload["items"][0]


def test_study_block_detail_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/blocks/study-block%3Amissing%3Adoc%3A0")

    assert response.status_code == 401


def test_study_block_detail_returns_404_for_missing_block(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/study/blocks/study-block%3Amissing%3Adoc%3A0")

    assert response.status_code == 404


def test_study_block_detail_returns_material_only_block(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK\n\n"
            b"## Poderes administrativos\n\n"
            b"Conteudo seguro."
        ),
    )
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_block_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["block_id"] == block["block_id"]
    assert payload["detail_status"] in {"ready", "needs_review"}
    assert payload["topic_id"] is None
    assert payload["material_id"] == document_id
    assert payload["material_title"] == block["material_title"]
    assert len(payload["sections"]) == 1
    assert payload["sections"][0]["title"] == block["title"]
    assert payload["actions"] == [
        {"label": "Abrir material", "href": f"/materials/{document_id}"},
        {"label": "Voltar ao caminho de estudo", "href": "/study"},
    ]
    assert_bounded_detail_payload(payload)


def test_study_block_detail_returns_connected_edital_labels(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    analyze_structured_edital(owner)
    uploaded = upload_material(
        owner,
        filename="atos-administrativos.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK\n\n"
            b"Atos administrativos produzem efeitos juridicos imediatos e devem observar finalidade publica."
        ),
    )
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_block_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["detail_status"] == "ready"
    assert payload["material_id"] == document_id
    assert payload["topic_label"] == "Direito Administrativo"
    assert payload["subtopic_label"] == "Atos administrativos"
    assert payload["title"] == "Atos administrativos"
    assert len(payload["sections"]) == 1
    assert_bounded_detail_payload(payload)


def test_study_block_detail_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula privada\n\nOTHER-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK",
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = other.get(encoded_block_path(str(block["block_id"])))

    assert response.status_code == 404


def test_study_block_detail_is_idempotent_and_read_only(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "stable-owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula estavel\n\nConteudo seguro.",
    )
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)
    section_count = len(repository.list_document_sections(document_id, user_id=user["user_id"]))
    chunk_count = len(repository.list_document_chunks(document_id, user_id=user["user_id"]))

    first = owner.get(encoded_block_path(str(block["block_id"])))
    second = owner.get(encoded_block_path(str(block["block_id"])))

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_document_sections(document_id, user_id=user["user_id"])) == section_count
    assert len(repository.list_document_chunks(document_id, user_id=user["user_id"])) == chunk_count
    assert_bounded_detail_payload(first.json())


def test_every_study_block_action_resolves_to_detail_when_encoded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    analyze_structured_edital(owner)
    uploaded = upload_material(
        owner,
        filename="atos-administrativos.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-BLOCK-DETAIL-SHOULD-NOT-LEAK\n\n"
            b"## Poderes administrativos\n\n"
            b"Conteudo seguro."
        ),
    )
    prepare_study_material(owner, uploaded)
    blocks = owner.get("/api/study/blocks").json()["items"]
    assert blocks

    for block in blocks:
        action_hrefs = [
            action["href"]
            for action in block["actions"]
            if action["href"].startswith("/study/blocks/")
        ]
        assert action_hrefs
        for href in action_hrefs:
            block_id = href.removeprefix("/study/blocks/")
            response = owner.get(encoded_block_path(block_id))
            assert response.status_code == 200
            assert response.json()["block_id"] == block["block_id"]
            assert_bounded_detail_payload(response.json())
