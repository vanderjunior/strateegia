"use client";

import { useEffect, useState } from "react";

import { BackendConnectionBanner } from "@/components/dashboard/BackendConnectionBanner";
import { CapabilityStatusPanel } from "@/components/dashboard/CapabilityStatusPanel";
import { DocumentStatusCards } from "@/components/dashboard/DocumentStatusCards";
import { PSCPPProfileCards } from "@/components/dashboard/PSCPPProfileCards";
import { RuntimeStatusCards } from "@/components/dashboard/RuntimeStatusCards";
import { StudyOverviewCards } from "@/components/dashboard/StudyOverviewCards";
import { Badge } from "@/components/ui/badge";
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

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[32px] border border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)] p-6">
          <Badge>beta fechado</Badge>
          <h2 className="mt-5 font-serif text-4xl text-ink">
            Estado atual do produto, sem esconder o que ainda esta em validacao
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-8 text-silver">
            Este painel combina fallback local auditado com leitura read-only do backend quando ela esta disponivel.
            O produto continua cauteloso com OCR, geracao completa de simulado e qualquer mutacao de runtime.
          </p>
        </div>
        <div className="rounded-[32px] border border-[rgba(168,184,196,0.10)] bg-[rgba(10,21,32,0.76)] p-6">
          <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
            restricoes claras
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>Somente GET read-only nesta camada</li>
            <li>Sem mutacao real de scheduler ou calendario</li>
            <li>Sem overclaim de OCR para PDF escaneado</li>
            <li>Sem exposicao de respostas finais sensiveis</li>
          </ul>
        </div>
      </section>

      <StudyOverviewCards cards={viewModel.studyOverviewCards} />

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          capability matrix
        </div>
        <CapabilityStatusPanel items={viewModel.capabilityItems} />
      </section>

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          materiais e edital
        </div>
        <DocumentStatusCards cards={viewModel.documentCards} />
      </section>

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          perfis PSCPP
        </div>
        <PSCPPProfileCards cards={viewModel.pscppCards} />
      </section>

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          runtime e ledger
        </div>
        <RuntimeStatusCards cards={viewModel.runtimeCards} />
      </section>
    </div>
  );
}
