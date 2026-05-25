import type { Audience, CapabilityCard } from "@/lib/api/types";
import type { ReactNode } from "react";
import { Card, CardTitle } from "@/components/ui/card";
import { FriendlyStatusBadge } from "@/components/product/FriendlyStatusBadge";
import { getUserFacingCapability, shouldShowCapability, translateInternalTerm } from "@/lib/product/product-language";

export function ProductCapabilityCard({
  card,
  audience = "student",
  technicalDetails = false,
  trailingContent
}: {
  card: CapabilityCard;
  audience?: Audience;
  technicalDetails?: boolean;
  trailingContent?: ReactNode;
}) {
  const friendly = card.internalKey ? getUserFacingCapability(card.internalKey, audience) : null;

  if (card.internalKey && !shouldShowCapability(card.internalKey, audience)) {
    return null;
  }

  const title = friendly?.label ?? translateInternalTerm(card.title, audience);
  const summary = friendly?.description ?? translateInternalTerm(card.summary, audience);
  const detail = translateInternalTerm(card.detail, audience);

  return (
    <Card className="h-full">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <FriendlyStatusBadge status={card.status} audience={audience} />
        {trailingContent}
      </div>
      <CardTitle className="mt-5">{title}</CardTitle>
      <p className="mt-4 text-sm leading-7 text-silver">{summary}</p>
      <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">{detail}</p>
      {technicalDetails && card.internalKey ? (
        <div className="mt-4 rounded-full border border-[rgba(168,184,196,0.14)] bg-[rgba(168,184,196,0.06)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
          detalhe tecnico
        </div>
      ) : null}
    </Card>
  );
}
