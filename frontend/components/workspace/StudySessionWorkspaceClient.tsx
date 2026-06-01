"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { StudySessionWorkspaceViewModel } from "@/lib/api/types";
import type { BackendNextStudySession } from "@/lib/api/types";
import { fetchNextStudySession } from "@/lib/api/study";
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

export function StudySessionWorkspaceClient() {
  const [viewModel, setViewModel] = useState<StudySessionWorkspaceViewModel>(
    buildMockStudySessionWorkspaceViewModel()
  );
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());
  const [nextStudySession, setNextStudySession] = useState<BackendNextStudySession | null>(null);
  const [nextStudySessionState, setNextStudySessionState] = useState<
    "loading" | "ready" | "not_ready" | "auth_required" | "offline" | "unsupported"
  >("loading");

  useEffect(() => {
    let active = true;
    void Promise.all([
      loadStudySessionWorkspaceViewModel(),
      loadRealUserStudyReadiness(),
      fetchNextStudySession()
    ]).then(
      ([nextViewModel, nextReadiness, nextSessionResult]) => {
        if (active) {
          setViewModel(nextViewModel);
          setReadiness(nextReadiness);
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
            Esta sessão ainda não altera seu progresso. Questões e revisão serão adicionadas depois.
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
      </div>
    );
  }

  if (nextStudySessionState !== "loading") {
    const title =
      nextStudySessionState === "auth_required"
        ? "Entre para ver sua sessão de estudo."
        : "Seu estudo ainda não está pronto.";
    const detail =
      nextStudySessionState === "auth_required"
        ? "Entre para carregar seus materiais preparados."
        : nextStudySessionState === "offline"
          ? "Não foi possível carregar a sessão agora."
          : "Envie e prepare um material de estudo para começar.";

    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="estudo"
          title="Estudo guiado"
          subtitle="A próxima sessão aparece quando houver material de estudo preparado."
          connection={
            nextStudySessionState === "offline"
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
            {nextStudySessionState === "auth_required" ? (
              <WorkspaceLink href="/login">Entrar</WorkspaceLink>
            ) : (
              <WorkspaceLink href="/materials/upload">Enviar material</WorkspaceLink>
            )}
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          </div>
        </Card>
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
        <Badge className={productStatusClass("Não altera seu progresso")}>Não altera seu progresso</Badge>
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
              Consulte o ciclo PSCPP para revisar o caminho de estudo. O guia continua disponível sem criar agenda
              automaticamente e sem alterar seu progresso.
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
