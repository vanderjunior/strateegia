"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { productStatusClass, WorkspaceLink } from "@/components/workspace/WorkspaceShared";
import type { OnboardingStepItem } from "@/lib/api/types";

export function OnboardingStepCard({ step }: { step: OnboardingStepItem }) {
  return (
    <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
      <div className="flex flex-wrap items-start justify-between gap-3 sm:flex-nowrap">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] font-mono text-sm tracking-[0.18em] text-ink">
            {String(step.stepNumber).padStart(2, "0")}
          </div>
          <div className="min-w-0">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">passo seguro</div>
            <CardTitle className="mt-4 break-words text-[1.7rem] leading-[1.04] sm:text-[1.85rem]">
              {step.title}
            </CardTitle>
          </div>
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
          <Badge className={productStatusClass(step.statusLabel)}>{step.statusLabel}</Badge>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <p className="text-sm leading-7 text-silver">{step.description}</p>
        <p className="text-sm leading-7 text-[rgba(232,238,242,0.72)]">{step.note}</p>
      </div>

      <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">observação</div>
        <p className="mt-2 break-words text-sm leading-7 text-[rgba(232,238,242,0.72)]">{step.cautionLabel}</p>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <WorkspaceLink href={step.primaryLink.href}>{step.primaryLink.label}</WorkspaceLink>
        {step.secondaryLinks.map((link) => (
          <WorkspaceLink key={link.href} href={link.href}>
            {link.label}
          </WorkspaceLink>
        ))}
      </div>
    </Card>
  );
}
