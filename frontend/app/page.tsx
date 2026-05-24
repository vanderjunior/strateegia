import { DashboardPreview } from "@/components/dashboard/DashboardPreview";
import { PublicNav } from "@/components/layout/PublicNav";
import { EarlyAccessSection } from "@/components/landing/EarlyAccessSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { Hero } from "@/components/landing/Hero";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { PipelineSection } from "@/components/landing/PipelineSection";

export default function HomePage() {
  return (
    <>
      <PublicNav />
      <main className="pb-16">
        <Hero />
        <PipelineSection />
        <FeaturesSection />
        <DashboardPreview />
        <HowItWorksSection />
        <EarlyAccessSection />
      </main>
    </>
  );
}
