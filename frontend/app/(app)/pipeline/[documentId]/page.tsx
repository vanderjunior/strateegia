import { PipelineDetailReadOnlyClient } from "@/components/workspace/PipelineDetailReadOnlyClient";

export default async function PipelineDetailPage({
  params
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  return <PipelineDetailReadOnlyClient documentId={documentId} />;
}
