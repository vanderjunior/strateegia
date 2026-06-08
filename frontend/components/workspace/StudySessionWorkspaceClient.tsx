"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { StudySessionWorkspaceViewModel } from "@/lib/api/types";
import type { BackendNextReviewBlock, BackendNextStudySession, BackendStudyBlocks } from "@/lib/api/types";
import { fetchNextReviewBlock, fetchNextStudySession, fetchStudyBlocks } from "@/lib/api/study";
import {
  buildMockStudySessionWorkspaceViewModel,
  loadStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import {
  buildDefaultRealUserStudyReadiness,
  loadRealUserStudyReadiness,
  type RealUserStudyReadiness
} from "@/lib/adapters/real-user-state";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { StudySessionMetaRow } from "@/components/workspace/StudySessionShared";
import Link from "next/link";

type ReviewCandidateState =
  | "loading"
  | "ready"
  | "needs_review"
  | "partial"
  | "not_ready"
  | "auth_required"
  | "unavailable";

function reviewBasisLabel(basis: BackendNextReviewBlock["basis"]) {
  return basis === "study_blocks" ? "Baseada em blocos disponíveis" : "Baseada em materiais preparados";
}

function questionsReadinessLabel(status: BackendNextReviewBlock["questions"]["status"]) {
  if (status === "ready") {
    return "Questões de revisão disponíveis";
  }
  if (status === "needs_review") {
    return "Questões de revisão em conferência";
  }
  return "Questões de revisão ainda não disponíveis";
}

function ReviewCandidateCard({
  review,
  state,
  compact = false
}: {
  review: BackendNextReviewBlock | null;
  state: ReviewCandidateState;
  compact?: boolean;
}) {
  if (state === "loading") {
    return null;
  }

  const safeMessage =
    state === "auth_required"
      ? "Entre para ver sua revisão acumulada."
      : state === "unavailable"
        ? "Não foi possível carregar a revisão agora."
        : "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.";

  if (!review || state === "not_ready" || state === "auth_required" || state === "unavailable") {
    if (compact && state === "not_ready") {
      return null;
    }
    return (
      <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
        <div className="section-kicker">revisão acumulada</div>
        <CardTitle className="mt-4 break-words text-[1.55rem] leading-[1.05]">
          Revisão acumulada sugerida
        </CardTitle>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-silver">{safeMessage}</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          <WorkspaceLink href="/study">Continuar estudando</WorkspaceLink>
        </div>
      </Card>
    );
  }

  if (state === "partial") {
    return (
      <Card className="border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
        <div className="section-kicker">revisão acumulada</div>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <CardTitle className="break-words text-[1.65rem] leading-[1.05]">
              Revisão acumulada em preparação.
            </CardTitle>
            <p className="mt-3 text-sm leading-7 text-silver">
              Prepare mais materiais para uma revisão mais completa.
            </p>
          </div>
          <Badge className={productStatusClass("Conferir")}>Em preparação</Badge>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">materiais preparados</p>
            <p className="mt-2 text-2xl text-ink">{review.materials_count}</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">blocos disponíveis</p>
            <p className="mt-2 text-2xl text-ink">{review.blocks_count}</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
            <p className="mt-2 text-2xl text-ink">{review.estimated_minutes} min</p>
          </div>
        </div>
        <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
          Esta revisão ainda não altera seu progresso. Ela não substitui o estudo dos blocos.
        </p>
      </Card>
    );
  }

  return (
    <Card className="border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
      <div className="section-kicker">revisão acumulada</div>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-3xl">
          <CardTitle className="break-words text-[1.65rem] leading-[1.05]">
            Revisão acumulada sugerida
          </CardTitle>
          <p className="mt-3 text-sm leading-7 text-silver">
            Use esta revisão para retomar pontos dos materiais preparados.
          </p>
        </div>
        <Badge className={productStatusClass(state === "ready" ? "Pronto" : "Conferir")}>
          {state === "ready" ? "Disponível para consulta" : "Precisa de conferência"}
        </Badge>
      </div>

      <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
        <p className="break-words text-sm text-ink">{review.title || "Revisão acumulada"}</p>
        <p className="mt-2 text-sm leading-7 text-silver">{reviewBasisLabel(review.basis)}</p>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">materiais preparados</p>
          <p className="mt-2 text-2xl text-ink">{review.materials_count}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">blocos disponíveis</p>
          <p className="mt-2 text-2xl text-ink">{review.blocks_count}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
          <p className="mt-2 text-2xl text-ink">{review.estimated_minutes} min</p>
        </div>
      </div>

      {review.summary.items.length ? (
        <div className="mt-5">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">pontos para revisar</p>
          <div className="mt-3 grid gap-3">
            {review.summary.items.slice(0, 3).map((item) => (
              <div
                key={`${item.title}-${item.message}`}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <p className="break-words text-sm text-ink">{item.title}</p>
                {item.topic_label || item.subtopic_label ? (
                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-muted">
                    {[item.topic_label, item.subtopic_label].filter(Boolean).join(" · ")}
                  </p>
                ) : null}
                <p className="mt-2 text-sm leading-7 text-silver">{item.message}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">questões de revisão</p>
          <p className="mt-2 text-sm leading-7 text-silver">
            {questionsReadinessLabel(review.questions.status)}
            {review.questions.items_count > 0 ? ` · ${review.questions.items_count} itens` : ""}
          </p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">reforço sugerido</p>
          <p className="mt-2 text-sm leading-7 text-silver">
            {review.reinforcement.weak_topics_count} pontos para revisar
          </p>
          {review.reinforcement.items.length ? (
            <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
              {review.reinforcement.items.slice(0, 2).map((item) => (
                <li key={`${item.topic_label ?? "tema"}-${item.message}`}>
                  {item.topic_label || item.subtopic_label ? (
                    <span className="text-ink">
                      {[item.topic_label, item.subtopic_label].filter(Boolean).join(" · ")}:{" "}
                    </span>
                  ) : null}
                  {item.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
        Esta revisão ainda não altera seu progresso. Ela não substitui o estudo dos blocos.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
        <WorkspaceLink href="/study">Continuar estudando</WorkspaceLink>
      </div>
    </Card>
  );
}

export function StudySessionWorkspaceClient() {
  const [viewModel, setViewModel] = useState<StudySessionWorkspaceViewModel>(
    buildMockStudySessionWorkspaceViewModel()
  );
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());
  const [studyBlocks, setStudyBlocks] = useState<BackendStudyBlocks | null>(null);
  const [studyBlocksState, setStudyBlocksState] = useState<
    "loading" | "ready" | "not_ready" | "auth_required" | "unavailable"
  >("loading");
  const [nextStudySession, setNextStudySession] = useState<BackendNextStudySession | null>(null);
  const [nextStudySessionState, setNextStudySessionState] = useState<
    "loading" | "ready" | "not_ready" | "auth_required" | "offline" | "unsupported"
  >("loading");
  const [nextReviewBlock, setNextReviewBlock] = useState<BackendNextReviewBlock | null>(null);
  const [nextReviewBlockState, setNextReviewBlockState] = useState<ReviewCandidateState>("loading");

  useEffect(() => {
    let active = true;
    void Promise.all([
      loadStudySessionWorkspaceViewModel(),
      loadRealUserStudyReadiness(),
      fetchStudyBlocks(),
      fetchNextStudySession(),
      fetchNextReviewBlock()
    ]).then(
      ([nextViewModel, nextReadiness, blocksResult, nextSessionResult, nextReviewResult]) => {
        if (active) {
          setViewModel(nextViewModel);
          setReadiness(nextReadiness);
          if (blocksResult.ok) {
            setStudyBlocks(blocksResult.data);
            setStudyBlocksState(blocksResult.data.items.length ? "ready" : "not_ready");
          } else if (blocksResult.error.code === "not_ready") {
            setStudyBlocks(null);
            setStudyBlocksState("not_ready");
          } else if (blocksResult.error.code === "auth_required" || blocksResult.error.code === "unauthorized") {
            setStudyBlocks(null);
            setStudyBlocksState("auth_required");
          } else {
            setStudyBlocks(null);
            setStudyBlocksState("unavailable");
          }
          if (nextSessionResult.ok) {
            setNextStudySession(nextSessionResult.data);
            setNextStudySessionState(
              nextSessionResult.data.session_status === "not_ready" ? "not_ready" : "ready"
            );
          } else if (nextSessionResult.error.code === "auth_required" || nextSessionResult.error.code === "unauthorized") {
            setNextStudySession(null);
            setNextStudySessionState("auth_required");
          } else if (nextSessionResult.source === "offline") {
            setNextStudySession(null);
            setNextStudySessionState("offline");
          } else if (nextSessionResult.source === "unsupported") {
            setNextStudySession(null);
            setNextStudySessionState("unsupported");
          } else {
            setNextStudySession(null);
            setNextStudySessionState("not_ready");
          }
          if (nextReviewResult.ok) {
            setNextReviewBlock(nextReviewResult.data);
            setNextReviewBlockState(nextReviewResult.data.review_status);
          } else if (nextReviewResult.error.code === "not_ready") {
            setNextReviewBlock(null);
            setNextReviewBlockState("not_ready");
          } else if (
            nextReviewResult.error.code === "auth_required" ||
            nextReviewResult.error.code === "unauthorized"
          ) {
            setNextReviewBlock(null);
            setNextReviewBlockState("auth_required");
          } else {
            setNextReviewBlock(null);
            setNextReviewBlockState("unavailable");
          }
        }
      }
    );
    return () => {
      active = false;
    };
  }, []);

  const nextSession = useMemo(
    () => viewModel.sessions.find((item) => item.id === viewModel.nextSuggestedSessionId) ?? viewModel.sessions[0],
    [viewModel]
  );
  const usesDemoMaterials = viewModel.connection.source === "mock";

  if (studyBlocks && studyBlocks.items.length) {
    const connectedToEdital = studyBlocks.scope_status === "connected_to_edital";
    const scopeCopy = connectedToEdital
      ? "Conectado ao edital."
      : "Baseado nos materiais preparados. Ainda não conectado completamente ao edital.";

    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Seu caminho de estudo"
          subtitle="Comece pelos blocos preparados a partir dos seus materiais."
          connection={{
            state: "connected",
            source: "backend",
            title: "Dados reais",
            detail: scopeCopy
          }}
        />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">blocos preparados</div>
          <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-3xl">
              <CardTitle className="break-words text-[1.95rem] leading-[1.02]">
                {connectedToEdital ? "Blocos conectados ao edital" : "Blocos baseados nos materiais"}
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{scopeCopy}</p>
            </div>
            <Badge className={productStatusClass(studyBlocks.blocks_status === "ready" ? "Pronto" : "Conferir")}>
              {studyBlocks.blocks_status === "ready" ? "Pronto para estudo" : "Precisa de conferência"}
            </Badge>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">blocos</p>
              <p className="mt-2 text-2xl text-ink">{studyBlocks.blocks_count}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
              <p className="mt-2 text-2xl text-ink">{studyBlocks.estimated_minutes} min</p>
            </div>
          </div>

          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            Use estes blocos como orientação de leitura. Nenhuma ação adicional é necessária nesta tela.
          </p>
        </Card>

        <ReviewCandidateCard review={nextReviewBlock} state={nextReviewBlockState} compact />

        <section className="space-y-4">
          <div>
            <div className="section-kicker">caminho sugerido</div>
            <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">O que estudar agora</h2>
          </div>
          <div className="grid gap-4 2xl:grid-cols-2">
            {studyBlocks.items.map((block) => {
              const statusLabel =
                block.status === "ready"
                  ? "Pronto para estudo"
                  : block.status === "not_ready"
                    ? "Ainda não pronto"
                    : "Precisa de conferência";
              const actions = block.actions.length
                ? block.actions
                : [{ label: "Ver material", href: `/materials/${block.material_id}` }];
              return (
                <Card key={block.block_id} className="h-full min-w-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 max-w-3xl">
                      <div className="section-kicker">bloco de estudo</div>
                      <CardTitle className="mt-4 break-words text-[1.55rem] leading-[1.05] sm:text-[1.7rem]">
                        {block.title}
                      </CardTitle>
                    </div>
                    <Badge className={productStatusClass(statusLabel)}>{statusLabel}</Badge>
                  </div>

                  {block.topic_label || block.subtopic_label ? (
                    <p className="mt-4 text-sm leading-7 text-silver">
                      {[block.topic_label, block.subtopic_label].filter(Boolean).join(" · ")}
                    </p>
                  ) : null}

                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted">material</p>
                      <p className="mt-2 break-words text-sm text-ink">{block.material_title}</p>
                    </div>
                    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted">seções</p>
                      <p className="mt-2 text-lg text-ink">{block.sections_count}</p>
                    </div>
                    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo</p>
                      <p className="mt-2 text-lg text-ink">{block.estimated_minutes} min</p>
                    </div>
                  </div>

                  <div className="mt-6 flex flex-wrap gap-3">
                    {actions.map((action) => (
                      <WorkspaceLink key={`${block.block_id}-${action.label}-${action.href}`} href={action.href}>
                        {action.label}
                      </WorkspaceLink>
                    ))}
                  </div>
                </Card>
              );
            })}
          </div>
        </section>
      </div>
    );
  }

  if (nextStudySession?.session_status === "ready" || nextStudySession?.session_status === "needs_review") {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudo de agora"
          subtitle="Comece por este material preparado."
          connection={{
            state: "connected",
            source: "backend",
            title: "Dados reais",
            detail: "Sessão de estudo montada a partir de um material preparado."
          }}
        />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">material preparado</div>
          <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-3xl">
              <CardTitle className="break-words text-[1.95rem] leading-[1.02]">
                {nextStudySession.material_title}
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{nextStudySession.message}</p>
            </div>
            <Badge className={productStatusClass(nextStudySession.session_status === "ready" ? "Pronto" : "Conferir")}>
              {nextStudySession.session_status === "ready" ? "Pronto para estudo" : "Precisa de conferência"}
            </Badge>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
              <p className="mt-2 text-2xl text-ink">{nextStudySession.estimated_minutes} min</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">seções</p>
              <p className="mt-2 text-2xl text-ink">{nextStudySession.sections_count}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">modo</p>
              <p className="mt-2 text-lg text-ink">Leitura orientada</p>
            </div>
          </div>

          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            Use esta orientação para organizar a leitura deste material.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            {nextStudySession.next_actions.map((action) => (
              <WorkspaceLink key={`${action.label}-${action.href}`} href={action.href}>
                {action.label}
              </WorkspaceLink>
            ))}
          </div>
        </Card>

        <section className="space-y-4">
          <div>
            <div className="section-kicker">resumo do material</div>
            <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">O que estudar agora</h2>
          </div>
          <div className="grid gap-4">
            {nextStudySession.items.map((item) => (
              <Card key={item.section_id} className="min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <CardTitle className="break-words text-[1.45rem] leading-[1.05]">
                    {item.title}
                  </CardTitle>
                  <Badge className={productStatusClass(item.status === "ready" ? "Pronto" : "Conferir")}>
                    {item.status === "ready" ? "Pronto" : "Conferir"}
                  </Badge>
                </div>
                <p className="mt-4 text-sm leading-7 text-silver">{item.summary}</p>
                {item.key_points.length ? (
                  <div className="mt-5">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted">pontos principais</p>
                    <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
                      {item.key_points.map((point) => (
                        <li key={point}>• {point}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <p className="mt-5 text-xs uppercase tracking-[0.18em] text-muted">
                  {item.estimated_minutes} min de leitura estimada
                </p>
              </Card>
            ))}
          </div>
        </section>

        <ReviewCandidateCard review={nextReviewBlock} state={nextReviewBlockState} compact />
      </div>
    );
  }

  if (studyBlocksState !== "loading" && nextStudySessionState !== "loading") {
    const title =
      studyBlocksState === "auth_required" || nextStudySessionState === "auth_required"
        ? "Entre para ver sua sessão de estudo."
        : "Seu estudo ainda não está pronto.";
    const detail =
      studyBlocksState === "auth_required" || nextStudySessionState === "auth_required"
        ? "Entre para carregar seus materiais preparados."
        : nextStudySessionState === "offline" && studyBlocksState === "unavailable"
          ? "Não foi possível carregar a sessão agora."
          : "Envie e prepare um material de estudo para começar.";

    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudo guiado"
          subtitle="O caminho aparece quando houver material de estudo preparado."
          connection={
            nextStudySessionState === "offline" && studyBlocksState === "unavailable"
              ? {
                  state: "offline",
                  source: "offline",
                  title: "Dados reais não carregados agora",
                  detail
                }
              : readiness.connection
          }
        />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">próximo passo</div>
          <CardTitle className="mt-5 max-w-3xl break-words text-[1.95rem] leading-[1.02]">
            {title}
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">{detail}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            {studyBlocksState === "auth_required" || nextStudySessionState === "auth_required" ? (
              <WorkspaceLink href="/login">Entrar</WorkspaceLink>
            ) : (
              <WorkspaceLink href="/materials/upload">Enviar material</WorkspaceLink>
            )}
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          </div>
        </Card>

        <ReviewCandidateCard review={nextReviewBlock} state={nextReviewBlockState} />
      </div>
    );
  }

  if (!readiness.canShowConcreteStudyPlan) {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudo guiado"
          subtitle="O caminho concreto será montado quando houver um edital analisado na sua sessão."
          connection={readiness.connection}
        />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">próximo passo</div>
          <CardTitle className="mt-5 max-w-3xl break-words text-[1.95rem] leading-[1.02]">
            Seu estudo guiado ainda não foi montado.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            {readiness.editalAnalysisState === "analysis_needs_review"
              ? "Edital analisado, mas precisa de conferência antes de orientar o estudo."
              : readiness.editalAnalysisState === "edital_uploaded_not_analyzed"
                ? "Edital recebido. A análise ainda não foi executada nesta versão. Depois, envie materiais de estudo para comparar cobertura quando essa análise estiver disponível."
                : readiness.editalAnalysisState === "analysis_unavailable"
                  ? "Análise indisponível agora. Quando os dados reais estiverem disponíveis, o estudo poderá seguir o estado do edital."
                  : "Envie um edital para orientar o caminho. Depois, envie materiais de estudo para comparar cobertura quando essa análise estiver disponível."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          </div>
        </Card>

        {nextSession ? (
          <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
            <div className="section-kicker">exemplo de orientação</div>
            <CardTitle className="mt-5 break-words text-[1.75rem] leading-[1.04]">
              Ainda não baseado no seu edital
            </CardTitle>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
              Você pode consultar uma orientação de demonstração para entender o formato, mas ela não representa seu
              plano personalizado.
            </p>
            <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <p className="break-words text-sm text-ink">{nextSession.title}</p>
              <p className="mt-2 text-sm leading-7 text-silver">{nextSession.objective}</p>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href={`/study/session/${nextSession.id}`}>Ver exemplo</WorkspaceLink>
              <WorkspaceLink href="/pscpp">Ver referência PSCPP</WorkspaceLink>
            </div>
          </Card>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="estudo"
        title="Orientação de estudo"
        subtitle="Sessões sugeridas a partir do perfil PSCPP, materiais e gaps identificados."
        connection={viewModel.connection}
      />

      <div className="flex flex-wrap gap-2">
        <Badge className={productStatusClass("Guia flexível")}>Guia flexível</Badge>
        <Badge className={productStatusClass("Somente leitura")}>Somente leitura</Badge>
      </div>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      {nextSession ? (
        <Card className="min-w-0 border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">próxima sessão sugerida</div>
          <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-3xl">
              <CardTitle className="break-words text-[1.95rem] leading-[1.02]">
                {nextSession.title}
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{nextSession.objective}</p>
            </div>
            <WorkspaceLink href={`/study/session/${nextSession.id}`}>Abrir orientação</WorkspaceLink>
          </div>
          <div className="mt-5">
            <StudySessionMetaRow
              durationLabel={nextSession.durationLabel}
              relatedMaterialsCount={nextSession.relatedMaterialsCount}
              relatedGapsCount={nextSession.relatedGapsCount}
              statusLabel={nextSession.statusLabel}
            />
          </div>
          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            {nextSession.priorityBlockTitle}
          </p>
        </Card>
      ) : null}

      <section className="space-y-4">
        <div>
          <div className="section-kicker">orientações sugeridas</div>
          <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">Orientações disponíveis</h2>
        </div>
        {viewModel.sessions.length ? (
          <div className="grid gap-4 2xl:grid-cols-2">
            {viewModel.sessions.map((session) => (
              <Card key={session.id} className="h-full min-w-0">
                <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
                  sessão {session.sessionNumber}
                </div>
                <CardTitle className="mt-5 break-words text-[1.55rem] leading-[1.05] sm:text-[1.7rem]">
                  {session.title}
                </CardTitle>
                <p className="mt-4 text-sm leading-7 text-silver">{session.objective}</p>
                <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                  {session.priorityBlockTitle}
                </p>
                <div className="mt-5">
                  <StudySessionMetaRow
                    durationLabel={session.durationLabel}
                    relatedMaterialsCount={session.relatedMaterialsCount}
                    relatedGapsCount={session.relatedGapsCount}
                    statusLabel={session.statusLabel}
                  />
                </div>
                <p className="mt-5 text-sm leading-7 text-silver">{session.note}</p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <WorkspaceLink href={`/study/session/${session.id}`}>Abrir orientação</WorkspaceLink>
                  <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
            <CardTitle className="text-[1.7rem] leading-[1.05]">Nenhuma sessão sugerida para exibir agora</CardTitle>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
              Consulte o ciclo PSCPP para revisar o caminho de estudo. O guia continua disponível apenas como
              orientação.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
              <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
            </div>
          </Card>
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="h-full min-w-0">
          <div className="section-kicker">gaps que orientam o estudo</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Gaps conectados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.highlightedGaps.map((gap) => (
              <div
                key={gap.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <p className="break-words text-sm text-ink">{gap.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{gap.detail}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">materiais para começar</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Materiais relacionados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.starterMaterials.map((material) => (
              <div
                key={material.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-ink">{material.title}</p>
                    <p className="mt-2 text-sm leading-7 text-silver">{material.typeLabel}</p>
                  </div>
                  <Badge className={productStatusClass(material.statusLabel)}>{material.statusLabel}</Badge>
                </div>
                <div className="mt-4">
                  <Link
                    href={usesDemoMaterials ? "/materials" : material.linkHref}
                    className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-4 py-2 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                  >
                    {usesDemoMaterials ? "Exemplo de material" : "Ver material"}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
