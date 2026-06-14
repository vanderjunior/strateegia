"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { StudySessionWorkspaceViewModel } from "@/lib/api/types";
import type {
  BackendNextReviewBlock,
  BackendNextStudySession,
  BackendStudyBlocks,
  StudyProgressSummary
} from "@/lib/api/types";
import {
  fetchNextReviewBlock,
  fetchNextStudySession,
  fetchStudyBlocks,
  fetchStudyProgressSummary
} from "@/lib/api/study";
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

type ProgressSummaryState = "loading" | "ready" | "not_ready" | "auth_required" | "unavailable";
type StudyBlockItem = BackendStudyBlocks["items"][number];

function reviewBasisLabel(basis: BackendNextReviewBlock["basis"]) {
  if (basis === "study_blocks") {
    return "Baseada em blocos disponíveis";
  }
  if (basis === "studied_materials") {
    return "Baseada em materiais estudados";
  }
  return "Baseada em materiais preparados";
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

function studyBlockHref(block: StudyBlockItem) {
  return block.actions[0]?.href ?? `/study/blocks/${encodeURIComponent(block.block_id)}`;
}

function studyBlockActionLabel(block: StudyBlockItem) {
  return block.actions[0]?.label ?? "Estudar bloco";
}

function StudyNextActionCard({ block }: { block: StudyBlockItem }) {
  return (
    <Card className="border-[rgba(201,169,110,0.22)] bg-[linear-gradient(135deg,rgba(201,169,110,0.13),rgba(255,255,255,0.035))]">
      <div className="section-kicker">próximo passo</div>
      <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div className="min-w-0">
          <CardTitle className="break-words text-[1.85rem] leading-[1.02] text-ink">
            Continue seus estudos
          </CardTitle>
          <p className="mt-3 max-w-3xl break-words text-lg leading-7 text-ink">{block.title}</p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs uppercase tracking-[0.16em] text-muted">
            <span>{block.material_title}</span>
            {block.topic_label || block.subtopic_label ? (
              <span>{[block.topic_label, block.subtopic_label].filter(Boolean).join(" · ")}</span>
            ) : null}
            <span>{block.estimated_minutes} min</span>
          </div>
        </div>
        <WorkspaceLink href={studyBlockHref(block)}>Continuar estudando</WorkspaceLink>
      </div>
    </Card>
  );
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
      <Card className="border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.018)] p-5">
        <div className="section-kicker">revisão acumulada</div>
        <CardTitle className="mt-3 break-words text-[1.35rem] leading-[1.08]">Revisão acumulada</CardTitle>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-silver">{safeMessage}</p>
      </Card>
    );
  }

  if (state === "partial") {
    return (
      <Card className="border-[rgba(201,169,110,0.12)] bg-[rgba(255,255,255,0.018)] p-5">
        <div className="section-kicker">revisão acumulada</div>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <CardTitle className="break-words text-[1.35rem] leading-[1.08]">Revisão acumulada</CardTitle>
            <p className="mt-2 text-sm leading-6 text-silver">Revisão acumulada em preparação.</p>
            <p className="mt-1 text-sm leading-6 text-silver">Prepare mais materiais para uma revisão mais completa.</p>
          </div>
          <Badge className={productStatusClass("Conferir")}>Em preparação</Badge>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">materiais preparados</p>
            <p className="mt-1 text-xl text-ink">{review.materials_count}</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">blocos disponíveis</p>
            <p className="mt-1 text-xl text-ink">{review.blocks_count}</p>
          </div>
          <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
            <p className="mt-1 text-xl text-ink">{review.estimated_minutes} min</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="border-[rgba(201,169,110,0.12)] bg-[rgba(255,255,255,0.018)] p-5">
      <div className="section-kicker">revisão acumulada</div>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-3xl">
          <CardTitle className="break-words text-[1.35rem] leading-[1.08]">Revisão acumulada</CardTitle>
          <p className="mt-2 text-sm leading-6 text-silver">Retome pontos importantes antes de avançar.</p>
        </div>
        <Badge className={productStatusClass(state === "ready" ? "Pronto" : "Conferir")}>
          {state === "ready" ? "Disponível para consulta" : "Precisa de conferência"}
        </Badge>
      </div>

      <div className="mt-4 rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
        <p className="break-words text-sm text-ink">{review.title || "Revisão acumulada"}</p>
        <p className="mt-1 text-sm leading-6 text-silver">{reviewBasisLabel(review.basis)}</p>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">materiais preparados</p>
          <p className="mt-1 text-xl text-ink">{review.materials_count}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">blocos disponíveis</p>
          <p className="mt-1 text-xl text-ink">{review.blocks_count}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">tempo estimado</p>
          <p className="mt-1 text-xl text-ink">{review.estimated_minutes} min</p>
        </div>
      </div>

      {review.summary.items.length ? (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">pontos para revisar</p>
          <div className="mt-2 grid gap-2">
            {review.summary.items.slice(0, 2).map((item) => (
              <div
                key={`${item.title}-${item.message}`}
                className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3"
              >
                <p className="break-words text-sm text-ink">{item.title}</p>
                {item.topic_label || item.subtopic_label ? (
                  <p className="mt-1 text-xs uppercase tracking-[0.16em] text-muted">
                    {[item.topic_label, item.subtopic_label].filter(Boolean).join(" · ")}
                  </p>
                ) : null}
                <p className="mt-1 text-sm leading-6 text-silver">{item.message}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 lg:grid-cols-2">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">questões de revisão</p>
          <p className="mt-1 text-sm leading-6 text-silver">
            {questionsReadinessLabel(review.questions.status)}
            {review.questions.items_count > 0 ? ` · ${review.questions.items_count} itens` : ""}
          </p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">reforço sugerido</p>
          <p className="mt-1 text-sm leading-6 text-silver">
            {review.reinforcement.weak_topics_count} pontos para revisar
          </p>
          {review.reinforcement.items.length ? (
            <ul className="mt-2 space-y-1 text-sm leading-6 text-silver">
              {review.reinforcement.items.slice(0, 1).map((item) => (
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

      <p className="mt-4 text-sm leading-6 text-[rgba(232,238,242,0.68)]">
        Revisão de apoio; continue pelos blocos.
      </p>
    </Card>
  );
}

function progressReviewBasisMessage(basis: StudyProgressSummary["review_basis"]) {
  if (basis === "prepared_materials") {
    return "Revisão sugerida com base em materiais preparados.";
  }
  if (basis === "studied_materials") {
    return "Revisão sugerida com base em materiais estudados.";
  }
  return null;
}

function ProgressSummaryCard({
  summary,
  state,
  showReviewBasis = true
}: {
  summary: StudyProgressSummary | null;
  state: ProgressSummaryState;
  showReviewBasis?: boolean;
}) {
  if (state === "loading") {
    return null;
  }

  if (!summary || state === "auth_required" || state === "unavailable" || state === "not_ready") {
    const message =
      state === "auth_required"
        ? "Entre para acompanhar seu estudo."
        : state === "unavailable"
          ? "Não foi possível carregar seu acompanhamento agora."
          : "Seu acompanhamento aparecerá quando houver ações registradas.";

    return (
      <Card className="border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.018)] p-5">
        <div className="section-kicker">acompanhamento</div>
        <CardTitle className="mt-3 break-words text-[1.25rem] leading-[1.08]">Acompanhamento do estudo</CardTitle>
        <p className="mt-2 text-sm leading-6 text-silver">{message}</p>
      </Card>
    );
  }

  const basisMessage = showReviewBasis ? progressReviewBasisMessage(summary.review_basis) : null;

  return (
    <Card className="border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.018)] p-5">
      <div className="section-kicker">acompanhamento</div>
      <CardTitle className="mt-3 break-words text-[1.25rem] leading-[1.08]">Acompanhamento do estudo</CardTitle>
      <p className="mt-2 text-sm leading-6 text-silver">Ações registradas por você.</p>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Materiais preparados</p>
          <p className="mt-1 text-xl text-ink">{summary.prepared_materials_count}</p>
        </div>
        {summary.studied_materials_count > 0 ? (
          <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Materiais estudados</p>
            <p className="mt-1 text-xl text-ink">{summary.studied_materials_count}</p>
          </div>
        ) : null}
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Blocos marcados como estudados</p>
          <p className="mt-1 text-xl text-ink">{summary.studied_blocks_count}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Questões revisadas nesta etapa</p>
          <p className="mt-1 text-xl text-ink">{summary.reviewed_questions_count}</p>
        </div>
      </div>

      {summary.opened_blocks_count > 0 || summary.weak_topics_count > 0 ? (
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {summary.opened_blocks_count > 0 ? (
            <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Blocos abertos</p>
              <p className="mt-1 text-xl text-ink">{summary.opened_blocks_count}</p>
            </div>
          ) : null}
          {summary.weak_topics_count > 0 ? (
            <div className="rounded-2xl border border-[rgba(168,184,196,0.08)] bg-[rgba(255,255,255,0.025)] p-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Pontos para reforço</p>
              <p className="mt-1 text-xl text-ink">{summary.weak_topics_count}</p>
            </div>
          ) : null}
        </div>
      ) : null}

      {basisMessage ? <p className="mt-3 text-sm leading-6 text-silver">{basisMessage}</p> : null}
      <p className="mt-3 text-sm leading-6 text-[rgba(232,238,242,0.68)]">
        Os registros não concluem materiais automaticamente.
      </p>
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
  const [progressSummary, setProgressSummary] = useState<StudyProgressSummary | null>(null);
  const [progressSummaryState, setProgressSummaryState] = useState<ProgressSummaryState>("loading");

  useEffect(() => {
    let active = true;
    void Promise.all([
      loadStudySessionWorkspaceViewModel(),
      loadRealUserStudyReadiness(),
      fetchStudyBlocks(),
      fetchNextStudySession(),
      fetchNextReviewBlock(),
      fetchStudyProgressSummary()
    ]).then(
      ([nextViewModel, nextReadiness, blocksResult, nextSessionResult, nextReviewResult, progressResult]) => {
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
          if (progressResult.ok) {
            setProgressSummary(progressResult.data);
            setProgressSummaryState(progressResult.data.progress_status === "not_ready" ? "not_ready" : "ready");
          } else if (
            progressResult.error.code === "auth_required" ||
            progressResult.error.code === "unauthorized"
          ) {
            setProgressSummary(null);
            setProgressSummaryState("auth_required");
          } else if (progressResult.error.code === "not_ready") {
            setProgressSummary(null);
            setProgressSummaryState("not_ready");
          } else {
            setProgressSummary(null);
            setProgressSummaryState("unavailable");
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
      : "Baseado nos materiais preparados.";
    const continuationBlock = studyBlocks.items[0];
    const shouldShowProgressBasis =
      nextReviewBlockState !== "ready" && nextReviewBlockState !== "needs_review";

    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudo guiado"
          subtitle="Comece pelos blocos preparados a partir dos seus materiais."
          connection={{
            state: "connected",
            source: "backend",
            title: "Caminho disponível",
            detail: scopeCopy
          }}
        />

        <StudyNextActionCard block={continuationBlock} />

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="section-kicker">caminho sugerido</div>
              <h2 className="mt-3 break-words font-serif text-[2rem] text-ink">Seu caminho de estudo</h2>
              <p className="mt-2 text-sm leading-6 text-silver">{scopeCopy}</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.16em] text-muted">
              <span>{studyBlocks.blocks_count} blocos</span>
              <span>{studyBlocks.estimated_minutes} min</span>
              <Badge className={productStatusClass(studyBlocks.blocks_status === "ready" ? "Pronto" : "Conferir")}>
                {studyBlocks.blocks_status === "ready" ? "Pronto para estudo" : "Precisa de conferência"}
              </Badge>
            </div>
          </div>
          <div className="grid gap-3">
            {studyBlocks.items.map((block) => {
              const statusLabel =
                block.status === "ready"
                  ? "Pronto para estudo"
                  : block.status === "not_ready"
                    ? "Ainda não pronto"
                    : "Precisa de conferência";
              return (
                <Card key={block.block_id} className="min-w-0 border-[rgba(168,184,196,0.10)] p-5">
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                    <div className="min-w-0 max-w-3xl">
                      <div className="section-kicker">bloco de estudo</div>
                      <CardTitle className="mt-3 break-words text-[1.35rem] leading-[1.08] sm:text-[1.5rem]">
                        {block.title}
                      </CardTitle>
                      {block.topic_label || block.subtopic_label ? (
                        <p className="mt-2 text-sm leading-6 text-silver">
                          {[block.topic_label, block.subtopic_label].filter(Boolean).join(" · ")}
                        </p>
                      ) : null}
                      <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.16em] text-muted">
                        <span>{block.material_title}</span>
                        <span>{block.sections_count} seções</span>
                        <span>{block.estimated_minutes} min</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 lg:justify-end">
                      <Badge className={productStatusClass(statusLabel)}>{statusLabel}</Badge>
                      <WorkspaceLink href={studyBlockHref(block)}>{studyBlockActionLabel(block)}</WorkspaceLink>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </section>

        <ReviewCandidateCard review={nextReviewBlock} state={nextReviewBlockState} compact />

        <ProgressSummaryCard
          summary={progressSummary}
          state={progressSummaryState}
          showReviewBasis={shouldShowProgressBasis}
        />
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
            title: "Estudo disponível",
            detail: "Orientação montada a partir de um material preparado."
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

        <ProgressSummaryCard summary={progressSummary} state={progressSummaryState} />
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
                  title: "Não foi possível carregar agora",
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

        {nextReviewBlockState === "partial" ? (
          <ReviewCandidateCard review={nextReviewBlock} state={nextReviewBlockState} compact />
        ) : null}
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
                ? "Edital recebido. Analise o edital e depois envie materiais de estudo."
                : readiness.editalAnalysisState === "analysis_unavailable"
                  ? "Não foi possível carregar a análise agora. Tente novamente em instantes."
                  : "Envie um edital para orientar o caminho. Depois, envie materiais de estudo."}
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
        subtitle="Orientações sugeridas a partir do perfil PSCPP, materiais e pontos a revisar."
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
          <div className="section-kicker">pontos a revisar</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Pontos conectados</CardTitle>
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
