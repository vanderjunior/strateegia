"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { StudySessionWorkspaceViewModel } from "@/lib/api/types";
import {
  buildMockStudySessionWorkspaceViewModel,
  loadStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { StudySessionMetaRow } from "@/components/workspace/StudySessionShared";
import Link from "next/link";

export function StudySessionWorkspaceClient() {
  const [viewModel, setViewModel] = useState<StudySessionWorkspaceViewModel>(
    buildMockStudySessionWorkspaceViewModel()
  );

  useEffect(() => {
    let active = true;
    void loadStudySessionWorkspaceViewModel().then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const nextSession = useMemo(
    () => viewModel.sessions.find((item) => item.id === viewModel.nextSuggestedSessionId) ?? viewModel.sessions[0],
    [viewModel]
  );

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="estudo"
        title="Estudo de hoje"
        subtitle="Sessões sugeridas a partir do perfil PSCPP, materiais e gaps identificados."
        connection={viewModel.connection}
      />

      <div className="flex flex-wrap gap-2">
        <Badge className={productStatusClass("Guia flexível")}>Guia flexível</Badge>
        <Badge className={productStatusClass("Não altera seu progresso")}>Não altera seu progresso</Badge>
      </div>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      {nextSession ? (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">próxima sessão sugerida</div>
          <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-3xl">
              <CardTitle className="break-words text-[1.95rem] leading-[1.02]">
                {nextSession.title}
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{nextSession.objective}</p>
            </div>
            <WorkspaceLink href={`/study/session/${nextSession.id}`}>Ver sessão</WorkspaceLink>
          </div>
          <div className="mt-5">
            <StudySessionMetaRow
              durationLabel={nextSession.durationLabel}
              relatedMaterialsCount={nextSession.relatedMaterialsCount}
              relatedGapsCount={nextSession.relatedGapsCount}
              statusLabel={nextSession.statusLabel}
            />
          </div>
          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            {nextSession.priorityBlockTitle}
          </p>
        </Card>
      ) : null}

      <section className="space-y-4">
        <div>
          <div className="section-kicker">sessões sugeridas</div>
          <h2 className="mt-3 font-serif text-[2rem] text-ink">Todas as sessões</h2>
        </div>
        <div className="grid gap-4 2xl:grid-cols-2">
          {viewModel.sessions.map((session) => (
            <Card key={session.id} className="h-full">
              <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
                sessão {session.sessionNumber}
              </div>
              <CardTitle className="mt-5 break-words text-[1.55rem] leading-[1.05] sm:text-[1.7rem]">
                {session.title}
              </CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{session.objective}</p>
              <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                {session.priorityBlockTitle}
              </p>
              <div className="mt-5">
                <StudySessionMetaRow
                  durationLabel={session.durationLabel}
                  relatedMaterialsCount={session.relatedMaterialsCount}
                  relatedGapsCount={session.relatedGapsCount}
                  statusLabel={session.statusLabel}
                />
              </div>
              <p className="mt-5 text-sm leading-7 text-silver">{session.note}</p>
              <div className="mt-6 flex flex-wrap gap-3">
                <WorkspaceLink href={`/study/session/${session.id}`}>Ver sessão</WorkspaceLink>
                <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="h-full">
          <div className="section-kicker">gaps que orientam o estudo</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Gaps conectados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.highlightedGaps.map((gap) => (
              <div
                key={gap.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <p className="break-words text-sm text-ink">{gap.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{gap.detail}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="h-full">
          <div className="section-kicker">materiais para começar</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Materiais relacionados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.starterMaterials.map((material) => (
              <div
                key={material.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-ink">{material.title}</p>
                    <p className="mt-2 text-sm leading-7 text-silver">{material.typeLabel}</p>
                  </div>
                  <Badge className={productStatusClass(material.statusLabel)}>{material.statusLabel}</Badge>
                </div>
                <div className="mt-4">
                  <Link
                    href={material.linkHref}
                    className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-4 py-2 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                  >
                    Ver material
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
