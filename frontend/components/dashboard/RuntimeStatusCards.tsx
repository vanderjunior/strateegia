import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { CapabilityCard } from "@/lib/api/types";
import { runtimeStatusCards } from "@/lib/mock/mentorium-demo-data";

export function RuntimeStatusCards({
  cards = runtimeStatusCards
}: {
  cards?: CapabilityCard[];
}) {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.title}>
          <Badge>{card.status.replaceAll("_", " ")}</Badge>
          <CardTitle className="mt-5">{card.title}</CardTitle>
          <p className="mt-4 text-sm leading-7 text-silver">{card.summary}</p>
          <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
            {card.detail}
          </p>
        </Card>
      ))}
    </div>
  );
}
