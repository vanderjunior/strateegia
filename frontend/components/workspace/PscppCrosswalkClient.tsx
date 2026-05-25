"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PscppCrosswalkViewModel } from "@/lib/api/types";
import {
  buildMockPscppCrosswalkViewModel,
  loadPscppCrosswalkViewModel
} from "@/lib/adapters/pscpp-crosswalk";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { PscppSectionNav } from "@/components/workspace/PscppShared";

export function PscppCrosswalkClient() {
  const [viewModel, setViewModel] = useState<PscppCrosswalkViewModel>(
    buildMockPscppCrosswalkViewModel()
  );

  useEffect(() => {
    let active = true;
    void loadPscppCrosswalkViewModel().then((next) => {
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
        eyebrow="pscpp / mapa"
        title="Mapa de preparação PSCPP"
        subtitle="Cruze materiais, edital, bibliografia e ciclo sugerido para entender onde estudar primeiro."
        connection={viewModel.connection}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <PscppSectionNav />
        <div className="flex flex-wrap gap-2">
          <Badge className="border-[rgba(201,169,110,0.22)] bg-[rgba(201,169,110,0.10)] text-ink">
            Guia de cobertura
          </Badge>
          <Badge className={productStatusClass("Não altera seu progresso")}>
            Não altera seu progresso
          </Badge>
        </div>
      </div>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="space-y-4">
        <div>
          <div className="section-kicker">cobertura por bloco</div>
          <h2 className="mt-3 font-serif text-[2rem] text-ink">Cobertura por bloco prioritário</h2>
        </div>
        <div className="grid gap-4 2xl:grid-cols-2">
          {viewModel.blocks.map((block) => (
            <Card key={block.id} className="h-full">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
                    prioridade {block.priorityNumber}
                  </div>
                  <CardTitle className="mt-4 break-words text-[1.45rem] leading-[1.08] sm:text-[1.6rem] xl:text-[1.7rem]">
                    {block.title}
                  </CardTitle>
                </div>
                <Badge className={productStatusClass(block.coverageLabel)}>{block.coverageLabel}</Badge>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <Badge className={productStatusClass(block.reviewState)}>{block.reviewState}</Badge>
                <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
                  {block.materialsCount} materiais
                </Badge>
                <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
                  {block.gapsCount} gaps
                </Badge>
              </div>

              <div className="mt-5 grid gap-3 xl:grid-cols-2">
                <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                    materiais relacionados
                  </div>
                  <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
                    {block.relatedMaterials.length ? (
                      block.relatedMaterials.map((item) => (
                        <li key={item.id}>
                          •{" "}
                          <Link
                            href={item.linkHref}
                            className="break-words text-silver transition hover:text-ink"
                          >
                            {item.title}
                          </Link>
                        </li>
                      ))
                    ) : (
                      <li>• Nenhum material relacionado com cobertura suficiente.</li>
                    )}
                  </ul>
                </div>
                <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                    sessões sugeridas
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {block.suggestedSessions.map((session) => (
                      <Badge
                        key={session.id}
                        className={productStatusClass(
                          session.emphasis === "gap_focus" ? "Sugestão de reforço" : "Sugestão flexível"
                        )}
                      >
                        {session.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
                {block.gaps.map((gap) => (
                  <li key={gap}>• {gap}</li>
                ))}
                {block.notes.map((note) => (
                  <li key={note}>• {note}</li>
                ))}
              </ul>

              <div className="mt-6 flex flex-wrap gap-3">
                <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
                <WorkspaceLink href="/editais/edital-pscpp-referencia">Ver edital de referência</WorkspaceLink>
                <WorkspaceLink href="/pscpp/ciclo">Ver ciclo</WorkspaceLink>
                <WorkspaceLink href="/pscpp/questoes">Ver questões PSCPP</WorkspaceLink>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="h-full">
          <div className="section-kicker">gaps principais</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Gaps encontrados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.mainGaps.map((gap) => (
              <div
                key={gap.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-ink">{gap.title}</p>
                    <p className="mt-2 text-sm leading-7 text-silver">{gap.affectedBlockTitle}</p>
                  </div>
                  <Badge className={productStatusClass(gap.reviewState)}>{gap.reviewState}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-silver">{gap.whyItMatters}</p>
                <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                  Sugestão de reforço: {gap.suggestedAction}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {gap.relatedSessions.map((session) => (
                    <Badge key={session.id} className={productStatusClass("Sugestão de reforço")}>
                      {session.label}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="h-full">
          <div className="section-kicker">materiais e edital</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Materiais relacionados</CardTitle>
          <div className="mt-5 space-y-3">
            {viewModel.relationships.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-ink">{item.material.title}</p>
                    <p className="mt-2 text-sm leading-7 text-silver">{item.blockTitle}</p>
                  </div>
                  <Badge className={productStatusClass(item.contributionLabel)}>{item.contributionLabel}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
                    {item.material.typeLabel}
                  </Badge>
                  <Badge className={productStatusClass(item.material.statusLabel)}>{item.material.statusLabel}</Badge>
                  <Badge className={productStatusClass(item.edital.statusLabel)}>{item.edital.statusLabel}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                  Edital de referência: {item.edital.title}
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    href={item.material.linkHref}
                    className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-4 py-2 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                  >
                    Ver material
                  </Link>
                  <Link
                    href={item.edital.linkHref}
                    className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-4 py-2 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                  >
                    Ver edital
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="h-full">
          <div className="section-kicker">conexão com o ciclo</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Sessões sugeridas para reforço</CardTitle>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass("Sugestão flexível")}>Sugestão flexível</Badge>
            <Badge className={productStatusClass("Não cria agenda automaticamente")}>
              Não cria agenda automaticamente
            </Badge>
          </div>
          <p className="mt-5 text-sm leading-7 text-silver">
            Este mapa conecta gaps e cobertura às sessões do ciclo sugerido, sem criar agenda e sem alterar progresso.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/pscpp/ciclo">Ver ciclo completo</WorkspaceLink>
            <WorkspaceLink href="/study">Ver estudo de hoje</WorkspaceLink>
          </div>
        </Card>

        <Card className="h-full">
          <div className="section-kicker">preview do ciclo</div>
          <CardTitle className="mt-5 text-[1.9rem] leading-[1.02]">Sessões destacadas</CardTitle>
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            {viewModel.highlightedSessions.map((session) => (
              <div
                key={session.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                      {session.label}
                    </div>
                    <p className="mt-3 text-sm text-ink">{session.detail}</p>
                  </div>
                  <Badge className={productStatusClass("Sugestão de reforço")}>reforço</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
