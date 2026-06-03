"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";
import { fetchStudyBlockDetail, fetchStudyBlockQuestions } from "@/lib/api/study";
import type { BackendStudyBlockDetail, BackendStudyBlockQuestions } from "@/lib/api/types";

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
  | { status: "ready"; questions: BackendStudyBlockQuestions }
  | { status: "needs_review"; questions: BackendStudyBlockQuestions }
  | { status: "not_ready"; message: string }
  | { status: "auth_required"; message: string }
  | { status: "not_found"; message: string }
  | { status: "unavailable"; message: string };

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

function questionTypeLabel(type: BackendStudyBlockQuestions["items"][number]["type"]): string {
  if (type === "true_false") {
    return "Certo ou errado";
  }
  if (type === "multiple_choice") {
    return "Múltipla escolha";
  }
  return "Resposta curta";
}

function questionDifficultyLabel(difficulty: BackendStudyBlockQuestions["items"][number]["difficulty"]): string {
  if (difficulty === "medium") {
    return "Média";
  }
  if (difficulty === "hard") {
    return "Difícil";
  }
  return "Básica";
}

function questionItemStatusLabel(status: BackendStudyBlockQuestions["items"][number]["status"]): string {
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

function QuestionsCard({ state }: { state: QuestionsState }) {
  return (
    <section className="space-y-4">
      <div>
        <div className="section-kicker">revisão</div>
        <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">Questões de fixação</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-silver">
          Use estas questões como revisão inicial do bloco. Elas ainda não exibem respostas oficiais nem avaliam respostas.
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
          {state.questions.items.length ? (
            state.questions.items.map((item, index) => {
              const itemStatusLabel = questionItemStatusLabel(item.status);
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

                  {item.alternatives.length ? (
                    <ul className="mt-5 space-y-2 text-sm leading-7 text-silver">
                      {item.alternatives.map((alternative) => (
                        <li key={`${item.question_id}-${alternative.id}`}>
                          {alternative.id}. {alternative.text}
                        </li>
                      ))}
                    </ul>
                  ) : null}

                  <p className="mt-5 text-xs uppercase tracking-[0.18em] text-muted">
                    Sem respostas oficiais nesta etapa
                  </p>
                </Card>
              );
            })
          ) : (
            <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
              <CardTitle className="text-[1.35rem]">As questões ainda não estão prontas para este bloco.</CardTitle>
              <p className="mt-3 text-sm leading-7 text-silver">Estude o resumo do bloco primeiro.</p>
            </Card>
          )}
        </div>
      ) : null}
    </section>
  );
}

export function StudyBlockDetailReadOnlyClient({ blockId }: { blockId: string }) {
  const [state, setState] = useState<BlockDetailState>({ status: "loading" });
  const [questionsState, setQuestionsState] = useState<QuestionsState>({ status: "loading" });

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

    void fetchStudyBlockQuestions(blockId).then((result) => {
      if (!active) {
        return;
      }
      if (result.ok) {
        setQuestionsState({
          status: result.data.question_status === "ready" ? "ready" : "needs_review",
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
            title: "Dados reais",
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
            title: state.status === "auth_required" ? "Entre para continuar" : "Dados reais não carregados agora",
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
            title: "Dados reais",
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
          title: "Dados reais",
          detail: "Esta tela mostra apenas uma orientação de leitura para este bloco."
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

      <QuestionsCard state={questionsState} />
    </div>
  );
}
