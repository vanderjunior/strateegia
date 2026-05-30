import type { ApiSource, CapabilityStatus, CapabilityStatusItem } from "@/lib/api/types";
import { getUserFacingStatus } from "@/lib/product/product-language";
import type { StatusTone } from "@/lib/product/status-copy";

export function capabilityStatusLabel(status: CapabilityStatus): string {
  return getUserFacingStatus(status, "student").label;
}

export function statusToneBadgeClass(tone: StatusTone): string {
  switch (tone) {
    case "positive":
      return "border-emerald-400/30 bg-emerald-400/12 text-emerald-200";
    case "warning":
      return "border-amber-400/30 bg-amber-400/12 text-amber-100";
    case "neutral":
      return "border-violet-400/30 bg-violet-400/12 text-violet-100";
    case "muted":
      return "border-rose-400/30 bg-rose-400/12 text-rose-100";
    default:
      return "";
  }
}

export function capabilityStatusBadgeClass(status: CapabilityStatus): string {
  return statusToneBadgeClass(getUserFacingStatus(status, "student").tone);
}

export function sourceLabel(source: ApiSource): string {
  switch (source) {
    case "backend":
      return "Dados reais";
    case "offline":
      return "Consulta local";
    case "unsupported":
      return "Painel em validação";
    default:
      return "Dados de demonstração";
  }
}

export function markCapabilitySources(
  items: CapabilityStatusItem[],
  overrides: Partial<Record<CapabilityStatusItem["id"], ApiSource>>
): CapabilityStatusItem[] {
  return items.map((item) => ({
    ...item,
    source: overrides[item.id] ?? item.source
  }));
}
