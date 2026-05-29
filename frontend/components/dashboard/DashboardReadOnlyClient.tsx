"use client";

import { useEffect, useState } from "react";

import { BackendConnectionBanner } from "@/components/dashboard/BackendConnectionBanner";
import { CapabilityStatusPanel } from "@/components/dashboard/CapabilityStatusPanel";
import { DashboardStudyBridge } from "@/components/dashboard/DashboardStudyBridge";
import { DocumentStatusCards } from "@/components/dashboard/DocumentStatusCards";
import { PSCPPProfileCards } from "@/components/dashboard/PSCPPProfileCards";
import { RuntimeStatusCards } from "@/components/dashboard/RuntimeStatusCards";
import { StudyOverviewCards } from "@/components/dashboard/StudyOverviewCards";
import { ProtectedReadPolicyNotice } from "@/components/layout/ProtectedReadPolicyNotice";
import { SessionStatusNotice } from "@/components/layout/SessionStatusNotice";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { WorkspaceLink } from "@/components/workspace/WorkspaceShared";
import type { DashboardViewModel, SessionState } from "@/lib/api/types";
import { buildMockDashboardViewModel, loadDashboardViewModel } from "@/lib/adapters/dashboard";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";

function UnauthenticatedDashboardPanel() {
  return (
    <div className="space-y-6">
      <SessionStatusNotice variant="dashboard" />
      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
        <Badge>acesso interno</Badge>
        <CardTitle className="mt-5 max-w-3xl break-words text-[2rem] leading-[1.02] sm:text-[2.35rem]">
          Entre para ver seus materiais, edital e caminho de estudo.
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">
          Sem uma sessão ativa, o painel evita mostrar contagens, sessões ou materiais de demonstração como se fossem
          seus dados reais.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <WorkspaceLink href="/login">Entrar</WorkspaceLink>
          <WorkspaceLink href="/onboarding">Conhecer o fluxo</WorkspaceLink>
        </div>
      </Card>
    </div>
  );
}

function DashboardNextStepCard() {
  return (
    <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
      <div className="section-kicker">próximo passo</div>
      <CardTitle className="mt-5 max-w-3xl break-words text-[1.9rem] leading-[1.02]">
        Envie ou identifique um edital para montar o caminho de estudo.
      </CardTitle>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
        O estudo orientado fica mais fiel quando parte do edital oficial. Enquanto isso, o painel mantém materiais reais
        e orientação geral sem sugerir uma sessão específica.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <WorkspaceLink href="/materials/upload">Enviar material</WorkspaceLink>
        <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
      </div>
    </Card>
  );
}

export function DashboardReadOnlyClient() {
  const [viewModel, setViewModel] = useState<DashboardViewModel>(buildMockDashboardViewModel());
  const [sessionState, setSessionState] = useState<SessionState>(buildDefaultSessionState());

  useEffect(() => {
    let active = true;

    void loadDashboardViewModel().then((next) => {
      if (active) {
        setViewModel(next);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    void loadSessionState({ refresh: true }).then((next) => {
      if (active) {
        setSessionState(next);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  if (sessionState.status !== "authenticated") {
    return <UnauthenticatedDashboardPanel />;
  }

  const shouldShowStudyBridge = sessionState.status === "authenticated" && viewModel.hasRealEditalContext;
  const shouldShowNextStep =
    sessionState.status === "authenticated" && viewModel.usesRealUserData && !viewModel.hasRealEditalContext;

  return (
    <div className="space-y-8">
      <BackendConnectionBanner connection={viewModel.connection} />

      {shouldShowStudyBridge ? <DashboardStudyBridge /> : null}
      {shouldShowNextStep ? <DashboardNextStepCard /> : null}

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[32px] border border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)] p-6">
          <Badge>beta fechado</Badge>
          <h2 className="mt-5 font-serif text-4xl text-ink">
            Painel atual da preparação, sem esconder o que ainda exige revisão
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-8 text-silver">
            Este painel combina dados de demonstração auditados com leitura de consulta do backend quando
            ela está disponível. O foco continua em materiais, edital, mapa PSCPP e estudo guiado.
          </p>
          <div className="mt-6 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
              orientação inicial
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.72)]">
              Veja o caminho seguro para usar a plataforma sem pular etapas de revisão, sem agenda automática
              e sem promessas de geração final.
            </p>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <WorkspaceLink href="/onboarding">Comece sua preparação</WorkspaceLink>
          </div>
        </div>
        <div className="naval-window">
          <div className="naval-window-bar">
            <span className="naval-window-dot bg-[#e17d69]" />
            <span className="naval-window-dot bg-[#d6c477]" />
            <span className="naval-window-dot bg-[#8fc9a9]" />
            <div className="window-url">limites e revisão</div>
          </div>
          <div className="p-6">
            <div className="section-kicker">
              limites atuais
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              <li>Somente leitura nesta camada</li>
              <li>Sem agenda automática nem alteração real de progresso</li>
              <li>Sem overclaim de OCR para PDF escaneado</li>
              <li>Sem exposição de respostas finais sensíveis</li>
            </ul>
          </div>
        </div>
      </section>

      <div className="space-y-4">
        <SessionStatusNotice variant="dashboard" />
        <ProtectedReadPolicyNotice surfaceLabel="Painel" />
      </div>

      <StudyOverviewCards cards={viewModel.studyOverviewCards} />

      <section className="space-y-4">
        <div className="section-kicker">
          o que já está preparado
        </div>
        <CapabilityStatusPanel items={viewModel.capabilityItems} />
      </section>

      <section className="space-y-4">
        <div className="section-kicker">
          materiais e edital
        </div>
        <DocumentStatusCards cards={viewModel.documentCards} />
      </section>

      <section className="space-y-4">
        <div className="section-kicker">
          perfis PSCPP
        </div>
        <PSCPPProfileCards cards={viewModel.pscppCards} />
      </section>

      <section className="space-y-4">
        <div className="section-kicker">
          uso controlado
        </div>
        <RuntimeStatusCards cards={viewModel.runtimeCards} />
      </section>
    </div>
  );
}
