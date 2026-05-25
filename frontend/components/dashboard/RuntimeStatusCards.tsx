import type { CapabilityCard } from "@/lib/api/types";
import { ProductCapabilityCard } from "@/components/product/ProductCapabilityCard";
import { runtimeStatusCards } from "@/lib/mock/mentorium-demo-data";

export function RuntimeStatusCards({
  cards = runtimeStatusCards
}: {
  cards?: CapabilityCard[];
}) {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <ProductCapabilityCard key={card.internalKey ?? card.title} card={card} />
      ))}
    </div>
  );
}
