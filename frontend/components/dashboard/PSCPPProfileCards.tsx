import type { CapabilityCard } from "@/lib/api/types";
import { ProductCapabilityCard } from "@/components/product/ProductCapabilityCard";
import { pscppProfileCards } from "@/lib/mock/mentorium-demo-data";

export function PSCPPProfileCards({
  cards = pscppProfileCards
}: {
  cards?: CapabilityCard[];
}) {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      {cards.map((card) => (
        <ProductCapabilityCard key={card.internalKey ?? card.title} card={card} />
      ))}
    </div>
  );
}
