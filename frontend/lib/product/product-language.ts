import type { Audience, CapabilityStatus } from "@/lib/api/types";
import { productBoundaryMatrix, type ProductBoundaryEntry, type ProductGroupKey, type VisibilityRule } from "@/lib/product/boundary-matrix";
import { statusCopy, type StatusTone } from "@/lib/product/status-copy";
import { userFacingLabels } from "@/lib/product/user-facing-labels";

export interface UserFacingCapability {
  internalKey: string;
  label: string;
  description: string;
  visibility: VisibilityRule;
  safeStatusLabels: string[];
  recommendedUiStatus: string;
  actionMode: ProductBoundaryEntry["actionMode"];
}

const termReplacements = [
  ["controlled propagation", "atualizacao controlada"],
  ["runtime chain", "fluxo de simulado"],
  ["final pedagogical update event", "atualizacao pedagogica proposta"],
  ["commit transaction", "etapa de atualizacao controlada"],
  ["mutation transaction", "atualizacao controlada"],
  ["applied event ledger", "registro de aplicacao"],
  ["propagation guardrail", "protecao contra atualizacao indevida"],
  ["controlled propagation apply", "registro controlado de atualizacao"],
  ["ledger", "registro"],
  ["guardrail", "protecao"],
  ["propagation", "atualizacao ampla"],
  ["shell", "etapa de revisao"],
  ["artifact", "registro"],
  ["mutation", "atualizacao"]
] as const;

function findCapability(internalKey: string): ProductBoundaryEntry | undefined {
  return productBoundaryMatrix.find((entry) => entry.internalKey === internalKey);
}

function resolveVisibility(entry: ProductBoundaryEntry, audience: Audience): VisibilityRule {
  switch (audience) {
    case "public":
    case "student":
      return entry.studentVisibility;
    case "mentor":
      return entry.mentorVisibility;
    case "admin":
      return entry.adminVisibility;
    case "developer":
      return entry.developerVisibility;
    default:
      return entry.studentVisibility;
  }
}

export function shouldShowCapability(internalKey: string, audience: Audience): boolean {
  const entry = findCapability(internalKey);
  if (!entry) {
    return true;
  }
  return !["hidden", "internal_only"].includes(resolveVisibility(entry, audience));
}

export function getUserFacingCapability(internalKey: string, audience: Audience): UserFacingCapability | null {
  const entry = findCapability(internalKey);
  if (!entry) {
    return null;
  }

  const label = entry.audienceLabels?.[audience] ?? entry.userFacingLabel;
  const description = entry.audienceDescriptions?.[audience] ?? entry.userFacingDescription;

  return {
    internalKey,
    label,
    description,
    visibility: resolveVisibility(entry, audience),
    safeStatusLabels: entry.safeStatusLabels,
    recommendedUiStatus: entry.recommendedUiStatus,
    actionMode: entry.actionMode
  };
}

export function getCapabilityGroup(groupKey: ProductGroupKey): ProductBoundaryEntry[] {
  return productBoundaryMatrix.filter((entry) => entry.groupKey === groupKey);
}

export function translateInternalTerm(text: string, audience: Audience): string {
  if (audience === "developer" || !text) {
    return text;
  }

  return termReplacements.reduce((current, [from, to]) => {
    return current.replaceAll(from, to);
  }, text);
}

export function getSafeProductCopy(key: keyof typeof userFacingLabels): string {
  return userFacingLabels[key];
}

export function getUserFacingStatus(statusKey: CapabilityStatus, audience: Audience): {
  label: string;
  tone: StatusTone;
} {
  const copy = statusCopy[statusKey] ?? statusCopy.unclear_needs_follow_up;
  return {
    label: copy.audienceLabel?.[audience] ?? copy.label,
    tone: copy.tone
  };
}
