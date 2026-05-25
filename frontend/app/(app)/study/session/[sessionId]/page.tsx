import { StudySessionDetailClient } from "@/components/workspace/StudySessionDetailClient";

export default async function StudySessionDetailPage({
  params
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <StudySessionDetailClient sessionId={sessionId} />;
}
