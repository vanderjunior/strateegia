import type { ApiSource, CapabilityStatus, CapabilityStatusItem } from "@/lib/api/types";

export function capabilityStatusLabel(status: CapabilityStatus): string {
  return status.replaceAll("_", " ");
}

export function capabilityStatusBadgeClass(status: CapabilityStatus): string {
  switch (status) {
    case "implemented_and_tested":
      return "border-emerald-400/30 bg-emerald-400/12 text-emerald-200";
    case "implemented_but_needs_manual_validation":
      return "border-amber-400/30 bg-amber-400/12 text-amber-100";
    case "partially_implemented":
      return "border-sky-400/30 bg-sky-400/12 text-sky-100";
    case "foundation_only":
      return "border-violet-400/30 bg-violet-400/12 text-violet-100";
    case "metadata_only":
      return "border-cyan-400/30 bg-cyan-400/12 text-cyan-100";
    case "not_implemented":
      return "border-rose-400/30 bg-rose-400/12 text-rose-100";
    default:
      return "";
  }
}

export function sourceLabel(source: ApiSource): string {
  switch (source) {
    case "backend":
      return "backend";
    case "offline":
      return "offline";
    case "unsupported":
      return "unsupported";
    default:
      return "mock";
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
