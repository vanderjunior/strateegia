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
    "question_status",
    "mode",
    "items",
    "warnings_count",
    "source",
}

ALLOWED_ITEM_KEYS = {
    "question_id",
    "type",
    "prompt",
    "alternatives",
    "topic_label",
    "subtopic_label",
    "difficulty",
    "status",
}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-FIXATION-QUESTIONS-SHOULD-NOT-LEAK",
    "OTHER-FIXATION-QUESTIONS-SHOULD-NOT-LEAK",
    "answer_key",
    "correct_answer",
    "correct_alternative",
    "gabarito",
    "is_correct",
    "solution",
    "rationale",
    "correction",
    "score",
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


def encoded_questions_path(block_id: str) -> str:
    return f"/api/study/blocks/{quote(block_id, safe='')}/questions"


def first_block(client: TestClient) -> dict[str, object]:
    response = client.get("/api/study/blocks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    return payload["items"][0]


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_questions_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_RESPONSE_KEYS
    assert isinstance(payload["block_id"], str)
    assert payload["question_status"] in {"ready", "needs_review", "not_ready", "unsupported"}
    assert payload["mode"] == "review_only"
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) <= 5
    assert isinstance(payload["warnings_count"], int)
    assert payload["source"] == "user_scope"
    prompts = [item["prompt"] for item in payload["items"]]
    assert len(prompts) == len(set(prompts))
    for item in payload["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert isinstance(item["question_id"], str)
        assert item["question_id"].startswith(f"question:{payload['block_id']}:")
        assert item["type"] in {"short_answer", "true_false", "multiple_choice"}
        assert isinstance(item["prompt"], str)
        assert item["prompt"]
        assert isinstance(item["alternatives"], list)
        if item["type"] == "short_answer":
            assert item["alternatives"] == []
        if item["type"] == "multiple_choice":
            alternative_ids = [alternative["id"] for alternative in item["alternatives"]]
            assert alternative_ids in (["A", "B", "C", "D"], ["A", "B", "C", "D", "E"])
            for alternative in item["alternatives"]:
                assert set(alternative.keys()) == {"id", "text"}
                assert isinstance(alternative["text"], str)
                assert alternative["text"]
        if item["type"] == "true_false":
            assert item["alternatives"] == [
                {"id": "C", "text": "Certo"},
                {"id": "E", "text": "Errado"},
            ]
        assert item["topic_label"] is None or isinstance(item["topic_label"], str)
        assert item["subtopic_label"] is None or isinstance(item["subtopic_label"], str)
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert item["status"] in {"candidate", "needs_review"}
    assert_no_forbidden_terms(payload)


def assert_multiple_choice_ae(payload: dict[str, object]) -> None:
    assert payload["items"]
    assert all(item["type"] == "multiple_choice" for item in payload["items"])
    assert all(
        [alternative["id"] for alternative in item["alternatives"]] == list("ABCDE")
        for item in payload["items"]
    )


def test_fixation_questions_require_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/blocks/study-block%3Amissing%3Adoc%3A0/questions")

    assert response.status_code == 401


def test_fixation_questions_return_404_for_missing_block(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/study/blocks/study-block%3Amissing%3Adoc%3A0/questions")

    assert response.status_code == 404


def test_fixation_questions_return_ready_material_only_candidates(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="aula.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-FIXATION-QUESTIONS-SHOULD-NOT-LEAK\n\n"
            + GROUNDED_QUESTION_SOURCE
        ),
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["block_id"] == block["block_id"]
    assert payload["question_status"] == "ready"
    assert payload["mode"] == "review_only"
    assert payload["items"]
    assert_multiple_choice_ae(payload)
    assert all(item["status"] == "candidate" for item in payload["items"])
    assert_bounded_questions_payload(payload)


def test_fixation_questions_include_connected_edital_labels(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    analyze_structured_edital(owner)
    uploaded = upload_material(
        owner,
        filename="atos-administrativos.md",
        content=(
            b"# Atos administrativos\n\n"
            b"RAW-FIXATION-QUESTIONS-SHOULD-NOT-LEAK\n\n"
            b"Atos administrativos produzem efeitos juridicos imediatos e devem observar finalidade publica."
        ),
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "ready"
    assert payload["items"]
    assert all(item["topic_label"] == "Direito Administrativo" for item in payload["items"])
    assert all(item["subtopic_label"] == "Atos administrativos" for item in payload["items"])
    assert_multiple_choice_ae(payload)
    assert_bounded_questions_payload(payload)


def test_fixation_questions_support_true_false_for_cebraspe_profile(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="cebraspe.md",
        content=b"# Atos administrativos\n\n" + GROUNDED_QUESTION_SOURCE,
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "cebraspe_true_false")

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "ready"
    assert payload["items"]
    assert all(item["type"] == "true_false" for item in payload["items"])
    assert all(
        item["alternatives"] == [{"id": "C", "text": "Certo"}, {"id": "E", "text": "Errado"}]
        for item in payload["items"]
    )
    assert_bounded_questions_payload(payload)


def test_fixation_questions_support_multiple_choice_ad_profile(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="objetiva-ad.md",
        content=b"# Atos administrativos\n\n" + GROUNDED_QUESTION_SOURCE,
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "multiple_choice_ad")

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "ready"
    assert payload["items"]
    assert all(item["type"] == "multiple_choice" for item in payload["items"])
    assert all(
        [alternative["id"] for alternative in item["alternatives"]] == list("ABCD")
        for item in payload["items"]
    )
    assert_bounded_questions_payload(payload)


def test_fixation_questions_return_unsupported_without_fabricated_fallback(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="fallback.md",
        content=b"# Atos administrativos\n\n" + GROUNDED_QUESTION_SOURCE,
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "unsupported_objective_profile")

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "unsupported"
    assert payload["items"] == []
    assert_bounded_questions_payload(payload)


def test_fixation_questions_return_not_ready_when_block_detail_is_not_ready(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    def fake_detail_response(repository, user_id: str, block_id: str) -> dict[str, object]:
        return {
            "block_id": block_id,
            "detail_status": "not_ready",
            "title": "Document",
            "topic_id": None,
            "topic_label": None,
            "subtopic_id": None,
            "subtopic_label": None,
            "material_id": "doc-1",
            "material_title": "Material",
            "summary_status": "not_ready",
            "estimated_minutes": 0,
            "sections": [],
            "actions": [],
            "source": "user_scope",
        }

    monkeypatch.setattr(routes, "_bounded_study_block_detail_response", fake_detail_response)
    monkeypatch.setattr(
        routes,
        "_grounded_question_evidence",
        lambda repository, user_id, detail: [],
    )

    response = owner.get(encoded_questions_path("study-block:not-ready:doc-1:0"))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "not_ready"
    assert payload["items"] == []
    assert_bounded_questions_payload(payload)


def test_fixation_questions_are_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="owner-study.md",
        content=b"# Aula privada\n\nOTHER-FIXATION-QUESTIONS-SHOULD-NOT-LEAK",
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = other.get(encoded_questions_path(str(block["block_id"])))

    assert response.status_code == 404


def test_fixation_questions_are_idempotent_and_read_only(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "stable-owner")
    uploaded = upload_material(
        owner,
        filename="aula-estavel.md",
        content=b"# Aula estavel\n\n" + GROUNDED_QUESTION_SOURCE,
    )
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)
    section_count = len(repository.list_document_sections(document_id, user_id=user["user_id"]))
    chunk_count = len(repository.list_document_chunks(document_id, user_id=user["user_id"]))

    first = owner.get(encoded_questions_path(str(block["block_id"])))
    second = owner.get(encoded_questions_path(str(block["block_id"])))

    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(repository.list_document_sections(document_id, user_id=user["user_id"])) == section_count
    assert len(repository.list_document_chunks(document_id, user_id=user["user_id"])) == chunk_count
    assert_bounded_questions_payload(first.json())


def test_fixation_questions_limit_and_deduplicate_candidates(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    def fake_detail_response(repository, user_id: str, block_id: str) -> dict[str, object]:
        return {
            "block_id": block_id,
            "detail_status": "needs_review",
            "title": "Revisão ampla",
            "topic_id": "topic-1",
            "topic_label": "Direito Administrativo",
            "subtopic_id": "subtopic-1",
            "subtopic_label": "Atos administrativos",
            "material_id": "doc-1",
            "material_title": "Material",
            "summary_status": "needs_review",
            "estimated_minutes": 20,
            "sections": [
                {
                    "section_id": "section-1",
                    "title": "Atos administrativos",
                    "summary": "Resumo em preparação para esta seção.",
                    "key_points": [
                        "Atos administrativos",
                        "Atos administrativos",
                        "Poderes administrativos",
                        "Responsabilidade civil do Estado",
                        "Controle administrativo",
                        "Licitações",
                    ],
                    "estimated_minutes": 10,
                    "status": "needs_review",
                }
            ],
            "actions": [],
            "source": "user_scope",
        }

    monkeypatch.setattr(routes, "_bounded_study_block_detail_response", fake_detail_response)
    monkeypatch.setattr(
        routes,
        "_grounded_question_evidence",
        lambda repository, user_id, detail: [
            {
                "text": (
                    f"O conceito {index} consiste em atividade administrativa que deve limitar direitos "
                    f"para proteger a finalidade publica e produzir efeitos imediatos."
                ),
                "strategy": "definition",
                "score": 10 - index,
                "source_order": (index, 0),
                "anchor": {
                    "chunk_id": f"chunk-{index}",
                    "chunk_index": index,
                    "sentence_index": 0,
                    "excerpt_fingerprint": f"fingerprint-{index}",
                    "page_start": None,
                    "page_end": None,
                },
            }
            for index in range(5)
        ],
    )

    response = owner.get(encoded_questions_path("study-block:wide:doc-1:0"))
    payload = response.json()

    assert response.status_code == 200
    assert payload["question_status"] == "needs_review"
    assert len(payload["items"]) == 5
    assert len({item["prompt"] for item in payload["items"]}) == 5
    assert all(item["type"] == "multiple_choice" for item in payload["items"])
    assert all(item["status"] == "needs_review" for item in payload["items"])
    assert_bounded_questions_payload(payload)


def test_fixation_questions_do_not_expose_answer_keys_or_raw_content(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="seguranca.md",
        content=(
            b"# Seguranca da resposta\n\n"
            b"answer_key correct_answer correct_alternative gabarito is_correct solution rationale correction score\n"
            b"raw text extracted_text chunk body section body storage_path /Users/ token cookie password_hash progress payload"
        ),
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_questions_payload(payload)
