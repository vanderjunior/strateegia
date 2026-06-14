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
    <Card className="h-full min-w-0">
      <div className="section-kicker">{eyebrow}</div>
      <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">{title}</CardTitle>
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
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());

  useEffect(() => {
    let active = true;
    void Promise.all([loadPscppQuestionsViewModel(), loadRealUserStudyReadiness()]).then(([next, nextReadiness]) => {
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
          eyebrow="pscpp / questões"
          title="Questões ainda não disponíveis"
          subtitle="As questões dependem de edital analisado, materiais relacionados e revisão."
          connection={readiness.connection}
        />

        <PscppSectionNav />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)]">
          <div className="section-kicker">em preparação</div>
          <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
            Questões ainda não disponíveis.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            As questões serão preparadas depois que houver edital analisado e materiais relacionados. Esta tela não
            mostra o funcionamento previsto, sem respostas finais ou avaliação completa.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </Card>

        <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">referência futura</div>
          <CardTitle className="mt-5 text-[1.7rem] leading-[1.04]">Como esta área será usada depois</CardTitle>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-silver">
            <li>• O edital analisado define o escopo.</li>
            <li>• Materiais relacionados ajudam a validar cobertura.</li>
            <li>• Questões revisadas poderão apoiar avaliações quando essa etapa existir.</li>
          </ul>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="pscpp / questões"
        title="Questões de fixação como referência"
        subtitle="Referência de formato e cautelas. Questões reais dependem de edital analisado e revisão."
        connection={viewModel.connection}
      />

      <PscppSectionNav />

      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)]">
        <div className="section-kicker">referência PSCPP</div>
        <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
          Exemplos de orientação. Ainda não baseados no seu edital.
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
          Esta tela mostra regras de ancoragem para uma etapa futura, sem criar avaliação completa.
        </p>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <GuidanceList title="Arquétipos de questão" eyebrow="formatos" items={viewModel.archetypes} />
        <Card className="h-full min-w-0">
          <div className="section-kicker">estado atual</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Relação com avaliações</CardTitle>
          <div className="mt-5 flex flex-wrap gap-2">
            {viewModel.relationToSimulado.map((item) => (
              <Badge key={item} className={productStatusClass(item)}>
                {item}
              </Badge>
            ))}
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Questões de fixação precisam de revisão antes de qualquer uso avaliativo.</li>
            <li>• Avaliações completas ficam para uma etapa posterior.</li>
            <li>• Esta tela não cria avaliações nem mostra respostas finais.</li>
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
            <WorkspaceLink href="/pscpp">Voltar à área PSCPP</WorkspaceLink>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <GuidanceList title="Regras de ancoragem" eyebrow="fonte obrigatória" items={viewModel.sourceRules} />
        <GuidanceList title="Revisão humana e cautelas" eyebrow="revisão" items={viewModel.reviewRules} />
      </section>
    </div>
  );
}
