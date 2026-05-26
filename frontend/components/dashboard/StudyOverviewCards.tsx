import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { translateInternalTerm } from "@/lib/product/product-language";
import type { StudyOverviewCard } from "@/lib/api/types";
import { studyOverviewCards } from "@/lib/mock/mentorium-demo-data";

export function StudyOverviewCards({
  cards = studyOverviewCards
}: {
  cards?: StudyOverviewCard[];
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      {cards.map((card, index) => (
        <Card key={card.id ?? `${card.internalKey ?? "study-card"}-${card.title}-${index}`} className="min-w-0">
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
            {translateInternalTerm(card.title, "student")}
          </div>
          <CardTitle className="mt-5 break-words text-[1.7rem] leading-[1.05]">
            {card.value}
          </CardTitle>
          <p className="mt-3 break-words text-sm leading-7 text-[rgba(232,238,242,0.72)]">
            {translateInternalTerm(card.note, "student")}
          </p>
          <div className="mt-5">
            <Progress value={card.metric} />
          </div>
        </Card>
      ))}
    </div>
  );
}
