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

  useEffect(() => {
    let active = true;
    void loadPscppWorkspaceViewModel().then((next) => {
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
        eyebrow="pscpp / praticagem"
        title={viewModel.profileTitle}
        subtitle="Guia técnico-operacional para estudo, materiais e questões candidatas."
        connection={viewModel.connection}
      />

      <PscppSectionNav />

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="h-full">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 max-w-3xl">
              <div className="section-kicker">perfil</div>
              <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">
                Perfil PSCPP configurado
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{viewModel.profileDescription}</p>
            </div>
            <FriendlyStatusBadge status="implemented_and_tested" />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass(viewModel.statusLabel)}>{viewModel.statusLabel}</Badge>
            <Badge className={productStatusClass(viewModel.modeLabel)}>{viewModel.modeLabel}</Badge>
            <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
              {viewModel.examProfileId}
            </Badge>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">perfil de questões</div>
              <p className="mt-3 break-words text-sm text-ink">{viewModel.questionStyleProfileId}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">perfil de ciclo</div>
              <p className="mt-3 break-words text-sm text-ink">{viewModel.studyCycleProfileId}</p>
            </div>
          </div>
        </Card>

        <Card className="h-full">
          <div className="section-kicker">cautela</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">
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
          <Card key={block.id} className="h-full">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
              prioridade {index + 1}
            </div>
            <CardTitle className="mt-5 text-[1.7rem] leading-[1.04]">{block.title}</CardTitle>
            <p className="mt-4 text-sm leading-7 text-silver">{block.detail}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
