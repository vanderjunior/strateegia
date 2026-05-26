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
              Siga um caminho seguro: envie materiais, revise o edital, entenda os gaps e avance pelo
              estudo sugerido.
            </p>
          </div>
          <div className="flex max-w-full flex-wrap gap-2 lg:justify-end">
            <Badge className={productStatusClass("Upload controlado")}>Upload controlado</Badge>
            <Badge className={productStatusClass("Análise candidata")}>Análise candidata</Badge>
            <Badge className={productStatusClass("Guia flexível")}>Guia flexível</Badge>
          </div>
        </div>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="space-y-5">
          {viewModel.steps.map((step) => (
            <OnboardingStepCard key={step.id} step={step} />
          ))}
        </div>

        <div className="space-y-5">
          <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
            <div className="section-kicker">o que já está pronto</div>
            <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">Fluxo de orientação disponível</CardTitle>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {viewModel.readyHighlights.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
              <WorkspaceLink href="/study">Ver estudo de hoje</WorkspaceLink>
            </div>
          </Card>

          <Card className="min-w-0 border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.03)]">
            <div className="section-kicker">o que ainda exige revisão</div>
            <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">Pontos de cautela antes de ampliar o uso</CardTitle>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {viewModel.reviewHighlights.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
              <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
