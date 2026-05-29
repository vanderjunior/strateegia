"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FriendlyStatusBadge } from "@/components/product/FriendlyStatusBadge";
import type { PscppWorkspaceViewModel } from "@/lib/api/types";
import {
  buildMockPscppWorkspaceViewModel,
  loadPscppWorkspaceViewModel
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

export function PscppWorkspaceClient() {
  const [viewModel, setViewModel] = useState<PscppWorkspaceViewModel>(
    buildMockPscppWorkspaceViewModel()
  );
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());

  useEffect(() => {
    let active = true;
    void Promise.all([loadPscppWorkspaceViewModel(), loadRealUserStudyReadiness()]).then(
      ([nextViewModel, nextReadiness]) => {
        if (active) {
          setViewModel(nextViewModel);
          setReadiness(nextReadiness);
        }
      }
    );
    return () => {
      active = false;
    };
  }, []);

  if (!readiness.canShowConcreteStudyPlan) {
    return (
      <div className="space-y-8">
        <WorkspaceSourcePanel
          eyebrow="pscpp / referência"
          title="Área PSCPP disponível como referência."
          subtitle="Para montar seu mapa real, envie e analise um edital."
          connection={readiness.connection}
        />

        <PscppSectionNav />

        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">referência, não plano personalizado</div>
          <CardTitle className="mt-5 max-w-3xl break-words text-[1.95rem] leading-[1.02]">
            O PSCPP aqui ainda não está baseado no seu edital.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            {readiness.editalAnalysisState === "analysis_needs_review"
              ? "Há edital analisado, mas ele precisa de conferência antes de virar mapa personalizado."
              : readiness.editalAnalysisState === "edital_uploaded_not_analyzed"
                ? "Você já enviou um edital, mas a análise ainda não foi executada nesta versão."
                : "A referência ajuda a conhecer o formato do mapa, ciclo e questões candidatas. O caminho real depende de um edital analisado e de materiais da sua sessão."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/pscpp/mapa">Ver referência PSCPP</WorkspaceLink>
            <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="pscpp / praticagem"
        title={viewModel.profileTitle}
        subtitle="Guia técnico-operacional para estudo, materiais e questões candidatas."
        connection={viewModel.connection}
      />

      <PscppSectionNav />

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="h-full min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 max-w-3xl">
              <div className="section-kicker">perfil da prova</div>
              <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">
                Referência PSCPP conectada
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{viewModel.profileDescription}</p>
            </div>
            <FriendlyStatusBadge status="implemented_and_tested" />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass(viewModel.statusLabel)}>{viewModel.statusLabel}</Badge>
            <Badge className={productStatusClass(viewModel.modeLabel)}>{viewModel.modeLabel}</Badge>
            <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
              Bibliografia identificada
            </Badge>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">questões candidatas</div>
              <p className="mt-3 break-words text-sm text-ink">Fonte obrigatória e revisão necessária.</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">ciclo sugerido</div>
              <p className="mt-3 break-words text-sm text-ink">Rotação flexível de 12 sessões, ajustável pelo candidato.</p>
            </div>
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">revisão necessária</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">
            Evidência histórica e uso atual
          </CardTitle>
          <div className="mt-5 flex flex-wrap gap-2">
            {viewModel.evidence.map((item) => (
              <Badge key={item} className="border-[rgba(201,169,110,0.22)] bg-[rgba(201,169,110,0.10)] text-ink">
                {item}
              </Badge>
            ))}
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {viewModel.evidenceNotes.map((note) => (
              <li key={note}>• {note}</li>
            ))}
          </ul>
          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            A prova antiga orienta estilo e estratégia, não substitui o edital atual.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {viewModel.priorityBlocks.map((block, index) => (
          <Card key={block.id} className="h-full min-w-0">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
              prioridade {index + 1}
            </div>
            <CardTitle className="mt-5 break-words text-[1.7rem] leading-[1.04]">{block.title}</CardTitle>
            <p className="mt-4 text-sm leading-7 text-silver">{block.detail}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
