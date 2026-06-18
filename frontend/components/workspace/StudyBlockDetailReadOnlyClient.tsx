"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";
import {
  createStudyProgressEvent,
  fetchAdaptiveQuestionQueue,
  fetchStudyBlockDetail,
  reviewStudyBlockQuestionAnswer
} from "@/lib/api/study";
import type {
  BackendAdaptiveQuestionQueue,
  BackendStudyBlockAnswerReview,
  BackendStudyBlockDetail,
  BackendStudyBlockQuestionItem,
  StudyBlockAnswerFormat
} from "@/lib/api/types";

type BlockDetailState =
  | { status: "loading" }
  | { status: "ready"; detail: BackendStudyBlockDetail }
  | { status: "needs_review"; detail: BackendStudyBlockDetail }
  | { status: "not_ready"; message: string }
  | { status: "auth_required"; message: string }
  | { status: "not_found"; message: string }
  | { status: "unavailable"; message: string };

type QuestionsState =
  | { status: "loading" }
  | { status: "ready"; questions: BackendAdaptiveQuestionQueue }
  | { status: "needs_review"; questions: BackendAdaptiveQuestionQueue }
  | { status: "not_ready"; message: string }
  | { status: "auth_required"; message: string }
  | { status: "not_found"; message: string }
  | { status: "unavailable"; message: string };

type QuestionReviewState = {
  selectedAlternative?: string;
  submissionKey?: string;
  status?: "submitting" | "success" | "error";
  message?: string;
  review?: BackendStudyBlockAnswerReview;
};

type QuestionReviewStateMap = Record<string, QuestionReviewState>;

type StudyProgressActionState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

function createAttemptSubmissionKey(questionId: string): string {
  const suffix =
    typeof globalThis.crypto?.randomUUID === "function"
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `question-attempt:${questionId}:${suffix}`;
}

function statusLabel(status: BackendStudyBlockDetail["detail_status"]): string {
  if (status === "ready") {
    return "Pronto para estudo";
  }
  if (status === "needs_review") {
    return "Precisa de conferência";
  }
  return "Ainda não pronto";
}

function sectionStatusLabel(status: BackendStudyBlockDetail["sections"][number]["status"]): string {
  return status === "ready" ? "Pronto para estudo" : "Precisa de conferência";
}

function questionTypeLabel(type: BackendStudyBlockQuestionItem["type"]): string {
  if (type === "true_false") {
    return "Certo ou errado";
  }
  if (type === "multiple_choice") {
    return "Múltipla escolha";
  }
  return "Resposta curta";
}

function questionDifficultyLabel(difficulty: BackendStudyBlockQuestionItem["difficulty"]): string {
  if (difficulty === "medium") {
    return "Média";
  }
  if (difficulty === "hard") {
    return "Difícil";
  }
  return "Básica";
}

function questionItemStatusLabel(status: BackendStudyBlockQuestionItem["status"]): string {
  return status === "candidate" ? "Questão candidata" : "Precisa de conferência";
}

function failureState(code: string | undefined): BlockDetailState {
  if (code === "auth_required" || code === "unauthorized") {
    return { status: "auth_required", message: "Entre para ver este bloco de estudo." };
  }
  if (code === "not_found") {
    return { status: "not_found", message: "Bloco de estudo não encontrado." };
  }
  if (code === "not_ready") {
    return { status: "not_ready", message: "Este bloco ainda não está pronto para estudo." };
  }
  return { status: "unavailable", message: "Não foi possível carregar este bloco agora." };
}

function questionsFailureState(code: string | undefined): QuestionsState {
  if (code === "auth_required" || code === "unauthorized") {
    return { status: "auth_required", message: "Entre para ver as questões deste bloco." };
  }
  if (code === "not_found") {
    return { status: "not_found", message: "Bloco de estudo não encontrado." };
  }
  if (code === "not_ready") {
    return { status: "not_ready", message: "As questões ainda não estão prontas para este bloco." };
  }
  return { status: "unavailable", message: "Não foi possível carregar as questões agora." };
}

function answerReviewFailureMessage(code: string | undefined): string {
  if (code === "auth_required" || code === "unauthorized") {
    return "Entre para revisar sua escolha.";
  }
  if (code === "not_found") {
    return "Questão ou bloco de estudo não encontrado.";
  }
  if (code === "validation_error") {
    return "Revise sua escolha antes de enviar.";
  }
  return "Não foi possível revisar sua escolha agora.";
}

function progressEventFailureMessage(code: string | undefined): string {
  if (code === "auth_required" || code === "unauthorized") {
    return "Entre para registrar seu estudo.";
  }
  if (code === "invalid_request" || code === "validation_error") {
    return "Não foi possível registrar este bloco.";
  }
  return "Não foi possível registrar esta ação agora.";
}

function suggestedActionLabel(action: BackendStudyBlockAnswerReview["reinforcement"]["suggested_action"]): string {
  if (action === "retry_question") {
    return "Tentar novamente";
  }
  if (action === "revisit_block") {
    return "Revisitar bloco";
  }
  return "Revisar resumo";
}

function reviewResultMessage(review: BackendStudyBlockAnswerReview): string {
  if (review.result === "correct") {
    return "Escolha alinhada ao material.";
  }
  if (review.result === "incorrect") {
    return "Revise este ponto antes de avançar.";
  }
  if (review.result === "ungraded") {
    return "Escolha revisada sem pontuação.";
  }
  if (review.result === "needs_review" || review.review_status === "needs_review") {
    return "Esta escolha precisa de conferência.";
  }
  return "Orientação de estudo registrada sem pontuação.";
}

function reinforcementMessage(review: BackendStudyBlockAnswerReview): string {
  return (
    review.reinforcement.message.trim() ||
    "Revise o resumo do bloco e os pontos principais antes de tentar novamente."
  );
}

function QuestionsCard({
  blockId,
  state,
  refreshQueue
}: {
  blockId: string;
  state: QuestionsState;
  refreshQueue: () => Promise<boolean>;
}) {
  const [reviews, setReviews] = useState<QuestionReviewStateMap>({});
  const [retainedQuestions, setRetainedQuestions] = useState<Record<string, BackendStudyBlockQuestionItem>>({});
  const [queueRefreshMessage, setQueueRefreshMessage] = useState<string | null>(null);

  useEffect(() => {
    setReviews({});
    setRetainedQuestions({});
    setQueueRefreshMessage(null);
  }, [blockId]);

  function updateQuestionReview(questionId: string, nextState: QuestionReviewState) {
    setReviews((current) => ({
      ...current,
      [questionId]: {
        ...current[questionId],
        ...nextState
      }
    }));
  }

  async function handleReviewChoice(item: BackendStudyBlockQuestionItem) {
    const current = reviews[item.question_id];
    const selectedAlternative = current?.selectedAlternative;
    if (!selectedAlternative) {
      updateQuestionReview(item.question_id, {
        status: "error",
        message: "Selecione uma alternativa antes de revisar."
      });
      return;
    }

    const answerFormat: StudyBlockAnswerFormat = item.type === "true_false" ? "true_false" : "choice";
    const submissionKey =
      current?.submissionKey ?? createAttemptSubmissionKey(item.question_id);
    updateQuestionReview(item.question_id, {
      submissionKey,
      status: "submitting",
      message: undefined,
      review: undefined
    });

    const result = await reviewStudyBlockQuestionAnswer(blockId, item.question_id, {
      answer: selectedAlternative,
      answer_format: answerFormat,
      response_context: "study_block",
      idempotency_key: submissionKey
    });

    if (result.ok) {
      updateQuestionReview(item.question_id, {
        submissionKey: undefined,
        status: "success",
        message: undefined,
        review: result.data
      });
      setRetainedQuestions((current) => ({
        ...current,
        [item.question_id]: item
      }));
      const refreshed = await refreshQueue();
      setQueueRefreshMessage(
        refreshed ? null : "A tentativa foi registrada, mas a próxima lista de questões não carregou agora."
      );
      return;
    }

    updateQuestionReview(item.question_id, {
      status: "error",
      message: answerReviewFailureMessage(result.error.code),
      review: undefined
    });
  }

  return (
    <section className="space-y-4">
      <div>
        <div className="section-kicker">revisão</div>
        <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">Questões de fixação</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-silver">
          Revise o bloco com questões de apoio.
        </p>
      </div>

      {state.status === "loading" ? (
        <Card className="border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)]">
          <CardTitle className="text-[1.35rem]">Carregando questões de fixação.</CardTitle>
        </Card>
      ) : null}

      {state.status === "not_ready" ? (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.35rem]">{state.message}</CardTitle>
          <p className="mt-3 text-sm leading-7 text-silver">Estude o resumo do bloco primeiro.</p>
        </Card>
      ) : null}

      {state.status === "auth_required" || state.status === "not_found" || state.status === "unavailable" ? (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.35rem]">{state.message}</CardTitle>
        </Card>
      ) : null}

      {state.status === "ready" || state.status === "needs_review" ? (
        <div className="grid gap-4">
          {state.status === "needs_review" ? (
            <p className="rounded-2xl border border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.07)] px-4 py-3 text-sm leading-7 text-silver">
              Estas questões precisam de conferência.
            </p>
          ) : null}
          {queueRefreshMessage ? (
            <p className="rounded-2xl border border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.07)] px-4 py-3 text-sm leading-7 text-silver">
              {queueRefreshMessage}
            </p>
          ) : null}
          {(() => {
            const retainedItems = Object.values(retainedQuestions).filter(
              (item) => reviews[item.question_id]?.status === "success"
            );
            const retainedIds = new Set(retainedItems.map((item) => item.question_id));
            const visibleItems = [
              ...retainedItems,
              ...state.questions.items.filter((item) => !retainedIds.has(item.question_id))
            ];
            return visibleItems.length ? (
            visibleItems.map((item, index) => {
              const itemStatusLabel = questionItemStatusLabel(item.status);
              const review = reviews[item.question_id];
              const isObjectiveQuestion = item.type === "multiple_choice" || item.type === "true_false";
              return (
                <Card key={item.question_id} className="min-w-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted">
                        {questionTypeLabel(item.type)} · {questionDifficultyLabel(item.difficulty)}
                      </p>
                      <CardTitle className="mt-3 break-words text-[1.25rem] leading-[1.15]">
                        {index + 1}. {item.prompt}
                      </CardTitle>
                    </div>
                    <Badge className={productStatusClass(itemStatusLabel)}>{itemStatusLabel}</Badge>
                  </div>

                  {item.topic_label || item.subtopic_label ? (
                    <p className="mt-4 text-sm leading-7 text-silver">
                      {[item.topic_label, item.subtopic_label].filter(Boolean).join(" · ")}
                    </p>
                  ) : null}

                  {!isObjectiveQuestion && item.alternatives.length ? (
                    <ul className="mt-5 space-y-2 text-sm leading-7 text-silver">
                      {item.alternatives.map((alternative) => (
                        <li key={`${item.question_id}-${alternative.id}`}>
                          {alternative.id}. {alternative.text}
                        </li>
                      ))}
                    </ul>
                  ) : null}

                  {isObjectiveQuestion && item.alternatives.length ? (
                    <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.025)] p-4">
                      <fieldset className="space-y-3">
                        <legend className="text-xs uppercase tracking-[0.18em] text-muted">
                          Escolha uma alternativa
                        </legend>
                        <div className="mt-3 grid gap-2">
                          {item.alternatives.map((alternative) => (
                            <label
                              key={`${item.question_id}-choice-${alternative.id}`}
                              className="flex cursor-pointer items-start gap-3 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.02)] px-4 py-3 text-sm leading-6 text-silver transition hover:border-[rgba(201,169,110,0.30)]"
                            >
                              <input
                                className="mt-1 accent-[var(--accent)]"
                                name={`answer-${item.question_id}`}
                                type="radio"
                                value={alternative.id}
                                checked={review?.selectedAlternative === alternative.id}
                                onChange={() =>
                                  updateQuestionReview(item.question_id, {
                                    selectedAlternative: alternative.id,
                                    submissionKey: undefined,
                                    status: undefined,
                                    message: undefined,
                                    review: undefined
                                  })
                                }
                              />
                              <span>
                                <span className="font-semibold text-ink">{alternative.id}.</span> {alternative.text}
                              </span>
                            </label>
                          ))}
                        </div>
                      </fieldset>

                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <button
                          className="rounded-full border border-[rgba(201,169,110,0.45)] bg-[rgba(201,169,110,0.12)] px-4 py-2 text-sm font-semibold text-ink transition hover:bg-[rgba(201,169,110,0.18)] disabled:cursor-not-allowed disabled:opacity-60"
                          type="button"
                          disabled={review?.status === "submitting"}
                          onClick={() => void handleReviewChoice(item)}
                        >
                          {review?.status === "submitting" ? "Revisando escolha..." : "Revisar escolha"}
                        </button>
                        {review?.status === "error" && review.message ? (
                          <p className="text-sm leading-7 text-silver">{review.message}</p>
                        ) : null}
                      </div>
                    </div>
                  ) : null}

                  {item.type === "short_answer" ? (
                    <p className="mt-5 rounded-2xl border border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.07)] px-4 py-3 text-sm leading-7 text-silver">
                      Revisão interativa ainda não disponível para este tipo de questão.
                    </p>
                  ) : null}

                  {review?.status === "success" && review.review ? (
                    <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)] p-4">
                      <div className="section-kicker">Orientação de estudo</div>
                      <CardTitle className="mt-3 text-[1.25rem]">Feedback</CardTitle>
                      <p className="mt-3 text-sm leading-7 text-silver">{reviewResultMessage(review.review)}</p>
                      <p className="mt-3 text-sm leading-7 text-silver">{review.review.feedback}</p>
                      <div className="mt-5 rounded-2xl border border-[rgba(201,169,110,0.18)] bg-[rgba(201,169,110,0.07)] p-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-gold2">Reforço sugerido</div>
                        {review.review.reinforcement.topic_label || review.review.reinforcement.subtopic_label ? (
                          <p className="mt-3 text-sm leading-7 text-silver">
                            {[review.review.reinforcement.topic_label, review.review.reinforcement.subtopic_label]
                              .filter(Boolean)
                              .join(" · ")}
                          </p>
                        ) : null}
                        <p className="mt-3 text-sm leading-7 text-silver">{reinforcementMessage(review.review)}</p>
                        <Badge
                          className={productStatusClass(
                            suggestedActionLabel(review.review.reinforcement.suggested_action)
                          )}
                        >
                          {suggestedActionLabel(review.review.reinforcement.suggested_action)}
                        </Badge>
                      </div>
                      <p className="mt-4 text-xs uppercase tracking-[0.18em] text-muted">
                        Orientação de estudo, sem correção oficial, notas ou alteração de progresso.
                      </p>
                    </div>
                  ) : null}

                  <p className="mt-5 text-xs uppercase tracking-[0.18em] text-muted">
                    Revisão sem respostas oficiais
                  </p>
                </Card>
              );
            })
          ) : (
            <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
              <CardTitle className="text-[1.35rem]">Nenhuma questão de fixação está disponível para este bloco.</CardTitle>
              <p className="mt-3 text-sm leading-7 text-silver">Continue pelo resumo e pelos pontos principais.</p>
            </Card>
          );
          })()}
        </div>
      ) : null}
    </section>
  );
}

export function StudyBlockDetailReadOnlyClient({ blockId }: { blockId: string }) {
  const [state, setState] = useState<BlockDetailState>({ status: "loading" });
  const [questionsState, setQuestionsState] = useState<QuestionsState>({ status: "loading" });
  const [progressActionState, setProgressActionState] = useState<StudyProgressActionState>({ status: "idle" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    setQuestionsState({ status: "loading" });

    void fetchStudyBlockDetail(blockId).then((result) => {
      if (!active) {
        return;
      }
      if (result.ok) {
        setState({
          status: result.data.detail_status === "ready" ? "ready" : "needs_review",
          detail: result.data
        });
        return;
      }
      setState(failureState(result.error.code));
    });

    void fetchAdaptiveQuestionQueue(blockId, 5).then((result) => {
      if (!active) {
        return;
      }
      if (result.ok) {
        setQuestionsState({
          status: result.data.queue_status === "ready" ? "ready" : "needs_review",
          questions: result.data
        });
        return;
      }
      setQuestionsState(questionsFailureState(result.error.code));
    });

    return () => {
      active = false;
    };
  }, [blockId]);

  async function refreshQuestionQueue(): Promise<boolean> {
    const result = await fetchAdaptiveQuestionQueue(blockId, 5);
    if (!result.ok) {
      return false;
    }
    setQuestionsState({
      status: result.data.queue_status === "ready" ? "ready" : "needs_review",
      questions: result.data
    });
    return true;
  }

  async function handleMarkBlockStudied() {
    if (progressActionState.status === "submitting" || progressActionState.status === "success") {
      return;
    }

    setProgressActionState({ status: "submitting" });

    const result = await createStudyProgressEvent({
      event_type: "block_marked_studied",
      target_type: "block",
      target_id: blockId,
      idempotency_key: `block_marked_studied:${blockId}`
    });

    if (result.ok) {
      setProgressActionState({ status: "success", message: "Bloco marcado como estudado." });
      return;
    }

    setProgressActionState({
      status: "error",
      message: progressEventFailureMessage(result.error.code)
    });
  }

  if (state.status === "loading") {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudar bloco"
          subtitle="Carregando a orientação deste bloco."
          connection={{
            state: "connected",
            source: "backend",
            title: "Bloco disponível",
            detail: "A leitura aparece quando o bloco estiver disponível."
          }}
        />
        <Card>
          <div className="section-kicker">carregando</div>
          <CardTitle className="mt-5 text-[1.8rem]">Preparando a leitura do bloco.</CardTitle>
        </Card>
      </div>
    );
  }

  if (state.status === "auth_required" || state.status === "not_found" || state.status === "unavailable") {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudar bloco"
          subtitle="Abra um bloco disponível no seu caminho de estudo."
          connection={{
            state: state.status === "auth_required" ? "auth_required" : "offline",
            source: state.status === "auth_required" ? "backend" : "offline",
            title: state.status === "auth_required" ? "Entre para continuar" : "Não foi possível carregar agora",
            detail: state.message
          }}
        />
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">próximo passo</div>
          <CardTitle className="mt-5 max-w-3xl break-words text-[1.95rem] leading-[1.02]">
            {state.message}
          </CardTitle>
          <div className="mt-6 flex flex-wrap gap-3">
            {state.status === "auth_required" ? <WorkspaceLink href="/login">Entrar</WorkspaceLink> : null}
            <WorkspaceLink href="/study">Voltar ao caminho de estudo</WorkspaceLink>
          </div>
        </Card>
      </div>
    );
  }

  if (state.status === "not_ready") {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudar bloco"
          subtitle="Este bloco precisa de preparo antes da leitura."
          connection={{
            state: "connected",
            source: "backend",
            title: "Bloco recebido",
            detail: state.message
          }}
        />
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">ainda não pronto</div>
          <CardTitle className="mt-5 max-w-3xl break-words text-[1.95rem] leading-[1.02]">
            Este bloco ainda não está pronto para estudo.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Volte ao caminho de estudo ou prepare o material relacionado.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/study">Voltar ao caminho de estudo</WorkspaceLink>
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          </div>
        </Card>
      </div>
    );
  }

  const detail = state.detail;
  const label = statusLabel(detail.detail_status);
  const actions = detail.actions.length
    ? detail.actions
    : [
        { label: "Abrir material", href: `/materials/${detail.material_id}` },
        { label: "Voltar ao caminho de estudo", href: "/study" }
      ];

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="estudo"
        title="Estudar bloco"
        subtitle="Use este bloco como guia inicial de leitura."
        connection={{
          state: "connected",
          source: "backend",
          title: "Bloco disponível",
          detail: "Leia o resumo, revise a questão e registre o estudo quando terminar."
        }}
      />

      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
        <div className="section-kicker">bloco de estudo</div>
        <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <CardTitle className="break-words text-[1.95rem] leading-[1.02]">
              {detail.title}
            </CardTitle>
            {detail.topic_label || detail.subtopic_label ? (
              <p className="mt-4 text-sm leading-7 text-silver">
                {[detail.topic_label, detail.subtopic_label].filter(Boolean).join(" · ")}
              </p>
            ) : null}
          </div>
          <Badge className={productStatusClass(label)}>{label}</Badge>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">material</p>
            <p className="mt-2 break-words text-sm text-ink">{detail.material_title}</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
            <p className="mt-2 text-lg text-ink">{detail.estimated_minutes} min</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">modo</p>
            <p className="mt-2 text-lg text-ink">Leitura orientada</p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          {actions.map((action) => (
            <WorkspaceLink key={`${action.label}-${action.href}`} href={action.href}>
              {action.label}
            </WorkspaceLink>
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.025)] p-4">
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="rounded-full border border-[rgba(201,169,110,0.45)] bg-[rgba(201,169,110,0.12)] px-4 py-2 text-sm font-semibold text-ink transition hover:bg-[rgba(201,169,110,0.18)] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={progressActionState.status === "submitting" || progressActionState.status === "success"}
              onClick={() => void handleMarkBlockStudied()}
            >
              {progressActionState.status === "submitting"
                ? "Registrando estudo..."
                : progressActionState.status === "success"
                  ? "Estudo registrado"
                  : "Marcar bloco como estudado"}
            </button>
            {progressActionState.status === "success" || progressActionState.status === "error" ? (
              <p className="text-sm leading-7 text-silver">{progressActionState.message}</p>
            ) : null}
          </div>
          <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted">
            Registra somente este bloco; não finaliza o material.
          </p>
        </div>
      </Card>

      <section className="space-y-4">
        <div>
          <div className="section-kicker">resumo do bloco</div>
          <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">Resumo do bloco</h2>
        </div>
        <div className="grid gap-4">
          {detail.sections.map((section) => {
            const sectionLabel = sectionStatusLabel(section.status);
            return (
              <Card key={section.section_id} className="min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <CardTitle className="break-words text-[1.45rem] leading-[1.05]">
                    {section.title}
                  </CardTitle>
                  <Badge className={productStatusClass(sectionLabel)}>{sectionLabel}</Badge>
                </div>
                <p className="mt-4 text-sm leading-7 text-silver">{section.summary}</p>
                {section.key_points.length ? (
                  <div className="mt-5">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted">pontos principais</p>
                    <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
                      {section.key_points.map((point) => (
                        <li key={point}>• {point}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <p className="mt-5 text-xs uppercase tracking-[0.18em] text-muted">
                  {section.estimated_minutes} min de leitura estimada
                </p>
              </Card>
            );
          })}
        </div>
      </section>

      <QuestionsCard blockId={blockId} state={questionsState} refreshQueue={refreshQuestionQueue} />
    </div>
  );
}
