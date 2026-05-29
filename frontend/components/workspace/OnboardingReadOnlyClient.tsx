"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { OnboardingStepCard } from "@/components/workspace/OnboardingStepCard";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { buildOnboardingViewModel } from "@/lib/adapters/onboarding";

export function OnboardingReadOnlyClient() {
  const viewModel = buildOnboardingViewModel();

  return (
    <div className="space-y-8">
      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <div className="section-kicker">como começar</div>
            <CardTitle className="mt-5 break-words text-[2rem] leading-[0.96] sm:text-[2.25rem]">
              Comece sua preparação
            </CardTitle>
            <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">
              Comece pelo básico: entre, envie o edital, depois organize materiais. O estudo guiado concreto só aparece
              quando houver edital analisado.
            </p>
          </div>
          <div className="flex max-w-full flex-wrap gap-2 lg:justify-end">
            <Badge className={productStatusClass("Orientação inicial")}>Orientação inicial</Badge>
            <Badge className={productStatusClass("Classificação salva")}>Classificação salva</Badge>
            <Badge className={productStatusClass("Disponível para consulta")}>Disponível para consulta</Badge>
          </div>
        </div>
        <div className="mt-6 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">caminho seguro</div>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-[rgba(232,238,242,0.72)]">
            Algumas funções ainda estão em validação e serão liberadas aos poucos. Esta tela não cria agenda, não gera
            questões e não altera progresso.
          </p>
        </div>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="space-y-5">
          <div className="section-kicker">etapas principais</div>
          {viewModel.steps.map((step) => (
            <OnboardingStepCard key={step.id} step={step} />
          ))}
        </div>

        <div className="space-y-5">
          <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
            <div className="section-kicker">disponível agora</div>
            <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">Fluxo inicial para staging interno</CardTitle>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {viewModel.readyHighlights.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
              <WorkspaceLink href="/study">Ver estudo guiado</WorkspaceLink>
            </div>
          </Card>

          <Card className="min-w-0 border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.03)]">
            <div className="section-kicker">em validação</div>
            <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">Funções liberadas aos poucos</CardTitle>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {viewModel.reviewHighlights.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/pscpp">Ver referência PSCPP</WorkspaceLink>
              <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
