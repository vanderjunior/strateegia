"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PscppCycleViewModel } from "@/lib/api/types";
import {
  buildMockPscppCycleViewModel,
  loadPscppCycleViewModel
} from "@/lib/adapters/pscpp";
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
import { PscppSectionNav } from "@/components/workspace/PscppShared";

export function PscppCycleClient() {
  const [viewModel, setViewModel] = useState<PscppCycleViewModel>(
    buildMockPscppCycleViewModel()
  );
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());

  useEffect(() => {
    let active = true;
    void Promise.all([loadPscppCycleViewModel(), loadRealUserStudyReadiness()]).then(([next, nextReadiness]) => {
      if (active) {
        setViewModel(next);
        setReadiness(nextReadiness);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  if (!readiness.canShowConcreteStudyPlan) {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="pscpp / ciclo"
          title="Ciclo aguardando edital analisado"
          subtitle="Esta área depende de um edital analisado antes de virar caminho real."
          connection={readiness.connection}
        />

        <PscppSectionNav />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)]">
          <div className="section-kicker">área gated</div>
          <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
            Esta área depende de um edital analisado.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Envie um edital para iniciar o fluxo. Quando a análise estiver disponível, esta tela poderá mostrar um
            ciclo conectado ao seu escopo real.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </Card>

        <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">exemplo de referência</div>
          <CardTitle className="mt-5 text-[1.7rem] leading-[1.04]">
            Ciclo de demonstração, não personalizado.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            A referência PSCPP pode ajudar a entender o formato geral, mas não cria agenda, não altera progresso e
            ainda não representa seu ciclo de estudo.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="pscpp / ciclo"
        title="Ciclo de referência PSCPP"
        subtitle="Referência flexível, sem agenda automática e ainda não baseada no seu edital."
        connection={viewModel.connection}
      />

      <PscppSectionNav />

      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)]">
        <div className="section-kicker">referência PSCPP</div>
        <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
          Ciclo de demonstração. Ainda não baseado no seu edital.
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
          O ciclo real deve partir de edital analisado e materiais enviados na sua sessão.
        </p>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="h-full min-w-0">
          <div className="section-kicker">modo de uso</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Guia flexível</CardTitle>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass(viewModel.modeLabel)}>{viewModel.modeLabel}</Badge>
            <Badge className={productStatusClass(viewModel.overrideLabel)}>{viewModel.overrideLabel}</Badge>
            <Badge className={productStatusClass(viewModel.baselineLabel)}>{viewModel.baselineLabel}</Badge>
          </div>
          <p className="mt-5 text-sm leading-7 text-silver">{viewModel.weeklyGuidance}</p>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            <li>• Não cria agenda automaticamente.</li>
            <li>• Não altera seu progresso.</li>
            <li>• Pode ser reordenado conforme edital, materiais e tempo disponível.</li>
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
            <WorkspaceLink href="/study">Ver estudo guiado</WorkspaceLink>
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">estrutura de sessão</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Checklist de estudo</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {viewModel.sessionStructure.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {viewModel.notebookSystem.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">caderno</div>
                <p className="mt-3 text-sm text-ink">{item.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="h-full min-w-0">
          <div className="section-kicker">fases</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Plano em quatro fases</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.phasePlan.map((phase, index) => (
              <div
                key={phase.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">fase {index + 1}</div>
                <p className="mt-3 text-sm text-ink">{phase.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{phase.detail}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">rotação</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Rotação de 12 sessões</CardTitle>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {viewModel.rotation.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  sessão {item.index}
                </div>
                <p className="mt-3 text-sm text-ink">{item.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
