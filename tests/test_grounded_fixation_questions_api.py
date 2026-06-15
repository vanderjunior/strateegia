from __future__ import annotations

import json

from app.api import routes
from app.domain.models import DocumentChunk
from tests.test_answer_review_api import encoded_review_path
from tests.test_fixation_questions_read_api import (
    create_clients,
    encoded_questions_path,
    first_block,
    prepare_study_material,
    register_and_login,
    upload_material,
)


DEFINITION_SOURCE = (
    b"# Poder de policia\n\n"
    b"O poder de policia consiste em atividade administrativa que deve limitar direitos "
    b"para proteger a finalidade publica e produzir efeitos imediatos."
)


def internal_questions(repository, user_id: str, block_id: str) -> list[dict[str, object]]:
    _, _, questions = routes._internal_fixation_question_candidates(repository, user_id, block_id)
    return questions


def test_grounded_definition_question_has_internal_correctness_and_evidence(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "definition-owner")
    uploaded = upload_material(owner, filename="definicao.md", content=DEFINITION_SOURCE)
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)

    response = owner.get(encoded_questions_path(str(block["block_id"])))
    payload = response.json()
    questions = internal_questions(repository, str(user["user_id"]), str(block["block_id"]))

    assert response.status_code == 200
    assert payload["question_status"] == "ready"
    assert payload["items"]
    public = payload["items"][0]
    internal = next(item for item in questions if item["question_id"] == public["question_id"])
    assert internal["_validation_state"] == "validated"
    assert internal["_correct_answer"] in {item["id"] for item in public["alternatives"]}
    assert internal["_evidence"] in {item["text"] for item in public["alternatives"]}
    assert internal["_material_id"] == document_id
    assert internal["_source_anchor"]["chunk_id"]
    assert internal["_source_anchor"]["excerpt_fingerprint"]
    assert internal["_rationale"]
    assert internal["_generator_method"] == "deterministic_source_transformation"
    assert internal["_generator_version"] == "grounded-question-v1"
    alternative_texts = [item["text"] for item in public["alternatives"]]
    assert len(alternative_texts) == len(set(alternative_texts)) == 5
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "correct_answer" not in serialized
    assert "_rationale" not in serialized
    assert internal["_evidence"] not in serialized or internal["_evidence"] in alternative_texts


def test_grounded_questions_are_deterministic_and_deduplicate_repeated_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "stable-question-owner")
    repeated = DEFINITION_SOURCE + b"\n\n" + DEFINITION_SOURCE.split(b"\n\n", maxsplit=1)[1]
    uploaded = upload_material(owner, filename="repetido.md", content=repeated)
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    first = owner.get(encoded_questions_path(str(block["block_id"]))).json()
    second = owner.get(encoded_questions_path(str(block["block_id"]))).json()
    internal_first = internal_questions(repository, str(user["user_id"]), str(block["block_id"]))
    internal_second = internal_questions(repository, str(user["user_id"]), str(block["block_id"]))

    assert first == second
    assert internal_first == internal_second
    assert len(first["items"]) == 1
    assert len({item["question_id"] for item in first["items"]}) == len(first["items"])
    assert len({item["prompt"] for item in first["items"]}) == len(first["items"])


def test_grounded_rule_and_exception_questions_preserve_source_meaning(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "rule-exception-owner")
    uploaded = upload_material(
        owner,
        filename="regras.md",
        content=(
            b"# Regras administrativas\n\n"
            b"A administracao deve limitar medidas imediatas para proteger a finalidade publica "
            b"e impedir atividade privada. "
            b"Exceto quando a lei permite medida imediata, a administracao deve limitar direitos "
            b"para proteger a finalidade publica."
        ),
    )
    prepare_study_material(owner, uploaded)
    block = first_block(owner)

    payload = owner.get(encoded_questions_path(str(block["block_id"]))).json()
    questions = internal_questions(repository, str(user["user_id"]), str(block["block_id"]))

    assert payload["question_status"] == "ready"
    assert {"rule_condition", "exception"} <= {item["_strategy"] for item in questions}
    for question in questions:
        if question["_strategy"] not in {"rule_condition", "exception"}:
            continue
        correct_text = next(
            alternative["text"]
            for alternative in question["alternatives"]
            if alternative["id"] == question["_correct_answer"]
        )
        assert correct_text == question["_evidence"]


def test_changed_source_changes_question_fingerprint_and_prompt_set(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "changed-question-owner")
    uploaded = upload_material(owner, filename="mudanca.md", content=DEFINITION_SOURCE)
    document_id = prepare_study_material(owner, uploaded)
    block = first_block(owner)
    block_id = str(block["block_id"])
    first = owner.get(encoded_questions_path(block_id)).json()
    first_ids = [item["question_id"] for item in first["items"]]

    chunks = repository.list_document_chunks(document_id, user_id=str(user["user_id"]))
    changed = [
        DocumentChunk.model_validate(
            {
                **chunk.model_dump(mode="json"),
                "text": (
                    "O poder regulamentar consiste em atividade administrativa que deve limitar "
                    "a execução para proteger a finalidade publica e produzir efeitos posteriores."
                ),
                "text_length": 153,
            }
        )
        for chunk in chunks
    ]
    repository.save_document_chunks(document_id, changed, user_id=str(user["user_id"]))

    second = owner.get(encoded_questions_path(block_id)).json()

    assert second["items"]
    assert [item["question_id"] for item in second["items"]] != first_ids
    assert [item["prompt"] for item in second["items"]] != [item["prompt"] for item in first["items"]]


def test_grounded_true_false_questions_include_evidence_backed_true_and_false_items(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "cebraspe-owner")
    uploaded = upload_material(owner, filename="cebraspe.md", content=DEFINITION_SOURCE)
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    monkeypatch.setattr(routes, "_resolve_fixation_question_profile", lambda detail: "cebraspe_true_false")

    payload = owner.get(encoded_questions_path(str(block["block_id"]))).json()
    questions = internal_questions(repository, str(user["user_id"]), str(block["block_id"]))

    assert payload["question_status"] == "ready"
    assert {item["_correct_answer"] for item in questions} == {"C", "E"}
    assert all(item["_validation_state"] == "validated" for item in questions)
    assert all(item["_evidence"] for item in questions)
    assert all(item["_source_anchor"]["chunk_id"] for item in questions)


def test_insufficient_and_ambiguous_sources_produce_no_validated_question(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "cautious-question-owner")

    title_only = upload_material(owner, filename="titulo.md", content=b"# Competencia\n")
    prepare_study_material(owner, title_only)
    title_block = first_block(owner)
    title_payload = owner.get(encoded_questions_path(str(title_block["block_id"]))).json()
    assert title_payload["question_status"] in {"needs_review", "not_ready"}
    assert title_payload["items"] == []
    assert internal_questions(repository, str(user["user_id"]), str(title_block["block_id"])) == []

    ambiguous = upload_material(
        owner,
        filename="ambiguo.md",
        content=(
            b"# Classificacao\n\n"
            b"A classificacao pode ser simples ou composta, conforme interpretacoes diferentes do contexto."
        ),
    )
    prepare_study_material(owner, ambiguous)
    ambiguous_block = owner.get("/api/study/blocks").json()["items"][-1]
    ambiguous_payload = owner.get(encoded_questions_path(str(ambiguous_block["block_id"]))).json()
    assert ambiguous_payload["items"] == []
    assert internal_questions(repository, str(user["user_id"]), str(ambiguous_block["block_id"])) == []


def test_answer_review_is_server_derived_source_grounded_and_stateless(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "stateless-review-owner")
    uploaded = upload_material(owner, filename="review.md", content=DEFINITION_SOURCE)
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    block_id = str(block["block_id"])
    public = owner.get(encoded_questions_path(block_id)).json()["items"][0]
    internal = internal_questions(repository, str(user["user_id"]), block_id)[0]
    correct_answer = str(internal["_correct_answer"])
    wrong_answer = next(
        item["id"] for item in public["alternatives"] if item["id"] != correct_answer
    )
    before_attempts = repository.list_study_question_attempts(user_id=str(user["user_id"]))
    before_progress = repository.list_study_progress_events(user_id=str(user["user_id"]))

    incorrect = owner.post(
        encoded_review_path(block_id, str(public["question_id"])),
        json={"answer": wrong_answer, "answer_format": "choice"},
    )
    correct = owner.post(
        encoded_review_path(block_id, str(public["question_id"])),
        json={"answer": correct_answer, "answer_format": "choice"},
    )

    assert incorrect.status_code == 200
    assert incorrect.json()["result"] == "incorrect"
    assert str(internal["_evidence"]) in incorrect.json()["reinforcement"]["message"]
    assert correct.status_code == 200
    assert correct.json()["result"] == "correct"
    assert str(internal["_evidence"]) in correct.json()["feedback"]
    assert repository.list_study_question_attempts(user_id=str(user["user_id"])) == before_attempts
    assert repository.list_study_progress_events(user_id=str(user["user_id"])) == before_progress


def test_answer_review_rejects_choice_outside_actual_alternatives(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "invalid-choice-owner")
    uploaded = upload_material(owner, filename="choice.md", content=DEFINITION_SOURCE)
    prepare_study_material(owner, uploaded)
    block = first_block(owner)
    question = owner.get(encoded_questions_path(str(block["block_id"]))).json()["items"][0]

    response = owner.post(
        encoded_review_path(str(block["block_id"]), str(question["question_id"])),
        json={"answer": "Z", "answer_format": "choice"},
    )

    assert response.status_code == 422
