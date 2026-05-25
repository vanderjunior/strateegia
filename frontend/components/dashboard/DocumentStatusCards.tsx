import type { CapabilityCard } from "@/lib/api/types";
import { ProductCapabilityCard } from "@/components/product/ProductCapabilityCard";
import { documentStatusCards } from "@/lib/mock/mentorium-demo-data";

export function DocumentStatusCards({
  cards = documentStatusCards
}: {
  cards?: CapabilityCard[];
}) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {cards.map((card) => (
        <ProductCapabilityCard key={card.internalKey ?? card.title} card={card} />
      ))}
    </div>
  );
}
