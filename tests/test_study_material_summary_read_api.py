import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.domain.models import DocumentChunk
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_STUDY_SUMMARY_KEYS = {
    "document_id",
    "summary_status",
    "material_type",
    "title",
    "sections_count",
    "items",
    "warnings_count",
    "source",
}


ALLOWED_STUDY_SUMMARY_ITEM_KEYS = {
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

ALLOWED_SOURCE_ANCHOR_KEYS = {
    "chunk_id",
    "chunk_index",
    "sentence_index",
    "excerpt_fingerprint",
    "page_start",
    "page_end",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-STUDY-SUMMARY-SHOULD-NOT-LEAK",
    "OTHER-STUDY-SUMMARY-SHOULD-NOT-LEAK",
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


def assert_bounded_study_summary_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_STUDY_SUMMARY_KEYS
    assert payload["summary_status"] in {"ready", "needs_review", "not_ready", "failed"}
    assert payload["material_type"] == "study_material"
    assert isinstance(payload["title"], str)
    assert isinstance(payload["sections_count"], int)
    assert isinstance(payload["items"], list)
    assert isinstance(payload["warnings_count"], int)
    assert payload["source"] == "user_scope"
    for item in payload["items"]:
        assert set(item.keys()) == ALLOWED_STUDY_SUMMARY_ITEM_KEYS
        assert isinstance(item["section_id"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["summary"], str)
        assert len(item["summary"]) <= 960
        assert isinstance(item["key_points"], list)
        assert len(item["key_points"]) <= 7
        assert all(len(point) <= 320 for point in item["key_points"])
        assert isinstance(item["estimated_minutes"], int)
        assert item["status"] in {"ready", "needs_review"}
        assert item["source_material_id"] == payload["document_id"]
        assert item["source_section_id"] == item["section_id"]
        assert isinstance(item["source_anchors"], list)
        assert len(item["source_anchors"]) <= 5
        for anchor in item["source_anchors"]:
            assert set(anchor.keys()) == ALLOWED_SOURCE_ANCHOR_KEYS
            assert isinstance(anchor["chunk_id"], str)
            assert isinstance(anchor["chunk_index"], int)
            assert isinstance(anchor["sentence_index"], int)
            assert isinstance(anchor["excerpt_fingerprint"], str)
            assert anchor["page_start"] is None or isinstance(anchor["page_start"], int)
            assert anchor["page_end"] is None or isinstance(anchor["page_end"], int)
        assert isinstance(item["content_fingerprint"], str)
        assert len(item["content_fingerprint"]) == 24
        assert item["generator_version"] == "grounded-summary-v1"
        assert item["generation_method"] == "deterministic_extractive"
    assert_no_forbidden_terms(payload)


def test_study_material_summary_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/materials/doc-unknown/study/summary")

    assert response.status_code == 401


def test_study_material_summary_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/materials/doc-unknown/study/summary")

    assert response.status_code == 404


def test_study_material_summary_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula\n\nOTHER-STUDY-SUMMARY-SHOULD-NOT-LEAK",
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    response = other.get(f"/api/materials/{document_id}/study/summary")

    assert response.status_code == 404


def test_study_material_summary_rejects_non_study_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="edital.md",
        content=b"# Edital\n\nConteudo seguro.",
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.get(f"/api/materials/{document_id}/study/summary")

    assert response.status_code == 422
    assert "study material" in response.json()["detail"].lower()


def test_unprepared_study_material_summary_returns_not_ready(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "unprepared-owner")
    uploaded = upload_material(
        owner,
        filename="aula.txt",
        content=b"Conteudo seguro ainda nao preparado.",
        content_type="text/plain",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.get(f"/api/materials/{document_id}/study/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["summary_status"] == "not_ready"
    assert payload["sections_count"] == 0
    assert payload["items"] == []
    assert repository.list_document_sections(document_id, user_id=user["user_id"]) == []
    assert_bounded_study_summary_payload(payload)


def test_prepared_markdown_study_material_returns_bounded_summary_items(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "md-owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-STUDY-SUMMARY-SHOULD-NOT-LEAK\n\n"
            b"## Poder de policia\n\n"
            b"Conteudo seguro para estudo."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    prepared = owner.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200

    response = owner.get(f"/api/materials/{document_id}/study/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["document_id"] == document_id
    assert payload["summary_status"] == "ready"
    assert payload["sections_count"] == 2
    assert [item["title"] for item in payload["items"]] == [
        "Atos administrativos",
        "Poder de policia",
    ]
    assert payload["items"][0]["summary"] == "Conteúdo insuficiente para montar um resumo confiável desta seção."
    assert payload["items"][0]["key_points"] == []
    assert payload["items"][1]["summary"] == "Conteudo seguro para estudo."
    assert payload["items"][0]["estimated_minutes"] >= 3
    assert_bounded_study_summary_payload(payload)


def test_prepared_text_study_material_with_weak_structure_needs_review(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "txt-owner")
    uploaded = upload_material(
        owner,
        filename="aula.txt",
        content=b"Conteudo seguro sem cabecalho markdown.",
        content_type="text/plain",
    )
    document_id = uploaded["metadata"]["document_id"]
    prepared = owner.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200

    response = owner.get(f"/api/materials/{document_id}/study/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["summary_status"] == "needs_review"
    assert payload["sections_count"] == 1
    assert payload["items"][0]["title"] == "Document"
    assert payload["items"][0]["key_points"] == []
    assert payload["items"][0]["status"] == "needs_review"
    assert_bounded_study_summary_payload(payload)


def test_study_material_summary_is_idempotent(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula estavel\n\nConteudo seguro.",
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    first = owner.get(f"/api/materials/{document_id}/study/summary").json()
    second = owner.get(f"/api/materials/{document_id}/study/summary").json()

    assert first == second
    assert_bounded_study_summary_payload(first)


def test_grounded_summary_preserves_definition_exception_and_source_anchors(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "grounded-owner")
    uploaded = upload_material(
        owner,
        filename="poder-policia.md",
        content=(
            b"# Poder de policia\n\n"
            b"O poder de policia consiste na atividade administrativa que limita direitos em favor do interesse publico. "
            b"A atuacao deve observar competencia, finalidade e proporcionalidade. "
            b"Exceto quando a lei autoriza medida imediata, a administracao deve respeitar o procedimento previsto. "
            b"A fiscalizacao preventiva reduz riscos antes da ocorrencia do dano."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    payload = owner.get(f"/api/materials/{document_id}/study/summary").json()
    item = payload["items"][0]

    assert payload["summary_status"] == "ready"
    assert item["status"] == "ready"
    assert "O poder de policia consiste" in item["summary"]
    assert "Exceto quando a lei autoriza" in item["summary"]
    assert 2 <= len(item["source_anchors"]) <= 5
    assert all(point in item["summary"] for point in item["key_points"])
    assert item["source_material_id"] == document_id
    assert item["source_section_id"] == item["section_id"]
    assert_bounded_study_summary_payload(payload)


def test_grounded_summary_deduplicates_repeated_sentences_and_list_items(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "list-owner")
    uploaded = upload_material(
        owner,
        filename="classificacao.md",
        content=(
            b"# Classificacao dos atos\n\n"
            b"Os atos administrativos classificam-se conforme alcance e destinatarios.\n"
            b"- Atos gerais possuem destinatarios indeterminados.\n"
            b"- Atos individuais possuem destinatarios determinados.\n"
            b"- Atos gerais possuem destinatarios indeterminados.\n"
            b"Os atos administrativos classificam-se conforme alcance e destinatarios."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    item = owner.get(f"/api/materials/{document_id}/study/summary").json()["items"][0]

    assert item["status"] == "ready"
    assert item["summary"].count("Atos gerais possuem destinatarios indeterminados.") == 1
    assert item["summary"].count("classificam-se conforme alcance e destinatarios.") == 1
    assert len(item["key_points"]) == len(set(item["key_points"]))
    assert len(item["key_points"]) <= 7


def test_grounded_summary_fingerprint_is_stable_and_changes_with_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "fingerprint-owner")
    uploaded = upload_material(
        owner,
        filename="competencia.md",
        content=(
            b"# Competencia\n\n"
            b"A competencia define qual agente pode praticar o ato administrativo."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    first = owner.get(f"/api/materials/{document_id}/study/summary").json()
    second = owner.get(f"/api/materials/{document_id}/study/summary").json()
    first_item = first["items"][0]
    assert first_item["content_fingerprint"] == second["items"][0]["content_fingerprint"]

    chunks = repository.list_document_chunks(document_id, user_id=user["user_id"])
    changed = [
        DocumentChunk.model_validate(
            {
                **chunk.model_dump(mode="json"),
                "text": "A competencia define o agente legalmente autorizado e impede atuacao fora dos limites previstos.",
                "text_length": 96,
            }
        )
        for chunk in chunks
    ]
    repository.save_document_chunks(document_id, changed, user_id=user["user_id"])

    third_item = owner.get(f"/api/materials/{document_id}/study/summary").json()["items"][0]
    assert third_item["content_fingerprint"] != first_item["content_fingerprint"]
    assert third_item["summary"] != first_item["summary"]


def test_grounded_summary_rejects_formatting_noise_as_source_evidence(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "noise-owner")
    uploaded = upload_material(
        owner,
        filename="indice.md",
        content=(
            b"# Indice\n\n"
            b"1\n2\n3\nPagina 4\nTodos os direitos reservados."
        ),
    )
    document_id = uploaded["metadata"]["document_id"]
    assert owner.post(f"/api/materials/{document_id}/study/prepare").status_code == 200

    item = owner.get(f"/api/materials/{document_id}/study/summary").json()["items"][0]

    assert item["status"] == "needs_review"
    assert item["summary"] == "Conteúdo insuficiente para montar um resumo confiável desta seção."
    assert item["key_points"] == []
    assert item["source_anchors"] == []
