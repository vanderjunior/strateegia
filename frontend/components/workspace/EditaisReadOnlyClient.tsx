"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { EditaisWorkspaceViewModel } from "@/lib/api/types";
import { buildMockEditaisWorkspaceViewModel, loadEditaisWorkspaceViewModel } from "@/lib/adapters/editais";
import { sourceLabel } from "@/lib/adapters/capabilities";
import { getUserFacingCapability } from "@/lib/product/product-language";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";

export function EditaisReadOnlyClient() {
  const [viewModel, setViewModel] = useState<EditaisWorkspaceViewModel>(buildMockEditaisWorkspaceViewModel());

  useEffect(() => {
    let active = true;
    void loadEditaisWorkspaceViewModel().then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const editalCopy = getUserFacingCapability("edital_ingestion", "student");
  const alignmentCopy = getUserFacingCapability("bibliography_alignment", "student");

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="editais"
        title="Editais"
        subtitle="Revise tópicos, bibliografia e lacunas identificadas."
        connection={viewModel.connection}
      />

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 lg:grid-cols-2">
        {viewModel.items.map((item) => (
          <Card key={item.id} className="flex h-full flex-col">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="max-w-[19rem]">
                <div className="section-kicker">edital</div>
                <CardTitle className="mt-4 text-[1.8rem]">{item.title}</CardTitle>
              </div>
              <Badge className={sourceBadgeClass(item.source)}>{sourceLabel(item.source)}</Badge>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Badge className={productStatusClass(item.statusLabel)}>{item.statusLabel}</Badge>
              <Badge className={productStatusClass(item.reviewState)}>{item.reviewState}</Badge>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  tópicos
                </div>
                <p className="mt-2 text-sm text-ink">{item.topicsCount}</p>
              </div>
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  bibliografia
                </div>
                <p className="mt-2 text-sm text-ink">{item.bibliographyItemsCount}</p>
              </div>
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  gaps
                </div>
                <p className="mt-2 text-sm text-ink">{item.gapsCount}</p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-7 text-silver">
              {editalCopy?.description ?? "O edital é analisado para identificar tópicos, bibliografia, pesos e lacunas."}
            </p>
            <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              {alignmentCopy?.description ??
                "O sistema compara materiais, bibliografia e tópicos para apontar cobertura e gaps."}
            </p>
            <div className="mt-6 flex items-center justify-between gap-4">
              <span className="text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.42)]">
                A leitura de edital seguirá em etapa controlada.
              </span>
              <WorkspaceLink href={`/editais/${item.id}`}>Ver edital</WorkspaceLink>
            </div>
          </Card>
        ))}
      </section>
    </div>
  );
}
