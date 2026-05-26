"use client";

import { useEffect, useState } from "react";

import { BackendConnectionBanner } from "@/components/dashboard/BackendConnectionBanner";
import { CapabilityStatusPanel } from "@/components/dashboard/CapabilityStatusPanel";
import { DashboardStudyBridge } from "@/components/dashboard/DashboardStudyBridge";
import { DocumentStatusCards } from "@/components/dashboard/DocumentStatusCards";
import { PSCPPProfileCards } from "@/components/dashboard/PSCPPProfileCards";
import { RuntimeStatusCards } from "@/components/dashboard/RuntimeStatusCards";
import { StudyOverviewCards } from "@/components/dashboard/StudyOverviewCards";
import { Badge } from "@/components/ui/badge";
import { WorkspaceLink } from "@/components/workspace/WorkspaceShared";
import type { DashboardViewModel } from "@/lib/api/types";
import { buildMockDashboardViewModel, loadDashboardViewModel } from "@/lib/adapters/dashboard";

export function DashboardReadOnlyClient() {
  const [viewModel, setViewModel] = useState<DashboardViewModel>(buildMockDashboardViewModel());

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

  return (
    <div className="space-y-8">
      <BackendConnectionBanner connection={viewModel.connection} />

      <DashboardStudyBridge />

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
