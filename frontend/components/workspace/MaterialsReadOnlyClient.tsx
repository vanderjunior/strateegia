"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { ProtectedReadPolicyNotice } from "@/components/layout/ProtectedReadPolicyNotice";
import type { MaterialListItem, MaterialType, MaterialsWorkspaceViewModel } from "@/lib/api/types";
import { buildMockMaterialsWorkspaceViewModel, loadMaterialsWorkspaceViewModel } from "@/lib/adapters/materials";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/adapters/capabilities";
import Link from "next/link";

export function MaterialsReadOnlyClient() {
  const [viewModel, setViewModel] = useState<MaterialsWorkspaceViewModel>(buildMockMaterialsWorkspaceViewModel());
  const [activeType, setActiveType] = useState<MaterialType | "all">("all");

  useEffect(() => {
    let active = true;
    void loadMaterialsWorkspaceViewModel().then((next) => {
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
        eyebrow="materiais"
        title="Materiais"
        subtitle="Acompanhe materiais adicionados, leitura segura e pontos que ainda exigem revisão."
        connection={viewModel.connection}
      />

      <ProtectedReadPolicyNotice surfaceLabel="Materiais" />

      <Card className="min-w-0 border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0 max-w-2xl">
            <div className="section-kicker">entrada controlada</div>
            <CardTitle className="mt-4 break-words text-[1.8rem]">Enviar material</CardTitle>
            <p className="mt-3 text-sm leading-7 text-silver">
              Adicione um PDF, TXT ou Markdown para validação inicial. O envio segue em etapa controlada e a leitura
              posterior continua sujeita a revisão.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/materials/upload"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-5 py-3 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)]"
            >
              Enviar material
            </Link>
          </div>
        </div>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      {viewModel.items.length ? (
        <>
          <Card className="min-w-0">
            <div className="section-kicker">organização por tipo</div>
            <CardTitle className="mt-5 break-words text-[1.8rem]">Materiais por classificação</CardTitle>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {viewModel.materialTypeGroups.map((group) => (
                <button
                  key={group.type}
                  type="button"
                  onClick={() => setActiveType(group.type)}
                  className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4 text-left transition hover:border-[rgba(201,169,110,0.22)]"
                >
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">{group.label}</div>
                  <p className="mt-3 text-2xl font-semibold text-ink">{group.count}</p>
                </button>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setActiveType("all")}
                className={`rounded-xl border px-4 py-2 text-sm transition ${
                  activeType === "all"
                    ? "border-[rgba(201,169,110,0.28)] bg-[rgba(201,169,110,0.12)] text-ink"
                    : "border-[rgba(168,184,196,0.12)] bg-transparent text-silver"
                }`}
              >
                Todos
              </button>
              {viewModel.materialTypeGroups.map((group) => (
                <button
                  key={group.type}
                  type="button"
                  onClick={() => setActiveType(group.type)}
                  className={`rounded-xl border px-4 py-2 text-sm transition ${
                    activeType === group.type
                      ? "border-[rgba(201,169,110,0.28)] bg-[rgba(201,169,110,0.12)] text-ink"
                      : "border-[rgba(168,184,196,0.12)] bg-transparent text-silver"
                  }`}
                >
                  {group.label}
                </button>
              ))}
            </div>
            {!viewModel.hasEdital ? (
              <p className="mt-5 text-sm leading-7 text-silver">
                Envie um edital para orientar o caminho de estudo.
              </p>
            ) : null}
            {!viewModel.hasStudyMaterial ? (
              <p className="mt-2 text-sm leading-7 text-silver">
                Depois do edital, envie materiais de estudo para comparar cobertura.
              </p>
            ) : null}
          </Card>

          <section className="space-y-6">
            {viewModel.materialTypeGroups
              .filter((group) => activeType === "all" || group.type === activeType)
              .map((group) => (
                <div key={group.type} className="space-y-4">
                  <div>
                    <div className="section-kicker">{group.label}</div>
                    <h2 className="mt-2 font-serif text-[1.9rem] text-ink">
                      {group.label} enviados
                    </h2>
                  </div>
                  {group.items.length ? (
                    <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                      {group.items.map((item) => (
                        <MaterialCard key={item.id} item={item} />
                      ))}
                    </div>
                  ) : (
                    <Card className="border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.02)]">
                      <CardTitle className="text-[1.4rem]">Nenhum item neste grupo</CardTitle>
                      <p className="mt-3 text-sm leading-7 text-silver">
                        A classificação ajuda a organizar a biblioteca, mas não aciona processamento automático.
                      </p>
                    </Card>
                  )}
                </div>
              ))}
          </section>
        </>
      ) : (
        <Card>
          <div className="section-kicker">materiais</div>
          <CardTitle className="mt-5 text-[1.8rem]">Nenhum material para exibir ainda</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            {viewModel.connection.state === "connected" && viewModel.connection.source === "backend"
              ? "Nenhum material foi encontrado na sua sessão até agora. Você pode enviar um material para iniciar a validação controlada."
              : "Envie um material para iniciar a validação. O envio segue controlado e a leitura posterior continua sujeita a revisão."}
          </p>
        </Card>
      )}
    </div>
  );
}

function MaterialCard({ item }: { item: MaterialListItem }) {
  return (
    <Card className="flex h-full min-w-0 flex-col">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-[18rem]">
          <div className="section-kicker">material</div>
          <CardTitle className="mt-4 break-words text-[1.55rem] leading-[1.02] sm:text-[1.8rem]">
            {item.title}
          </CardTitle>
        </div>
        <Badge className={sourceBadgeClass(item.source)}>{sourceLabel(item.source)}</Badge>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Badge className={productStatusClass(item.processingStatus)}>{item.processingStatus}</Badge>
        <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
          {item.typeLabel}
        </Badge>
        {item.materialTypeLabel ? (
          <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
            {item.materialTypeLabel}
          </Badge>
        ) : null}
        <Badge className={productStatusClass(item.reviewState)}>{item.reviewState}</Badge>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">extração</div>
          <p className="mt-2 text-sm text-ink">{item.extractionStatus}</p>
        </div>
        <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">estrutura</div>
          <p className="mt-2 break-words text-sm text-ink">
            {item.sectionsCount ?? 0} seções · {item.chunksCount ?? 0} trechos
          </p>
        </div>
      </div>
      <p className="mt-5 text-sm leading-7 text-silver">
        O material é lido, organizado em seções seguras e preparado para revisão.
      </p>
      <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
        {item.processingStatus === "OCR necessário"
          ? "A leitura de PDFs escaneados está em validação e pode exigir revisão."
          : `Gaps relacionados: ${item.relatedGaps}.`}
      </p>
      <div className="mt-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <span className="max-w-[18rem] text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.42)]">
          Consulta local e revisão controlada.
        </span>
        <WorkspaceLink href={`/materials/${item.id}`}>Ver material</WorkspaceLink>
      </div>
    </Card>
  );
}
