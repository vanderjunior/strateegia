"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PscppQuestionsViewModel } from "@/lib/api/types";
import {
  buildMockPscppQuestionsViewModel,
  loadPscppQuestionsViewModel
} from "@/lib/adapters/pscpp";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { PscppSectionNav } from "@/components/workspace/PscppShared";

function GuidanceList({
  title,
  eyebrow,
  items
}: {
  title: string;
  eyebrow: string;
  items: PscppQuestionsViewModel["archetypes"];
}) {
  return (
    <Card className="h-full">
      <div className="section-kicker">{eyebrow}</div>
      <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">{title}</CardTitle>
      <div className="mt-5 space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
          >
            <p className="text-sm text-ink">{item.title}</p>
            <p className="mt-2 text-sm leading-7 text-silver">{item.detail}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function PscppQuestionsClient() {
  const [viewModel, setViewModel] = useState<PscppQuestionsViewModel>(
    buildMockPscppQuestionsViewModel()
  );

  useEffect(() => {
    let active = true;
    void loadPscppQuestionsViewModel().then((next) => {
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
      <WorkspaceSourcePanel
        eyebrow="pscpp / questões"
        title="Orientação de questões PSCPP"
        subtitle="Guia de estilo, fonte e revisão para questões candidatas e relação com simulados ainda não finalizados."
        connection={viewModel.connection}
      />

      <PscppSectionNav />

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <GuidanceList title="Arquétipos de questão" eyebrow="formatos" items={viewModel.archetypes} />
        <Card className="h-full">
          <div className="section-kicker">estado atual</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Relação com simulado</CardTitle>
          <div className="mt-5 flex flex-wrap gap-2">
            {viewModel.relationToSimulado.map((item) => (
              <Badge key={item} className={productStatusClass(item)}>
                {item}
              </Badge>
            ))}
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Questões candidatas precisam de revisão antes de qualquer uso avaliativo.</li>
            <li>• O simulado completo ainda exige preparação e conferência humanas.</li>
            <li>• Esta tela não gera questões, não gera simulados e não mostra respostas finais.</li>
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
            <WorkspaceLink href="/pscpp">Voltar ao workspace PSCPP</WorkspaceLink>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <GuidanceList title="Regras de ancoragem" eyebrow="fonte obrigatoria" items={viewModel.sourceRules} />
        <GuidanceList title="Revisão humana e cautelas" eyebrow="revisao" items={viewModel.reviewRules} />
      </section>
    </div>
  );
}
