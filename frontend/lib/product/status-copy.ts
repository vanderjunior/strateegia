import type { Audience, CapabilityStatus } from "@/lib/api/types";

export type StatusTone = "positive" | "warning" | "neutral" | "muted";

export interface UserFacingStatusCopy {
  label: string;
  tone: StatusTone;
  audienceLabel?: Partial<Record<Audience, string>>;
}

export const statusCopy: Record<CapabilityStatus, UserFacingStatusCopy> = {
  implemented_and_tested: {
    label: "Validado",
    tone: "positive"
  },
  implemented_but_needs_manual_validation: {
    label: "Revisão necessária",
    tone: "warning"
  },
  partially_implemented: {
    label: "Parcial",
    tone: "warning"
  },
  foundation_only: {
    label: "Ainda não executável",
    tone: "neutral"
  },
  metadata_only: {
    label: "Orientação guiada",
    tone: "neutral"
  },
  mocked_or_demo_only: {
    label: "Demonstração",
    tone: "neutral"
  },
  not_implemented: {
    label: "Não implementado",
    tone: "muted"
  },
  intentionally_deferred: {
    label: "Adiado intencionalmente",
    tone: "muted"
  },
  unclear_needs_follow_up: {
    label: "Painel em validação",
    tone: "warning"
  }
};
