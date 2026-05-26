import type { OnboardingViewModel } from "@/lib/api/types";
import { onboardingViewModelMock } from "@/lib/mock/mentorium-demo-data";

export function buildOnboardingViewModel(): OnboardingViewModel {
  return {
    ...onboardingViewModelMock,
    summary: [...onboardingViewModelMock.summary],
    readyHighlights: [...onboardingViewModelMock.readyHighlights],
    reviewHighlights: [...onboardingViewModelMock.reviewHighlights],
    steps: onboardingViewModelMock.steps.map((step) => ({
      ...step,
      primaryLink: { ...step.primaryLink },
      secondaryLinks: step.secondaryLinks.map((link) => ({ ...link }))
    }))
  };
}
