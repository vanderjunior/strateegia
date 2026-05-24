import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { studyOverviewCards } from "@/lib/mock/mentorium-demo-data";

export function StudyOverviewCards() {
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      {studyOverviewCards.map((card) => (
        <Card key={card.title}>
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
            estudo
          </div>
          <CardTitle className="mt-5 text-[1.7rem]">{card.value}</CardTitle>
          <p className="mt-3 text-sm text-silver">{card.title}</p>
          <p className="mt-2 text-sm text-[rgba(232,238,242,0.68)]">{card.note}</p>
          <div className="mt-5">
            <Progress value={card.metric} />
          </div>
        </Card>
      ))}
    </div>
  );
}
