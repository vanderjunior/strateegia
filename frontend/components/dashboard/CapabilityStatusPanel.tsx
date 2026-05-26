import { Card } from "@/components/ui/card";
import { sourceLabel } from "@/lib/adapters/capabilities";
import type { CapabilityStatusItem } from "@/lib/api/types";
import { FriendlyStatusBadge } from "@/components/product/FriendlyStatusBadge";
import { getUserFacingCapability, translateInternalTerm } from "@/lib/product/product-language";
import { Badge } from "@/components/ui/badge";

export function CapabilityStatusPanel({ items }: { items: CapabilityStatusItem[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {items.map((item) => (
        <Card key={item.id} className="flex h-full min-w-0 flex-col justify-between gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="section-kicker">
                capacidade
              </div>
              <h3 className="mt-3 break-words font-serif text-2xl text-ink">
                {item.internalKey
                  ? (getUserFacingCapability(item.internalKey, "student")?.label ?? translateInternalTerm(item.label, "student"))
                  : translateInternalTerm(item.label, "student")}
              </h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <FriendlyStatusBadge status={item.status} />
              <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
                {sourceLabel(item.source)}
              </Badge>
            </div>
          </div>
          <div className="h-px w-full bg-[linear-gradient(90deg,rgba(168,184,196,0.14),transparent)]" />
          <p className="text-sm leading-7 text-silver">
            {item.internalKey
              ? (getUserFacingCapability(item.internalKey, "student")?.description ?? translateInternalTerm(item.detail, "student"))
              : translateInternalTerm(item.detail, "student")}
          </p>
        </Card>
      ))}
    </div>
  );
}
