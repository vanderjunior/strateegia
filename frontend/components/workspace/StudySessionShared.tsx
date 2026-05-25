"use client";

import { Badge } from "@/components/ui/badge";
import { productStatusClass } from "@/components/workspace/WorkspaceShared";

export function StudySessionMetaRow({
  durationLabel,
  relatedMaterialsCount,
  relatedGapsCount,
  statusLabel
}: {
  durationLabel: string;
  relatedMaterialsCount: number;
  relatedGapsCount: number;
  statusLabel: string;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge className={productStatusClass(statusLabel)}>{statusLabel}</Badge>
      <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
        {durationLabel}
      </Badge>
      <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
        {relatedMaterialsCount} materiais
      </Badge>
      <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
        {relatedGapsCount} gaps
      </Badge>
    </div>
  );
}
