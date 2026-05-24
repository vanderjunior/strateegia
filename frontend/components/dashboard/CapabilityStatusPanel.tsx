import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { capabilityStatusBadgeClass, capabilityStatusLabel, sourceLabel } from "@/lib/adapters/capabilities";
import type { CapabilityStatusItem } from "@/lib/api/types";

export function CapabilityStatusPanel({ items }: { items: CapabilityStatusItem[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {items.map((item) => (
        <Card key={item.id} className="flex h-full flex-col justify-between gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
                capability
              </div>
              <h3 className="mt-3 font-serif text-2xl text-ink">{item.label}</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className={capabilityStatusBadgeClass(item.status)}>
                {capabilityStatusLabel(item.status)}
              </Badge>
              <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
                {sourceLabel(item.source)}
              </Badge>
            </div>
          </div>
          <p className="text-sm leading-7 text-silver">{item.detail}</p>
        </Card>
      ))}
    </div>
  );
}
